---
tool: time
date: 2026-11-17
domains: [Unix/Linux CLI, Performance engineering, Shell scripting, Systems programming, HPC/benchmarking]
roles: [Linux System Administrator, Performance / SRE, Software Developer / Systems Programmer, Shell Scripting / DevOps Engineer, HPC / Research Computing Engineer, Cybersecurity Analyst / Pentester, Data Engineer, CS Student / Educator]
scope: every major type of Linux system (Debian/Ubuntu, Fedora/RHEL, Arch, openSUSE, Gentoo/Void/NixOS, Alpine, OpenWrt/embedded, Android, distroless containers), compared with BSD/macOS/Windows
tags: [time, gnu-time, bash, busybox, toybox, zsh, mksh, getrusage, wait4, rusage, max-rss, benchmarking, hyperfine, cgroups]
---

# time

## Summary

`time` runs a command and reports how long it took (wall-clock **real**, user-mode CPU **user**, kernel-mode CPU **sys**). GNU time also reports peak memory (max RSS), page faults, block I/O, context switches and the exit status.

On Linux the name hides **3 to 6 different implementations**, depending on your shell, your distro and how you call it:

```
$ type -a time
time is a shell keyword        ← bash's built-in (wins by default)
time is /usr/bin/time          ← GNU time binary (only if the "time" package is installed)
```

GNU's own page warns that the shell's built-in usually takes precedence. Check with `type`, and force the binary with `env time`, `command time`, `\time` or `/usr/bin/time`.

Reading the result:
- `real > user + sys`: the process **waited** (disk, network, locks, sleep, scheduler).
- `user + sys > real`: it **ran in parallel** across several CPUs.

---

## Usage & commands

### Install / availability by Linux system type

| Linux system type | Interactive shell's `time` | `/bin/sh` scripts get… | Binary by default | Install GNU time |
|---|---|---|---|---|
| Debian / Ubuntu / Mint | bash keyword | dash has **no keyword**, so a `#!/bin/sh` script runs `/usr/bin/time`, or fails with "not found" if the package is missing | GNU 1.9 (package `time`); **absent in minimal/cloud/Docker images** (the Ubuntu 24.04 image I tested had none) | `apt install time` |
| Fedora / RHEL / Rocky / Alma / Amazon Linux | bash keyword | bash in POSIX mode: still a keyword, except `time -<flag>` goes to the binary | GNU (package `time`), often absent in minimal installs | `dnf install time` |
| Arch / Manjaro | bash keyword | bash | GNU, separate package | `pacman -S time` |
| openSUSE / SLES | bash keyword | bash | GNU | `zypper in time` |
| Gentoo / Void / NixOS | bash keyword | depends | GNU | `emerge sys-process/time` / `xbps-install time` / `nix-shell -p time` |
| Alpine (most Docker bases) | BusyBox ash (**no keyword**) | ash | **BusyBox `time` applet** (has `-v`; ×4 RSS bug in 1.36) | `apk add time` |
| OpenWrt / embedded / initramfs | BusyBox ash | ash | BusyBox applet, only if compiled in (`CONFIG_TIME`, default y) | usually not available |
| Android (`adb shell`) | mksh keyword | mksh | **toybox `time`** (only `-p -v`) | n/a |
| Distroless / scratch containers | no shell | none | none | copy in a static binary or measure from outside |
| zsh / fish / tcsh users | the shell's own keyword/builtin with its own format | none | none | none |

