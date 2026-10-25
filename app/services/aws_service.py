"""
AWS EC2 Carbon & Energy Modeling Service
Provides micro-architectural TDP power modeling for AWS EC2 instance families,
regional grid carbon factor mapping, and spatial workload optimization (green shifting).
"""
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import hashlib
import json

from app.core.provenance import compute_payload_hash


AWS_EC2_CATALOG: Dict[str, Dict[str, Any]] = {
    "t3.medium": {
        "instance_type": "t3.medium",
        "family": "General Purpose (x86)",
        "vcpu": 2,
        "ram_gb": 4.0,
        "arch": "Intel Xeon Platinum 8000 (Skylake/Cascade Lake)",
        "idle_w": 7.5,
        "max_tdp_w": 35.0,
        "gpu": None,
        "description": "Burstable general purpose for microservices & lightweight APIs"
    },
    "t4g.xlarge": {
        "instance_type": "t4g.xlarge",
        "family": "General Purpose (ARM)",
        "vcpu": 4,
        "ram_gb": 16.0,
        "arch": "AWS Graviton2 (64-bit ARM Neoverse N1)",
        "idle_w": 6.0,
        "max_tdp_w": 32.0,
        "gpu": None,
        "description": "High-efficiency ARM microarchitecture for modern microservices"
    },
    "c6i.4xlarge": {
        "instance_type": "c6i.4xlarge",
        "family": "Compute Optimized (x86)",
        "vcpu": 16,
        "ram_gb": 32.0,
        "arch": "Intel Xeon Scalable 3rd Gen (Ice Lake)",
        "idle_w": 45.0,
        "max_tdp_w": 220.0,
        "gpu": None,
        "description": "High-throughput CPU batch processing, media transcoding & analytics"
    },
    "c7g.4xlarge": {
        "instance_type": "c7g.4xlarge",
        "family": "Compute Optimized (ARM)",
        "vcpu": 16,
        "ram_gb": 32.0,
        "arch": "AWS Graviton3 (Neoverse V1, DDR5)",
        "idle_w": 24.0,
        "max_tdp_w": 115.0,
        "gpu": None,
        "description": "Next-gen ultra-low carbon compute; ~50% energy reduction vs x86"
    },
    "m6a.4xlarge": {
        "instance_type": "m6a.4xlarge",
        "family": "Memory Optimized (AMD)",
        "vcpu": 16,
        "ram_gb": 64.0,
        "arch": "AMD EPYC 3rd Gen (Milan 7R13)",
        "idle_w": 48.0,
        "max_tdp_w": 240.0,
        "gpu": None,
        "description": "Memory-intensive databases, caching clusters & enterprise backends"
    },
    "g5.2xlarge": {
        "instance_type": "g5.2xlarge",
        "family": "Accelerated GPU Compute",
        "vcpu": 8,
        "ram_gb": 32.0,
        "arch": "AMD EPYC + NVIDIA A10G Tensor Core (24GB VRAM)",
        "idle_w": 65.0,
        "max_tdp_w": 310.0,
        "gpu": "1x NVIDIA A10G (150W TDP)",
        "description": "Deep learning inference, computer vision & cloud rendering"
    },
    "p4de.24xlarge": {
        "instance_type": "p4de.24xlarge",
        "family": "Hyperscale AI / LLM Training",
        "vcpu": 96,
        "ram_gb": 1152.0,
        "arch": "Intel Xeon Platinum 8252C + 8x NVIDIA A100 80GB SXM4",
        "idle_w": 650.0,
        "max_tdp_w": 3300.0,
        "gpu": "8x NVIDIA A100 80GB SXM4 (3200W total GPU TDP)",
        "description": "Distributed LLM training cluster (GPT/Llama fine-tuning)"
    }
}


