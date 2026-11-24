---
tool: resolvectl
date: 2026-11-24
domains: [Networking, DNS, Linux, Cybersecurity]
roles: [Network Engineer, Network Administrator, Cybersecurity Expert]
tags: [dns, systemd, systemd-resolved, split-dns, vpn, dns-leak, llmnr, mdns, dnssec, dns-over-tls, linux]
---

# resolvectl

## Summary

`resolvectl` is the command-line client of **systemd-resolved**, the local DNS resolver service on most modern Linux systems. The tool itself does little work: it talks to the daemon over D-Bus. The daemon resolves names, caches answers, and keeps DNS servers and routing domains **per network interface (link)**. With `resolvectl` you see which DNS server and which link a lookup really used, resolve names the way applications do, change per-link DNS at runtime, and flush, inspect and monitor the cache.

- Problem it solves: one global `/etc/resolv.conf` cannot describe a machine with Wi-Fi, Ethernet and a VPN at once; resolved keeps DNS per link and routes each domain to the right servers.
- Availability: any Linux distribution with systemd-resolved (default on Ubuntu, Fedora 33+ and others). Not on Windows, macOS or Android, which have their own equivalents (see the comparison).
- Same binary also answers as `resolvconf` for old VPN scripts.

---

## Usage and commands

Syntax: `resolvectl [OPTIONS...] {COMMAND} [NAME...]` [1]. The **Since** column is the systemd version that added each item, from the systemd 261 manual [1]; check yours with `resolvectl --version`.

### 1. Inspect state

| Command | What it does | Since |
|---|---|---|
| `resolvectl status [LINK…]` | Global and per-link DNS settings (default command) | 239 |
| `resolvectl statistics` | Resolver statistics (transactions, cache, DNSSEC verdicts) | 239 |
| `resolvectl reset-statistics` | Reset statistics counters (root) | 239 |
| `resolvectl monitor` | Stream local resolution queries and responses | 252 |
| `resolvectl show-cache` | Current cache content per scope | 254 |
| `resolvectl show-server-state` | Detailed state per DNS server | 255 |
| `resolvectl log-level [LEVEL]` | Show or change the daemon's log level | 244 |

### 2. Look things up

| Command | What it does | Since |
|---|---|---|
| `resolvectl query example.com` | Forward lookup (A and AAAA) | 239 |
| `resolvectl query 85.214.157.71` | Reverse (PTR) lookup | 239 |
| `resolvectl -t MX query example.com` | Low-level lookup of one record type | 239 |
| `resolvectl service _xmpp-server._tcp gmail.com` | DNS-SD and SRV services | 239 |
| `resolvectl tlsa tcp example.org:443` | TLSA records (DANE) | 239 |
| `resolvectl openpgp user@example.org` | OPENPGPKEY records | 239 |

If a parameter is an IPv4/IPv6 address, the reverse lookup is done. Output reports the protocol used, the interface the data came from, and whether the data could be authenticated (DNSSEC-validated, or from trusted local sources such as `/etc/hosts` and `localhost`) [2].

### 3. Change per-interface DNS at runtime

| Command | What it does | Since |
|---|---|---|
| `resolvectl dns eth0 1.1.1.1 9.9.9.9` | Get/set per-link DNS servers | 239 |
| `resolvectl domain wg0 '~corp.test'` | Get/set per-link search/route domains (`~` = routing only) | 239 |
| `resolvectl domain wg0 '~.'` | Route **all** DNS through wg0 | 239 |
| `resolvectl default-route wg0 yes` | Whether a link may be a default DNS route | 239 |
| `resolvectl llmnr eth0 no` | Per-link LLMNR mode | 239 |
| `resolvectl mdns eth0 no` | Per-link Multicast DNS mode | 239 |
| `resolvectl dnssec eth0 yes` | Per-link DNSSEC mode | 239 |
| `resolvectl dnsovertls eth0 yes` | Per-link DNS-over-TLS mode | 239 |
| `resolvectl nta eth0 lab.local` | Per-link DNSSEC negative trust anchors | 239 |
| `resolvectl revert eth0` | Reset per-link DNS configuration | 239 |
| `resolvectl dns eth0 ""` | `dns`, `domain` and `nta` take a single empty string to clear their lists [3] | 239 |

