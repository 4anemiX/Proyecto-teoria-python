import time
import logging
import functools
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from arch import arch_model
from pypfopt import EfficientFrontier, risk_models, expected_returns

from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Decorador timer_log ─────────────────────────────────────────
def timer_log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"[timer_log] {func.__name__} ejecutado en {elapsed:.3f}s")
        return result
    return wrapper

# ── Constantes del portafolio ───────────────────────────────────
PORTFOLIO = {
    "ACN":  {"empresa": "Accenture",       "sector": "Consultoría Tecnológica"},
    "MSFT": {"empresa": "Microsoft",        "sector": "Cloud / Inteligencia Artificial"},
    "NVDA": {"empresa": "NVIDIA",           "sector": "Semiconductores / IA"},
    "KO":   {"empresa": "Coca-Cola",        "sector": "Consumo Defensivo"},
    "JPM":  {"empresa": "JPMorgan Chase",   "sector": "Finanzas Digitales"},
}
BENCHMARK = "SPY"
TICKERS_ALL = list(PORTFOLIO.keys()) + [BENCHMARK]

def _clean(lst):
    """Convierte NaN a None para serialización JSON."""
    return [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), 6) for v in lst]

# ── DataService ─────────────────────────────────────────────────
class DataService:
    @timer_log
    def get_prices(self, ticker: str, years: int = None, start: str = None, end: str = None) -> pd.DataFrame:
        if start and end:
            df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        else:
            y = years or settings.default_years
            df = yf.download(ticker, period=f"{y}y", auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"No se encontraron datos para {ticker}")
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df

    @timer_log
    def get_asset_info(self) -> List[Dict]:
        result = []
        for ticker, meta in PORTFOLIO.items():
            precio, variacion = 0.0, 0.0
            for intento in range(3):  # hasta 3 intentos
                try:
                    df = yf.download(
                        ticker,
                        period="5d",
                        auto_adjust=True,
                        progress=False,
                        timeout=30,
                    )
                    if df.empty or len(df) < 2:
                        continue
                    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                    precio = float(df["Close"].iloc[-1])
                    prev = float(df["Close"].iloc[-2])
                    variacion = (precio - prev) / prev * 100
                    if precio > 0:
                        break  # éxito, salir del loop
                except Exception as e:
                    logger.warning(f"Intento {intento+1} fallido para {ticker}: {e}")
                    time.sleep(2)

            result.append({
                "ticker": ticker,
                "empresa": meta["empresa"],
                "sector": meta["sector"],
                "precio_actual": round(precio, 2),
                "variacion_diaria": round(variacion, 4),
            })
        return result

# ── TechnicalIndicators ─────────────────────────────────────────
class TechnicalIndicators:
    def __init__(self, sma=None, ema=None, rsi=None):
        self.sma_p = sma or settings.sma_period
        self.ema_p = ema or settings.ema_period
        self.rsi_p = rsi or settings.rsi_period

    @timer_log
    def compute(self, df: pd.DataFrame) -> Dict:
        close = df["Close"]
        sma = close.rolling(self.sma_p).mean()
        ema = close.ewm(span=self.ema_p, adjust=False).mean()
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(self.rsi_p).mean()
        loss = (-delta.clip(upper=0)).rolling(self.rsi_p).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()

        low14 = df["Low"].rolling(14).min()
        high14 = df["High"].rolling(14).max()
        stoch_k = 100 * (close - low14) / (high14 - low14)
        stoch_d = stoch_k.rolling(3).mean()

        fechas = [str(d)[:10] for d in df.index]
        return {
            "fechas": fechas,
            "close": _clean(close.tolist()),
            "sma": _clean(sma.tolist()),
            "ema": _clean(ema.tolist()),
            "bb_upper": _clean(bb_upper.tolist()),
            "bb_lower": _clean(bb_lower.tolist()),
            "bb_mid": _clean(bb_mid.tolist()),
            "rsi": _clean(rsi.tolist()),
            "macd": _clean(macd.tolist()),
            "macd_signal": _clean(macd_signal.tolist()),
            "stoch_k": _clean(stoch_k.tolist()),
            "stoch_d": _clean(stoch_d.tolist()),
        }

