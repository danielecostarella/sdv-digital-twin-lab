# Architecture — SDV Digital Twin Lab

**Version:** 1.0  
**Date:** 2026-04-09  
**Status:** Current

---

## 1. Overview

The SDV Digital Twin Lab implements the **Provider / Broker / Consumer** pattern that is at the heart of every modern Software-Defined Vehicle platform. A simulated vehicle gateway publishes real-time sensor data to a semantically-typed digital twin. Multiple consumers — a browser dashboard today, a cybersecurity monitor or ADAS simulator tomorrow — read from the twin without any coupling to the data source.

```
  Physical World (simulated)          Digital World
  ───────────────────────────         ──────────────────────────────────────
                                         ┌─────────────────────────────┐
  ┌──────────────────────────┐           │      KUKSA Databroker       │
  │     Vehicle ECUs         │  CAN/LIN  │   (Digital Twin — SSoT)     │
  │  Speed sensor            │ ────────▶ │                             │
  │  Battery BMS             │  SOME/IP  │  VSS 4.0 schema enforcement │
  │  GPS receiver            │           │  gRPC API (typed Datapoints)│
  │  Body controller         │           │  In-memory signal store     │
  └──────────────────────────┘           └──────────┬──────────────────┘
           │                                        │
           │  [In this lab: Python emulator]        │  subscribe_current_values
           │  [In production: C++ gateway]          │  (streaming gRPC)
           ▼                                        ▼
  ┌──────────────────────────┐           ┌─────────────────────────────┐
  │   gateway-emulator       │           │   infotainment-dashboard    │
  │                          │           │                             │
  │  signals.py              │           │  broker_client.py           │
  │  compute_state(t)        │           │  subscribe_loop()           │
  │                          │           │                             │
  │  publisher.py            │           │  websocket_bridge.py        │
  │  set_current_values()    │           │  ConnectionManager          │
  │  @ 1 Hz via gRPC         │           │  broadcast()                │
  └──────────────────────────┘           │                             │
                                         │  FastAPI (uvicorn)          │
                                         │  GET /health                │
                                         │  GET /api/state             │
                                         │  WS  /ws                    │
                                         └──────────┬──────────────────┘
                                                    │  WebSocket JSON
                                                    ▼
                                         ┌─────────────────────────────┐
                                         │       Browser               │
                                         │   dashboard.js              │
                                         │   Chart.js gauges           │
                                         │   Speed, RPM, SoC, GPS…    │
                                         └─────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 KUKSA.val Databroker — Digital Twin Core

| Property | Value |
|---|---|
| Image | `ghcr.io/eclipse-kuksa/kuksa-databroker:0.6.1` |
| Protocol | gRPC over HTTP/2 |
| Internal port | 55555 |
| Host port | 55556 (macOS Docker Desktop workaround) |
| Auth mode | `--insecure` (dev) / JWT (production) |
| VSS schema | COVESA VSS 4.0 (`vss_rel_4.0.json`) |
| Language | Rust (distroless container, no shell) |

**Responsibilities:**
- Receive typed `Datapoint` values from providers via `set_current_values` RPC
- Validate values against the VSS schema (type, path existence)
- Store the latest value for each registered signal
- Stream updates to subscribers via `subscribe_current_values` server-side streaming RPC
- Reject unknown signal paths or type mismatches at ingestion

**Why it is the Single Source of Truth:**  
No consumer ever calls the gateway directly. The broker is the only source of vehicle state. This means a consumer can be developed, tested, and deployed independently of the gateway implementation — the interface contract is the VSS schema.

---

### 2.2 Gateway Emulator — Signal Provider

| Property | Value |
|---|---|
| Language | Python 3.11 |
| Library | `kuksa-client 0.5.x` (`kuksa_client.grpc.aio.VSSClient`) |
| Publish frequency | 1 Hz (configurable via `PUBLISH_INTERVAL_SEC`) |
| Restart policy | `on-failure` (retries until broker is up) |

**Signal simulation logic** (`signals.py`):

| Signal | Formula |
|---|---|
| `Vehicle.Speed` | `60 + 60·sin(2π·t/120)` — 0..120 km/h, 120 s period |
| `Vehicle.Powertrain.ElectricMotor.Speed` | `speed × 50 + Gauss(0, 20)` rpm |
| `Vehicle.Body.Lights.Beam.High.IsOn` | `speed > 90.0` |
| `Vehicle.CurrentLocation.Latitude` | `48.1351 + Gauss(0, 0.0005)` (Munich origin) |
| `Vehicle.CurrentLocation.Longitude` | `11.5820 + Gauss(0, 0.0005)` |
| `Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` | `max(10, 85 − t/60)` % |

The random seed for GPS jitter is derived from `t` so replays are deterministic.

**gRPC call pattern:**
```
client.set_current_values({
    "Vehicle.Speed": Datapoint(60.5),
    ...
})
```
All signals are published in a single batch RPC call per cycle, minimising round-trips.

---

### 2.3 Infotainment Dashboard — Signal Consumer

| Property | Value |
|---|---|
| Language | Python 3.11 (backend) + HTML/CSS/JS (frontend) |
| Framework | FastAPI 0.100+ + uvicorn |
| Real-time | WebSocket (`/ws` endpoint) |
| REST snapshot | `GET /api/state` |
| Frontend | Vanilla JS + Chart.js 4.4 (CDN) |
| Port | 8080 |

**Fan-out bridge pattern:**

```
KUKSA gRPC subscribe (1 stream)
        │
        ▼
