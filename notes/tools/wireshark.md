---
tool: Wireshark (with tshark, dumpcap and companion tools)
date: 2026-11-24
domains: [Networking, Cybersecurity (blue and red team), Digital Forensics, Protocol Development, IoT/OT, Telecom/VoIP, Cloud/SRE, Education]
roles: [Network Engineer, SOC / Cybersecurity Analyst, Penetration Tester / Red Teamer, DFIR, Protocol / Embedded Developer, OT/ICS & IoT Security Engineer, Telecom / VoIP Engineer, Cloud / DevOps SRE]
tags: [wireshark, tshark, dumpcap, pcap, pcapng, libpcap, npcap, bpf, display-filters, packet-capture, protocol-analysis, tls-decryption, vpn-testing, dns-leak, kill-switch, split-tunnel, mtu, post-quantum, ml-kem, extcap, debconf]
---

# Wireshark

## Summary

Wireshark captures the raw frames on a network interface (or opens a capture file) and decodes each one into a tree of protocol fields, layer by layer. You can then filter, follow, graph and export those fields. It answers "what actually went over the wire?" instead of guessing from logs.

- **Suite:** `wireshark` (Qt GUI), `tshark` (CLI analyzer, same engine), `dumpcap` (the small privileged capture helper), plus `capinfos`, `editcap`, `mergecap`, `text2pcap`, `reordercap`, `rawshark`, `randpkt`.
- **Versions (Nov 2026):** stable 4.6.x (4.6.9 / 4.4.19 on 23 Sep 2026) [1]; 5.0.0rc1 development release on 21 Oct 2026 [2].
- **Scale:** about 3,100 protocols, 269k fields and 2,400 authors (SharkFest EU 2025 keynote) [3].
- **Licence:** GPL. **Origin:** Ethereal by Gerald Combs, 1998; renamed Wireshark 2006; Wireshark Foundation since 2023.

---

## Install and availability

| Platform | How | Capture engine |
|---|---|---|
| Debian/Ubuntu/Kali | `sudo apt install wireshark`. The installer asks "Should non-superusers be able to capture packets?" Answer **Yes**, then `sudo usermod -aG wireshark $USER` and log out and back in | libpcap |
| Fedora/RHEL | `sudo dnf install wireshark` (Qt GUI) + `wireshark-cli` | libpcap |
| Arch | `pacman -S wireshark-qt` | libpcap |
| macOS | Official universal `.dmg` or `brew install --cask wireshark`; run the bundled ChmodBPF step to open `/dev/bpf*` | BPF |
| Windows | Official installer, bundles **Npcap**. WinPcap and AirPcap are no longer supported since 4.6 [4] | Npcap (NDIS LWF) |
| Headless/servers/containers | `tshark`, `dumpcap` | same |
| Android/iOS | No native Wireshark. Capture elsewhere (PCAPdroid, `rvictl` on iOS) and open the file | — |

---

## Usage and commands

### The mental model: 3 steps, 6 flags

```
 1. CAPTURE           2. FILTER               3. LOOK
 ──────────           ─────────               ───────
 -i  where            -Y  "what I want"        (nothing) → one line per packet
 -w  save to file                              -V  → full detail
 -r  open a file                               -z  → summary / counts
```

**Golden rule:** capture everything to a file once, then ask the file questions as many times as you like. Never try to filter perfectly while capturing. Only the filter in quotes changes between tasks; skill comes from learning filters, not flags.

**Split the tools:** Wireshark GUI is for exploring (you don't know yet what you're looking for); tshark is for checking (you know the filter and want a repeatable yes/no). In the GUI only four things matter: the filter bar (same syntax as `-Y`, turns green when valid); right-click a field → Apply as Filter (Wireshark writes the filter for you; copy it into tshark); right-click a packet → Follow → TCP/UDP Stream; Statistics → Conversations.

**Ignore for now** (until a need appears): ring buffers (`-b`), `-T fields -e`, `-o` preferences, `-d` decode-as, editcap/mergecap.

### Core: the 5 commands every use case starts from

```bash
tshark -i $NIC -i $TUN -w $F              # capture (Ctrl+C to stop)
tshark -r $F -Y '<filter>'                # look at matching packets
tshark -r $F -Y 'frame.number==N' -V      # full detail of one packet
tshark -r $F -q -z conv,ip                # who talked to whom
wireshark $F                              # explore visually
```
Useful variations: `-a duration:60` (auto-stop), `-t ad` (real date and time), `-c 100` (first 100 packets).

### Shell shortcuts (`~/.bashrc`)

```bash
cap()   { tshark -i eno1 -i adrishya -w "$1"; }                  # cap <file>
look()  { tshark -r "$1" -t ad ${2:+-Y "$2"}; }                  # look <file> [filter]
deep()  { tshark -r "$1" -Y "frame.number==$2" -V; }             # deep <file> <n>
who()   { tshark -r "$1" -q -z conv,ip ${2:+-Y "$2"}; }          # who <file> [filter]
```

### The 10 most useful operations, with sample output

**1. List interfaces**
```
$ tshark -D
1. eth0
2. wlan0
3. any
4. lo (Loopback)
5. bluetooth-monitor
6. nflog
7. ciscodump (Cisco remote capture)
8. sshdump (SSH remote capture)
```
`any` uses Linux "cooked" SLL2 headers (no real Ethernet header). `sshdump`/`ciscodump` are extcap plugins that capture remotely.

**2. Live capture with a BPF capture filter into a ring buffer**
```
$ dumpcap -i eth0 -f "tcp port 443 or udp port 53" -b filesize:100000 -b files:10 -w /tmp/edge.pcapng
Capturing on 'eth0'
File: /tmp/edge_00001_20261118120900.pcapng
Packets: 18342
```
`-f` is a kernel BPF filter (non-matching traffic is dropped before it reaches you). `-b` rotates every 100 MB and keeps 10 files.

