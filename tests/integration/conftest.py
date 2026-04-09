"""Shared pytest fixtures for integration tests.

Requires a running `docker compose up` stack.
"""

import pytest
from kuksa_client.grpc.aio import VSSClient

BROKER_HOST = "localhost"
BROKER_PORT = 55556  # host-side mapping (container internal port is 55555)


@pytest.fixture()
async def kuksa_client():
    """Fresh gRPC connection per test — avoids grpc.aio event-loop binding issues."""
    async with VSSClient(BROKER_HOST, BROKER_PORT) as client:
        yield client
