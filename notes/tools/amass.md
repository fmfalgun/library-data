---
tool: amass
date: 2026-11-24
domains: [Offensive Security, Reconnaissance, OSINT, DNS & Internet Infrastructure, Attack Surface Management]
roles: [Penetration Tester / Red Teamer, Bug Bounty Hunter, Attack Surface Management / Security Engineer (Blue Team), OSINT Investigator / Threat Intelligence Analyst, SOC / Cybersecurity Analyst, Network Engineer / DNS Administrator, Security Tool Developer / Go Engineer]
tags: [amass, owasp, recon, subdomain-enumeration, attack-surface, asm, osint, dns, certificate-transparency, axfr, brute-force, open-asset-model, asset-db, bug-bounty, go]
---

# amass (OWASP Amass)

## Summary

OWASP Amass is a Go framework for **attack surface mapping and external asset discovery**. It starts from a seed (a root domain, ASN, CIDR or address range) and expands it into a **graph** of subdomains (FQDNs), IP addresses, netblocks, ASNs and organisations. It collects from passive OSINT sources (certificate transparency, passive DNS and dozens of APIs) and, when allowed, active techniques: zone-transfer attempts, certificate grabs, DNS brute force, name alterations and recursion. Everything goes into a persistent asset database built on the **Open Asset Model (OAM)**, so you can query, diff and visualise across runs [1][2][3].

- **Problem it solves:** "What does this organisation actually have exposed on the internet?", answered as a graph with history rather than a flat list.
- **Current version (Nov 2026):** v5.1.3, Apache-2.0, actively maintained, about 15k GitHub stars [1].
- **Status:** OWASP Flagship project; project leader Jeff Foley [4].
- **Big caveat:** v5 is architecturally different from v3/v4, and most online tutorials still describe v3.

---

## Usage and commands

### Install / availability

| Platform | Method |
|---|---|
| Kali / Parrot | Installed by default on Kali, managed as a normal package [5]; `sudo apt install amass` (may lag upstream) |
| macOS / Linuxbrew | `brew tap owasp-amass/homebrew-amass && brew install amass` [6] |
| Any OS with Go (1.26+) | `CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main` [6] |
| Windows / Linux / macOS | Prebuilt release zip from GitHub; put the binary on PATH |
| Docker | `docker pull caffix/amass`; mount `~/.config/amass` so the DB persists |
| Android / iOS | Not meaningful (server-side workload) |

### v5 architecture (read this first)

- A **background engine** (REST API on `127.0.0.1:4000`) does the collection. `amass enum` starts it automatically if it isn't running and acts as a client; `amass engine` runs it by hand [7].
- **Subcommands:** `enum`, `subs`, `track`, `viz`, `assoc`, `engine` [7][8].
- **Removed:** v4's `intel` and `db` subcommands, and `-json`/`-o` on enum. ASN/org lookups moved to seeds on `enum` [7][2].
- **Results live in the asset DB** (`~/.config/amass` on Linux), not in `-o` files; read them with `subs`, `track`, `viz` and `assoc` [6].
- Workflow: **collect** (`enum`), then **query** (`subs`, `track`, `viz`, `assoc`). Since 5.0, `enum` drives the engine and the analysis subcommands query the stored graph afterwards [8].

### The 10 most useful operations

> Sample outputs are **representative**: they use RFC 5737 documentation IPs and private-use ASN 64496, not a live scan.

**1. Default enumeration (passive sources + DNS resolution)**
```bash
amass enum -d example.com
```
```
example.com (FQDN) --> ns_record --> ns1.example.com (FQDN)
www.example.com (FQDN) --> a_record --> 198.51.100.10 (IPAddress)
dev.example.com (FQDN) --> cname_record --> example.herokuapp.com (FQDN)
198.51.100.0/24 (Netblock) --> contains --> 198.51.100.10 (IPAddress)
64496 (ASN) --> announces --> 198.51.100.0/24 (Netblock)
64496 (ASN) --> managed_by --> EXAMPLE-NET (RIROrganization)
```

**2. Active techniques + brute force (in-scope targets only)**
```bash
amass enum -active -brute -w words.txt -d example.com
```
Amass pulls subdomains from passive sources, can enable active DNS recon, and can brute-force more names against a wordlist [2]. `-active` adds zone-transfer attempts and certificate grabs; `-brute` adds wordlist guessing plus alterations of names already found.

