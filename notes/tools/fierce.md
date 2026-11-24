---
tool: fierce
date: 2026-11-24
domains: [Cybersecurity, Offensive Security / VAPT, DNS, Network Infrastructure, OSINT, Attack-Surface Management]
roles: [Penetration Tester / Red Teamer, Bug Bounty Hunter, DNS / Network Engineer, Cybersecurity Analyst (Blue Team / SOC), Attack-Surface Management / Threat Intel Analyst, CTF Player / Cert Candidate, Cloud / DevOps Engineer, Tool Developer]
tags: [dns, recon, enumeration, axfr, zone-transfer, wildcard, subdomain, brute-force, reverse-dns, ptr, non-contiguous-ip, kali, python, perl, ha.ckers.org]
related: [dnsrecon, dnsenum]
---

# fierce

## Summary

`fierce` is a lightweight DNS reconnaissance tool for locating **non-contiguous IP space** and hostnames for a domain [1]. Robert "RSnake" Hansen wrote the original Perl `fierce.pl` at ha.ckers.org (released February 2007) [2][3]; today's version is Matt Schwager's (mschwager) Python 3 port, GPL-3.0 [1]. One run checks NS and SOA, tries a zone transfer, tests for wildcard DNS, brute-forces subdomains, and then looks up the PTR records of the IPs **next to** every hit, revealing hosts no wordlist contains.

- **Problem it solves:** a company's hosts are scattered across unrelated netblocks; scanning "their /24" misses most of them. Fierce pivots through reverse DNS to find them.
- **Position:** a fast second opinion after dnsrecon; an internal PTR sweeper (`--range`).
- **Siblings:** studied together with `dnsrecon` and `dnsenum`; see the Q&A on why they get lumped together.

| | dnsrecon | dnsenum | fierce |
|---|---|---|---|
| Language | Python 3 (Ruby origin) | Perl (ithreads) | Python 3 (Perl origin) |
| Strength | Widest technique set, structured output, API | One fixed pipeline, IP-block mapping | Neighbour PTR walking |
| Status (Nov 2026) | Active (1.6.x) | Maintained fork (dnsenum2) | Python port; upstream slowed |

---

## Installation and availability

| Platform | How |
|---|---|
| Kali | Preinstalled (Python version) |
| Debian / Ubuntu / Mint | `sudo apt install fierce` (1.6.0 in trixie; the package also ships the original `scripts/fierce.pl`) [4][5] |
| Any OS with Python 3 | `python -m pip install fierce` [1] |
| From source | `git clone https://github.com/mschwager/fierce.git && cd fierce && python -m pip install dnspython==1.16.0 && python fierce/fierce.py -h` (note the old pinned dnspython) [1] |
| Android | Termux + pip |

---

## What one run does

1. Look up NS records.
2. Look up SOA.
3. Attempt a zone transfer against the name servers; on success print the zone and stop.
4. Wildcard check using a random subdomain.
5. Brute force subdomains (built-in list, `--subdomains` or `--subdomain-file`).
6. For each hit, PTR-look-up nearby IPs (`--traverse N`, default ±5) and print them as **Nearby**; `--wide` does the whole /24.

---

## Usage and commands (with sample outputs)

