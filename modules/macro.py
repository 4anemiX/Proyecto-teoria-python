# ============================================================
# modules/macro.py — Módulo 8 ⭐: Macro y Benchmark
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
 
from config import TICKERS, BENCHMARK, TICKER_INFO, TRADING_DAYS
from utils.data_loader import obtener_tasa_libre_riesgo, obtener_datos_macro
 
 
# ── Métricas de desempeño ─────────────────────────────────────────────────────
 
def _alpha_jensen(r_p, r_bm, rf_d):
    ex_p  = r_p - rf_d
    ex_bm = r_bm - rf_d
    aligned = pd.concat([ex_p, ex_bm], axis=1).dropna()
    slope, intercept, *_ = stats.linregress(aligned.iloc[:,1], aligned.iloc[:,0])
    return float(intercept * TRADING_DAYS)
 
def _tracking_error(r_p, r_bm):
    diff = (r_p - r_bm).dropna()
    return float(diff.std() * np.sqrt(TRADING_DAYS))
 
def _information_ratio(r_p, r_bm):
    diff = (r_p - r_bm).dropna()
    te   = diff.std() * np.sqrt(TRADING_DAYS)
    al   = diff.mean() * TRADING_DAYS
    return float(al / te) if te > 0 else 0.0
 
def _sharpe(r, rf):
    ann_r = r.mean() * TRADING_DAYS
    ann_v = r.std() * np.sqrt(TRADING_DAYS)
    return float((ann_r - rf) / ann_v) if ann_v > 0 else 0.0
 
def _max_dd(cum_prices):
    peak = cum_prices.cummax()
    return float(((cum_prices - peak) / peak).min() * 100)
 
 
