"""
FastAPI REST Routes and Controllers for Energy-to-CO2 Engine
"""
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.config import settings
from app.models.database_models import (
    PowerSample,
    EnergyInterval,
    EmissionFactor,
    CarbonEstimate,
    AuditLedger
)
from app.models.schemas import (
    PowerSampleCreate,
    PowerSampleResponse,
    EnergySummaryResponse,
    CarbonSummaryResponse,
    CarbonTimeseriesPoint,
    EmissionFactorCreate,
    EmissionFactorResponse,
    StressTestRequest,
    StressTestStatusResponse,
    AuditLedgerResponse,
    HealthResponse,
    AwsWorkloadOptimizationRequest,
    AwsSimulateTelemetryRequest,
    AiAnomalyEvaluationRequest,
    AiCopilotChatRequest,
    AiRightSizingRequest
)
from app.services.telemetry_collector import TelemetryCollectorService
from app.services.emissions_calculator import EmissionsCalculator
from app.services.stress_tester import stress_experiment_runner
from app.services.aws_service import AwsEc2CarbonService
from app.services.ai_forecaster import AiTimeSeriesForecaster
from app.services.ai_anomaly_detector import ai_anomaly_engine
from app.services.ai_rightsizing import AiHardwareRightSizer
from app.services.ai_copilot import AiSustainabilityCopilot
from app.api.metrics import (
    export_prometheus_metrics,
    GAUGE_POWER_WATTS,
    GAUGE_CARBON_INTENSITY,
    GAUGE_CARBON_RATE_GRAMS_PER_HOUR,
    COUNTER_ENERGY_WATTHOURS,
    COUNTER_ENERGY_KILOWATTHOURS,
    COUNTER_CARBON_GRAMS,
    COUNTER_TELEMETRY_SAMPLES,
    COUNTER_TELEMETRY_GAPS,
    GAUGE_AI_ANOMALY_SCORE,
    COUNTER_AI_ANOMALIES,
    GAUGE_AI_FORECAST_WATTS
)

router = APIRouter()
start_server_time = time.time()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """System health check, uptime, and database status."""
    try:
        sample_count = db.query(func.count(PowerSample.id)).scalar() or 0
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        sample_count = 0

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        model_version=settings.MODEL_VERSION,
        uptime_seconds=round(time.time() - start_server_time, 1),
        database=db_status,
        active_region=settings.DEFAULT_REGION,
        background_collector=settings.ENABLE_BACKGROUND_COLLECTOR,
        samples_ingested=sample_count
    )


@router.post("/telemetry", status_code=status.HTTP_201_CREATED, tags=["Telemetry"])
def ingest_telemetry(
    payload: PowerSampleCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    region: Optional[str] = Query(None, description="Optional target region for inline carbon attachment"),
    db: Session = Depends(get_db)
):
    """
    Ingest measured or simulated power watts with UTC timestamp, source provenance,
    and automatic unit-safe energy integration and regional carbon calculation.
    """
    result = TelemetryCollectorService.ingest_sample(
        db=db,
        sample_in=payload,
        idempotency_key=idempotency_key,
        region=region or settings.DEFAULT_REGION
    )

    # Update Prometheus metrics
    is_measured = "measured" if "psutil" in payload.source or "rapl" in payload.source else "simulated"
    GAUGE_POWER_WATTS.labels(
        host=payload.host,
        source=payload.source,
        type=is_measured
    ).set(payload.power_w)

    COUNTER_TELEMETRY_SAMPLES.labels(
        host=payload.host,
        quality=payload.quality or "OK"
    ).inc()

    if result.get("integration_status") == "GAP_DETECTED":
        COUNTER_TELEMETRY_GAPS.labels(host=payload.host).inc()

    if result.get("interval_energy_wh") and result["interval_energy_wh"] > 0:
        wh = result["interval_energy_wh"]
        kwh = wh / 1000.0
        COUNTER_ENERGY_WATTHOURS.labels(host=payload.host, method="trapezoidal").inc(wh)
        COUNTER_ENERGY_KILOWATTHOURS.labels(host=payload.host, method="trapezoidal").inc(kwh)

        if result.get("estimate"):
            gco2e = result["estimate"]["grams_co2e"]
            COUNTER_CARBON_GRAMS.labels(
                host=payload.host,
                region=result["estimate"]["region"],
                model_version=settings.MODEL_VERSION
            ).inc(gco2e)

            # Instantaneous rate: grams per hour = Power (kW) * PUE * factor
            factor_val = EmissionsCalculator.get_factor_for_region(db, result["estimate"]["region"]).gco2e_kwh
            grams_per_hour = (payload.power_w / 1000.0) * settings.DEFAULT_PUE * factor_val
            GAUGE_CARBON_RATE_GRAMS_PER_HOUR.labels(
                host=payload.host,
                region=result["estimate"]["region"]
            ).set(grams_per_hour)

    return result


