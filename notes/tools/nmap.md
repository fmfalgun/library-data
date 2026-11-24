---
tool: nmap
includes: NSE (Nmap Scripting Engine), Zenmap, Ncat, Nping, Ndiff
date: 2026-11-24
explored: 2026-11-17
domains: [Networking, Cybersecurity (offensive & defensive), Systems/Network Administration, Compliance/Auditing, Security Research]
roles:
  - Penetration Tester / Red Teamer
  - Network Engineer
  - SOC / Blue Team Analyst
  - Vulnerability Management / Security Engineer
  - System Administrator / SRE
  - NSE Script Developer / Security Tool Developer
  - Compliance / GRC Auditor
  - Internet Measurement Researcher
tags: [nmap, nse, lua, port-scanning, host-discovery, os-fingerprinting, service-detection, recon, vapt, phase-2-scanning, npcap, tcp, rfc793]
---

# nmap (+NSE)

## Summary
Nmap ("Network Mapper") is a free, source-available network scanner. It finds which hosts are up, which ports they expose, which software and version is behind each port, and which OS they run. The **Nmap Scripting Engine (NSE)** extends it with Lua scripts for enumeration, brute-forcing and vulnerability checks. Gordon "Fyodor" Lyon released it in 1997 in *Phrack* #51, and it is still the reconnaissance backbone of almost every security assessment.

- **Current version:** the nmap.org changelog lists **7.99 (2026-03-26)** as the newest entry. A `v7.991` source tag exists, and a third-party download site claims 7.991 shipped on 6 Aug 2026 (OpenSSL 3.0.21, Zenmap profile-crash fix). That is unverified on nmap.org.
- **Licence:** the Nmap Public Source License (NPSL) since 7.90 (2020). Earlier releases used GPLv2 with exceptions.
- **The problem in one line:** find hosts, ports, services and OSes on a network, then script deeper checks.

---

## Install / availability
| Platform | How |
|---|---|
| Debian/Ubuntu/Kali | `sudo apt install nmap` |
| Fedora/RHEL | `sudo dnf install nmap` (stuck on 7.92; see gotchas) |
| Arch | `sudo pacman -S nmap` |
| macOS | `brew install nmap`, or the official .dmg (Zenmap, Ncat, Ndiff included) |
| Windows | Official installer, which bundles **Npcap** (needed for raw packets) and Zenmap |
| Android | Termux `pkg install nmap` (raw scans need root) |
| *BSD/Solaris | Ports/packages (OpenBSD packages 7.99) |
| Source | `./configure && make && sudo make install` |

**Distro version gotcha:** Fedora 44 (CVE-2026-58058 fix in July 2026) and SUSE (SLE 15 SP7 / 16.0) still ship **7.92**. The cause is *inferred* to be the NPSL licence change, which these distros did not accept as open source. The freeze itself is a fact. On those distros you miss five years of fingerprints and scripts unless you install the upstream RPM.

---

## Usage & commands (with sample outputs)
Sample outputs are representative of the real format and have been trimmed.

### 1. Host discovery only: `-sn`
```
$ sudo nmap -sn 192.168.1.0/24
Nmap scan report for router.lan (192.168.1.1)
Host is up (0.0021s latency).
MAC Address: 3C:84:6A:11:22:33 (TP-Link Technologies)
Nmap done: 256 IP addresses (14 hosts up) scanned in 2.31 seconds
```
- On a local LAN as root it uses **ARP**, which is why the MAC address and vendor appear (the vendor comes from `nmap-mac-prefixes`).
- Off-LAN it sends ICMP echo, TCP SYN to 443, TCP ACK to 80 and ICMP timestamp.
- As non-root it falls back to TCP connect to 80/443.

