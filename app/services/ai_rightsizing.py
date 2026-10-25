"""
AI Hardware Right-Sizing & Architecture Advisor
Analyzes workload utilization patterns against micro-architectural TDP envelopes
to identify over-provisioned compute and recommend green, cost-effective architectures.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math

from app.services.aws_service import AWS_EC2_CATALOG, AWS_REGION_GRID_MAP, AwsEc2CarbonService
from app.core.provenance import compute_payload_hash


class AiHardwareRightSizer:
    """
    Evaluates observed instance telemetry against hardware envelopes
    and recommends optimal green compute right-sizing.
    """

    @classmethod
    def analyze_workload(
        cls,
        current_instance_type: str,
        instance_count: int = 1,
        observed_avg_cpu_percent: float = 25.0,
        observed_peak_cpu_percent: float = 40.0,
        source_region: str = "us-east-1",
        hours_per_month: float = 730.0
    ) -> Dict[str, Any]:
        """
        Produce AI right-sizing recommendations based on observed utilization.
        """
        current_inst = AWS_EC2_CATALOG.get(current_instance_type)
        if not current_inst:
            raise ValueError(f"Unknown instance type: '{current_instance_type}'")

        src_reg = AWS_REGION_GRID_MAP.get(source_region.lower())
        if not src_reg:
            raise ValueError(f"Unknown source region: '{source_region}'")

        # Compute current baseline
        current_power = AwsEc2CarbonService.calculate_instance_power(
            current_instance_type, observed_avg_cpu_percent
        )
        total_curr_watts = current_power["power_watts"] * instance_count
        curr_monthly_kwh = (total_curr_watts * hours_per_month * src_reg["default_pue"]) / 1000.0
        curr_monthly_kgco2e = (curr_monthly_kwh * src_reg["factor_gco2e_kwh"]) / 1000.0

        # Assess over-provisioning severity
        is_heavily_overprovisioned = observed_avg_cpu_percent < 30.0 and observed_peak_cpu_percent < 55.0
        headroom_wasted_pct = round(max(0.0, 100.0 - (observed_avg_cpu_percent * 2.2)), 1)

        # AI Recommendation Selection:
        # If compute-optimized x86 (e.g. c6i), recommend ARM Graviton3 (c7g) or right-sized Graviton2 (t4g)
        if "c6i" in current_instance_type or "m6a" in current_instance_type:
            target_instance_type = "c7g.4xlarge" if current_inst["vcpu"] >= 16 else "t4g.xlarge"
            new_estimated_cpu_pct = min(88.0, observed_avg_cpu_percent * 1.35)
            reason = "Workload exhibits low CPU saturation. Modern AWS Graviton3 (ARM Neoverse V1) offers DDR5 memory bandwidth with ~50% lower TDP."
        elif "g5" in current_instance_type:
            target_instance_type = "c7g.4xlarge" if observed_peak_cpu_percent < 25.0 else "t4g.xlarge"
            new_estimated_cpu_pct = 65.0
            reason = "GPU Tensor Cores are severely under-utilized. Moving inference to optimized CPU instruction sets eliminates 200W+ idle GPU tax."
        elif "p4de" in current_instance_type:
            target_instance_type = "g5.2xlarge"
            new_estimated_cpu_pct = 75.0
            reason = "Hyperscale 8x A100 training cluster is running batch inference at low efficiency. Migrating to single A10G cuts 3000W+ overhead."
        else:
            target_instance_type = "t4g.xlarge"
            new_estimated_cpu_pct = min(85.0, observed_avg_cpu_percent * 1.5)
            reason = "Workload is suitable for high-efficiency burstable ARM instances with automated sleep intervals."

        target_inst = AWS_EC2_CATALOG.get(target_instance_type, AWS_EC2_CATALOG["c7g.4xlarge"])

        # Calculate target power & carbon in same region
        target_power = AwsEc2CarbonService.calculate_instance_power(
            target_instance_type, new_estimated_cpu_pct
        )
        total_target_watts = target_power["power_watts"] * instance_count
        target_monthly_kwh = (total_target_watts * hours_per_month * src_reg["default_pue"]) / 1000.0
        target_monthly_kgco2e = (target_monthly_kwh * src_reg["factor_gco2e_kwh"]) / 1000.0

        # Calculate savings
        saved_kgco2e = curr_monthly_kgco2e - target_monthly_kgco2e
        percent_saved = ((curr_monthly_kgco2e - target_monthly_kgco2e) / max(0.001, curr_monthly_kgco2e)) * 100.0

        # Also calculate Combined: Right-Size + Move to Greenest Region (Stockholm eu-north-1)
        green_reg = AWS_REGION_GRID_MAP["eu-north-1"]
        combo_monthly_kwh = (total_target_watts * hours_per_month * green_reg["default_pue"]) / 1000.0
        combo_monthly_kgco2e = (combo_monthly_kwh * green_reg["factor_gco2e_kwh"]) / 1000.0
        combo_saved_kgco2e = curr_monthly_kgco2e - combo_monthly_kgco2e
        combo_percent_saved = ((curr_monthly_kgco2e - combo_monthly_kgco2e) / max(0.001, curr_monthly_kgco2e)) * 100.0

        provenance_dict = {
            "current_instance": current_instance_type,
            "recommended_instance": target_instance_type,
            "instance_count": instance_count,
            "avg_cpu_util": observed_avg_cpu_percent,
            "peak_cpu_util": observed_peak_cpu_percent,
            "curr_kgco2e": round(curr_monthly_kgco2e, 3),
            "target_kgco2e": round(target_monthly_kgco2e, 3),
            "saved_kgco2e": round(saved_kgco2e, 3),
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
        provenance_hash = compute_payload_hash(provenance_dict)

        return {
            "workload_profile": {
                "current_instance_type": current_instance_type,
                "current_arch": current_inst["arch"],
                "current_max_tdp_w": current_inst["max_tdp_w"],
                "instance_count": instance_count,
                "observed_avg_cpu_percent": observed_avg_cpu_percent,
                "observed_peak_cpu_percent": observed_peak_cpu_percent,
                "is_overprovisioned": is_heavily_overprovisioned,
                "wasted_headroom_percent": headroom_wasted_pct,
                "current_fleet_power_w": round(total_curr_watts, 1),
                "current_monthly_kg_co2e": round(curr_monthly_kgco2e, 2)
            },
            "recommendation": {
                "target_instance_type": target_instance_type,
                "target_family": target_inst["family"],
                "target_arch": target_inst["arch"],
                "target_max_tdp_w": target_inst["max_tdp_w"],
                "estimated_target_cpu_percent": round(new_estimated_cpu_pct, 1),
                "recommended_fleet_power_w": round(total_target_watts, 1),
                "recommended_monthly_kg_co2e": round(target_monthly_kgco2e, 2),
                "reasoning": reason
            },
            "same_region_savings": {
                "power_reduction_watts": round(total_curr_watts - total_target_watts, 1),
                "monthly_kwh_saved": round(curr_monthly_kwh - target_monthly_kwh, 1),
                "monthly_kg_co2e_saved": round(saved_kgco2e, 2),
                "annual_metric_tons_co2e_saved": round((saved_kgco2e * 12.0) / 1000.0, 3),
                "percent_carbon_reduction": round(percent_saved, 1),
                "trees_planted_equivalent_months": round(max(0.0, saved_kgco2e) / 1.81, 1),
                "car_miles_avoided": round(max(0.0, saved_kgco2e) * 2.5, 1)
            },
            "combined_with_green_region": {
                "target_region": "eu-north-1 (Stockholm Clean Hydro)",
                "combined_monthly_kg_co2e": round(combo_monthly_kgco2e, 2),
                "combined_monthly_kg_co2e_saved": round(combo_saved_kgco2e, 2),
                "combined_percent_reduction": round(combo_percent_saved, 1),
                "combined_annual_metric_tons_saved": round((combo_saved_kgco2e * 12.0) / 1000.0, 3)
            },
            "provenance_hash": provenance_hash
        }
