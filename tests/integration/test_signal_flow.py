"""Integration tests — verify end-to-end signal flow through the digital twin.

Requires: `docker compose up` stack running with gateway publishing signals.
"""

import pytest

SIGNALS = [
    "Vehicle.Speed",
    "Vehicle.Powertrain.ElectricMotor.Speed",
    "Vehicle.Body.Lights.Beam.High.IsOn",
    "Vehicle.CurrentLocation.Latitude",
    "Vehicle.CurrentLocation.Longitude",
    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current",
]


@pytest.mark.asyncio
async def test_broker_is_reachable(kuksa_client):
    """Databroker accepts gRPC connections."""
    values = await kuksa_client.get_current_values(["Vehicle.Speed"])
    assert "Vehicle.Speed" in values


@pytest.mark.asyncio
async def test_all_signals_are_published(kuksa_client):
    """Gateway has published at least one reading for every monitored signal."""
    values = await kuksa_client.get_current_values(SIGNALS)
    for sig in SIGNALS:
        assert values.get(sig) is not None, f"No datapoint for {sig}"
        assert values[sig].value is not None, f"Null value for {sig}"


@pytest.mark.asyncio
async def test_speed_in_valid_range(kuksa_client):
    values = await kuksa_client.get_current_values(["Vehicle.Speed"])
    speed = values["Vehicle.Speed"].value
    assert 0.0 <= float(speed) <= 250.0, f"Speed {speed} out of range"


@pytest.mark.asyncio
async def test_soc_in_valid_range(kuksa_client):
    path = "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current"
    values = await kuksa_client.get_current_values([path])
    soc = float(values[path].value)
    assert 0.0 <= soc <= 100.0, f"SoC {soc} out of range"


@pytest.mark.asyncio
async def test_latitude_in_valid_range(kuksa_client):
    values = await kuksa_client.get_current_values(["Vehicle.CurrentLocation.Latitude"])
    lat = float(values["Vehicle.CurrentLocation.Latitude"].value)
    assert -90.0 <= lat <= 90.0


@pytest.mark.asyncio
async def test_longitude_in_valid_range(kuksa_client):
    values = await kuksa_client.get_current_values(["Vehicle.CurrentLocation.Longitude"])
    lon = float(values["Vehicle.CurrentLocation.Longitude"].value)
    assert -180.0 <= lon <= 180.0