- Runtime changes are lost when the link resets; make them permanent in NetworkManager, or in a systemd-networkd `.network` file.
- Older manual editions say these commands fail on interfaces managed by systemd-networkd (configure those in their `.network` files). That wording came from an unofficial mirror; check `man resolvectl` on your version.
- Values and their effects are documented in systemd.network(5) [6].

### 4. Cache and server maintenance

| Command | What it does | Since |
|---|---|---|
| `resolvectl flush-caches` | Flush all local DNS caches (≈ sending SIGUSR2 to systemd-resolved) [4] | 239 |
| `resolvectl reset-server-features` | Forget learned server feature levels; probing restarts on next lookup (≈ SIGRTMIN+1) | 239 |

### 5. Options

| Option | What it does | Since |
|---|---|---|
| `-4` / `-6` | IPv4 or IPv6 only | 239 |
| `-i IFACE` | Run the query on one interface | 239 |
| `-p dns\|llmnr\|mdns` | Limit lookup protocols (`help` lists values) | 239 |
| `-t TYPE` / `-c CLASS` | Record type / class for `query` | 239 |
| `--legend=no` | Hide headers and metadata | 239 |
| `--search=no` | Disable search domains for single-label names | 239 |
| `--cname=no` | Error instead of following CNAME/DNAME | 239 |
| `--raw[=payload\|packet]` | Dump answers as binary | 239 |
| `--service-address=`, `--service-txt=` | Control extra lookups for `service` | 239 |
| `--cache=no` | Bypass the local cache | 248 |
| `--validate=no` | Disable DNSSEC validation for this query | 248 |
| `--network=no` | Forbid network requests (local answers only) | 248 |
| `--synthesize=no` | Do not synthesize special names (`localhost`, etc.) | 248 |
| `--zone=no` | Ignore locally registered LLMNR/mDNS records | 248 |
| `--trust-anchor=no` | Ignore local DNSSEC trust anchors for DS/DNSKEY | 248 |
| `--stale-data=no` | Forbid answers from expired records | 254 |
| `--relax-single-label=yes` | Send single-label names upstream | 256 |
| `--json=pretty\|short\|off`, `-j` | JSON output | not stated |
| `--no-pager`, `--no-ask-password`, `-h`, `--version` | Script-friendly / help | not stated |

### 6. Combinations admins use

```bash
resolvectl status                                 # which server/link for what
resolvectl query --cache=no example.com           # fresh answer, skip cache (248+)
resolvectl query -i wg0 -p dns intranet.corp      # force one link, plain DNS only
resolvectl query --validate=no broken-dnssec.tld  # is DNSSEC the cause of the failure?
resolvectl --legend=no -t TXT query example.com   # clean output for scripts
resolvectl status --json=pretty                   # machine-readable state
sudo resolvectl monitor                           # live query log (252+)
resolvectl flush-caches                           # after changing records or servers
```

Related commands around it:

```bash
cat /etc/systemd/resolved.conf                    # global config (DNS=, LLMNR=, DNSSEC=, DNSOverTLS=)
ls -l /etc/resolv.conf                            # symlink to the stub = apps use 127.0.0.53
getent hosts example.com                          # what applications get (through NSS)
dig example.com                                   # direct query, bypasses resolved's rules
systemctl status systemd-resolved
journalctl -u systemd-resolved
```

### 7. resolvconf compatibility mode

Invoked as `resolvconf` [1]:
- `-a`: register per-interface DNS data from stdin (resolv.conf format)
- `-d`: unregister (like `revert`)
- `-f`: ignore missing interfaces with `-a`/`-d`
- `-x`: partially supported; maps to an extra `~.` domain
- `-p`: do not use the interface as default route (since 257)
- `-m`: accepted and ignored; most other resolvconf options are unsupported and fail

### 8. Common mistakes and gotchas

- Trusting `dig` to reflect what apps see: it ignores split-DNS routing domains. Compare with `resolvectl query` or `getent hosts`.
- Runtime `resolvectl dns/domain` changes vanish on reconnect; persist them in the network manager.
- Changing DNS records and forgetting the local cache: run `flush-caches`.
- Containers: the host's `/etc/resolv.conf` points at 127.0.0.53, which inside a container means the container's own loopback. Point them at `/run/systemd/resolve/resolv.conf` (the real upstream list) instead.
- Setting commands, `monitor` and `reset-statistics` need root (or polkit authorization).
- Newer commands (`monitor`, `show-cache`, `show-server-state`) don't exist on older LTS systems.

