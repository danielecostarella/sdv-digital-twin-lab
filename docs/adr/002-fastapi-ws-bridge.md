# ADR 002 — FastAPI WebSocket bridge instead of direct gRPC-Web

**Status:** Accepted  
**Date:** 2026-04-09

## Context

The browser dashboard needs real-time access to vehicle signals. Two approaches
were evaluated:

1. **Direct gRPC-Web** — browser calls the databroker directly via gRPC-Web protocol.
2. **FastAPI WebSocket bridge** — a Python backend subscribes to KUKSA and fans
   out updates to browsers over native WebSocket.

## Decision

Use a **FastAPI backend** as an intermediary WebSocket bridge.

## Rationale

The KUKSA Databroker deployment in this project uses plain gRPC over HTTP/2.
Browsers cannot initiate raw HTTP/2 requests; they require gRPC-Web (which needs
an Envoy-class proxy in front of the broker) or a dedicated transcoding layer.

The FastAPI bridge is simpler: one Python process, no proxy, browser-native
WebSocket. It also provides natural extension points:

- **Authentication** — JWT validation before upgrading to WebSocket
- **Rate limiting** — throttle broadcast frequency without touching the broker
- **REST snapshot** — `GET /api/state` for dashboard cold-start and integration tests

## Consequences

- Adds one application hop (broker → FastAPI → browser). Measured latency: < 5 ms
  on localhost, negligible for a 1 Hz signal stream.
- The `/ws` endpoint is a single point of failure. Mitigated by the `restart:
  on-failure` Docker policy and the browser's auto-reconnect logic.
