---
tool: whatweb
date: 2026-11-24
domains: [Cybersecurity, Web Application Security, Reconnaissance, OSINT, Web Development, IT Operations]
roles: [Penetration Tester / Red Teamer, Bug Bounty Hunter, Cybersecurity Analyst (SOC / Vulnerability Management), Web Application Security Engineer (AppSec), OSINT / Threat Intelligence Analyst, Network Engineer, Web Developer / DevOps Engineer, Security Researcher / Plugin Author]
tags: [whatweb, fingerprinting, recon, enumeration, web, cms, wordpress, banner-grabbing, ruby, kali, vapt, osint, wappalyzer, httpx, nuclei]
---

# whatweb

## Summary

**WhatWeb** is a Ruby command-line web scanner that answers "what is this website running, and which version?" It recognises content management systems, blogging platforms, analytics packages, JavaScript libraries, web servers and embedded devices, and extracts version numbers, email addresses, account IDs, framework modules and SQL errors [1]. It has about **1835 plugins** (counted in the 0.6.4 source tree), each a Ruby file of match rules plus optional custom code.

- **Problem it solves:** it turns a URL, host, IP range or list into a technology stack with versions, starting from a single HTTP request, so you can map versions to CVEs, inventory assets or check what your own site leaks.
- **Authors:** Andrew Horton (`urbanadventurer`) and Brendan Coles (`bcoles`) [1].
- **First release:** v0.3 at Kiwicon III, Wellington, New Zealand, 2 November 2009 [1].
- **Latest:** v0.6.4, 3 April 2026, a performance overhaul [1][6].
- **License:** GPLv2 [1].
- **Stack position:** port discovery (nmap, masscan, naabu) → HTTP probing (httpx) → **fingerprinting (WhatWeb)** → specialist scanners (wpscan, droopescan, nuclei, nikto) → manual testing (Burp, ZAP).

All sample outputs below are **real runs** of WhatWeb 0.6.4 (from a git clone, Ruby 3.3.6). The target was a local test page served by `python3 -m http.server`, built to look like a WordPress site with jQuery 3.7.1, a GA4 tag, a contact email `admin@acme.example` and a password field:

```html
<html><head><title>Acme Intranet</title>
<meta name="generator" content="WordPress 6.4.2">
<link rel='stylesheet' href='/wp-content/themes/twentytwentyfour/style.css'>
<script src="/wp-includes/js/jquery/jquery.min.js?ver=3.7.1"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123XYZ"></script>
</head><body>Contact: admin@acme.example<form><input type="password" name="pwd"></form></body></html>
```

---

## Install and availability

| Platform | How |
|---|---|
| Kali / Parrot | Preinstalled, or `sudo apt install whatweb` |
| Debian / Ubuntu | `sudo apt install whatweb`. Distro versions lag: Debian accepted 0.6.2-1 into unstable on 2025-08-25, and it reached testing on 2025-08-31 [7] |
| Gentoo | ebuild targets ruby32/ruby33, keywords amd64, ~arm64, x86 [8] |
| macOS | `brew install whatweb` (Homebrew formula) |
| From source (any OS with Ruby) | `git clone https://github.com/urbanadventurer/WhatWeb && cd WhatWeb && bundle install && ./whatweb` (or `make install`) |
| Windows | No native package. Use WSL, Docker or Ruby from source |
| Android | Should run under Termux, which has Ruby *(inferred, not tested)* |

- **Required gems:** `ipaddr`, `addressable`, `json`. `lib/gems.rb` checks for them, and if any is missing WhatWeb refuses to start with: "WhatWeb is not installed and is missing dependencies. The following gems are missing: - addressable … To install run … 'bundle install'". (`addressable` also needs `public_suffix`.)
- **Optional:** `bundle install --with mongo` (MongoDB logging), `--with rchardet` (character set detection, which is CPU-heavy), `ruby-prof` for profiling. Older Bundler versions use the `GEMFILE_GROUPS` environment variable instead [1].
- **Lab note:** in a sandbox that couldn't reach rubygems.org, I installed the gems by cloning `sporkmonger/addressable` and `weppos/publicsuffix-ruby` from GitHub, then running `gem build` and `gem install --local` on each.

---

## Usage and commands (with real output)

### 1. Basic scan (aggression 1, a single request)

```
$ whatweb http://127.0.0.1:8080/
http://127.0.0.1:8080/ [200 OK] Country[RESERVED][ZZ], Email[admin@acme.exam],
HTTPServer[SimpleHTTP/0.6 Python/3.13.18], IP[127.0.0.1], JQuery[3.7.1],
MetaGenerator[WordPress 6.4.2], PasswordField[pwd], Python[3.13.18], Script,
Title[Acme Intranet], WordPress[6.4.2]
```

### 2. Verbose (`-v`): see the evidence behind each match

