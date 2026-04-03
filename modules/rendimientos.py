# ============================================================
# modules/rendimientos.py — Módulo 2: Rendimientos y Estadísticos
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
 
from config import TICKERS, TRADING_DAYS
 
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## 📊 Módulo 2 — Rendimientos y Propiedades Empíricas")
 
    # Rendimientos simples para comparar
    ret_simples = precios[TICKERS].pct_change().dropna()
    ret_log     = rendimientos[TICKERS]
 
    tipo = st.radio("Tipo de rendimiento a analizar",
                    ["Log-rendimientos", "Rendimientos simples"], horizontal=True)
    rets = ret_log if tipo == "Log-rendimientos" else ret_simples
 
    # ── Estadísticos descriptivos ──────────────────────────────────────────────
    st.markdown("### 📋 Estadísticos descriptivos")
    rows = []
    for t in TICKERS:
        r = rets[t].dropna()
        jb_stat, jb_p = stats.jarque_bera(r)
        sw_stat, sw_p = stats.shapiro(r[:5000])
        rows.append({
            "Ticker":     t,
            "Media diaria":  f"{r.mean()*100:.4f}%",
            "Vol. diaria":   f"{r.std()*100:.4f}%",
            "Vol. anual":    f"{r.std()*np.sqrt(TRADING_DAYS)*100:.2f}%",
            "Asimetría":     f"{r.skew():.4f}",
            "Curtosis exc.": f"{r.kurtosis():.4f}",
            "Mín":           f"{r.min()*100:.2f}%",
            "Máx":           f"{r.max()*100:.2f}%",
            "JB p-valor":    f"{jb_p:.4f}",
            "SW p-valor":    f"{sw_p:.4f}",
            "¿Normal?":      "❌ No" if jb_p < 0.05 else "✅ Sí",
        })
 
    st.dataframe(pd.DataFrame(rows).set_index("Ticker"), use_container_width=True)
    st.caption("**JB**: Jarque-Bera · **SW**: Shapiro-Wilk · p < 0.05 → rechazar normalidad.")
 
    st.markdown("---")
 
    # ── Gráficos por activo ────────────────────────────────────────────────────
    ticker = st.selectbox("Activo para visualización detallada", TICKERS)
    r      = rets[ticker].dropna()
 
    tabs = st.tabs(["📊 Histograma", "📈 Serie temporal", "📉 Q-Q Plot", "📦 Boxplot", "🔗 Autocorrelaciones"])
 
    # Histograma
    with tabs[0]:
        x_range  = np.linspace(r.min(), r.max(), 300) * 100
        norm_pdf = stats.norm.pdf(x_range, r.mean() * 100, r.std() * 100)
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=r * 100, nbinsx=80, histnorm="probability density",
                                   name="Rendimientos", marker_color="#6C63FF", opacity=0.7))
        fig.add_trace(go.Scatter(x=x_range, y=norm_pdf, name="Normal teórica",
                                 line=dict(color="#FF6B6B", width=2)))
        fig.update_layout(template="plotly_white", height=400,
                          title=f"Distribución de rendimientos — {ticker}",
                          xaxis_title="Rendimiento (%)", yaxis_title="Densidad")
        st.plotly_chart(fig, use_container_width=True)
 
    # Serie temporal
    with tabs[1]:
        fig2 = go.Figure(go.Scatter(x=r.index, y=r * 100, mode="lines",
                                    line=dict(color="#6C63FF", width=0.8)))
        fig2.update_layout(template="plotly_white", height=380,
                           title=f"Serie de rendimientos — {ticker}",
                           xaxis_title="Fecha", yaxis_title="Rendimiento (%)")
        st.plotly_chart(fig2, use_container_width=True)
 
    # Q-Q Plot
    with tabs[2]:
        (osm, osr), (slope, intercept, _) = stats.probplot(r, dist="norm")
        ly = slope * np.array([osm[0], osm[-1]]) + intercept
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=osm, y=osr, mode="markers", name="Cuantiles empíricos",
                                  marker=dict(color="#6C63FF", size=3, opacity=0.6)))
        fig3.add_trace(go.Scatter(x=[osm[0], osm[-1]], y=ly, mode="lines",
                                  name="Línea normal", line=dict(color="#FF6B6B", width=2)))
        fig3.update_layout(template="plotly_white", height=400,
                           title=f"Q-Q Plot — {ticker}",
                           xaxis_title="Cuantiles teóricos", yaxis_title="Cuantiles empíricos")
        st.plotly_chart(fig3, use_container_width=True)
 
    # Boxplot comparativo
    with tabs[3]:
        fig4 = go.Figure()
        colores = ["#6C63FF", "#00C2CB", "#FF6B6B", "#FFD93D", "#4ECDC4"]
        for i, t in enumerate(TICKERS):
            fig4.add_trace(go.Box(y=rets[t].dropna() * 100, name=t,
                                  marker_color=colores[i % len(colores)], boxmean=True))
        fig4.update_layout(template="plotly_white", height=420,
                           title="Boxplot comparativo de rendimientos (%)",
                           yaxis_title="Rendimiento (%)")
        st.plotly_chart(fig4, use_container_width=True)
 
    # Autocorrelaciones
    with tabs[4]:
        max_lag  = 40
        ci       = 1.96 / np.sqrt(len(r))
        acf_r    = [r.autocorr(k) for k in range(1, max_lag + 1)]
        acf_r2   = [(r**2).autocorr(k) for k in range(1, max_lag + 1)]
        lags     = list(range(1, max_lag + 1))
 
        fig5 = make_subplots(rows=1, cols=2,
                             subplot_titles=["ACF rendimientos", "ACF rendimientos²"])
        for vals, col in [(acf_r, 1), (acf_r2, 2)]:
            fig5.add_trace(go.Bar(x=lags, y=vals, marker_color="#6C63FF", opacity=0.7), row=1, col=col)
            fig5.add_hline(y=ci,  line_dash="dash", line_color="red", row=1, col=col)
            fig5.add_hline(y=-ci, line_dash="dash", line_color="red", row=1, col=col)
        fig5.update_layout(template="plotly_white", height=380,
                           showlegend=False, title=f"Autocorrelaciones — {ticker}")
        st.plotly_chart(fig5, use_container_width=True)
        st.caption("ACF de r² persistente y positiva → evidencia de agrupamiento de volatilidad (ARCH). "
                   "Líneas rojas = intervalo de confianza 95%.")
 
    # ── Hechos estilizados ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 Hechos estilizados")
    kurt     = r.kurtosis()
    skew     = r.skew()
    acf1     = r.autocorr(1)
    acf1_sq  = (r**2).autocorr(1)
 
    st.markdown(f"""
| Hecho estilizado | Evidencia en {ticker} | Conclusión |
|---|---|---|
| **Colas pesadas** | Curtosis exceso = {kurt:.3f} | {"✅ Leptocúrtica" if kurt > 0 else "⚠️ No detectada"} |
| **Asimetría** | Skewness = {skew:.4f} | {"📉 Negativa (caídas más frecuentes)" if skew < 0 else "📈 Positiva"} |
| **Sin autocorrelación** | ACF lag-1 = {acf1:.4f} | {"✅ Mercado eficiente" if abs(acf1) < 0.05 else "⚠️ Posible patrón lineal"} |
| **Clusters de volatilidad** | ACF(r²) lag-1 = {acf1_sq:.4f} | {"✅ Presente → justifica GARCH" if acf1_sq > 0.1 else "⚠️ Débil"} |
    """)