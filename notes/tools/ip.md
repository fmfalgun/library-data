---
tool: ip
package: iproute2
date: 2026-11-23
domains: [Linux networking, Sysadmin, DevOps / containers, Security]
roles: [Network Engineer, Linux System Administrator, DevOps / SRE Engineer, Penetration Tester / Red Teamer, Cybersecurity Analyst / Incident Responder, Cloud / Virtualization Engineer, Embedded / IoT Engineer, Network Automation Engineer, Student / Certification Candidate]
tags: [ip, iproute2, netlink, linux, routing, namespaces, ifconfig-replacement, net-tools, networking]
---

# ip (iproute2)

## 1. Summary

`ip` is the Linux command that shows and changes the kernel network stack: interfaces (`link`), addresses (`address`), routes (`route`), policy-routing rules (`rule`), ARP/NDP neighbors (`neighbour`), tunnels, VRFs, network namespaces (`netns`) and live kernel events (`monitor`). It is part of the iproute2 package and talks to the kernel over netlink. It replaced the older net-tools commands `ifconfig`, `route` and `arp`. Syntax: `ip [OPTIONS] OBJECT { COMMAND | help }`.

Key points to remember:
- Changes made with `ip` are live and **not persistent**. Persistence belongs to NetworkManager, systemd-networkd, netplan or ifupdown.
- Reading is unprivileged, writing needs root or `CAP_NET_ADMIN`.
- `ip route get <dst>` shows the kernel's real forwarding decision and is the best single triage command.
- iproute2 releases follow kernel versions (latest found: 7.1, announced 15 June 2026). Newer iproute2 works on older kernels with some limits; there are no long-term stable branches.
- Original author Alexey Kuznetsov; maintained by Stephen Hemminger and David Ahern.

## 2. Usage and commands

### Install and availability
- Linux: part of the iproute2 package, installed on all modern distributions. The package is `iproute2` on Debian/Ubuntu and `iproute` on RHEL/older Fedora. It is sometimes installed in `/sbin`, which may not be on an unprivileged user's PATH.
- Other platforms: no native `ip` on macOS, BSD or Windows (see the cross-platform table). Android and BusyBox systems ship a reduced `ip` applet.

### The ten most useful operations

| # | Command | What it does |
|---|---|---|
| 1 | `ip -br a` | Brief address list |
| 2 | `ip -br link` | Brief link-layer state |
| 3 | `ip route` | Routing table |
| 4 | `ip route get 8.8.8.8` | Route, interface and source IP the kernel would use |
| 5 | `ip neigh` | ARP/NDP neighbor cache |
| 6 | `ip -s link show eth0` | Interface counters (errors, drops) |
| 7 | `ip addr add / del` | Add or remove an address |
| 8 | `ip link set eth0 up/down/mtu/address` | Interface state, MTU, MAC |
| 9 | `ip rule` + `ip route show table X` | Policy routing |
| 10 | `ip monitor` or `ip -j ...` | Live kernel events; JSON output for scripts |

Global options worth knowing: `-br` brief, `-j` JSON, `-p` pretty (with `-j`), `-h` human-readable counters, `-s` statistics (`-s -s` for detail), `-n <netns>` run inside a named namespace.

### Sample outputs (illustrative) and fields

```text
$ ip -br a
lo      UNKNOWN  127.0.0.1/8 ::1/128
eth0    UP       192.168.1.20/24 fe80::a00:27ff:fe4e:66a1/64
docker0 DOWN     172.17.0.1/16
```
Columns: interface, operational state, every address with prefix length. `UNKNOWN` on `lo` is normal.

```text
$ ip a show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 08:00:27:4e:66:a1 brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.20/24 brd 192.168.1.255 scope global dynamic eth0
       valid_lft 85234sec preferred_lft 85234sec
    inet6 fe80::a00:27ff:fe4e:66a1/64 scope link
```
- `<...>` interface flags. `UP` is the admin state; `LOWER_UP` means carrier is present. `UP` without `LOWER_UP` usually means an unplugged cable.
- `mtu` maximum frame size; `qdisc` queueing discipline (where `tc` comes in).
- `state` operational state reported by the driver.
- `link/ether ... brd` MAC address and broadcast MAC.
- `inet ... scope global dynamic` address came from DHCP; `valid_lft` and `preferred_lft` are lease timers; `forever` means static.