### 2. Default scan (SYN "half-open")
```
$ sudo nmap 10.0.0.5
PORT     STATE    SERVICE
22/tcp   open     ssh
80/tcp   open     http
443/tcp  closed   https
3306/tcp filtered mysql
Not shown: 996 closed tcp ports (reset)
```
- It scans the **top 1000 TCP ports** (ranked by frequency in `nmap-services`), not all ports.
- `SERVICE` is a **port-number lookup**, not detection.
- `Not shown ... (reset)` gives the reason the ports were collapsed.

### 3. Service/version detection: `-sV`
```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 9.6p1 Ubuntu 3ubuntu13.5 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    nginx 1.24.0 (Ubuntu)
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```
- It sends probes from `nmap-service-probes` and matches the replies against regex `match` lines.
- `--version-intensity 0-9` trades speed against depth. The default is 7.
- The CPE strings are what vulnerability tooling maps to CVEs.

### 4. OS detection: `-O`
```
Device type: general purpose
Running: Linux 5.X|6.X
OS details: Linux 5.0 - 6.2
Network Distance: 1 hop
```
- It needs one open and one closed port to be reliable. Otherwise it warns `OSScan results may be unreliable`.
- `-A` = `-O -sV -sC --traceroute`.

### 5. NSE default scripts: `-sC` / `--script default`
```
22/tcp open ssh
| ssh-hostkey:
|   256 aa:bb:...:ff (ECDSA)
|_  256 11:22:...:99 (ED25519)
80/tcp open http
|_http-title: Admin Login
|_http-server-header: nginx/1.24.0
```
`|` lines are script output. `|_` marks the last line of a script's block.

### 6. Targeted NSE with arguments
```
nmap -p445 --script smb-os-discovery,smb2-security-mode 10.0.0.20
nmap -p443 --script ssl-enum-ciphers example.com
nmap -p80 --script http-enum --script-args http-enum.basepath=/app/ 10.0.0.5
nmap --script "vuln and safe" 10.0.0.5        # boolean category expressions
nmap --script-help ssl-enum-ciphers           # docs for one script
nmap --script-updatedb                         # after adding/removing scripts or changing categories
```

### 7. UDP: `-sU`
```
$ sudo nmap -sU --top-ports 50 10.0.0.1
53/udp  open          domain
123/udp open          ntp
161/udp open|filtered snmp
```
- UDP scans are slow because Linux rate-limits ICMP port-unreachable to about 1 per second.
- Add `-sV` so protocol-specific probes turn `open|filtered` into `open`.

### 8. All ports, fast
```
sudo nmap -p- --min-rate 2000 -T4 -n -Pn 10.0.0.5
```
- `-p-` covers ports 1 to 65535.
- `-n` skips DNS.
- `-Pn` skips host discovery and treats the host as up (use when ICMP is blocked).

### 9. Reasons
`--reason` shows the evidence for each state: `syn-ack`, `reset`, `no-response`, `port-unreach ttl 63`.

### 10. Output and diffing
```
$ nmap -sV -oA scans/web-2026-11-17 10.0.0.0/24   # .nmap .gnmap .xml
$ ndiff scans/web-2026-11-10.xml scans/web-2026-11-17.xml
-10.0.0.7:
+3389/tcp open ms-wbt-server
```
- XML is the machine-readable format consumed by Metasploit (`db_nmap`), Faraday, Dradis and custom parsers.
- `xsltproc scan.xml -o report.html` renders an HTML report.

---

## Output / fields explained
### Port states
| State | Meaning |
|---|---|
| `open` | An application accepted the connection (SYN/ACK) |
| `closed` | Reachable, but nothing is listening (RST) |
| `filtered` | No reply or an ICMP unreachable came back; a firewall is likely, but loss or rate limiting are also possible |
| `unfiltered` | ACK scan only: reachable, but open/closed is unknown |
| `open\|filtered` | UDP/FIN/NULL/Xmas scans: silence is ambiguous |
| `closed\|filtered` | Idle scan only |

