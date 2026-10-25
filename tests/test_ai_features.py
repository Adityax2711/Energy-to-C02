"""
Automated Test Suite for AI/ML Features
Covers P1 (Predictive Forecaster & Green Windows), P2 (Anomaly Detection),
P3 (Hardware Right-Sizing), and P4 (AI Sustainability Copilot).
"""
from datetime import datetime, timezone, timedelta
import pytest

from app.models.database_models import PowerSample
from app.services.ai_forecaster import AiTimeSeriesForecaster
from app.services.ai_anomaly_detector import AiPowerAnomalyDetector
from app.services.ai_rightsizing import AiHardwareRightSizer
from app.services.ai_copilot import AiSustainabilityCopilot


# ============================================================================
# P1: Forecaster & Green Windows Tests
# ============================================================================
def test_ai_forecaster_service(db_session):
    """Test Fourier harmonic time-series forecaster and green window detection."""
    # Seed 20 historical samples
    base_t = datetime.now(timezone.utc) - timedelta(hours=2)
    for i in range(25):
        s = PowerSample(
            host="forecast-node",
            timestamp=base_t + timedelta(minutes=5 * i),
            power_w=40.0 + (i % 5) * 8.0,
            source="test_fixture",
            quality="OK"
        )
        db_session.add(s)
    db_session.commit()

    forecast = AiTimeSeriesForecaster.generate_forecast(
        db=db_session,
        region="US-EAST",
        horizon_hours=12,
        pue=1.20,
        host="forecast-node"
    )

    assert forecast["status"] == "success"
    assert "predictions" in forecast
    assert len(forecast["predictions"]) > 0
    assert "model_metrics" in forecast
    assert "mae_watts" in forecast["model_metrics"]
    assert "green_window" in forecast
    assert "recommendation" in forecast["green_window"]
    assert "provenance" in forecast


def test_api_ai_forecast_endpoint(client):
    """Test GET /ai/forecast API endpoint."""
    res = client.get("/ai/forecast?horizon_hours=6&region=US-WEST")
    assert res.status_code == 200
    data = res.json()
    assert data["region"] == "US-WEST"
    assert len(data["predictions"]) > 0


# ============================================================================
# P2: AI Anomaly Detection Pipeline Tests
# ============================================================================
def test_ai_anomaly_detector_logic():
    """Test statistical Z-score and gradient surge anomaly detection."""
    detector = AiPowerAnomalyDetector(window_size=20, z_threshold=2.0, gradient_threshold=20.0)

    # Normal baseline samples
    for _ in range(10):
        detector.record_and_evaluate(40.0)

    # Sudden runaway spike from 40W to 180W
    surge_eval = detector.record_and_evaluate(180.0)
    assert surge_eval["is_anomaly"] is True
    assert surge_eval["severity"] in ["MEDIUM", "HIGH"]
    assert surge_eval["anomaly_score"] > 0.4
    assert "spiked" in surge_eval["diagnostic_message"].lower() or "surge" in surge_eval["diagnostic_message"].lower()


def test_api_ai_anomaly_endpoints(client):
    """Test /ai/anomalies/live and /ai/anomalies/evaluate."""
    # 1. Custom evaluation endpoint
    eval_res = client.post("/ai/anomalies/evaluate", json={"power_w": 210.0})
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert "anomaly_score" in data
    assert "severity" in data

    # 2. Live status endpoint
    live_res = client.get("/ai/anomalies/live")
    assert live_res.status_code == 200


# ============================================================================
# P3: Hardware Right-Sizing Tests
# ============================================================================
def test_ai_hardware_rightsizing_logic():
    """Test micro-architectural right-sizing from x86 Xeon to ARM Graviton3."""
    res = AiHardwareRightSizer.analyze_workload(
        current_instance_type="c6i.4xlarge",
        instance_count=2,
        observed_avg_cpu_percent=20.0,
        observed_peak_cpu_percent=38.0,
        source_region="us-east-1"
    )

    assert "recommendation" in res
    assert "c7g" in res["recommendation"]["target_instance_type"]  # Graviton3 recommended
    assert res["same_region_savings"]["monthly_kg_co2e_saved"] > 0
    assert res["same_region_savings"]["percent_carbon_reduction"] > 0
    assert res["combined_with_green_region"]["combined_percent_reduction"] > 80.0


def test_api_ai_rightsizing_endpoint(client):
    """Test POST /ai/rightsizing/evaluate endpoint."""
    res = client.post("/ai/rightsizing/evaluate", json={
        "current_instance_type": "c6i.4xlarge",
        "instance_count": 3,
        "observed_avg_cpu_percent": 25.0,
        "observed_peak_cpu_percent": 45.0,
        "source_region": "us-east-1"
    })
    assert res.status_code == 200
    data = res.json()
    assert "same_region_savings" in data


# ============================================================================
# P4: AI Sustainability Copilot Tests
# ============================================================================
def test_ai_copilot_service(db_session):
    """Test natural language intent classification and response generation."""
    # 1. ESG Scope 2 Report intent
    report_res = AiSustainabilityCopilot.process_query(db_session, "Generate ESG Scope 2 Report", region="US-EAST")
    assert report_res["query_type"] == "ESG_SCOPE_2_REPORT"
    assert "GHG Protocol" in report_res["response_markdown"]
    assert "metrics" in report_res

    # 2. Spike investigation intent
    spike_res = AiSustainabilityCopilot.process_query(db_session, "Why did emissions spike at 3pm?", region="US-EAST")
    assert spike_res["query_type"] == "ANOMALY_INVESTIGATION"

    # 3. Decarbonization advice intent
    opt_res = AiSustainabilityCopilot.process_query(db_session, "How can we optimize our cloud carbon footprint?", region="US-EAST")
    assert opt_res["query_type"] == "OPTIMIZATION_ADVISOR"


def test_api_ai_copilot_endpoint(client):
    """Test POST /ai/copilot/chat API endpoint."""
    res = client.post("/ai/copilot/chat", json={
        "query": "Please provide an executive ESG summary for our platform.",
        "region": "EU-CENTRAL",
        "pue": 1.18
    })
    assert res.status_code == 200
    data = res.json()
    assert "response_markdown" in data
    assert "suggested_actions" in data