---

## Output and fields explained: `DNS Domain: ~.`

In `resolvectl status`, **`DNS Domain: ~.`** on a link makes it a **routing domain for the DNS root**: all DNS queries are routed to this link's DNS servers.

- **`~` (tilde)** = routing-only domain. resolved uses it to pick which link's servers answer a query. It is **not** appended to short names: `~example.com` routes `*.example.com` lookups to this link, but `ping foo` does not try `foo.example.com` (a plain `example.com` without `~` would be both a search and a routing domain).
- **`.` (dot)** = the DNS root; every name sits under it.
- **`~.` together** matches every domain, so this link's servers become the default route for all lookups.

**Why you see it:** almost always a **VPN** (WireGuard, OpenVPN, NetworkManager VPNs, Tailscale with an exit node). It sets `~.` so all DNS goes through the tunnel and does not leak to the local or ISP resolver. The `resolvconf -x` compatibility flag maps to exactly this.

**Most specific match wins** when several links have domains:

| Query | Link with `~corp.local` | Link with `~.` |
|---|---|---|
| `git.corp.local` | chosen (more specific) | |
| `google.com` | | chosen |

If **no** link has `~.`, queries matching no routing domain go to every link that has DNS servers and `DefaultRoute=yes`.

**Set it manually:**

```bash
sudo resolvectl domain wg0 '~.'      # route all DNS via wg0
sudo resolvectl default-route wg0 yes
```

Persistent, in a systemd-networkd `.network` file:

```ini
[Network]
DNS=10.0.0.1
Domains=~.
```

Check which link a query used: `resolvectl query example.com`.

---

## History and evolution

| When | What happened |
|---|---|
| 1970s – 1983 | Every host kept a copy of one central `HOSTS.TXT` (SRI-NIC). It stopped scaling; DNS was designed (RFC 882/883 in 1983, later RFC 1034/1035). |
| 1980s – 2000s | The BIND resolver library went into libc, configured by one global `/etc/resolv.conf` (`nameserver`, `search`). NSS (`/etc/nsswitch.conf`, from Solaris) chained sources: `hosts: files dns`. |
| 2000s | Laptops, Wi-Fi and VPNs broke the one-file model. Stopgaps: `resolvconf` (Debian) and `openresolv` merged per-interface settings; `dnsmasq` and `nscd` added caching. |
| 2014 (systemd 215) | First systemd-resolved, "Network Name Resolution manager", copyright 2014 Tom Gundersen [7]. |
| 19 Aug 2014 (systemd 216) | Lennart Poettering's release announcement: systemd-resolved "is now a pretty complete caching DNS and LLMNR stub resolver"; D-Bus APIs for hostnames, addresses and arbitrary RRs; a `systemd-resolve-host` tool added to query it [8]. |
| Feb 2016 (systemd 229) | The `systemd-resolve` client tool, previously experimental, improved; resolved synthesizes RRs from `/etc/hosts` [9]. DNSSEC validation lands in the same era. NetworkManager gains a mode to push its per-link DNS into resolved (requested by Poettering, Feb 2016) [10]. |
| 2018 (systemd 239) | `resolvectl` replaces `systemd-resolve` as the main client; DNS-over-TLS support arrives around the same time. |
| 2016 – 2020 | Distributions adopt it as default: Ubuntu in its 16.10 – 18.04 era, Fedora 33 (2020). |
| 244 – 256 | `log-level` (244); per-query flags `--cache`, `--validate`, `--network`, `--synthesize`, `--zone`, `--trust-anchor` (248); `monitor` (252); `show-cache`, `--stale-data` (254); `show-server-state` (255); `--relax-single-label` (256); resolvconf `-p` (257). |
| Today (systemd 26x) | Stub listeners on 127.0.0.53 and 127.0.0.54 [11]; a native Varlink API on `/run/systemd/resolve/io.systemd.Resolve` alongside D-Bus [12]. |

### Why the concept arrived (what `/etc/resolv.conf` could not do)

