"""
Unit and Integration Tests for AWS Cloud Carbon Modeling & Spatial Optimizer
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.aws_service import AwsEc2CarbonService, AWS_EC2_CATALOG, AWS_REGION_GRID_MAP


@pytest.fixture
def client():
    return TestClient(app)


def test_aws_service_instance_catalog():
    """Verify EC2 catalog contains key instance types and valid TDP envelopes."""
    instances = AwsEc2CarbonService.list_instances()
    assert len(instances) >= 5

    # Check c6i.4xlarge
    c6i = next(i for i in instances if i["instance_type"] == "c6i.4xlarge")
    assert c6i["vcpu"] == 16
    assert c6i["max_tdp_w"] == 220.0
    assert c6i["idle_w"] == 45.0

    # Check Graviton3 c7g.4xlarge
    c7g = next(i for i in instances if i["instance_type"] == "c7g.4xlarge")
    assert "Graviton3" in c7g["arch"]
    assert c7g["max_tdp_w"] < c6i["max_tdp_w"]  # ARM efficiency guarantee


def test_aws_service_power_calculation():
    """Test non-linear power calculation under different loads."""
    # At 0% CPU load, power should equal idle baseline
    idle_result = AwsEc2CarbonService.calculate_instance_power("c6i.4xlarge", 0.0)
    assert idle_result["power_watts"] == 45.0

    # At 100% CPU load, power should reach max TDP
    peak_result = AwsEc2CarbonService.calculate_instance_power("c6i.4xlarge", 100.0)
    assert peak_result["power_watts"] == 220.0

    # At 50% CPU load, power should be between idle and peak
    mid_result = AwsEc2CarbonService.calculate_instance_power("c6i.4xlarge", 50.0)
    assert 45.0 < mid_result["power_watts"] < 220.0


def test_aws_service_workload_optimization():
    """Test regional carbon shifting from us-east-1 to eu-north-1."""
    result = AwsEc2CarbonService.optimize_workload(
        instance_type="c6i.4xlarge",
        instance_count=5,
        cpu_utilization_percent=75.0,
        hours_per_month=730.0,
        source_region="us-east-1",
        target_region="eu-north-1"
    )

    # Check calculations
    assert result["optimization_delta"]["is_beneficial"] is True
    # eu-north-1 (45 g/kWh) vs us-east-1 (380.5 g/kWh) -> ~88% reduction
    assert 85.0 < result["optimization_delta"]["percent_reduction"] < 90.0
    assert result["optimization_delta"]["saved_kg_co2e_monthly"] > 0
    assert result["real_world_equivalents"]["mature_trees_planted_offset_months"] > 0
    assert result["provenance_hash"] is not None


def test_api_aws_instance_and_region_endpoints(client):
    """Test REST GET /aws/instances and /aws/regions endpoints."""
    res_inst = client.get("/aws/instances")
    assert res_inst.status_code == 200
    inst_data = res_inst.json()
    assert len(inst_data) >= 5

    res_reg = client.get("/aws/regions")
    assert res_reg.status_code == 200
    reg_data = res_reg.json()
    regions = [r["region_code"] for r in reg_data]
    assert "us-east-1" in regions
    assert "eu-north-1" in regions


def test_api_aws_optimize_endpoint(client):
    """Test POST /aws/optimize endpoint and audit ledger recording."""
    payload = {
        "instance_type": "g5.2xlarge",
        "instance_count": 2,
        "cpu_utilization_percent": 80.0,
        "hours_per_month": 730.0,
        "source_region": "us-east-1",
        "target_region": "eu-north-1"
    }
    res = client.post("/aws/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["instance_profile"]["instance_type"] == "g5.2xlarge"
    assert data["optimization_delta"]["percent_reduction"] > 80.0

    # Verify audit ledger has this event
    res_ledger = client.get("/audit/ledger?limit=5")
    assert res_ledger.status_code == 200
    ledger_entries = res_ledger.json()
    assert any(e["event_type"] == "AWS_WORKLOAD_OPTIMIZED" for e in ledger_entries)


def test_api_aws_inject_telemetry(client):
    """Test POST /aws/inject-telemetry feeding into live engine."""
    payload = {
        "instance_type": "t4g.xlarge",
        "instance_count": 4,
        "cpu_utilization_percent": 60.0,
        "region": "us-west-2"
    }
    res = client.post("/aws/inject-telemetry", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "injected"
    assert data["aws_instance_type"] == "t4g.xlarge"
    assert data["modeled_watts"] > 0
    assert data["telemetry_result"]["status"] == "success"
