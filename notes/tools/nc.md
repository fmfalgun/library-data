---
tool: nc (netcat)
date: 2026-11-24
domains: [Networking, Security / VAPT, Linux & Unix sysadmin, DevOps / SRE]
roles: [Network Engineer, Penetration Tester / Red Teamer, Linux / Unix System Administrator, SOC / Blue Team Analyst, DevOps / SRE, Backend / Protocol Developer, CTF Player / Security Student, Embedded / IoT Engineer]
tags: [netcat, nc, ncat, netcat-openbsd, netcat-traditional, tcp, udp, unix-sockets, port-check, banner-grabbing, file-transfer, firewall-testing]
---

# nc (netcat)

## Summary
`nc` opens a raw TCP, UDP or Unix-domain socket connection, or listens for one, and wires it to stdin/stdout. That makes the network usable from any shell pipeline. Hobbit released it in 1995 as "a network version of `cat`", and it became the "TCP/IP Swiss army knife". Today **"nc" is a name, not one program**: depending on the system it is Hobbit's original (netcat-traditional), the OpenBSD rewrite (Debian, Ubuntu, macOS and BSD default), Nmap's Ncat (RHEL/Fedora), BusyBox nc (Alpine, routers) or GNU netcat. The flags overlap but are not the same.

**Identify your variant first:** `nc -h 2>&1 | head -1`. The banner says `OpenBSD netcat …`, `Ncat …`, `BusyBox …`, or `[v1.10-NN]` for traditional. On Debian-family systems also run `readlink -f "$(which nc)"`.

---

## Install and availability

| Platform | What `nc` is | Install |
|---|---|---|
| Debian / Ubuntu | OpenBSD nc (`netcat-openbsd`); `/usr/bin/nc → /etc/alternatives/nc → nc.openbsd` | `apt install netcat-openbsd` / `netcat-traditional` |
| Kali | Ships `netcat-traditional` (`nc.traditional`, v1.10-50.1). Sources disagree on which one `nc` points to, so check with `readlink` | `apt install netcat-traditional`; switch with `update-alternatives --config nc` |
| RHEL / Fedora / Rocky | **Ncat**: the `nmap-ncat` package provides `nc`, `nc6`, `ncat` | `dnf install nmap-ncat` |
| Arch | Your choice: `openbsd-netcat` or `gnu-netcat` | `pacman -S openbsd-netcat` |
| macOS | Apple fork of OpenBSD nc, built in | `brew install netcat` / `nmap` for others |
| Alpine, containers, routers | BusyBox nc applet; available flags depend on build config | built in |
| Windows | Not built in. Ncat comes with the Nmap installer; old `nc.exe` ports exist | nmap.org installer |
| Android | Toybox/BusyBox `nc` via `adb shell`; Termux `netcat-openbsd` | — |

---

## Usage and commands (OpenBSD syntax unless noted; real output from OpenBSD netcat 1.226 on Ubuntu)

### 1. Port reachability check: `-z` (zero I/O) + `-v`
```
$ nc -zv -w1 127.0.0.1 8078-8081
nc: connect to 127.0.0.1 port 8078 (tcp) failed: Connection refused
nc: connect to 127.0.0.1 port 8079 (tcp) failed: Connection refused
Connection to 127.0.0.1 8080 port [tcp/http-alt] succeeded!
nc: connect to 127.0.0.1 port 8081 (tcp) failed: Connection refused
```

### 2. Speak a text protocol by hand (HTTP)
```
$ printf 'HEAD / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' | nc -w 3 127.0.0.1 8080
HTTP/1.0 200 OK
Server: SimpleHTTP/0.6 Python/3.13.18
Date: Tue, 17 Nov 2026 11:36:46 GMT
Content-type: text/html
Content-Length: 3
Last-Modified: Tue, 17 Nov 2026 11:36:45 GMT
```
HTTP and SMTP need CRLF (`\r\n`) line endings. `-C` sends CRLF for interactive input. Redis example: `printf 'PING\r\n' | nc -N localhost 6379` returns `+PONG`.

### 3. Banner grab
`nc -v host 22` prints something like `SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13`. SSH, SMTP and FTP servers announce themselves first, so you get the software and version without sending anything.

