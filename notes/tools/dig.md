---
tool: dig
date: 2026-11-24
domains: [Networking (DNS), Linux/Unix sysadmin, DevOps/SRE, Cybersecurity (recon & DNS security), Email infrastructure, Cloud]
roles: [Network Engineer, DNS / Systems Administrator, DevOps / SRE, Penetration Tester / Red Teamer, SOC / Cybersecurity Analyst, Email / Messaging Administrator, Cloud Engineer, Threat Intelligence / OSINT Researcher]
tags: [dns, bind, isc, dnssec, doh, dot, axfr, recon, troubleshooting, email-auth, spf, dkim, dmarc, kubernetes]
---

# dig — DNS lookup utility

## Summary

`dig` (originally "domain information groper") sends a DNS question to any DNS server and prints the **whole raw reply**: header flags, status code, every section, TTLs, EDNS options, query time, and which server answered over which transport. It shows what DNS actually returns, not just a final IP. The BIND man page says most DNS administrators use it because of its flexibility, ease of use and clarity of output.

- Ships with ISC BIND 9 (packages `dnsutils` / `bind9-dnsutils` / `bind-utils` / `bind-tools`).
- Written by Steve Hotz at USC-ISI (1.0 public 29 Mar 1989; 2.0 on 1 Sep 1990), merged into BIND 4.9 by Paul Vixie, rewritten for BIND 9 by Michael Sawyer (c. 2000).
- Status (Nov 2026): BIND **9.20** is the supported stable/ESV branch (EOL target Q2 2028). **9.18 reached end of life in June 2026** (final release 9.18.50). ISC is releasing security fixes monthly through 2026; the latest seen was 9.20.30 / 9.21.27.

---

## Install / availability

| Platform | How to get it |
|---|---|
| Debian/Ubuntu | `sudo apt install dnsutils` (newer: `bind9-dnsutils`) |
| RHEL/Fedora/Rocky | `sudo dnf install bind-utils` |
| Arch | `sudo pacman -S bind` |
| Alpine | `apk add bind-tools` |
| macOS | Pre-installed (Apple-built BIND dig); `brew install bind` for a current version |
| FreeBSD | `pkg install bind-tools` |
| OpenBSD | Ships its own forked `dig` in base (`/usr.bin/dig`) |
| Windows | No current native build: BIND 9.18 removed native Windows support; **9.16 was the last branch with Windows**. Use WSL, Docker, an old 9.16 `dig.exe`, or PowerShell `Resolve-DnsName`. |
| Android / iOS | None built in: Termux (`pkg install dnsutils`) or third-party lookup apps |

---

## Usage & commands (with sample outputs)

### 1. Plain lookup — the anatomy
```
$ dig example.com

; <<>> DiG 9.20.x <<>> example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 41872
;; flags: qr rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
;; QUESTION SECTION:
;example.com.                   IN      A

;; ANSWER SECTION:
example.com.            2847    IN      A       93.184.215.14

;; Query time: 14 msec
;; SERVER: 127.0.0.53#53(127.0.0.53) (UDP)
;; WHEN: Tue Nov 17 16:58:00 IST 2026
;; MSG SIZE  rcvd: 56
```
*(Representative; IP and timings will differ.)* Default query type is A unless `-x` is used.

### 2. Short answer only
```
$ dig +short example.com A
93.184.215.14
```

### 3. Clean answer section (scripts/notes)
```
$ dig +noall +answer example.com MX
example.com.  3600  IN  MX  0 .
```
`MX 0 .` = **null MX** (RFC 7505): the domain accepts no mail.

### 4. Ask a specific server
```
$ dig @1.1.1.1 example.com
$ dig @ns1.example.net example.com +norecurse    # ask the authoritative server directly
```

### 5. Reverse lookup (PTR)
```
$ dig -x 8.8.8.8 +short
dns.google.
```
dig builds `8.8.8.8.in-addr.arpa` for you.

