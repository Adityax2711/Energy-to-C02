"""
Telemetry Ingestion Pipeline
Validates inputs, protects against duplicate timestamps, handles idempotency keys,
drives energy integration and attaches regional emissions.
"""
from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.database_models import PowerSample, AuditLedger, EnergyInterval
from app.models.schemas import PowerSampleCreate
from app.services.integrator import EnergyIntegrator
from app.services.emissions_calculator import EmissionsCalculator
from app.core.provenance import compute_payload_hash
from app.core.config import settings


class TelemetryCollectorService:
    """
    Ingestion coordinator:
    Host Sensor / Simulator -> Normalize & Validate -> Ingest Sample -> Integrate Energy -> Attach Regional Emissions -> Audit
    """

    @classmethod
    def ingest_sample(
        cls,
        db: Session,
        sample_in: PowerSampleCreate,
        idempotency_key: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a raw power sample with full transactional safety, idempotency,
        energy integration, and regional carbon attachment.
        """
        # Ensure UTC timezone awareness on timestamp
        ts = sample_in.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        payload_dict = {
            "host": sample_in.host,
            "timestamp": ts.isoformat(),
            "power_w": sample_in.power_w,
            "source": sample_in.source,
            "quality": sample_in.quality
        }
        payload_hash = compute_payload_hash(payload_dict)

        # Idempotency check if header provided
        if idempotency_key:
            existing_audit = (
                db.query(AuditLedger)
                .filter(AuditLedger.idempotency_key == idempotency_key)
                .first()
            )
            if existing_audit:
                # Return conflict 409 or return existing transaction details
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency key '{idempotency_key}' already processed in ledger ID #{existing_audit.id}."
                )

        # Check for duplicate timestamp on same host
        existing_sample = (
            db.query(PowerSample)
            .filter(
                PowerSample.host == sample_in.host,
                PowerSample.timestamp == ts
            )
            .first()
        )
        if existing_sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate timestamp '{ts.isoformat()}' already recorded for host '{sample_in.host}'."
            )

        # Create PowerSample
        sample = PowerSample(
            host=sample_in.host,
            timestamp=ts,
            power_w=sample_in.power_w,
            source=sample_in.source,
            quality=sample_in.quality or "OK"
        )
        db.add(sample)
        db.flush()

        # Step 2: Energy Integration
        interval, integration_status = EnergyIntegrator.integrate_sample(
            db=db,
            new_sample=sample,
            method="trapezoidal"
        )

        estimate_data = None
        if interval and interval.energy_kwh > 0:
            # Step 3: Carbon Calculation
            estimate = EmissionsCalculator.calculate_estimate_for_interval(
                db=db,
                interval=interval,
                region=region or settings.DEFAULT_REGION
            )
            estimate_data = {
                "id": estimate.id,
                "region": estimate.region,
                "energy_kwh": estimate.energy_kwh,
                "grams_co2e": estimate.grams_co2e,
                "provenance_hash": estimate.provenance_hash
            }

        # Step 4: Ledger recording
        audit_entry = AuditLedger(
            idempotency_key=idempotency_key,
            event_type="TELEMETRY_INGESTED",
            host=sample.host,
            payload_hash=payload_hash,
            details=json.dumps({
                "sample_id": sample.id,
                "power_w": sample.power_w,
                "integration_status": integration_status,
                "interval_id": interval.id if interval else None,
                "estimate": estimate_data
            })
        )
        db.add(audit_entry)
        db.commit()

        return {
            "status": "success",
            "sample_id": sample.id,
            "host": sample.host,
            "timestamp": sample.timestamp.isoformat(),
            "power_w": sample.power_w,
            "quality": sample.quality,
            "integration_status": integration_status,
            "interval_id": interval.id if interval else None,
            "interval_energy_wh": round(interval.energy_wh, 6) if interval else 0.0,
            "estimate": estimate_data
        }
