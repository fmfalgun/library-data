---
tool: Device Posture
date: 2026-11-24
domains: [Zero Trust Architecture, Identity & Access Management, Endpoint Security, Network Access Control, Cloud Security / SASE]
roles: [Security Architect]
tags: [zero-trust, zta, nist-800-207, nist-1800-35, beyondcorp, device-posture, device-trust, conditional-access, intune, mdm, edr, ztna, tpm, attestation, cisa-ztmm, nac]
---

# Device posture in Zero Trust Architecture (ZTA)

## Summary

**Device posture** is the security state of an endpoint at the moment it asks for access, and again each time that access is renewed: OS patch level, disk encryption, Secure Boot / TPM attestation, MDM enrollment and compliance, EDR running and its risk verdict, firewall, and a device identity certificate. In a Zero Trust Architecture, posture is one of the signals the **Policy Engine** weighs next to identity. A valid username, token or certificate does not prove the endpoint behind it is healthy, enrolled or under control, so NIST SP 800-207 calls for multiple signals, not identity alone [1][2].

- **Problem it solves:** stop a valid (possibly phished) identity on an unhealthy or unknown device from reaching sensitive resources, and revoke access when a device's state degrades mid-session.
- **Nature:** an architecture concept, not a single binary. You build it from a signal chain: posture producers → policy decision point (PDP) → policy enforcement point (PEP).
- **Roles studied:** Security Architect.

### Role pick offered (for reference)
1. Security Architect (selected): designs the PDP/PEP flow and decides which posture signals gate which resources
2. IAM / Identity Engineer: wires posture into conditional access (Entra ID, Okta, Google BeyondCorp)
3. Endpoint / MDM Administrator: produces posture data (Intune, Jamf, Kandji, osquery)
4. Network Engineer (NAC/ZTNA): enforces posture at the edge (Cisco ISE, ClearPass, Zscaler, Cloudflare WARP, Tailscale)
5. Cybersecurity Analyst / SOC: investigates posture failures, correlates EDR risk with access logs
6. Penetration Tester / Red Teamer: spoofs and bypasses posture checks
7. GRC / Compliance Analyst: maps controls to NIST 800-207, 800-53, CISA ZTMM, ISO 27001, DoD ZT
8. Hardware/Platform Security Engineer: TPM / Secure Enclave attestation, measured boot

---

## What "posture" means in ZTA (the term is overloaded)

| Meaning | What is being assessed | Typical producer |
|---|---|---|
| **Device posture** (main sense) | Endpoint security state at access time | MDM, EDR, ZTNA agent, TPM |
| User / session risk posture | Sign-in risk, impossible travel, leaked credentials | IdP risk engine (Entra ID Protection, Okta ThreatInsight) |
| Workload posture | Container/VM/serverless config and vulnerability state | CSPM/KSPM, SPIFFE node attestation |
| Organisational "security posture" | Overall program state | CISA ZTMM scoring, CSPM dashboards |

---

## Usage: signals, commands and sample outputs

### Where it lives (availability)
- **Producers:** MDM (Intune, Jamf, Kandji, Workspace ONE, Google Endpoint Management), EDR (CrowdStrike, SentinelOne, Defender), ZTNA agents (Cloudflare One/WARP, Zscaler Client Connector, Netskope, Tailscale), osquery/Kolide, TPM/Secure Enclave attestation.
- **Decision (PDP):** IdP conditional access, or the ZTNA/SSE policy engine.
- **Enforcement (PEP):** access proxy, ZTNA gateway, NAC switch/RADIUS, or the app's token check.

### The 8 most useful posture signals (sample outputs are representative)

**1. Disk encryption**
```
PS> manage-bde -status C:
    Conversion Status:    Fully Encrypted
    Protection Status:    Protection On
    Key Protectors:       TPM, Numerical Password
$ fdesetup status                       # macOS
FileVault is On.
$ lsblk -o NAME,TYPE,FSTYPE             # Linux
nvme0n1p3  part  crypto_LUKS
└─luks-…   crypt ext4
```
- *Protection On* matters more than *Fully Encrypted*. A suspended BitLocker volume is encrypted but its key is stored in the clear.
- Linux: `crypto_LUKS` → `crypt` means the root filesystem sits on an unlocked LUKS mapping.

