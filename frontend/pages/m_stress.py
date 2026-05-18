import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_stress, TICKERS
from utils.theme import COLORS


def render():
    st.markdown("""
    <div class="section-title">Stress Testing</div>
    <div class="section-subtitle">Escenarios extremos sobre el portafolio — crisis, shocks de tasa y volatilidad</div>
    """, unsafe_allow_html=True)

    # ── Selección de portafolio ────────────────────────────────────────────────
    st.markdown("#### Composición del portafolio")
    tickers_sel = st.multiselect("Activos", TICKERS + ["SPY"], default=["MSFT", "KO", "JPM"])
    if len(tickers_sel) < 2:
        st.warning("Selecciona al menos 2 activos.")
        return

    cols = st.columns(len(tickers_sel))
    raw_weights = []
    for i, t in enumerate(tickers_sel):
        w = cols[i].number_input(f"Peso {t} (%)", 0.0, 100.0, round(100.0 / len(tickers_sel), 1), 1.0)
        raw_weights.append(w)

    total = sum(raw_weights)
    if abs(total - 100.0) > 0.1:
        st.error(f"Los pesos suman {total:.1f}% — deben sumar exactamente 100%.")
        return

    weights = [w / 100.0 for w in raw_weights]

    # ── Escenarios personalizados ──────────────────────────────────────────────
    usar_custom = st.checkbox("Definir escenario personalizado (además de los 6 estándar)")
    scenarios = []
    if usar_custom:
        with st.expander("Configurar escenario personalizado"):
            col1, col2, col3, col4 = st.columns(4)
            name         = col1.text_input("Nombre", "Mi escenario")
            rate_shock   = col2.slider("Shock de tasa (pb)", -300, 300, 100)
            market_drop  = col3.slider("Caída de mercado (%)", -80, 50, -20) / 100
            vol_mult     = col4.slider("Multiplicador volatilidad", 0.5, 5.0, 2.0, 0.5)
            scenarios = [{"name": name, "rate_shock_bp": rate_shock,
                          "market_drop_pct": market_drop, "vol_multiplier": vol_mult}]

    if st.button("▶ Ejecutar Stress Test", type="primary"):
        with st.spinner("Aplicando escenarios de estrés..."):
            data = fetch_stress(tickers_sel, weights, scenarios)

        if not data:
            st.warning("Error al ejecutar el stress test.")
            return

        # Normalizar estructura (puede ser lista o dict con 'results')
        results = data if isinstance(data, list) else data.get("results", [])

        if not results:
            st.warning("No se obtuvieron resultados.")
            return

        # ── Tabla de resultados ────────────────────────────────────────────────
        st.markdown("#### Resultados por escenario")

        names    = [r.get("scenario", r.get("name", f"Escenario {i+1}")) for i, r in enumerate(results)]
        ret_port = [r.get("portfolio_return_pct", r.get("portfolio_loss_pct", 0)) for r in results]
        max_loss = [r.get("max_individual_loss_pct", 0) for r in results]

        col1, col2, col3 = st.columns(3)
        worst_idx = ret_port.index(min(ret_port))
        col1.metric("Peor escenario", names[worst_idx])
        col2.metric("Pérdida máx. portafolio", f"{min(ret_port):.2f}%")
        col3.metric("Pérdida máx. activo individual", f"{min(max_loss):.2f}%")

        # Gráfico de barras por escenario
        colors = [COLORS["negative"] if v < 0 else COLORS["positive"] for v in ret_port]
        fig = go.Figure(go.Bar(
            x=names, y=ret_port,
            marker_color=colors,
            text=[f"{v:.2f}%" for v in ret_port],
            textposition="outside",
        ))
        fig.update_layout(
            xaxis_title="Escenario", yaxis_title="Retorno del portafolio (%)",
            margin=dict(t=20, b=80),
            paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
            font=dict(color=COLORS["text"]),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detalle por escenario
        st.markdown("#### Detalle por escenario")
        for r in results:
            nombre = r.get("scenario", r.get("name", "Escenario"))
            with st.expander(f"📋 {nombre}"):
                asset_returns = r.get("asset_returns", r.get("individual_returns", {}))
                if asset_returns:
                    fig2 = go.Figure(go.Bar(
                        x=list(asset_returns.keys()),
                        y=list(asset_returns.values()),
                        marker_color=[
                            COLORS["negative"] if v < 0 else COLORS["positive"]
                            for v in asset_returns.values()
                        ],
                    ))
                    fig2.update_layout(
                        xaxis_title="Activo", yaxis_title="Retorno (%)",
                        margin=dict(t=10, b=30),
                        paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
                        font=dict(color=COLORS["text"]),
                        height=280,
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.json(r)