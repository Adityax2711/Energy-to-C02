"""
Deterministic Unit Tests for Energy Integration (Watts -> Watt-hours and kWh)
Verifies exact hand-calculated figures with trapezoidal and Riemann methods.
"""
from datetime import datetime, timezone, timedelta
import pytest
from app.models.database_models import PowerSample
from app.services.integrator import EnergyIntegrator


def test_hand_calculated_constant_power_integration(db_session):
    """
    HAND-CALCULATED BENCHMARK 1:
    Constant power of 100.0 Watts over 3600 seconds (1.0 hour).
    Expected:
      Average Power = (100.0 + 100.0) / 2 = 100.0 Watts
      Delta Time = 3600 s = 1.0 hr
      Energy Wh = 100.0 * 1.0 = 100.0000 Wh
      Energy kWh = 100.0 / 1000 = 0.10000 kWh
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=3600)

    # First sample: establishes baseline
    s0 = PowerSample(host="test-host-01", timestamp=t0, power_w=100.0, source="fixture", quality="OK")
    db_session.add(s0)
    db_session.flush()

    interval0, status0 = EnergyIntegrator.integrate_sample(
        db_session, s0, method="trapezoidal", max_gap_seconds=4000.0
    )
    assert status0 == "FIRST_SAMPLE"
    assert interval0 is None

    # Second sample 1 hour later
    s1 = PowerSample(host="test-host-01", timestamp=t1, power_w=100.0, source="fixture", quality="OK")
    db_session.add(s1)
    db_session.flush()

    interval1, status1 = EnergyIntegrator.integrate_sample(
        db_session, s1, method="trapezoidal", max_gap_seconds=4000.0
    )
    assert status1 == "INTEGRATED"
    assert interval1 is not None

    # Assert exact deterministic numbers
    assert interval1.duration_seconds == 3600.0
    assert pytest.approx(interval1.energy_wh, rel=1e-6) == 100.0
    assert pytest.approx(interval1.energy_kwh, rel=1e-6) == 0.1


def test_hand_calculated_variable_trapezoidal_integration(db_session):
    """
    HAND-CALCULATED BENCHMARK 2:
    Variable power ramp from 50.0 Watts to 150.0 Watts over 1800 seconds (0.5 hour).
    Expected:
      Average Power = (50.0 + 150.0) / 2 = 100.0 Watts
      Delta Time = 1800 s = 0.5 hr
      Energy Wh = 100.0 * 0.5 = 50.0000 Wh
      Energy kWh = 50.0 / 1000 = 0.05000 kWh
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1800)

    s0 = PowerSample(host="ramp-host", timestamp=t0, power_w=50.0, source="fixture", quality="OK")
    db_session.add(s0)
    db_session.flush()
    EnergyIntegrator.integrate_sample(db_session, s0, method="trapezoidal", max_gap_seconds=2000.0)

    s1 = PowerSample(host="ramp-host", timestamp=t1, power_w=150.0, source="fixture", quality="OK")
    db_session.add(s1)
    db_session.flush()
    interval, status = EnergyIntegrator.integrate_sample(db_session, s1, method="trapezoidal", max_gap_seconds=2000.0)

    assert status == "INTEGRATED"
    assert pytest.approx(interval.energy_wh, rel=1e-6) == 50.0
    assert pytest.approx(interval.energy_kwh, rel=1e-6) == 0.05


def test_riemann_integration_methods(db_session):
    """
    HAND-CALCULATED BENCHMARK 3:
    Compare Trapezoidal vs Riemann Left Sum.
    t0: 50.0 W, t1: 150.0 W, dt = 1800s (0.5 hr).
    Riemann Left = 50.0 W * 0.5 hr = 25.0 Wh.
    Riemann Right = 150.0 W * 0.5 hr = 75.0 Wh.
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1800)

    # Left Riemann
    s0 = PowerSample(host="host-left", timestamp=t0, power_w=50.0, source="fixture")
    db_session.add(s0)
    db_session.flush()
    EnergyIntegrator.integrate_sample(db_session, s0)

    s1 = PowerSample(host="host-left", timestamp=t1, power_w=150.0, source="fixture")
    db_session.add(s1)
    db_session.flush()
    interval_left, _ = EnergyIntegrator.integrate_sample(
        db_session, s1, method="riemann_left", max_gap_seconds=2000.0
    )
    assert pytest.approx(interval_left.energy_wh, rel=1e-6) == 25.0

    # Right Riemann
    s0_r = PowerSample(host="host-right", timestamp=t0, power_w=50.0, source="fixture")
    db_session.add(s0_r)
    db_session.flush()
    EnergyIntegrator.integrate_sample(db_session, s0_r)

    s1_r = PowerSample(host="host-right", timestamp=t1, power_w=150.0, source="fixture")
    db_session.add(s1_r)
    db_session.flush()
    interval_right, _ = EnergyIntegrator.integrate_sample(
        db_session, s1_r, method="riemann_right", max_gap_seconds=2000.0
    )
    assert pytest.approx(interval_right.energy_wh, rel=1e-6) == 75.0