broker_client.subscribe_loop()          # single persistent gRPC subscription
        │  on_update(payload: dict)
        ▼
state.vehicle_state.update(payload)     # in-memory snapshot update
        │
        ▼
manager.broadcast(vehicle_state.copy()) # fan-out to N browser WebSockets
        │
        ├──▶ Browser A WebSocket
        ├──▶ Browser B WebSocket
        └──▶ Browser N WebSocket
```

One gRPC subscription serves arbitrarily many browser clients. The dashboard never opens more than one gRPC connection to the broker regardless of how many browser tabs are open.

**Frontend widget inventory:**

| Widget | Signal | Rendering |
|---|---|---|
| Speed gauge | `Vehicle.Speed` | Chart.js doughnut, 0..130 km/h |
| Battery bar | `Vehicle.Powertrain.TractionBattery.StateOfCharge.Current` | CSS progress, green→yellow→red |
| Motor RPM | `Vehicle.Powertrain.ElectricMotor.Speed` | Numeric readout |
| High beam LED | `Vehicle.Body.Lights.Beam.High.IsOn` | SVG circle, yellow/grey |
| GPS | `Vehicle.CurrentLocation.Latitude/Longitude` | Numeric display (6 decimal places) |
| Speed sparkline | `Vehicle.Speed` (last 60 values) | Chart.js line chart |

**Auto-reconnect:** If the WebSocket drops, `dashboard.js` retries after 2 s with exponential backoff.

---

## 3. Data Flow — End-to-End Signal Lifecycle

```
t=0 s   Gateway wakes up, connects to KUKSA broker

t=1 s   compute_state(t=1.0) → VehicleState(speed=61.4, soc=84.98, ...)
        publisher → set_current_values({...}) → gRPC → Broker stores values

        Broker → streaming update → broker_client.subscribe_loop()
        on_update({"Vehicle.Speed": 61.4, ...})
        vehicle_state.update(...)
        manager.broadcast({"Vehicle.Speed": 61.4, ...})

        Browser WebSocket → applyState(data)
        updateGauge(61.4)
        pushHistory(61.4)
        socBar.style.width = "85%"
        ...
        User sees live dashboard update

t=2 s   Next publish cycle begins
```

End-to-end latency (localhost): < 10 ms from sensor publish to browser render.

---

## 4. Network Topology

### Docker Compose Network (`sdv-net`, bridge driver)

```
┌──────────────────────────────────────────────────────────────────┐
│  sdv-net (172.18.0.0/16)                                         │
│                                                                  │
│  sdv-databroker        172.18.0.2   :55555  gRPC                │
│  sdv-gateway-emulator  172.18.0.3   (no exposed port)           │
│  sdv-dashboard         172.18.0.4   :8080   HTTP/WS             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
         │                              │
         │ :55556 (host)                │ :8080 (host)
         ▼                              ▼
    Host machine                  Host machine
  (CLI / tests)                 (Browser / tests)
