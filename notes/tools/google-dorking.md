---
tool: Google Dorking
aka: [Google hacking, Google-fu, search-engine reconnaissance]
date: 2026-11-24
domains: [Cybersecurity (recon / VAPT), OSINT, Bug Bounty, Threat Intelligence, Web/SEO, Investigative Research, Privacy/GRC]
roles: [Penetration Tester / Red Teamer, OSINT Analyst / Investigator, Bug Bounty Hunter, SOC / Blue Team (ASM), Threat Intelligence Analyst, Web Developer / SEO Engineer, Journalist / Academic Researcher, GRC / Privacy Officer]
tags: [osint, recon, passive-recon, ghdb, exploit-db, search-operators, attack-surface, seo, robots-txt, vapt, phase-1]
related_records: [data/tools/google-dorking.json, data/people/johnny-long.json]
---

# Google Dorking

## Summary

Google dorking (also called Google hacking) is a **technique, not a binary**: it chains Google's advanced search operators (`site:`, `inurl:`, `intitle:`, `intext:`, `filetype:`/`ext:`, `before:`/`after:`) to find the handful of indexed pages, files and errors that should never have been public. It does not exploit anything; it only reads a third party's index, so the target never sees a packet. That makes it the standard **passive reconnaissance** step (Phase 1) before any active scanning.

