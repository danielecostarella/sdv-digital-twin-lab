"""Async KUKSA Databroker subscriber — feeds the WebSocket bridge."""

import logging
import os
from collections.abc import Awaitable, Callable

from kuksa_client.grpc.aio import VSSClient

logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv("KUKSA_DATABROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("KUKSA_DATABROKER_PORT", "55555"))

SIGNALS = [
    "Vehicle.Speed",
    "Vehicle.Powertrain.ElectricMotor.Speed",
    "Vehicle.Body.Lights.Beam.High.IsOn",
    "Vehicle.CurrentLocation.Latitude",
    "Vehicle.CurrentLocation.Longitude",
    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current",
]


async def subscribe_loop(
    on_update: Callable[[dict], Awaitable[None]],
) -> None:
    """Subscribe to VSS signals and call *on_update* on every change.

    Runs indefinitely; cancel the enclosing task to stop it.
    """
    logger.info("Subscribing to %d VSS signals via %s:%d", len(SIGNALS), BROKER_HOST, BROKER_PORT)
    async with VSSClient(BROKER_HOST, BROKER_PORT) as client:
        async for updates in client.subscribe_current_values(SIGNALS):
            payload: dict = {}
            for path, datapoint in updates.items():
                if datapoint is not None:
                    payload[path] = datapoint.value
            if payload:
                await on_update(payload)