**3. Display filters** (Wireshark's own language, applied after capture)
```
tcp.analysis.retransmission
dns.flags.rcode != 0
http.request.method == "POST"
tls.handshake.type == 1 && tls.handshake.extensions_server_name contains "bank"
ip.addr == 10.0.0.5 && !(tcp.port == 22)
frame.time_delta_displayed > 1
```
Operators: `&&` and, `||` or, `!` not, `in {…}` set, `contains` byte search, `matches` PCRE regex.

**4. Read a file and print fields**
```
$ tshark -r edge.pcapng -Y "dns.qry.name" -T fields -e frame.time -e ip.src -e dns.qry.name -e dns.a
Nov 18, 2026 12:09:01.120  10.0.0.23  api.github.com   140.82.112.6
Nov 18, 2026 12:09:01.455  10.0.0.23  x7f3a.badcdn.xyz
```
An empty `dns.a` means no answer / NXDOMAIN, which is worth a SOC analyst's attention.

**5. Statistics**
```
$ tshark -r edge.pcapng -q -z conv,tcp
TCP Conversations
                                    |  <-   | |  ->   | |  Total  |  Rel Start | Duration
10.0.0.23:51544 <-> 140.82.112.6:443   412 501k     230  24k       642  525k     0.0012     8.43
```
Other `-z` statistics: `io,stat,1`, `http,tree`, `dns,tree`, `expert`, `endpoints,ip`, `sip,stat`, `rtp,streams`.

**6. Follow a stream**
```
$ tshark -r web.pcap -q -z follow,tcp,ascii,3
GET /login HTTP/1.1
Host: intranet.local
Authorization: Basic YWRtaW46UGFzc3dvcmQx
```
`tcp.stream` is an index Wireshark assigns per 5-tuple, not a protocol field. The Basic string decodes to `admin:Password1`.

**7. Expert info**
```
$ tshark -r slow.pcap -q -z expert
Warnings (212)
  Previous segment(s) not captured        tcp   41
  Duplicate ACK (#1)                      tcp   97
  Retransmission (suspected)              tcp   74
Notes ...
  Zero window                             tcp    6
```

**8. TLS decryption with a key log**
```bash
export SSLKEYLOGFILE=~/tls.keys   # before starting Chrome/Firefox/curl
tshark -r https.pcapng -o tls.keylog_file:~/tls.keys -Y http2 -T fields -e http2.header.value
```
For TLS 1.3 and ECDHE you need per-session secrets; a server RSA key does not help.

**9. Export objects**
```
$ tshark -r mal.pcap --export-objects http,./out
$ ls out
invoice.doc  update.exe  favicon.ico
```
Also `smb`, `imf`, `tftp`, `dicom`, `ftp-data`.

**10. Edit and merge**
```bash
editcap -A "2026-11-18 12:00:00" -B "2026-11-18 12:05:00" big.pcapng window.pcapng
mergecap -w both.pcapng client.pcapng server.pcapng
capinfos window.pcapng
```

### Full flag reference

#### Capture
| Flag | Meaning | Example |
|---|---|---|
| `-D` | List interfaces | `tshark -D` |
| `-i <if>` | Interface; repeatable | `-i eth0 -i tun0` |
| `-f "<bpf>"` | Capture filter (kernel BPF) | `-f "udp port 1194 or port 53"` |
| `-c <n>` | Stop after n packets | `-c 500` |
| `-a <cond>` | Auto-stop: `duration:`, `filesize:` (KB), `files:`, `packets:` | `-a duration:120` |
| `-b <cond>` | Ring buffer: `filesize:`, `duration:`, `files:`, `interval:` | `-b filesize:100000 -b files:10` |
| `-w <file>` | Write raw packets (`-` = stdout) | `-w vpn.pcapng` |
| `-s <len>` | Snaplen | `-s 128` |
| `-p` | No promiscuous mode | |
| `-I` | Monitor mode (Wi-Fi) | `-i wlan0 -I` |
| `-B <MB>` | Kernel buffer (fewer drops) | `-B 64` |
| `-y <type>` / `-L` | Set / list link-layer types | `-i wlan0 -L` |
| `-F <fmt>` | Output file format | `-F pcap` |
| `--list-time-stamp-types` / `--time-stamp-type` | Hardware timestamps | |
| `-q` | Quiet (with `-w` or `-z`) | |
| `-P` | Print packets while writing | |

On busy links use `dumpcap` (same capture flags) for capture and tshark/Wireshark only for analysis.

#### Read and filter
| Flag | Meaning | Example |
|---|---|---|
| `-r <file>` | Read a file | |
| `-Y "<dfilter>"` | Display filter (single pass) | `-Y "dns"` |
| `-2` | Two-pass analysis (reassembly, "response in") | |
| `-R "<dfilter>"` | Read filter; needs `-2` | |
| `-n` / `-N <flags>` | No name resolution / choose `m` `n` `t` `d` | `-N mt` |
| `-d <rule>` | Decode As | `-d udp.port==51820,wg` |
| `--disable-protocol` / `--enable-heuristic` | Toggle dissectors | `--enable-heuristic rtp_udp` |

#### Output
| Flag | Meaning |
|---|---|
| `-V` | Full detail tree |
| `-O <proto,…>` | Detail only for these protocols |
| `-x` | Hex + ASCII dump |
| `-T text\|fields\|json\|jsonraw\|ek\|pdml\|psml` | Output format (`ek` = Elasticsearch bulk) |
| `-e <field>` | Field for `-T fields` (repeatable) |
| `-E header=y`, `separator=,`, `quote=d`, `occurrence=f`, `aggregator=;` | Field formatting |
| `-t a\|ad\|r\|d\|dd\|e\|u` | Time format |
| `-u s\|hms` | Seconds format |
| `-l` | Line-buffered (piping live) |
| `-j` / `-J "<proto>"` | Limit JSON/PDML to protocols |
| `-G fields\|protocols\|decodes\|values` | Glossaries; `tshark -G fields \| grep -i <word>` finds field names |

#### Statistics (`-z`, usually with `-q`)
```
-z io,phs  |  -z conv,tcp|udp|ip  |  -z endpoints,ip  |  -z io,stat,1,"<filter>"
-z expert[,error|warn|note]  |  -z follow,tcp|udp|tls|http2|quic,ascii,<n>
-z dns,tree | http,tree | http_req,tree  |  -z sip,stat | rtp,streams  |  -z credentials
```

#### Preferences, decryption, export
`-o <pref>:<val>` (e.g. `tls.keylog_file`, `tcp.relative_sequence_numbers:FALSE`, `ip.defragment:TRUE`), `-C <profile>`, `--export-objects <proto>,<dir>`, `--export-tls-session-keys <file>`, `-X lua_script:<file>`, `-K <keytab>`.

#### GUI-only (`wireshark`)
`-k` start immediately, `-S` live update, `-l` auto-scroll, `-g <n>` go to packet, `-J`/`-j` jump to filter match, `-z` open stats window, `--fullscreen`. Example: `wireshark -i eth0 -i tun0 -k -f "not port 22" -C VPN-Test`.

#### Companion tools
```bash
capinfos f.pcapng                                    # duration, count, rate, interfaces, hashes
editcap -A "<start>" -B "<end>" in.pcapng out.pcapng # time slice
editcap -c 10000 big.pcapng part.pcapng              # split by packet count
editcap -D 5 in.pcap dedup.pcap                      # remove duplicates
editcap -t +1.25 a.pcap shifted.pcap                 # shift timestamps
editcap -s 96 in.pcapng headers-only.pcapng          # strip payloads before sharing
editcap --inject-secrets tls,keys.log in.pcapng out.pcapng
mergecap -w all.pcapng a.pcapng b.pcapng
text2pcap -u 1000,2000 hex.txt out.pcap
reordercap in.pcapng sorted.pcapng
```

### Commands by use case

Variables used below: `F=test.pcapng; S=<VPN server IP>; NIC=eno1; TUN=adrishya`, and `VPN='ip.addr in {…}'` or `VPN='udp.port==51820'` (see "Unknown VPN server IP").

#### A. Our use case: VPN client testing on Linux

**A0 routine:** one action per capture, named `<scheme>_<server>_<feature>.pcapng`:
```bash
tshark -i $NIC -i $TUN -a duration:120 -w A1_S1_split.pcapng
```

**F1 split tunnel**
```bash
curl -s https://included.example >/dev/null; curl -s https://excluded.example >/dev/null
tshark -r $F -Y "frame.interface_name==\"$NIC\" && !($VPN)" -T fields -e ip.dst -e tls.handshake.extensions_server_name
tshark -r $F -Y "frame.interface_name==\"$TUN\"" -q -z conv,ip
```
Pass: excluded names only on eno1, included only on the tunnel.

**F2 kill switch**
```bash
sudo nft add table inet t; sudo nft add chain inet t o '{ type filter hook output priority 0; }'
sudo nft add rule inet t o ip daddr $S drop          # simulate server loss
tshark -r $F -t ad -Y "frame.interface_name==\"$NIC\" && !($VPN) && !arp && !icmpv6"
sudo nft delete table inet t
```
Variation: add `log group 5` to the client's drop rule and watch `tshark -i nflog:5`. Pass: nothing leaves eno1 after the tunnel drops.

**F3 DNS reconfiguration / leak**
```bash
tshark -r $F -Y "frame.interface_name==\"$NIC\" && !($VPN) && (dns || tcp.port==853)"   # leaks
tshark -r $F -Y "frame.interface_name==\"$TUN\" && dns" -T fields -e ip.dst -e dns.qry.name
tshark -i dbus-system -Y 'dbus.member contains "DNS"'     # the config change itself
```

**F4 MTU**
```bash
tshark -r $F -Y "tcp.flags.syn==1 && frame.interface_name==\"$TUN\"" -T fields -e tcp.options.mss_val
tshark -r $F -Y "frame.interface_name==\"$NIC\" && ($VPN)" -T fields -e frame.len | sort -n | tail -1
tshark -r $F -Y 'ip.flags.mf==1 || ip.frag_offset>0 || (icmp.type==3 && icmp.code==4)'
ping -M do -s 1372 -c 3 10.8.0.1
```
Pass: MSS clamped (e.g. ≤1360), outer ≤1500, no fragments or frag-needed.

**F5 auto-connect on boot** (capture must start before the VPN service)
```ini
# /etc/systemd/system/bootcap.service  (systemctl enable bootcap)
[Unit]
Before=<vpn-client>.service
After=network-pre.target
[Service]
ExecStart=/usr/bin/dumpcap -i eno1 -a duration:180 -w /var/tmp/boot.pcapng
```
```bash
tshark -r /var/tmp/boot.pcapng -t ad -Y "!($VPN) && !arp && !dhcp"     # pre-tunnel leaks
tshark -r /var/tmp/boot.pcapng -t ad -Y "$VPN" -c 1                     # first handshake time
```

**A1–A4 authentication behaviour**
```bash
tshark -r $F -t ad -Y "($VPN) && (tls.handshake.type in {1 2} || tls.alert_message || tcp.flags.reset==1 || isakmp.exchtype==37)"
tshark -r $F -Y 'tls.handshake.extension.type==41' -T fields -e frame.time -e ip.dst   # PSK resumption
tshark -r $F -q -z conv,udp -Y "$VPN"                                                   # conv,tcp for TCP VPNs
```

**S1/S2 PQ vs non-PQ**
```bash
tshark -r $F -Y 'tls.handshake.type==2' -T fields -e ip.src -e tls.handshake.extensions_key_share_group
tshark -r $F -Y 'tls.handshake.extensions_key_share_group in {0x11ec 0x11eb 0x11ed 0x6399}'
tshark -r $F -Y isakmp -O isakmp | grep -Ei 'transform|key exchange|intermediate'
tshark -r $F -Y wg -T fields -e wg.type
```
Code points: `0x11ec` X25519MLKEM768, `0x11eb` SecP256r1MLKEM768, `0x11ed` SecP384r1MLKEM1024, `0x6399` old X25519Kyber768 draft. Check field names on your version with `tshark -G fields | grep -i key_share`.

**Report across the 8 combinations**
```bash
for f in A*_S*.pcapng; do
  echo "== $f"; tshark -r "$f" -Y 'tls.handshake.type==2' -T fields -e tls.handshake.extensions_key_share_group | sort -u
  echo "leaks: $(tshark -r "$f" -Y "frame.interface_name==\"$NIC\" && !($VPN) && dns" | wc -l)"
done
```

#### B. Other use cases

**B1 Network troubleshooting**
```bash
tshark -r $F -q -z expert
tshark -r $F -Y 'tcp.analysis.flags'
tshark -r $F -Y 'tcp.analysis.initial_rtt' -T fields -e ip.dst -e tcp.analysis.initial_rtt
tshark -r $F -q -z io,stat,1
tshark -r $F -Y 'dhcp' -T fields -e dhcp.option.dhcp -e dhcp.ip.your
tshark -r $F -Y 'arp.duplicate-address-detected || arp.duplicate-address-frame'
dumpcap -i eno1 -b filesize:100000 -b files:20 -w long.pcapng
```

**B2 SOC / threat hunting**
```bash
tshark -r $F -Y 'dns.qry.name.len > 50 || dns.flags.rcode==3' -T fields -e ip.src -e dns.qry.name
tshark -r $F -Y 'tls.handshake.type==1' -T fields -e ip.src -e tls.handshake.extensions_server_name -e tls.handshake.ja4
tshark -r $F -Y 'http.request' -T fields -e ip.src -e http.host -e http.request.uri -e http.user_agent
tshark -r $F -q -z endpoints,ip
tshark -r $F -q -z io,stat,10,"ip.dst==<suspect>"     # beaconing = steady counts
```

**B3 Pentesting**
```bash
tshark -r $F -q -z credentials
tshark -r $F -Y 'ntlmssp.messagetype==3' -T fields -e ntlmssp.auth.domain -e ntlmssp.auth.username
tshark -r $F -Y 'http.authorization || ftp.request.command=="PASS"'
tshark -r $F -Y 'arp.duplicate-address-detected'
tshark -r $F -Y 'llmnr || nbns || mdns'
tshark -r $F -q -z io,phs
```

**B4 DFIR**
```bash
sha256sum $F; capinfos $F
tshark -r $F --export-objects http,./out
tshark -r $F -q -z follow,tcp,ascii,5
tshark -r $F -T fields -E header=y -E separator=, -e frame.time_epoch -e ip.src -e ip.dst -e _ws.col.Info > timeline.csv
editcap -A "2026-11-18 10:00:00" -B "2026-11-18 10:30:00" $F window.pcapng
```

**B5 VoIP / telecom**
```bash
tshark -r $F -q -z sip,stat
tshark -r $F -Y 'sip.Method=="INVITE" || sip.Status-Code>=400' -T fields -e sip.from.user -e sip.to.user -e sip.Status-Code
tshark -r $F -q -z rtp,streams
tshark -r $F -d udp.port==10000,rtp -Y rtp
```
GUI: Telephony → VoIP Calls → Play Streams.

**B6 Wi-Fi**
```bash
tshark -i wlx00c0caae649b -I -w wifi.pcapng
tshark -r wifi.pcapng -Y 'wlan.fc.type_subtype==0x08' -T fields -e wlan.ssid -e wlan.bssid | sort -u
tshark -r wifi.pcapng -Y 'eapol'
tshark -r wifi.pcapng -Y 'wlan.fc.type_subtype==0x0c'
```

**B7 IoT / OT**
```bash
tshark -r $F -Y 'modbus.func_code in {5 6 15 16}'
tshark -r $F -Y 'mqtt.msgtype==3' -T fields -e mqtt.topic -e mqtt.msg
tshark -r $F -Y 's7comm || dnp3 || iec60870_104 || enip'
tshark -r $F -q -z conv,tcp -Y 'tcp.port==502'
```

**B8 Cloud / Kubernetes / remote**
```bash
ssh user@host "sudo tcpdump -U -i eth0 -w - not port 22" | wireshark -k -i -
kubectl debug -it <pod> --image=nicolaka/netshoot -- tcpdump -i eth0 -w - | wireshark -k -i -
tshark -r $F -Y 'vxlan || geneve'
tshark -r $F -Y 'tls.alert_message' -T fields -e ip.src -e tls.alert_message.desc
tshark -r $F -Y 'http2.rst_stream || tcp.flags.reset==1' -t ad
```

**B9 Decryption**
```bash
SSLKEYLOGFILE=~/keys.log curl https://example.com
tshark -r $F -o tls.keylog_file:$HOME/keys.log -Y http2
editcap --inject-secrets tls,$HOME/keys.log $F decrypted-ready.pcapng
tshark -r wifi.pcapng -o wlan.enable_decryption:TRUE -o 'uat:80211_keys:"wpa-pwd","Passw0rd:MySSID"'
```

**B10 Protocol development**
```bash
tshark -r $F -X lua_script:myproto.lua -Y myproto -V
tshark -r $F -d tcp.port==9000,http
text2pcap -u 5000,6000 dump.txt out.pcap
tshark -G fields | grep -i <word>
```

**B11 File housekeeping:** see "Companion tools".

### Realistic task: "the web app is slow from branch office B"
1. Capture at both ends at once: `dumpcap -i eth0 -f "host 10.20.0.0/16 and tcp port 443" -w srv.pcapng` on the server, same on a branch laptop.
2. Client file: `tcp.analysis.flags && !tcp.analysis.window_update`; Statistics → Conversations → TCP sorted by duration.
3. `tcp.analysis.initial_rtt` in the SYN/ACK: 180 ms to a datacenter 20 km away means a routing or VPN hairpin.
4. MTU black hole: handshake works, large TLS records stall, `ip.flags.df==1`, no ICMP frag-needed. Confirm with `icmp.type==3 && icmp.code==4` on the server side.
5. VoIP add-on: Telephony → VoIP Calls → RTP Stream Analysis for jitter and loss.
6. SRE add-on: RSTs from the LB VIP after exactly 60 s idle = idle-timeout mismatch.
7. Write-up: I/O Graphs or Plots, `-z expert` counts, screenshots.

### Common mistakes and gotchas
- **Running the GUI as root.** Only `dumpcap` needs privileges (`cap_net_raw,cap_net_admin`); dissectors are big C parsers reading hostile input.
- Mixing capture filters (BPF: `host 1.2.3.4`) with display filters (`ip.addr == 1.2.3.4`).
- Switch ports only show your own traffic; use SPAN, a TAP or monitor mode.
- Wi-Fi without monitor mode shows only your own frames, translated to 802.3.
- NIC offloads (TSO/GSO/LRO, checksum offload) create 64 KB "jumbo" segments and false bad-checksum warnings: `ethtool -K eth0 tso off gso off gro off`, or ignore.
- Snaplen truncation shows `[Packet size limited during capture]`.
- Clock skew between two capture points: `editcap -t`.
- Drops: check the `Dropped:` status; use dumpcap, `-B`, BPF filters.
- Legal: capturing traffic that isn't yours can breach wiretap and privacy laws (in India, the IT Act and Telegraph Act). Have written authorization.
- Dissector CVEs are frequent; in 2026 the project noted many fixes came from AI-assisted vulnerability reports [5]. Keep it patched; open untrusted PCAPs in a VM.

---

## Output and fields explained

### The three GUI panes
- **Packet list:** `No.` frame index; `Time` (seconds since first packet by default; set "Since Previous Displayed" for latency hunting); `Source`, `Destination`; `Protocol` = highest-layer dissector that matched; `Length` = bytes on the wire; `Info` = that dissector's summary.
- **Details tree:** `Frame` (metadata) → `Ethernet II` → `IPv4` → `TCP` → `TLS`. Fields in `[square brackets]` are **computed by Wireshark** (`[Stream index]`, `[iRTT]`, `[SEQ/ACK analysis]`, `[Calculated window size]`), not bytes in the packet.
- **Bytes pane:** hex + ASCII; clicking a field highlights its bytes.
- **`Seq=1`** is a relative sequence number (ISN subtracted). Turn off under Preferences → Protocols → TCP to match captures taken elsewhere.
- **`Win=` vs `[Calculated window size]`:** raw Win must be multiplied by the window scale negotiated in the SYN; without the SYN the scale shows `-1 (unknown)`.

### Interfaces listed by `wireshark -D` (real output from a PowerEdge T40, Ubuntu)

Without capture permission only extcaps appear, because local interfaces are enumerated by the privileged `dumpcap`; extcaps are plain programs in `/usr/lib/x86_64-linux-gnu/wireshark/extcap/` that run as the user.

| Interface | What it is | Use |
|---|---|---|
| `eno1` | Onboard Ethernet (`en` Ethernet, `o1` onboard index 1) | Physical uplink; leak checks |
| `adrishya` | Non-standard name, so created by software; very likely the VPN client's tunnel ("invisible" in Hindi). Confirm with `ip -d link show adrishya` | Traffic inside the tunnel |
| `wlx00c0caae649b` | USB Wi-Fi adapter (`wlx` + MAC); OUI 00:c0:ca is ALFA Network. Appeared only after being plugged in | Wi-Fi, monitor mode with `-I` |
| `any` | Linux pseudo-interface, all interfaces, SLL2 cooked headers, no promiscuous mode | Overview; duplicates for routed packets |
| `lo` | Loopback | Local services, e.g. DNS stub 127.0.0.53 |
| `docker0` | Docker default bridge | Container traffic before NAT |
| `bluetooth-monitor` | BlueZ HCI monitor (like `btmon`) | Bluetooth/BLE |
| `nflog` | Netfilter NFLOG: packets sent by an nftables/iptables rule with `log group N` | See what the firewall drops |
| `nfqueue` | Netfilter NFQUEUE: packets handed to userspace for a verdict | Userspace firewall/IPS debugging |
| `dbus-system` / `dbus-session` | D-Bus messages | Watch a VPN client reconfigure DNS via systemd-resolved/NetworkManager |
| `ciscodump` | SSH into Cisco IOS/ASA, runs Embedded Packet Capture, streams back | Remote capture on routers |
| `sshdump` | SSH into any host, runs tcpdump/dumpcap, streams pcap | Remote capture |
| `wifidump` | Remote Wi-Fi monitor mode over SSH | Remote wireless capture |
| `sshdig` | Remote system-call capture (Falco/sysdig) over SSH | For Stratoshark |
| `udpdump` | Listens on a UDP port, turns datagrams into packets (exported PDUs) | Devices streaming packets to you |
| `dpauxmon` | DisplayPort AUX channel monitor via netlink | Display-driver work |
| `randpkt` | Random packet generator | Fuzzing dissectors |
| `sdjournal` | systemd journal entries as packets | Logs and packets on one timeline |

With `-i any` the interface name is not recorded; map `sll.ifindex` to names with `ip -o link | awk '{print $1, $2}'`.

### The debconf prompt
`wireshark-common/install-setuid` (boolean, default false). Yes → creates group `wireshark`, `chown root:wireshark /usr/bin/dumpcap`, `chmod 750`, `setcap cap_net_raw,cap_net_admin+eip` (falls back to setuid 4750). Details in the follow-up Q&A.

---

## History and evolution

| When | What happened |
|---|---|
| 1988 | tcpdump at Lawrence Berkeley Laboratory (Van Jacobson, Craig Leres, Steven McCanne); libpcap later split out as the portable capture API |
| 1992–93 | BPF, "The BSD Packet Filter" (McCanne & Jacobson, USENIX 1993): register-based in-kernel filter VM replacing CSPF and Sun's NIT |
| Late 1997 | Gerald Combs, at a small ISP, needs to troubleshoot its network and learn networking; commercial analyzers cost about $1,500 and don't run on Solaris or Linux [6][7] |
| 14 Jul 1998 | Ethereal 0.2.0 announced on the GTK mailing list [8] |
| 1998 | Gilbert Ramirez contributes a low-level dissector; in October Guy Harris, wanting something better than tcpview, starts contributing [9] |
| Late 1990s | Loris Degioanni's WinPcap (Politecnico di Torino) brings libpcap to Windows |
| May 2006 | Combs joins CACE Technologies with Loris Degioanni; he holds the code copyright but not the Ethereal trademark, so the repository becomes Wireshark [6][10] |
| 2008 | Wireshark 1.0, after ten years [9] |
| 2010 | Riverbed acquires CACE; Riverbed becomes lead sponsor [11] |
| 2015 | Wireshark 2.0: GUI moves from GTK+ to Qt (GTK UI dropped in 3.0) |
| ~2019 | Npcap replaces WinPcap as the Windows driver |
| 2021 | Combs moves to Sysdig, which becomes lead sponsor [11] |
| 1 Mar 2023 | Sysdig announces the Wireshark Foundation, open governance; board includes Loris Degioanni and Gerald Combs; it takes over SharkFest [12][13] |
| 2025 | Stratoshark: system call and log analyzer combining Wireshark's filtering with Falco's capture [14] |
| 8 Oct 2025 | 4.6.0: Plots dialog (scatter plots), live capture compression, NTS-NTP decryption, X.509 export, macOS process info/packet metadata from tcpdump, WinPcap/AirPcap dropped [4][15][16] |
| 2026 | Official certification (Wireshark Certified Analyst) [17]; steady security releases, many from AI-assisted reports [5]; 4.6.9/4.4.19 on 23 Sep [1] |
| 21 Oct 2026 | 5.0.0rc1: new welcome page, "Processes" profile with PID and Proc Name columns [2] |

### Underlying concepts
- **Capture:** BPF and libpcap on Unix; `AF_PACKET`/`PACKET_MMAP` (TPACKET_V3) rings on Linux; NDIS lightweight filter (Npcap) on Windows. eBPF builds on the same idea today.
- **Dissector model:** protocol parsers registered in tables (`tcp.port`, `udp.port`, heuristic tables) build a field tree consumed by one display-filter engine; new compared with tcpdump's one-line printers.
- **File formats:** libpcap `.pcap` (24-byte global header, 16-byte per-record headers) and **pcapng** (IETF OPSAWG draft): multiple interfaces, comments, name-resolution blocks, nanosecond timestamps, Decryption Secrets Blocks.

### Why it's still the default
- Protocol coverage is the moat (3,000+ dissectors including OT, telecom, automotive).
- Open file format plus one shared filter language across Zeek, Suricata, Arkime, NetworkMiner and cloud packet mirrors.
- Privilege separation: capture with dumpcap anywhere, analyse elsewhere; tshark scripts into pipelines (`-T ek` to Elasticsearch).
- Extensible: Lua/C dissectors, extcap plugins, decryption for TLS, WPA2/3, IPsec, SSH, Kerberos, SNMPv3.
- Stack position: the "microscope". Flow tools (NetFlow/IPFIX, Zeek) say *that* something happened; Wireshark shows *exactly what* happened.

---

## How it works internally

```
NIC ─► kernel (AF_PACKET/BPF/Npcap, BPF capture filter -f)
        │
        ▼
   dumpcap  (only privileged part: CAP_NET_RAW + CAP_NET_ADMIN, or root/setuid)
        │  writes pcapng to file or pipe
        ▼
 wireshark / tshark (unprivileged)
   wiretap  → reads pcap, pcapng, etl, snoop, … formats
   epan     → dissector tree (Ethernet→IP→TCP→TLS→…), reassembly, expert info
   dfilter  → compiles display filters (-Y) and evaluates them on the field tree
   taps     → statistics (-z), follow streams, export objects
   extcap   → external capture programs (sshdump, ciscodump, nflog/dbus via libpcap, randpkt…)
```

- **Privilege separation:** tshark and the GUI spawn `dumpcap` as a child. If the user can't execute it, you get "Couldn't run dumpcap in child process: Permission denied".
- **Single pass vs two pass:** tshark is single-pass by default, so fields that need future packets (request ↔ response links) need `-2`.
- **Where Linux egress capture sits:** outgoing packets reach `AF_PACKET` in `dev_queue_xmit`, after netfilter's OUTPUT/POSTROUTING hooks, so a packet dropped by nftables never appears on `eno1`. That makes "nothing on eno1" a valid kill-switch proof. Incoming packets are captured before netfilter, so dropped inbound packets still show up.
- **Debian packaging:** the postinst script applies the debconf answer (group, ownership, file capabilities, setuid fallback).
- **Stratoshark** reuses epan/dfilter on Falco system-call events.

---

## Cross-platform comparison

| Platform | Native capture API/service | Native tool | Wireshark support | Same or different |
|---|---|---|---|---|
| Linux | `AF_PACKET` + TPACKET_V3, classic BPF, eBPF/XDP, NFLOG | `tcpdump`, `ip monitor` | Full | Reference platform |
| BSD/macOS | `/dev/bpf*` (original BPF) + PKTAP process metadata | `tcpdump -k`, `nettop` | Full; process info since 4.6 | Kernel adds per-packet PID |
| Windows | Npcap NDIS LWF, `pktmon`, ETW NDIS-PacketCapture | `pktmon`, `netsh trace` (.etl) | Full via Npcap; reads `.etl`/pktmon pcapng | No in-kernel BPF; runs in the NDIS stack |
| Android | `AF_PACKET` needs root | none | `androiddump` extcap/adb, or PCAPdroid file | Sandboxed; non-root via VpnService API |
| iOS | Remote Virtual Interface (`rvictl -s <UDID>`) | none | Open on a Mac | Only from a tethered Mac |
| Cloud | AWS VPC Traffic Mirroring (VXLAN), GCP Packet Mirroring, Azure vTAP / Network Watcher | console/API | Reads the pcap, decodes VXLAN | Mirrored over a tunnel; no hypervisor NIC |
| Kubernetes | Ephemeral debug container + tcpdump, `kubectl sniff`, eBPF (Retina, Inspektor Gadget) | — | Remote stream via sshdump/pipe | Needs `NET_RAW` in the pod namespace |
| Network gear | Cisco EPC / `monitor capture`, Juniper `monitor traffic`, Arista tcpdump, ERSPAN | built in | `ciscodump`; decodes ERSPAN/GRE | Captured on ASIC or control plane |

---

## Alternatives

| Need | Same platform | Other platforms |
|---|---|---|
| CLI capture/print | `tcpdump`, `tshark`, `termshark` (TUI) | Windows `pktmon`, macOS `tcpdump -k` |
| Network security monitoring | Zeek, Suricata, Arkime | Security Onion bundles them |
| Forensic carving | NetworkMiner, Xplico, BruteShark | — |
| HTTP(S) only | mitmproxy, Burp Suite, Fiddler, Charles | Proxyman (macOS/iOS) |
| Commercial deep analysis | Riverbed/NetScout/Gigamon, Omnipeek | ExtraHop |
| Wireless | Kismet, aircrack-ng | Omnipeek Wi-Fi, Apple Wireless Diagnostics |
| BLE/IoT | nRF Sniffer (extcap), Ubertooth | Ellisys/Frontline hardware |
| Host/system calls | Stratoshark, sysdig, bpftrace, Retina | Windows ETW/Procmon |
| Mobile | PCAPdroid, HTTP Toolkit | iOS `rvictl` |

---

## Role: Network Engineer
- **Why:** the final word when teams argue whose fault it is.
- **Day to day:** TCP stream graphs (Stevens/tcptrace), `tcp.analysis.*`, DHCP DORA, STP, OSPF/BGP, MTU/MSS, captures at both ends.
- **Expert knowledge:** capture location changes what "retransmission" means; relative SEQ and offloads mislead; `[Bytes in flight]` vs receive window separates sender-, receiver- and network-limited flows; dumpcap with ring buffers in production, never the GUI.

## Role: SOC / Cybersecurity Analyst
- **Why:** PCAP is the ground truth behind IDS alerts.
- **Day to day:** pivot from a Suricata alert to the flow; DNS anomalies (`dns.qry.name.len > 50`); TLS fingerprints (`tls.handshake.ja4`, JA3 via plugin); beacon detection with fixed-interval I/O graphs; user-agent hunting.
- **Expert knowledge:** a custom column profile saves hours (malware-traffic-analysis style); `contains` is a byte search, `matches` is PCRE; confirm the server cert without decrypting; analyse malicious PCAPs in a VM.

## Role: Penetration Tester / Red Teamer
- **Why:** proves impact (cleartext creds, token leaks) and confirms attacks behave as expected.
- **Day to day:** confirm ARP spoofing / LLMNR-NBT-NS poisoning (Responder), capture NTLMv2 for cracking, inspect thick-client protocols, TLS downgrades, 802.1X/EAP.
- **Expert knowledge:** `ntlmssp` fields give a hashcat-ready string; Protocol Hierarchy shows attack surface in seconds; captures are sensitive loot under the rules of engagement.

## Role: DFIR
- **Why:** reconstructs what was transferred and when.
- **Day to day:** Export Objects, Follow Stream, timelines from `frame.time_epoch` to CSV, `smb2.filename`, IMF email, `capinfos -H` hashes.
- **Expert knowledge:** preserve and hash the original, work on `editcap` copies; pcapng comments as case notes; time-zone and clock-skew pitfalls; capture loss can understate exfiltration.

## Role: Protocol / Embedded Developer
- **Why:** the debugger for anything you put on a wire.
- **Day to day:** Lua dissectors (`Proto`, `ProtoField`, `DissectorTable.get("udp.port"):add(...)`) or C plugins; heuristic dissectors; `text2pcap` for logic-analyzer/UART dumps; USB via usbmon/USBPcap.
- **Expert knowledge:** `tvb` range safety (fuzzed input); TCP PDU reassembly (`dissect_tcp_pdus`, Lua `pinfo.desegment_len`); epan is a library, so the same dissector runs in tshark and Stratoshark.

## Role: OT/ICS & IoT Security Engineer
- **Why:** industrial protocols have no auth, and Wireshark decodes Modbus/TCP, DNP3, S7comm, IEC 104, EtherNet/IP-CIP, BACnet, PROFINET, OPC UA, MQTT, CoAP, Zigbee, BLE, CAN.
- **Day to day:** passive asset inventory (never active scanning on a plant floor); Modbus writes `modbus.func_code in {5 6 15 16}`; BLE pairing via nRF Sniffer.
- **Expert knowledge:** passive TAP/SPAN only; baselines beat signatures (OT traffic is periodic); vendor variants need custom Lua dissectors.

## Role: Telecom / VoIP Engineer
- **Why:** SIP/RTP debugging and mobile-core signalling (GTP, Diameter, S1AP/NGAP, SCTP) in one tool.
- **Day to day:** VoIP Calls → Flow Sequence ladders, RTP stream analysis (jitter, loss, sequence), RTP Player, SIP response codes.
- **Expert knowledge:** "Decode As" RTP when SDP wasn't captured; jitter per RFC 3550; 5G NAS needs keys; one-way audio is usually NAT/SDP, not codecs.

## Role: Cloud / DevOps SRE
- **Why:** overlays, meshes and load balancers hide which layer is failing; packets don't.
- **Day to day:** `kubectl debug` + `tcpdump -w -` piped to Wireshark; VXLAN/Geneve mirror traffic; mTLS failures (`tls.alert_message`); conntrack/SNAT exhaustion via RST patterns; HTTP/2 and gRPC resets.
- **Expert knowledge:** sidecars make in-pod captures look like localhost; capture on the node's veth; offloads are on in VMs; eBPF tools add pod/process context, Wireshark adds bytes.

---

## Related topics
- **Subjects:** computer networks (TCP/IP in practice), network security, digital forensics, wireless security, VoIP/telecom, ICS security, protocol engineering, OS networking internals, VPN testing (split tunnel, kill switch, DNS leaks, MTU, PQ key exchange).
- **Certifications/curricula:** Wireshark Certified Analyst (Foundation), Cisco CCNA/CCNP, CompTIA Network+/Security+/CySA+, CEH, OSCP/PNPT labs, SANS SEC503 and FOR572, GICSP/ICS515, Blue Team Level 1, CWNA/CWAP, university "Wireshark Labs" (Kurose & Ross).
- **Related library entries:** resolvectl (`~.` routing domain, D-Bus DNS changes), WireGuard (handshake sizes, PSK-based PQ), nmap, nc, dig.

---

## Follow-up Q&A

### Q1: Which VPN client functions, auth schemes and server types can Wireshark verify on a Linux client?

Context: a VPN client app with split tunnel, kill switch, DNS reconfiguration, MTU optimization, auto-connect on (secure) boot and log export; auth schemes LDAP (single user, multiple sessions), LDAP + session, LDAP + device ID, session + device ID; servers PQ or non-PQ. Capture on the physical NIC and the tunnel at the same time.

**Functionalities**

| # | Function | Verifiable? | Evidence |
|---|---|---|---|
| F1 | Split tunnel | ✅ | Excluded destinations in clear on eno1; included only on the tunnel and as encrypted VPN packets on eno1 |
| F2 | Kill switch | ✅ effect only | After the tunnel drops, nothing but reconnect attempts leaves eno1 (egress capture is after netfilter, so nft drops never appear) |
| F3 | DNS reconfiguration / leak | ✅ | Port 53 only via the tunnel to the VPN's DNS; none on eno1 (DoH hides DNS inside HTTPS). Config change itself visible on `dbus-system` if done via resolved/NetworkManager |
| F4 | MTU optimization | ⚠️ partly | Effects: SYN MSS on the tunnel, outer size ≤ path MTU, no fragments or frag-needed storms. Configured value via `ip link` |
| F5 | Auto-connect on boot | ⚠️ partly | Only if dumpcap runs as a systemd unit before the VPN service; shows first handshake time and pre-tunnel leaks |
| F6 | Application log export | ❌ | Local disk I/O. Exception: an upload's destination and TLS can be seen, not its content |

Not verifiable: Secure Boot itself (UEFI signature checks happen before any network stack; use `mokutil --sb-state`).

**Authentication schemes.** The client sends credentials to the VPN server inside an encrypted control channel; the server does the LDAP bind on its back end. From the client you can't see the bind, username, password, session token or device ID, only **behaviour**, unless you can decrypt the control channel (`SSLKEYLOGFILE` honoured by the client, IKE keys in Wireshark's IKEv2 table), or capture server-side (VPN server ↔ LDAP 389/636).

