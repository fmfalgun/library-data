---
tool: System Resources
type: concept (not a tool)
date: 2026-11-24
domains: [Computer Architecture, Operating Systems, Performance Engineering, Cybersecurity]
roles: [Software Engineer / Developer, Red Team, Blue Team, Cybersecurity Expert]
tags: [cpu, ram, gpu, disk-io, network-io, cores, threads, smt, hyper-threading, numa, amdahl, c10k, io_uring, rss, bottleneck, performance, memory-hierarchy]
related_tools: [time, htop, top, mpstat, perf, free, vmstat, smem, nvidia-smi, nvtop, radeontop, iostat, iotop, fio, iftop, nload, ss, sar, ethtool, numactl, lscpu, hashcat, john, nmap, masscan, arp-scan, ffuf, gobuster, volatility, suricata, zeek]
---

# System resources: CPU, RAM, GPU, Disk I/O, Network I/O

## Summary

Every program uses five hardware resources: the **CPU** runs instructions, **RAM** holds the working data, the **GPU** does massively parallel maths, the **disk** stores data persistently, and the **network** moves data between machines. They differ in latency by up to a factor of 100 million, so performance work is mostly about keeping data as high up the memory hierarchy as possible and finding which single resource is the bottleneck. How much **cores** and **threads** help depends entirely on which resource is the limit. Compute scales with cores (if the code parallelises), while I/O scales with concurrency (threads or async), not with GHz.

**One-line analogy:** the CPU is the chef, RAM is the kitchen counter, the disk is the storeroom, the network is the delivery van, and the GPU is a brigade of 10,000 line cooks who can only all chop the same vegetable at the same time.

---

## 1. CPU vs RAM (the starting question)

The CPU *does* the work, and RAM *holds* the work while it's being done. A faster chef finishes each dish sooner. A bigger counter lets you lay out more ingredients and dishes at the same time without running to the storeroom (the disk).

| | CPU (processor) | RAM (memory) |
|---|---|---|
| **Job** | Runs instructions: math, logic, comparisons, moving data | Temporarily stores the code and data the CPU is working on |
| **Measured in** | Cores, clock speed (GHz), IPC, cache size | Capacity (GB), speed (MT/s), latency |
| **Speed** | Fastest part. Registers and L1 cache take about 1 ns | About 60–100 ns per access, roughly 100× slower than L1 |
| **When it's not enough** | Tasks take longer, and usage shows 100% | The system starts **swapping** to disk and suddenly slows to a crawl, or the OOM killer stops processes |
| **Volatile?** | Yes (registers and cache) | Yes. It's wiped when the power goes off |
| **Linux check** | `top`, `htop`, `mpstat`, `uptime` (load avg) | `free -h`, `vmstat`, `/proc/meminfo` |

They are linked through the **memory hierarchy**: registers → L1/L2/L3 cache (inside the CPU) → RAM → SSD/disk. The CPU can only work on data it has pulled up into its caches. So a program can be "slow" even when the CPU isn't busy, because the CPU is waiting on RAM. This is called being **memory-bound**.

### Which kinds of software depend on which

**CPU-bound** (more or faster cores help most):
- Compiling code (`make -j`, `cargo build`)
- Video and audio encoding (`ffmpeg`, Handbrake)
- Compression and encryption (`zstd`, `gpg`, TLS on busy servers)
- Password cracking on the CPU (`john`), hashing
- Physics, simulations, scientific number-crunching
- Game logic, and game frame rates at low resolution

**RAM-bound** (more GB or faster memory helps most):
- Virtual machines and containers. Each VM reserves its own block of RAM.
- Databases and caches (PostgreSQL buffer pool, Redis, Elasticsearch)
- Browsers with many tabs, Electron apps
- Big data and analytics (pandas DataFrames, Spark)
- Running LLMs locally: the model weights have to fit in RAM or VRAM
- Large photo, video and 3D projects (Photoshop layers, video-editing timelines)

**Both** (balanced):
- Video editing: encoding uses the CPU, the timeline uses RAM
- Gaming: game logic uses the CPU, textures and assets use RAM/VRAM
- Kubernetes nodes, CI runners, IDEs indexing large codebases

