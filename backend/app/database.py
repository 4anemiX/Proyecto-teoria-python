"""
database.py — Motor SQLAlchemy, sesión inyectable con Depends() y seed inicial
"""
from __future__ import annotations
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from .config import settings
from .models.db_models import Base, Asset

# ── Motor ─────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},   # necesario para SQLite
    echo=False,
)

# Activar WAL mode para mejor concurrencia con SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# ── Sesión ────────────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Generador de sesión inyectable vía Depends()."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Inicialización ────────────────────────────────────────────────────────────
PORTFOLIO_SEED = [
    {"ticker": "ACN",  "name": "Accenture",       "sector": "Consultoría Tecnológica"},
    {"ticker": "MSFT", "name": "Microsoft",        "sector": "Cloud / IA"},
    {"ticker": "NVDA", "name": "NVIDIA",           "sector": "Semiconductores / IA"},
    {"ticker": "KO",   "name": "Coca-Cola",        "sector": "Consumo Defensivo"},
    {"ticker": "JPM",  "name": "JPMorgan Chase",   "sector": "Finanzas Digitales"},
    {"ticker": "SPY",  "name": "S&P 500 ETF",      "sector": "Benchmark"},
]


def init_db() -> None:
    """Crea tablas y hace seed de activos si no existen."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for item in PORTFOLIO_SEED:
            exists = db.query(Asset).filter(Asset.ticker == item["ticker"]).first()
            if not exists:
                db.add(Asset(**item))
        db.commit()
    finally:
        db.close()