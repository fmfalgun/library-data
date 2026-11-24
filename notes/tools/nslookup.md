---
tool: nslookup
date: 2026-11-24
domains: [Networking, DNS / Internet infrastructure, System administration, Cybersecurity (recon, DFIR), Windows/AD administration]
roles: [Network Engineer, System Administrator (Linux/Unix), Cybersecurity Analyst / SOC, Penetration Tester / Red Teamer, Windows / Active Directory Administrator, DevOps / SRE / Cloud Engineer, Email / Messaging Administrator, Digital Forensics / Incident Responder]
tags: [dns, bind, isc, resolver, recon, lolbin, clickfix, active-directory, email-auth, troubleshooting]
---

# nslookup

## Summary

nslookup sends a DNS question straight to a chosen name server and shows the raw answer, without going through the operating system's normal name-resolution path. Andrew Cherenson wrote it at UC Berkeley in 1986 and it became part of BIND. The Unix/macOS version now comes from ISC BIND 9 (current stable branch 9.20). Windows ships a separate Microsoft `nslookup.exe`, and BusyBox has a minimal clone. Bypassing the OS resolver is both its main strength (it tests the *server*) and its biggest trap (it does *not* show what applications see). Since 2026 it is also a known LOLBin: ClickFix campaigns use it to pull payloads through DNS.

**Problem it solves:** it asks a specific DNS server for a specific record and shows the raw reply, so a DNS-server fault can be isolated from a client-stack, routing or firewall fault.

---

## Install and availability

| Platform | How you get it | Notes |
|---|---|---|
| Windows (all versions) | Built in: `C:\Windows\System32\nslookup.exe` | Microsoft's own code, not BIND. Still has interactive `ls` |
| Debian/Ubuntu | `apt install bind9-dnsutils` (`dnsutils` = older transitional name) | Ships with `dig` and `host` |
| RHEL/Fedora/Rocky | `dnf install bind-utils` | |
| Arch | `pacman -S bind` | |
| Alpine / containers | BusyBox `nslookup` by default; `apk add bind-tools` for the real one | The BusyBox version behaves differently |
| macOS | Built in (BIND-derived) | |
| FreeBSD | Not in base since BIND left base (Unbound replaced it); `pkg install bind-tools` | Base system offers `host(1)` and `drill(1)` instead |
| Android / iOS | Not available natively | Termux: `pkg install dnsutils`; iOS needs a network-tools app |

**Source layout:** in BIND 9, `bin/dig/nslookup.c` shares its query engine (`dighost.c`) with `dig` and `host`.

**Versions (as of Nov 2026):**
- BIND 9.20 is the current stable/ESV branch, supported to about mid-2028.
- 9.18 reached end of life in June 2026 with 9.18.50.
- On 16 Sep 2026 ISC released 9.20.29 / 9.21.26, fixing 14 CVEs.
- ISC said to expect security fixes in every monthly release for the rest of 2026. The flaws are in the server, but distros rebuild `bind9-dnsutils` in the same cycle.

---

## Usage and commands (with sample outputs)

The IPs are illustrative (RFC 5737 / 3849 documentation ranges). The output format is real.

### 1. Basic forward lookup (A + AAAA)
```
$ nslookup example.com
Server:		127.0.0.53
Address:	127.0.0.53#53

Non-authoritative answer:
Name:	example.com
Address: 192.0.2.10
Name:	example.com
Address: 2001:db8::10
```

### 2. Ask a specific server
```
$ nslookup example.com 1.1.1.1
Server:		1.1.1.1
Address:	1.1.1.1#53
...
```
Comparing answers from different servers (internal resolver, ISP, 1.1.1.1, 8.8.8.8, the authoritative NS) shows where the problem is.

### 3. Mail exchangers
```
$ nslookup -type=mx example.com
Non-authoritative answer:
example.com	mail exchanger = 10 mx1.example.com.
example.com	mail exchanger = 20 mx2.example.com.
```

