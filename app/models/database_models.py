"""
SQLAlchemy Database Models for Energy-to-CO2 Engine
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Enum,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class PowerSample(Base):
    """
    Represents an instantaneous power reading (Watts) from a host/sensor.
    Quality flags:
      - 'OK': Normal reading
      - 'INTERPOLATED': Synthesized reading
      - 'GAP_DETECTED': Follows a sample gap > max_gap_seconds
      - 'SUSPICIOUS': Outlier or high jitter
    """
    __tablename__ = "power_samples"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    host = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    power_w = Column(Float, nullable=False)
    source = Column(String(100), nullable=False, default="simulator")
    quality = Column(String(50), nullable=False, default="OK")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_power_samples_host_timestamp", "host", "timestamp"),
        UniqueConstraint("host", "timestamp", name="uq_host_timestamp"),
    )


class EnergyInterval(Base):
    """
    Represents time-integrated energy over an interval [start_at, end_at].
    energy_wh: Watt-hours
    energy_kwh: Kilowatt-hours (Wh / 1000)
    method: 'trapezoidal' or 'riemann_left' / 'riemann_right'
    """
    __tablename__ = "energy_intervals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    host = Column(String(100), nullable=False, index=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    energy_wh = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)
    method = Column(String(50), nullable=False, default="trapezoidal")
    quality = Column(String(50), nullable=False, default="OK")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    carbon_estimates = relationship("CarbonEstimate", back_populates="interval", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_energy_intervals_host_end_at", "host", "end_at"),
    )


class EmissionFactor(Base):
    """
    Represents location-specific greenhouse gas intensity factor.
    gco2e_kwh: Grams of CO2 equivalent per kilowatt-hour.
    source: e.g. 'EIA 2024', 'Electricity Maps', 'EPA eGRID', 'DEFRA'
    valid_at: Historical or effective validity timestamp.
    """
    __tablename__ = "emission_factors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region = Column(String(50), nullable=False, index=True)
    valid_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    gco2e_kwh = Column(Float, nullable=False)
    source = Column(String(150), nullable=False, default="EIA / Grid Intensity")
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    carbon_estimates = relationship("CarbonEstimate", back_populates="factor")

    __table_args__ = (
        Index("ix_emission_factors_region_valid", "region", "valid_at"),
    )


class CarbonEstimate(Base):
    """
    Represents the calculated greenhouse gas emissions for an energy interval.
    grams_co2e = energy_kwh * pue * factor_gco2e_kwh
    model_version: Exact model policy version for auditing and reproducibility.
    """
    __tablename__ = "carbon_estimates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interval_id = Column(Integer, ForeignKey("energy_intervals.id"), nullable=False, index=True)
    factor_id = Column(Integer, ForeignKey("emission_factors.id"), nullable=False, index=True)
    host = Column(String(100), nullable=False, index=True)
    region = Column(String(50), nullable=False, index=True)
    energy_kwh = Column(Float, nullable=False)
    pue = Column(Float, nullable=False, default=1.20)
    grams_co2e = Column(Float, nullable=False)
    model_version = Column(String(100), nullable=False)
    provenance_hash = Column(String(64), nullable=True)
    calculated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    interval = relationship("EnergyInterval", back_populates="carbon_estimates")
    factor = relationship("EmissionFactor", back_populates="carbon_estimates")

    __table_args__ = (
        Index("ix_carbon_estimates_region_calculated", "region", "calculated_at"),
    )


class AuditLedger(Base):
    """
    Immutable ledger of state transitions, calculation decisions, factor updates,
    idempotent submissions, and anomalies.
    """
    __tablename__ = "audit_ledger"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idempotency_key = Column(String(100), nullable=True, unique=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    host = Column(String(100), nullable=True, index=True)
    payload_hash = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_ledger_created_at", "created_at"),
    )
