---
tool: CDN (Content Delivery Network)
date: 2026-11-24
domains: [Networking, Internet infrastructure, Web performance, Cloud/DevOps, Security (DDoS/WAF), Media streaming, DNS]
roles: [Network Engineer]
tags: [cdn, anycast, bgp, dns, ecs, edns-client-subnet, caching, http-caching, peering, ixp, akamai, cloudflare, cloudfront, fastly, open-connect, google-global-cache, public-dns, 8.8.8.8, dns-leak-test, isp-dns, censorship-india]
studied_as: concept (providers used as worked examples)
---

# CDN (Content Delivery Network)

## Summary

A **CDN** is a network of servers spread around the world (points of presence, **PoPs**) that keep copies of content (websites, APIs, downloads, video) close to users. It steers each user to a nearby edge, so pages load faster, the origin carries less load, transit costs drop and DDoS traffic is absorbed at the edge. Example: a request from Tokyo for a US-hosted asset is answered by a nearby PoP in under ~50 ms RTT instead of crossing a 150–250 ms transcontinental link.

CDN is an **architecture and a service category, not a single tool**. The largest providers are Akamai, Cloudflare and Amazon CloudFront, followed by Google, Microsoft and Fastly. It was studied here as a concept through the **Network Engineer** lens, with providers as examples.

A CDN steers users in one of two ways (most large deployments now combine both):
- **DNS-based mapping** (pioneered by Akamai): an authoritative DNS server returns a different edge IP depending on who is asking (the resolver's address, or the client's subnet via ECS).
- **BGP anycast** (Cloudflare and others): the same IP prefix is announced from every PoP, and Internet routing delivers each packet to one of them.

---

## Usage & commands (with sample outputs)

> You don't install a CDN; you buy one (Akamai, Cloudflare, CloudFront, Fastly, Google Cloud CDN, Azure Front Door, Gcore, bunny.net, CDN77) or build one from parts: caches (Varnish, nginx `proxy_cache`, Apache Traffic Server, Squid) plus steering (GeoDNS such as PowerDNS/NS1/Route 53, or your own anycast with BIRD/FRR).
> Inspecting a CDN from outside uses standard tools: Linux/macOS `dig`, `curl`, `mtr`/`traceroute`, `whois`, `openssl`; Windows `Resolve-DnsName`, `curl.exe`, `tracert`, `pathping`.
> The sample outputs below are representative; your values will differ.

### 1. Find out which CDN fronts a site: follow the CNAME chain
```
$ dig +noall +answer www.example-shop.com
www.example-shop.com.        300  IN CNAME www.example-shop.com.edgekey.net.
www.example-shop.com.edgekey.net. 21600 IN CNAME e1234.a.akamaiedge.net.
e1234.a.akamaiedge.net.       20  IN A     23.45.67.89
```
- Suffix → provider: `edgekey.net` / `akamaiedge.net` = Akamai, `cloudfront.net` = CloudFront, `fastly.net` = Fastly. Cloudflare-proxied names usually return A/AAAA records directly, with no CNAME.
- A **20 s TTL** on the last record means a DNS-steered CDN that re-decides often. Akamai's mapping uses a two-level DNS hierarchy whose low-level answers typically have a TTL near 20 s, so it can move traffic off a degraded cluster in about a minute.

### 2. Tell DNS steering from anycast: ask from different vantage points
```
$ dig @<authoritative-ns> +subnet=49.36.0.0/24 e1234.a.akamaiedge.net +short
23.45.67.89
$ dig @<authoritative-ns> +subnet=81.2.69.0/24 e1234.a.akamaiedge.net +short
2.16.186.10        ← different answer for a UK subnet = DNS-based steering
```
- `+subnet` sends an **EDNS Client Subnet** (RFC 7871) option, as a resolver would. A DNS-steered CDN normally sees only the resolver's IP; ECS passes a truncated client prefix, usually a /24.
- If the answer changes with the subnet, the CDN uses DNS steering. If you get the same IP everywhere, it's anycast.

### 3. Read the cache headers (the most useful single command)
```
$ curl -sI https://www.example.com/app.js
HTTP/2 200
cache-control: public, max-age=86400
age: 3412
cf-cache-status: HIT
cf-ray: 8f1a2b3c4d5e6f70-BOM
```
- `age`: seconds the object has been in cache. `cf-cache-status`: HIT / MISS / EXPIRED / REVALIDATED / BYPASS / DYNAMIC. The `cf-ray` suffix is the IATA code of the PoP (BOM = Mumbai).

Other providers use different headers:
```
x-cache: Hit from cloudfront
x-amz-cf-pop: BOM78-P1
via: 1.1 3f2a....cloudfront.net (CloudFront)
---
x-served-by: cache-bom4741-BOM          # Fastly node + PoP
x-cache: MISS, HIT                      # shield, then edge
x-cache-hits: 0, 7
```
- CloudFront, Fastly, Varnish, Akamai and Azure use `X-Cache` (each with its own values); Cloudflare uses `Cf-Cache-Status`.
- The standard replacement is `Cache-Status` (RFC 9211, Mark Nottingham, Fastly, June 2022). In 2026 Netlify Edge and Deno Deploy send it; Cloudflare, Fastly and Akamai still use their own headers.
- Tip: request the same URL twice. MISS then HIT means caching works. MISS twice means the cache key or headers are preventing it.

