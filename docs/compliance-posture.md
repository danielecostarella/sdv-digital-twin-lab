# Cybersecurity Compliance Posture

> This document maps the SDV Digital Twin Lab architecture to the two dominant
> automotive cybersecurity standards. It is intentionally framed at the
> *capability* level — demonstrating the posture a production system would adopt,
> not claiming full certification.

---

## ISO 21434 — Road Vehicle Cybersecurity Engineering

### Clause 8 — Continual Cybersecurity Activities

| Activity | Capability in this project |
|---|---|
| **8.3 Cybersecurity monitoring** | The `infotainment-dashboard` subscribes to all signals and can be extended to feed a SIEM/VSOC. Signal anomalies (out-of-range values) are detectable at the broker subscription layer. |
| **8.5 Vulnerability management** | GitHub Dependabot can be enabled on `requirements.txt` to surface CVEs in Python dependencies. Docker image pins (`0.6.1`) enable reproducible builds and scheduled re-evaluation. |

### Clause 10 — Product Development at the Vehicle Level

| Activity | Capability in this project |
|---|---|
| **10.4 Integration & verification** | The `integration-test.yml` workflow enforces signal-level contract testing on every push to `main`. A regression in signal range or broker connectivity fails the CI gate before merge. |
| **10.5 Cybersecurity validation** | Architecture Decision Records (ADRs) document threat-informed design choices (e.g., ADR 001: schema enforcement at ingestion; ADR 002: authentication extension point in the WS bridge). |

---

## UN Regulation No. 155 (UN R155) — Cybersecurity Management System

UN R155 requires OEMs to implement a **CSMS (Cybersecurity Management System)**
covering the vehicle lifecycle. Key obligations and how this architecture maps:

### Article 7 — Vehicle Type Cybersecurity

| R155 Requirement | Architecture mapping |
|---|---|
| **Identify and manage cyber risks** | The VSS schema acts as a signal whitelist: only signals declared in `vss_release_4.0.json` are accepted by the broker. Unknown signals are rejected at ingestion. |
| **Detect and respond to cyber attacks** | The broker subscription model makes it straightforward to attach an anomaly detector: subscribe to all signals, apply a rules engine (threshold violations, temporal anomalies), emit structured alerts. |
| **Protect data and software** | The `--insecure` flag is development-only. In production the broker supports mTLS and JWT-based access control, which would be enabled via the `--tls-cert` and `--jwt-public-key` flags. |
| **Support software updates** | The container-based architecture makes OTA updates a Docker image pull + rolling restart — no hardware reflash required. |

### Annex 5 — Mitigations for Threat Categories

| Threat category | Mitigation |
|---|---|
| Spoofing (unauthorised signal injection) | Production: JWT token required for `set_current_values`. Dev: network-isolated Docker bridge. |
| Tampering (signal value modification) | VSS type enforcement rejects malformed Datapoints. |
| Information disclosure | Dashboard serves read-only signal data; write access restricted to the gateway service account. |
| Denial of service | `restart: on-failure` ensures gateway and dashboard recover from crashes. Broker health-check gates dependent services. |

---

## Further Evolution (roadmap suggestions)

1. **Enable KUKSA JWT auth** — generate a signing key, configure the broker with
   `--jwt-public-key`, issue separate tokens to gateway (write) and dashboard (read).
2. **Add Falco rules** — detect anomalous container syscalls (e.g. unexpected network
   connections from the gateway container).
3. **SBOM generation** — add `syft` to the CI pipeline to produce a Software Bill of
   Materials for each image, satisfying NTIA/EC supply-chain transparency requirements.
4. **Signal anomaly alerting** — implement a lightweight rules engine service that
   subscribes to all signals and emits structured JSON alerts to stdout (Loki/ELK
   compatible).