```text
$ ip route
default via 192.168.1.1 dev eth0 proto dhcp src 192.168.1.20 metric 100
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.20
```
`proto` records who installed the route (`kernel` for connected routes, `dhcp`, `static`, `bgp`). Lowest `metric` wins between equal routes. `src` is the source address that will be used.

```text
$ ip route get 1.1.1.1
1.1.1.1 via 192.168.1.1 dev eth0 src 192.168.1.20 uid 1000
```
Answers "why does traffic leave by that interface?" using the kernel's actual decision.

```text
$ ip neigh
192.168.1.1 dev eth0 lladdr 3c:84:6a:11:22:33 REACHABLE
192.168.1.77 dev eth0 lladdr 08:00:27:aa:bb:cc STALE
192.168.1.90 dev eth0  FAILED
```
States: `REACHABLE` recently confirmed; `STALE` valid but unconfirmed, re-probed on next use; `DELAY`/`PROBE` verifying; `FAILED` no ARP reply; `PERMANENT` static entry.

```text
$ ip -s link show eth0
    RX:  bytes packets errors dropped  missed   mcast
  9812345678 7123456      0      12       0   4401
    TX:  bytes packets errors dropped carrier collsns
  1234567890 5123456      0       0       0       0
```
Non-zero `errors`, `dropped` or `carrier` point to cabling, driver or buffer problems.

Other operations:
- `ip addr add 10.0.0.5/24 dev eth0`, then `ip link set eth0 up`
- Policy routing: `ip rule add from 10.0.0.0/24 table 100`, then `ip route add default via 10.0.0.1 table 100`
- `ip monitor` for live events; `ip -j -p route` for JSON

### One realistic task: a routed two-host lab with namespaces

Suits network engineers, DevOps, pentesters and students.

```bash
# Run as root. Create two host namespaces and a router namespace
ip netns add h1; ip netns add h2; ip netns add r
# Link each host to the router with a veth pair
ip link add h1-r type veth peer name r-h1
ip link add h2-r type veth peer name r-h2
ip link set h1-r netns h1; ip link set r-h1 netns r
ip link set h2-r netns h2; ip link set r-h2 netns r
# Addresses
ip -n h1 addr add 10.0.1.2/24 dev h1-r
ip -n r  addr add 10.0.1.1/24 dev r-h1
ip -n h2 addr add 10.0.2.2/24 dev h2-r
ip -n r  addr add 10.0.2.1/24 dev r-h2
# Bring everything up (including lo)
for n in h1 h2 r; do ip -n $n link set lo up; done
ip -n h1 link set h1-r up; ip -n h2 link set h2-r up
ip -n r link set r-h1 up;  ip -n r link set r-h2 up
# Routes and forwarding on the router
ip -n h1 route add default via 10.0.1.1
ip -n h2 route add default via 10.0.2.1
ip netns exec r sysctl -w net.ipv4.ip_forward=1
# Test it and watch the neighbor table fill
ip netns exec h1 ping -c2 10.0.2.2
ip -n h1 neigh
ip -n r route get 10.0.2.2
# Clean up
ip netns del h1; ip netns del h2; ip netns del r
```
This shows the object model: `link`, `addr`, `route`, `neigh` and `netns` all use the same pattern, with `-n NS` scoping.

### Common mistakes, permissions and gotchas
- **Nothing is persistent.** A reboot, or NetworkManager/networkd re-applying config, undoes changes. Make permanent changes in netplan, NetworkManager, systemd-networkd or ifupdown.
- **Permissions:** viewing is unprivileged; changing needs root or `CAP_NET_ADMIN`.
- **Abbreviations** (`ip a`, `ip r`, `ip l`, `ip n`) work, but scripts should use full words.
- **A missing prefix** in `ip addr add 10.0.0.5 dev eth0` gives a `/32`. Always write the prefix length.
- **Locking yourself out:** `ip link set eth0 down` or `ip addr flush dev eth0` over SSH kills the session.
- **`add` fails if the entry exists** ("File exists"). Use `replace` for idempotent scripts.
- **`ifconfig` aliases (`eth0:1`)** do not exist in `ip`; just add a second address to `eth0`.
- **Symbolic names** for routing tables and protocols come from files in `/etc/iproute2`; they are re-read on every run.
- **Container hosts:** `ip` inside a container shows only that container's namespace.