### 4. Akamai debug headers
```
$ curl -sI -H 'Pragma: akamai-x-cache-on, akamai-x-get-cache-key, akamai-x-check-cacheable' https://www.example-shop.com/
X-Cache: TCP_MEM_HIT from a23-45-67-89.deploy.akamaitechnologies.com (AkamaiGHost/...)
X-Check-Cacheable: YES
X-Cache-Key: S/L/1234/567890/1d/www.example-shop.com/
```
- `TCP_HIT` / `TCP_MEM_HIT`: the edge had the object (disk or memory). `TCP_MISS`: fetched from a parent tier or the origin. `1d` in the cache key is the TTL; the hostname shows which edge server answered.

### 5. Ask the edge where you landed (Cloudflare)
```
$ curl -s https://www.cloudflare.com/cdn-cgi/trace
ip=49.36.x.x
colo=BOM
loc=IN
http=http/2
tls=TLSv1.3
warp=off
```
- `colo` is the PoP that answered. If you're in Chennai and see `SIN`, your ISP's routing is sending you to Singapore. That's an anycast/BGP problem, not a caching problem.

### 6. Map an IP to its network (ASN)
```
$ whois -h whois.cymru.com " -v 104.16.132.229"
AS      | IP             | BGP Prefix      | CC | Registry | Allocated  | AS Name
13335   | 104.16.132.229 | 104.16.128.0/20 | US | arin     | 2014-03-28 | CLOUDFLARENET - Cloudflare, Inc., US
```
- ASNs to recognise: Cloudflare AS13335, Google AS15169, Netflix AS2906, Akamai AS20940 (among others), Amazon/CloudFront AS16509.

### 7. See the path to the edge
```
$ mtr -rwz -c 20 www.example.com
HOST                                   Loss%  Snt  Last  Avg  Best  Wrst
 1. AS???   192.168.1.1                0.0%   20   1.1  1.3   0.9   2.4
 2. AS55836 10.x.x.x                   0.0%   20   4.8  5.2   4.1   9.8
 ...
 6. AS13335 172.71.x.x                 0.0%   20   6.9  7.1   6.5   8.0
```
- `-z` shows the ASN of each hop. The CDN's ASN 3–6 hops away at single-digit ms means on-net or locally peered. A last hop 60–80 ms away means you're being served from another country.

### 8. Check how the prefix is announced in BGP (RIPEstat, bgp.tools, looking glass)
```
route-views> show ip bgp 104.16.128.0/20
  Paths: (24 available)
  ... 6939 13335 / 3356 13335 / 1299 13335 ...   origin AS13335 via every upstream
```
- Anycast: the same prefix and origin AS are visible from everywhere; the **local** BGP best path decides which PoP you reach.
- DNS-steered CDN: edge IPs are often in the hosting ISP's prefixes (embedded caches), not the CDN's own AS.

### 9. Look at the TLS edge
```
$ openssl s_client -connect www.example.com:443 -servername www.example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -ext subjectAltName
subject=CN = example.com
issuer=C = US, O = Google Trust Services, CN = WE1
```
- TLS ends at the edge, so you see the certificate the CDN presents (often provider-issued). SNI (`-servername`) is required because one edge IP serves thousands of hostnames.

### 10. Time each phase and purge the cache
```
$ curl -so /dev/null -w 'dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://www.example.com/
dns=0.012 tcp=0.019 tls=0.041 ttfb=0.058 total=0.061      ← HIT at edge
dns=0.011 tcp=0.019 tls=0.040 ttfb=0.412 total=0.420      ← MISS: ttfb includes the origin fetch

$ aws cloudfront create-invalidation --distribution-id E2ABC123 --paths "/index.html" "/css/*"
```
- A fast `tcp` time means the edge is close. A large gap between `tls` and `ttfb` is time spent at the origin or in the cache hierarchy.
- Purging needs API credentials. Fastly purges near-instantly; CloudFront invalidations are slower and cost extra beyond the free quota.

### Worked task: "Chennai users say the site is slow"
1. **Identify the CDN:** `dig +noall +answer` (CNAME suffix), then `whois.cymru.com` on the IP. Say it's Cloudflare.
2. **Find the PoP:** `curl /cdn-cgi/trace` from a Chennai vantage point (RIPE Atlas probe, VM, or the user). It shows `colo=SIN`.
3. **Check the path:** `mtr -z` shows the ISP's AS handing off to a transit AS that carries traffic to Singapore. The ISP has no local peering with AS13335 in Chennai or Mumbai, or a BGP policy that prefers one transit exit.
4. **Rule out caching:** `curl -sI` twice: HIT, `age` increasing. Caching is fine; the problem is RTT, not the origin.
5. **Measure:** `curl -w` gives tcp=0.070 s, against about 0.010 s from Mumbai. Each extra round trip adds ~60 ms.
6. **Fix (network-side):** open a ticket with the CDN NOC and the ISP peering team: a PNI, a peering session at the local IXP, or a BGP community/prepend change. On a DNS-steered CDN, check instead whether users sit behind a public resolver that hides their location, and fix that with ECS, a local resolver or an ISP-embedded cache.
7. **Verify:** re-run trace and mtr: `colo=MAA` or `BOM`, single-digit RTT.

---

## Output / fields explained