**2. Secure Boot / boot integrity**
```
PS> Confirm-SecureBootUEFI      → True
$ mokutil --sb-state            → SecureBoot enabled
$ csrutil status                → System Integrity Protection status: enabled.
```

**3. TPM presence and hardware attestation**
```
PS> Get-Tpm
TpmPresent : True   TpmReady : True   ManufacturerVersion : 7.2.x
```
The TPM is the root that turns posture from "the agent says so" into "the hardware measured it".

**4. OS version / patch level**
```
PS> [Environment]::OSVersion.Version  → 10.0.26100.x   (last field = UBR, the patch level)
$ sw_vers                             → ProductVersion: 15.x
$ . /etc/os-release; echo $VERSION_ID
```
Cloudflare's posture API field `os_version_extra` carries the Windows UBR, the macOS/iOS Product Version Extra, or the Linux distribution name and version [9].

**5. Management / enrollment state**
```
PS> dsregcmd /status
  AzureAdJoined : YES     DeviceId : 3f2a…     TpmProtected : YES
$ profiles status -type enrollment     # macOS
  Enrolled via DEP: Yes
  MDM enrollment: Yes (User Approved)
```

**6. EDR running + risk verdict.** The most dynamic signal: a device can be fully compliant and still be "high risk" because an active detection is open on it.

**7. Firewall on.** Platform support is uneven. In Cloudflare's client-check matrix the Firewall check is supported on Windows and macOS only, while OS version works on all five platforms [8].

**8. Device identity certificate / serial number.** Answers "is this a corporate device at all?", not "is it healthy?".

**Cross-platform query layer (osquery)**
```sql
osquery> SELECT encrypted, type FROM disk_encryption WHERE name LIKE '%disk0%';
osquery> SELECT name, version, build FROM os_version;
```

**Posture as policy-as-code (Cloudflare example)** [10]
```
type: "os_version", description: "Require Windows 10.0.19045+",
match: [{ platform: "windows" }], schedule: "5m",
input: { operatingSystem: "windows", operator: ">=", version: "10.0.19045" }
```
The `schedule` field means posture is re-checked on a timer, not only at login.

**Microsoft stack:** an Intune compliance policy (Device Health: Require BitLocker, Secure Boot, Code Integrity; Device Properties: min/max OS; System Security: TPM, firewall, jailbreak/root detection; Defender risk level) produces a status. An Entra Conditional Access grant control, "Require device to be marked as compliant", turns that status into allow or block. Device-based CA requires Entra ID P1/P2 [11][12][13].

---

## Output / fields explained

| Field | Meaning | When it changes |
|---|---|---|
| BitLocker *Protection Status* | Whether key protectors are active (On) or suspended (Off) | Suspended during firmware/BIOS updates; resumes after reboot |
| `TpmPresent` / `TpmReady` | TPM exists / is provisioned and owned | Firmware TPM toggles, clearing the TPM |
| Windows UBR | Cumulative update level within a build | Every monthly cumulative update |
| `AzureAdJoined` / `TpmProtected` | Device registered to Entra / device key bound to TPM | Re-join, re-image |
| Intune compliance state | Compliant / NonCompliant / InGracePeriod / Error | Each check-in; grace period expiry; Error persisting > 7 days becomes Not compliant or In grace period [12] |
| EDR risk score | Vendor's current threat verdict for the device | Detections opened or closed (minutes) |

---

## Realistic task: designing posture-gated tiers (Security Architect)

**Goal:** a contractor on a BYOD laptop reaches the wiki but never prod SSH. An admin on a hardened corporate laptop reaches both, until EDR flags the laptop.

1. **Classify resources into tiers.** Google's model: access to data increases as device hardening increases; Google initially supported four tiers, from Untrusted to Highly-Privileged Access [6].

