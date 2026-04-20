import streamlit as st
import plotly.graph_objects as go
import numpy as np
from data.client import fetch_var, fetch_rendimientos, TICKERS
from utils.theme import ticker_color, COLORS


def _interpret_var(data: dict, ticker: str, confidence: float) -> tuple[str, str]:
    vp = data["var_parametric"] * 100
    vh = data["var_historical"] * 100
    vm = data["var_montecarlo"] * 100
    cvar = data["cvar"] * 100
    kupiec_ok = data["kupiec_pval"] > 0.05

    spread = max(vp, vh, vm) - min(vp, vh, vm)
    consensus = np.mean([vp, vh, vm])

    msg = (
        f"Con un nivel de confianza del <strong>{confidence*100:.0f}%</strong>, "
        f"el portafolio de {ticker} tiene un VaR consenso de <strong>{consensus:.3f}%</strong> diario. "
    )

    if spread < 0.1:
        msg += "Los tres métodos convergen — alta consistencia del estimador. "
        css = "positive"
    else:
        msg += f"Divergencia de {spread:.3f}pp entre métodos — el VaR histórico captura mejor colas no normales. "
        css = "warning"

    msg += (
        f"El CVaR (Expected Shortfall) de <strong>{cvar:.3f}%</strong> indica la pérdida promedio "
        f"en los peores escenarios — siempre mayor al VaR. "
    )

    if kupiec_ok:
        msg += f"El test de Kupiec valida el modelo (p={data['kupiec_pval']:.4f} > 0.05) — el número de excepciones es estadísticamente aceptable."
    else:
        msg += f"El test de Kupiec rechaza el modelo (p={data['kupiec_pval']:.4f} < 0.05) — revisar los supuestos distribucionales."
        css = "negative"

    return msg, css


def render():
    st.markdown("""
    <div class="section-title">VaR & CVaR</div>
    <div class="section-subtitle">Value at Risk paramétrico, histórico y Montecarlo — Expected Shortfall y backtesting de Kupiec</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    ticker = col1.selectbox("Activo", TICKERS)
    confidence = col2.slider("Nivel de confianza", 0.90, 0.99, 0.95, 0.01, format="%.2f")
    simulations = col3.select_slider("Simulaciones Montecarlo", [1000, 5000, 10000, 50000], 10000)

    with st.spinner("Calculando VaR..."):
        data = fetch_var(ticker, confidence, simulations)
    if not data:
        st.warning("No se pudieron calcular los modelos VaR.")
        return

    color = ticker_color(ticker)

    # ── Tarjetas VaR ──
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    var_items = [
        ("VaR Paramétrico", data["var_parametric"], COLORS["negative"], c1),
        ("VaR Histórico", data["var_historical"], COLORS["warning"], c2),
        ("VaR Montecarlo", data["var_montecarlo"], "#A78BFA", c3),
        ("CVaR (ES)", data["cvar"], "#F43F5E", c4),
    ]
    for label, val, col_c, col in var_items:
        with col:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{col_c};">
                <div class="metric-value" style="color:{col_c}; font-size:1.3rem;">{val*100:.3f}%</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2 = st.columns(2)
    kupiec_ok = data["kupiec_pval"] > 0.05
    kupiec_color = COLORS["positive"] if kupiec_ok else COLORS["negative"]
    with k1:
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{kupiec_color};">
            <div class="metric-value" style="color:{kupiec_color}; font-size:1.2rem;">{data['kupiec_stat']:.4f}</div>
            <div class="metric-label">Kupiec LR Estadístico</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{kupiec_color};">
            <div class="metric-value" style="color:{kupiec_color}; font-size:1.2rem;">{data['kupiec_pval']:.4f}</div>
            <div class="metric-label">Kupiec p-valor</div>
            <div class="metric-change" style="color:{kupiec_color};">{"Modelo válido" if kupiec_ok else "Revisar modelo"}</div>
        </div>
        """, unsafe_allow_html=True)

    # Interpretación
    interp_msg, interp_class = _interpret_var(data, ticker, confidence)
    st.markdown(f'<div class="interpretation-box {interp_class}" style="margin-top:16px;">{interp_msg}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Distribución con VaR ──
    ret_data = fetch_rendimientos(ticker)
    if ret_data:
        rets = [r for r in ret_data["logaritmicos"] if r is not None]
        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=rets, nbinsx=80, name="Rendimientos",
            marker_color=color, opacity=0.55,
            hovertemplate="Rendimiento: %{x:.4f}<br>Frecuencia: %{y}<extra></extra>"
        ))

        var_lines = [
            (data["var_parametric"], "VaR Param.", COLORS["negative"]),
            (data["var_historical"], "VaR Hist.", COLORS["warning"]),
            (data["var_montecarlo"], "VaR MC", "#A78BFA"),
            (data["cvar"], "CVaR", "#F43F5E"),
        ]
        for val, label, lcolor in var_lines:
            fig.add_vline(
                x=val, line_dash="dot", line_color=lcolor, line_width=1.5,
                annotation_text=label,
                annotation_font=dict(size=10, color=lcolor),
                annotation_position="top right"
            )

        fig.update_layout(
            height=380,
            title=f"Distribución de rendimientos y umbrales de pérdida — {ticker} ({confidence*100:.0f}%)",
            hovermode="x"
        )
        st.plotly_chart(fig, use_container_width=True)