# ── Render ────────────────────────────────────────────────────────────────────
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## 🌐 Módulo 8 — Contexto Macro y Benchmark ⭐")
 
    rf_annual = obtener_tasa_libre_riesgo()
    rf_daily  = rf_annual / TRADING_DAYS
 
    with st.spinner("Cargando datos macroeconómicos (FRED)…"):
        macro = obtener_datos_macro()
 
    # ── KPIs macro ────────────────────────────────────────────────────────────
    st.markdown("### 📡 Indicadores macroeconómicos (FRED)")
    c1, c2, c3 = st.columns(3)
    c1.metric("T-Bill 3M (Rf anual)", f"{rf_annual*100:.3f}%", "Fuente: FRED DGS3MO")
 
    if "inflation" in macro and not macro["inflation"].empty:
        infl = macro["inflation"].dropna().pct_change(12).dropna()
        c2.metric("Inflación interanual (CPI)", f"{infl.iloc[-1]*100:.2f}%", "Fuente: FRED CPIAUCSL")
    else:
        c2.metric("Inflación (CPI)", "N/D", "Configura FRED_API_KEY")
 
    if "vix" in macro and not macro["vix"].empty:
        vix = macro["vix"].dropna()
        c3.metric("VIX (volatilidad mercado)", f"{vix.iloc[-1]:.2f}",
                  f"Promedio 1A: {vix.tail(252).mean():.2f}")
    else:
        c3.metric("VIX", "N/D", "Configura FRED_API_KEY")
 
    # Gráficos macro
    if macro:
        tabs_macro = st.tabs(["T-Bill 3M", "Inflación YoY", "VIX"])
        series_map = [
            ("rf_rate",    "T-Bill 3M (%)", "#3D008D", None),
            ("inflation",  "Inflación YoY (%)", "#ED1E79", 12),
            ("vix",        "VIX", "#FF6B6B", None),
        ]
        for tab, (key, title, color, pct_periods) in zip(tabs_macro, series_map):
            with tab:
                if key in macro and not macro[key].empty:
                    s = macro[key].dropna()
                    if pct_periods:
                        s = s.pct_change(pct_periods).dropna() * 100
                    fig = go.Figure(go.Scatter(x=s.index, y=s,
                                              line=dict(color=color, width=1.5)))
                    if key == "inflation":
                        fig.add_hline(y=2, line_dash="dot", annotation_text="Meta Fed 2%")
                    fig.update_layout(template="plotly_white", height=300,
                                      title=title, yaxis_title="%")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Configura FRED_API_KEY en .env para ver esta gráfica.")
 
    st.markdown("---")
 
    # ── Rendimiento acumulado vs. benchmark ───────────────────────────────────
    st.markdown(f"### 📈 Rendimiento acumulado vs. {BENCHMARK}")
    bm_ret = rendimientos[BENCHMARK].dropna()
    common = rendimientos[TICKERS].dropna().index.intersection(bm_ret.index)
 
    bm_cum = (1 + bm_ret.reindex(common)).cumprod() - 1
 
    colores = ["#6C63FF", "#00C2CB", "#FF6B6B", "#FFD93D", "#4ECDC4"]
    fig_cum = go.Figure()
    for i, t in enumerate(TICKERS):
        r_t   = rendimientos[t].reindex(common).dropna()
        cum_t = (1 + r_t).cumprod() - 1
        fig_cum.add_trace(go.Scatter(x=cum_t.index, y=cum_t*100,
                                      name=t, line=dict(color=colores[i], width=1.8)))
    fig_cum.add_trace(go.Scatter(x=bm_cum.index, y=bm_cum*100,
                                  name=f"{BENCHMARK} (benchmark)",
                                  line=dict(color="black", width=2, dash="dash")))
    fig_cum.update_layout(template="plotly_white", height=420,
                           title="Rendimiento acumulado (%)",
                           xaxis_title="Fecha", yaxis_title="%",
                           legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig_cum, use_container_width=True)
 
    # ── Tabla de desempeño ─────────────────────────────────────────────────────
    st.markdown("### 📊 Tabla de desempeño relativo")
    rows = []
 
    # Benchmark
    bm_r   = bm_ret.reindex(common)
    bm_cum_p = (1 + bm_r).cumprod()
    rows.append({
        "Activo":         BENCHMARK,
        "Sector":         "Benchmark",
        "Ret. anual":     f"{bm_r.mean()*TRADING_DAYS*100:.2f}%",
        "Vol. anual":     f"{bm_r.std()*np.sqrt(TRADING_DAYS)*100:.2f}%",
        "Sharpe":         f"{_sharpe(bm_r, rf_annual):.4f}",
        "Max Drawdown":   f"{_max_dd(bm_cum_p):.2f}%",
        "Alpha Jensen":   "—",
        "Tracking Error": "—",
        "Info. Ratio":    "—",
    })
 
    for t in TICKERS:
        r_t   = rendimientos[t].reindex(common).dropna()
        bm_t  = bm_r.reindex(r_t.index)
        p_t   = (1 + r_t).cumprod()
        rows.append({
            "Activo":         t,
            "Sector":         TICKER_INFO[t]["sector"],
            "Ret. anual":     f"{r_t.mean()*TRADING_DAYS*100:.2f}%",
            "Vol. anual":     f"{r_t.std()*np.sqrt(TRADING_DAYS)*100:.2f}%",
            "Sharpe":         f"{_sharpe(r_t, rf_annual):.4f}",
            "Max Drawdown":   f"{_max_dd(p_t):.2f}%",
            "Alpha Jensen":   f"{_alpha_jensen(r_t, bm_t, rf_daily)*100:.3f}%",
            "Tracking Error": f"{_tracking_error(r_t, bm_t)*100:.3f}%",
            "Info. Ratio":    f"{_information_ratio(r_t, bm_t):.4f}",
        })
 
    st.dataframe(pd.DataFrame(rows).set_index("Activo"), use_container_width=True)
    st.caption("**Alpha de Jensen**: exceso de retorno sobre el CAPM · "
               "**Tracking Error**: desviación vs. benchmark · "
               "**IR > 0.5**: gestión activa efectiva.")
 
    # ── Correlación rodante vs. benchmark ─────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 🔗 Correlación rodante vs. {BENCHMARK}")
    col_t  = st.selectbox("Activo", TICKERS, key="macro_corr")
    w_corr = st.slider("Ventana (días)", 30, 252, 60)
 
    r_ct   = rendimientos[col_t].reindex(common).dropna()
    bm_ct  = bm_r.reindex(r_ct.index)
    roll_c = r_ct.rolling(w_corr).corr(bm_ct)
 
    fig_c = go.Figure(go.Scatter(x=roll_c.index, y=roll_c,
                                  line=dict(color="#6C63FF", width=1.5)))
    fig_c.add_hline(y=0, line_dash="dot", line_color="gray")
    fig_c.update_layout(template="plotly_white", height=320,
                        title=f"Correlación rodante {col_t} vs {BENCHMARK} — {w_corr}d",
                        xaxis_title="Fecha", yaxis_title="Correlación",
                        yaxis_range=[-1, 1])
    st.plotly_chart(fig_c, use_container_width=True)
    st.caption("Correlación alta con el benchmark → menor diversificación respecto al mercado.")