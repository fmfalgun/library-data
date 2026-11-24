---
tool: dnsrecon
date: 2026-11-24
domains: [Cybersecurity, Offensive Security / VAPT, DNS, Network Infrastructure, OSINT, Attack-Surface Management]
roles: [Penetration Tester / Red Teamer, Bug Bounty Hunter, DNS / Network Engineer, Cybersecurity Analyst (Blue Team / SOC), Attack-Surface Management / Threat Intel Analyst, CTF Player / Cert Candidate, Cloud / DevOps Engineer, Tool Developer]
tags: [dns, recon, enumeration, axfr, zone-transfer, subdomain, brute-force, ptr, srv, dnssec, nsec, zone-walking, cache-snooping, certificate-transparency, kali, python]
related: [dnsenum, fierce]
---

# dnsrecon

## Summary

`dnsrecon` is a Python 3 DNS reconnaissance tool by Carlos Perez (darkoperator). It bundles nearly every DNS enumeration technique into one command with selectable modes (`-t`): standard records, zone transfer (AXFR) tests against every name server, subdomain brute force with wildcard detection, SRV discovery, reverse (PTR) sweeps, DNSSEC NSEC zone walking, cache snooping and Certificate Transparency (crt.sh) lookups. Results export to JSON, XML, CSV or SQLite, and since 1.6.0 (Feb 2026) it also offers a REST API.

- **Problem it solves:** one tool answers "what hosts, mail servers and services exist for this domain, and is its DNS leaking more than it should?", sending queries only to DNS servers, never to the target hosts themselves.
- **Position:** the active, authoritative step after passive collection (CT logs, passive DNS) and before port scanning.
- **Siblings:** studied together with `dnsenum` and `fierce` (see their notes). They share a recon phase but differ in author, language, capabilities and maintenance; see the Q&A on why AI answers lump them together.

| | dnsrecon | dnsenum | fierce |
|---|---|---|---|
| Language | Python 3 (Ruby origin) | Perl (ithreads) | Python 3 (Perl origin) |
| Strength | Widest technique set, structured output, API | One fixed pipeline, IP-block mapping | Neighbour PTR walking (non-contiguous IP space) |
| Status (Nov 2026) | Active (1.6.x) | Maintained fork (dnsenum2) | Python port; upstream slowed |

---

## Installation and availability

| Platform | How |
|---|---|
| Kali / Parrot | Preinstalled |
| Debian / Ubuntu | `sudo apt install dnsrecon`; Debian testing/unstable 1.6.0-1, while the Debian tracker notes upstream 1.6.3 is available [3] |
| Alpine / Gentoo / FreeBSD | Alpine community 1.3.1 [4]; Pentoo overlay 1.6.1 [5]; FreeBSD port still 0.10.1 [6] |
| pip | Avoid: PyPI stayed at 0.10.1 (released Jun 7, 2021) [7]. Use git: `git clone https://github.com/darkoperator/dnsrecon && cd dnsrecon && pip install -r requirements.txt` |
| macOS / Windows | git + Python 3 (venv or pipx) |
| Android | Termux + git + Python |

---

## Usage and commands (with sample outputs)

Sample outputs use `zonetransfer.me` (a domain DigiNinja deliberately leaves open for practice) and placeholder `example.com` / documentation IPs. The format is the tool's, but live IPs and records change.

### 1. Standard enumeration (`-t std`, the default)

```
$ dnsrecon -d zonetransfer.me
[*] std: Performing General Enumeration against: zonetransfer.me...
[-] DNSSEC is not configured for zonetransfer.me
[*]      SOA nsztm1.digi.ninja 81.4.108.41
[*]      NS nsztm1.digi.ninja 81.4.108.41
[*]      NS nsztm2.digi.ninja 34.225.33.2
[*]      MX ASPMX.L.GOOGLE.COM 142.250.x.x
[*]      A zonetransfer.me 5.196.105.14
[*]      TXT zonetransfer.me google-site-verification=...
[*] Enumerating SRV Records
[+]      SRV _sip._tcp.zonetransfer.me www.zonetransfer.me 5.196.105.14 5060
[+] 1 Records Found
```

### 2. Zone transfer (`-t axfr`, or `-a` together with std)

