# RHEL-ConfigAsCode

Configuration as code for the RHEL operating system after first login, assuming
working Ansible access. Application stacks, OS installation and hypervisor
provisioning are outside this project's current scope.

The initial target is **RHEL 9 on x86_64 only**. RHEL 10 is later work. RHEL 8
support is optional future scope contingent on separate funding and approval;
neither it nor other architectures belong in the first implementation. Check
the selected RHEL 9 minor release before using version-specific role features.

## Status

Version **0.0.1** initializes the repository, records the owner's requirements,
and proposes configuration sections and an extensible capture template. There
are no executable scan or apply playbooks yet. No host has been scanned or
configured, and no runtime or certified-collection compatibility is claimed.

This public repository holds reusable playbooks, generic templates and documentation.
Actual host configuration belongs only as whole-file Ansible Vault ciphertext
in the separate private `RHEL-ConfigAsCode-secrets` repository. Vault credentials
stay outside Git. The owner selected an existing protected Ansible Vault password
file; supply its location through the protected execution environment. Its actual
name, path and contents are not repository configuration. The private companion
is not an umbrella submodule.

## Owner-approved requirements

- Use RHEL System Roles wherever they support the required behavior. Account for
  every role in the catalogue without automatically activating every subsystem.
- Keep reusable execution logic separate from actual host configuration.
- Maintain an extensible generic configuration template. A new scan starts from
  a copy, fills observable configuration and produces encrypted host data.
- Provide a read-only scanner and a separate operation to apply reviewed saved
  configuration to an explicitly selected RHEL host.
- Build independent modules. Every module accepts external variables that
  override saved CaC values, so one saved configuration can seed similar hosts.
- Support configuring an already-running new host without a prior scan, using
  complete externally supplied values or a configuration populated in advance.
  Here, deploy means configure RHEL; it does not mean install the operating system.
- Define a minimal mandatory module set for that deployment path. The concrete
  set is proposed in [module contracts](docs/modules.md) and needs agreement.
- Include logging, authentication (including AD integration), OS services and
  certificate configuration, as subsequently accepted by the owner.
- Cover root/account passwords, local users/groups/homes, sudo, package policies,
  sshd, firewall, kernel settings, mounts, SELinux, all network interfaces,
  storage including mirrors/LVM, subscriptions, repositories and Insights.

## Configuration sections for discussion

Rows without a proposed label organize requested or subsequently accepted
coverage. Proposed rows answer the question about major missing OS configuration.
The grouping and field schema remain proposals until agreed; they are not a
claim of implemented support. Specific role coverage is in
[the System Roles catalogue](docs/system-roles.md).

| Area | Configuration to represent |
|---|---|
| Local accounts | Root and user password hashes or supplied replacements; UID/GID, groups, home, shell, lock/expiry/aging and authorized public keys |
| Privilege | Sudo rules, permitted commands and groups; service-account privilege boundaries |
| Packages | Name, epoch/version/release/architecture; explicit exact, present, latest or absent policy; multiple installed kernels |
| SSH | Effective sshd configuration and persistent drop-ins; client configuration and access keys |
| Firewall | Zones, interfaces, services, ports, sources, rich rules and policies; permanent versus runtime state |
| Kernel settings | Persistent sysctl settings and observed runtime values, kept distinct |
| Mounts | Sources, targets, filesystem types, options, dependencies and automounts |
| SELinux | Mode, policy, booleans, persistent file contexts and port labels |
| Network | All interfaces and persistent profiles, addresses, DHCP intent, DNS, routes/rules, bonds, bridges, VLANs and MTU |
| Storage | Persistent device identity, partitions, filesystems, LVM, mirrors/RAID, swap and encryption where used |
| Registration and software sources | Subscription/Satellite state, release lock, repository definitions and enabled state, GPG trust, DNF settings, exclusions/version locks/module streams, Insights settings |
| Proposed: host identity | Hostname, hosts file, timezone, locale/keymap |
| Proposed: time synchronization | NTP/PTP configuration |
| Authentication | PAM/authselect, NSS/SSSD and AD/directory membership configuration, password/lockout policy |
| Services | Enabled/disabled/masked systemd units and overrides; timers and cron are proposed scheduling coverage |
| Logging | journald, rsyslog destinations and rotation/retention; audit rules and session recording are proposed extensions |
| Certificates and trust | Host certificate configuration, CA trust and protected references to required key/issuance inputs |
| Proposed: additional security policy | Crypto policy, FIPS state and optional AIDE/fapolicyd |
| Proposed: boot and recovery | Bootloader/default kernel, command line, modules/blacklists, initramfs requirements and kdump |
| Proposed: operating defaults | Limits, umask, tuning, login defaults/banners and selected OS configuration files |
| Proposed: specialized OS facilities | NBDE, quotas, udev/multipath, clustering/GFS2 and attestation only where explicitly needed |