### Other fields
- **`MAC Address: … (Vendor)`**: only for targets on the same L2 segment. The vendor comes from the OUI lookup in `nmap-mac-prefixes`.
- **`Not shown: N closed tcp ports (reset)`**: collapsed ports, with the reason.
- **`SERVICE` (without -sV)**: a guess from `nmap-services`.
- **`VERSION`**: a `nmap-service-probes` match, often including a distro patch string (e.g. `3ubuntu13.5`).
- **`CPE`**: the Common Platform Enumeration identifier used for CVE mapping.
- **`Network Distance`**: hop count derived from TTL.
- **`ttl 63` in `--reason`**: the reply came from one hop away. When it differs from the open ports' TTL, a firewall in front of the host may be answering instead.
- **Script output `|` / `|_`**: NSE results nested under the port (portrule) or under "Host script results" (hostrule).

---

## Realistic task: audit a /24 and baseline it
```bash
# 1. Who's alive (keep the list)
sudo nmap -sn 10.10.20.0/24 -oG - | awk '/Up$/{print $2}' > live.txt

# 2. Full TCP sweep, fast, no version detection yet
sudo nmap -iL live.txt -p- --min-rate 3000 -n -Pn -oA step2-allports

# 3. Extract open ports and do deep checks only on those
ports=$(grep -oP '\d+/open' step2-allports.gnmap | cut -d/ -f1 | sort -un | paste -sd,)
sudo nmap -iL live.txt -p "$ports" -sV -sC -O --reason -oA step3-deep

# 4. Targeted NSE on interesting findings
nmap -p443,8443 --script ssl-enum-ciphers,ssl-cert -iL live.txt -oA step4-tls
nmap -p445 --script smb-security-mode,smb2-security-mode,smb-vuln-ms17-010 -iL live.txt

# 5. Next week: rerun step 3 and diff
ndiff step3-deep.xml step3-deep-nextweek.xml
```
How each role uses the result:
- The pentester uses steps 3 and 4 to choose attack paths.
- The network engineer reads `filtered` vs `closed` to check ACLs.
- Vulnerability management schedules step 5.
- GRC files the XML as evidence.

---

## NSE (Nmap Scripting Engine)
- **Language:** embedded Lua **5.4** in current versions (it was 5.2 around 7.40). Scripts live in `/usr/share/nmap/scripts/*.nse` and libraries in `nselib/`.
- **Size:** the 7.90 release notes (2020) counted 601 scripts. There are a few more today.
- **Activation:** `-sC` (the default category) or `--script <names|categories|expressions|paths>`. Use `--script-args` / `--script-args-file` for arguments and `--script-trace` / `-d` for debugging.
- **Categories:** `auth, broadcast, brute, default, discovery, dos, exploit, external, fuzzer, intrusive, malware, safe, version, vuln`.
- **Rules:** `prerule` (before the scan), `hostrule` (per host), `portrule` (per port), `postrule` (after the scan).
- **Key libraries:** `shortport`, `stdnse`, `http`, `smb`, `smb2`, `ldap`, `snmp`, `tls`, `brute`, `creds`, `vulns`, `comm`.
- **Scope:** nmap's own docs say it is not a comprehensive vulnerability scanner, but NSE can handle demanding vulnerability checks.
- **Intro video:** Fyodor and David Fifield at Black Hat/Defcon 2010, https://nmap.org/presentations/BHDC10/

### Minimal custom script
```lua
-- http-xpoweredby.nse
local shortport = require "shortport"
local http = require "http"
description = [[Reports the X-Powered-By header.]]
categories = {"discovery", "safe"}
portrule = shortport.http
action = function(host, port)
  local r = http.get(host, port, "/")
  return r and r.header and r.header["x-powered-by"]
end
```
Run it with `nmap -p80 --script ./http-xpoweredby.nse target`.

---

