---
tool: [apt, snap]
date: 2026-11-24
domains: [Linux System Administration, DevOps, Software Packaging & Distribution, Linux Security, Embedded/IoT]
roles: [Linux System Administrator, DevOps / Platform Engineer, Cybersecurity Analyst / Hardening Engineer, Software Developer / Packager, Penetration Tester / Red Teamer, SRE / Release Engineer, Embedded / IoT Engineer]
tags: [apt, apt-get, dpkg, deb, snap, snapd, snapcraft, ubuntu, debian, ubuntu-core, package-management, dependency-solver, solver3, apparmor, seccomp, squashfs, supply-chain, privilege-escalation, flatpak, dnf, pacman, winget, homebrew]
---

# apt and snap: the two package managers on Ubuntu

## Summary

- **APT** (Advanced Package Tool) is the classic package manager of Debian-family systems (Debian, Ubuntu, Mint, Kali, Raspberry Pi OS). It installs, upgrades and removes software, resolves dependencies automatically and downloads signed `.deb` packages from repositories maintained by the distribution. It sits on top of `dpkg`, which does the actual unpacking. Created in the Debian "deity" project, working by March 1998.
- **snap** is Canonical's newer containerised format (2014; snapd 2.0 in Ubuntu 16.04, 2016). A snap bundles an application with its dependencies in one compressed squashfs image, runs it confined (AppArmor + seccomp + mount namespace), and updates it automatically. Snaps work on any distro with `snapd`; Ubuntu Core (IoT) is built entirely from snaps.
- On Ubuntu both ship by default: APT supplies the OS and server stack; snaps supply fast-moving apps (Firefox, App Center, kubectl, LXD, MicroK8s). Current versions on Ubuntu 26.04 LTS: APT 3.2.0, snapd 2.74.1 [1].

### Mental model: the layers

```
 apt / apt-get / aptitude / synaptic / App Center (debs)
        │  resolves deps, downloads, verifies signatures
        ▼
 dpkg   ── unpacks .deb, runs maintainer scripts, owns /var/lib/dpkg/status
        ▼
 files spread into /usr, /etc, /var  (shared libraries, one system)

 snap CLI / App Center (snaps)
        │  REST over /run/snapd.socket
        ▼
 snapd (root daemon) ── downloads from Snap Store, verifies assertions
        ▼
 /var/lib/snapd/snaps/<name>_<rev>.snap  (squashfs) → loop-mounted at /snap/<name>/<rev>
        + AppArmor + seccomp + mount namespace = confinement
```

### Install / availability

| | APT | snap |
|---|---|---|
| Ubuntu | Built in | Built in (snapd preinstalled; Firefox, App Center, `core*` are snaps) |
| Debian, Mint, Pop!_OS, Kali, Raspberry Pi OS | Built in | `sudo apt install snapd` (Mint blocks it by default via `/etc/apt/preferences.d/nosnap.pref`) |
| Fedora, Arch, openSUSE, etc. | Not native (dnf / pacman / zypper) | Install `snapd`, enable `snapd.socket` |
| Ubuntu Core (IoT) | No APT at all | The whole OS is snaps |
| WSL Ubuntu | Yes | Works when systemd is enabled |

---

## Usage and commands

### APT: the 10 most useful operations

**1. Refresh the index:** `sudo apt update`
```
Hit:1 http://archive.ubuntu.com/ubuntu noble InRelease
Get:2 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]
Get:3 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages [612 kB]
Fetched 1,140 kB in 2s (571 kB/s)
14 packages can be upgraded. Run 'apt list --upgradable' to see them.
```

**2. Install:** `sudo apt install nginx`
```
The following additional packages will be installed:
  libnginx-mod-http-... nginx-common
Suggested packages:
  fcgiwrap nginx-doc
The following NEW packages will be installed:
  nginx nginx-common ...
0 upgraded, 4 newly installed, 0 to remove and 14 not upgraded.
Need to get 620 kB of archives.
After this operation, 1,890 kB of additional disk space will be used.
Do you want to continue? [Y/n]
```

**3. Upgrade:**
- `sudo apt upgrade` never removes packages. In the `apt` front end it may install new dependencies.
- `sudo apt full-upgrade` (formerly `dist-upgrade`) may remove packages to resolve a change.

**4. Search and inspect:** `apt search ripgrep`, then `apt show ripgrep`
```
Package: ripgrep
Version: 14.1.0-1
Priority: optional
Section: universe/utils
Maintainer: Ubuntu Developers <...>
Installed-Size: 5,207 kB
Depends: libc6 (>= 2.34), libgcc-s1 (>= 4.2), libpcre2-8-0 (>= 10.34)
APT-Sources: http://archive.ubuntu.com/ubuntu noble/universe amd64 Packages
```

**5. Which version would be installed, and why:** `apt policy nginx`
```
nginx:
  Installed: 1.24.0-2ubuntu7
  Candidate: 1.24.0-2ubuntu7.1
  Version table:
     1.24.0-2ubuntu7.1 500
        500 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages
        500 http://security.ubuntu.com/ubuntu noble-security/main amd64 Packages
 *** 1.24.0-2ubuntu7 100
        100 /var/lib/dpkg/status
```

**6. Remove:**
- `sudo apt remove pkg` keeps the config files in `/etc`.
- `sudo apt purge pkg` deletes them too.
- `sudo apt autoremove` removes automatically installed dependencies that nothing needs any more.

**7. Manual/auto and hold:**
- `sudo apt-mark hold docker-ce` freezes the version. `apt-mark showhold` lists frozen packages.
- `apt-mark showmanual` lists the packages you asked for yourself, as opposed to ones pulled in as dependencies. Autoremove relies on this distinction.

**8. File ↔ package:**
- `dpkg -S /usr/bin/dig` gives `bind9-dnsutils: /usr/bin/dig`.
- `dpkg -L bind9-dnsutils` lists the package's files.
- `apt-file search bin/dig` searches packages that are *not* installed. Run `apt install apt-file && apt-file update` first.

**9. Dependency trees:**
- `apt-cache depends nginx` shows what it needs.
- `apt-cache rdepends --installed libssl3` shows what on this system needs it.
- APT 3.x adds `apt why` / `apt why-not`, which explain why a package is or isn't installed (from solver3's implication graph [4]).

