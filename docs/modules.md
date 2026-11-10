# Module scope

All modules are optional for new and existing running RHEL hosts. The owner
confirmed this; the earlier mandatory-core proposal is superseded. Omit a module
to preserve it. Validate selected fields before host changes. External dictionary
fields override saved fields recursively; external lists replace saved lists.

## First deployment slice

The owner approved root hash only, then users/keys, wheel sudo and SSH. Keep
this slice bounded: no general account lifecycle, full sudo grammar or arbitrary
SSH-policy framework.

| Section | Fields |
|---|---|
| `root_password` | Required `password_hash`: usable SHA-512 or yescrypt hash without a lock marker |
| `accounts` | List of `name`, optional absolute `home`/`shell`, required nonempty `ssh_public_keys`; optional `ssh_private_key` stays in encrypted CaC only |
| `privilege` | `wheel_members` list and `wheel_nopasswd` boolean |
| `ssh` | `password_authentication` boolean; controls both direct and keyboard-interactive passwords |

Account entries add public keys and preserve unrelated keys. They do not deploy
private keys, delete accounts, or manage user passwords/aging. Wheel membership
is additive. A false NOPASSWD value sets PASSWD on the owned rule but does not
remove independent privileges granted by somebody else's rules.

The sudo System Role owns `/etc/sudoers.d/90-rhel-cac`; SSH owns
`/etc/ssh/sshd_config.d/00-rhel-cac.conf`. Validate combined configuration and
effective settings; do not replace unrelated policy. Restart SSH after validation
when changes notify its handler.

Required `config_source` chooses `default_config` or `stored_config`, both maps
under `rhel_cac` in the selected encrypted `config_file`. Observations do not
overwrite defaults. Empty maps select no modules. Missing protected inputs must
remain omitted or fail validation, never turn into invented passwords.

## Later discussion order

Original order: root password; users/homes/groups/passwords; sudo; packages;
sshd; firewall; kernel parameters; mounts/targets/options; SELinux; network/all
interfaces; storage/mirrors/LVM; subscription; repositories; Insights. The owner
subsequently explicitly selected root/users/sudo/SSH as the first slice.

Logging, authentication/AD, OS services and certificates were also accepted as
future areas. Account for every public RHEL System Role without activating every
subsystem. Application stacks remain excluded.

Accepted fuller DNF scope covers repository definitions/access/enabled state,
GPG/TLS checks, release locks/module streams, exclusions/version locks, and
dependency behavior such as weak dependencies. Keep it separate from per-package
exact/present/latest. Its detailed contract is future work.

## Capture and release sequence

Finish and commit deployment playbooks as patch releases before writing scanners.
Then add corresponding scanners as minor releases. Capture only implemented
sections and keep observed values separate from defaults and scan metadata.

Privileged scans can read shadow hashes, not original plaintext passwords.
Authorized public keys cannot recover private client keys; scanning private keys
is outside this slice. Missing/inaccessible reads must not imply removal or unlock.
Arbitrary custom sudo/SSH constructs remain outside this initial bounded scope.

Scan-version retention and comparison is a separate owner-requested discussion
tracked in Beads; no retention policy or comparison component is selected.


## Initial scanner contract

The minor scanner release captures exactly the four implemented modules.
Explicitly selected local accounts supply observed homes/shells and plain public
authorization keys; private client keys remain only in original encrypted
defaults. Wheel membership includes primary groups, and sudo capture is limited
to the active owned wheel ALL rule with explicit PASSWD/NOPASSWD.

Root capture requires a representable usable hash. SSH capture requires both
password methods to agree and selected-user/management-context checks to pass.
Unsupported data fails before publication. Each new per-host encrypted file has
empty defaults, flat observed `stored_config` and separate completeness/source
metadata. Existing output files are preserved; history/comparison remains a
separate undecided capability. See the [scanner inputs and implementation](../README.md#scan-the-supported-configuration).
