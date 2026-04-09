# SDV Digital Twin Lab

[![CI](https://github.com/danielecostarella/sdv-digital-twin-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/danielecostarella/sdv-digital-twin-lab/actions/workflows/ci.yml)
[![Integration Tests](https://github.com/danielecostarella/sdv-digital-twin-lab/actions/workflows/integration-test.yml/badge.svg)](https://github.com/danielecostarella/sdv-digital-twin-lab/actions/workflows/integration-test.yml)

> A production-grade **Digital Twin reference architecture** for Software-Defined
> Vehicles, built entirely on open-source tooling: Eclipse KUKSA, COVESA VSS,
> FastAPI, and Docker.

This project is a **learning lab** — a reproducible blueprint for understanding
how modern automotive software stacks are evolving from hardware-centric ECU
architectures to cloud-native, software-defined platforms. Every design decision
is documented and every component runs with `docker compose up`.

Companion project (C++ embedded gateway side): [sdv-gateway-cpp](https://github.com/danielecostarella/sdv-gateway-cpp)

---

## What is a Software-Defined Vehicle?

A Software-Defined Vehicle (SDV) is one where the majority of vehicle functions —
historically determined at design time by dedicated hardware (ECUs, body controllers,
powertrain modules) — are instead delivered, updated, and reconfigured through
software running on high-performance compute platforms.

The SDV model enables a fundamentally different lifecycle: features ship over-the-air,
diagnostics happen remotely, and new functionality can be added after the vehicle
leaves the factory floor. Initiatives like COVESA, AUTOSAR Adaptive, and the SOAFEE
working group are standardising the middleware and signal semantics that make this
interoperability possible.

## What is a Vehicle Digital Twin?

A Vehicle Digital Twin is a real-time, authoritative software mirror of a vehicle's
state — its speed, battery level, sensor readings, actuator positions — maintained
in the cloud or on an HPC unit. Unlike a static simulation, a digital twin receives
live data and reflects the current state of the physical vehicle at any point in time.

The key architectural benefit is **shift-left development**: software teams can
develop, test, and validate against the digital twin before physical hardware is
available. This compresses development cycles, reduces hardware prototype costs, and
enables continuous integration testing of vehicle software — all of which translate
directly into reduced time-to-market and higher software quality.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Docker Compose Network                        │
│                                                                     │
│  ┌─────────────────┐   gRPC                  ┌──────────────────┐  │
│  │                 │  set_current_values      │                  │  │
│  │ gateway-emulator│ ───────────────────────▶ │ KUKSA Databroker │  │
│  │   (Provider)    │                          │  (Digital Twin)  │  │
│  │                 │                          │  VSS 4.0 schema  │  │
│  │ Simulates ECU   │                          │  Single Source   │  │
│  │ sensor readings │                          │  of Truth        │  │
│  └─────────────────┘                          └────────┬─────────┘  │
│                                                        │            │
│                                               gRPC subscribe        │
│                                                        │            │
│                                                        ▼            │
│                                              ┌──────────────────┐  │
│                                              │  infotainment-   │  │
│                                              │  dashboard       │  │
│                                              │  (Consumer)      │  │
│                                              │  FastAPI + WS    │  │
│                                              └────────┬─────────┘  │
└───────────────────────────────────────────────────────┼────────────┘
                                                        │ WebSocket
                                                        ▼
                                                 Browser :8080
```

### Components

| Service | Role | Technology |
|---|---|---|
| **KUKSA Databroker** | Digital Twin Core — validates and stores vehicle state against the VSS schema | Eclipse KUKSA 0.6.1, gRPC |
| **Gateway Emulator** | Signal Provider — simulates ECU/sensor data and publishes to the broker | Python 3.11, kuksa-client |
| **Infotainment Dashboard** | Signal Consumer — real-time browser UI with live charts | FastAPI, WebSocket, Chart.js |

### Design Principles

- **Single Source of Truth**: all state flows through the broker. The dashboard
  never talks to the gateway directly.
- **Schema enforcement**: the VSS JSON schema rejects malformed signal types at
  ingestion. Consumers receive typed data, not raw strings.
- **Zero build-step frontend**: the dashboard is plain HTML/CSS/JS loaded via CDN.
  No npm, no bundler — the architecture is the demo.

---

## VSS Signals Implemented

All signals conform to [COVESA VSS 4.0](https://github.com/COVESA/vehicle_signal_specification).

| Signal path | Type | Unit | Range | Simulation |
|---|---|---|---|---|
| `Vehicle.Speed` | float | km/h | 0..250 | Sinusoidal, 120 s period |
| `Vehicle.Powertrain.ElectricMotor.Speed` | int32 | rpm | 0..20 000 | Proportional to speed |
| `Vehicle.Body.Lights.Beam.High.IsOn` | bool | — | — | True when speed > 90 km/h |
| `Vehicle.CurrentLocation.Latitude` | double | ° | ±90 | Gaussian walk from Munich |
| `Vehicle.CurrentLocation.Longitude` | double | ° | ±180 | Gaussian walk from Munich |
| `Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` | float | % | 0..100 | Linear decay −1 %/min |

---

## Business Value

### Shift-Left Testing

By decoupling software development from hardware availability, digital twins allow
engineering teams to begin integration testing months before physical prototypes
are ready. A CI/CD pipeline can spin up the full stack in under two minutes and
validate signal contracts on every pull request.

### Reduced Time-to-Market

OTA software updates can be regression-tested against the digital twin before
deployment to a vehicle fleet. Issues that would previously require a vehicle recall
are caught in the integration pipeline.

### Lower Development Cost

Hardware-in-the-loop (HIL) test benches cost tens of thousands of euros and require
dedicated lab space. A containerised digital twin replicates the signal interface for
the cost of a CI runner.

### Regulatory Readiness

The architecture provides a natural extension point for a Vehicle Security Operations
Centre (VSOC) — a requirement under UN R155. See [compliance posture](docs/compliance-posture.md).

---

## Cybersecurity & Compliance

This project demonstrates the architectural posture required by:

- **ISO 21434** — Road Vehicle Cybersecurity Engineering (Clause 8: monitoring; Clause 10: integration verification)
- **UN Regulation No. 155** — CSMS requirements for type approval

Key capabilities:

- VSS schema acts as a signal whitelist at ingestion
- JWT access control is available in the broker (disabled in dev via `--insecure`)
- Integration tests enforce signal-range contracts as a CI gate
- ADRs document threat-informed design decisions

Full mapping: [docs/compliance-posture.md](docs/compliance-posture.md)

---

## Getting Started

### Prerequisites

- Docker Engine 24+
- Docker Compose v2
- `curl` (for VSS download)

### One-Command Start

```bash
# 1. Download the VSS schema (run once)
bash scripts/download-vss.sh

# 2. Build and start all services
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) to see the live dashboard.

The gateway starts publishing signals within ~2 seconds of the broker becoming healthy.

### Verify via KUKSA CLI

```bash
pip install kuksa-client

# Interactive shell
kuksa-client --host localhost --port 55555 --insecure

# Inside the shell:
getValue Vehicle.Speed
getValue Vehicle.Powertrain.TractionBattery.StateOfCharge.Current
```

### Stop

```bash
docker compose down
```

---

## Running Tests

### Unit Tests

```bash
pip install pytest pytest-asyncio httpx
pip install -r services/gateway-emulator/requirements.txt
pip install -r services/infotainment-dashboard/requirements.txt

pytest services/ -v
```

### Integration Tests (requires running stack)

```bash
bash scripts/download-vss.sh
docker compose up -d --build
sleep 8  # wait for gateway to publish first signals

pip install pytest pytest-asyncio httpx kuksa-client
pytest tests/integration/ -v --timeout=30

docker compose down
```

---

## CI/CD

Two GitHub Actions pipelines run on every push:

| Pipeline | Trigger | What it checks |
|---|---|---|
| **CI** | Every push + PR | ruff lint, unit tests (matrix), Docker build validation |
| **Integration Tests** | Push to `main` + PR | Full stack startup, signal publication, dashboard health |

The integration pipeline is the quality gate: it spins up the complete Docker Compose
stack, waits for the broker, and verifies that all six VSS signals are published and
within valid physical ranges.

---

## Repository Structure

```
.
├── services/
│   ├── databroker/vss/          # VSS JSON (downloaded at build time, git-ignored)
│   ├── gateway-emulator/        # Python signal provider
│   └── infotainment-dashboard/  # FastAPI + WebSocket + static UI
├── tests/integration/           # End-to-end signal flow tests
├── scripts/download-vss.sh      # VSS schema download helper
├── docs/
│   ├── adr/                     # Architecture Decision Records
│   └── compliance-posture.md   # ISO 21434 / UN R155 mapping
├── docker-compose.yml
└── docker-compose.override.yml  # Dev hot-reload overrides
```

---

## Architecture Decision Records

Design choices are documented as ADRs so that the reasoning is preserved alongside the code:

- [ADR 001 — KUKSA over raw MQTT](docs/adr/001-kuksa-over-mqtt.md)
- [ADR 002 — FastAPI WebSocket bridge](docs/adr/002-fastapi-ws-bridge.md)

---

## Relation to sdv-gateway-cpp

[sdv-gateway-cpp](https://github.com/danielecostarella/sdv-gateway-cpp) implements
the embedded gateway side of the same architecture in C++: CAN/SOME-IP signal parsing,
DDS bridging, and ECU abstraction. Together, the two repositories demonstrate the
complete vehicle-to-cloud signal path — from raw hardware signals in C++ to a live
browser dashboard in Python.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-signal`)
3. Ensure `ruff check` and `pytest services/` pass
4. Open a pull request

---

## License

[Apache License 2.0](LICENSE)