```

### Port Mapping

| Container port | Host port | Purpose |
|---|---|---|
| 55555 (gRPC) | 55556 | CLI/test access to broker from host |
| 8080 (HTTP/WS) | 8080 | Dashboard browser access |

> **Note:** Port 55555 is remapped to 55556 on the host due to a Docker Desktop for macOS reservation. Container-to-container communication uses the internal port 55555 unchanged.

---

## 5. Deployment Topology

### Local Development

```
docker compose up --build
                 ↑
         docker-compose.override.yml automatically loaded:
         - Volume mounts for live code reload
         - PUBLISH_INTERVAL_SEC=0.5 (faster feedback)
         - uvicorn --reload for dashboard
```

### CI/CD (GitHub Actions)

```
docker compose -f docker-compose.yml up -d --build
                ↑
         Override file explicitly excluded.
         Immutable images, no volume mounts.
         Integration tests run from host (outside containers).
```

### Production Extension Points

The architecture is designed to evolve toward production:

| Concern | Current (dev) | Production path |
|---|---|---|
| Auth | `--insecure` | KUKSA JWT tokens, per-path ACL |
| TLS | None | `--tls-cert` + `--tls-private-key` on broker |
| Dashboard auth | None | FastAPI OAuth2/OIDC middleware |
| Signal persistence | In-memory | InfluxDB time-series bridge |
| Observability | Container logs | Prometheus metrics + Grafana |
| Multi-vehicle | Single broker | Broker-per-vehicle or namespace isolation |

---

## 6. Technology Selection Rationale

| Decision | Chosen | Rejected alternatives | See ADR |
|---|---|---|---|
| Signal bus | KUKSA Databroker | Raw MQTT, DDS, REST polling | [ADR 001](adr/001-kuksa-over-mqtt.md) |
| Browser realtime | FastAPI WebSocket bridge | Direct gRPC-Web, Server-Sent Events | [ADR 002](adr/002-fastapi-ws-bridge.md) |
| Frontend stack | Vanilla JS + Chart.js CDN | React, Vue, Angular | — (zero build step principle) |
| Schema standard | COVESA VSS 4.0 | Custom schema, OBD-II codes | — (industry standard) |

---

## 7. Extension Scenarios

### Add an IDS Monitor (Intrusion Detection)

Add a fourth service that subscribes to all signals and applies a rules engine:

```python
async for updates in client.subscribe_current_values(SIGNALS):
    for path, datapoint in updates.items():
        anomaly = check_range(path, datapoint.value)
        if anomaly:
            logger.warning("[%s] %s", anomaly.severity, anomaly.message)
```

No changes to existing services required — the broker fan-out handles the additional subscriber transparently.

### Add a Map View

The dashboard already exposes `Vehicle.CurrentLocation.Latitude/Longitude` via WebSocket. Adding a Leaflet.js map tile to `index.html` requires only client-side changes.

### Connect to a Real Gateway

Replace the `gateway-emulator` container with the C++ gateway from [sdv-gateway-cpp](https://github.com/danielecostarella/sdv-gateway-cpp). The broker and dashboard require zero modification — the VSS signal contract is the interface.

### Scale to Multiple Vehicles

Each vehicle gets its own broker instance. A fleet aggregator service subscribes to all brokers and exposes a unified REST/GraphQL API. The infotainment dashboard connects to the fleet aggregator instead of a single broker.

---

## 8. Relation to sdv-gateway-cpp

```
┌────────────────────────────────────────────────────────────────┐
│                  Full Vehicle-to-Cloud Path                    │
│                                                                │
│  ┌─────────────────────┐         ┌────────────────────────┐   │
│  │   sdv-gateway-cpp   │         │  sdv-digital-twin-lab  │   │
│  │                     │         │                         │   │
│  │  C++ embedded side  │  gRPC   │  Python cloud side      │   │
│  │                     │ ──────▶ │                         │   │
│  │  CAN frame parsing  │  VSS    │  KUKSA Databroker       │   │
│  │  SOME/IP bridging   │  4.0    │  Infotainment Dashboard │   │
│  │  DDS middleware     │         │  CI/CD pipeline         │   │
│  │  ECU abstraction    │         │  Compliance docs        │   │
│  └─────────────────────┘         └────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

The two repositories together model a complete SDV software stack:
the C++ side shows how raw bus signals become structured VSS data;
this lab shows how that data is consumed, visualised, and tested.