```
WhatWeb report for http://127.0.0.1:8080/
Status    : 200 OK
Title     : Acme Intranet
IP        : 127.0.0.1
Country   : RESERVED, ZZ

Summary   : Email[admin@acme.exam], HTTPServer[SimpleHTTP/0.6 Python/3.13.18], JQuery[3.7.1], MetaGenerator[WordPress 6.4.2], PasswordField[pwd], Python[3.13.18], Script, WordPress[6.4.2]

Detected Plugins:
[ Email ]
	Extract email addresses. ... This uses the simplified email regular
	expression from http://www.regular-expressions.info/email.html ...
	String       : admin@acme.exam

[ HTTPServer ]
	HTTP server header string. This plugin also attempts to
	identify the operating system from the server header.
	String       : SimpleHTTP/0.6 Python/3.13.18 (from server string)

[ JQuery ]
	Version      : 3.7.1
	Website     : http://jquery.com/

[ MetaGenerator ]
	String       : WordPress 6.4.2

[ PasswordField ]
	String       : pwd (from field name)

[ Python ]
	Version      : 3.13.18 (from # Server # Version Detection)

[ WordPress ]
	WordPress is an opensource blogging system commonly used as a CMS.
	Version      : 6.4.2
	Aggressive function available (check plugin file or details).
	Google Dorks: (1)
	Website     : http://www.wordpress.org/

HTTP Headers:
	HTTP/1.0 200 OK
	Server: SimpleHTTP/0.6 Python/3.13.18
	Date: Tue, 17 Nov 2026 11:58:26 GMT
	Content-type: text/html
	Content-Length: 427
```

Use verbose output in reports: it shows where each value came from and dumps the raw response headers.

### 3. Aggressive version detection on one plugin

```
$ whatweb -a 3 -p wordpress http://127.0.0.1:8080/
http://127.0.0.1:8080/ [200 OK] WordPress[6.4.2]
```

The README recommends pairing `-a 3` with `-p` (one plugin) to limit requests [1].

### 4. Ranges, lists and quiet mode

```
whatweb --no-errors 192.168.1.0/24          # local network, hide connection errors
whatweb -i targets.txt                      # one target per line (file or stdin)
whatweb --url-prefix https:// -i hosts.txt  # force HTTPS
```

Targets can be URLs, hostnames, IPs, files, or IP ranges in CIDR or dash format, read from a file or stdin [1].

Real run with a dead target in the list:
```
$ whatweb -i /tmp/t.txt --log-json=/tmp/scan.json
ERROR Opening: http://127.0.0.1:9/ - Connection refused - connect(2) for "127.0.0.1" port 9
http://127.0.0.1:8080/ [200 OK] Country[RESERVED][ZZ], Email[admin@acme.exam], ...
$ echo $?
0
```

### 5. Machine-readable logging

```
$ whatweb -q --log-json=- http://127.0.0.1:8080/
[
    {
        "target": "http://127.0.0.1:8080/",
        "http_status": 200,
        "request_config": { "headers": { "User-Agent": "WhatWeb/0.6.4" } },
        "plugins": {
            "Country":     { "string": ["RESERVED"], "module": ["ZZ"] },
            "Email":       { "string": ["admin@acme.exam"] },
            "HTTPServer":  { "string": ["SimpleHTTP/0.6 Python/3.13.18"] },
            "IP":          { "string": ["127.0.0.1"] },
            "JQuery":      { "version": ["3.7.1"] },
            ...
        }
    }
]
```

Formats: brief (greppable one-liner), verbose, XML (with XSL stylesheet), JSON, JSON verbose, MagicTree XML, Ruby object, MongoDB, ElasticSearch, and SQL (INSERT statements plus table creation), plus an error log. Several logs can be written at once [1]. The logger implementations are in `lib/logging/` (`brief.rb`, `verbose.rb`, `xml.rb`, `json.rb`, `jsonverbose.rb`, `magictreexml.rb`, `object.rb`, `sql.rb`, `mongodb.rb`, `elasticsearch.rb`, `errors.rb`).

### 6. Plugin discovery

```
$ whatweb -l | head
WhatWeb Plugin List
Plugin                        Website
--------------------------------------------------------------------------------
1&1 Hosting                   https://www.1and1.com/
1024-CMS                      http://www.1024cms.org/
360-Web-Manager               http://www.360webmanager.com
3COM-NBX                      http://inpath.com/products/3com-nbx.html
...
For complete plugin descriptions use : whatweb --info-plugins <SEARCH>

$ whatweb --info-plugins=jquery
Plugin:         Drupal
Description:    Drupal is an opensource CMS written in PHP.
Authors:        Andrew Horton, Brendan Coles <bcoles@gmail.com>, Bhavin Senjaliya, Gregory Boddin
Version:        0.5
Features:       [Yes]  Pattern Matching (9)
                [No]   Version detection from pattern matching
                [No]   Function for passive matches
                [Yes]  Function for aggressive matches
                [Yes]  Google Dorks (1)
Google Dorks:
[1] inurl:/user/register "Powered by Drupal"
```

`--info-plugins` searches plugin **content**, not only names, which is why a search for "jquery" returned Drupal. `--dorks <plugin>` lists a plugin's Google dorks.

### 7. Grep the response for your own string or regex

```
$ whatweb --grep "Acme" http://127.0.0.1:8080/
http://127.0.0.1:8080/ [200 OK] ..., Grep, HTTPServer[...], ...
```

