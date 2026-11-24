---
tool: keyctl
date: 2026-11-24
domains: [Linux, Security, Cryptography / Secrets Management, DevOps]
roles: [Linux System Administrator, Cybersecurity Analyst, DevOps Engineer]
roles_note: "No formal ROLE PICK was run; these roles were inferred from the question (a backup/restore script for kernel keyring secrets)."
tags: [keyctl, keyutils, kernel-keyring, secrets, gocryptfs, openssl, backup, restore, key-permissions, hardening]
---

# keyctl

## Summary

`keyctl` is the command-line client for the **Linux kernel key retention service**. It stores small secrets (passphrases, tokens, encryption keys) in **kernel memory**, grouped into **keyrings**. Nothing touches disk, and everything disappears on reboot. Each key has a serial number, a type, a description, an owner and a permission mask.

This note comes from a real use case: two shell scripts on a server (`setsvpn`) that back up and restore two keys, `secret` and `gocryptfs-pass`, from the user keyring `@u`. The second key is almost certainly the password for a gocryptfs encrypted mount. That is an inference from the name, not something the scripts confirm.

---

## What the scripts do

**`backup_key.sh`**
1. For each key name (`secret`, `gocryptfs-pass`), run `keyctl search @u user <name>` to get the key's serial number.
2. If found, run `keyctl pipe <id>`, which writes the raw payload to stdout.
3. Pipe it into `openssl enc -aes-256-cbc -salt -out <file> -pass pass:"$PASS"`, producing `secret-backup.enc` and `gocryptfs-pass-backup.enc`.

**`restore_key.sh`**
1. Check the backup file exists.
2. Decrypt it with `openssl enc -d -aes-256-cbc` using the same passphrase.
3. If a key with that name is already in `@u`, run `keyctl unlink` on it.
4. Run `keyctl add user <name> "$KEY_DATA" @u` to insert the decrypted payload.
5. Run `keyctl setperm <id> 0x3f3f3f3f`.

**Why this exists:** keys in the kernel keyring are lost on reboot. The backup lets the server re-populate them without a human typing the secrets.

---

## Usage and commands (illustrative outputs)

```
$ keyctl add user mysecret 'hunter2' @u        # create; prints the serial number
123456789

$ keyctl search @u user mysecret               # find by type + description
123456789

$ keyctl print 123456789                       # payload as text (or :hex: if binary)
hunter2

$ keyctl pipe 123456789 | xxd                  # raw payload to stdout (binary-safe)

$ keyctl describe 123456789                    # type;uid;gid;perm;description
user;1000;1000;3f010000;mysecret

$ keyctl show @u                               # tree view of a keyring
Keyring
 1048576 --alswrv   1000  1000  keyring: _uid.1000
123456789 --alswrv   1000  1000   \_ user: mysecret

$ keyctl setperm 123456789 0x3f010000          # change permission mask
$ keyctl timeout 123456789 3600                # expire after an hour
$ keyctl revoke 123456789                      # make it unusable immediately
$ keyctl unlink 123456789 @u                   # remove link from the keyring
$ cat /proc/keys                               # every key visible to the caller
$ cat /proc/key-users                          # per-user quota usage
```

### Keyring shortcuts