**Neither** (other parts are the bottleneck):
- File copying, booting, package installs → **disk I/O**
- Downloads, scanners like `nmap`/`arp-scan`, web APIs → **network I/O**
- Deep-learning training, 3D rendering, `hashcat` → **GPU**

### Quick rule of thumb
- If your CPU is pinned at 100% and RAM has room, you're **CPU-bound**. Get more or faster cores, or parallelize.
- If RAM is full and swap is growing (watch `si`/`so` in `vmstat 1`), you're **RAM-bound**. Add memory or reduce the working set.
- If both look idle but things are still slow, check disk (`iostat`) or network.
- For everyday use, running out of RAM usually *feels* worse than having a slow CPU. A slow CPU makes everything a bit slower, but swapping can make everything about 1000× slower.

---

## 2. The five resources at a glance

| Resource | What it does | Its unit of "more" | Typical speed | Signs it's the bottleneck | Linux tools |
|---|---|---|---|---|---|
| **CPU** | Runs general-purpose instructions: logic, branching, math | Cores, GHz, IPC, cache | ~1 ns per operation | 100% usage, high load average, fans spinning | `htop`, `mpstat`, `perf` |
| **RAM** | Holds the working data and code | GB, MT/s bandwidth | ~100 ns | Swap usage, OOM kills, sudden freezes | `free -h`, `vmstat 1`, `smem` |
| **GPU** | Runs thousands of simple maths operations in parallel | CUDA/stream cores, VRAM, TFLOPS | Very high throughput, but slow to start each job | Shown in `nvidia-smi` as 100% util or VRAM full | `nvidia-smi`, `nvtop`, `radeontop` |
| **Disk I/O** | Persistent storage: reads and writes | IOPS, MB/s, latency | NVMe ~20–100 µs, HDD ~5–10 ms | High `iowait`, processes stuck in `D` state | `iostat -x`, `iotop`, `fio` |
| **Network I/O** | Moves data between machines | Bandwidth (Gbps), latency, packets per second | LAN ~0.1 ms, Internet 10–300 ms | Retransmits, dropped packets, saturated links, timeouts | `iftop`, `nload`, `ss`, `sar -n DEV` |

### The latency ladder (the key mental model)

Each step is 100 to 1,000,000 times slower than the one before:

```
Register/L1 (1 ns) → RAM (100 ns) → NVMe (50 µs) → LAN (0.5 ms) → HDD (8 ms) → Internet (100 ms)
```

Most performance engineering comes down to keeping data as high on this ladder as possible (caching, buffering, batching, locality).

### How to watch all five at once (Linux)

```bash
htop                 # CPU per core, RAM, swap, load average
vmstat 1             # r (run queue), si/so (swap in/out), wa (iowait)
iostat -x 1          # per-disk %util, await (latency), r/s w/s
nvidia-smi -l 1      # GPU util %, VRAM used, power, temperature
iftop -i eth0        # per-connection bandwidth
ss -s                # socket summary (connection counts)
sar -n DEV 1         # per-interface packets & bytes per second
```

Key fields:
- `vmstat` **r**: runnable threads. Consistently > core count means CPU saturation.
- `vmstat` **si/so**: pages swapped in/out per second. Anything sustained above 0 means RAM pressure.
- `vmstat` / `top` **wa**: % of time the CPU sat idle waiting on I/O. High means disk-bound (or NFS/network storage).
- `iostat` **%util** near 100% on an HDD means saturated. On NVMe it's misleading, because the drive serves many requests in parallel, so look at **await** and queue size instead.
- `top` process state **D**: uninterruptible sleep, almost always waiting on disk or network filesystem.

---

## 3. Role lens

### Software engineer / developer

| Resource | What loads it | How much it matters |
|---|---|---|
| **CPU** | Compiling (`make -j`, `cargo`, `gradle`), test suites, IDE indexing, linting, Docker builds | ⭐⭐⭐⭐⭐ |
| **RAM** | IDE + browser + Docker + multiple containers + a local DB + Slack/Electron apps all running at once | ⭐⭐⭐⭐⭐ (32 GB is a comfortable baseline now) |
| **GPU** | Only for ML/AI work, game dev, graphics, or running local LLMs | ⭐ (⭐⭐⭐⭐⭐ for ML devs) |
| **Disk** | `node_modules`, `git` operations, Docker image layers, builds with many small files | ⭐⭐⭐⭐ (NVMe makes a big difference) |
| **Network** | `git clone`, package installs, pulling container images, calls to cloud APIs | ⭐⭐ locally, ⭐⭐⭐⭐⭐ for backend/distributed systems |