| Field / header | Provider | Meaning |
|---|---|---|
| CNAME suffix (`edgekey.net`, `akamaiedge.net`, `cloudfront.net`, `fastly.net`) | DNS | Which CDN fronts the hostname |
| TTL ≈ 20 s on final A record | Akamai | DNS mapping re-decides frequently, so traffic can be moved off a bad cluster within about a minute |
| `age` | All (RFC 9111) | Seconds the response has been stored in cache |
| `cache-control: max-age=…, public` | Origin | How long caches may keep it; `private`/`no-store` prevent shared caching |
| `cf-cache-status` | Cloudflare | HIT / MISS / EXPIRED / REVALIDATED / BYPASS / DYNAMIC |
| `cf-ray: <id>-<IATA>` | Cloudflare | Request ID + PoP airport code |
| `x-cache: Hit/Miss/RefreshHit from cloudfront` | CloudFront | Cache result at the edge |
| `x-amz-cf-pop: BOM78-P1` | CloudFront | Edge location that served you |
| `x-served-by`, `x-cache: MISS, HIT`, `x-cache-hits` | Fastly | Node chain (shield → edge) and per-node result and hit counts |
| `X-Cache: TCP_HIT / TCP_MEM_HIT / TCP_MISS`, `X-Cache-Key` | Akamai (Pragma debug) | Edge result; cache key including TTL |
| `Cache-Status: Name; hit; ttl=…` / `fwd=…` | RFC 9211 standard | Standard per-cache report, one entry per cache in the chain |
| `colo=`, `loc=`, `http=`, `tls=` | Cloudflare `/cdn-cgi/trace` | PoP, client country, HTTP version, TLS version |
| Team Cymru whois columns | — | AS, IP, BGP prefix, country, RIR, allocation date, AS name |
| `curl -w` timers | — | DNS / TCP connect / TLS done / first byte / total |
| `o-o.myaddr.l.google.com` TXT | Google Public DNS | Egress resolver IP plus the ECS subnet forwarded on your behalf |

---

## History & evolution

### Origin
- Before CDNs: FTP **mirror sites**, then shared **web proxy caches** (the Harvest project, which led to Squid in the mid-1990s).
- The commercial CDN came from **MIT**. Paper: Karger, Lehman, Leighton, Panigrahy, Levine, Lewin, *"Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web"*, ACM STOC 1997, pp. 654–663. The problem was **hot spots**: a popular page overwhelming one server.
- **Akamai** entered the 1998 MIT $50K competition with a plan based on consistent hashing and was one of six finalists out of about 100 entries. It had a working prototype by August 1998 and was incorporated on **20 August 1998**.
- Founders: **Daniel Lewin, F. Thomson (Tom) Leighton**, Jonathan Seelig, Randall Kaplan (plus Preetish Nijhawan in some lists). Leighton headed the Algorithms Group at MIT's Laboratory for Computer Science. Lewin found the name *akamai* (Hawaiian for "clever" / "cool") in a Hawaiian–English dictionary.
- **Lewin was killed on 9/11** (aged 31, American Airlines Flight 11) after fighting the hijackers. Leighton became CEO in 2013, replacing Paul Sagan.
- Contemporaries: Sandpiper Networks, Digital Island; RealNetworks built a media-only network (RBN) for streaming. "First CDN" depends on the definition, but Akamai is generally treated as the first large commercial one.

### How the concept evolved

| Era | Idea | Key specs / events |
|---|---|---|
| 1990s | Mirrors, then shared proxy caches | Harvest/Squid; ICP (RFC 2186/2187, 1997) |
| 1997–99 | Consistent hashing + DNS mapping onto many edge servers | Karger et al. 1997; Akamai 1998 |
| 2003 | First IETF CDN-interconnection attempt | RFC 3466 (CDI) |
| 2000s | Anycast moves from DNS root servers to HTTP | RFC 1546 (1993), RFC 4786 (anycast operations, 2006); Cloudflare launches 2010 on all-anycast |
| late 2000s–2012 | Caches embedded inside ISPs | Google Global Cache; Netflix Open Connect |
| 2014 | CDN-to-CDN interconnection | RFC 7336 (CDNI framework, Aug 2014; Peterson (Akamai), Davie, van Brandenburg), which with RFC 6707 obsoletes RFC 3466 |
| 2016 | Better DNS steering | ECS, RFC 7871 |
| 2017–22 | Edge compute + caching standards | Lambda@Edge, Cloudflare Workers; RFC 9111 (HTTP caching), RFC 9211 (Cache-Status), RFC 9213 (CDN-Cache-Control); HTTP/3/QUIC (RFC 9000 family) |
| 2024–26 | Consolidation | Edgio's assets acquired by Akamai (late 2024), Edgio no longer operating (2025); StackPath shut down its CDN |

### Why it's used today
- **Physics:** each TCP + TLS round trip costs a full RTT, and a nearby edge shortens every handshake.
- **Economics:** serving from inside or next to the user's ISP avoids paid transit for both sides (embedded caches, settlement-free peering).
- **Capacity:** the combined edge bandwidth absorbs DDoS attacks no single origin could.
- **Stack position:** combines DNS (steering), BGP (anycast, peering), L4 (TCP/QUIC termination) and L7 (HTTP cache and proxy) between eyeball networks and origins.
- **Scale:** Akamai, Cloudflare and Amazon CloudFront are the largest by public measures, followed by Google, Microsoft and Fastly. Akamai reported $3.99 B revenue for 2024 and $4.21 B for 2025.