A `Grep` entry in the output means the string matched.

### 8. Stealth and OPSEC

```
whatweb -U "Mozilla/5.0 (X11; Linux x86_64)" --proxy 127.0.0.1:8080 --wait=2 -t 1 target
```

- `-U`: custom User-Agent (the default announces `WhatWeb/0.6.4`)
- `--proxy host:port` (default port 8080), `--proxy-user`: route through Burp, ZAP or Tor
- `--wait=SECONDS` between connections, `-t` threads (default 25)
- `--open-timeout` (default 15 s), `--read-timeout` (default 30 s) [1]
- `--follow-redirect=never|http-only|meta-only|same-site|always` (default `always`), `--max-redirects` (default 10) [1]
- Auth: `-u user:pass` (basic auth), `--cookie`, `--cookie-jar`, `--no-cookies` (added in 0.6.3) [1][5]
- `.onion` targets through an HTTP proxy are supported since 0.6.2 [4]

### 9. Target modification (path sweeps)

```
whatweb -i sites.txt --url-suffix /crossdomain.xml -p crossdomain_xml
```

Options: `--url-prefix`, `--url-suffix`, `--url-pattern` (insert targets into a URL pattern) [1].

### 10. Performance tuning (0.6.4)

`--output-sync`, `--output-buffer-size` and the `WHATWEB_PROFILE` environment variable [6]. Output buffering is tuned automatically from the thread count [1].

### Option reference (summary of `whatweb --help` categories)

| Category | Key options |
|---|---|
| Target selection | `<targets>`, `-i/--input-file` |
| Target modification | `--url-prefix`, `--url-suffix`, `--url-pattern` |
| Aggression | `-a 1/3/4` |
| HTTP | `-U`, `--header`, `--follow-redirect`, `--max-redirects` |
| Authentication | `-u`, `--cookie`, `--cookie-jar`, `--no-cookies` |
| Proxy | `--proxy`, `--proxy-user` |
| Plugins | `-l`, `-I/--info-plugins`, `--search-plugins`, `-p/--plugins` (select/exclude with `+`/`-`), `-g/--grep`, `--custom-plugin`, `--dorks` |
| Output | `-v` (twice for debug), `--color`, `-q`, `--no-errors` |
| Logging | `--log-brief/verbose/xml/json/json-verbose/magictree/object/mongo-*/elastic-*/sql/sql-create/errors` |
| Performance | `-t`, `--wait`, `--open-timeout`, `--read-timeout`, `--output-sync`, `--output-buffer-size` |
| Misc | `-h`, `--help`, `--debug`, `--version` |

---

## Output and fields explained

Brief line: `URL [status] Plugin[value][module], Plugin, ...`

| Element | Meaning | Where it comes from | When it changes |
|---|---|---|---|
| `http://127.0.0.1:8080/` | Final URL scanned | Input, after redirects (redirects are followed by default) | Redirect policy, prefix/suffix options |
| `[200 OK]` | HTTP status of that response | Status line | Server state; auth; WAF blocks (403/406/429) |
| `Plugin[x]` | A plugin matched; `x` is the extracted string or version | Match rules in `plugins/<name>.rb` | Site content, aggression level |
| `Plugin[x][y]` | Second bracket = "module", e.g. `Country[RESERVED][ZZ]` = name + ISO code | Plugin's `:module` capture | — |
| `Plugin` (no bracket) | Present, nothing extracted (e.g. `Script`) | Text or regex match only | — |
| `Country[...]` | GeoIP of the target's IP | **Local** database `plugins/IpToCountry.csv` (software77 IP2Country, about 15 MB) compiled into `plugins/country-ips.dat` (about 650 KB). Updating instructions are in the plugin comments | Only when you refresh the CSV; `RESERVED/ZZ` = private or loopback IP |
| `IP[...]` | Resolved address | DNS lookup | DNS changes, CDNs |
| `HTTPServer[...]` | `Server:` header | Response headers | Admin spoofing or removal |
| `Python[3.13.18]` | Inferred from the `Server:` header, not the page | One header can feed several plugins ("from # Server # Version Detection") | — |
| `MetaGenerator[...]` | `<meta name="generator">` value | HTML body | CMS settings and hardening plugins remove it |
| `WordPress[6.4.2]` | CMS and version | Many signals (see How it works) | Aggression level adds `/readme.html`, favicon and login-page checks |
| `PasswordField[pwd]` | A password input exists (its name) | HTML forms | — |
| `Email[...]` | Addresses found in the page | Regex (see Gotchas: TLD truncation) | — |
| `Grep` | Your `--grep` pattern matched | Raw response | — |
| `Title[...]` | `<title>` | HTML | — |

JSON fields: `target`, `http_status`, `request_config.headers` (shows the User-Agent sent), and `plugins.<Name>.{string, version, module, account, ...}`. Every value is an **array**, so use `[0]` in jq.

---

## One realistic task, start to finish: external recon to a prioritised CVE list

