"""
Deterministic Carbon Calculator Tests
Verifies hand-calculated emissions math, PUE multiplier, regional factor adaptations,
and cryptographic provenance hashes.
"""
from datetime import datetime, timezone, timedelta
import pytest
from app.models.database_models import PowerSample, EnergyInterval, EmissionFactor
from app.services.emissions_calculator import EmissionsCalculator


def test_hand_calculated_carbon_emissions(db_session):
    """
    HAND-CALCULATED BENCHMARK 4:
    Energy Interval: 0.100 kWh (100 Wh)
    PUE Multiplier: 1.20
    Regional Factor (US-EAST): 380.5 gCO2e/kWh
    Expected:
      Gross Energy = 0.100 kWh * 1.20 = 0.120 kWh
      Carbon gCO2e = 0.120 kWh * 380.5 gCO2e/kWh = 45.660000 gCO2e
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=3600)

    interval = EnergyInterval(
        host="calc-node-01",
        start_at=t0,
        end_at=t1,
        duration_seconds=3600.0,
        energy_wh=100.0,
        energy_kwh=0.1,
        method="trapezoidal",
        quality="OK"
    )
    db_session.add(interval)
    db_session.flush()

    estimate = EmissionsCalculator.calculate_estimate_for_interval(
        db=db_session,
        interval=interval,
        region="US-EAST",
        pue=1.20
    )

    assert estimate is not None
    assert pytest.approx(estimate.grams_co2e, rel=1e-5) == 45.66
    assert estimate.region == "US-EAST"
    assert estimate.pue == 1.20
    assert len(estimate.provenance_hash) == 64  # Valid SHA-256


def test_regional_factor_variance_and_updates(db_session):
    """
    Verify regional carbon sensitivity:
    Same energy (1.0 kWh) in EU-NORTH (45 g/kWh) vs IN-SOUTH (630 g/kWh).
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=3600)

    interval = EnergyInterval(
        host="global-server",
        start_at=t0,
        end_at=t1,
        duration_seconds=3600.0,
        energy_wh=1000.0,
        energy_kwh=1.0,
        method="trapezoidal",
        quality="OK"
    )
    db_session.add(interval)
    db_session.flush()

    # EU-NORTH estimate (Clean hydro/nuclear)
    est_nordic = EmissionsCalculator.calculate_estimate_for_interval(
        db_session, interval, region="EU-NORTH", pue=1.0
    )
    assert pytest.approx(est_nordic.grams_co2e, rel=1e-5) == 45.0

    # IN-SOUTH estimate (Coal heavy baseline)
    est_india = EmissionsCalculator.calculate_estimate_for_interval(
        db_session, interval, region="IN-SOUTH", pue=1.0
    )
    assert pytest.approx(est_india.grams_co2e, rel=1e-5) == 630.0

    # Variance ratio: 630 / 45 = 14x carbon intensity difference
    ratio = est_india.grams_co2e / est_nordic.grams_co2e
    assert pytest.approx(ratio, rel=1e-3) == 14.0


def test_custom_factor_update_audit(db_session):
    """
    Test updating a regional factor to a newer date and ensuring the latest is picked up.
    """
    new_factor = EmissionFactor(
        region="US-EAST",
        gco2e_kwh=320.0,  # Improved clean grid mix
        source="EIA Updated Q3 2026",
        valid_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db_session.add(new_factor)
    db_session.commit()

    active_factor = EmissionsCalculator.get_factor_for_region(db_session, "US-EAST")
    assert active_factor.gco2e_kwh == 320.0
    assert active_factor.source == "EIA Updated Q3 2026"