## 3. Output and fields explained

See the sample outputs above. Recurring concepts:
- **Flags / state:** admin `UP` vs carrier `LOWER_UP` vs operational `state`.
- **scope:** `global` (routable), `link` (on-link only, e.g. fe80::), `host` (loopback).
- **proto:** the route's owner (`kernel`, `dhcp`, `static`, `bgp`, ...), which tells you who will re-create or remove it.
- **metric:** tie-breaker among otherwise equal routes; lower wins.
- **valid_lft / preferred_lft:** address lifetimes; `forever` for static addresses.
- **Neighbor states:** `REACHABLE`, `STALE`, `DELAY`, `PROBE`, `FAILED`, `PERMANENT`.

## 4. History and evolution

- **Origin:** the original author is Alexey Kuznetsov, who was responsible for the quality-of-service implementation in the Linux kernel; that is why `tc` lives in the same package. The CREDITS file lists Stephen Hemminger as having taken over starting with the 2.6 kernel, and the README names Hemminger and David Ahern as maintainers.
- **Start date:** Wikipedia's ifconfig page says iproute2 has been available since 1999 for Linux 2.2 (this confirmed an earlier recollection).
- **Netlink standardisation:** RFC 3549, "Linux Netlink as an IP Services Protocol" (Informational, published July 2003), whose authors include Jamal Hadi Salim, Hormuzd Khosravi, Alexey Kuznetsov and Andi Kleen. Netlink replaced the ioctl and `/proc` approach with a structured message API that supports dumps, atomic operations and kernel-pushed notifications (what `ip monitor` shows).
- **Evolution of the tool:** started with address, route and rule; later gained many `link` types (bridge, bond, VLAN, VXLAN, GRE, veth, macvlan), `netns`, VRF and nexthop objects, and newer families such as `ioam6` (monitor command added 2024), `stats` (2022) and nexthop group stats. The 6.19 release (Feb 2026) added a `dpll` command. An older note: `ip link` could not create tunnels, VXLAN or L2TPv3 links; by iproute2 3.16 it could create everything except L2TPv3.
- **Recent releases:** 6.19 (21 Feb 2026), 7.0 (13-15 April 2026), 7.1 (15 June 2026).
- **JSON output (`-j`):** relatively recent; I recalled roughly 2017 but did not verify it.
- **Why net-tools lost:** the old tools cannot represent most modern features. net-tools 2.10 (7 January 2021) is its latest release and it has been described as deprecated since 2011. RHEL 7 no longer installs it by default; Ubuntu stopped installing `ifconfig` on desktops; Debian's wiki lists many packages that still depend on it.
- **Release policy:** a new iproute2 per kernel version; always use the latest; no maintenance releases and no long-term stable version.

## 5. How it works internally

- `ip` opens an `AF_NETLINK` socket (rtnetlink family) and sends request messages to the kernel (for example create/delete address, route, link, neighbor), and reads replies and notifications. Reads use "dump" requests; writes are individual messages; `ip monitor` subscribes to multicast groups to receive kernel events.
- This is the same interface used by NetworkManager, systemd-networkd, container runtimes and CNI plugins, which is why `ip` shows the ground truth.
- Symbolic names (routing tables, protocols, scopes, realms) are looked up from files under `/etc/iproute2`.
- The iproute2 userspace carries copies of kernel UAPI headers; new kernel features arrive via the iproute2-next tree and are released in step with the kernel.
- Certainty: the netlink and `/etc/iproute2` points are documented in the sources cited; the message-type details above are general knowledge and not re-verified in this session.

## 6. Cross-platform comparison

