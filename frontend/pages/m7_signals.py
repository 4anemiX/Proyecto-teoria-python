import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_alertas, TICKERS
from utils.theme import ticker_color, COLORS

# ── Constantes ──────────────────────────────────────────────────────────────

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
    "rsi_signal":   "Velocidad del precio. >70 sobrecompra, <30 sobreventa.",
    "macd_signal":  "Cruce de EMAs. Alcista si MACD > línea de señal.",
    "bb_signal":    "Precio fuera de bandas indica extensión extrema.",
    "sma_cross":    "EMA sobre SMA indica momentum alcista.",
    "stoch_signal": "Oscilador de momentum. >80 sobrecompra, <20 sobreventa.",
}

# Explicaciones narrativas detalladas por indicador y señal
IND_EXPLAIN = {
    "rsi_signal": {
        "Compra":      "El RSI está por debajo de 30, indicando que el activo está en zona de sobreventa. Históricamente, este nivel precede rebotes al alza.",
        "Sobreventa":  "El RSI está en zona de sobreventa extrema (<30). Alta probabilidad de reversión alcista en el corto plazo.",
        "Venta":       "El RSI supera 70, señalando sobrecompra. El activo puede estar sobreextendido y vulnerable a una corrección.",
        "Sobrecompra": "El RSI en zona de sobrecompra extrema (>70). Riesgo elevado de corrección; considerar reducir exposición.",
        "Neutral":     "El RSI se ubica entre 30 y 70, sin señales extremas. No hay presión compradora ni vendedora dominante.",
    },
    "macd_signal": {
        "Compra":      "El MACD cruzó por encima de la línea de señal, confirmando momentum alcista. Las EMAs de corto plazo aceleran sobre las de largo plazo.",
        "Sobreventa":  "Cruce alcista del MACD desde niveles bajos, lo que sugiere recuperación del momentum.",
        "Venta":       "El MACD cruzó por debajo de la línea de señal, indicando pérdida de momentum. La presión bajista gana fuerza.",
        "Sobrecompra": "MACD en niveles altos con posible agotamiento del impulso alcista.",
        "Neutral":     "El MACD y su señal están convergentes sin cruce definido. Momentum lateral sin dirección clara.",
    },
    "bb_signal": {
        "Compra":      "El precio tocó la banda inferior de Bollinger, indicando una extensión bajista extrema. Las reversiones desde este nivel son frecuentes.",
        "Sobreventa":  "Precio por debajo de la banda inferior, en territorio de extensión extrema con alta probabilidad de rebote.",
        "Venta":       "El precio alcanzó la banda superior de Bollinger. La extensión alcista podría estar agotándose.",
        "Sobrecompra": "Precio sobre la banda superior, indicando sobreextensión. Posible reversión o consolidación inminente.",
        "Neutral":     "El precio se mueve dentro de las bandas sin tocar extremos. Volatilidad contenida y tendencia indefinida.",
    },
    "sma_cross": {
        "Compra":      "La EMA de corto plazo cruzó por encima de la SMA de largo plazo (Golden Cross). Señal clásica de cambio de tendencia a alcista.",
        "Sobreventa":  "Cruce alcista de medias móviles desde niveles deprimidos, reforzando la señal de recuperación.",
        "Venta":       "La EMA cayó por debajo de la SMA (Death Cross), confirmando un cambio de tendencia a bajista.",
        "Sobrecompra": "Las medias indican tendencia alcista pero con divergencia respecto a otros indicadores de momentum.",
        "Neutral":     "Las medias móviles están prácticamente alineadas sin cruce. Tendencia lateral o transición de fase.",
    },
    "stoch_signal": {
        "Compra":      "El Estocástico salió de la zona de sobreventa (<20) con cruce alcista. Señal de recuperación de momentum.",
        "Sobreventa":  "Estocástico en zona de sobreventa extrema (<20), lista para posible rebote técnico.",
        "Venta":       "El Estocástico entró en sobrecompra (>80) con cruce bajista. Momentum alcista puede estar agotándose.",
        "Sobrecompra": "Estocástico en zona de sobrecompra extrema (>80). Alta probabilidad de corrección a corto plazo.",
        "Neutral":     "El Estocástico entre 20 y 80 sin cruces definidos. Momentum neutral sin señales de reversión.",
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def _badge(signal: str) -> str:
    cls, label = SIGNAL_BADGE.get(signal, ("badge-blue", signal))
    return f'<span class="badge {cls}">{label}</span>'


def _calc_score(a: dict) -> int:
    return sum(SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS)


def _interpret_global(alertas: list) -> tuple[str, str]:
    buy_count  = sum(1 for a in alertas if "Compra" in a.get("overall", ""))
    sell_count = sum(1 for a in alertas if "Venta"  in a.get("overall", ""))
    neut_count = len(alertas) - buy_count - sell_count
    if buy_count > sell_count:
        return (
            f"Portafolio con sesgo <strong>alcista</strong>: {buy_count} activo(s) en compra "
            f"frente a {sell_count} en venta. Condiciones favorables para posiciones largas selectivas.",
            "positive",
        )
    elif sell_count > buy_count:
        return (
            f"Portafolio con sesgo <strong>bajista</strong>: {sell_count} activo(s) en venta "
            f"frente a {buy_count} en compra. Considerar reducir exposición o implementar coberturas.",
            "negative",
        )
    else:
        return (
            f"Señales <strong>mixtas</strong> ({neut_count} neutral, {buy_count} compra, "
            f"{sell_count} venta). Esperar confirmación de dirección antes de tomar posiciones.",
            "warning",
        )


def _interpret_ticker(a: dict) -> tuple[str, str]:
    scores  = [SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS]
    total   = sum(scores)
    buy_n   = sum(1 for s in scores if s > 0)
    sell_n  = sum(1 for s in scores if s < 0)
    neut_n  = sum(1 for s in scores if s == 0)

    conflicting = (
        [IND_LABELS[i] for i, s in enumerate(scores) if s < 0] if total > 0 else
        [IND_LABELS[i] for i, s in enumerate(scores) if s > 0] if total < 0 else
        []
    )

    if total >= 2:
        msg = f"<strong>Señal alcista consolidada</strong> ({buy_n}/5 indicadores positivos). "
        msg += (
            f"Señales contrarias en: {', '.join(conflicting)} — monitorear como riesgo de reversión."
            if conflicting else
            "Convergencia total de indicadores — alta convicción en la dirección."
        )
        return msg, "positive"
    elif total <= -2:
        msg = f"<strong>Señal bajista consolidada</strong> ({sell_n}/5 indicadores negativos). "
        msg += (
            f"Señales contrarias en: {', '.join(conflicting)} — posible soporte técnico."
            if conflicting else
            "Convergencia total a la baja — considerar salida o cobertura."
        )
        return msg, "negative"
    else:
        return (
            f"<strong>Señal mixta</strong> ({buy_n} alcista, {sell_n} bajista, {neut_n} neutral). "
            "Sin consenso claro entre indicadores — evitar posiciones direccionales hasta confirmar.",
            "warning",
        )


def _interp_color(kind: str) -> str:
    return {
        "positive": COLORS["positive"],
        "negative": COLORS["negative"],
        "warning":  COLORS["warning"],
    }.get(kind, COLORS["muted"])


# ── Subcomponentes ───────────────────────────────────────────────────────────

def _render_metric_cards(alertas: list):
    buy_count  = sum(1 for a in alertas if "Compra" in a.get("overall", ""))
    sell_count = sum(1 for a in alertas if "Venta"  in a.get("overall", ""))
    neut_count = len(alertas) - buy_count - sell_count
    scores     = [_calc_score(a) for a in alertas]
    avg_score  = sum(scores) / len(scores) if scores else 0

    cols = st.columns(4)
    metrics = [
        ("Señales compra",  buy_count,  COLORS["positive"], "↑"),
        ("Señales venta",   sell_count, COLORS["negative"], "↓"),
        ("Neutral",         neut_count, COLORS["warning"],  "—"),
        ("Score promedio",  f"{avg_score:+.1f}", COLORS["text"], "◈"),
    ]
    for col, (label, value, color, icon) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""<div style="
                    background: linear-gradient(135deg, #0D1018 0%, #111520 100%);
                    border: 1px solid #1C2030;
                    border-top: 2px solid {color};
                    border-radius: 10px;
                    padding: 18px 20px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                ">
                    <div style="
                        position: absolute; top: 10px; right: 14px;
                        font-size: 1.2rem; color: {color}; opacity: 0.15;
                    ">{icon}</div>
                    <div style="
                        font-size: 0.62rem; font-weight: 700; letter-spacing: 0.12em;
                        text-transform: uppercase; color: #3B4460; margin-bottom: 8px;
                    ">{label}</div>
                    <div style="
                        font-size: 1.7rem; font-weight: 300; font-family: 'DM Mono', monospace;
                        color: {color}; line-height: 1;
                    ">{value}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _render_interpretation_box(msg: str, kind: str):
    border_color = _interp_color(kind)
    icon = {"positive": "▲", "negative": "▼", "warning": "◆"}.get(kind, "●")
    bg = {
        "positive": "rgba(29,158,117,0.07)",
        "negative": "rgba(200,50,50,0.07)",
        "warning":  "rgba(230,180,50,0.07)",
    }.get(kind, "#0D1018")
    st.markdown(
        f"""<div style="
            background: {bg};
            border-left: 3px solid {border_color};
            border-radius: 0 10px 10px 0;
            padding: 14px 18px;
            font-size: 0.82rem;
            color: #C8D0E0;
            margin: 12px 0;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        ">
            <span style="color: {border_color}; font-size: 0.7rem; margin-top: 2px; flex-shrink: 0;">{icon}</span>
            <span>{msg}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_heatmap(alertas: list):
    """Mapa de calor con paleta de lilas/violetas."""
    tickers_list = [a["ticker"] for a in alertas]
    z    = [[SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS] for a in alertas]
    text = [[a.get(k, "—") for k in IND_KEYS] for a in alertas]

    # Paleta lila: bajista=violeta oscuro, neutral=gris medio, alcista=lila brillante
    colorscale = [
        [0.0,  "#1A0A2E"],   # bajista profundo — violeta muy oscuro
        [0.25, "#3D1A6E"],   # bajista — morado medio
        [0.5,  "#1C2030"],   # neutral — gris oscuro
        [0.75, "#7B4FBF"],   # alcista — lila medio
        [1.0,  "#B48FFF"],   # alcista fuerte — lila brillante
    ]

    fig = go.Figure(go.Heatmap(
        z=z, x=IND_LABELS, y=tickers_list,
        colorscale=colorscale,
        zmid=0, zmin=-1, zmax=1,
        text=text, texttemplate="%{text}",
        textfont=dict(size=10, family="DM Sans, sans-serif", color="#E0D8FF"),
        showscale=True,
        colorbar=dict(
            tickvals=[-1, 0, 1],
            ticktext=["Venta", "Neutral", "Compra"],
            tickfont=dict(size=10, color="#8A8FAA"),
            outlinewidth=0,
            bgcolor="rgba(0,0,0,0)",
            len=0.7,
        ),
        hovertemplate="<b>%{y}</b> · %{x}<br>Señal: %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=max(280, len(alertas) * 48 + 80),
        title=dict(
            text="Lila brillante = alcista · Violeta oscuro = bajista · Gris = neutral",
            font=dict(size=10, color="#3B4460"),
        ),
        margin=dict(l=80, r=80, t=52, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8A8FAA"),
        xaxis=dict(side="top", tickfont=dict(size=11, family="DM Sans, sans-serif")),
        yaxis=dict(tickfont=dict(size=11, family="DM Mono, monospace")),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_gauge(ticker: str, score_total: int, t_color: str):
    bar_color = (
        COLORS["positive"] if score_total > 0 else
        COLORS["negative"] if score_total < 0 else
        COLORS["warning"]
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_total,
        title={"text": f"Score técnico — {ticker}", "font": {"size": 11, "color": "#3B4460"}},
        gauge={
            "axis": {
                "range": [-5, 5],
                "tickwidth": 1,
                "tickcolor": "#2E3550",
                "tickvals": [-5, -3, -1, 0, 1, 3, 5],
            },
            "bar":  {"color": t_color, "thickness": 0.3},
            "bgcolor": COLORS["surface"],
            "borderwidth": 0,
            "steps": [
                {"range": [-5, -2], "color": "rgba(200,50,50,0.12)"},
                {"range": [-2,  2], "color": "rgba(255,255,255,0.03)"},
                {"range": [ 2,  5], "color": "rgba(29,158,117,0.12)"},
            ],
            "threshold": {
                "line": {"color": "#3B4460", "width": 1},
                "thickness": 0.75,
                "value": 0,
            },
        },
        number={
            "font": {"size": 32, "family": "DM Mono, monospace", "color": t_color},
            "suffix": "/5",
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=30, r=30, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8A8FAA"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_compare_chart(alertas: list):
    sorted_alertas = sorted(alertas, key=_calc_score, reverse=True)
    tickers  = [a["ticker"] for a in sorted_alertas]
    scores   = [_calc_score(a) for a in sorted_alertas]
    # Usar colores del ticker para las barras
    bar_colors = [ticker_color(a["ticker"]) for a in sorted_alertas]

    fig = go.Figure(go.Bar(
        x=scores,
        y=tickers,
        orientation="h",
        marker=dict(
            color=bar_colors,
            opacity=0.85,
            line=dict(width=0),
        ),
        text=[f"{s:+d}" for s in scores],
        textposition="outside",
        textfont=dict(size=11, family="DM Mono, monospace", color="#C8D0E0"),
        hovertemplate="<b>%{y}</b><br>Score: %{x:+d}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="#2E3550", opacity=0.8)
    fig.update_layout(
        height=max(280, len(alertas) * 42 + 70),
        xaxis=dict(
            range=[-5.5, 5.5],
            title="Score técnico  (–5 bajista · 0 neutral · +5 alcista)",
            tickfont=dict(size=10, color="#3B4460"),
            color="#3B4460",
            gridcolor="#111520",
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=12, family="DM Mono, monospace", color="#8A8FAA"),
        ),
        margin=dict(l=90, r=70, t=20, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.35,
        font=dict(color="#8A8FAA"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_indicator_detail(a: dict):
    """Panel expandido con tarjetas de indicadores + explicación narrativa por señal."""
    cols = st.columns(5)
    for col, key, label in zip(cols, IND_KEYS, IND_LABELS):
        sig   = a.get(key, "Neutral")
        score = SIGNAL_SCORE.get(sig, 0)
        bar_color = (
            COLORS["positive"] if score > 0 else
            COLORS["negative"] if score < 0 else
            COLORS["warning"]
        )
        explanation = IND_EXPLAIN.get(key, {}).get(sig, IND_DESC.get(key, ""))
        with col:
            st.markdown(f"""
            <div style="
                padding: 14px 10px 12px;
                background: linear-gradient(160deg, #0D1018 0%, #0F1320 100%);
                border: 1px solid #1C2030;
                border-top: 2px solid {bar_color};
                border-radius: 10px;
                height: 100%;
                display: flex;
                flex-direction: column;
                gap: 8px;
            ">
                <div style="
                    font-size: 0.6rem; font-weight: 700; letter-spacing: 0.1em;
                    text-transform: uppercase; color: #3B4460; text-align: center;
                ">{label}</div>
                <div style="text-align: center;">{_badge(sig)}</div>
                <div style="
                    font-size: 0.64rem; color: #3B4460; line-height: 1.45;
                    text-align: left; padding-top: 4px; border-top: 1px solid #1C2030;
                ">{explanation}</div>
            </div>
            """, unsafe_allow_html=True)


# ── Render principal ─────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div class="section-title">Señales &amp; Alertas</div>
    <div class="section-subtitle">
        Síntesis de señales técnicas por activo — RSI · MACD · Bollinger · SMA Cross · Estocástico
    </div>
    """, unsafe_allow_html=True)

    # ── Carga de datos ──
    with st.spinner("Cargando señales técnicas..."):
        alertas = fetch_alertas()
    if not alertas:
        st.warning("No se pudieron cargar las alertas.")
        return

    # ── Métricas resumen ──
    st.markdown('<div class="summary-label" style="margin-bottom:10px;">Resumen del portafolio</div>',
                unsafe_allow_html=True)
    _render_metric_cards(alertas)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Interpretación global ──
    global_msg, global_kind = _interpret_global(alertas)
    _render_interpretation_box(global_msg, global_kind)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Filtros + Exportar ──
    fil_col, exp_col = st.columns([4, 1])
    with fil_col:
        filtro = st.radio(
            "Filtrar por señal global",
            ["Todas", "Solo compras", "Solo ventas", "Solo neutral"],
            horizontal=True,
            key="signals_filter",
        )
    with exp_col:
        rows_export = [
            {
                "Ticker":      a["ticker"],
                "RSI":         a.get("rsi_signal",   "—"),
                "MACD":        a.get("macd_signal",  "—"),
                "Bollinger":   a.get("bb_signal",    "—"),
                "SMA Cross":   a.get("sma_cross",    "—"),
                "Estocástico": a.get("stoch_signal", "—"),
                "Global":      a.get("overall",      "—"),
                "Score":       f"{_calc_score(a):+d}/5",
            }
            for a in alertas
        ]
        csv_bytes = pd.DataFrame(rows_export).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Exportar CSV",
            data=csv_bytes,
            file_name="señales_datarisk.csv",
            mime="text/csv",
            use_container_width=True,
            key="signals_export",
        )

    filtro_map = {
        "Todas":        None,
        "Solo compras": "Compra",
        "Solo ventas":  "Venta",
        "Solo neutral": "Neutral",
    }
    filtro_val = filtro_map[filtro]
    alertas_filtradas = [
        a for a in alertas
        if filtro_val is None or filtro_val in a.get("overall", "")
    ]

    if not alertas_filtradas:
        st.info("No hay activos con esa señal en este momento.")
        return

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── TABS principales ──
    tab_detalle, tab_heatmap, tab_comparativa = st.tabs([
        "🔍 Análisis por activo",
        "🟣 Mapa de calor",
        "📊 Comparativa",
    ])

    # ────────────────────────────────────────────────────────────────────────
    # TAB 1 — Análisis detallado por activo
    # ────────────────────────────────────────────────────────────────────────
    with tab_detalle:
        ticker_sel = st.selectbox(
            "Selecciona un activo",
            [a["ticker"] for a in alertas_filtradas],
            key="signals_ticker",
        )
        a = next((x for x in alertas_filtradas if x["ticker"] == ticker_sel), None)
        if not a:
            st.info("Activo no encontrado.")
        else:
            overall_color = OVERALL_COLOR.get(a.get("overall", "Neutral"), COLORS["muted"])
            t_color       = ticker_color(ticker_sel)
            score_total   = _calc_score(a)

            # — Cabecera del activo —
            st.markdown(f"""
            <div style="
                display: flex; align-items: center; gap: 16px;
                padding: 16px 20px;
                background: linear-gradient(135deg, #0D1018 0%, #111520 100%);
                border: 1px solid #1C2030;
                border-radius: 12px;
                border-left: 3px solid {t_color};
                margin-bottom: 16px;
            ">
                <div style="
                    font-family: 'DM Mono', monospace;
                    font-size: 1.15rem; font-weight: 500; color: {t_color};
                ">{ticker_sel}</div>
                <div style="width:1px;height:28px;background:#1C2030;"></div>
                {_badge(a.get('overall','Neutral'))}
                <div style="
                    margin-left: auto; font-size: 0.7rem; color: #2E3550;
                    font-family: 'DM Mono', monospace;
                ">Score: <span style="color:{t_color}">{score_total:+d}</span> / 5</div>
            </div>
            """, unsafe_allow_html=True)

            # — Indicadores con explicación narrativa —
            st.markdown('<div class="summary-label" style="margin-bottom:10px;">Indicadores técnicos</div>',
                        unsafe_allow_html=True)
            _render_indicator_detail(a)

            st.markdown("<br>", unsafe_allow_html=True)

            # — Interpretación específica + gauge —
            interp_msg, interp_kind = _interpret_ticker(a)
            _render_interpretation_box(interp_msg, interp_kind)

            # — Gauge con color del ticker —
            _render_gauge(ticker_sel, score_total, t_color)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 2 — Mapa de calor (paleta lila/violeta)
    # ────────────────────────────────────────────────────────────────────────
    with tab_heatmap:
        st.markdown(
            '<div class="summary-label" style="margin-bottom:12px;">Mapa de señales del portafolio</div>',
            unsafe_allow_html=True,
        )
        _render_heatmap(alertas_filtradas)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 3 — Comparativa con colores por ticker
    # ────────────────────────────────────────────────────────────────────────
    with tab_comparativa:
        st.markdown(
            '<div class="summary-label" style="margin-bottom:12px;">Ranking por score técnico</div>',
            unsafe_allow_html=True,
        )
        _render_compare_chart(alertas_filtradas)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(
            '<div class="summary-label" style="margin-bottom:10px;">Detalle por activo</div>',
            unsafe_allow_html=True,
        )

        indicators = [
            ("rsi_signal",   "RSI"),
            ("macd_signal",  "MACD"),
            ("bb_signal",    "Bollinger"),
            ("sma_cross",    "SMA Cross"),
            ("stoch_signal", "Estocástico"),
        ]

        for a in alertas_filtradas:
            ov_color = OVERALL_COLOR.get(a.get("overall", "Neutral"), COLORS["muted"])
            t_color  = ticker_color(a["ticker"])
            score    = _calc_score(a)

            with st.expander(
                f"{a['ticker']}  ·  {a.get('overall','—')}  ·  Score {score:+d}/5",
                expanded=False,
            ):
                # Cabecera interna
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                    <div style="
                        font-family:'DM Mono',monospace;font-size:1rem;
                        font-weight:500;color:{t_color};
                    ">{a['ticker']}</div>
                    <div style="width:2px;height:20px;background:{ov_color};border-radius:2px;"></div>
                    {_badge(a.get('overall','Neutral'))}
                    <span style="margin-left:auto;font-size:0.7rem;color:#3B4460;font-family:'DM Mono',monospace;">
                        Score: <span style="color:{t_color}">{score:+d}</span>/5
                    </span>
                </div>
                """, unsafe_allow_html=True)

                # Indicadores con explicación
                ind_cols = st.columns(len(indicators))
                for col, (key, label) in zip(ind_cols, indicators):
                    sig = a.get(key, "Neutral")
                    sc  = SIGNAL_SCORE.get(sig, 0)
                    bc  = (
                        COLORS["positive"] if sc > 0 else
                        COLORS["negative"] if sc < 0 else
                        COLORS["warning"]
                    )
                    explanation = IND_EXPLAIN.get(key, {}).get(sig, IND_DESC.get(key, ""))
                    with col:
                        st.markdown(f"""
                        <div style="
                            text-align:center; padding: 12px 6px;
                            background:#0D1018; border: 1px solid #1C2030;
                            border-top: 2px solid {bc};
                            border-radius: 8px; height: 100%;
                        ">
                            <div style="
                                font-size:0.6rem; font-weight:700; letter-spacing:0.1em;
                                text-transform:uppercase; color:#2E3550; margin-bottom:8px;
                            ">{label}</div>
                            {_badge(sig)}
                            <div style="
                                font-size:0.61rem; color:#2E3550; margin-top:8px;
                                line-height:1.45; text-align:left;
                                border-top:1px solid #1C2030; padding-top:6px;
                            ">{explanation}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                t_msg, t_kind = _interpret_ticker(a)
                _render_interpretation_box(t_msg, t_kind)

        # — Tabla final plana —
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(
            '<div class="summary-label" style="margin-bottom:8px;">Vista tabular completa</div>',
            unsafe_allow_html=True,
        )
        df_rows = [
            {
                "Ticker":      a["ticker"],
                "RSI":         a.get("rsi_signal",   "—"),
                "MACD":        a.get("macd_signal",  "—"),
                "Bollinger":   a.get("bb_signal",    "—"),
                "SMA Cross":   a.get("sma_cross",    "—"),
                "Estocástico": a.get("stoch_signal", "—"),
                "Global":      a.get("overall",      "—"),
                "Score":       f"{_calc_score(a):+d}/5",
            }
            for a in alertas_filtradas
        ]
        st.dataframe(pd.DataFrame(df_rows), use_container_width=True, hide_index=True)