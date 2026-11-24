---
tool: curl
date: 2026-11-24
domains: [Networking, Web/API Development, DevOps/SRE, Cybersecurity, Embedded Systems, Linux]
roles: [Backend/API Developer, DevOps/SRE Engineer, Network Engineer, Penetration Tester (VAPT), Cybersecurity Analyst (Blue team), Embedded/Systems C Developer, Linux Sysadmin, Open-Source Maintainer]
tags: [curl, libcurl, http, https, http2, http3, quic, tls, alpn, api-testing, rest, ssrf, cve, supply-chain, wget, invoke-webrequest, cli, c-library]
---

# curl

## Summary

**curl** is a command-line tool, and **libcurl** a C library, for transferring data with URLs. It works over about 25 protocols, including HTTP/1.1, HTTP/2 and HTTP/3, FTP(S), SFTP/SCP, SMTP(S), IMAP(S), POP3(S), LDAP(S), MQTT, TFTP, DICT, Gopher, RTSP, WebSocket, file:// and Unix sockets.

- **Problem it solves:** moving bytes to or from any URL, over almost any internet protocol, the same way from a shell, a script, or (through libcurl) inside any program.
- **Who made it:** Daniel Stenberg, building on Rafael Sagula's HttpGet (1996). The tool was renamed urlget in 1997 and became curl 4.0 on 20 March 1998.
- **Scale:** curl is estimated at 10+ billion installations in 2023 and about 30 billion by its 30th anniversary (Nov 2026). It ships in every OS, phone, car, TV and console stack.
- **State in Nov 2026:** the latest release is 8.23.0 (14 Oct 2026). Releases come every 8 weeks, and the next one is planned for 9 Dec 2026. 2026 set records for the number of CVEs fixed.

---

## Install and availability