### 4. Listener / mini server
`nc -l 9000` (OpenBSD, Ncat) or `nc -l -p 9000` (traditional, BusyBox). Add `-k` (OpenBSD) to keep accepting clients.

### 5. File transfer
```
receiver$ nc -l 127.0.0.1 9100 > recv.txt
sender$   nc -N 127.0.0.1 9100 < index.html
receiver$ cat recv.txt
hi
```
`-N` calls `shutdown(SHUT_WR)` when stdin reaches EOF, so the receiver sees the end of the data. Traditional uses `-q 0` for this.

### 6. Unix-domain sockets: `-U` (OpenBSD only)
```
$ nc -lU /tmp/s.sock > u.txt &   ;   echo "via unix socket" | nc -NU /tmp/s.sock
$ cat u.txt
via unix socket
```
Real uses: `printf 'GET /containers/json HTTP/1.0\r\n\r\n' | nc -U /var/run/docker.sock`, or talking to Redis, PHP-FPM or systemd sockets.

### 7. UDP
`nc -u host 514` sends syslog lines; `nc -lu 5140` receives them.

### 8. Through a proxy
`nc -X 5 -x proxy:1080 host 22` goes via SOCKS5. `-X connect` goes via an HTTP CONNECT proxy. A classic use is as an SSH `ProxyCommand`.

### 9. TLS
Upstream OpenBSD (5.9 and later): `nc -c -v example.com 443`. Ncat: `ncat --ssl example.com 443`. **Debian/Ubuntu's OpenBSD build has no TLS**: `-h` lists no `-c/-C/-K`, and `ldd` shows no libtls. Use Ncat, `openssl s_client` or socat instead.

### 10. Relay / port forward
Use Ncat (`--sh-exec` to chain to a second connection) or `socat TCP-LISTEN:8000,fork TCP:target:80`. With plain OpenBSD nc this needs a named-pipe trick, so socat or Ncat is the cleaner choice.

---

## Output and fields explained
- **`succeeded!`** (OpenBSD) or **`open`** (traditional): the TCP 3-way handshake completed. With `-z`, nc then closes immediately.
- **`[tcp/http-alt]`** or **`(http-alt)`**: the service name for the port, looked up in the local `/etc/services`. It says nothing about what is actually running on the remote side.
- **`Connection refused`**: a RST came back, so the host is reachable but nothing listens on that port (or a host firewall REJECTed it). A **timeout** (no reply) usually means a firewall silently DROPped the packet. This distinction is nc's most valuable diagnostic signal.
- **`-w N`**: connect/idle timeout. Without it, a filtered port can hang for about 2 minutes.
- **Exit code**: 0 for success, 1 for failure. Scripts should rely on this, never on the output text, because the text differs between variants.
- **`Connection received on 10.20.0.15 51734`** (OpenBSD listener with `-v`): the address the connection arrived from, as seen after any NAT, plus the client's ephemeral source port (from the kernel's `ip_local_port_range`).
- Traditional `-v` listener: `listening on [any] 9901 ...` / `connect to [127.0.0.1] from localhost [127.0.0.1] 48918`.
- Traditional `-o file` hex dump: `> 00000000 68 65 6c 6c 6f 0a  # hello.`, where `>` is sent and `<` is received.

---

## Worked task: verify a firewall change end to end
Change CHG-1234 claims app01 → db01:5432 is open. Prove it, and prove data actually flows.
```bash
# 1. db01 (port free): test listener
db01$ nc -lkv 5432
Listening on 0.0.0.0 5432

# 2. app01: handshake test with timeout
app01$ nc -zv -w3 db01 5432 ; echo "exit=$?"
Connection to db01 5432 port [tcp/postgresql] succeeded!
exit=0
#   timeout -> firewall DROP / routing;  refused -> reached host, no listener / host REJECT

# 3. Prove payload passes (catches IPS/middleboxes that allow SYN but kill data, MTU black holes)
app01$ head -c 5M /dev/urandom | tee >(sha256sum) | nc -N db01 5432
db01$  nc -l 5432 | sha256sum          # hashes must match

# 4. Check the source IP the far side sees (NAT/SNAT surprises)
db01 (-v): Connection received on 10.20.0.15 51734
```

---

