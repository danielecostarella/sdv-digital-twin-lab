# ADR 001 — KUKSA.val Databroker over raw MQTT

**Status:** Accepted  
**Date:** 2026-04-09

## Context

The project needs a centralised signal bus. Two candidates were evaluated:

| Criterion | Raw MQTT (Mosquitto) | Eclipse KUKSA Databroker |
|---|---|---|
| VSS schema enforcement | None — any payload | Native VSS 4.0 validation |
| Type safety | String blobs | Typed Datapoint (float, int, bool…) |
| Access control | ACL files | JWT-based per-path permissions |
| Discovery | Manual topic docs | gRPC reflection + metadata API |
| Ecosystem | Generic IoT | Automotive-specific (Eclipse SDV) |

## Decision

Use **Eclipse KUKSA.val Databroker** as the Single Source of Truth for vehicle state.

## Rationale

KUKSA enforces the VSS schema at ingestion time: a gateway cannot publish a
`Vehicle.Speed` of type `string`. This makes the digital twin semantically correct,
not just a message pipe.

The gRPC API also provides a stable, versioned contract between the gateway and
consumers. Adding a new signal requires only updating `vss_release_4.0.json` —
no protocol negotiation, no topic naming convention to document.

## Consequences

- Consumers (dashboard, IDS) must use the `kuksa-client` gRPC library instead of
  a generic MQTT client. This is a minor dependency overhead.
- The VSS JSON file must be pinned and distributed alongside the broker. See
  `scripts/download-vss.sh`.