### 6. Trace delegation from the root
```
$ dig +trace www.example.com
.                 518400 IN NS a.root-servers.net.
...
com.              172800 IN NS a.gtld-servers.net.
;; Received 1173 bytes from 198.41.0.4#53(a.root-servers.net) in 20 ms
example.com.      172800 IN NS a.iana-servers.net.
;; Received ... from 192.5.6.30#53(a.gtld-servers.net) in 32 ms
www.example.com.  300    IN A  93.184.215.14
;; Received ... from 199.43.135.53#53(a.iana-servers.net) in 150 ms
```
With `+trace` dig acts as the iterative resolver itself, so it **bypasses your resolver's cache**.

### 7. SOA and serial
```
$ dig +noall +answer example.com SOA
example.com. 3600 IN SOA ns.icann.org. noc.dns.icann.org. 2026111701 7200 3600 1209600 3600
```
Fields: primary NS (MNAME), admin mailbox (RNAME, the first `.` stands for `@`), **serial**, refresh, retry, expire, negative-cache TTL (minimum).

### 8. Zone transfer test
```
$ dig axfr example.com @ns1.example.com
; Transfer failed.
```
"Transfer failed" is healthy. A full dump means the AXFR ACL is misconfigured.

### 9. DNSSEC
```
$ dig +dnssec example.com A        # adds RRSIG records; look for the ad flag
$ dig +cd example.com              # checking disabled: works with +cd but SERVFAILs without it → DNSSEC is broken
$ dig +multiline example.com DNSKEY
```
(`+sigchase` was removed from later versions; use `delv` for validation chains.)

### 10. Encrypted DNS and transports
```
$ dig +https @1.1.1.1 example.com     # DNS over HTTPS (RFC 8484), default path /dns-query
$ dig +tls   @1.1.1.1 example.com     # DNS over TLS (RFC 7858), port 853
$ dig +tcp   example.com
```
Added in BIND 9.18 (DoH first appeared in dig in the 9.17.10 dev release, 2021). Since 9.18 the `SERVER:` line shows the transport (UDP, TCP, TLS, HTTPS), and `+qid=<num>` sets a fixed query ID for testing. 9.18.38 added support for the CO flag.

### Other useful flags
- `-f names.txt`: batch mode (one query per line, same syntax as the command line)
- `+nsid`: which anycast instance answered
- `+subnet=1.2.3.0/24`: test EDNS Client Subnet / GeoDNS (RFC 7871)
- `-4` / `-6`, `-p 5353`, `-b <srcaddr>`
- `+search`: apply resolv.conf search domains (off by default)
- `+yaml`: machine-readable output
- `-k`/`-y`: TSIG-sign queries
- `~/.digrc`: default options

---

## Output / fields explained

| Field | Meaning | Where it comes from / when it changes |
|---|---|---|
| `opcode: QUERY` | Message type (QUERY, NOTIFY, UPDATE…) | Set by the sender |
| `status:` (RCODE) | `NOERROR` OK; `NXDOMAIN` name doesn't exist; `SERVFAIL` resolver failed (often DNSSEC or upstream); `REFUSED` policy/ACL; `FORMERR` malformed | Set by the server in the header |
| `id:` | 16-bit query ID matching reply to query | Random per query; `+qid=` fixes it |
| `qr` | This is a response | Always in replies |
| `aa` | Authoritative answer | Only when querying the zone's authoritative server |
| `rd` | Recursion desired | Set by dig by default; `+norecurse` clears it |
| `ra` | Recursion available | Set by recursive resolvers; authoritative-only servers don't set it |
| `ad` | Authenticated data: resolver validated DNSSEC | Signed zone + validating resolver |
| `cd` | Checking disabled | You set it with `+cd` |
| `tc` | Truncated: retry over TCP | Large UDP responses |
| `QUERY/ANSWER/AUTHORITY/ADDITIONAL` | Count of records in each section | Response contents |
| `OPT PSEUDOSECTION` / `udp: 1232` | EDNS0 version and advertised UDP buffer | 1232 is the DNS Flag Day 2020 default |
| `COOKIE:` | DNS cookie (RFC 7873) | Present when client and server support cookies |
| TTL column | Seconds left in cache | **Counts down on recursive resolvers; fixed on authoritative servers** |
| `Query time` | Round-trip time | Near 0 ms = served from cache |
| `SERVER:` | Who answered, port, transport | `/etc/resolv.conf` unless `@server` |
| `MSG SIZE rcvd` | Response bytes | Watch near the 1232 limit (fragmentation/TC) |