| # | Scheme | How to verify |
|---|---|---|
| A1 | LDAP, single user multiple sessions | Same user on 2 machines: both tunnels keep carrying data, or the first is torn down (TLS alert / RST / IKE DELETE) |
| A2 | LDAP + session | Reconnect shows a shorter handshake (TLS PSK resumption, fewer round trips) |
| A3 | LDAP + device ID | Same credentials from an unbound machine: handshake completes, then alert/close right after the auth exchange |
| A4 | Session + device ID | Copied session state rejected elsewhere; resumes on the original machine |

**Server type**

| # | Server | Verifiable? | Evidence |
|---|---|---|---|
| S1 | Post-quantum | ✅ TLS-based VPNs and IKEv2; ⚠️ not plain WireGuard | TLS 1.3 ServerHello `key_share` hybrid ML-KEM group (e.g. X25519MLKEM768), large ClientHello (> 1 MTU). IKEv2: additional key exchanges (RFC 9370) and IKE_INTERMEDIATE (RFC 9242). WireGuard: fixed X25519 handshake; PQ comes via a PSK (e.g. Rosenpass on UDP 9999), so the handshake looks identical |
| S2 | Non-PQ | ✅ | Classical groups only (x25519, secp256r1), no extra key exchanges |

A proprietary protocol shows only UDP/TCP payload unless you write a dissector; S1/S2 can't be told apart then.