**10. History and audit:** `/var/log/apt/history.log` (one entry per command, with its command line and the user who ran it) and `/var/log/dpkg.log` (each package state change)
```
Start-Date: 2026-11-17  12:01:44
Commandline: apt install nginx
Requested-By: falgun (1000)
Install: nginx:amd64 (1.24.0-2ubuntu7), nginx-common:amd64 (...)
End-Date: 2026-11-17  12:01:49
```

### snap: the 10 most useful operations

**1. Search:** `snap find kubectl`
```
Name     Version   Publisher     Notes    Summary
kubectl  1.34.2    canonical✓    classic  Command line client for controlling a Kubernetes cluster.
```

**2. Install:**
- `sudo snap install kubectl --classic --channel=1.34/stable`
- `sudo snap install firefox`
- Output: `kubectl (1.34/stable) 1.34.2 from Canonical✓ installed`

**3. List installed:** `snap list`
```
Name     Version          Rev    Tracking         Publisher    Notes
core22   20251015         2139   latest/stable    canonical✓   base
firefox  145.0-1          7123   latest/stable/…  mozilla✓     -
kubectl  1.34.2           3655   1.34/stable      canonical✓   classic
snapd    2.74.1           25577  latest/stable    canonical✓   snapd
```

**4. Info and channels:** `snap info kubectl` shows the publisher, store URL, every track and risk with its version, and the `refresh-date`.

**5. Updates:**
- `sudo snap refresh` updates everything now. `snap refresh --list` shows what is pending.
- `sudo snap refresh --hold=72h firefox`, or `--hold` with no time to hold indefinitely.
- `sudo snap set system refresh.timer=sat,03:00-05:00` sets a maintenance window. `snap refresh --time` shows the schedule.

**6. Roll back:** `sudo snap revert firefox` returns to the previous revision kept on disk, together with that revision's copy of the data.

**7. Permissions (interfaces):** `snap connections firefox`
```
Interface        Plug                   Slot             Notes
audio-playback   firefox:audio-playback :audio-playback  -
camera           firefox:camera         -                -
home             firefox:home           :home            -
```
- Grant a missing one with `sudo snap connect firefox:camera`.

**8. What snapd did:** `snap changes` (`ID Status Spawn Ready Summary`) and `snap tasks <id>`. Use these when an install hangs.

**9. Services:**
- `snap services` lists services. `sudo snap restart <snap>.<svc>` restarts one.
- `snap logs <snap> -n 50` shows its logs. Each service is a systemd unit named `snap.<name>.<app>.service`.

**10. Remove:**
- `sudo snap remove --purge firefox`. Without `--purge`, snapd keeps an automatic snapshot of the user data.
- `snap saved` lists snapshots and `snap restore <id>` brings one back.

### Realistic task: provision a hardened Ubuntu server

Docker comes from the vendor's repository and kubectl from a snap. Updates run in controlled windows and every step is auditable.

```bash
# 1. Base update and unattended security patches (SysAdmin/SRE)
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades     # writes /etc/apt/apt.conf.d/20auto-upgrades

# 2. Add a third-party repo the MODERN way: per-repo key, deb822 format (Security)
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.gpg
EOF

# 3. Pin it so this repo can ONLY supply docker packages (Security/Packager)
sudo tee /etc/apt/preferences.d/docker.pref >/dev/null <<'EOF'
Package: *
Pin: origin download.docker.com
Pin-Priority: 100

Package: docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
Pin: origin download.docker.com
Pin-Priority: 500
EOF
sudo apt update && apt policy docker-ce          # verify the candidate comes from docker.com

# 4. Install a specific version and freeze it (DevOps/SRE)
apt list -a docker-ce | head -3
sudo apt install -y docker-ce=<version-from-apt-list> docker-ce-cli containerd.io
sudo apt-mark hold docker-ce docker-ce-cli containerd.io

# 5. kubectl as a snap, pinned to a minor-version track (DevOps)
sudo snap install kubectl --classic --channel=1.34/stable

# 6. Control snap refreshes (SRE)
sudo snap set system refresh.timer=sun,02:00-04:00
sudo snap set system refresh.retain=2
snap refresh --time

# 7. Audit (Security)
apt-mark showhold
grep -h ^Signed-By /etc/apt/sources.list.d/*.sources   # every repo should have its own key
ls /etc/apt/trusted.gpg.d/                              # should be near-empty: these keys trust ALL repos
snap list --all | awk '$6 ~ /disabled/'                 # old revisions kept on disk
```

Why it's done this way:
- `Signed-By` scopes a key to one repository. A key in `trusted.gpg.d` can sign *any* repo.
- The pin stops Docker's repo from silently replacing unrelated packages.
- `hold` stops unattended-upgrades and `full-upgrade` from bumping Docker.
- The channel `1.34/stable` follows only 1.34 patch releases.

### Common mistakes, permissions and gotchas

**APT**
- `apt` in scripts. It warns `apt does not have a stable CLI interface`. Scripts should use `apt-get` and `apt-cache`.
- Dockerfiles: run `update` and `install` in the same `RUN`, then clean up: `apt-get update && apt-get install -y --no-install-recommends … && rm -rf /var/lib/apt/lists/*`.
- CI hangs on prompts: use `DEBIAN_FRONTEND=noninteractive` and `-y`.
- `apt-key add` is deprecated and was removed during the APT 3.x cycle. Use `/etc/apt/keyrings` and `Signed-By`.
- `Could not get lock /var/lib/dpkg/lock-frontend` usually means unattended-upgrades is running. Wait. Never delete the lock files.
- An interrupted dpkg leaves packages half-configured: run `sudo dpkg --configure -a`, then `sudo apt -f install`.
- PPAs and third-party repos complicate release upgrades. `do-release-upgrade` disables them.
- Ubuntu **phased updates**: "deferred due to phasing" is normal. Updates roll out to a percentage of machines at a time.
- Root is needed for everything except `search`, `show`, `policy` and `list`.