| Platform | Inspect / change interfaces and addresses | Routes | Neighbors | Notes |
|---|---|---|---|---|
| Linux | `ip addr`, `ip link` | `ip route` | `ip neigh` | netlink |
| macOS / FreeBSD / OpenBSD | `ifconfig` | `route`, `netstat -rn` | `arp`, `ndp` | Routing socket (PF_ROUTE), not netlink; `ifconfig` originated in 4.2BSD |
| Windows | `netsh interface ip`, `Get-NetIPAddress`, `New-NetIPAddress` | `route print`, `Get-NetRoute`, `New-NetRoute` | `arp -a`, `Get-NetNeighbor` | PowerShell NetTCPIP module |
| Android | Linux `ip` in a limited shell; `ConnectivityManager` for apps | same | same | Kernel is Linux, but apps cannot change it |
| Cisco IOS / network devices | `show ip interface brief` | `show ip route` | `show arp` | Vendor CLI, different object model |
| Cloud (AWS etc.) | VPC/subnet APIs | Route tables via API | Managed | Config lives outside the VM |

Same idea everywhere, but only Linux exposes namespaces, VRFs and policy routing in one tool.

## 7. Alternatives and comparative analysis (follow-up Q&A)

**Question: "comparative analysis between other options"**

Main finding: most alternatives are not competitors to `ip`; they work at different layers. Only net-tools is a like-for-like rival.

### 7.1 Layers

| Layer | Tools | Question answered |
|---|---|---|
| Kernel state, live (read/write) | `ip`, `bridge`, `tc`, net-tools, BusyBox `ip`, `pyroute2` | What is the network doing now, and can I change it this second? |
| Config managers (persistent, declarative) | NetworkManager (`nmcli`), systemd-networkd (`networkctl`), netplan, ifupdown | What should the network look like after reboot? |
| Device and driver | `ethtool`, `iw`/`iwconfig` | What is the NIC or radio doing? |
| Sockets and filtering | `ss`, `nft`/`iptables` | Who is talking, and what is allowed? |

Config managers do not replace `ip`: nmcli configurations are usually persistent, while `ip` gives low-level control by interacting directly with the kernel.

### 7.2 `ip` vs net-tools

| Criterion | `ip` (iproute2) | net-tools |
|---|---|---|
| Maintenance | Releases track each kernel (7.1, June 2026) | Latest release 2.10, 7 January 2021 |
| Status | Standard | Deprecated since 2011 |
| Installed by default | Yes | Still in repos, not pre-installed |
| Kernel interface | Netlink | ioctls and `/proc` |
| Namespaces, VRF, policy routing, nexthops | Yes | No |
| Multiple addresses per interface | Native | `eth0:1` aliases |
| Tunnels, VXLAN, veth, bridges, bonds | Yes (`ip link add type ...`) | Mostly no (`brctl`, `iptunnel` separately) |
| Machine-readable output | `-j` JSON | Text parsing only |
| Learning curve | Higher, uniform OBJECT COMMAND pattern | Lower for simple jobs |
| Portability | Linux only | Same command names on BSD and macOS |

Command mapping: `ifconfig` -> `ip addr`, `ip link`, `ip -s link`; `route` -> `ip route`; `arp` -> `ip neigh`; `iptunnel` -> `ip tunnel`; `netstat` -> `ss`; `brctl` -> `bridge`.

Distribution status: RHEL 7 stopped installing net-tools by default (Red Hat and Fedora got serious about it in 2011); Ubuntu stopped installing `ifconfig` on desktops while servers still got it at the time of its blog post; Debian historically shipped both, and its wiki lists many packages still depending on net-tools. CentOS has iproute2 present but net-tools not installed by default. Some of this detail comes from 2017-and-older articles; check current defaults on the release you target.

When net-tools still wins: muscle memory in a quick lab, ancient scripts, and BSD/macOS parity. Elsewhere it is a liability because it cannot show things like a second routing table or a namespace.

### 7.3 `ip` vs config managers