**3. Seed from network ranges**
```bash
amass enum -asn 64496 -cidr 198.51.100.0/24
amass enum -addr 198.51.100.1-254 -d example.com
```
v5 has no `intel`; ranges are scope seeds for `enum` [6].

**4. Names only (for piping)**
```bash
amass subs -d example.com -names -nocolor
```
```
example.com
www.example.com
dev.example.com
vpn.example.com
```

**5. Names with IPs**
```bash
amass subs -d example.com -ip
```
```
www.example.com 198.51.100.10
vpn.example.com 203.0.113.5,2001:db8::5
```

**6. ASN summary**
```bash
amass subs -d example.com -summary
```
```
ASN: 64496 - EXAMPLE-NET - Example Hosting Inc.
        198.51.100.0/24       3  Subdomain Name(s)
ASN: 64511 - CLOUDCO - Cloud Provider LLC
        203.0.113.0/24        1  Subdomain Name(s)
```

**7. Save to file**: `amass subs -d example.com -names -o names.txt` (`-o` is on `subs` in v5) [2].

**8. Track new assets**: `amass track -d example.com`. It analyses OAM data in the graph DB to find assets newly discovered for given domains, optionally filtered by timestamp [9].

**9. Visualise**: `amass viz -d3 -d example.com` (also `-dot`, `-gexf` for Gephi). Needs at least one format and one root domain [9].

**10. Walk associations**: `amass assoc -d example.com` queries the OAM graph along a walk defined by relation triples [10]. It's the newest and least documented subcommand; see `amass assoc -h`.

**Other useful flags:** `enum -list` (data sources and key status), `-r` / `-tr` (resolvers / trusted resolvers), `-bl` (blacklist subdomains), `-dir` (alternative DB directory), `-timeout` (minutes), `-silent`, `-nocolor`.

### Configuration

- **`~/.config/amass/config.yaml`**: scope (domains, IPs, ASNs, CIDRs, blacklist), resolvers, brute-force options, DB connection.
- **`datasources.yaml`**: API keys (Shodan, Censys, SecurityTrails, VirusTotal, Netlas, WhoisXML and others). Without keys, passive coverage drops sharply; this is the biggest quality lever.
- **Database:** asset-db library, a unified repository interface over several backends [11]. SQLite by default; PostgreSQL through env vars `AMASS_DB_USER`, `AMASS_DB_PASSWORD`, `AMASS_DB_HOST` (default localhost), `AMASS_DB_PORT` (default 5432), `AMASS_DB_NAME` (default assetdb) [12].

### Realistic task, start to finish (authorised external assessment of example.com)

```bash
# 0. Put API keys in ~/.config/amass/datasources.yaml, then confirm they load
amass enum -list | grep -v '^\s*$'

# 1. Passive pass first (no direct traffic to the target beyond DNS resolution)
amass enum -d example.com -dir ./ex-db -timeout 60 | tee enum.log

# 2. In-scope active pass: brute force plus alterations
amass enum -d example.com -dir ./ex-db -active -brute -w ~/wordlists/dns-top20k.txt | tee -a enum.log

# 3. Pull the results
amass subs -d example.com -dir ./ex-db -names -o names.txt
amass subs -d example.com -dir ./ex-db -ip      > names_ips.txt
amass subs -d example.com -dir ./ex-db -summary > asn_summary.txt

# 4. Hand off to the rest of the pipeline
cat names.txt | httpx -silent -title -tech-detect -o live.txt
grep cname_record enum.log | grep -Ei 'herokuapp|azurewebsites|s3|github.io'   # takeover candidates

# 5. Blue-team handover: weekly cron, then diff
amass enum -d example.com -dir /srv/amass && amass track -d example.com -dir /srv/amass
```

### Common mistakes and gotchas