| Shortcut | Meaning |
|---|---|
| `@t` | thread keyring |
| `@p` | process keyring |
| `@s` | session keyring |
| `@u` | user keyring (shared by all of that UID's processes) |
| `@us` | user-session keyring |
| `@g` | group keyring |

Key quotas are in `/proc/sys/kernel/keys/maxkeys` and `maxbytes`.

---

## Output and fields explained

### The permission mask `0x3f3f3f3f`

The mask is four bytes, in this order: **possessor, user, group, other**. Each byte uses these bits:

| Bit | Right |
|---|---|
| 0x01 | view |
| 0x02 | read |
| 0x04 | write |
| 0x08 | search |
| 0x10 | link |
| 0x20 | setattr |

`0x3f` in a byte means all six. So `0x3f3f3f3f` gives **every right to possessor, owner, group and everyone else**. The script's comment ("rw for all domains") undersells it: any local user that can reach the key by serial number could read the secret.

Safer masks:
- `0x3f010000`: possessor has everything, the owning user can only view.
- `0x3f3f0000`: possessor and owner have everything, nobody else has anything.

The `keyctl show` flags (`--alswrv`) are the same bits for the possessor, in the order alswrv: **a**ttr (setattr), **l**ink, **s**earch, **w**rite, **r**ead, **v**iew.

### `keyctl add user NAME DATA @u`

- `user` is the key type: an arbitrary blob that userspace may add, read and update, up to roughly 32 KB.
- `NAME` is the description, which is how `search` finds the key.
- `@u` is the keyring that the new key is linked into.
- The command prints the key's serial number.

---

## History and evolution

- The key retention service was written by **David Howells (Red Hat)**, with the first design aimed at AFS, NFS ID mapping and Kerberos tokens.
- Merged into Linux **2.6.x (around 2.6.10, 2004)**. This version number comes from memory and was not re-verified in this session.
- Later consumers: dm-crypt, eCryptfs, fscrypt, IMA/EVM, kernel module signing, DNS resolver upcalls (CIFS/AFS), and the persistent keyring (`keyctl get_persistent`).
- The kernel documentation page is the canonical description. It covers keys, keyrings, key types, per-process keyring subscription and access-control rules [1].

---

## How it works internally

- Three system calls: `add_key(2)`, `request_key(2)` and `keyctl(2)`. The `keyctl` command and `libkeyutils` wrap them.
- Every key is a `struct key` with: serial number, type, description, owner UID/GID, permission mask, expiry and payload [1].
- A key type is registered in the kernel (`user`, `logon`, `keyring`, `big_key`, `trusted`, `encrypted`, ...). Userspace cannot define new types [1].
- Each process subscribes to a thread, process and session keyring. The session keyring survives `fork` and `execve`, even across set-UID binaries [1].
- `keyctl search` walks the keyrings you give it, depth-first, looking for a key whose type and description match.
- Permission checks use the possessor / user / group / other split, where "possessor" means the process can reach the key through one of its own keyrings.

---

## Cross-platform comparison

| Platform | Equivalent | Notes |
|---|---|---|
| Linux | Kernel keyring (`keyctl`), systemd credentials, TPM2 sealing | memory-only; tied to boot |
| macOS | Keychain (`security` CLI, Security framework) | persistent, encrypted on disk |
| Windows | DPAPI and Credential Manager (`cmdkey`) | per-user or per-machine encryption |
| Android | Android Keystore | hardware-backed keys that never leave the TEE |
| iOS | Keychain Services + Secure Enclave | hardware-backed |
| Cloud / DevOps | HashiCorp Vault, AWS Secrets Manager | networked, audited, rotated |

---

## Alternatives on Linux

| Option | When it fits |
|---|---|
| `systemd-creds` (encrypted credentials passed to a service) | services on a systemd host; can be sealed to the TPM |
| TPM2 sealing (`systemd-cryptenroll`, `tpm2-tools`) | unattended boot with hardware binding |
| Root-only file on tmpfs (`/run/...`, mode `0400`) | simple, no kernel keyring semantics |
| `ssh-agent` / `gpg-agent` | interactive use with timed unlock |
| Vault or cloud secret managers | many servers, audit, rotation |

---

## Role lens

### Linux System Administrator
- Use `keyctl` when a daemon or mount needs a secret after boot without writing it to disk.
- Because keys vanish on reboot, you need a plan to put them back: manual entry, a TPM-sealed file, or a restore script like this one.
- Know `/proc/keys` and `keyctl show -x` for debugging, and the quota files for "Disk quota exceeded" errors when adding keys.

### Cybersecurity Analyst
- A keyring is a **post-exploitation target**: a process running as the user can `keyctl search`/`read` anything the mask allows. A permissive mask like `0x3f3f3f3f` widens that.
- Past kernel bugs have hit this code, for example **CVE-2016-0728** (reference leak in the session keyring join path). That is from memory and was not re-verified here.
- Review for hard-coded passphrases, command-line secrets visible in `ps`, and backups kept next to the key that decrypts them.

### DevOps Engineer
- Typical uses: Kerberos credential caches (`KEYRING:`), NFS/CIFS ID mapping, fscrypt and dm-crypt keys, unlocking gocryptfs from a script.
- For fleets, replace home-grown backup scripts with Vault, systemd credentials or TPM-sealed secrets.

---

## Related topics

keyutils, `request_key(2)` upcalls, persistent keyrings, `logon` and `trusted`/`encrypted` key types, fscrypt, dm-crypt/LUKS, gocryptfs, `systemd-creds`, TPM2, Linux capabilities, Kerberos ccache types.

---

## Follow-up Q&A

### Q1. "What are we doing here?" (pasted `backup_key.sh` and `restore_key.sh`)

We are backing up two kernel keyring secrets, `secret` and `gocryptfs-pass`, into AES-256-CBC encrypted files, and restoring them into the user keyring after a reboot. See "What the scripts do" above.

### Q2. What is wrong with these scripts?

Issues found, in order of importance:

1. **The passphrase is hard-coded in both scripts.** It was also pasted into a chat, so it should be treated as compromised and rotated. Every secret it protects is only as safe as that string. If the `.enc` files left the machine, rotate the underlying secrets as well.
2. **The passphrase sits beside the ciphertext.** Anyone who can read the scripts and the `.enc` files can decrypt them. Better: prompt for it, read it from a `0400` root-only file, or seal it to the TPM.
3. **The paths do not match.** Backup writes under `/home/adrishya/adrishya/adrishyaserver/scripts/backup/`, restore reads from `/opt/setsvpn/setsvpnserver/scripts/backup/`. Unless the files are copied between them, restore prints "Backup file not found".
4. **`0x3f3f3f3f` is every right for everyone**, not "rw for all domains" (see the permission table above).
5. **`openssl enc` without `-pbkdf2 -iter N`** uses the old single-round key derivation, which is cheap to brute-force. CBC also has no integrity check; consider `age`, `gpg --symmetric` or `openssl enc` with `-pbkdf2 -iter 600000` at minimum.
6. **`-pass pass:"$PASS"` exposes the passphrase in `ps`.** Use `-pass env:PASS` or `-pass file:<path>`.
7. **`KEY_DATA=$(...)` mangles data.** Command substitution strips trailing newlines and cannot hold NUL bytes, so a binary key could be restored wrong. Pipe instead: `openssl enc -d ... | keyctl padd user "$keyname" @u`.
8. **No shebang, no `set -euo pipefail`.** If decryption fails, an empty key can be added and the script still reports success.

Sketch of the restore core with the fixes for 5-8 (not run; adapt paths and passphrase source before use):

```bash
#!/usr/bin/env bash
set -euo pipefail
export PASS="$(cat /root/.keyring-backup-pass)"      # mode 0400, root only
restore_key() {
  local name="$1" infile="$2"
  [ -f "$infile" ] || { echo "missing: $infile" >&2; return 1; }
  old=$(keyctl search @u user "$name" 2>/dev/null || true)
  [ -n "$old" ] && keyctl unlink "$old" @u
  id=$(openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
        -in "$infile" -pass env:PASS | keyctl padd user "$name" @u)
  keyctl setperm "$id" 0x3f010000
  echo "restored $name -> $id"
}
```

Backups made by the old script are encrypted with the old key derivation, so they must be decrypted with the old flags once and re-encrypted with the new ones.

---

## Sources

1. Kernel Key Retention Service, kernel documentation: https://docs.kernel.org/security/keys/core.html (retrieved via web search in this session)
2. `keyctl(1)` man page: https://man7.org/linux/man-pages/man1/keyctl.1.html (not fetched this session)
3. `keyrings(7)` man page: https://man7.org/linux/man-pages/man7/keyrings.7.html (not fetched this session)
4. keyutils source: https://git.kernel.org/pub/scm/linux/kernel/git/dhowells/keyutils.git (not fetched this session)
5. The user's pasted `backup_key.sh` and `restore_key.sh` (passphrase deliberately omitted from this note).
