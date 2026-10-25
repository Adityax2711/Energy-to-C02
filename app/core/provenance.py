"""
Provenance, Audit, and Cryptographic Hash Utilities
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict


def compute_payload_hash(data: Dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of a payload dictionary."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def generate_provenance_record(
    interval_id: int,
    host: str,
    energy_kwh: float,
    factor_id: int,
    region: str,
    factor_gco2e_kwh: float,
    factor_source: str,
    factor_valid_at: datetime,
    pue: float,
    grams_co2e: float,
    model_version: str
) -> Dict[str, Any]:
    """
    Construct a verifiable calculation provenance chain.
    """
    calculation_math = f"{energy_kwh:.8f} kWh * {pue:.2f} PUE * {factor_gco2e_kwh:.2f} gCO2e/kWh = {grams_co2e:.6f} gCO2e"
    payload = {
        "interval_id": interval_id,
        "host": host,
        "energy_kwh": energy_kwh,
        "factor_id": factor_id,
        "region": region,
        "factor_gco2e_kwh": factor_gco2e_kwh,
        "factor_source": factor_source,
        "factor_valid_at": factor_valid_at.isoformat() if hasattr(factor_valid_at, "isoformat") else str(factor_valid_at),
        "pue": pue,
        "grams_co2e": grams_co2e,
        "model_version": model_version,
        "calculation_formula": calculation_math
    }
    payload["provenance_hash"] = compute_payload_hash(payload)
    return payload
