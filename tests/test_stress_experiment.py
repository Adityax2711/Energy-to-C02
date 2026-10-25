"""
Controlled Stress-Test Experiment Tests
Verifies API endpoints, schema validation, and stage calculation logic.
"""
from app.services.stress_tester import ControlledStressExperiment, stress_experiment_runner
from app.models.schemas import StressTestRequest


def test_stress_test_status_endpoint(client):
    """
    Test GET /simulate/status returns valid operational state and telemetry schema.
    """
    status_res = client.get("/simulate/status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert "is_running" in data
    assert "stage" in data
    assert "current_power_w" in data
    assert "cumulative_wh" in data
    assert "cumulative_gco2e" in data


def test_stress_experiment_lifecycle():
    """
    Unit test for ControlledStressExperiment state machine and calculations.
    """
    exp = ControlledStressExperiment()
    status = exp.get_status()
    assert status["is_running"] is False
    assert status["stage"] == "IDLE"
    assert status["duration_seconds"] == 30

    # Verify stop flag handling
    exp.stop_experiment()
    assert exp._stop_event.is_set()


def test_stress_test_trigger_endpoint(client, monkeypatch):
    """
    Test POST /simulate/stress-test endpoint triggers experiment.
    """
    monkeypatch.setattr(
        stress_experiment_runner,
        "start_experiment",
        lambda req: {"message": "Stress test experiment started", "status": stress_experiment_runner.get_status()}
    )

    res = client.post("/simulate/stress-test", json={
        "duration_seconds": 15,
        "profile": "tiered",
        "target_load_percent": 85.0
    })
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
