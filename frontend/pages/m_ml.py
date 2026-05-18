import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_predict, fetch_predict_history, TICKERS
from utils.theme import COLORS


_REGIME_COLOR = {
    "alcista":  COLORS["positive"],
    "bajista":  COLORS["negative"],
    "lateral":  COLORS["warning"],
}

_REGIME_ICON = {
    "alcista": "📈",
    "bajista": "📉",
    "lateral": "➡️",
}


def render():
    st.markdown("""
    <div class="section-title">Predicción ML — Régimen de Mercado</div>
    <div class="section-subtitle">Clasificación alcista · bajista · lateral — pipeline scikit-learn + Singleton</div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🤖 Predicción", "🗂️ Historial"])

    # ── Tab 1: Predicción ──────────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns([1, 3])
        ticker = col1.selectbox("Activo", TICKERS + ["SPY"])

        if col2.button("▶ Predecir régimen", type="primary"):
            with st.spinner(f"Ejecutando modelo ML para {ticker}..."):
                result = fetch_predict(ticker)

            if not result:
                st.warning("Error al obtener predicción. Verifica que el modelo esté entrenado.")
                return

            regime      = result.get("regime", "desconocido")
            confidence  = result.get("confidence", 0.0)
            probs       = result.get("probabilities", {})
            features    = result.get("features_used", {})
            accuracy    = result.get("model_accuracy", 0.0)
            interp      = result.get("interpretation", "")
            version     = result.get("model_version", "v1")

            color = _REGIME_COLOR.get(regime, COLORS["muted"])
            icon  = _REGIME_ICON.get(regime, "❓")

            st.markdown(
                f"<div class='insight-box' style='border-color:{color}'>"
                f"<strong>{icon} Régimen predicho: {regime.upper()}</strong><br>"
                f"Confianza: {confidence*100:.1f}% | Modelo: {version} | "
                f"Accuracy histórico: {accuracy*100:.1f}%<br>{interp}</div>",
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)

            # Gráfico de probabilidades
            with col1:
                st.markdown("#### Probabilidades por régimen")
                labels = list(probs.keys())
                values = list(probs.values())
                fig = go.Figure(go.Bar(
                    x=labels, y=[v * 100 for v in values],
                    marker_color=[_REGIME_COLOR.get(l, COLORS["muted"]) for l in labels],
                    text=[f"{v*100:.1f}%" for v in values],
                    textposition="outside",
                ))
                fig.update_layout(
                    xaxis_title="Régimen", yaxis_title="Probabilidad (%)",
                    yaxis_range=[0, 110],
                    margin=dict(t=10, b=30),
                    paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
                    font=dict(color=COLORS["text"]),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Features usadas
            with col2:
                st.markdown("#### Features del modelo")
                if features:
                    feat_names = list(features.keys())
                    feat_vals  = list(features.values())
                    fig2 = go.Figure(go.Bar(
                        x=feat_names, y=feat_vals,
                        marker_color=COLORS["accent"],
                        orientation="v",
                    ))
                    fig2.update_layout(
                        xaxis_title="Feature", yaxis_title="Valor",
                        margin=dict(t=10, b=60),
                        paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
                        font=dict(color=COLORS["text"]),
                        xaxis_tickangle=-30,
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No se retornaron features del modelo.")

    # ── Tab 2: Historial ───────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Predicciones guardadas en SQLite")

        col1, col2 = st.columns([1, 3])
        filter_ticker = col1.selectbox("Filtrar por ticker", ["Todos"] + TICKERS + ["SPY"])
        limit         = col2.slider("Máximo de registros", 5, 100, 20)

        ticker_param = None if filter_ticker == "Todos" else filter_ticker

        with st.spinner("Cargando historial..."):
            history = fetch_predict_history(ticker_param, limit)

        if not history:
            st.info("No hay predicciones guardadas aún. Ejecuta una predicción primero.")
            return

        for rec in history:
            regime = rec.get("label", "?")
            color  = _REGIME_COLOR.get(regime, COLORS["muted"])
            icon   = _REGIME_ICON.get(regime, "❓")
            conf   = rec.get("confidence", 0.0) or 0.0
            ts     = str(rec.get("timestamp", ""))[:16]
            tick   = rec.get("ticker", "")
            ver    = rec.get("model_version", "")

            st.markdown(
                f"<div class='metric-card'>"
                f"<span style='color:{color}'>{icon} <strong>{regime.upper()}</strong></span> — "
                f"<strong>{tick}</strong> | {ts} | confianza: {conf*100:.1f}% | {ver}"
                f"</div>",
                unsafe_allow_html=True,
            )