AWS_REGION_GRID_MAP: Dict[str, Dict[str, Any]] = {
    "us-east-1": {
        "region_code": "us-east-1",
        "region_name": "US East (N. Virginia)",
        "grid_name": "PJM Interconnection",
        "factor_gco2e_kwh": 380.5,
        "factor_source": "EPA eGRID 2024 / PJM Interconnection",
        "clean_energy_pct": 22.0,
        "default_pue": 1.15
    },
    "us-west-2": {
        "region_code": "us-west-2",
        "region_name": "US West (Oregon)",
        "grid_name": "Northwest Power Pool (Hydroelectric)",
        "factor_gco2e_kwh": 180.0,
        "factor_source": "EPA eGRID 2024 / NWPP",
        "clean_energy_pct": 68.0,
        "default_pue": 1.12
    },
    "eu-north-1": {
        "region_code": "eu-north-1",
        "region_name": "Europe (Stockholm)",
        "grid_name": "Nordic Clean Grid (Hydro + Wind + Nuclear)",
        "factor_gco2e_kwh": 45.0,
        "factor_source": "European Environment Agency (EEA) / Svenska Kraftnät",
        "clean_energy_pct": 95.0,
        "default_pue": 1.10
    },
    "eu-central-1": {
        "region_code": "eu-central-1",
        "region_name": "Europe (Frankfurt)",
        "grid_name": "Continental European Grid (ENTSO-E)",
        "factor_gco2e_kwh": 315.0,
        "factor_source": "European Environment Agency (EEA) 2024",
        "clean_energy_pct": 54.0,
        "default_pue": 1.14
    },
    "ap-south-1": {
        "region_code": "ap-south-1",
        "region_name": "Asia Pacific (Mumbai)",
        "grid_name": "India National Grid / Central Electricity Authority",
        "factor_gco2e_kwh": 630.0,
        "factor_source": "India Central Electricity Authority (CEA) Baseline Database",
        "clean_energy_pct": 18.0,
        "default_pue": 1.25
    },
    "ap-southeast-2": {
        "region_code": "ap-southeast-2",
        "region_name": "Asia Pacific (Sydney)",
        "grid_name": "Australia National Electricity Market (NEM)",
        "factor_gco2e_kwh": 550.0,
        "factor_source": "Australian Energy Market Operator (AEMO) 2024",
        "clean_energy_pct": 31.0,
        "default_pue": 1.18
    }
}


