# ============================================================
# modules/var.py — Módulo 5: VaR y CVaR
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
 
from config import TICKERS, TICKER_INFO, CONFIDENCE_LEVELS, TRADING_DAYS
 
 
def _var_parametrico(r: pd.Series, cl: float, h: int = 1):
    mu, sigma = r.mean(), r.std()
    z    = stats.norm.ppf(1 - cl)
    var  = -(mu * h + z * sigma * np.sqrt(h))
    cvar = -(mu * h - sigma * np.sqrt(h) * stats.norm.pdf(z) / (1 - cl))
    return var, cvar
 
def _var_historico(r: pd.Series, cl: float, h: int = 1):
    var  = -np.percentile(r, (1 - cl) * 100)
    tail = r[r <= -var]
    cvar = -tail.mean() if len(tail) > 0 else var
    return var, cvar
 
def _var_montecarlo(r: pd.Series, cl: float, h: int = 1, n: int = 10_000):
    sims = np.random.normal(r.mean() * h, r.std() * np.sqrt(h), n)
    var  = -np.percentile(sims, (1 - cl) * 100)
    cvar = -sims[sims <= -var].mean()
    return var, cvar, sims
 
def _kupiec(r: pd.Series, var: float, cl: float) -> dict:
    n, exc = len(r), (r < -var).sum()
    p_hat  = exc / n
    p      = 1 - cl
    if exc == 0 or exc == n:
        return {"n": n, "exc": int(exc), "p_hat": p_hat, "lr": np.nan, "p_val": np.nan}
    lr    = -2 * (np.log(p**exc * (1-p)**(n-exc)) - np.log(p_hat**exc * (1-p_hat)**(n-exc)))
    p_val = 1 - stats.chi2.cdf(lr, df=1)
    return {"n": n, "exc": int(exc), "p_hat": float(p_hat), "lr": float(lr), "p_val": float(p_val)}
 
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## 🛡️ Módulo 5 — Valor en Riesgo (VaR) y CVaR")
 
    col1, col2, col3 = st.columns(3)
    ticker  = col1.selectbox("Activo", TICKERS,
                             format_func=lambda t: f"{t} — {TICKER_INFO[t]['sector']}")
    cl      = col2.selectbox("Nivel de confianza", CONFIDENCE_LEVELS,
                             format_func=lambda x: f"{x*100:.0f}%", index=1)
    horizon = col3.number_input("Horizonte (días)", 1, 30, 1)
 
    r = rendimientos[ticker].dropna()
    np.random.seed(42)
 
    var_p, cvar_p       = _var_parametrico(r, cl, horizon)
    var_h, cvar_h       = _var_historico(r, cl, horizon)
    var_m, cvar_m, sims = _var_montecarlo(r, cl, horizon)
 
    # ── Tabla comparativa ──────────────────────────────────────────────────────
    st.markdown("### 📊 Comparación de métodos")
    df_comp = pd.DataFrame({
        "Método":    ["Paramétrico (Normal)", "Histórico", "Montecarlo (10K)"],
        "VaR":       [f"{var_p*100:.4f}%",  f"{var_h*100:.4f}%",  f"{var_m*100:.4f}%"],
        "CVaR":      [f"{cvar_p*100:.4f}%", f"{cvar_h*100:.4f}%", f"{cvar_m*100:.4f}%"],
        "Descripción": [
            "Supone distribución normal de retornos",
            "Distribución empírica real del período",
            "10,000 escenarios simulados (Monte Carlo)",
        ],
    })
    st.dataframe(df_comp.set_index("Método"), use_container_width=True)
    st.caption(f"**VaR {cl*100:.0f}%**: pérdida máxima con {cl*100:.0f}% de confianza en {horizon}d. "
               "**CVaR**: pérdida esperada cuando se supera el VaR (peor escenario de cola).")
 
    st.markdown("---")
 
    # ── Distribución con líneas VaR/CVaR ──────────────────────────────────────
    st.markdown("### 📈 Distribución de rendimientos y umbrales de riesgo")
    x_range = np.linspace(r.min(), r.max(), 300) * 100
 
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=r * 100, nbinsx=80, histnorm="probability density",
                               marker_color="#6C63FF", opacity=0.6, name="Rendimientos"))
    fig.add_trace(go.Scatter(x=x_range,
                             y=stats.norm.pdf(x_range, r.mean()*100, r.std()*100),
                             name="Normal teórica", line=dict(color="gray", width=1.5, dash="dot")))
 
    color_map = {"Paramétrico": "#3D008D", "Histórico": "#ED1E79", "Montecarlo": "#FF6B6B"}
    for name, var in [("Paramétrico", var_p), ("Histórico", var_h), ("Montecarlo", var_m)]:
        fig.add_vline(x=-var * 100, line_color=color_map[name], line_dash="dash", line_width=2,
                      annotation_text=f"VaR {name[:4]}", annotation_position="top")
 
    fig.update_layout(template="plotly_white", height=420,
                      title=f"Distribución — {ticker} | CL {cl*100:.0f}% | H={horizon}d",
                      xaxis_title="Rendimiento (%)", yaxis_title="Densidad",
                      legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)
 
    # ── VaR rodante ────────────────────────────────────────────────────────────
    st.markdown("### 📉 VaR histórico rodante")
    window = st.slider("Ventana (días)", 60, 500, 252)
    roll_var = r.rolling(window).apply(lambda x: _var_historico(x, cl)[0], raw=False)
 
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=r.index, y=-r * 100, mode="lines",
                              name="Pérdida diaria", line=dict(color="#6C63FF", width=0.7)))
    fig2.add_trace(go.Scatter(x=roll_var.index, y=roll_var * 100,
                              name=f"VaR {cl*100:.0f}% rodante {window}d",
                              line=dict(color="#ED1E79", width=2)))
    fig2.update_layout(template="plotly_white", height=360,
                       title=f"VaR histórico rodante — {ticker}",
                       xaxis_title="Fecha", yaxis_title="%")
    st.plotly_chart(fig2, use_container_width=True)
 
    # ── Backtesting Kupiec ─────────────────────────────────────────────────────
    st.markdown("### 🔬 Backtesting — Test de Kupiec")
    bt_rows = []
    for mname, var in [("Paramétrico", var_p), ("Histórico", var_h), ("Montecarlo", var_m)]:
        res = _kupiec(r, var, cl)
        bt_rows.append({
            "Método":          mname,
            "N obs.":          res["n"],
            "Excedencias":     res["exc"],
            "Tasa observada":  f"{res['p_hat']*100:.2f}%",
            "Tasa esperada":   f"{(1-cl)*100:.2f}%",
            "LR stat.":        f"{res['lr']:.4f}" if not np.isnan(res["lr"]) else "—",
            "p-valor":         f"{res['p_val']:.4f}" if not np.isnan(res["p_val"]) else "—",
            "Resultado":       ("✅ H₀ no rechazada"
                                if not np.isnan(res.get("p_val", np.nan))
                                   and res["p_val"] > 0.05
                                else "❌ H₀ rechazada"),
        })
    st.dataframe(pd.DataFrame(bt_rows).set_index("Método"), use_container_width=True)
    st.caption("H₀: tasa de excedencias observada = 1 − CL. "
               "p > 0.05 → el modelo calibra correctamente el riesgo.")