Android background: the shell has been mksh since Ice Cream Sandwich, and nearly all tools have come from toybox since Marshmallow. Alpine projects that need GNU flags install the separate package (for example, charliecloud's Alpine test image runs `apk add coreutils diffutils findutils grep sed time util-linux`).

### The 10 most useful operations

| # | Command | What you get |
|---|---|---|
| 1 | `time cmd` | real/user/sys from the shell keyword; works for functions, builtins, pipelines |
| 2 | `time -p cmd` | POSIX format (`real 0.31` / `user 0.21` / `sys 0.10`), the only format that's the same everywhere |
| 3 | `TIMEFORMAT='%3R'; time cmd` | bash: just elapsed seconds with ms precision |
| 4 | `/usr/bin/time -v cmd` | full rusage report |
| 5 | `/usr/bin/time -f '%e %M %x' cmd` | custom fields: elapsed, max RSS KB, exit code |
| 6 | `/usr/bin/time -o log -a -f '…' cmd` | append stats to a file, so the program's stderr stays clean |
| 7 | `command time …` / `env time …` / `\time …` | force the binary without the full path |
| 8 | `{ time cmd; } 2> t.txt` | capture the keyword's output |
| 9 | `/usr/bin/time -q cmd` | suppress "Command exited with non-zero status" |
| 10 | bare `time` (bash POSIX mode) | cumulative user/sys of the shell and its children |

### Same workload, every implementation (real output; Ubuntu 24.04, bash 5.2.21, GNU time 1.9, BusyBox 1.36.1, toybox 0.8.9)

Workload: a Python script that allocates and touches 200 MB, then loops for CPU.

```
=== bash keyword
real	0m0.385s
user	0m0.229s
sys	0m0.132s

=== bash time -p
real 0.31
user 0.21
sys 0.10

=== bash TIMEFORMAT="%3R real %3U user %3S sys %P%%"
0.382 real 0.280 user 0.099 sys 99.22%

=== GNU time 1.9 default
0.20user 0.09system 0:00.30elapsed 99%CPU (0avgtext+0avgdata 215512maxresident)k
0inputs+0outputs (0major+52202minor)pagefaults 0swaps

=== GNU -f "%e s elapsed | %M KB maxrss | %x exit"
0.32 s elapsed | 215536 KB maxrss | 0 exit

=== GNU -p
real 0.31
user 0.21
sys 0.09

=== dash -c 'time …'   (no keyword, so it silently ran /usr/bin/time)
0.21user 0.09system 0:00.31elapsed 99%CPU (0avgtext+0avgdata 215528maxresident)k
0inputs+0outputs (0major+52203minor)pagefaults 0swaps

=== zsh
python3 /tmp/w.py  0.22s user 0.11s system 98% cpu 0.342 total

=== zsh TIMEFMT="%E real %U user %S sys %P cpu %M max"
0.35s real 0.25s user 0.10s sys 99% cpu 210 max        ← %M is MEGABYTES in zsh

=== mksh
    0m00.30s real     0m00.19s user     0m00.10s system

=== BusyBox 1.36.1 time
real	0m 0.32s
user	0m 0.21s
sys	0m 0.08s

=== BusyBox 1.36.1 time -v  (excerpt)
	Maximum resident set size (kbytes): 862000      ← 4 × the real 215,492
```

GNU `-v` (full):

```
	Command being timed: "python3 /tmp/w.py"
	User time (seconds): 0.18
	System time (seconds): 0.10
	Percent of CPU this job got: 98%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:00.29
	Average shared text size (kbytes): 0
	Average unshared data size (kbytes): 0
	Average stack size (kbytes): 0
	Average total size (kbytes): 0
	Maximum resident set size (kbytes): 215492
	Average resident set size (kbytes): 0
	Major (requiring I/O) page faults: 0
	Minor (reclaiming a frame) page faults: 52202
	Voluntary context switches: 1
	Involuntary context switches: 0
	Swaps: 0
	File system inputs: 0
	File system outputs: 0
	Socket messages sent: 0
	Socket messages received: 0
	Signals delivered: 0
	Page size (bytes): 4096
	Exit status: 0
```

toybox 0.8.9 (`-v`, different workload: 50 MB touch):

```
Real time (s): 0.041521
User time (s): 0.011296
System time (s): 0.029808
Max RSS (KiB): 62068
Major faults: 0
Minor faults: 13782
File system inputs: 0
File system outputs: 0
Voluntary context switches: 1
Involuntary context switches: 1
```

### Keyword vs binary behaviour (tested)

```
# pipeline: keyword times the whole pipeline, binary only the first stage
bash -c 'time (sleep 0.3 | sleep 0.5)'        → real 0m0.502s
bash -c '/usr/bin/time sleep 0.3 | sleep 0.5' → 0:00.30elapsed

# functions/builtins
bash -c 'f(){ for i in $(seq 200000); do :; done; }; time f'  → real 0.220 user 0.194
bash -c 'f(){ :; }; /usr/bin/time f'  → /usr/bin/time: cannot run f: No such file or directory (status 127)

# redirection
bash -c 'time sleep 0.1 2>/dev/null'       → timing STILL printed
bash -c '{ time sleep 0.1; } 2>/tmp/t.txt' → timing captured in file

# bash POSIX mode
bash --posix -c 'time -p sleep 0.1'   → real 0.10 / user 0.00 / sys 0.00
bash --posix -c 'sleep 0.2; time'     → user 0m0.00s / sys 0m0.00s (shell+children cumulative)

# exit status passthrough (GNU 1.9)
/usr/bin/time false        → "Command exited with non-zero status 1", rc=1
/usr/bin/time -q false     → no status line, rc=1
/usr/bin/time nonexist     → "cannot run nonexist", rc=127
/usr/bin/time sh -c 'kill -9 $$' → "Command terminated by signal 9", rc=137

# shell type checks
zsh: time is a reserved word | dash: time is /usr/bin/time
mksh: time is a reserved word | busybox sh: time is /usr/bin/time
```

### One realistic task, start to finish: OOM-killed nightly ETL container

```bash
# 1. Get the real binary (minimal images often lack it)
apt-get install -y time        # Debian/Ubuntu
apk add time                   # Alpine; avoid busybox time for %M (×4 bug in 1.36)

# 2. Log one CSV-friendly line per run, keeping the job's stderr clean
/usr/bin/time -o /var/log/etl.time -a \
  -f "$(date -Is),%e,%U,%S,%P,%M,%F,%R,%w,%c,%I,%O,%x" \
  python3 etl.py --date 2026-11-16

# 3. Read it
tail -1 /var/log/etl.time
# 2026-11-17T02:00:03+05:30,412.88,61.20,9.40,17%,1843212,12,480211,90311,402,8123400,220,0
```

Interpretation (illustrative numbers):
- `%e=412.88` vs `%U+%S=70.6`, `%P=17%`: 83% of the time is **waiting**.
- `%w=90311` voluntary switches + `%I=8,123,400` blocks in: **disk-I/O-bound**. Faster storage, bigger reads or parallel I/O will help; more CPU won't.
- `%M=1843212` KB ≈ 1.76 GiB peak (largest single process), so set the container limit around 2.2–2.5 GiB.
- If the job forks workers, `%M` is the largest worker, not the total. Use the cgroup `memory.peak` / `systemd-run` for the whole tree.

---

## Output / fields explained

| Field (GNU `-f` code) | Meaning | Source | When it changes / pitfalls |
|---|---|---|---|
| real / elapsed (`%e`, `%E`) | wall-clock time from start to exit | clock before fork, after wait | includes I/O waits, sleep, scheduler delay |
| user (`%U`) | CPU time in the program's own code | `ru_utime` from `wait4()` | sums all threads and children, so it can exceed real |
| sys / system (`%S`) | CPU time in the kernel on its behalf | `ru_stime` | high means many syscalls, small I/O, page faults |
| %CPU (`%P`) | (user+sys)/real | computed | <100% waited; >100% parallel. GNU 1.9 fixed `??%` for runs under 1 s |
| maxresident (`%M`) | peak RSS of the **largest single process** | `ru_maxrss` (KB on Linux) | not the sum of a process tree |
| avgtext/avgdata (`%X %D %K %p %t`) | average memory sizes | `ru_ixrss` etc. | **always 0 on Linux** (unmaintained kernel fields) |
| major faults (`%F`) | faults that needed disk I/O | `ru_majflt` | cold cache / memory pressure |
| minor faults (`%R`) | faults satisfied without I/O | `ru_minflt` | 52,202 × 4 KB ≈ 204 MB = the 200 MB buffer touched for the first time |
| inputs / outputs (`%I %O`) | block I/O operations | `ru_inblock` / `ru_oublock` | real disk I/O only, not page-cache hits (first `false` run showed 56 inputs cold, then 0) |
| swaps (`%W`) | swap-outs | `ru_nswap` | always 0 on Linux |
| voluntary ctx switches (`%w`) | the process gave up the CPU (I/O, lock, sleep) | `ru_nvcsw` | high means I/O-bound or lock contention |
| involuntary ctx switches (`%c`) | the process was preempted | `ru_nivcsw` | high means CPU contention, noisy neighbours, CFS throttling |
| socket msgs (`%r %s`) | messages sent/received | rusage | 0 on Linux |
| exit status (`%x`) | child's exit code | `wait4` status | 127 not found, 128+N killed by signal; codes standardised in GNU 1.8 (125 usage, 126 can't exec, 127 not found) |