```
$ dnsrecon -d zonetransfer.me -t axfr
[*] Checking for Zone Transfer for zonetransfer.me name servers
[*] Resolving SOA Record
[+]      SOA nsztm1.digi.ninja 81.4.108.41
[*] Resolving NS Records
[*] Trying NS server 81.4.108.41
[+] 81.4.108.41 Has port 53 TCP Open
[+] Zone Transfer was successful!!
[*]      A www.zonetransfer.me 5.196.105.14
[*]      A office.zonetransfer.me 4.23.39.254
[*]      A vpn.zonetransfer.me 174.36.59.154
[*] Trying NS server 34.225.33.2
[-] Zone Transfer Failed for 34.225.33.2!
```

### 3. Subdomain brute force (`-t brt`)

```
$ dnsrecon -d example.com -t brt -D subdomains-top1million-5000.txt --threads 20
[*] Using the dictionary file: subdomains-top1million-5000.txt (provided by user)
[*] brt: Performing host and subdomain brute force against example.com...
[+]      A dev.example.com 203.0.113.10
[+]      CNAME shop.example.com example.myshopify.com
[+]      A example.myshopify.com 23.227.38.x
[+] 2 Records Found
```

### 4. Reverse sweep (`-r`, internally `-t rvl`)

```
$ dnsrecon -r 203.0.113.0/24 -n ns1.example.com
[*] Performing Reverse Lookup from 203.0.113.0 to 203.0.113.255
[+]      PTR fw-outside.example.com 203.0.113.1
[+]      PTR mail.example.com 203.0.113.25
[+] 2 Records Found
```

### 5. Certificate Transparency, passive (`-t crt` or `-k`)
Pulls names from crt.sh without querying the target's DNS.

### 6. DNSSEC zone walk (`-t zonewalk` or `-z`)
Follows the NSEC chain to list every name in a signed zone. This (plus source plugins) is what dnsrecon adds over dnsenum [8].

### 7. Cache snooping (`-t snoop -n <resolver> -D domains.txt`)
Non-recursive (RD=0) queries to a resolver reveal which domains it has cached, i.e. what that organisation's users visit. DNSRecon is one of the tools that support it [9].

### 8. Other modes and switches
- `-t srv` SRV dictionary; `-t tld` same name across every TLD; `-t bing` / `-t yand` search-engine scraping.
- `-s` reverse-sweep SPF ranges; `-w` deep whois plus reverse sweep of the netranges found.
- Output: `--json f.json`, `--xml f.xml`, `-c f.csv`, `--db f.sqlite`. REST API since 1.6.0 [10].
- Tuning: `--threads`, `--lifetime` (query timeout), `--tcp`, `-f` (filter wildcard-resolving records), `--iw` (continue brute force despite wildcard), `--disable_check_recursion`, `--disable_check_bindversion`.
- `-n` name server; if none is given, the target's SOA server is used [11].

### 9. Realistic task: external attack-surface baseline for `acme.example`

```bash
dnsrecon -d acme.example -t crt --json 01-crt.json                 # passive
dnsrecon -d acme.example -a -s -w --json 02-std.json               # std + AXFR + SPF/whois sweeps
dnsrecon -d acme.example -t zonewalk --json 03-walk.json           # only if DNSSEC (NSEC) reported
dnsrecon -d acme.example -t brt -D words.txt -n <auth-NS> --threads 25 --json 04-brt.json
dnsrecon -r 198.51.100.0/24 -n <auth-NS> --json 05-ptr.json        # owned netblock
jq -r '.[] | select(.name) | .name' 0*.json | sort -u > hosts.txt  # dedupe → nmap / httpx
```

Triage: successful AXFR = reportable finding; CNAMEs to S3/Azure/Heroku/GitHub Pages = takeover candidates; RFC1918 IPs in public A records = internal leak; walkable NSEC = whole zone exposed.

The combined three-tool workflow from the first session:
1. Passive: `dnsrecon -d acme.example -t crt --json crt.json`.
2. Baseline: `dnsrecon -d acme.example -a -s --json std.json`.
3. Wildcard check if AXFR failed: `fierce --domain acme.example`.
4. Brute force: `dnsrecon -d acme.example -t brt -D subdomains-top1million-20000.txt --threads 20 --json brt.json`.
5. Expand IP space: `fierce --domain acme.example --subdomain-file found.txt --traverse 15`; `dnsrecon -r 198.51.100.0/24`.
6. Triage and report; feed in-scope hosts to nmap.

