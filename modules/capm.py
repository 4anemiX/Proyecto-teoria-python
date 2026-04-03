# ============================================================
# modules/capm.py — Módulo 4: CAPM y Riesgo Sistemático
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
 
from config import TICKERS, BENCHMARK, TICKER_INFO, TRADING_DAYS
from utils.data_loader import obtener_tasa_libre_riesgo
 
 
def _beta_regression(r_asset: pd.Series, r_market: pd.Series):
    aligned = pd.concat([r_asset, r_market], axis=1).dropna()
    x = aligned.iloc[:, 1].values
    y = aligned.iloc[:, 0].values
    slope, intercept, r_val, p_val, stderr = stats.linregress(x, y)
    return intercept, slope, r_val**2, p_val
 
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## 🎯 Módulo 4 — CAPM y Riesgo Sistemático")
 
    rf_annual = obtener_tasa_libre_riesgo()
    rf_daily  = rf_annual / TRADING_DAYS
 
    bm_ret = rendimientos[BENCHMARK].dropna()
    st.info(f"📌 Tasa libre de riesgo anual (FRED DGS3MO): **{rf_annual*100:.3f}%** | "
            f"Benchmark: **{BENCHMARK}** | Rf diaria: {rf_daily*100:.5f}%")
 
    excess_assets = rendimientos[TICKERS].sub(rf_daily)
    excess_market = bm_ret - rf_daily
 
    # ── Tabla CAPM ────────────────────────────────────────────────────────────
    st.markdown("### 📊 Tabla de parámetros CAPM")
    capm_rows = []
    betas     = {}
 
    for t in TICKERS:
        alpha, beta, r2, p_beta = _beta_regression(excess_assets[t], excess_market)
        ann_alpha   = alpha * TRADING_DAYS
        exp_return  = rf_annual + beta * (bm_ret.mean() * TRADING_DAYS - rf_annual)
        real_return = rendimientos[t].mean() * TRADING_DAYS
        betas[t]    = beta
 
        capm_rows.append({
            "Ticker":            t,
            "Sector":            TICKER_INFO[t]["sector"],
            "Beta (β)":          round(beta, 4),
            "p-valor β":         f"{p_beta:.4f}",
            "Alpha Jensen (α)":  f"{ann_alpha*100:.3f}%",
            "R²":                f"{r2:.4f}",
            "E[R] CAPM":         f"{exp_return*100:.2f}%",
            "R real anual":      f"{real_return*100:.2f}%",
            "Tipo":              "🔵 Defensivo" if beta < 1 else "🔴 Agresivo",
        })
 
    df_capm = pd.DataFrame(capm_rows).set_index("Ticker")
    st.dataframe(df_capm, use_container_width=True)
    st.caption("**β < 1**: menor sensibilidad que el mercado · **β > 1**: amplifica movimientos · "
               "**Alpha > 0**: retorno por encima del CAPM.")
 
    st.markdown("---")
 
    # ── Dispersión + regresión por activo ─────────────────────────────────────
    ticker = st.selectbox("Activo para gráfico de dispersión", TICKERS)
    alpha_t, beta_t, r2_t, _ = _beta_regression(excess_assets[ticker], excess_market)
 
    aligned = pd.concat([excess_assets[ticker], excess_market], axis=1).dropna()
    x_vals  = aligned.iloc[:, 1].values
    y_vals  = aligned.iloc[:, 0].values
    x_line  = np.linspace(x_vals.min(), x_vals.max(), 200)
    y_line  = alpha_t + beta_t * x_line
 
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_vals * 100, y=y_vals * 100, mode="markers",
                             name="Observaciones",
                             marker=dict(size=4, color="#6C63FF", opacity=0.4)))
    fig.add_trace(go.Scatter(x=x_line * 100, y=y_line * 100, mode="lines",
                             name=f"β={beta_t:.3f} | α={alpha_t*TRADING_DAYS*100:.3f}%/año",
                             line=dict(color="#ED1E79", width=2.5)))
    fig.update_layout(template="plotly_white", height=420,
                      title=f"Regresión CAPM — {ticker} vs {BENCHMARK}",
                      xaxis_title=f"Exceso mercado ({BENCHMARK}) %",
                      yaxis_title=f"Exceso retorno ({ticker}) %")
    st.plotly_chart(fig, use_container_width=True)
 
    c1, c2, c3 = st.columns(3)
    c1.metric("Beta (β)", f"{beta_t:.4f}")
    c2.metric("Alpha Jensen (anual)", f"{alpha_t * TRADING_DAYS * 100:.3f}%")
    c3.metric("R²", f"{r2_t:.4f}", f"Riesgo sist.: {r2_t*100:.1f}%")
 
    # ── Descomposición de riesgo ───────────────────────────────────────────────
    st.markdown("### 📌 Descomposición del riesgo total")
    bm_var = excess_market.var()
    risk_rows = []
    for t in TICKERS:
        tot_var  = rendimientos[t].var()
        sys_var  = (betas[t] ** 2) * bm_var
        idio_var = max(tot_var - sys_var, 0)
        risk_rows.append({
            "Ticker":              t,
            "Var. total (×252)":   f"{tot_var*TRADING_DAYS:.6f}",
            "Var. sistemática":    f"{sys_var*TRADING_DAYS:.6f}",
            "Var. idiosincrática": f"{idio_var*TRADING_DAYS:.6f}",
            "% Sistemático":       f"{min(sys_var/tot_var*100,100):.1f}%",
        })
    st.dataframe(pd.DataFrame(risk_rows).set_index("Ticker"), use_container_width=True)
 
    # ── SML ───────────────────────────────────────────────────────────────────
    st.markdown("### 📈 Línea del Mercado de Valores (SML)")
    mkt_premium = bm_ret.mean() * TRADING_DAYS - rf_annual
    beta_range  = np.linspace(0, 2.5, 100)
 
    fig_sml = go.Figure()
    fig_sml.add_trace(go.Scatter(x=beta_range, y=(rf_annual + beta_range * mkt_premium) * 100,
                                 mode="lines", name="SML",
                                 line=dict(color="gray", width=2)))
    for row in capm_rows:
        t    = row["Ticker"]
        b    = row["Beta (β)"]
        real = float(row["R real anual"].strip("%"))
        exp  = float(row["E[R] CAPM"].strip("%"))
        col  = "#4ECDC4" if real >= exp else "#FF6B6B"
        fig_sml.add_trace(go.Scatter(x=[b], y=[real],
                                     mode="markers+text", text=[t],
                                     textposition="top center",
                                     marker=dict(size=14, color=col),
                                     showlegend=False))
    fig_sml.add_hline(y=rf_annual * 100, line_dash="dot", line_color="#6C63FF",
                      annotation_text=f"Rf = {rf_annual*100:.2f}%")
    fig_sml.update_layout(template="plotly_white", height=420,
                          title="SML — Retorno real vs. predicho por CAPM",
                          xaxis_title="Beta (β)", yaxis_title="Retorno anual (%)")
    st.plotly_chart(fig_sml, use_container_width=True)
    st.caption("🟢 Por encima de la SML → alpha positivo (outperformance). "
               "🔴 Por debajo → rendimiento inferior al requerido por el mercado.")