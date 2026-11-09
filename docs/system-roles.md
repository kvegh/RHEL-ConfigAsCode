# RHEL System Roles catalogue and scan coverage

The [Red Hat certified catalogue](https://catalog.redhat.com/en/software/collection/redhat/rhel_system_roles)
currently identifies `redhat.rhel_system_roles` version **2.4.2** and 46 role
directories. This is not evidence of 46 independent public configuration areas.
The public-role candidate list below has 36 entries; the remaining directories
include internal helper roles. Exact certified artifact contents, dependency
requirements and release support must be verified before pinning a runtime.

This is a catalogue for design, not a requirements manifest or installation.
The [Red Hat support matrix](https://access.redhat.com/articles/3050101) and
[RHEL 9 System Roles guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/automating_system_administration_by_using_rhel_system_roles/index)
are primary references. The support overview is dated 2025 and omits newer
entries; [upstream documentation](https://linux-system-roles.github.io/) alone
does not establish downstream certification or RHEL release compatibility.

| Configuration area | Public role candidates |
|---|---|
| Identity and access | `ad_integration`, `sudo`, `ssh`, `sshd` |
| Host security | `selinux`, `crypto_policies`, `certificate`, `aide`, `auditd`, `fapolicyd`, `tlog` |
| Networking | `network`, `firewall`, `vpn` |
| Storage/encryption | `storage`, `nbde_client`, `nbde_server`, `snapshot` |
| Boot/kernel | `bootloader`, `kernel_settings`, `kdump` |
| Time | `timesync` |
| OS services/observability | `systemd`, `journald`, `logging`, `metrics`, `cockpit`, `rhc` |
| Clustered OS facilities | `ha_cluster`, `gfs2` |
| Attestation | `keylime_server`, `trustee_client`, `trustee_server` |
| Outside the OS-only baseline | `podman`, `postfix`, `postgresql` |

Including a role in this catalogue does not enable it or install its workload.
OS-level use of `metrics` must not silently add Grafana or other application
components. Cluster, attestation and NBDE facilities are represented only when
needed and supported by the selected release. SAP and Microsoft SQL Server
content is outside this project; additional upstream names such as `hpc`,
`pam_pwd` and `mssql` are not established as this certified collection's public roles.

Root/account administration, generic package policy and arbitrary OS files do
not have dedicated roles in this list. Suitable `ansible.builtin` modules remain
appropriate for those capabilities; document concrete gaps before custom helpers.

## Reusing native capture capabilities

Do not run every configuration role as a scanner. Verify its pinned implementation
and invocation is read-only first.

- `bootloader_gather_facts` can populate `bootloader_facts`.
- `ha_cluster_export_configuration` can populate `ha_cluster_facts`, but a
  read-only export requires both `ha_cluster_cluster_present: null` and
  `ha_cluster_qnetd: null`. Defaults can reconfigure a cluster before exporting.
  Export omits passwords and key/certificate file content.
- The [firewall role interface](https://github.com/linux-system-roles/firewall/blob/main/README.md)
  documents fact gathering and `firewall_config`; downstream version and
  fact-only behavior must be verified before use.

Other sections can start with setup, package, service and getent facts, then
collect persistent subsystem settings where those facts are insufficient.
There is no verified universal inverse exporter. A complete replayable capture
must not be claimed from ordinary facts alone.