**snap**
- On Ubuntu, `apt install firefox` or `chromium` installs a transitional .deb that pulls in the snap.
- `df` and `lsblk` show many `/dev/loopN` squashfs mounts, one per revision. That's normal.
- Disk use grows because 2–3 revisions of each snap are kept (`refresh.retain`).
- Strict snaps can't see `/mnt`, hidden dot-directories in home, or other users' files unless an interface (`removable-media`, `home`) is connected.
- Data lives in `~/snap/<name>/<rev>/`, not `~/.config`.
- First launch is slower (squashfs decompression and AppArmor profile load).
- An auto-refresh restarts services. Use `refresh.timer`, `--hold`, or a Snap Store Proxy for fleets.
- `find`, `list` and `info` work as a normal user. Install, remove, refresh and connect need root, or polkit on desktops.

---

## Output and fields explained

**`apt update` lines**
- `Hit`: the index is unchanged and nothing was downloaded.
- `Get`: the index was downloaded.
- `Ign`: ignored, which is often harmless.
- `InRelease`: the signed file that lists the hashes of every index.
- `Packages`: the index for one component and architecture.
- `update` changes only `/var/lib/apt/lists/` and never installs anything.

**`apt install` summary**
- **Recommends** are installed by default. **Suggests** are only listed. Add `--no-install-recommends` for slim installs.
- "not upgraded" counts packages with pending upgrades that this command isn't touching.
- APT 3.x shows the same information in a coloured, columnar layout.

**`apt show`:** `Section: universe/...` means community-maintained. `main` means Canonical-supported, which matters for security support and ESM coverage.

**`apt policy`**
- The numbers are **pin priorities**:

| Priority | Meaning |
|---|---|
| 1001+ | Force, even a downgrade |
| 990 | Target release |
| 500 | Default for a repository |
| 100 | Installed (`/var/lib/dpkg/status`) or NotAutomatic repos such as backports |
| <0 | Never install |

- `***` marks the installed version.
- **Candidate** = the highest-priority version, or the highest version among equal priorities. This is the single most useful APT debugging command.

**`snap find` / `snap list`**
- `✓` = verified publisher, and a star = starred developer. Neither means the code was audited.
- **Rev** = store revision, a number that only ever goes up. **Version** is just the developer's label.
- **Tracking** = channel, written `track/risk[/branch]`. Risk is `stable`, `candidate`, `beta` or `edge`. A branch is a temporary hotfix stream.
- **Notes**: `base` (a runtime core snap), `classic` (no sandbox), `devmode` (sandbox only logs), `disabled` (an old revision kept for revert), `snapd`.

**`snap connections`:** an empty slot `-` means the permission isn't connected.

---

## History and evolution

### APT

| Year | Milestone |
|---|---|
| 1993–94 | Debian starts. `dpkg` (Ian Murdock, then Ian Jackson) handles single packages with no dependency fetching |
| 1995–97 | `dselect`, a hard-to-use menu front end. In April 1997 Release Manager Brian White commissions the "deity" replacement project [5][6] |
| Mar 1998 | Jason Gunthorpe's "It's working" mail. apt-get is born [5] |
| 1999 | APT 0.3 ships in Debian 2.1 "slink". Code © 1997–1999 Jason Gunthorpe and others, GPLv2+, C++ [7] |
| 2005 | **Secure APT** (0.6): GPG-signed Release/InRelease files carrying hashes of the indices |
| 2008 | PackageKit gives desktops a cross-distro API (APT backend) |
| 2014 | **APT 1.0** adds the friendly `apt` command |
| 2020 | **APT 2.0** (March) |
| 2021–24 | `apt-key` deprecated in favour of `signed-by`. deb822 `.sources` becomes Ubuntu's default (`ubuntu.sources`, 24.04) |
| May 2024 | solver3 previewed in APT 2.9.3 behind `--solver 3.0` [4][8] |
| Apr 2025 | **APT 3.0**: new UI, Sequoia replaces GnuPG for verifying signatures, solver3, in time for Debian 13 "trixie". Dedicated to Steve Langasek [3] |
| 2026 | Ubuntu 26.04 LTS ships APT 3.2.0 [1] |

Current development is driven mainly by Julian Andres Klode [3].

### snap

| Year | Milestone |
|---|---|
| 2013 | "Click" packages for Ubuntu Touch, the predecessor |
| 2014 | Work on snaps begins for a "headless phone" IoT image, using read-only tarballs and a Python "snappy" script [9]. Ubuntu Core with "snappy transactional updates" is announced on 9 Dec 2014 [10] |
| Apr 2016 | snapd 2.0, rewritten in Go, ships in Ubuntu 16.04 LTS with the new snap format [11][12] |
| Jun 2016 | snapd ported to other distributions (Arch, Debian, Fedora, etc.) [10] |
| 2019 | Dirty Sock local privilege escalation in snapd (CVE-2019-7304) [14] |
| 2020 | Linux Mint blocks snapd after Ubuntu's Chromium deb→snap switch |
| 2022 | Firefox is a snap by default in Ubuntu 22.04 |
| 2024 | Fake crypto-wallet snaps lead to manual review of new registrations [13] |
| 2026 | Attackers take over old publisher accounts via expired domains [13]. Ubuntu 26.04 ships snapd 2.74 [1]. Ubuntu Core 26 |

### The underlying ideas

- **APT is a dependency-resolving distribution package manager.** Choosing a consistent set of versions is constraint solving: the EDOS/Mancoosi research showed it is NP-complete, which is why solver design matters. solver3 is described by Klode as a DPLL solver without pure-literal elimination [3]. It is fully backtracking, solves smaller choices first (A before A|B), never promotes manually installed packages for removal, and records an implication graph that explains its decisions [4][8].
- **Snap is an application-image model.** The app is bundled with its dependencies, mounted read-only, confined by Linux security modules, and updated atomically. Its ancestors are the Mac `.app` bundle, Klik/AppImage, and Android's per-app sandbox. Flatpak (2015, as xdg-app, Alexander Larsson) is its main peer.

### Why both are used today

- **APT is the base of the OS.** The kernel, libc, systemd and server daemons should come from one tested set of packages with a single security-patch stream. That is signed and reproducible, and it is what compliance frameworks expect.
- **Snap fixes the "old app on an LTS" problem.** It also gives Canonical one build for every Ubuntu release, gives Ubuntu Core transactional OTA updates, and gives publishers channels for staging releases.
- **Ubuntu's split:** APT/deb for the OS and server stack; snaps for fast-moving desktop apps, Canonical's own infrastructure tools and Ubuntu Core; Flatpak is one `apt install` away.

