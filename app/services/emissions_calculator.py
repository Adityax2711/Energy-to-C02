"""
Emissions Factor Adapter and Carbon Calculator
Attaches regional grid carbon intensity to energy intervals, applying datacenter PUE overhead,
and recording full provenance and model auditability.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.database_models import (
    EnergyInterval,
    EmissionFactor,
    CarbonEstimate,
    AuditLedger,
    PowerSample
)
from app.core.config import settings
from app.core.provenance import generate_provenance_record


# Default regional emissions factors (gCO2e per kWh)
DEFAULT_FACTORS = [
    {
        "region": "US-EAST",
        "gco2e_kwh": 380.5,
        "source": "EPA eGRID / PJM Interconnection 2024"
    },
    {
        "region": "US-WEST",
        "gco2e_kwh": 210.0,
        "source": "CAISO California Grid Mix 2024"
    },
    {
        "region": "EU-CENTRAL",
        "gco2e_kwh": 315.0,
        "source": "European Environment Agency (EEA) / Agora 2024"
    },
    {
        "region": "EU-NORTH",
        "gco2e_kwh": 45.0,
        "source": "Nord Pool Scandinavian Clean Grid 2024"
    },
    {
        "region": "IN-SOUTH",
        "gco2e_kwh": 630.0,
        "source": "CEA India CO2 Baseline Database v19"
    },
    {
        "region": "AU-EAST",
        "gco2e_kwh": 550.0,
        "source": "AEMO National Electricity Market 2024"
    }
]


class EmissionsCalculator:
    """
    Core emissions calculation service.
    Formula: Carbon (gCO2e) = Energy (kWh) * PUE * Regional Intensity (gCO2e/kWh)
    """

    @classmethod
    def seed_default_factors_if_needed(cls, db: Session):
        """Seed initial realistic regional emission factors if the table is empty."""
        count = db.query(EmissionFactor).count()
        if count == 0:
            for item in DEFAULT_FACTORS:
                factor = EmissionFactor(
                    region=item["region"],
                    gco2e_kwh=item["gco2e_kwh"],
                    source=item["source"],
                    valid_at=datetime.now(timezone.utc)
                )
                db.add(factor)
            db.commit()

    @classmethod
    def get_factor_for_region(cls, db: Session, region: str) -> EmissionFactor:
        """
        Fetch the most recent valid emission factor for a region.
        Falls back to DEFAULT_REGION if the region is not recognized.
        """
        factor = (
            db.query(EmissionFactor)
            .filter(EmissionFactor.region == region.upper())
            .order_by(desc(EmissionFactor.valid_at), desc(EmissionFactor.id))
            .first()
        )
        if not factor:
            # Fall back to system default region
            factor = (
                db.query(EmissionFactor)
                .filter(EmissionFactor.region == settings.DEFAULT_REGION)
                .order_by(desc(EmissionFactor.valid_at), desc(EmissionFactor.id))
                .first()
            )
        if not factor:
            # Guarantee fallback
            cls.seed_default_factors_if_needed(db)
            factor = (
                db.query(EmissionFactor)
                .filter(EmissionFactor.region == settings.DEFAULT_REGION)
                .first()
            )
        return factor

    @classmethod
    def calculate_estimate_for_interval(
        cls,
        db: Session,
        interval: EnergyInterval,
        region: Optional[str] = None,
        pue: Optional[float] = None
    ) -> CarbonEstimate:
        """
        Calculate carbon emissions for an EnergyInterval, attaching regional factor and PUE.
        Persists a CarbonEstimate row and constructs provenance hash.
        """
        if region is None:
            region = settings.DEFAULT_REGION
        if pue is None:
            pue = settings.DEFAULT_PUE

        factor = cls.get_factor_for_region(db, region)

        # Core emissions formula:
        # grams_co2e = energy_kwh * pue * factor_gco2e_per_kwh
        grams_co2e = interval.energy_kwh * pue * factor.gco2e_kwh

        provenance = generate_provenance_record(
            interval_id=interval.id,
            host=interval.host,
            energy_kwh=interval.energy_kwh,
            factor_id=factor.id,
            region=factor.region,
            factor_gco2e_kwh=factor.gco2e_kwh,
            factor_source=factor.source,
            factor_valid_at=factor.valid_at,
            pue=pue,
            grams_co2e=grams_co2e,
            model_version=settings.MODEL_VERSION
        )

        estimate = CarbonEstimate(
            interval_id=interval.id,
            factor_id=factor.id,
            host=interval.host,
            region=factor.region,
            energy_kwh=interval.energy_kwh,
            pue=pue,
            grams_co2e=grams_co2e,
            model_version=settings.MODEL_VERSION,
            provenance_hash=provenance["provenance_hash"],
            calculated_at=datetime.now(timezone.utc)
        )
        db.add(estimate)
        db.flush()
        return estimate

    @classmethod
    def get_carbon_summary(
        cls,
        db: Session,
        region: Optional[str] = None,
        host: Optional[str] = None,
        pue: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compute total carbon summary for the specified region and optional host.
        Dynamically applies the regional factor and PUE to all intervals.
        """
        if not region:
            region = settings.DEFAULT_REGION
        if pue is None:
            pue = settings.DEFAULT_PUE

        factor = cls.get_factor_for_region(db, region)

        interval_query = db.query(
            func.coalesce(func.sum(EnergyInterval.energy_kwh), 0.0).label("total_kwh"),
            func.coalesce(func.sum(EnergyInterval.energy_wh), 0.0).label("total_wh"),
            func.count(EnergyInterval.id).label("interval_count"),
            func.max(EnergyInterval.end_at).label("last_end")
        )
        if host:
            interval_query = interval_query.filter(EnergyInterval.host == host)

        result = interval_query.one()
        total_kwh = float(result.total_kwh)
        total_grams = total_kwh * pue * factor.gco2e_kwh
        total_kg = total_grams / 1000.0
        total_metric_tons = total_kg / 1000.0

        sample_provenance = {
            "formula": f"Energy ({total_kwh:.6f} kWh) x PUE ({pue:.2f}) x Factor ({factor.gco2e_kwh} gCO2e/kWh)",
            "factor_source": factor.source,
            "factor_valid_at": factor.valid_at.isoformat() if factor.valid_at else None,
            "model_version": settings.MODEL_VERSION,
            "region": factor.region
        }

        return {
            "region": factor.region,
            "host_filter": host,
            "factor_gco2e_kwh": factor.gco2e_kwh,
            "factor_source": factor.source,
            "factor_valid_at": factor.valid_at,
            "pue": pue,
            "total_energy_kwh": round(total_kwh, 8),
            "total_grams_co2e": round(total_grams, 6),
            "total_kg_co2e": round(total_kg, 8),
            "total_metric_tons_co2e": round(total_metric_tons, 10),
            "model_version": settings.MODEL_VERSION,
            "last_calculated_at": result.last_end or datetime.now(timezone.utc),
            "provenance_sample": sample_provenance
        }

    @classmethod
    def get_timeseries_points(
        cls,
        db: Session,
        region: Optional[str] = None,
        host: Optional[str] = None,
        limit: int = 100,
        pue: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate time-series points combining instantaneous power, accumulated energy,
        and cumulative carbon emissions.
        """
        if not region:
            region = settings.DEFAULT_REGION
        if pue is None:
            pue = settings.DEFAULT_PUE

        factor = cls.get_factor_for_region(db, region)

        # Get latest power samples
        sample_query = db.query(PowerSample)
        if host:
            sample_query = sample_query.filter(PowerSample.host == host)
        samples = (
            sample_query.order_by(desc(PowerSample.timestamp))
            .limit(limit)
            .all()
        )
        samples.reverse()

        # Build chronological running accumulator
        points = []
        cumulative_wh = 0.0
        cumulative_grams = 0.0

        # Fetch intervals matching this timeframe
        for i, s in enumerate(samples):
            # Compute interval if not first
            interval_wh = 0.0
            if i > 0:
                prev_s = samples[i - 1]
                t_cur = s.timestamp
                t_prev = prev_s.timestamp
                if t_cur.tzinfo is not None and t_prev.tzinfo is None:
                    t_prev = t_prev.replace(tzinfo=timezone.utc)
                elif t_cur.tzinfo is None and t_prev.tzinfo is not None:
                    t_cur = t_cur.replace(tzinfo=timezone.utc)
                dt = (t_cur - t_prev).total_seconds()
                if 0 < dt <= settings.MAX_GAP_SECONDS:
                    avg_w = (prev_s.power_w + s.power_w) / 2.0
                    interval_wh = avg_w * (dt / 3600.0)

            cumulative_wh += interval_wh
            interval_kwh = interval_wh / 1000.0
            interval_grams = interval_kwh * pue * factor.gco2e_kwh
            cumulative_grams += interval_grams

            points.append({
                "timestamp": s.timestamp.isoformat(),
                "host": s.host,
                "power_w": round(s.power_w, 2),
                "cumulative_energy_wh": round(cumulative_wh, 4),
                "interval_grams_co2e": round(interval_grams, 6),
                "cumulative_grams_co2e": round(cumulative_grams, 6),
                "region": factor.region,
                "quality": s.quality
            })

        return points
