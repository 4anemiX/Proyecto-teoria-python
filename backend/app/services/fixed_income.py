"""
fixed_income.py — Renta fija: curva de rendimiento y bono sintético
Clases: YieldCurve, Bond
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import least_squares
from scipy.interpolate import CubicSpline
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class YieldCurve:
    """Ajusta la curva de rendimiento de tesoros US con el modelo Nelson-Siegel."""

    # Vencimientos estándar FRED en años
    STD_MATURITIES = {
        "DGS3MO": 0.25,
        "DGS6MO": 0.5,
        "DGS1":   1.0,
        "DGS2":   2.0,
        "DGS5":   5.0,
        "DGS10":  10.0,
        "DGS30":  30.0,
    }

    def __init__(self):
        self.params_: np.ndarray | None = None   # [β0, β1, β2, λ]
        self.rmse_: float | None = None
        self._maturities: np.ndarray | None = None
        self._yields: np.ndarray | None = None

    # ── Nelson-Siegel ─────────────────────────────────────────────────────────
    @staticmethod
    def _ns(tau: np.ndarray, b0: float, b1: float, b2: float, lam: float) -> np.ndarray:
        """y(τ) = β0 + β1·f1 + β2·f2"""
        f1 = (1 - np.exp(-tau / lam)) / (tau / lam)
        f2 = f1 - np.exp(-tau / lam)
        return b0 + b1 * f1 + b2 * f2

    def fit_nelson_siegel(
        self,
        maturities: List[float],
        yields: List[float],
    ) -> Dict:
        """
        Ajusta Nelson-Siegel por mínimos cuadrados no lineales.
        Retorna dict con parámetros e interpretación.
        """
        tau = np.array(maturities, dtype=float)
        y   = np.array(yields,     dtype=float) / 100.0   # convertir de % a decimal

        def residuals(p):
            return self._ns(tau, *p) - y

        x0 = [y.mean(), y[0] - y[-1], 0.0, 1.5]
        bounds = (
            [-np.inf, -np.inf, -np.inf, 0.01],
            [ np.inf,  np.inf,  np.inf, 30.0],
        )
        result = least_squares(residuals, x0, bounds=bounds, method="trf")
        self.params_ = result.x
        self._maturities = tau
        self._yields = y

        fitted = self._ns(tau, *self.params_)
        self.rmse_ = float(np.sqrt(np.mean((fitted - y) ** 2)) * 100)  # en pb

        b0, b1, b2, lam = self.params_
        return {
            "beta0": round(float(b0) * 100, 4),
            "beta1": round(float(b1) * 100, 4),
            "beta2": round(float(b2) * 100, 4),
            "lambda": round(float(lam), 4),
            "rmse_bp": round(self.rmse_, 4),
            "interpretation": {
                "beta0": "Nivel de largo plazo de la curva",
                "beta1": "Pendiente (corto menos largo); negativo = curva normal",
                "beta2": "Curvatura (joroba o invertida)",
                "lambda": "Velocidad de decaimiento hacia el largo plazo",
            },
        }

    def spot_rate(self, tau: float) -> float:
        """Tasa spot Nelson-Siegel en % para un vencimiento tau (años)."""
        if self.params_ is None:
            raise ValueError("Modelo no ajustado. Llame a fit_nelson_siegel primero.")
        return float(self._ns(np.array([tau]), *self.params_)[0]) * 100

    def curve_points(self, n: int = 100) -> Dict:
        """Devuelve la curva ajustada y los puntos observados para graficar."""
        if self.params_ is None:
            raise ValueError("Modelo no ajustado.")
        tau_range = np.linspace(0.25, 30, n)
        ns_vals   = self._ns(tau_range, *self.params_) * 100
        return {
            "tau_ns":    tau_range.tolist(),
            "yield_ns":  ns_vals.tolist(),
            "tau_obs":   (self._maturities * 1).tolist(),
            "yield_obs": (self._yields * 100).tolist(),
        }

    def curve_shape(self) -> str:
        """Clasifica la forma de la curva."""
        if self.params_ is None:
            return "desconocida"
        short = self.spot_rate(0.25)
        long_  = self.spot_rate(10.0)
        spread = long_ - short
        if spread > 0.5:
            return "normal"
        elif spread < -0.5:
            return "invertida"
        else:
            return "plana"


class Bond:
    """Bono sintético de cupón fijo. Calcula precio, duración y convexidad."""

    def __init__(
        self,
        face_value: float = 1_000.0,
        coupon_rate: float = 0.05,
        maturity_years: int = 10,
        frequency: int = 2,        # pagos por año (2 = semestral)
    ):
        self.F  = face_value
        self.c  = coupon_rate
        self.T  = maturity_years
        self.m  = frequency
        self.n  = maturity_years * frequency        # total de períodos
        self.coupon = face_value * coupon_rate / frequency

    def _cash_flows(self) -> Tuple[np.ndarray, np.ndarray]:
        """Retorna (tiempos en años, flujos de caja)."""
        times = np.arange(1, self.n + 1) / self.m
        cfs   = np.full(self.n, self.coupon)
        cfs[-1] += self.F
        return times, cfs

    def price(self, ytm: float) -> float:
        """Precio del bono dado el rendimiento al vencimiento (ytm anual)."""
        times, cfs = self._cash_flows()
        r_period = ytm / self.m
        pv = np.sum(cfs / (1 + r_period) ** (times * self.m))
        return float(pv)

    def macaulay_duration(self, ytm: float) -> float:
        """Duración de Macaulay en años."""
        times, cfs = self._cash_flows()
        r_period = ytm / self.m
        pv_cfs   = cfs / (1 + r_period) ** (times * self.m)
        P        = pv_cfs.sum()
        return float(np.sum(times * pv_cfs) / P)

    def modified_duration(self, ytm: float) -> float:
        """Duración modificada: sensibilidad % del precio a Δytm."""
        D   = self.macaulay_duration(ytm)
        return float(D / (1 + ytm / self.m))

    def convexity(self, ytm: float) -> float:
        """Convexidad del bono."""
        times, cfs = self._cash_flows()
        r_period   = ytm / self.m
        P          = self.price(ytm)
        periods    = times * self.m
        conv = np.sum(
            cfs * periods * (periods + 1) / (1 + r_period) ** (periods + 2)
        ) / (P * self.m ** 2)
        return float(conv)

    def price_change_approx(self, ytm: float, delta_ytm: float) -> Dict:
        """
        Aproxima el cambio de precio ante un shock de tasa Δytm:
        - Lineal (solo duración modificada)
        - Segundo orden (duración + convexidad)
        - Exacto (reprice)
        """
        P0   = self.price(ytm)
        D_m  = self.modified_duration(ytm)
        C    = self.convexity(ytm)

        dp_linear  = -D_m * delta_ytm * P0
        dp_convex  = (-D_m * delta_ytm + 0.5 * C * delta_ytm ** 2) * P0
        P_exact    = self.price(ytm + delta_ytm)
        dp_exact   = P_exact - P0

        return {
            "ytm_base":       round(ytm * 100, 4),
            "ytm_shocked":    round((ytm + delta_ytm) * 100, 4),
            "delta_ytm_bp":   round(delta_ytm * 10_000, 1),
            "price_base":     round(P0, 4),
            "price_exact":    round(P_exact, 4),
            "dp_linear":      round(dp_linear, 4),
            "dp_convex":      round(dp_convex, 4),
            "dp_exact":       round(dp_exact, 4),
            "pct_linear":     round(dp_linear / P0 * 100, 4),
            "pct_convex":     round(dp_convex / P0 * 100, 4),
            "pct_exact":      round(dp_exact / P0 * 100, 4),
        }

    def full_metrics(self, ytm: float) -> Dict:
        """Métricas completas del bono."""
        P   = self.price(ytm)
        D   = self.macaulay_duration(ytm)
        D_m = self.modified_duration(ytm)
        C   = self.convexity(ytm)

        shocks = {}
        for bp in [-200, -100, -50, 50, 100, 200]:
            key = f"shock_{bp:+d}bp"
            shocks[key] = self.price_change_approx(ytm, bp / 10_000)

        return {
            "face_value":          self.F,
            "coupon_rate_pct":     round(self.c * 100, 2),
            "maturity_years":      self.T,
            "frequency":           self.m,
            "ytm_pct":             round(ytm * 100, 4),
            "price":               round(P, 4),
            "macaulay_duration":   round(D, 4),
            "modified_duration":   round(D_m, 4),
            "convexity":           round(C, 4),
            "price_sensitivity":   shocks,
            "interpretation": {
                "macaulay_duration": f"El bono recupera en promedio su inversión en {D:.2f} años.",
                "modified_duration": f"Un alza de 100 pb reduce el precio ≈ {D_m:.2f}%.",
                "convexity": f"La convexidad ({C:.2f}) atenúa la pérdida y amplifica la ganancia ante shocks.",
            },
        }