| Tier | Example resources | Required posture |
|---|---|---|
| T0 Untrusted | Public docs | none |
| T1 Basic | Wiki, chat (web) | OS ≥ N-1, disk encrypted, *or* MAM/browser isolation for BYOD |
| T2 Managed | Source code, CRM | MDM-enrolled + compliant + EDR running + device cert |
| T3 Privileged | Prod SSH, cloud console | T2 + hardware-attested boot (TPM/DHA) + EDR risk = low + checks ≤ 5 min old |

2. **Choose signal sources by trustworthiness:** hardware attestation > MDM-verified > agent self-report > user-declared.
3. **Place PEPs:** SSO apps go through IdP conditional access. Legacy/non-SSO apps go behind an access proxy, because apps that can only validate a credential cannot consume posture, so enforcement moves to the gateway, proxy or IdP layer [3].
4. **Set freshness and revocation:** T3 is re-evaluated every few minutes, with session kill on posture drop (CAE or short-lived tokens).
5. **Define degraded modes:** compliant → normal access, partially compliant → limited, non-compliant → block or remediation [4].
6. **Fail-mode for PDP outage:** fail-closed for T3; fail-open with alerting is defensible for T1.
7. **Log every decision with its full input set** so the SOC can explain every deny.

---

## Common mistakes and gotchas

- **"Compliant" is only a label.** A compliance policy produces a status; Conditional Access turns it into a block, and grace-period / error-state handling decides how long a failing device keeps access [12].
- **Intune's tenant default is fail-open.** If the default stays at *Compliant*, any device with no assigned policy passes every Conditional Access check [13].
- **Grace periods are access decisions.** Error persisting past seven days becomes Not compliant, or In grace period if one is configured. Combined, a failing device can keep access for well over a week [12].
- **Token lifetime outlives posture.** Posture is checked at token issuance; without continuous access evaluation, a valid token survives a failed check until it expires [14].
- **Self-reported posture can be spoofed.** CISA's ZTMM places "self-reported device characteristics with limited enforcement" at the Initial stage [7].
- **Some checks need a reboot.** Windows Health Attestation settings are evaluated at boot, so a reboot may be needed after remediation before the device shows compliant [15].
- **Permissions:** reading BitLocker/TPM state needs admin/SYSTEM. Posture agents run privileged, which makes them high-value targets.
- **Mixed fleets:** the same rule means different things on Windows, macOS, Linux and mobile, because each reports differently [5].

---

## History and evolution

### Origin
No single inventor. Three lineages converged:
- **NAC era (mid-2000s):** Cisco NAC, Microsoft NAP (Windows Server 2008) and TCG Trusted Network Connect checked endpoint health *at the network port*: binary, one-time admission or quarantine.
- **Google BeyondCorp:** created in response to Operation Aurora (2009), documented in a series of ;login: articles from 2014 to 2018 [16]. The first paper, Rory Ward and Betsy Beyer, *BeyondCorp: A New Approach to Enterprise Security* (Dec 2014), allows only managed devices, built around a device inventory database [17]. Later papers: *Design to Deployment at Google* (Osborn, McWilliams, Beyer, Saltonstall, 2016), *The Access Proxy* (2016), *Migrating to BeyondCorp* (2017).
- **NIST formalisation:** SP 800-207 *Zero Trust Architecture*, by Scott Rose and Oliver Borchert (NIST ITL), Stu Mitchell (Stu2Labs) and Sean Connelly (CISA/DHS), August 2020 [18].

### Timeline

| Year | Milestone | What it added to posture |
|---|---|---|
| 2004–08 | Jericho Forum de-perimeterisation; NAP/NAC; TCG TNC | Endpoint health as an admission gate |
| 2008–10 | IETF NEA: RFC 5209 (requirements), RFC 5792 PA-TNC, RFC 5793 PB-TNC | Standard posture *attributes* and transport |
| 2010 | Forrester (John Kindervag) coins "Zero Trust" | Network-centric; devices not central yet |
| 2014–18 | BeyondCorp papers | Device inventory → Trust Inferer → trust tiers → access proxy; posture becomes **per-request and tiered** |
| 2020 | NIST SP 800-207 | Tenet: the enterprise collects asset-state information to improve security posture; continuous monitoring feeds the Policy Engine [19] |
| 2021 | EO 14028 (May); CISA ZTMM v1 (July) | Federal mandate to adopt ZTA [19][20] |
| 2023 | CISA ZTMM 2.0 (April); IETF RFC 9334 (RATS) | Devices pillar adds Policy Enforcement & Compliance Monitoring, Asset & Supply Chain Risk Management, Device Threat Protection [21]; remote attestation standardised |
| 2025 | NIST SP 1800-35 (June 10) | 19 example builds using commercial tools, mapped to CSF and SP 800-53 [22][23] |