## Common mistakes, permissions and gotchas
- **Root vs non-root:** without raw socket privileges (root / CAP_NET_RAW), `-sS`, `-O`, `-sU` and ARP discovery are unavailable, and nmap silently uses `-sT` (a full connect, which the application logs). Windows needs Npcap. WSL1 has no raw sockets.
- **Top 1000 is not all ports:** high-port services (8443, 10250, 27017...) are missed without `-p-`.
- **`filtered` is not proof of a firewall:** it can also be loss or rate limiting. Use `--reason` and retries.
- **`-T5` / a high `--min-rate` lose accuracy:** dropped probes show up as `filtered`.
- **NSE categories:** `intrusive`, `brute`, `dos` and `exploit` can lock accounts or crash fragile devices (OT/ICS, printers, old switches). `vuln` is not automatically safe.
- **Reverse DNS:** forgetting `-n` on big ranges wastes time.
- **VM NAT/VPN:** scanning through them distorts results.
- **Legal:** unauthorised scanning is illegal or a contract breach in many places (e.g. CFAA in the US, IT Act s.43/66 in India). `scanme.nmap.org` is the official practice target.
- **Stale distro packages:** see Install.

---

## History & evolution
### Origin
- **Author:** Gordon "Fyodor" Lyon.
- **First release:** 1 September 1997, *Phrack* #51 article 11, "The Art of Port Scanning". Linux-only C at first.
- **The problem:** the scanners of the day (strobe, SATAN modules, one-offs) each did a single technique. Nmap unified SYN, FIN, Xmas, NULL, fragmentation and decoys.
- **Organisation:** Nmap Project / Insecure.Com LLC.
- **Notable contributors:** David Fifield, Daniel Miller (current lead maintainer of much of the code), Patrick Donnelly (NSE), Ron Bowes (SMB/NSE libraries), Diman Todorov (original NSE, via Google Summer of Code).
- **Funding:** for 20+ years the project has been funded by OEM licences (companies redistributing Nmap/Npcap in products) plus commercial support. This explains the licence history.

### Timeline
| Year | Milestone |
|---|---|
| 1981 | RFC 793 (TCP) defines how stacks respond to SYN/FIN/stray packets; every stealth scan exploits these rules. RFC 9293 (2022) supersedes it |
| 1995 | SATAN (Farmer & Venema) and strobe pioneer automated service scanning |
| 1997 | Nmap released in Phrack #51 |
| 1998 | Phrack #54: remote OS detection via TCP/IP stack fingerprinting. Antirez publishes the idle scan (hping), later `-sI` |
| 2000s | Windows port. Passive fingerprinting (p0f) appears elsewhere. Version detection (3.45, 2003). 2nd-gen OS detection (4.20, 2006) |
| 2007–08 | NSE ships (4.50); Zenmap replaces NmapFE |
| 2008 | Book *Nmap Network Scanning* |
| 2009–10 | Ncat, Nping, Ndiff join the suite. NSE talk at Black Hat/Defcon 2010 |
| 2012 | Nmap 6: full IPv6 |
| 2013 | ZMap and masscan: stateless internet-wide scanning splits off |
| 2015 | Nmap 7.00 (19 Nov): TLS vulnerability scripts (Heartbleed, POODLE, FREAK) |
| 2020 | 7.90: Npcap 1.0, NPSL licence, 601 NSE scripts |
| 2025 | 7.96 (May): parallel forward DNS, Npcap 1.82. Then 7.97 (May), 7.98 (Aug) |
| 2026 | 7.99 (26 Mar). Possible 7.991 point release (Aug, unverified) |

### Why it's used today
- **One engine, many techniques:** raw packets via libpcap/Npcap and libdnet, with a TCP-like congestion controller (cwnd, RTT estimates, retransmits) that adapts to lossy networks.
- **Crowd-sourced databases:** `nmap-os-db`, `nmap-service-probes`, `nmap-mac-prefixes`, `nmap-services`.
- **NSE turns a scanner into a framework.**
- **Stable XML output** is the de-facto input format for the security stack.
- **Ecosystem position:** passive recon (Shodan/Censys, DNS) → fast sweep (masscan/rustscan) → **nmap deep scan + NSE** → vulnerability scanner (Nessus/OpenVAS) → exploitation (Metasploit).

