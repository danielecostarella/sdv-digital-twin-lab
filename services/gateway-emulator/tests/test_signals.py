"""Unit tests for the signal simulation logic."""

import pytest

from src.signals import VehicleState, compute_state


def test_returns_vehicle_state():
    state = compute_state(0.0)
    assert isinstance(state, VehicleState)


def test_speed_at_t0_is_near_zero():
    # At t=0 the sine is 0, so speed = 60 + 60*sin(0) = 60
    state = compute_state(0.0)
    assert abs(state.speed_kmh - 60.0) < 1.0


def test_speed_always_in_valid_range():
    for t in range(0, 240, 5):
        state = compute_state(float(t))
        assert 0.0 <= state.speed_kmh <= 250.0, f"Speed out of range at t={t}"


def test_motor_rpm_non_negative():
    for t in range(0, 120, 10):
        assert compute_state(float(t)).motor_rpm >= 0


def test_soc_decays_over_time():
    early = compute_state(0.0, initial_soc=85.0)
    later = compute_state(120.0, initial_soc=85.0)
    assert later.soc_percent < early.soc_percent


def test_soc_floor_at_10_percent():
    # After a very long time the battery should not drop below 10%
    state = compute_state(10_000.0, initial_soc=85.0)
    assert state.soc_percent >= 10.0


def test_high_beam_on_at_high_speed():
    # At t=30s speed ≈ 120 km/h → high beam should be on
    state = compute_state(30.0)
    assert state.high_beam is True


def test_high_beam_off_at_low_speed():
    # At t=0s speed ≈ 60 km/h → high beam should be off
    state = compute_state(0.0)
    assert state.high_beam is False


def test_gps_within_reasonable_bounds():
    state = compute_state(0.0)
    assert 47.0 < state.latitude < 49.0
    assert 10.0 < state.longitude < 13.0
