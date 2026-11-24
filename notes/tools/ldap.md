---
tool: LDAP
date: 2026-11-24
domains: [Identity & Access Management, Networking/Protocols, Linux/Windows SysAdmin, Cybersecurity, DevOps]
roles: [Systems Administrator, IAM Engineer, Penetration Tester / Red Teamer, SOC / Blue Team Analyst, Network Engineer, DevOps / Platform Engineer, Backend Developer, Protocol / Standards Researcher]
tags: [ldap, openldap, slapd, ldapsearch, ldapmodify, ldif, active-directory, directory-services, sssd, nss, pam, lmdb, cn-config, acl, ldaps, starttls, sasl, kerberos, ldap-signing, channel-binding, vpn-authentication]
---

# LDAP (Lightweight Directory Access Protocol)

## Summary

LDAP is an open IETF protocol (LDAPv3, RFC 4510–4519) for reading and writing a **directory**: a tree of entries describing users, groups, machines and permissions. Servers include OpenLDAP (`slapd`), Microsoft Active Directory, 389 Directory Server / FreeIPA and Samba AD DC. Clients include the OpenLDAP command-line tools (`ldapsearch`, `ldapmodify`, …), SSSD/nslcd for Linux logins, and countless applications (VPNs, mail, CI, SSO) through libraries such as `libldap`, `python-ldap`, `ldap3` and JNDI.

- **Problem it solves:** one standard network protocol for looking up and changing identity records, so every app, server and device can share one directory instead of keeping its own user list.
- **Scope of these notes:** the protocol, plus the OpenLDAP client suite and the `slapd` server as the hands-on part, plus a full real-world investigation of an OpenLDAP server backing a VPN product (anonymised).
- **Mental model:** slapd keeps a **tree of entries** (DN = path, attributes = data, objectClass + schema = rules) in one memory-mapped **LMDB** file and keeps its own **configuration as LDAP entries** (`cn=config`). Clients connect over **TLS (ldaps)** or the **local socket (ldapi)** and send BER-encoded operations: **Bind** to prove identity, **Search** to find, **Add/Modify/Delete** to change. **ACLs** decide what each identity may do.

---

## Install and availability

