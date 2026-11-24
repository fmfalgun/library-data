---
tool: whois
date: 2026-11-24
domains: [Networking, Internet Infrastructure, DNS & Domain Administration, Cybersecurity, OSINT, Threat Intelligence, Unix Tools]
roles: [Network Engineer, Penetration Tester / Red Teamer, SOC / Threat Intelligence Analyst, DNS / Domain Administrator, Linux System Administrator, Digital Forensics / Fraud Investigator, Internet Governance Researcher]
tags: [whois, rdap, rfc3912, port-43, icann, rir, arin, ripe, irr, radb, rpsl, epp, gdpr, osint, recon, abuse-contact, asn]
---

# whois

## Summary

`whois` is the client for the **WHOIS protocol** (RFC 3912): it opens TCP port 43 on a registry, registrar or Regional Internet Registry (RIR) server, sends one line, and prints the free-text record that comes back. It answers *who holds this domain / IP block / ASN, since when, through which registrar or registry, and whom do I contact (especially for abuse)*.

- **Protocol:** NICNAME/WHOIS, RFC 812 (1982), Ken Harrenstien and Vic White, SRI Network Information Center; last revised as RFC 3912 (2004).
- **Linux client:** Marco d'Itri's "intelligent" whois (written from scratch in 1999, C, GPL-2.0; 5.6.6 current in 2026). macOS/BSD ship the BSD client; Windows has Sysinternals whois.
- **Status in 2026:** ICANN ended the obligation for gTLD registries/registrars to run port-43 WHOIS on **28 January 2025** (except .com, .name, .post). Its successor is **RDAP** (HTTPS + JSON). Port 43 still works for most ccTLDs, the RIRs, IRRs (RADB) and services like Team Cymru. ARIN decided in October 2026 **not** to retire port 43 yet.
- Problem it solves in one line: find out who registered a domain, IP block or ASN, when, through whom, and whom to contact about it.

---

## Install / availability

| Platform | How |
|---|---|
| Debian / Ubuntu / Kali | `sudo apt install whois` (d'Itri's client; Debian tracker shows 5.6.6) |
| Arch / Alpine / Gentoo | `pacman -S whois` (5.6.6, built Feb 2026), `apk add whois`, `emerge net-misc/whois` |
| RHEL / Fedora | `dnf install whois` |
| macOS | `/usr/bin/whois` built in: the **BSD** client, with different flags and simpler referral logic |
| FreeBSD | built-in BSD `whois`; d'Itri's client in ports as `net/whois` |
| Windows | nothing built in; **Sysinternals Whois v1.21** (Mark Russinovich, Dec 2019), `choco install whois`. Usage: `whois [-v] domainname [whois.server]`, `-v` prints referral records |

- No root needed: it is a plain outbound TCP connection to port 43.
- Distro age matters: d'Itri has noted most distributions do not update the client in stable releases. Since **5.6.1** the client asks RIPE for **UTF-8**; older versions expect Latin-1. The built-in server table goes stale on old packages.

---

## How it works internally

RFC 3912 is the entire protocol:

1. Client connects to the server on **TCP 43**.
2. Client sends one query line terminated by **CRLF**.
3. Server returns free-form text and **closes the connection**.

No schema, no authentication, no encryption, no standard field names. You can do it by hand:

```bash
printf 'example.com\r\n' | nc whois.verisign-grs.com 43
```

**How d'Itri's client picks a server:** an internal table (regexes and TLD/IP/ASN ranges → server) that the author says is often more accurate than IANA's. Override order: `-h host` on the command line, then `/etc/whois.conf` (lines of `regex  server`, consulted before built-in rules), then the built-in table, then referral following (e.g. IANA → TLD registry → registrar for thin registries). Query strings are converted from the locale to IDN ASCII-compatible encoding (punycode).

**Thin vs thick registries:** `.com` (Verisign) is **thin**: the registry holds only domain, registrar, dates, status and name servers; contacts live at the registrar, so a full answer takes two hops (`Registrar WHOIS Server:` referral). Most other gTLDs are **thick**: the registry holds everything.