### bash `TIMEFORMAT`
`%R` real, `%U` user, `%S` sys, `%P` CPU percent; an optional precision digit (`%3R`) and `l` for the long form (`%lR` = `0m0.385s`). The default is `$'\nreal\t%3lR\nuser\t%3lU\nsys\t%3lS'`. The variable is read by the **keyword**, so `TIMEFORMAT=x time cmd` (assignment prefix) bypasses the keyword and runs the binary.

### zsh `TIMEFMT`
Contains `%E %U %S %P` plus memory, I/O and fault fields. In my test `%M` printed `210` for a ≈215,000 KB peak, i.e. **megabytes**. Note the unit mismatch with GNU's KB.

---

## History & evolution

- **1971, Unix First Edition:** `tm` with arguments ran a command and reported its times; with no arguments it showed time since boot and since the last `tm`. Categories: real ("tim"), system overhead ("ovh"), disk wait ("dsk"), idle ("idl"), user ("usr"), plus an RK disk error count.
- **1973, Version 3 AT&T Unix:** the `time` utility appears (per the macOS/BSD man page HISTORY section).
- **V7 era:** elapsed time accurate to 1 s, CPU times to 1/60 s, so the CPU sum could exceed elapsed by up to a second.
- **csh** made `time` a builtin with its own format (`8.9u 7.0s 0:29 54%`); BSD man pages tell csh users to call `/bin/time`. **ksh** made it a pipeline reserved word; POSIX worded `time` so that it can be either a standalone utility or a shell reserved word. Austin Group issue 267 still debates how a reserved-word `time` should treat stderr redirection.
- **4.2BSD** added `getrusage` / `wait3` / `wait4` and `struct rusage`; GNU time reads `wait3`, with `times` as a fallback.
- **1990:** David Keppel writes GNU time (FSF copyright 1990–96); David MacKenzie heavily modifies it.
- **1996:** GNU time 1.7, then **no release for 21 years**. Distros carried their own patches (e.g. Debian's `ru_maxrss.patch`). The ×4 max-RSS bug was reported to LKML and Red Hat in 2012 (cause: `ptok()` converting Linux's already-KB `ru_maxrss` as if it were pages).
- **2013:** Rob Landley writes toybox `time` (initially `-p` only).
- **Nov 2017:** GNU time 1.8 (Assaf Gordon): gnulib, downstream patches merged, GPLv3+, `-q/--quiet`, coreutils-style exit codes. Same month: Elliott Hughes adds `time -v` to toybox.
- **Mar 2018:** GNU time 1.9: CPU% for runs under 1 s (previously `??%`); `-p` no longer adds the "Command exited…" line. Still the current release; Ubuntu 24.04 ships `1.9-0.2build1`, which reports its version as `UNKNOWN`.
- **2022:** Linux 5.19 adds cgroup v2 `memory.peak`. **2023:** systemd-run prints "Memory peak" next to "CPU time consumed", effectively `time` for a whole cgroup (requested on systemd-devel as "systemd-time" back in 2013).

