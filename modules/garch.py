# ============================================================
# modules/garch.py — Módulo 3: Modelos ARCH/GARCH
# ============================================================
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
 
from config import TICKERS, TICKER_INFO, TRADING_DAYS
 
 
def _fit_garch(returns: pd.Series, p: int, q: int, dist: str = "t"):
    try:
        from arch import arch_model
        model = arch_model(returns * 100, vol="Garch", p=p, q=q, dist=dist)
        return model.fit(disp="off")
    except Exception as e:
        st.error(f"Error ajustando GARCH({p},{q}): {e}")
        return None
 
 
def render(precios: pd.DataFrame, rendimientos: pd.DataFrame):
    st.markdown("## 🌊 Módulo 3 — Modelos ARCH/GARCH")
    st.caption("Modelado de volatilidad condicional: ajuste, comparación y pronóstico.")
 
    ticker = st.selectbox("Activo", TICKERS,
                          format_func=lambda t: f"{t} — {TICKER_INFO[t]['sector']}")
    r = rendimientos[ticker].dropna()
 
    col1, col2, col3 = st.columns(3)
    dist    = col1.selectbox("Distribución de errores", ["normal", "t", "skewt"], index=1)
    h       = col2.number_input("Horizonte pronóstico (días)", 1, 60, 10)
    roll_w  = col3.number_input("Ventana vol. rodante", 20, 120, 30)
 
    # ── Ajuste de 3 especificaciones ──────────────────────────────────────────
    specs = [("ARCH(1)", 1, 0), ("GARCH(1,1)", 1, 1), ("GARCH(2,1)", 2, 1)]
    results = {}
    with st.spinner("Ajustando modelos GARCH…"):
        for name, p, q in specs:
            res = _fit_garch(r, p, q, dist)
            if res is not None:
                results[name] = res
 
    if not results:
        st.error("No se pudo ajustar ningún modelo.")
        return
 
    # ── Tabla comparativa AIC/BIC ──────────────────────────────────────────────
    st.markdown("### 📊 Comparación de especificaciones")
    comp = [{"Modelo": n, "Log-verosimilitud": f"{res.loglikelihood:.2f}",
             "AIC": f"{res.aic:.2f}", "BIC": f"{res.bic:.2f}"}
            for n, res in results.items()]
    best_name = min(results, key=lambda k: results[k].aic)
    st.dataframe(pd.DataFrame(comp).set_index("Modelo"), use_container_width=True)
    st.success(f"✅ Mejor modelo por AIC: **{best_name}**")
 
    best = results[best_name]
 
    # ── Parámetros ────────────────────────────────────────────────────────────
    st.markdown(f"### ⚙️ Parámetros estimados — {best_name}")
    df_p = pd.DataFrame({
        "Parámetro":  best.params.index,
        "Estimado":   best.params.values.round(6),
        "Std. Error": best.std_err.values.round(6),
        "p-valor":    best.pvalues.values.round(4),
        "Sig.":       ["✅" if p < 0.05 else "⚠️" for p in best.pvalues],
    })
    st.dataframe(df_p.set_index("Parámetro"), use_container_width=True)
 
    # ── Volatilidad condicional ────────────────────────────────────────────────
    st.markdown("### 📈 Volatilidad condicional vs. rodante")
    cond_vol = best.conditional_volatility
    roll_vol = r.rolling(roll_w).std() * np.sqrt(TRADING_DAYS) * 100
 
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.45, 0.55], vertical_spacing=0.04,
                        subplot_titles=[f"Rendimientos — {ticker}",
                                        "Volatilidad condicional GARCH vs. rodante"])
    fig.add_trace(go.Scatter(x=r.index, y=r * 100, name="Rendimiento",
                             line=dict(color="#6C63FF", width=0.8)), row=1, col=1)
    fig.add_trace(go.Scatter(x=cond_vol.index, y=cond_vol, name=f"Vol. condicional ({best_name})",
                             line=dict(color="#ED1E79", width=1.8)), row=2, col=1)
    fig.add_trace(go.Scatter(x=roll_vol.index, y=roll_vol, name=f"Vol. rodante {roll_w}d",
                             line=dict(color="orange", width=1.2, dash="dash")), row=2, col=1)
    fig.update_layout(template="plotly_white", height=520,
                      legend=dict(orientation="h", y=1.02),
                      margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)
 
    # ── Diagnóstico de residuos ────────────────────────────────────────────────
    st.markdown("### 🔬 Diagnóstico de residuos estandarizados")
    std_resid = best.std_resid.dropna()
 
    col_a, col_b = st.columns(2)
    with col_a:
        x_r = np.linspace(std_resid.min(), std_resid.max(), 300)
        fig_r = go.Figure()
        fig_r.add_trace(go.Histogram(x=std_resid, nbinsx=60, histnorm="probability density",
                                      marker_color="#6C63FF", opacity=0.7, name="Residuos"))
        fig_r.add_trace(go.Scatter(x=x_r, y=stats.norm.pdf(x_r), name="N(0,1)",
                                    line=dict(color="#FF6B6B", width=2)))
        fig_r.update_layout(template="plotly_white", height=320, title="Distribución residuos")
        st.plotly_chart(fig_r, use_container_width=True)
 
    with col_b:
        (osm, osr), (slope, intercept, _) = stats.probplot(std_resid, dist="norm")
        ly = slope * np.array([osm[0], osm[-1]]) + intercept
        fig_qq = go.Figure()
        fig_qq.add_trace(go.Scatter(x=osm, y=osr, mode="markers",
                                    marker=dict(size=3, color="#6C63FF", opacity=0.7)))
        fig_qq.add_trace(go.Scatter(x=[osm[0], osm[-1]], y=ly, mode="lines",
                                    line=dict(color="#FF6B6B", width=2), name="Normal"))
        fig_qq.update_layout(template="plotly_white", height=320, title="Q-Q residuos")
        st.plotly_chart(fig_qq, use_container_width=True)
 
    jb_stat, jb_p = stats.jarque_bera(std_resid)
    st.metric("Jarque-Bera p-valor (residuos)", f"{jb_p:.4f}",
              "✅ Residuos aceptables" if jb_p > 0.05 else "⚠️ Considera distribución-t o skewt")
 
    # ── Pronóstico ────────────────────────────────────────────────────────────
    st.markdown(f"### 🔮 Pronóstico de volatilidad — próximos {h} días")
    try:
        forecast  = best.forecast(horizon=h, reindex=False)
        fcast_vol = np.sqrt(forecast.variance.iloc[-1].values) * np.sqrt(TRADING_DAYS)
        days      = list(range(1, h + 1))
 
        fig_f = go.Figure(go.Scatter(x=days, y=fcast_vol, mode="lines+markers",
                                     line=dict(color="#3D008D", width=2),
                                     marker=dict(size=6)))
        fig_f.update_layout(template="plotly_white", height=340,
                            title=f"Volatilidad anualizada pronosticada — {best_name}",
                            xaxis_title="Días hacia adelante",
                            yaxis_title="Volatilidad anualizada (%)")
        st.plotly_chart(fig_f, use_container_width=True)
 
        last_vol = cond_vol.iloc[-1]
        st.info(f"📌 Volatilidad condicional actual: **{last_vol:.3f}%** diaria | "
                f"Anualizada ≈ **{last_vol * np.sqrt(TRADING_DAYS):.2f}%**")
    except Exception as e:
        st.warning(f"No se pudo generar el pronóstico: {e}")