## Common mistakes, permissions and gotchas
- **Flag differences between variants**: `-e` is missing on OpenBSD; `-l -p` is required on traditional but rejected by upstream OpenBSD (Debian tolerates it); Ncat's `-i` is an idle timeout, not an interval; OpenBSD `-w` in listen mode does not time out an accept.
- **UDP "scans" lie**: UDP has no handshake. "Success" only means no ICMP port-unreachable came back, so filtered and open look the same. On localhost, `nc -zvu 127.0.0.1 9999` printed nothing on OpenBSD and exited 1.
- **Hanging connections**: neither variant half-closes on stdin EOF by default. Use `-N` (OpenBSD), `-q` (traditional and Debian's OpenBSD build), `-w`, or `--send-only` (Ncat).
- **Permissions**: binding below port 1024 needs root or `CAP_NET_BIND_SERVICE`. Everything else is unprivileged, because nc uses normal sockets, not raw sockets (unlike an nmap SYN scan).
- **DNS slowness**: `-n` skips name resolution.
- **IPv4 vs IPv6**: `localhost` may resolve to `::1` first. Force the family with `-4`/`-6`.
- **Cleartext and unauthenticated** unless you use TLS (`-c` upstream OpenBSD, `--ssl` Ncat).
- **Handshake ≠ application healthy**: a load balancer or proxy that completes the handshake can make a dead backend look alive.

---

## History and evolution
- **Roots**: Unix pipes and `cat` (1971); BSD sockets API (4.2BSD, 1983); TCP (RFC 793 → RFC 9293); UDP (RFC 768); telnet (RFC 854) as the original "raw TCP client".
- **28 Oct 1995**: Hobbit announces netcat on Bugtraq. 1.10 follows in March 1996 (Avian Research) with TCP/UDP, listen/connect, port ranges, `-o` hex dump, source routing, and `-e` exec gated behind the compile flag `GAPING_SECURITY_HOLE`. The README's case for it: unlike telnet, nc scripts cleanly and keeps errors on stderr.
- **1998**: Chris Wysopal (Weld Pond, L0pht) ports it to Windows NT. **Dec 2004**: a buffer overflow in Netcat for Windows 1.1 is reported; 1.11 fixes it.
- **2001**: Eric Jackson's clean-room rewrite for OpenBSD. It adds IPv6, SOCKS/HTTP CONNECT proxies (RFC 1928) and Unix sockets, and drops `-e`.
- **Early 2000s**: GNU netcat (Giovanni Giacobbi, now largely dormant); socat (Gerhard Rieger) generalises the idea to any two byte streams; cryptcat and sbd add encryption.
- **2005–2009**: Ncat is built inside the Nmap project with no shared code, on Nmap's nsock library. It adds SSL, proxies, IPv6, connection brokering and access control.
- **2015–16**: Bob Beck adds TLS to OpenBSD nc via libtls (OpenBSD 5.9), and nc later gains `pledge()`/`unveil()` sandboxing. FreeBSD and NetBSD import it.
- **Today**: OpenBSD netcat.c is still edited (rev 1.229, Nov 2024); Debian/Ubuntu ship 1.226; Kali packages netcat-traditional 1.10-50.1; Ncat ships with Nmap 7.991 (6 Aug 2026).

## How it works internally
- **Connect mode**: `socket()` → `connect()`. **Listen mode**: `socket()` → `bind()` → `listen()` → `accept()`.
- **Data loop**: OpenBSD's `readwrite()` runs a `poll()` loop that copies data between stdin/stdout and the socket file descriptor using `atomicio()` for complete reads and writes. Traditional uses older `select()`-based code with fixed buffers and global state.
- **`-z`**: connect then close immediately. For UDP `-z`, OpenBSD writes a few probe bytes and checks whether the kernel reports `ECONNREFUSED` (caused by an ICMP port-unreachable), which is why a UDP result only means "maybe open".
- **`-N`**: `shutdown(SHUT_WR)` on stdin EOF, so the peer reads EOF while nc can still receive.
- OpenBSD uses `getaddrinfo()` (that's where IPv6 support comes from); traditional predates it.
- *Certain*: the socket flow and the `-N` → `shutdown()` behaviour (source). *Inferred from older source*: the exact number of UDP probe bytes may vary by release.

## Why it is still used
It is about the smallest possible bridge between the socket API and Unix pipes. One generic tool replaces a dozen protocol-specific clients, and it shows you the bytes on the wire with no client-side interpretation. It sits at **layer 4**, between application clients (curl, psql, openssl s_client) and packet tools (hping3, scapy, tcpdump). It's preinstalled almost everywhere, unprivileged and tiny, so it is the default "does the port answer?" step in runbooks, containers and incident response.

---

## Cross-platform comparison

| Platform / tool | Mechanism | TCP | UDP | Listen | Pipe raw data | TLS |
|---|---|---|---|---|---|---|
| OpenBSD nc | BSD sockets + poll loop | ✓ | ✓ (weak test) | ✓ | ✓ | ✓ `-c` (upstream only) |
| Traditional nc | BSD sockets + select loop | ✓ | ✓ | ✓ | ✓ | ✗ |
| Ncat | Nmap nsock | ✓ | ✓ | ✓ + broker | ✓ | ✓ `--ssl` |
| socat | Generic address pairs | ✓ | ✓ | ✓ | ✓ | ✓ |
| Windows `Test-NetConnection` (PowerShell 4.0+) | .NET TcpClient connect | ✓ | ✗ | ✗ | ✗ | ✗ |
| bash `/dev/tcp`, `/dev/udp` | bash redirection | ✓ | ✓ | ✗ | ✓ | ✗ |
| Cloud reachability analyzers (AWS VPC Reachability Analyzer, Azure Network Watcher, GCP Connectivity Tests) | Config/route analysis, no packets sent | model | model | n/a | ✗ | n/a |
| Cisco IOS `telnet ip port` | Telnet client | ✓ | ✗ | ✗ | partial | ✗ |

## Alternatives
- **Unix**: socat, Ncat, bash `/dev/tcp`, telnet, `openssl s_client`, `curl telnet://host:port`, nmap (real scanning), hping3 (crafted packets), cryptcat, sbd, pwncat (Python), websocat (WebSockets).
- **Windows**: `Test-NetConnection` / `tnc` (built in, TCP only), PortQry.exe, powercat (PowerShell), Ncat.exe, WSL nc.
- **Android**: Toybox/BusyBox `nc` via adb; Termux netcat-openbsd. **iOS**: no shell; network-utility apps only do reachability checks.
- **Cloud**: the path-analysis services above. **Network devices**: IOS/Junos `telnet <ip> port <n>`, MikroTik `/tool fetch`, BusyBox nc on embedded Linux.

---

## Role sections

### Network Engineer
The first tool after ping for checking firewalls and ACLs: `-zv -w` to validate change tickets, listeners at both ends of a path, `-s <src-ip>` to test from a specific interface, source address or VRF, and `-M` for TTL. **Expert knowledge**: refused (RST) vs. timeout (DROP) vs. "the handshake succeeds but data dies", which points to IPS, MTU or PMTUD black holes. Test the last one by pushing a multi-MB stream, not just a handshake. A proxy or load balancer can fake liveness for a dead backend.

### Penetration Tester / Red Teamer
In authorised engagements and labs: banner grabbing, quick checks on targeted ports, moving files in and out, and catching callbacks during exploitation exercises. **Expert knowledge**: which variant the target has, since OpenBSD nc or BusyBox is common and traditional's extra features are often missing. nc is cleartext and noisy, and AV/EDR flag the traditional builds. Professionals prefer TLS-capable tools (Ncat `--ssl`, socat) for operational security.

### Linux / Unix System Administrator
Checking whether a daemon really listens on a reachable interface, sending logs to remote syslog, streaming `tar` or `dd` images between hosts when scp isn't available, and querying local Unix sockets. **Expert knowledge**: `ss -ltnp` shows what is bound locally, nc shows what is reachable remotely, and you need both. Use `-N`/`-q` to avoid hangs; `/etc/services` names are cosmetic.

### SOC / Blue Team Analyst
Mostly hunting for nc rather than using it. Signals: `nc`/`ncat` with exec options (`-e`, `-c` on traditional, `--sh-exec`/`--exec` on Ncat), named pipes combined with nc, a shell whose parent is nc, new listening sockets on servers, and long-lived sessions to high ports. nc is also useful as a test listener when validating detections. **Expert knowledge**: attackers rename binaries, so detect the behaviour (a shell's stdin/stdout wired to a socket) rather than the process name. Bash `/dev/tcp` leaves no nc process at all.

### DevOps / SRE
Wait-for-dependency loops (`until nc -z db 5432; do sleep 1; done`), init containers, and debugging Kubernetes Services and NetworkPolicies from a netshoot pod. **Expert knowledge**: Alpine uses BusyBox nc, whose flags depend on its build. `nc -z` only proves the TCP accept, not application readiness, so use the real client for readiness probes. NetworkPolicy drops appear as timeouts, not refusals.

### Backend / Protocol Developer
Hand-crafting HTTP, SMTP, Redis or memcached requests; `nc -lk` as a fake server to see exactly what a client sends; `nc -U` for IPC sockets such as Docker's. **Expert knowledge**: CRLF framing, half-close (`shutdown` vs `close`) semantics, Nagle and delayed-ACK effects. `nc -l | xxd` (or traditional's `-o`) beats any logger for wire-format bugs.

### CTF Player / Security Student
Most challenge services are reached with `nc chall.host 1337`, and nc is where students first meet networking from the shell. **Expert knowledge**: move to pwntools `remote()` for scripted interaction, handle binary data carefully, and understand how NAT and firewalls affect which side can initiate a connection.

### Embedded / IoT Engineer
BusyBox nc is often the only network tool on a board: pulling logs, pushing firmware or test files (`nc -l -p 9000 > fw.bin`), bridging debug consoles. **Expert knowledge**: BusyBox applet options vary by `.config`, and some builds include exec. That is a security risk in shipped products, so audit firmware images and init scripts for leftover debug listeners.

---

## Related topics
- **Subjects**: TCP/IP fundamentals (handshake, RST vs DROP), socket programming, firewall testing, troubleshooting methodology, incident response, container networking, Unix philosophy and pipes.
- **Certifications and curricula**: CompTIA Network+, Security+, PenTest+, CySA+; OSCP / PEN-200; eJPT; CEH; SANS SEC504; RHCSA / LFCS; CCNA / CCNP (host-side check alongside device ACLs); CKA / CKAD (Service and NetworkPolicy debugging).
- **Frameworks**: MITRE ATT&CK techniques such as ingress tool transfer and non-application-layer protocols, where netcat commonly appears as the tool used.

---

## Follow-up Q&A

### Q: Comparative analysis between nc (traditional) and netcat-openbsd
Both were installed side by side for testing: `netcat-traditional 1.10-48` and `netcat-openbsd 1.226-1ubuntu2`.

**At a glance**

| | Traditional nc (Hobbit) | netcat-openbsd |
|---|---|---|
| Author | Hobbit, 1995–96, plus Debian patches | Eric Jackson's rewrite (2001); Bob Beck added TLS (2015) |
| Codebase | Original 1.10, no upstream development since 1996 | New code, still developed in the OpenBSD tree |
| `-h` banner | `[v1.10-48]` | `OpenBSD netcat (Debian patchlevel 1.226…)` |
| Binary / deps | 35 KB; libc only | 39 KB; libc + libbsd + libresolv |
| License | Hobbit's permissive licence | BSD |
| Philosophy | Swiss-army knife including program exec | Lean and safe: no exec; IPv6, proxies, Unix sockets, TLS added |
| Default `nc` on | Older distributions; packaged in Kali | Debian, Ubuntu, macOS (Apple fork), FreeBSD, NetBSD |

**Only in one of them**

| Capability | Traditional | OpenBSD |
|---|---|---|
| Program exec on connect | `-e`, `-c` | ✗ (`invalid option -- 'e'`) |
| Hex dump of traffic | `-o file` | ✗ |
| IP source routing | `-g`, `-G` | ✗ |
| IPv6 | ✗ (`invalid option -- '6'`) | `-4` / `-6` |
| Unix sockets | ✗ (`invalid option -- 'U'`) | `-U` |
| SOCKS4/5 and HTTP CONNECT | ✗ | `-X`, `-x`, `-P` |
| Half-close on EOF | `-q 0` | `-N` |
| Repeated accepts | ✗ | `-k` |
| Pass socket fd | ✗ | `-F` |
| TCP MD5 (BGP) | ✗ | `-S` |
| TTL/min-TTL, buffers, routing table | ✗ | `-M`, `-m`, `-I`/`-O`, `-V` |
| Stop after N packets | ✗ | `-W` |
| TLS | ✗ | `-c`, `-C`, `-K`, `-e name` (upstream only) |

**Same letter, different meaning**

| Flag | Traditional | OpenBSD |
|---|---|---|
| `-k` | TCP keepalive | Keep listening after a client leaves |
| `-c` | Run a shell command | Upstream: use TLS |
| `-p` | Required with `-l` (listening port) | Local *source* port; upstream rejects it with `-l`, Debian tolerates it |
| `-q` | Quit N seconds after stdin EOF | Not upstream; a Debian addition |
| `-r` | Randomise local and remote ports | Randomise remote ports |
| `-o` / `-O` | `-o` writes the hex dump | `-O` sets the TCP send buffer |

Shared, with the same meaning: `-l -n -u -v -w -z -s -i -t -C -T -b` (output and edge cases still differ).

**Observed behaviour**
- Scan output: traditional `-v` prints **only open ports** (`localhost [127.0.0.1] 8080 (http-alt) open`) and needs `-vv` for closed ones plus a `sent 0, rcvd 0` summary. OpenBSD prints every port (`succeeded!` / `Connection refused`).
- Traditional does reverse DNS (`localhost [127.0.0.1]`) and shows `(UNKNOWN)` with `-n`.
- **Traditional scans ranges high to low** (`-zvv 8001-8004` reported 8004 → 8001); OpenBSD scans low to high.
- Listener `-v` messages: traditional `listening on [any] 9901 ...` / `connect to [127.0.0.1] from localhost [127.0.0.1] 48918`; OpenBSD `Listening on 0.0.0.0 9900` / `Connection received on localhost 44024`.
- EOF timing (`echo x | nc host port`): OpenBSD with no flag took 2.70 s (it waited for the peer to close), with `-N` 0.006 s; traditional with no flag 2.70 s, with `-q0` 0.007 s.
- `-k`: OpenBSD `-lk` accepted two clients one after another; traditional `-l -k` (keepalive) refused the second connection.
- `-o` hex dump (traditional): `> 00000000 68 65 6c 6c 6f 0a  # hello.`
- UDP check against a closed port: both exited 1; traditional printed `Connection refused`.

**Debian patches matter.** Upstream OpenBSD nc has TLS and `pledge()`. Debian/Ubuntu's build has no TLS (no `-c/-C/-K` in `-h`, no libtls in `ldd`), adds `-q`, and relaxes `-l -p`. macOS nc is a separate Apple fork. So "OpenBSD nc" on Ubuntu, on OpenBSD and on macOS are three slightly different tools.

**Design and security**: OpenBSD removed exec because a binary that attaches a program to a socket is effectively a ready-made backdoor, and Hobbit had already gated it behind `GAPING_SECURITY_HOLE`. Traditional is 1990s `select()` code with fixed buffers and global state; OpenBSD uses `poll()`, `getaddrinfo()` and `atomicio()`, and is reviewed as part of the OpenBSD base system. Debian's 48+ patch revisions keep traditional alive. AV/EDR products flag traditional builds more often.

**Portable scripting**
```bash
case "$(nc -h 2>&1 | head -1)" in
  OpenBSD*) NCV=openbsd ;;  \[v1.10*) NCV=traditional ;;  *Ncat*) NCV=ncat ;;  *BusyBox*) NCV=busybox ;;
esac
nc -z -w2 "$host" "$port" && echo up || echo down          # exit code, not text
[ "$NCV" = traditional ] && nc -l -p "$port" || nc -l "$port"
```
*Certainty*: flags, outputs, timings and the missing TLS were observed directly. That `-q` and the relaxed `-l -p` are Debian additions comes from upstream man pages and Debian patch history (well established, but the patches weren't diffed in this session).

### Q: Where to use nc (Kali / traditional) vs nc (Debian/Ubuntu / OpenBSD)
Check first: `readlink -f "$(which nc)"`. Kali packages `netcat-traditional` (v1.10-50.1), but sources disagree on which variant `nc` points to by default. Switch with `sudo update-alternatives --config nc`, or call `nc.traditional` / `nc.openbsd` directly.

**Use OpenBSD nc (Debian/Ubuntu default) for:**
- Production servers, containers and runbooks: it's already installed everywhere.
- Firewall, ACL and change validation: clear per-port output, IPv6, `-s`, `-M`.
- Local daemons over Unix sockets (`-U`): Docker, Redis, PHP-FPM, systemd.
- Proxies (`-X`/`-x`): SOCKS and HTTP CONNECT, e.g. SSH `ProxyCommand`.
- Repeated test listeners (`-lk`) and clean scripted transfers (`-N`).
- CI/CD and Kubernetes wait-for-port loops (use the exit code).
- Security-conscious hosts: no exec feature, so it is the safer binary to leave installed.

**Use traditional nc (Kali's netcat-traditional) for:**
- Your own attack box in authorised pentests, labs and CTFs, where course material (OSCP, eJPT, older SANS) often assumes its syntax and options.
- Quick traffic hex dumps with `-o`.
- Old scripts and docs written for `nc -l -p`, its `open` output, or high-to-low scan order.
- Practising for legacy and embedded targets: BusyBox nc behaves much like traditional.
- Learning the history: it is the original 1996 code.

**Use neither (Ncat or socat) when you need:** TLS (Debian's OpenBSD build lacks it and traditional never had it), Windows support, access control, connection brokering or multi-client relays.

| Situation | Choice |
|---|---|
| Servers, containers, automation, ops runbooks | OpenBSD |
| Your own Kali box, authorised engagement or lab | Traditional (plus OpenBSD and Ncat installed alongside) |
| Remote host you don't control | Expect OpenBSD, BusyBox or none; don't assume traditional's features |
| Scripts that must run on any system | Only `-z -w -v -u`, exit codes, detect the variant |
| Anything sensitive | A TLS-capable tool, not plain nc |

---

## Sources
- [Netcat – Wikipedia](https://en.wikipedia.org/wiki/Netcat)
- [Hobbit, "New tool available: Netcat", Bugtraq 1995](https://seclists.org/bugtraq/1995/Oct/28)
- [Ncat compatibility matrix – SecWiki](https://secwiki.org/w/Ncat/Compatibility)
- [Ncat guide (Nmap source)](https://gitverse.ru/githubmirror/nmap/tag/v7.991/ncat/docs/ncatguide.xml)
- [OpenBSD netcat.c source](https://src.rcs.uwaterloo.ca/xref/openbsd-src/usr.bin/nc/netcat.c)
- [FreeBSD vendor import of OpenBSD 5.9 nc (TLS)](https://lists.freebsd.org/pipermail/svn-src-all/2016-April/122316.html)
- [Arch FS#49759 – OpenBSD nc TLS since 5.9](https://bugs.archlinux.org/task/49759)
- [Bugtraq: Netcat for Windows 1.11 fix (Chris Wysopal)](https://seclists.org/bugtraq/2004/Dec/433)
- [GIAC paper – Netcat, the TCP/IP Swiss army knife](https://giac.org/paper/gsec/436/netcat-tcp-ip-swiss-army-knife/101060)
- [diegocr/netcat – Netcat for Windows](https://www.GitHub.com/diegocr/netcat)
- [Kali tools – netcat](https://www.kali.org/tools/netcat)
- [Ask Ubuntu – traditional vs openbsd](https://askubuntu.com/questions/346869/what-are-the-differences-between-netcat-traditional-and-netcat-openbsd)
- [Graham Helton – which $(nc) && when?](https://grahamhelton.com/blog/which_netcat)
- [Fedora nmap-ncat package](https://packages.fedoraproject.org/pkgs/nmap/nmap-ncat/fedora-44-updates.html)
- [Nmap 7.991 release coverage](https://tech-insider.org/?p=23117)
- [Linode – Learning netcat](https://www.linode.com/docs/guides/netcat)
- [IT-Connect – Test-NetConnection](https://www.it-connect.fr/tester-un-port-avec-powershell-test-netconnection/)
- [softpanorama – netcat](https://softpanorama.org/Net/Netutils/netcat.shtml)
- Local tests: OpenBSD netcat 1.226-1ubuntu2 and netcat-traditional 1.10-48 on Ubuntu 24.04 (17 Nov 2026)