---

## How it works internally

### APT
1. **Sources:** `/etc/apt/sources.list` and `/etc/apt/sources.list.d/*.list|*.sources` (deb822), each with a `Signed-By` keyring.
2. **Fetch:** `apt update` downloads `InRelease`, checks the signature (Sequoia `sqv` in APT 3.x, GnuPG before that), then downloads the `Packages` and `Sources` indices whose hashes are in `InRelease`. Everything is stored in `/var/lib/apt/lists/`.
3. **Cache:** the indices are compiled into binary caches (`/var/cache/apt/pkgcache.bin`, `srcpkgcache.bin`).
4. **Policy:** each version gets a pin priority from `/etc/apt/preferences(.d)`, which picks the candidate.
5. **Solver:** solver3 by default in 3.x, the old problem resolver earlier. It satisfies Depends/Pre-Depends/Conflicts/Breaks and installs Recommends by default.
6. **Acquire:** downloads `.deb` files to `/var/cache/apt/archives/` and verifies each file's hash against the index. The `.deb` itself is not individually signed.
7. **dpkg** runs with an ordered install plan: unpack, run the `preinst`/`postinst` maintainer scripts **as root**, record state in `/var/lib/dpkg/status`. Auto/manual marks live in `/var/lib/apt/extended_states`.
8. **Hooks:** `/etc/apt/apt.conf.d/` keys such as `DPkg::Pre-Invoke`, `APT::Update::Post-Invoke` run commands as root. This is useful and also an attack surface.
9. **Logs:** `/var/log/apt/history.log`, `term.log`, `/var/log/dpkg.log`.

