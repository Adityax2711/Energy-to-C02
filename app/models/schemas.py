"""
Pydantic Schemas for Request/Response Validation and Serialization
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PowerSampleCreate(BaseModel):
    host: str = Field(..., min_length=1, max_length=100, description="Host identifier or workload ID")
    timestamp: datetime = Field(..., description="Sample timestamp in UTC")
    power_w: float = Field(..., ge=0.0, le=100000.0, description="Instantaneous power in Watts (must be non-negative)")
    source: str = Field(default="simulator", max_length=100, description="Telemetry sensor source (e.g. psutil, rapl, smart_plug, simulator)")
    quality: Optional[str] = Field(default="OK", max_length=50, description="Quality descriptor (e.g. OK, INTERPOLATED)")

    @field_validator("power_w")
    @classmethod
    def validate_power_w(cls, v: float) -> float:
        if v < 0:
            raise ValueError("power_w must be non-negative (>= 0.0)")
        return v


class PowerSampleResponse(BaseModel):
    id: int
    host: str
    timestamp: datetime
    power_w: float
    source: str
    quality: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnergyIntervalResponse(BaseModel):
    id: int
    host: str
    start_at: datetime
    end_at: datetime
    duration_seconds: float
    energy_wh: float
    energy_kwh: float
    method: str
    quality: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmissionFactorCreate(BaseModel):
    region: str = Field(..., min_length=2, max_length=50, description="Regional grid identifier (e.g. US-EAST, EU-CENTRAL)")
    gco2e_kwh: float = Field(..., ge=0.0, le=2000.0, description="Emissions factor in gCO2e/kWh")
    source: str = Field(..., min_length=2, max_length=150, description="Data provider or reference standard")
    valid_at: Optional[datetime] = Field(default=None, description="Timestamp when factor became effective")


class EmissionFactorResponse(BaseModel):
    id: int
    region: str
    valid_at: datetime
    gco2e_kwh: float
    source: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CarbonEstimateResponse(BaseModel):
    id: int
    interval_id: int
    factor_id: int
    host: str
    region: str
    energy_kwh: float
    pue: float
    grams_co2e: float
    model_version: str
    provenance_hash: Optional[str]
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnergySummaryResponse(BaseModel):
    host: Optional[str]
    total_energy_wh: float
    total_energy_kwh: float
    total_duration_seconds: float
    average_power_w: float
    interval_count: int
    sample_count: int
    last_sample_at: Optional[datetime]
    integration_method: str


class CarbonSummaryResponse(BaseModel):
    region: str
    host_filter: Optional[str]
    factor_gco2e_kwh: float
    factor_source: str
    factor_valid_at: datetime
    pue: float
    total_energy_kwh: float
    total_grams_co2e: float
    total_kg_co2e: float
    total_metric_tons_co2e: float
    model_version: str
    last_calculated_at: Optional[datetime]
    provenance_sample: Optional[Dict[str, Any]] = None


class CarbonTimeseriesPoint(BaseModel):
    timestamp: datetime
    host: str
    power_w: float
    cumulative_energy_wh: float
    cumulative_grams_co2e: float
    interval_grams_co2e: float
    region: str
    quality: str


class StressTestRequest(BaseModel):
    duration_seconds: int = Field(default=30, ge=5, le=300, description="Total duration of the controlled experiment")
    profile: str = Field(default="tiered", description="Profile: 'tiered' (baseline->spike->sustained->cooldown), 'spike', or 'constant'")
    target_load_percent: float = Field(default=85.0, ge=10.0, le=100.0, description="Peak load target percentage")
    host: Optional[str] = Field(default=None, description="Host to label workload under")


class StressTestStatusResponse(BaseModel):
    is_running: bool
    stage: str
    elapsed_seconds: float
    duration_seconds: float
    progress_percent: float
    profile: str
    current_power_w: float
    current_load_percent: float
    cumulative_wh: float
    cumulative_gco2e: float
    summary: Optional[Dict[str, Any]] = None


class AuditLedgerResponse(BaseModel):
    id: int
    idempotency_key: Optional[str]
    event_type: str
    host: Optional[str]
    payload_hash: Optional[str]
    details: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    version: str
    model_version: str
    uptime_seconds: float
    database: str
    active_region: str
    background_collector: bool
    samples_ingested: int


# ============================================================================
# AWS Cloud Carbon Modeling & Optimization Schemas
# ============================================================================
class AwsWorkloadOptimizationRequest(BaseModel):
    instance_type: str = Field(default="c6i.4xlarge", description="AWS EC2 Instance Type (e.g., c6i.4xlarge, c7g.4xlarge, g5.2xlarge)")
    instance_count: int = Field(default=1, ge=1, le=1000, description="Number of instances running the workload")
    cpu_utilization_percent: float = Field(default=75.0, ge=1.0, le=100.0, description="Average CPU utilization percentage (1-100%)")
    hours_per_month: float = Field(default=730.0, ge=1.0, le=744.0, description="Operating hours per month (standard full month is 730h)")
    source_region: str = Field(default="us-east-1", description="Source AWS Region where workload currently runs")
    target_region: Optional[str] = Field(default="eu-north-1", description="Target green AWS Region to evaluate shifting to")
    pue: Optional[float] = Field(default=None, ge=1.0, le=2.0, description="Optional custom Datacenter PUE (defaults to AWS regional standard ~1.12-1.15)")


class AwsSimulateTelemetryRequest(BaseModel):
    instance_type: str = Field(default="c6i.4xlarge", description="EC2 instance type to simulate")
    instance_count: int = Field(default=1, ge=1, le=100, description="Number of instances")
    cpu_utilization_percent: float = Field(default=75.0, ge=1.0, le=100.0, description="Target CPU utilization")
    region: str = Field(default="us-east-1", description="AWS Region to assign telemetry to")
    host_tag: Optional[str] = Field(default=None, description="Optional host label for telemetry stream")


# ============================================================================
# AI Anomaly Detection & Cloud Right-Sizing Schemas
# ============================================================================
class AiAnomalyStatusResponse(BaseModel):
    power_w: float
    anomaly_score: float
    status: str
    severity: str
    z_score: float
    rolling_mean_w: float
    rolling_std_w: float
    gradient_w_per_sec: float
    is_anomaly: bool
    diagnostic_message: str
    evaluated_at: Optional[str] = None


class AiRightSizingRequest(BaseModel):
    current_instance_type: str = Field(default="c6i.4xlarge", description="Current provisioned EC2 instance type")
    instance_count: int = Field(default=5, ge=1, le=500, description="Fleet size")
    observed_avg_cpu_percent: float = Field(default=22.0, ge=1.0, le=100.0, description="Observed mean CPU utilization (%)")
    observed_peak_cpu_percent: float = Field(default=42.0, ge=1.0, le=100.0, description="Observed peak CPU utilization (%)")
    source_region: str = Field(default="us-east-1", description="Current operating AWS Region")


class AiAnomalyEvaluationRequest(BaseModel):
    power_w: float = Field(..., ge=0.0, description="Power in Watts to evaluate for anomaly status")
    timestamp: Optional[datetime] = Field(default=None, description="Optional evaluation timestamp")


class AiCopilotChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Natural language question or request")
    region: Optional[str] = Field(default="US-EAST", description="Contextual electrical grid region")
    pue: Optional[float] = Field(default=1.20, ge=1.0, le=2.5, description="Datacenter PUE context")