| | `ip` | `nmcli` (NetworkManager) | `networkctl` + networkd | `netplan` |
|---|---|---|---|---|
| What it is | Kernel control | Connection profile manager | Declarative `.network`/`.netdev` files | YAML front-end |
| Persistent? | No | Yes | Yes | Yes |
| Typical home | Everywhere | Desktops, RHEL/Fedora, Wi-Fi/VPN | Minimal servers, containers, embedded | Default on Ubuntu Server (YAML in /etc/netplan/) |
| Wi-Fi, VPN, mobile broadband | No | Strong | Limited | Passes through to a backend |
| Rollback safety | None | Profile-level | Reload | `netplan try` timed rollback |
| Best for | Inspect, debug, temporary change | Per-user and roaming setups | Fixed servers | Cloud images and Ubuntu fleets |

Netplan configures nothing itself; it renders YAML through networkd or NetworkManager. On an Ubuntu server the chain is netplan -> networkd -> kernel, and `ip` is how you check the last link.

Triage rule: if an interface shows `unmanaged` in NetworkManager, Netplan (or another tool) manages it; if it shows connected/disconnected, NetworkManager manages it and you should use `nmcli`. Changing a managed interface with `ip` may be silently undone by the manager.

Recommended split: use `ip` for diagnosis and throwaway changes (check with `ip link`, `ip address`, `ip route`, then `ss` and an application probe); use the owning manager for anything that must survive a reboot.

### 7.4 `ip` next to siblings (complementary)

| Tool | Overlap with `ip` | Use it instead when |
|---|---|---|
| `ethtool` | Both show link info; `ip` is logical, `ethtool` is the NIC | Speed/duplex, offloads, ring buffers, driver stats |
| `ss` | Same package | Sockets, not interfaces |
| `bridge` | Replaces `brctl` | FDB, VLAN filtering, MDB detail |
| `tc` | Same package | Queueing, shaping, netem delay and loss |
| `iw` | None | Wireless specifics |
| `nft` | None | Packet filtering and NAT |
| `arp-scan` | `ip neigh` is passive | Actively find hosts on the segment |

### 7.5 Programmatic options

| Option | Strength | Weakness |
|---|---|---|
| `ip -j` + `jq` | No dependencies, easy in shell | Field names can change between versions; a process per call |
| `pyroute2` (Python) | Direct netlink, no parsing, event-driven | Extra dependency, larger API |
| Raw netlink / libnl (C) | Fastest, fullest control | High effort |
| BusyBox `ip` | Tiny, in most embedded images | Subset of options; may lack JSON and newer link types |

### 7.6 Decision guide

| Situation | Pick |
|---|---|
| Quick look at addresses, routes or neighbors | `ip -br a`, `ip route`, `ip neigh` |
| "Why does traffic go out that interface?" | `ip route get <dst>` |
| Temporary test change | `ip` (expect it to vanish on reboot) |
| Permanent change on a desktop or Wi-Fi/VPN machine | `nmcli` |
| Permanent change on an Ubuntu server | netplan, then `netplan try` |
| Permanent change on a minimal or container host | systemd-networkd files |
| NIC speed or offload issue | `ethtool` |
| Socket or port question | `ss` |
| Container or lab networking | `ip netns`, `ip link add type veth` |
| Script that must survive version changes | `pyroute2` or pinned `ip -j` |
| Old host with only `ifconfig` | Use it, but plan to move |

### 7.7 Confidence notes
- Confident: net-tools vs iproute2 facts (cited); layering and persistence differences; the netplan -> networkd/NM chain.
- Confirmed during the session: the 1999 start date (Wikipedia: available since 1999 for Linux 2.2).
- General knowledge, not checked: exact link types BusyBox `ip` supports; when JSON output arrived. Check on your target version.
- Some distro-deprecation detail dates from 2017 and earlier articles; confirm current defaults.

## 8. Role lens (all nine roles)