```bash
# 1. Live web hosts (from your port scan / httpx output)
cat live_urls.txt

# 2. Fingerprint passively, at scale, to JSON
whatweb -i live_urls.txt -a 1 -t 20 --no-errors -q --log-json=scan.json

# 3. Pull out every WordPress site and its version
jq -r '.[] | select(.plugins.WordPress) |
  "\(.target) \(.plugins.WordPress.version[0] // "unknown")"' scan.json
#   → http://127.0.0.1:8080/ 6.4.2          (real output from the lab run)

# 4. For "unknown" versions only, escalate on that single plugin (only in scope!)
whatweb -a 3 -p wordpress https://site-with-unknown-version/

# 5. Map versions to CVEs, then hand off to the specialist: wpscan / droopescan / nuclei
```

Who gets what from this: the pentester and bug bounty hunter get targets, the SOC analyst gets an asset inventory, and the AppSec engineer or DevOps engineer finds out what is leaking.

---

## Common mistakes and gotchas

1. **Truncated emails (verified in source).** `plugins/email.rb:35` uses `/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}/i`. The TLD is capped at 4 letters, so `admin@acme.example` was reported as `admin@acme.exam`. `.online`, `.example` and `.solutions` are all cut off.
2. **GA4 is missed (verified).** The test page had `gtag/js?id=G-ABC123XYZ`, and no Google-Analytics hit appeared. The plugin's account regex, `id=(\w{2}-\w{1,}-\d{1,})`, expects old `UA-12345678-1` style IDs (and the `.js` regexp needs a non-word character before `gtag.js`). A missing GA result is not proof that the site has no analytics.
3. **Exit code 0 on failure (verified).** A connection-refused target still returned `rc=0`. In pipelines, check `--log-errors`, not the exit status.
4. **`-q` hides the brief output.** Use it only with a log file or `--log-json=-`.
5. **Absence ≠ not present.** Level 1 sees one page's headers and HTML. WhatWeb does **not execute JavaScript**, so SPAs and JS-injected libraries are often missed.
6. **Headers can lie.** Admins spoof or strip `Server:`. The old README example showed reddit returning `HTTPServer['; DROP TABLE servertypes; --]` [9].
7. **CDNs and WAFs** (CloudFlare plugin) mean you see the **edge**, not the origin.
8. **Permissions and legality.** No root needed (plain HTTP over TCP). But levels 3–4 are active probing: the project warns that level 3 aggressive plugins "will guess more URLs and perform actions that are potentially unsuitable without permission" [10]. Get written authorisation.
9. **Large ranges.** For large IP ranges, run a port scanner first to find hosts with port 80 open [1].
10. **Character set detection** (rchardet) significantly increases CPU use [1].
11. **The default User-Agent** `WhatWeb/0.6.x` is flagged by WAFs and SOCs. Use `-U`.
12. **Help text lag.** The 0.6.4 help text still shows a default User-Agent of `WhatWeb/0.6.3` [1], while the actual request sent `WhatWeb/0.6.4` (seen in the JSON log).
13. **`--info-plugins` search** matches plugin content, not just names, so expect surprising results.
14. **The Country database is bundled and static.** Refresh it, or don't trust it for recently reassigned IP space.

---

## History and evolution

### Origin

- **Who:** Andrew Horton (`urbanadventurer`), a New Zealand security consultant. Early READMEs credit "Andrew Horton aka urbanadventurer from Security-Assessment.com" [11]. The project is published under his **MorningStar Security** brand (homepage morningstarsecurity.com/research/whatweb). **Brendan Coles** (`bcoles`) is co-developer and wrote a large share of the plugins [1].
- **When and where:** v0.3 released at **Kiwicon III**, Wellington, **2 November 2009** [1].
- **Original problem:** a research project to fingerprint an entire country. The Kiwicon talk "Next generation web scanning – New Zealand: A case study" set the goal "to scan all of New Zealand's web-space to see what's there", covering targets (DNS zone transfers, Bing IP-to-vhost lookups, Google), scanning and analysis [12].
- **Released alongside it:** WhatWeb, bing-ip2hosts, gggooglescan and basedomainname were published during that first presentation. At launch WhatWeb was "written in Ruby for Linux" with a "flexible plugin architecture with over 70 plugins", and its passive plugins used headers, cookies, the HTML body and the URL [13]. Horton also published geoipgen, "the first published use of a geographic ip database in reverse", translating a country into IP ranges [13].

### Release timeline

| Version | Date | Notes |
|---|---|---|
| 0.3 | 2 Nov 2009 | Kiwicon III; about 70 plugins [1][13] |
| 0.4 – 0.4.5 | Mar – Aug 2010 | Rapid iteration [1] |
| 0.4.6 | 25 Mar 2011 | "Now with over 900 plugins!" [14] |
| 0.4.7 | 5 Apr 2011 | [1] |
| 0.4.8-dev | 2012 – 2017 | Continuous release [1]; this is the version many old distros carried for years |
| 0.4.9 | 23 Nov 2017 | [1] |
| 0.5.0 – 0.5.5 | Jun 2019 – Jan 2021 | Plugin format v0.5 (migration script in `plugin-development/`) [1] |
| 0.6.1 | Aug 2025 | Improved SSL/TLS cipher support; dropped Ruby 2.0; JSON logging UTF-8 fix; plugin updates (WordPress, Drupal, TYPO3, Shopify, CloudFlare …) [3] |
| 0.6.2 | 25 Aug 2025 | `.onion` scanning through an HTTP proxy (bypasses DNS); `set` gem fix [4] |
| 0.6.3 | 18 Oct 2025 | Cookies retained between redirects; `--no-cookies` [5] |
| 0.6.4 | 3 Apr 2026 | Performance overhaul ("output is no longer the bottleneck"); `--output-sync`, `--output-buffer-size`, `WHATWEB_PROFILE`. The release notes thank "Claude from Anthropic" for the bug fixes [6] |