---

## How it works internally

### External binaries (GNU / BusyBox / toybox)

```
clock_start = now()                 # GNU: gettimeofday; toybox: CLOCK_MONOTONIC
pid = fork()
child:  execvp(cmd, args)           # must be a real file: no functions/builtins/aliases
parent: ignore SIGINT/SIGQUIT; wait4(pid, &status, 0, &rusage)
clock_end = now()
format fields from rusage + elapsed, write to stderr (or -o file)
exit with child's status
```

### Bash keyword

Recognised by the **parser**, not looked up in PATH. It wraps the whole pipeline, takes `getrusage(RUSAGE_SELF)` + `getrusage(RUSAGE_CHILDREN)` snapshots and a wall-clock reading before and after, and prints the differences in `TIMEFORMAT`. Because it includes the shell's own time, it can time builtins and functions that never fork.
- *Certain (documented):* keyword/pipeline behaviour, timing of builtins/functions/pipelines, assignment prefix disabling it (Chet Ramey), POSIX-mode `-` rule.
- *Inferred:* the exact SELF+CHILDREN delta mechanism is from my reading of bash's `execute_cmd.c` and matches the observed results, but wasn't re-verified against current source.

### Bash POSIX mode
In POSIX mode `time` isn't recognised as a reserved word if the next token starts with `-`, so on systems where `/bin/sh` is bash, `sh -c 'time -p x'` can hit the binary. Bare `time` prints the cumulative user/sys of the shell and its children.