### Network Engineer
- Why it matters: Linux hosts are routers, firewalls, load balancers and lab nodes. A Cisco blog argues every network engineer should be able to explore a Linux system's network configuration with `ip`, noting `ifconfig` has not been the best choice for a long time.
- Day to day: `ip route get`, `ip neigh`, `ip -s link`, VLAN subinterfaces (`ip link add link eth0 name eth0.100 type vlan id 100`), bridges, GRE/VXLAN tunnels, VRFs.
- Expert knowledge: `proto` and `metric` show who owns a route; `ip route get` tests the kernel's decision rather than the table you think is active; `rp_filter` and multiple routing tables explain most asymmetric-routing mysteries.

### Linux System Administrator
- Why it matters: default network tool on every server.
- Day to day: diagnosing "comes back from reboot with no network" (first check which interfaces are up and which addresses they have), then fixing config in the proper persistence layer.
- Expert knowledge: temporary `ip` changes versus persistent config; `ip -br` for one-glance triage; `ip -s -s link` for error breakdown; how to recover a remote host without a reboot.

### DevOps / SRE Engineer
- Why it matters: container networking is namespaces, veth pairs and bridges. Network namespaces give a separate network stack for a task, even without Docker.
- Day to day: `nsenter -t PID -n ip a` to inspect a container; `ip link` to find the host-side veth; `ip route` on nodes to debug CNI; MTU mismatches in overlays.
- Expert knowledge: map a container interface to its host peer via `ifindex`/`iflink`; many Kubernetes pod networking problems are routing or MTU problems visible in `ip route` and `ip link`.

### Penetration Tester / Red Teamer
- Why it matters: after a foothold, interface and route recon shows network segments and pivot options.
- Day to day: `ip a`, `ip route`, `ip neigh` for host and subnet discovery; `ip tuntap add`, `ip link add type gre` or wireguard for pivots; `ip link set dev eth0 address ...` for MAC changes; `ip route add` to steer traffic through a pivot.
- Expert knowledge: the neighbor table is passive recon (hosts this machine has already talked to); these actions are loud on monitored networks. It complements `arp-scan`, which actively probes the local segment.

### Cybersecurity Analyst / Incident Responder
- Why it matters: shows a suspect host's network state without extra tooling.
- Day to day: look for unexpected routes, extra interfaces (tunnels, tun/tap), the `PROMISC` flag in `ip link`, and ARP spoofing signs such as two IPs sharing one MAC in `ip neigh`.
- Expert knowledge: `ip` output is volatile evidence, so capture it early (for example `ip -j`); a rootkit can lie about it, so compare with out-of-band captures.

### Cloud / Virtualization Engineer
- Why it matters: hypervisor hosts are bridge, VLAN and overlay machines.
- Day to day: bridge and VLAN filtering (`bridge` and `ip link`), VXLAN and VRF setups, inspecting cloud guests where the cloud config already set routes.
- Expert knowledge: cloud-init and netplan render config that `ip` then shows; when the guest disagrees with the cloud console, `ip` plus instance metadata shows which side is wrong.

### Embedded / IoT Engineer
- Why it matters: small boards often have BusyBox and no NetworkManager.
- Day to day: bring-up scripts (`ip link set usb0 up`, `ip addr add`), static routes, USB/gadget networking.
- Expert knowledge: BusyBox `ip` supports fewer options (JSON and some link types may be missing); test on the target.

### Network Automation Engineer
- Why it matters: `-j` gives structured output without screen-scraping.
- Day to day: `ip -j addr | jq ...` in shell, or `pyroute2` for netlink-native Python; Ansible and similar tools often wrap the same calls.
- Expert knowledge: JSON field names can change between iproute2 versions, so pin or test; prefer netlink libraries for long-lived automation; newer iproute2 works with older kernels but with limitations, so features can silently be missing.

### Student / Certification Candidate
- Why it matters: it is the standard answer to "show IP addresses and routes on Linux".
- Day to day: learn the object/command pattern, then practise with the namespace lab.
- Expert knowledge: `ip` is the same everywhere on Linux, so lab skills transfer to production.

## 9. Related topics and where it applies