Repository stats (mid-2026 snapshots): about 6.6k–7k GitHub stars, about 1k forks [2][10].

### Concept history: from banner grabbing to technology fingerprinting

1. **Banner grabbing (1990s).** HTTP/1.0 (RFC 1945, 1996) introduced the `Server:` header, and recon simply read it. RFC 2616 and now RFC 9110 §10.2.4 warn that detailed Server values make known flaws easier to target. That warning is both the reason WhatWeb works and the reason hardening guides tell you to strip the header.
2. **Behavioural fingerprinting (early 2000s).** Tools like httprint identified servers by **how** they respond to odd or malformed requests, not by what they claim, following the same idea as Nmap OS/version detection and p0f.
3. **Content fingerprinting (2009).** WhatWeb and Wappalyzer appeared the same year. Both moved from "which server?" to "which **application stack**?", using `<meta generator>`, cookie names, path patterns (`/wp-content/`), JS library filenames, favicon and file hashes, and HTML tag structure.
4. **Today.** Favicon mmh3 hashing (Shodan `http.favicon.hash`), TLS fingerprinting (JARM, JA4), template engines (Nuclei), and shared JSON fingerprint databases in Wappalyzer format. Wappalyzer itself went closed source in 2023, leaving open forks: enthec/webappanalyzer [15] and the HTTP Archive fork [16].

---

## How it works internally

(From reading `lib/plugins.rb`, `lib/gems.rb` and `plugins/*.rb` in the 0.6.4 source.)

```
target ──► Target.open (1 HTTP request, follow redirects, cookies)
             │   body, raw headers, status, uri, md5sum, tag_pattern
             ▼
   for each of ~1835 plugins:
     matches[] ──► make_matches(target, match)      (passive, level 1)
     passive {}  ─► custom Ruby on @body/@headers/@base_uri
     if aggression ≥ 3 and plugin matched (or level 4: always):
        aggressive {} + every match with :url ──► fetch extra URLs, re-run matches
             ▼
   results (certainty, version, string, module, account...) ──► loggers (brief/json/sql/...)
```

### Plugin DSL (example: `plugins/wordpress.rb`)

```ruby
Plugin.define do
name "WordPress"
authors [ "Andrew Horton", "@SlivTaMere", "@anoroozian", "@ajgon", "@juananpe" ]
version "0.9"
description "WordPress is an opensource blogging system commonly used as a CMS."
website "http://www.wordpress.org/"
dorks [ '"is proudly powered by WordPress"' ]
matches [
  {:text=>'<meta name="generator" content="WordPress.com" />'},
  {:text=>"<link rel='https://api.w.org/'", :name=>'REST API link'},
  {:regexp=>/"[^"]+\/wp-content\/[^"]+"/, :name=>"wp-content", :certainty=>75 },
  {:version=>/<meta name="generator" content="WordPress ([0-9\.]+)"/ },
  {:url=>"/wp-cron.php"},
  {:url=>"/wp-login.php", :text=>'action=lostpassword'},
  {:url=>"/wp-login.php", :tagpattern=>"!doctype,html,head,title,/title,..."},
  {:url=>"favicon.ico", :md5=>'f420dc2c7d90d7873a90d82cd7fde315'},
  {:url=>"/readme.html", :version=>/<h1.*WordPress.*Version ([0-9a-z\.]+).*<\/h1>/m}
]
passive do
  # detect relative /wp-content/ links on the same host, ignoring links to other sites
end
end
```

### Match types (from `make_matches`)

| Key | What it checks |
|---|---|
| `:text` | Literal string in the search context |
| `:regexp` | Regex; `:offset` picks a capture group |
| `:version`, `:string`, `:account`, `:module`, `:model`, `:firmware`, `:os`, `:filepath` | Regex captures stored in those result fields |
| `:md5` | MD5 of the whole response (e.g. favicon) |
| `:tagpattern` | Comma-separated HTML tag skeleton of the page |
| `:ghdb` | Google-dork syntax (`inurl:`, `intitle:`, …) evaluated locally |
| `:status` | HTTP status code |
| `:url` | Only matches when the target URL equals or ends with this path. In aggressive mode the engine **fetches** it (`URI.join(base, url)`) |
| `:certainty` | Confidence; **defaults to 100** when unset (`lib/plugins.rb`, around line 290) |
| `:name` | Label shown in verbose output |

### Search context (`:search`)

