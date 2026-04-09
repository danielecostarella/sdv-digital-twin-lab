"""Integration tests for the Infotainment Dashboard HTTP/WS endpoints."""

import pytest
import httpx

DASHBOARD_URL = "http://localhost:8080"


@pytest.mark.asyncio
async def test_dashboard_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DASHBOARD_URL}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_dashboard_state_returns_vehicle_speed():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DASHBOARD_URL}/api/state", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert "Vehicle.Speed" in data


@pytest.mark.asyncio
async def test_dashboard_serves_html():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DASHBOARD_URL}/", timeout=5)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