- Subjects: computer networks, Linux administration, container and virtual networking, network security, forensics, SDN.
- Certifications and curricula that typically cover it (general knowledge; check current exam objectives): LPIC-1/2, Linux Foundation LFCS, RHCSA/RHCE, CompTIA Linux+ (study guides show `ip link`, `ip address` and `ip route` for verifying interface and path), CKA/CKAD/CKS (node and pod network debugging), OSCP/PNPT (pivoting), Linux sections of vendor network certs.
- Related tools in the library: `arp-scan` (active ARP discovery vs passive `ip neigh`), `resolvectl` (per-link DNS), `wireguard` (creates interfaces `ip` manages), `nmap`, `wireshark`.
- Related iproute2 tools: `ss`, `tc`, `bridge`, `nstat`, `devlink`, `rdma`, `dcb`, `tipc`, `vdpa`, `rtmon`, `lnstat`, `ctstat`, `rtacct`, `routel`, `routef`, `arpd`.

## 10. Follow-up Q&A log

1. **Role pick (`ip command`)** - Domains found: Linux networking, sysadmin, DevOps/containers, security. Nine roles suggested; user chose `all`.
2. **Full explore (Blocks A and B)** - covered in sections 2 to 9 above.
3. **"comparative analysis between other options"** - covered in section 7.
4. **`/save`** - produced the files listed in the checklist (data/tools/ip.json, three people records, this note).

## 11. Sources

- Linux ip Command with Examples, linuxize: https://linuxize.com/post/linux-ip-command/
- Exploring the Linux ip command, Cisco Blogs: https://blogs.cisco.com/learning/exploring-the-linux-ip-command
- ip(8) man page: https://man7.org/linux/man-pages/man8/ip.8.html
- iproute2, Wikipedia: https://en.wikipedia.org/wiki/Iproute2
- iproute2 7.1 release, LWN: https://lwn.net/Articles/1078188/
- iproute2 6.19.0 and 7.0 release announcements (netdev list mirrors): https://lore.kernel.ime.usp.br/netdev/20260221081009.45f00ca8@phoenix.local/ and https://lore.kernel.ime.usp.br/netdev/20260413124459.1d6f40dd@phoenix.local/
- iproute2 README and CREDITS patch (netdev list): https://lists.openwall.net/netdev/2023/05/14/20
- iproute2 ChangeLog 2004-2005: https://googlers.googlesource.com/maze/iproute2/+/ss050607/ChangeLog
- iproute2 source on kernel.org: https://www.kernel.org/pub/scm/network/iproute2/iproute2.git/log/ and iproute2-next: https://www.kernel.org/pub/scm/network/iproute2/iproute2-next.git/log/
- Task-centered iproute2 user guide, baturin.org: https://baturin.org/docs/iproute2/
- RFC 3549 history, IETF Datatracker: https://datatracker.ietf.org/doc/rfc3549/history/
- Moving on from net-tools, LWN: https://lwn.net/Articles/710000/
- If you're still using ifconfig, Ubuntu blog: https://ubuntu.com/blog/if-youre-still-using-ifconfig-youre-living-in-the-past
- Deprecated Linux Networking Commands and Their Replacements, Tecmint: https://www.tecmint.com/deprecated-linux-networking-commands-and-their-replacements/
- Ifconfig, Wikipedia: https://en.wikipedia.org/wiki/Ifconfig
- NetToolsDeprecation, Debian Wiki: https://wiki.debian.org/NetToolsDeprecation
- Undefaulting the net-tools package, NixOS Discourse: https://discourse.nixos.org/t/undefaulting-the-net-tools-package/39484
- ip or nmcli, Red Hat Learning Community: https://learn.redhat.com/t5/Platform-Linux/ip-or-nmcli/m-p/50845
- Linux Network Configuration, nmcli, Netplan and Resolution: https://open-exam-prep.com/study-guides/comptia-linux-plus/storage-networking-and-backup/network-configuration
- Local interfaces (netplan vs NetworkManager): https://rjseymour66.github.io/networking/book/local-interfaces/
- Linux Magazine, One ip tool to rule them all: https://www.linux-magazine.com/Issues/2016/193/Core-Technologies/(offset)/3
- ip command from iproute2, linuxblog.io: https://linuxblog.io/ip-command-from-iproute2-utilities-for-tcp-ip-networking-in-linux/
