# Modular configuration and deployment inputs

## Approved behavior

The owner requires independent modules, external overrides for every module,
and configuring an already-running new RHEL host without a prior scan.
Initial support is RHEL 9 on x86_64. This is an OS configuration project.
The owner also expressly accepted logging, authentication (including AD),
services and certificates as configuration areas. AD is a candidate for later
functional testing; no directory target or join operation has been authorized.

A project module means a selectable configuration area. Use certified RHEL
System Roles directly where they provide the capability, and suitable native
Ansible tasks for concrete gaps. This does not require a custom Ansible module
plugin, a new collection, a service or a wrapper around every System Role.

Both input paths must work:

1. Saved configuration supplies defaults; external variables override the
   chosen fields for the target host.
2. A clean configuration plus complete external variables, or CaC populated
   in advance, supplies all required inputs for a new host.

External values take precedence. A missing value does not mean deletion.
The effective configuration must be validated before host changes begin;
required fields must be supplied, not guessed from another host's identity.
Credentials stay in protected inputs, including when supplied as overrides.

## CaC presence semantics

The existing AAP importer calls CoP's `infra.aap_configuration.dispatch`, whose
role selection checks whether each configuration variable is defined. Individual
resource roles then process their supplied entries. This is a section-level
pattern; role defaults and enforce-default options can still affect omitted fields.

Use that presence-based style for this project's proposal:

- An omitted optional section is skipped and its existing state is preserved.
- A defined section with valid settings is applied; external settings override
  corresponding saved settings. Do not add a separate managed/enabled flag.
- An empty list supplies no items. A section without valid settings must not
  trigger a System Role whose defaults would change unrelated configuration.
- Deletion requires an explicit supported removal instruction, such as an item's
  `state: absent`. Missing sections, entries or failed reads are not deletion.
- New-host deployment validates the agreed mandatory sections first and fails
  clearly if required inputs are absent. Partial configuration may omit them.

Check field behavior for each selected System Role rather than assuming that
undefined fields are universally ignored. Preserve meaningful `false` and zero
values when mapping inputs.

## DNF configuration data

The owner accepted the fuller DNF scope as CaC entries. Represent only declared
settings; omitted settings are left unchanged. Keep package installation entries
and their exact/present/latest policy separate from these package-manager settings.

| Area | Data to capture and apply when defined |
|---|---|
| Repositories | IDs, definitions, base URL/mirror list/metalink, enabled state and applicable access/proxy settings |
| Trust | GPG keys, package/metadata signature-check policy, TLS verification and applicable CA/client-certificate references |
| Release selection | Subscription/repository release lock and explicitly enabled module streams |
| Package constraints | Exclusions, inclusion filters where used, and explicit version-lock entries |
| Dependency behavior | Weak-dependency installation and applicable existing DNF dependency settings |

Capture existing values without imposing stricter or looser defaults. Protected
repository credentials and private key material belong only in encrypted or
protected inputs. A scan cannot infer whether an observed package version was
an intentional pin. In a new-host deployment, validate that declared repositories
can supply the requested packages; no automatic repository or trust bypass is implied.

## Proposed smallest mandatory set

This set is for owner discussion, not selected or implemented behavior.
Mandatory means the deployment contract must account for the area; an explicit
approved preserve-existing choice may be appropriate where no change is wanted.

| Module | Required decision/input area |
|---|---|
| Host identity | Target hostname, hosts-file policy, locale/keymap and timezone |
| Accounts and privilege | Root policy, administrative accounts/groups/homes, sudo and required access keys |
| SSH | Server access policy and persistent sshd configuration |
| Network | Management connectivity, interface/profile identity, addresses or DHCP intent, DNS and routes |
| Registration and software sources | Subscription/Satellite/offline mode, repository definitions and enabled state, relevant DNF policy |
| Packages | Explicit baseline packages and exact/present/latest policy |
| Time synchronization | Selected NTP/PTP sources or an explicit preserve-existing choice |

Add the four accepted areas to the proposed base contract: authentication,
logging, OS services and certificates/trust. Their required fields and whether
an explicit preserve-existing choice is sufficient for a particular deployment
still need agreement. Acceptance of an area does not enable every possible service.

Target identity, RHEL release/architecture, Ansible/become access, required inputs
and supported section capabilities also need a preflight validation before apply.
These checks are technical prerequisites, not extra deployable services.

The remaining catalogue areas stay independent modules: storage, mounts,
SELinux, firewall, kernel, audit/session recording, additional crypto policy,
boot/kdump, schedules and specialized OS facilities.
This minimum does not authorize changing their existing state or applying an
unspecified hardening profile. Insights remains an explicit setting, not an
automatic registration side effect.

## Proposed value handling and portability

The illustrative template lists available sections as comments and starts with
no desired sections defined. Capture completeness and required external inputs
belong in separate scan metadata; they must not accidentally select a module.
The exact schema and field contracts remain proposals.

The simplest proposed override rule is recursive replacement of explicitly
provided dictionary fields, with supplied lists replacing the saved list as a
whole. Do not append disks, interfaces, accounts or firewall rules implicitly.
Define explicit removal separately from absence. Finalize these semantics with
the schema before implementation; no custom merge framework is selected.

A scan preserves observed configuration and marks inaccessible, unsupported or
unscanned sections. Desired policy and target-specific overrides are separate
decisions. Reusing captured NIC/disk/SSH/subscription identities on a different
host requires explicit target mapping or a deliberate regeneration policy.
Storage creation, resizing, deletion and encryption changes must remain explicit;
the fact that a new host is being configured does not authorize repartitioning it.

## Verification required before delivery

Exercise every module's override contract, absence versus explicit removal and
incomplete-capture behavior. On an authorized disposable RHEL host, demonstrate
scan/encrypt/apply/repeat and the no-prior-scan deployment path using supplied
variables. Verify effective configuration and preservation of unrelated state.
This initial documentation release performs none of those host operations.