---

## Output and fields explained

- `[*]` info line, `[+]` finding, `[-]` negative result or error.
- **DNSSEC line**: whether the zone is signed, which decides whether `-t zonewalk` is worth trying.
- **SOA**: the primary master, the first AXFR candidate.
- **NS**: every listed server is tested separately for AXFR; secondaries are often left open while the primary is locked.
- **MX**: mail provider (here Google Workspace), useful context for phishing and SPF analysis.
- **TXT**: SPF includes and SaaS verification tokens, effectively a vendor inventory.
- **SRV**: services; a DNSRecon walkthrough showed SRV records revealing Cisco's VoIP, XMPP and videoconferencing [12]. `_ldap._tcp.dc._msdcs` and `_kerberos` reveal Active Directory.
- **"Has port 53 TCP Open"**: AXFR runs over TCP, so the tool checks TCP 53 first.
- **CNAME to a third party**: starting point for subdomain-takeover checks.
- **Record counts** (`[+] N Records Found`) summarise each mode.

---

## History and evolution

| When | What happened |
|---|---|
| Early 2007 | Carlos Perez writes a Ruby DNS recon script "to learn the language and about DNS" [1] |
| 2009 | Ruby dnsrecon v1.6, to be included in BackTrack 4 [2]; needed pNet-DNS and the ip gem, and Ruby 1.8.7 (not 1.9.1) [13] |
| Dec 2009 | Same logic as the Metasploit `dns_enum` auxiliary module ("Standard Record Lookup" of SOA, NS, MX...) [14] |
| 16 Dec 2010 | Python repository created, GPL-2.0 [1] |
| 2010s | Grows modes: SRV, rvl, snoop, zonewalk, tld, search-engine scraping; output to XML/CSV/SQLite/JSON |
| Jun 2021 | Last PyPI release, 0.10.1 [7] |
| 2024–2025 | 1.2.x / 1.3.x in Alpine and Debian [3][4] |
| 28 Feb 2026 | 1.6.0, introducing a REST API [10] |
| 2026 | Upstream 1.6.3; Debian 1.6.0-1 accepted July 2026 [3] |

### Concept history: the techniques behind each mode

| Mode | Standard / origin |
|---|---|
| std | RFC 1034/1035 (1987, Mockapetris) |
| axfr | RFC 1034 §4.3.5, formalised in RFC 5936 (2010); IXFR is RFC 1995 |
| srv | RFC 2782 (2000); Active Directory depends on it |
| rvl | `in-addr.arpa` (RFC 1035), `ip6.arpa` (RFC 3596) |
| zonewalk | NSEC (RFC 4033–4035, 2005); the exposure motivated NSEC3 (RFC 5155, 2008) |
| snoop | Luis Grangeia's 2004 paper on DNS cache snooping |
| crt | Certificate Transparency (RFC 6962, 2013) |
| bing / yand | Search-engine `site:` dorking, the successor of Google scraping |
| wildcard handling | RFC 1034 wildcards, clarified in RFC 4592 (2006) |

Field evolution: late 1990s–early 2000s AXFR was often open (`nslookup ls -d` was enough) → 2005–2010 AXFR locked down, so brute force plus reverse sweeps took over (fierce, dnsenum, dnsrecon) → 2010s DNSSEC NSEC walking, answered by NSEC3 → ~2015 onward passive sources (CT logs, passive DNS, search APIs) dominate with mass resolvers (amass, subfinder, puredns, dnsx). dnsrecon's mode list mirrors that history, ending with automation through an API.

### Why it is used today
- Broadest single-tool coverage, especially of configuration weaknesses that passive tools cannot test: open AXFR, walkable NSEC, cache snooping, recursion on authoritative servers, BIND version banners.
- Structured output (JSON, SQLite) and an API fit pipelines.
- Actively maintained, preinstalled on Kali, part of exam syllabi.
- Sits in the recon/OSINT layer: after scoping and passive collection, before nmap/httpx.

---

## How it works internally