---

## How it works internally

1. **Steering**: how a user reaches an edge.
   - **DNS-based**: the user's resolver asks the CDN's authoritative DNS, which picks an edge from the resolver IP (or the ECS client subnet) and live load/health data, and returns it with a short TTL. It gives fine control on small timescales, but decisions are made per resolver.
     - Akamai architecture: an edge network of about 4,100 server locations across 1,000+ partner networks, a mapping system that re-scores clusters every tens of seconds to minutes, and tiered caching.
   - **Anycast**: the same prefix is announced from every PoP, and BGP chooses. It is simple, recovers fast from failures, and has low cold-start latency, but BGP doesn't measure latency, so control is coarse.
   - **Regional anycast**: anycast within a region, DNS steering between regions.
   - **Measurement (2026):** in one study, 12 of 17 CDNs used DNS-based redirection, and DNS-based systems delivered the most bytes in most regions. Validation recovered Akamai as DNS-based, Cloudflare as anycast and Edgio as regional anycast. Most large deployments combine both: DNS selects the region, anycast handles the rest.
2. **Consistent hashing**: maps objects to cache servers so adding or removing a server reshuffles only a small fraction of keys. This is what lets a cluster share load without duplicating every object.
3. **Tiered caching / origin shield**: edge → parent/regional tier → origin. Called Argo Tiered Cache (Cloudflare), Origin Shield (Fastly/CloudFront) and Tiered Distribution (Akamai). It cuts origin requests sharply (often quoted as 70–90%).
4. **HTTP caching rules**: RFC 9111 freshness (`max-age`, `s-maxage`, `Age`), validation (ETag/If-None-Match), `Vary`, cache keys; `CDN-Cache-Control` (RFC 9213) targets CDN caches specifically.
5. **TLS termination at the edge**: SNI selects the certificate; the edge re-encrypts to the origin (or uses authenticated origin pulls or mTLS).
6. **Private/embedded CDNs (Netflix Open Connect)**:
   - Open Connect Appliances (OCAs) come in two forms: embedded inside ISPs, and clustered at IXPs.
   - Each appliance establishes a **BGP session with the closest connected router**, so the ISP controls which networks it serves.
   - Netflix gives qualifying ISPs the hardware free. The ISP provides rack space, power and connectivity; Netflix owns and operates the box.
   - The threshold is roughly **5 Gbps of Netflix peak traffic**; smaller ISPs are served from the nearest peering point.
   - The playback service hands the client the URL of an appliance that already has the file, so a miss never becomes a user-visible latency event.
   - Netflix still carries about 15% of global downstream traffic (2026).
   - Google Global Cache does the same for YouTube.

---

## Cross-platform comparison table

| System | Steering | Where caches sit | Control for a network engineer |
|---|---|---|---|
| Akamai | DNS mapping (short TTLs, resolver/ECS based) | Very deep: ~4,100 locations in 1,000+ partner networks, plus tiered parents | Fine-grained per request; DNS-cache lag |
| Cloudflare | Global anycast: same IPs everywhere, BGP decides | Every PoP runs every service | Peering and BGP communities; fast failover |
| CloudFront | DNS-based to edge locations; regional edge caches as a middle tier | AWS edge locations | Route 53 integration; origin shield |
| Fastly | Mix of DNS and anycast; fewer, larger PoPs | Varnish heritage; shielding | Instant purge; programmable edge (VCL/Compute) |
| Netflix Open Connect | App hands out an appliance URL | Inside ISPs + IXP sites | BGP session per appliance; ISP decides which prefixes it serves |
| Google Global Cache | Google steering | Inside ISPs | Same model as OCA, for YouTube/Google |
| Windows Delivery Optimization | OS peer discovery | Other PCs (LAN/WAN) | Group Policy / Intune |
| Microsoft Connected Cache | Configured cache node | ISP or enterprise network | Hosted by the ISP or enterprise |
| macOS Content Caching | Devices find the cache by public IP/subnet | A Mac on the LAN | Settings / MDM |
| ISP / enterprise proxy cache (Squid, ATS) | Transparent or explicit proxy | Inside the network | Full |

---

## Alternatives

- **Same idea, built yourself:** Varnish, nginx `proxy_cache`, Apache Traffic Server, Squid, HAProxy; GeoDNS or latency-based DNS (PowerDNS, NS1, Route 53); your own anycast with BIRD/FRR.
- **Different approaches to the same problem:** multi-region origins with global load balancing; P2P delivery (BitTorrent, WebRTC peer-assisted CDNs); IP multicast (IPTV inside ISPs); content-addressed networks (IPFS).
- **By platform:**
  - **Windows**: Delivery Optimization (P2P updates), BranchCache, Microsoft Connected Cache.
  - **macOS/iOS**: Content Caching (caches Apple software updates and some iCloud data for devices on the LAN).
  - **Linux**: apt-cacher-ng, or Squid as a distro mirror/cache.
  - **Android/iOS apps**: no OS-level CDN; apps rely on their backend's CDN.
  - **Cloud**: CloudFront (AWS), Cloud CDN / Media CDN (Google), Azure Front Door (Microsoft is moving customers from classic Azure CDN to Front Door).