| Problem | Why `resolv.conf` failed |
|---|---|
| Multiple networks (Wi-Fi + VPN + Ethernet) | One global server list, no per-interface settings |
| Programs fighting | dhclient, NetworkManager and VPN scripts each overwrote the file |
| VPN split DNS (`*.corp` to the VPN, rest to the ISP) | No domain-to-server routing at all |
| No caching | Every lookup hit the network unless nscd/dnsmasq was added |
| No local DNSSEC or encryption | The libc resolver is deliberately minimal |

### Why Linux uses it now

- Fits dynamic networking: Wi-Fi roaming, VPNs up and down, Docker bridges.
- Proper split DNS through routing domains; helps prevent DNS leaks.
- One place to look (`resolvectl status`) instead of guessing which daemon rewrote resolv.conf.
- Shared local cache: faster lookups.
- Security hooks: DNSSEC validation, DNS-over-TLS.
- **Not universal:** Debian servers, Alpine, minimal Arch and many container images still use plain resolv.conf. Some admins disable resolved because the 127.0.0.53 stub has confused Docker, VPN scripts and DNSSEC edge cases.

---

## How it works internally

```
App (curl, firefox ...)
   │  getaddrinfo()
   ▼
glibc → NSS (/etc/nsswitch.conf) → nss-resolve ──┐
   or /etc/resolv.conf → 127.0.0.53 (stub) ──────┤
                                                 ▼
                                     systemd-resolved
                        (cache, per-link DNS, routing domains,
                         DNSSEC, DNS-over-TLS, LLMNR, mDNS)
                                                 │
            ┌──────────────┬─────────────────────┼───────────────┐
            ▼              ▼                     ▼               ▼
        eth0 DNS       wlan0 DNS          wg0 (VPN) DNS    mDNS / LLMNR (LAN)
```

- **Three ways in:** the `nss-resolve` NSS module (preferred, over D-Bus/Varlink), the stub listener on 127.0.0.53 for programs that read `/etc/resolv.conf`, and the native D-Bus and Varlink APIs [12].
- **`/etc/resolv.conf` modes:** symlink to `/run/systemd/resolve/stub-resolv.conf` (apps use the stub), to `/run/systemd/resolve/resolv.conf` (apps talk to upstream servers directly, bypassing resolved), or managed by another package, in which case resolved reads it for configuration [13].
- **Configuration sources:** global `/etc/systemd/resolved.conf` (and `.conf.d/` drop-ins), per-link static settings in `/etc/systemd/network/*.network`, and per-link runtime settings pushed by NetworkManager, networkd, VPN clients or `resolvectl` [11].
- **Routing:** for each query resolved picks the link(s) whose routing domain is the longest suffix match; with no match it uses links with `DefaultRoute=yes`.
- **resolvectl** is only a client of these APIs; signals do the same for some actions (SIGUSR2 = flush caches, SIGRTMIN+1 = reset server features).

---

## Cross-platform comparison

Every major OS converged on the same design: a local resolver daemon with a cache, servers per network, domain-based routing for split DNS, link-local names, and encrypted DNS.

### How other platforms solve the same problem

- **Windows:** DNS Client service (`Dnscache`) caches for the whole system. Split DNS uses the **NRPT** (Name Resolution Policy Table), the equivalent of `~corp.example`, pushed by VPNs and DirectAccess. Server choice follows interface metrics, plus "smart multi-homed name resolution" that can query several interfaces at once (a known DNS-leak source). LLMNR and NetBIOS are being phased out; native DoH in Windows 11 and Server 2022.
  - Commands: `ipconfig /all`, `ipconfig /displaydns`, `ipconfig /flushdns`, `Resolve-DnsName`, `Get-DnsClientServerAddress`, `Get-DnsClientNrptPolicy`, `Get-DnsClientCache`, `Clear-DnsClientCache`.
- **Android:** apps never read resolv.conf. Bionic libc hands lookups to `netd` and the **DnsResolver** module (updatable through Play system updates since Android 10). DNS is kept per **Network object**; a VPN can capture DNS per app (per UID). **Private DNS** (DNS-over-TLS) since Android 9; DoH for some providers later.
  - Commands: `adb shell dumpsys dnsresolver`, `adb shell dumpsys connectivity`; Settings → Network → Private DNS.