- **Following v3 tutorials:** `amass intel`, `amass db`, `-json`, and `-o` on `enum` are gone; `db` was already removed in v4.2.0 (moved to `oam_subs`) [13].
- **Treating `enum` stdout as the deliverable:** the DB is the deliverable; export with `subs`.
- **No API keys:** Amass looks weak without them; with keys it's usually the most thorough tool.
- **Bad resolvers:** public resolvers rate-limit and return poisoned or wildcard answers. Use a vetted list plus `-tr`.
- **Wildcard DNS:** detected, but brute force against wildcard zones can still produce noise. Verify before reporting.
- **Run time:** large orgs take hours. Use `-timeout` and `tmux`.
- **Scope and legality:** passive collection is generally fine; `-active` and `-brute` touch the target's DNS and hosts and need written authorisation.
- **Permissions:** no root needed (userland DNS and HTTPS). Docker needs a volume mount or the DB is lost.
- **Shared ASNs:** seeding with CDN or cloud ASNs (AWS, Cloudflare) pulls in other companies' assets. Seed only with ASNs the org owns.

---

## Output and fields explained

Each `enum` output line is **one edge in the OAM graph**:

```
<subject> (<AssetType>) --> <relation> --> <object> (<AssetType>)
```

- **Asset types (OAM):** `FQDN`, `IPAddress`, `Netblock`, `ASN`, `RIROrganization`, and others (organisations, certificates, URLs, services as the model grows).
- **DNS relations:** `a_record`, `aaaa_record`, `cname_record`, `ns_record`, `mx_record` (and other record types), from resolving the names.
- **Routing/ownership relations:** `contains` (netblock → IP), `announces` (ASN → netblock, from BGP/routing data), `managed_by` (ASN → registry organisation, from RIR/WHOIS data).
- **Takeover signal:** a `cname_record` pointing at third-party SaaS (`*.herokuapp.com`, `*.azurewebsites.net`, S3, `github.io`) is a candidate if the target resource no longer exists.
- **`subs -summary`** rows: ASN number, name and description, then each netblock with the count of discovered names resolving into it. Names clustering in an unexpected ASN often mean shadow IT or a forgotten vendor.
- **`subs -ip`:** name followed by comma-separated IPv4/IPv6 addresses.
- **When values change:** each `enum` run adds entities and edges with timestamps; `track` compares by discovery time, so the same command over time shows drift.

---

## History and evolution

### Origin
- Created by **Jeff Foley** in **2017** as a simple CLI to automate recon. His background in the defence industry, where attack surface mapping was decades ahead of mainstream practice, and frustration with slow, error-prone manual intelligence gathering motivated it. He shared it with peers first, and the community encouraged him to open-source it [14].
- The trigger: while showing organisations what they look like on the internet, he found existing tools lacking [15].
- **September 2018:** presented at OWASP London as "The OWASP Amass Project: DNS Enumeration written in Go" by Jeff Foley (caffix), then US Manager of Penetration Testing & Red Teaming at National Grid [16].
- **2019:** Foley and contributor **Anthony Rhodes** (Senior Purple Team Member, National Grid) presented at BSidesROC, OWASP Rochester and Bugcrowd LevelUp [17][18].
- Later became an **OWASP Flagship** project (classified Flagship, Breaker, Builder, Tool) [4].

### Concept lineage

| Era | Technique / milestone |
|---|---|
| 1987 → | **Zone transfers (AXFR)**, RFC 1034/1035 (later RFC 5936). Misconfigured servers leak the whole zone. Amass still tries it under `-active`. |
| 2000s | **Wordlist brute force**: dnsmap, fierce (RSnake), dnsenum, dnsrecon. |
| 2005 | **Passive DNS** (Florian Weimer), later commercial pDNS (Farsight, SecurityTrails): historical resolutions. |
| Early 2010s | **Search-engine / OSINT scraping**: theHarvester, Recon-ng, Sublist3r. |
| 2013 → | **Certificate Transparency** (RFC 6962); crt.sh made CT the richest subdomain source after about 2015. |
| 2017–18 | **Amass** combines all of these in one concurrent Go engine with many data sources, alterations and recursion, and a **graph** of name → IP → netblock → ASN. Enumeration becomes attack surface mapping. |
| 2022 | **Open Asset Model** announced at DEF CON 30: a standard, extensible taxonomy for internet-facing assets [19]. |
| 2023 (v4.0) | v4 introduces the Open Asset Model and Asset Database [20]; PostgreSQL integration [21]. |
| v4.2.0 | `db` subcommand removed (now in `oam_subs`); asset-db performance work [13]. |
| 2025 (v5.0) | Collection split into a separate **engine**; client pruned; OAM upgrades; Neo4j-related work; asset-db cache [22]. `intel` dropped [2]. |
| 2026 (v5.1.x) | First **engine REST API**, Go 1.26, asset-db v0.24.x with schema changes affecting performance [23]; v5.1.3 by Nov 2026 [1]. |