---

## Realistic task start to finish

**Problem:** "We changed the website's IP an hour ago. Why do some users still reach the old server?"

```bash
# 1. Truth: what do the authoritative servers say?
dig +short example.com NS
dig @ns1.example-dns.com example.com A +norecurse +noall +answer
#  -> new IP, aa flag set. The zone is correct.

# 2. Did the change reach every secondary?
for ns in $(dig +short example.com NS); do echo -n "$ns "; dig @$ns example.com SOA +short | awk '{print $3}'; done
#  -> one secondary has an older serial, so a stale secondary is serving the old IP

# 3. What do the big public resolvers have cached, and for how long?
for r in 1.1.1.1 8.8.8.8 9.9.9.9; do dig @$r example.com A +noall +answer; done
#  -> 8.8.8.8 still returns the old IP with TTL 2100: cached before the change

# 4. Full path without cache
dig +trace example.com
```
**Diagnosis:** old TTL of 3600 was never lowered before the change, and one secondary missed the NOTIFY.
**Fix:** `rndc retransfer example.com` on the stale secondary; wait out the TTL. **Next time:** lower the TTL 24–48 hours before a cutover.

---

## Common mistakes, permissions, gotchas

- **Testing the stub by accident:** on systemd-resolved hosts the default server is `127.0.0.53`, so you're testing resolved's cache, not the network. Use `@server` deliberately. (See the resolvectl note: dig bypasses split-DNS routing domains.)
- **dig skips /etc/hosts and nsswitch:** it speaks DNS directly. `getent hosts name` shows what applications really get. dig/browser mismatches often come from `/etc/hosts`, mDNS, macOS `/etc/resolver/*`, or VPN split DNS.
- **`+short` hides failures:** NXDOMAIN and SERVFAIL both print nothing.
- **`ANY` is mostly dead:** under RFC 8482 servers may return a minimal HINFO reply. Query types explicitly.
- **TTL semantics:** they count down on resolvers but stay fixed on authoritative servers, so don't compare the two.
- **Search list not applied by default** (unlike `host`/`nslookup`): add `+search`.
- **Permissions:** no root needed. Firewalls may block UDP/TCP 53, 853 (DoT) or intercept port 53 transparently; `+https` gets around middleboxes.
- **AXFR / recon:** only against domains you are authorised to test.

---

## History & evolution

| When | Event |
|---|---|
| 1983–87 | HOSTS.TXT replaced by DNS: RFC 882/883 (Paul Mockapetris, 1983) → RFC 1034/1035 (1987), the protocol dig speaks |
| 1984–86 | BIND written at UC Berkeley (CSRG) with `nslookup` as its interactive query tool |
| 29 Mar 1989 | dig 1.0 public distribution from USC-ISI (Steve Hotz); revised 1.0 on 15 Apr 1989 with man page |
| 1 Sep 1990 | dig 2.0 public distribution; compiled on Sun3, SPARC, VAX, RT |
| Early 1990s | Paul Vixie (DEC) merges dig into BIND 4.9; his notes say dig 2.0 was built by copying sections of libresolv.a and nslookup, and that dig now linked against nslookup's object files |
| 1998–2000 | BIND 9 full rewrite (development started 1998); Michael Sawyer rewrites dig on BIND 9 libraries: multiple lookups per command, batch mode, `+option` syntax, EDNS0 (RFC 2671 → 6891) |
| 2005 | DNSSEC-bis (RFC 4033–4035): `+dnssec`, `+cd`, `+sigchase` (later removed; `delv` replaces it) |
| 2016–2020 | Cookies (RFC 7873), ECS (RFC 7871, `+subnet`), RFC 8482 minimal ANY, DNS Flag Day 2020 (1232-byte buffer) |
| 2017 | "Domain Information Groper" expansion removed from the man page; licence moved from ISC to MPL 2.0 with 9.11 |
| 2021 | `dig +https` first appears (9.17.10 dev); Windows support dropped after 9.17.14 (dev), with 9.16 the last stable branch supporting it |
| 2022 | BIND 9.18.0: dig gains `+tls` (DoT) and `+https` (DoH); output shows transport; `+qid=` |
| 2024 | BIND 9.20.0: transition to libuv asynchronous loops complete |
| Jun 2026 | BIND 9.18 EOL (final 9.18.50); bind-esv repos switch to 9.20 in July 2026 |
| 2026 | ISC moves to monthly security releases, driven partly by a flood of LLM-generated vulnerability reports (9.20.26 Jul, 9.20.27 Aug, 9.20.29 Sep after a withdrawn 9.20.28, 9.20.30 later) |

