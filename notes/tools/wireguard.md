---
tool: WireGuard
date: 2026-11-24
domains: [Networking, Security, Cryptography, Linux kernel, DevOps/Cloud, Privacy]
roles: [Network Engineer, Cybersecurity Analyst / Blue Team, Linux System Administrator, DevOps / Cloud Engineer, Penetration Tester / Red Teamer, Cryptographer / Protocol Researcher, Embedded / Mobile Developer, Privacy / Commercial VPN Operator]
tags: [vpn, wireguard, wg, wg-quick, noise-protocol, curve25519, chacha20-poly1305, cryptokey-routing, tunnel, linux-kernel, zero-trust, mesh, post-quantum, rosenpass, amneziawg, pivoting]
---

# WireGuard

## Summary

WireGuard is a small, fast VPN that runs inside the Linux kernel (and as native drivers or userspace implementations on other OSes). It creates a normal network interface (`wg0`). Peers identify each other only by **Curve25519 public keys**, like SSH keys; there are no certificates, usernames or cipher menus. Traffic is carried over **UDP** with one fixed, modern crypto suite.

- **Problem it solves:** an encrypted Layer-3 tunnel between machines, configured by exchanging public keys, without the negotiation complexity of IPsec or OpenVPN.
- **Userspace tools:** `wg` (configure/inspect) and `wg-quick` (bash wrapper that reads `/etc/wireguard/<if>.conf`). Current release: **wireguard-tools v1.0.20260223** [1].
- **Size:** about 4,000 lines of code versus OpenVPN's 400,000+ [10], small enough to audit.
- **Default port:** UDP 51820 (convention only).

---

## Install and availability

| Platform | How |
|---|---|
| Linux ≥ 5.6 | Module built in; install `wireguard-tools` (`apt`, `dnf`, `pacman`, `apk`). v1.0.20260223 is in Arch, Debian, Fedora, Alpine [1][2] |
| Linux 3.10 – 5.5 | `wireguard-linux-compat` out-of-tree backport [3] |
| Windows | WireGuard for Windows on the **WireGuardNT** kernel driver (since August 2021) [4]; v1.0 released [5] |
| macOS / iOS | App Store app (NetworkExtension + wireguard-go); `brew install wireguard-tools` for CLI |
| Android | Official app; kernel backend where available (GKI support since 30 March 2020) [4], otherwise wireguard-go |
| OpenBSD | `wg(4)` in base since 22 June 2020 (Matt Dunwoodie and Jason A. Donenfeld) [4] |
| FreeBSD | `if_wg` kernel module |
| Routers | OpenWrt (`luci-proto-wireguard`), MikroTik RouterOS 7, pfSense/OPNsense, AVM Fritz!Box (Fritz!OS 7.39+, site-to-site from 7.50) [4] |

---

## Usage and commands (with sample outputs)

### 1. Generate keys
```
$ umask 077; wg genkey | tee priv.key | wg pubkey > pub.key
$ cat pub.key
xTIBA5rboUvnH4htodjb6e697QjLERt1NAB4mZqp8Dg=
```
32-byte Curve25519 keys, Base64 = 44 characters. The private key is random bytes (clamped by `wg`). The **public key is the peer's identity**.

### 2. Preshared key (optional symmetric layer; also the post-quantum hook)
```
$ wg genpsk
FpCyhws9cxwWoV4xELtfJvjJN+zQVRPISllRWgeopVE=
```

### 3. Minimal server config `/etc/wireguard/wg0.conf`
```ini
[Interface]
Address    = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <server priv>
PostUp   = nft add rule ip nat postrouting oifname "eth0" masquerade   # or iptables

[Peer]
PublicKey  = <client pub>
AllowedIPs = 10.8.0.2/32
```
`Address`, `DNS`, `MTU`, `Table`, `PreUp/PostUp/PreDown/PostDown`, `SaveConfig` are **wg-quick-only** keys. The kernel only knows private key, listen port, fwmark and peers (public key, PSK, endpoint, AllowedIPs, keepalive).

### 4. Bring it up
```
$ sudo wg-quick up wg0
[#] ip link add wg0 type wireguard
[#] wg setconf wg0 /dev/fd/63
[#] ip -4 address add 10.8.0.1/24 dev wg0
[#] ip link set mtu 1420 up dev wg0
```
wg-quick is a bash script translating the config into `ip` + `wg` calls. Persistent: `systemctl enable --now wg-quick@wg0`.

