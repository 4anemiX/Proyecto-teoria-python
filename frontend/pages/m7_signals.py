import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_alertas, TICKERS
from utils.theme import ticker_color, COLORS

SIGNAL_BADGE = {
    "Compra":      ("badge-green",  "Compra"),
    "Venta":       ("badge-red",    "Venta"),
    "Neutral":     ("badge-yellow", "Neutral"),
    "Sobrecompra": ("badge-red",    "Sobrecompra"),
    "Sobreventa":  ("badge-green",  "Sobreventa"),
}

OVERALL_COLOR = {
    "Compra":  COLORS["positive"],
    "Venta":   COLORS["negative"],
    "Neutral": COLORS["warning"],
}


def _badge(signal: str) -> str:
    cls, label = SIGNAL_BADGE.get(signal, ("badge-blue", signal))
    return f'<span class="badge {cls}">{label}</span>'


def _dot(signal: str) -> str:
    color = (
        COLORS["positive"] if signal in ("Compra", "Sobreventa") else
        COLORS["negative"] if signal in ("Venta", "Sobrecompra") else
        COLORS["warning"]
    )
    return f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};"></span>'


def _interpret_signals(alertas: list) -> str:
    buy_count = sum(1 for a in alertas if "Compra" in a.get("overall", ""))
    sell_count = sum(1 for a in alertas if "Venta" in a.get("overall", ""))
    neutral_count = len(alertas) - buy_count - sell_count

    if buy_count > sell_count:
        return f"El portafolio muestra <strong>sesgo alcista</strong>: {buy_count} activo(s) con señal de compra frente a {sell_count} de venta. Condiciones favorables para posiciones largas selectivas."
    elif sell_count > buy_count:
        return f"El portafolio muestra <strong>sesgo bajista</strong>: {sell_count} activo(s) con señal de venta frente a {buy_count} de compra. Considerar reducir exposición o implementar coberturas."
    else:
        return f"Señales mixtas en el portafolio ({neutral_count} neutral, {buy_count} compra, {sell_count} venta). Esperar confirmación de dirección antes de tomar posiciones."


def render():
    st.markdown("""
    <div class="section-title">Señales & Alertas</div>
    <div class="section-subtitle">Síntesis de señales técnicas por activo — RSI, MACD, Bollinger, SMA Cross, Estocástico</div>
    """, unsafe_allow_html=True)

    with st.spinner("Cargando señales técnicas..."):
        alertas = fetch_alertas()
    if not alertas:
        st.warning("No se pudieron cargar las alertas.")
        return

    # Interpretación global
    st.markdown(f'<div class="interpretation-box">{_interpret_signals(alertas)}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Panel por activo ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:16px;">Señales por Activo</div>', unsafe_allow_html=True)

    indicators = [
        ("rsi_signal",  "RSI"),
        ("macd_signal", "MACD"),
        ("bb_signal",   "Bollinger"),
        ("sma_cross",   "SMA Cross"),
        ("stoch_signal","Estocástico"),
    ]

    for a in alertas:
        overall_color = OVERALL_COLOR.get(a.get("overall", "Neutral"), COLORS["muted"])
        ticker_c = ticker_color(a["ticker"])

        with st.expander(f"{a['ticker']}  ·  señal global: {a.get('overall','—')}", expanded=True):
            # Header
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                <div style="font-family:'DM Mono',monospace; font-size:1rem; font-weight:500; color:{ticker_c};">{a['ticker']}</div>
                <div style="width:3px; height:20px; background:{overall_color}; border-radius:2px;"></div>
                {_badge(a.get('overall','Neutral'))}
            </div>
            """, unsafe_allow_html=True)

            # Indicadores en fila
            cols = st.columns(len(indicators))
            for col, (key, label) in zip(cols, indicators):
                sig = a.get(key, "Neutral")
                with col:
                    st.markdown(f"""
                    <div style="text-align:center; padding:10px 4px;
                                background:#0D1018; border:1px solid #1C2030;
                                border-radius:8px;">
                        <div style="font-size:0.65rem; font-weight:600; letter-spacing:0.08em;
                                    text-transform:uppercase; color:#2E3550; margin-bottom:6px;">{label}</div>
                        {_badge(sig)}
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Tabla resumen ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Tabla Resumen</div>', unsafe_allow_html=True)

    rows = [{
        "Ticker":      a["ticker"],
        "RSI":         a.get("rsi_signal", "—"),
        "MACD":        a.get("macd_signal", "—"),
        "Bollinger":   a.get("bb_signal", "—"),
        "SMA Cross":   a.get("sma_cross", "—"),
        "Estocástico": a.get("stoch_signal", "—"),
        "Global":      a.get("overall", "—"),
    } for a in alertas]

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Heatmap de señales ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin:16px 0 12px;">Mapa de Calor de Señales</div>', unsafe_allow_html=True)

    signal_score = {
        "Compra": 1, "Sobreventa": 1,
        "Neutral": 0,
        "Venta": -1, "Sobrecompra": -1,
    }
    tickers_list = [a["ticker"] for a in alertas]
    ind_keys = ["rsi_signal", "macd_signal", "bb_signal", "sma_cross", "stoch_signal"]
    ind_labels = ["RSI", "MACD", "Bollinger", "SMA Cross", "Estocástico"]

    z = [[signal_score.get(a.get(k, "Neutral"), 0) for k in ind_keys] for a in alertas]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=ind_labels,
        y=tickers_list,
        colorscale=[[0, "#2E0D10"], [0.5, "#0D1018"], [1, "#0D2E20"]],
        zmid=0, zmin=-1, zmax=1,
        text=[[a.get(k, "—") for k in ind_keys] for a in alertas],
        texttemplate="%{text}",
        textfont=dict(size=10, family="DM Sans, sans-serif"),
        showscale=False,
        hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>"
    ))
    fig.update_layout(height=280, title="Verde = Compra / Rojo = Venta / Neutro = Sin señal")
    st.plotly_chart(fig, use_container_width=True)