---

## How it works internally

- **Not the system resolver:** dig uses BIND's own libraries (libdns/libisc) to build the wire-format DNS message itself. It reads `/etc/resolv.conf` only to pick default servers (and search list with `+search`); it ignores nsswitch, `/etc/hosts`, mDNS and per-domain OS resolvers.
- **Message construction:** header (ID, flags RD by default), question (name, type, class), and an EDNS0 OPT record (buffer size 1232, optional DO bit for `+dnssec`, NSID, ECS, cookie options).
- **Transport:** UDP by default; automatic retry over TCP when `tc` is set; `+tcp`, `+tls` (port 853) and `+https` (HTTP/2 via libnghttp2, `/dns-query`) select others.
- **Event loop:** BIND 9.20 is built on libuv from the ground up, so dig's networking runs through the same netmgr layer as `named`.
- **`+trace`:** dig starts at the root hints, asks each level non-recursively, follows NS referrals (using glue), and prints each hop, so it reproduces the iteration a recursive resolver does, without any cache.
- **Output:** it renders the parsed message section by section in zone-file presentation format; `+yaml` emits structured output instead.

---

## Cross-platform comparison

| Platform | Native mechanism | Raw-DNS tool built in? | Same as dig / different |
|---|---|---|---|
| Linux | glibc `getaddrinfo` + nsswitch, often systemd-resolved | No (dig is a package) | dig bypasses the system resolver; `resolvectl query` uses it |
| Windows | DNS Client service (`Dnscache`), `DnsQuery_*` Win32 API | `nslookup`, `Resolve-DnsName` | Resolve-DnsName covers most of dig's job; NRPT rules complicate split DNS |
| macOS | mDNSResponder, per-interface `scutil` resolvers | dig + `dscacheutil` | dig ignores `/etc/resolver/*` per-domain files that apps honour |
| Android | `netd` / DnsResolver module, Private DNS (DoT) | No | Termux or apps; Private DNS can make your results differ from the network's |
| iOS | Network.framework, encrypted DNS profiles | No | Apps only; no shell |
| Cloud | Route 53, Cloud DNS, Azure DNS | Console "test record" features | Test from inside the VPC to see private zones |
| Network devices | Cisco IOS `ip domain lookup`, Junos `show host` | Very limited | Usually run dig from a jump host |

---

## Alternatives

| Tool | Platform | Notes |
|---|---|---|
| `nslookup` | All OSes (only one on stock Windows) | Older, interactive, hides detail |
| `host` | Unix (BIND) | Terse human-readable output |
| `delv` | Unix (BIND) | Validates DNSSEC itself and explains failures |
| `drill` | Unix (NLnet Labs ldns) | dig-like, good DNSSEC chasing |
| `kdig` | Unix (CZ.NIC Knot) | dig-compatible; strong DoT/DoH/DoQ |
| `doggo`, `q`, `dog` | Cross-platform (Go/Rust) | Modern, colour, JSON, DoH/DoT/DoQ |
| `resolvectl query` | Linux (systemd) | What the system resolver returns (stub, cache, split DNS) |
| `getent hosts` | Linux | What applications get (hosts + DNS + mDNS) |
| `Resolve-DnsName` | Windows PowerShell | The Windows equivalent of dig |
| `dscacheutil -q host`, `scutil --dns` | macOS | System resolver's view and config |
| Google Admin Toolbox Dig, DNSViz, dnschecker | Web | Other vantage points; DNSViz for DNSSEC debugging |
| `nmap --script dns-*`, `dnsrecon`, `dnsx`, `fierce` | Security tooling | Bulk recon built on the same queries |

---