---

## How it works internally

```
            seeds (-d, -df, -asn, -cidr, -addr, config.yaml scope)
                                  │
                         amass enum (client)
                                  │ REST (127.0.0.1:4000)
                                  ▼
                     ┌────── Amass engine ───────┐
                     │ session per enumeration   │
                     │  ├─ queue.db (SQLite+GORM) │ work items / state
                     │  ├─ cache.db (SQLite)      │ dedup, temp assets
                     │  └─ plugins / handlers     │
                     │     • passive APIs, CT     │
                     │     • DNS resolution/AXFR  │
                     │     • brute + alterations  │
                     │     • HTTP/TLS probes      │
                     │     • RIR / BGP / WHOIS    │
                     └────────────┬──────────────┘
                                  ▼
                 asset-db (OAM entities + relations)
                 SQLite (default) | PostgreSQL | (Neo4j work)
                                  ▲
            amass subs / track / viz / assoc  (read the graph)
```

- **Event-driven pipeline:** each discovered asset becomes an event that triggers further handlers (an FQDN gets resolved, the IP gets mapped to a netblock and ASN, which can seed further discovery). Recursion and alterations grow from found names.
- **Per-session tiers:** a temporary SQLite **cache** (`<tmpdir>/cache.db`) for deduplication and a SQLite + GORM **queue** (`<tmpdir>/queue.db`) for work tracking, both lasting only for the session [12].
- **Entities:** every OAM asset is wrapped in a `dbt.Entity` (unique DB ID, the asset, and relationship edges) from asset-db [24].
- **The owasp-amass ecosystem:** collection engine, the Amass CLI, Asset Database, Open Asset Model and OAM Tools [25].
- **Extensibility:** v3 used Lua `.ads` scripts for custom data sources (Amass Scripting Engine) [26]; v5 uses Go plugins, and the REST API lets your own code drive the engine.
- *Certainty:* the subcommands, API port, DB backends, env vars and session-tier files come from docs and changelogs. The plugin/event-pipeline description is a general reading of the architecture, not verified line by line in source.

---

## Cross-platform comparison: how other platforms solve the same problem

| Approach | Example | Discovery method | Persistence / history | Relationships | Cost |
|---|---|---|---|---|---|
| **Amass CLI** | `amass enum` | Passive APIs, CT, AXFR, brute force, alterations, recursion | Yes: local SQLite / Postgres graph | Yes (OAM graph) | Free (API keys may cost) |
| Fast passive CLI | subfinder | Passive APIs only | No (flat list) | No | Free |
| Event-graph framework | BBOT | Passive + active modules | Optional (Neo4j/JSON output) | Yes | Free |
| Web lookup | crt.sh / DNSDumpster | CT logs / pDNS | Their dataset | Limited | Free |
| Internet-scan engines | Shodan / Censys | Global scanning + certs | Their dataset | Host ↔ cert ↔ service | Freemium |
| SaaS ASM | Defender EASM, Cortex Xpanse | Proprietary crawl, pDNS, WHOIS pivots, scanning | Yes, managed | Yes + risk scoring | Enterprise |

The core difference is that Amass is self-hosted, bring-your-own-keys, with an open data model (OAM). SaaS ASM sells the same idea with proprietary datasets, scheduling and triage.

OS availability: one Go binary for Linux, macOS and Windows, plus Docker. No meaningful mobile equivalent.

---

## Alternatives

**Open-source CLI (same job):**

