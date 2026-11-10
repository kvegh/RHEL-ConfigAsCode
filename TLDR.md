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

Deployment commits are patch releases. Scanners follow completed deployment
playbooks and are minor releases.