Fuller DNF policy means repository definitions/access and GPG/TLS verification,
release locks and module streams, exclusions/version locks and dependency policy
such as weak dependencies. It is separate from each package's exact/present/latest
policy. Capture existing settings first; do not silently impose new package policy.
See the [RHEL 9 DNF guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/managing_software_with_the_dnf_tool/index).

## Scan and apply proposal

Use ordinary Ansible orchestration and the selected System Roles; no separate
service, database or generic plugin framework is proposed. Prefer existing
read-only facts and verified native role export interfaces before adding a
small subsystem-specific reader for a concrete gap.

1. Select the source host and a new destination configuration, using the generic
   template as the starting point. Keep existing captures intact.
2. Collect persistent configuration separately from useful observed runtime
   state. Record each section's completeness and any required external inputs.
3. Encrypt before publishing host data to the private repository. Do not log
   secrets, retain plaintext host-data files or cache secret facts.
4. Review captured settings and choose actual desired policies. A scan does not
   know whether a package should remain pinned, present or track latest.
5. Resolve external per-module overrides over the saved values and validate the
   effective target configuration. Omitted values retain their saved meaning.
6. Apply only reviewed, explicitly managed sections to the chosen target, then
   verify the resulting configuration and a repeated apply.

Alternatively, begin with a clean template and supply all required deployment
inputs externally or populate CaC first. A previous scan is not required.

The illustrative [proposed template](templates/host-config.proposed.yml) uses
sparse desired configuration: define a section to apply it, and omit it to
leave that area unchanged. There is no additional managed flag. Keep scan
completeness separate from desired values. The exact field schema is not selected
and no executable code consumes it yet. Empty or failed reads must never imply
permission to delete configuration. Updating the generic template must preserve
previously filled host values. New-host deployment must reject missing mandatory
inputs before changing the host; partial configuration may skip omitted modules.

## Capture limits

- A privileged scan can read local password hashes and lock/aging state, not the
  original plaintext passwords. Whether to preserve hashes is still a decision.
- Registration state does not recover the original activation key or login
  credentials. Unknown credentials remain clearly marked as requiring protected input.
- LUKS metadata does not reveal an unknown passphrase. Certificate/key material,
  SSH host identity and registration identity need an explicit portability policy.
- Disk identifiers, NIC identities and routes may need mapping for another host.
  Reproducing configuration is not a disk backup or a restoration of user files.
- Exact RPM replay requires the corresponding packages to remain available.
- System Roles are not universally invertible. Some export facts, while other
  sections require explicit collection and conversion into supported role inputs.

## Decisions required before executable implementation

Initial support is RHEL 9/x86_64 and includes configuring new hosts from saved
or entirely new input. The external Vault password file has been selected.
Module policy remains open: no configuration area is inherently required on
an already-running reachable host, so optional-only modules are the current
recommendation; the earlier mandatory-core list remains an unapproved proposal.
Password
hash capture, destructive storage changes and host-identity reuse also need
explicit policies before their dependent behavior is implemented. New section
proposals do not authorize activating services or applying security baselines.

## Validation and future functional tests

This initial version contains documentation and a non-executable example only.
Static checks cover YAML parsing, catalogue accounting, links, whitespace and
the absence of actual host/secret values. No runtime tests or formal review
acceptance are claimed.

Before functional delivery, version-control a simple repeatable test against an
authorized disposable RHEL target: scan, verify encryption, change selected
owned settings, apply the saved configuration, verify results, and repeat to
check idempotency. Document protected inputs, target selection, exact commands,
expected pass/fail and preservation/cleanup boundaries once execution is implemented.
No target is selected or authorized by this document.

See [design decisions](design_decisions_history.md) for the approved scope and
the distinction between requirements and proposals.
