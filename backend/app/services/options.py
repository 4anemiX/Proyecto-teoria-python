"""
options.py — Valoración de opciones europeas: Black-Scholes, Greeks, vol implícita
Clase: OptionPricer
"""
from __future__ import annotations
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from typing import Dict, Literal
import logging

logger = logging.getLogger(__name__)

OptionType = Literal["call", "put"]


class OptionPricer:
    """
    Valoración de opciones europeas con Black-Scholes.
    Parámetros del constructor (todos configurables por request Pydantic):
        S     : precio del subyacente
        K     : strike
        T     : tiempo al vencimiento en años
        r     : tasa libre de riesgo (decimal)
        sigma : volatilidad (decimal)
        tipo  : "call" o "put"
    """

    def __init__(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        tipo: OptionType = "call",
    ):
        if T <= 0:
            raise ValueError("T (tiempo al vencimiento) debe ser > 0.")
        if sigma <= 0:
            raise ValueError("sigma (volatilidad) debe ser > 0.")
        if S <= 0 or K <= 0:
            raise ValueError("S y K deben ser > 0.")

        self.S     = S
        self.K     = K
        self.T     = T
        self.r     = r
        self.sigma = sigma
        self.tipo  = tipo

    # ── Auxiliares ───────────────────────────────────────────────────────────
    def _d1_d2(self) -> tuple[float, float]:
        d1 = (np.log(self.S / self.K) + (self.r + 0.5 * self.sigma ** 2) * self.T) \
             / (self.sigma * np.sqrt(self.T))
        d2 = d1 - self.sigma * np.sqrt(self.T)
        return float(d1), float(d2)

    # ── Precio Black-Scholes ─────────────────────────────────────────────────
    def black_scholes(self) -> float:
        d1, d2 = self._d1_d2()
        disc   = self.K * np.exp(-self.r * self.T)
        if self.tipo == "call":
            price = self.S * norm.cdf(d1) - disc * norm.cdf(d2)
        else:
            price = disc * norm.cdf(-d2) - self.S * norm.cdf(-d1)
        return float(price)

    # ── Greeks ───────────────────────────────────────────────────────────────
    def greeks(self) -> Dict:
        d1, d2 = self._d1_d2()
        nprime  = norm.pdf(d1)
        disc    = np.exp(-self.r * self.T)
        sqrt_T  = np.sqrt(self.T)

        delta = norm.cdf(d1) if self.tipo == "call" else norm.cdf(d1) - 1
        gamma = nprime / (self.S * self.sigma * sqrt_T)
        vega  = self.S * sqrt_T * nprime                    # por unidad de σ
        if self.tipo == "call":
            theta = (
                - self.S * nprime * self.sigma / (2 * sqrt_T)
                - self.r * self.K * disc * norm.cdf(d2)
            ) / 365     # por día calendario
            rho = self.K * self.T * disc * norm.cdf(d2) / 100
        else:
            theta = (
                - self.S * nprime * self.sigma / (2 * sqrt_T)
                + self.r * self.K * disc * norm.cdf(-d2)
            ) / 365
            rho = -self.K * self.T * disc * norm.cdf(-d2) / 100

        return {
            "delta": round(float(delta), 6),
            "gamma": round(float(gamma), 6),
            "vega":  round(float(vega),  6),
            "theta": round(float(theta), 6),
            "rho":   round(float(rho),   6),
            "interpretation": {
                "delta": f"El precio de la opción cambia ≈ {delta:.4f} por cada $1 de movimiento del subyacente.",
                "gamma": f"Delta cambia ≈ {gamma:.4f} por cada $1 de movimiento.",
                "vega":  f"El precio cambia ≈ ${vega:.4f} por 1 pp de cambio en volatilidad.",
                "theta": f"La opción pierde ≈ ${abs(theta):.4f} de valor por día.",
                "rho":   f"El precio cambia ≈ ${rho:.4f} ante +1 pp en la tasa libre de riesgo.",
            },
        }

    # ── Paridad Put-Call ─────────────────────────────────────────────────────
    def put_call_parity_check(self) -> Dict:
        """Verifica C - P = S - K·e^(-rT) numéricamente."""
        call = OptionPricer(self.S, self.K, self.T, self.r, self.sigma, "call").black_scholes()
        put  = OptionPricer(self.S, self.K, self.T, self.r, self.sigma, "put").black_scholes()
        lhs  = call - put
        rhs  = self.S - self.K * np.exp(-self.r * self.T)
        error = abs(lhs - rhs)
        return {
            "call_price":  round(call, 6),
            "put_price":   round(put, 6),
            "lhs_C_minus_P": round(lhs, 6),
            "rhs_S_minus_Ke": round(float(rhs), 6),
            "error":       round(float(error), 8),
            "parity_holds": bool(error < 1e-6),
        }

    # ── Volatilidad implícita (Newton-Raphson) ───────────────────────────────
    def implied_volatility(self, market_price: float) -> Dict:
        """
        Encuentra σ_imp tal que BS(σ_imp) = market_price.
        Usa Brent (más robusto) como fallback a Newton-Raphson.
        """
        def objective(sigma_try: float) -> float:
            op = OptionPricer(self.S, self.K, self.T, self.r, sigma_try, self.tipo)
            return op.black_scholes() - market_price

        try:
            # Newton-Raphson con vega como derivada
            sigma = 0.3
            for _ in range(100):
                op      = OptionPricer(self.S, self.K, self.T, self.r, sigma, self.tipo)
                price   = op.black_scholes()
                vega_val = op.greeks()["vega"]
                if abs(vega_val) < 1e-10:
                    break
                delta_s = (price - market_price) / vega_val
                sigma  -= delta_s
                sigma   = max(0.001, min(sigma, 10.0))
                if abs(delta_s) < 1e-8:
                    break
            # Verificar convergencia; si no, usar Brent
            if abs(objective(sigma)) > 1e-4:
                sigma = brentq(objective, 0.001, 10.0, xtol=1e-8)
        except Exception:
            try:
                sigma = brentq(objective, 0.001, 10.0, xtol=1e-8)
            except Exception:
                return {"error": "No se pudo encontrar volatilidad implícita."}

        spread = sigma - self.sigma
        return {
            "sigma_historica_pct":  round(self.sigma * 100, 4),
            "sigma_implicita_pct":  round(sigma * 100, 4),
            "spread_pp":            round(spread * 100, 4),
            "interpretation": (
                f"La vol. implícita ({sigma*100:.2f}%) es "
                + ("mayor" if spread > 0 else "menor")
                + f" que la histórica ({self.sigma*100:.2f}%), "
                + ("indicando que el mercado anticipa más incertidumbre." if spread > 0
                   else "indicando que el mercado anticipa menor volatilidad.")
            ),
        }

    # ── Payoff y curvas para graficar ────────────────────────────────────────
    def payoff_curve(self, spot_range: int = 50) -> Dict:
        """Genera puntos para las curvas de payoff y precio vs spot."""
        spots  = np.linspace(self.S * 0.5, self.S * 1.5, spot_range)
        prices = []
        payoffs = []
        for s in spots:
            op    = OptionPricer(s, self.K, self.T, self.r, self.sigma, self.tipo)
            prices.append(round(op.black_scholes(), 4))
            if self.tipo == "call":
                payoffs.append(round(float(max(s - self.K, 0)), 4))
            else:
                payoffs.append(round(float(max(self.K - s, 0)), 4))
        return {
            "spots":   spots.tolist(),
            "prices":  prices,
            "payoffs": payoffs,
        }

    def delta_curve(self, spot_range: int = 50, T_values: list | None = None) -> Dict:
        """Curva de delta vs spot para distintos T."""
        if T_values is None:
            T_values = [self.T, self.T * 0.5, self.T * 0.1]
        spots   = np.linspace(self.S * 0.5, self.S * 1.5, spot_range)
        curves  = {}
        for T_val in T_values:
            label  = f"T={T_val:.2f}a"
            deltas = []
            for s in spots:
                op = OptionPricer(s, self.K, max(T_val, 1e-4), self.r, self.sigma, self.tipo)
                deltas.append(round(op.greeks()["delta"], 6))
            curves[label] = deltas
        return {"spots": spots.tolist(), "delta_curves": curves}

    # ── Resultado completo ───────────────────────────────────────────────────
    def full_result(self) -> Dict:
        price  = self.black_scholes()
        d1, d2 = self._d1_d2()
        return {
            "inputs": {
                "S": self.S, "K": self.K,
                "T": self.T, "r": round(self.r * 100, 4),
                "sigma_pct": round(self.sigma * 100, 4),
                "tipo": self.tipo,
            },
            "d1": round(d1, 6),
            "d2": round(d2, 6),
            "price": round(price, 6),
            "greeks": self.greeks(),
            "parity": self.put_call_parity_check(),
        }