- **Commercial market (2026):** Akamai, Cloudflare, CloudFront, Fastly, Google Cloud CDN, Azure, Gcore, bunny.net (Volume pricing about $0.005/GB), CDN77, EdgeNext, Hostinger CDN. Edgio is gone (assets to Akamai) and StackPath's CDN shut down.

---

## Role: Network Engineer

**Why it matters:** a large share of an eyeball network's inbound traffic comes from a few CDNs and "hypergiants" (Netflix alone is about 15% of global downstream traffic, over 30% at evening peak on some North American access networks). How you peer with them sets the transit bill and users' latency.

**Day to day:**
- **Peering decisions:** settlement-free peering at an IXP, a PNI, or hosting embedded caches (Netflix OCA, Google GGC) at no hardware cost to the ISP above the traffic threshold.
- **Hosting cache racks:** space, power, a BGP session per appliance, deciding which customer prefixes each cache serves, and the fallback path when it misses or fails.
- **Traffic engineering:** BGP communities, local-pref and prepends to pull CDN traffic onto the right links; capacity planning for evening peaks and big launches (game patches, OS updates, live sport).
- **Troubleshooting:** the toolkit above, used to separate routing problems (wrong PoP) from resolver problems (wrong DNS answer), cache problems (MISS) and origin problems (slow TTFB).
- **Running your own anycast** (DNS or an internal CDN): announce the same prefix from many sites, withdraw routes based on health checks, and avoid more-specific prefixes that undo the anycast.

**What an expert knows that a beginner doesn't:**
- Anycast means "closest by BGP policy", not by kilometres. One ISP with a single upstream exit can send a whole country to the wrong continent.
- DNS steering works per resolver. ECS helps, but costs privacy and resolver cache efficiency, and not every resolver sends it.
- An edge IP inside *your* address space means an embedded cache. Its misses become fill traffic upstream, which you must plan capacity for.
- Hit ratio measures origin offload. The latency users see depends mostly on RTT to the edge plus how many tiers a miss passes through.
- Hosting caches changes peering negotiations: embedded appliances move traffic off IXP and transit ports, so the business case is about bytes and power, not just latency.
- Anycast interacts badly with stateful middleboxes (firewalls, CGNAT with asymmetric return paths, PMTUD), so test from inside your own network, not just from a looking glass.

### Common mistakes, permissions and gotchas
- Blaming the CDN for an ISP routing problem: with anycast, your ISP's BGP best path picks the PoP.
- Public-resolver mislocation on DNS-steered CDNs, when the resolver doesn't send ECS.
- **Origin IP leaks:** old DNS records, MX/SPF hosts or direct-to-IP requests let attackers bypass the CDN and its DDoS protection. Firewall the origin to the CDN's IP ranges, or use authenticated origin pulls or mTLS.
- **Cache-key pollution:** query strings, cookies and `Vary: User-Agent` split the cache into thousands of variants, so the hit ratio collapses.
- **Anycast + PMTUD:** an ICMP "Packet Too Big" message can reach a different server than the one holding the TCP session. Watch MSS clamping and tunnels (GRE/IPsec).
- **Allowlisting:** origin fetches and health checks come from the CDN's address ranges, which change. Pull the published lists automatically.
- **Permissions:** client-side inspection needs nothing special; `mtr` needs `cap_net_raw` (via `mtr-packet`) or root; purges and config changes need provider API credentials.

---

## Related topics, study areas & certifications
- **Courses and texts:** Kurose & Ross, *Computer Networking: A Top-Down Approach* (application layer: DNS, CDNs, video streaming); distributed systems (consistent hashing).
- **Certifications:** CompTIA Network+ (CDN concepts); Cisco CCNP/CCIE Service Provider and Enterprise (BGP traffic engineering, anycast); AWS Certified Advanced Networking – Specialty (CloudFront, Route 53); Azure networking (Front Door).
- **Areas:** BGP and inter-domain routing, IXPs and peering economics (PeeringDB, NANOG/APRICOT/SANOG talks), DNS (ECS, TTL design, public resolvers), HTTP caching (RFC 9111/9211/9213), DDoS mitigation, video delivery (HLS/DASH), network measurement (RIPE Atlas, academic CDN-mapping studies), Internet censorship measurement.
- **Related library entries:** `DNS`, `dig`, `resolvectl`, `whois`, `host`, `nslookup`, `nmap`, `whatweb`.

---

## Follow-up Q&A

### Q1. How is a CDN different from DNS? `resolvectl status` shows 8.8.8.8, but dnsleaktest shows different IPs marked as Google. What's going on, and how does the CDN affect the result?

**CDN vs DNS**

| | DNS | CDN |
|---|---|---|
| Job | Translates a name into an address ("where is `www.x.com`?") | Delivers the content from a server near you |
| What travels | Small questions and answers (UDP/TCP 53, DoT 853, DoH 443) | Pages, images, video, APIs (HTTP/HTTPS/QUIC) |
| Main parts | Stub resolver, then recursive resolver (8.8.8.8), then authoritative servers | Edge PoPs, cache tiers, origin |
| Relationship | One of the two ways a CDN steers you (the other is BGP anycast) | Uses DNS as its "front desk" |

A CDN isn't a kind of DNS; it *uses* DNS. Its authoritative name servers pick an edge IP based on **who is asking**, and that is exactly what the leak test reveals.