| Tool | Notes vs Amass |
|---|---|
| subfinder (ProjectDiscovery) | Passive only, very fast, clean output; fits dnsx/httpx/nuclei. Less depth, no graph. |
| assetfinder (tomnomnom), findomain | Minimal, fast passive. |
| Sublist3r | Historical; largely unmaintained. |
| puredns / shuffledns + massdns | Massive-scale brute force and resolution; better wildcard filtering than Amass's built-in brute force. |
| dnsgen / alterx / gotator | Permutation generators to feed resolvers. |
| dnsrecon, dnsenum, fierce | Classic active DNS (AXFR, brute force, reverse). |
| BBOT (Black Lantern Security) | Recursive event-graph OSINT framework; closest modern rival in philosophy. |
| SpiderFoot, Recon-ng, theHarvester | Broader OSINT (emails, people, breaches); DNS is one module. |
| reconFTW, Osmedeus | Orchestrators that wrap Amass and the tools above. |

**GUI / analyst:** Maltego (has had Amass integrations [17]), SpiderFoot HX.
**Web services (often used as Amass sources):** crt.sh, DNSDumpster, SecurityTrails, Shodan, Censys, VirusTotal.
**Commercial ASM (from general knowledge, not re-verified):** Microsoft Defender EASM (ex-RiskIQ), Palo Alto Cortex Xpanse, Censys ASM, Mandiant ASM, CrowdStrike Falcon Exposure Management, Tenable ASM.

---

## Role: Penetration Tester / Red Teamer

- **Why it matters:** an unknown host is an untested host, and the forgotten staging box is where attackers start. Accenture's adversary simulation team has called Amass its primary tool suite for external enumeration [27].
- **Day to day:** a passive run on day 0 to reconcile against the client's asset list; an active/brute run after sign-off; then `subs -ip` → port scan → web probe. `-summary` separates owned netblocks from rented SaaS (often out of scope).
- **What experts know:** reconcile against the signed scope (`-bl` for exclusions); ASN-seeded results include hosts you're **not** authorised to touch; alterations from found names beat bigger wordlists; use one `-dir` per engagement so client data never mixes.

## Role: Bug Bounty Hunter

- **Why it matters:** wide-scope programs (`*.target.com`) reward whoever finds the obscure host first.
- **Day to day:** a recon VPS with every free API key, a large resolver list, and nightly `enum` + `track`. New names → httpx → nuclei → manual testing.
- **What experts know:** **diffing beats scanning**, because new assets are the least tested, so `amass track` on cron is the edge. Pair Amass's breadth with puredns for wildcard-safe brute force; grep CNAMEs for takeovers; raise default timeouts for big programs.

## Role: Attack Surface Management / Security Engineer (Blue Team)

- **Why it matters:** you can't patch or monitor what isn't in the inventory.
- **Day to day:** scheduled enumeration into a shared PostgreSQL asset-db; `track` diffs feed tickets ("new host on an unknown ASN, who owns it?"); reconcile with the CMDB and cloud accounts.
- **What experts know:** the Postgres backend plus SQL over OAM tables turns Amass into a mini ASM platform. The project's workshop extracts subdomains with joins over assets and relations, filtering `a_record`/`aaaa_record` plus `contains` [19]. Watch for dangling CNAME/NS records after decommissions.

## Role: OSINT Investigator / Threat Intelligence Analyst

- **Why it matters:** infrastructure links reveal ownership, including adversary infrastructure. OSINT investigators and intel analysts have used Amass to hunt threats since its early days [18].
- **Day to day:** pivot from a phishing domain → netblock → ASN → sibling domains (`assoc`), then export (`viz -gexf`) for reports.
- **What experts know:** passive mode leaves no footprint on the target (OPSEC). pDNS and CT data is historical, so treat results as time-stamped evidence, not the current state.

## Role: SOC / Cybersecurity Analyst

- **Why it matters:** "Is this host ours?" is often the first incident question; Amass has even been written up for mapping your external perimeter during an incident [28].
- **Day to day:** query the existing DB, or run a quick passive `enum` on an alert's domain; check the ASN or netblock against corporate ranges.
- **What experts know:** a pre-built, regularly refreshed DB beats a cold run at 3 a.m.; unexpected new hosts in `track` can mean rogue deployments or compromised DNS.

## Role: Network Engineer / DNS Administrator