### Bug 1: BusyBox 1.36.x max RSS ×4 (reproduced)

```
GNU time -f %M      → 62084
busybox time -f %M  → 248336   (exactly 4 × 62084)
```
BusyBox 1_36_stable `case 'M'`: `printf("%lu", ptok(pagesize, (UL) resp->ru.ru_maxrss));`, the same mistake as GNU 1.7. Upstream master now prints `resp->ru.ru_maxrss` directly and has `ptok` under `#ifdef UNUSED`. I didn't confirm which release first shipped the fix.

### Bug 2: toybox 0.8.9 default-mode fraction (reproduced)

```
toybox time sleep 0.05      → user 0.1176   (really 0.001176 s)
toybox time python3 …       → sys  0.3982   (-p shows sys 0.003982)
```
Format `"%s%s%c%lld.%0*d\n"` with width `6>>!toys.optflags`: 3 in default mode, 6 with flags. Real time is scaled to match, but user/sys come straight from `tv_usec` (microseconds) and aren't scaled; `%0*d` with width 3 is a minimum, so 3982 µs prints as `.3982`. **Use `-p` or `-v` on Android.** Your device's toybox may be newer.

### Implementation comparison

| Implementation | Fields | Formats | Default precision | Known issues |
|---|---|---|---|---|
| bash keyword | real/user/sys | `TIMEFORMAT` | ms | redirection needs braces |
| zsh keyword | + memory, faults, I/O | `TIMEFMT` | 10 ms | `%M` in MB |
| mksh/ksh | real/user/sys | ksh93 `TIMEFORMAT`; mksh fixed | 10 ms | none found |
| GNU time 1.9 | full rusage | `-f`/`TIME`, `-p`, `-v`, `-o -a`, `-q` | 10 ms | Linux zero fields |
| BusyBox | GNU-like (`-v -p -f -o -a`) | GNU-like | 10 ms | %M ×4 in 1.36 |
| toybox | real/user/sys + `-v` set | `-p`, `-v` only | ms / µs | 0.8.9 fraction bug |

---

## Cross-platform comparison