**What experienced developers know:** in production, most web apps are **I/O-bound** (waiting on the database and network), not CPU-bound. That's why async frameworks like Node, Go, asyncio and Tokio exist. Profile before you optimise.

### Red team (offensive / pentester)

| Resource | What loads it | How much it matters |
|---|---|---|
| **CPU** | Exploit compilation, `john` (CPU cracking), fuzzing (AFL++, libFuzzer), payload encoding | ⭐⭐⭐⭐ (fuzzing uses all available cores) |
| **RAM** | Running multiple attack VMs (Kali, Windows targets, AD lab), BloodHound/Neo4j graphs, Burp Suite with large project files | ⭐⭐⭐⭐⭐ (home labs eat RAM) |
| **GPU** | `hashcat` cracking NTLM, WPA2, Kerberos tickets (Kerberoasting). A GPU is 100–1000× faster than a CPU for this | ⭐⭐⭐⭐⭐ for password attacks |
| **Disk** | Wordlists (rockyou is ~130 MB; other lists can be 100s of GB), rainbow tables, VM snapshots | ⭐⭐⭐ |
| **Network** | `nmap`, `masscan`, `arp-scan`, `gobuster`/`ffuf`, C2 traffic, exfiltration | ⭐⭐⭐⭐⭐ (scanning is latency-bound) |

**What experienced red teamers know:** scan speed is usually limited by **network latency and the target's rate limits/IDS**, not by your CPU. `masscan` can send millions of packets per second, but doing that gets you caught and can knock fragile targets over. Being stealthy means using resources *deliberately slowly*.

### Blue team (defensive / SOC / DFIR)

| Resource | What loads it | How much it matters |
|---|---|---|
| **CPU** | SIEM queries, YARA scans, Suricata/Snort rule matching, log parsing | ⭐⭐⭐⭐⭐ (IDS on fast links is CPU-hungry) |
| **RAM** | Elasticsearch/Splunk indexes, memory forensics (Volatility needs room for the RAM dump), sandbox VMs | ⭐⭐⭐⭐⭐ |
| **GPU** | Rarely needed. Some ML anomaly detection and password-audit cracking | ⭐ |
| **Disk** | Log retention (TBs per day at scale), packet capture (Zeek/Arkime write full PCAP), disk images for forensics | ⭐⭐⭐⭐⭐ (throughput *and* capacity) |
| **Network** | Taps/SPAN ports, NetFlow, IDS sensors that must keep up with line rate without dropping packets | ⭐⭐⭐⭐⭐ |

**What experienced blue teamers know:** an IDS that **drops packets under load is blind exactly when an attack is happening**, because attacks often cause traffic spikes. Sensors need sizing for peak load, not average. Tools like PF_RING, AF_PACKET fanout and DPDK spread packet capture across cores.

### Cybersecurity experts more broadly (malware analysts, researchers, architects)

| Resource | What loads it |
|---|---|
| **CPU** | Disassembly/decompilation (Ghidra, IDA analysis passes), symbolic execution (angr), emulation |
| **RAM** | Ghidra on large binaries, multiple sandbox VMs, memory forensics |
| **GPU** | AI-assisted analysis, crypto research, cracking audits |
| **Disk** | Malware sample collections, VM snapshot rollback (fast NVMe means fast reverts) |
| **Network** | Isolated lab networks, traffic capture, threat-intel feeds |

### The five resources as attack surfaces

| Resource | Attacks / abuse |
|---|---|
| **CPU** | Spectre/Meltdown (speculative execution side channels), cryptojacking |
| **RAM** | Rowhammer, cold-boot attacks, credential dumping (Mimikatz reading LSASS memory) |
| **GPU** | GPU-resident malware, leftover data in VRAM, cracking power |
| **Disk** | Ransomware (disk I/O spikes are a detection signal), data remanence |
| **Network** | DDoS (network/CPU resource exhaustion), exfiltration, MITM |

For security, availability is a resource problem: DoS, cryptojacking and ransomware are all about exhausting or abusing these five resources, and resource monitoring is one of the cheapest detection signals a blue team has.