### 4. Name servers and SOA
```
$ nslookup -type=soa example.com
example.com
	origin = ns1.example.com
	mail addr = hostmaster.example.com
	serial = 2026111701
	refresh = 7200
	retry = 3600
	expire = 1209600
	minimum = 3600
```

### 5. Reverse lookup (PTR)
```
$ nslookup 8.8.8.8
8.8.8.8.in-addr.arpa	name = dns.google.
```

### 6. TXT records (SPF, DMARC, verification)
```
$ nslookup -type=txt _dmarc.example.com
_dmarc.example.com	text = "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
```

### 7. SRV records (Active Directory, SIP, XMPP)
```
C:\> nslookup -type=srv _ldap._tcp.dc._msdcs.corp.example.com
_ldap._tcp.dc._msdcs.corp.example.com	SRV service location:
	  priority       = 0
	  weight         = 100
	  port           = 389
	  svr hostname   = dc01.corp.example.com
```

### 8. Authoritative check
```
$ nslookup -type=ns example.com              # 1) find the NS
$ nslookup www.example.com ns1.example.com   # 2) ask it directly
Server:		ns1.example.com
Address:	198.51.100.53#53

Name:	www.example.com
Address: 192.0.2.20
```
There is no "Non-authoritative answer" line, so this is the zone's own answer. If it differs from #1, the cause is caching or TTL lag, or split-horizon DNS.

### 9. Debug: TTLs and every section of the packet
```
$ nslookup -debug www.example.com
------------
    QUESTIONS:
	www.example.com, type = A, class = IN
    ANSWERS:
    ->  www.example.com
	internet address = 192.0.2.20
	ttl = 287
    AUTHORITY RECORDS:
    ADDITIONAL RECORDS:
------------
```
On Windows, `-d2` dumps everything, including the header flags.

### 10. Interactive mode
```
$ nslookup
> server 9.9.9.9
> set type=any
> set port=5353
> set vc            # force TCP
> example.com
> exit
```
Windows keeps `ls -d zone` (a zone-transfer/AXFR attempt). BIND 9's nslookup dropped `ls`; on Linux, use `dig axfr`.

---

## Output and fields explained