@router.get("/telemetry/samples", response_model=List[PowerSampleResponse], tags=["Telemetry"])
def list_telemetry_samples(
    host: Optional[str] = Query(None, description="Filter by host identifier"),
    limit: int = Query(50, ge=1, le=500, description="Max samples to return"),
    db: Session = Depends(get_db)
):
    """Retrieve recent power samples chronologically."""
    query = db.query(PowerSample)
    if host:
        query = query.filter(PowerSample.host == host)
    return query.order_by(desc(PowerSample.timestamp)).limit(limit).all()


@router.get("/energy/summary", response_model=EnergySummaryResponse, tags=["Energy"])
def get_energy_summary(
    host: Optional[str] = Query(None, description="Optional host filter"),
    db: Session = Depends(get_db)
):
    """
    Summarize total energy integrated over time (Wh and kWh),
    average power, duration, and sample counts.
    """
    sample_query = db.query(
        func.count(PowerSample.id).label("cnt"),
        func.avg(PowerSample.power_w).label("avg_w"),
        func.max(PowerSample.timestamp).label("last_ts")
    )
    if host:
        sample_query = sample_query.filter(PowerSample.host == host)
    s_res = sample_query.one()

    interval_query = db.query(
        func.coalesce(func.sum(EnergyInterval.energy_wh), 0.0).label("total_wh"),
        func.coalesce(func.sum(EnergyInterval.energy_kwh), 0.0).label("total_kwh"),
        func.coalesce(func.sum(EnergyInterval.duration_seconds), 0.0).label("total_dur"),
        func.count(EnergyInterval.id).label("int_cnt")
    )
    if host:
        interval_query = interval_query.filter(EnergyInterval.host == host)
    i_res = interval_query.one()

    return EnergySummaryResponse(
        host=host,
        total_energy_wh=round(float(i_res.total_wh), 4),
        total_energy_kwh=round(float(i_res.total_kwh), 6),
        total_duration_seconds=round(float(i_res.total_dur), 1),
        average_power_w=round(float(s_res.avg_w or 0.0), 2),
        interval_count=int(i_res.int_cnt),
        sample_count=int(s_res.cnt),
        last_sample_at=s_res.last_ts,
        integration_method="trapezoidal"
    )


@router.get("/carbon/summary", response_model=CarbonSummaryResponse, tags=["Carbon"])
def get_carbon_summary(
    region: Optional[str] = Query(None, description="Regional grid (e.g. US-EAST, US-WEST, EU-CENTRAL, IN-SOUTH)"),
    host: Optional[str] = Query(None, description="Optional host filter"),
    pue: Optional[float] = Query(None, ge=1.0, le=3.0, description="Facility Power Usage Effectiveness overhead"),
    db: Session = Depends(get_db)
):
    """
    Retrieve location-specific greenhouse gas emissions estimate in grams, kilograms,
    and metric tons of CO2e with factor source provenance.
    """
    return EmissionsCalculator.get_carbon_summary(
        db=db,
        region=region,
        host=host,
        pue=pue
    )


@router.get("/carbon/timeseries", response_model=List[CarbonTimeseriesPoint], tags=["Carbon"])
def get_carbon_timeseries(
    region: Optional[str] = Query(None, description="Regional grid code"),
    host: Optional[str] = Query(None, description="Optional host filter"),
    limit: int = Query(60, ge=10, le=300, description="Number of points"),
    db: Session = Depends(get_db)
):
    """
    Generate timeseries data points combining instantaneous Watts, accumulated Wh,
    and cumulative gCO2e for live charting.
    """
    return EmissionsCalculator.get_timeseries_points(
        db=db,
        region=region,
        host=host,
        limit=limit
    )


@router.get("/regions", response_model=List[EmissionFactorResponse], tags=["Grid Intensity"])
def list_regions(db: Session = Depends(get_db)):
    """List available regional grid emission factors with validity dates and sources."""
    EmissionsCalculator.seed_default_factors_if_needed(db)
    return db.query(EmissionFactor).order_by(EmissionFactor.region).all()


