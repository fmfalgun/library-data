---
tool: host
date: 2026-11-24
domains: [Networking, DNS, Linux, Cybersecurity, DevOps]
roles: [Network Engineer, Linux / System Administrator, Penetration Tester / Red Teamer, DNS Administrator / Hostmaster, DevOps / SRE Engineer, Email / Messaging Administrator, SOC / Threat Intel Analyst]
tags: [dns, bind, bind9, isc, dig, nslookup, reverse-dns, ptr, mx, spf, dmarc, axfr, zone-transfer, recon, resolv-conf, linux]
---

# host

## Summary

`host` is BIND 9's simple DNS lookup utility from the Internet Systems Consortium (ISC). It "is normally used to convert names to IP addresses and vice versa" [1], and it can also fetch any record type, check SOA consistency across a zone's name servers, and attempt zone transfers. It sends DNS queries directly, to the servers in `/etc/resolv.conf` or to a server you name, and prints each answer as one readable sentence. It shares its engine with `dig` and `nslookup`.

- **Problem it solves:** quick, correct DNS answers in plain language, without dig's full protocol dump.
- **Current upstream:** BIND 9.20.27 (Current Stable / ESV, Aug 2026, EOL Q2 2028). 9.18 reached EOL with 9.18.50 in June 2026. 9.21.x is the development branch [2].
- **Syntax (BIND 9.20):** `host [-aACdlnrsTUwv] [-c class] [-N ndots] [-p port] [-R number] [-t type] [-W wait] [-m flag] [-4|-6] [-v] [-V] {name} [server]` [1]

### Install / availability

| Platform | How to get it |
|---|---|
| Debian / Ubuntu | `apt install bind9-host` (often pulled in by `bind9-dnsutils`) |
| RHEL / Fedora / Rocky | `dnf install bind-utils` |
| Arch | `pacman -S bind` |
| Alpine | `apk add bind-tools` |
| macOS | Preinstalled at `/usr/bin/host` (BIND-derived) |
| FreeBSD | Base ships an `ldns`-based `host` clone (BIND left base in FreeBSD 10); install `bind-tools` for the ISC version |
| Windows | Not available natively. ISC stopped Windows builds after BIND 9.16, so you use `nslookup` or `Resolve-DnsName` |
| AIX / z/OS | Both have their own `host` commands: same name, different code, going through the system resolver [9] |

---

## Usage and commands (with sample outputs)

### 1. Forward lookup (default)
```
$ host example.com
example.com has address 93.184.215.14
example.com has IPv6 address 2606:2800:21f:cb07:6820:80da:af6b:8b2c
example.com mail is handled by 0 .
```
With no `-t`, host asks for **A, AAAA and MX**, which is why you get three kinds of line. `mail is handled by 0 .` is a **Null MX** (RFC 7505), meaning "this domain accepts no mail".

### 2. Reverse lookup (PTR)
```
$ host 8.8.8.8
8.8.8.8.in-addr.arpa domain name pointer dns.google.
```
If the argument is a dotted-decimal IPv4 or colon-delimited IPv6 address, host performs a reverse lookup by default [3]. It builds the `in-addr.arpa` name for IPv4, or the nibble-reversed `ip6.arpa` name for IPv6, and asks for PTR. The trailing dot marks a fully qualified name.

### 3. A specific record type: `-t`
```
$ host -t MX gmail.com
gmail.com mail is handled by 5 gmail-smtp-in.l.google.com.
gmail.com mail is handled by 10 alt1.gmail-smtp-in.l.google.com.
$ host -t TXT _dmarc.example.org
_dmarc.example.org descriptive text "v=DMARC1; p=reject; rua=mailto:..."
$ host -t NS example.com
example.com name server a.iana-servers.net.
$ host -t SOA example.com
example.com has SOA record ns.icann.org. noc.dns.icann.org. 2024081436 7200 3600 1209600 3600
```

### 4. CNAME chains
```
$ host www.github.com
www.github.com is an alias for github.com.
github.com has address 140.82.121.4
```

### 5. Ask a specific server (bypasses `/etc/resolv.conf`)
```
$ host example.com 1.1.1.1
Using domain server:
Name: 1.1.1.1
Address: 1.1.1.1#53
Aliases:

example.com has address 93.184.215.14
```
`#53` is the port. Use `-p` to change it.