The default is the response **body**. Other values: `all` (raw response), `headers` (raw headers), `headers[x-powered-by]` (one header), `uri.path`, `uri.query`, `uri.extension`.

### Aggression levels

| Level | Behaviour [1][10] |
|---|---|
| 1 Stealthy (default) | One HTTP request per target, follows redirects |
| 2 | Unused |
| 3 Aggressive | A handful of requests; aggressive plugin tests run **only for plugins that matched at level 1** |
| 4 Heavy | Many requests; all aggressive tests from all plugins run against all URLs |

### Other internals

- **Dependency gate:** `lib/gems.rb` checks `ipaddr`, `addressable` and `json` with `Gem::Specification.find_by_name` and exits with install instructions if any is missing.
- **Plugin-development helpers:** `plugin-development/` contains `get-pattern`, `find-common-stuff`, `migrate-plugins-to-v0.5.rb`, `plugin-tutorials.txt`, and Alexa top-10/100/1000 test lists.

---

## Cross-platform comparison: how other platforms solve the same problem

| Platform | Native approach | Same as WhatWeb | Different |
|---|---|---|---|
| Linux | WhatWeb, httpx `-td`, nuclei, nmap NSE (CLI) | — | Reference platform |
| Windows | No built-in tool. WSL/Docker WhatWeb, Burp/ZAP, PowerShell `Invoke-WebRequest` + manual header reading | Same HTTP evidence | Needs a Ruby/WSL layer |
| macOS | Homebrew WhatWeb, browser extensions | Identical CLI | — |
| Browser (any OS) | Wappalyzer / BuiltWith extensions | Pattern matching on headers and HTML | Also sees the **rendered DOM and JS globals** (e.g. `window.React`); passive to the target because you were visiting anyway |
| Web / cloud | BuiltWith, Netcraft Site Report, Shodan, Censys, URLScan.io | Same fingerprint logic | Pre-collected data: zero contact with the target, but can be stale |
| Android | Few practical options. WhatWeb under Termux *(inferred)* | Same CLI | Clumsy at scale |
| iOS | Nothing practical natively. Use web services | — | — |
| Intercepting proxies | Burp passive scan / BApps; ZAP Technology Detection add-on | Header and body patterns | Continuous, evidence-linked, no extra requests. ZAP's add-on doesn't match on DOM properties and lets you see the evidence [17] |

---

## Alternatives

| Tool | Type | Notes |
|---|---|---|
| **Wappalyzer** | Browser extension / API | The big one. Went closed source in 2023; the HTTP Archive fork of the last open version is used for its monthly crawl [16] |
| **enthec/webappanalyzer** | Fingerprint DB | A continuation of Wappalyzer, which went private in August 2023 [15] |
| **httpx `-td` / wappalyzergo** | Go CLI/library | Wappalyzer-format fingerprints. Fastest for huge lists; less depth than WhatWeb's aggressive mode |
| **webanalyze** | Go CLI | Wappalyzer fingerprints, very fast |
| **Nuclei** (tech-detect templates) | Template engine | YAML templates, big community, also does vulnerability checks |
| **Nmap** `-sV` + `http-generator`, `http-headers` NSE | Network scanner | Handy when you're already in nmap |
| **Nikto** | Web vulnerability scanner | Noisy; finds misconfigurations as well as versions |
| **wpscan / droopescan / CMSeeK / joomscan** | CMS-specific | Go much deeper once WhatWeb has named the CMS |
| **OWASP ZAP Technology Detection** | Proxy add-on | Evidence per detection [17] |
| **Burp Suite** | Proxy | Passive detection while browsing |
| **BuiltWith, Netcraft** | Web services | No packets from you; historical data |
| **Shodan, Censys** | Internet-scan search engines | Fully passive to the target (`http.component:`, favicon hash) |

### When to choose which

- **WhatWeb:** deepest open plugin set, aggression control, many log formats.
- **httpx `-td`:** first sweep over 10k+ hosts.
- **Nuclei:** when you want detection **and** vulnerability checks.
- **Browser extension:** when you're browsing the target anyway and need JS-rendered detection.
- **Shodan/Censys/BuiltWith:** when zero contact with the target is required.

---

## Role: Penetration Tester / Red Teamer

**Why it matters:** it's the first-hour recon step that turns a list of IPs into stacks and versions (e.g. "WordPress 6.4.2, jQuery 3.7.1, PHP 7.4 on Apache 2.4.41"), which gives you a CVE shortlist.

**Day to day:** run WhatWeb after the port scan, then pick specialist tools (wpscan, droopescan, nuclei) and look up exploits.

**What an expert knows that a beginner doesn't:** always start at `-a 1`, then escalate with `-a 3 -p <one plugin>` only where the version is unknown. Change `-U`, because the default User-Agent is a giveaway. Treat versions taken from `Server:` as hints, not facts. Run it through Burp (`--proxy`) so every request is logged as evidence for the report. Use `-v` output as report evidence.

## Role: Bug Bounty Hunter

**Why it matters:** it fingerprints large scope lists quickly to find outdated or interesting stacks.

**Day to day:** feed it thousands of subdomains via `-i` and `--log-json`, then use jq to find outliers: old Struts, exposed Jenkins, forgotten staging CMSs.

