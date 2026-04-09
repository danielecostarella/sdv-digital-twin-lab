"""Unit tests for FastAPI routes (no live broker required)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    # Patch the subscribe loop so it doesn't try to connect to a real broker
    with patch("src.broker_client.subscribe_loop", new_callable=AsyncMock):
        from src.main import app

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_state_returns_all_signals(client):
    resp = client.get("/api/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "Vehicle.Speed" in data
    assert "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current" in data
