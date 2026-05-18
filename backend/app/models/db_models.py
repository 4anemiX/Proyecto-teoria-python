"""
db_models.py — Modelos ORM SQLAlchemy para persistencia en SQLite
Tablas: Asset, Price, Portfolio, PredictionLog, SignalLog, MacroCache
"""
from __future__ import annotations
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, JSON, Boolean, Text
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Asset(Base):
    """Activos del portafolio."""
    __tablename__ = "assets"

    id     = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name   = Column(String(120))
    sector = Column(String(60))

    prices  = relationship("Price",     back_populates="asset", cascade="all, delete-orphan")
    signals = relationship("SignalLog", back_populates="asset", cascade="all, delete-orphan")


class Price(Base):
    """Precios OHLCV diarios — cache transparente de yfinance."""
    __tablename__ = "prices"

    id       = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    date     = Column(Date, nullable=False, index=True)
    open     = Column(Float)
    high     = Column(Float)
    low      = Column(Float)
    close    = Column(Float)
    volume   = Column(Float)

    asset = relationship("Asset", back_populates="prices")


class Portfolio(Base):
    """Portafolios guardados por el usuario."""
    __tablename__ = "portfolios"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(120), nullable=False)
    tickers    = Column(JSON)        # list[str]
    weights    = Column(JSON)        # dict ticker -> float
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes      = Column(Text, nullable=True)


class PredictionLog(Base):
    """Log de predicciones del modelo ML para monitoreo."""
    __tablename__ = "predictions_log"

    id             = Column(Integer, primary_key=True, index=True)
    model_version  = Column(String(40), nullable=False)
    timestamp      = Column(DateTime, default=datetime.utcnow, index=True)
    ticker         = Column(String(10), index=True)
    input_features = Column(JSON)
    prediction     = Column(Float)
    prediction_label = Column(String(20), nullable=True)   # para clasificación
    actual         = Column(Float, nullable=True)
    confidence     = Column(Float, nullable=True)


class SignalLog(Base):
    """Log de señales técnicas disparadas — persistencia obligatoria del Mód. 7."""
    __tablename__ = "signals_log"

    id        = Column(Integer, primary_key=True, index=True)
    asset_id  = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    rule      = Column(String(60))      # ej: "rsi_overbought"
    value     = Column(Float)           # valor del indicador al disparar
    signal    = Column(String(20))      # "Compra" | "Venta" | "Neutral"

    asset = relationship("Asset", back_populates="signals")


class MacroCache(Base):
    """Cache de datos macroeconómicos con TTL de 24h."""
    __tablename__ = "macro_cache"

    id         = Column(Integer, primary_key=True, index=True)
    series_id  = Column(String(30), unique=True, nullable=False, index=True)  # ej: "DGS10"
    value      = Column(Float)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    source     = Column(String(30), default="FRED")