**Expert knowledge:** for very large scopes, httpx `-td` is faster as a first sweep. WhatWeb earns its place on the interesting subset, with aggressive plugins and `--grep` for your own markers. Respect programme rate limits with `-t` and `--wait`. Read each programme's rules on automated scanning before using `-a 3/4`.

## Role: Cybersecurity Analyst (SOC / Vulnerability Management)

**Why it matters:** two uses. First, inventory of your **own** estate. Second, detecting **others'** scans.

**Day to day:** schedule WhatWeb on internal ranges with `--log-elastic-*` or `--log-sql` and alert when a version appears below your baseline. On the detection side, watch for `WhatWeb/0.6.x` in User-Agent logs, and for one IP making bursts of requests to `/wp-login.php`, `/readme.html`, `/wp-cron.php` or `favicon.ico`.

**Expert knowledge:** level-1 scans with a spoofed User-Agent are almost invisible, because they look like a single page view. What stands out is level-3/4 probing of fixed paths. This maps to MITRE ATT&CK **T1595** (Active Scanning) and **T1592.002** (Gather Victim Host Information: Software).

## Role: Web Application Security Engineer (AppSec)

**Why it matters:** it checks what your apps leak, and confirms that hardening actually works.

**Day to day:** run it as a regression check. After stripping `Server`/`X-Powered-By`, removing `<meta generator>` and removing `/readme.html`, WhatWeb should go quiet.

**Expert knowledge:** a single plugin like WordPress has many independent signals: the generator tag, relative `/wp-content/` links (certainty 75), the REST API link, `/wp-cron.php`, `/wp-login.php` text and tag patterns, favicon MD5s, and `/readme.html` version regexes. Removing the meta tag alone is not enough. Obscurity buys time, while patching fixes the actual problem.

## Role: OSINT / Threat Intelligence Analyst

**Why it matters:** it profiles infrastructure and gives you pivot points.

**Day to day:** extract `Email[]`, analytics or AdSense account IDs, and `UncommonHeaders`, then pivot. Sites that share a tracking ID often share an owner or operator.

**Expert knowledge:** the GA plugin misses GA4 `G-` IDs and the email regex cuts off long TLDs (both verified), so write a custom plugin or use `--grep` for those. Route scans through `--proxy` or Tor to keep attribution off you. 0.6.2+ handles `.onion` sites.

## Role: Network Engineer

**Why it matters:** it identifies embedded devices and appliances on the LAN from their web admin UIs.

**Day to day:** `whatweb --no-errors 10.0.0.0/24` identifies routers, printers, cameras, UPSs and BMCs. Plugins exist for many devices (e.g. `3COM-NBX` in the list).

**Expert knowledge:** add `--url-prefix https://` for devices that only answer on HTTPS, and run a quick port scan first. Its value here is finding unmanaged devices that the asset register doesn't know about.

## Role: Web Developer / DevOps Engineer

**Why it matters:** it shows what your production stack reveals to the public, and lets you benchmark competitors' stacks.

**Day to day:** add it to CI after deploy (`whatweb -a 1 --log-json`) and fail the build if version-revealing plugins appear in production (`X-Powered-By` with a version, `MetaGenerator`, framework versions).

**Expert knowledge:** CDNs and WAFs (CloudFlare plugin) mask the origin. What WhatWeb sees is your **edge**. Also check the origin directly from inside your network.

## Role: Security Researcher / Plugin Author

**Why it matters:** writing WhatWeb fingerprint plugins teaches passive vs. active fingerprinting.

**Day to day:** write `plugins/<name>.rb` files with `matches [...]` plus optional `passive do` and `aggressive do` blocks. Load test plugins with `--custom-plugin`.

**Expert knowledge:** know all the match keys (`:text`, `:regexp`, `:version`, `:md5`, `:tagpattern`, `:ghdb`, `:status`, `:url`) and `:search` scopes (body, `all`, `headers`, `headers[x]`, `uri.path`, `uri.query`, `uri.extension`). Set `:certainty` (default 100) for weak signals. Remember that a `:url` match triggers an extra fetch in aggressive mode. Use `plugin-development/` helpers (`get-pattern`, `find-common-stuff`) and the Alexa lists for testing. Good first contributions: a GA4 `G-` detector, and an email regex that accepts long TLDs.

---

## Related topics (where it applies)

- **Study areas:** reconnaissance and enumeration, web application fingerprinting, attack surface management (ASM), OSINT, vulnerability management, the HTTP protocol (RFC 9110 headers), web server hardening, WAF/CDN behaviour.
- **Standards and frameworks:** OWASP WSTG **INFO-02** (Fingerprint Web Server) and **INFO-08** (Fingerprint Web Application Framework); MITRE ATT&CK **T1595** and **T1592.002**; PTES Intelligence Gathering.
- **Certifications and curricula:** OSCP (PEN-200), eJPT / eCPPT, CEH (footprinting, web server hacking), CompTIA PenTest+, PNPT, OSWA, GIAC GPEN / GWAPT, Kali KLCP, HTB / TryHackMe web-recon modules.
- **Lab idea:** serve a fake CMS page locally (as in these notes), scan it at `-a 1` and `-a 3`, watch the server's access log to see the extra requests, then strip each signal and see which detections disappear.