- Built on **dnspython**; each mode is a function that issues queries and yields record dicts, which output writers serialise (JSON, XML, CSV, SQLite).
- **Name-server choice:** `-n` if given, otherwise the target's SOA server [11].
- **AXFR:** resolve SOA and NS → check TCP 53 on each NS → request AXFR from each separately.
- **Brute force:** first query random non-existent names to detect a wildcard; if one exists, prompt or follow `--iw` / `-f`; then resolve wordlist entries with a thread pool (`--threads`).
- **Reverse sweep:** expand range (first-last or CIDR) and send PTR queries in threads.
- **Zone walk:** request a non-existent name, read the NSEC record's "next owner name", step past it, and repeat until the chain loops back to the apex.
- **Cache snoop:** send queries with the RD (recursion desired) bit cleared; an answer means the record was cached.
- **Since 1.6:** a REST API layer (Debian control lists python3-slowapi for rate limiting and python3-stamina for retries [15]).
- Privileges: none special; ordinary UDP/TCP 53 client.

---

## Cross-platform comparison

| dnsrecon mode | Windows | macOS | Web/cloud |
|---|---|---|---|
| std | `Resolve-DnsName -Type ANY/MX/NS/TXT` | `dig` | DNSDumpster |
| axfr | `nslookup` → `ls -d dom`; `Resolve-DnsName -Type AXFR` | `dig axfr` | n/a (zone owners export through the provider API) |
| brt | PowerShell loop over a wordlist | bash loop over `dig` | Passive-DNS APIs replace it |
| rvl | `Resolve-DnsName -Type PTR` loop | `dig -x` loop | Shodan/Censys reverse data |
| snoop | `nslookup -norecurse` | `dig +norecurse` | n/a |
| zonewalk | No native tool | `ldns-walk` (Homebrew) | n/a |
| crt | Browser → crt.sh | `curl 'crt.sh/?q=%25.dom&output=json'` | crt.sh, Censys certificates |

General platform view (all three tools):

| Platform | Native tool / API | Zone transfer | Brute force | Reverse sweep | Notes |
|---|---|---|---|---|---|
| Linux | `dig`, `host`, `drill`; glibc `res_query` | `dig axfr` | Scripting | `dig -x` loop | The three tools wrap this via dnspython / Net::DNS |
| Windows | `nslookup`, `Resolve-DnsName` (DnsQuery_W API) | `ls -d` / `-Type AXFR` | PowerShell loops | Yes | AD-integrated DNS adds LDAP enumeration of internal zones (adidnsdump-style) |
| macOS | `dig`/`host`, `dscacheutil`; mDNSResponder | `dig axfr` | Scripting | Yes | Bonjour `dns-sd -B` enumerates local mDNS services (a different problem) |
| Android / iOS | No CLI; Termux, Network Analyzer, HE.NET tools | App-dependent | Limited | Limited | Usually done from a laptop |
| Web/cloud | CT logs, passive-DNS APIs, Route 53 / Cloud DNS APIs (own zones) | Not needed for owners | n/a | n/a | Defenders export their zone; recon tools give the outside view |

Same: every platform speaks RFC 1035, so the queries are identical. Different: only the Linux tools bundle the strategy (wordlists, wildcard filtering, per-NS testing, neighbour walking).

---

## Alternatives

