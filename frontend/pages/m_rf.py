import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_curva_rendimiento, fetch_bono
from utils.theme import COLORS


def render():
    st.markdown("""
    <div class="section-title">Renta Fija</div>
    <div class="section-subtitle">Curva de rendimiento Nelson-Siegel · Duración · Convexidad · Sensibilidad de precio</div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📈 Curva de Rendimiento", "🔖 Valoración de Bono"])

    # ── Tab 1: Curva Nelson-Siegel ─────────────────────────────────────────────
    with tab1:
        st.markdown("#### Tesoros US — FRED + ajuste Nelson-Siegel")

        with st.spinner("Descargando tasas desde FRED..."):
            data = fetch_curva_rendimiento()

        if not data:
            st.warning("No se pudo obtener la curva de rendimiento. Verifica FRED_API_KEY.")
            return

        # Forma de la curva
        shape = data.get("shape", "")
        shape_msg = data.get("shape_interpretation", "")
        color_shape = {"normal": COLORS["positive"], "invertida": COLORS["negative"],
                       "plana": COLORS["warning"]}.get(shape, COLORS["muted"])

        st.markdown(
            f"<div class='insight-box' style='border-color:{color_shape}'>"
            f"<strong>Forma de la curva: {shape.upper()}</strong><br>{shape_msg}</div>",
            unsafe_allow_html=True,
        )

        # Gráfico
        pts = data["curve_points"]
        obs_x = data["maturities_obs"]
        obs_y = data["yields_obs_pct"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pts["tau_ns"], y=pts["yield_ns"],
            mode="lines", name="Nelson-Siegel",
            line=dict(color=COLORS["accent"], width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=obs_x, y=obs_y,
            mode="markers", name="Observado (FRED)",
            marker=dict(color=COLORS["warning"], size=9, symbol="circle"),
        ))
        fig.update_layout(
            xaxis_title="Vencimiento (años)", yaxis_title="Tasa (%)",
            legend=dict(orientation="h", y=1.1),
            margin=dict(t=30, b=40),
            paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
            font=dict(color=COLORS["text"]),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Parámetros NS
        ns = data["nelson_siegel"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("β₀ — Nivel LP", f"{ns['beta0']:.4f}")
        col2.metric("β₁ — Pendiente", f"{ns['beta1']:.4f}")
        col3.metric("β₂ — Curvatura", f"{ns['beta2']:.4f}")
        col4.metric("λ — Decaimiento", f"{ns['lambda']:.4f}")  # corregido: era lambda_

    # ── Tab 2: Bono sintético ──────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Bono sintético — parámetros")

        col1, col2, col3, col4, col5 = st.columns(5)
        face_value     = col1.number_input("Valor nominal ($)", 100.0, 1_000_000.0, 1000.0, 100.0)
        coupon_rate    = col2.slider("Cupón anual (%)", 0.0, 20.0, 5.0, 0.25) / 100
        maturity_years = col3.slider("Vencimiento (años)", 1, 30, 10)
        frequency      = col4.selectbox("Frecuencia pagos/año", [1, 2, 4, 12], index=1)
        ytm            = col5.slider("YTM (%)", 0.01, 20.0, 5.0, 0.25) / 100

        with st.spinner("Calculando métricas del bono..."):
            bond = fetch_bono(face_value, coupon_rate, maturity_years, frequency, ytm)

        if not bond:
            st.warning("Error al calcular las métricas del bono.")
            return

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precio", f"${bond['price']:,.2f}")
        col2.metric("Duración Macaulay", f"{bond['macaulay_duration']:.4f} años")
        col3.metric("Duración Modificada", f"{bond['modified_duration']:.4f}")
        col4.metric("Convexidad", f"{bond['convexity']:.4f}")

        # Sensibilidad a shocks
        st.markdown("#### Sensibilidad a shocks de tasa")
        sens = bond.get("price_sensitivity", {})
        if sens:
            shocks = sorted(sens.keys(), key=lambda x: int(x.replace("shock_", "").replace("bp", "").replace("+", "")))
            rows = []
            for s in shocks:
                info = sens[s]
                rows.append({
                    "Shock": f"{info['delta_ytm_bp']:+.0f} pb",
                    "Precio exacto": f"${info['price_exact']:,.4f}",
                    "Δ Precio (dur.)": f"${info['dp_linear']:,.4f}",
                    "Δ Precio (dur.+conv.)": f"${info['dp_convex']:,.4f}",
                    "Δ% exacto": f"{info['pct_exact']:+.4f}%",
                })

            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Gráfico de sensibilidad
            delta_ytm_bp = [sens[s]["delta_ytm_bp"] for s in shocks]
            dp_exact     = [sens[s]["pct_exact"] for s in shocks]
            dp_convex    = [sens[s]["pct_convex"] for s in shocks]

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=delta_ytm_bp, y=dp_exact,
                mode="lines+markers", name="Precio exacto",
                line=dict(color=COLORS["accent"], width=2.5),
                marker=dict(size=7),
            ))
            fig2.add_trace(go.Scatter(
                x=delta_ytm_bp, y=dp_convex,
                mode="lines+markers", name="Aprox. dur+conv.",
                line=dict(color=COLORS["warning"], width=1.8, dash="dot"),
                marker=dict(size=5),
            ))
            fig2.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"], line_width=1)
            fig2.update_layout(
                xaxis_title="Shock de tasa (pb)",
                yaxis_title="Cambio en precio (%)",
                legend=dict(orientation="h", y=1.1),
                margin=dict(t=30, b=40),
                paper_bgcolor=COLORS["surface"],
                plot_bgcolor=COLORS["bg"],
                font=dict(color=COLORS["text"]),
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Interpretación
            d_mod = bond["modified_duration"]
            conv  = bond["convexity"]
            st.markdown(f"""
            <div class='insight-box'>
                <strong>Interpretación:</strong><br>
                Con una duración modificada de <strong>{d_mod:.4f}</strong>, un alza de 100 pb
                reduce el precio aproximadamente <strong>{d_mod:.2f}%</strong>.<br>
                La convexidad de <strong>{conv:.4f}</strong> implica que la pérdida real es menor
                que la estimada por duración sola — y la ganancia ante bajas de tasa es mayor.
            </div>
            """, unsafe_allow_html=True)