- **Coined by:** Johnny Long, who started collecting "googleDorks" in 2002 (a "dork" was the careless admin who exposed the data, not the searcher).
- **Catalogue:** the Google Hacking Database (GHDB) began in 2004 and has been maintained by Offensive Security on Exploit-DB since 2010. It is browsable without an account and sorted into 14 categories.
- **State in 2026:** about 25 operators still work. `cache:`, `link:`, `info:`, `related:` and `~` are gone. Google has required JavaScript for search since January 2025 and has ignored `&num=100` since September 2025, so scripted dorking now goes through APIs.
- **Library link:** the VAPT Toolkit page lists it under *OSINT Frameworks* (passive) with the companion repo [`fmfalgun/dork-runner`](https://github.com/fmfalgun/dork-runner).

---

## Install / availability

| Where | How |
|---|---|
| Any browser, any OS or phone | google.com. Nothing to install. |
| Scripts (Python/curl) | Plain HTTP requests have hit a JavaScript wall since Jan 2025; results come 10 per page since Sep 2025 (`&num=100` ignored). Automated queries break Google's ToS. |
| Legit automation | Google Programmable Search Engine / Custom Search JSON API (being wound down; check its current status), paid SERP APIs, and frameworks that wrap them: **pagodo** (runs GHDB dorks), **GooFuzz**, **theHarvester**, **Recon-ng**, **SpiderFoot**, **Metagoofil/FOCA** (document metadata), **SearchDiggity** (Bishop Fox) |
| Dork library | https://www.exploit-db.com/google-hacking-database: filter by keyword, category, author, date |
| Distros | Kali / BlackArch ship GHDB-aware tooling (pagodo, theHarvester, recon-ng) |

---

## Usage & commands (with sample outputs)

> `example.com` = a domain you own or have written authorisation to test. Outputs are illustrative SERP lines.

### 1. `site:`: restrict to a domain or subdomain
It anchors nearly every dork, and it's the only operator all six major engines support.
```
site:example.com -site:www.example.com
→ staging.example.com › login          "Staging Portal – Sign in"
→ jira.example.com › browse › OPS-112  "OPS-112: rotate DB creds…"
```
**Fields:** the breadcrumb (`host › path`) shows which subdomain was indexed. `-site:www` drops the main site so forgotten hosts surface. This is **passive subdomain enumeration**: keep adding `-site:<found-host>` to reach the next layer.

### 2. `filetype:` / `ext:`: files by extension
```
site:example.com (ext:pdf OR ext:docx OR ext:xlsx)
→ [XLS] example.com › uploads › 2019 › vendor-list.xlsx
```
**Fields:** a `[PDF]`/`[XLS]` tag means Google parsed the document's **contents**, not just a link, so `intext:` will also match inside it.

### 3. `intitle:` / `allintitle:`: matches the HTML `<title>`
```
intitle:"index of" site:example.com
→ "Index of /backup"   example.com › backup ›
```
**Fields:** `Index of /…` is the title Apache/nginx autoindex generates, which means **directory listing is enabled** on that path.

### 4. `inurl:` / `allinurl:`: matches the URL path
```
site:example.com inurl:admin | inurl:login | inurl:wp-admin
```
`|` is shorthand for `OR`.

### 5. `intext:` / `allintext:`: matches body text (errors, banners, versions)
```
site:example.com intext:"sql syntax near" | intext:"Warning: mysql_"
→ "…You have an error in your SQL syntax near '' at line 1…"
```
**Fields:** a database error in the index means unhandled input, a lead for SQLi testing (an active step needing authorisation).

### 6. Boolean core: `"exact phrase"`, `-exclude`, `OR` (uppercase), `*` (whole-word wildcard in phrases), `( )` grouping

### 7. `before:` / `after:`: date filters (YYYY-MM-DD), added 2019
```
site:example.com ext:log after:2026-01-01
```
Use them to separate new exposures from old ones, or to build a timeline of when something leaked.

### 8. Third-party leak hunting: point `site:` at platforms where your data ends up
```
"example.com" (site:pastebin.com | site:trello.com | site:github.com | site:docs.google.com)
```

### 9. `AROUND(n)`: proximity (unofficial, inconsistent)
```
"example" AROUND(3) "password"
```

### Operator status table (2026)

| Status | Operators |
|---|---|
| Working | `site:` `filetype:`/`ext:` `intitle:` `allintitle:` `inurl:` `allinurl:` `intext:` `allintext:` `"…"` `-` `OR`/`|` `*` `( )` `before:` `after:` `define:` `#..#` (number range) |
| Unreliable | `AROUND(n)`, `inanchor:`, `daterange:` (Julian dates) |
| Dead | `cache:` (removed Feb–Mar 2024; use the Wayback Machine), `related:` (2023), `link:` and `info:` (2017), `~` synonyms (2013), `+` forced term (2011), `phonebook:` (2010) |

---

## Output / fields explained

| You see | Meaning | Where it comes from | When it changes |
|---|---|---|---|
| `host › path ›` breadcrumb | Indexed URL | Googlebot crawl | Re-crawl, or removal via Search Console |
| `[PDF]` / `[DOC]` / `[XLS]` tag | Document body parsed and searchable | Google's document converters | When file is removed and recrawled (or URL returns 404/410) |
| Snippet text | Excerpt matching your terms | Indexed page text | Page edits after recrawl |
| "About N results" | **Estimate**, not a count | Index sampling | Varies per query/session; never use as a metric |
| "No information is available for this page" | URL indexed but content blocked by robots.txt | URL discovered via links, crawl disallowed | Add `noindex` (and *allow* crawl so Google can read it) or remove the URL |
| "unusual traffic" / CAPTCHA | Rate-limiting / bot detection (SearchGuard) | Too many queries, VPN/Tor exit IPs | Slow down, change network, use an API |

---

## One realistic task: external exposure audit of `example.com`

Use this as a blue-team self-audit, an in-scope pentest recon step, or bug bounty scoping.

1. **Scope:** list root domains, brands and acquisitions. Get written authorisation if it isn't your own asset.
2. **Subdomains:** `site:*.example.com -site:www.example.com`, then keep excluding what you find. Flag hosts named dev, staging, uat, jira, jenkins, grafana.
3. **Documents:** `site:example.com (ext:pdf | ext:docx | ext:xlsx | ext:pptx)`. Download, then `exiftool *.pdf` to collect author usernames, internal paths and software versions (this is what Metagoofil/FOCA automate).
4. **Leaky files:** `site:example.com (ext:env | ext:log | ext:bak | ext:sql | ext:conf | ext:old)` and `site:example.com inurl:.git`.
5. **Listings and errors:** `intitle:"index of"` plus the `intext:` error strings.
6. **Login surfaces:** `site:example.com inurl:login | intitle:"sign in"`. These feed later active testing.
7. **Off-site leaks:** the third-party `site:` query (#8).
8. **Record:** query → URL → data exposed → severity → owner → date found.
9. **Fix:** remove the file or put it behind authentication → return 404/410 → Search Console **Removals** for fast de-indexing → `noindex` / `X-Robots-Tag: noindex` for pages that must stay reachable → **rotate every exposed secret** (de-indexing doesn't un-leak it).
10. **Cross-check** in Bing (`ip:` for virtual hosts), crt.sh (subdomains), Wayback CDX (deleted files), GitHub code search (hard-coded secrets).

---

## Common mistakes, permissions & gotchas

- **robots.txt is not security.** `Disallow` stops crawling, not indexing: the URL can still be listed without a snippet. The file is public, so it hands attackers a list of paths. Use authentication plus `noindex`.
- **`Disallow` + `noindex` conflict:** if crawling is blocked, Google never reads the `noindex` tag.
- **De-indexing ≠ un-leaking.** Archives, scrapers and GHDB users may already have copies. Rotate credentials.
- **Result counts are estimates**, and results are personalised by location and account. Use a clean profile for evidence.
- **Syntax:** no space after the colon (`site:x`), `OR` must be uppercase, 32-word query limit.
- **Rate limits / CAPTCHAs**, worse from VPN/Tor exits. Scripted scraping breaks the ToS.
- **Dead operators** (`cache:`, `link:`, `related:`) still appear in old cheat-sheets and silently return junk.
- **Indexed ≠ live.** Verify a finding is still reachable before you report it.
- **Law and authorisation:** looking at what Google already shows is generally not intrusion. **Using** found credentials or knowingly downloading restricted data can be unauthorised access (US CFAA; India IT Act 2000 §43/§66; UK CMA). Stay in scope and read the bug bounty programme's rules on "publicly exposed data". (Not legal advice.)

---

## History & evolution

### Origin
- **2002:** Johnny Long (handle *j0hnny*) began collecting Google queries that revealed vulnerable systems or sensitive disclosures and called them **googleDorks**.
- **2004:** the list became the **Google Hacking Database (GHDB)**. Long presented "Google Hacking" at **Black Hat 2004**.
- **Dec 2004 / Feb 2005:** *Google Hacking for Penetration Testers* (Syngress, 448 pp; with contributions by Ed Skoudis and others).
- **2005:** DEF CON 13 talk; Black Hat EU 2005.
- **2007:** *Google Hacking for Penetration Testers, Vol. 2*.
- **2010:** Long handed the GHDB to **Offensive Security** (Exploit-DB, "GHDB Reborn", Nov 2010) when he left on a year-long volunteer mission. Long founded **Hackers for Charity**.
- **Dec 2015:** 3rd edition by Bill Gardner, Johnny Long and Justin Brown (234 pp).

### Concept history (the underlying idea)
| Period | Development |
|---|---|
| 1960s–80s | Boolean, field-restricted retrieval in library/online databases (e.g. DIALOG `TI=`, `AU=`). Dork operators are these field qualifiers applied to the web. |
| 1994 | Martijn Koster's Robots Exclusion Protocol (robots.txt), a politeness convention, standardised only in 2022 as **RFC 9309**. Never access control. |
| Mid-1990s | AltaVista brings `+`/`-` and field operators (`title:`, `url:`, `host:`, `link:`) to web search. |
| 1998+ | Google's `intitle:`, `inurl:`, `site:`, `filetype:` over the largest crawl, which made them worth exploiting. |
| 2002–2005 | googleDorks → GHDB → book and conferences. Automation: Foundstone SiteDigger, Gooscan, SensePost Wikto (via Google's SOAP Search API). |
| 2009–2013 | Shodan (2009) indexes service banners, not HTML. Stach & Liu (later Bishop Fox) SearchDiggity (2010) adds Bing dorking. Real-world abuse: a 2016 DOJ indictment describes an Iran-linked actor who found the Bowman Avenue Dam SCADA system (2013) partly through Google searches. |
| 2017 | `link:` / `info:` dropped. |
| 2019 | `before:` / `after:` added, the last new operators. |
| 2023 | `related:` removed. |
| Feb–Sep 2024 | Cache link removed (Search Liaison confirmed ~Feb 1 2024), then the `cache:` operator stopped working and its docs were deleted. Google pointed to the Internet Archive instead. |
| 15–17 Jan 2025 | JavaScript required for Google Search (later named **SearchGuard**). Every plain-HTTP scraper broke. |
| ~11 Sep 2025 | `&num=100` no longer honoured; top-100 takes 10 paginated requests. This also reset Search Console impression baselines. |
| Aug 2026 | Result links routed through opaque `google.com/goto` redirects (confirmed). |
| 2025–2026 | AI search: Perplexity explicitly supports `site:`, `filetype:`, `before:`, `after:` inside natural-language prompts. LLM answers are non-deterministic and summarised, so not evidence-grade. |

---

## How it works internally

1. **Crawl:** Googlebot follows links (and sitemaps) to anything reachable over HTTP(S) without authentication. It checks `robots.txt` before fetching, but a disallowed URL can still be *known* from inbound links.
2. **Parse:** HTML is split into fields (title, URL, body, anchor text). Office docs and PDFs are converted to text, which is why `[PDF]` results are searchable by `intext:`.
3. **Index:** an inverted index maps terms to documents **per field**. Operators like `intitle:` and `inurl:` are field-restricted lookups into that index, and `site:` / `filetype:` are document-attribute filters.
4. **Query:** the operators are intersected (AND by default, `OR`, `-` negation) and ranked. Counts are statistical estimates.
5. **Removal paths:** `noindex` meta or header (needs crawl access to be seen), 404/410 (drops on recrawl), Search Console Removals (temporary hide, about 6 months, fast), authentication (stops future indexing).

**Why it's passive:** you're querying Google's copy of the target, not the target. The only traffic the target sees comes when you *click through*, and that's where passive becomes active, and where authorisation starts to matter.

**Certainty note:** the crawl/index/field model is documented by Google Search Central. The exact ranking and estimation internals are proprietary and inferred.

---

## Why it's still used today

- Crawlers index whatever is reachable, and people keep publishing things by mistake, so the index is a free, pre-built **map of misconfigurations**.
- It sends **zero packets** to the target: stealthy for attackers, safe for production for defenders.
- It sits at the **passive recon layer** of the stack (ATT&CK Reconnaissance, PTES Intelligence Gathering), before active tools such as nmap, ffuf/gobuster and nuclei.
- It's still the opening move in most pentests and OSINT CTFs. The GHDB itself runs no code: it's a catalogue of human error at internet scale.
- Symmetry: if a dork can find your backup, so can an attacker, so defenders run the same queries.

---

## Cross-platform comparison: how other indexes solve "find exposed info about a target"

| Platform / index | What it indexes | Query style | Same as Google dorking? | Unique strength |
|---|---|---|---|---|
| **Google** | Web pages + document contents | `site: inurl: intitle: ext:` | — | Biggest crawl, document text |
| **Bing** | Web pages | similar + **`ip:`**, `inbody:` | Mostly same | Virtual-host discovery (`ip:`), no Google equivalent |
| **DuckDuckGo** | Mostly Bing's index + others | `site:`, `filetype:`, `!bangs` | Similar | No personalisation |
| **Yandex** | Web, strong in CIS | `host:`, `rhost:`, `mime:` | Similar | Regional coverage, reverse image |
| **Baidu** | Chinese web | `site:`, `filetype:` | Similar | China-hosted content |
| **Shodan / Censys / FOFA / ZoomEye / Netlas** | TCP/UDP banners, TLS certs, ports | `port:`, `product:`, `ssl.cert.subject.cn:` | **Different** (network layer) | Non-HTTP services, ICS/SCADA, cameras |
| **GitHub / GitLab / grep.app / Sourcegraph** | Source code | `org:`, `path:`, `language:` | Different | Hard-coded secrets, internal hostnames |
| **crt.sh / CT logs** | Issued TLS certificates | `%.example.com` | Different | Subdomains never crawled or linked |
| **Wayback Machine / CDX API** | Historical snapshots | `url=example.com/*` | Complementary | Deleted files, old endpoints (replaces `cache:`) |
| **LLM search (Perplexity etc.)** | Web via retrieval | Natural language + some operators | Partly | Summaries, but non-deterministic |

---

## Alternatives & companion tools

| Kind | Options |
|---|---|
| Other web engines | Bing, DuckDuckGo, Yandex, Baidu, Brave Search |
| Device/banner engines | Shodan, Censys, FOFA, ZoomEye, Netlas |
| Code search | GitHub/GitLab code search, grep.app, Sourcegraph |
| History | Wayback Machine + CDX API, archive.today |
| Certificates | crt.sh, CT log APIs (and subfinder, which aggregates them) |
| Automation | pagodo (GHDB runner), GooFuzz, theHarvester, Recon-ng, SpiderFoot, Metagoofil, FOCA, SearchDiggity, own: `fmfalgun/dork-runner` |
| Defensive SaaS | Attack-surface-management / digital-risk-protection platforms (continuous dork-style monitoring) |

---

## Role lens

### Penetration Tester / Red Teamer
- **Why:** Phase-0/1 recon in PTES Intelligence Gathering. Get usernames from document metadata, login portals, the tech stack, and staging hosts outside the WAF, with **no traces in target logs**.
- **Day to day:** run the audit flow above at the start of every engagement, then feed hosts and portals into active tooling.
- **Expert vs beginner:** experts chain 3–4 operators, **pivot** (an internal hostname in a PDF becomes the next `site:` query), cross-check Bing and Yandex because the indexes differ, and treat the GHDB as a set of ideas rather than a checklist. Real attackers do exactly this (Bowman Avenue Dam case).

### OSINT Analyst / Investigator
- **Why:** it's the cheapest way to pivot on people and organisations.
- **Day to day:** `"Firstname Lastname" (ext:pdf | ext:doc)`, `site:linkedin.com/in "Company"`, attendee lists, `before:`/`after:` timelines.
- **Expert:** archive each find immediately (results change and disappear). Log the exact query and timestamp for **chain of custody**. Search from a clean, non-personalised profile and location.

### Bug Bounty Hunter
- **Why:** finds forgotten in-scope assets that other hunters miss.
- **Day to day:** wildcard-scope dorks for `.env`, Swagger/OpenAPI (`inurl:swagger-ui`), `intitle:"index of"`, exposed backups.
- **Expert:** checks the asset is **still live** (indexed ≠ reachable), shows real impact, reads the programme's rules on "public data" findings, and dorks the target on **third-party SaaS** (Trello, Jira Cloud, Postman public workspaces), where duplicates are rare.

### SOC / Blue Team (Attack Surface Management)
- **Why:** catch leaks before attackers do.
- **Day to day:** a scheduled set of dorks per domain, alerting on new hits (`after:` makes the diff easy).
- **Expert:** tie each hit to a playbook (remove → 410 → Search Console removal → rotate secrets → root cause). Feed the same queries into ASM tooling. Use the GHDB's 14 categories as coverage areas for internal checks.

### Threat Intelligence Analyst
- **Why:** measure how exposed the internet is when a CVE drops ("advisory chasing").
- **Day to day:** dork the vulnerable product's login title or version string, and watch paste sites for organisation mentions.
- **Expert:** pairs Google counts with Shodan/Censys numbers (Google sees HTTP pages, Shodan sees banners), and expects attackers to run the same dorks within hours of a public PoC.

### Web Developer / SEO Engineer
- **Why:** you own what gets indexed. This is the defensive half of dorking.
- **Day to day:** `noindex`, `X-Robots-Tag` on PDFs and JSON, canonicals, sitemaps, Search Console Coverage and Removals, and `site:` audits.
- **Expert:** knows the `Disallow` + `noindex` conflict, gates staging behind authentication instead of robots.txt, treats `site:` counts as approximate, and knows the 2025 `&num=100` removal broke rank tracking and reset Search Console impression baselines.

### Journalist / Academic Researcher
- **Why:** precise primary-source discovery.
- **Day to day:** `site:gov.in ext:pdf "annual report"`, `site:sec.gov`, court and procurement documents, `before:`/`after:` for "what was said when".
- **Expert:** verifies documents against the original host and the Wayback Machine, and never cites an LLM summary instead of the source file.

### GRC / Privacy Officer
- **Why:** an indexed PII exposure is a reportable incident.
- **Day to day:** `site:example.com ext:xlsx intext:"PAN" | intext:"Aadhaar" | intext:"DOB"`.
- **Expert:** discovery starts breach-assessment clocks (GDPR 72 h; India's DPDP Act/Rules require notifying the Data Protection Board and affected people). Document the discovery date and evidence, and use Wayback to estimate when exposure began.

---

## Related topics, frameworks & certifications

- **Frameworks:** MITRE ATT&CK **T1593.002** (Search Open Websites/Domains: Search Engines); OWASP WSTG **WSTG-INFO-01** (Search Engine Discovery Reconnaissance for Information Leakage); PTES Intelligence Gathering; OSSTMM.
- **Certifications:** CEH (Footprinting & Reconnaissance), OSCP / PEN-200 (passive information gathering), PNPT, eJPT, CompTIA PenTest+ and Security+, SANS SEC487 / GIAC GOSI (OSINT).
- **Study areas:** OSINT, attack surface management, information retrieval (inverted indexes), web crawling and robots.txt (RFC 9309), SEO and indexing control, data-leak prevention, privacy law, CTFs.
- **Library cross-links:** VAPT Toolkit page → OSINT Frameworks → *Google dorking* (`dork-runner`); siblings: recon-ng, crt.sh, subfinder.

---

## Follow-up Q&A

No follow-up questions were asked in this session beyond the role pick (`all`) and the initial EXPLORE.

---

## Sources

- DeepStrike: Google Dorking: operators, risks and how to audit your site: https://deepstrike.io/blog/google-dorking
- CybelAngel: Google Hacking Database (GHDB) guide: https://cybelangel.com/blog/google-hacking-database-ghdb-guide/
- Exploit-DB GHDB: https://www.exploit-db.com/google-hacking-database
- Google hacking (Wikipedia mirror): https://bafybeiaysi4s6lnjev27ln5icwm6tueaw2vdykrtjkwiphwekaywqhcjze.ipfs.ipfs.hypha.coop/wiki/Google_hacking
- OSINTion: OSINT technique spotlight, Google: https://tidbit.theosintion.com/p/osint-technique-spotlight-google
- GBHackers: Google dorks list: https://gbhackers.com/latest-google-dorks-list/amp/
- HackerDNA: Google Dorking beginner's guide (2026): https://hackerdna.com/blog/google-dorking
- Elsevier: *Google Hacking for Penetration Testers*, 1st ed.: https://shop.elsevier.com/books/google-hacking-for-penetration-testers/long/978-1-931836-36-4
- Elsevier: 3rd ed.: https://shop.elsevier.com/books/google-hacking-for-penetration-testers/gardner/978-0-12-802964-0
- Help Net Security: review of the 3rd edition: https://www.helpnetsecurity.com/2016/01/19/review-google-hacking-for-penetration-testers-third-edition/
- InfoCon: DEF CON 13 talk: https://infocondb.org/con/def-con/def-con-13/google-hacking-for-penetration-testers
- Seonio: Google search operators (working/unreliable/deprecated): https://seonio.com/wiki/google-search-operators
- GreenGeeks: full operator list 2026: https://www.greengeeks.com/blog/google-search-operators-full-list-and-examples/
- MaxIntel: Google dorking reference 2026: https://maxintel.org/google-dorking-reference-2026.html
- Search Engine Journal: Google removes cache: operator docs: https://www.searchenginejournal.com/google-removes-cache-search-operator-documentation/528022/
- PPC Land: Google removes cache feature: https://ppc.land/google-removes-cache-feature-from-search-results/
- Serpent: Google Search now requires JavaScript: https://apiserpent.com/blog/google-search-requires-javascript
- Serpent: Google killed &num=100: https://apiserpent.com/blog/google-num-100-removed-rank-tracker-fix
- Serpent: Google SERP changes timeline 2024–2026: https://apiserpent.com/blog/google-serp-changes-timeline
- Traject Data: num=100 removal: https://trajectdata.com/navigating-googles-num100-removal-what-it-means-for-serp-monitoring/
- Google Search Central: search operators: https://developers.google.com/search/docs/monitor-debug/search-operators
- OWASP WSTG-INFO-01: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/01-Conduct_Search_Engine_Discovery_Reconnaissance_for_Information_Leakage
- MITRE ATT&CK T1593.002: https://attack.mitre.org/techniques/T1593/002/
- RFC 9309 (Robots Exclusion Protocol): https://www.rfc-editor.org/rfc/rfc9309