| Platform | Native way | Wall | User/Sys | Peak memory | Notes |
|---|---|---|---|---|---|
| Linux | bash `time`, GNU `/usr/bin/time -v`, BusyBox, toybox | ✔ | ✔ | ✔ KB | reference |
| macOS | zsh `time`; BSD `/usr/bin/time -l` (`-h`, `-p`) | ✔ | ✔ | ✔ **bytes** | no GNU `-v`; `-l` gives the rusage list |
| FreeBSD / NetBSD / OpenBSD | `/usr/bin/time -l`, NetBSD `-c` (csh format) | ✔ | ✔ | ✔ | NetBSD man page documents ru_maxrss in bytes |
| Windows PowerShell | `Measure-Command { … }` | ✔ | ✘ | ✘ | returns `TimeSpan`; uses `Stopwatch`; runs in the current scope; CPU/memory via `Get-Process` (`TotalProcessorTime`, `PeakWorkingSet64`) or Win32 `GetProcessTimes` / `GetProcessMemoryInfo` |
| Windows cmd.exe | `time` **sets the clock** | – | – | – | unrelated; use `%time%` before/after |
| Android | toybox `time -pv`; `simpleperf` | ✔ | ✔ | ✔ KiB | toybox format quirks |
| iOS | Xcode Instruments, `os_signpost` | ✔ | ✔ | ✔ | GUI/tracing, no shell |
| Web / Node | `performance.now()`, `console.time()`, Node `process.cpuUsage()` / `process.resourceUsage()` | ✔ | Node | Node | Node's resourceUsage is libuv getrusage, the same struct |
| AWS Lambda | REPORT line: Duration, Billed Duration, Max Memory Used | ✔ | ✘ | ✔ | per-invocation `time -v`, tied to billing |
| Kubernetes | `kubectl top`, metrics-server, cgroup `memory.peak` | sampled | ✔ | ✔ | per cgroup, not per process |

---

## Alternatives

| Tool | Use it when |
|---|---|
| hyperfine (David Peter, Rust) | statistics over repeated runs: at least 10 runs / about 3 s by default, `--warmup`, `--prepare`, outlier detection, export to JSON/CSV/Markdown |
| perf stat | hardware counters: cycles, instructions, IPC, cache misses |
| systemd-run --wait -p MemoryAccounting=yes | whole-cgroup CPU time + peak memory |
| /sys/fs/cgroup/…/memory.peak | container/pod-level peak memory (Linux 5.19+) |
| /proc/PID/status `VmHWM` | peak RSS of a process that's still running |
| strace -c / ltrace -c | which syscalls make up the sys time |
| `times` builtin | cumulative shell + children time so far |
| valgrind massif / heaptrack | heap-level memory profiles |
| `date +%s.%N` deltas, `ts` | checkpoints inside a script |
| `curl -w '%{time_total}'` | network request timing without local process overhead |

---

## Role lens

### 1. Linux System Administrator
- **Why:** first-pass triage of slow cron jobs, backups, `rsync`/`find`.
- **Daily:** `time rsync …`; compare real with user+sys to decide between disk/network and CPU.
- **Expert knows:** `type -a time` first; Debian cron `/bin/sh` scripts run the binary (dash), so the format differs from interactive; minimal images lack the binary; `-o file -a` keeps cron mail clean.

### 2. Performance / SRE
- **Why:** `%M` is the cheapest way to size memory requests and limits.
- **Daily:** `/usr/bin/time -f '%M %e %P %c %w'` in CI for memory and latency regressions.
- **Expert knows:** `ru_maxrss` = largest single process; many involuntary switches point to CPU contention/throttling; minor faults × 4 KB ≈ memory touched for the first time; switch to `memory.peak` / `systemd-run` for the whole tree; know the historical ×4 bug and the BusyBox one.

### 3. Software Developer / Systems Programmer
- **Why:** quick A/B checks of builds, compilers, algorithms.
- **Daily:** `time make -j8`, `time ./a.out < input`.
- **Expert knows:** user > real means parallelism works; high sys means syscall overhead (batch I/O, mmap); use hyperfine for decisions and `perf stat` for IPC; the fields are `struct rusage`, which they can read in their own code.

### 4. Shell Scripting / DevOps Engineer
- **Why:** timing pipeline steps.
- **Daily:** `TIMEFORMAT='%R'; { time step; } 2>>timings.log`.
- **Expert knows:** keyword vs binary, assignment prefix, POSIX-mode `-` rule, braces for redirection, `time -p` for portability across dash, bash, ash and mksh; GitHub/GitLab CI `ubuntu-latest` is bash, but `alpine` job containers are BusyBox.

