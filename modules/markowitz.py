# ============================================================
# modules/markowitz.py — Módulo 6: Optimización Markowitz
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.optimize import minimize
 
from config import TICKERS, TRADING_DAYS
from utils.data_loader import obtener_tasa_libre_riesgo
 
 
def _stats(w, mu, cov, rf):
    ret = w @ mu * TRADING_DAYS
    vol = np.sqrt(w @ cov @ w * TRADING_DAYS)
    sr  = (ret - rf) / vol if vol > 0 else 0
    return ret, vol, sr
 
def _min_var(mu, cov, n):
    res = minimize(lambda w: w @ cov @ w * TRADING_DAYS,
                   np.ones(n)/n, method="SLSQP",
                   bounds=[(0,1)]*n,
                   constraints=[{"type":"eq","fun":lambda w: w.sum()-1}])
    return res.x if res.success else np.ones(n)/n
 
def _max_sharpe(mu, cov, rf, n):
    def neg_sr(w):
        r = w @ mu * TRADING_DAYS
        v = np.sqrt(w @ cov @ w * TRADING_DAYS)
        return -(r - rf)/v if v > 0 else 0
    res = minimize(neg_sr, np.ones(n)/n, method="SLSQP",
                   bounds=[(0,1)]*n,
                   constraints=[{"type":"eq","fun":lambda w: w.sum()-1}])
    return res.x if res.success else np.ones(n)/n
 