**Where the data comes from:** registrars push data to registries over **EPP** (RFC 5730/5731); RIRs keep their own databases (ARIN's object model: `NetRange`/`OrgId`/POCs; RIPE/APNIC/AFRINIC use **RPSL** objects: `inetnum`, `inet6num`, `aut-num`, `route`, `organisation`, `mntner`, `role`, `person`). All of it is **self-reported** by the registrant and not verified.

---

## Usage and commands

Sample outputs are trimmed and illustrative; live values will differ.

### 1. Domain lookup

```
$ whois example.com
   Domain Name: EXAMPLE.COM
   Registry Domain ID: 2336799_DOMAIN_COM-VRSN
   Registrar WHOIS Server: whois.iana.org
   Updated Date: 2025-08-14T07:01:39Z
   Creation Date: 1995-08-14T04:00:00Z
   Registry Expiry Date: 2026-08-13T04:00:00Z
   Registrar: RESERVED-Internet Assigned Numbers Authority
   Registrar IANA ID: 376
   Domain Status: clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited
   Domain Status: clientTransferProhibited ...
   Name Server: A.IANA-SERVERS.NET
   DNSSEC: signedDelegation
```

### 2. See the referral chain

```
$ whois --verbose example.com      # or -I to start at whois.iana.org
Using server whois.iana.org.
Query string: "example.com"
refer:        whois.verisign-grs.com
...
```

### 3. IP lookup

```
$ whois 8.8.8.8
NetRange:       8.8.8.0 - 8.8.8.255
CIDR:           8.8.8.0/24
NetName:        GOGL
NetType:        Direct Allocation
Parent:         NET8 (NET-8-0-0-0-0)
Organization:   Google LLC (GOGL)
OrgAbuseEmail:  network-abuse@google.com
RegDate:        2023-12-28
```

### 4. ASN lookup

`whois AS15169`: ASN holder, organisation, contacts.

### 5. Query a specific server

`whois -h whois.ripe.net 193.0.6.139` (wrong auto-pick, mirrors, IRRs). `-p PORT` for non-standard ports.

### 6. RIPE-style server flags (always after `--`)

```bash
whois -h whois.ripe.net -- -B 193.0.6.139              # unfiltered (show emails)
whois -h whois.ripe.net -- -r -T inetnum 193.0.6.139   # no contact recursion, only inetnum objects
whois -h whois.ripe.net -- -i mnt-by RIPE-NCC-MNT      # inverse lookup: all objects with this maintainer
whois -h whois.ripe.net -- -M 193.0.0.0/16             # all more-specific blocks (-m one level, -L/-l less specific)
whois -h whois.ripe.net -- -x 193.0.0.0/21             # exact match only
whois -h whois.ripe.net HELP                           # full flag reference (RIPE-223)
```

The man page: options meant for a non-standard server should follow the `--` separator; RIPE-specific options are ignored for non-RIPE servers.

### 7. Map an organisation's announced prefixes from the IRR (RADB)

```
$ whois -h whois.radb.net -- '-i origin AS15169' | grep -E '^route6?:'
route:      8.8.8.0/24
route:      34.0.0.0/15
...
```

### 8. IP to ASN with Team Cymru (live BGP view)

```
$ whois -h whois.cymru.com " -v 8.8.8.8"
AS      | IP       | BGP Prefix  | CC | Registry | Allocated  | AS Name
15169   | 8.8.8.8  | 8.8.8.0/24  | US | arin     | 2023-12-28 | GOOGLE, US
```

Bulk mode: `printf 'begin\nverbose\n1.1.1.1\n8.8.8.8\nend\n' | nc whois.cymru.com 43`.

### 9. Hide legal boilerplate

`whois -H example.com`, or `export WHOIS_HIDE=1`.

### 10. Override server selection

`/etc/whois.conf`, e.g. `\.dev$  whois.nic.google`.

### Cheat sheet

| Goal | Command |
|---|---|
| Domain record | `whois -H domain.tld` |
| Follow referrals, show servers | `whois --verbose domain.tld` / `whois -I domain.tld` |
| IP owner + abuse | `whois IP \| grep -Ei 'netrange\|cidr\|org\|abuse\|country'` |
| ASN | `whois ASnnnn` |
| Specific server | `whois -h server -- 'query'` |
| All prefixes of an AS (IRR) | `whois -h whois.radb.net -- '-i origin ASnnnn'` |
| IP → ASN (BGP) | `whois -h whois.cymru.com " -v IP"` |
| Same data via RDAP | `curl -s https://rdap.org/domain/x.com \| jq` / `rdap x.com` |
| Raw protocol | `printf 'q\r\n' \| nc server 43` |

---

## Output and fields explained

### Domain records (gTLD format)

- **`Registry Domain ID`**: the registry's internal ROID. Stays the same for the life of a registration and changes if the domain is dropped and re-registered, so it is a cheap way to detect that a domain changed hands.
- **`Registrar WHOIS Server`**: referral target for thin registries.
- **`Creation Date`**: when the *current* registration was created, not when the name first existed. A very recent date is the main phishing signal.
- **`Updated Date`**: last change of the registry object (often contact, NS or status edits). Bumps can line up with takeovers.
- **`Registry Expiry Date`**: from the registry; the registrar's own expiry can differ during auto-renew / renew-grace periods.
- **`Domain Status`**: EPP status codes (RFC 5731). `client*` codes are set by the registrar and `server*` codes by the registry.
  - `clientTransferProhibited`: normal anti-hijack lock.
  - `clientDeleteProhibited` / `clientUpdateProhibited`: further locks; `server*` versions = registry lock (strongest).
  - `clientHold` / `serverHold`: domain removed from the zone (resolves NXDOMAIN while registered).
  - `pendingDelete`, `redemptionPeriod`, `autoRenewPeriod`: lifecycle; the domain is about to drop or was just renewed.
  - `ok` / `active`: no restrictions.
- **`Name Server`**: the delegation in the parent zone, not necessarily what `dig NS` returns from the child. A mismatch points to lame delegation.
- **`DNSSEC: signedDelegation`**: a DS record exists at the parent; `unsigned` means none.
- **Contacts**: since GDPR (2018) usually `REDACTED FOR PRIVACY`. Redaction is the default now, not a red flag.

### IP / ASN records (ARIN format; RIPE equivalents in brackets)

- **`NetRange` / `CIDR`** (`inetnum` / `inet6num`): the registered block.
- **`NetName`** (`netname`): label chosen by the holder.
- **`NetType`** (`status`): `Direct Allocation` / `Direct Assignment` = ARIN gave it straight to this org; `Reallocated` / `Reassigned` = an ISP sub-delegated it to a customer, so the real user is one level down. RIPE: `ALLOCATED PA`, `ASSIGNED PA`, `ASSIGNED PI`, `SUB-ALLOCATED PA`, etc.
- **`Parent`**: the enclosing block; walking parents shows the allocation hierarchy.
- **`OriginAS`** (`origin` in `route` objects): AS the holder says originates the block (self-asserted).
- **`Organization`** (`org`): holder organisation handle.
- **`OrgAbuseEmail`** (`abuse-c` → `abuse-mailbox`): where abuse reports go. This is the field sysadmins actually use.
- **`RegDate` / `Updated`** (`created` / `last-modified`): record dates.
- **`mnt-by`** (RIPE): maintainer object that authorises changes; pivot for inverse lookups.

---

## One realistic task: triage a suspicious domain from a proxy log

```bash
D=login-micros0ft-support.com
whois -H "$D" | grep -Ei 'creation|registrar:|status|name server|abuse'   # 1. age, registrar, registrar abuse contact
dig +short "$D" A                                                          # 2. where it points
whois -H 203.0.113.50 | grep -Ei 'netrange|cidr|org|abuse|country'         # 3. who hosts that IP
whois -h whois.cymru.com " -v 203.0.113.50"                               # 4. which ASN routes it
curl -s https://rdap.org/domain/$D | jq '.events, .entities[].roles'      # 5. structured JSON via RDAP
```

Reading it: a creation date only days old, a budget registrar, a bulletproof-looking ASN and redacted contacts add up to a strong phishing indicator. The registrar abuse contact (step 1) and the hosting abuse contact (step 3) are the two takedown routes. Save raw outputs with timestamps if this may become evidence.

---

## Common mistakes, permissions and gotchas

- **gTLDs may stop answering on port 43.** Since 28 Jan 2025 gTLD registries/registrars are no longer required to run WHOIS or web WHOIS (except .com, .name, .post); 74 gTLD registries shut theirs down in February 2025, and registrars like Spaceship retired port 43 on 18 March 2026. "Connection refused" or an empty answer → use RDAP.
- **Redacted contacts** (GDPR, ICANN Temporary Specification 2018): normal; non-public data via ICANN's RDRS or legal process.
- **Rate limits / blocks**: RIRs and registries throttle; RIPE blocks clients that pull too many personal objects.
- **Non-standard output**: every registry and RIR has its own field names; parsing is fragile. Use RDAP JSON for automation.
- **Outbound TCP 43 is often blocked** by corporate firewalls.
- **Untrusted input**: the man page warns the command-line parser may have buffer overflows; don't pass untrusted data from scripts.
- **macOS BSD client** has different shortcut flags (`-a` ARIN, `-r` RIPE, etc.) and simpler referral logic.
- **Old distro packages** carry stale server tables and Latin-1 assumptions.
- **Self-reported data**: names, addresses and dates are not verified.
- **Current ≠ historical**: the live record says nothing about who held the domain last month.
- No root or special capabilities required.

---

## History and evolution

| Year | Milestone |
|---|---|
| 1977 | RFC 742, NAME/FINGER (Ken Harrenstien, SRI-KL): the one-line query model WHOIS borrows |
| 1982 | RFC 812, NICNAME/WHOIS (Harrenstien and Vic White, SRI NIC); port 43; directory of ARPANET people and hosts |
| 1985 | RFC 954 revision (Harrenstien, Stahl, Feinler) |
| 1990s | NIC splits into InterNIC/Network Solutions and the RIRs (RIPE NCC, APNIC, ARIN; later LACNIC, AFRINIC). WHOIS becomes a distributed set of servers, so clients need referral logic. RWhois (RFC 2167) attempts hierarchy |
| 1998–99 | ICANN formed; registrars must publish WHOIS. RPSL (RFC 2622) defines RIPE-style objects. Marco d'Itri writes his Linux client (1999) |
| 2004 | RFC 3912 (L. Daigle): last update; describes only the transport |
| 2012–15 | IETF WEIRDS working group; RDAP RFCs 7480–7484 (HTTPS + JSON, IANA bootstrap) |
| 2018 | GDPR and ICANN Temporary Specification → mass redaction of contacts |
| 26 Aug 2019 | All gTLD registries/registrars must run RDAP alongside WHOIS |
| 2022–23 | RDAP consolidated in RFCs 9082, 9083, 9224 |
| 7 Aug 2023 | ICANN Global Amendment takes effect, setting the WHOIS Services Sunset Date 18 months later |
| 28 Jan 2025 | WHOIS sunset for gTLDs (obligation ends; .com, .name, .post excepted) |
| Feb 2025 | 74 gTLD registries shut down WHOIS (ICANN reachability scan) |
| Jun 2025 | RDAP queries overtake WHOIS (gTLD RDAP ~7 bn/month in Jan 2025 → 65 bn in Aug 2025) |
| Feb 2026 | d'Itri's whois 5.6.6 released (Debian, Arch) |
| Mar 2026 | Spaceship retires its port-43 service (example of registrars switching off) |
| Aug–Oct 2026 | ARIN consults on retiring Whois-RWS, RWhois and port 43 (proposed port 43 date 1 Jan 2029 or later). Outcome (21 Oct 2026): RWhois retired 365 days after a migration tool ships; Whois-RWS only after RDAP parity; **port 43 not retired now**, revisited once RDAP adoption milestones are met |

**The sunset nuance (Internet governance):** 28 Jan 2025 ended a *contractual obligation* for gTLDs; it did not switch off a protocol. ccTLDs and RIRs answer to their own communities, not ICANN, which is why port 43 will survive for years in places.

---

## Why it's used today

- **Zero dependencies, instant**: one TCP line; works from any box, even with `nc`.
- **Still served** by most ccTLD registries, some gTLD registries, all RIRs, IRRs.
- **Muscle memory and automation**: ARIN notes port 43 remains heavily used by cybersecurity professionals, researchers and law enforcement.
- **IRRs (RADB, RIPE) and Team Cymru speak WHOIS** with no real RDAP equivalent for those uses.
- **Place in the stack**: the out-of-band *ownership* layer next to DNS (`dig`, where a name points) and BGP (looking glasses, `bgp.he.net`, who routes it).

---

## Cross-platform comparison

| | WHOIS (port 43) | RDAP | Web lookup (ICANN / RIR) | Sysinternals whois | Commercial APIs |
|---|---|---|---|---|---|
| Transport | TCP 43, cleartext | HTTPS | HTTPS | TCP 43 | HTTPS |
| Output | free text | JSON (RFC 9083) | HTML | text | JSON |
| Finding the right server | client's table / IANA referral | IANA bootstrap files (RFC 9224) | built in | follows referrals (`-v`) | vendor-side |
| Auth / tiered access | none | possible (OAuth etc.) | none | none | API key |
| i18n | messy (Latin-1 vs UTF-8) | UTF-8 | yes | — | yes |
| History | no | no | no | no | yes |
| gTLD support in 2026 | unreliable | mandatory | yes | unreliable | yes |

### How other platforms solve the same problem

- **Windows**: Sysinternals `whois.exe`; PowerShell `Invoke-RestMethod https://rdap.org/domain/example.com` (RDAP JSON → objects); WSL with the Linux client.
- **macOS**: built-in BSD `whois`; Homebrew `whois` (d'Itri's); RDAP clients.
- **Web / cloud**: `lookup.icann.org` (RDAP front end), each RIR's web search (ARIN, RIPE DB, APNIC), `bgp.he.net`.
- **Android / iOS**: assorted WHOIS/RDAP apps; in practice the web lookups.
- **Non-public data**: ICANN RDRS (Registration Data Request Service) to request redacted data from registrars.

---

## Alternatives

| Tool | Platform | Notes |
|---|---|---|
| `rdap` (OpenRDAP) | Linux/macOS/Windows | Go RDAP client, bootstrap-aware |
| `icann-rdap` | cross-platform | ICANN's Rust RDAP client/library |
| `nicinfo` | cross-platform | ARIN's Ruby RDAP client |
| `curl https://rdap.org/...` + `jq` | any | rdap.org redirects to the authoritative server |
| BSD `whois` | macOS, *BSD | built in, simpler |
| `jwhois` | Linux | GNU client, abandoned |
| `nc host 43` | any | raw protocol |
| Sysinternals `whois` | Windows | v1.21 (2019) |
| lookup.icann.org, RIR web UIs | web | no install |
| DomainTools, WhoisXML API, SecurityTrails | web/API | **historical** WHOIS (pre-GDPR data, ownership timelines), paid |
| `bgpq4` | Linux | builds router prefix filters from IRR data (uses the same RPSL/IRR sources) |

---

## Role: Network Engineer

- **Why it matters:** IP and ASN ownership, peering and NOC contacts, checking a prefix is registered before announcing or filtering it.
- **Day to day:** `whois ASnnnn`; `-i origin ASnnnn` on RADB/RIPE to build prefix filters (often automated with `bgpq4`); checking `NetType` to see who really holds a block; finding upstream NOC contacts during incidents.
- **Expert knowledge:** IRR data is self-asserted and often stale; RPKI ROAs are what route origins are validated against. RIR object models differ (ARIN `NetRange/OrgId` vs RIPE `inetnum/organisation/mntner`). Allocation vs assignment (PA vs PI) decides who can route a block.

## Role: Penetration Tester / Red Teamer

- **Why it matters:** passive, legal reconnaissance that never touches the target (PTES / OSINT phase 1).
- **Day to day:** take the org's names, emails and maintainer handles and inverse-query RIPE (`-i mnt-by`, `-i org`, `-i admin-c`) to find every netblock; pivot on registrant data and name servers to find sibling domains; IRR `route` objects for scoping.
- **Expert knowledge:** check scope against `Reassigned` blocks. An IP in the client's range may belong to a cloud or ISP customer, and testing it without authorization is illegal. Historical WHOIS (paid sources) recovers pre-GDPR emails for pivoting. RDAP and WHOIS lookups are themselves logged by registries; heavy querying can be noticed and rate-limited.

## Role: SOC / Threat Intelligence Analyst

- **Why it matters:** domain age, registrar and hosting ASN are fast reputation signals.
- **Day to day:** enrich alerts with creation date, registrar, status and hosting ASN; pivot through shared name servers or registrant handles.
- **Expert knowledge:** after GDPR, registrant pivoting mostly died, so pivot on name servers, SOA emails, TLS certificate SANs and passive DNS. RDAP's `events` array (registration, last changed, expiration) parses reliably; WHOIS text doesn't.

## Role: DNS / Domain Administrator

- **Why it matters:** expiry, locks, delegation, transfers.
- **Day to day:** confirm `clientTransferProhibited` (and ideally a registry lock) on critical domains; check expiry is far out; compare `Name Server` lines with the zone after a migration.
- **Expert knowledge:** registry and registrar views can differ; the thin `.com` model means two hops; `serverHold` / `clientHold` take a domain out of DNS, so when `dig` says NXDOMAIN on a registered domain, look for those codes first.

## Role: Linux System Administrator

- **Why it matters:** working out who is brute-forcing SSH and where to report it.
- **Day to day:** `whois <ip> | grep -i abuse`; fail2ban actions can mail abuse contacts automatically using whois.
- **Expert knowledge:** cloud providers usually ignore the RIR abuse mailbox in favour of their own web forms; abuse reports rarely change much, so blocking by ASN or prefix (Team Cymru data) works better.

## Role: Digital Forensics / Fraud Investigator

- **Why it matters:** attribution and timelines for phishing and brand impersonation.
- **Day to day:** record each lookup (timestamp + raw output) as evidence; use historical WHOIS for the registrant at the time of the fraud; request redacted data through RDRS or the registrar with legal process.
- **Expert knowledge:** the current record says nothing about last month's holder; `Registry Domain ID` changes reveal re-registrations; registrar `Updated Date` bumps often line up with takeover events.

## Role: Internet Governance Researcher

- **Why it matters:** WHOIS is a 40-year case study in privacy versus accountability.
- **Focus:** ICANN Temporary Specification, EPDP and Registration Data Policy; the 2025 sunset; RIR decisions such as ARIN's 2026 consultation; RDRS.
- **Expert knowledge:** the sunset ended a gTLD *contractual obligation*, not the protocol; ccTLDs and RIRs follow their own communities; RDAP's tiered access is the technical hook for differentiated (authenticated) access to non-public data.

---

## Related topics (where it applies)

1. OSINT and footprinting: CEH (module 2), OSCP / PEN-200 information gathering, SANS SEC487, PTES pre-engagement/intelligence gathering.
2. CompTIA Network+, Security+, PenTest+.
3. Threat intelligence: GIAC GCTI, infrastructure pivoting, phishing analysis.
4. DNS and domain management: registries, registrars, EPP, DNSSEC delegation.
5. BGP and routing security: IRR, RPSL, RPKI, MANRS, prefix filtering.
6. Incident response and abuse handling.
7. Internet governance: ICANN, RIRs, GDPR, Registration Data Policy.
8. Protocol design: one-line text protocols vs REST/JSON, service bootstrap (RFC 9224).

---

## Follow-up Q&A

No follow-up questions were asked in this session beyond the initial EXPLORE answer (roles: all seven).

---

## Sources

[1] L. Daigle, "WHOIS Protocol Specification," RFC 3912, IETF, Sep. 2004. [Online]. Available: https://www.rfc-editor.org/rfc/rfc3912

[2] K. Harrenstien and V. White, "NICNAME/WHOIS," RFC 812, Mar. 1982. [Online]. Available: https://www.rfc-editor.org/rfc/rfc812

[3] K. Harrenstien, "NAME/FINGER," RFC 742, Dec. 1977. [Online]. Available: https://www.rfc-editor.org/rfc/rfc742 (accessed Nov. 24, 2026).

[4] "WHOIS," Wikipedia (via Wikiwand). [Online]. Available: https://www.wikiwand.com/en/WHOIS (accessed Nov. 17, 2026).

[5] M. d'Itri, "whois — Intelligent WHOIS client," GitHub. [Online]. Available: https://github.com/rfc1036/whois (accessed Nov. 17, 2026).

[6] Debian Package Tracker, "whois." [Online]. Available: https://tracker.debian.org/whois (accessed Nov. 17, 2026).

[7] Arch Linux, "whois 5.6.6-1." [Online]. Available: https://archlinux.org/packages/extra/x86_64/whois/ (accessed Nov. 17, 2026).

[8] M. d'Itri, post on RIPE db-wg mailing list about UTF-8 since 5.6.1. [Online]. Available: https://mailman.ripe.net/archives/list/db-wg@ripe.net/message/FWM7FL4HHDL555FZG47SYOQNVUP5ND4J/ (accessed Nov. 17, 2026).

[9] whois(1) manual page, Arch Linux. [Online]. Available: https://man.archlinux.org/man/whois.1.en (accessed Nov. 17, 2026).

[10] whois(1) manual page, root.cz. [Online]. Available: https://www.root.cz/man/1/whois/ (accessed Nov. 17, 2026).

[11] M. Russinovich, "Whois v1.21," Microsoft Sysinternals, Dec. 2019. [Online]. Available: https://learn.microsoft.com/en-us/sysinternals/downloads/whois (accessed Nov. 17, 2026).

[12] ICANN, "RDAP FAQs." [Online]. Available: https://www.icann.org/en/contracted-parties/registry-operators/registration-data-access-protocol/rdap-faqs-31-08-2018-en (accessed Nov. 17, 2026).

[13] ICANN, "Reminder: effective date of Base Registry Agreement Specification 13 amendment," Jul. 2023. [Online]. Available: https://new.icann.org/en/system/files/files/reminder-effective-date-base-agreement-spec-13-27jul23-en.pdf

[14] IETF Blog, "Current state of RDAP." [Online]. Available: https://ietf.org/blog/current-state-of-rdap/ (accessed Nov. 17, 2026).

[15] CaptainDNS, "RDAP vs WHOIS: the complete guide to the transition," Mar. 17, 2026. [Online]. Available: https://www.captaindns.com/en/blog/rdap-vs-whois-complete-guide

[16] Spaceship, "Announcement: TCP WHOIS (Port 43) service sunset." [Online]. Available: https://www.spaceship.com/blog/tcp-whois-sunset/

[17] ARIN, "Consultation on the Future of ARIN's Directory Services," Aug. 14, 2026. [Online]. Available: https://www.arin.net/announcements/20260814/

[18] ARIN, "Results of Consultation on the Future of ARIN Directory Services," Oct. 21, 2026. [Online]. Available: https://www.arin.net/announcements/20261021/

[19] K. McDonald, "WHOIS is dead, long live RDAP," Jan. 6, 2026. [Online]. Available: https://kmcd.dev/posts/whois-from-scratch/

[20] Linux Magazine, "Query domain information with RDAP," 2024. [Online]. Available: https://www.linux-magazine.com/index.php/Issues/2024/282/RDAP

[21] Internet Society, "Marco d'Itri" (author bio). [Online]. Available: https://internetsociety.org/author/marcoditri ; RIPE 85 speaker bio: https://ripe85.ripe.net/speakers/marco-ditri

[22] NPR, "Google Launches Closed Captioning For YouTube," Nov. 2009 (interview with Ken Harrenstien). [Online]. Available: https://www.npr.org/transcripts/124501330

Notes on certainty: package versions, ICANN sunset dates, gTLD shutdown counts, RDAP growth figures, ARIN's consultation and outcome, Sysinternals details and the d'Itri / Harrenstien biographies were checked against the sources above. Sample outputs (`example.com`, `8.8.8.8`, RADB, Team Cymru), RIPE flag details, EPP status meanings, RFC 954 co-authors, and the BSD client's flags and 1980s origin come from general knowledge and were not re-verified in this session.
