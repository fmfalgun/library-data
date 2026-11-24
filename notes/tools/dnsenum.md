---
tool: dnsenum
date: 2026-11-24
domains: [Cybersecurity, Offensive Security / VAPT, DNS, Network Infrastructure, OSINT, Attack-Surface Management]
roles: [Penetration Tester / Red Teamer, Bug Bounty Hunter, DNS / Network Engineer, Cybersecurity Analyst (Blue Team / SOC), Attack-Surface Management / Threat Intel Analyst, CTF Player / Cert Candidate, Cloud / DevOps Engineer, Tool Developer]
tags: [dns, recon, enumeration, axfr, zone-transfer, subdomain, brute-force, whois, netrange, reverse-dns, google-scraping, kali, perl]
related: [dnsrecon, fierce]
---

# dnsenum

## Summary

`dnsenum` is a multithreaded Perl script by Filip Waeytens and tixxDZ that runs one fixed DNS enumeration pipeline per domain: A/NS/MX records, zone transfer attempts, search-engine scraping, wordlist brute force (with recursion), class C netrange expansion with whois, reverse lookups across those ranges, and a final list of IP blocks. Its stated aim is to gather as much information as possible about a domain and to discover **non-contiguous IP blocks** [1][2]. The maintained line today is the **dnsenum2** fork (SparrowOchon), shipped in Kali, Debian and Ubuntu as `dnsenum` [3].

- **Problem it solves:** one command maps which IP blocks a domain's hosts live in, including blocks in unrelated providers' space.
- **Position:** recon phase, after passive collection, before port scanning; the "fire and forget" option among its siblings.
- **Siblings:** studied together with `dnsrecon` and `fierce`; see the Q&A on why they get lumped together.

| | dnsrecon | dnsenum | fierce |
|---|---|---|---|
| Language | Python 3 (Ruby origin) | Perl (ithreads) | Python 3 (Perl origin) |
| Strength | Widest technique set, structured output, API | One fixed pipeline, IP-block mapping | Neighbour PTR walking |
| Status (Nov 2026) | Active (1.6.x) | Maintained fork (dnsenum2) | Python port; upstream slowed |

---

## Installation and availability

| Platform | How |
|---|---|
| Kali | Preinstalled; Kali's tool page shows `dnsenum VERSION:1.3.1` [4] |
| Debian / Ubuntu / Mint | `sudo apt install dnsenum` (1.3.2 in trixie/plucky) [5][6]; Mint's package points to SparrowOchon/dnsenum2 [7] |
| Other Linux / macOS | It's a Perl script: install modules via cpan or distro. Required: Net::DNS, Net::IP, Net::Netmask; optional: Net::Whois::IP, HTML::Parser, WWW::Mechanize; perl must be compiled with ithreads (threads, threads::shared) [2]. Debian also depends on libstring-random-perl and libxml-writer-perl [4] |
| Windows | Use WSL; native threaded Perl is fragile |
| Source | Original `github.com/fwaeytens/dnsenum`; maintained fork `github.com/SparrowOchon/dnsenum2` (`make install` creates a callable `dnsenum`, wordlist at `/usr/share/dnsenum/dns.txt`) [5] |

---

## The pipeline (what one run does)

From the README and man page [1][8][9]:
1. Get the host's address (A record).
2. Get the name servers (threaded).
3. Get the MX records (threaded).
4. Perform AXFR queries on the name servers (and, historically, get the BIND version; threaded).
5. Get extra names and subdomains via Google scraping (query `-www site:domain`).
6. Brute force subdomains from a file (required), optionally recursing into found subdomains that have NS records.
7. Calculate class C netranges and run whois queries on them.
8. Perform reverse lookups on those netranges (class C or whois netranges; threaded).
9. Write the IP blocks to `domain_ips.txt`.

Supported operations in one line from the man page: nslookup, zonetransfer, google scraping, domain brute force (with recursion), whois ip and reverse lookups [9].

---

## Usage and commands (with sample outputs)