---

## 4. Cores and threads

### Terms

| Term | Meaning |
|---|---|
| **Physical core** | An independent execution unit with its own ALUs and L1/L2 cache |
| **Hardware thread (SMT / Hyper-Threading)** | One core shows itself to the OS as 2 logical CPUs. They share the core's execution units, so the second thread gives roughly **+15–30%**, not 2× |
| **Software thread** | An OS-scheduled stream of execution. You can have thousands of them on a 4-core machine; they take turns |
| **Process vs thread** | Processes have separate memory. Threads share memory, which makes communication cheaper but bugs (race conditions) easier |
| **Async / event loop** | One thread handles thousands of tasks by never waiting. It switches to another task when one is blocked on I/O |

Check with `lscpu`, `nproc`, `cat /proc/cpuinfo`. "Thread(s) per core: 2" means SMT is on.

### How each resource depends on cores and threads

#### 1. CPU: scales directly, with limits
- More cores help **only if the work can be split**. `make -j16` scales well. A single-threaded Python script uses one core however many you have.
- **Amdahl's law**: if 10% of a job is serial, the maximum speedup is 10× even with infinite cores.
- SMT threads help when one thread stalls (waiting on memory) and the other can use the idle units. They help little when both threads compete for the same units.
- **Practical rule:** for CPU-bound work, threads ≈ physical cores (or logical cores). More than that just adds context-switching overhead.

#### 2. RAM: more threads use more of it and compete for it
- **Capacity:** each thread has its own stack (default 8 MB virtual on Linux), and each worker process (e.g. Apache prefork, Chrome tabs) duplicates data. 64 workers can mean 64× the memory.
- **Bandwidth:** all cores share the memory channels. Beyond a certain number of cores, memory-heavy workloads stop scaling. This is the **memory wall**.
- **NUMA:** on multi-socket servers, each CPU has "its own" RAM, and reaching the other socket's RAM is slower. Pinning threads to the right node matters (`numactl`).
- **Cache contention:** threads on the same core share L1/L2, so two SMT threads can evict each other's data.
- **Security note:** threads share address space. A memory bug in one thread can corrupt or leak the whole process.

#### 3. GPU: a completely different model of "cores"
- A GPU has **thousands of small cores** (e.g. ~10,000+ CUDA cores on high-end cards), grouped into SMs/CUs. They run threads in lockstep groups of 32 (NVIDIA *warps*) or 32/64 (AMD *wavefronts*).
- GPU "cores" are **not comparable** to CPU cores. Each is simple, with no branch prediction to speak of and poor handling of `if/else` (divergent branches serialise the warp). They're ideal for "do the same maths on a million items", such as hashing candidate passwords, matrix multiplication and pixels.
- The GPU depends on **CPU threads to feed it**. A weak CPU or a single feeding thread can leave the GPU idle. **PCIe transfer** between RAM and VRAM is often the real bottleneck.
- `hashcat` exposes this tradeoff with its workload profile `-w 1..4`.

#### 4. Disk I/O: depends on threads for queue depth, not compute
- An HDD has one read/write head, so many threads competing for it cause **seek thrashing** and make it slower.
- NVMe SSDs have up to 64K queues × 64K commands, and Linux gives roughly **one queue per CPU core** (`blk-mq`). A single thread doing synchronous I/O can't reach NVMe's rated speed. You need **many threads or async I/O** (`io_uring`, `libaio`) to keep the queue full.
- Example: `fio --iodepth=1` vs `--iodepth=32` on NVMe can differ by 5–10×.
- Threads waiting on disk show up as **`iowait`**. The CPU isn't busy; it's waiting.

#### 5. Network I/O: latency hidden by concurrency, packets spread across cores
- **Latency-bound work** (scanning, HTTP requests, DNS lookups) benefits enormously from concurrency, because each request mostly *waits*. That's why `ffuf -t 50` and `nmap --min-parallelism` make such a difference even on a 2-core laptop. Async I/O (epoll, as used by nginx and masscan) handles thousands of connections in very few threads.
- **High-throughput work** (10/40/100 Gbps): a single core can't process every packet. Multi-queue NICs use **RSS** (Receive Side Scaling) to hash flows to different cores, and each queue gets its own IRQ on its own core. Check with `ethtool -l eth0` and `/proc/interrupts`.
- **The C10K problem:** thread-per-connection breaks down at around 10,000 connections because of memory and context switching. The solution is event-driven design. This is why nginx beat Apache prefork on concurrency.

