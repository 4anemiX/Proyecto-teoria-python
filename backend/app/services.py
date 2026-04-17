import yfinance as yf
import numpy as np
import pandas as pd
from scipy import stats
from arch import arch_model
import warnings
warnings.filterwarnings("ignore")

TICKERS = ["ACN", "MSFT", "NVDA", "KO", "JPM", "SPY"]
BENCHMARK = "SPY"

def get_prices(tickers: list[str], period: str = "3y") -> pd.DataFrame:
    data = yf.download(tickers, period=period, progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        return data["Close"].dropna(how="all")
    return data[["Close"]].rename(columns={"Close": tickers[0]}).dropna()

def get_returns(tickers: list[str], period: str = "3y") -> pd.DataFrame:
    prices = get_prices(tickers, period)
    return np.log(prices / prices.shift(1)).dropna()

# ── Indicadores técnicos ─────────────────────────────────────────────────────
def compute_indicators(ticker: str) -> dict:
    df = get_prices([ticker], period="1y")
    close = df[ticker] if ticker in df.columns else df.iloc[:, 0]

    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]
    ema20 = close.ewm(span=20).mean().iloc[-1]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - 100 / (1 + rs)).iloc[-1]

    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()

    sma20_bb = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = (sma20_bb + 2 * std20).iloc[-1]
    bb_lower = (sma20_bb - 2 * std20).iloc[-1]

    last = float(close.iloc[-1])

    # Señal simple
    signal = "NEUTRAL"
    if rsi < 35 and last < float(sma50):
        signal = "COMPRA"
    elif rsi > 65 and last > float(sma50):
        signal = "VENTA"

    return {
        "ticker": ticker,
        "sma_20": round(float(sma20), 2),
        "sma_50": round(float(sma50), 2),
        "ema_20": round(float(ema20), 2),
        "rsi": round(float(rsi), 2),
        "macd": round(float(macd_line.iloc[-1]), 4),
        "macd_signal": round(float(signal_line.iloc[-1]), 4),
        "bb_upper": round(float(bb_upper), 2),
        "bb_lower": round(float(bb_lower), 2),
        "last_price": round(last, 2),
        "signal": signal,
    }

# ── VaR & CVaR ───────────────────────────────────────────────────────────────
def compute_var(tickers: list[str], weights: list[float], confidence: float = 0.95) -> dict:
    rets = get_returns(tickers)
    portfolio_rets = (rets * weights).sum(axis=1)

    # Histórico
    var_hist = float(-np.percentile(portfolio_rets, (1 - confidence) * 100))
    cvar = float(-portfolio_rets[portfolio_rets <= -var_hist].mean())

    # Paramétrico (normal)
    mu, sigma = portfolio_rets.mean(), portfolio_rets.std()
    var_param = float(-(mu + stats.norm.ppf(1 - confidence) * sigma))

    # Monte Carlo
    np.random.seed(42)
    sim = np.random.normal(mu, sigma, 10000)
    var_mc = float(-np.percentile(sim, (1 - confidence) * 100))

    return {
        "ticker_or_portfolio": "Portfolio",
        "var_historico": round(var_hist, 6),
        "var_parametrico": round(var_param, 6),
        "var_montecarlo": round(var_mc, 6),
        "cvar": round(cvar, 6),
        "confidence_level": confidence,
    }

# ── CAPM ─────────────────────────────────────────────────────────────────────
def compute_capm(ticker: str, rf: float = 0.045) -> dict:
    rets = get_returns([ticker, BENCHMARK])
    asset = rets[ticker]
    market = rets[BENCHMARK]

    slope, intercept, r_val, *_ = stats.linregress(market, asset)
    mkt_annual = float(market.mean() * 252)
    expected = rf + slope * (mkt_annual - rf)

    return {
        "ticker": ticker,
        "beta": round(slope, 4),
        "alpha": round(intercept * 252, 6),
        "expected_return": round(expected, 4),
        "risk_free_rate": rf,
        "market_return": round(mkt_annual, 4),
        "r_squared": round(r_val**2, 4),
    }

# ── Frontera eficiente ────────────────────────────────────────────────────────
def compute_efficient_frontier(tickers: list[str], n_portfolios: int = 3000) -> dict:
    rets = get_returns(tickers)
    mu = rets.mean() * 252
    cov = rets.cov() * 252
    n = len(tickers)

    results = {"returns": [], "volatility": [], "sharpe": [], "weights": []}
    np.random.seed(42)
    for _ in range(n_portfolios):
        w = np.random.dirichlet(np.ones(n))
        r = float(np.dot(w, mu))
        v = float(np.sqrt(w @ cov @ w))
        s = r / v
        results["returns"].append(round(r, 6))
        results["volatility"].append(round(v, 6))
        results["sharpe"].append(round(s, 4))
        results["weights"].append([round(x, 4) for x in w])

    # Portafolio óptimo Sharpe
    best_idx = int(np.argmax(results["sharpe"]))
    opt_w = results["weights"][best_idx]
    opt_portfolio = {t: round(opt_w[i], 4) for i, t in enumerate(tickers)}

    return {
        "frontier": results,
        "optimal_portfolio": opt_portfolio,
        "optimal_sharpe": results["sharpe"][best_idx],
        "optimal_return": results["returns"][best_idx],
        "optimal_volatility": results["volatility"][best_idx],
        "tickers": tickers,
    }

# ── GARCH ─────────────────────────────────────────────────────────────────────
def compute_garch(ticker: str) -> dict:
    rets = get_returns([ticker])
    r = rets[ticker].dropna() * 100

    try:
        am = arch_model(r, vol="Garch", p=1, q=1, dist="normal")
        res = am.fit(disp="off")
        forecast = res.forecast(horizon=5)
        vol_forecast = list(np.sqrt(forecast.variance.values[-1]) / 100)
        aic, bic = res.aic, res.bic
        params = {k: round(v, 6) for k, v in res.params.items()}
    except Exception:
        vol_forecast = [None] * 5
        aic, bic = None, None
        params = {}

    return {
        "ticker": ticker,
        "aic": round(aic, 2) if aic else None,
        "bic": round(bic, 2) if bic else None,
        "params": params,
        "vol_forecast_5d": [round(v, 6) if v else None for v in vol_forecast],
    }

# ── Macro (tasa libre de riesgo simplificada) ─────────────────────────────────
def get_macro(fred_api_key: str = "demo") -> dict:
    try:
        import requests
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF"
        df = pd.read_csv(url, index_col=0, parse_dates=True)
        rf_daily = float(df.iloc[-1, 0]) / 100
        rf_annual = rf_daily
        return {
            "risk_free_rate": round(rf_annual, 4),
            "source": "FRED - Federal Funds Rate",
            "inflation_us": None,
            "fed_funds_rate": round(rf_annual, 4),
        }
    except Exception:
        return {
            "risk_free_rate": 0.045,
            "source": "Default (FRED no disponible)",
            "inflation_us": None,
            "fed_funds_rate": None,
        }