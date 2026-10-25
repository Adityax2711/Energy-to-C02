"""
Pytest Fixtures and In-Memory Database Configuration for Testing
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Disable background sampler during test suite
from app.core.config import settings
settings.ENABLE_BACKGROUND_COLLECTOR = False

import app.models.database_models  # Ensure all SQLAlchemy models are registered
from app.core.database import Base, get_db
from app.main import app
from app.services.emissions_calculator import EmissionsCalculator

# Use StaticPool so all in-memory connections share the exact same SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database with all tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    EmissionsCalculator.seed_default_factors_if_needed(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient overriding the get_db dependency with in-memory session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
