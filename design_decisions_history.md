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
selected architecture or implemented scanning/applying. Later owner replies
selected RHEL 9/x86_64 first and new-host configuration with modular external
overrides. The Vault credential source remains unresolved.

Initialization commit: `e780302`. It contains documentation and the explicitly
proposed generic template only. YAML parsing and unmanaged/unscanned defaults
passed static validation; independent scope review found no concrete issue.
Executable scan/apply behavior, certified artifact contents and live tests
remain unverified.

## 2026-11-09 — Define the initial platform and modular input requirement

The owner selected RHEL 9 on x86_64 for initial support, RHEL 10 later and RHEL 8
only as optional funding-dependent future work. Every module must accept external
variables overriding saved CaC. A new host means an already-running RHEL host;
it may be configured from complete external inputs or CaC populated beforehand,
without a prior scan. Reusing a saved configuration for a similar host is required.

The mandatory module list and field/merge semantics are proposals awaiting
agreement. No alternate platform support or executable deployment is implied.
The owner subsequently accepted logging, authentication including AD integration,
services and certificates. The DNF discussion distinguishes repository/update
policy from each package's exact/present/latest setting; no new defaults are selected.
The scope documentation commit ID will be recorded after it is created.
