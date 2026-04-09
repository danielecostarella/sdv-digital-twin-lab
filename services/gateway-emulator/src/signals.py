"""Vehicle signal simulation — pure functions, no I/O."""

import math
import random
from dataclasses import dataclass


@dataclass
class VehicleState:
    speed_kmh: float
    motor_rpm: int
    high_beam: bool
    latitude: float
    longitude: float
    soc_percent: float


# Munich city centre as the GPS origin for the simulation
_ORIGIN_LAT = 48.1351
_ORIGIN_LON = 11.5820

# Speed cycle period in seconds
_SPEED_PERIOD_S = 120.0

# Battery drain rate: 1% per minute
_SOC_DRAIN_RATE = 1.0 / 60.0


def compute_state(t: float, initial_soc: float = 85.0) -> VehicleState:
    """Return a simulated VehicleState at elapsed time *t* seconds.

    All maths is deterministic except for the small Gaussian GPS jitter,
    which is seeded from *t* so replays are reproducible.
    """
    # Speed: sinusoidal 0..120 km/h over a 120 s cycle
    speed = 60.0 + 60.0 * math.sin(2 * math.pi * t / _SPEED_PERIOD_S)

    # Motor RPM: proportional to speed with light Gaussian noise
    rng = random.Random(int(t * 1000))
    motor_rpm = max(0, int(speed * 50 + rng.gauss(0, 20)))

    # High beam on when cruising above 90 km/h (highway simulation)
    high_beam = speed > 90.0

    # GPS: bounded random walk around the origin (~500 m radius)
    lat = _ORIGIN_LAT + rng.gauss(0, 0.0005)
    lon = _ORIGIN_LON + rng.gauss(0, 0.0005)

    # Battery: linear decay, floored at 10 %
    soc = max(10.0, initial_soc - t * _SOC_DRAIN_RATE)

    return VehicleState(
        speed_kmh=round(speed, 2),
        motor_rpm=motor_rpm,
        high_beam=high_beam,
        latitude=round(lat, 6),
        longitude=round(lon, 6),
        soc_percent=round(soc, 2),
    )