## Why it's still the standard

- **Honest:** shows the raw message (flags, sections, EDNS, transport) and maps one-to-one onto RFC 1035.
- **Reference implementation:** same codebase as `named`, the yardstick for other DNS servers.
- **Ubiquitous:** on every Unix, so runbooks, RFC examples and Stack Overflow posts use dig syntax.
- **Scriptable:** `+short`, `+noall +answer`, `+yaml`, batch mode.
- **Stack position:** app → OS resolver (glibc/systemd-resolved) → recursive resolver → authoritative. dig skips the first two layers and can query any of the others directly.

---

## Role lens

### Network Engineer
- **Why:** many "network down" tickets turn out to be DNS.
- **Day to day:** `@resolver` comparisons between sites; `+tcp` vs UDP for fragmentation/MTU problems; `+nsid` to see which anycast node answered; resolver latency via `Query time`.
- **Expert knows:** `tc` plus TCP failure points to a firewall blocking TCP/53; EDNS buffer size interacts with path MTU; middleboxes rewrite or intercept UDP/53, and `+https` gets around them.

### DNS / Systems Administrator
- **Why:** it's how you verify the servers you run.
- **Day to day:** SOA serials across primary/secondaries; `+norecurse` checks of authoritative servers; AXFR checks between your own servers; PTR checks for mail servers.
- **Expert knows:** look for `aa`; the SOA's last field is the negative TTL (how long NXDOMAIN is cached); when `+cd` "fixes" a SERVFAIL, reach for `delv` or DNSViz; lower TTLs well before changes.

### DevOps / SRE
- **Why:** service discovery, blue/green cutovers, CDNs and Kubernetes all depend on DNS.
- **Day to day:** `kubectl run -it --rm dnsutils ... dig svc.ns.svc.cluster.local` for CoreDNS; `+subnet` for GeoDNS steering; `+short` in health checks and CI.
- **Expert knows:** Kubernetes `ndots:5` makes external names try the search list first (extra queries, latency); JVMs and other runtimes cache DNS beyond TTL; dig won't reproduce search-list behaviour without `+search`.

### Penetration Tester / Red Teamer
- **Why:** DNS is free, passive-ish reconnaissance.
- **Day to day:** `dig axfr @ns target` (rarely open now, still worth testing); TXT records that reveal SaaS vendors (`google-site-verification`, `MS=`); MX/SPF that reveal mail providers; wildcard detection (`dig random123.target`); PTR sweeps; dangling CNAMEs for subdomain takeover.
- **Expert knows:** try AXFR against *every* NS, including hidden primaries from the SOA MNAME, and over IPv6 separately; NSEC zone walking (`dig +dnssec nonexistent.target`) enumerates signed zones that lack NSEC3.

### SOC / Cybersecurity Analyst
- **Why:** most malware touches DNS.
- **Day to day:** resolving IOC domains safely (`+short`, from a sandbox resolver); spotting fast-flux (low TTLs, rotating IPs); NS/SOA ownership checks; testing RPZ/sinkhole on internal resolvers.
- **Expert knows:** querying an attacker's domain can tip them off (their authoritative server sees your resolver), so prefer passive DNS or public resolvers; long, high-entropy labels in TXT/NULL queries indicate DNS tunnelling.

### Email / Messaging Administrator
- **Why:** email authentication is stored entirely in DNS.
- **Day to day:** `dig MX domain`; `dig TXT domain` (SPF); `dig TXT selector._domainkey.domain` (DKIM); `dig TXT _dmarc.domain`; `dig -x mailserver-ip` (FCrDNS: forward and reverse must match); `_mta-sts` and `_smtp._tls` TXT.
- **Expert knows:** the SPF 10-DNS-lookup limit (count by digging each `include:`); a DKIM key split into multiple TXT strings is still one record; two SPF records = PermError.

### Cloud Engineer
- **Why:** cloud DNS has private zones, aliases and resolver endpoints that behave differently from public DNS.
- **Day to day:** dig from inside the VPC (`@169.254.169.253` or VPC+2 on AWS, `@168.63.129.16` on Azure) versus outside to check split-horizon; alias/CNAME chain checks; delegation checks for subdomain hand-offs.
- **Expert knows:** Route 53 ALIAS records look like plain A records to dig; a record in a private hosted zone is invisible from outside, and so are mistakes in it; a missing NS delegation in the parent zone is the classic "works in the console, not on the internet".

