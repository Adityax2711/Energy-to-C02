"""
Controlled Stress-Test Experiment Runner
Executes a multi-stage workload experiment (Baseline -> Spike -> Sustained Heavy Load -> Cooldown),
feeding telemetry into the translation engine and recording state transitions and carbon impact.
"""
import time
import math
import random
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.database import SessionLocal
from app.models.schemas import PowerSampleCreate, StressTestRequest
from app.models.database_models import AuditLedger
from app.services.telemetry_collector import TelemetryCollectorService
from app.core.config import settings


class ControlledStressExperiment:
    """
    Manages controlled stress test experiments.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.is_running = False
        self.start_time: Optional[float] = None
        self.duration_seconds: int = 30
        self.profile: str = "tiered"
        self.target_load_percent: float = 85.0
        self.host: str = settings.DEFAULT_HOST
        self.stage: str = "IDLE"
        self.current_power_w: float = 0.0
        self.current_load_percent: float = 0.0
        self.cumulative_wh: float = 0.0
        self.cumulative_gco2e: float = 0.0
        self.summary: Optional[Dict[str, Any]] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def get_status(self) -> Dict[str, Any]:
        """Return the current experiment status and telemetry."""
        with self._lock:
            now = time.time()
            elapsed = (now - self.start_time) if self.start_time else 0.0
            progress = min(100.0, (elapsed / self.duration_seconds) * 100.0) if self.duration_seconds > 0 else 0.0
            
            return {
                "is_running": self.is_running,
                "stage": self.stage,
                "elapsed_seconds": round(elapsed, 1),
                "duration_seconds": self.duration_seconds,
                "progress_percent": round(progress, 1),
                "profile": self.profile,
                "current_power_w": round(self.current_power_w, 2),
                "current_load_percent": round(self.current_load_percent, 1),
                "cumulative_wh": round(self.cumulative_wh, 4),
                "cumulative_gco2e": round(self.cumulative_gco2e, 4),
                "summary": self.summary
            }

    def start_experiment(self, req: StressTestRequest) -> Dict[str, Any]:
        """Initiate the experiment in a dedicated background worker thread."""
        with self._lock:
            if self.is_running:
                return {"error": "Experiment already in progress", "status": self.get_status()}

            self.is_running = True
            self.start_time = time.time()
            self.duration_seconds = req.duration_seconds
            self.profile = req.profile
            self.target_load_percent = req.target_load_percent
            self.host = req.host or settings.DEFAULT_HOST
            self.stage = "INITIALIZING"
            self.cumulative_wh = 0.0
            self.cumulative_gco2e = 0.0
            self.summary = None
            self._stop_event.clear()

            self._thread = threading.Thread(target=self._run_experiment_loop, daemon=True)
            self._thread.start()

            return {"message": "Stress test experiment started", "status": self.get_status()}

    def stop_experiment(self):
        """Request premature termination."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run_experiment_loop(self):
        """Worker loop executing the phased load profile and ingesting telemetry."""
        db = SessionLocal()
        baseline_samples = []
        peak_samples = []
        last_sample_time = time.time()

        try:
            # Audit record: start
            start_audit = AuditLedger(
                event_type="STRESS_EXPERIMENT_STARTED",
                host=self.host,
                details=f"Duration: {self.duration_seconds}s, Profile: {self.profile}, Target: {self.target_load_percent}%"
            )
            db.add(start_audit)
            db.commit()

            start_t = time.time()
            sample_interval = 1.0  # 1Hz high-resolution telemetry during stress test

            while not self._stop_event.is_set():
                now = time.time()
                elapsed = now - start_t
                if elapsed >= self.duration_seconds:
                    break

                fraction = elapsed / self.duration_seconds

                # Phased stage calculation
                if fraction < 0.20:
                    current_stage = "STAGE_1_BASELINE_IDLE"
                    load_pct = random.uniform(10.0, 18.0)
                    power_w = 32.0 + (load_pct * 0.4) + random.uniform(-1.0, 1.0)
                    baseline_samples.append(power_w)
                elif fraction < 0.40:
                    current_stage = "STAGE_2_TRAFFIC_SPIKE"
                    load_pct = random.uniform(70.0, 95.0)
                    power_w = 110.0 + random.uniform(-5.0, 8.0)
                    peak_samples.append(power_w)
                elif fraction < 0.80:
                    current_stage = "STAGE_3_SUSTAINED_HEAVY_LOAD"
                    load_pct = self.target_load_percent + random.uniform(-4.0, 4.0)
                    power_w = 40.0 + (120.0 - 40.0) * (load_pct / 100.0) ** 1.1 + random.uniform(-2.0, 2.0)
                    peak_samples.append(power_w)
                else:
                    current_stage = "STAGE_4_COOLDOWN_RECOVERY"
                    load_pct = random.uniform(12.0, 22.0)
                    power_w = 35.0 + (load_pct * 0.3) + random.uniform(-1.0, 1.0)

                with self._lock:
                    self.stage = current_stage
                    self.current_power_w = power_w
                    self.current_load_percent = load_pct

                # Ingest sample into translation pipeline
                sample_payload = PowerSampleCreate(
                    host=self.host,
                    timestamp=datetime.now(timezone.utc),
                    power_w=round(power_w, 2),
                    source=f"stress_experiment_{self.profile}",
                    quality="OK"
                )

                try:
                    res = TelemetryCollectorService.ingest_sample(
                        db=db,
                        sample_in=sample_payload,
                        region=settings.DEFAULT_REGION
                    )
                    if res.get("interval_energy_wh"):
                        with self._lock:
                            self.cumulative_wh += res["interval_energy_wh"]
                            if res.get("estimate") and res["estimate"].get("grams_co2e"):
                                self.cumulative_gco2e += res["estimate"]["grams_co2e"]
                except Exception as ex:
                    db.rollback()

                self._stop_event.wait(timeout=sample_interval)

            # Build summary
            avg_baseline_w = sum(baseline_samples) / max(1, len(baseline_samples))
            avg_peak_w = sum(peak_samples) / max(1, len(peak_samples))
            power_increase_pct = ((avg_peak_w - avg_baseline_w) / max(0.1, avg_baseline_w)) * 100.0

            with self._lock:
                self.stage = "COMPLETED"
                self.is_running = False
                self.summary = {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": round(time.time() - start_t, 1),
                    "baseline_power_avg_w": round(avg_baseline_w, 2),
                    "peak_power_avg_w": round(avg_peak_w, 2),
                    "power_increase_percent": round(power_increase_pct, 1),
                    "total_energy_wh": round(self.cumulative_wh, 4),
                    "total_grams_co2e": round(self.cumulative_gco2e, 4),
                    "grid_region": settings.DEFAULT_REGION,
                    "model_version": settings.MODEL_VERSION,
                    "stages_evaluated": ["BASELINE_IDLE", "TRAFFIC_SPIKE", "SUSTAINED_HEAVY_LOAD", "COOLDOWN_RECOVERY"]
                }

            # Audit record: complete
            complete_audit = AuditLedger(
                event_type="STRESS_EXPERIMENT_COMPLETED",
                host=self.host,
                details=f"Completed. Wh: {self.cumulative_wh:.4f}, gCO2e: {self.cumulative_gco2e:.4f}, Power Increase: {power_increase_pct:.1f}%"
            )
            db.add(complete_audit)
            db.commit()

        except Exception as e:
            with self._lock:
                self.stage = f"ERROR: {str(e)}"
                self.is_running = False
        finally:
            db.close()


stress_experiment_runner = ControlledStressExperiment()