- **macOS / iOS:** `mDNSResponder` handles unicast DNS and Bonjour (mDNS). Scoped resolvers per interface plus per-domain resolvers; split DNS via files in `/etc/resolver/<domain>`. Encrypted DNS through configuration profiles (iOS 14 / macOS 11+).
  - Commands: `scutil --dns`, `dscacheutil -q host -a name example.com`, `sudo killall -HUP mDNSResponder`.
- **OpenBSD / FreeBSD:** `unwind` (OpenBSD) and `local_unbound` (FreeBSD) as local validating resolvers; `resolvconf` manages the file. Tools: `unwindctl`, `local-unbound-control`.

### Same vs different

| Aspect | Linux (resolved) | Windows | macOS | Android |
|---|---|---|---|---|
| Unit of configuration | Link | Interface + NRPT policy | Scoped resolver | Network object + UID |
| Split DNS | `~domain` routing domains | NRPT | `/etc/resolver/<domain>` | VPN / per-network routing |
| Legacy path | 127.0.0.53 stub + resolv.conf | n/a | resolv.conf (informational only) | none |
| Encrypted DNS | DoT (no native DoH as far as known) | DoH | DoH / DoT via profiles | DoT (Private DNS), some DoH |
| Link-local names | LLMNR, mDNS | LLMNR, NetBIOS, mDNS | mDNS (Bonjour) | mDNS (limited) |
| Replaceable? | Yes | No | No | No |
| Inspect with | `resolvectl status` | `ipconfig /all`, PowerShell | `scutil --dns` | `dumpsys dnsresolver` |

---

## Alternatives

### On Linux

| Tool | Role |
|---|---|
| `/etc/resolv.conf` + glibc | Classic minimal setup |
| `resolvconf` / `openresolv` | Merge per-interface DNS into resolv.conf |
| `dnsmasq` | Lightweight cache/forwarder (common under NetworkManager) |
| `unbound` | Full validating, caching recursive resolver |
| `nscd` | Name-service cache daemon (older) |
| `stubby`, `dnscrypt-proxy`, `cloudflared` | Encrypted DNS proxies (DoT, DNSCrypt, DoH) |
| `nmcli` | Configure DNS through NetworkManager |
| `dig`, `host`, `nslookup`, `drill`, `kdig` | Query servers directly, **bypassing** the system resolver |
| `getent hosts name` | Resolve exactly as applications do (NSS) |

### On other platforms

See the cross-platform section: Windows DNS Client + NRPT, macOS/iOS mDNSResponder, Android netd/DnsResolver, BSD unwind/local_unbound.

---

## Role: Network Engineer / Network Administrator

**Why it matters:** "It's always DNS." resolvectl tells you which server, over which link, actually answered, which is the first fact you need in any name-resolution problem on Linux.

**When to use it (day to day):**
1. A site or service won't resolve: `resolvectl status` to see which DNS server each interface uses.
2. Tools disagree (dig vs the browser): `resolvectl query name` shows what apps get and which link answered.
3. You changed records or servers: `resolvectl flush-caches`.
4. Setting up or checking a VPN: internal domains (`~corp.local`) via the VPN; `~.` on the tunnel for full-tunnel DNS.
5. DNS leak tests: make sure nothing escapes to the ISP resolver while the VPN is up.
6. Split DNS: company domains to internal DNS, everything else to public DNS.
7. Multi-homed hosts (Wi-Fi + Ethernet + VPN): which network handles which lookups.
8. Quick temporary change without editing files: `resolvectl dns eth0 1.1.1.1` (reverts when the link resets).
9. Containers and Kubernetes DNS failures: confirm the 127.0.0.53 stub is the cause.
10. Service health: is systemd-resolved running and answering before blaming the network?

**What an expert knows that a beginner doesn't:** dig bypasses routing domains; `~` domains route but don't search; the most specific routing domain wins; DefaultRoute decides where unmatched names go; runtime settings are overwritten by the network manager; the resolv.conf symlink target decides whether apps use resolved at all.

## Role: Cybersecurity Expert

**Why it matters:** DNS is both an attack surface and a source of evidence.