### Threat Intelligence / OSINT Researcher
- **Why:** DNS is how you connect infrastructure to its owners.
- **Day to day:** pivoting on shared NS/SOA RNAME emails, MX hosts and PTR patterns; combining live dig with passive-DNS history.
- **Expert knows:** live dig shows only the present, so attribution needs history; bulletproof hosts reuse NS sets; querying is observable by the actor (OPSEC).

---

## Related topics

- **Subjects:** DNS protocol, DNSSEC, encrypted DNS (DoT/DoH), email authentication, network troubleshooting, Kubernetes networking, CDNs/GeoDNS, OSINT/recon, DNS security (tunnelling, cache poisoning, subdomain takeover).
- **Certifications:** CompTIA Network+ / Security+ / PenTest+, CCNA, LPIC-2 (201/202, DNS server topics), RHCSA/RHCE, CEH, OSCP/PNPT (recon), GIAC GCIH/GPEN, AWS Advanced Networking Specialty, CKA (cluster DNS).
- **Further reading:** RFC 1034/1035, 4033–4035, 6891, 7858, 7871, 7873, 8482, 8484; BIND 9 ARM dig manual; *DNS and BIND* (Albitz & Liu, O'Reilly).
- **Library cross-links:** `resolvectl` (system-resolver view vs dig's direct view), DNS Mindmap page.

---

## Follow-up Q&A

No follow-up questions were asked in this session (roles: all 8 selected; one EXPLORE answer, then save).

---

## Sources

- [dig (command) – Wikipedia](https://en.wikipedia.org/wiki/Dig_(command))
- [dig 2.0 README (USC-ISI, 1990)](https://ftp5.gwdg.de/pub/linux/funet/util/networking/programs/dig/dig-2.0.README)
- [BIND 4.9.3 dig.c (Vixie's merge notes)](https://stuff.mit.edu/afs/sipb/project/bind/src/bind-4.9.3-BETA-%3F/tools/dig.c)
- [dig man page source (NetBSD/BIND, dig.rst)](https://grok.dragonflybsd.org/xref/netbsd/external/mpl/bind/dist/bin/dig/dig.rst)
- [OpenBSD dig.1](https://src.rcs.uwaterloo.ca/raw/openbsd-src/usr.bin/dig/dig.1)
- [BIND 9.18.0 release notes](https://bind9.readthedocs.io/en/v9.18.0/notes.html)
- [BIND 9.18.1 release notes](https://bind9.readthedocs.io/en/v9.18.1/notes.html)
- [BIND 9.18.38 release notes](https://bind9.readthedocs.io/en/v9.18.38/notes.html)
- [ISC: Status of DoH in BIND 9 (2021)](https://isc.org/blogs/bind-doh-update-2021/)
- [ISC: BIND update summer 2021 (Windows removal)](https://victor.isc.org/blogs/bind-update-summer2021/)
- [ISC: BIND 9.18 End of Life (June 2026)](https://victor.isc.org/blogs/2026-06-10-bind9-18-eol/)
- [bind-users: 9.18 EOL + bind-esv will be 9.20](https://lists.isc.org/pipermail/bind-users/2026-July/110677.html)
- [BIND 9.20 announcement – Help Net Security](https://www.helpnetsecurity.com/?p=307572)
- [BIND 9.20.27 release coverage](https://www.linuxcompatible.org/story/bind-92027-and-92125-released-what-dns-operators-should-know/)
- [BIND 9.20.30 release coverage](https://www.warp2search.net/story/isc-releases-bind-92030-and-92127-patching-four-flaws-including-an-rce/)
- [The Hacker News – BIND monthly security fixes (Sep 2026)](https://thehackernews.com/2026/09/bind-9-update-fixes-14-flaws-including.html)
- [ISC GRNOG 2026 talk – BIND 9 history](https://grnog.indico.nogalliance.org/event/11/contributions/124/attachments/94/163/BIND%209%20-%20GRNOG.pdf)