### Summary: cores and threads × resources

| Resource | More **cores** help? | More **threads** help? | Best concurrency model |
|---|---|---|---|
| **CPU** | ✅ Yes, if the work parallelises (Amdahl) | ✅ Up to the core count, then ❌ | Thread pool ≈ number of cores |
| **RAM** | ⚠️ Not directly. More cores means more competition for bandwidth | ❌ Each thread uses memory | Fewer threads, shared data, NUMA-aware |
| **GPU** | ✅ GPU cores do the work. CPU cores just feed it | ✅ Massive (thousands, in warps) | SIMT kernels + async transfers |
| **Disk** | ⚠️ NVMe uses per-core queues | ✅ for NVMe (queue depth), ❌ for HDD | Async I/O (`io_uring`) or a moderate thread pool |
| **Network** | ✅ for high packet rates (RSS) | ✅✅ for latency-bound work | Event loop/async, multi-queue NIC |

---

## 5. Comparative analysis

### Head-to-head

| Dimension | CPU | RAM | GPU | Disk | Network |
|---|---|---|---|---|---|
| **Latency** | ~1 ns | ~100 ns | µs to start a job, then very fast | 20 µs (NVMe) – 10 ms (HDD) | 0.1 ms (LAN) – 300 ms (WAN) |
| **Good at** | Complex, branchy, serial logic | Fast random access | Massive simple parallelism | Persistence, capacity | Distance, sharing |
| **Bad at** | Massively parallel maths | Persistence, capacity per $ | Branching, small tasks | Random small I/O (HDD) | Latency; you don't control it |
| **When exhausted** | Slows down gradually | **Falls off a cliff** (swap/OOM) | Job fails or queues | Everything stalls (`D` state) | Timeouts, retransmits, drops |
| **Cheapest to upgrade?** | Expensive (often means a new board) | **Cheapest, biggest effect** | Expensive | Cheap (NVMe) | Depends on ISP/infrastructure |
| **Scales by** | Cores × IPC × GHz | Capacity + channels | Cores + VRAM | Parallel queues, RAID | Links, NIC queues, CDNs |
| **Biggest security risk** | Side channels, cryptojacking | Credential dumping, Rowhammer | Cracking power | Ransomware, data remanence | DDoS, exfiltration, MITM |

### Which role is most limited by which resource (🔴 = main bottleneck)

| Role | CPU | RAM | GPU | Disk | Network |
|---|---|---|---|---|---|
| Developer (general) | 🔴 High | 🔴 High | Low | Medium | Medium |
| Backend/distributed dev | Medium | High | Low | High | 🔴 High |
| ML/AI developer | Medium | High | 🔴 Critical | High | Medium |
| Red team (scanning/web) | Low | Medium | Low | Low | 🔴 Critical |
| Red team (cracking) | Medium | Low | 🔴 Critical | Medium (wordlists) | Low |
| Red team (labs/AD) | Medium | 🔴 Critical | Low | High | Medium |
| Blue team (SOC/SIEM) | High | 🔴 Critical | Low | 🔴 Critical | High |
| Blue team (IDS/NSM) | 🔴 Critical | High | Low | High (PCAP) | 🔴 Critical |
| DFIR / malware analyst | High | 🔴 Critical | Low | High | Low |

### Takeaways

1. **Find the bottleneck before upgrading.** Whichever resource is saturated sets the speed, and improving the others does nothing (*theory of constraints*). Use `htop` + `vmstat 1` + `iostat -x 1` + `nvidia-smi` + `iftop` together.
2. **RAM is the most common real-world limit** for developers and security labs, because modern workflows run many VMs, containers and Electron apps at the same time.
3. **The GPU is a specialist.** Essential for ML and password cracking, nearly useless otherwise.
4. **For I/O (disk and network), more threads or async is the answer, not more GHz.** For compute (CPU), more cores is the answer only if the code parallelises.
5. **Cores ≠ threads ≠ speed.** 8 cores with SMT = 16 logical CPUs ≈ 9–10 cores' worth of real throughput. A thousand software threads on those still give you only that much compute; they help only when most of them are *waiting*.
6. **For security, availability is a resource problem.** DoS, cryptojacking and ransomware all exhaust or abuse these five resources.