@router.post("/regions", response_model=EmissionFactorResponse, status_code=status.HTTP_201_CREATED, tags=["Grid Intensity"])
def add_or_update_region_factor(
    payload: EmissionFactorCreate,
    db: Session = Depends(get_db)
):
    """Add or update an emission factor with provenance source and audit record."""
    valid_time = payload.valid_at or datetime.now(timezone.utc)
    factor = EmissionFactor(
        region=payload.region.upper(),
        gco2e_kwh=payload.gco2e_kwh,
        source=payload.source,
        valid_at=valid_time
    )
    db.add(factor)
    
    # Audit log
    audit = AuditLedger(
        event_type="EMISSION_FACTOR_UPDATED",
        details=f"Region {payload.region.upper()} set to {payload.gco2e_kwh} gCO2e/kWh ({payload.source})"
    )
    db.add(audit)
    db.commit()
    db.refresh(factor)

    # Update gauge
    GAUGE_CARBON_INTENSITY.labels(region=factor.region, source=factor.source).set(factor.gco2e_kwh)
    return factor


@router.post("/simulate/stress-test", tags=["Experiment"])
def trigger_stress_test(req: StressTestRequest):
    """
    Launch a controlled multi-stage stress test experiment:
    Baseline Idle -> Traffic Spike -> Sustained Heavy Load -> Cooldown.
    """
    result = stress_experiment_runner.start_experiment(req)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["error"])
    return result


@router.get("/simulate/status", response_model=StressTestStatusResponse, tags=["Experiment"])
def get_stress_test_status():
    """Query the status and live metrics of the controlled stress test experiment."""
    return stress_experiment_runner.get_status()


