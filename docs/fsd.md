# Functional Specification Document — SDV Digital Twin Lab

**Document ID:** SDV-DTL-FSD-001  
**Version:** 1.0  
**Date:** 2026-04-09  
**Status:** Approved  
**Author:** Daniele Costarella

---

## 1. Purpose and Scope

### 1.1 Purpose

This document specifies the functional and non-functional requirements of the
**SDV Digital Twin Lab** — a containerised reference architecture demonstrating
the Provider / Broker / Consumer pattern for Software-Defined Vehicle (SDV) platforms.

It serves two audiences:

- **Technical audience:** engineers implementing or extending the system
- **Management audience:** stakeholders evaluating the architectural approach, technology choices, and compliance posture

### 1.2 Scope

In scope:

- Eclipse KUKSA Databroker as digital twin core
- Python gateway emulator publishing COVESA VSS 4.0 signals
- FastAPI + WebSocket infotainment dashboard consuming those signals
- CI/CD pipeline (GitHub Actions) for automated quality gates
- Compliance posture documentation (ISO 21434, UN R155)

Out of scope:

- Production-grade multi-vehicle fleet management
- Physical CAN/LIN/SOME-IP bus integration (addressed by [sdv-gateway-cpp](https://github.com/danielecostarella/sdv-gateway-cpp))
- Mobile or embedded infotainment runtimes
- OTA update infrastructure

### 1.3 Definitions

| Term | Definition |
|---|---|
| **Digital Twin** | A real-time software mirror of a physical vehicle's state, maintained in software and accessible via a defined API |
| **SSoT** | Single Source of Truth — the broker is the only authoritative source of vehicle signal state |
| **VSS** | COVESA Vehicle Signal Specification — a hierarchical, typed schema for vehicle signals |
| **Datapoint** | A VSS-typed value (float, int32, bool, double, string) published to or read from the broker |
| **Provider** | A service that publishes signal values to the broker (`set_current_values`) |
| **Consumer** | A service that reads signal values from the broker (`get_current_values` or `subscribe_current_values`) |
| **Fan-out bridge** | The FastAPI pattern that holds one gRPC subscription and broadcasts updates to N WebSocket clients |

---

## 2. System Context

The system operates in the context of an evolving automotive software lifecycle. Traditional OEM development is hardware-centric: software cannot be validated without physical ECU prototypes. This project demonstrates that a digital twin enables **shift-left development** — software validation begins months before hardware is available.

```
Traditional lifecycle:
  Hardware ready ──────────────────────▶ Software integration ──▶ Test ──▶ Ship
                                                (blocked)

SDV Digital Twin lifecycle:
  Sprint 1: Digital Twin available ──▶ Software integration ──▶ Test
  Sprint N: Hardware arrives       ──▶ Validation against twin ──▶ Ship
```

---

## 3. Stakeholders

| Role | Interest |
|---|---|
| **Software Engineer** | Clear API contract, reproducible local dev environment, test coverage |
| **Domain Leader** | Architecture quality, technology currency, documentation completeness |
| **Engineering Manager** | Time-to-market impact, cost reduction, regulatory alignment, CI/CD maturity |
| **Cybersecurity Engineer** | Signal integrity, access control posture, compliance traceability |
| **Student / OSS Contributor** | Learning SDV stack from first principles using public tooling |

---

## 4. Functional Requirements

### FR-001 — Signal Publication

**Priority:** MUST  
**Component:** gateway-emulator

The gateway emulator SHALL publish the following VSS 4.0 signals to the KUKSA Databroker at a configurable frequency (default: 1 Hz):

| Signal Path | VSS Type | Unit | Valid Range |
|---|---|---|---|
| `Vehicle.Speed` | float | km/h | 0.0 – 250.0 |
| `Vehicle.Powertrain.ElectricMotor.Speed` | int32 | rpm | 0 – 20 000 |
| `Vehicle.Body.Lights.Beam.High.IsOn` | bool | — | true / false |
| `Vehicle.CurrentLocation.Latitude` | double | ° | −90.0 – 90.0 |
| `Vehicle.CurrentLocation.Longitude` | double | ° | −180.0 – 180.0 |
| `Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` | float | % | 0.0 – 100.0 |

All signals SHALL be published in a single batch gRPC call per cycle.

### FR-002 — Signal Simulation Fidelity

**Priority:** SHOULD  
**Component:** gateway-emulator

Signal values SHALL exhibit physically plausible behaviour:

- Speed SHALL follow a sinusoidal profile with 120 s period and 0–120 km/h range
- Motor RPM SHALL be proportional to speed with Gaussian noise (σ = 20 rpm)
- High beam SHALL activate automatically when speed exceeds 90 km/h
- GPS SHALL perform a bounded random walk around a fixed origin (Munich: 48.1351°N, 11.5820°E)
- Battery SoC SHALL decay linearly at −1 % per minute with a floor of 10 %
- Simulation SHALL be reproducible given the same elapsed time `t` (deterministic seeding)

### FR-003 — Schema Enforcement

**Priority:** MUST  
**Component:** KUKSA Databroker

The broker SHALL reject any `set_current_values` call that:

- References a signal path not declared in the loaded VSS JSON (`vss_rel_4.0.json`)
- Provides a value of incorrect type for a declared signal

### FR-004 — Real-Time Dashboard

**Priority:** MUST  
**Component:** infotainment-dashboard

The dashboard SHALL:

- Display live values for all six VSS signals within 1 second of publication
- Connect to the broker via a server-side WebSocket bridge (not directly via gRPC)
- Show the following widgets: speed gauge, battery SoC bar, motor RPM readout, high beam indicator, GPS coordinates, speed history sparkline
- Reconnect automatically if the WebSocket connection drops, within 5 seconds

### FR-005 — REST State Snapshot

**Priority:** MUST  
**Component:** infotainment-dashboard

The dashboard SHALL expose `GET /api/state` returning the latest values of all monitored signals as a JSON object. This endpoint SHALL be usable for integration testing and programmatic polling.

### FR-006 — Health Endpoint

**Priority:** MUST  
**Component:** infotainment-dashboard

The dashboard SHALL expose `GET /health` returning `{"status": "ok"}` with HTTP 200 when the service is running, regardless of broker connectivity.

### FR-007 — Graceful Startup

**Priority:** MUST  
**Components:** gateway-emulator, infotainment-dashboard

Both services SHALL implement retry logic on broker connection failure. They SHALL restart automatically (`restart: on-failure`) until the broker is available, without manual intervention.

### FR-008 — VSS Schema Distribution

**Priority:** MUST  
**Component:** build / CI

The VSS schema JSON SHALL NOT be committed to the repository. It SHALL be downloaded at build time via `scripts/download-vss.sh` from the official COVESA GitHub release. This ensures the schema is always obtained from the authoritative source and avoids licensing ambiguity.

### FR-009 — CI Quality Gates

**Priority:** MUST  
**Component:** GitHub Actions

The CI pipeline SHALL enforce the following gates on every pull request:

| Gate | Tool | Failure condition |
|---|---|---|
| Lint | ruff | Any E, F, W, I, UP violation |
| Unit tests | pytest | Any test failure in `services/*/tests/` |
| Docker build | docker build | Any image build failure |
| Integration: broker reachable | pytest + kuksa-client | Broker not accepting gRPC connections |
| Integration: signals published | pytest + kuksa-client | Any of the 6 signals returning None |
| Integration: signal ranges | pytest | Any signal value outside physical bounds |
| Integration: dashboard health | httpx | `GET /health` not returning 200 |

### FR-010 — Developer Hot-Reload

**Priority:** SHOULD  
**Component:** docker-compose.override.yml

In local development mode, source code changes to the gateway and dashboard SHALL take effect without rebuilding Docker images, via volume mounts and uvicorn `--reload`.

---

## 5. Non-Functional Requirements

### NFR-001 — Latency

| Path | Requirement |
|---|---|
| Sensor publish → broker store | < 50 ms (p95, local network) |
| Broker store → dashboard WebSocket | < 100 ms (p95, local network) |
| Browser render after WebSocket message | < 16 ms (one animation frame) |

### NFR-002 — Startup Time

The full stack (`docker compose up --build` with cached layers) SHALL be operational within 30 seconds of the command being issued on a developer workstation.

### NFR-003 — Reproducibility

Any developer with Docker Engine 24+ and Docker Compose v2 SHALL be able to run the complete stack with three commands:

```bash
git clone https://github.com/danielecostarella/sdv-digital-twin-lab
bash scripts/download-vss.sh
docker compose up --build
```

No additional tools, language runtimes, or cloud accounts SHALL be required.

### NFR-004 — Observability

All services SHALL emit structured log lines to stdout with the format:

```
%(asctime)s [<service-name>] %(levelname)s %(message)s
```

Log level SHALL be configurable via the `LOG_LEVEL` environment variable (default: `INFO`).

### NFR-005 — Portability

The system SHALL run on Linux (x86\_64, arm64) and macOS (Apple Silicon) without architecture-specific configuration.

### NFR-006 — Security Posture (Development)

In the development configuration:
- The broker runs with `--insecure` (no TLS, no JWT)
- The dashboard does not require authentication
- All services are isolated within the `sdv-net` Docker bridge network

In a production configuration, the following SHALL be enabled:
- mTLS between all services and the broker
- JWT-based access control with separate read/write tokens per service
- HTTPS termination at the dashboard reverse proxy

### NFR-007 — Maintainability

- All component versions SHALL be explicitly pinned (Docker image tags, Python package versions with `>=` lower bounds)
- Architecture decisions SHALL be documented as ADRs in `docs/adr/`
- Code SHALL pass `ruff check` with the project's `ruff.toml` configuration
- Test coverage SHALL exist for all signal simulation functions and all FastAPI endpoints

---

## 6. Use Cases

### UC-001 — Developer validates new VSS signal

**Actor:** Software Engineer  
**Precondition:** Stack is running  
**Flow:**

1. Engineer adds a new signal to `signals.py` and `publisher.py`
2. Engineer restarts the gateway container (`docker compose restart gateway-emulator`)
3. Broker validates the signal path against VSS schema
4. If path is invalid → broker rejects, gateway logs error
5. If path is valid → dashboard receives the new signal on next WebSocket message
6. Engineer opens `GET /api/state` to confirm the new signal appears

**Postcondition:** New signal visible in dashboard and integration test assertions

---

### UC-002 — CI validates a pull request

**Actor:** GitHub Actions  
**Precondition:** Developer opens a pull request  
**Flow:**

1. `ci.yml` runs: ruff lint → unit tests → Docker build validation
2. `integration-test.yml` runs: downloads VSS → starts stack → waits for broker → runs pytest
3. `test_all_signals_are_published` verifies all 6 signals have non-None values
4. `test_speed_in_valid_range` verifies 0 ≤ speed ≤ 250
5. `test_dashboard_health` verifies `GET /health` returns 200

**Success:** All checks green → PR can be merged  
**Failure:** Any check fails → PR blocked, developer fixes issue

---

### UC-003 — Student understands digital twin architecture

**Actor:** Student / OSS Contributor  
**Precondition:** Repository cloned  
**Flow:**

1. Student reads README → understands SDV and digital twin concepts
2. Student reads `docs/architecture.md` → understands component roles and data flow
3. Student runs `docker compose up` → sees live dashboard
4. Student reads `services/gateway-emulator/src/signals.py` → understands simulation math
5. Student reads `services/infotainment-dashboard/src/broker_client.py` → understands gRPC subscription pattern
6. Student modifies a signal formula → observes dashboard updating

**Postcondition:** Student understands the full signal lifecycle from simulation to browser

---

### UC-004 — Engineering Manager presents to stakeholders

**Actor:** Engineering Manager  
**Precondition:** Stack is running  
**Flow:**

1. Manager opens `http://localhost:8080` — live dashboard visible
2. Manager opens `docs/compliance-posture.md` — ISO 21434 / UN R155 mapping
3. Manager opens GitHub Actions — green CI/CD badges visible
4. Manager references `docs/adr/` — design decisions with rationale
5. Manager explains shift-left value: "this is what our teams can test before hardware arrives"

---

## 7. Interface Definitions

### 7.1 Gateway → Broker (gRPC)

```protobuf
// Simplified representation of the KUKSA gRPC API
service VAL {
  rpc SetCurrentValues(SetCurrentValuesRequest)
    returns (SetCurrentValuesResponse);
}

message SetCurrentValuesRequest {
  map<string, Datapoint> datapoints = 1;
}

message Datapoint {
  oneof value {
    float   float_value  = 1;
    int32   int32_value  = 2;
    bool    bool_value   = 3;
    double  double_value = 4;
    string  string_value = 5;
  }
}
```

Full API definition: [KUKSA.val proto files](https://github.com/eclipse-kuksa/kuksa-databroker/tree/main/proto)

### 7.2 Broker → Dashboard (gRPC streaming)

```protobuf
service VAL {
  rpc SubscribeCurrentValues(SubscribeCurrentValuesRequest)
    returns (stream SubscribeCurrentValuesResponse);
}
```

The broker pushes a `SubscribeCurrentValuesResponse` containing only the changed signals whenever a provider calls `SetCurrentValues`.

### 7.3 Dashboard → Browser (WebSocket JSON)

**Endpoint:** `ws://<host>:8080/ws`  
**Direction:** Server → Client (broadcast on every broker update)  
**Format:** JSON object with signal paths as keys

```json
{
  "Vehicle.Speed": 61.4,
  "Vehicle.Powertrain.ElectricMotor.Speed": 3070,
  "Vehicle.Body.Lights.Beam.High.IsOn": false,
  "Vehicle.CurrentLocation.Latitude": 48.135316,
  "Vehicle.CurrentLocation.Longitude": 11.582108,
  "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current": 84.97
}
```

Null values indicate the signal has not yet been received from the broker.

### 7.4 Dashboard REST API

| Endpoint | Method | Response | Description |
|---|---|---|---|
| `/health` | GET | `{"status": "ok"}` | Liveness probe |
| `/api/state` | GET | Signal JSON object | Latest known values for all signals |
| `/ws` | WS | Signal JSON stream | Real-time broadcast |
| `/` | GET | `text/html` | Dashboard HTML |

---

## 8. Error Handling

| Scenario | Component | Behaviour |
|---|---|---|
| Broker unavailable at startup | gateway-emulator | `kuksa-client` raises `AioRpcError`; container exits with code 1; Docker restarts with `on-failure` policy |
| Broker unavailable at startup | infotainment-dashboard | Same restart behaviour; `GET /health` returns 200 regardless (liveness ≠ readiness) |
| Invalid VSS signal path published | KUKSA Databroker | Broker returns gRPC error `NOT_FOUND (404)`; gateway logs the error and continues |
| WebSocket client disconnects | infotainment-dashboard | `WebSocketDisconnect` exception caught; client removed from `ConnectionManager._active` set |
| Broker subscription drops | infotainment-dashboard | `subscribe_loop` raises; FastAPI lifespan task is cancelled and recreated on next startup |

---

## 9. Constraints and Assumptions

- The system is designed for **single-vehicle, single-broker** operation. Fleet scenarios are out of scope.
- Docker Desktop for macOS reserves port 55555 in the hypervisor layer; the host mapping uses port 55556. This does not affect container-to-container communication.
- The VSS JSON file must be downloaded before `docker compose up`. The CI pipeline does this automatically via `scripts/download-vss.sh`.
- The KUKSA Databroker image is distroless (no shell). Health checks must use TCP probes or be performed by a companion container.
- Signal simulation is mathematically deterministic for a given elapsed time `t`, but GPS jitter uses a per-tick random seed which varies between runs.

---

## 10. Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-04-09 | Daniele Costarella | Initial release |
