# RHEL-ConfigAsCode

Configure an already-running **RHEL 9/x86_64** host with Ansible and encrypted
CaC. OS installation and application stacks are outside scope. RHEL 10 is later
work; RHEL 8 remains optional funded scope.

## Status and release order

Working version: **0.1.0**. The first slice implements root hashes,
declared local accounts/public keys, wheel sudo and SSH password authentication.
All modules are optional, including for new running hosts. Selected modules still
validate their fields and require supported targets and elevated Ansible access.

Deployment patches **0.0.2** and **0.0.3** were completed, committed and
functionally tested first. This minor release adds matching bounded scanners.
Actual publication and test results/gaps are recorded in the decision history.

## Configuration and use

Public code contains generic examples. Actual host data, account names, password
hashes and generated public/private keypairs belong only as whole-file Ansible
Vault ciphertext in private RHEL-ConfigAsCode-secrets. Keep the selected external
Vault password file outside Git. The private companion is not an umbrella submodule.

The [generic template](templates/host-config.yml) has schema version 1 and two
independent maps under `rhel_cac`: `default_config` for declared defaults and
`stored_config` for scanned observations. Separate `scan_metadata` never
selects a deployment module. The generic template itself is not a deployable
plaintext configuration.

| Input | Meaning |
|---|---|
| `config_source` | Required: exactly `default_config` or `stored_config`; no default |
| `config_file` | Required controller-side path to whole-file Vault-encrypted CaC |
| `rhel_cac_overrides` | Optional map overriding the selected source's module fields |

External dictionary fields override saved fields recursively; supplied lists
replace whole lists. False is meaningful. Omitted sections preserve existing state.
Unsupported sections/fields and malformed inputs fail before configuration tasks.
This slice implements no deletion. The owner requires the unprefixed
`config_source` interface; other project variables use the `rhel_cac_` prefix.

Use an external protected inventory with the `rhel_cac_targets` group:

```sh
ansible-playbook -i <protected-inventory> deploy.yml \
  --vault-password-file <protected-vault-password-file> \
  -e config_source=default_config -e config_file=<encrypted-configuration>
```

For scanned values select `config_source=stored_config`. Each source can be empty
or define only the modules wanted. Execution order is root, accounts, sudo, SSH.

## First supported scope

| Module | Behavior |
|---|---|
| `root_password` | Apply one usable SHA-512 or yescrypt hash; no plaintext, locking or aging management |
| `accounts` | Ensure declared accounts, optional home/shell and authorized public keys; preserve unrelated keys |
| `privilege` | Add declared accounts to wheel without removing other memberships; manage one wheel ALL rule with NOPASSWD or PASSWD |
| `ssh` | Set PasswordAuthentication and KbdInteractiveAuthentication together; validate combined config and restart sshd on change |

Private client keys remain in encrypted CaC and are never copied to target
accounts. Omitted accounts and wheel members are not removed. The sudo role owns
one drop-in and preserves unrelated rules; another rule can still grant privileges.
SSH uses an early owned drop-in, preserves unrelated directives, and fails before
restart if effective settings conflict. Match policy and actual key login must
also be exercised by functional tests. Retain existing key-based management access
and console recovery for authorized disposable targets. This first slice requires
existing `UseDNS no`; it checks managed users and the management login against
the actual management connection's addresses. Other client contexts remain outside
that check's evidence; hostname-based Match policy is not generalized here.

See [module contracts](docs/modules.md) and the [System Roles catalogue](docs/system-roles.md).
Later modules, account lifecycle and arbitrary sudo/SSH grammar are not implemented.

## Scan the supported configuration

[scan.yml](scan.yml) reads the same four modules and creates one new whole-file
Vault capture per selected host. Capture files keep `default_config: {}`, place
observed values in `stored_config`, and keep source/time/completeness information
in separate `scan_metadata`. The original defaults and their private client keys
are untouched. A completed capture means complete for its selected scope.

| Scanner module | Supported observations |
|---|---|
| `root_password` | One local usable SHA-512/yescrypt root hash; locked, empty or other formats fail |
| `accounts` | Explicitly selected local accounts, current absolute home/shell and plain supported OpenSSH public-key lines |
| `privilege` | Selected local accounts' wheel membership, including primary membership, and the active owned wheel rule |
| `ssh` | Matching effective password/keyboard-interactive booleans with UseDNS no, checked for selected users and the actual management connection |

Account passwords, aging, UID/GID migration, authorized-key options/certificates,
private client keys, arbitrary sudo grammar and general SSH Match conversion
remain outside this slice. Unrepresentable or inaccessible data fails before a
capture is published. Account comments/blank key lines are ignored; authorization
options are never stripped to make a different key usable.