**Verifiable combinations** (each with F1, F2, F3, F4 partly, F5 partly): A1+S1, A1+S2, A2+S1, A2+S2, A3+S1, A3+S2, A4+S1, A4+S2. Caveats: auth by behaviour only; S1 unconfirmable on WireGuard.

### Q2: Why does the Debian/Ubuntu install now ask "Should non-superusers be able to capture packets?"

**It isn't new.** The debconf question `wireshark-common/install-setuid` (boolean, default false) [18] has existed since about 2010: it was in Ubuntu 10.04 Lucid, where postinst could `addgroup --system wireshark` and `chown root:wireshark /usr/bin/dumpcap` only if answered Yes [19]; in 2014 it hung Docker builds on Ubuntu 14.04 despite `apt-get -y` [20]; and a 2015 Debian 8 bug report shows users answering it [21].

**Why you might not have seen it before:**
1. Debconf remembers the answer; upgrades and reinstalls don't ask again (only purge or `dpkg-reconfigure`).
2. Pre-installed images (e.g. Kali) are built non-interactively; Kali also ran as root by default until 2020.1.
3. GUI installers (Ubuntu Software/PackageKit) or `DEBIAN_FRONTEND=noninteractive` silently take the default No.
4. Non-Debian systems (Fedora, Arch, Windows, macOS) have no debconf.