Sample output is a format-faithful illustration using `zonetransfer.me` (DigiNinja's deliberately open practice domain); live records change.

### 1. Basic run

```
$ dnsenum zonetransfer.me
dnsenum VERSION:1.3.1

-----   zonetransfer.me   -----

Host's addresses:
__________________
zonetransfer.me.                         7200     IN    A        5.196.105.14

Name Servers:
______________
nsztm1.digi.ninja.                       7200     IN    A        81.4.108.41
nsztm2.digi.ninja.                       7200     IN    A        34.225.33.2

Mail (MX) Servers:
___________________
ASPMX.L.GOOGLE.COM.                      300      IN    A        142.250.x.x

Trying Zone Transfers and getting Bind Versions:
_________________________________________________

Trying Zone Transfer for zonetransfer.me on nsztm1.digi.ninja ...
zonetransfer.me.                         7200     IN    SOA      (
zonetransfer.me.                         7200     IN    NS       nsztm1.digi.ninja.
www.zonetransfer.me.                     7200     IN    A        5.196.105.14
...
Brute forcing with /usr/share/dnsenum/dns.txt:
_______________________________________________
...
zonetransfer.me class C netranges:
___________________________________
 5.196.105.0/24

Performing reverse lookup on 256 ip addresses:
...
zonetransfer.me ip blocks:
__________________________
 5.196.105.14/32
done.
```

### 2. Everything at once
`dnsenum --enum example.com`: shortcut for `--threads 5 -s 15 -w` (threads + scraping + whois).

### 3. Custom wordlist and recursion
`dnsenum -f subdomains.txt -r example.com`: `-r` brute-forces again under each discovered subdomain (`*.dev.example.com`). Without `-f`, it uses `/usr/share/dnsenum/dns.txt` or the `dns.txt` in the script's directory [4].

### 4. Fast mode, no reverse sweep
`dnsenum --noreverse example.com`: reverse sweeps of every /24 are the slowest part.

### 5. XML report
Kali's own example: `dnsenum --noreverse -o mydomain.xml example.com` [4].

### 6. Specific DNS server (lab or internal)
`dnsenum --dnsserver 10.10.10.10 --enum -p 0 -s 0 -f wordlist.txt domain.htb`: `-p 0 -s 0` disables Google scraping; the standard HTB/OSCP invocation [10].

### 7. Whois netrange expansion
`-w`: whois each netrange so the scan covers the whole allocated block, not just the /24.

### 8. Wordlist self-update
`-u a|g|r|z`: add names found by AXFR (z), Google (g), reverse lookups (r) or all (a) back into the wordlist, building a site-specific dictionary.

### 9. Hygiene flags
`--subfile out.txt` (save subdomains), `-e regex` (exclude PTRs), `--private` (show and save private IPs: internal-leak indicator), `-t` timeout, `-d` whois delay, `--threads N`, `--nocolor`, `-v` verbose.

### 10. Realistic task: map all of a company's IP blocks

```bash
dnsenum --enum -p 0 -s 0 -f /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
        -r -u a --private -o acme.xml --subfile acme-subs.txt acme.example
cat acme.example_ips.txt         # non-contiguous blocks → scope check → nmap
```

Result: subdomains, IP blocks (including blocks in other providers' space) and any leaked private IPs. Confirm every block is in scope before scanning.

---

## Output and fields explained

- Output is in **BIND zone-file columns**: name, TTL, class, type, data, so results can be compared with (or pasted into) a zone file.
- **Host's addresses / Name Servers / Mail (MX) Servers**: steps 1–3 of the pipeline.
- **"Trying Zone Transfers and getting Bind Versions"**: AXFR on each NS. The BIND version part no longer runs: the 1.2.4 changelog says "Removed Bind Version detection" [11], but the heading stayed.
- **Brute forcing with <file>**: step 6; recursion results appear under each subdomain when `-r` is used.
- **class C netranges**: each discovered IP expanded to its /24; dnsenum's distinctive idea.
- **Performing reverse lookup on N ip addresses**: PTR sweep of those ranges (256 per /24).
- **ip blocks**: the final "non-contiguous IP blocks" deliverable, also written to `<domain>_ips.txt`.

---

## History and evolution

| When | What happened |
|---|---|
| Mid-2000s (exact year unconfirmed) | Filip Waeytens and tixxDZ write dnsenum in Perl [1] |
| ~2008–2010 | Hosted on Google Code; Fedora packages 1.2 (Apr 2010) [12]; installed under `/pentest/enumeration/dnsenum` in BackTrack-era guides [13] |
| 1.2.4 | BIND version detection removed [11]; Kali example output shows 1.2.4 [4] |
| 2014 | Copyright "2014 - Filip Waeytens, tixxDZ" in source [14]; project moves to GitHub (`fwaeytens/dnsenum`) [15] |
| 17 Sep 2018 | SparrowOchon forks it as dnsenum2 [3] |
| 2019 | Copyright "2019 - Network Silence" (maintainer) [14] |
| 2019–2025 | 1.3.0 → 1.3.2 in Debian/Ubuntu; dnsenum2 "officially mainlined in Kali Linux"; adds dynamic DNS.txt reading, extra DNS.txt entries, allinurl fix [3][5] |

Version-label confusion: Ubuntu's `dnsenum_1.3.0-5` package man page still says "dnsenum version 1.2.6" [16], and the 1.3.0 source header literally says "changed version number to the correct one" [14]. Trust the package version.

### Concept history
- **AXFR + BIND version** (`version.bind` CHAOS TXT): BIND 8/9-era habit of fingerprinting servers for vulnerable versions.
- **Google scraping:** the Johnny Long "Google hacking" era (mid-2000s); since killed by search-engine bot detection.
- **Class C expansion + whois:** pre-cloud internet assumption that a company owns its /24s and whois (RFC 3912; earlier RFC 954) shows the allocation. The cloud breaks this assumption.
- **Recursive brute force:** precursor of today's permutation tools (altdns, gotator).
- **"Non-contiguous IP blocks":** the same goal fierce (2007) was built around; the two tools share the idea and even wordlists [10].

### Why it is used today
One-command "give me everything" with zone-file-style output; its netrange → `domain_ips.txt` deliverable is unique among the three; in every Kali build and in training material as the comprehensive Perl option. Weaker on modern techniques (no CT, no NSEC walking, no structured JSON).

---

## How it works internally

- Perl with **ithreads** (`threads`, `threads::shared`, `Thread::Queue`) and **Net::DNS** for queries; Net::IP / Net::Netmask for range maths; Net::Whois::IP for whois; WWW::Mechanize + HTML::Parser for scraping; XML::Writer for `-o`; String::Random to generate random names (used for wildcard probing) [2][14].
- Defaults in source: timeout 10 s, delay 3 s, pages 5 [14].
- Sequential stages; NS, MX, AXFR, brute force and reverse lookups are threaded within a stage.
- Netrange step: collect all IPs found → group into /24 (or whois netrange with `-w`) → PTR every address → keep those whose PTR is in the target domain → print blocks.
- No root needed; ordinary UDP/TCP 53, whois (TCP 43) and HTTP clients.

---

## Cross-platform comparison

| dnsenum stage | Windows | macOS | Web/cloud |
|---|---|---|---|
| A / NS / MX | `Resolve-DnsName` | `dig` | DNSDumpster |
| AXFR | `nslookup` → `ls -d` | `dig axfr` | n/a |
| Google scraping | Manual `site:` search | Same | Search APIs (Bing, Google CSE), theHarvester |
| Brute force + recursion | PowerShell loop | bash + `dig` | Passive DNS |
| Netrange + whois | `whois` (Sysinternals) | `whois` | bgp.he.net, RIPEstat, ARIN RDAP |
| Reverse sweep | PTR loop | `nmap -sL` / `dig -x` | Shodan / Censys |

General platform view: Linux (`dig`/`host`, the tools wrap Net::DNS/dnspython); Windows (`nslookup`, `Resolve-DnsName`; AD-integrated DNS adds LDAP zone enumeration); macOS (`dig`, mDNSResponder; Bonjour is a different problem); Android/iOS (no CLI, apps or Termux); web/cloud (CT logs, passive DNS, provider APIs for own zones). Same protocol everywhere (RFC 1035); only the Linux tools bundle the strategy.

---

## Alternatives

dnsrecon (superset, actively developed), fierce (lighter neighbour walking), OWASP Amass (modern all-in-one), nmap `dns-brute`, `whois` + `nmap -sL` for netrange PTR sweeps, theHarvester (search-source scraping that works through APIs), DNSDumpster, bgp.he.net (netblocks by ASN: the modern replacement for whois class C guessing), subfinder, puredns, dnsx.

---

## Role: Penetration Tester / Red Teamer
- **Why:** one command gives scope evidence (`domain_ips.txt`).
- **Day to day:** `--enum -p 0 -s 0 -f <list> -r -u a`, XML into the report.
- **Expert knowledge:** disable scraping; grow a target-specific wordlist with `-u a` across the engagement; check each expanded /24 against scope, because that expansion is how people accidentally scan third parties.

## Role: Bug Bounty Hunter
- **Why:** less central (no CT, slow), but `-r` recursion finds deep names (`api.internal.dev.target`) that flat brute force misses.
- **Expert knowledge:** feed it a wordlist already enriched from passive sources; keep netrange expansion off for cloud-hosted targets.

## Role: DNS / Network Engineer
- **Why:** zone-file columns make diffing exposed records against your zone easy.
- **Day to day:** `--private` reveals RFC1918 records published by mistake; reverse sweeps show stale or missing PTRs (mail deliverability); AXFR section proves transfers are closed.

## Role: Cybersecurity Analyst (Blue Team / SOC)
- **Why:** recognise it.
- **Signature:** a burst of A/NS/MX queries, AXFR on every NS, brute force with its well-known `dns.txt`, then 256 sequential PTR queries per /24, very visible in reverse-zone logs.

## Role: Attack-Surface Management / Threat Intel Analyst
- **Why:** netrange + whois is crude IP-ownership attribution.
- **Expert knowledge:** today use RDAP and ASN data (bgp.he.net, RIPEstat), and keep dnsenum output as a cross-check.

## Role: CTF Player / Cert Candidate (OSCP, CPTS, eJPT, CEH)
- **Standard exam command:** `dnsenum --dnsserver <box> --enum -p 0 -s 0 -f wordlist domain` [10].
- **Expert knowledge:** `-p 0 -s 0` avoids pointless Google timeouts in offline labs; old guides still show `/pentest/enumeration/dnsenum` paths.

## Role: Cloud / DevOps Engineer
- **Why:** mostly a lesson: class C expansion around cloud IPs is meaningless or out of scope, which explains why outside scanners hit neighbouring tenants.
- **Day to day:** `--private` catches internal IPs leaked into public zones by IaC.

## Role: Tool Developer (Python / Perl)
- **Lessons:** Perl ithreads + Net::DNS design, XML::Writer output, String::Random wildcard probing; how a dead dependency (Google scraping) and version-label drift happen when maintenance passes between owners (Waeytens → Network Silence → SparrowOchon).

---

## Related topics, curricula and certifications

DNS footprinting, IP allocation and whois/RDAP, network scoping, Google hacking history. Appears in CEH (footprinting), OSCP and HTB CPTS DNS sections [17], eJPT, PNPT, CompTIA PenTest+, and Kali-based courses (*Kali Linux Network Scanning Cookbook*, ch. 2 [18]). Practice: `zonetransfer.me`, HTB/THM port-53 boxes, a home BIND lab.

---

## Follow-up Q&A

### Q: Which roles care about dnsrecon/dnsenum/fierce? (role pick)
All eight selected: Penetration Tester / Red Teamer; Bug Bounty Hunter; DNS / Network Engineer; Cybersecurity Analyst (Blue Team / SOC); Attack-Surface Management / Threat Intel; CTF Player / Cert Candidate; Cloud / DevOps Engineer (non-obvious); Tool Developer (non-obvious).

### Q: Why does every AI present dnsrecon, dnsenum and fierce as one entity?
**Mechanism:** (1) training material teaches them together: InfoSec Institute's "Fierce, DNSenum and DNSrecon" section [19], the Kali cookbook introducing dnsenum as "similar to dnsrecon" [18], comparison tables [20]; models learn co-occurrence. (2) Curricula group by job (information gathering → DNS analysis), where the three overlap. (3) Descriptions overlap because ideas were borrowed: dnsenum's "discover non-contiguous IP blocks" [2] echoes fierce's "locating non-contiguous IP space" [21]; cheat sheets run dnsenum with `fierce-hostlist.txt` [10]. (4) Answers optimise for doing the task, so every fitting tool is listed.

**Valid vs misleading:**

| Valid to group | Misleading to group |
|---|---|
| Same layer (DNS, port 53) | Origin: RSnake 2007 (Perl); Waeytens/tixxDZ (Perl); Perez 2007 Ruby → 2010 Python |
| Same recon phase | Capabilities: dnsrecon alone does NSEC walking, snooping, CT, API; fierce alone walks neighbours by default; dnsenum alone expands whois netranges |
| Same basic tests | Health: dnsrecon active; dnsenum a fork; fierce upstream slowed |
| Same defensive fixes | Internals: Perl ithreads + Net::DNS vs dnspython |

Mental model: three implementations of one methodology (like nmap / masscan / RustScan). **Certain:** co-occurrence in teaching material, shared phrasing, different authors/languages. **Inferred:** that this is the main cause of AI lumping.

### Q: Re-explain per tool, all roles
This note is the dnsenum section; see `notes/tools/dnsrecon.md` and `notes/tools/fierce.md`.

### Picking between the three

| Need | Use |
|---|---|
| Most techniques, JSON, DNSSEC, CT, API | **dnsrecon** |
| One command mapping the IP blocks a domain owns | **dnsenum** |
| Hosts next to known ones; internal PTR sweeps | **fierce** |

---

## Sources

[1] cckchy/dnsenum, "README - dnsenum.pl VERSION: 1.2.4," GitHub mirror. [Online]. Available: https://github.com/cckchy/dnsenum (accessed Nov. 17, 2026).

[2] "dnsenum(1)," ManKier. [Online]. Available: https://www.mankier.com/1/dnsenum (accessed Nov. 17, 2026).

[3] SparrowOchon, "dnsenum2," GitHub. [Online]. Available: https://github.com/SparrowOchon/dnsenum2 (accessed Nov. 17, 2026); project record, Ecosyste.ms: https://awesome.ecosyste.ms/projects/github.com%2FSparrowOchon%2Fdnsenum2.

[4] Kali Linux, "dnsenum," Kali Tools. [Online]. Available: https://www.kali.org/tools/dnsenum (accessed Nov. 17, 2026).

[5] Debian sources, "dnsenum 1.3.2-1 README.md." [Online]. Available: https://sources.debian.org/src/dnsenum/1.3.2-1/README.md (accessed Nov. 17, 2026).

[6] "dnsenum(1)," Ubuntu plucky manual pages. [Online]. Available: https://manpages.ubuntu.com/manpages/plucky/man1/dnsenum.1.html (accessed Nov. 17, 2026).

[7] Linux Mint Community, "dnsenum." [Online]. Available: https://community.linuxmint.com/software/view/dnsenum (accessed Nov. 17, 2026).

[8] cmenning/dnsenum2 README, GitHub. [Online]. Available: https://www.github.com/cmenning/dnsenum2 (accessed Nov. 17, 2026).

[9] "dnsenum(1)," Debian trixie manual pages. [Online]. Available: https://dyn.manpages.debian.org/trixie/dnsenum/dnsenum.1.en.html (accessed Nov. 17, 2026).

[10] "DNS Enumeration (Port 53)," vipa0z notes. [Online]. Available: https://vipa0z.github.io/02-internal-networks/02-service-enumeration/01-dns.html (accessed Nov. 17, 2026).

[11] tonitech/dnsenum README (1.2.4 changelog), GitHub. [Online]. Available: https://github.com/tonitech/dnsenum (accessed Nov. 17, 2026).

[12] Fedora, "dnsenum.spec." [Online]. Available: https://src.fedoraproject.org/rpms/dnsenum/blob/c33a9c6dee5217e88f35f79a79b9b16f64bc3546/f/dnsenum.spec (accessed Nov. 17, 2026).

[13] "Dnsenum," aldeid wiki. [Online]. Available: https://aldeid.com/wiki/Dnsenum (accessed Nov. 17, 2026).

[14] Debian sources, "dnsenum 1.3.1-1 dnsenum.pl." [Online]. Available: https://sources.debian.org/data/main/d/dnsenum/1.3.1-1/dnsenum.pl (accessed Nov. 17, 2026).

[15] Google Code Archive, "dnsenum." [Online]. Available: https://code.google.com/archive/p/dnsenum (accessed Nov. 17, 2026).

[16] "dnsenum(1)," Ubuntu jammy manual pages. [Online]. Available: https://manpages.ubuntu.com/manpages/jammy/man1/dnsenum.1.html (accessed Nov. 17, 2026).

[17] "Subdomain Enumeration," CPTS prep notes. [Online]. Available: https://kabaneridev.gitbook.io/pentesting-notes/certification-preparation/cpts-prep/web-enumeration/subdomain-enumeration (accessed Nov. 17, 2026).

[18] M. Hixon, *Kali Linux Network Scanning Cookbook*, 2nd ed., Packt, 2017, ch. 2. [Online]. Available: https://subscription.packtpub.com/book/cloud_&_networking/9781787287907/2/ch02lvl1sec21/introduction (accessed Nov. 17, 2026).

[19] InfoSec Institute, "DNS enumeration techniques in Linux." [Online]. Available: https://infosecinstitute.com/resources/penetration-testing/dns-enumeration-techniques-in-linux/ (accessed Nov. 17, 2026).

[20] "Which command-line tool can be used for DNS enumeration," Ultimate Systems Blog, May 2025. [Online]. Available: https://blog.usro.net/2025/05/which-command-line-tool-can-be-used-for-dns-enumeration/ (accessed Nov. 17, 2026).

[21] mschwager/fierce, GitHub. [Online]. Available: https://github.com/mschwager/fierce (accessed Nov. 17, 2026).

Notes on certainty: dnsenum's first-release year is unconfirmed (mid-2000s inferred from version history). Option meanings beyond those quoted from the man page (`-u`, `-e`, `--private`, `--enum` expansion) come from the tool's help text as remembered and were not re-fetched this session. Sample output is a format-faithful illustration.