---

## How it works internally
- **Packet I/O:** crafts raw IP packets (libdnet/raw sockets) and reads replies via libpcap (Linux/macOS BPF) or Npcap (Windows NDIS driver).
- **SYN scan:** sends SYN. A SYN/ACK means open and nmap answers RST (the kernel does too, since it never opened the socket). An RST means closed. Silence or ICMP type 3 means filtered.
- **FIN/NULL/Xmas:** RFC 793 says a closed port answers a non-SYN with RST and an open port stays silent. Windows and some stacks ignore this, which makes these scans unreliable against them.
- **Timing engine:** `-T0` to `-T5` templates set `--min/max-rtt-timeout`, `--max-retries`, `--scan-delay` and parallelism. A dynamic congestion window shrinks on loss.
- **OS detection:** a fixed probe set (SEQ ×6, OPS, WIN, ECN, T1–T7, U1 to a closed UDP port, IE ICMP echoes). It measures ISN patterns, IP ID sequence, TCP options order, window sizes, DF and TTL, then scores the fingerprint against `nmap-os-db`.
- **Version detection:** NULL probe first (wait for a banner), then probes ranked by `rarity` and port hints, with `match`/`softmatch` regexes. SSL is detected and wrapped automatically.
- **NSE runtime:** each script/target pair is a Lua coroutine. Socket calls yield to **Nsock** (non-blocking, event-driven), so hundreds run concurrently without threads. Shared state goes through `nmap.registry`, and ordering through `dependencies`.

---

## Cross-platform comparison
| Platform | Mechanism | Same as nmap? | Difference |
|---|---|---|---|
| Linux nmap | Raw sockets + libpcap | — | Reference point |
| Windows | Npcap NDIS driver, or plain Winsock connect (Test-NetConnection) | Same with Npcap | Without Npcap: connect scans only |
| macOS | BPF devices (`/dev/bpf*`) | Same | Needs root / ChmodBPF |
| Android / iOS | App sandbox, no raw sockets without root/jailbreak | Partly | Connect scans, mDNS/ARP-cache discovery (Fing) |
| AWS / Azure / GCP | Config analysis (security groups, NACLs, routes): AWS Inspector network reachability, Azure Network Watcher, GCP Connectivity Tests | No | Answers "*could* this be reachable" without sending packets |
| Shodan / Censys | Continuous internet-wide ZMap-style scanning plus banner grabs | Concept only | Passive for you, historic data, public IPs only |
| Masscan / ZMap | Stateless SYN with state encoded in the sequence number | Partly | Millions of packets per second, no deep service/OS/NSE work |

---

## Alternatives
- **Linux/Unix:**
  - masscan, zmap (internet scale)
  - rustscan, naabu (fast port discovery, often piped into nmap)
  - unicornscan, hping3 (packet crafting)
  - `nc -zv` (quick checks)
  - arp-scan (L2 discovery only; see `arp-scan` in this library)
  - `ss` / `netstat` (the *local* listener view)
- **Vulnerability scanners:** Nessus, OpenVAS/Greenbone, Nuclei (templates, HTTP-heavy), Qualys.
- **Windows:** `Test-NetConnection -Port`, PortQry, Advanced IP Scanner, Angry IP Scanner (cross-platform).
- **macOS:** the old Network Utility port scan (removed in recent macOS), `nc`, nmap itself.
- **Android:** Fing, "Network Mapper" nmap front-ends, Termux.
- **iOS:** Fing, iNetTools (connect-only because of sandboxing).
- **Web/cloud:** Shodan, Censys, ZoomEye (passive), cloud reachability analysers.

---

## Role lens