---

## Follow-up Q&A

### Q: whatweb (role pick)
Domains: Cybersecurity (recon/VAPT), Web Application Security, OSINT, Web Development/IT Operations. All 8 suggested roles were selected: Penetration Tester / Red Teamer, Bug Bounty Hunter, Cybersecurity Analyst (SOC/VulnMgmt), Web Application Security Engineer, OSINT / Threat Intelligence Analyst, Network Engineer, Web Developer / DevOps Engineer, Security Researcher / Plugin Author.

### Q: all (full explore)
Covered in full above: install, ten command groups with real output, field explanations, an end-to-end recon task, gotchas (three verified in source and by experiment: email TLD truncation, GA4 miss, exit code 0), origin and history, internals, cross-platform comparison, alternatives, the eight role sections, and related topics.

---

## Sources

[1] A. Horton and B. Coles, "WhatWeb – Next generation web scanner," GitHub repository README. [Online]. Available: https://github.com/urbanadventurer/whatweb (accessed Nov. 17, 2026).

[2] DEV.co, "WhatWeb," open-source security listing. [Online]. Available: https://dev.co/security/open-source/whatweb (accessed Nov. 17, 2026).

[3] NewReleases.io, "urbanadventurer/WhatWeb v0.6.1." [Online]. Available: https://newreleases.io/project/github/urbanadventurer/WhatWeb/release/v0.6.1 (accessed Nov. 17, 2026).

[4] NewReleases.io, "urbanadventurer/WhatWeb v0.6.2." [Online]. Available: https://newreleases.io/project/github/urbanadventurer/WhatWeb/release/v0.6.2 (accessed Nov. 17, 2026).

[5] NewReleases.io, "urbanadventurer/WhatWeb v0.6.3." [Online]. Available: https://newreleases.io/project/github/urbanadventurer/WhatWeb/release/v0.6.3 (accessed Nov. 17, 2026).

[6] NewReleases.io, "urbanadventurer/WhatWeb v0.6.4." [Online]. Available: https://newreleases.io/project/github/urbanadventurer/WhatWeb/release/v0.6.4 (accessed Nov. 17, 2026).

[7] Debian, "whatweb – Debian Package Tracker." [Online]. Available: https://tracker.debian.org/whatweb (accessed Nov. 17, 2026).

[8] Gentoo overlay ebuild for whatweb. [Online]. Available: https://gpo.zugaina.org/AJAX/Ebuild/56328324/View (accessed Nov. 17, 2026).

[9] hqren/WhatWeb (fork with old README example output). [Online]. Available: https://github.com/hqren/WhatWeb (accessed Nov. 17, 2026).

[10] D. Gupta, "WhatWeb," Recon Atlas. [Online]. Available: https://guptadeepak.com/recon-atlas/tool/whatweb/ (accessed Nov. 17, 2026).

[11] gremwell/WhatWeb (fork carrying the 0.4.6 README). [Online]. Available: https://github.com/gremwell/WhatWeb (accessed Nov. 17, 2026).

[12] A. Horton, "Next generation web scanning – New Zealand: A case study," Kiwicon III, 2009. [Online]. Available: https://www.exploit-db.com/download/13674 (accessed Nov. 17, 2026).

[13] Packet Storm Security, author page for MorningStar Security releases. [Online]. Available: https://packetstormsecurity.com/files/authors/6819/page2/ (accessed Nov. 17, 2026).

[14] A. Horton, "WhatWeb v0.4.6 Released. Now with over 900 plugins!," Full Disclosure mailing list, Mar. 26, 2011. [Online]. Available: https://seclists.org/fulldisclosure/2011/Mar/302 (accessed Nov. 17, 2026).

[15] Enthec, "webappanalyzer." [Online]. Available: https://github.com/Zalaxx/webappanalyzer (accessed Nov. 17, 2026).

[16] HTTP Archive, "wappalyzer" fork. [Online]. Available: https://awesome.ecosyste.ms/projects/github.com%2Fhttparchive%2Fwappalyzer (accessed Nov. 17, 2026).

[17] OWASP ZAP, "Technology Detection" add-on documentation. [Online]. Available: https://zaproxy.org/docs/desktop/addons/technology-detection (accessed Nov. 17, 2026).

[18] WhatWeb 0.6.4 source code: `lib/plugins.rb`, `lib/gems.rb`, `lib/logging/`, `plugins/wordpress.rb`, `plugins/email.rb`, `plugins/google-analytics.rb`, `plugins/country.rb` (read locally, Nov. 17, 2026).

Notes on certainty: release dates, aggression levels, options and changelog items come from the README and release notes. Match types, defaults and the three bugs (email TLD, GA4, exit code) were verified by reading the 0.6.4 source and by running it locally. The following come from general knowledge and were not re-verified in this session: Homebrew availability, RFC section numbers, httprint history, Brendan Coles's Metasploit work, Termux support, certification mappings, and the WSTG/ATT&CK IDs.
