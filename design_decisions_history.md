# Design decisions history

## 2026-11-09 — Start RHEL-ConfigAsCode

The owner selected this repository name and public visibility. Reusable RHEL
OS configuration logic and generic templates belong here. Actual configuration
belongs as whole-file Ansible Vault ciphertext in the separate private
RHEL-ConfigAsCode-secrets repository; credentials remain outside Git.
Only the public repository is to be an AAP Advanced Features submodule.

The starting point is a RHEL host after first login with Ansible access. The
owner requires an extensible template, a scanner and applying reviewed saved
configuration, using RHEL System Roles where applicable. Application stacks
are excluded. The initial section schema and added areas are proposals, not
selected architecture or implemented scanning/applying. Supported releases,
target portability and the Vault credential source remain unresolved.

The initialization commit ID will be recorded after that commit is created.
