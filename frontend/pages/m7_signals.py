import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_alertas, fetch_indicadores, TICKERS
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
SIGNAL_SCORE = {
    "Compra": 1, "Sobreventa": 1,
    "Neutral": 0,
    "Venta": -1, "Sobrecompra": -1,
}
IND_KEYS   = ["rsi_signal", "macd_signal", "bb_signal", "sma_cross", "stoch_signal"]
IND_LABELS = ["RSI", "MACD", "Bollinger", "SMA Cross", "Estocástico"]
IND_DESC = {
    "rsi_signal":   "Mide velocidad y magnitud de movimientos de precio (sobrecompra >70, sobreventa <30).",
    "macd_signal":  "Cruce de medias exponenciales — señal alcista cuando MACD > línea de señal.",
    "bb_signal":    "Precio fuera de las bandas indica extensión extrema del movimiento.",
    "sma_cross":    "Cruce EMA/SMA — EMA sobre SMA indica momentum alcista.",
    "stoch_signal": "Oscilador de momentum (sobrecompra >80, sobreventa <20).",
}


def _badge(signal: str) -> str:
    cls, label = SIGNAL_BADGE.get(signal, ("badge-blue", signal))
    return f'<span class="badge {cls}">{label}</span>'


def _interpret_signals(alertas: list) -> str:
    buy_count  = sum(1 for a in alertas if "Compra" in a.get("overall", ""))
    sell_count = sum(1 for a in alertas if "Venta" in a.get("overall", ""))
    neutral_count = len(alertas) - buy_count - sell_count
    if buy_count > sell_count:
        return f"El portafolio muestra <strong>sesgo alcista</strong>: {buy_count} activo(s) con señal de compra frente a {sell_count} de venta. Condiciones favorables para posiciones largas selectivas."
    elif sell_count > buy_count:
        return f"El portafolio muestra <strong>sesgo bajista</strong>: {sell_count} activo(s) con señal de venta frente a {buy_count} de compra. Considerar reducir exposición o implementar coberturas."
    else:
        return f"Señales mixtas ({neutral_count} neutral, {buy_count} compra, {sell_count} venta). Esperar confirmación de dirección antes de tomar posiciones."