| Field / output | Meaning | Where it comes from / when it changes |
|---|---|---|
| `Server:` / `Address:` | The resolver that answered; `#53` = port (BIND prints it, Windows doesn't) | resolv.conf / adapter settings, or the server argument. `127.0.0.53` = systemd-resolved stub |
| `Non-authoritative answer` | The AA bit in the reply header is 0, so the answer came from cache or recursion | Disappears when you query an authoritative NS directly |
| `mail exchanger = 10 ...` | MX preference; lower is tried first. A trailing `.` means fully qualified | Zone data |
| SOA `origin` | Primary master (MNAME) | Zone data |
| SOA `mail addr` | Zone contact (RNAME); the first `.` stands for `@` | Zone data |
| SOA `serial` | Secondaries compare it to decide whether to transfer the zone; YYYYMMDDnn is a common convention | Changes on every zone edit |
| SOA `refresh/retry/expire` | Secondary sync timers, in seconds | Zone data |
| SOA `minimum` | Since RFC 2308, the **negative-caching TTL** (how long an NXDOMAIN is cached), not a default TTL | Zone data |
| `in-addr.arpa name =` | PTR record; nslookup reverses the octets for you (`ip6.arpa` for IPv6) | Reverse zone owner, usually the IP block holder |
| `ttl =` (debug) | Remaining cache lifetime; counts down on a caching resolver, shows the configured value on the authoritative server | Per query |
| `canonical name =` | A CNAME was followed; the chain prints before the final address | Zone data |
| `** server can't find x: NXDOMAIN` | The name does not exist (authoritative "no") | |
| `*** Can't find x: No answer` | The name exists, but there is no record of that type (NOERROR/NODATA) | |
| `SERVFAIL` | The resolver failed upstream: DNSSEC validation failure, unreachable authoritative servers, or a lame delegation | |
| `REFUSED` | The server won't recurse for you, or an ACL blocks you | |
| `;; connection timed out; no servers could be reached` | UDP/53 blocked or the server is dead | |
| `Server: UnKnown` (Windows) | Windows nslookup first does a PTR lookup of the DNS server's own IP; no PTR → "UnKnown". Harmless | Missing reverse zone |

---

## Realistic task: verifying a DNS cutover during a site migration

Goal: move `shop.example.com` from 192.0.2.20 to 203.0.113.40 with minimal stale caching.

1. **A few days before (T-48h): check the current TTL at the source.** `nslookup -debug shop.example.com ns1.example.com` shows `ttl = 86400`. That is too long, so lower it to 300.
2. **Confirm the change landed.** `nslookup -type=soa example.com ns1.example.com` shows the serial went up. Repeat against `ns2` and confirm the secondaries have the same serial.
3. **Wait at least the old TTL (24h).**
4. **Cut over:** change the A record and bump the serial.
5. **Check the authoritative servers:** `nslookup shop.example.com ns1.example.com` and `ns2` both give 203.0.113.40.
6. **Check public resolvers:** query `1.1.1.1`, `8.8.8.8`, `9.9.9.9` and the corporate resolver. Any that still show the old IP have it cached, and it expires within 300 s.
7. **Check what applications see:** `getent ahosts shop.example.com` (Linux, follows NSS and /etc/hosts) or `Resolve-DnsName shop.example.com` (Windows). nslookup can't show this.
8. **Afterwards:** raise the TTL back to 3600 or more.

---

## Gotchas, common mistakes and permissions

- **nslookup is not what your apps see.** It doesn't use the OS resolver library. It ignores `/etc/hosts` and `nsswitch.conf`, but reads `/etc/resolv.conf` for servers and the search list.
- **On Windows the gap is bigger.** The Windows DNS client resolver (DNS-CR) uses the hosts file, the DNS client cache, WINS, NetBIOS, LLMNR, mDNS and DNS servers. nslookup ignores all of these except DNS servers, does not honour the NRPT, and can't test DoH. `Resolve-DnsName` calls `DnsQueryEx()` and uses DoT/DoH when configured. VPN split-DNS products that rely on NRPT look broken in nslookup even when they work. Microsoft's rule of thumb: if nslookup works but an app doesn't, suspect Windows itself, a DNS policy, or endpoint protection.
- **Search-suffix surprises:** without a trailing dot, nslookup (especially on Windows) tries `name.<suffix>` first. Use `nslookup example.com.` to stop that.
- **Windows retry behaviour:** per a Microsoft engineer in the Windows-Containers repo, Windows nslookup queries only the first DNS server by default, while Linux nslookup retries the others in resolv.conf.
- **BusyBox nslookup** (Alpine, Kubernetes debug pods) is a separate minimal implementation. Older builds handled search domains, `ndots` and AAAA oddly, so use a `dnsutils` image.
- **`set type=any`** is mostly dead: RFC 8482 (2019) lets servers give a minimal answer to ANY queries.
- **No modern transports:** no DoT, DoH or DoQ, no DNSSEC validation display, weak EDNS control.
- **Exit codes** vary by version and platform, so don't script with nslookup. Use `dig +short` or `Resolve-DnsName`.
- **Permissions:** none are needed; any user can run it. That is why attackers like it.

---

## History and evolution

### Origin
- **1986:** Andrew Cherenson writes nslookup as a UC Berkeley class project. It first ships in 4.3-Tahoe BSD and becomes part of BIND.
- **BIND** (Berkeley Internet Name Domain) began as a DARPA-funded Berkeley project in the early 1980s. It was later maintained at DEC (Kevin Dunlap), then by Paul Vixie, and from 1994 by ISC (Internet Systems Consortium, co-founded by Vixie).
- **Original problem:** DNS had just replaced HOSTS.TXT, and admins needed to query a name server and see the raw reply.
- **Other implementations:** Microsoft wrote its own nslookup.exe for Windows NT. ReactOS has a GPL clone by Lucas Suggs. BusyBox has a minimal one.

### Concept timeline
- **1983:** RFC 882/883 (Paul Mockapetris) define DNS.
- **1986:** nslookup.
- **1987:** RFC 1034/1035, the DNS standards still in force.
- **1989:** Steve Hotz at USC-ISI releases `dig` ("domain information groper"), a scriptable tool that prints the whole DNS message. Paul Vixie later merged it into BIND 4.9, linking it against libresolv and nslookup code. `host` is the simple alternative.
- **Late 1990s:** nslookup is criticised for giving provably wrong results in some cases. The blame goes to buggy resolver code carried forward from BIND 4 (discussed by Paul Vixie in an interview; Dan Bernstein published a well-known critique).
- **BIND 9 rewrite (2000):** ISC plans to deprecate nslookup in favour of `dig` and `host` and prints a "deprecated" warning.
- **2004, BIND 9.3:** the deprecation is reversed. Changelog #1700 reads: "nslookup is no longer to be treated as deprecated. Remove 'deprecated' warning message. Add man page." The likely reason is that too many scripts and tools depended on it.
  - ⚠️ **Disputed date:** mailing-list memories place the warning's removal later (one FreeBSD user said after 9.8; another poster cited the 9.9.0a3 notes). The changelog number fits 2004. Treat 2004 as the official date and the later ones as distro lag (inferred).
- **1999 to today:** EDNS0 (RFC 2671 → 6891), DNSSEC (RFC 4033–4035, 2005), RFC 8482 restricting ANY (2019), DNS Flag Day 2020 (EDNS buffer of 1232), and encrypted DNS: DoT (RFC 7858), DoH (RFC 8484), DoQ (RFC 9250). nslookup follows none of these well; `dig` (`+dnssec`, `+tls`, `+https` in 9.18 and later), `delv` and `kdig` do.
- **2026:** nslookup becomes a malware-delivery LOLBin in ClickFix campaigns (see the SOC and DFIR sections).

---

## How it works internally

- **BIND version:** a front end to `dighost.c`, the same query engine as `dig` and `host`. It reads `/etc/resolv.conf` for nameservers, the search list and options, builds an RFC 1035 query with RD=1, sends it over UDP/53 (TCP with `set vc` or when the reply is truncated), parses the reply and prints it in its own human format. It **does not** call `getaddrinfo()`/NSS, so `/etc/hosts`, nsswitch modules, nscd/systemd-resolved NSS paths and mDNS are skipped. It still goes through the resolved stub if resolv.conf points at `127.0.0.53`.
- **Windows version:** a self-contained executable with its own DNS client. It does not use the Windows DNS Client service (`DnsQuery`/`DnsQueryEx`), so it skips the cache, hosts file, LLMNR, NetBIOS, mDNS, NRPT and DoH. Before each session it does a PTR lookup of the server's IP (hence "Server: UnKnown"). It applies the adapter's DNS suffix search list.
- **Modes:** non-interactive (arguments) or interactive (`>` prompt with `server`, `lserver`, `set` options, and `ls` on Windows).
- **"Non-authoritative answer"** is printed from the AA flag in the response header.

---

## Cross-platform comparison

| Platform | Native "ask DNS" tool / API | Goes through the OS resolver? | Encrypted DNS | Notes |
|---|---|---|---|---|
| Linux (BIND tools) | `nslookup`, `dig`, `host` | ❌ (own client, reads resolv.conf) | `dig +tls/+https` only | Reference implementation |
| Linux (system) | `getaddrinfo()`, `getent`, `resolvectl` | ✅ | resolved can do DoT | What apps actually get |
| Windows | `nslookup.exe` | ❌ | ❌ | Separate Microsoft codebase |
| Windows | `Resolve-DnsName` → `DnsQueryEx()` | ✅ (hosts, cache, LLMNR, mDNS, NRPT) | ✅ DoH/DoT if configured | Microsoft-recommended |
| macOS | `dscacheutil`, `dns-sd`, `getaddrinfo` via mDNSResponder | ✅ | ✅ (encrypted DNS profiles) | `nslookup`/`dig` also bypass it |
| Android | No shell tool; `InetAddress`/`DnsResolver` API; "Private DNS" (DoT) | ✅ | ✅ DoT, DoH on newer versions | Termux gives dnsutils |
| iOS | No shell; Network.framework / `getaddrinfo` | ✅ | ✅ (encrypted DNS profiles) | Third-party apps only |
| Web | Google Admin Toolbox Dig, MXToolbox, `dns.google/resolve?name=` (JSON DoH) | n/a (remote vantage point) | ✅ (DoH) | Tests from outside your network |
| Cloud | Route 53 `TestDNSAnswer`, `gcloud dns record-sets list`, `az network dns record-set list` | n/a | n/a | Checks zone data, not propagation |
| Containers / embedded | BusyBox `nslookup` | ❌ | ❌ | Minimal; behaviour differs |

**Same:** they all send an RFC 1035 query to a server. **Different:** whether hosts files, caches, multicast (LLMNR/mDNS) and policy (NRPT, split DNS) apply, and whether the transport is encrypted.

---

## Alternatives

**Linux**
- `dig`: the power tool, shows full sections and flags
- `host`: terse output
- `drill`: from ldns
- `kdig`: from Knot; supports DoT/DoH
- `delv`: DNSSEC validation
- `resolvectl query`: systemd-resolved's own view
- `getent ahosts`: the true application path via NSS
- Modern options: `doggo` and `q`, both with DoH/DoT/DoQ support and coloured output

**Windows**
- `Resolve-DnsName`: uses the native DNS client
- `ipconfig /displaydns` and `/flushdns`
- `ping`: exercises the full resolver path
- `dcdiag /test:dns` and `nltest /dsgetdc:` for AD

**macOS**
- `dscacheutil -q host -a name <name>`
- `dns-sd -G v4v6 <name>`
- `scutil --dns`

**Web and cloud:** see the table above.

---

## Role lens

### Network Engineer
- **Why it matters:** "It's always DNS." You need to tell a DNS fault from a routing or firewall fault in under a minute.
- **Day to day:** query the same name through several servers to isolate the failing hop; use `set vc` to check that TCP/53 works (truncated replies and DNSSEC need TCP); check PTR records for router and interface naming.
- **What an expert knows:** whether the AA bit means anything; that a timeout and a SERVFAIL point to different layers; that UDP fragmentation of large EDNS replies breaks behind some firewalls (DNS Flag Day 2020 → 1232-byte buffer). nslookup can't show that, so they switch to `dig +bufsize`.

### System Administrator (Linux/Unix)
- **Why it matters:** apps fail on name resolution and you need to know which layer is at fault.
- **Day to day:** `nslookup` against `127.0.0.53` versus the upstream server; `resolvectl status`; comparing with `getent hosts`.
- **What an expert knows:** nslookup ignores `/etc/hosts` and nsswitch; the resolved stub caches; `options ndots:N` and `search` in resolv.conf change which names get queried; and when to reach for `dig` instead.

### Cybersecurity Analyst / SOC
- **Why it matters:** enriching IOCs (PTR, MX, NS, TXT for a suspicious domain), and nslookup itself as a threat.
- **2026 threat context:**
  - In February 2026, Microsoft Threat Intelligence disclosed a ClickFix variant. Victims are lured into running an `nslookup` command from the Windows Run dialog against an attacker-controlled DNS server, not their default one. The reply carries a PowerShell script that runs on the device. The chain ended with the ModeloRAT remote access trojan, with persistence via startup entries.
  - One researcher (Muhammad Hassoub) noted the payload rode in the DNS response's "Name" field rather than in TXT records, which tools usually watch.
  - Separately, Unit 42 saw KongTuke campaigns use DNS TXT records to stage the next step (leading to the Interlock RAT).
- **What an expert hunts for:**
  - `nslookup.exe` with an explicit non-corporate server argument
  - parent process `explorer.exe` (the Run dialog) or a `cmd /c` chain
  - output piped into `powershell` / `iex`
  - unusual record types
  - DNS traffic that skips the corporate resolver
- **What a beginner misses:** blocking outbound UDP/TCP 53 except to your own resolvers kills the whole technique.

### Penetration Tester / Red Teamer
- **Why it matters:** DNS recon (MITRE ATT&CK T1590.002) and living off the land on Windows.
- **Day to day:**
  - MX, NS and TXT lookups (TXT verification tokens reveal SaaS vendors)
  - PTR sweeps of an IP range
  - zone-transfer attempts with Windows `nslookup` → `server ns1.target` → `ls -d target.com`
  - on a domain-joined foothold, querying `_ldap._tcp.dc._msdcs.<domain>` and `_kerberos._tcp` SRV records to map DCs without extra tooling
- **What an expert knows:** AXFR almost always fails externally but sometimes works internally against AD-integrated DNS; querying the target's own resolver is quieter than going to an external one, which shows up as anomalous.

### Windows / Active Directory Administrator
- **Why it matters:** AD runs on DNS SRV records. Broken DNS means broken logons, GPOs and replication.
- **Day to day:** check DC SRV records, `_msdcs` CNAMEs (DSA GUIDs) and conditional forwarders; do a `server <dc>` check per DC.
- **What an expert knows:** use nslookup to test the DNS *server* and Resolve-DnsName to test the *client*; "Server: UnKnown" just means a missing reverse zone; suffix appending causes confusing extra queries; `dcdiag /test:dns` and `nltest /dsgetdc:` are the AD-aware companions.

### DevOps / SRE / Cloud Engineer
- **Why it matters:** cutovers, blue/green deploys, CDN onboarding, Kubernetes service discovery.
- **Day to day:** the cutover workflow above; `kubectl run -it --rm dnsutils --image=registry.k8s.io/e2e-test-images/jessie-dnsutils:1.3 -- nslookup kubernetes.default`; checking CoreDNS.
- **What an expert knows:** `ndots:5` in pods means `api.example.com` is tried first against the cluster search domains (several wasted queries), and a trailing dot fixes it; BusyBox nslookup results are untrustworthy; TTLs are only a hint, since some resolvers and JVMs (`networkaddress.cache.ttl`) cache longer.

### Email / Messaging Administrator
- **Why it matters:** deliverability lives in DNS.
- **Day to day:** `-type=mx`; `-type=txt` on the domain (SPF), `selector._domainkey.domain` (DKIM), `_dmarc.domain`, `_mta-sts.domain` and `_smtp._tls.domain` (TLS-RPT); PTR on the sending IP, which must match the HELO name (FCrDNS).
- **What an expert knows:** more than one SPF TXT record means a permerror; SPF's 10-lookup limit; long DKIM keys are split into several quoted strings that join together; the null MX (`0 .`, RFC 7505) for domains that never receive mail.

### Digital Forensics / Incident Responder
- **Why it matters:** nslookup shows up in attacker command lines, scripts and LNK files.
- **Day to day:** reviewing 4688 / Sysmon EID 1 (process creation) and EID 22 (DNS query); RunMRU registry entries (Run dialog history, key evidence for ClickFix); PowerShell transcripts; pivoting on the attacker's DNS server IP and domains in passive DNS.
- **What an expert knows:** Sysmon EID 22 logs DnsQuery API calls, and nslookup bypasses that API, so its queries are likely *not* in EID 22. You need network telemetry (DNS server logs, Zeek `dns.log`, firewall logs). *(Inferred from the architecture; verify in a lab.)*

---

## Related topics, study areas and certifications

- **Networking:** CCNA, CompTIA Network+, *TCP/IP Illustrated*, *DNS and BIND* (has a full nslookup chapter), O'Reilly *DNS on Windows* (nslookup chapter)
- **Linux:** LPIC-1 (109 networking), LPIC-2 (207 DNS server), RHCSA/RHCE
- **Windows:** AZ-800/801 (Windows Server Hybrid), MD-102
- **Security:** Security+, CySA+, PenTest+, CEH (footprinting), OSCP (enumeration), GIAC GCIH/GCFA; MITRE ATT&CK T1590.002 (Gather Victim Network Info: DNS), T1071.004 (Application Layer Protocol: DNS), T1016 (System Network Configuration Discovery)
- **Cloud and containers:** AWS SAA / Advanced Networking (Route 53), CKA (cluster DNS debugging)
- **Study topics:** DNS resolution, caching and TTLs, split-horizon DNS, DNSSEC, email authentication (SPF/DKIM/DMARC), LOLBins, DNS tunnelling and C2
- **Related library records:** `dig`, `whois`, `resolvectl`, `nmap`, `fierce`, `amass`; people: Paul Mockapetris, Paul Vixie, Kevin Dunlap, Andrew Cherenson

---

## Follow-up Q&A

No follow-up questions were asked in this session. The session went role pick (all 8 roles) → full explore → save.

---

## Certain vs. inferred

- **Certain (sourced):** the 1986 Berkeley origin, the 4.3-Tahoe BSD release, the BIND 9 deprecation and its 2004 reversal, the Windows resolver behaviour (Microsoft), the 2026 ClickFix nslookup campaigns, and the BIND version status.
- **Disputed:** exactly when the deprecation warning disappeared from distro builds.
- **Inferred:** the Sysmon EID 22 blind spot, and the reason for the deprecation reversal (the cited poster guessed it).

---

## Sources

- [Wikipedia: Nslookup](https://en.wikipedia.org/wiki/Nslookup) and [mirror with infobox](https://wiki.riteme.site/wiki/Nslookup)
- [Stevens cs615asa list: nslookup vs dig (Jan Schaumann)](https://lists.stevens.edu/pipermail/cs615asa/2018-March/001921.html)
- [DNG list: Rick Moen on the nslookup deprecation](https://lists.dyne.org/lurker/message/20181017.055443.32d18573.ca.html)
- [FreeBSD questions: nslookup removed from base](https://groups.google.com/g/mailing.freebsd.questions/c/NKGL2QEcsQc)
- [Microsoft Tech Community: Resolve-DnsName vs nslookup](https://techcommunity.microsoft.com/blog/networkingblog/resolve-dnsname-vs-nslookup-in-windows/4483858)
- [Microsoft Tech Community: Network trace analysis 04 — DNS](https://techcommunity.microsoft.com/t5/core-infrastructure-and-security/introduction-to-network-trace-analysis-4-dns-it-s-always-dns/ba-p/4005803)
- [Matt Davis: Resolve-DnsName vs nslookup](https://da5is.github.io/Resolve-DNS-Name-vs-nslookup)
- [TheITBros: nslookup command and DoH](https://theitbros.com/nslookup-command/)
- [Microsoft Windows-Containers issue #216](https://github.com/microsoft/Windows-Containers/issues/216)
- [jdebp: nslookup flaws](https://jdebp.uk/FGA/nslookup-flaws.html)
- [ISC BIND downloads](https://www.isc.org/downloads/bind/) · [endoflife.date: BIND 9](https://endoflife.date/bind-9)
- [LinuxCompatible: BIND 9.20.27 / 9.18 EOL](https://www.linuxcompatible.org/story/bind-92027-and-92125-released-what-dns-operators-should-know/)
- [The Hacker News: BIND 9 fixes 14 flaws](https://thehackernews.com/2026/09/bind-9-update-fixes-14-flaws-including.html)
- [Secure.com: Microsoft on DNS-based ClickFix](https://www.secure.com/blog/microsoft-warns-clickfix-attackers-are-now-hiding-malware-inside-dns-traffic)
- [Aviatrix: ClickFix DNS / ModeloRAT](https://aviatrix.ai/threat-research-center/clickfix-dns-powershell-attack-2026)
- [Cyber Security News: ClickFix via nslookup.exe](https://cybersecuritynews.com/clickfix-attack-using-nslookup/)
- [Cryptika: KongTuke DNS TXT staging](https://www.cryptika.com/attackers-using-dns-txt-records-in-clickfix-script-to-execute-powershell-commands/)
- [Microsoft Learn: nslookup](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/nslookup)
