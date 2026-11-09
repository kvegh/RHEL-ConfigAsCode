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
overrides. The Vault credential source was unresolved at initialization and
was subsequently selected as an existing protected external password file.

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
Scope documentation commit: `ca6371c`. Later discussion accepts fuller DNF
settings as CaC data and asks for the existing CoP presence-based style.
The template proposal therefore supersedes its initial managed flags with
defined/apply and undefined/skip semantics and separate scan metadata. This does
not establish universal field omission behavior for every System Role.
Mandatory new-host inputs must be validated rather than silently skipped.
Corresponding follow-up commit: `37ac7a9`. Static validation confirms a sparse
desired-section map, separate scan metadata and 21 commented catalogue areas;
no apply module is selected by the generic template. These remain design/data
checks, not verification of executable capture or apply behavior.

## 2026-11-09 — Record the selected external encryption password file

Documentation commit: `a9d50c9`. The owner selected an existing protected
Ansible Vault password file, resolving the encryption-input question. Its actual
name, path and contents stay outside both repositories. Metadata-only checks
confirmed that the file exists, is readable and has mode600; no contents were read.

This corrects the earlier unresolved-source wording. It does not implement or
verify encryption, scanning or applying configuration. Module policy remains
an independent unanswered decision; optional-only behavior is a recommendation.
No real host configuration, credential or new runtime mechanism was added.

## 2026-11-09 — Start defining the template one module at a time

The owner requested building the template in the original brainstorming order,
clarifying a bounded scope for each module before expanding it. The comments
now begin with root password and preserve the original sequence through
subscription, repositories and Insights. Discussion order does not prescribe
execution order. Later catalogue areas remain unexpanded.

The first proposal contains one root-password hash field, with capture/replay
versus supplied-only behavior awaiting the owner's choice. Real hashes remain
inside encrypted host data. No plaintext recovery, account-policy expansion,
scanner, apply operation or live host change is introduced. The independent
optional-module policy remains unanswered. Version stays 0.0.1 because these
are documentation and inactive template comments only.

Template/documentation commit: `09770eb`. YAML parsing, empty desired-section
maps, original comment ordering, generic placeholders and whitespace checks
passed. These are static checks only; no executable functionality is claimed.