### 5. HPC / Research Computing Engineer
- **Why:** accurate SLURM/PBS `--mem` / `--time` requests.
- **Daily:** `/usr/bin/time -v` on a small test run, then scale.
- **Expert knows:** per-rank `%M` ≠ node total for MPI, so use `sacct -o MaxRSS,Elapsed,TotalCPU`; `%U` / (`%e` × cores) = parallel efficiency.

### 6. Cybersecurity Analyst / Pentester
- **Why:** timing side channels: time-based blind SQLi (`SLEEP(5)`), username enumeration via response time, constant-time comparison checks.
- **Daily:** `time curl -s …` for a first look; in practice `curl -w '%{time_total}'` or Burp timers.
- **Expert knows:** one sample is useless against jitter, so confirm statistically; on defence, `time -v` on a suspicious binary in a sandbox shows heavy sys time or many voluntary switches (but Linux leaves socket counters at 0). `time` is a measurement aid, not a security tool.

### 7. Data Engineer
- **Why:** decide CPU-bound vs I/O-bound before rewriting an ETL step (e.g. in Spark).
- **Daily:** the CSV logging pattern above.
- **Expert knows:** Parquet vs CSV shows directly in `%I` and `%U`; cold vs warm cache can differ 10×, so drop caches or use hyperfine `--prepare`.

### 8. CS Student / Educator
- **Why:** the clearest demo of user vs kernel mode, process accounting, fork/exec/wait, page faults, virtual memory.
- **Daily:** `time dd if=/dev/zero of=/dev/null bs=1 count=…` vs `bs=1M` (sys explodes with tiny syscalls); touching N MB gives about N×256 minor faults.
- **Expert knows:** keyword vs fork/exec is a lesson in how shells parse; `ru_maxrss` units differ by OS; online judges enforce limits via the same rusage.

---

## Related topics

- Operating systems: process accounting, user vs kernel mode, fork/exec/wait, virtual memory, page faults
- Linux certifications (LPIC-1, LFCS-style): builtins vs external commands, `type`, PATH lookup, process management
- Performance engineering: USE method, benchmarking method, capacity planning
- Shell language & POSIX: reserved words, pipelines, POSIX mode, portability
- Containers & Kubernetes: sizing requests/limits, minimal images, cgroup v2 `memory.peak`
- HPC: job sizing, parallel efficiency
- Security: timing side channels, time-based blind injection
- Competitive programming / online judges: time and memory limits

---

## Q&A from the session

### Q: What is `time`? (role pick)
A Unix utility, and also a shell keyword, that runs a command and reports elapsed, user and system time; GNU time adds memory, I/O and fault counters. Note: Windows cmd `time` is a different command (it sets the clock); PowerShell's equivalent is `Measure-Command`.

### Q: Cover all roles, all types of Linux systems, and compare implementations
Covered above: the cross-Linux availability map, side-by-side real output from bash, GNU, dash, zsh, mksh, BusyBox and toybox, the implementation comparison table, and the two current bugs found during testing (BusyBox 1.36 RSS ×4, toybox 0.8.9 fraction width).

---

## Gotchas checklist

1. `time -v cmd` → "-v: command not found": the keyword grabbed it; use `/usr/bin/time -v`.
2. `VAR=x time cmd` uses the binary, not the keyword.
3. `time cmd 2>file` doesn't capture the timing; use `{ time cmd; } 2>file`.
4. The binary can't time functions, aliases or builtins.
5. The binary times only the first stage of a pipeline.
6. `sudo time cmd` runs the binary; `time sudo cmd` includes sudo's overhead.
7. `#!/bin/sh` differs per distro: dash (binary or missing), bash-as-sh (keyword), ash (BusyBox). Use `time -p`.
8. Peak memory units: Linux KB, macOS bytes, zsh `%M` MB.
9. One run is noise: use hyperfine.
10. Ubuntu 24.04 `time --version` prints `UNKNOWN`; check `dpkg -l time`.
11. BusyBox 1.36 `%M` ×4; toybox 0.8.9 default fractions wrong.
12. No root needed; you always see the rusage of your own children.