1. **Hardening:** check whether LLMNR and mDNS are on; LLMNR/mDNS poisoning (e.g. Responder) is a classic credential-capture attack on internal networks. Disable with `LLMNR=no` / `MulticastDNS=no` in `resolved.conf` when not needed.
2. **DNS security state:** verify DNSSEC validation and DNS-over-TLS are actually active, not just configured.
3. **Incident response:** malware (DNSChanger family), rogue DHCP and VPN apps change DNS settings; check the servers per link.
4. **VPN assessments:** verify `~.` on the tunnel and capture `tcpdump -i eth0 port 53` to prove there is no plain-text leak.
5. **Monitoring and threat hunting:** `resolvectl monitor` streams lookups live (beaconing, C2 domains, DGA patterns); `statistics` and `show-cache` show recent activity.
6. **DNSSEC triage:** `--validate=no` and `nta` tell a real DNSSEC failure from an outage.

**What an expert knows:** link-local name protocols leak names and hashes on hostile networks; a cache can hold poisoned or stale answers (`flush-caches`, `--cache=no`); DNS settings can be changed by any privileged component, so verify per link rather than trusting one file.

---

## Related topics (where it applies)

1. DNS fundamentals: recursive vs stub resolvers, caching, TTLs, search domains.
2. DHCP: options 6 (DNS servers), 15 (domain name), 119 (search list), and how they reach resolved.
3. VPNs: split tunneling, split-horizon DNS, leak testing (WireGuard, OpenVPN, Tailscale).
4. DNS security: DNSSEC, DoT / DoH, hijacking, spoofing, cache poisoning.
5. Zero-config networking: mDNS, LLMNR, `.local` names, and attacks on them.
6. Multi-homed hosts: routing, interface priority, DefaultRoute.
7. Containers and Kubernetes: CoreDNS, `ndots`, host stub resolver problems.
8. Enterprise networks: Active Directory domains, internal zones, NRPT equivalents.
9. Blue team / SOC: DNS-based threat hunting, sinkholing, egress filtering.
10. Red team / pentesting: LLMNR/mDNS poisoning, DNS tunneling, rogue DHCP/DNS.

Hands-on lab: bring up a WireGuard tunnel to a machine running a DNS server; set `~corp.test` on wg0 and compare `resolvectl query`, `getent hosts` and `dig` for `host.corp.test`; then switch wg0 to `~.` and confirm with `tcpdump -i eth0 port 53` that nothing leaks.

---

## Follow-up Q&A

### Q: What does "DNS Domain: ~." mean in `resolvectl status`?
The link is a routing domain for the root zone, so all DNS queries are routed to its servers; usually set by a VPN to prevent leaks. Full explanation in "Output and fields explained" above.

### Q: Where does resolvectl come from, why did the concept arrive, and how did it evolve?
From the systemd project: systemd-resolved (Tom Gundersen, 2014; complete caching DNS/LLMNR stub in systemd 216), with the client growing from `systemd-resolve-host` and `systemd-resolve` into `resolvectl` (systemd 239, 2018). It arrived because one global `/etc/resolv.conf` could not handle multiple networks, VPN split DNS, caching or DNSSEC. See "History and evolution".

### Q: Why does Linux use it now, and what are the alternatives (Linux and other devices)?
See "Why Linux uses it now" and "Alternatives".

### Q: How do Android and Windows implement the same logic, and how is it the same or different?
Windows: DNS Client service + NRPT; Android: netd/DnsResolver with per-network DNS and Private DNS; macOS/iOS: mDNSResponder with scoped resolvers. All share a cached local resolver with per-network servers and domain routing; they differ in the unit of configuration and controls. See "Cross-platform comparison".

### Q: Why is it important for a network engineer and a cybersecurity expert, and in which topics should we use it?
See the two role sections and "Related topics".

### Q: When should a network administrator use resolvectl? (simple points)
1. A site or service won't resolve: `resolvectl status`.
2. Tools give different answers: `resolvectl query name`.
3. After changing DNS records or servers: `resolvectl flush-caches`.
4. Setting up or checking a VPN (`~corp.local`, `~.` on the tunnel).
5. Testing for DNS leaks.
6. Configuring split DNS.
7. Machines on several networks at once.
8. Quick temporary DNS change: `resolvectl dns eth0 1.1.1.1`.
9. Hardening servers: turn off LLMNR/mDNS when unneeded.
10. Checking DNSSEC and DNS-over-TLS are active.
11. Incident investigation: were DNS servers changed by malware or rogue DHCP?
12. Watching lookups: `resolvectl monitor`, `resolvectl statistics`.
13. DNS failing inside Docker or Kubernetes.
14. Checking the DNS service itself is healthy.

