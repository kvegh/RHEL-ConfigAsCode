#!/usr/bin/env python3
"""Run the approved two-host deployment workflow with protected test inputs.

Reason: existing Ansible/SSH CLIs need controller-side key materialization,
ordered runs, recap checks and fresh key-only logins with reliable cleanup.
Justification: ../README.md#automated-functional-test
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def protected_write(path, content):
    """Create an owner-readable file without overwriting an existing path."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)


def ssh_arguments(target, user, options):
    port = int(target.get("ansible_port", 22))
    if not 1 <= port <= 65535:
        raise RuntimeError("Invalid protected target SSH port")
    return ["ssh", *options, "-p", str(port), "-l", user, "--", target["ansible_host"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--vault-password-file", required=True)
    parser.add_argument("--collections", required=True)
    parser.add_argument("--scan-output-directory",
                        help="Optional new capture paths for the scanner/stored-config round trip")
    parser.add_argument("--known-hosts", required=True,
                        help="Protected file containing the explicitly enrolled guest host keys")
    args = parser.parse_args()
    artifact = Path(tempfile.mkdtemp(prefix="rhel-cac-functional-evidence-"))
    artifact.chmod(0o700)
    runtime_directory = None
    vault = None
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="rhel-cac-functional-runtime-") as temporary:
            runtime = Path(temporary)
            runtime_directory = runtime
            runtime.chmod(0o700)
            environment = dict(os.environ)
            environment.update({
                "ANSIBLE_COLLECTIONS_PATH": args.collections,
                "ANSIBLE_LOCAL_TEMP": str(runtime / "ansible-local"),
                "ANSIBLE_SSH_CONTROL_PATH_DIR": str(runtime / "connections"),
                "ANSIBLE_NOCOLOR": "1",
                "ANSIBLE_CACHE_PLUGIN": "memory",
                "ANSIBLE_HOST_KEY_CHECKING": "true",
                "LC_ALL": "C.utf8",
            })
            # Import only after creating private Ansible temporary storage.
            os.environ["ANSIBLE_LOCAL_TEMP"] = environment["ANSIBLE_LOCAL_TEMP"]
            import yaml
            from ansible.parsing.vault import VaultLib, VaultSecret

            source = Path(args.source).resolve(strict=True)
            vault_path = Path(args.vault_password_file).resolve(strict=True)
            vault = VaultLib([("default", VaultSecret(vault_path.read_bytes().strip()))])
            config_path = Path(args.config).resolve(strict=True)
            ciphertext = config_path.read_bytes()
            if not ciphertext.startswith(b"$ANSIBLE_VAULT;"):
                raise RuntimeError("Test configuration must be whole-file Vault ciphertext")
            configuration = yaml.safe_load(vault.decrypt(ciphertext))
            accounts = configuration["rhel_cac"]["default_config"]["accounts"]
            if len(accounts) != 2 or len({account["name"] for account in accounts}) != 2:
                raise RuntimeError("The first functional slice requires its two declared accounts")
            protected_values = [account["ssh_private_key"] for account in accounts]
            root = configuration["rhel_cac"]["default_config"].get("root_password", {})
            if root.get("password_hash"):
                protected_values.append(root["password_hash"])
            known_hosts = runtime / "known_hosts"
            protected_write(known_hosts, Path(args.known_hosts).resolve(strict=True).read_bytes())
            inventory_path = Path(args.inventory).resolve(strict=True)
            if not inventory_path.read_bytes().startswith(b"$ANSIBLE_VAULT;"):
                raise RuntimeError("Test inventory must be whole-file Vault ciphertext")
            inventory = subprocess.run(
                ["ansible-inventory", "--list", "-i", str(inventory_path),
                 "--vault-password-file", str(vault_path)],
                env=environment, capture_output=True, text=True, check=False, timeout=45,
            )
            protected_write(artifact / "inventory.vault",
                            vault.encrypt((inventory.stdout + inventory.stderr).encode()))
            if inventory.returncode:
                raise RuntimeError("Protected test inventory could not be loaded")
            inventory_data = json.loads(inventory.stdout)
            target_group = inventory_data["rhel_cac_targets"]
            if target_group.get("children"):
                raise RuntimeError("The test group must list its two targets directly without children")
            names = target_group["hosts"]
            hostvars = inventory_data["_meta"]["hostvars"]
            if len(names) != 2 or len(set(names)) != 2:
                raise RuntimeError("Expected exactly two authorized disposable test targets")
            for name in names:
                if not all(hostvars[name].get(field) for field in (
                        "rhel_cac_test_baseline_snapshot", "rhel_cac_test_guest_uuid",
                        "ansible_host", "ansible_user")):
                    raise RuntimeError("Each target needs its recorded baseline, identity and connection")
            if len({hostvars[name]["ansible_host"] for name in names}) != 2:
                raise RuntimeError("The two target connection addresses must be distinct")
            management_users = {hostvars[name]["ansible_user"] for name in names}
            keys = {}
            for index, account in enumerate(accounts):
                if not re.fullmatch(r"[a-z_][a-z0-9_-]*\$?", account["name"]):
                    raise RuntimeError("Invalid declared account name")
                key = runtime / ("client-key-" + str(index))
                protected_write(key, account["ssh_private_key"].encode())
                keys[account["name"]] = key
            if len(management_users) != 1 or next(iter(management_users)) not in keys:
                raise RuntimeError("The shared test management user needs its declared client key")
            management = next(iter(management_users))
            ssh_options = ["-o", "UserKnownHostsFile=" + str(known_hosts),
                           "-o", "StrictHostKeyChecking=yes", "-o", "IdentitiesOnly=yes",
                           "-o", "ConnectTimeout=15"]
            # Disable agent and connection reuse to prove each fresh key authentication.
            key_options = [*ssh_options, "-o", "BatchMode=yes", "-o", "IdentityAgent=none",
                           "-o", "ControlMaster=no", "-o", "ControlPath=none",
                           "-o", "PasswordAuthentication=no",
                           "-o", "KbdInteractiveAuthentication=no"]

            def record(stage, completed, elapsed, *, required=True, recap=False, unchanged=False):
                output = completed.stdout + completed.stderr
                protected_write(artifact / (stage + ".vault"), vault.encrypt(output.encode()))
                if any(value and value in output for value in protected_values):
                    raise RuntimeError("Protected configuration appeared in captured tool output")
                result = {"stage": stage, "rc": completed.returncode,
                          "elapsed_seconds": round(elapsed, 2)}
                if not required:
                    result["bootstrap_key_probe"] = True
                rows = re.findall(
                    r"^\S+\s+: ok=(\d+)\s+changed=(\d+)\s+unreachable=(\d+)\s+failed=(\d+)",
                    output, re.MULTILINE,
                )
                if recap:
                    counts = [tuple(map(int, row)) for row in rows]
                    result["recap_totals"] = dict(zip(
                        ("ok", "changed", "unreachable", "failed"),
                        (sum(row[index] for row in counts) for index in range(4)),
                    ))
                    if len(counts) != 2 or any(row[0] == 0 or row[2] or row[3] for row in counts):
                        raise RuntimeError(stage + " did not successfully exercise both targets")
                    if unchanged and any(row[1] for row in counts):
                        raise RuntimeError(stage + " reported unexpected changes")
                results.append(result)
                print(json.dumps(result), flush=True)
                if required and completed.returncode:
                    raise RuntimeError(stage + " failed; protected evidence retained")

            password = None
            for index, name in enumerate(names):
                target = hostvars[name]
                start = time.monotonic()
                completed = subprocess.run(
                    ssh_arguments(target, management, [*key_options, "-i", str(keys[management])])
                    + ["id -un"], stdin=subprocess.DEVNULL,
                    env=environment, capture_output=True, text=True, timeout=35, check=False,
                )
                record("bootstrap-key-" + str(index + 1), completed,
                       time.monotonic() - start, required=False)
                if completed.returncode:
                    # Authentication refusal may be expected on a fresh baseline.
                    # Transport/host-key failures must never trigger a password attempt.
                    if completed.returncode != 255 or "Permission denied" not in completed.stderr:
                        raise RuntimeError("Bootstrap key connection failed before authentication")
                    if shutil.which("sshpass") is None:
                        raise RuntimeError("Password bootstrap requires the existing sshpass utility")
                    if password is None:
                        password = getpass.getpass("Existing disposable test SSH/sudo password: ")
                        if not password:
                            raise RuntimeError("An existing protected test password is required")
                    read_fd, write_fd = os.pipe()
                    try:
                        os.write(write_fd, password.encode() + b"\n")
                        os.close(write_fd)
                        write_fd = None
                        start = time.monotonic()
                        completed = subprocess.run(
                            ["sshpass", "-d", str(read_fd), *ssh_arguments(target, management, [
                                *ssh_options, "-o", "PreferredAuthentications=password",
                                "-o", "PubkeyAuthentication=no",
                                "-o", "ControlMaster=no", "-o", "ControlPath=none",
                            ]), "id -un"], pass_fds=(read_fd,),
                            env=environment, capture_output=True, text=True, timeout=35, check=False,
                        )
                        record("bootstrap-password-" + str(index + 1), completed,
                               time.monotonic() - start)
                    finally:
                        os.close(read_fd)
                        if write_fd is not None:
                            os.close(write_fd)
                if completed.stdout.strip() != management:
                    raise RuntimeError("Authenticated management identity differs from inventory")
            runtime_vars = {
                "config_source": "default_config", "config_file": str(config_path),
                "ansible_ssh_private_key_file": str(keys[management]),
                "ansible_ssh_common_args": shlex.join(ssh_options),
            }
            if password is not None:
                runtime_vars.update(ansible_password=password, ansible_become_password=password)
            variables_file = runtime / "runtime-vars.vault.yml"
            protected_write(variables_file, vault.encrypt(yaml.safe_dump(runtime_vars).encode()))
            base = ["ansible-playbook", "-i", str(inventory_path),
                    "--vault-password-file", str(vault_path), "-e", "@" + str(variables_file)]
            for stage, playbook, unchanged in (
                    ("deploy-first", "deploy.yml", False),
                    ("verify-first", "tests/verify.yml", True),
                    ("deploy-repeat", "deploy.yml", True),
                    ("verify-repeat", "tests/verify.yml", True)):
                start = time.monotonic()
                completed = subprocess.run(base + [str(source / playbook)], cwd=source,
                                           env=environment, capture_output=True, text=True,
                                           timeout=1200, check=False)
                record(stage, completed, time.monotonic() - start, recap=True, unchanged=unchanged)
            if args.scan_output_directory:
                scan_directory = Path(args.scan_output_directory).resolve()
                scan_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                capture_paths = [scan_directory / ("capture-" + str(index + 1).zfill(2) + ".vault.yml")
                                 for index in range(len(names))]
                if any(path.exists() or path.is_symlink() for path in capture_paths):
                    raise RuntimeError("Scanner tests require new capture paths; existing captures are preserved")
                scan_hosts = {}
                for name, capture in zip(names, capture_paths):
                    scan_hosts[name] = dict(hostvars[name],
                                            rhel_cac_scan_output_file=str(capture))
                scan_inventory = {"all": {"children": {
                    "rhel_cac_targets": {"hosts": scan_hosts}}}}
                scan_inventory_file = runtime / "scan-inventory.vault.yml"
                protected_write(scan_inventory_file,
                                vault.encrypt(yaml.safe_dump(scan_inventory).encode()))
                scan_vars = {key: value for key, value in runtime_vars.items()
                             if key not in ("config_source", "config_file")}
                scan_vars.update({
                    "rhel_cac_scan_modules": list(configuration["rhel_cac"]["default_config"]),
                    "rhel_cac_scan_accounts": [account["name"] for account in accounts],
                    "rhel_cac_scan_vault_password_file": str(vault_path),
                    "rhel_cac_test_default_config_file": str(config_path),
                })
                scan_vars_file = runtime / "scan-vars.vault.yml"
                protected_write(scan_vars_file,
                                vault.encrypt(yaml.safe_dump(scan_vars).encode()))
                start = time.monotonic()
                completed = subprocess.run(
                    ["ansible-playbook", "-i", str(scan_inventory_file),
                     "--vault-password-file", str(vault_path),
                     "-e", "@" + str(scan_vars_file),
                     str(source / "tests/scan_roundtrip.yml")],
                    cwd=source, env=environment, capture_output=True,
                    text=True, timeout=1200, check=False,
                )
                record("scan-stored-roundtrip", completed,
                       time.monotonic() - start, recap=True)
                for capture in capture_paths:
                    if not capture.read_bytes().startswith(b"$ANSIBLE_VAULT;"):
                        raise RuntimeError("A stored capture is not whole-file encrypted")
                    if capture.stat().st_mode & 0o077:
                        raise RuntimeError("A stored capture has excessive local permissions")
                if config_path.read_bytes() != ciphertext:
                    raise RuntimeError("The original default configuration ciphertext changed")
                print(json.dumps({"scan_capture_count": len(capture_paths),
                                  "default_configuration_unchanged": True}), flush=True)
            for host_index, name in enumerate(names):
                for account_index, account in enumerate(accounts):
                    start = time.monotonic()
                    completed = subprocess.run(
                        ssh_arguments(hostvars[name], account["name"], [
                            *key_options, "-i", str(keys[account["name"]]),
                        ]) + ["id -un && sudo -n -k /usr/bin/id -u"],
                        stdin=subprocess.DEVNULL, env=environment, capture_output=True, text=True,
                        timeout=35, check=False,
                    )
                    record("key-login-" + str(host_index + 1) + "-" + str(account_index + 1),
                           completed, time.monotonic() - start)
                    if completed.stdout.splitlines() != [account["name"], "0"]:
                        raise RuntimeError("Fresh client-key login or passwordless sudo identity failed")
        protected_write(artifact / "summary.vault.yml",
                        vault.encrypt(yaml.safe_dump({"results": results}).encode()))
        if runtime_directory.exists():
            raise RuntimeError("Temporary credential cleanup did not complete")
        print(json.dumps({"functional_result": "PASS", "targets": 2, "fresh_key_logins": 4,
                          "evidence_directory": str(artifact),
                          "temporary_private_keys_removed": True}), flush=True)
        return 0
    except Exception as error:
        # Do not print arbitrary tool exceptions: they can contain protected data.
        if vault is not None:
            try:
                failure = {"error_type": type(error).__name__, "detail": str(error),
                           "partial_stdout": getattr(error, "stdout", None),
                           "partial_stderr": getattr(error, "stderr", None), "results": results}
                protected_write(artifact / "failure.vault.yml",
                                vault.encrypt(yaml.safe_dump(failure).encode()))
            except Exception:
                # A failure to retain evidence must not turn the test into a pass.
                pass
        reason = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(json.dumps({"functional_result": "FAIL", "reason": reason,
                          "evidence_directory": str(artifact),
                          "temporary_private_keys_removed":
                              runtime_directory is None or not runtime_directory.exists()}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