**Why the IPs differ: Google Public DNS has a separate front door and back door**
```
your PC ──query──▶ 8.8.8.8  (anycast "front door", same IP worldwide)
                     │  BGP delivers it to the nearest Google DNS cluster (e.g. Mumbai)
                     ▼
              cluster of many resolver machines
                     │  each has its OWN unicast "egress" IP
                     ▼
        authoritative server (dnsleaktest's, or a CDN's) sees THAT egress IP
```
- 8.8.8.8 / 8.8.4.4 are **anycast**. Queries go to the nearest Google DNS cluster by best route, and each cluster has many servers.
- When a cluster member queries an authoritative server, it uses its **own egress IP**. Google publishes these ranges with location codes (`bom`, `del`, `sin`, `atl`…).
- **How a leak test works:** the site makes your browser resolve several random, one-time subdomains under a zone it runs. Its authoritative server records the source IP of every recursive resolver that comes to ask. That is always the egress IP, never 8.8.8.8. Random names mean caches can't hide any resolver.
- **Multiple IPs are normal:** each query can be handled by a different cluster member. Seeing several DNS servers is not a leak.
- Google's resolvers answer only at 8.8.8.8/8.8.4.4, not at the members' own IPs.
- **Is it a leak?** No. A leak would be your ISP's resolver (Jio, Airtel, ACT…) appearing when you configured 8.8.8.8 or are using a VPN. All-Google results mean your queries really go to Google.

**Verify it yourself**
```bash
resolvectl status
#   Current DNS Server: 8.8.8.8      ← where your stub sends queries
#   (apps actually talk to 127.0.0.53, which forwards to 8.8.8.8)

dig o-o.myaddr.l.google.com TXT +short @8.8.8.8
"172.253.x.x"                                  ← egress IP (what leak tests see)
"edns0-client-subnet 49.36.x.0/24"             ← your /24, forwarded to authoritative servers

dig TXT locations.publicdns.goog +short @8.8.8.8   # egress ranges + location codes
whois -h whois.cymru.com " -v <ip-from-leak-test>"  # → AS15169 GOOGLE
```
- Repeat `o-o.myaddr` several times and the egress IP changes. That's the same load balancing the leak test shows.
- **Browser caveat:** Chrome and Firefox may use DoH themselves and bypass `resolvectl`. Chrome automatically upgrades to `dns.google` over DoH when the system DNS is 8.8.8.8, so the browser's path differs from `dig`'s, though the leak test still shows Google egress IPs.

**Where the CDN comes in**
1. **Google Public DNS is built like a CDN:** an anycast front end with clusters in many places (the same technique Cloudflare uses for its edges). Your ISP's BGP decides which cluster, so egress IPs should be in a city near you (`bom`/`del` for India). `sin` or Europe means your ISP's routing, not Google.
2. **The egress IP + ECS decide which CDN edge you get.** For a DNS-steered CDN (e.g. Akamai), the authoritative server sees the Google egress IP *and* the ECS /24 of your address, and maps you near you. With a resolver that doesn't send ECS (Cloudflare 1.1.1.1, for privacy), the CDN only knows the resolver's location and may choose a worse edge. Anycast CDNs aren't affected, because BGP picks the edge from your own packets.
   ```bash
   dig +short www.akamai.com @8.8.8.8      # steered using your ECS subnet
   dig +short www.akamai.com @1.1.1.1      # steered by the resolver's location only
   ```
3. **The CDN doesn't change the leak-test result.** The leak-test page may be served by a CDN, but the resolver list comes from DNS queries reaching the site's own authoritative server.

**In short:** 8.8.8.8 is where you send queries. The leak-test IPs are the Google servers doing the lookups, and that address plus your ECS subnet is what every CDN's DNS uses to decide where to send you.

### Q2. Why do so many people use Google DNS instead of their ISP's DNS? Why Google specifically, and why not other free resolvers or a custom one?

**Why people leave the ISP resolver**

| Reason | What's actually happening | Still valid in 2026? |
|---|---|---|
| "Faster / more reliable" | ISP resolvers were historically slow, overloaded or prone to outages; public resolvers use anycast, many servers and a huge shared cache | Sometimes; measure it |
| No NXDOMAIN hijacking | Some ISPs replace "domain doesn't exist" replies with answers pointing to their own ad or search pages; Google always returns a real NXDOMAIN, as the DNS standard requires | Yes, on some ISPs |
| Getting around blocks (big in India) | Blocking orders under IT Act Sections 69A and 79; each ISP implements them differently. Measured: DNS tampering by ACT, Airtel, BSNL and MTNL; HTTP header filtering by all six ISPs studied; SNI inspection by Jio only (Airtel returned NXDOMAIN for blocked sites; BSNL/MTNL returned wrong addresses). Blocking orders are confidential, and lists differ between ISPs. | Partly: changing DNS only escapes DNS-based blocks, not SNI or HTTP filtering. Encrypted DNS (DoH) prevents tampering with the DNS step. |
| Privacy from the ISP | The ISP sees every lookup and usually has no published DNS privacy policy | Only with encrypted DNS. Plain port-53 queries to 8.8.8.8 are still readable, and can be intercepted, by the ISP. |
| Habit / folklore | "Set DNS to 8.8.8.8" has been the standard fix in tutorials and help desks for 15 years | The main reason in practice |