Short version: whenever you need to know which DNS server a Linux machine is really using, why, and whether that's safe.

### Q: Cheat sheet of resolvectl commands from official documentation only, version-tagged
See "Usage and commands" (sections 1–7), built from the systemd manual pages [1]–[4].

### Q: Library page
A searchable page with this material was added to the `library` repo as `pages/resolvectl-guide.html` (with `pages/js/pages/resolvectl-guide.js`, a one-line phone-width fix in `pages/css/base.css`, and updated `library.json` / README).

---

## Sources

[1] The systemd Project, "resolvectl, resolvconf — Resolve domain names, IPV4 and IPv6 addresses, DNS resource records, and services; introspect and reconfigure the DNS resolver," *systemd 261 Manual Pages*, freedesktop.org. [Online]. Available: https://www.freedesktop.org/software/systemd/man/261/resolvconf.html (accessed Nov. 17, 2026).

[2] The systemd Project, "resolvectl(1)," *systemd 258 Manual Pages*, freedesktop.org. [Online]. Available: https://www.freedesktop.org/software/systemd/man/258/resolvconf.html (accessed Nov. 17, 2026).

[3] The systemd Project, "resolvectl(1)," *systemd 259 Manual Pages*, freedesktop.org. [Online]. Available: https://www.freedesktop.org/software/systemd/man/259/resolvconf.html (accessed Nov. 17, 2026).

[4] The systemd Project, "resolvectl(1)," *systemd 260 Manual Pages*, freedesktop.org. [Online]. Available: https://www.freedesktop.org/software/systemd/man/260/resolvconf.html (accessed Nov. 17, 2026).

[5] The systemd Project, "resolvectl(1)," *systemd 263~devel Manual Pages*, freedesktop.org. [Online]. Available: https://www.freedesktop.org/software/systemd/man/devel/resolvectl.html (accessed Nov. 17, 2026).

[6] The systemd Project, "systemd.network — Network configuration," *systemd Manual Pages*, freedesktop.org. [Online]. Available: https://www.freedesktop.org/software/systemd/man/latest/systemd.network.html (not opened from this session).

[7] T. Gundersen, "systemd-resolved.service," systemd 215 manual page (Debian source), 2014. [Online]. Available: https://sources.debian.org/src/systemd/215-17/man/systemd-resolved.html (accessed Nov. 24, 2026).

[8] L. Poettering, "[ANNOUNCE] systemd 216," systemd-devel mailing list, Aug. 19, 2014. [Online]. Available: https://lists.freedesktop.org/archives/systemd-devel/2014-August/022295.html (accessed Nov. 24, 2026).

[9] L. Poettering, "[ANNOUNCE] systemd v229," systemd-devel mailing list, Feb. 11, 2016. [Online]. Available: https://lists.freedesktop.org/archives/systemd-devel/2016-February/035748.html (accessed Nov. 24, 2026).

[10] L. Poettering, "NetworkManager should push DNS information into systemd-resolved," GNOME Bugzilla #762540, Feb. 2016. [Online]. Available: https://bugzilla.gnome.org/show_bug.cgi?id=762540 (accessed Nov. 24, 2026).

[11] The systemd Project, "systemd-resolved.service," Debian manual pages. [Online]. Available: https://manpages.debian.org/man/systemd-resolved (accessed Nov. 24, 2026).

[12] The systemd Project, "systemd-resolved.service," *systemd 262 Manual Pages*, freedesktop.org. [Online]. Available: https://freedesktop.org/software/systemd/man/latest/systemd-resolved.html (accessed Nov. 24, 2026).

[13] The systemd Project, "systemd-resolved.service," Debian stretch manual pages. [Online]. Available: https://manpages.debian.org/stretch/systemd/systemd-resolved.8.en.html (accessed Nov. 24, 2026).

[14] M. Larabel, "Systemd Founder Lennart Poettering Announces Amutable Company," Phoronix, Jan. 27, 2026. [Online]. Available: https://phoronix.com/news/amutable (accessed Nov. 24, 2026).

Notes on certainty: version numbers for commands and options come from the official systemd 261 manual. The Windows, macOS and Android details, DoT timing (around systemd 239) and distribution adoption dates come from general knowledge and were not re-verified against primary sources in this session.