### 5. Status
```
$ sudo wg show
interface: wg0
  public key: Hs3pX0...=
  private key: (hidden)
  listening port: 51820

peer: xTIBA5rboUvnH4htodjb6e697QjLERt1NAB4mZqp8Dg=
  preshared key: (hidden)
  endpoint: 203.0.113.7:43122
  allowed ips: 10.8.0.2/32
  latest handshake: 1 minute, 12 seconds ago
  transfer: 4.21 MiB received, 18.90 MiB sent
  persistent keepalive: every 25 seconds
```

### 6. Script-friendly output
```
$ sudo wg show wg0 latest-handshakes
xTIBA5rb...=	1763372105          # Unix epoch; 0 = never
$ sudo wg show wg0 dump            # tab-separated, one line per peer
$ sudo wg show wg0 transfer
$ sudo wg show wg0 endpoints
```

### 7. Add / remove peers live
```
$ sudo wg set wg0 peer <pub> allowed-ips 10.8.0.3/32
$ sudo wg set wg0 peer <pub> preshared-key ./psk.key
$ sudo wg set wg0 peer <pub> remove
```

### 8. Reload config without dropping sessions
```
$ sudo wg syncconf wg0 <(wg-quick strip wg0)
```
`wg-quick down/up` tears every tunnel down; `syncconf` applies only the diff.

### 9. Dump running state as config
```
$ sudo wg showconf wg0
```

### 10. Kernel debug logging (Linux)
```
# echo module wireguard +p > /sys/kernel/debug/dynamic_debug/control
# dmesg -w
wireguard: wg0: Receiving handshake initiation from peer 3 (203.0.113.7:43122)
wireguard: wg0: Sending handshake response to peer 3 (203.0.113.7:43122)
wireguard: wg0: Keypair 7 created for peer 3
```
WireGuard says nothing on the wire about failures; this is the only place you see them.

### Other integrations
```
nmcli connection import type wireguard file wg0.conf     # NetworkManager
qrencode -t ansiutf8 < client.conf                      # QR for mobile apps
ip link add wg0 type wireguard && wg setconf wg0 x.conf # manual, no wg-quick
```
systemd-networkd: a `.netdev` with `[NetDev] Kind=wireguard` plus `[WireGuard]` / `[WireGuardPeer]` sections.

---

## Output and fields explained

| Field | Meaning | Where it comes from / when it changes |
|---|---|---|
| `public key` | Interface identity | Derived from the private key |
| `listening port` | UDP port | `ListenPort`, or random if unset (clients) |
| `endpoint` | IP:port of the **last authenticated packet** from that peer | Updates automatically when the peer roams (Wi-Fi → LTE). Servers never need it configured |
| `allowed ips` | Cryptokey routing table entry for this peer | Config / `wg set`; adding a prefix already owned by another peer **moves** it |
| `latest handshake` | Time of last successful handshake | Re-keys about every 2 min while traffic flows (REKEY_AFTER_TIME 120 s); keys rejected after 180 s (REJECT_AFTER_TIME). >3 min with expected traffic = down. Missing line = never handshaked (wrong key, UDP blocked, wrong endpoint) |
| `transfer` | Bytes received/sent since interface creation | "Sent grows, received 0" = firewall/NAT problem |
| `persistent keepalive` | Empty authenticated packet interval | Only when set; keeps NAT mappings open |
| `fwmark` | Mark on WireGuard's own UDP packets | Set by wg-quick for full-tunnel policy routing |

### Cryptokey routing (`AllowedIPs`)
- **Outbound:** packet to destination X → choose the peer whose AllowedIPs contains X (longest prefix) → encrypt to that peer.
- **Inbound:** decrypt → check the inner **source** IP is in that peer's AllowedIPs → otherwise drop.
- So AllowedIPs = routing table **and** ACL.
- `AllowedIPs = 0.0.0.0/0, ::/0` on a client = full tunnel. wg-quick then sets fwmark `51820`, a routing table `51820` with the default route via wg0, and a rule `not fwmark 51820 lookup 51820` (plus `suppress_prefixlength 0` on main) so encrypted UDP doesn't loop into the tunnel.