**Sensible all-round workstation (2026)** for these roles: 8–16 core CPU, **32–64 GB RAM**, NVMe SSD, a mid-range NVIDIA GPU if you crack hashes or do ML, and a wired gigabit+ connection for lab and scanning work.

---

## 6. History & key people

| Year | Person | Contribution | Why it matters here |
|---|---|---|---|
| 1945 | John von Neumann | *First Draft of a Report on the EDVAC*: stored-program design with the CPU separate from memory | The origin of the CPU vs RAM split, and of the "von Neumann bottleneck" that caches and the memory hierarchy work around |
| 1967 | Gene Amdahl | Amdahl's law (AFIPS paper) | Caps the speedup from more cores by the serial fraction of the work |
| 1999 | Dan Kegel | *The C10K problem* | Why thread-per-connection fails and network I/O needs event loops (epoll, kqueue) |
| 2000s–2010s | Brendan Gregg | USE method, flame graphs, *Systems Performance* | A checklist for finding which of the five resources is the bottleneck |
| 2013 / 2019 | Jens Axboe | blk-mq (multi-queue block layer), io_uring, fio | Why NVMe needs deep queues and async I/O to reach its rated speed |

---

## 7. Related topics

- **Computer architecture:** memory hierarchy, caches, pipelining, speculative execution, SIMD/SIMT, PCIe, NUMA
- **Operating systems:** scheduling, context switches, virtual memory, paging/swap, OOM killer, block layer (`blk-mq`), interrupts/IRQ affinity, `io_uring`, epoll
- **Performance engineering:** Amdahl's law, Gustafson's law, USE method (Utilization, Saturation, Errors, by Brendan Gregg), theory of constraints, profiling (`perf`, flame graphs)
- **Concurrency:** threads vs processes vs async, race conditions, C10K/C10M
- **Security:** side channels (Spectre/Meltdown), Rowhammer, memory forensics, DoS/DDoS, cryptojacking detection, IDS sizing
- **Related library entries:** `time` (wall vs user vs sys, peak RSS), `arp-scan` (latency-bound network I/O)
- **Certifications / curricula where this comes up:** CompTIA A+ (hardware), Linux+/LFCS/RHCSA (performance monitoring), Security+/CySA+ (DoS, resource-based detection), OSCP (cracking/scanning performance), GCFA/GCIH (memory forensics), CS courses in computer organisation and OS

---

## 8. Q&A from the session

### Q1: How is the CPU different from RAM, and which types of software depend on which most?
See section 1.

### Q2: Give an overview of all five (CPU, RAM, GPU, disk I/O, network I/O) for software engineers, developers, red and blue team, and cybersecurity experts. Explain the dependency of those five on cores and threads, and give an overall comparative analysis.
See sections 2 (overview), 3 (role lens), 4 (cores and threads) and 5 (comparative analysis).

---

## Sources

Conceptual material from standard references; no live web sources were cited in the session. Good references for further reading:
- Brendan Gregg, *Systems Performance* (2nd ed.) and the USE Method — https://www.brendangregg.com/usemethod.html
- "Latency numbers every programmer should know" (Jeff Dean / Peter Norvig) — https://gist.github.com/jboner/2841832
- Linux `vmstat(8)`, `iostat(1)`, `lscpu(1)`, `numactl(8)`, `ethtool(8)` man pages — https://man7.org/linux/man-pages/
- Linux kernel docs: Scaling in the Linux Networking Stack (RSS/RPS) — https://docs.kernel.org/networking/scaling.html
- Linux kernel docs: Multi-Queue Block IO (blk-mq) — https://docs.kernel.org/block/blk-mq.html
- Dan Kegel, *The C10K problem* — http://www.kegel.com/c10k.html
- NVIDIA CUDA C++ Programming Guide (SIMT, warps) — https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- Brendan Gregg, "Why I joined OpenAI" (7 Feb 2026) — https://www.brendangregg.com/blog/2026-02-07/why-i-joined-openai.html
- Jens Axboe, "Efficient IO with io_uring" (2019) — https://kernel.dk/io_uring.pdf
- Jens Axboe — https://en.wikipedia.org/wiki/Jens_Axboe