def _target_ret(mu, cov, target, n):
    res = minimize(lambda w: w @ cov @ w * TRADING_DAYS,
                   np.ones(n)/n, method="SLSQP",
                   bounds=[(0,1)]*n,
                   constraints=[
                       {"type":"eq","fun":lambda w: w.sum()-1},
                       {"type":"eq","fun":lambda w: w @ mu * TRADING_DAYS - target},
                   ])
    return res.x if res.success else None
 
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## ⚖️ Módulo 6 — Optimización de Portafolio (Markowitz)")
 
    n   = len(TICKERS)
    rf  = obtener_tasa_libre_riesgo()
    mu  = rendimientos[TICKERS].mean().values
    cov = rendimientos[TICKERS].cov().values
 
    st.info(f"📌 Rf anual: **{rf*100:.3f}%** | Activos: {', '.join(TICKERS)}")
 
    # ── Heatmap de correlación ─────────────────────────────────────────────────
    st.markdown("### 🌡️ Heatmap de correlación")
    corr = rendimientos[TICKERS].corr()
    fig_c = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                      zmin=-1, zmax=1, aspect="auto")
    fig_c.update_layout(template="plotly_white", height=360,
                        margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_c, use_container_width=True)
    st.caption("Correlación baja entre activos → mayor beneficio de diversificación.")
 
    st.markdown("---")
 
    # ── Frontera eficiente ────────────────────────────────────────────────────
    st.markdown("### 🎯 Frontera eficiente")
    n_sim = 12_000
    np.random.seed(42)
 
    with st.spinner(f"Simulando {n_sim:,} portafolios…"):
        rets_sim = np.zeros(n_sim)
        vols_sim = np.zeros(n_sim)
        srs_sim  = np.zeros(n_sim)
 
        for i in range(n_sim):
            w = np.random.dirichlet(np.ones(n))
            r_, v_, s_ = _stats(w, mu, cov, rf)
            rets_sim[i] = r_
            vols_sim[i] = v_
            srs_sim[i]  = s_
 
        w_mv = _min_var(mu, cov, n)
        w_ms = _max_sharpe(mu, cov, rf, n)
        ret_mv, vol_mv, sr_mv = _stats(w_mv, mu, cov, rf)
        ret_ms, vol_ms, sr_ms = _stats(w_ms, mu, cov, rf)
 
    fig_fe = go.Figure()
    fig_fe.add_trace(go.Scatter(
        x=vols_sim * 100, y=rets_sim * 100, mode="markers",
        name="Portafolios simulados",
        marker=dict(size=3, color=srs_sim, colorscale="Viridis",
                    showscale=True, colorbar=dict(title="Sharpe"), opacity=0.5),
    ))
 
    # Activos individuales
    colores_act = ["#6C63FF", "#00C2CB", "#FF6B6B", "#FFD93D", "#4ECDC4"]
    for i, t in enumerate(TICKERS):
        r_t = rendimientos[t]
        fig_fe.add_trace(go.Scatter(
            x=[r_t.std() * np.sqrt(TRADING_DAYS) * 100],
            y=[r_t.mean() * TRADING_DAYS * 100],
            mode="markers+text", text=[t], textposition="top center",
            marker=dict(size=12, symbol="diamond", color=colores_act[i % len(colores_act)]),
            showlegend=False,
        ))
 
    fig_fe.add_trace(go.Scatter(
        x=[vol_mv*100], y=[ret_mv*100], mode="markers+text",
        text=["Mín. Var."], textposition="top right",
        marker=dict(size=16, symbol="star", color="#00C2CB"),
        name=f"Mín. Varianza (Sharpe={sr_mv:.3f})",
    ))
    fig_fe.add_trace(go.Scatter(
        x=[vol_ms*100], y=[ret_ms*100], mode="markers+text",
        text=["Máx. Sharpe"], textposition="top right",
        marker=dict(size=16, symbol="star", color="#ED1E79"),
        name=f"Máx. Sharpe ({sr_ms:.3f})",
    ))
    fig_fe.update_layout(template="plotly_white", height=500,
                         title=f"Frontera eficiente — {n_sim:,} portafolios simulados",
                         xaxis_title="Volatilidad anual (%)",
                         yaxis_title="Retorno anual (%)",
                         legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig_fe, use_container_width=True)
 
    # ── Pesos óptimos ─────────────────────────────────────────────────────────
    st.markdown("### ⚖️ Composición de portafolios óptimos")
    col1, col2 = st.columns(2)
 
    for col, label, w, ret, vol, sr in [
        (col1, "Mínima Varianza", w_mv, ret_mv, vol_mv, sr_mv),
        (col2, "Máximo Sharpe",   w_ms, ret_ms, vol_ms, sr_ms),
    ]:
        with col:
            st.markdown(f"**{label}**")
            df_w = pd.DataFrame({"Ticker": TICKERS, "Peso (%)": (w*100).round(2)})
            df_w = df_w[df_w["Peso (%)"] > 0.01].sort_values("Peso (%)", ascending=False)
            fig_p = go.Figure(go.Pie(labels=df_w["Ticker"], values=df_w["Peso (%)"], hole=0.35))
            fig_p.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(df_w.set_index("Ticker"), use_container_width=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Retorno", f"{ret*100:.2f}%")
            c2.metric("Volatilidad", f"{vol*100:.2f}%")
            c3.metric("Sharpe", f"{sr:.4f}")
 
    # ── Retorno objetivo ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🎛️ Portafolio con retorno objetivo")
    target = st.slider("Retorno objetivo anual (%)",
                       float(rets_sim.min()*100), float(rets_sim.max()*100),
                       float(ret_mv*100), step=0.1)
    w_t = _target_ret(mu, cov, target / 100, n)
    if w_t is not None:
        r_t, v_t, s_t = _stats(w_t, mu, cov, rf)
        ca, cb, cc = st.columns(3)
        ca.metric("Retorno alcanzable", f"{r_t*100:.2f}%")
        cb.metric("Volatilidad", f"{v_t*100:.2f}%")
        cc.metric("Sharpe", f"{s_t:.4f}")
        df_wt = pd.DataFrame({"Peso (%)": (w_t*100).round(2)}, index=TICKERS)
        st.dataframe(df_wt[df_wt["Peso (%)"] > 0.01].sort_values("Peso (%)", ascending=False),
                     use_container_width=True)
    else:
        st.info("Retorno objetivo fuera del rango factible. Ajusta el deslizador.")