### 6. Verbose, dig-style output: `-v` (`-a` = `-v -t ANY`)
```
$ host -v -t A example.com
Trying "example.com"
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 4242
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; QUESTION SECTION:
;example.com.                   IN      A
;; ANSWER SECTION:
example.com.            3271    IN      A       93.184.215.14
Received 45 bytes from 127.0.0.53#53 in 3 ms
```

### 7. SOA consistency check: `-C`
```
$ host -C example.com
Nameserver 199.43.135.53:
        example.com has SOA record ns.icann.org. noc.dns.icann.org. 2024081436 7200 3600 1209600 3600
Nameserver 199.43.133.53:
        example.com has SOA record ns.icann.org. noc.dns.icann.org. 2024081436 7200 3600 1209600 3600
```
host queries the SOA record for the zone from all of its listed authoritative name servers [4].

### 8. Zone transfer (AXFR): `-l`
```
$ host -l zonetransfer.me nsztm1.digi.ninja
zonetransfer.me name server nsztm1.digi.ninja.
zonetransfer.me name server nsztm2.digi.ninja.
...
```
With `-l`, host performs a zone transfer and prints the NS, PTR and address (A/AAAA) records. Adding `-a` prints all records in the zone [5]. A properly configured server answers `; Transfer failed.` / `REFUSED`. (`zonetransfer.me` is a deliberately open lab zone.)

### 9. Non-recursive query: `-r`
`-r` makes host behave like a name server: it sends non-recursive queries and expects answers that are usually referrals to other name servers [6]. Two uses: walking the delegation chain by hand, and **cache snooping** (asking a resolver whether it already has a name cached).

### 10. Transport, timing and class controls
| Flag | Meaning |
|---|---|
| `-T` / `-U` | Force TCP / UDP |
| `-4` / `-6` | IPv4-only / IPv6-only transport |
| `-W n` | Wait n seconds per query |
| `-R n` | Number of UDP retries (default 1) [6] |
| `-N n` | ndots: how many dots make a name "absolute" before search domains are tried |
| `-c CLASS` | Query class: IN (default), CH (Chaosnet), HS (Hesiod) [4] |
| `-p port` | Non-standard server port |
| `-v` / `-a` | Verbose / verbose + ANY |
| `-C` / `-l` / `-r` | SOA check / zone transfer / non-recursive |
| `-V` | Print version |

```
$ host -c CH -t TXT version.bind ns1.target.tld
version.bind descriptive text "9.18.24"
```
This grabs the server's version banner: classic recon, and a classic thing for a hostmaster to hide.

---

## Output and fields explained

| Output line | Record | Meaning |
|---|---|---|
| `X has address Y` | A | IPv4 address |
| `X has IPv6 address Y` | AAAA | IPv6 address |
| `X mail is handled by N Z` | MX | N = preference (lower is tried first); `0 .` = Null MX, accepts no mail |
| `X is an alias for Z` | CNAME | host followed the alias and then printed the target's records |
| `X name server Z` | NS | Delegated authoritative server |
| `X descriptive text "..."` | TXT | SPF, DMARC, DKIM, site verification tokens |
| `...in-addr.arpa domain name pointer Z` | PTR | Reverse mapping |
| `X has SOA record A B serial refresh retry expire minimum` | SOA | Primary NS; RNAME mailbox (first `.` = `@`); serial; refresh; retry; expire; negative-cache TTL (RFC 2308) |

**Verbose (`-v`) header fields:**
- `status`: the RCODE (NOERROR, NXDOMAIN, SERVFAIL, REFUSED)
- `flags`: `qr` = this is a response; `rd` = recursion desired; `ra` = recursion available; `aa` = authoritative answer, when present
- The number before `IN` in the answer section is the **remaining TTL** in the cache
- `Received ... from 127.0.0.53#53` means the systemd-resolved stub answered, not the real upstream

**Errors and exit codes:**
```
Host nope.example.com not found: 3(NXDOMAIN)      # name doesn't exist
Host example.com not found: 2(SERVFAIL)           # resolver failed (often DNSSEC validation)
Host example.com not found: 5(REFUSED)            # server won't answer you
;; connection timed out; no servers could be reached
```
The number is the RCODE (RFC 1035 / RFC 6895). The exit status is non-zero on failure, so `if host -W 2 name >/dev/null; then ...` works in scripts.