- **Why it matters:** shows your zones *as the internet sees them*, including what you forgot.
- **Day to day:** check for AXFR leaks (`-active`), stale A records to released cloud IPs, and CNAMEs to deleted SaaS apps.
- **What experts know:** CT logs expose internal-sounding names (`jira-int`, `vpn-test`) as soon as a public certificate is issued, so use an internal CA or wildcards for names that shouldn't be advertised. Split-horizon leaks show up as names resolving differently from different resolvers.

## Role: Security Tool Developer / Go Engineer

- **Why it matters:** one of the larger real-world concurrent Go security codebases, and OAM is an open data model to build on.
- **Day to day / study:** plugin handlers in an event-driven pipeline; per-session SQLite cache and queue [12]; `dbt.Entity` wrappers [24]; asset-db repository abstraction (SQLite, Postgres, Neo4j work) [22][11].
- **What experts know:** drive the engine via the REST API on `127.0.0.1:4000` instead of shelling out [7]; v3's Lua `.ads` data sources [26] were replaced by Go plugins; follow OAM version bumps, because asset-type changes ripple through the client [22].

---

## Related topics (where it applies)

- **Frameworks:** MITRE ATT&CK Reconnaissance (TA0043: T1590 Gather Victim Network Information, T1596 Search Open Technical Databases); PTES Intelligence Gathering; OWASP WSTG Information Gathering (WSTG-INFO); NIST CSF Identify / Asset Management (ID.AM).
- **Study areas:** DNS internals (record types, AXFR, wildcards, recursion), Certificate Transparency, BGP and ASNs, passive DNS, OSINT methodology, subdomain takeover, external attack surface management, graph data modelling.
- **Certifications / curricula:** OSCP / PEN-200 (information gathering), PNPT, eJPT / eCPPT, CEH (footprinting), GIAC GPEN, SANS SEC497 (practical OSINT), CompTIA PenTest+ (recon), HTB Academy / TCM bug-bounty recon paths.

---

## Follow-up Q&A

### Q: amass (role pick)
Seven roles were suggested and **all** were selected: Penetration Tester / Red Teamer, Bug Bounty Hunter, ASM / Security Engineer (Blue Team), OSINT / Threat Intel Analyst, SOC / Cybersecurity Analyst, Network Engineer / DNS Administrator, Security Tool Developer / Go Engineer. The full first-answer content is organised into the sections above. No further follow-up questions were asked before `/save`.

---

## Sources

[1] D. Gupta, "OWASP Amass," *Recon Atlas*. [Online]. Available: https://guptadeepak.com/recon-atlas/tool/amass/ (accessed Nov. 17, 2026).

[2] Trickest, "amass," *Trickest Tools*, updated Oct. 13, 2026. [Online]. Available: https://trickest.com/tools/amass (accessed Nov. 17, 2026).

[3] OWASP Foundation, "OWASP Amass." [Online]. Available: https://owasp.org/amass (accessed Nov. 17, 2026).

[4] OWASP Foundation, "OWASP Amass — Project Classification." [Online]. Available: https://owasp.org/projects/amass (accessed Nov. 17, 2026).

[5] SourceForge, "OWASP Amass mirror — profile." [Online]. Available: https://www.sourceforge.net/mirror/owasp-amass/profile (accessed Nov. 17, 2026).

[6] Terminal Skills, "amass," *Skills Directory*. [Online]. Available: https://www.skillsdirectory.com/skills/terminalskills-amass (accessed Nov. 17, 2026).

[7] Terminal Skills, "amass (v5)," *skills.sh*. [Online]. Available: https://www.skills.sh/terminalskills/skills/amass (accessed Nov. 17, 2026).

[8] Linux Command Library, "amass." [Online]. Available: https://linuxcommandlibrary.com/man/amass (accessed Nov. 17, 2026).

[9] Algolia DocSearch, "OWASP Amass repository docs." [Online]. Available: https://docsearch.algolia.com/mcp/docs/repo/owasp-amass/amass (accessed Nov. 17, 2026).

[10] Wraith, "amass" (from kali.org tool page, updated Apr. 16, 2026). [Online]. Available: https://wraith-eight.vercel.app/tools/amass (accessed Nov. 17, 2026).

[11] "Asset Database," community Amass documentation. [Online]. Available: https://51nk0r5w1m.github.io/docs/asset_db (accessed Nov. 17, 2026).

