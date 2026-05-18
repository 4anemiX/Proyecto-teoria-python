"""
conftest.py — Fixtures globales para pytest
Configura BD en memoria y variables de entorno para tests.
"""
import os
import pytest

# Usar SQLite en memoria para no contaminar la BD de desarrollo
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FRED_API_KEY", "test_key")
os.environ.setdefault("GROQ_API_KEY", "test_key")
os.environ.setdefault("ALPHA_VANTAGE_KEY", "test_key")


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Inicializa tablas en la BD de test antes de cualquier test."""
    from app.database import engine
    from app.models.db_models import Base
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