def _interpret_ticker(a: dict) -> tuple[str, str]:
    scores = [SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS]
    total = sum(scores)
    buy_n  = sum(1 for s in scores if s > 0)
    sell_n = sum(1 for s in scores if s < 0)
    neut_n = sum(1 for s in scores if s == 0)

    conflicting = [IND_LABELS[i] for i, s in enumerate(scores) if s < 0] if total > 0 else \
                  [IND_LABELS[i] for i, s in enumerate(scores) if s > 0] if total < 0 else []

    if total >= 2:
        msg = f"<strong>Señal alcista consolidada</strong> ({buy_n}/5 indicadores positivos). "
        if conflicting:
            msg += f"Señales contrarias en: {', '.join(conflicting)} — monitorear como riesgo de reversión."
        else:
            msg += "Convergencia total de indicadores — alta convicción en la dirección."
        return msg, "positive"
    elif total <= -2:
        msg = f"<strong>Señal bajista consolidada</strong> ({sell_n}/5 indicadores negativos). "
        if conflicting:
            msg += f"Señales contrarias en: {', '.join(conflicting)} — posible soporte técnico."
        else:
            msg += "Convergencia total a la baja — considerar salida o cobertura."
        return msg, "negative"
    else:
        msg = f"<strong>Señal mixta</strong> ({buy_n} alcista, {sell_n} bajista, {neut_n} neutral). Sin consenso claro entre indicadores — evitar posiciones direccionales hasta confirmar."
        return msg, "warning"


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

    # ── Interpretación global ──
    st.markdown(f'<div class="interpretation-box">{_interpret_signals(alertas)}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Heatmap interactivo primero ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Mapa de Señales del Portafolio</div>', unsafe_allow_html=True)

    tickers_list = [a["ticker"] for a in alertas]
    z    = [[SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS] for a in alertas]
    text = [[a.get(k, "—") for k in IND_KEYS] for a in alertas]

    fig_heat = go.Figure(go.Heatmap(
        z=z, x=IND_LABELS, y=tickers_list,
        colorscale=[[0, "#2E0D10"], [0.5, "#0D1018"], [1, "#0D2E20"]],
        zmid=0, zmin=-1, zmax=1,
        text=text, texttemplate="%{text}",
        textfont=dict(size=10, family="DM Sans, sans-serif"),
        showscale=False,
        hovertemplate="<b>%{y}</b> · %{x}<br>Señal: %{text}<extra></extra>"
    ))
    fig_heat.update_layout(
        height=260,
        title="Verde = alcista / Rojo = bajista — clic en un ticker para ver detalle",
        margin=dict(l=60, r=20, t=48, b=40),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Selector interactivo de activo ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Análisis Detallado por Activo</div>', unsafe_allow_html=True)

    ticker_sel = st.selectbox("Selecciona un activo para analizar", TICKERS, key="signals_ticker")
    a = next((x for x in alertas if x["ticker"] == ticker_sel), None)

    if a:
        overall_color = OVERALL_COLOR.get(a.get("overall", "Neutral"), COLORS["muted"])
        ticker_c = ticker_color(ticker_sel)

        # Cabecera del activo
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px;
                    padding:14px 18px; background:#0D1018; border:1px solid #1C2030; border-radius:10px;
                    border-left:3px solid {ticker_c};">
            <div style="font-family:'DM Mono',monospace; font-size:1.1rem; font-weight:500; color:{ticker_c};">{ticker_sel}</div>
            <div style="width:2px; height:24px; background:{overall_color}; border-radius:2px;"></div>
            {_badge(a.get('overall','Neutral'))}
            <div style="margin-left:auto; font-size:0.75rem; color:#3B4460;">
                Score técnico: {sum(SIGNAL_SCORE.get(a.get(k,'Neutral'),0) for k in IND_KEYS):+d} / 5
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Indicadores con descripción
        cols = st.columns(5)
        for col, key, label in zip(cols, IND_KEYS, IND_LABELS):
            sig = a.get(key, "Neutral")
            score = SIGNAL_SCORE.get(sig, 0)
            bar_color = COLORS["positive"] if score > 0 else COLORS["negative"] if score < 0 else COLORS["warning"]
            with col:
                st.markdown(f"""
                <div style="text-align:center; padding:12px 6px;
                            background:#0D1018; border:1px solid #1C2030;
                            border-top:2px solid {bar_color};
                            border-radius:8px; height:100%;">
                    <div style="font-size:0.65rem; font-weight:600; letter-spacing:0.08em;
                                text-transform:uppercase; color:#2E3550; margin-bottom:8px;">{label}</div>
                    {_badge(sig)}
                    <div style="font-size:0.62rem; color:#2E3550; margin-top:8px; line-height:1.4;">
                        {IND_DESC[key]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Interpretación específica del ticker
        interp_msg, interp_class = _interpret_ticker(a)
        st.markdown(f'<div class="interpretation-box {interp_class}">{interp_msg}</div>', unsafe_allow_html=True)

        # ── Gauge de score técnico ──
        score_total = sum(SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score_total,
            title={"text": f"Score técnico — {ticker_sel}", "font": {"size": 13, "color": COLORS["muted"]}},
            gauge={
                "axis": {"range": [-5, 5], "tickwidth": 1, "tickcolor": COLORS["muted"]},
                "bar": {"color": COLORS["positive"] if score_total > 0 else COLORS["negative"] if score_total < 0 else COLORS["warning"]},
                "bgcolor": COLORS["surface"],
                "borderwidth": 0,
                "steps": [
                    {"range": [-5, -2], "color": "#2E0D10"},
                    {"range": [-2, 2],  "color": "#1C2030"},
                    {"range": [2, 5],   "color": "#0D2E20"},
                ],
                "threshold": {
                    "line": {"color": COLORS["muted"], "width": 2},
                    "thickness": 0.75,
                    "value": 0,
                },
            },
            number={"font": {"size": 28, "family": "DM Mono, monospace", "color": COLORS["text"]}},
        ))
        fig_gauge.update_layout(
            height=240,
            margin=dict(l=30, r=30, t=60, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLORS["muted"]),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Comparativa rápida todos los activos ──
    st.markdown('<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Comparativa Rápida — Todos los Activos</div>', unsafe_allow_html=True)

    rows = []
    for a in alertas:
        score = sum(SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS)
        rows.append({
            "Ticker":      a["ticker"],
            "RSI":         a.get("rsi_signal", "—"),
            "MACD":        a.get("macd_signal", "—"),
            "Bollinger":   a.get("bb_signal", "—"),
            "SMA Cross":   a.get("sma_cross", "—"),
            "Estocástico": a.get("stoch_signal", "—"),
            "Global":      a.get("overall", "—"),
            "Score":       f"{score:+d}/5",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)