---

## Realistic task: pre-cutover DNS audit for `corp.example`

This is the audit you'd run before moving a domain's mail and web to new infrastructure. It uses all seven roles.

```bash
D=corp.example
host -t NS $D                          # 1. Who is authoritative?          (DNS admin)
host -C $D                             # 2. Do all NS agree on serial?      (DNS admin)
host -t SOA $D | awk '{print $NF}'     # 3. Negative TTL: how long do NXDOMAINs stick?  (SRE)
host -t MX $D                          # 4. Mail routing                    (Email admin)
host -t TXT $D | grep spf1             # 5. SPF present?
host -t TXT _dmarc.$D                  # 6. DMARC policy
MX=$(host -t MX $D | awk 'NR==1{print $NF}')
IP=$(host $MX | awk '/has address/{print $NF; exit}')
host $IP                               # 7. FCrDNS: PTR of the MX IP should map back to $MX
for ns in $(host -t NS $D | awk '{print $NF}'); do
  host -l $D $ns >/dev/null && echo "AXFR OPEN on $ns" || echo "AXFR refused on $ns"
done                                   # 8. Zone-transfer exposure         (Pentester)
host -t A www.$D 8.8.8.8; host -t A www.$D 1.1.1.1   # 9. Propagation on public resolvers (SRE/NetEng)
```
**What a clean result looks like:** every NS shows the same serial, the MX has a matching PTR, SPF and DMARC exist, AXFR is refused everywhere, and the public resolvers agree.

---

## Common mistakes, permissions and gotchas

- **host ignores `/etc/hosts` and nsswitch.** It speaks DNS directly to the servers in `/etc/resolv.conf`, which is the file listed in its FILES section [7]. Applications use `getaddrinfo()`, which follows `/etc/nsswitch.conf`. So `host foo` failing while `ping foo` works (or the reverse) is normal. To see what applications see, run `getent ahosts foo`.
- **On systemd-resolved hosts** you query the `127.0.0.53` stub, not the real upstream. Use `resolvectl status` to see the real upstream servers, or pass a server explicitly. (See the `resolvectl` note.)
- **Search domains and ndots.** `host db` may silently become `db.corp.example`. Use a trailing dot (`host db.`) to stop the search list being appended.
- **`-a` / ANY is unreliable.** Many servers give minimal answers to ANY under RFC 8482 (Cloudflare returns an HINFO "RFC8482"). Query each type you need instead.
- **Default output hides TTLs and flags.** Use `-v` when TTL or the AA flag matters.
- **No DNSSEC detail.** host can't show RRSIG/AD details like `dig +dnssec`. A SERVFAIL here is often a DNSSEC validation failure; confirm with `dig +cd` or `delv`.
- **Permissions:** you don't need root. Port 53 egress has to be allowed, and AXFR needs TCP/53.
- **Legal and ethical:** run `-l` (AXFR) and `-r` cache snooping only against targets you're authorised to test.
- **Name collision:** AIX and z/OS `host` are different programs with different flags [9].

---

## History and evolution

### Three generations of `host`

| Generation | Who / where | What it was |
|---|---|---|
| **1. Rutgers / BSD (mid-1980s)** | Rutgers University; attributed to **Charles Hedrick** (medium confidence, see notes on certainty) | Small C program shipped with BSD and BIND 4. Man page "host - look up host names using domain server", with Rutgers examples (`ATHOS.RUTGERS.EDU has address 128.6.5.46`) and zone downloads via `host -l -v -t any rutgers.edu` [8] |
| **2. Nikhef (1990s)** | **Eric Wassenaar**, Nikhef, Amsterdam | Greatly extended into a zone-checking tool: recursive zone listings, canonical-name and invalid-underscore checks, zone caching [10] |
| **3. BIND 9 (2000 to today)** | **ISC** (BIND 9 engineering partly by Nominum) | Rewritten from scratch alongside `dig` and `nslookup` on one shared engine (`bin/dig/dighost.c`); copyright dates start in 2000; licensed MPL 2.0 [11] |

### Concept history (DNS and BIND)

