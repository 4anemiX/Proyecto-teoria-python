"""
train.py — Entrenamiento offline del clasificador de régimen de mercado
Modelo: RandomForestClassifier (alcista / bajista / lateral)
Ejecutar: python -m app.ml.train
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
import os
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "model_v1.joblib"
TICKERS    = ["ACN", "MSFT", "NVDA", "KO", "JPM", "SPY"]
LABELS     = {0: "bajista", 1: "lateral", 2: "alcista"}


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye features a partir de precios:
    - ret_1d, ret_5d, ret_20d : rendimientos logarítmicos 1, 5 y 20 días
    - vol_20d                 : volatilidad móvil 20 días
    - rsi_14                  : RSI de 14 días
    - macd                    : diferencia MACD - señal
    - bb_pct                  : %B de Bollinger (posición dentro de la banda)
    """
    close = df["Close"]
    ret1  = np.log(close / close.shift(1))
    feats = pd.DataFrame(index=df.index)
    feats["ret_1d"]  = ret1
    feats["ret_5d"]  = np.log(close / close.shift(5))
    feats["ret_20d"] = np.log(close / close.shift(20))
    feats["vol_20d"] = ret1.rolling(20).std()

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    feats["rsi_14"] = 100 - 100 / (1 + gain / loss)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    feats["macd"] = macd - macd.ewm(span=9, adjust=False).mean()

    # Bollinger %B
    mid  = close.rolling(20).mean()
    std  = close.rolling(20).std()
    feats["bb_pct"] = (close - (mid - 2 * std)) / (4 * std)

    return feats


def label_regime(ret_20d: pd.Series, threshold: float = 0.03) -> pd.Series:
    """
    Etiqueta el régimen a partir del retorno a 20 días (forward-looking).
    > +3%   → 2 (alcista)
    < -3%   → 0 (bajista)
    resto   → 1 (lateral)
    """
    conditions = [
        ret_20d > threshold,
        ret_20d < -threshold,
    ]
    return pd.Series(
        np.select(conditions, [2, 0], default=1),
        index=ret_20d.index
    )


def train() -> None:
    logger.info("Descargando datos de entrenamiento...")
    frames = []
    for ticker in TICKERS:
        df = yf.download(ticker, period="5y", auto_adjust=True, progress=False)
        if df.empty:
            continue
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        feats  = build_features(df)
        # Etiqueta forward: régimen que observaremos en los próximos 20 días
        future_ret = np.log(df["Close"].shift(-20) / df["Close"])
        label  = label_regime(future_ret)
        feats["label"] = label.values
        feats.dropna(inplace=True)
        frames.append(feats)

    if not frames:
        raise RuntimeError("No se pudieron obtener datos para entrenar.")

    data = pd.concat(frames).dropna()
    feature_cols = ["ret_1d", "ret_5d", "ret_20d", "vol_20d", "rsi_14", "macd", "bb_pct"]

    X = data[feature_cols].values
    y = data["label"].astype(int).values

    # Split temporal (sin shuffle para evitar leakage)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    logger.info(f"Accuracy en test: {acc:.4f}")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=list(LABELS.values())))

    # Guardar modelo con metadatos
    artifact = {
        "pipeline":     pipeline,
        "feature_cols": feature_cols,
        "labels":       LABELS,
        "version":      "v1",
        "accuracy":     round(acc, 4),
        "tickers":      TICKERS,
    }
    joblib.dump(artifact, MODEL_PATH)
    logger.info(f"Modelo guardado en {MODEL_PATH}")


if __name__ == "__main__":
    train()