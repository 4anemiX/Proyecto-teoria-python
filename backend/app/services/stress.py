"""
stress.py — Stress testing de portafolios
Clase: StressTester
"""
from __future__ import annotations
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class StressTester:
    """
    Aplica escenarios de estrés macroeconómico a un portafolio.
    Usa betas de CAPM para estimar el impacto de shocks de mercado.
    """

    # Escenarios obligatorios del módulo
    DEFAULT_SCENARIOS = [
        {
            "name": "Crisis 2008",
            "rate_shock_bp": 200,
            "market_drop_pct": -0.40,
            "vol_multiplier": 3.0,
        },
        {
            "name": "COVID-19 (Mar 2020)",
            "rate_shock_bp": -150,
            "market_drop_pct": -0.34,
            "vol_multiplier": 4.0,
        },
        {
            "name": "Dot-com 2000",
            "rate_shock_bp": 100,
            "market_drop_pct": -0.30,
            "vol_multiplier": 2.5,
        },
        {
            "name": "Shock de tasas +200pb",
            "rate_shock_bp": 200,
            "market_drop_pct": -0.10,
            "vol_multiplier": 1.5,
        },
        {
            "name": "Recesión suave",
            "rate_shock_bp": -50,
            "market_drop_pct": -0.15,
            "vol_multiplier": 1.8,
        },
        {
            "name": "Escenario base (sin estrés)",
            "rate_shock_bp": 0,
            "market_drop_pct": 0.0,
            "vol_multiplier": 1.0,
        },
    ]

    def __init__(
        self,
        tickers: List[str],
        weights: List[float],
        betas: Dict[str, float],
        current_prices: Dict[str, float],
        base_vol: Dict[str, float],
        rf: float = 0.05,
    ):
        self.tickers        = tickers
        self.weights        = weights
        self.betas          = betas
        self.current_prices = current_prices
        self.base_vol       = base_vol
        self.rf             = rf

    def apply(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica un escenario de estrés y retorna el impacto estimado
        sobre cada activo y el portafolio total.
        """
        name            = scenario.get("name", "Escenario")
        rate_shock_bp   = scenario.get("rate_shock_bp", 0)
        market_drop_pct = scenario.get("market_drop_pct", 0.0)
        vol_multiplier  = scenario.get("vol_multiplier", 1.0)

        asset_impacts = []
        portfolio_pnl = 0.0

        for ticker, weight in zip(self.tickers, self.weights):
            beta      = self.betas.get(ticker, 1.0)
            price     = self.current_prices.get(ticker, 100.0)
            base_v    = self.base_vol.get(ticker, 0.02)

            # Impacto via beta: retorno_activo ≈ beta × retorno_mercado
            market_ret    = market_drop_pct
            asset_ret     = beta * market_ret
            # Ajuste por shock de tasas (aprox -duración × Δr; usamos 5 como proxy)
            rate_adj      = -5.0 * (rate_shock_bp / 10_000)
            total_ret     = asset_ret + rate_adj
            stressed_price = price * (1 + total_ret)
            stressed_vol   = base_v * vol_multiplier * np.sqrt(252)  # anualizada

            pnl_pct = total_ret * 100
            asset_impacts.append({
                "ticker":          ticker,
                "weight":          round(weight, 4),
                "beta":            round(beta, 4),
                "price_base":      round(price, 4),
                "price_stressed":  round(stressed_price, 4),
                "return_pct":      round(pnl_pct, 4),
                "vol_stressed_ann": round(stressed_vol * 100, 4),
            })
            portfolio_pnl += weight * total_ret

        # VaR paramétrico bajo estrés (normal, 95%)
        port_vol_stressed = np.sqrt(
            sum(
                (w * self.base_vol.get(t, 0.02) * vol_multiplier) ** 2
                for t, w in zip(self.tickers, self.weights)
            )
        )
        var_95 = 1.645 * port_vol_stressed * 100

        return {
            "scenario":             name,
            "rate_shock_bp":        rate_shock_bp,
            "market_drop_pct":      round(market_drop_pct * 100, 2),
            "vol_multiplier":       vol_multiplier,
            "portfolio_return_pct": round(portfolio_pnl * 100, 4),
            "var_95_stressed_pct":  round(var_95, 4),
            "assets":               asset_impacts,
        }

    def run_all_scenarios(self) -> Dict[str, Any]:
        """Ejecuta los 6 escenarios obligatorios."""
        results = [self.apply(s) for s in self.DEFAULT_SCENARIOS]
        worst   = min(results, key=lambda r: r["portfolio_return_pct"])
        return {
            "results": results,
            "summary": {
                "worst_scenario":      worst["scenario"],
                "worst_portfolio_pct": worst["portfolio_return_pct"],
                "tickers":             self.tickers,
                "weights":             self.weights,
            },
        }