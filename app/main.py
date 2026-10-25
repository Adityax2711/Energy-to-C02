"""
Energy-to-CO2 Translation Engine
Main FastAPI Application Entrypoint
"""
import time
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.routes import router as api_router
from app.services.emissions_calculator import EmissionsCalculator
from app.services.sensor_adapter import HostPsutilSensor, SyntheticSimulatorSensor
from app.services.telemetry_collector import TelemetryCollectorService
from app.models.schemas import PowerSampleCreate
from app.models.database_models import EmissionFactor
from app.api.metrics import GAUGE_CARBON_INTENSITY


# Background Telemetry Worker
_bg_stop_event = threading.Event()
_bg_thread = None


def background_sampler_loop():
    """
    Background worker periodically sampling telemetry from the selected sensor
    (Host psutil or Synthetic Simulator) to ensure live continuous time series.
    """
    psutil_sensor = HostPsutilSensor()
    synthetic_sensor = SyntheticSimulatorSensor(mode="diurnal")

    while not _bg_stop_event.is_set():
        db = SessionLocal()
        try:
            if settings.SIMULATED_POWER_ENABLED:
                reading = synthetic_sensor.read_watts()
            else:
                try:
                    reading = psutil_sensor.read_watts()
                except Exception:
                    reading = synthetic_sensor.read_watts()

            sample = PowerSampleCreate(
                host=settings.DEFAULT_HOST,
                timestamp=datetime.now(timezone.utc),
                power_w=reading["power_w"],
                source=reading["source"],
                quality=reading["quality"]
            )

            TelemetryCollectorService.ingest_sample(
                db=db,
                sample_in=sample,
                region=settings.DEFAULT_REGION
            )
        except Exception as e:
            db.rollback()
        finally:
            db.close()

        time.sleep(settings.BACKGROUND_SAMPLE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    global _bg_thread

    # 1. Initialize DB Schema
    Base.metadata.create_all(bind=engine)

    # 2. Seed default factors
    db = SessionLocal()
    EmissionsCalculator.seed_default_factors_if_needed(db)
    # Set default metrics gauges
    for f in db.query(EmissionFactor).all():
        GAUGE_CARBON_INTENSITY.labels(region=f.region, source=f.source).set(f.gco2e_kwh)
    db.close()

    # 3. Start background telemetry collection if enabled
    if settings.ENABLE_BACKGROUND_COLLECTOR:
        _bg_stop_event.clear()
        _bg_thread = threading.Thread(target=background_sampler_loop, daemon=True)
        _bg_thread.start()

    yield

    # Shutdown
    _bg_stop_event.set()
    if _bg_thread and _bg_thread.is_alive():
        _bg_thread.join(timeout=3.0)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Translates host & hardware power telemetry into unit-safe energy intervals and traceable location-specific greenhouse gas estimates.",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes at root level (e.g. /telemetry, /energy/summary, /metrics)
app.include_router(api_router)
# Also include routes under /api prefix for API consumers
app.include_router(api_router, prefix="/api")

# Static files for the web dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the single-page web dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Energy-to-CO2 Translation Engine API is running. Visit /docs for OpenAPI specifications."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