### MTU 1420
1500 − 80, where 80 = IPv6 outer header (40) + UDP (8) + WireGuard data header (16) + Poly1305 tag (16). Over IPv4 the overhead is 60. Lower it (1380 / 1280) over PPPoE or nested tunnels.

---

## Realistic task: full-tunnel remote-access VPN on a cloud VM

```bash
# SERVER (Ubuntu VM, public IP 198.51.100.10)
sudo apt install wireguard-tools
sudo sysctl -w net.ipv4.ip_forward=1        # persist in /etc/sysctl.d/99-wg.conf
cd /etc/wireguard && umask 077
wg genkey | tee srv.key | wg pubkey > srv.pub
# write wg0.conf as in command 3, using the client's public key
sudo systemctl enable --now wg-quick@wg0
sudo ufw allow 51820/udp                     # AND the cloud security group

# CLIENT laptop: /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <client priv>
Address    = 10.8.0.2/32
DNS        = 1.1.1.1
[Peer]
PublicKey  = <srv.pub>
Endpoint   = 198.51.100.10:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25

sudo wg-quick up wg0
curl -4 ifconfig.me          # → 198.51.100.10 = success
sudo wg show                 # handshake present, both counters growing
```
Mobile clients: `qrencode -t ansiutf8 < client.conf` and scan in the app.

---

## Common mistakes, permissions and gotchas

- **Privileges:** root or `CAP_NET_ADMIN` to create/configure interfaces. `chmod 600` configs (they hold the private key).
- **No dynamic IP assignment, DHCP or user auth** in the protocol [11]. Addresses are static per peer unless a control plane hands them out.
- **UDP only.** No TCP fallback in the protocol; networks that block UDP kill it. Products wrap it (Tailscale falls back to a TCP-based relay transport when firewalls force it [12]).
- **Overlapping AllowedIPs** between peers: the prefix silently moves to the last peer configured.
- **Endpoint hostnames resolve once** at setup; dynamic DNS changes break the tunnel until re-resolved (`contrib/reresolve-dns`).
- **NAT/CGNAT clients** need `PersistentKeepalive = 25` for inbound reachability.
- **MTU black holes** over PPPoE / nested tunnels.
- **`DNS=` needs `resolvconf` or systemd-resolved**, otherwise "resolvconf: command not found". With resolved, wg-quick sets `~.` on wg0 (see resolvectl notes).
- **Forgot `ip_forward` / masquerade:** handshake fine, no internet.
- **Cloud firewall:** UFW open but security group closed.
- **Clock jumps:** handshake replay protection uses TAI64N timestamps; a peer whose clock went far forward and back can be refused until restart.

---

## History and evolution

### Origin
- **Author:** Jason A. Donenfeld ("zx2c4"), security researcher and kernel developer; org Edge Security, later WireGuard LLC. He holds the WireGuard trademark [13].
- **Original problem:** a stealthy traffic-tunnelling tool for **penetration-testing engagements** [6], plus frustration with IPsec/OpenVPN complexity [7]. (CSO dates the idea to 2017; Wikipedia lists the initial release as 2015 [4], and public snapshots exist from 30 June 2016 [8] — the 2015–2016 dating is more consistent.)
- **Logo:** inspired by a stone engraving of the mythological Python seen at a museum in Delphi [8].
- **Paper:** "WireGuard: Next Generation Kernel Network Tunnel", NDSS 2017.