### snap
1. `snap` (the CLI) talks to **snapd**, a root daemon, through a REST API on `/run/snapd.socket`. Socket peer credentials decide which calls are allowed; Dirty Sock abused this check.
2. snapd fetches **assertions** (signed metadata: snap-declaration, snap-revision with the file's hash, account) and the `.snap` file from the store, then verifies them against Canonical's root key.
3. The snap is a **squashfs** file at `/var/lib/snapd/snaps/<name>_<rev>.snap`, mounted through systemd mount units at `/snap/<name>/<rev>`. `current` is a symlink to the active revision.
4. Running an app goes through `/snap/bin/<app>` → `snap run` → **snap-confine** (a setuid-root helper). It sets up the mount namespace and loads the AppArmor profile and seccomp filter generated from the snap's connected **interfaces** (plugs and slots).
5. **Confinement modes:** `strict` (full sandbox), `classic` (no sandbox, like a traditional package, needs store approval), `devmode` (the sandbox only logs violations).
6. **Refresh:** snapd checks the store about 4 times a day by default. A refresh downloads a new revision, takes a copy of the data, switches `current`, and keeps old revisions (`refresh.retain`). `snap revert` switches back.
7. **Bases** (core20/22/24) provide the root filesystem the app sees. **Content snaps** share large runtimes such as GNOME platforms.
8. Every operation is a **change** made of **tasks** (`snap changes`, `snap tasks`), which makes it transactional.

---

## Cross-platform comparison

### apt vs snap head to head

| Dimension | APT (.deb) | snap |
|---|---|---|
| Dependencies | Shared system libraries, solved by APT | Bundled + shared "base" (core22/24) + content snaps |
| Sandbox | None (maintainer scripts run as root) | AppArmor + seccomp + mount namespace (strict); none (classic) |
| Updates | Admin-driven (or unattended-upgrades) | Automatic, ~4×/day check, can be held |
| Rollback | Manual downgrade, if the old version is still available | `snap revert`, atomic |
| Disk | Small | Larger (bundles + retained revisions) |
| Source of truth | Many repos, anyone can host one, GPG-signed | One store (proprietary backend), assertions signed by Canonical |
| Cross-distro | Debian family only | Any distro with snapd |
| Startup | Native | Slight cold-start penalty |
| Offline / air-gapped | `apt-offline`, mirrors (aptly, apt-mirror) | `snap download` + `snap ack`, Snap Store Proxy |

### How other platforms solve the same problem

| Platform | System packages | App distribution | Sandbox | Atomic update / rollback |
|---|---|---|---|---|
| Debian/Ubuntu | APT + dpkg | APT, snap, Flatpak | Snap/Flatpak only | Snap yes; APT no (unless using Btrfs/ZFS snapshots) |
| Fedora/RHEL | dnf + rpm | dnf, Flatpak (default) | Flatpak (bubblewrap) | rpm-ostree/bootc: yes |
| Arch | pacman | pacman, AUR, Flatpak | Flatpak | No |
| NixOS | Nix (functional, hashed store paths) | Nix | No by default | Yes, generations |
| Windows | Windows Update (OS) | winget, MSIX/Microsoft Store, Chocolatey, Scoop | MSIX/AppContainer | Partial |
| macOS | `softwareupdate` (OS) | App Store, Homebrew, .pkg/.dmg | App Sandbox (mandatory for Store apps) | OS: sealed system volume + snapshots |
| Android | APEX/Mainline + A/B OTA | Play Store / APK | Per-app UID + SELinux | Yes (A/B) |
| iOS | Signed OS image | App Store only (EU alternative marketplaces) | Mandatory | Yes |
| Containers/cloud | Base image's manager | OCI images | namespaces/cgroups | Redeploy = rollback |

**What's the same and what differs**
- **Same everywhere:** signed metadata, a central index, dependency handling.
- **The key split:** shared libraries plus a solver (APT, dnf, pacman, Homebrew) vs bundled plus sandboxed (snap, Flatpak, MSIX, mobile).
- **Closest matches:**
  - Snap ≈ MSIX + Microsoft Store, and ≈ Android's model on IoT.
  - APT ≈ dnf/pacman.
  - `apt` in daily use ≈ `winget`/`brew`.

---

## Alternatives

- **On Debian/Ubuntu:**
  - `aptitude`: an alternative resolver plus a text UI.
  - `nala`: a prettier front end with parallel downloads.
  - `synaptic`: a GUI.
  - `dpkg -i` for a local `.deb`.
  - Flatpak, AppImage.
  - Nix/Guix (installable on Debian).
  - Homebrew on Linux.
  - Distrobox/toolbox containers.
  - Language package managers (pip, npm, cargo) for developer tools.
- **Other Linux:**
  - dnf/rpm (Fedora, RHEL)
  - zypper (SUSE)
  - pacman + AUR (Arch)
  - apk (Alpine, and now OpenWrt)
  - xbps (Void)
  - emerge (Gentoo)
  - rpm-ostree/bootc (image-based Fedora)
  - Nix (NixOS)
- See the follow-up Q&A below for the full cross-OS survey and the reasons behind each choice.

---

## Role: Linux System Administrator

**Why it matters:** every patch, install and dependency problem on a Debian/Ubuntu fleet goes through APT, and on Ubuntu snaps now run alongside it.

**Day to day:**
- `apt update && apt list --upgradable`, `apt policy`, `apt-mark hold`.
- Reading `history.log`.
- Fixing a broken dpkg with `dpkg --configure -a`.
- Managing `sources.list.d/`.
- `snap list`, `snap refresh --hold`.

**What experts know:**
- **Pin priorities:** 1001+ forces even a downgrade; 990 is the target release; 500 the default; 100 installed or backports; below 0 means never.
- `apt policy` tells you *why* a version was chosen.
- `needrestart` shows which services still run old libraries after an upgrade.
- `apt.conf.d` drop-ins: `Acquire::http::Proxy`, `APT::Install-Recommends "false"`, `Dpkg::Options::="--force-confold"`.
- `debsums -c` verifies installed files against their checksums.

## Role: DevOps / Platform Engineer

**Why it matters:** reproducible images and pipelines.

**Day to day:**
- Dockerfiles and Ansible's `apt` module.
- Version pins (`pkg=1.2.3-1`).
- Snapshot mirrors (`snapshot.debian.org`, `snapshot.ubuntu.com`, aptly).
- No snaps inside Docker (there is no systemd in the container). Snaps on VMs and hosts for kubectl, LXD and MicroK8s.

**What experts know:**
- `snapshot.ubuntu.com` lets you install exactly the archive state from a given date.
- `--no-install-recommends` plus cleaning the lists cuts image size dramatically.
- Snap channels (`1.34/stable`) give per-tool version tracks without extra repositories.
- A Snap Store Proxy or Landscape controls which revisions reach a fleet.

## Role: Cybersecurity Analyst / Hardening Engineer

**Why it matters:** the package manager is the software supply chain.

**Day to day:**
- Verify every repo uses `Signed-By`.
- Audit PPAs.
- Run `unattended-upgrades` with only `-security` origins.
- Check Ubuntu Pro/ESM coverage (`pro security-status`).
- Map CVEs with `debsecan` or OVAL feeds.
- CIS benchmark checks: GPG keys, repos, updates.

**What experts know:**
- **APT's trust chain:** the signed InRelease lists the hash of each Packages index, which lists the hash of each `.deb`. Individual `.deb` files are **not** signed by default.
- **Maintainer scripts run as root.** Installing a third-party `.deb` is equivalent to giving it root.
- **Snap's model** is different: assertions signed by Canonical's store plus confinement at run time. But "verified publisher" ≠ audited code, and `classic` snaps have no sandbox.
- **Real incidents:**
  - A fake "Exodus" wallet snap cost one user nine bitcoins (about $490,000 at the time) [13].
  - In 2026 attackers began hijacking long-standing publisher accounts by registering their expired domains, so updates to old, trusted snaps turned malicious [13].

## Role: Software Developer / Packager

**Why it matters:** deciding how users get your software.

**deb route:**
- `debian/` directory, `dpkg-buildpackage`/`debuild`, `lintian`.
- A Launchpad PPA or your own repo (aptly, reprepro).
- `nfpm`/`fpm` for quick debs.

**snap route:**
- `snapcraft.yaml` (base, confinement, parts, plugs).
- `snapcraft` builds (locally or on Launchpad).
- `snapcraft upload --release=edge`, then promote through candidate to stable.

**What experts know:**
- Getting into Debian proper means following Debian Policy and finding a sponsor. A PPA is easier but not trusted by default.
- Classic confinement needs a manual store review.
- Content snaps (e.g. gnome platform snaps) shrink bundles.
- Branches (`latest/stable/hotfix-123`) let you ship a fix to one customer.

## Role: Penetration Tester / Red Teamer

**Why it matters:** package managers run as root, so any misconfiguration can become root. This applies to authorised testing only.

**Things to look for (all well-known, documented patterns):**
- **`sudo` rules allowing `apt`, `apt-get` or `dpkg`.** These are trivially exploitable through the pager or `-o APT::Update::Pre-Invoke` hooks (documented on GTFOBins). For the same reason, `sudo snap install` of a crafted `--devmode`/`--dangerous` snap with an install hook gives root.
- **Writable `/etc/apt/apt.conf.d/` or `sources.list.d/`** plus a root cron or timer running `apt update` gives code execution as root through hooks.
- **Unpatched snapd.**
  - **Dirty Sock (CVE-2019-7304)**, found by Chris Moberly: snapd 2.28–2.37 parsed the socket peer address incorrectly during access control. A socket name containing `;uid=0;` was treated as root, which unlocked `create-user` (v1) or a sideloaded devmode snap with a root install hook (v2) [14].
  - Later snap-confine local privilege escalations (Qualys, 2021–2022) follow the same pattern: a root-owned local helper as the attack surface.
- **Enumeration:** `snap version`, `dpkg -l | grep snapd`, `apt list --upgradable` reveal the patch level.

**What experts know:** on a hardened host, the package manager's attack surface is its *configuration* (sudoers, writable conf dirs, untrusted repos). Defenders should watch `/etc/apt/**` with auditd.

## Role: SRE / Release Engineer

**Why it matters:** updates cause outages.

**Day to day:**
- `unattended-upgrades` with `Automatic-Reboot-Time` and `Package-Blacklist`.
- Ubuntu's **phased updates** (canary-style rollouts for the archive).
- `snap set system refresh.timer` / `--hold`.
- `snap revert` during incidents.
- Recording package state per host (`dpkg --get-selections`, `snap list`).

**What experts know:**
- A snap refresh restarts that snap's services, so treat it like a deploy.
- APT has no native rollback. Real rollback comes from ZFS/Btrfs snapshots, immutable images, or snapshot mirrors.
- Livepatch and `needrestart` reduce reboot pressure.

## Role: Embedded / IoT Engineer

**Why it matters:** Ubuntu Core is entirely snaps. The kernel, gadget (board configuration), base and apps are each a snap.

**Day to day:**
- Model assertion plus `ubuntu-image`.
- A brand store for the fleet.
- OTA updates via refresh, with automatic rollback if the new kernel fails to boot.
- `snap set` for device configuration.

**What experts know:**
- Transactional updates: a failed boot rolls back automatically.
- **Validation sets** pin a fleet to exact revisions.
- There is no APT on Core. Debug with `snap changes`/`snap tasks` and the classic shell snap.
- On routers, the comparable world is OpenWrt (now apk) and Yocto/Buildroot images.

---

## Related topics (where it applies)

- **Certifications:**
  - LPI LPIC-1 / Linux Essentials (objective 102.4, Debian package management)
  - CompTIA Linux+
  - LFCS
  - Canonical/Ubuntu training
  - RHCSA (the dnf equivalent)
- **Security:**
  - CIS Benchmarks and DISA STIG for Ubuntu/Debian
  - OSCP/PNPT Linux privilege escalation (sudo misconfiguration, GTFOBins)
  - Software supply-chain security (SLSA, reproducible builds, SBOMs)
- **DevOps:** Docker image optimisation, Ansible, immutable infrastructure, CKA (kubectl install paths).
- **CS theory:** dependency resolution as SAT/NP-complete, version-constraint solving.
- **OS concepts:** AppArmor, seccomp, Linux namespaces, squashfs, loop devices, setuid helpers.
- **Embedded:** Ubuntu Core, OTA update design, A/B partitions.

---

## Follow-up Q&A

### Q: What are the package managers on other Linux systems, Windows, Android, Apple platforms (macOS, iPhone) and others, and why did those systems choose them?

*This question came just before `/save` and was interrupted before an answer. It was researched then and is answered here.*

**The two forces behind every choice:**
- **Lineage.** Whoever built the OS built its package format: Red Hat → RPM, Debian → dpkg, Apple → bundles and the App Store.
- **Philosophy.** Each system trades control, openness, simplicity and reproducibility differently.

The rest follows from those two.

#### Other Linux distributions

| Distro family | Package manager (format) | Why they chose it |
|---|---|---|
| Fedora / RHEL / CentOS Stream / Rocky / Alma | **dnf** over **rpm** (`.rpm`) | Red Hat created RPM (1997) for its own distribution. yum (2003) added repositories and dependency resolution. dnf replaced yum as Fedora's default in Fedora 22 (2015) and in RHEL 8, using the libsolv SAT solver [15]. **DNF5**, a C++ rewrite with no Python dependency, became Fedora's default in Fedora 41, replacing both dnf and microdnf [16]. Enterprise needs (signed RPMs, modularity, long support) drove each step |
| openSUSE / SLES | **zypper** + libzypp over rpm | SUSE also built on RPM but wrote its own stack. libzypp introduced the **libsolv** SAT solver, later adopted by dnf, for fast, correct resolution on large repositories |
| Arch / Manjaro / EndeavourOS | **pacman** (`.pkg.tar.zst`) + **AUR** via helpers (yay, paru) | Arch's "keep it simple" rolling-release philosophy (Judd Vinet, 2002): a fast, simple binary manager plus build recipes (PKGBUILD) for anything else. Fast and readable, no Recommends layer |
| Alpine (and postmarketOS) | **apk** (apk-tools) | Built for tiny, security-focused systems (musl, BusyBox). Very fast and small, which is why Alpine is a favourite container base image |
| OpenWrt (routers) | **apk** since 25.12 (previously **opkg**) | OpenWrt switched because its opkg fork was no longer maintained while apk is actively developed [17][18]. Most package names stayed the same; the command syntax changed |
| Gentoo | **Portage / emerge** (source-based, ebuilds, USE flags) | A source-based design for maximum customisation: every package compiled for your hardware and feature flags. Binary packages are now offered too |
| Void | **xbps** | Written for Void as a fast, simple binary manager with transactional installs |
| NixOS (and Nix anywhere) / Guix | **Nix** / **Guix** (functional, hash-addressed store) | Built for reproducibility: every package lives at `/nix/store/<hash>-name`, so versions coexist, builds are reproducible, and the whole system rolls back by generation |
| Fedora Atomic / CoreOS / Silverblue | **rpm-ostree / bootc** (image-based) | An immutable OS: the system is deployed as a whole versioned image with atomic update and rollback; apps come as Flatpaks and containers |
| Cross-distro desktop apps | **Flatpak** (Flathub), **snap**, **AppImage** | Separates apps from the distro's release cycle. Most non-Ubuntu distros chose Flatpak (a community-run Flathub, bubblewrap sandbox). Canonical chose snap (a store it controls, which also covers servers and IoT). AppImage is a single portable file with no installer or daemon |

#### BSD and other Unix

| System | Package manager | Why |
|---|---|---|
| FreeBSD | **pkg** (pkgng) for binaries + **Ports** (source) | BSDs keep the **base system** (kernel + userland, updated with `freebsd-update`) separate from third-party packages. Ports came first, and pkg adds fast binary installs |
| OpenBSD | **pkg_add** + ports; `syspatch` for base | The same base/packages split, with a minimalist, security-first design |
| NetBSD (and others) | **pkgsrc** | Portability: pkgsrc builds on NetBSD, illumos, macOS and Linux |
| Solaris / illumos | **IPS** (`pkg(5)`) | Network repositories, with boot environments (ZFS) for rollback |
| IBM AIX | **installp** (+ RPM via the AIX Toolbox) | A vendor-controlled OS with filesets for base software |

#### Windows

| Layer | Tool | Why |
|---|---|---|
| OS | **Windows Update** (WSUS/Intune in enterprises) | Microsoft owns and ships the whole OS centrally, including cumulative monthly updates |
| Installer formats | **setup.exe**, **MSI** (Windows Installer, 1999), **MSIX** (2018) | Historically, every vendor shipped its own installer, with no central repository. MSI added transactional installs. MSIX adds containerised install/uninstall and clean updates |
| Store | **Microsoft Store** | A curated, sandboxed (AppContainer) channel |
| CLI package managers | **winget** (Microsoft, 2020, open-source manifests in a GitHub repo), **Chocolatey** (2011, NuGet-based), **Scoop** (installs per user, without admin rights) | They fill the "apt for Windows" gap. Note that winget mostly **downloads the vendor's own installer** from a catalogue of manifests, because the Windows ecosystem is vendor-distributed rather than distro-built |
| Enterprise | Intune, Configuration Manager (SCCM), Group Policy | Fleets need central deployment, compliance and reporting |

**Why:** Windows grew up as a commercial platform where vendors ship binaries directly to users, so there was never a distribution maintainer rebuilding everything the way Debian does. Package managers came late and act as **catalogues of vendor installers**.

#### macOS

| Layer | Tool | Why |
|---|---|---|
| OS | **Software Update** / `softwareupdate` | Apple ships the whole OS. Since Big Sur it is a **signed, sealed system volume** that updates atomically |
| Apps | **.app bundles** (drag-and-drop), **.pkg** installers, **Mac App Store** (2011) | Inherited from NeXTSTEP: an app is a self-contained folder bundle, so "install" usually means "copy". Store apps must be sandboxed. Apps from outside the Store need **Developer ID signing + notarization** (Gatekeeper) |
| CLI / open source | **Homebrew** (2009, Max Howell, Ruby), **MacPorts** (2002), **Nix** | Apple ships no package manager for Unix tools, so the community built them. Homebrew won on simplicity and installs prebuilt "bottles" |

**Why:** bundles make apps independent of each other, so there is no system-wide dependency resolution. Apple controls the OS and the Store, while the open-source CLI world is served by community tools.

#### iPhone / iPad (iOS, iPadOS)

| Tool | Why |
|---|---|
| **App Store** only (2008). Every app is signed by Apple, reviewed, and mandatorily sandboxed | Security and privacy, plus Apple's business model (review + commission). The OS is a signed image updated as a whole |
| **TestFlight**, enterprise distribution / MDM (Apple Business Manager) | Beta testing and corporate in-house apps |
| **EU alternative marketplaces** (since iOS 17.4, 2024, under the Digital Markets Act) | Required by regulation. Apps must still be notarised by Apple |

#### Android

| Layer | Tool | Why |
|---|---|---|
| OS | **A/B (seamless) OTA updates** from the OEM; **Project Mainline / APEX** modules updated through Google Play | Phones fragment across OEMs, so Google moved core components into updatable modules. A/B partitions allow atomic update and rollback |
| Apps | **APK / AAB** via **Google Play**; OEM stores (Galaxy Store, Xiaomi GetApps, etc.); **F-Droid** (free software, built from source, with reproducible builds) | Android was designed to be open: sideloading and alternative stores were allowed from the start. Each app gets its own Linux UID + SELinux sandbox, so permissions protect users regardless of source |
| Tooling | `adb install`, `pm` on the device | Developer and enterprise workflows |

**What changed in 2026:** Google is extending **developer verification** to all apps on certified devices, including sideloaded ones.
- **Why:** anonymous developers kept spreading malware [19].
- **Rollout:** rules took effect on 30 September 2026 in Brazil, Indonesia, Singapore and Thailand, covering Play and major OEM stores [20]. Global rollout follows in 2027 [19].
- **The escape hatch:** unverified apps can still be installed through an "advanced flow" (with a restart and a 24-hour wait) or ADB [21].

#### Other platforms

| Platform | Package system | Why |
|---|---|---|
| ChromeOS | A/B image updates for the OS; Play Store for Android apps; **Crostini** (a Debian container, so **APT**) for Linux apps | The OS is an immutable, verified image. Flexibility comes from containers |
| Embedded Linux build systems | **Yocto/OpenEmbedded** (can produce rpm/deb/ipk feeds), **Buildroot** (no package manager, one image) | Devices ship as whole images. Package feeds are optional, for field updates |
| Containers / cloud | **OCI images** (Docker, Podman, Kubernetes) | The whole userspace is the unit of deployment: rebuild and redeploy instead of updating in place |
| HarmonyOS (Huawei) | **AppGallery** | Vendor-controlled store, like iOS/Android |
| Game consoles (PlayStation, Xbox, Switch) | Closed vendor stores, signed system updates | Total platform control, anti-piracy and certification |
| Language ecosystems | pip/PyPI, npm, cargo/crates.io, gem, Go modules, Maven, NuGet, conda | They solve dependencies **inside one language**, independently of the OS. That is also why supply-chain attacks such as typosquatting cluster there |

#### The patterns, in one table

| Design choice | Who uses it | Why |
|---|---|---|
| Distribution builds everything + shared libs + solver | Debian (APT), Fedora (dnf), SUSE, Arch, Alpine, BSD ports | One tested, coherent set of packages; small disk; one security stream. Costs: an old app on a stable release, dependency conflicts |
| Vendor installers + optional catalogue | Windows (winget/Chocolatey), macOS (.pkg, Homebrew casks) | A commercial ecosystem where vendors ship binaries directly |
| Bundled + sandboxed + store | snap, Flatpak, MSIX, Mac/iOS App Store, Android | App independence, security isolation, fast updates. Costs: disk, store gatekeeping, trust in one operator |
| Image-based / atomic OS | Ubuntu Core, Fedora Atomic/bootc, ChromeOS, Android A/B, iOS, macOS SSV | Reliable updates and rollback on fleets and consumer devices |
| Functional / reproducible | Nix, Guix | Exact reproducibility and side-by-side versions |

### Q: Should apt and snap be studied together or separately?
Together, as one session with a head-to-head comparison. The library gets separate records (`data/tools/apt.json`, `data/tools/snap.json`) and this single shared note.

---

## Sources

[1] "Snap vs Flatpak vs APT on Ubuntu 26.04 LTS: Which to Use," ComputingForGeeks, Apr. 2026. [Online]. Available: https://computingforgeeks.com/ubuntu-2604-snap-flatpak-apt-guide/ (accessed Nov. 17, 2026).

[2] N. Dhandala, "How to Install and Manage Applications with Snap on Ubuntu," OneUptime blog, Mar. 2, 2026. [Online]. Available: https://oneuptime.com/blog/post/2026-03-02-install-manage-applications-snap-ubuntu/markdown (accessed Nov. 17, 2026).

[3] "APT 3.0," LWN.net, 2025. [Online]. Available: https://lwn.net/Articles/1017315 (accessed Nov. 17, 2026).

[4] J. A. Klode, "The new APT 3.0 solver," May 14, 2024. [Online]. Available: https://blog.jak-linux.org/2024/05/14/solver3/ (accessed Nov. 17, 2026).

[5] "APT (software)," encyclopedia.pub (citing B. C. White, "dselect replacement project (deity)," Apr. 1997, and J. Gunthorpe, "It's working," deity list, Mar. 2, 1998). [Online]. Available: https://encyclopedia.pub/entry/31354 and https://encyclopedia.pub/entry/30575 (accessed Nov. 17, 2026).

[6] Debian deity mailing list archives, 1998–1999. [Online]. Available: https://lists.debian.org/deity/ (accessed Nov. 17, 2026).

[7] "Package: apt / 1.4.10 — copyright," sources.debian.org. [Online]. Available: https://sources.debian.org/copyright/license/apt/1.4.10 (accessed Nov. 17, 2026).

[8] M. Larabel, "Debian Releases APT 2.9.3 With New Package Solver," Phoronix, May 2024. [Online]. Available: https://www.phoronix.com/news/APT-2.9.3-New-Package-Solver (accessed Nov. 17, 2026).

[9] "Snap/Snappy Ecosystem," Snapcraft forum. [Online]. Available: https://forum.snapcraft.io/t/snap-snappy-ecosystem/19807/5 (accessed Nov. 17, 2026).

[10] "Snappy (package manager)," wiki mirror (citing M. Shuttleworth, "Announcing Ubuntu Core, with snappy transactional updates!", Dec. 9, 2014). [Online]. Available: https://bafybeiemxf5abjwjbikoz4mc3a3dla6ual3jsgpdr4cjr3oz3evfyavhwq.ipfs.4everland.io/wiki/Snapcraft.html (accessed Nov. 17, 2026).

[11] Canonical, "Canonical unveils 6th LTS release of Ubuntu with 16.04," Apr. 20, 2016. [Online]. Available: https://ubuntu.com/blog/canonical-unveils-6th-lts-release-of-ubuntu-with-16-04 (accessed Nov. 17, 2026).

[12] G. Niemeyer, "snappy changes," labix.org blog, Apr. 20, 2016. [Online]. Available: https://blog.labix.org/2016/04/20/snappy-changes (accessed Nov. 17, 2026).

[13] "Canonical cracks down on crypto cons following Snap Store scam spree," The Register, Mar. 28, 2024, https://theregister.com/2024/03/28/canonical_snap_store_scams/ ; "Linux users targeted by crypto thieves via hijacked apps on Snap Store," Help Net Security, Jan. 21, 2026, https://www.helpnetsecurity.com/2026/01/21/linux-malware-snap-store/ (accessed Nov. 17, 2026).

[14] "Dirty Sock: snapd privilege escalation (CVE-2019-7304)," BetaNews / The Hacker News, Feb. 2019, https://betanews.com/article/dirty-sock-snapd-linux , https://thehackernews.com/2019/02/snapd-linux-privilege-escalation.html ; CVE record: https://cve.circl.lu/vuln/cve-2019-7304 (accessed Nov. 17, 2026).

[15] "DNF (software)," Wikipedia. [Online]. Available: https://en.wikipedia.org/wiki/DNF_(software) (accessed Nov. 17, 2026).

[16] Fedora Project, "Changes/SwitchToDnf5," Fedora wiki, https://www.fedoraproject.org/wiki/Changes/SwitchToDnf5 ; Fedora 41 release notes, https://docs.fedoraproject.org/el/fedora/f41/release-notes/sysadmin (accessed Nov. 17, 2026).

[17] H. Mehrtens, "OpenWrt 25.12.0 - Stable Release," openwrt-devel mailing list, Mar. 5, 2026. [Online]. Available: https://lists.openwrt.org/pipermail/openwrt-devel/2026-March/044621.html (accessed Nov. 17, 2026).

[18] "OpenWrt 25.12 Released with APK Package Manager Replacing opkg," Linuxiac, Mar. 2026. [Online]. Available: https://linuxiac.com/openwrt-25-12-released-with-apk-package-manager-replacing-opkg/ (accessed Nov. 17, 2026).

[19] "Google will extend developer verification to all Android apps," The Register, Aug. 26, 2025. [Online]. Available: https://www.theregister.com/2025/08/26/android_developer_verification_sideloading (accessed Nov. 17, 2026).

[20] "Google's developer verification rules have reached their first Android users," Android Authority, Oct. 1, 2026. [Online]. Available: https://androidauthority.com/android-sideloading-developer-verification-first-wave-rollout-3717921 (accessed Nov. 17, 2026).

[21] "Google's Android advanced flow sideloading rollout begins," Android Authority, 2026. [Online]. Available: https://androidauthority.com/google-android-advanced-flow-sideloading-rollout-begins-3700073 (accessed Nov. 17, 2026).

**Notes on certainty**
- Verified from the sources above: version numbers, the APT 3.0/solver3 facts, snap's 2014/2016 history, the Snap Store incidents, Dirty Sock, the dnf5/OpenWrt/Android changes.
- From general knowledge, not re-verified in this session:
  - Secure APT 0.6 (2005), APT 1.0 (2014) and APT 2.0 (March 2020) dates, and the `apt-key` removal timing.
  - Mint's 2020 snap block and Ubuntu's Firefox snap in 22.04.
  - Qualys snap-confine CVEs.
  - Windows, macOS, iOS and BSD details, yum/RPM/pacman/Homebrew/winget origin years.
  - The EU iOS 17.4 date.
- Sample command outputs are representative, not captured from one machine.