Sample outputs are format-faithful illustrations (`zonetransfer.me` is DigiNinja's open practice domain; `example.com` and documentation IPs are placeholders).

### 1. Basic

```
$ fierce --domain example.com
NS: ns1.example.com. ns2.example.com.
SOA: ns1.example.com. (203.0.113.53)
Zone: failure
Wildcard: failure
Found: admin.example.com. (203.0.113.60)
Nearby:
{'203.0.113.55': 'vpn.example.com.',
 '203.0.113.58': 'git.example.com.',
 '203.0.113.61': 'jenkins.example.com.'}
Found: mail.example.com. (203.0.113.25)
Nearby:
{'203.0.113.24': 'smtp2.example.com.'}
```

### 2. AXFR success

```
$ fierce --domain zonetransfer.me
NS: nsztm1.digi.ninja. nsztm2.digi.ninja.
SOA: nsztm1.digi.ninja. (81.4.108.41)
Zone: success
{<DNS name @>: '@ 7200 IN SOA nsztm1.digi.ninja. robin.digi.ninja. ...',
 <DNS name www>: 'www 7200 IN A 5.196.105.14', ...}
```

### 3–9. README examples [1]

| Command | Purpose |
|---|---|
| `fierce --domain google.com --subdomains accounts admin ads` | Check specific subdomains only |
| `fierce --domain facebook.com --subdomains admin --traverse 10` | Wider neighbour walk (±10) |
| `fierce --domain facebook.com --subdomains admin --search fb.com fb.net` | Keep only PTRs in related domains |
| `fierce --domain stackoverflow.com --subdomains mail --connect` | Try HTTP on each hit |
| `fierce --domain facebook.com --wide` | Scan the whole /24 around each hit |
| `fierce --domain zonetransfer.me` | Zone transfer test |
| `fierce --dns-servers 10.0.0.1 --range 10.0.0.0/24` | Internal range reverse sweep |

Other flags: `--subdomain-file`, `--dns-file`, `--tcp`, `--delay` (seconds between lookups). Save output by redirecting stdout (`> output.txt`).

### 10. Realistic task: find hidden hosts next to known ones

```bash
fierce --domain acme.example --subdomain-file top5000.txt --traverse 15 \
       --search acme.example acme-corp.net --delay 0.2 > fierce.txt
grep -E "Found|'" fierce.txt
```

The neighbour walk typically finds the unglamorous hosts (`jenkins`, `backup`, `vpn-old`) sitting next to the well-known `www` and `mail`.

---

## Output and fields explained

- **NS / SOA**: name servers and primary master (with IP), the AXFR targets.
- **Zone: failure / success**: AXFR refused / allowed. On success the zone is printed as a Python dict of record objects and the run ends.
- **Wildcard: failure / success**: whether a random name resolves. `failure` = no wildcard, so Found lines are trustworthy; `success` = every guess resolves, filter results.
- **Found: name (IP)**: a brute-force hit.
- **Nearby: {IP: PTR}**: neighbouring IPs and their reverse names, fierce's signature output; names here were not in the wordlist.

---

## History and evolution

| When | What happened |
|---|---|
| 2006 | `fierce.pl` written ("Copywrite 2006,2007 - By RSnake at http://ha.ckers.org/fierce/") [6] |
| 20 Feb 2007 | Public release announced: born out of frustration after a web application security audit [2]; written by RSnake with input from id, Vacuum and Robert E Lee [3] |
| 24 Mar 2007 | v0.9.9 Beta; threading and additions by IceShaman [5][7] |
| Dec 2007 | Described as a Perl script that scans domains in a few minutes using several tactics [6] |
| ~2009 | Perl "Fierce 2.0" by Joshua "Jabra" Abraham (from memory, unconfirmed) |
| 2016–2019 | mschwager's Python 3 port, "simply a conversion to Python 3 to simplify and modernize the codebase," GPL-3.0 [1][8]; PyPI releases 1.1 → 1.3 → 1.5 [9][10] |
| ~2024 | mschwager maintenance ends per a fork's README; forks such as fierce3 continue [11] |
| 2025–2026 | Debian 1.6.0-1 (forky/sid/trixie), bundling the original Perl script [5] |

### Concept history
- **Non-contiguous IP space:** organisations' hosts live in several providers and blocks. Pivot through `in-addr.arpa` reverse DNS (RFC 1035): once one host is found, its neighbours' PTRs probably belong to the same organisation.
- **Wildcard check:** RFC 1034 wildcard behaviour (clarified in RFC 4592, 2006) was a common source of false positives, so fierce checks first.
- **Influence:** dnsenum adopted the same "non-contiguous IP blocks" goal [12]; SecLists ships `fierce-hostlist.txt`, which cheat sheets use even with dnsenum [13]. Fierce's ideas outlived its original code.

### Why it is used today
Small codebase, readable output, one distinctive technique (neighbour PTR walking) the others don't run by default; quick second opinion after dnsrecon; handy internal PTR sweeper.

---

## How it works internally

- Python 3 on **dnspython** (pinned 1.16.0 for source installs) [1].
- Resolver: system resolver unless `--dns-servers` / `--dns-file`; `--tcp` forces TCP.
- AXFR attempted against each NS; success short-circuits the run.
- Wildcard: resolve a random label; if it resolves, record the wildcard IP.
- Brute force and neighbour PTR lookups run **sequentially**: "Provide multiprocessing capabilities" is still a README TODO [14]. `--delay` adds pauses.
- Neighbour walk: for each found IP, generate ±N addresses (`--traverse`) or the /24 (`--wide`), PTR each, optionally keep only names matching `--search` domains.
- `--connect` makes an HTTP request to each found host.
- Original Perl (`fierce.pl`) did the same with Net::DNS and IceShaman's threads [7].
- No root needed.

---

## Cross-platform comparison

| fierce step | Windows | macOS | Web/cloud |
|---|---|---|---|
| NS / SOA / AXFR | `nslookup` (`set type=SOA`, `ls -d`) | `dig` | DNSDumpster |
| Wildcard check | `Resolve-DnsName rand123.dom` | `dig rand123.dom` | n/a |
| Brute force | PowerShell loop | bash loop | Passive DNS |
| Neighbour PTR walk | `Resolve-DnsName -Type PTR` over ±N IPs | `dig -x` loop / `nmap -sL` | Shodan/Censys reverse data, bgp.he.net |
| `--range` internal | `nslookup` loop against the DC | `nmap -sL --dns-servers` | n/a |

General platform view: same RFC 1035 protocol everywhere; Linux tools bundle the strategy; Windows has `nslookup`/`Resolve-DnsName` (plus AD LDAP zone enumeration internally); macOS `dig`/mDNSResponder; Android/iOS rely on apps or Termux; web/cloud uses CT, passive DNS and provider APIs.

---

## Alternatives

dnsrecon `-r` (bulk PTR), `nmap -sL <range>` (list scan: reverse-resolves every IP without probing hosts), dnsx `-ptr`, hakrevdns, prips + massdns (fast PTR sweeps), the original `fierce.pl` (still in Debian), dnsenum (full /24 sweeps + whois), Amass, subfinder.

---

## Role: Penetration Tester / Red Teamer
- **Why:** finds hosts outside the obvious set.
- **Day to day:** after the main enumeration, `--traverse` on each hit; internally `--dns-servers <DC> --range 10.x.x.0/24` maps an AD network through PTRs without port scanning (quiet).
- **Expert knowledge:** use `--search` to stay inside the organisation's PTR namespace; `--delay` for stealth.

## Role: Bug Bounty Hunter
- **Why:** the neighbour walk finds forgotten infrastructure (staging, CI, admin panels) that wordlists miss.
- **Day to day:** run on each hit from passive tools, with `--connect` for a quick HTTP check.
- **Expert knowledge:** skip neighbour walking on shared cloud IPs (other tenants are out of scope).

## Role: DNS / Network Engineer
- **Why:** shows how much your PTR records leak: descriptive reverse names (`jenkins.corp…`) are an attacker's map.
- **Expert knowledge:** generic PTRs on public ranges; internal hosts named without revealing their function; AXFR closed (fierce prints it plainly).

## Role: Cybersecurity Analyst (Blue Team / SOC)
- **Signature:** small clusters of sequential PTR lookups (±5 around each hit) interleaved with brute force, distinct from dnsenum's full /24 sweeps.
- **Expert knowledge:** alert on sequential `in-addr.arpa` queries from one client.

## Role: Attack-Surface Management / Threat Intel Analyst
- **Why:** cheap IP attribution: if an adjacent PTR carries the organisation's domain, the block is probably theirs.
- **Expert knowledge:** confirm with RDAP and ASN data before adding to the inventory.

## Role: CTF Player / Cert Candidate (OSCP, CPTS, eJPT, CEH)
- **Day to day:** quick AXFR + wildcard check: `fierce --domain box.htb --dns-servers <IP>`.
- **Expert knowledge:** old notes use Perl syntax (`fierce -dns example.com -wordlist wordlist.txt` [15]); the Python version needs `--domain` / `--subdomain-file`.

## Role: Cloud / DevOps Engineer
- **Why:** cloud default PTRs (`ec2-…compute.amazonaws.com`) defeat neighbour walking, but custom PTRs set for mail deliverability put your names back in.
- **Expert knowledge:** set reverse names deliberately.

## Role: Tool Developer (Python / Perl)
- **Lessons:** a minimal, readable dnspython tool (Debian package: about 942 lines of Python plus the 510-line Perl original [5]); a good base to fork; the open multiprocessing TODO is an obvious first contribution; the Perl → Python port shows how CLI syntax breaks old tutorials.

---

## Related topics, curricula and certifications

Reverse DNS and IP-space mapping, wildcard DNS, internal network recon, web-security history (ha.ckers.org era). Appears in CEH (footprinting), OSCP and HTB CPTS DNS sections [16], CompTIA PenTest+ (recon), InfoSec Institute's DNS enumeration guide [15]. Practice: `zonetransfer.me`, HTB/THM port-53 boxes, a home BIND lab with descriptive PTRs.

---

## Follow-up Q&A

### Q: Which roles care about dnsrecon/dnsenum/fierce? (role pick)
All eight selected: Penetration Tester / Red Teamer; Bug Bounty Hunter; DNS / Network Engineer; Cybersecurity Analyst (Blue Team / SOC); Attack-Surface Management / Threat Intel; CTF Player / Cert Candidate; Cloud / DevOps Engineer (non-obvious); Tool Developer (non-obvious).

### Q: Why does every AI present dnsrecon, dnsenum and fierce as one entity?
**Mechanism:** (1) training material teaches them together (InfoSec Institute's "Fierce, DNSenum and DNSrecon" section [15], comparison tables, cookbooks); models learn co-occurrence. (2) Curricula group by job (information gathering → DNS analysis). (3) Descriptions overlap because ideas were borrowed: fierce's "locating non-contiguous IP space" [1] became dnsenum's "discover non-contiguous IP blocks" [12]; cheat sheets run dnsenum with `fierce-hostlist.txt` [13]. (4) Answers optimise for doing the task.

**Valid vs misleading:**

| Valid to group | Misleading to group |
|---|---|
| Same layer (DNS, port 53) | Origin: RSnake 2007 (Perl); Waeytens/tixxDZ (Perl); Perez 2007 Ruby → 2010 Python |
| Same recon phase | Capabilities: fierce alone walks neighbours by default; dnsrecon alone does NSEC walking, snooping, CT, API; dnsenum alone expands whois netranges |
| Same basic tests | Health: dnsrecon active; dnsenum a fork; fierce upstream slowed |
| Same defensive fixes | Internals: dnspython (sequential) vs Perl ithreads |

Mental model: three implementations of one methodology. **Certain:** co-occurrence in teaching material, shared phrasing, different authors/languages. **Inferred:** that this is the main cause of AI lumping.

### Q: Re-explain per tool, all roles
This note is the fierce section; see `notes/tools/dnsrecon.md` and `notes/tools/dnsenum.md`.

### Picking between the three

| Need | Use |
|---|---|
| Most techniques, JSON, DNSSEC, CT, API | **dnsrecon** |
| One command mapping the IP blocks a domain owns | **dnsenum** |
| Hosts next to known ones; internal PTR sweeps | **fierce** |

### Note on the earlier library record
The previous `data/tools/fierce.json` gave the year as 2006 and called fierce "the first tool to combine AXFR with brute force". The script's own header says copyright 2006–2007 and the public release was 20 February 2007 [2][6]; the "first tool" claim could not be verified, so the updated record drops it.

---

## Sources

[1] mschwager/fierce, GitHub. [Online]. Available: https://github.com/mschwager/fierce (accessed Nov. 17, 2026).

[2] "Fierce Domain Scanner Released – Domain Reconnaissance Tool," Darknet, Feb. 20, 2007. [Online]. Available: https://www.darknet.org.uk/2007/02/fierce-domain-scanner-released-domain-reconnaissance-tool/ (accessed Nov. 17, 2026).

[3] Darknet, fierce.pl usage and credits. [Online]. Available: https://www.darknet.org.uk/?p=442 (accessed Nov. 17, 2026).

[4] Linux Mint Community, "fierce." [Online]. Available: https://community.linuxmint.com/software/view/fierce (accessed Nov. 17, 2026).

[5] Debian sources, "fierce 1.6.0-1 scripts/fierce.pl." [Online]. Available: https://sources.debian.org/src/fierce/1.6.0-1/scripts/fierce.pl (accessed Nov. 17, 2026).

[6] "FierceDNS for DNS enumeration," carnal0wnage, Dec. 25, 2007. [Online]. Available: https://blog.carnal0wnage.com/2007/12/fiercedns-for-dns-enumeration.html (accessed Nov. 17, 2026).

[7] fierce.pl v0.9.9 source (gist). [Online]. Available: https://gist.github.com/Lh4cKg/3e14280b7c6b8db8e230 (accessed Nov. 17, 2026).

[8] mschwager/fierce project record, Ecosyste.ms. [Online]. Available: https://awesome.ecosyste.ms/projects/github.com%2Fmschwager%2Ffierce (accessed Nov. 17, 2026).

[9] PyPI metadata mirror, "fierce." [Online]. Available: https://pypi.tcis.de/data/web/json/fierce (accessed Nov. 17, 2026).

[10] kandi, "fierce (Version 1.5.0)." [Online]. Available: https://kandi.openweaver.com/python/mschwager/fierce (accessed Nov. 17, 2026).

[11] meese-enterprises/fierce3, GitHub mirror. [Online]. Available: https://gh.r-mj.com/meese-enterprises/fierce3 (accessed Nov. 17, 2026).

[12] "dnsenum(1)," Debian bullseye manual pages. [Online]. Available: https://dyn.manpages.debian.org/bullseye/dnsenum/dnsenum.1 (accessed Nov. 17, 2026).

[13] "DNS Enumeration (Port 53)," vipa0z notes. [Online]. Available: https://vipa0z.github.io/02-internal-networks/02-service-enumeration/01-dns.html (accessed Nov. 17, 2026).

[14] DKChain/fierce (README TODO), GitHub fork. [Online]. Available: https://github.com/DKChain/fierce (accessed Nov. 17, 2026).

[15] InfoSec Institute, "DNS enumeration techniques in Linux." [Online]. Available: https://infosecinstitute.com/resources/penetration-testing/dns-enumeration-techniques-in-linux/ (accessed Nov. 17, 2026).

[16] "Subdomain Enumeration," CPTS prep notes. [Online]. Available: https://kabaneridev.gitbook.io/pentesting-notes/certification-preparation/cpts-prep/web-enumeration/subdomain-enumeration (accessed Nov. 17, 2026).

Notes on certainty: Jabra's Fierce 2.0 is from memory and unconfirmed. Default traverse width (±5) and internal behaviour are from the tool's help/source as remembered, not re-fetched this session. Sample outputs are format-faithful illustrations.