### Concept history
| Era | Idea | What it contributed |
|---|---|---|
| 1990s | IPsec (RFC 1825 → 2401 → 4301), IKE / IKEv2 (RFC 7296) | Kernel IP-layer encryption, but huge negotiation complexity and cipher agility |
| 2001 | OpenVPN | Userspace TLS tunnel over TUN/TAP; flexible, slower, large codebase |
| 2005 – 2012 | Curve25519 (2005), ChaCha20 / Poly1305 (Bernstein), BLAKE2 (2012) | Fast constant-time software crypto, no AES hardware needed |
| 2016 – 2018 | Noise Protocol Framework (Trevor Perrin) | Handshake grammar; WireGuard uses **Noise_IKpsk2** |
| 2017 – 2019 | Formal verification | Tamarin symbolic proofs (Donenfeld & Milner); CryptoVerif computational proof (Lipp, Blanchet, Bhargavan) |
| 2018 – 2019 | Upstreaming fight | Donenfeld rejected the Linux crypto API as too complex; his **Zinc** library was proposed, parts merged into the kernel crypto lib in 5.5 [9]. Torvalds (2018): "Can I just once again state my love for it and hope it gets merged soon?" [6] |
| 9 Dec 2019 | Merged into net-next [14] | |
| 28 Jan 2020 | Torvalds merges net-next; WireGuard in mainline tree [8] | |
| 29 Mar 2020 | **Linux 5.6 released** — first stable release, i.e. 1.0.0 [6] | |
| 30 Mar 2020 | Android GKI native support [4] | |
| 22 Apr 2020 | GNOME NetworkManager GUI support (Beniamino Galvani) [8] | |
| 22 Jun 2020 | OpenBSD `wg(4)` [4] | |
| 2021 | FreeBSD 13.0 episode: a Netgate-sponsored kernel port was found flawed and pulled before release; rewritten later with Donenfeld's involvement (from general knowledge) | |
| Aug 2021 | **WireGuardNT** native Windows kernel driver [4]; later v1.0 of WireGuardNT and WireGuard for Windows [5] | |
| 2023 – 2026 | **Post-quantum:** Rosenpass (Rust; Classic McEliece + Kyber) injects a PQ key through the PSK slot [15][16]; PQ-WireGuard variants analysed at USENIX Security 2025 [17] | |
| 2024 – 2026 | **Censorship evasion:** AmneziaWG fork adds junk packets, randomised headers and signature spoofing to defeat DPI, crypto unchanged [18][19] | |
| Feb 2026 | wireguard-tools v1.0.20260223 [1] | |

### Why it's used today
- Small and auditable; formally verified handshake.
- In-kernel and fast; ChaCha20 is fast even on CPUs without AES instructions.
- **Roaming** works automatically (endpoint follows the last authenticated packet).
- It is a normal netdev: routing, firewalls, namespaces, policy routing all apply.
- SSH-style key model.
- So it became the **data plane of modern mesh / ZTNA**: Tailscale, Netbird, Netmaker, Firezone, Cloudflare WARP (BoringTun), NordLynx, Mullvad, Proton; Kubernetes encryption in Cilium and Calico.
- Enterprise remote access adopted it more slowly: no user auth, IP pools or compliance features [11]; ChaCha20 is not FIPS-approved (inference).

---

## How it works internally

- **Primitives (fixed, no negotiation):** Curve25519 ECDH, ChaCha20-Poly1305 AEAD, BLAKE2s hashing, SipHash24 for hashtable keys, HKDF key derivation [10][20]. If a primitive breaks, the fix is a new protocol version.
- **Handshake (Noise_IKpsk2, 1-RTT):**
  - Type 1 **Initiation, 148 bytes:** sender index, initiator ephemeral public key, encrypted initiator static key, encrypted **TAI64N timestamp** (replay protection), mac1, mac2.
  - Type 2 **Response, 92 bytes:** sender/receiver indexes, responder ephemeral, empty encrypted payload (proves key), mac1, mac2.
  - Type 3 **Cookie reply, 64 bytes:** sent only under load.
  - Type 4 **Transport data:** 16-byte header (type, receiver index, 64-bit counter) + ChaCha20-Poly1305 ciphertext + 16-byte tag.
  - Type field is 1 byte followed by 3 reserved zero bytes.
- **Stealth:** `mac1` is keyed with a hash of the **responder's public key**. A packet with invalid mac1 gets **no reply at all**, so scanners see nothing.
- **DoS resistance:** under load the responder demands a valid `mac2`, keyed with a **cookie** tied to the sender's IP (sent encrypted with XChaCha20-Poly1305), so spoofed sources can't force expensive DH work.
- **Timers instead of a state machine:** rekey after 120 s or 2^60 messages; reject after 180 s; old keys zeroed → perfect forward secrecy. Initiator identity is hidden (encrypted static key).
- **Silence:** no packets when idle unless PersistentKeepalive is set.
- **Replay window:** sliding counter window on transport packets.
- **Properties for cryptographers:** KCI resistance, identity hiding (initiator), forward secrecy; **not post-quantum** by itself — PSK slot is the hybrid upgrade path. State-disruption attacks exist against classic WireGuard when NTP is used to set the clock [16].

---

## Cross-platform comparison