**Mechanism:** capture needs `CAP_NET_RAW` (AF_PACKET socket) and `CAP_NET_ADMIN` (promiscuous/monitor mode). Yes → group `wireshark`, `root:wireshark` mode 750 on dumpcap, `setcap cap_net_raw,cap_net_admin+eip`, setuid 4750 fallback. Only the small dumpcap is privileged; the dissectors run as you.

**Why default No:** group members can sniff every packet on the host (other users, containers, cleartext creds), dumpcap has its own CVEs, and Debian lets the admin decide privilege grants with a safe default. README.Debian advises capturing as root with dumpcap and analysing as a normal user when the answer is No [22].

```bash
debconf-show wireshark-common
ls -l /usr/bin/dumpcap
getcap /usr/bin/dumpcap
sudo dpkg-reconfigure wireshark-common
sudo usermod -aG wireshark $USER
echo "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections
```
Certain: the prompt's age, default and mechanism (templates, postinst, README.Debian). Inferred: which of reasons 1–4 applied (check `/var/log/apt/history.log*`).

### Q3: What commands and flags can I run with wireshark/tshark?
See "Full flag reference" above.

### Q4: What are the other interfaces in `wireshark -D` (apart from eno1, adrishya, lo, docker)?
See "Interfaces listed by `wireshark -D`". VPN-relevant: `nflog` (watch kill-switch drops with `log group 5` → `-i nflog:5`), `dbus-system` (`dbus.member contains "DNS"` shows `SetLinkDNS`/`SetLinkDomains` calls to `org.freedesktop.resolve1`; not visible if the client edits `/etc/resolv.conf` directly), `sdjournal` (VPN service logs on the packet timeline), `any` (quick look only; use explicit interfaces for evidence).

