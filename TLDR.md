# RHEL CaC quick start

Already-running RHEL 9/x86_64 with elevated Ansible access. All modules optional.
The first deployment slice manages root hashes, declared accounts/public keys,
wheel sudo and SSH password authentication.

Keep actual configuration whole-file Vault encrypted in the private companion.
Require `config_source=default_config` or `config_source=stored_config` and
`config_file`. Optional `rhel_cac_overrides` takes precedence. Private client
keys remain in encrypted data and are never deployed to targets.

Run `deploy.yml`, check with `tests/verify.yml`, then repeat deployment.
Use authorized disposable targets; SSH changes and restart affect connectivity.
See the [README](README.md) for commands, dependencies, scope and verification gaps.

For the repeatable two-host functional workflow, run `python3.12
tests/run_functional.py` with the protected inventory, default configuration,
Vault-password-file, installed collection roots and enrolled known-hosts inputs
shown in the [functional test instructions](README.md#automated-functional-test).
It verifies apply/repeat and four fresh key-only logins with passwordless sudo.
Generated management keys are tried first, so hardened hosts can be tested again.
Raw evidence stays encrypted; temporary client keys are removed on normal exit.
The earlier 0.0.2 deployment and the repeatable 0.0.3 runner both passed on the
two authorized guests. The repeatable run made zero changes and passed all
four fresh key/sudo logins. AAP end-to-end acceptance remains future work.

Deployment commits are patch releases. Scanners follow completed deployment
playbooks and are minor releases.


`scan.yml` captures the same four bounded modules for explicitly selected local
accounts. Supply unique new encrypted-output paths and the existing protected
Vault password source in protected inventory. It preserves defaults/client
private keys and refuses existing outputs or unsupported policy. Replay with
`config_source=stored_config`. Add `--scan-output-directory` to the functional
runner for scan → stored replay → captured/default verification. That complete
0.1.0 workflow passed on both test guests, preserved defaults and finished four
fresh key/sudo logins. AAP acceptance and snapshot restoration remain untested.
