"""
Unit-safe Energy Integrator
Integrates instantaneous power (Watts) over time intervals to compute Watt-hours (Wh) and kWh.
Handles sample interval normalization, edge cases, and explicit gap detection.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database_models import PowerSample, EnergyInterval
from app.core.config import settings


class EnergyIntegrator:
    """
    Mathematical energy integrator adhering to unit safety:
    Power is instantaneous (Watts, J/s).
    Energy is time-accumulated (Watt-hours = Joules / 3600, and kWh = Wh / 1000).
    """

    @staticmethod
    def integrate_sample(
        db: Session,
        new_sample: PowerSample,
        method: str = "trapezoidal",
        max_gap_seconds: Optional[float] = None
    ) -> Tuple[Optional[EnergyInterval], str]:
        """
        Integrates a newly arrived PowerSample against the most recent prior sample for the same host.
        Returns (EnergyInterval or None, status_code).
        Status codes:
          - 'INTEGRATED': Successfully created interval
          - 'FIRST_SAMPLE': No prior sample to integrate against
          - 'GAP_DETECTED': Interval exceeded max gap threshold; gap recorded without false energy
          - 'DUPLICATE_OR_PAST_TIMESTAMP': Sample timestamp <= prior timestamp
        """
        if max_gap_seconds is None:
            max_gap_seconds = settings.MAX_GAP_SECONDS

        # Query the most recent prior sample for this host strictly before new_sample.timestamp
        prior_sample = (
            db.query(PowerSample)
            .filter(
                PowerSample.host == new_sample.host,
                PowerSample.id != new_sample.id,
                PowerSample.timestamp <= new_sample.timestamp
            )
            .order_by(desc(PowerSample.timestamp), desc(PowerSample.id))
            .first()
        )

        if not prior_sample:
            return None, "FIRST_SAMPLE"

        t_new = new_sample.timestamp
        t_prior = prior_sample.timestamp
        if t_new.tzinfo is not None and t_prior.tzinfo is None:
            t_prior = t_prior.replace(tzinfo=timezone.utc)
        elif t_new.tzinfo is None and t_prior.tzinfo is not None:
            t_new = t_new.replace(tzinfo=timezone.utc)

        delta_seconds = (t_new - t_prior).total_seconds()

        # Handle zero or negative time intervals (duplicate or out-of-order)
        if delta_seconds <= 0:
            return None, "DUPLICATE_OR_PAST_TIMESTAMP"

        # Explicit gap handling: If delta_seconds exceeds max threshold, do not integrate blindly!
        # Continuous integration over days/hours of sensor silence would hallucinate massive energy.
        if delta_seconds > max_gap_seconds:
            # Mark new sample as GAP_DETECTED
            new_sample.quality = "GAP_DETECTED"
            # We record a zero-energy marker interval to document the downtime/gap
            gap_interval = EnergyInterval(
                host=new_sample.host,
                start_at=prior_sample.timestamp,
                end_at=new_sample.timestamp,
                duration_seconds=delta_seconds,
                energy_wh=0.0,
                energy_kwh=0.0,
                method=method,
                quality="GAP_DETECTED"
            )
            db.add(gap_interval)
            db.flush()
            return gap_interval, "GAP_DETECTED"

        # Normal unit-safe integration
        # Trapezoidal method: Average power * delta_t_hours
        p1 = prior_sample.power_w
        p2 = new_sample.power_w
        delta_hours = delta_seconds / 3600.0

        if method == "trapezoidal":
            avg_power_w = (p1 + p2) / 2.0
            energy_wh = avg_power_w * delta_hours
        elif method == "riemann_left":
            energy_wh = p1 * delta_hours
        elif method == "riemann_right":
            energy_wh = p2 * delta_hours
        else:
            avg_power_w = (p1 + p2) / 2.0
            energy_wh = avg_power_w * delta_hours

        energy_kwh = energy_wh / 1000.0

        # Quality propagation
        quality = "OK"
        if prior_sample.quality != "OK" or new_sample.quality != "OK":
            quality = new_sample.quality if new_sample.quality != "OK" else prior_sample.quality

        interval = EnergyInterval(
            host=new_sample.host,
            start_at=prior_sample.timestamp,
            end_at=new_sample.timestamp,
            duration_seconds=delta_seconds,
            energy_wh=energy_wh,
            energy_kwh=energy_kwh,
            method=method,
            quality=quality
        )
        db.add(interval)
        db.flush()

        return interval, "INTEGRATED"
