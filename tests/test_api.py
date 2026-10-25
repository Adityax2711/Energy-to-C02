"""
End-to-End REST API and Prometheus Endpoint Tests
"""
from datetime import datetime, timezone, timedelta
import pytest


def test_api_health_endpoint(client):
    """Test /health endpoint returns healthy status and metadata."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "model_version" in data


def test_api_telemetry_ingest_and_summary(client):
    """
    Test POST /telemetry ingestion pipeline followed by GET /energy/summary
    and GET /carbon/summary.
    """
    t0 = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=10)

    # Ingest Sample 1 (100W)
    res1 = client.post("/telemetry", json={
        "host": "api-test-node",
        "timestamp": t0.isoformat(),
        "power_w": 100.0,
        "source": "api_test"
    })
    assert res1.status_code == 201
    assert res1.json()["status"] == "success"

    # Ingest Sample 2 (100W, 10 seconds later)
    # Energy: 100W * (10 / 3600) hr = 0.277777 Wh
    res2 = client.post("/telemetry", json={
        "host": "api-test-node",
        "timestamp": t1.isoformat(),
        "power_w": 100.0,
        "source": "api_test"
    })
    assert res2.status_code == 201
    assert res2.json()["integration_status"] == "INTEGRATED"
    assert pytest.approx(res2.json()["interval_energy_wh"], rel=1e-3) == 0.277778

    # Verify /energy/summary
    res_energy = client.get("/energy/summary?host=api-test-node")
    assert res_energy.status_code == 200
    e_data = res_energy.json()
    assert e_data["interval_count"] == 1
    assert e_data["sample_count"] == 2
    assert e_data["total_energy_wh"] > 0

    # Verify /carbon/summary
    res_carbon = client.get("/carbon/summary?region=US-EAST&host=api-test-node")
    assert res_carbon.status_code == 200
    c_data = res_carbon.json()
    assert c_data["region"] == "US-EAST"
    assert c_data["total_grams_co2e"] > 0
    assert "provenance_sample" in c_data


def test_api_prometheus_metrics_export(client):
    """
    Test GET /metrics delivers valid Prometheus exposition format.
    """
    # Ingest a sample first
    client.post("/telemetry", json={
        "host": "prom-node",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "power_w": 82.5,
        "source": "prom_test"
    })

    res = client.get("/metrics")
    assert res.status_code == 200
    content = res.text
    assert "energy_power_watts" in content
    assert "carbon_emissions_grams_total" in content
    assert "telemetry_samples_total" in content


def test_api_regions_endpoints(client):
    """Test listing and adding regions."""
    res = client.get("/regions")
    assert res.status_code == 200
    regions = res.json()
    assert len(regions) >= 1

    # Add a new region
    new_reg = {
        "region": "UK-NATIONAL",
        "gco2e_kwh": 185.0,
        "source": "National Grid ESO Carbon Intensity API"
    }
    res_create = client.post("/regions", json=new_reg)
    assert res_create.status_code == 201
    assert res_create.json()["region"] == "UK-NATIONAL"


def test_api_audit_ledger_view(client):
    """Test retrieving immutable audit ledger entries."""
    res = client.get("/audit/ledger?limit=10")
    assert res.status_code == 200
    ledger = res.json()
    assert isinstance(ledger, list)