**Direction of travel:** binary → tiered → continuous → hardware-attested → risk-scored. CISA's *Optimal* device stage: compliance continuously verified and enforced throughout the lifetime of devices and virtual assets [7].

### CISA ZTMM device maturity (summary)
| Stage | Device posture capability |
|---|---|
| Traditional | Limited visibility into device compliance; few enforcement methods |
| Initial | Self-reported device characteristics; limited enforcement |
| Advanced | Verified insights on initial access; compliance enforced for most devices |
| Optimal | Continuous verification and enforcement throughout device lifetime |

---

## How it works internally

```
 Posture producers                 PDP                         PEP                 Resource
 ─────────────────          ─────────────────           ──────────────          ──────────
 MDM compliance  ─┐         Policy Engine (PE)          Access proxy /
 EDR risk score  ─┼──────▶  + Policy Administrator ───▶ ZTNA gateway /   ───▶   App / SSH /
 ZTNA agent      ─┤         (PA)                        NAC / IdP token         cloud console
 TPM attestation ─┤            ▲  identity, threat
 Device cert     ─┘            │  intel, activity logs
                               └── continuous monitoring / re-evaluation (revoke mid-session)
```

- In 800-207 terms, posture is a **data source feeding the Policy Engine**, which makes the final grant/deny/revoke decision; the PA tears down sessions when the PE revokes [24].
- BeyondCorp's equivalents: a Device Inventory Service collects device state continuously; a Trust Inferer assigns the maximum trust tier; Access Policies; an Access Control Engine authorises in real time; an Access Proxy sits in front of every resource [25].
- **Evidence strength:** self-report (agent reads OS APIs) < MDM-verified < hardware-attested (TPM PCR quotes / measured boot via Device Health Attestation; Apple Managed Device Attestation; Android key attestation / Play Integrity).
- **Freshness:** checks run on a schedule (e.g. every 5 min in Cloudflare) plus at token issuance. The effective exposure window ≈ check interval + token lifetime + grace period (+ error timeout).

---

## Cross-platform comparison

| Platform | Native posture / attestation mechanism | Hardware root | Common gap |
|---|---|---|---|
| Windows | Intune compliance + Device Health Attestation; Entra device registration | TPM 2.0 (PCRs, measured boot) | Grace periods, default-compliant setting |
| macOS | MDM + Managed Device Attestation (macOS 14+) | Secure Enclave | Third-party agents need user-approved MDM |
| iOS/iPadOS | MDM + Managed Device Attestation (iOS 16+); App Attest | Secure Enclave | Limited OS visibility for agents |
| Android | Android Enterprise + Play Integrity API + key attestation | TEE / StrongBox | OEM and patch fragmentation |
| ChromeOS | Chrome Verified Access / Endpoint Verification | H1/Ti50 security chip | Fewer third-party integrations |
| Linux | osquery/agent checks; Intune for Ubuntu/RHEL; Keylime for TPM attestation | TPM (if used) | Weakest: mostly self-reported; firewall checks often unsupported |
| Workloads / cloud | SPIFFE/SPIRE node attestation; CSPM; confidential-VM attestation | vTPM / SEV-SNP / TDX | "Posture" = config drift, not a user device |

- **Same everywhere:** collect → normalise → evaluate → enforce.
- **Different:** who signs the evidence. Mobile and Apple platforms have vendor-attested evidence; on Linux, usually nobody does.

---

## Alternatives (other ways to get device assurance)