| Scanner input | Meaning |
|---|---|
| `rhel_cac_scan_modules` | Optional list drawn from the four module names; defaults to all four; an empty list is allowed |
| `rhel_cac_scan_accounts` | Explicit selected local account list when capturing accounts or privilege |
| `rhel_cac_scan_output_file` | Required new absolute controller-side path, distinct for every selected host; parent directory must already exist |
| `rhel_cac_scan_vault_password_file` | Required existing readable owner-only controller Vault password file, mode 0400 or 0600 |

Supply real values through protected inventory/variables. For two hosts, assign
different generic capture filenames in their encrypted host variables; real
hostnames must not become plaintext Git filenames. A one-host `--limit` may use
a single explicit output path.

```sh
ansible-playbook -i <encrypted-scan-inventory> scan.yml \
  --vault-password-file <protected-vault-password-file>
```

The scanner refuses check mode and every existing destination, including a
symlink. It creates new captures only and does not choose a history, overwrite,
retention or comparison policy. That separate design discussion remains queued.
To replay a capture, run `deploy.yml` with its encrypted `config_file` and
required `config_source=stored_config`; it does not inherit defaults/private
client keys from another file.

### Scanner implementation

Native modules collect files and ordinary data. Registered `getent -s files`
commands keep shadow/account reads out of cacheable Ansible facts; `id -nG`
includes primary as well as supplementary groups. The certified sudo/SSH roles
configure their supported policy but do not export these CaC fields, so bounded
native utility reads are used. Sudo syntax and inclusion of the owned rule are
checked; unrelated grants are not exported.

The standard Vault CLI encrypts protected stdin in a private controller
workspace, then decrypts into process memory to verify exact readback before
publication. Local pipelining is required so the captured stdin is not written
inside a temporary module wrapper; keeping remote module files is refused.
Only ciphertext is written into the capture workspace.

GNU `ln --no-target-directory` publishes the verified ciphertext with an atomic
exclusive create. The installed native file module can replace an existing
symlink even with `force: false`; this concrete gap requires the small native
command. No force option is used, so existing files/directories/symlinks are
preserved even if one appears during publication. Temporary ciphertext is
removed after success or handled failure. No new component, custom module,
general parser or dependency is introduced.

## Dependencies, AAP and verification

[Collection requirements](collections/requirements.yml) pin certified
`redhat.rhel_system_roles:1.120.5` and `ansible.posix:2.2.2`. Existing certification
records and relevant artifact files were verified for development. This does not
establish equivalence with newer catalogue version 2.4.2. Minimum combined core
is 2.16. Use the configured approved Automation Hub; obtain approval before
installing missing dependencies. Do not vendor collections.

Root/accounts use native Ansible modules: the public System Roles catalogue
does not provide a dedicated general local-account role. Public keys use certified
POSIX content; sudo/SSH use certified System Roles directly. No custom modules,
plugins or service framework are needed. Keep fact caching off; job output is
protected with `no_log`.

Local contract tests use real encrypted fixtures and Ansible without host changes:

```sh
python3.12 -m unittest discover -s tests -v
ansible-playbook --syntax-check -i <protected-inventory> deploy.yml
ansible-lint --offline --profile production --strict
```

Run `tests/verify.yml` after deployment with the same protected inventory,
Vault input, `config_source` and `config_file`. It checks actual selected host
settings and fails nonzero on mismatch. Repeat deployment and require no
unintended changes. Limit testing and cleanup to authorized disposable resources.
Syntax and local fixtures alone do not prove deployed behavior.

## Automated functional test

The repeatable [functional runner](tests/run_functional.py) exercises the existing
deployment and verifier playbooks, then fresh client-key authentication. Run it
only against the two explicitly authorized disposable targets:

```sh
python3.12 tests/run_functional.py \
  --inventory <encrypted-test-inventory> \
  --config <encrypted-default-configuration> \
  --vault-password-file <protected-vault-password-file> \
  --collections <existing-installed-collection-roots> \
  --known-hosts <protected-file-with-explicitly-enrolled-guest-host-keys>
```

Prerequisites are the existing Python 3.12, Ansible, PyYAML, SSH client,
UTF-8 C locale and pinned collections. Password bootstrap additionally uses the existing `sshpass` utility;
the runner installs nothing. The whole-file Vault inventory must list exactly two
distinct hosts directly in `rhel_cac_targets`, without child groups. Each host
needs `ansible_host`, `ansible_user`, `rhel_cac_test_guest_uuid` and
`rhel_cac_test_baseline_snapshot`. Confirm those recorded identities and rollback
baselines refer to the intended guests before launching; the runner requires the
fields but does not independently interrogate the hypervisor.

