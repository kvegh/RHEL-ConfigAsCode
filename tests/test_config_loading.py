"""Test the real Ansible loader, without running host-changing tasks.

Run: python3.12 -m unittest discover -s tests -p 'test_config_loading.py' -v
Requires existing ansible-playbook, PyYAML and cryptography; installs nothing.
Random Vault credentials and generic fixtures stay in private temporary data.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import unittest

import yaml


PROJECT = Path(__file__).resolve().parents[1]


class ConfigLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("ansible-playbook") is None:
            raise RuntimeError("An existing ansible-playbook CLI is required")
        cls.workspace = tempfile.TemporaryDirectory(prefix="rhel-cac-config-tests-")
        cls.directory = Path(cls.workspace.name)
        cls.directory.chmod(0o700)
        cls.original_local_temp = os.environ.get("ANSIBLE_LOCAL_TEMP")
        os.environ["ANSIBLE_LOCAL_TEMP"] = str(cls.directory / "ansible-local")
        # Ansible initializes temporary storage when importing Vault/constants.
        from ansible.parsing.vault import VaultLib, VaultSecret
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519

        cls.password = secrets.token_urlsafe(32).encode()
        cls.vault = VaultLib([("default", VaultSecret(cls.password))])
        cls.password_file = cls.directory / "vault-password"
        cls.password_file.write_bytes(cls.password)
        cls.password_file.chmod(0o600)
        cls.public_key = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
        ).decode()
        # Structured fixture only; never a real account credential.
        cls.hash_value = "$" + "6$fixturesalt$" + "A" * 86
        cls.private_canary = "FIXTURE_PRIVATE_KEY_MUST_NOT_APPEAR_IN_OUTPUT"
        cls.default = {
            "root_password": {"password_hash": cls.hash_value},
            "accounts": [{
                "name": "fixture_admin", "home": "/home/fixture_admin",
                "shell": "/bin/bash", "ssh_public_keys": [cls.public_key],
                "ssh_private_key": cls.private_canary,
            }],
            "privilege": {"wheel_members": ["fixture_admin"], "wheel_nopasswd": True},
            "ssh": {"password_authentication": True},
        }

    @classmethod
    def tearDownClass(cls):
        if cls.original_local_temp is None:
            os.environ.pop("ANSIBLE_LOCAL_TEMP", None)
        else:
            os.environ["ANSIBLE_LOCAL_TEMP"] = cls.original_local_temp
        cls.workspace.cleanup()

    def document(self, default=None, stored=None):
        return {
            "rhel_cac": {
                "schema_version": 1,
                "default_config": copy.deepcopy(self.default if default is None else default),
                "stored_config": copy.deepcopy({} if stored is None else stored),
            },
            "scan_metadata": {},
        }

    def run_loader(self, document, *, source="default_config", overrides=None,
                   expected=None, encrypted=True, include_source=True):
        with tempfile.TemporaryDirectory(dir=self.directory, prefix="case-") as case:
            case_path = Path(case)
            config = case_path / "configuration.yml"
            serialized = yaml.safe_dump(document).encode()
            config.write_bytes(self.vault.encrypt(serialized) if encrypted else serialized)
            config.chmod(0o600)
            variables = {"config_file": str(config)}
            if include_source:
                variables["config_source"] = source
            if overrides is not None:
                variables["rhel_cac_overrides"] = overrides
            tasks = [{"name": "Run the actual protected configuration loader",
                      "ansible.builtin.import_tasks": str(PROJECT / "tasks/load_config.yml")}]
            if expected is not None:
                variables["fixture_expected_config"] = expected
                tasks.append({
                    "name": "Verify resolved configuration and absence semantics",
                    "ansible.builtin.assert": {
                        "that": "rhel_cac_effective == fixture_expected_config", "quiet": True,
                    },
                })
            playbook = case_path / "load.yml"
            playbook.write_text(yaml.safe_dump([{
                "name": "Test encrypted configuration loading only", "hosts": "localhost",
                "connection": "local", "gather_facts": False, "become": False,
                "no_log": True, "tasks": tasks,
            }], sort_keys=False))
            inputs = case_path / "launch.yml"
            inputs.write_text(yaml.safe_dump(variables))
            inputs.chmod(0o600)
            environment = os.environ.copy()
            environment.update({
                "ANSIBLE_LOCAL_TEMP": str(case_path / "ansible-local"),
                "ANSIBLE_REMOTE_TEMP": str(case_path / "ansible-remote"),
                "ANSIBLE_NOCOLOR": "1", "ANSIBLE_DISPLAY_ARGS_TO_STDOUT": "false",
                "ANSIBLE_STDOUT_CALLBACK": "default", "ANSIBLE_FACT_CACHING": "memory",
                "ANSIBLE_RETRY_FILES_ENABLED": "false",
            })
            result = subprocess.run([
                "ansible-playbook", "-i", "localhost,", str(playbook),
                "--vault-password-file", str(self.password_file), "-e", "@" + str(inputs),
            ], env=environment, text=True, capture_output=True, timeout=45, check=False)
            output = result.stdout + result.stderr
            for protected in (self.password.decode(), self.hash_value,
                              self.private_canary, self.public_key):
                self.assertFalse(protected in output, "Protected fixture escaped no_log output")
            task_names = [line for line in output.splitlines() if line.startswith("TASK [")]
            diagnostic = "Last task: " + (task_names[-1] if task_names else "no task executed")
            return result.returncode, diagnostic

    def assert_accepted(self, document, **kwargs):
        code, diagnostic = self.run_loader(document, **kwargs)
        self.assertEqual(code, 0, diagnostic)

    def assert_rejected(self, document, **kwargs):
        code, diagnostic = self.run_loader(document, **kwargs)
        self.assertNotEqual(code, 0, diagnostic)

    def test_default_configuration_is_selected(self):
        self.assert_accepted(self.document(), expected=self.default)

    def test_stored_configuration_is_selected(self):
        stored = {"ssh": {"password_authentication": False}}
        self.assert_accepted(self.document(stored=stored), source="stored_config", expected=stored)

    def test_external_dictionary_fields_override_and_lists_replace(self):
        replacement = copy.deepcopy(self.default["accounts"][0])
        replacement["name"] = "fixture_operator"
        overrides = {
            "accounts": [replacement],
            "privilege": {"wheel_members": ["fixture_operator"], "wheel_nopasswd": False},
            "ssh": {"password_authentication": False},
        }
        expected = copy.deepcopy(self.default)
        expected.update(overrides)
        self.assert_accepted(self.document(), overrides=overrides, expected=expected)

    def test_omitted_sections_and_empty_account_list_are_valid(self):
        for configuration in ({}, {"accounts": []}):
            with self.subTest(configuration=configuration):
                self.assert_accepted(self.document(default=configuration), expected=configuration)

    def test_recursive_override_preserves_unsupplied_fields(self):
        expected = copy.deepcopy(self.default)
        expected["privilege"]["wheel_nopasswd"] = False
        self.assert_accepted(self.document(), overrides={"privilege": {"wheel_nopasswd": False}},
                             expected=expected)

    def test_configuration_source_is_mandatory_and_restricted(self):
        self.assert_rejected(self.document(), include_source=False)
        self.assert_rejected(self.document(), source="unrecognized_source")

    def test_plaintext_actual_configuration_is_rejected(self):
        self.assert_rejected(self.document(), encrypted=False)

    def test_locked_and_malformed_root_hashes_are_rejected(self):
        for value in ("!" + self.hash_value, "plaintext-password", "$" + "6$incomplete"):
            with self.subTest(kind="locked" if value.startswith("!") else "malformed"):
                self.assert_rejected(self.document(default={"root_password": {"password_hash": value}}))

    def test_invalid_accounts_are_rejected(self):
        for accounts in ([{"name": "fixture_admin"}],
                         [{"name": "root", "ssh_public_keys": [self.public_key]}],
                         [{"name": "invalid name", "ssh_public_keys": [self.public_key]}]):
            with self.subTest(case="invalid account"):
                self.assert_rejected(self.document(default={"accounts": accounts}))

    def test_unsupported_sections_and_string_booleans_are_rejected(self):
        self.assert_rejected(self.document(default={"unimplemented_area": {"setting": True}}))
        self.assert_rejected(self.document(default={"ssh": {"password_authentication": "false"}}))


if __name__ == "__main__":
    unittest.main()
