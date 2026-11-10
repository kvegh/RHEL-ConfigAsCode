"""Exercise real scanner normalization/export tasks with controller fixtures.

The fixtures represent command/slurp observations; no host collector is invoked.
Ansible and its Vault library perform the actual validation and encrypted export.
"""

from __future__ import annotations

import base64
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


class ScanConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("ansible-playbook") is None:
            raise RuntimeError("An existing ansible-playbook CLI is required")
        cls.workspace = tempfile.TemporaryDirectory(prefix="rhel-cac-scan-tests-")
        cls.directory = Path(cls.workspace.name)
        cls.directory.chmod(0o700)
        cls.original_local_temp = os.environ.get("ANSIBLE_LOCAL_TEMP")
        os.environ["ANSIBLE_LOCAL_TEMP"] = str(cls.directory / "ansible-local")
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
        cls.hash_value = "$" + "6$fixturesalt$" + "A" * 86
        cls.private_canary = "SCANNER_MUST_NOT_COPY_PRIVATE_DEFAULT_KEY"

    @classmethod
    def tearDownClass(cls):
        if cls.original_local_temp is None:
            os.environ.pop("ANSIBLE_LOCAL_TEMP", None)
        else:
            os.environ["ANSIBLE_LOCAL_TEMP"] = cls.original_local_temp
        cls.workspace.cleanup()

    def observations(self):
        names = ["fixture_admin", "fixture_operator"]
        accounts = [{"item": name, "stdout":
                     f"{name}:x:1001:1001::/home/{name}:/bin/bash", "rc": 0}
                    for name in names]
        return {
            "rhel_cac_scan_modules": ["root_password", "accounts", "privilege", "ssh"],
            "rhel_cac_scan_accounts": names,
            "ansible_facts": {"distribution": "RedHat", "distribution_major_version": "9",
                              "architecture": "x86_64"},
            "rhel_cac_scan_root_read": {"stdout": f"root:{self.hash_value}:1:0:99999:7:::", "rc": 0},
            "rhel_cac_scan_account_reads": {"results": accounts},
            "rhel_cac_scan_key_reads": {"results": [
                {"item": {"name": name, "home": f"/home/{name}", "shell": "/bin/bash"},
                 "content": base64.b64encode((self.public_key + "\n").encode()).decode()}
                for name in names]},
            "rhel_cac_scan_group_reads": {"results": [
                {"item": name, "stdout": name + " wheel", "rc": 0} for name in names]},
            "rhel_cac_scan_sudo_read": {
                "content": base64.b64encode(b"# Ansible managed\n%wheel ALL=(ALL) NOPASSWD: ALL\n").decode()},
            "rhel_cac_scan_sshd_read": {
                "stdout_lines": ["usedns no", "passwordauthentication no",
                                 "kbdinteractiveauthentication no"], "rc": 0},
            "rhel_cac_scan_hostname_read": {"stdout": "fixture.example.invalid", "rc": 0},
            "rhel_cac_scan_time_read": {"stdout": "2026-01-01T00:00:00Z", "rc": 0},
            # Caller data must not be merged into an independently captured file.
            "rhel_cac_document": {"rhel_cac": {"default_config": {
                "accounts": [{"name": names[0], "ssh_private_key": self.private_canary}]}}},
        }

    def run_scan_tasks(self, observations, *, existing=False, keep_remote_files=False):
        with tempfile.TemporaryDirectory(dir=self.directory, prefix="case-") as case:
            case_path = Path(case)
            destination = case_path / "capture.vault.yml"
            prior = self.vault.encrypt(b"existing_capture: preserve-this-content\n") if existing else None
            if prior is not None:
                destination.write_bytes(prior)
                destination.chmod(0o600)
            variables = copy.deepcopy(observations)
            variables.update({"rhel_cac_scan_output_file": str(destination),
                              "rhel_cac_scan_vault_password_file": str(self.password_file)})
            inputs = case_path / "fixture.yml"
            # The real scanner resolves per-host output paths through hostvars.
            inputs.write_text(yaml.safe_dump({"all": {"hosts": {"fixture_source": variables}}}))
            inputs.chmod(0o600)
            playbook = case_path / "normalize-export.yml"
            playbook.write_text(yaml.safe_dump([{
                "name": "Test actual scanner normalization and export only",
                "hosts": "fixture_source", "connection": "local", "gather_facts": False,
                "become": False, "no_log": True,
                "tasks": [
                    {"name": "Validate scanner scope and controller destination",
                     "ansible.builtin.import_tasks": str(PROJECT / "tasks/scan/inputs.yml")},
                    {"name": "Parse selected local accounts",
                     "ansible.builtin.import_tasks": str(PROJECT / "tasks/scan/parse_accounts.yml"),
                     "when": "'accounts' in rhel_cac_scan_selected_modules"},
                    {"name": "Build a captured configuration from observations",
                     "ansible.builtin.import_tasks": str(PROJECT / "tasks/scan/build.yml")},
                    {"name": "Validate captured deployment parameters",
                     "ansible.builtin.import_tasks": str(PROJECT / "tasks/validate_config.yml")},
                    {"name": "Publish a new encrypted capture",
                     "ansible.builtin.import_tasks": str(PROJECT / "tasks/scan/publish.yml")},
                ],
            }], sort_keys=False))
            environment = os.environ.copy()
            environment.update({"ANSIBLE_LOCAL_TEMP": str(case_path / "ansible-local"),
                                "ANSIBLE_REMOTE_TEMP": str(case_path / "ansible-remote"),
                                "ANSIBLE_NOCOLOR": "1", "ANSIBLE_CACHE_PLUGIN": "memory",
                                "ANSIBLE_KEEP_REMOTE_FILES": str(keep_remote_files).lower(),
                                "ANSIBLE_STDOUT_CALLBACK": "default",
                                "ANSIBLE_DISPLAY_ARGS_TO_STDOUT": "false", "LC_ALL": "C.utf8"})
            result = subprocess.run([
                "ansible-playbook", "-i", str(inputs), str(playbook),
                "--vault-password-file", str(self.password_file),
            ], env=environment, text=True, capture_output=True, timeout=45, check=False)
            output = result.stdout + result.stderr
            for protected in (self.password.decode(), self.hash_value, self.public_key, self.private_canary):
                self.assertFalse(protected in output, "Protected fixture escaped no_log output")
            last_task = "no task executed"
            failed_task = None
            for line in output.splitlines():
                if line.startswith("TASK ["):
                    last_task = line
                elif line.startswith("fatal:"):
                    failed_task = last_task
            diagnostic = "Failure/last task: " + (failed_task or last_task)
            self.assertFalse(list(case_path.glob(".rhel-cac-scan-*")),
                             "Scanner capture workspace was retained")
            published = destination.read_bytes() if destination.exists() else None
            if existing:
                self.assertEqual(published, prior, "Existing encrypted capture was altered")
            document = None
            if published is not None and not existing:
                self.assertTrue(published.startswith(b"$ANSIBLE_VAULT;"))
                document = yaml.safe_load(self.vault.decrypt(published))
            return result.returncode, document, published is not None, diagnostic

    def assert_refused(self, observations, expected_task, *, existing=False, keep_remote_files=False):
        code, _, published, diagnostic = self.run_scan_tasks(
            observations, existing=existing, keep_remote_files=keep_remote_files)
        self.assertNotEqual(code, 0, diagnostic)
        self.assertIn(expected_task, diagnostic, "Refusal occurred before the intended validation")
        if not existing:
            self.assertFalse(published, "A refused observation was nevertheless published")

    def test_valid_capture_is_encrypted_replayable_and_contains_no_private_defaults(self):
        code, document, _, diagnostic = self.run_scan_tasks(self.observations())
        self.assertEqual(code, 0, diagnostic)
        self.assertEqual(document["rhel_cac"]["schema_version"], 1)
        self.assertEqual(document["rhel_cac"]["default_config"], {})
        stored = document["rhel_cac"]["stored_config"]
        self.assertEqual(set(stored), {"root_password", "accounts", "privilege", "ssh"})
        self.assertEqual(stored["root_password"]["password_hash"], self.hash_value)
        self.assertEqual([account["name"] for account in stored["accounts"]],
                         ["fixture_admin", "fixture_operator"])
        self.assertEqual(stored["accounts"][0]["ssh_public_keys"], [self.public_key])
        self.assertTrue(stored["privilege"]["wheel_nopasswd"])
        self.assertFalse(stored["ssh"]["password_authentication"])
        self.assertTrue(document["scan_metadata"]["complete"])
        self.assertFalse(self.private_canary in yaml.safe_dump(document))
        self.assertTrue(all("ssh_private_key" not in account for account in stored["accounts"]))

    def test_selected_subset_does_not_publish_unselected_modules(self):
        observations = self.observations()
        observations["rhel_cac_scan_modules"] = ["root_password"]
        code, document, _, diagnostic = self.run_scan_tasks(observations)
        self.assertEqual(code, 0, diagnostic)
        self.assertEqual(set(document["rhel_cac"]["stored_config"]), {"root_password"})

    def test_locked_root_is_refused_before_publication(self):
        observations = self.observations()
        observations["rhel_cac_scan_root_read"]["stdout"] = "root:!" + self.hash_value + ":1:0:99999:7:::"
        self.assert_refused(observations, "Validate root password hash")

    def test_authorized_key_options_are_refused_before_publication(self):
        observations = self.observations()
        observations["rhel_cac_scan_key_reads"]["results"][0]["content"] = base64.b64encode(
            ('from="192.0.2.0/24" ' + self.public_key + "\n").encode()).decode()
        self.assert_refused(observations, "Validate declared authorized public keys")

    def test_foreign_sudo_grammar_is_refused_before_publication(self):
        observations = self.observations()
        observations["rhel_cac_scan_sudo_read"]["content"] = base64.b64encode(
            b"%other_fixture_group ALL=(ALL) NOPASSWD: ALL\n").decode()
        self.assert_refused(observations, "Require exactly the supported owned wheel rule")

    def test_differing_ssh_password_paths_are_refused_before_publication(self):
        observations = self.observations()
        observations["rhel_cac_scan_sshd_read"]["stdout_lines"] = [
            "usedns no", "passwordauthentication no", "kbdinteractiveauthentication yes"]
        self.assert_refused(observations, "Require SSH policy representable by the single supported boolean")

    def test_existing_capture_is_refused_and_preserved(self):
        self.assert_refused(self.observations(), "Refuse an existing capture destination", existing=True)

    def test_retained_module_files_are_refused_before_encryption(self):
        self.assert_refused(
            self.observations(),
            "Require protected in-memory module transport for capture encryption",
            keep_remote_files=True,
        )


if __name__ == "__main__":
    unittest.main()