---

## Sources

- GNU time homepage: https://www.gnu.org/s/time/
- GNU Time 1.8 announcement: https://lists.gnu.org/r/info-gnu/2017-11/msg00002.html
- GNU Time 1.9 announcement: https://lists.endsoftwarepatents.org/archive/html/bug-time/2018-03/msg00002.html
- pkgsrc gnutime changelog (1.7→1.8→1.9 changes): https://backiee.wasmer.app/https_pkgsrc_se/time/gnutime
- Assaf Gordon on the max RSS bug: https://lists.gnu.org/archive/html/bug-time/2018-12/msg00001.html
- Red Hat bug 783143: https://bugzilla.redhat.com/show_bug.cgi?id=783143
- LKML 2012 thread: https://lists.openwall.net/linux-kernel/2012/10/11/691
- Debian time-1.7 patches (Bob Proulx): https://lists.libreplanet.org/archive/html/bug-gnu-utils/2013-11/msg00007.html
- BusyBox time.c (master): https://gogs.librecmc.org/OWEALs/busybox/raw/master/miscutils/time.c
- BusyBox time.c (1_36_stable): https://gogs.librecmc.org/OWEALs/busybox/src/1_36_stable/miscutils/time.c
- toybox time.c (Android): https://android.googlesource.com/platform/external/toybox/+/865c9d0cd360f1eeb8b01d7ba790b31c67f09eed/toys/posix/time.c
- toybox "Add time -v" commit: https://landley.net/toybox/git/commit/95942749b049
- Android shell & utilities README: https://fuchsia.googlesource.com/third_party/android.googlesource.com/platform/system/core/+show/18b746188c73a83ad57b99558914ba9421e8a20a/shell_and_utilities/README.md
- Bash manual, Pipelines: https://www.gnu.org/s/bash/manual/html_node/Pipelines.html
- Chet Ramey on TIMEFORMAT / reserved word: https://mail.gnu.org:443/archive/html/bug-bash/2009-03/msg00164.html
- Wikipedia, time (Unix): https://en.wikipedia.org/wiki/Time_(Unix)
- POSIX time(1p): https://manpages.ubuntu.com/manpages/trusty/man1/time.1posix.html
- Austin Group issue 267: https://austingroupbugs.net/view.php?id=267
- Ubuntu time(1): https://manpages.ubuntu.com/manpages/lunar/man1/time.1.html
- AUUGN notes on Unix Edition One: https://sunsite2.icm.edu.pl/pub/unix/UnixArchive/Documentation/TUHS/Old/AUUGN/andrew_notes.txt
- V7 time(1): https://mail.typewritten.org/Manual/Sun/Unisoft/V7/man1/time.html
- macOS time(1): https://leancrew.com/all-this/man/man1/time.html
- NetBSD time(1): https://www.daemon-systems.org/man/time.1.html
- macOS maxrss in bytes: https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/44883526/unit-of-maximum-resident-set-size-in-the-output-of-time
- hyperfine docs: https://docs.rs/hyperfine
- Measure-Command: https://learn.microsoft.com/powershell/module/microsoft.powershell.utility/measure-command
- systemd-devel memory.peak thread: https://lists.freedesktop.org/archives/systemd-devel/2022-August/048176.html
- systemd-run "Memory peak" patch: https://git.almalinux.org/rpms/systemd/src/commit/479809cb6eca2c44d01203ee191ddb00cf50d9b8/1197-run-include-peak-memory-in-output.patch
- charliecloud Alpine Dockerfile: https://sources.debian.org/src/charliecloud/0.43-2/test/gitlab.com/alpine.df
- Local test environment: Ubuntu 24.04.5, bash 5.2.21, GNU time 1.9-0.2build1, BusyBox 1.36.1-6ubuntu3.1, toybox 0.8.9, zsh 5.9, mksh 59c