| When | Milestone |
|---|---|
| 1970s – 1982 | Hosts used one central **HOSTS.TXT** file from SRI-NIC. Mockapetris dates the genesis of DNS to the observation, around 1982, that this system was heading for problems [12] |
| 1983 | **RFC 882 / 883** (Paul Mockapetris, ISI) describe the core of DNS; it "officially" began in 1984 with RFC 920 [13] |
| 1987 | **RFC 1034 / 1035** become the standards every DNS implementation is built on [13]. They still define what host prints: RR types, classes and RCODEs |
| 1980s | **BIND** is written by UC Berkeley graduate students under a DARPA grant [13]; host ships with it |
| 2000 | **BIND 9**, "a major rewrite of nearly all aspects of the underlying BIND architecture" [14]. dig, host and nslookup are unified; nslookup is deprecated and users are pointed to host and dig (June 2000 commit: "also suggest 'host' in addition to 'dig'") [15]. nslookup's deprecation was reversed in 2004 with BIND 9.3 (see the `nslookup` note) |
| 2000s – 2010s | host gains IPv6 (AAAA, `ip6.arpa`, RFC 3596), IDN support, EDNS and TCP control |
| 2019 | RFC 8482 lets servers give minimal ANY responses, which weakens `host -a` |
| 2026 | BIND 9.18 reaches EOL in June [16]. The July release fixed 10 CVEs, mostly DNSSEC handling, crashes and CPU/memory issues in `named`, not the client tools [17]. 9.20.27 (Aug 2026) is current stable / ESV to Q2 2028 [2] |

### Why it's still used today

- **The output is a sentence** ("X has address Y"), which suits both eyeballing and `awk`.
- **It shares dig's engine**, so you get dig-grade correctness (raw DNS, explicit server, TCP/UDP control) with nslookup-grade brevity.
- **It's present on nearly every Linux and macOS box** where bind-utils / bind9-host is installed.
- **Where it sits:** client-side DNS diagnostics, a direct way to query any layer of the resolution chain.

---

## How it works internally

```
host <name> [server]
   │
   ├─ parse args; read /etc/resolv.conf (nameserver, search, ndots)   ← NOT nsswitch, NOT /etc/hosts
   │
   ├─ build query list: default A + AAAA + MX (or -t TYPE; PTR if name is an IP)
   │      apply search list / ndots unless name ends with "."
   │
   ├─ dighost.c engine (shared with dig, nslookup)
   │      UDP by default → TCP on truncation, for AXFR (-l), or with -T
   │      retries (-R), timeout (-W), RD bit set unless -r
   │
   ▼
stub (127.0.0.53) / recursive resolver / authoritative server
   │
   ▼
format each RR as a sentence ("has address", "mail is handled by" …)
exit status ≠ 0 on NXDOMAIN / SERVFAIL / timeout
```