### Q5: Too many flag combinations; make it easy
See "The mental model", "Core", and "Shell shortcuts". Example test with the shortcuts:
```bash
cap killswitch.pcapng
look killswitch.pcapng 'frame.interface_name=="eno1" && !(ip.addr==1.2.3.4)'
deep killswitch.pcapng 57
who  killswitch.pcapng 'frame.interface_name=="eno1"'
```
Filters to learn: `frame.interface_name=="eno1"`, `frame.interface_name=="adrishya"`, `ip.addr==<server>`, `!(ip.addr==<server>)`, `dns`, `tls.handshake`, `tls.alert_message || tcp.flags.reset==1`, `ip.flags.mf==1 || icmp.type==3`. DNS leak = `frame.interface_name=="eno1" && dns`.

### Q6: Why were so many flags developed if they're rarely needed?
They are needed, just not by everyone at once.
1. **tshark mirrors the GUI headlessly:** Statistics → `-z`, Preferences → `-o`, Decode As → `-d`, Export Objects → `--export-objects`, profiles → `-C`.
2. **Different jobs hit different limits:** `-b` (disk on multi-day captures), `-B`/`-s` (drops on 10/40 Gbps), `-a` (scripts/cron), `-T json/ek` + `-e` (SIEM ingestion), `-2`/`-R` (single pass can't see the future), `-d` (non-standard ports), `-I`/`-y` (raw 802.11), `-o tls.keylog_file` (encryption), `-X lua_script` (proprietary protocols), `-G fields` (260k+ field names).
3. **Inheritance from tcpdump:** `-i -w -r -c -s -n -D -f` kept muscle memory.
4. **Flags are rarely removed:** scripts depend on them.
5. **Many are just output formatting:** `-t -u -E -l -x -V -O`.

Usage tiers: everyone (`-i -w -r -Y` + `-V`/`-z`); regulars (`-T fields -e`, `-a`, `-b`, `-o`, `-d`, `-f`); specialists (`-I -y -2/-R -X -G -K -B -C --export-*`).
Certain: tcpdump heritage, single-pass `-2`, JSON/EK purpose (man page, User's Guide). Inferred: the never-remove policy (consistent with history, not a verified stated policy) and the persona-to-flag mapping.

### Q7: Segregate commands by our use case and other use cases
See "Commands by use case" (A: VPN testing F1–F5, A1–A4, S1/S2, reporting; B1–B11 other roles).

### Q8: We don't know the VPN server IP (it's inside the client app)
The client has to reach the server, so the IP is discoverable.

**Method 1 – ask the machine while connected (fastest):**
```bash
ip route | grep -v adrishya | grep '/32\|via'     # host route to server via real gateway
ip -6 route | grep -v adrishya
sudo ss -tunap state established                  # client process sockets
sudo wg show 2>/dev/null | grep endpoint          # WireGuard
sudo ip xfrm state 2>/dev/null | grep '^src'      # kernel IPsec
```
Exception: WireGuard-style policy routing (`ip rule`, fwmark) instead of a host route.

**Method 2 – from the capture** (`tshark -i eno1 -i adrishya -a duration:60 -w connect.pcapng`, then click Connect):
```bash
# a) biggest talker on the NIC = server
ME=$(ip -4 -o addr show eno1 | awk '{split($4,a,"/");print a[1]}')
tshark -r connect.pcapng -Y 'frame.interface_name=="eno1" && ip' -T fields -e ip.src -e ip.dst -e frame.len |
awk -v me="$ME" '{p=($1==me)?$2:$1; b[p]+=$3} END{for(k in b) print b[k], k}' | sort -rn | head -3
# b) peers contacted just before the first tunnel packet
tshark -r connect.pcapng -Y 'frame.interface_name=="adrishya"' -c 1 -T fields -e frame.time_relative
# c) the domain, via DNS and SNI
tshark -r connect.pcapng -Y 'dns.flags.response==1 && dns.a' -T fields -e dns.qry.name -e dns.a
tshark -r connect.pcapng -Y 'tls.handshake.type==1' -T fields -e ip.dst -e tls.handshake.extensions_server_name
```
No DNS query at all = hardcoded IP or private DoH; note it in the report.

**Method 3 – pin the tunnel by flow:** `tshark -r connect.pcapng -q -z conv,udp` (or `conv,tcp`), then `VPN='udp.port==51820'`, `VPN='esp || udp.port in {500 4500}'` or `VPN='ip.addr in {a b}'`, and replace `ip.addr==$S` with `($VPN)` in every command.

**Watch for:** the IP changing per connect (log it next to each capture), IPv6 (`ipv6.addr`, `ip -6 route`; IPv4-only tunnels leaking IPv6 are a classic bug), multiple probed servers ("fastest server"), CDN/anycast domains (the routing-table/socket IP is ground truth).

### Q9: Step 0 failed (permission denied, no device "adrishya", file could not be opened)
Three separate problems:
1. **`Couldn't run dumpcap in child process: Permission denied`:** user not in `wireshark`. `sudo dpkg-reconfigure wireshark-common` (Yes), `sudo usermod -aG wireshark sets`, log out and in (group membership is read at login). Verify: `id | grep -o wireshark`, `ls -l /usr/bin/dumpcap` (`-rwxr-x--- root wireshark`), `getcap /usr/bin/dumpcap`, `tshark -D` without sudo.
2. **`There is no device named "adrishya"`:** the tunnel exists only while the VPN is connected (`ip link show adrishya`). Already-connected tests: connect first, then capture both. Tunnel-appearing tests (connect, auth, kill switch, boot): capture on eno1 alone, where handshake, auth and leaks happen anyway. Or `-i any` (catches later interfaces) and map `sll.ifindex` via `ip -o link`; the tunnel index can change per connect.
3. **`could not be opened: Permission denied` even as root:** likely a snap-installed Wireshark (confinement blocks root writing another user's home) or AppArmor. Check `which -a tshark dumpcap`, `snap list | grep -i shark`, `sudo dmesg | grep -i 'apparmor.*denied'`. Fixing problem 1 removes the need for sudo; otherwise `sudo tshark -i eno1 -w - > test.pcapng` lets your shell create the file. Delete the empty `touch`-created file.

Retry:
```bash
F=test.pcapng; NIC=eno1; TUN=adrishya
ip link show $TUN && tshark -i $NIC -i $TUN -a duration:60 -w $F
tshark -r $F | head
```
If it still fails: `id`, `which -a tshark dumpcap`, `ls -l /usr/bin/dumpcap`.

---

## Sources

[1] Wireshark Foundation, "Wireshark 4.6.9 and 4.4.19 Released," Sep. 23, 2026. https://www.wireshark.org/news/20260923.html

[2] Wireshark Foundation, "Wireshark 5.0.0rc1 Development Release," Oct. 21, 2026. https://www.wireshark.org/news/20261021.html

[3] G. Combs, "What's New In 4.6?" SharkFest EU 2025 keynote slides. https://sharkfest.wireshark.org/retrospective/sfeu/presentations25eu/gerald-keynote-slides.pdf

[4] Wireshark Foundation, "Wireshark 4.6.0 Release Notes." https://www.wireshark.org/update/relnotes/wireshark-4.6.0.html

[5] Wireshark Foundation, release news, Apr. 29, 2026. https://www.wireshark.org/news/20260429.html

[6] Wikipedia, "Wireshark." https://en.wikipedia.org/wiki/Wireshark

[7] Wireshark User's Guide, "A Brief History Of Wireshark." https://www.wireshark.org/docs/wsug_html_chunked/ChIntroHistory.html

[8] G. Combs, "The evolution of system introspection from BPF to Wireshark to Falco," Wireshark blog. https://blog.wireshark.org/page/2/

[9] Wireshark User's Guide, section 1.4 history. https://www.wireshark.org/docs/wsug_html_chunked/ChIntroHistory.html

[10] Network World, "What is Wireshark?" https://www.networkworld.com/article/3663021/what-is-wireshark.html

[11] SDxCentral, "Open source Wireshark network protocol analyzer finally gets its own foundation," Mar. 2023. https://www.sdxcentral.com/articles/news/open-source-wireshark-network-protocol-analyzer-finally-gets-its-own-foundation/2023/03/

[12] Sysdig, "Sysdig Announces New Wireshark Foundation," Mar. 1, 2023. https://www.sysdig.com/press-releases/wireshark-foundation

[13] InfoQ, "Traffic Protocol Analyzer Wireshark Gets its Own Foundation," Mar. 2023. https://www.infoq.com/news/2023/03/wireshark-foundation

[14] Debian sources, "Stratoshark Release Notes" (wireshark 4.6.1-2). https://sources.debian.org/src/wireshark/4.6.1-2/doc/Stratoshark_Release_Notes.adoc

[15] Help Net Security, "Wireshark 4.6.0 brings major updates for packet analysis and decryption." https://www.helpnetsecurity.com/?p=346081

[16] heise online, "Wireshark 4.6: New functions for encrypted data." https://heise.de/-10749993

[17] Wireshark Foundation, "Wireshark 4.6.3 and 4.4.13 Released," Jan. 14, 2026. https://www.wireshark.org/news/20260114.html

[18] Debian packaging, `debian/templates` (wireshark-common/install-setuid). https://git.lekensteyn.nl/peter/wireshark/tree/debian/templates

[19] Launchpad bug #513903, "wireshark must be run as root unless wireshark-common is reconfigured." https://bugs.launchpad.net/ubuntu/+source/wireshark/+bug/513903

[20] Ask Wireshark, "debian package installation breaks all docker images…" https://osqa-ask.wireshark.org/questions/58798/

[21] Debian bug report, wireshark-common 1.12.1, Nov. 2015. https://groups.google.com/g/linux.debian.bugs.dist/c/tbJdHoh8EUs

[22] Debian, wireshark `README.Debian`. https://metadata.security.debian.org/changelogs/main/w/wireshark/stable_README.Debian ; G. Harris, "Give more detailed information about capture permissions on Debian," 2018. https://gitea.osmocom.org/osmocom/wireshark/src/commit/863ba5cd98978832ce5dc767f5f943c9a3e0c6f5/debian/README.Debian

Notes on certainty: BPF/libpcap history, the Qt switch (2.0, 2015), Npcap timing, cross-platform capture APIs, TLS group code points, role practices and certification lists come from general knowledge and were not re-verified in this session. Interface identifications for `adrishya` (VPN tunnel) and `wlx00c0caae649b` (ALFA adapter) are inferences to confirm on the machine.
