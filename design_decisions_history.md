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

## 2026-11-10 — Implement the first deployment slice before its scanner

The owner approved root hash capture from shadow, declared local accounts with
fresh SSH keypairs saved in encrypted CaC, wheel passwordless sudo and disabled
SSH password authentication with service restart. All modules are optional.
The owner explicitly requires config_source to select default_config or
stored_config, deployment code commits to be patch releases, and scanner code
to follow completed deployment playbooks as minor releases. This deployment
slice advances to 0.0.2; no scanner is included.

The implementation uses ordinary Ansible task files, native account operations,
certified POSIX authorized-key content and certified sudo/SSH System Roles.
Dependencies are pinned to the existing verified artifacts: System Roles1.120.5
and POSIX2.2.2, with combined core minimum2.16. No tool was installed or content
vendored. Selected fields are validated before configuration tasks; external
dictionary overrides recurse and lists replace. Default and stored maps stay
separate. Private client keys never deploy to targets.

Focused review corrected unrelated SSH host-key management, added effective
per-user SSH connection checks and timestamp-independent sudo execution tests.
SSH preserves unrelated configuration, requires existing UseDNS no for its
IP-based management context, validates before restart and reconnects afterward.
Other client contexts and arbitrary policy conversion remain outside this slice.

Ten real Ansible encrypted-input tests passed, including source selection,
overrides, optional sections, invalid inputs and absence of fixture secrets in
output. Deployment and verifier syntax checks and offline production strict lint
passed. These are development checks, not deployed functionality or formal review
acceptance. Protected default preparation verified two distinct matching keypairs;
source shadow access still needs existing sudo authentication. Test guests are
being prepared separately. The owner permits local Ansible for development but
requires AAP from the first functional test. AAP setup and actual deployment,
verification, repeated apply and key-login tests remain pending.

Implementation commit: `9e64c7c` (deployment patch0.0.2). The scanner has not
been authored or included in that commit. This record does not turn the pending
AAP functional checks into passed results.