### Penetration Tester / Red Teamer
- **Why it matters:** step one of every internal and external engagement. NSE does a lot of enumeration for free: SMB shares and signing, LDAP rootDSE, HTTP titles, TLS issues.
- **Day to day:** the staged workflow above, `-oA` for reports, `db_nmap` inside Metasploit, `smb-enum-*` and `ldap-rootdse` scripts, and brute scripts kept under control.
- **Expert vs beginner:**
  - Beginners run `-A -T5` on everything.
  - Experts do a fast discovery pass, then a narrow deep pass.
  - They tune `--max-retries`, `--host-timeout` and `--min-hostgroup`.
  - For evasion they use `--data-length`, `-f`, `--source-port 53`, `-D` decoys and `--scan-delay` (mostly legacy-IDS evasion now).
  - They know `-sV` is noisier than `-sS`, and that EDR/NDR flags nmap's default probes and the NSE User-Agent (override with `--script-args http.useragent=`).

### Network Engineer
- **Why it matters:** it tests the network from outside rather than trusting the configuration.
- **Day to day:**
  - Verifying firewall/ACL changes: `filtered` (dropped) vs `closed` (host RST).
  - `-sA` to map stateful vs stateless filtering.
  - `--traceroute`.
  - SNMP checks (`snmp-info`, `snmp-interfaces`).
  - Broadcast scripts (`broadcast-dhcp-discover`, `broadcast-ospf2-discover`).
- **Expert vs beginner:**
  - Experts read TTLs in `--reason` (`ttl 63` vs `64`) to see whether a firewall one hop earlier answered.
  - They know ICMP rate limiting distorts UDP results.
  - They scan from several vantage points (inside a VLAN, across the core, from the internet).

### SOC / Blue Team Analyst
- **Why it matters:** attackers use it, so its signatures are worth knowing. Defenders use it to confirm exposure.
- **Day to day:**
  - Spotting SYN-without-ACK bursts over the top 1000 ports.
  - Recognising `-sV` probe strings and the "Nmap Scripting Engine" User-Agent.
  - Suricata/Snort `ET SCAN` rules.
  - Quick "is it really open" checks after alerts.
- **Expert vs beginner:**
  - Experts tell nmap from masscan/ZMap by timing, IP ID, TCP options, window sizes and the fixed `-O` probe sequence (T1–T7, U1, IE).
  - They know `-D` decoys mean not every logged source IP is the attacker.

### Vulnerability Management / Security Engineer
- **Why it matters:** cheap, scriptable discovery feeding asset inventory and CVE matching via CPE.
- **Day to day:** scheduled cron/CI scans, `ndiff` baselines, `vulners`/`vulscan` NSE scripts, `ssl-enum-ciphers` for TLS posture, XML into a database.
- **Expert vs beginner:**
  - A banner is not a vulnerability: distros backport fixes, so "OpenSSH 8.2p1 Ubuntu-4ubuntu0.11" may be patched.
  - NSE `vuln` hits are leads to confirm.
  - Size scan windows and rates so production isn't disturbed.

### System Administrator / SRE
- **Why it matters:** catches unintended exposure such as debug ports, databases bound to 0.0.0.0 and forgotten admin panels.
- **Day to day:** `nmap -sT -p- host` from another box after a deploy, compared with `ss -tulpn` on the host. Ncat for quick tests.
- **Expert vs beginner:**
  - The gap between `ss` (locally bound) and nmap (remotely reachable) is the firewall's real behaviour.
  - Scanning your own cloud IPs can trip provider abuse detection.

### NSE Script Developer / Security Tool Developer
- **Why it matters:** NSE is a sandboxed, parallel networking runtime with protocol libraries already written (`http`, `smb`, `smb2`, `ldap`, `snmp`, `tls`, `brute`, `creds`, `shortport`, `stdnse`, `vulns`).
- **Day to day:**
  - Writing `portrule` + `action` scripts.
  - `stdnse.output_table()` for structured XML output.
  - The `vulns` library for standard reports.
  - `--script-trace` and `-d` for debugging.
  - Contributing via GitHub `nmap/nmap`.
