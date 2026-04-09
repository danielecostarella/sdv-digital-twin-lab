"""Publishes simulated VSS signals to the KUKSA Databroker via gRPC."""

import asyncio
import logging
import os
import time

from kuksa_client.grpc import Datapoint
from kuksa_client.grpc.aio import VSSClient

from .signals import compute_state

logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv("KUKSA_DATABROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("KUKSA_DATABROKER_PORT", "55555"))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL_SEC", "1.0"))


async def run() -> None:
    logger.info("Connecting to KUKSA Databroker at %s:%d", BROKER_HOST, BROKER_PORT)
    start = time.monotonic()

    async with VSSClient(BROKER_HOST, BROKER_PORT) as client:
        logger.info("Connected. Publishing VSS signals every %.1f s", PUBLISH_INTERVAL)
        while True:
            t = time.monotonic() - start
            state = compute_state(t)

            await client.set_current_values(
                {
                    "Vehicle.Speed": Datapoint(state.speed_kmh),
                    "Vehicle.Powertrain.ElectricMotor.Speed": Datapoint(
                        state.motor_rpm
                    ),
                    "Vehicle.Body.Lights.Beam.High.IsOn": Datapoint(state.high_beam),
                    "Vehicle.CurrentLocation.Latitude": Datapoint(state.latitude),
                    "Vehicle.CurrentLocation.Longitude": Datapoint(state.longitude),
                    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current": Datapoint(
                        state.soc_percent
                    ),
                }
            )

            logger.debug(
                "Published — speed=%.1f km/h  rpm=%d  soc=%.1f%%",
                state.speed_kmh,
                state.motor_rpm,
                state.soc_percent,
            )
            await asyncio.sleep(PUBLISH_INTERVAL)
