"""
AI Power Telemetry Anomaly & Runaway Workload Detector
Uses dynamic statistical windowing, exponential moving statistics, and gradient spurts
to detect runaway CPU loops, memory leak thrashing, crypto-mining, and rogue workloads.
"""
from datetime import datetime, timezone
import math
import collections
from typing import Dict, Any, List, Optional
import json

from app.core.provenance import compute_payload_hash


class AiPowerAnomalyDetector:
    """
    Real-time AI telemetry anomaly detector.
    Maintains a rolling window of recent power samples to calculate dynamic baseline,
    standard deviation, rate of change (dP/dt), and anomaly severity score.
    """

    def __init__(self, window_size: int = 40, z_threshold: float = 2.2, gradient_threshold: float = 25.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.gradient_threshold = gradient_threshold
        self.history: collections.deque = collections.deque(maxlen=window_size)
        self.last_sample_time: Optional[float] = None
        self.last_power_w: Optional[float] = None

    def record_and_evaluate(self, power_w: float, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Record a power sample and evaluate real-time anomaly score.
        Returns detailed anomaly diagnostics, severity, and root-cause indicators.
        """
        now_ts = timestamp or datetime.now(timezone.utc)
        now_epoch = now_ts.timestamp()

        # Compute gradient (rate of change dP/dt)
        gradient = 0.0
        if self.last_power_w is not None and self.last_sample_time is not None:
            dt = max(0.2, now_epoch - self.last_sample_time)
            gradient = (power_w - self.last_power_w) / dt

        self.last_power_w = power_w
        self.last_sample_time = now_epoch

        # If history is still warming up (fewer than 5 samples)
        if len(self.history) < 5:
            self.history.append(power_w)
            return {
                "power_w": power_w,
                "anomaly_score": 0.05,
                "status": "NORMAL",
                "severity": "LOW",
                "z_score": 0.0,
                "rolling_mean_w": round(power_w, 2),
                "rolling_std_w": 0.0,
                "gradient_w_per_sec": round(gradient, 2),
                "is_anomaly": False,
                "diagnostic_message": "Baseline model warming up with streaming telemetry."
            }

        # Calculate rolling statistics
        samples_list = list(self.history)
        mean_w = sum(samples_list) / len(samples_list)
        variance = sum((x - mean_w) ** 2 for x in samples_list) / len(samples_list)
        std_w = math.sqrt(variance) if variance > 0.001 else 1.0

        # Z-score computation
        z_score = (power_w - mean_w) / std_w

        # Multi-factor anomaly score (0.0 to 1.0)
        # 1. Z-score component (sigmoid mapped)
        z_factor = 1.0 / (1.0 + math.exp(-1.2 * (abs(z_score) - self.z_threshold)))
        
        # 2. Gradient spurt component
        grad_factor = min(1.0, max(0.0, abs(gradient) / (self.gradient_threshold * 1.5)))

        # 3. Sustained high-load component
        sustained_factor = 1.0 if (power_w > mean_w * 1.8 and power_w > 90.0) else 0.0

        # Weighted aggregate anomaly score
        anomaly_score = min(1.0, max(0.0, (z_factor * 0.55) + (grad_factor * 0.30) + (sustained_factor * 0.15)))

        # Classification
        if anomaly_score >= 0.72 or z_score >= 3.0:
            status = "CRITICAL_RUNAWAY"
            severity = "HIGH"
            is_anomaly = True
            diagnostic = f"CRITICAL ANOMALY: Power draw spiked to {power_w:.1f} W ({z_score:+.1f}σ above {mean_w:.1f} W baseline). High probability of runaway CPU loop or crypto-mining."
        elif anomaly_score >= 0.40 or z_score >= 2.0 or abs(gradient) >= self.gradient_threshold:
            status = "SUSPICIOUS_SPURT"
            severity = "MEDIUM"
            is_anomaly = True
            diagnostic = f"SUSPICIOUS ACTIVITY: Sudden power surge detected ({gradient:+.1f} W/s). Inspecting for memory thrashing or burst traffic."
        else:
            status = "NORMAL"
            severity = "LOW"
            is_anomaly = False
            diagnostic = "Telemetry within normal operating envelope."

        # Append to sliding history
        self.history.append(power_w)

        return {
            "power_w": round(power_w, 2),
            "anomaly_score": round(anomaly_score, 3),
            "status": status,
            "severity": severity,
            "z_score": round(z_score, 2),
            "rolling_mean_w": round(mean_w, 2),
            "rolling_std_w": round(std_w, 2),
            "gradient_w_per_sec": round(gradient, 2),
            "is_anomaly": is_anomaly,
            "diagnostic_message": diagnostic,
            "evaluated_at": now_ts.isoformat()
        }

    def analyze_batch(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Annotate a series of power readings with anomaly scores."""
        results = []
        for s in samples:
            w = float(s.get("power_w", 0.0))
            ts = datetime.fromisoformat(s["timestamp"]) if "timestamp" in s else None
            eval_res = self.record_and_evaluate(w, ts)
            results.append({**s, "anomaly": eval_res})
        return results


# Global singleton instance tracking live stream
ai_anomaly_engine = AiPowerAnomalyDetector()