# ── RiskCalculator ──────────────────────────────────────────────
class RiskCalculator:
    @timer_log
    def returns_stats(self, df: pd.DataFrame) -> Dict:
        close = df["Close"].dropna()
        ret_simple = close.pct_change().dropna()
        ret_log = np.log(close / close.shift(1)).dropna()
        jb_stat, jb_pval = stats.jarque_bera(ret_log)
        sh_stat, sh_pval = stats.shapiro(ret_log[-500:] if len(ret_log) > 500 else ret_log)
        fechas = [str(d)[:10] for d in ret_simple.index]
        return {
            "fechas": fechas,
            "simples": _clean(ret_simple.tolist()),
            "logaritmicos": _clean(ret_log.tolist()),
            "media": round(float(ret_log.mean()), 6),
            "std": round(float(ret_log.std()), 6),
            "skewness": round(float(stats.skew(ret_log)), 4),
            "kurtosis": round(float(stats.kurtosis(ret_log)), 4),
            "jarque_bera_stat": round(float(jb_stat), 4),
            "jarque_bera_pval": round(float(jb_pval), 4),
            "shapiro_stat": round(float(sh_stat), 4),
            "shapiro_pval": round(float(sh_pval), 4),
        }

    @timer_log
    def compute_var(self, df: pd.DataFrame, confidence: float, simulations: int) -> Dict:
        close = df["Close"].dropna()
        ret = np.log(close / close.shift(1)).dropna().values
        alpha = 1 - confidence

        # Paramétrico
        mu, sigma = ret.mean(), ret.std()
        var_param = float(stats.norm.ppf(alpha, mu, sigma))

        # Histórico
        var_hist = float(np.percentile(ret, alpha * 100))

        # Montecarlo
        sim = np.random.normal(mu, sigma, simulations)
        var_mc = float(np.percentile(sim, alpha * 100))

        # CVaR
        cvar = float(ret[ret <= var_hist].mean())

        # Test de Kupiec
        violations = int(np.sum(ret < var_hist))
        n = len(ret)
        p_hat = violations / n
        p_expected = alpha
        if p_hat > 0 and p_hat < 1:
            lr = -2 * (
                n * np.log(1 - p_expected) + violations * np.log(p_expected)
                - (n - violations) * np.log(1 - p_hat) - violations * np.log(p_hat)
            )
        else:
            lr = 0.0
        kup_pval = float(1 - stats.chi2.cdf(lr, df=1))

        return {
            "confidence": confidence,
            "var_parametric": round(var_param, 6),
            "var_historical": round(var_hist, 6),
            "var_montecarlo": round(var_mc, 6),
            "cvar": round(cvar, 6),
            "kupiec_stat": round(float(lr), 4),
            "kupiec_pval": round(kup_pval, 4),
        }

    @timer_log
    def compute_garch(self, df: pd.DataFrame) -> Dict:
        close = df["Close"].dropna()
        ret = np.log(close / close.shift(1)).dropna() * 100
        results = {}
        specs = {
            "ARCH(1)":    {"vol": "ARCH", "p": 1, "q": 0, "dist": "normal"},
            "GARCH(1,1)": {"vol": "GARCH", "p": 1, "q": 1, "dist": "normal"},
            "GJR-GARCH":  {"vol": "GARCH", "p": 1, "q": 1, "dist": "t", "o": 1},
            "EGARCH":     {"vol": "EGARCH", "p": 1, "q": 1, "dist": "normal"},
        }
        for name, sp in specs.items():
            try:
                kwargs = {"vol": sp["vol"], "p": sp["p"], "dist": sp["dist"]}
                if sp["vol"] != "EGARCH":
                    kwargs["q"] = sp.get("q", 0)
                if "o" in sp:
                    kwargs["o"] = sp["o"]
                m = arch_model(ret, **kwargs)
                r = m.fit(disp="off", show_warning=False)
                cond_vol = r.conditional_volatility
                forecast = r.forecast(horizon=5)
                fcast_vol = np.sqrt(forecast.variance.values[-1]) if forecast.variance is not None else []
                results[name] = {
                    "aic": round(r.aic, 2),
                    "bic": round(r.bic, 2),
                    "cond_vol": _clean(cond_vol.tolist()),
                    "fechas": [str(d)[:10] for d in cond_vol.index],
                    "forecast_5d": _clean(fcast_vol.tolist()) if hasattr(fcast_vol, "tolist") else [],
                    "params": {k: round(v, 6) for k, v in r.params.items()},
                }
            except Exception as e:
                results[name] = {"error": str(e)}
        return results