| Platform | Native VPN mechanism | WireGuard path | Same vs different |
|---|---|---|---|
| Linux | XFRM (IPsec), TUN/TAP | In-kernel `wireguard` netdev | WG is a routable interface; XFRM is policy-based and transparent to interfaces |
| Windows | RAS: IKEv2, SSTP, L2TP, Always On VPN | WireGuardNT driver + GUI service | No built-in WG; RAS integrates AD/certs, WG uses static keys |
| macOS / iOS | NetworkExtension (`NEVPNManager` IKEv2, `NEPacketTunnelProvider`) | App = packet tunnel provider + wireguard-go | Same extension API as other VPN apps; on-demand rules by OS |
| Android | `VpnService` API, built-in IKEv2/IPsec | Official app: kernel module if present, else wireguard-go | VpnService gives a TUN fd; always-on VPN is easy |
| OpenBSD / FreeBSD | IPsec (`iked`) | `wg(4)` / `if_wg` | Configured with `ifconfig`, not `wg` |
| AWS / Azure / GCP | Managed IPsec site-to-site; AWS Client VPN is OpenVPN-based | Self-host on VMs, or Tailscale/Netbird | No managed WG at hyperscalers as far as known (inferred; verify) |
| Routers | Vendor IPsec / SSL | OpenWrt, RouterOS 7, OPNsense/pfSense, Fritz!Box | Often the fastest VPN on cheap routers thanks to lightweight crypto |

---

## Alternatives

- **Linux, traditional:** IPsec (strongSwan, Libreswan); OpenVPN (now with DCO kernel offload); SSH tunnels (`ssh -D`, sshuttle); OpenConnect / ocserv (AnyConnect-compatible).
- **Overlays / mesh:** ZeroTier, Nebula (Slack), Tinc.
- **Unencrypted tunnels** (pair with your own crypto): GRE, VXLAN, IPIP.
- **WireGuard-based management layers:** Tailscale / Headscale, Netbird, Netmaker, Firezone, wg-easy, innernet, defguard.
- **Forks / add-ons:** AmneziaWG (DPI evasion), Rosenpass (post-quantum), BoringTun (Rust userspace, Cloudflare).
- **Other platforms:** built-in IKEv2/IPsec on Windows, macOS/iOS and Android; SSTP/L2TP on Windows; cloud managed IPsec gateways; commercial SSL VPNs (Fortinet, Palo Alto GlobalProtect, Cisco AnyConnect).
- **Commercial VPNs on WG:** early adopters included NordVPN, Mullvad and Surfshark [11]; ProtonVPN and IPVanish also offer it [21].

---

## Role: Network Engineer

- **Why it matters:** site-to-site and hub-and-spoke tunnels without IKE proposals to match.
- **Day to day:** designing AllowedIPs like route tables; running OSPF/BGP over wg interfaces with `Table = off` and FRR/BIRD; MTU and TCP MSS clamping.
- **Expert knowledge:** WG is not multicast-aware and AllowedIPs pins prefixes to peers, so dynamic routing needs one interface per tunnel (point-to-point), or `/32`s plus static next-hops. Knows the 60/80-byte overhead by heart, and that roaming endpoints make it friendly to dual-WAN.

## Role: Cybersecurity Analyst / Blue Team

- **Why it matters:** minimal attack surface for admin access — but its stealth also hides **unauthorised** tunnels.
- **Detection:** UDP flows with fixed sizes (148-byte initiation, 92-byte response, 64-byte cookie), first byte `0x01–0x04` followed by three zero bytes, handshakes roughly every 2 minutes during traffic. Zeek / Suricata rules can match these. AmneziaWG exists to defeat exactly these signatures; its obfuscation operates at the transport layer and leaves the payload untouched [19].
- **Expert knowledge:** a stolen private key = full identity theft; there is no revocation infrastructure — removal from every peer is the revocation. Protect keys like SSH host keys; monitor `/etc/wireguard` and Windows `Data\Configurations`.

## Role: Linux System Administrator

- **Day to day:** `wg-quick@.service`; systemd-networkd `.netdev` (`Kind=wireguard`); NetworkManager import; `syncconf` for zero-downtime changes; debug logging via dynamic_debug.
- **Expert knowledge:** the **network-namespace trick** — create wg0 in the init namespace (its UDP socket stays there), then move the interface into a container's netns: that container's only route to the world is the tunnel, so leaks are impossible.

## Role: DevOps / Cloud Engineer