- **Network location** (trusted LAN): what Zero Trust replaces.
- **VPN + NAC:** posture checked once at connect, then flat network access.
- **Device certificate only:** proves *which* device, not whether it is *healthy*.
- **No posture, isolate instead:** VDI/DaaS, remote browser isolation, enterprise browsers (Island, Chrome Enterprise). Common for BYOD and contractors.
- **App-level protection (MAM):** protect the app container (Intune App Protection), not the device.

Products by function: Intune/Entra, Jamf, Kandji, Workspace ONE, Google Endpoint Management (MDM); CrowdStrike, SentinelOne, Defender (EDR); Cloudflare One, Zscaler, Netskope, Tailscale, Pomerium (ZTNA/proxy); Cisco ISE, Aruba ClearPass, Forescout (NAC); osquery, Kolide (query/agent); Keylime (Linux TPM attestation).

---

## Role: Security Architect

**Why it matters:** posture is the control that stops a phished-but-valid session from a compromised laptop from reaching crown jewels. The architect owns the trust model: which signals count, how fresh they must be, and what happens when they are missing.

**Day to day:**
- Map resource sensitivity to posture tiers; review new apps against them.
- Pick the PEP per app (IdP, proxy, NAC, service mesh), especially for legacy apps.
- Design the signal pipeline (MDM + EDR + ZTNA agent → PDP) and reconcile conflicting verdicts.
- Set posture-freshness SLAs against token lifetimes; decide where CAE or short tokens are required.
- Define fail modes, break-glass accounts, and the exception/waiver process.
- Map controls for auditors: NIST 800-207 / 1800-35, CISA ZTMM devices pillar, SP 800-53.

**What an expert knows that a beginner doesn't:**
1. **Ask who signs the evidence.** A check is only as strong as its weakest producer. A green "disk encrypted" from an unattested agent is a claim, not a fact.
2. **Posture has a half-life.** The real exposure window is check interval + token lifetime + grace period + error timeout; compute it per tier.
3. **Denials need an off-ramp.** Every block must say why and how to fix it, or users route around it (personal devices, shadow IT).
4. **Mixed fleets break uniform policy.** Test whether the platform makes consistent decisions across Windows MDM, macOS agents, Linux tooling and mobile managers [5].
5. **Don't gate everything.** Check the device when resource sensitivity justifies the cost, not on every login [4].
6. **The posture agent is attack surface.** It runs privileged and can be tampered with; its absence must itself count as a failing signal.

---

## Related topics (where it applies)

- **Standards:** NIST SP 800-207, SP 1800-35, CISA ZTMM 2.0 (devices pillar), DoD Zero Trust Reference Architecture, NIST CSF 2.0 (PR.AA, DE.CM), SP 800-53 (CM-8 inventory, CA-7 continuous monitoring, AC-19 mobile devices), IETF RFC 9334 (RATS), RFC 5209 (NEA).
- **Study areas:** SASE/SSE, ZTNA, conditional access, endpoint management, remote attestation and measured boot, continuous authorization, Network Access Control.
- **Certifications:** CISSP (Domains 3 & 5), CCSP, CSA CCZT, Microsoft SC-300 / MD-102, Zscaler ZTCA, (ISC)² ISSAP.

---

## Follow-up Q&A

### Q: postures in ZTA (opening question)
Answered in full above: definition and the overloaded meanings of "posture", the eight core signals with commands, the tiering design task, gotchas, history from NAC through BeyondCorp to NIST SP 800-207 / 1800-35 and CISA ZTMM 2.0, internal flow, the cross-platform table, alternatives, and the Security Architect lens.

Suggested next questions (not yet asked): how TPM measured boot and PCR quotes prove posture; how CAE revokes a token mid-session; how a red teamer spoofs posture checks.

---

## Sources