# ── PortfolioAnalyzer ───────────────────────────────────────────
class PortfolioAnalyzer:
    def __init__(self, data_svc: DataService):
        self.data_svc = data_svc

    @timer_log
    def capm(self, start: str = None, end: str = None) -> List[Dict]:
        bench_df  = self.data_svc.get_prices(BENCHMARK, start=start, end=end)
        bench_ret = np.log(bench_df["Close"] / bench_df["Close"].shift(1)).dropna()
        rf_ticker = yf.download("^IRX", period="5d", progress=False, auto_adjust=True)
        rf_annual = float(rf_ticker["Close"].iloc[-1]) / 100 if not rf_ticker.empty else 0.05
        rf_daily  = rf_annual / 252
        market_ret = float(bench_ret.mean()) * 252

        results = []
        for ticker in PORTFOLIO:
            try:
                df  = self.data_svc.get_prices(ticker, start=start, end=end)
                ret = np.log(df["Close"] / df["Close"].shift(1)).dropna()
                common = ret.index.intersection(bench_ret.index)
                r_a = ret.loc[common].values
                r_m = bench_ret.loc[common].values
                cov  = np.cov(r_a, r_m)
                beta = cov[0, 1] / cov[1, 1]
                slope, intercept, r_val, _, _ = stats.linregress(r_m, r_a)
                expected = rf_daily * 252 + beta * (market_ret - rf_annual)
                results.append({
                    "ticker":          ticker,
                    "beta":            round(beta, 4),
                    "alpha":           round(float(intercept) * 252, 6),
                    "r_squared":       round(r_val ** 2, 4),
                    "expected_return": round(expected, 6),
                    "risk_free_rate":  round(rf_annual, 6),
                    "market_return":   round(market_ret, 6),
                })
            except Exception as e:
                results.append({"ticker": ticker, "error": str(e)})
        return results
    
    @timer_log
    def efficient_frontier(self, tickers: List[str], weights: List[float]) -> Dict:
        prices = pd.DataFrame()
        for t in tickers:
            df = self.data_svc.get_prices(t)
            prices[t] = df["Close"]
        prices.dropna(inplace=True)

        mu = expected_returns.mean_historical_return(prices)
        S = risk_models.sample_cov(prices)

        ef_mv = EfficientFrontier(mu, S)
        ef_mv.min_volatility()
        w_mv = ef_mv.clean_weights()
        p_mv = ef_mv.portfolio_performance()

        ef_ms = EfficientFrontier(mu, S)
        ef_ms.max_sharpe()
        w_ms = ef_ms.clean_weights()
        p_ms = ef_ms.portfolio_performance()

        # Frontera eficiente
        vols, rets = [], []
        for target in np.linspace(float(mu.min()), float(mu.max()), 60):
            try:
                ef_t = EfficientFrontier(mu, S)
                ef_t.efficient_return(target)
                perf = ef_t.portfolio_performance()
                vols.append(round(perf[1], 6))
                rets.append(round(perf[0], 6))
            except Exception:
                pass

        return {
            "volatilities": vols,
            "returns": rets,
            "min_var_weights": {k: round(v, 4) for k, v in w_mv.items()},
            "min_var_return": round(p_mv[0], 6),
            "min_var_vol": round(p_mv[1], 6),
            "max_sharpe_weights": {k: round(v, 4) for k, v in w_ms.items()},
            "max_sharpe_return": round(p_ms[0], 6),
            "max_sharpe_vol": round(p_ms[1], 6),
            "max_sharpe_ratio": round(p_ms[2], 4),
        }

# ── AlertasService ──────────────────────────────────────────────
class AlertasService:
    def __init__(self, tech: TechnicalIndicators):
        self.tech = tech

    @timer_log
    def generate(self, ticker: str, df: pd.DataFrame) -> Dict:
        ind = self.tech.compute(df)

        def last_valid(lst):
            for v in reversed(lst):
                if v is not None:
                    return v
            return None

        rsi_val = last_valid(ind["rsi"])
        macd_val = last_valid(ind["macd"])
        macd_sig = last_valid(ind["macd_signal"])
        close_val = last_valid(ind["close"])
        bb_up = last_valid(ind["bb_upper"])
        bb_lo = last_valid(ind["bb_lower"])
        stoch_k = last_valid(ind["stoch_k"])
        sma_val = last_valid(ind["sma"])
        ema_val = last_valid(ind["ema"])

        rsi_signal = "Sobrecompra" if rsi_val and rsi_val > 70 else ("Sobreventa" if rsi_val and rsi_val < 30 else "Neutral")
        macd_signal = "Compra" if (macd_val and macd_sig and macd_val > macd_sig) else "Venta"
        bb_signal = "Sobrecompra" if (close_val and bb_up and close_val > bb_up) else ("Sobreventa" if (close_val and bb_lo and close_val < bb_lo) else "Neutral")
        sma_cross = "Compra" if (sma_val and ema_val and ema_val > sma_val) else "Venta"
        stoch_signal = "Sobrecompra" if (stoch_k and stoch_k > 80) else ("Sobreventa" if (stoch_k and stoch_k < 20) else "Neutral")

        buy_signals = sum(1 for s in [rsi_signal, macd_signal, bb_signal, sma_cross, stoch_signal] if s in ["Compra", "Sobreventa"])
        sell_signals = sum(1 for s in [rsi_signal, macd_signal, bb_signal, sma_cross, stoch_signal] if s in ["Venta", "Sobrecompra"])
        overall = "🟢 Compra" if buy_signals > sell_signals else ("🔴 Venta" if sell_signals > buy_signals else "🟡 Neutral")

        return {
            "ticker": ticker,
            "rsi_signal": rsi_signal,
            "macd_signal": macd_signal,
            "bb_signal": bb_signal,
            "sma_cross": sma_cross,
            "stoch_signal": stoch_signal,
            "overall": overall,
        }

# ── MacroService ────────────────────────────────────────────────
class MacroService:
    @timer_log
    def get_macro(self) -> Dict:
        def fetch(ticker, col="Close"):
            try:
                df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
                return float(df[col].iloc[-1])
            except Exception:
                return 0.0

        rf_raw = fetch("^IRX")
        return {
            "risk_free_rate": round(rf_raw / 100, 6),
            "sp500_return": round(fetch("^GSPC"), 2),
            "vix": round(fetch("^VIX"), 2),
            "usdcop": round(fetch("USDCOP=X"), 2),
            "eurusd": round(fetch("EURUSD=X"), 6),
            "tnx": round(fetch("^TNX"), 4),
        }