- **Day to day:** multi-cloud meshes, CI runners reaching private networks, Kubernetes node-to-node encryption (Cilium `encryption.type=wireguard`, Calico `wireguardEnabled`), Terraform/Ansible-generated configs.
- **Expert knowledge:** a hand-managed full mesh is O(n²) key/config pairs, so beyond a dozen nodes you use a control plane (Tailscale, Headscale, Netbird). Plain WG does no NAT traversal (STUN/relays); those products add it.

## Role: Penetration Tester / Red Teamer

- **Why it matters:** WireGuard was born from this role's need for stealthy pivots [6].
- **Day to day:** pivot through a compromised Linux host with an in-memory wireguard-go; loot configs — `/etc/wireguard/*.conf`, Windows `%ProgramFiles%\WireGuard\Data\Configurations\*.dpapi`, mobile backups — each holds a private key, i.e. network access.
- **Expert knowledge:** a WG port never answers scanners (`nmap -sU` → `open|filtered`, no reply), so you find it via configs, processes, routing tables or the 51820 default, not banners. In VAPT, check AllowedIPs for over-broad inbound ranges (a client allowed `0.0.0.0/0` inbound can spoof internal sources) and keys reused across devices.

## Role: Cryptographer / Protocol Researcher

- **Why it matters:** the reference production deployment of Noise and of the "no cipher agility" philosophy.
- **Study topics:** Noise_IKpsk2 properties (KCI resistance, initiator identity hiding, forward secrecy); timestamp-based replay defence and its clock-dependency weakness [16]; cookie/mac2 DoS design; formal proofs (Tamarin, CryptoVerif).
- **Expert knowledge:** WG is not post-quantum. The PSK slot is the official hybrid path: Rosenpass uses two post-quantum KEMs and no PQ signatures to give ephemeral secrecy and deniability [16]; PQ-WireGuard replaces DH with KEMs [17]; practical guides deliver PQ PSKs over ML-KEM hybrid TLS [22].

## Role: Embedded / Mobile Developer

- **Day to day:** embedding wireguard-go, WireGuardKit (wireguard-apple), Android `GoBackend` vs `WgQuickBackend`, OpenWrt packages, microcontroller ports (ESP32).
- **Expert knowledge:** WG is battery-friendly because it is silent when idle; `PersistentKeepalive` costs battery, so enable it only when inbound reachability through NAT is needed. ChaCha20 beats AES on CPUs without AES instructions, which is why WG flies on cheap routers.

## Role: Privacy / Commercial VPN Operator

- **Why it matters:** default protocol at Mullvad, Proton, NordVPN (NordLynx) and Surfshark [11].
- **Core trade-off:** the server keeps each client's last endpoint IP and static inner IP in memory, which clashes with no-logs promises. Workarounds: double-NAT (NordLynx), API-driven dynamic peer provisioning, removing idle peers after timeouts.
- **Expert knowledge:** plain WG is fingerprinted and blocked by censors; by early 2026 hundreds of VPN services were restricted in Russia, with ASN-level blocking from May 2026 [19], so operators ship AmneziaWG or wrap WG in TLS/QUIC.

---

## Related topics (where it applies)

- **Networking:** tunnelling and overlays, NAT traversal, MTU / PMTUD, policy routing, SD-WAN, split vs full tunnel DNS (see resolvectl `~.`).
- **Security:** Zero Trust Network Access, VPN hardening, encrypted-traffic classification and network forensics, pivoting (OSCP / OSEP / CRTO-style labs).
- **Cryptography:** AEAD, ECDH, the Noise framework, forward secrecy, formal verification (Tamarin, ProVerif, CryptoVerif), post-quantum migration (ML-KEM).
- **Linux:** kernel networking, network namespaces, systemd-networkd, nftables.
- **Cloud native:** CNI encryption (Cilium, Calico), multi-cloud meshes.
- **Certifications:** not confirmed by name in any blueprint, but the VPN concepts appear in CompTIA Network+/Security+, CCNA/CCNP Security (IPsec vs alternatives), LFCS/RHCE networking, CKS (in-cluster encryption) and OSCP (tunnelling/pivoting practice).

---

## Follow-up Q&A

### Q: Which roles care about WireGuard? (role pick)
Eight roles were suggested and all were selected: Network Engineer; Cybersecurity Analyst / Blue Team; Linux System Administrator; DevOps / Cloud Engineer; Penetration Tester / Red Teamer; Cryptographer / Protocol Researcher (non-obvious); Embedded / Mobile Developer (non-obvious); Privacy / Commercial VPN Operator. Each has its own section above.

