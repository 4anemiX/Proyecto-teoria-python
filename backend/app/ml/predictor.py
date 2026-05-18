"""
predictor.py — Singleton para servir el modelo ML sin recargar por request
Clase: ModelPredictor (patrón Singleton)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "model_v1.joblib"


class ModelPredictor:
    """
    Singleton: el modelo se carga UNA SOLA VEZ en memoria.
    Verificación: el mensaje 'Cargando modelo ML...' aparece solo una vez en los logs.
    """
    _instance: "ModelPredictor | None" = None
    _artifact: dict | None = None

    def __new__(cls) -> "ModelPredictor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Modelo no encontrado en {MODEL_PATH}. "
                "Ejecutar primero: python -m app.ml.train"
            )
        logger.info("Cargando modelo ML...  (este mensaje debe aparecer UNA SOLA VEZ)")
        self._artifact = joblib.load(MODEL_PATH)
        logger.info(
            f"Modelo {self._artifact['version']} cargado — "
            f"accuracy: {self._artifact['accuracy']}"
        )

    @property
    def version(self) -> str:
        return self._artifact["version"] if self._artifact else "sin_cargar"

    @property
    def labels(self) -> Dict[int, str]:
        return self._artifact["labels"] if self._artifact else {}

    @property
    def accuracy(self) -> float:
        return self._artifact.get("accuracy", 0.0) if self._artifact else 0.0

    @property
    def feature_cols(self) -> List[str]:
        return self._artifact.get("feature_cols", []) if self._artifact else []

    def _build_features(self, close: pd.Series) -> np.ndarray:
        """Replica exactamente el mismo pipeline de features que train.py."""
        ret1 = np.log(close / close.shift(1))
        feats = {
            "ret_1d":  float(ret1.iloc[-1]),
            "ret_5d":  float(np.log(close.iloc[-1] / close.iloc[-6])) if len(close) > 5 else 0.0,
            "ret_20d": float(np.log(close.iloc[-1] / close.iloc[-21])) if len(close) > 20 else 0.0,
            "vol_20d": float(ret1.rolling(20).std().iloc[-1]),
        }

        # RSI
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        feats["rsi_14"] = float(100 - 100 / (1 + gain.iloc[-1] / max(loss.iloc[-1], 1e-10)))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd  = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        feats["macd"] = float((macd - signal).iloc[-1])

        # Bollinger %B
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        bb_pct = (close - (mid - 2 * std)) / (4 * std)
        feats["bb_pct"] = float(bb_pct.iloc[-1])

        return np.array([[feats[c] for c in self.feature_cols]])

    def predict(self, ticker: str, close_series: pd.Series) -> Dict:
        """
        Predice el régimen de mercado actual para un ticker.
        Retorna clase, probabilidades y features usadas.
        """
        if self._artifact is None:
            raise RuntimeError("Modelo no cargado.")

        pipeline = self._artifact["pipeline"]
        X = self._build_features(close_series)

        # Verificar NaN
        if np.any(np.isnan(X)):
            return {"error": "Features con valores NaN. Serie demasiado corta."}

        pred_class = int(pipeline.predict(X)[0])
        pred_proba = pipeline.predict_proba(X)[0]
        label      = self.labels.get(pred_class, "desconocido")
        confidence = float(pred_proba[pred_class])

        feature_vals = {
            col: round(float(X[0][i]), 6)
            for i, col in enumerate(self.feature_cols)
        }

        return {
            "ticker":         ticker,
            "model_version":  self.version,
            "regime":         label,
            "regime_code":    pred_class,
            "confidence":     round(confidence, 4),
            "probabilities": {
                self.labels.get(i, str(i)): round(float(p), 4)
                for i, p in enumerate(pred_proba)
            },
            "features_used":  feature_vals,
            "model_accuracy": self.accuracy,
            "interpretation": {
                "alcista":  "El modelo anticipa retornos positivos en los próximos ~20 días.",
                "bajista":  "El modelo anticipa retornos negativos en los próximos ~20 días.",
                "lateral":  "El modelo no detecta tendencia clara en los próximos ~20 días.",
            }.get(label, ""),
        }


# Instancia singleton de módulo (se crea al importar por primera vez)
def get_predictor() -> ModelPredictor:
    """Factory para inyección con Depends()."""
    return ModelPredictor()