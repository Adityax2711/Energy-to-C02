"""
Prometheus Metrics Registry and Exporter
Exposes real-time gauges, counters, and histograms for Prometheus / Grafana observability.
Labels estimates and measured readings separately.
"""
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import Response

# Primary Registry
REGISTRY = CollectorRegistry(auto_describe=True)

# Gauges: Instantaneous physical measurements
GAUGE_POWER_WATTS = Gauge(
    "energy_power_watts",
    "Current instantaneous power telemetry in Watts",
    ["host", "source", "type"],  # type: 'measured' vs 'simulated'
    registry=REGISTRY
)

GAUGE_CARBON_INTENSITY = Gauge(
    "carbon_grid_intensity_gco2e_per_kwh",
    "Current regional grid carbon intensity in gCO2e/kWh",
    ["region", "source"],
    registry=REGISTRY
)

GAUGE_CARBON_RATE_GRAMS_PER_HOUR = Gauge(
    "carbon_emission_rate_grams_per_hour",
    "Current instantaneous carbon emission rate in grams CO2e per hour",
    ["host", "region"],
    registry=REGISTRY
)

# Counters: Cumulative time-integrated quantities
COUNTER_ENERGY_WATTHOURS = Counter(
    "energy_integrated_watthours_total",
    "Cumulative integrated energy in Watt-hours (Wh)",
    ["host", "method"],
    registry=REGISTRY
)

COUNTER_ENERGY_KILOWATTHOURS = Counter(
    "energy_integrated_kilowatthours_total",
    "Cumulative integrated energy in kilowatt-hours (kWh)",
    ["host", "method"],
    registry=REGISTRY
)

COUNTER_CARBON_GRAMS = Counter(
    "carbon_emissions_grams_total",
    "Cumulative location-based greenhouse gas emissions in grams CO2 equivalent",
    ["host", "region", "model_version"],
    registry=REGISTRY
)

COUNTER_TELEMETRY_SAMPLES = Counter(
    "telemetry_samples_total",
    "Total count of telemetry samples ingested",
    ["host", "quality"],
    registry=REGISTRY
)

COUNTER_TELEMETRY_GAPS = Counter(
    "telemetry_gaps_total",
    "Total count of sensor telemetry gaps exceeding threshold",
    ["host"],
    registry=REGISTRY
)

HISTOGRAM_API_LATENCY = Histogram(
    "api_request_duration_seconds",
    "Latency of API request handling in seconds",
    ["endpoint", "method"],
    registry=REGISTRY
)

# AI / ML Observability Metrics
GAUGE_AI_ANOMALY_SCORE = Gauge(
    "ai_anomaly_score",
    "Current real-time AI power telemetry anomaly score (0.0 normal to 1.0 critical runaway)",
    ["host", "severity"],
    registry=REGISTRY
)

COUNTER_AI_ANOMALIES = Counter(
    "ai_anomalies_detected_total",
    "Total count of AI detected anomalies categorized by severity",
    ["host", "severity"],
    registry=REGISTRY
)

GAUGE_AI_FORECAST_WATTS = Gauge(
    "ai_forecast_predicted_watts",
    "AI forward predicted power consumption in Watts",
    ["host", "horizon_hours"],
    registry=REGISTRY
)


def export_prometheus_metrics() -> Response:
    """Generate Prometheus exposition text format response."""
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