- **Linux, manual:** `dig`, `host`, `drill`.
- **nmap NSE:** `dns-brute`, `dns-zone-transfer`, `dns-nsec-enum`, `dns-nsec3-enum`, `dns-cache-snoop`, `dns-srv-enum`.
- **Modern subdomain discovery:** OWASP Amass, subfinder (passive), puredns / massdns (fast brute force), dnsx (Trickest: a fast resolver and prober for a known list, while dnsrecon covers more techniques [8]), shuffledns, gobuster dns.
- **DNSSEC walking:** ldns-walk, nsec3walker (NSEC3 hash cracking).
- **Frameworks:** Metasploit `auxiliary/gather/enum_dns` (dnsrecon's sibling), recon-ng, SpiderFoot, theHarvester.
- **Siblings:** dnsenum (fixed pipeline, IP-block mapping), fierce (neighbour PTR walking).
- **Windows:** `Resolve-DnsName`, `nslookup`.
- **Web:** crt.sh, DNSDumpster, SecurityTrails, VirusTotal passive DNS, Shodan/Censys.
- **Defensive / EASM:** Censys ASM, Palo Alto Xpanse, Microsoft Defender EASM.

---

## Role: Penetration Tester / Red Teamer
- **Why:** DNS defines the external attack surface and reachable scope; dnsrecon is the default DNS step of external recon.
- **Day to day:** std + axfr + brt to JSON, then fierce for neighbours, then nmap. Internally, point `-n` at the domain controller.
- **Expert knowledge:** test AXFR on every NS (a forgotten secondary is common); brute-force against the authoritative NS, not 8.8.8.8; use `-t srv` to map AD (`_ldap._tcp.dc._msdcs`, `_kerberos`) and VoIP (`_sip`); compare internal and external views for split-horizon leaks; JSON goes straight into the report.

## Role: Bug Bounty Hunter
- **Why:** forgotten subdomains are where findings come from.
- **Day to day:** crt first (passive), brt with custom wordlists, filter CNAMEs to S3/Azure/Heroku/GitHub Pages for takeovers.
- **Expert knowledge:** wordlists built from the target's naming conventions (`app-prod-eu1`); scheduled re-runs and diffs, because new hosts appear; respect program rate limits.

## Role: DNS / Network Engineer
- **Why:** self-audit of your own zones.
- **Day to day:** after each change: AXFR must fail on all NS, `zonewalk` must not dump the zone, no recursion on authoritative servers, no BIND version banner; `-r` to check PTR coverage.
- **Expert knowledge:** fixes are `allow-transfer` + TSIG, NSEC3 or online signing ("white lies"), hidden version strings, recursion off on authoritative servers (prevents cache snooping and amplification), no RFC1918 addresses in public zones, stale NS records expose hidden primaries.

## Role: Cybersecurity Analyst (Blue Team / SOC)
- **Why:** recognise dnsrecon hitting you.
- **Day to day:** detections for NXDOMAIN bursts from one source, AXFR attempts from non-secondaries, high-volume PTR sweeps.
- **Expert knowledge:** attackers often brute-force through public resolvers, so authoritative logs show Google/Cloudflare IPs, not the attacker; authoritative logging (dnstap, Route 53 query logs) is noisy; RD=0 queries against your resolver hint at cache snooping.

## Role: Attack-Surface Management / Threat Intel Analyst
- **Why:** continuous inventory of external DNS assets, shadow IT, takeover risks.
- **Day to day:** scheduled JSON/SQLite runs or the 1.6 REST API feeding an asset database, diffed against the previous run.
- **Expert knowledge:** combine with passive-DNS history; keep ownership attribution current through SOA, NS and whois (`-w`).

## Role: CTF Player / Cert Candidate (OSCP, CPTS, eJPT, CEH)
- **Why:** port 53 open on an exam box almost always means "try AXFR against the box itself".
- **Day to day:** `dnsrecon -d box.htb -n <box-IP> -t axfr`; the zone holds the vhost names you need.
- **Expert knowledge:** always specify the name server for lab domains (they are internal, the default resolver fails); add names to `/etc/hosts` immediately.

## Role: Cloud / DevOps Engineer
- **Why:** IaC churn (resource deleted, DNS record left) creates dangling CNAMEs.
- **Day to day:** brt/std against own zones in CI; flag CNAMEs whose targets return NXDOMAIN or NoSuchBucket-type errors.
- **Expert knowledge:** fix at the pipeline level: DNS records live in the same Terraform stack as the resource; prefer alias records over CNAMEs.

## Role: Tool Developer (Python / Perl)
- **Why:** a model of a mature recon tool.
- **Lessons:** dnspython-based modes, thread pools, wildcard detection, pluggable output writers, and since 1.6 a REST layer with rate limiting and retries. Shared design problems: wildcard handling, resolver rotation, rate limiting, UDP truncation and TCP fallback, EDNS0 buffer sizes. Contrast with dnsenum (Perl ithreads + Net::DNS) and fierce (minimal Python port).

---

## Related topics, curricula and certifications

- **Subjects:** DNS protocol (RFC 1034/1035), DNSSEC (NSEC/NSEC3), OSINT and reconnaissance, attack-surface management, subdomain takeover, Active Directory enumeration through SRV records, DNS hardening.
- **Certifications:** OSCP (PEN-200 information gathering), HTB CPTS, eJPT/eCPPT, CEH (footprinting), PNPT, CompTIA PenTest+ (recon), GPEN/SANS SEC560; defensive: SANS SEC503/SEC511 (DNS detection), DNS-OARC / BIND training.
- **Practice:** `zonetransfer.me`, HTB/THM boxes with port 53, your own BIND lab with `allow-transfer { any; };` to see both sides.

---

## Follow-up Q&A

### Q: Which roles care about dnsrecon/dnsenum/fierce? (role pick)
Suggested and selected (all): Penetration Tester / Red Teamer; Bug Bounty Hunter; DNS / Network Engineer; Cybersecurity Analyst (Blue Team / SOC); Attack-Surface Management / Threat Intel Analyst; CTF Player / Cert Candidate; Cloud / DevOps Engineer (non-obvious: dangling CNAMEs from IaC churn); Tool Developer (non-obvious: the same technique implemented three times, Perl → Python).

### Q: Why does every AI present dnsrecon, dnsenum and fierce as a single entity when they are different tools by different creators in different languages?
**Mechanism:**
1. **Training data groups them.** Tutorials, cheat sheets, books and course notes teach the three in one chapter: InfoSec Institute has a section titled "Fierce, DNSenum and DNSrecon" [16]; the Kali Network Scanning Cookbook introduces dnsenum as "similar to dnsrecon" [17]; comparison blogs put them in one feature table [18]. A language model learns co-occurrence, so one name makes the other two statistically likely.
2. **Curricula group by job, not author.** CEH, OSCP, CPTS, Kali's menus and pentest methodologies are organised by phase (information gathering → DNS analysis). For the basic job (records, AXFR, brute force) the three really are interchangeable.
3. **Their descriptions overlap because they borrowed from each other.** dnsenum's tagline is to "discover non-contiguous IP blocks" [19]; fierce's is "locating non-contiguous IP space" [20], fierce's original 2007 idea. Cheat sheets even run dnsenum with `fierce-hostlist.txt` [21].
4. **Answers optimise for "do the task",** so assistants list every tool that fits rather than their differences.

**Where grouping is valid vs misleading:**

| Valid to group | Misleading to group |
|---|---|
| Same layer (DNS, port 53) | Origin: RSnake 2007 (Perl); Waeytens/tixxDZ (Perl); Perez 2007 Ruby → 2010 Python |
| Same recon phase | Capabilities: only dnsrecon does NSEC walking, cache snooping, CT, REST API; only fierce walks neighbour IPs by default; only dnsenum expands whois netranges |
| Same basic tests (AXFR, brute force, PTR) | Health: dnsrecon actively released; dnsenum survives as a fork; fierce upstream slowed |
| Same defensive fixes (lock AXFR, NSEC3, no recursion) | Internals: Perl ithreads + Net::DNS vs dnspython; different speed, portability, wildcard handling |

Better mental model: three implementations of one methodology, like nmap vs masscan vs RustScan.

**Certainty:** certain: the co-occurrence in teaching material, the shared "non-contiguous" phrasing, the different authors and languages. Inferred: that training-data co-occurrence is the main cause of AI lumping (consistent with how language models work; no specific training set can be inspected). Tip: ask "compare X vs Y vs Z on origin, internals and unique features" to get them separated.

### Q: Re-explain everything per tool, all roles
Done: this note is the dnsrecon section; see `notes/tools/dnsenum.md` and `notes/tools/fierce.md`.

### Picking between the three

| Need | Use |
|---|---|
| Most techniques, JSON, DNSSEC, CT, API | **dnsrecon** |
| One command mapping the IP blocks a domain owns | **dnsenum** |
| Hosts next to known ones; internal PTR sweeps | **fierce** |

---

## Sources

[1] darkoperator/dnsrecon, project record and README quote ("a Python port of a Ruby script that I wrote to learn the language and about DNS in early 2007"), Ecosyste.ms. [Online]. Available: https://awesome.ecosyste.ms/projects/github.com%2Fdarkoperator%2Fdnsrecon (accessed Nov. 17, 2026).

[2] C. Perez, "DNS Recon Tool written in Ruby," darkoperator.com, Apr. 3, 2009. [Online]. Available: https://www.darkoperator.com/blog/2009/4/3/dns-recon-tool-written-in-ruby.html (accessed Nov. 17, 2026).

[3] Debian Package Tracker, "dnsrecon." [Online]. Available: https://tracker.debian.org/pkg/dnsrecon (accessed Nov. 17, 2026).

[4] Alpine Linux packages, "dnsrecon 1.3.1-r1 (v3.22 community)." [Online]. Available: https://pkgs.alpinelinux.org/package/v3.22/community/x86/dnsrecon (accessed Nov. 17, 2026).

[5] Gentoo/Pentoo overlay, "net-analyzer/dnsrecon." [Online]. Available: https://gpo.zugaina.org/net-analyzer/dnsrecon (accessed Nov. 17, 2026).

[6] FreshPorts, "dns/dnsrecon." [Online]. Available: https://freshports.org/dns/dnsrecon/ (accessed Nov. 17, 2026).

[7] Snyk Advisor, "dnsrecon (PyPI)." [Online]. Available: https://snyk.io/advisor/python/dnsrecon (accessed Nov. 17, 2026).

[8] Trickest, "dnsrecon," updated Jul. 14, 2026. [Online]. Available: https://trickest.com/tools/dnsrecon (accessed Nov. 17, 2026).

[9] "What is DNS Reconnaissance and its Tools," Medium (zerosuniverse). [Online]. Available: https://medium.com/zerosuniverse/what-is-dns-reconnaissance-and-its-tools-61fd46bc16b9 (accessed Nov. 17, 2026).

[10] "DNSRecon," Cyber Research Wiki. [Online]. Available: https://danyel-ii.github.io/cyber-research-wiki/tools/dnsrecon/ (accessed Nov. 17, 2026).

[11] "dnsrecon(1)," Debian buster manual pages. [Online]. Available: https://manpages.debian.org/buster/dnsrecon/dnsrecon.1.en.html (accessed Nov. 17, 2026).

[12] "DNS Reconnaissance – DNSRecon," Penetration Testing Lab. [Online]. Available: https://pentestlab.blog/page/203/ (accessed Nov. 17, 2026).

[13] "Dnsrecon," aldeid wiki. [Online]. Available: https://www.aldeid.com/wiki/Dnsrecon (accessed Nov. 17, 2026).

[14] C. Perez, "DNS Enumeration with Metasploit," darkoperator.com, Dec. 11, 2009. [Online]. Available: https://www.darkoperator.com/blog/2009/12/11/enumeration-thru-dns-and-metasploit.html (accessed Nov. 17, 2026).

[15] Debian, "dnsrecon 1.6.0-1 control file." [Online]. Available: https://tracker.debian.org/media/packages/d/dnsrecon/control-1.6.0-1 (accessed Nov. 17, 2026).

[16] InfoSec Institute, "DNS enumeration techniques in Linux." [Online]. Available: https://infosecinstitute.com/resources/penetration-testing/dns-enumeration-techniques-in-linux/ (accessed Nov. 17, 2026).

[17] M. Hixon, *Kali Linux Network Scanning Cookbook*, 2nd ed., Packt, 2017, ch. 2 "Enumerating DNS using the dnsenum command." [Online]. Available: https://subscription.packtpub.com/book/cloud_&_networking/9781787287907/2/ch02lvl1sec21/introduction (accessed Nov. 17, 2026).

[18] "Which command-line tool can be used for DNS enumeration," Ultimate Systems Blog, May 2025. [Online]. Available: https://blog.usro.net/2025/05/which-command-line-tool-can-be-used-for-dns-enumeration/ (accessed Nov. 17, 2026).

[19] "dnsenum(1)," Debian bullseye manual pages. [Online]. Available: https://dyn.manpages.debian.org/bullseye/dnsenum/dnsenum.1 (accessed Nov. 17, 2026).

[20] mschwager/fierce, GitHub. [Online]. Available: https://github.com/mschwager/fierce (accessed Nov. 17, 2026).

[21] "DNS Enumeration (Port 53)," vipa0z notes. [Online]. Available: https://vipa0z.github.io/02-internal-networks/02-service-enumeration/01-dns.html (accessed Nov. 17, 2026).

Notes on certainty: sample outputs are format-faithful illustrations, not captured live. RFC numbers, the Grangeia paper, cross-platform commands and role practices come from general knowledge and were not re-verified against primary sources in this session.
