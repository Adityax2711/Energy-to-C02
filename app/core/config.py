"""
Core Application Configuration
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Energy-to-CO2 Translation Engine"
    VERSION: str = "1.0.0"
    MODEL_VERSION: str = "v1.0.0-trapezoidal-traceable"
    
    # Database
    DATABASE_URL: str = (
        "sqlite:////tmp/energy_to_co2.db"
        if (os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
        else "sqlite:///./energy_to_co2.db"
    )
    
    # Telemetry and Integration Policies
    DEFAULT_HOST: str = "node-alpha-01"
    DEFAULT_REGION: str = "US-EAST"
    DEFAULT_PUE: float = 1.20  # Power Usage Effectiveness datacenter overhead
    MAX_GAP_SECONDS: float = 15.0  # Gaps > 15 seconds trigger GAP_DETECTED quality
    MIN_INTERVAL_SECONDS: float = 0.05  # Prevent absurdly small intervals causing division anomalies
    
    # Background Telemetry Collection
    ENABLE_BACKGROUND_COLLECTOR: bool = not bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
    BACKGROUND_SAMPLE_INTERVAL_SECONDS: float = 2.0
    SIMULATED_POWER_ENABLED: bool = False  # If false and psutil is present, reads psutil; else simulation
    
    # Carbon Calculation Settings
    CARBON_CACHE_SECONDS: int = 60
    
    # Security & Protection Settings
    SECURITY_ENABLED: bool = False  # Set True to enforce X-API-Key validation on protected endpoints
    API_KEY: str = "secret-telemetry-key-2026"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 180
    
    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