- **-C** first fetches the NS set, then sends an SOA query to each server separately.
- **-l** opens TCP/53 to the given server (or the zone's NS) and requests AXFR.
- **-r** clears the RD (recursion desired) bit, so a resolver answers only from cache or with a referral.

**Certain vs. inferred:** the resolv.conf file, default record types, flags and behaviours come from the man pages [1][3][4][5][6][7]. The shared `dighost.c` engine is visible in the BIND source tree and changelogs [11][18]. The exact UDP→TCP fallback details are standard dig-engine behaviour, described here from knowledge rather than from a re-read of the source.

---

## Cross-platform comparison

| Platform | Tool / API | Talks to | Bypasses OS resolver? | Pick server | AXFR | Scriptable output |
|---|---|---|---|---|---|---|
| Linux / macOS | `host` | DNS directly | ✅ (reads `resolv.conf`) | ✅ | ✅ `-l` | Sentence lines |
| Linux / macOS | `dig` | DNS directly | ✅ | ✅ `@srv` | ✅ | Zone-file format / `+short` |
| Linux | `getent ahosts` / `getaddrinfo()` | nsswitch (files, dns, mdns …) | ❌ (*is* the OS path) | ❌ | ❌ | Simple |
| Linux | `resolvectl query` | systemd-resolved D-Bus | ❌ | Per-link | ❌ | Simple + DNSSEC/cache info |
| Windows | `nslookup` | DNS directly | ✅ | ✅ | ✅ (`ls -d`) | Awkward |
| Windows | `Resolve-DnsName` | DnsQuery API | Optional (`-DnsOnly`, `-Server`) | ✅ | ❌ | PowerShell objects |
| macOS | `dscacheutil -q host` | mDNSResponder | ❌ | ❌ | ❌ | Key/value |
| Web | DNSViz / Google Admin Toolbox Dig | Remote vantage point | n/a | Limited | ❌ | HTML/JSON |
| Cloud | Route 53 `test-dns-answer`, Cloud DNS logs | Provider API | n/a | Provider NS | ❌ | JSON |

**The key split** is between DNS-protocol tools (host, dig, nslookup), which tell you *what DNS says*, and OS-resolver tools (getent, Resolve-DnsName default, dscacheutil), which tell you *what applications see*. Most "DNS is broken" tickets live in the gap between the two.

---

## Alternatives

### Same platform (Unix / Linux)
| Tool | Why pick it |
|---|---|
| `dig` (BIND) | Full protocol view: `+trace`, `+dnssec`, `+short` |
| `nslookup` (BIND) | Interactive, cross-platform muscle memory |
| `drill` / `ldns-host` (NLnet Labs) | DNSSEC chase; FreeBSD base `host` |
| `kdig` (Knot) | DoT / DoH support |
| `delv` (BIND) | DNSSEC validation debugging |
| `resolvectl query` | Goes through systemd-resolved (what apps see on resolved systems) |
| `getent hosts/ahosts` | The nsswitch path apps actually use |
| `doggo` / `dog` | Modern, colourised, DoH/DoT |
| `dnsrecon` / `dnsenum` / `fierce` | Recon automation (record sweeps, AXFR attempts, brute force) |

### Other platforms
- **Windows:** `nslookup`, PowerShell `Resolve-DnsName`
- **macOS:** `host`/`dig` built in; `dscacheutil -q host` for the OS path
- **Android:** Termux `dnsutils`; apps such as Network Analyzer
- **iOS:** apps such as iNetTools, Network Toolbox
- **Web:** Google Admin Toolbox Dig, DNSViz, MXToolbox, dnschecker.org

---

## Role: Network Engineer

**Why it matters:** host is the first check in "is it DNS?".
**Day to day:** forward/reverse checks on device names; PTRs for interfaces (readable traceroutes); internal vs external resolver comparisons (`host app 10.0.0.53` vs `host app 8.8.8.8`) to find split-horizon bugs; `-T` vs UDP to catch firewalls and middleboxes dropping large or fragmented UDP.
**What the expert knows:** a timeout and a REFUSED are different layers (path vs. policy); fragmented EDNS responses die at MTU boundaries; anycast resolvers can answer differently from different sites.

## Role: Linux / System Administrator

**Why it matters:** it shows what DNS itself returns, separate from local overrides.
**Day to day:** validating `resolv.conf`, search domains and ndots; checking server forward/reverse consistency (Kerberos, SSH `UseDNS` and many services break on PTR mismatch).
**What the expert knows:** host ≠ getaddrinfo, so they always compare `host x` with `getent ahosts x`. They know the systemd-resolved stub at `127.0.0.53`, and that `options ndots:5` in Kubernetes pods turns one lookup into several.

## Role: Penetration Tester / Red Teamer

**Why it matters:** DNS is the first map of a target.
**Day to day:** NS/MX/TXT enumeration (TXT leaks SaaS verification tokens and SPF includes, which reveal mail providers); AXFR attempts on every NS; reverse-PTR sweeps over a netblock (`for i in {1..254}; do host 10.1.2.$i; done | grep pointer`); `version.bind` CHAOS banner grabs; `-r` cache snooping to infer which sites a target's resolver has visited.
**What the expert knows:** try AXFR against *each* NS individually, because secondaries are often the misconfigured ones. Wildcard DNS produces false positives in brute forcing, so check a random name first. Internal-only names and `ip6.arpa` data can leak through misconfigured split-horizon resolvers.

## Role: DNS Administrator / Hostmaster

**Why it matters:** it's the quickest way to verify what each authoritative server actually serves.
**Day to day:** `-C` for serial drift after edits; `-r` against each authoritative server to make sure it answers authoritatively (`aa` flag under `-v`); lame-delegation checks (the parent's NS list should match the child's); making sure AXFR and `version.bind` are locked down.
**What the expert knows:** serial arithmetic (RFC 1982); the SOA negative-TTL field; and that a recursive answer tells you nothing about authoritative correctness, so query the authoritative servers directly.

## Role: DevOps / SRE Engineer

**Why it matters:** DNS changes are part of most deploys and cutovers.
**Day to day:** scripted health checks (`host -W 2 svc.internal || alert`); post-deploy propagation checks across several public resolvers; lowering TTLs before migrations.
**What the expert knows:** "propagation" is really cache expiry, governed by the old TTL and the SOA negative TTL. Querying the authoritative server shows the future; querying the resolver shows what's still cached. Pin timeouts (`-W`, `-R`) so checks don't hang.

## Role: Email / Messaging Administrator

**Why it matters:** mail deliverability is mostly DNS.
**Day to day:** MX ordering; SPF (`host -t TXT dom`); DKIM (`host -t TXT sel._domainkey.dom`); DMARC (`_dmarc.dom`); MTA-STS (`_mta-sts.dom`); FCrDNS for every outbound IP (PTR → name → A must loop back).
**What the expert knows:** SPF's 10-DNS-lookup limit; DMARC policy is read from the organisational domain; Null MX (`0 .`) deliberately rejects mail; big receivers (Gmail, Microsoft) penalise missing or mismatched PTRs.

## Role: SOC / Threat Intel Analyst

**Why it matters:** fast IOC enrichment during triage.
**Day to day:** PTRs for suspicious IPs (hosting provider, residential vs. datacenter naming); many A records with low TTLs (a fast-flux sign); NS/SOA pointing to bulletproof providers; TXT oddities.
**What the expert knows:** every live lookup can touch attacker infrastructure if the attacker runs the authoritative server, and it leaks your organisation's resolver IP. For opsec-sensitive IOCs, query through a neutral resolver or use passive-DNS databases instead.

---

## Related topics (where it applies)

- **Study areas:** DNS (RFC 1034/1035); reverse DNS (`in-addr.arpa`, `ip6.arpa`); zone transfers (AXFR/IXFR, TSIG); email authentication (SPF/DKIM/DMARC, MTA-STS); Linux name resolution (nsswitch, systemd-resolved); OSINT and reconnaissance; DNS security (cache snooping, version disclosure, DNSSEC)
- **Certifications:** CompTIA Network+, Linux+, Security+, PenTest+; Cisco CCNA; LPIC-1 (109.4 client-side DNS) and LPIC-2 (207 DNS server); RHCSA/RHCE; CEH (footprinting); OSCP / PNPT / eJPT (information gathering); SANS SEC504 / SEC560
- **Related library entries:** `dig` and `nslookup` (same BIND 9 `dighost.c` engine; dig's BIND 9 rewrite is credited to Michael Sawyer), `dns` (the protocol, Paul Mockapetris), `dnsrecon` / `dnsenum` / `fierce` (automated DNS recon that wraps the same queries), `whois` (registration side of DNS & WHOIS recon), `resolvectl` (what host's queries pass through on systemd systems), `arp-scan` (Layer-2 discovery; host covers the naming side), `keepalived` (VIPs usually sit behind DNS names you verify with host). In the VAPT toolkit page, host is listed under DNS & WHOIS as "dig / host / nslookup".

---

## Follow-up Q&A

### Q: `host` (tool name only), then roles: `all`
Role pick offered 7 roles; all were selected. The full Block A (practical usage) and Block B (deep dive) are reorganised into the sections above. There were no further follow-up questions in this session.

---

## Sources

[1] Arch Linux, "host(1), BIND 9.20.3," man.archlinux.org. [Online]. Available: https://man.archlinux.org/man/host.1.en.raw (accessed Nov. 17, 2026).

[2] Internet Systems Consortium, "BIND 9 downloads," isc.org. [Online]. Available: https://www.isc.org/downloads/bind/ (accessed Nov. 17, 2026).

[3] CentOS source-git, "host.html (BIND)," git.stg.centos.org. [Online]. Available: https://git.stg.centos.org/source-git/bind/blob/d3afd5b428dff0254f0b61445db21d457973043c/f/bin/dig/host.html (accessed Nov. 17, 2026).

[4] Oracle, "host(1)," man pages section 1: User Commands, Feb. 2022. [Online]. Available: https://docs.oracle.com/cd/E88353_01/html/E37839/host-1.html (accessed Nov. 17, 2026).

[5] ISC, "host," BIND 9.10.8-P1 ARM (mirror). [Online]. Available: https://ftp.u-strasbg.fr/unix/isc/bind/9.10.8-P1/doc/arm/man.host.html (accessed Nov. 17, 2026).

[6] Oracle, "host(1M)," man pages. [Online]. Available: https://docs.oracle.com/cd/E86824_01/html/E54764/host-1m.html and https://docs.oracle.com/cd/E36784_01/html/E36871/host-1m.html (accessed Nov. 17, 2026).

[7] Linux.org, "host(1), BIND9." [Online]. Available: https://www.linux.org/docs/man1/host.html (accessed Nov. 17, 2026).

[8] University of Auckland mirror, "host(1), UNIX Reference Manual" (BSD / Rutgers-era version). [Online]. Available: https://www.cs.auckland.ac.nz/references/unix/man/host.1.html (accessed Nov. 17, 2026). See also Debian bind 8.1.2 host.1: https://sources.debian.org/src/bind/1%3A8.1.2-3/debian/host.1

[9] IBM, "host Command," AIX 7.3 documentation. [Online]. Available: https://www.ibm.com/docs/en/ssw_aix_73/h_commands/host.html; and "z/OS UNIX host," https://www.ibm.com/docs/SSLTBW_2.4.0/com.ibm.zos.v2r4.halu101/hostid.htm (accessed Nov. 17, 2026).

[10] E. Wassenaar, "host release notes (991529)," Amiga port readme, Aminet. [Online]. Available: https://se.aminet.net/dev/gg/host-991529.readme (accessed Nov. 17, 2026).

[11] Wikipedia mirror, "host (Unix)." [Online]. Available: https://cavac.at/cavacopedia/Host_%28Unix%29 (accessed Nov. 17, 2026).

[12] P. Mockapetris and K. Dunlap, "Development of the Domain Name System," SIGCOMM 1988. [Online]. Available: https://www.cs.princeton.edu/courses/archive/fall08/cos561/papers/mockapetris88.pdf

[13] ISC, "A Brief History of the DNS and BIND," BIND 9 ARM. [Online]. Available: https://bind9.readthedocs.io/en/latest/history.html (accessed Nov. 17, 2026).

[14] Ubuntu bind9 package, "README (BIND 9)," Launchpad. [Online]. Available: https://bazaar.launchpad.net/~ubuntu-branches/ubuntu/hardy/bind9/hardy-updates/view/33/README

[15] D. Lawrence, "also suggest 'host' in addition to 'dig'," bind9 commit ad7bb5bf, ISC GitLab, Jun. 20, 2000. [Online]. Available: https://gitlab.isc.org/isc-projects/bind9/-/blob/ad7bb5bff3e796f5648835bf87a203d23d8319e4/bin/dig/nslookup.c

[16] ISC, "June 2026 release marks the End of Life for BIND 9.18," isc.org blog. [Online]. Available: https://isc.org/blogs/2026-06-10-bind9-18-eol/

[17] Linux Compatible, "BIND 9.20.27 and 9.21.25 released: what DNS operators should know," 2026. [Online]. Available: https://www.linuxcompatible.org/story/bind-92027-and-92125-released-what-dns-operators-should-know/

[18] FreeBSD stable/5, "contrib/bind9/CHANGES." [Online]. Available: https://socsvn.freebsd.org/socsvn/mirror/FreeBSD/stable/5/contrib/bind9/CHANGES

**Notes on certainty:** flags, output formats and defaults come from the man pages above. Several attributions are inferred rather than sourced: Charles Hedrick as the original Rutgers author (from the Rutgers examples plus memory), and Michael Sawyer writing host's BIND 9 rewrite (he is credited with dig's rewrite on the same shared engine, so host is likely his too, but no source here confirms it). Sample outputs are representative; live IPs and serials change. Install package names and FreeBSD / Windows availability come from general knowledge.
