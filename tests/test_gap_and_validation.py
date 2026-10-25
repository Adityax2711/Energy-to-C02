"""
Unit & Edge Case Tests: Telemetry Gaps, Negative Watts, Duplicate Timestamps, Idempotency
"""
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.database_models import PowerSample
from app.models.schemas import PowerSampleCreate
from app.services.integrator import EnergyIntegrator
from app.services.telemetry_collector import TelemetryCollectorService


def test_explicit_telemetry_gap_handling(db_session):
    """
    CRITICAL EDGE CASE: Telemetry Gap Handling.
    Sensor reports at t=0s (100W), then disconnects for 300 seconds, and reports at t=300s (100W).
    Without gap handling, naive integration would assume 100W for 300s = 8.33 Wh of phantom energy!
    With gap handling:
      - Detected as GAP_DETECTED (300s > max_gap 15s)
      - Zero false energy is added (energy_wh = 0.0)
      - Gap interval is explicitly flagged in the ledger.
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=300)  # 5 minutes downtime

    s0 = PowerSample(host="gap-node", timestamp=t0, power_w=100.0, source="fixture", quality="OK")
    db_session.add(s0)
    db_session.flush()
    EnergyIntegrator.integrate_sample(db_session, s0, max_gap_seconds=15.0)

    # Disconnected sensor reconnects 300s later
    s1 = PowerSample(host="gap-node", timestamp=t1, power_w=100.0, source="fixture", quality="OK")
    db_session.add(s1)
    db_session.flush()

    gap_interval, status = EnergyIntegrator.integrate_sample(
        db=db_session,
        new_sample=s1,
        max_gap_seconds=15.0
    )

    assert status == "GAP_DETECTED"
    assert gap_interval is not None
    assert gap_interval.quality == "GAP_DETECTED"
    assert gap_interval.energy_wh == 0.0  # Zero phantom energy hallucinated
    assert gap_interval.duration_seconds == 300.0
    assert s1.quality == "GAP_DETECTED"


def test_negative_power_rejection():
    """
    Validation Test: Negative watts must be rejected by schema validator.
    """
    with pytest.raises(ValidationError):
        PowerSampleCreate(
            host="bad-meter",
            timestamp=datetime.now(timezone.utc),
            power_w=-25.0,  # Negative power violates physics
            source="faulty_sensor"
        )


def test_duplicate_timestamp_rejection(db_session):
    """
    Validation Test: Duplicate timestamps on the same host must raise HTTP 400 Bad Request.
    """
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    s1 = PowerSampleCreate(host="dup-host", timestamp=now, power_w=50.0, source="sensor")
    TelemetryCollectorService.ingest_sample(db_session, s1)

    # Attempting to re-ingest identical host + timestamp
    with pytest.raises(HTTPException) as exc_info:
        TelemetryCollectorService.ingest_sample(db_session, s1)

    assert exc_info.value.status_code == 400
    assert "Duplicate timestamp" in exc_info.value.detail


def test_idempotency_key_deduplication(db_session):
    """
    Ledger Safety: Repeated submissions with the same Idempotency-Key
    must be detected and rejected with HTTP 409 Conflict.
    """
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=2)

    sample1 = PowerSampleCreate(host="idemp-host", timestamp=t0, power_w=60.0, source="sensor")
    TelemetryCollectorService.ingest_sample(db_session, sample1, idempotency_key="tx-req-uuid-001")

    sample2 = PowerSampleCreate(host="idemp-host", timestamp=t1, power_w=65.0, source="sensor")
    with pytest.raises(HTTPException) as exc_info:
        TelemetryCollectorService.ingest_sample(db_session, sample2, idempotency_key="tx-req-uuid-001")

    assert exc_info.value.status_code == 409
    assert "already processed" in exc_info.value.detail