@router.get("/audit/ledger", response_model=List[AuditLedgerResponse], tags=["Audit & Provenance"])
def get_audit_ledger(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """View the immutable audit ledger of decisions, state transitions, and provenance."""
    return db.query(AuditLedger).order_by(desc(AuditLedger.created_at)).limit(limit).all()


@router.get("/metrics", tags=["Observability"])
def get_metrics():
    """Prometheus exposition metrics endpoint for scraping."""
    return export_prometheus_metrics()


# ============================================================================
# AWS Cloud Carbon Modeling & Spatial Optimization Endpoints
# ============================================================================
@router.get("/aws/instances", response_model=List[Dict[str, Any]], tags=["AWS Cloud Carbon"])
def get_aws_instance_catalog():
    """List available AWS EC2 instance types with hardware specifications, vCPU, RAM, and TDP profiles."""
    return AwsEc2CarbonService.list_instances()


@router.get("/aws/regions", response_model=List[Dict[str, Any]], tags=["AWS Cloud Carbon"])
def get_aws_regions():
    """List supported AWS regions with their regional electrical grid carbon intensities."""
    return AwsEc2CarbonService.list_regions()


@router.post("/aws/optimize", response_model=Dict[str, Any], tags=["AWS Cloud Carbon"])
def optimize_aws_workload(
    req: AwsWorkloadOptimizationRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate the carbon emissions of running an EC2 workload in a source AWS region
    versus a target green region, providing verified carbon reduction metrics and equivalencies.
    """
    try:
        analysis = AwsEc2CarbonService.optimize_workload(
            instance_type=req.instance_type,
            instance_count=req.instance_count,
            cpu_utilization_percent=req.cpu_utilization_percent,
            hours_per_month=req.hours_per_month,
            source_region=req.source_region,
            target_region=req.target_region,
            custom_pue=req.pue
        )

        # Record to immutable audit ledger
        audit = AuditLedger(
            event_type="AWS_WORKLOAD_OPTIMIZED",
            host=f"aws-cluster-{req.instance_type}",
            payload_hash=analysis.get("provenance_hash"),
            details=f"Optimized {req.instance_count}x {req.instance_type} from {req.source_region} to {req.target_region or 'eu-north-1'}: Saved {analysis['optimization_delta']['saved_kg_co2e_monthly']} kg CO2e/mo ({analysis['optimization_delta']['percent_reduction']}%)"
        )
        db.add(audit)
        db.commit()

        return analysis
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/aws/inject-telemetry", status_code=status.HTTP_201_CREATED, tags=["AWS Cloud Carbon"])
def inject_aws_telemetry(
    req: AwsSimulateTelemetryRequest,
    db: Session = Depends(get_db)
):
    """
    Inject a real-time AWS EC2 power sample directly into the live engine's stream,
    automatically triggering trapezoidal energy integration and regional carbon calculation.
    """
    try:
        power_data = AwsEc2CarbonService.calculate_instance_power(
            req.instance_type,
            req.cpu_utilization_percent
        )
        total_watts = power_data["power_watts"] * req.instance_count
        host_name = req.host_tag or f"aws-ec2-{req.instance_type}-{req.region.lower().replace('-', '')}"

        sample = PowerSampleCreate(
            host=host_name,
            timestamp=datetime.now(timezone.utc),
            power_w=round(total_watts, 2),
            source=f"aws_ec2_cloudwatch_{req.instance_type}",
            quality="OK"
        )

        result = TelemetryCollectorService.ingest_sample(
            db=db,
            sample_in=sample,
            region=req.region
        )
        return {
            "status": "injected",
            "aws_instance_type": req.instance_type,
            "instance_count": req.instance_count,
            "modeled_watts": round(total_watts, 2),
            "region": req.region,
            "telemetry_result": result
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ============================================================================
# P1: AI Predictive Time-Series Forecasting & Green Windows
# ============================================================================
@router.get("/ai/forecast", tags=["AI Predictive Forecaster"])
def get_ai_forecast(
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours"),
    region: str = Query("US-EAST", description="Regional electrical grid code"),
    pue: float = Query(1.20, ge=1.0, le=2.5, description="Datacenter PUE overhead"),
    host: Optional[str] = Query(None, description="Optional host filter"),
    db: Session = Depends(get_db)
):
    """
    P1: Predict continuous future power draw (Watts) and carbon emissions (gCO2e/hr)
    using Fourier harmonic decomposition and Ridge regression with 95% confidence intervals
    and automated Green Computing Window detection.
    """
    result = AiTimeSeriesForecaster.generate_forecast(
        db=db,
        region=region,
        horizon_hours=horizon_hours,
        pue=pue,
        host=host
    )
    if result.get("predictions"):
        next_w = result["predictions"][0]["predicted_power_w"]
        GAUGE_AI_FORECAST_WATTS.labels(host=host or "cluster-wide", horizon_hours=str(horizon_hours)).set(next_w)
    return result


# ============================================================================
# P2: Full AI Anomaly Detection Pipeline
# ============================================================================
@router.get("/ai/anomalies/live", tags=["AI Anomaly Detection"])
def get_live_anomaly_status(
    host: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    P2: Evaluate real-time anomaly score and runaway workload status for the latest telemetry sample.
    """
    query = db.query(PowerSample)
    if host:
        query = query.filter(PowerSample.host == host)
    latest = query.order_by(desc(PowerSample.timestamp)).first()
    
    if not latest:
        return {
            "power_w": 0.0,
            "anomaly_score": 0.0,
            "status": "NORMAL",
            "severity": "LOW",
            "is_anomaly": False,
            "diagnostic_message": "No telemetry samples recorded yet."
        }

    eval_result = ai_anomaly_engine.record_and_evaluate(latest.power_w, latest.timestamp)
    GAUGE_AI_ANOMALY_SCORE.labels(host=latest.host, severity=eval_result["severity"]).set(eval_result["anomaly_score"])
    if eval_result["is_anomaly"]:
        COUNTER_AI_ANOMALIES.labels(host=latest.host, severity=eval_result["severity"]).inc()
    return eval_result


@router.post("/ai/anomalies/evaluate", tags=["AI Anomaly Detection"])
def evaluate_custom_anomaly(
    req: AiAnomalyEvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    P2: Explicitly evaluate an arbitrary instantaneous power reading for anomaly status.
    """
    eval_result = ai_anomaly_engine.record_and_evaluate(req.power_w, req.timestamp)
    if eval_result["is_anomaly"]:
        audit = AuditLedger(
            event_type=f"ANOMALY_{eval_result['severity']}",
            details=eval_result["diagnostic_message"],
            host=settings.DEFAULT_HOST
        )
        db.add(audit)
        db.commit()
    return eval_result


# ============================================================================
# P3: Hardware Right-Sizing & Cloud Migration Engine
# ============================================================================
@router.post("/ai/rightsizing/evaluate", tags=["AI Hardware Right-Sizing"])
def evaluate_hardware_rightsizing(req: AiRightSizingRequest):
    """
    P3: Analyze workload utilization against CPU/GPU TDP microarchitectural envelopes
    and compute exact carbon and cost savings across AWS Graviton and green regions.
    """
    try:
        return AiHardwareRightSizer.analyze_workload(
            current_instance_type=req.current_instance_type,
            instance_count=req.instance_count,
            observed_avg_cpu_percent=req.observed_avg_cpu_percent,
            observed_peak_cpu_percent=req.observed_peak_cpu_percent,
            source_region=req.source_region
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ============================================================================
# P4: AI Sustainability Copilot (Natural Language Assistant)
# ============================================================================
@router.post("/ai/copilot/chat", tags=["AI Sustainability Copilot"])
def chat_with_copilot(
    req: AiCopilotChatRequest,
    db: Session = Depends(get_db)
):
    """
    P4: Natural-language sustainability copilot. Answers questions on telemetry spikes,
    generates GHG Protocol Scope 2 executive reports, and advises on decarbonization strategies.
    """
    return AiSustainabilityCopilot.process_query(
        db=db,
        query=req.query,
        region=req.region,
        pue=req.pue
    )