| Platform | Client tools | Server |
|---|---|---|
| Debian/Ubuntu | `sudo apt install ldap-utils` | `sudo apt install slapd` |
| RHEL/Fedora | `sudo dnf install openldap-clients` | `389-ds-base` (Red Hat's server) or `openldap-servers` |
| Arch | `pacman -S openldap` (client and server) | same |
| macOS | `ldapsearch` ships built in | (old Open Directory server was in macOS Server, discontinued) |
| Windows | `ldp.exe`, `dsquery`, PowerShell `Get-ADUser` (RSAT), `adfind` | Active Directory Domain Services, AD LDS |
| Containers | `bitnami/openldap`, `osixia/openldap` (older) | same |

On RHEL, `openldap-clients` contains the command-line tools for viewing and modifying directories. The OpenLDAP suite includes `ldapadd`, `ldapcompare`, `ldapdelete`, `ldapexop`, `ldapmodify`, `ldapmodrdn`, `ldappasswd`, `ldapsearch`, `ldapurl`, `ldapwhoami` [5].

**Versions (Nov 2026):** OpenLDAP 2.6 is the LTS line. 2.6.14 (2026-08-06) added libldap support for the OpenSSL 4.0 series [2]; 2.6.13 (2026-03-09) fixed a libldap heap overflow [3]. Distros lag: Ubuntu 24.04 ships 2.6.10 [4], and the Ubuntu 26.04 box studied below runs `2.6.10+dfsg-1ubuntu5`.

---

## Core concepts

```
dc=example,dc=com                     ← base / suffix (root of the DIT, Directory Information Tree)
├── ou=People
│   └── uid=jsmith                    ← entry; DN = uid=jsmith,ou=People,dc=example,dc=com
│         objectClass: inetOrgPerson  ← schema decides which attributes are allowed
│         cn: John Smith
│         mail: jsmith@example.com
└── ou=Groups
    └── cn=devs  (member: uid=jsmith,ou=People,...)
```

- **DN (Distinguished Name):** full unique path of an entry, read right to left (root → leaf). **RDN:** the leftmost part (`uid=jsmith`), the entry's name inside its parent.
- **`dc=` (domainComponent):** naming the root after a DNS domain (`example.com` → `dc=example,dc=com`), RFC 2247 convention. **`ou=`** = organizationalUnit, a container.
- **Entry:** set of attributes with one or more values. **objectClass** decides required (MUST) and allowed (MAY) attributes; rules live in the **schema**.
  - `inetOrgPerson` inherits `top → person (MUST cn, sn; MAY userPassword, telephoneNumber…) → organizationalPerson → inetOrgPerson (MAY mail, uid, displayName, mobile…)`.
  - Ubuntu loads `core`, `cosine`, `nis`, `inetorgperson` by default (`/etc/ldap/schema/`).
- **Bind** = authenticate: anonymous, simple (DN + password), or SASL (GSSAPI/Kerberos, EXTERNAL, …).
- **Scope:** `base` (this entry), `one` (direct children), `sub` (whole subtree, default).
- **Filter:** prefix notation, e.g. `(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))`.
- **Ports:** 389 (LDAP, or StartTLS upgraded in place), 636 (LDAPS, TLS from the first byte), 3268/3269 (AD Global Catalog), `ldapi:///` (local Unix socket).
- **LDIF:** LDAP Data Interchange Format, the plain-text format for entries and changes.

---

## Usage and commands

### The 10 most useful commands (with sample output)

**1. Read the RootDSE (no authentication). Always first.**
```bash
ldapsearch -x -H ldap://dc01.corp.local -s base -b "" "(objectClass=*)" namingContexts supportedSASLMechanisms supportedLDAPVersion
```
```
dn:
namingContexts: DC=corp,DC=local
namingContexts: CN=Configuration,DC=corp,DC=local
supportedLDAPVersion: 3
supportedSASLMechanisms: GSSAPI
supportedSASLMechanisms: GSS-SPNEGO
```
`namingContexts` = which base DN to use; `supportedSASLMechanisms` = which bind methods work. The RootDSE is anonymously readable even on AD.

**2. Simple bind + search**
```bash
ldapsearch -x -H ldap://ldap.example.com -D "cn=admin,dc=example,dc=com" -W \
  -b "ou=People,dc=example,dc=com" -LLL "(uid=jsmith)" cn mail memberOf
```
```
dn: uid=jsmith,ou=People,dc=example,dc=com
cn: John Smith
mail: jsmith@example.com
```
`-x` simple bind (without it the tools try SASL); `-W` prompt for password (never `-w pass`: visible in `ps` and history); `-LLL` clean LDIF. Matching entries come back in LDIF format [6].

**3. Who am I bound as?**
```bash
ldapwhoami -x -H ldap://ldap.example.com -D "uid=jsmith,ou=People,dc=example,dc=com" -W
# dn:uid=jsmith,ou=People,dc=example,dc=com
```

**4. StartTLS vs LDAPS**
```bash
ldapsearch -x -ZZ -H ldap://ldap.example.com ...   # StartTLS on 389, fail if TLS can't start
ldapsearch -x    -H ldaps://ldap.example.com ...   # TLS on 636 from the first byte
```
`-Z` tries StartTLS but continues in cleartext on failure; `-ZZ` refuses.

**5. Add an entry from LDIF**
```bash
cat > user.ldif <<'EOF'
dn: uid=asha,ou=People,dc=example,dc=com
objectClass: inetOrgPerson
uid: asha
cn: Asha Rao
sn: Rao
mail: asha@example.com
EOF
ldapadd -x -D "cn=admin,dc=example,dc=com" -W -f user.ldif
# adding new entry "uid=asha,ou=People,dc=example,dc=com"
```

**6. Modify (replace / add / delete values)**
```
dn: uid=asha,ou=People,dc=example,dc=com
changetype: modify
replace: mail
mail: asha.rao@example.com
-
add: telephoneNumber
telephoneNumber: +91 98xxxxxx
```
`ldapmodify -x -D ... -W -f mod.ldif`. A lone `-` separates changes in one modify operation.

**7. Delete and rename**
```bash
ldapdelete -x -D "cn=admin,..." -W "uid=asha,ou=People,dc=example,dc=com"
ldapmodrdn -x -D "cn=admin,..." -W "uid=asha,ou=People,dc=example,dc=com" "uid=arao"
```

**8. Change a password (Password Modify extended operation, RFC 3062)**
```bash
ldappasswd -x -D "uid=asha,ou=People,dc=example,dc=com" -W -S
```
`ldappasswd` and `ldapwhoami` do not work against Active Directory [1]; AD changes passwords by writing `unicodePwd` over an encrypted connection.

**9. Local admin of OpenLDAP's config over the Unix socket (as root)**
```bash
sudo ldapsearch -Y EXTERNAL -H ldapi:/// -b "cn=config" "(olcDatabase=*)" olcSuffix olcRootDN
```
SASL EXTERNAL: the kernel passes your UID/GID over the socket, no password needed.

**10. Large result sets: paging**
```bash
ldapsearch ... -E pr=500/noprompt "(objectClass=user)" sAMAccountName
```
AD caps searches at `MaxPageSize` (1000 by default); without paging you get `Size limit exceeded (4)`.

### Realistic task: hook a Linux server to AD and verify it

```bash
dig +short _ldap._tcp.corp.local SRV                         # 1. discover DCs via DNS
# 2. RootDSE (command 1): base DN and SASL mechanisms
ldapsearch -x -H ldaps://dc01.corp.local -D "svc-ldap@corp.local" -W \
  -b "DC=corp,DC=local" -LLL "(sAMAccountName=jsmith)" memberOf userAccountControl   # 3. test bind over LDAPS
# 4. "8 Strong(er) authentication required" on plain 389 = DC enforces signing → LDAPS or SASL/GSSAPI
kinit jsmith@CORP.LOCAL && ldapsearch -Y GSSAPI -H ldap://dc01.corp.local -b "DC=corp,DC=local" "(sAMAccountName=jsmith)"
# 5. realm join corp.local (sssd), then: id jsmith@corp.local ; getent group devs
```

### Common mistakes and gotchas

- **Windows Server 2025 changed defaults:** all new AD deployments require LDAP signing by default via "Domain controller: LDAP server signing requirements enforcement"; channel binding is "When supported" [7]. A policy left "Not Configured" translates to "Require Signing" [8]. Appliances doing simple binds on plain 389 break (e.g. FortiGate connections stop working after migration [9]); the fix is LDAPS.
- **Accidental anonymous bind:** a simple bind with a DN and an empty password succeeds as an "unauthenticated bind" (RFC 4513 §5.1.2). Apps that only check "bind returned 0" can be fooled; reject empty passwords.
- **TLS trust:** the client checks the server cert against `TLS_CACERT` in `/etc/ldap/ldap.conf` (Debian) or `/etc/openldap/ldap.conf` (RHEL). `LDAPTLS_REQCERT=never` hides MITM problems.
- **Base DN typos** → result 32. **Wrong attribute names per platform:** AD `sAMAccountName`/`memberOf`; OpenLDAP `uid`/`memberUid`/`member` (`memberOf` needs an overlay).
- **Permissions:** reads are often open to any authenticated user (AD by design: one stolen low-privilege account = full AD recon). Writes need ACL grants; `cn=config` changes need root over `ldapi`.

---

## Command cheat sheet: which command and flag, when

Placeholders: `BASE = dc=example,dc=com`, `USERS = ou=Vpnuser,dc=example,dc=com`, `ADMIN = cn=admin,dc=example,dc=com`, `CA = /etc/ssl/certs/ca_ldap.crt`, server `10.0.0.85`.

### Flags used 90% of the time

**Where and how to connect**

| Flag | Meaning | When |
|---|---|---|
| `-H ldapi:///` | local Unix socket | on the server as root |
| `-H ldaps://10.0.0.85` | TLS on 636 | over the network |
| `-H ldap://host -ZZ` | 389 + mandatory StartTLS | servers offering 389 + StartTLS (common on AD) |
| `-Z` | try StartTLS, continue without | rarely; prefer `-ZZ` |

**Who you bind as**

| Flags | Identity | When |
|---|---|---|
| `-Y EXTERNAL -H ldapi:///` (sudo) | root via the OS | read/change **config**; read data (not passwords) |
| `-x -D "ADMIN" -W` | directory admin (rootDN) | **write data**: add/modify/delete users, reset passwords |
| `-x -D "cn=user,USERS" -W` | normal user | test a user's password; see what they see |
| `-x` alone | anonymous | see what an unauthenticated visitor can read |

`-W` prompts; `-w pass` leaks to history/`ps`; `-y file` reads the password from a file (scripts).

Gotcha learned on the real server: **root via `-Y EXTERNAL` could read data but not write it**, because the data database's ACL `{2} to * by * read` matched first and stopped; root's `manage` right existed only on `cn=config`. Data changes need `-D cn=admin,...`.

**What to search**

| Flag | Meaning |
|---|---|
| `-b "BASE"` | where to start |
| `-s base` / `one` / `sub` | entry only / direct children / whole subtree (default) |
| `'(filter)'` | which entries; always single-quote |
| `attr1 attr2` | only these attributes |
| `'*'` / `'+'` / `1.1` | all user attrs / operational attrs (createTimestamp, modifiersName, entryUUID…) / DN only |

**Output control**

| Flag | Effect |
|---|---|
| `-LLL` | clean LDIF |
| `-o ldif-wrap=no` | no 76-char wrapping (good for grep) |
| `-z 10` | max 10 entries |
| `-E pr=500/noprompt` | paged results |
| `-v` / `-d 1` | verbose / protocol debug |
| `-n` | dry run (add/modify/delete) |
| `-c` | continue past errors (bulk LDIF) |

**TLS for network connections:** `LDAPTLS_CACERT=/etc/ssl/certs/ca_ldap.crt ldapsearch -x -H ldaps://10.0.0.85 ...` Without the right CA: `Can't contact LDAP server (-1)`.

### Filter syntax

| Want | Filter |
|---|---|
| exact | `'(cn=user20)'` |
| present | `'(mail=*)'` |
| starts/contains/ends | `'(cn=sets*)'` `'(cn=*user*)'` `'(cn=*20)'` |
| AND / OR / NOT | `'(&(objectClass=inetOrgPerson)(cn=u*))'` `'(\|(cn=a)(cn=b))'` `'(!(cn=x))'` (type a plain pipe in the terminal) |
| range | `'(modifyTimestamp>=20261118000000Z)'` (UTC, YYYYMMDDHHMMSSZ) |
| everything | `'(objectClass=*)'` |

### "I need to…" → command

**Check the server**

| Situation | Command |
|---|---|
| Running? | `systemctl status slapd` |
| Listening on? | `sudo ss -ltnp \| grep slapd` |
| Version | `slapd -VV` (not `--version`) |
| Alive + trees held (RootDSE) | `ldapsearch -x -H ldapi:/// -s base -b "" -LLL namingContexts supportedSASLMechanisms` |
| TLS works from here | `LDAPTLS_CACERT=CA ldapwhoami -x -H ldaps://10.0.0.85` → `anonymous` |
| Who's connected | `sudo ss -tnp state established '( sport = :636 )'` |

**Look at data**

| Situation | Command |
|---|---|
| All DNs | `sudo ldapsearch -Y EXTERNAL -H ldapi:/// -b BASE -LLL 1.1` |
| Count users | `... -b USERS -LLL '(objectClass=inetOrgPerson)' 1.1 \| grep -c '^dn:'` |
| One user | `... -b USERS -LLL '(cn=user20)'` |
| Created/modified when and by whom | add `'*' '+'` or `createTimestamp modifyTimestamp creatorsName modifiersName` |
| Changed today | `... -b BASE -LLL '(modifyTimestamp>=20261118000000Z)' modifyTimestamp modifiersName` |
| Does user X exist | `... -b USERS '(cn=user20)' 1.1` → one `dn:` line = yes |
| Yes/no on a value | `ldapcompare -x -H ldapi:/// "cn=user20,USERS" "sn:user20"` → TRUE (exit 6) / FALSE (exit 5) |

**Test logins**

| Situation | Command |
|---|---|
| Is this user's password right (what a VPN does) | `ldapwhoami -x -H ldapi:/// -D "cn=user20,USERS" -W` → `dn:...` = correct; `Invalid credentials (49)` = wrong |
| Admin password works | `ldapwhoami -x -H ldapi:/// -D ADMIN -W` |
| What anonymous sees | `ldapsearch -x -H ldapi:/// -b BASE -LLL 1.1` |
| What user X sees | `ldapsearch -x -H ldapi:/// -D "<userDN>" -W -b BASE -LLL` |

**Change data (admin bind; add `-n` for a dry run)**

| Situation | Command |
|---|---|
| Add | `ldapadd -x -H ldapi:/// -D ADMIN -W -f new.ldif` |
| Modify | `ldapmodify -x -H ldapi:/// -D ADMIN -W -f change.ldif` |
| Rename | `ldapmodrdn -x -H ldapi:/// -D ADMIN -W -r "cn=old,USERS" "cn=new"` (`-r` drops old RDN value) |
| Move | add `-s "ou=Other,BASE"` |
| Delete / subtree | `ldapdelete -x -H ldapi:/// -D ADMIN -W "cn=x,USERS"` / `-r "ou=Test,BASE"` |
| Set password (server hashes) | `ldappasswd -x -H ldapi:/// -D ADMIN -W -S "cn=user20,USERS"` |
| Own password | `ldappasswd -x -H ldapi:/// -D "<userDN>" -W -S` |
| Hash by hand | `slappasswd -h '{SSHA}'` |

**Server configuration (cn=config)**

| Situation | Command |
|---|---|
| Databases/suffixes/admins | `sudo ldapsearch -Y EXTERNAL -H ldapi:/// -b cn=config -LLL '(olcDatabase=*)' olcDatabase olcSuffix olcRootDN` |
| ACLs | `... -b cn=config -LLL '(olcAccess=*)' olcAccess` |
| TLS/log settings | `... -b cn=config -s base -LLL olcTLSCertificateFile olcTLSCACertificateFile olcLogLevel` |
| Loaded schemas | `... -b cn=schema,cn=config -LLL -s one cn` |
| objectClass definition | `... -b cn=schema,cn=config -LLL -o ldif-wrap=no olcObjectClasses \| grep -i "'inetOrgPerson'"` |
| Indexes | `... -b cn=config -LLL '(olcDbIndex=*)' olcDbIndex` |
| Change config | `sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f config-change.ldif` |

**Server-side `slap*` tools**

| Situation | Command | slapd |
|---|---|---|
| Backup data | `sudo slapcat -b BASE -l data-$(date +%F).ldif` | running OK |
| Backup config | `sudo slapcat -n 0 -l config-$(date +%F).ldif` | running OK |
| Export matching | `sudo slapcat -b BASE -a '(cn=u*)'` | running OK |
| Test config | `sudo slaptest -F /etc/ldap/slapd.d -u` | running OK |
| Schema check | `sudo slapschema -b BASE` | running OK |
| Test ACL | `sudo slapacl -F /etc/ldap/slapd.d -b "cn=user20,USERS" "sn/read"` (`-D` to test as someone) | running OK |
| Normalise DN | `sudo slapdn -F /etc/ldap/slapd.d "CN=User20, OU=Vpnuser,DC=example,DC=com"` | running OK |
| Restore / bulk import | `sudo systemctl stop slapd && sudo -u openldap slapadd -b BASE -l data.ldif && sudo systemctl start slapd` | **stopped** |
| Reindex | `sudo systemctl stop slapd && sudo -u openldap slapindex -b BASE && sudo systemctl start slapd` | **stopped** |

Run `slapadd`/`slapindex` as `openldap`, or new files belong to root and slapd won't start.

**Troubleshoot**

| Symptom | Investigate |
|---|---|
| `Can't contact LDAP server (-1)` | wrong URL/port or TLS → `ss -ltnp`, rerun with `-d 1` |
| `Invalid credentials (49)` | `ldapwhoami -x -D "<DN>" -W` (AD adds `data 52e/775/532` = bad pw / locked / expired) |
| `No such object (32)` | wrong `-b`; check RootDSE |
| `Insufficient access (50)` | ACL; bind as admin or `slapacl` |
| `Size limit exceeded (4)` | `-E pr=500/noprompt` |
| `Strong(er) authentication required (8)` | server requires signing/TLS |
| slapd won't start | `journalctl -u slapd -n 50`, `slaptest -u` |
| See every operation live | `olcLogLevel: stats` then `journalctl -u slapd -f` |

### LDIF templates

Add:
```
dn: cn=testuser,ou=Vpnuser,dc=example,dc=com
objectClass: inetOrgPerson
cn: testuser
sn: testuser
```
Modify (changes separated by `-`):
```
dn: cn=testuser,ou=Vpnuser,dc=example,dc=com
changetype: modify
replace: sn
sn: Tester
-
add: mail
mail: test@example.com
-
delete: description
```
Delete / rename in batch:
```
dn: cn=old,ou=Vpnuser,dc=example,dc=com
changetype: delete

dn: cn=a,ou=Vpnuser,dc=example,dc=com
changetype: modrdn
newrdn: cn=b
deleteoldrdn: 1
```
Rules: blank line separates entries; `attr:: value` = base64; `#` comment; a leading space continues the previous line.

### Shorter commands: `~/.ldaprc`
```
URI        ldaps://10.0.0.85
BASE       dc=example,dc=com
TLS_CACERT /etc/ssl/certs/ca_ldap.crt
```

### Picking the tool
```
READ?              → ldapsearch (ldapcompare yes/no, ldapwhoami to test a login)
CHANGE entries?    → ldapadd / ldapmodify / ldapmodrdn / ldapdelete (+ -D admin -W)
CHANGE passwords?  → ldappasswd (server hashes)
CHANGE config?     → ldapmodify -Y EXTERNAL -H ldapi:/// (sudo)
BACKUP / RESTORE?  → slapcat / slapadd (on the server)
Server problem?    → systemctl, journalctl, slaptest, -d 1
```

### Identifying LDAP commands on a box (and look-alikes)

- **`ldap*` = client tools** (`ldap-utils`): talk to a server over the network or socket.
- **`slap*` = server tools** (`slapd` package): work directly on the server's database files. All `slap*` are one binary (`slapd`) that checks its own name or `-T {acl|add|auth|cat|dn|index|modify|passwd|test}`.
- **Not LDAP:** `ld`, `ld.bfd` (GNU linker), `ld.so` (dynamic loader), `ldd` (list shared libs), `ldconfig` (lib cache), `ldattach` (serial line discipline), `slattach` (SLIP), `slabtop` / `slabratetop-bpfcc` (kernel slab memory). `libldap` is a shared library, not a command.
- Running `slapd` with no args as a normal user prints nothing: it forks and logs to syslog; it fails with `bind(7) failed errno=13 (Permission denied)` because the default `ldap:///` means port 389, which needs root. Version flag is `-V`/`-VV`, not `--version`.

---

## How LDAP shows up on a Linux machine

Three modes:

| Mode | Meaning | How common |
|---|---|---|
| A. Library only (`libldap`) | dependency of other programs; nothing queries a server | almost every machine |
| B. LDAP client of a directory | logins, groups, sudo rules, SSH keys or home dirs come from LDAP/AD/FreeIPA | corporate, university, lab machines |
| C. LDAP server | the machine **is** the directory (`slapd`, `389-ds`, Samba AD DC) | only if set up |

**Why libldap is present anyway:** `curl/libcurl` (`ldap://` URLs), `gnupg`/`dirmngr` (keys, CRLs), `samba`, `sssd`, `postfix`/`dovecot`, Apache `mod_authnz_ldap`, `php-ldap`/`python3-ldap`, `cyrus-sasl`, `krb5`, mail clients; also **PostgreSQL's libpq/server** (LDAP auth method) and `fwupd` (via curl) were seen loading it on the studied box without using it.

**Client lookup points:**
```
 login/ssh ─►  PAM ───────────┐
 ls -l, id ─►  NSS (glibc) ───┼──► sssd or nslcd ──► LDAP server (389/636/3268)
 sudo      ─►  sudo rules ────┤      (cache)
 sshd      ─►  AuthorizedKeysCommand
 autofs    ─►  automount maps ┘
```
- **NSS** `/etc/nsswitch.conf`: `passwd: files sss` (SSSD), `ldap` (nslcd), `winbind` (Samba→AD); `files systemd` = local only; `netgroup: nis` is an unused Ubuntu default.
- **PAM** `/etc/pam.d/*`: `pam_sss.so`, `pam_ldap.so`, `pam_winbind.so` = passwords verified by the directory.
- **sudo:** `sudoers: sss` or `sudo-ldap` reads `sudoRole` entries.
- **SSH keys:** `AuthorizedKeysCommand /usr/bin/sss_ssh_authorizedkeys` fetches `sshPublicKey`.
- **autofs:** `automount: sss|ldap` → NFS maps from the directory.
- **Daemons:** `sssd` (`/etc/sssd/sssd.conf`: `id_provider = ldap|ad|ipa`, `ldap_uri`, `ldap_search_base`), `nslcd` (`/etc/nslcd.conf`), `winbind` (`smb.conf`), `realmd` (configures them: `realm join`).
- **`/etc/ldap/ldap.conf`** only sets defaults for `ldapsearch` and libldap programs (BASE, URI, TLS_CACERT); it does **not** enable LDAP logins.

**Server files (OpenLDAP):** listens on 389/636/`ldapi:///` (`/var/run/slapd/ldapi`); data in `/var/lib/ldap/` (LMDB `data.mdb`, `lock.mdb`); config in `/etc/ldap/slapd.d/` (cn=config as LDIF, never hand-edit); logs via `journalctl -u slapd`.

---

## Runbook: find what LDAP is doing on ANY Linux machine

```
  P1 Is LDAP software there? ──no──► absent, done
        │yes
  P2 SERVER?   P3 LOGIN CLIENT?   P4 APP CLIENT?
        └──────── P5 live traffic ────────┘
                 P6 deep dive per role
                 P7 evaluation → verdict
  (P2–P4 all "no" → LIBRARY ONLY)
```

**P1 – presence:** packages (`dpkg -l | grep -Ei 'ldap|sssd|nslcd|winbind|realmd|freeipa|389-ds|samba|krb5'`, or rpm/pacman/apk), `ldconfig -p | grep -E 'libldap|liblber'`, and which **running** processes have libldap mapped:
```bash
for p in /proc/[0-9]*; do grep -qs libldap "$p/maps" && echo "${p#/proc/}  $(tr '\0' ' ' <"$p/cmdline" | cut -c1-100)"; done
```
| Seen | Meaning |
|---|---|
| only libldap / openldap-libs | dependency, idle |
| ldap-utils / openldap-clients | someone wanted CLI tools |
| slapd / openldap-servers / 389-ds-base / freeipa-server / samba-dc | server → P2 |
| sssd, nslcd, winbind, realmd, freeipa-client | login client → P3 |
| krb5-user/workstation | Kerberos, usually AD/FreeIPA |
| process: slapd, ns-slapd, samba | server running |
| process: sssd_be, nslcd, winbindd | client running |
| process: apache2, postfix, freeradius, python/gunicorn | app client → P4 |

**P2 – server:** `pgrep -a -f '(^|/)(slapd|ns-slapd|samba|lldap|glauth|kanidmd)( |$)'`, `ss -ltnup | grep -E ':(389|636|3268|3269)\s'`, `ss -xlp | grep ldapi`, `grep SLAPD_ /etc/default/slapd /etc/sysconfig/slapd`.
- `ns-slapd -D /etc/dirsrv/slapd-NAME` = 389-DS (maybe FreeIPA: `ipactl status`); samba + 389/88/3268 = Samba AD DC; 3268/3269 = Global Catalog (AD/Samba DC).
- `0.0.0.0:389` = plain LDAP network-wide; `0.0.0.0:636` only = LDAPS only; `127.0.0.1:389` = local; only `ldapi` = local root/apps only.

**P3 – login client:** nsswitch/PAM/sssd/nslcd/realm/krb5/sshd checks above; prove with `getent passwd <user>`, `id <user>`, `sssctl domain-status <dom>`, `sssctl user-checks <user>`. With SSSD `enumerate=false`, `getent passwd` alone lists no directory users: query a name.

| sssd value | Meaning |
|---|---|
| `id_provider = ad` / `ipa` / `ldap` | joined to AD / FreeIPA / plain LDAP |
| `ldap_uri = ldap://…` without StartTLS | passwords may cross the network unencrypted |
| `cache_credentials = True` | offline logins work |
| `realm list` → `kerberos-member` | domain-joined |

**P4 – apps:** `grep -rIlsE 'ldaps?://|ldapi://' /etc /opt /srv /usr/local/etc` (exclude `site-packages`, `dist-packages`, `node_modules`, `test`, `schema`, `doc`). Typical hits: Apache `AuthLDAPURL`, Postfix/Dovecot LDAP maps, FreeRADIUS `mods-enabled/ldap`, OpenVPN auth-ldap/strongSwan, GitLab/Grafana/Jenkins/Keycloak, `sudo-ldap.conf`, Samba `ldapsam`. Also search for `ldap3`, `python-ldap`, `ldap_(uri|host|server|bind|base)` keys to find app code and config.

**P5 – live traffic:** `ss -tnp state established | grep -E ':(389|636|3268|3269)\s'`: local port 389/636 + other peer = someone querying this server; peer port 389/636 = this machine querying a directory (process name shows which program). Connections can be short: `watch -n2 ...`, `tcpdump -ni any 'tcp port 389 or tcp port 636 or tcp port 3268' -c 30`; on plain 389 `tcpdump -A` shows DNs/filters in cleartext. Server-side: set `olcLogLevel: stats`, read `journalctl -u slapd -f`:
```
conn=12 fd=15 ACCEPT from IP=10.0.0.5:51234 (IP=0.0.0.0:636)   ← who connected
conn=12 op=0 BIND dn="cn=svc-vpn,dc=x,dc=com" method=128       ← who they logged in as (128 = simple)
conn=12 op=1 SRCH base="ou=Users,dc=x,dc=com" scope=2 filter="(uid=bob)"
conn=12 op=1 SEARCH RESULT tag=101 err=0 nentries=1             ← 0 OK, 49 bad pw, 32 no such object
```
SSSD: `debug_level = 6` in `[domain/…]`, logs in `/var/log/sssd/`.

**P6 – deep dive:** OpenLDAP `cn=config` queries (databases, `olcAccess`, `olcSyncrepl`/`olcMultiProvider`, TLS, modules, overlays), objectClass counts via `slapcat | awk`; 389-DS `dsctl -l`, `dsconf <inst> backend suffix list`; FreeIPA `ipactl status`, `ipa user-find`; Samba `samba-tool domain info 127.0.0.1`, `samba-tool user list`, `samba-tool drs showrepl`; SSSD `sssctl domain-list`, `config-check`.

| Attribute | Reading |
|---|---|
| `olcDatabase={1}mdb` + `olcSuffix` | each data tree; `{0}config` = config, `{-1}frontend` = global defaults |
| `olcRootDN` | super-admin of that tree, bypasses ACLs |
| `olcAccess` | top-down, first match wins; `to * by * read` = anyone reads |
| `olcSyncrepl` / `olcMultiProvider: TRUE` | replication (HA); absent = single node |
| `olcModuleLoad` ppolicy/memberof/syncprov | password policy / memberOf / replication provider |
| objectClass counts (posixAccount, inetOrgPerson, groupOfNames, sudoRole) | what the directory is for |

**P7 – evaluation table**

| Check | Command | Good | Bad |
|---|---|---|---|
| Encrypted transport | `ss -ltn`, `olcSecurity`/`olcRequires` | 636 only, or 389 with `tls=1` | 389 without TLS required |
| Anonymous read | `ldapsearch -x -H ldapi:/// -b BASE -LLL dn \| grep -c '^dn:'` | 0 | >0 |
| Password storage | scheme snippet below | `{ARGON2}`, `{SSHA512}`, `{CRYPT}$6$` | plaintext, `{MD5}`, `{SHA}` |
| Certificate | `openssl s_client -connect 127.0.0.1:636 </dev/null \| openssl x509 -noout -subject -issuer -enddate -ext subjectAltName` | valid, SAN matches addresses used | expired / SAN mismatch |
| CA key on server | `find / -name '*.key' -path '*ldap*'` | only server key | CA key too |
| Exposure | `ss -ltn`, `nft list ruleset` | limited to known clients | open everywhere |
| Client TLS verify | `grep TLS_REQCERT/tls_reqcert/ldap_tls_reqcert` | demand/hard | never/allow |
| Replication/HA | `olcSyncrepl` on every node | yes | single node behind a VIP |

Password scheme counter (prints only scheme names):
```bash
slapcat -b "<suffix>" -o ldif-wrap=no | awk '/^userPassword::/{print "b",$2} /^userPassword: /{print "p",$2}' |
while read -r t v; do [ "$t" = b ] && v=$(printf %s "$v" | base64 -d 2>/dev/null)
  case "$v" in '{'*'}'*) printf '%s}\n' "${v%%\}*}";; *) echo PLAINTEXT;; esac; done | sort | uniq -c
```

### The audit script (final version, paste-friendly, read-only)

Paste the whole block into a terminal. Runs as root in one go, saves to `~/ldap-audit.txt`. Contains no `!` (avoids bash history expansion) and no tabs (avoids completion); stdin-reading commands get `</dev/null` so they don't eat the heredoc. Masks secrets and never prints hashes.

```bash
sudo bash <<'EOF' 2>&1 | tee ~/ldap-audit.txt
H(){ printf '\n===== %s =====\n' "$*"; }
FLAG(){ FLAGS+=("$*"); printf '  ALERT: %s\n' "$*"; }
FLAGS=(); SERVER=0; CLIENT=0; APP=0
EXC='--exclude-dir=site-packages --exclude-dir=dist-packages --exclude-dir=node_modules --exclude-dir=test --exclude-dir=tests --exclude-dir=schema --exclude-dir=doc --exclude-dir=.git'

H "0. System"
. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME | kernel $(uname -r) | host $(hostname)"
echo "IPs: $(hostname -I)"

H "1. Installed LDAP-related software"
if   command -v dpkg-query >/dev/null; then PK=$(dpkg-query -W -f='${db:Status-Abbrev} ${Package} ${Version}\n' | awk '$1=="ii"{print $2,$3}')
elif command -v rpm    >/dev/null; then PK=$(rpm -qa --qf '%{NAME} %{VERSION}\n')
elif command -v pacman >/dev/null; then PK=$(pacman -Q)
elif command -v apk    >/dev/null; then PK=$(apk info -v 2>/dev/null); fi
echo "$PK" | grep -Ei 'ldap|sssd|nslcd|nss-pam|winbind|realmd|freeipa|ipa-(client|server)|389-ds|samba|krb5|kanidm|glauth' || echo "  (none)"
ldconfig -p | grep -E 'libldap|liblber' || echo "  (libldap not present)"

H "1b. Running processes that have libldap loaded"
for p in /proc/[0-9]*; do
  grep -qs libldap "$p/maps" && printf '  %-8s %-10s %s\n' "${p#/proc/}" "$(stat -c %U "$p")" "$(tr '\0' ' ' <"$p/cmdline" | cut -c1-110)"
done

H "2. Is this machine an LDAP SERVER?"
if pgrep -a -f '(^|/)(slapd|ns-slapd|samba|lldap|glauth|kanidmd)( |$)'; then SERVER=1; fi
pgrep -a -f 'opendj|apacheds|forgerock' && SERVER=1
L=$(ss -H -ltnup 2>/dev/null | grep -E ':(389|636|3268|3269)\s')
echo "${L:-  (no listener on 389/636/3268/3269)}"
[ -n "$L" ] && SERVER=1
echo "$L" | grep -Eq '(0\.0\.0\.0|\[::\]|\*):389\s' && FLAG "Plain LDAP (389) listens on ALL interfaces - check that TLS is required"
echo "$L" | grep -Eq '(0\.0\.0\.0|\[::\]|\*):636\s' && echo "  note: LDAPS (636) is reachable on ALL interfaces"
ss -xlp 2>/dev/null | grep -i ldapi
grep -sE '^\s*SLAPD_(SERVICES|URLS|OPTIONS)' /etc/default/slapd /etc/sysconfig/slapd

H "3. Does this machine use LDAP for its own LOGINS?"
grep -E '^\s*(passwd|group|shadow|sudoers|automount|netgroup)\s*:' /etc/nsswitch.conf
grep -Eq '^\s*(passwd|group)\s*:.*\b(sss|ldap|winbind)\b' /etc/nsswitch.conf && { CLIENT=1; echo "  -> users/groups come from a directory"; }
grep -Eq '^\s*sudoers\s*:.*\b(sss|ldap)\b' /etc/nsswitch.conf && echo "  -> sudo rules come from a directory"
P=$(grep -RHoE 'pam_(sss|ldap|winbind)\.so' /etc/pam.d/ 2>/dev/null | sort -u); [ -n "$P" ] && { CLIENT=1; echo "$P"; }
for f in /etc/sssd/sssd.conf /etc/sssd/conf.d/*.conf; do
  [ -r "$f" ] && { echo "-- $f"; grep -E '^\s*(\[domain/|id_provider|auth_provider|access_provider|ldap_uri|ldap_search_base|ad_domain|ad_server|ipa_server|ipa_domain|ldap_tls_reqcert|cache_credentials)' "$f"; }
done
[ -r /etc/nslcd.conf ] && { echo "-- /etc/nslcd.conf"; grep -E '^\s*(uri|base|binddn|ssl|tls_reqcert)' /etc/nslcd.conf; }
command -v realm >/dev/null && realm list </dev/null
grep -sE '^\s*default_realm' /etc/krb5.conf
grep -shiE '^\s*AuthorizedKeysCommand\b' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf && echo "  -> SSH keys may come from a directory"
for f in /etc/ldap/ldap.conf /etc/openldap/ldap.conf; do
  [ -r "$f" ] && { echo "-- $f (defaults for ldapsearch etc. only)"; grep -Ev '^\s*(#|$)' "$f" || echo "   (all defaults)"; }
done
grep -shiE '^\s*(TLS_REQCERT|tls_reqcert|ldap_tls_reqcert)\s*=?\s*(never|allow)' /etc/ldap/ldap.conf /etc/openldap/ldap.conf /etc/nslcd.conf /etc/sssd/sssd.conf && FLAG "A client does NOT verify the server TLS certificate"
[ $CLIENT = 0 ] && echo "  -> NO: logins on this machine use local files only"

H "4. Applications configured to use LDAP (secrets masked)"
A=$(grep -rIlsiE $EXC 'ldaps?://|ldapi://|ldap_(ur[il]|host|server|bind|base|port|user)|^ldap3|python-ldap|AuthLDAP' /etc /opt /srv /usr/local/etc 2>/dev/null \
    | grep -vE 'ldap\.conf$|\.dpkg-|^/etc/ldap/|^/etc/default/slapd|\.pyc$|/bin/' | head -40)
if [ -n "$A" ]; then
  APP=1
  for f in $A; do
    echo "-- $f"
    grep -nIiE 'ldaps?://|ldapi://|ldap_|ldap3|python-ldap|AuthLDAP|bind_?dn|base_?dn|search_?base' "$f" \
      | sed -E 's/((pass(word)?|passwd|secret|pwd|token|key)[^=:]*[=:][[:space:]]*).*/\1****/I' | head -8
  done
else echo "  (none)"; fi

H "5. Live LDAP connections right now"
E=$(ss -H -tnp state established 2>/dev/null | grep -E ':(389|636|3268|3269)\s')
if [ -n "$E" ]; then
  echo "-- this machine connecting OUT to an LDAP server (count, program -> server):"
  echo "$E" | awk '$4 ~ /:(389|636|3268|3269)$/ { p="?"; if (match($0,/users:\(\("[^"]+"/)) p=substr($0,RSTART+9,RLENGTH-10); print p" -> "$4 }' | sort | uniq -c
  echo "-- clients connected IN to this server (count, client IP):"
  echo "$E" | awk '$3 ~ /:(389|636|3268|3269)$/ { ip=$4; sub(/:[0-9]+$/,"",ip); print ip }' | sort | uniq -c
else echo "  (no LDAP connections at this moment)"; fi

if pgrep -x slapd >/dev/null; then
  H "6. OpenLDAP (slapd) configuration and data"
  Q(){ ldapsearch -Y EXTERNAL -H ldapi:/// -LLL -o ldif-wrap=no "$@" </dev/null 2>/dev/null; }
  echo "-- databases:"
  Q -b cn=config '(objectClass=olcDatabaseConfig)' olcDatabase olcSuffix olcRootDN olcDbDirectory olcSyncrepl olcMultiProvider
  echo "-- access rules (ACLs):"
  Q -b cn=config '(olcAccess=*)' olcAccess
  echo "-- global settings (TLS, logging, security):"
  Q -b cn=config -s base olcTLSCertificateFile olcTLSCertificateKeyFile olcTLSCACertificateFile olcTLSProtocolMin olcLogLevel olcSecurity olcRequires olcDisallows
  echo "-- loaded modules / overlays:"
  Q -b cn=config '(objectClass=olcModuleList)' olcModuleLoad
  Q -b cn=config '(objectClass=olcOverlayConfig)' dn
  Q -b cn=config -s base olcTLSCertificateFile | grep -q olcTLSCertificateFile || FLAG "slapd has NO TLS certificate configured"
  Q -b cn=config '(|(olcSyncrepl=*)(olcMultiProvider=TRUE))' dn | grep -q '^dn:' || echo "  note: no replication configured - this is a single node (no HA copy of the data)"
  for s in $(Q -b cn=config '(olcSuffix=*)' olcSuffix | awk '/^olcSuffix:/{print $2}'); do
    echo
    echo "-- data tree: $s"
    slapcat -b "$s" 2>/dev/null </dev/null | awk '/^dn:/{n++} /^objectClass:/{c[$2]++} END{print "   total entries:",n+0; print "   entry types:"; for(k in c) printf "   %5d %s\n",c[k],k}'
    echo "   entries (first 40):"
    slapcat -b "$s" -o ldif-wrap=no 2>/dev/null </dev/null | awk '/^dn:/{print "    "$0}' | head -40
    PW=$(slapcat -b "$s" -o ldif-wrap=no 2>/dev/null </dev/null | awk '/^userPassword::/{print "b",$2} /^userPassword: /{print "p",$2}' |
      while read -r t v; do
        [ "$t" = b ] && v=$(printf %s "$v" | base64 -d 2>/dev/null)
        case "$v" in '{'*'}'*) printf '%s}\n' "${v%%\}*}";; *) echo PLAINTEXT;; esac
      done | sort | uniq -c)
    echo "   password storage (scheme : count):"; echo "${PW:-   (no userPassword attributes)}"
    echo "$PW" | grep -q PLAINTEXT && FLAG "PLAINTEXT passwords stored in $s"
    echo "$PW" | grep -Eq '\{(MD5|SHA|SMD5)\}' && FLAG "Weak password hashes (MD5/SHA1) in $s"
    N=$(ldapsearch -x -H ldapi:/// -b "$s" -LLL dn </dev/null 2>/dev/null | grep -c '^dn:')
    echo "   anonymous (no password) can list: $N entries"
    [ "$N" -gt 0 ] && FLAG "ANONYMOUS READ: anyone reaching the server can list $N entries in $s"
  done
  for d in $(Q -b cn=config '(olcDbDirectory=*)' olcDbDirectory | awk '/^olcDbDirectory:/{print $2}'); do
    echo "-- database files in $d:"; ls -l "$d"
  done
fi
command -v dsctl >/dev/null && { H "6b. 389 Directory Server"; dsctl -l </dev/null; }
command -v ipactl >/dev/null && { H "6c. FreeIPA"; ipactl status </dev/null; }
command -v samba-tool >/dev/null && pgrep -x samba >/dev/null && { H "6d. Samba AD DC"; samba-tool domain info 127.0.0.1 </dev/null 2>/dev/null; }

H "7. TLS certificate offered to clients"
for port in 636 3269; do
  ss -H -ltn | grep -Eq ":$port\s" || continue
  echo "-- port $port"
  CERT=$(echo | timeout 5 openssl s_client -connect 127.0.0.1:$port 2>/dev/null | openssl x509 2>/dev/null)
  [ -z "$CERT" ] && { FLAG "Could not read certificate on port $port"; continue; }
  echo "$CERT" | openssl x509 -noout -subject -issuer -enddate -ext subjectAltName
  echo "$CERT" | openssl x509 -noout -checkend 2592000 >/dev/null || FLAG "Certificate on port $port expires within 30 days"
  SAN=$(echo "$CERT" | openssl x509 -noout -ext subjectAltName 2>/dev/null)
  for ip in $(hostname -I); do
    echo "$SAN" | grep -qw "$ip" || echo "  note: certificate does NOT cover $ip - clients connecting to that address will fail TLS verification"
  done
done
ss -H -ltn | grep -Eq ':389\s' && { echo "-- port 389 StartTLS"; echo | timeout 5 openssl s_client -starttls ldap -connect 127.0.0.1:389 2>/dev/null | openssl x509 -noout -subject -enddate 2>/dev/null || FLAG "Port 389 open but StartTLS not offered"; }

H "8. Private keys near LDAP"
find /etc/ldap /etc/openldap /etc/ssl/private /home /root -maxdepth 4 -type f -name '*.key' -printf '  %m %u:%g %p\n' 2>/dev/null
find /etc/ldap /etc/openldap /etc/ssl/private /home /root -maxdepth 4 -type f \( -iname 'ca*.key' -o -iname '*_ca.key' -o -iname '*-ca.key' -o -iname '*rootca*.key' \) 2>/dev/null | grep -q . && FLAG "A CA private key is stored on this server (anyone with root can mint trusted certificates)"
find /etc/ldap /etc/openldap /etc/ssl/private /home /root -maxdepth 4 -type f -name '*.key' -perm -o+r 2>/dev/null | grep -q . && FLAG "A private key file is world-readable"

H "9. High availability"
pgrep -a keepalived || echo "  (keepalived not running)"
ip -br addr | grep -v '^lo'

H "10. Recent LDAP-related logs (24h)"
journalctl --no-pager -q --since -24h -u slapd -u sssd -u nslcd -u 'dirsrv@*' -u samba-ad-dc -u winbind 2>/dev/null | tail -25
[ -z "$(journalctl --no-pager -q --since -24h -u slapd 2>/dev/null)" ] && echo "  (nothing logged - slapd log level is probably minimal)"

H "VERDICT"
[ $SERVER = 1 ] && echo "  * SERVER - this machine HOSTS a directory (sections 2, 6)"
[ $CLIENT = 1 ] && echo "  * CLIENT - this machine's own LOGINS come from a directory (section 3)"
[ $APP    = 1 ] && echo "  * APPS   - some services on this machine QUERY LDAP (sections 4, 5)"
[ "$SERVER$CLIENT$APP" = 000 ] && echo "  * LIBRARY ONLY - LDAP is installed as a dependency and is doing nothing"
if [ ${#FLAGS[@]} -gt 0 ]; then echo "  Security findings:"; printf '   - %s\n' "${FLAGS[@]}"; else echo "  No automatic security findings."; fi
echo
echo "Saved to ~/ldap-audit.txt"
EOF
```

| Verdict | What LDAP does | Next |
|---|---|---|
| LIBRARY ONLY | nothing | nothing |
| CLIENT | logins/`id`/sudo ask a remote directory | P3 config: which server, TLS verify, offline cache |
| APPS | specific services check users against LDAP | P4 file: which server, bind account, TLS |
| SERVER | this machine is the directory others depend on | P5 who uses it, P6 what it holds, P7 how safe |
| several | e.g. FreeIPA server = SERVER + CLIENT | combine |

Lessons from running it: the first run **without sudo** gave a thin report (no process names in `ss`, section 6 skipped, empty journal); the first app search matched Python library code in virtualenvs, hence the `--exclude-dir` list.

---

## Case study: an OpenLDAP server behind a VPN product (anonymised)

Real investigation on an Ubuntu 26.04 VM (kernel 7.0). Names, IPs and the organisation are replaced: host `vpn01`, LAN IP `10.0.0.85`, keepalived VIP `10.0.0.26`, WireGuard IP `10.99.0.4`, suffix `dc=example,dc=com`, users `user01…user18`, apps `/opt/auth-service` and `/opt/vpn-portal`.

### Findings step by step

1. **Packages:** `ldap-utils`, `libldap2`, `libldap-common`, `slapd`, all `2.6.10+dfsg-1ubuntu5`; no sssd/nslcd. `ldconfig` showed `libldap.so.2`, `liblber.so.2` (BER encoder/decoder), `liblmdb.so.0` (slapd's storage engine), `libsasl2.so.2` (used by `-Y EXTERNAL`).
2. **Server running:** `slapd.service` active for 6 days, PID run as `openldap`, `-h "ldapi:/// ldaps:///"` (from `/etc/default/slapd` `SLAPD_SERVICES`), `-d0`, 14 MB RAM, 1.5 s CPU in 6 days. `ss`: slapd on `0.0.0.0:636` and `[::]:636` plus `/var/run/slapd/ldapi`; **no 389**.
3. **Why tests failed:** `ldapsearch -H ldap://localhost` → `Can't contact LDAP server (-1)` (LDAP_SERVER_DOWN: TCP connect failed, nothing on 389). Running `slapd` as a normal user → `bind(7) failed errno=13`: default `ldap:///` = port 389, privileged; the real slapd was unaffected.
4. **Journal timeline:** slapd first started at install time (10:22, same as `/etc/ldap/schema` timestamp); three quick restarts at 10:59 = reconfiguration by a setup script (TLS certs generated in `~/ldap/`, `ca.ldif` applied, `add.ldif` loaded, restart with `ldaps:///`). `connection_input: conn=1176 deferring operation: binding` nine hours later = 1,176 connections so far, so something polls regularly; the message itself just means a client sent its next request before its bind finished and slapd queued it. `data.mdb` mtime showed a write earlier the same day; `lock.mdb` changes on reads.
5. **Setup kit in `~/ldap/`** (root-owned): `root_ca_ldap.cnf` → `ca_ldap.key/.crt` (+ `.srl` serial counter) = a private CA; `ldapserver.cnf` → `ldap.key` (RSA-2048 size) + `ldap.csr`; `ldapserver_cert_ext.cnf` → `ldap.crt` (SAN, serverAuth); `ca.ldif` (TLS config), `add.ldif` (base entries), older `ou.ldif`. slapd (user `openldap`) can't read a 750 home dir, so the live copies are in `/etc/ssl` (confirmed: `olcTLSCertificateFile /etc/ssl/certs/ldap.crt`, key `/etc/ssl/private/ldap.key` 640 `root:ssl-cert`, CA `/etc/ssl/certs/ca_ldap.crt`).
6. **Databases:** `{-1}frontend`, `{0}config` (`olcRootDN cn=admin,cn=config`), `{1}mdb` (`/var/lib/ldap`, suffix `dc=example,dc=com`, rootDN `cn=admin,dc=example,dc=com`). Only module `back_mdb`; no overlays; **no replication**; `olcLogLevel: none`.
7. **Root over ldapi:** `SASL username: gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth`, `SASL SSF: 0` (no SASL-layer encryption; fine on a local socket).
8. **Data:** 20 entries: `dc=example,dc=com` (dcObject + organization), `ou=Vpnuser` (organizationalUnit), 18 `inetOrgPerson` users named by `cn=`. No groups. Password schemes: 14 `{SSHA}`, 4 stored without a scheme prefix (plaintext). Anonymous bind could list all 20 entries.
9. **This machine's own logins:** `passwd/group/shadow: files systemd` → not an LDAP client.
10. **Who uses it:** two local Python apps using `ldap3`:
    - `/opt/auth-service` (gunicorn, 4 workers, `app.main:...`): the **VPN login checker**; auth modes "LDAP", "LDAP + device binding", "LDAP + session-based" (flags in PostgreSQL); reads `ldapIP`, `ldap_port`, `ldap_user`, `ldap_password`, `baseDn` from a `[VpnServerInfo]` config section.
    - `/opt/vpn-portal` (Django, 3 workers): **admin UI**: adds LDAP users (`adduserldap.js`, `/check_ldap_user/`), changes passwords (`MODIFY_REPLACE`), stores the auth mode.
    - **13 established LDAPS connections**, all from gunicorn to `10.0.0.85:636`, i.e. long-lived per-worker connections to itself; no remote clients.
    - PostgreSQL 18 database holds VPN users (`device_id`, `tunnel_ip`, WireGuard `public_key`, `ldap_user` boolean); `is_ldap_configured = True` was set the same minute slapd was installed.
    - libldap was also mapped in postgres and fwupd processes: library only (Postgres supports LDAP auth; fwupd via curl).
11. **Certificate:** issued by the private "root ca", valid one year; SAN = IP `10.0.0.85` only, so it does not cover the VIP `10.0.0.26` or `10.99.0.4`.
12. **HA:** keepalived running (VIP on ens18, route `proto 0x12` = RTPROT_KEEPALIVED), Proxmox VM (MAC prefix `bc:24:11`), WireGuard `wg01`. With no syncrepl, a failover node would not share this directory unless copied separately.

### Architecture

```
 VPN user's laptop                         vpn01 (one VM)
 ┌──────────────┐  username +   ┌──────────────────────────────────────────────────┐
 │ VPN client   │──password────►│ auth-service (Python, gunicorn)                  │
 └──────────────┘               │   │ "is this password right?"                     │
                                │   ▼  LDAP over TLS (636)                         │
 admin in browser               │ slapd ◄── OpenLDAP server                        │
 ┌──────────────┐  add/edit     │   ▼                                              │
 │ vpn-portal   │──users──LDAP─►│ /var/lib/ldap/data.mdb (18 users)                │
 └──────────────┘ (Django)      │ PostgreSQL ← device, tunnel IP, WG key, flags    │
                                │ WireGuard wg01 ← the tunnel                      │
                                └──────────────────────────────────────────────────┘
```
LDAP answers "who is this and is the password right?"; PostgreSQL answers "what device/tunnel do they get?"; WireGuard carries traffic.

### What each app does, in LDAP operations

| Human action | App | LDAP operation |
|---|---|---|
| VPN user connects | auth-service | Bind (service) → Search `(cn=user)` → Bind (as user) |
| Admin checks a name (`/check_ldap_user/`) | vpn-portal | Search: does `cn=<name>` exist? |
| Admin creates a VPN user | vpn-portal | Add `inetOrgPerson` under `ou=Vpnuser` (+ Postgres row `ldap_user=true`) |
| Password change | vpn-portal | Modify (`MODIFY_REPLACE` on `userPassword`) |
| Choose auth mode | vpn-portal | none (stored in Postgres) |

### Observations recorded (not acted on in this session)

Four security-relevant observations from the audit: 4 plaintext `userPassword` values (likely written by the portal's `MODIFY_REPLACE` without hashing; the Password Modify extended operation, `conn.extend.standard.modify_password()` in ldap3, would let the server hash them); anonymous read via `to * by * read` with 636 open on all interfaces including the VPN tunnel; the private CA key and a duplicate server key stored in a home directory; an unrelated world-readable key file. Also: single node behind a keepalived VIP, and no LDAP logging. The study deliberately stopped at observation; remediation was out of scope.

---

## How it works internally

### Inside slapd

- **Three databases:** `{-1}frontend` (default rules for all DBs), `{0}config` (the configuration itself as an LDAP tree), `{1}mdb` (the data).
- **cn=config (dynamic config):** settings are LDAP entries changed with `ldapmodify` at runtime, no restart; on disk as LDIF under `/etc/ldap/slapd.d/` (never hand-edit). Predecessor: static `slapd.conf` + restart. `olc` = OpenLDAP Config. `{n}` = ordering.
- **`olcRootDN`:** super-user of the data, ignores ACLs, password in `olcRootPW`; not an entry in the tree.
- **LMDB:** `data.mdb` = whole directory as a memory-mapped B+tree (reads straight from RAM pages); copy-on-write writes switch the root pointer, so crashes can't half-write and readers never block writers; `lock.mdb` = reader table. `slapcat` reads the file directly and dumps LDIF.
- **Modules/overlays:** `back_mdb` only on the studied box; overlays such as `memberof`, `ppolicy`, `syncprov` add features.

### Transports

| URL | Transport | Used by (case study) |
|---|---|---|
| `ldaps:///` | TCP 636, TLS from first byte | the apps |
| `ldapi:///` | Unix socket `/var/run/slapd/ldapi` | root (`-Y EXTERNAL`) |
| `ldap:///` | 389 | not enabled |

LDAPS: TCP connect → TLS handshake (server cert checked against client's CA file) → LDAP messages inside TLS. ldapi as root: slapd asks the kernel for the peer's credentials (`SO_PEERCRED`) → identity `gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth` (SASL EXTERNAL). Long-lived pooled connections avoid repeating TCP+TLS handshakes per login.

### Access control (ACLs)

Case-study rules on `{1}mdb`:
```
{0} to attrs=userPassword       by self write   by anonymous auth   by * none
{1} to attrs=shadowLastChange   by self write   by * read
{2} to *                        by * read
```
- Evaluated top-down; first matching `to` wins; inside it, first matching `by` decides. Frontend rules are appended after the database's own.
- `{0}`: users may change their own password; **anonymous `auth`** lets an unauthenticated connection use the password only to check a login, which is what makes bind-as-user work; nobody else (not even root over ldapi) can read it.
- `{2}`: everything else readable by anyone.
- Access levels: `none < disclose < auth < compare < search < read < write < manage`.
- Frontend/config `{0}to * by dn.exact=gidNumber=0+uidNumber=0,cn=peercred,... manage by * break`: root over ldapi manages config; `break` = continue to later rules.

### The protocol on the wire

LDAP messages are ASN.1 structures encoded with BER (`liblber`); each `LDAPMessage { messageID, protocolOp, controls }` lets several requests share a connection. Operations: Bind, Search, Compare, Add, Modify, Delete, ModifyDN, Extended (password modify, StartTLS, whoami), Unbind, Abandon.

Search-then-bind login (inferred from the ldap3 code in the case study):
```
app                                                slapd
 │ ── TLS handshake (636) ─────────────────────────►│
 │ msg 1 BindRequest dn=<ldap_user> pw=<ldap_password>     (service login)
 │ ◄────────────────── BindResponse resultCode=0
 │ msg 2 SearchRequest base="ou=Vpnuser,dc=example,dc=com" scope=sub filter="(cn=user20)"
 │ ◄────────────────── SearchResultEntry dn="cn=user20,ou=Vpnuser,dc=example,dc=com"
 │ ◄────────────────── SearchResultDone resultCode=0
 │ msg 3 BindRequest dn="cn=user20,..." pw=<typed>   (checked via ACL "auth")
 │ ◄────────────────── BindResponse 0 (correct) or 49 invalidCredentials
 ▼ then PostgreSQL device/session rules → WireGuard peer allowed
```
Password check: `{SSHA}` value = base64 of SHA-1(password + salt) + salt; slapd re-hashes the typed password with the stored salt and compares. A value with no `{scheme}` prefix is compared as a plain string. Both work for login; they differ only in storage.

Result codes: 0 success, 4 size limit, 8 stronger auth required, 32 no such object, 49 invalid credentials, 50 insufficient access. `attr:: base64==` (double colon) = base64-encoded value.

---

## History and evolution

| Year | Milestone |
|---|---|
| 1988–90 | ITU-T X.500 / DAP: global OSI directory, too heavy for desktops |
| 1992 | U-M developers release the first LDAP software [10] |
| July 1993 | RFC 1487 by Yeong (PSI), Howes (U-M), Kille (ISODE) [11][12]: X.500 model over TCP, string DNs, lightweight BER [13]; Tim Howes led the NSF-backed U-M work [10]. Parallel earlier efforts: Marshall Rose (RFC 1202), Howes et al. (RFC 1249) [14] |
| 1995 | RFC 1777 (LDAPv2), listener on TCP 389 [15] |
| 1996 | U-M announces Netscape will incorporate its LDAP technology; Netscape Directory Server becomes the leading commercial LDAP server [10] |
| 1997 | RFC 2251 (LDAPv3): SASL, controls, extended ops, referrals, UTF-8 |
| 1998 | OpenLDAP Project founded (Kurt Zeilenga), from U-M slapd 3.3 |
| 2000 | Active Directory (Windows 2000) uses LDAPv3 as its core access protocol |
| 2006 | RFC 4510–4519 replace RFC 2251 (current LDAPv3) |
| 2011+ | OpenLDAP moves to LMDB (Howard Chu), replacing BDB/HDB |
| 2021 | OpenLDAP 2.6 (LTS) |
| 2024–25 | Windows Server 2025 requires LDAP signing by default; channel binding enabled ("when supported") by default [7][16] |
| 2026 | OpenLDAP 2.6.12 (Jan), 2.6.13 (Mar), 2.6.14 (Aug: OpenSSL 4.0 support) [2][3][17] |

Two lines of descent from U-M: OpenLDAP and Netscape DS → (sold via AOL, bought and open-sourced by Red Hat) Fedora/389 Directory Server → FreeIPA [10].

### Why it's still used

- Data model fits identity: hierarchical, read-heavy, indexed, schema-checked, fine-grained ACLs.
- The protocol everything speaks: PAM/NSS (SSSD), Apache, Postfix, Samba, Jenkins, GitLab, Grafana, Keycloak, VPNs, firewalls, printers, NAS.
- Sits under SSO: OIDC/SAML (Keycloak, Entra ID, Okta) on top, LDAP as on-prem source of truth; Kerberos authenticates in AD, LDAP handles lookups and authorisation data (tied via SASL/GSSAPI).
- Wire efficiency: BER over TCP with message multiplexing.

---

## Cross-platform comparison

| Platform | Mechanism | Same as LDAP? |
|---|---|---|
| Windows / AD | AD DS speaks LDAPv3 natively; plus ADSI/COM, PowerShell AD module (ADWS 9389), Kerberos | same protocol, Microsoft schema and controls |
| macOS | Open Directory (OpenLDAP-based, legacy), Directory Utility, `dscl`; modern fleets bind to Entra/Okta via Platform SSO | historically same, moving to OIDC |
| Linux | SSSD / nslcd → NSS/PAM; FreeIPA | same protocol, RFC 2307 posixAccount schema |
| Android / iOS | no system directory; MDM (Intune, Jamf) + OIDC/SAML; Exchange GAL via ActiveSync | different (REST/OAuth) |
| Web/cloud | Entra ID (Graph API), Okta Universal Directory, Google Directory API, SCIM | different: JSON over HTTPS, OAuth tokens |
| Network devices | RADIUS/TACACS+ in front, LDAP behind (e.g. Cisco ASA DAP uses LDAP for access decisions [18]) | LDAP as backend |

---

## Alternatives

| Category | Options |
|---|---|
| Servers (Linux) | OpenLDAP slapd, 389-DS / Red Hat DS, FreeIPA (389-DS + MIT Kerberos + Dogtag), Samba 4 AD DC, ForgeRock/Ping DS, OpenDJ, Apache DS, lldap (Rust), Kanidm (LDAP read gateway), glauth |
| Servers (Windows) | AD DS, AD LDS |
| Cloud | Entra ID (no native LDAP; Entra Domain Services adds it), AWS Managed Microsoft AD, Google Secure LDAP, JumpCloud LDAP-as-a-Service |
| Non-LDAP replacements | SCIM 2.0 (provisioning), OIDC/SAML (auth), Microsoft Graph, NIS/NIS+ (legacy), Novell eDirectory |
| GUIs | Apache Directory Studio, JXplorer, LDAP Admin, phpLDAPadmin, LDAP Account Manager; ldp.exe, ADExplorer [5] |
| Libraries | python-ldap, ldap3, JNDI / UnboundID SDK, go-ldap, .NET System.DirectoryServices.Protocols |
| Gateways | ForgeRock DSML / REST-to-LDAP, Json2Ldap, redap [5] |

---

## Role: Systems Administrator (Linux/Windows)

- **Why:** every login, sudo rule, mail alias and group share depends on it.
- **Day to day:** create/disable accounts (LDIF, PowerShell), reset passwords, debug "can't log in" with `ldapsearch` + `sssctl`, watch replication (syncrepl; `repadmin /showrepl` in AD), back up with `slapcat`.
- **Expert knows:** index tuning (`olcDbIndex`; unindexed `eq` filters log `<= mdb_equality_candidates: (uid) not indexed`), `slapcat` is safe live on LMDB, delta-syncrepl vs plain syncrepl, AD tombstones and recycle bin, run `slapadd` as `openldap`.

## Role: IAM Engineer

- **Why:** LDAP is the source of truth feeding SSO.
- **Day to day:** design the DIT, group model (`groupOfNames` vs `posixGroup`), least-privilege service accounts; configure Keycloak/Okta federation and SSSD access filters; password policy (`ppolicy`, AD fine-grained policies).
- **Expert knows:** nested groups (`LDAP_MATCHING_RULE_IN_CHAIN` 1.2.840.113556.1.4.1941), `memberOf` overlay limits, `refint` for referential integrity, "bind as user" vs "search then bind" and their failure modes.

## Role: Penetration Tester / Red Teamer

- **Why:** any domain user can read most of AD over LDAP; it's the main recon channel.
- **Day to day:** anonymous-bind checks; enumerate users, SPNs (Kerberoasting), `DONT_REQ_PREAUTH` (AS-REP roasting), `ms-DS-MachineAccountQuota`, passwords in `description`, LAPS attributes; BloodHound/SharpHound, `ldapdomaindump`, `windapsearch`, NetExec `--module ldap`; NTLM relay to LDAP(S) with `ntlmrelayx` (RBCD, shadow credentials).
- **Expert knows:** relay to LDAP needs signing off; relay to LDAPS needs channel binding off; Server 2025 shuts both by default, pushing attackers toward AD CS (ESC8) and older DCs. `ldap://` traffic is sniffable, `ldaps://` is not.

## Role: SOC / Blue Team Analyst

- **Why:** high-volume or unusual LDAP queries are a strong early recon indicator [19].
- **Day to day:** Event IDs 2889 (unsigned/simple binds), 2887 (daily summary), 3039/3074/3075 (channel binding audit), 1644 (expensive searches, with Field Engineering diagnostics); hunt `(servicePrincipalName=*)`, `(userAccountControl:...:=4194304)`; Defender for Identity "LDAP reconnaissance"; OpenLDAP `olcLogLevel stats`.
- **Expert knows:** SharpHound's collection pattern, honeytoken accounts with SPNs, LDAPS hides filters from the network so DC-side telemetry (ETW) is needed.

## Role: Network Engineer

- **Why:** device admin logins, VPN auth, 802.1X/NAC lean on LDAP directly or via RADIUS; Cisco NAC uses LDAP groups to assign roles [18].
- **Day to day:** LDAP server objects on ASA/FortiGate/Palo Alto (base DN, bind DN, group mapping), firewall rules for 389/636/3268/3269, packet captures.
- **Expert knows:** use the Global Catalog (3268/3269) for forest-wide lookups; on Server 2025 port 389 without signing/TLS is blocked by default [20], so appliances need LDAPS plus the right CA chain; referral chasing across domains often times out on appliances; certificate SAN must match the address clients use (VIP vs node IP, as in the case study).

## Role: DevOps / Platform Engineer

- **Why:** every CI/CD and observability tool has an "LDAP auth" box.
- **Day to day:** run slapd/lldap in containers seeded from LDIF, keep bind credentials in Vault, front LDAP with Dex/Keycloak for Kubernetes OIDC.
- **Expert knows:** manage `cn=config` declaratively (LDIF in Git, `ldapmodify -Y EXTERNAL`), never bake `-w` passwords into scripts, health checks that do a real bind + search.

## Role: Backend Developer

- **Why:** app logins and user lookups, plus a vulnerability class.
- **Day to day:** `ldap3`/JNDI: service-account connection, search for user DN, re-bind as user; pools and timeouts (the case study's gunicorn workers each held long-lived LDAPS connections).
- **Expert knows:** **LDAP injection**: escape filter input per RFC 4515 (`*`→`\2a`, `(`→`\28`, `)`→`\29`, `\`→`\5c`, NUL→`\00`) and DNs per RFC 4514; reject empty passwords (unauthenticated-bind trap); change passwords with the Password Modify extended operation so the server hashes them instead of writing raw `userPassword`; Log4Shell (CVE-2021-44228) abused JNDI `ldap://` lookups (a JNDI flaw, not LDAP's).

## Role: Protocol / Standards Researcher

- **Why:** textbook "lightweight profile beats heavyweight parent": X.500's data model survived, DAP and OSI didn't.
- **Day to day:** RFC 4511 ASN.1, Wireshark `ldap` dissector, extensions (controls by OID, extended ops, syncrepl RFC 4533).
- **Expert knows:** string DNs and lightweight BER were the deliberate simplifications [13]; modern open work is binding authentication to the transport (channel binding, RFC 5056/5929).

---

## Related topics

- **Study areas:** directory services, IAM, Kerberos/AD security, PKI (CRL/cert publishing over LDAP), ASN.1/BER, Linux auth (NSS/PAM/SSSD), secure coding (injection), VPN authentication design (LDAP + device/session binding), HA (keepalived VIP vs directory replication).
- **Certifications:** CompTIA Security+/Network+, RHCSA/RHCE (IdM client), LPIC-3 300 (OpenLDAP, Samba), Microsoft AZ-800/801, OSCP/CRTP/CRTO, GIAC GCIH/GCFA, CISSP Domain 5, Cisco CCNP Security (ISE/ASA AAA).

---

## Follow-up Q&A

### Q: LDAP — which roles? (role pick)
Offered 8 roles (Sysadmin, IAM, Pentester, SOC, Network Engineer, DevOps, Backend Developer, Protocol Researcher); user chose **all**. Scope set to protocol + OpenLDAP client suite + slapd.

### Q: I have a Linux machine; what is LDAP doing there?
Three modes (library only / login client / server), the client lookup points (NSS, PAM, sudo, SSH keys, autofs, sssd/nslcd/winbind), why libldap is installed everywhere, and server file locations. See "How LDAP shows up on a Linux machine".

### Q: What LDAP is there? (tab-completion list of `ldap*` / `slap*` / look-alikes)
Client tools vs server tools vs unrelated `ld*`/`sl*` commands; `slap*` are one binary; why `slapd` with no args printed nothing and `--version` failed. See "Identifying LDAP commands on a box".

### Q: Here are my outputs (ldconfig, journal, systemctl, ss, ls, cn=config, slapcat, nsswitch)
Interpreted into: OpenLDAP server on LDAPS + ldapi only, 18 VPN users, setup timeline from timestamps, the TLS setup kit, keepalived VIP from `proto 0x12`, Proxmox from the MAC prefix. See the case study, findings 1–8 and 12.

### Q: Teach me how to check what LDAP is doing on ANY Linux machine, by running commands and evaluating results
The seven-phase runbook with result-to-meaning tables and the audit script. See "Runbook".

### Q: The first audit output wasn't useful; give simple bullets
It ran without sudo (no section 6, no process names, empty logs) and section 4 matched virtualenv library code. Even so it showed slapd on 636 + ldapi, a local gunicorn app with ldap3 holding 8 connections to itself, logins not using LDAP, and a certificate covering only the node IP.

### Q: Give the full script again; I'll paste it, not save it
Rewritten as one `sudo bash <<'EOF' ... EOF | tee ~/ldap-audit.txt` block, no `!` and no tabs, `</dev/null` on stdin readers, library folders excluded, secrets masked, connection summaries per program and client IP, certificate SAN/expiry checks, key-file checks, HA section. Final version in the runbook section.

### Q: Here is the full audit output
Two apps identified (VPN auth service and admin portal), PostgreSQL's role, 13 local LDAPS connections, ACLs, password schemes, anonymous read, certificate coverage, keys, no replication under keepalived. See the case study.

### Q: No fixes — just teach me LDAP and what is happening there
Concepts explained on the real system: tree/DN/RDN/objectClass/schema, slapd's three databases, cn=config, LMDB, transports, peercred, ACL semantics (including why `anonymous auth` makes logins work), the search-then-bind message flow, `{SSHA}` checking, app actions mapped to LDAP operations. See "How it works internally" and the case-study tables.

### Q: I don't know the commands/flags or when to use them; give me a set for when I need them
The cheat sheet: core flags (connect, bind identity, search, output, TLS), filters, "I need to…" tables (check, read, test logins, change, config, slap tools, troubleshoot), LDIF templates, `~/.ldaprc`, and a decision guide. See "Command cheat sheet".

---

## Sources

[1] Delinea, "Using OpenLDAP Commands," Server Suite documentation. [Online]. Available: https://docs.delinea.com/online-help/server-suite/admin/admin-linux-unix/openldap-proxy-service/using-openldap-commands.htm (accessed Nov. 18, 2026).

[2] OpenLDAP Project, "OpenLDAP 2.6.14 is now available," openldap-announce, Aug. 2026. [Online]. Available: https://lists.openldap.org/hyperkitty/list/openldap-announce@openldap.org/thread/FS6S7TKPWNEV5L5PQN55Q4FMOCQHVN7I/ (accessed Nov. 18, 2026).

[3] OpenLDAP Project, "OpenLDAP 2.6.13 Release," openldap-announce, Mar. 2026. [Online]. Available: https://lists.openldap.org/hyperkitty/list/openldap-announce@openldap.org/2026/3/ (accessed Nov. 18, 2026).

[4] UbuntuUpdates, "Package slapd (noble)." [Online]. Available: https://ubuntuupdates.org/package/core/noble/main/updates/slapd (accessed Nov. 18, 2026).

[5] Ping Identity, "LDAP Tools," ldap.com. [Online]. Available: https://ldap.com/ldap-tools/ (accessed Nov. 18, 2026).

[6] Symas, "OpenLDAP Client Command Reference," Symas Knowledge Base. [Online]. Available: https://kb.symas.com/openldap-client-command-reference.html (accessed Nov. 18, 2026).

[7] Microsoft, "LDAP signing and channel binding," Microsoft Learn. [Online]. Available: https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/ldap-signing (accessed Nov. 18, 2026).

[8] TrustedSec, "LDAP Channel Binding and LDAP Signing." [Online]. Available: https://trustedsec.com/blog/ldap-channel-binding-and-ldap-signing (accessed Nov. 18, 2026).

[9] Ctrl Alt Nod, "FortiGate LDAP Integration with Windows Server 2025." [Online]. Available: https://www.ctrlaltnod.com/?p=3083 (accessed Nov. 18, 2026).

[10] Linux Journal, "LDAP Series Part III - The Historical Secrets." [Online]. Available: https://www.linuxjournal.com/content/ldap-series-part-iii-historical-secrets (accessed Nov. 18, 2026).

[11] IETF Datatracker, "RFC 1487: X.500 Lightweight Directory Access Protocol." [Online]. Available: https://datatracker.ietf.org/doc/rfc1487 (accessed Nov. 18, 2026).

[12] idmdude, "The Most Complete History of Directory Services You Will Ever Find." [Online]. Available: https://idmdude.com/2012/04/13/the-most-complete-history-of-directory-services-you-will-ever-find/ (accessed Nov. 18, 2026).

[13] W. Yeong, T. Howes, S. Kille, "RFC 1487: X.500 Lightweight Directory Access Protocol," July 1993. [Online]. Available: https://www.rfc-editor.org/rfc/rfc1487.html (accessed Nov. 18, 2026).

[14] C. Huitema, message to the cryptography mailing list, Oct. 2021. [Online]. Available: https://www.metzdowd.com/pipermail/cryptography/attachments/20211027/1f208dc2/attachment.htm (accessed Nov. 18, 2026).

[15] W. Yeong, T. Howes, S. Kille, "RFC 1777: Lightweight Directory Access Protocol," Mar. 1995. [Online]. Available: https://www.ietf.org/rfc/rfc1777.txt (accessed Nov. 18, 2026).

[16] Microsoft Security Response Center, "Mitigating NTLM Relay Attacks by Default," Dec. 2024. [Online]. Available: https://www.microsoft.com/en-us/msrc/blog/2024/12/mitigating-ntlm-relay-attacks-by-default (accessed Nov. 18, 2026).

[17] OpenLDAP Project, "OpenLDAP 2.6.12 is now available," openldap-announce, Jan. 2026. [Online]. Available: https://lists.openldap.org/hyperkitty/list/openldap-announce@openldap.org/thread/DKSKLEBVPEXCGQOALYVISOZ6IP4YNY64/ (accessed Nov. 18, 2026).

[18] NetCraftsmen, "LDAP tools." [Online]. Available: https://netcraftsmen.com/ldap-tools (accessed Nov. 18, 2026).

[19] ManageEngine, "LDAP search," ADManager Plus KB. [Online]. Available: https://www.manageengine.com/products/ad-manager/kb/ldap/ldap-search.html (accessed Nov. 18, 2026).

[20] Ctrl Alt Nod, "FortiGate LDAP Integration with Windows Server 2025 – Complete Guide," Nov. 2025. [Online]. Available: https://www.ctrlaltnod.com/en/bugs-issues/network-vpn/fortigate-ldap-integration-windows-server (accessed Nov. 18, 2026).

Notes on certainty: release versions, Windows Server 2025 defaults and the RFC 1487 history come from the sources above. The OpenLDAP 1998 founding, RFC 2251/4510 dates, LMDB timing, role-lens details (event IDs, attack techniques, sssd options) and cross-platform rows are from general knowledge and were not re-verified in this session. The case-study login flow is inferred from the apps' ldap3 imports and config keys, not from packet captures or source review. All case-study identifiers (host, IPs, suffix, user names, app paths, organisation) were anonymised before saving.