[12] "Data Model," community Amass architecture documentation. [Online]. Available: https://51nk0r5w1m.github.io/docs/architecture/data-model (accessed Nov. 17, 2026).

[13] NewReleases, "owasp-amass/amass v4.2.0." [Online]. Available: https://newreleases.io/project/github/owasp-amass/amass/release/v4.2.0 (accessed Nov. 17, 2026).

[14] ZeroFox, "How to Use the Amass Open Asset Database." [Online]. Available: https://www.zerofox.com/blog/how-to-use-the-amass-open-asset-database/ (accessed Nov. 17, 2026).

[15] CSIAC, "OWASP Amass: Discovering Your Exposure on the Internet." [Online]. Available: https://csiac.org/tag/enumeration (accessed Nov. 17, 2026).

[16] J. Foley, "The OWASP Amass Project: DNS Enumeration written in Go," OWASP London, Sep. 6, 2018. [Online]. Available: https://owasp.org/www-chapter-london/assets/slides/OWASPLondon-OWASP-Amass-Project-20180906-PDF.pdf (accessed Nov. 17, 2026).

[17] OWASP Wiki (archived), "OWASP Amass Project." [Online]. Available: https://wiki.owasp.org/index.php/OWASP_Amass_Project (accessed Nov. 17, 2026).

[18] J. Foley and A. Rhodes, "The OWASP Amass Project: In-depth DNS Enumeration and Network Mapping," OWASP Rochester, May 8, 2019. [Online]. Available: https://wiki.owasp.org/images/0/00/OWASP_Amass_Rochester_2019.pdf (accessed Nov. 17, 2026).

[19] J. Foley, "OWASP Amass Flagship Project / Open Asset Model workshop" (slides). [Online]. Available: https://docs.google.com/presentation/d/1vS_lHfrH1iu_dtULJerHYQRDPK_Pm3XzCCRJ3_2MSeM/htmlpresent (accessed Nov. 17, 2026).

[20] NewReleases, "owasp-amass/amass v4.0.1 — Introducing the Open Asset Model and Asset Database." [Online]. Available: https://newreleases.io/project/github/owasp-amass/amass/release/v4.0.1 (accessed Nov. 17, 2026).

[21] NewReleases, "owasp-amass/amass v4.0.2." [Online]. Available: https://newreleases.io/project/github/owasp-amass/amass/release/v4.0.2 (accessed Nov. 17, 2026).

[22] NewReleases, "owasp-amass/amass v5.0.0." [Online]. Available: https://newreleases.io/project/github/owasp-amass/amass/release/v5.0.0 (accessed Nov. 17, 2026).

[23] NewReleases, "owasp-amass/amass v5.1.1." [Online]. Available: https://newreleases.io/project/github/owasp-amass/amass/release/v5.1.1 (accessed Nov. 17, 2026).

[24] "Core Concepts," community Amass architecture documentation. [Online]. Available: https://51nk0r5w1m.github.io/docs/architecture/core-concepts (accessed Nov. 17, 2026).

[25] OWASP Amass Project, "owasp-amass" GitHub organisation. [Online]. Available: https://github.com/owasp-amass (accessed Nov. 17, 2026).

[26] "OWASP Amass — The Amass Scripting Engine Manual" (v3 docs, fork copy). [Online]. Available: https://github.com/zpaav/amass/blob/master/doc/scripting.md (accessed Nov. 17, 2026).

[27] Go Packages, "github.com/OWASP/Amass/v3 v3.18.1" (README testimonials). [Online]. Available: https://beta.pkg.go.dev/github.com/OWASP/Amass/v3@v3.18.1 (accessed Nov. 17, 2026).

[28] OWASP Amass README, "External Projects Helping Amass Users" (fork copy). [Online]. Available: https://github.com/owaSP/Amass (accessed Nov. 17, 2026).

**Notes on certainty:** version numbers, subcommands, the engine API port, DB backends and env vars come from release notes and documentation-derived pages, but the canonical GitHub README could not be fetched directly in this session. Sample outputs are representative, not from a live run. The commercial ASM vendor list, the concept-lineage dates for pre-Amass tools, and the framework/certification mappings come from general knowledge and were not re-verified against primary sources.