The default configuration must contain the two declared accounts and their
generated private keys. Both targets use the same declared management account.
The runner explicitly tests `default_config`; `stored_config` selection remains
covered by local loader tests until its later scanner workflow is implemented.
Supply a known-hosts file from the explicitly authorized host-key enrollment.
Enrollment records first-use trust; it does not imply independent hypervisor
attestation of the keys. Every test SSH
connection uses strict host-key checking; the runner neither accepts new host
keys nor replaces existing pins. Transport or host-key failures stop the test.

On a fresh baseline, the generated management key can be absent: the runner tries
it first, then prompts through `getpass` for the existing test SSH/sudo password
only after authentication refusal. That existing bootstrap password must apply
to both targets. A repeat on hardened targets uses the deployed key and
passwordless sudo without forcing a password login. Password values are never
command arguments or log output.

The workflow applies, verifies, applies again and verifies again. Both verifier
runs and the repeated apply must report zero changes. It then makes four fresh
key-only connections, one per declared account on each guest, disables SSH agent
and connection reuse, and verifies passwordless sudo returns UID zero. A mismatch,
failed command or unexpected repeat change gives exit status 1 and a final JSON
`functional_result: FAIL`; success gives exit status 0 and `PASS`.

Raw stage output and the summary are retained only as Vault ciphertext in an
owner-private evidence directory named in the final JSON. Console summaries show
numeric totals rather than inventory/account names. Runtime private keys and
encrypted launch variables are created under a mode-700 temporary directory;
individual files use mode 600. Cleanup runs on normal success and handled failure,
and the final result reports whether the temporary directory was removed. A hard
process kill or host failure can prevent cleanup; inspect protected temporary
data before another run. The runner creates no snapshots, rolls nothing back,
deletes no guests and changes no unrelated resources. Restore a baseline only
through a separately authorized operation.

This small controller-side helper uses the standard Ansible and OpenSSH tools
plus Ansible's Vault library. Its concrete gap is orchestrating the existing
playbooks, checking their machine-detectable recaps, temporarily materializing
encrypted client credentials and proving fresh SSH logins with cleanup. Native
modules and certified roles still perform the actual host configuration. It adds
no custom Ansible module/plugin, service or testing framework.

The earlier command-line run against published deployment **0.0.2 / `b206bd3`**
passed on both authorized guests: first apply changed six tasks per guest,
46 verifier checks passed per guest, repeat apply changed zero tasks, repeat
verification passed, and all four fresh key/sudo logins passed. That evidence came
from the preceding one-off driver. The version-controlled runner in patch
**0.0.3** also passed against the hardened guests: both applies reported zero
changes, both verifier runs passed all 46 checks per guest, and all four fresh
key/sudo logins passed using the explicitly enrolled host keys. Its protected
runtime key files were removed. This is command-line functional evidence;
AAP end-to-end acceptance remains future work under the job-template hold.

To include the scanner and stored-configuration round trip, add
`--scan-output-directory <private-capture-directory>` to the functional command.
The two generic capture filenames in that directory must not exist. The runner
uses a protected temporary inventory to scan, checks the encrypted capture
structure/scope, replays each host's `stored_config`, verifies it, then verifies
the original defaults again. It checks that default ciphertext stayed identical
and ends with the same fresh key/sudo checks. The generated captures are kept;
the runner does not delete or overwrite prior captures.

The **0.1.0** command-line round trip passed on both authorized guests. It
created two complete encrypted captures, replayed `stored_config`, passed the
captured-state and original-default verifiers, and finished all four fresh
key-only/passwordless-sudo checks. The scan/replay phase completed 506 successful
tasks with eight changes, all delegated controller ciphertext-publication work;
no guest configuration task changed. Original default ciphertext was identical.
Eight real Ansible capture fixtures, strict offline production lint and all five
entry-point syntax checks also passed. This does not establish AAP acceptance or
test snapshot restoration.

AAP must use an appropriate EE, Machine and Vault credentials, and materialize
encrypted input inside the job's own protected workspace using approved repository
access. Do not borrow another project's checkout or embed workstation paths.
This repo does not create AAP objects or launch jobs. Normal AAP end-to-end
execution remains required before platform acceptance can be claimed.

[TLDR](TLDR.md) · [Decision history](design_decisions_history.md)
