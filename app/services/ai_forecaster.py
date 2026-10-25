"""
P1: Predictive Time-Series Forecaster & Green Computing Window Optimizer
Uses chronological train/validation splits, Fourier diurnal harmonic decomposition,
and Ridge regression to forecast future power (W) and carbon emission rates (gCO2e/hr)
with 95% confidence intervals and automated green window detection.
"""
from datetime import datetime, timezone, timedelta
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database_models import PowerSample
from app.services.emissions_calculator import EmissionsCalculator
from app.core.config import settings
from app.core.provenance import compute_payload_hash


class AiTimeSeriesForecaster:
    """
    Predictive Power and Carbon Emission Forecaster.
    Employs Fourier harmonic regression to model both autoregressive trend and 24-hour diurnal seasonality.
    """

    @classmethod
    def _extract_features(cls, timestamps: List[datetime], powers: List[float]) -> np.ndarray:
        """
        Extract multi-dimensional temporal and cyclical features:
        - Diurnal sine/cosine harmonic cycles (24h primary and 12h overtone)
        - Polynomial trend
        - Autoregressive short-term moving average
        """
        features = []
        for i, (ts, p) in enumerate(zip(timestamps, powers)):
            hour_frac = ts.hour + (ts.minute / 60.0) + (ts.second / 3600.0)
            
            # 24-hour primary diurnal harmonic
            sin_24 = math.sin(2.0 * math.pi * hour_frac / 24.0)
            cos_24 = math.cos(2.0 * math.pi * hour_frac / 24.0)
            
            # 12-hour secondary semi-diurnal harmonic
            sin_12 = math.sin(4.0 * math.pi * hour_frac / 24.0)
            cos_12 = math.cos(4.0 * math.pi * hour_frac / 24.0)
            
            # Autoregressive lag (previous power if available)
            prev_p = powers[i - 1] if i > 0 else p
            delta_p = p - prev_p

            features.append([
                hour_frac / 24.0,   # Normalized hour [0, 1]
                sin_24, cos_24,
                sin_12, cos_12,
                prev_p, delta_p
            ])
            
        return np.array(features, dtype=np.float64)

    @classmethod
    def generate_forecast(
        cls,
        db: Session,
        region: str = "US-EAST",
        horizon_hours: int = 24,
        pue: float = 1.20,
        host: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train regression forecaster on chronological telemetry and project forward.
        Returns prediction series with 95% confidence intervals, MAE, RMSE, and green window.
        """
        # 1. Fetch chronological historical power samples
        query = db.query(PowerSample)
        if host:
            query = query.filter(PowerSample.host == host)
        
        samples = (
            query.order_by(desc(PowerSample.timestamp))
            .limit(120)
            .all()
        )
        samples.reverse()

        now = datetime.now(timezone.utc)

        # If sparse history, synthesize warm-up diurnal pattern to seed the model
        if len(samples) < 15:
            timestamps = [now - timedelta(minutes=2 * (15 - i)) for i in range(15)]
            powers = [50.0 + 35.0 * math.sin((t.hour + t.minute / 60.0) * math.pi / 12.0) for t in timestamps]
        else:
            timestamps = [s.timestamp for s in samples]
            powers = [s.power_w for s in samples]

        # 2. Chronological Train / Validation Split (80% train, 20% validation)
        split_idx = max(8, int(len(powers) * 0.8))
        train_ts, val_ts = timestamps[:split_idx], timestamps[split_idx:]
        train_p, val_p = powers[:split_idx], powers[split_idx:]

        X_train = cls._extract_features(train_ts, train_p)
        y_train = np.array(train_p, dtype=np.float64)

        X_val = cls._extract_features(val_ts, val_p)
        y_val = np.array(val_p, dtype=np.float64)

        # 3. Fit Ridge Regression Model
        model = Ridge(alpha=1.5)
        model.fit(X_train, y_train)

        # 4. Out-of-sample Validation Evaluation
        y_val_pred = model.predict(X_val)
        mae = float(mean_absolute_error(y_val, y_val_pred))
        rmse = float(root_mean_squared_error(y_val, y_val_pred))
        
        # Calculate residual standard error for 95% confidence interval
        residuals = y_val - y_val_pred
        residual_std = float(np.std(residuals)) if len(residuals) > 1 else 4.5
        residual_std = max(2.5, residual_std)  # Reasonable lower bound

        # 5. Generate Forward Predictions
        factor = EmissionsCalculator.get_factor_for_region(db, region)
        factor_intensity = factor.gco2e_kwh

        predictions = []
        step_minutes = 60 if horizon_hours > 6 else 15
        num_steps = int((horizon_hours * 60) / step_minutes)

        last_known_p = powers[-1]
        sim_p = last_known_p

        for step in range(1, num_steps + 1):
            future_ts = now + timedelta(minutes=step * step_minutes)
            hour_frac = future_ts.hour + (future_ts.minute / 60.0)
            
            sin_24 = math.sin(2.0 * math.pi * hour_frac / 24.0)
            cos_24 = math.cos(2.0 * math.pi * hour_frac / 24.0)
            sin_12 = math.sin(4.0 * math.pi * hour_frac / 24.0)
            cos_12 = math.cos(4.0 * math.pi * hour_frac / 24.0)

            feat = np.array([[
                hour_frac / 24.0,
                sin_24, cos_24,
                sin_12, cos_12,
                sim_p, 0.0
            ]], dtype=np.float64)

            pred_w = float(model.predict(feat)[0])
            pred_w = max(15.0, pred_w)  # Physical hardware floor
            sim_p = pred_w

            # 95% Confidence bounds (+/- 1.96 * sigma)
            # Uncertainty expands slightly with prediction horizon
            horizon_expansion = 1.0 + (0.02 * (step / num_steps))
            ci_margin = 1.96 * residual_std * horizon_expansion
            lower_ci = max(10.0, pred_w - ci_margin)
            upper_ci = pred_w + ci_margin

            # Carbon rate: gCO2e per hour = (Power kW) * PUE * Grid Factor
            carbon_rate_ghr = (pred_w / 1000.0) * pue * factor_intensity

            predictions.append({
                "timestamp": future_ts.isoformat(),
                "hour_label": future_ts.strftime("%H:%M"),
                "predicted_power_w": round(pred_w, 2),
                "lower_ci_95": round(lower_ci, 2),
                "upper_ci_95": round(upper_ci, 2),
                "predicted_carbon_rate_g_per_hr": round(carbon_rate_ghr, 3),
                "grid_intensity_factor": factor_intensity
            })

        # 6. Optimal Green Computing Window Detection
        # Find 3-hour consecutive window with minimum carbon intensity
        window_size = min(3, max(1, len(predictions) // 4))
        best_avg_carbon = float("inf")
        worst_avg_carbon = float("-inf")
        best_window_idx = 0

        for i in range(len(predictions) - window_size + 1):
            window_slice = predictions[i:i + window_size]
            avg_carb = sum(p["predicted_carbon_rate_g_per_hr"] for p in window_slice) / window_size
            if avg_carb < best_avg_carbon:
                best_avg_carbon = avg_carb
                best_window_idx = i
            if avg_carb > worst_avg_carbon:
                worst_avg_carbon = avg_carb

        best_window = predictions[best_window_idx:best_window_idx + window_size]
        start_win_ts = best_window[0]["timestamp"]
        end_win_ts = best_window[-1]["timestamp"]
        savings_pct = max(0.0, ((worst_avg_carbon - best_avg_carbon) / max(0.01, worst_avg_carbon)) * 100.0)

        green_window_info = {
            "start_time": start_win_ts,
            "end_time": end_win_ts,
            "duration_hours": window_size,
            "optimal_power_w": round(sum(p["predicted_power_w"] for p in best_window) / window_size, 1),
            "optimal_carbon_rate_ghr": round(best_avg_carbon, 2),
            "carbon_reduction_percent": round(savings_pct, 1),
            "recommendation": f"Schedule heavy batch, ML training, or CI/CD pipelines between {best_window[0]['hour_label']} and {best_window[-1]['hour_label']} to reduce greenhouse emissions by ~{savings_pct:.1f}%."
        }

        # Build Provenance Record
        provenance = {
            "model_type": "Fourier_Harmonic_Ridge_v1",
            "validation_mae_watts": round(mae, 3),
            "validation_rmse_watts": round(rmse, 3),
            "region": region,
            "pue": pue,
            "horizon_hours": horizon_hours
        }
        provenance["provenance_hash"] = compute_payload_hash(provenance)

        return {
            "status": "success",
            "region": region,
            "horizon_hours": horizon_hours,
            "model_metrics": {
                "mae_watts": round(mae, 2),
                "rmse_watts": round(rmse, 2),
                "training_samples": len(train_p),
                "validation_samples": len(val_p)
            },
            "green_window": green_window_info,
            "predictions": predictions,
            "provenance": provenance
        }
