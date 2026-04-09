"""Shared pytest fixtures for integration tests.

Requires a running `docker compose up` stack.
"""

import asyncio

import pytest
from kuksa_client.grpc.aio import VSSClient

BROKER_HOST = "localhost"
BROKER_PORT = 55556  # host-side mapping (container internal port is 55555)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def kuksa_client():
    async with VSSClient(BROKER_HOST, BROKER_PORT) as client:
        yield client