| Platform | How |
|---|---|
| Linux | Preinstalled almost everywhere; `apt install curl` / `dnf install curl` / `apk add curl` |
| macOS | Ships with the OS (Apple's build); `brew install curl` gets the latest version |
| Windows 10 1803+ / 11 | `C:\Windows\System32\curl.exe` ships with the OS. **Gotcha:** in Windows PowerShell 5.1, `curl` is an *alias* for `Invoke-WebRequest`. Type `curl.exe` to get the real one. |
| Android / iOS | libcurl is embedded inside apps. The CLI is available via Termux on Android or a-Shell on iOS. |
| Embedded | libcurl is cross-compiled into routers, TVs, cars and consoles |

### Know your build: `curl -V`
Real output from an Ubuntu 24.04 machine:
```
curl 8.5.0 (x86_64-pc-linux-gnu) libcurl/8.5.0 OpenSSL/3.0.13 zlib/1.3.1.zlib-ng brotli/1.1.0 zstd/1.5.5 libidn2/2.3.7 libpsl/0.21.2 libssh/0.10.6/openssl/zlib nghttp2/1.59.0 librtmp/2.3 OpenLDAP/2.6.10
Release-Date: 2023-12-06, security patched: 8.5.0-2ubuntu10.16
Protocols: dict file ftp ftps gopher gophers http https imap imaps ldap ldaps mqtt pop3 pop3s rtmp rtsp scp sftp smb smbs smtp smtps telnet tftp
Features: alt-svc AsynchDNS brotli GSS-API HSTS HTTP2 HTTPS-proxy IDN IPv6 Kerberos Largefile libz NTLM PSL SPNEGO SSL threadsafe TLS-SRP UnixSockets zstd
```
| Field | Meaning |
|---|---|
| Line 1 | The libcurl version, the TLS backend (OpenSSL 3.0.13), and the compression, IDN, PSL, SSH, HTTP/2 (nghttp2), RTMP and LDAP libraries it was linked against |
| `security patched: …` | The distro backported fixes into an old version number. Don't judge a curl's safety by its version number alone. |
| Protocols | What this build can actually speak. These are compile-time choices: `smb` disappears in 8.23+, and builds can drop any protocol. |
| Features | Compile-time capabilities. There is no `HTTP3` here, so `--http3` will fail on this build. |

---

## Usage and commands

### 1. Fetch and save a file
```bash
curl -fsSLO https://example.com/file.tar.gz   # -O = keep the remote name
curl -fsSL -o out.json https://api.example.com/x
```
- `-f` / `--fail`: exit with status 22 on HTTP ≥ 400 instead of saving the error page as if it were your file. `--fail-with-body` keeps the body.
- `-s` = silent (no progress meter); `-S` = still show errors
- `-L` = follow redirects
- `-o FILE` = write to FILE; `-O` = use the remote file name

### 2. Headers only
```bash
curl -sI https://example.com
```
```
HTTP/2 200
content-type: text/html; charset=UTF-8
cache-control: max-age=3600
server: ECAcct
```
`-I` sends a **HEAD** request. Some servers answer HEAD differently from GET. To see the headers of a real GET: `curl -s -D - -o /dev/null URL`.

### 3. Verbose: see the whole conversation
Real trace against `https://pypi.org/simple/`, trimmed:
```
*   Trying 151.101.64.223:443...
* Connected to pypi.org (151.101.64.223) port 443
* ALPN: curl offers h2,http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / X25519 / RSASSA-PSS
* ALPN: server accepted h2
* Server certificate:
*  subject: CN=pypi.org
*  subjectAltName: host "pypi.org" matched cert's "pypi.org"
*  SSL certificate verify ok.
* using HTTP/2
> GET /simple/ HTTP/2
> Host: pypi.org
> User-Agent: curl/8.5.0
< HTTP/2 200
```
| Prefix / line | Meaning |
|---|---|
| `*` | curl's own commentary: DNS, connect, TLS, decisions |
| `>` | Bytes curl **sent** (request line and headers) |
| `<` | Bytes the server **sent back** |
| `IPv4: a, b, c` | Every address DNS returned; curl tries them (happy eyeballs) |
| `ALPN: curl offers h2,http/1.1` | The HTTP version is negotiated inside the TLS ClientHello (RFC 7301) |
| `SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / X25519 / RSASSA-PSS` | TLS version / cipher suite / key-exchange group / signature algorithm |
| `subjectAltName … matched` | Hostname verification passed (RFC 6125) |
| `CAfile` / `CApath` | Where the trusted root certificates came from |

Deeper options: `--trace-ascii -` (full bytes, including bodies) and `--trace-time`. (Note: in the capture sandbox the issuer line showed an internal egress-proxy CA, so it is left out here. On the public internet it shows a public CA.)

### 4. Send JSON to an API
```bash
curl -sS https://api.example.com/items \
  -H "Authorization: Bearer $TOKEN" \
  --json '{"name":"x","qty":2}'
```
`--json` (7.82+) = `--data` + `Content-Type: application/json` + `Accept: application/json`. On older builds: `-H 'Content-Type: application/json' -d @body.json`. Use double quotes around the header so `$TOKEN` expands.

### 5. Timing breakdown (`-w` write-out)
```bash
curl -sS -o /dev/null -w 'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total} code=%{http_code} ver=%{http_version}\n' https://github.com
```
Real output (captured behind a proxy, which explains the 400 and HTTP/1.1):
```
dns=0.000021 connect=0.000134 tls=0.204874 ttfb=0.264651 total=0.264732 code=400 ver=1.1
```
| Variable | Meaning |
|---|---|
| `time_namelookup` | DNS done |
| `time_connect` | TCP (or QUIC) connected |
| `time_appconnect` | TLS handshake done |
| `time_pretransfer` / `time_starttransfer` | About to send / first response byte (TTFB) |
| `time_total` | Everything done |
| `http_code`, `http_version`, `remote_ip`, `ssl_verify_result`, `size_download`, `speed_download`, `num_redirects` | Other useful variables |

**Key point:** all times are **cumulative from the start**, not per phase. TLS cost = appconnect − connect; server think time ≈ starttransfer − appconnect. Put a format in a file and reuse it with `-w @fmt.txt`.

### 6. Form upload / multipart
```bash
curl -F 'file=@report.pdf' -F 'note=hi' https://upload.example.com
```
`-F` builds `multipart/form-data`. `@` attaches a file, and `<` reads the file's content as a field value.

### 7. Cookies and sessions
```bash
curl -c jar.txt -b jar.txt -d 'user=a&pass=b' https://site/login
curl -b jar.txt https://site/dashboard
```
`-c` = write cookies to a file (Netscape format); `-b` = send cookies (from a file or a literal string).

### 8. Override DNS / pin a backend
```bash
curl --resolve app.example.com:443:10.0.0.12 https://app.example.com/health
curl --connect-to ::canary-lb:443 https://app.example.com/
```
SNI, the `Host` header and certificate checking all still use the real name. Only the IP you connect to changes. This is the standard way to test before a cutover or to hit one node behind a load balancer.

### 9. Resume a download, limit speed, retry
```bash
curl -C - -O --limit-rate 2M --retry 5 --retry-all-errors https://mirror/iso
```
- `-C -` = continue from the size of the local file
- `--retry-all-errors` also retries on HTTP errors
- Pair with `--connect-timeout` and `--max-time`

### 10. Protocols beyond HTTP
```bash
curl -T file.txt sftp://user@host/~/                                   # SFTP upload
curl --url smtps://smtp.gmail.com:465 --mail-from a@x --mail-rcpt b@y -T mail.txt -u a@x   # send mail
curl -s dict://dict.org/d:latency                                      # DICT protocol
curl --unix-socket /var/run/docker.sock http://localhost/containers/json   # Docker API, no SDK
```

### More worth knowing
- `--http3` (HTTP/3 with fallback) / `--http3-only` / `--http2-prior-knowledge` / `--http1.1`
- `-x http://127.0.0.1:8080 -k`: send traffic through Burp or ZAP
- `-z FILE`: download only if newer than FILE; `--netrc`: credentials from `~/.netrc`
- `-K FILE`: config file of options; `--variable` / `--expand-*`: templating (8.3+)
- `--follow` (8.16+) and `--out-null` (8.16+); `--path-as-is`, `--request-target`, `--globoff`
- `wcurl`: the curl project's wget-like wrapper for simple downloads

---

## Realistic task: "Is the new backend safe to switch traffic to?"
```bash
# 1. Hit the new LB directly, with production SNI and Host
curl -sS --connect-to app.example.com:443:new-lb.internal:443 \
  -o /dev/null -w '%{http_code} %{time_total} %{ssl_verify_result} %{remote_ip}\n' \
  https://app.example.com/health
# → 200 0.143 0 10.2.0.5   (ssl_verify_result 0 = cert OK)

# 2. Compare the headers old vs new
diff <(curl -sI https://app.example.com/) \
     <(curl -sI --connect-to ::new-lb.internal https://app.example.com/)

# 3. A small latency sample (20 requests → ~p50, ~p95)
for i in $(seq 20); do curl -s -o /dev/null -w '%{time_starttransfer}\n' \
  --connect-to ::new-lb.internal https://app.example.com/; done | sort -n | sed -n '10p;19p'

# 4. Check it negotiates HTTP/2 and serves the right cert
curl -sv --connect-to ::new-lb.internal https://app.example.com/ -o /dev/null 2>&1 | grep -E 'ALPN|subject:|expire'
```

---

## Common mistakes, permissions and gotchas
- **Missing `-f` in scripts:** a 404 page gets saved as `install.sh` and executed.
- **`curl … | sh`:** if the connection drops mid-stream, a truncated script runs. Download first, then verify (checksum or signature), then run.
- **`-k` / `--insecure` left in production code:** this disables certificate validation entirely.
- **Quoting:** single quotes stop `$VAR` from expanding. On Windows `cmd`, single quotes don't work; use double quotes and escape inner ones.
- **`-d` silently implies POST** and `application/x-www-form-urlencoded`, and it strips CR/LF from `@file`. Use `--data-binary @file` to send a file exactly as it is.
- **`-X POST` combined with `-L`:** curl keeps POST on every redirect, ignoring the usual 301/302→GET conversion. Let `-d` choose the method instead.
- **Proxies come from environment variables** (`http_proxy`, `https_proxy`, `no_proxy`, `ALL_PROXY`), as the first verbose line shows when one is in use. This is a common hidden cause of slowness or failures; use `--noproxy '*'` to rule it out.
- **Secrets leak:** `-u user:pass` shows up in `ps` output and shell history. Use `-u user` (curl prompts), `--netrc`, `-H @headerfile`, or a config file with tight permissions.
- **`~/.curlrc`** can silently change behaviour; `-q` as the first option ignores it.
- **Windows PowerShell 5.1:** `curl` = `Invoke-WebRequest`. Use `curl.exe`.
- **Permissions:** a normal user needs nothing special. Root is only needed to write to protected paths or bind privileged local ports with `--local-port`.
- **Version-dependent behaviour:** in 8.23.0, `smb://` is gone; `CURL_GLOBAL_WIN32` → `CURL_GLOBAL_WINSOCK`; and `--no-clobber` now writes `report-1.pdf` where it used to write `report.pdf.1` [9].

---

## History and evolution

| When | What happened |
|---|---|
| Late 1996 | Daniel Stenberg was writing an IRC bot for an Amiga channel on EFnet and wanted to fetch currency exchange rates from the web [5]. |
| 11 Nov 1996 | **HttpGet 0.1** released by Rafael Sagula (Brazil; homepage at inf.ufrgs.br). Stenberg fixed bugs, added features and took it over [4][6]. On the very same day, Wget 1.4.0 shipped [3]. |
| 8 Apr 1997 | HttpGet 1.0 with HTTP proxy support [7]. |
| Aug 1997 | FTP download support added; renamed **urlget 2.0** [7]. |
| 14 Aug 1997 | urlget 2.2 builds on Windows and Solaris [7]. |
| Nov 1997 – Mar 1998 | FTP upload (3.1), HTTP POST (3.5), proxy auth (3.12) [7]. |
| **20 Mar 1998** | Upload made "urlget" misleading, so it was renamed **curl 4.0**, keeping the version numbering. About 2,200 lines of code [3][8]. "c URL" = "see URL"; also read as "Client for URLs" [8]. |
| 1998 | SSL support via SSLeay (the precursor of OpenSSL); 20 releases in the first year; the licence moved away from the GPL (MPL, later the MIT-style curl licence) [4]. |
| 1999 | First configure script, cookie support, packaged in Debian [4]. |
| 2000 | **libcurl** split out as a library, the turning point that made curl infrastructure. |
| 2000s | easy API → multi API → `multi_socket` (event-driven, built for scale); TFTP, SCP/SFTP, IMAP/POP3/SMTP and more; pluggable TLS backends (OpenSSL, GnuTLS, NSS, Schannel, Secure Transport, wolfSSL/CyaSSL, mbedTLS, later rustls) [7]. |
| 2010 | Hundreds of millions of installations [8]. |
| 2015 | HTTP/2 via nghttp2. |
| 2018 | `curl.exe` ships with Windows 10 (1803). |
| 2019 | Experimental HTTP/3 (ngtcp2, quiche); HackerOne bug bounty starts. |
| 2023 | **curl 8.0.0** (25th birthday): a version bump without API/ABI breakage; requires a 64-bit integer type. About 155k lines of code; "more than ten billion" installs [8]. |
| 2024–2025 | `--json`, `--variable`, `--follow`, `--out-null`; msh3 HTTP/3 backend dropped; complaints about AI-generated reports grow. |
| Jan 2026 | **8.18.0** (7 Jan): OpenSSL 3.0 becomes the minimum; legacy platforms deprecated [10]. OpenSSL-QUIC backend removed, leaving ngtcp2+nghttp3 or quiche for HTTP/3 [11]. **Bug bounty ends on 31 Jan 2026** because of AI slop reports [12][13]. |
| Mar / Apr 2026 | 8.19.0; **8.20.0**: NTLM disabled by default, SMB opt-in [14]. |
| Jun 2026 | **8.21.0** (24 Jun): 18 security fixes, a record for one release and for a calendar year [15]. |
| Jul 2026 | The security team pauses vulnerability intake from 1 Jul to 3 Aug ("summer of bliss") because report volume doubled and the confirmed rate fell below 5% [16]. |
| Sep 2026 | 8.22.0. |
| **14 Oct 2026** | **8.23.0**: 24 CVEs published together, including **CVE-2026-92392**, an HTTP/2 upload use-after-free rated HIGH (possible RCE, most likely a crash), found by Luna Tong at Anthropic with its OSS Scanner [17][18]. SMB removed [9]. |
| 11 Nov 2026 | Stenberg's "30 years of Internet transfers with curl" essay: about 30 billion installations; options grew from 24 (in 4.0) to 273 [19]. |
| 9 Dec 2026 | Next planned release [2]. |

Numbers at 8.18.0 / 8.20.0: 273 command-line options, 308 `curl_easy_setopt()` options, 100 public libcurl functions, about 3,660 contributors and 1,460 authors [10][14].

---

## How it works internally

```
curl (tool: src/)  ── parses args, config, globbing, output files, progress
   │  uses the public API
   ▼
libcurl (lib/)
 ├─ easy handle  (one transfer: URL + options set by curl_easy_setopt)
 ├─ multi handle (many transfers, one thread, non-blocking state machine)
 │     └─ multi_socket API → plugs into epoll/kqueue/libuv event loops
 ├─ connection pool / cache (reuse TCP+TLS; DNS cache; share interface)
 ├─ protocol handlers  http.c, http2.c (nghttp2), vquic/ (ngtcp2|quiche),
 │                     ftp.c, smtp.c, imap.c, ssh (libssh|libssh2), mqtt.c …
 ├─ connection filters ("cfilters"): socket → happy-eyeballs → proxy →
 │                     TLS (vtls/: OpenSSL, wolfSSL, GnuTLS, mbedTLS,
 │                     Schannel, Apple SecTrust, rustls) → HTTP/2|3
 └─ resolvers: synchronous, threaded, or c-ares
```
- **Easy API:** `curl_easy_init()` → `curl_easy_setopt()` (about 308 options) → `curl_easy_perform()` (blocking) → `curl_easy_cleanup()`.
- **Multi API:** add easy handles to a multi handle and drive them with `curl_multi_perform()` / `curl_multi_poll()`, or with `curl_multi_socket_action()` from your own event loop. One thread can handle thousands of transfers.
- **Callbacks:** `CURLOPT_WRITEFUNCTION` / `READFUNCTION` / `HEADERFUNCTION` / `XFERINFOFUNCTION` move the data. Don't clean up the handle from inside its own callback.
- **Connection reuse:** a later transfer reuses a pooled connection only if the host, port, TLS settings, credentials and so on match. Several 2026 CVEs were about bad reuse matching (auth or STARTTLS state leaking across reuse) [15].
- **Happy eyeballs:** races IPv6 against IPv4 and, with `--http3`, QUIC against TCP, with fallback to h2/h1 if QUIC is not fast enough [11].
- **HTTP/3 needs three parts:** TLS 1.3 for QUIC + a QUIC library + an HTTP/3 library (ngtcp2 + nghttp3, or quiche).
- **The tool is a libcurl user:** the `curl` binary is one big client of the public API. `--libcurl file.c` prints C code for the exact command you ran.

---

## Cross-platform comparison

### How other platforms solve the same problem
- **Windows:** `curl.exe` (the real curl, Schannel TLS) is built in, plus PowerShell `Invoke-WebRequest` / `Invoke-RestMethod` (.NET `HttpClient`), BITS (`Start-BitsTransfer`), and the WinHTTP / WinINet APIs. `certutil -urlcache -f` is abused by attackers as a downloader.
- **macOS / iOS:** the system curl on macOS; apps use `URLSession` (NSURLSession) with Network.framework, which supports HTTP/3. `networkQuality` measures responsiveness.
- **Android:** apps use OkHttp, `HttpURLConnection` or Cronet (Chromium's stack, with QUIC). libcurl appears inside NDK/native apps.
- **Browser / web:** `fetch()` and XHR, with CORS and same-origin enforcement. DevTools offers "Copy as cURL".
- **Languages:** Python `requests` / `httpx`, Go `net/http`, Node `fetch` (undici), Java `HttpClient`, Rust `reqwest` / `hyper`. Many bindings, such as PHP's curl extension and pycurl, wrap libcurl itself.

### Same vs different
| | curl / libcurl | PowerShell IWR | Apple URLSession | Android OkHttp / Cronet | Browser `fetch()` | wget |
|---|---|---|---|---|---|---|
| Form | CLI + C library | cmdlet (.NET HttpClient) | OS framework | Java/Kotlin library | JS API | CLI |
| Protocols | about 25 | HTTP(S), FTP (limited) | HTTP(S), WebSocket | HTTP(S), WebSocket; Cronet adds QUIC | HTTP(S) | HTTP(S), FTP |
| HTTP/3 | yes (build-dependent) | .NET 7+ | yes | Cronet yes | yes | no |
| TLS stack | pluggable | SChannel | Apple TLS | Conscrypt / BoringSSL | browser's | GnuTLS / OpenSSL |
| Scripting output | `-w` variables, raw bytes | .NET objects | n/a | n/a | Promises | logs |
| Recursion / mirroring | no | no | no | no | no | **yes** |
| CORS / same-origin | none | none | none | none | **enforced** | none |

Key difference: browsers enforce origin policies and curl doesn't. That is why "works in curl, fails in the browser" usually means CORS.

---

## Alternatives

| Platform / need | Alternatives |
|---|---|
| Linux/Unix CLI | **wget** (recursive mirroring, simpler), **wget2**, **HTTPie** / **xh** (friendlier output for humans), **aria2** (multi-source / BitTorrent), **wcurl** (curl project's wget-like wrapper), `nc` / `openssl s_client` (raw socket / TLS) |
| Windows | `Invoke-WebRequest` / `Invoke-RestMethod`, BITS, `certutil -urlcache` (abused) |
| macOS | `URLSession`, `networkQuality`, the system curl |
| GUI / API development | Postman, Insomnia, Bruno, Hoppscotch, `.http` files in VS Code / JetBrains |
| Libraries | Go `net/http`, Python `requests` / `httpx`, Node `fetch` / `undici`, Java `HttpClient`, Rust `reqwest` / `hyper` |
| Pentest | Burp Repeater, OWASP ZAP, `ffuf` (fuzzing), ProjectDiscovery `httpx` (probing many hosts) |

---

## Role: Backend / API Developer
**Why it matters:** curl is the universal language of API docs and bug reports.
**Day to day:**
- "Copy as cURL" from DevTools to reproduce a request
- `--json` payloads; `-w '%{http_code}'` assertions
- Testing auth flows (Bearer, Basic, OAuth token exchanges)
- `--trace-ascii` to see the exact bytes of a body

**What experts know:**
- `-d` vs `--data-binary` vs `--data-urlencode` vs `-F`
- `-X` changes only the method word, not curl's behaviour
- `--variable` / `--expand-*` templating (8.3+) and `-K` config files for repeatable calls
- `--libcurl` generates C code
- curl is lenient where browsers are strict, and the other way round (CORS, mixed content)

## Role: DevOps / SRE Engineer
**Why it matters:** health checks, Kubernetes probes, CI steps and Docker `HEALTHCHECK` lines run curl everywhere, including in minimal images.
**Day to day:**
- `-w` timing templates
- `--retry --retry-all-errors --connect-timeout --max-time`
- `--resolve` / `--connect-to` for blue/green and canary checks
- `-f` so pipelines fail correctly

**What experts know:**
- Time values are cumulative
- Set `--connect-timeout` separately from `--max-time`
- Distro curl versions like "8.5.0 security patched" hide backports, so use `curl -V` and the distro advisories
- Track the 8-week release cycle and the 2026 CVE volume (18 fixes in 8.21.0, 24 CVEs in 8.23.0, including HIGH-severity CVE-2026-92392), and rebuild base images promptly

## Role: Network Engineer
**Why it matters:** curl is the fastest layer-7 probe there is; `-v` shows DNS → TCP/QUIC → TLS → ALPN → HTTP in one view.
**Day to day:**
- Path and stack control: `--interface`, `-4` / `-6`, `--local-port`
- HTTP version control: `--http2-prior-knowledge`, `--http3-only`, `--alt-svc`
- Diagnostics and proxies: `--trace-time`, `--haproxy-protocol`, `--dns-servers` (c-ares builds), `--doh-url`

**What experts know:**
- Happy-eyeballs racing (IPv6/IPv4, and QUIC vs TCP with fallback)
- Connection reuse when several URLs are given in one invocation
- SNI vs the `Host` header
- ALPN negotiation, and Alt-Svc upgrades to h3
- Per-phase latency arithmetic from `-w` values

## Role: Penetration Tester (VAPT)
**Why it matters:** curl gives exact control of a request with no browser normalisation, so it is ideal for proofs of concept and one-line evidence in reports.
**Day to day:**
- `--path-as-is` (stops curl from collapsing `../`); `--request-target` (raw request line); `--globoff`
- Header tampering: `-H 'Host: evil'`, `X-Forwarded-For` spoofing; method tampering
- `-x` into Burp with `-k`; `--cert` / `--key` for mTLS
- `gopher://` and `dict://` as SSRF payload carriers; `--http1.0` / `--http0.9` for parser edge cases

**What experts know:**
- curl normalises URLs unless told not to
- Turn every finding into a reproducible `curl` command for the client
- Smuggling and desync tests need raw control, so combine curl with tools that write raw bytes

## Role: Cybersecurity Analyst (Blue team)
**Why it matters:** curl appears in attacker activity (`curl … | sh` droppers, exfiltration via `-T` / `-F`, `curl.exe` as a Windows LOLBin) and in defenders' own tooling. It is also a supply-chain dependency with its own vulnerability stream.
**Day to day:**
- Hunting process creations of `curl` / `curl.exe` with odd parents
- Spotting the default `User-Agent: curl/x.y` in proxy logs
- Fetching threat-intel feeds and IOCs
- Tracking curl advisories in SBOMs

**What experts know:**
- 2026 is an unusual year: a record 18 fixes in 8.21.0 [15], 24 CVEs with 8.23.0 [17]
- CVE-2026-92392 (HTTP/2 upload UAF, HIGH) needs a ~135 KB upload to a server with a valid certificate, so it is realistic but conditional [18]
- Only the latest release gets fixes; distros backport [2]

## Role: Embedded / Systems C Developer
**Why it matters:** libcurl is the de facto HTTP client in C on devices.
**Day to day:**
- `curl_easy_setopt` (about 308 options)
- The multi API for many transfers on one thread
- Write, read and progress callbacks
- `CURLSH` share handles for DNS and connection caches
- Picking a small TLS backend (wolfSSL, mbedTLS)

**What experts know:**
- `./configure --disable-*` / CMake options for tiny builds
- Build minimums (OpenSSL 3.0+ from 8.18.0) [10]
- Reuse handles to keep connections alive
- Never clean up a handle inside its own callback
- Watch deprecations (`CURL_GLOBAL_WIN32` → `CURL_GLOBAL_WINSOCK`, SMB removal) [9]
- The ABI has been stable since 2006 (soname `libcurl.so.4`)

## Role: Linux Sysadmin
**Why it matters:** installers, mirrors, mail alerts, FTP/SFTP and API calls to hypervisors and container engines all go through it.
**Day to day:**
- `-C -` resume, `-z` "only if newer", `--netrc`
- SMTP alerts from cron
- `-T` uploads
- `--unix-socket` for Docker, Podman and other local APIs

**What experts know:**
- Behaviour changes between versions (for example `--no-clobber` naming in 8.23) [9]
- `~/.curlrc` and `-q`
- Proxy environment variables and `--noproxy`
- Distro backports vs upstream versions

## Role: Open-Source Maintainer (non-obvious)
**Why it matters:** curl is the textbook case of a one-person-led project that became critical infrastructure: BDFL governance, no foundation, independent [8][2].
**Lessons:**
- Public, fixed 8-week releases
- A CVE for every security bug, with detailed advisories
- A deprecation policy with lead time (curl.se/dev/deprecate)
- Firm handling of AI-generated reports: the bug bounty ran 2019 to 31 Jan 2026 (reports cite 78–87 confirmed vulnerabilities and $86k to over $100k paid out; sources differ) and ended to remove the incentive for slop [12][13][16]. Intake was paused in July 2026.
- The same year, AI-assisted scanners also found real HIGH-severity bugs (CVE-2026-92392) [18]: the same technology produced the noise and the real finds.

---

## Related topics (where it applies)
1. HTTP/1.1, 2 and 3 (RFC 9110–9114), QUIC (RFC 9000), TLS 1.3 (RFC 8446), ALPN (RFC 7301), URL syntax (RFC 3986), cookies (RFC 6265), HSTS, Alt-Svc
2. REST/API design and testing, webhooks, OAuth 2.0 flows
3. Web application security: OWASP Top 10, SSRF, request smuggling, CORS, open redirects
4. Observability and SRE: synthetic probes, TTFB / latency analysis, health checks
5. Supply-chain security: SBOMs, CVE triage, distro backports
6. Embedded networking and C library design (ABI stability, event loops)
7. Open-source governance and sustainability
8. Certifications and curricula: CompTIA Linux+ / Network+ / Security+, LPIC, RHCSA, CKA / CKAD, OSCP / PNPT / eWPT / BSCP, AWS / GCP associate exams (metadata endpoints and APIs)

---

## Follow-up Q&A

### Q: Which roles care about curl? (role pick)
Eight were suggested and all were selected: Backend/API Developer, DevOps/SRE, Network Engineer, Penetration Tester (VAPT), Blue-team Analyst, Embedded/C Developer, Linux Sysadmin, and Open-Source Maintainer (the non-obvious one, chosen because curl is a case study in governance, release discipline and AI-report handling). See the role sections above.

No other follow-up questions were asked before saving.

---

## Sources

[1] curl project, "curl," official website. [Online]. Available: https://curl.se/

[2] Safeguard, "curl release history: from httpget to curl 8, protocols, TLS backends and the security process," Oct. 2026. [Online]. Available: https://safeguard.sh/resources/blog/curl-release-history-from-httpget-to-curl-8-protocols-tls-backends-and-the-security-process (accessed Nov. 19, 2026).

[3] D. Stenberg, "curl's birthday / changes from before it was curl," daniel.haxx.se. [Online]. Available: https://daniel.haxx.se/blog/2023/08/15/ and https://daniel.haxx.se/blog/?p=15831 (accessed Nov. 19, 2026).

[4] D. Stenberg, blog posts tagged "birthday," daniel.haxx.se. [Online]. Available: https://daniel.haxx.se/blog/tag/birthday/ (accessed Nov. 19, 2026).

[5] curl project, "History of curl." [Online]. Available: https://curl.se/docs/history.html (accessed Nov. 19, 2026).

[6] D. Stenberg, "Age is just a number or two," Jan. 3, 2021. [Online]. Available: https://daniel.haxx.se/blog/2021/01/03/ (accessed Nov. 19, 2026).

[7] curl project, docs/HISTORY.md (Debian source, curl 8.19.0). [Online]. Available: https://sources.debian.org/src/curl/8.19.0-3/docs/HISTORY.md (accessed Nov. 19, 2026).

[8] T. Claburn, "Curl, the URL fetcher that can, marks 25 years of transfers," The Register, Mar. 21, 2023; D. Stenberg, "curl is 23 years old today," Mar. 20, 2021. [Online]. Available: https://www.theregister.com/2023/03/21/curl_project_25/ ; https://daniel.haxx.se/blog/2021/03/20/

[9] T. A. Anderson, "curl 8.23.0 removes SMB," Sesame Disk, Nov. 5, 2026. [Online]. Available: https://sesamedisk.com/curl-8-23-0-removes-smb/ (accessed Nov. 19, 2026).

[10] x-cmd, "curl 8.18.0 Released: OpenSSL 3.0 Now Minimum Requirement," Jan. 2026; D. Stenberg, "curl 8.18.0," Jan. 7, 2026; curl-announce, "curl and libcurl 8.18.0." [Online]. Available: https://www.x-cmd.com/blog/260111 ; https://daniel.haxx.se/blog/2026/01/07/curl-8-18-0/ ; https://curl.se/mail/archive-2026-01/0000.html

[11] D. Stenberg, "More HTTP/3 focus, one backend less," Jan. 17, 2026; curl docs/HTTP3.md. [Online]. Available: https://daniel.haxx.se/blog/2026/01/17/more-http-3-focus-one-backend-less/ ; https://sources.debian.org/src/curl/8.19.0-3/docs/HTTP3.md

[12] D. Stenberg, "The end of the curl bug bounty," Jan. 26, 2026. [Online]. Available: https://daniel.haxx.se/blog/2026/01/26/the-end-of-the-curl-bug-bounty/

[13] The Register, "Curl shutters bug bounty program to remove incentive for submitting AI slop," Jan. 21, 2026; Neowin; Bugcrowd; TechRadar. [Online]. Available: https://www.theregister.com/2026/01/21/curl_ends_bug_bounty/ ; https://www.neowin.net/amp/beloved-tool-curl-is-shutting-down-its-bug-bounty-over-ai-slop-reports/ ; https://www.bugcrowd.com/?p=19187

[14] D. Stenberg, "[RELEASE] curl 8.20.0," curl-library mailing list, Apr. 29, 2026. [Online]. Available: https://curl.se/mail/lib-2026-04/0029.html

[15] GBHackers, "Curl 8.21.0 Released With 18 Security Fixes," 2026. [Online]. Available: https://gbhackers.com/?p=190372

[16] Pinggy, "curl's Summer of Bliss: Why It Stopped Taking Bug Reports in July 2026," Jul. 3, 2026. [Online]. Available: https://pinggy.io/blog/curl_ai_slop_summer_of_bliss/

[17] curl security team, "[SECURITY ADVISORIES] curl 8.23.0," oss-security, Oct. 14, 2026. [Online]. Available: https://openwall.com/lists/oss-security/2026/10/14/3

[18] D. Stenberg, "A UAF turned RCE," Oct. 14, 2026. [Online]. Available: https://daniel.haxx.se/blog/2026/10/14/a-uaf-turned-rce/

[19] tproger, "How curl grew from 100 lines of C to 30 billion installs in 30 years" (summary of D. Stenberg, "30 years of Internet transfers with curl," Nov. 11, 2026). [Online]. Available: https://tproger.ru/articles/kak-curl-za-30-let-vyros-iz-100-strok-na-c-do-30-mlrd-ustanovok

Notes on certainty:
- The command and option behaviour comes from curl's documentation and general knowledge. Version tags for `--json` (7.82), `--variable` (8.3) and `--follow` / `--out-null` (8.16) were partly verified from release notes.
- The `curl -V`, `-v` and `-w` samples are real output captured on Ubuntu 24.04 behind an egress proxy. The `-I` sample and the realistic-task outputs are illustrative.
- From general knowledge and not re-verified in this session: Windows 10 1803 bundling, the HTTP/2 (2015) and libcurl (2000) dates, Stenberg's employers, and the PowerShell alias details.
- The bug-bounty totals differ between sources (78 vs 87 vulnerabilities; $86k vs over $100k).
