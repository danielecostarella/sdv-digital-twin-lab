"""Shared in-memory vehicle state.

Intentionally kept as a plain dict so any coroutine can read/write without
needing a lock — FastAPI runs in a single-threaded event loop.
"""

vehicle_state: dict = {
    "Vehicle.Speed": None,
    "Vehicle.Powertrain.ElectricMotor.Speed": None,
    "Vehicle.Body.Lights.Beam.High.IsOn": None,
    "Vehicle.CurrentLocation.Latitude": None,
    "Vehicle.CurrentLocation.Longitude": None,
    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current": None,
}