- **Expert vs beginner:**
  - Every socket call yields to Nsock, so never block. Use `nmap.new_socket()`/`comm`, not LuaSocket.
  - Use `nmap.registry` and `dependencies`, and respect timeouts.
  - Pick categories honestly, because users rely on `safe`.

### Compliance / GRC Auditor
- **Why it matters:** objective, repeatable exposure evidence. Relevant controls include PCI-DSS segmentation testing (req. 11.4.5), ISO 27001 Annex A 8.20/8.21, and CIS Controls 1/4/12.
- **Day to day:** reviewing XML/HTML reports (`xsltproc`), tracking diffs over time, checking that scope and authorisation are documented.
- **Expert vs beginner:** experts check the method as well as the result: vantage point, `-p-` coverage, UDP coverage, timing. A clean top-1000-TCP-only result is weak segmentation evidence.

### Internet Measurement Researcher
- **Why it matters:** nmap's fingerprint databases and congestion-control design are reference points in the literature. Its slowness at internet scale is why ZMap and masscan exist.
- **Day to day:** ZMap/masscan for candidates, nmap or ZGrab for deep follow-up on samples, opt-out lists, rate caps.
- **Expert vs beginner:**
  - Nmap keeps per-probe state (accurate, slow).
  - ZMap encodes state in packet fields and scans IPv4 in under an hour at 1 Gbps.
  - Scanning ethics (from the ZMap paper): rate limits, an explanatory web page on the scanning IP, honouring opt-outs.

---

## Related topics
- **Subjects:** TCP/IP and RFC 793/9293 behaviour, network reconnaissance, firewall testing, OS fingerprinting, attack-surface management, IDS signatures, Lua scripting, scanning ethics and law (CFAA, India IT Act s.43/66).
- **Certifications/curricula:** CompTIA Network+, Security+, CySA+, PenTest+; EC-Council CEH; OffSec OSCP (PEN-200); eJPT; PNPT; GIAC GPEN/GCIH; Cisco CyberOps Associate; TryHackMe/HTB nmap rooms.
- **Related library entries:** `arp-scan` (L2 discovery; also via `nmap -sn -PR`).

---

## Follow-up Q&A
No follow-up questions were asked in this session. The exploration covered the role pick (all 8 roles) and the full Block A and Block B answer. Suggested future deep dives: `-O` probe internals, the timing engine, idle scan mechanics, writing a `vulns`-library NSE script, and the NPSL licence story.

---

## Sources
- Nmap Changelog: https://nmap.org/changelog
- Nmap Scripting Engine, chapter 9: https://nmap.org/nse
- NSE man section: https://nmap.org/book/man-nse.html
- NSE script docs: https://nmap.org/nsedoc/
- scripting.xml in the v7.991 tag (mirror; Lua 5.4): https://gitverse.ru/githubmirror/nmap/tag/v7.991/docs/scripting.xml
- Nmap 7 announcement: https://nmap.org/7/
- Nmap 7.90 announcement (601 scripts, OEM funding, licence): https://seclists.org/nmap-announce/2020/1
- Fedora 44 nmap 7.92 advisory: https://linuxsecurity.com/advisories/fedora/fedora-44-nmap-2026-3b30fa1da4
- SUSE Package Hub nmap: https://packagehub.suse.com/packages/nmap/
- OpenBSD nmap 7.99 package: https://www.openbsdhandbook.com/packages/current/net/nmap/
- Nmap 7.96 coverage: https://cybersecuritynews.com/nmap-7-96-released/
- Techdows (7.991 claim, unverified): https://techdows.com/?p=18038
- Phrack #51 "The Art of Port Scanning" (1997) and Phrack #54 "Remote OS detection via TCP/IP Stack FingerPrinting" (1998): http://phrack.org/
