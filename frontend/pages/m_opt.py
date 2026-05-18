import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_opcion, fetch_opcion_curvas, TICKERS
from utils.theme import COLORS


def render():
    st.markdown("""
    <div class="section-title">Opciones Europeas — Black-Scholes</div>
    <div class="section-subtitle">Valoración · Greeks · Paridad put-call · Volatilidad implícita</div>
    """, unsafe_allow_html=True)

    # ── Parámetros ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    S     = col1.number_input("Precio subyacente (S)", 1.0, 10000.0, 100.0, 1.0)
    K     = col2.number_input("Strike (K)", 1.0, 10000.0, 100.0, 1.0)
    T     = col3.slider("Tiempo al vencimiento (años)", 0.01, 5.0, 1.0, 0.01)
    r     = col4.slider("Tasa libre de riesgo (%)", 0.0, 20.0, 5.0, 0.25) / 100
    sigma = col5.slider("Volatilidad σ (%)", 1.0, 150.0, 20.0, 1.0) / 100
    tipo  = col6.selectbox("Tipo", ["call", "put"])

    market_price = st.number_input(
        "Precio de mercado (opcional — para vol. implícita)",
        min_value=0.0, value=0.0, step=0.01,
        help="Deja en 0 para omitir el cálculo de volatilidad implícita",
    )
    market_price_val = market_price if market_price > 0 else None

    with st.spinner("Valorando opción..."):
        data   = fetch_opcion(S, K, T, r, sigma, tipo, market_price_val)
        curvas = fetch_opcion_curvas(S, K, T, r, sigma, tipo)

    if not data:
        st.warning("Error al valorar la opción.")
        return

    # ── Métricas principales ───────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Precio {tipo.upper()}", f"${data['price']:.4f}")
    col2.metric("d₁", f"{data['d1']:.4f}")
    col3.metric("d₂", f"{data['d2']:.4f}")

    # ── Greeks ────────────────────────────────────────────────────────────────
    st.markdown("#### Greeks")
    g = data["greeks"]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Δ Delta",  f"{g['delta']:.4f}")
    col2.metric("Γ Gamma",  f"{g['gamma']:.6f}")
    col3.metric("ν Vega",   f"{g['vega']:.4f}")
    col4.metric("Θ Theta",  f"{g['theta']:.4f}")
    col5.metric("ρ Rho",    f"{g['rho']:.4f}")

    with st.expander("Interpretación de las Greeks"):
        for greek, interp in g.get("interpretation", {}).items():
            st.markdown(f"**{greek}**: {interp}")

    # ── Paridad put-call ───────────────────────────────────────────────────────
    parity = data.get("parity", {})
    if parity:
        ok = parity.get("holds", False)
        color = COLORS["positive"] if ok else COLORS["negative"]
        label = "✅ Paridad put-call verificada" if ok else "⚠️ Paridad put-call no verificada"
        st.markdown(
            f"<div class='insight-box' style='border-color:{color}'><strong>{label}</strong><br>"
            f"LHS (C − P): {parity.get('lhs', 0):.4f} | RHS (S − Ke⁻ʳᵀ): {parity.get('rhs', 0):.4f} | "
            f"Error: {parity.get('diff', 0):.6f}</div>",
            unsafe_allow_html=True,
        )

    # ── Volatilidad implícita ──────────────────────────────────────────────────
    if data.get("implied_vol"):
        iv = data["implied_vol"]
        st.markdown("#### Volatilidad Implícita")
        col1, col2, col3 = st.columns(3)
        col1.metric("σ implícita", f"{iv.get('sigma_implicita_pct', 0):.2f}%")
        col2.metric("vs σ ingresada", f"{sigma*100:.2f}%")
        diff = iv.get("sigma_implicita_pct", 0) - sigma * 100
        col3.metric("Diferencia", f"{diff:+.2f}pp")

    # ── Curvas de payoff y delta ───────────────────────────────────────────────
    if curvas:
        st.markdown("#### Curvas de payoff y delta")
        col1, col2 = st.columns(2)

        with col1:
            payoff = curvas.get("payoff_curve", {})
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=payoff.get("S_range", []), y=payoff.get("payoff", []),
                mode="lines", name="Payoff al vencimiento",
                line=dict(color=COLORS["accent"], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=payoff.get("S_range", []), y=payoff.get("price_curve", []),
                mode="lines", name="Precio Black-Scholes",
                line=dict(color=COLORS["warning"], width=2, dash="dash"),
            ))
            fig.add_vline(x=K, line_dash="dot", line_color=COLORS["muted"],
                          annotation_text=f"K={K}", annotation_position="top right")
            fig.update_layout(
                xaxis_title="Precio subyacente", yaxis_title="Valor ($)",
                margin=dict(t=20, b=40),
                paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
                font=dict(color=COLORS["text"]),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            delta_c = curvas.get("delta_curve", {})
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=delta_c.get("S_range", []), y=delta_c.get("delta", []),
                mode="lines", name="Delta",
                line=dict(color=COLORS["positive"], width=2),
            ))
            fig2.add_vline(x=K, line_dash="dot", line_color=COLORS["muted"])
            fig2.add_hline(y=0, line_dash="dot", line_color=COLORS["muted"])
            fig2.update_layout(
                xaxis_title="Precio subyacente", yaxis_title="Delta",
                margin=dict(t=20, b=40),
                paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
                font=dict(color=COLORS["text"]),
            )
            st.plotly_chart(fig2, use_container_width=True)