class AwsEc2CarbonService:
    """
    Core engine for AWS EC2 instance power estimation and regional carbon optimization.
    """

    @classmethod
    def list_instances(cls) -> List[Dict[str, Any]]:
        """Return all supported EC2 instance types and hardware specs."""
        return list(AWS_EC2_CATALOG.values())

    @classmethod
    def list_regions(cls) -> List[Dict[str, Any]]:
        """Return all supported AWS regions with carbon grid intensities."""
        return list(AWS_REGION_GRID_MAP.values())

    @classmethod
    def calculate_instance_power(cls, instance_type: str, cpu_utilization_pct: float) -> Dict[str, Any]:
        """
        Estimate instantaneous power draw for an EC2 instance given CPU utilization.
        Formula uses non-linear microarchitectural dynamic load scaling.
        """
        instance = AWS_EC2_CATALOG.get(instance_type)
        if not instance:
            raise ValueError(f"Unknown AWS EC2 instance type: '{instance_type}'")

        cpu_clamped = max(0.0, min(100.0, cpu_utilization_pct))
        idle_w = instance["idle_w"]
        max_tdp = instance["max_tdp_w"]

        # Empirical non-linear scaling curve: dynamic load = (max_tdp - idle) * (util/100)^1.15
        dynamic_w = (max_tdp - idle_w) * ((cpu_clamped / 100.0) ** 1.15)
        total_w = idle_w + dynamic_w

        return {
            "instance_type": instance_type,
            "family": instance["family"],
            "vcpu": instance["vcpu"],
            "ram_gb": instance["ram_gb"],
            "arch": instance["arch"],
            "gpu": instance["gpu"],
            "cpu_utilization_percent": round(cpu_clamped, 1),
            "power_watts": round(total_w, 2),
            "idle_baseline_w": idle_w,
            "peak_tdp_w": max_tdp
        }

    @classmethod
    def optimize_workload(
        cls,
        instance_type: str,
        instance_count: int,
        cpu_utilization_percent: float,
        hours_per_month: float,
        source_region: str,
        target_region: Optional[str] = None,
        custom_pue: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate the carbon impact of running an EC2 workload in a source AWS region
        versus a target green region, providing actionable carbon savings recommendations.
        """
        # Validate instance
        inst_info = cls.calculate_instance_power(instance_type, cpu_utilization_percent)
        single_instance_w = inst_info["power_watts"]
        total_cluster_w = single_instance_w * max(1, instance_count)

        # Validate source region
        src_reg = AWS_REGION_GRID_MAP.get(source_region.lower())
        if not src_reg:
            raise ValueError(f"Unknown source AWS region: '{source_region}'. Supported: {list(AWS_REGION_GRID_MAP.keys())}")

        # Determine target region (default to greenest available region if not provided)
        if not target_region:
            target_region = "eu-north-1"  # Stockholm Nordic clean hydro
        tgt_reg = AWS_REGION_GRID_MAP.get(target_region.lower())
        if not tgt_reg:
            raise ValueError(f"Unknown target AWS region: '{target_region}'. Supported: {list(AWS_REGION_GRID_MAP.keys())}")

        # Find global greenest region
        greenest = min(AWS_REGION_GRID_MAP.values(), key=lambda r: r["factor_gco2e_kwh"])

        # PUE
        pue = custom_pue if custom_pue is not None else src_reg["default_pue"]

        # Energy consumption: kWh = (Watts * hours) / 1000
        cluster_kwh_raw = (total_cluster_w * hours_per_month) / 1000.0
        cluster_kwh_with_pue = cluster_kwh_raw * pue

        # Source emissions
        source_factor = src_reg["factor_gco2e_kwh"]
        source_gco2e = cluster_kwh_with_pue * source_factor
        source_kgco2e = source_gco2e / 1000.0

        # Target emissions
        target_factor = tgt_reg["factor_gco2e_kwh"]
        target_gco2e = cluster_kwh_with_pue * target_factor
        target_kgco2e = target_gco2e / 1000.0

        # Carbon Delta
        saved_kgco2e = source_kgco2e - target_kgco2e
        percent_saved = ((source_kgco2e - target_kgco2e) / max(0.0001, source_kgco2e)) * 100.0

        # Real-world equivalencies:
        # 1 mature urban tree absorbs ~21.77 kg CO2 / year (~1.81 kg CO2 / month)
        # 1 gallon of gasoline = ~8.887 kg CO2 -> 1 kg CO2 ≈ 2.5 miles passenger car
        # 1 smartphone charge ≈ 3.5 grams CO2e
        monthly_trees_equiv = round(abs(saved_kgco2e) / 1.81, 1)
        miles_driven_equiv = round(abs(saved_kgco2e) * 2.5, 1)
        smartphones_equiv = int(abs(saved_kgco2e * 1000.0) / 3.5)

        # Architectural Action / Recommendation
        if saved_kgco2e > 0.05:
            recommendation_text = (
                f"Shifting this workload from {src_reg['region_name']} to {tgt_reg['region_name']} "
                f"reduces Scope 2 greenhouse gas emissions by {abs(percent_saved):.1f}%, eliminating "
                f"{saved_kgco2e:.2f} kg CO2e per month. Recommended for batch, CI/CD, training, or asynchronous services."
            )
        elif saved_kgco2e < -0.05:
            recommendation_text = (
                f"Warning: {tgt_reg['region_name']} has higher carbon intensity ({target_factor} g/kWh) "
                f"than {src_reg['region_name']} ({source_factor} g/kWh). Keep this workload in {src_reg['region_name']}."
            )
        else:
            recommendation_text = "Emissions are equivalent between selected regions."

        # Cryptographic provenance payload
        provenance_dict = {
            "instance_type": instance_type,
            "instance_count": instance_count,
            "cpu_utilization_percent": cpu_utilization_percent,
            "hours_per_month": hours_per_month,
            "cluster_power_w": round(total_cluster_w, 2),
            "cluster_kwh_total": round(cluster_kwh_with_pue, 4),
            "source_region": src_reg["region_code"],
            "source_kgco2e": round(source_kgco2e, 4),
            "target_region": tgt_reg["region_code"],
            "target_kgco2e": round(target_kgco2e, 4),
            "saved_kgco2e": round(saved_kgco2e, 4),
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
        provenance_hash = compute_payload_hash(provenance_dict)

        return {
            "instance_profile": inst_info,
            "cluster_summary": {
                "instance_count": instance_count,
                "single_instance_watts": round(single_instance_w, 2),
                "total_cluster_watts": round(total_cluster_w, 2),
                "hours_per_month": hours_per_month,
                "monthly_energy_kwh": round(cluster_kwh_with_pue, 3),
                "pue_applied": pue
            },
            "source_region_analysis": {
                "region_code": src_reg["region_code"],
                "region_name": src_reg["region_name"],
                "grid_name": src_reg["grid_name"],
                "grid_factor_gco2e_kwh": source_factor,
                "clean_energy_percent": src_reg["clean_energy_pct"],
                "monthly_grams_co2e": round(source_gco2e, 2),
                "monthly_kg_co2e": round(source_kgco2e, 3)
            },
            "target_region_analysis": {
                "region_code": tgt_reg["region_code"],
                "region_name": tgt_reg["region_name"],
                "grid_name": tgt_reg["grid_name"],
                "grid_factor_gco2e_kwh": target_factor,
                "clean_energy_percent": tgt_reg["clean_energy_pct"],
                "monthly_grams_co2e": round(target_gco2e, 2),
                "monthly_kg_co2e": round(target_kgco2e, 3)
            },
            "optimization_delta": {
                "saved_kg_co2e_monthly": round(saved_kgco2e, 3),
                "saved_metric_tons_co2e_annual": round((saved_kgco2e * 12.0) / 1000.0, 4),
                "percent_reduction": round(percent_saved, 1),
                "is_beneficial": saved_kgco2e > 0
            },
            "real_world_equivalents": {
                "mature_trees_planted_offset_months": monthly_trees_equiv,
                "passenger_car_miles_avoided": miles_driven_equiv,
                "smartphone_charges_saved": smartphones_equiv
            },
            "global_greenest_region": {
                "region_code": greenest["region_code"],
                "region_name": greenest["region_name"],
                "factor_gco2e_kwh": greenest["factor_gco2e_kwh"],
                "potential_max_reduction_percent": round(((source_factor - greenest["factor_gco2e_kwh"]) / source_factor) * 100.0, 1)
            },
            "architectural_recommendation": recommendation_text,
            "provenance_hash": provenance_hash
        }