No further follow-up questions were asked in this session.

---

## Sources

[1] J. A. Donenfeld, "[ANNOUNCE] wireguard-tools v1.0.20260223 released," WireGuard mailing list, Feb. 23, 2026. https://lists.zx2c4.com/pipermail/wireguard/2026-February/009514.html

[2] Arch Linux, "wireguard-tools 1.0.20260223-1." https://archlinux.org/packages/extra/x86_64/wireguard-tools/ ; Debian Package Tracker, "wireguard-tools." https://tracker.debian.org/pkg/wireguard-tools

[3] J. A. Donenfeld, wireguard-linux-compat commit cf877de9, Mar. 18, 2020. https://kernel.googlesource.com/pub/scm/linux/kernel/git/zx2c4/wireguard-linux-compat/+/cf877de9a8b38422aef6beb514b688a0eedae4d8

[4] Wikipedia, "WireGuard." https://en.wikipedia.org/wiki/WireGuard

[5] M. Larabel, "WireGuard For Windows Reaches v1.0," Phoronix. https://phoronix.com/news/wireguard-for-windows-1.0

[6] L. Constantin, "What is WireGuard?," CSO Online. https://www.csoonline.com/article/3434788/what-is-wireguard-secure-simple-vpn-still-in-development.html

[7] "WireGuard VPN protocol will ship with Linux kernel 5.6," TechRadar. https://techradar.com/news/wireguard-vpn-protocol-will-ship-with-linux-kernel-56

[8] Cavacopedia mirror of Wikipedia, "WireGuard" (history section). https://cavac.at/cavacopedia/WireGuard

[9] "WireGuard VPN Is On Its Way To Linux" (ZDNet via Slashdot), Dec. 2019. https://linux.slashdot.org/story/19/12/09/2319257/

[10] F. Gray, "Best VPNs with WireGuard in 2026," Gizmodo. https://gizmodo.com/best-vpn/wireguard

[11] Twingate, "Should businesses consider WireGuard?" https://www.twingate.com/blog/what-is-wireguard-vpn

[12] Tailscale, "VPN reviewer's guide." https://tailscale.com/kb/1062/reviewer-guide/

[13] Wikipedia (2023-10 mirror), "WireGuard" (trademark, license). https://kaweah.freedombox.rocks/kiwix/wikipedia_en_all_maxi_2023-10/Wireguard

[14] J. A. Donenfeld, "[ANNOUNCE] WireGuard merged to net-next, on its way to Linux 5.6," Dec. 9, 2019. https://lists.zx2c4.com/pipermail/wireguard/2019-December/004704.html

[15] NGI, "Rosenpass." https://ngi.eu/?p=67614

[16] NLnet, "Rosenpass: Post Quantum Security Add-On for WireGuard." https://nlnet.nl/project/Rosenpass/

[17] P. Lafourcade et al., PQ-WireGuard analysis, USENIX Security 2025. https://www.usenix.org/system/files/usenixsecurity25-lafourcade.pdf

[18] Fiery, "AmneziaWG vs WireGuard: Which to Choose in 2026," May 22, 2026. https://app.fiery.host/en/blog/amneziawg-vs-wireguard

[19] Fiery (mirror), same article. https://dostup.fiery.host/en/blog/amneziawg-vs-wireguard

[20] OVPN, "WireGuard." https://www.ovpn.com/en/wireguard

[21] CyberInsider, "Best WireGuard VPN." https://cyberinsider.com/vpn/best/wireguard-vpn/

[22] "Post-Quantum WireGuard: A Practical Implementation Guide," engrXiv. https://engrxiv.org/preprint/view/5020

Further primary references (not opened in this session): WireGuard protocol page https://www.wireguard.com/protocol/ ; whitepaper https://www.wireguard.com/papers/wireguard.pdf ; `wg(8)` and `wg-quick(8)` man pages.

Notes on certainty: version numbers, kernel/OS dates, Rosenpass and AmneziaWG facts come from the cited sources. Packet sizes, timer constants, wg-quick routing details, detection heuristics, role practices, the FreeBSD 2021 episode and the absence of managed WG at hyperscalers come from general knowledge of the protocol and docs and were not re-verified against primary sources in this session.