[1] NHI Mgmt Group, "Why do device checks matter in zero trust environments?" https://nhimg.org/?p=9877
[2] NHI Mgmt Group, "Device posture" (glossary). https://nhimg.org/glossary/device-posture/
[3] NHI Mgmt Group, FAQ on device checks and legacy apps. https://nhimg.org/faq/why-do-device-checks-matter-in-zero-trust-environments/
[4] NHI Mgmt Group, "Should organisations require device posture checks for every login?" https://nhimg.org/faq/should-organisations-require-device-posture-checks-for-every-login/
[5] NHI Mgmt Group, "How should teams evaluate Zero Trust IAM platforms for mixed device fleets?" https://nhimg.org/faq/how-should-teams-evaluate-zero-trust-iam-platforms-for-mixed-device-fleets/
[6] Google Security Blog, September 2019 (access tiers). https://security.googleblog.com/2019/09/
[7] CMS, "Zero Trust Maturity Devices Pillar." https://www.cms.gov/tra/ZeroTrust/ZT_0030_ZTMM_Devices_Pillar.htm
[8] Cloudflare Docs, "WARP client checks." https://developers.cloudflare.com/cloudflare-one/identity/devices/warp-client-checks/
[9] Cloudflare API, device posture resource. https://developers.cloudflare.com/api/node/resources/zero_trust/subresources/devices/subresources/posture
[10] alchemy.run, Cloudflare DevicePostureRule examples. https://v2.alchemy.run/providers/cloudflare/devices/deviceposturerule
[11] Microsoft Learn, "Require healthy and compliant devices with Intune." https://learn.microsoft.com/en-us/microsoft-365/solutions/manage-devices-with-intune-require-compliance
[12] Nerdio, "Intune compliance policies." https://getnerdio.com/blog/intune-compliance-policies/
[13] ManageEngine, "Intune compliance policy." https://www.manageengine.com/products/active-directory-audit/kb/microsoft-intune/microsoft-intune-compliance-policy.html
[14] WWT, "Advanced zero trust: device health and the eight hours inside it." https://www.wwt.com/article/advanced-zero-trust-device-health-and-the-eight-hours-inside-it
[15] "Intune compliance tiered framework." https://neckbeard.pages.dev/intune-compliance-tiered-framework/
[16] Wikipedia, "BeyondCorp." https://en.wikipedia.org/wiki/BeyondCorp
[17] R. Ward, B. Beyer, "BeyondCorp: A New Approach to Enterprise Security," ;login:, Dec 2014. https://www.usenix.net/system/files/login/articles/login_dec14_02_ward.pdf
[18] S. Rose, O. Borchert, S. Mitchell, S. Connelly, NIST SP 800-207 "Zero Trust Architecture," Aug 2020. https://doi.org/10.6028/NIST.SP.800-207
[19] "NIST SP 800-207" explainer (tenets, EO 14028). https://rolling-thunder-security.pages.dev/extras/nist_sp_800_207
[20] Forcepoint, "CISA evolves Zero Trust guidance." https://www.forcepoint.com/blog/insights/cisa-evolves-zero-trust-guidance
[21] Microsoft Learn, "CISA Zero Trust Maturity Model intro." https://learn.microsoft.com/en-us/security/zero-trust/cisa-zero-trust-maturity-model-intro
[22] NIST CSRC, "Implementing a Zero Trust Architecture: NIST Publishes SP 1800-35," June 10, 2025. https://csrc.nist.gov/News/2025/implementing-a-zero-trust-architecture-sp-1800-35
[23] Help Net Security, "19 ways to build zero trust," June 2025. https://www.helpnetsecurity.com/2025/06/13/zero-trust-implementation-guide/
[24] KindaTechnical, "NIST SP 800-207: Zero Trust Architecture." https://kindatechnical.com/cybersecurity-frameworks/nist-sp-800-207-zero-trust-architecture.html
[25] "BeyondCorp: Google Security For Everyone Else" (slides). https://www.slideshare.net/slideshow/beyondcorp-google-security-for-everyone-else/75898805

**Notes on certainty:** NIST/CISA dates, BeyondCorp paper details, the Cloudflare check matrix and the Intune behaviours come from the sources above. The NAC/NAP/TNC history, IETF RFC numbers (5209, 5792, 5793, 9334), Apple Managed Device Attestation OS versions, the ChromeOS and Linux attestation details and the certification list come from general knowledge and were not re-verified in this session. Sample command outputs are representative, not captured from a live machine.