**Why Google specifically**
1. **First and best known:** launched December 2009 with a promise to follow DNS protocols to the letter (no blocking, hijacking or filtering), focused on speed. Quad9 came in 2017 and Cloudflare 1.1.1.1 in 2018.
2. **Memorable address:** `8.8.8.8` / `8.8.4.4`.
3. **No-tampering policy:** filtering only in rare security or legal cases; no account needed.
4. **Infrastructure:** a large anycast footprint with clusters near Indian users; for years measured as the leader in most regions (newer 2026 tests often put Cloudflare ahead on speed).
5. **Works well with CDNs (ECS):** forwards your /24 so DNS-steered CDNs pick an edge near you, not near Google.
6. **Clear privacy terms, though not the strictest:** temporary logs with IP and query deleted within 24–48 h (may be kept longer only for security or abuse); permanent logs keep only city/region-level location for aggregate analysis; not used for ad targeting; not correlated with other Google services except for security and abuse.
7. **Modern protocols:** DNSSEC validation, DoH/DoT at `dns.google`; Chrome's automatic DoH upgrade.

**Why not Cloudflare, Quad9 and others: each is a trade-off**

| | Google 8.8.8.8 | Cloudflare 1.1.1.1 | Quad9 9.9.9.9 | AdGuard / NextDNS | ISP default |
|---|---|---|---|---|---|
| Filtering | None by default | None on 1.1.1.1; 1.1.1.2 blocks malware; 1.1.1.3 adds adult content | Threat blocking on by default (Swiss nonprofit) | Ad/tracker blocking, custom lists | Whatever the government or ISP blocks |
| ECS to CDNs | Yes | No (privacy win, small performance cost) | Not on 9.9.9.9; 9.9.9.11 is the ECS variant | Varies | Not needed (already inside your network) |
| Logging | IP kept 24–48 h | No source-IP logging; anonymised and deleted within ~25 h; audited in 2020 and 2026 | No source-IP logging | Configurable | Usually no public policy |
| Strength | Reliability, CDN accuracy, familiar name | Often fastest globally | Security with zero setup | Control over filtering | Closest; best match for ISP-hosted caches |

People stay with Google because once DNS works nobody re-checks it; filtering resolvers sometimes block sites users want, which surprises them; and Cloudflare's no-ECS choice can occasionally mean a less ideal edge.

**Why few run their own ("custom") DNS** (Pi-hole/AdGuard Home forwarding upstream, or Unbound doing full recursion):
- Needs an always-on box, updates and monitoring; if it dies, the whole house loses "internet".
- Privacy is less than it looks: Unbound queries authoritative servers from your home IP in plaintext, so the ISP still sees them; Pi-hole just moves the trust to its upstream.
- A small cache misses more often than Google's warm shared cache.
- Benefits: network-wide ad and tracker blocking, local names, full control, and no single company seeing everything.

**Network-engineer lens: the ISP side**
- **CDN mapping:** the ISP's own resolver is the best signal for steering users to caches embedded inside the ISP (OCA, GGC). With 8.8.8.8 the CDN depends on ECS; without ECS (1.1.1.1) users may be sent to a cache in another network or city, so moving away from ISP DNS can make streaming slightly *worse*.
- **Transparent DNS interception:** some ISPs answer all port-53 traffic themselves. Check with `dig o-o.myaddr.l.google.com TXT +short @8.8.8.8`: an IP in your ISP's ASN instead of AS15169 means "Google DNS" is being intercepted. Only DoH/DoT avoids this.
- **Lost visibility:** subscribers on public DNS remove a security and analytics signal from the ISP, which is one reason some ISPs now offer their own encrypted DNS.

**Measure instead of guessing**
```bash
for r in 8.8.8.8 1.1.1.1 9.9.9.9 $(resolvectl status | awk '/Current DNS Server/{print $4; exit}'); do
  printf '%-16s ' "$r"; dig @"$r" example.in +noall +stats | grep 'Query time'
done
# Run twice: first may be a cache miss; second shows network RTT + cache hit.
```
Then compare the CDN edge each resolver gives you (`dig +short www.akamai.com @<resolver>`, then `curl -sI` for the PoP code). Pick the fastest resolver that also lands you on a nearby edge, and add DoH/DoT (or Android "Private DNS") if privacy from the ISP is the goal.

**In short:** Google DNS is popular because it doesn't tamper with answers, gets around DNS-based blocking, has 15 years of default advice behind it, and works well with CDNs because it sends ECS. Cloudflare is often faster and logs less, Quad9 adds malware blocking, and running your own gives control; on plain port 53, none of them hides your lookups from your ISP.

---

## Sources

