"""Entry point for the Gateway Emulator service."""

import asyncio
import logging

from .publisher import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [gateway] %(levelname)s %(message)s",
)

if __name__ == "__main__":
    asyncio.run(run())