- Akamai Technologies — Wikipedia: https://en.wikipedia.org/wiki/Akamai_Technologies
- Akamai history (MIT $50K, prototype, incorporation): https://encyclopedia.com/books/politics-and-business-magazines/akamai-technologies-inc
- Mobile Television Could Not Exist Without CDNs (Lewin, consistent hashing, RBN): https://thebroadcastbridge.com/content/entry/553/mobile-television-could-not-exist-without-content-delivery-networks
- Karger et al., Consistent Hashing and Random Trees (STOC 1997): https://dl.acm.org/doi/10.1145/258533.258660
- RFC 7336 CDNI Framework: https://www.rfc-editor.org/rfc/rfc7336 · datatracker: https://datatracker.ietf.org/doc/rfc7336
- RFC 9211 Cache-Status: https://www.rfc-editor.org/rfc/rfc9211 · explainer: https://http.dev/cache-status
- X-Cache explainer: https://http.dev/x-cache
- RFC 9111 HTTP Caching: https://www.rfc-editor.org/rfc/rfc9111 · RFC 9213 CDN-Cache-Control: https://www.rfc-editor.org/rfc/rfc9213 · RFC 7871 ECS: https://www.rfc-editor.org/rfc/rfc7871
- Anycast vs DNS routing (BlazingCDN, 2026): https://blog.blazingcdn.com/en-us/anycast-vs-dns-routing-how-a-cdn-picks-the-pop
- Akamai CDN architecture explained: https://blog.blazingcdn.com/en-us/akamai-cdn-architecture-explained-edge-mapping-and-tiers
- CDN replica-selection study (NINeS 2026): https://drops.dagstuhl.de/storage/01oasics/oasics-vol139-nines2026/html/OASIcs.NINeS.2026.23/OASIcs.NINeS.2026.23.html
- Internet Society Pulse — Who is steering Internet traffic: https://pulse.internetsociety.org/en/blog/who-is-steering-internet-traffic-understanding-opacity-in-cdn-replica-selection/
- Analyzing the Performance of an Anycast CDN (IMC 2015): https://courses.cs.duke.edu/fall19/compsci514/papers/anycast-imc15.pdf
- APNIC Labs on anycast / content steering: https://labs.apnic.net/?p=1902
- ThousandEyes — Using Anycast for Internet Services: https://blog.thousandeyes.com/using-anycast-for-internet-services
- Biggest CDN providers 2026: https://blog.blazingcdn.com/en-us/biggest-cdn-providers-market-share-pop-count-2025
- Best CDN providers 2026: https://blog.blazingcdn.com/en-us/top-cdn-providers-2025-an-expert-guide-to-types-technologies-and-performance-0
- CDN providers list (wmtips): https://www.wmtips.com/technologies/cdn/
- CDN overview (PoP counts, tiered caching names): https://unseel.pages.dev/cs/cdn
- Netflix Open Connect: https://openconnect.netflix.com/en/ · overview PDF: https://openconnect.netflix.com/Open-Connect-Overview.pdf
- APNIC — Netflix content distribution through Open Connect: https://blog.apnic.net/2018/06/20/netflix-content-distribution-through-open-connect/
- Netflix Open Connect in 2026 (BlazingCDN): https://blog.blazingcdn.com/en-us/see-netflix-open-connect-explore-how-content-reaches-isps-globally
- Peering, IXPs and on-net caching (ASNs, OCA threshold, GGC): https://www.forasoft.com/learn/video-streaming/articles-streaming/peering-ixp-private-interconnect
- NANOG — Figuring out which Google DNS cluster you are using: https://mailman.nanog.org/pipermail/nanog/2017-August/092036.html · https://seclists.org/nanog/2017/Aug/223
- Google Public DNS FAQ: https://developers.google.com/speed/public-dns/faq · Intro: https://developers.google.com/speed/public-dns/docs/intro · Privacy: https://developers.google.com/speed/public-dns/privacy
- DNS leak test mechanics: https://www.whatismyip.com/dns-leak-test/ · https://www.ionos.com/digitalguide/server/know-how/dns-leak/ · https://speedtesthq.com/guides/privacy/what-is-a-dns-leak
- Introducing Google Public DNS (2009) discussion: https://boards.straightdope.com/t/google-dns-rocks/520111.md
- Infoblox — On Google's Public DNS Service: https://community.infoblox.com/discussion/3217/on-googles-public-dns-service
- Network World — public DNS performance: https://www.networkworld.com/article/3194890/comparing-the-performance-of-popular-public-dns-providers.html
- CIS India — How India Censors the Web: https://cis-india.org/internet-governance/blog/how-india-censors-the-web · paper: https://ar5iv.labs.arxiv.org/html/1912.08590
- CIS India — Reliance Jio SNI inspection: https://cis-india.org/internet-governance/blog/reliance-jio-is-using-sni-inspection-to-block-websites
- OONI — TLS blocking in India: https://ooni.org/post/2020-tls-blocking-india/
- Lantern corpus — India heterogeneous censorship: https://corpus.lantern.io/findings/2020-singh-india__india-heterogeneous-multi-layer-censorship/
- ThePrint — India has blocked at least 43,000 domains: https://theprint.in/tech/india-has-currently-blocked-at-least-43000-domains-new-study-shows-scale-for-the-first-time/2868178
- Quad9 vs Cloudflare (privacy, ECS): https://guptadeepak.com/quad9-vs-cloudflare-dns-which-resolver-is-more-secure-and-private/
- Top DNS security solutions 2026: https://guptadeepak.com/tools/top-5-dns-security-solutions-2026/
- Best DNS servers 2026 (Cyble): https://cyble.com/knowledge-hub/best-dns-servers-for-security/
- Best DNS servers October 2026 (Tech Insider): https://tech-insider.org/?p=47727
- NextDNS vs AdGuard vs Quad9 vs Cloudflare 2026: https://simeononsecurity.com/articles/dns-comparison-adguard-quad9-cloudflare-pi-hole/
