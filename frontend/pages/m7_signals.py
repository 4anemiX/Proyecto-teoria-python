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
        ("Señales compra",  buy_count,  COLORS["positive"]),
        ("Señales venta",   sell_count, COLORS["negative"]),
        ("Neutral",         neut_count, COLORS["warning"]),
        ("Score promedio",  f"{avg_score:+.1f}", COLORS["text"]),
    ]
    for col, (label, value, color) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""<div style="background:#0D1018;border:1px solid #1C2030;border-radius:8px;
                                padding:14px 16px;text-align:center;">
                    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.08em;
                                text-transform:uppercase;color:#2E3550;margin-bottom:6px;">{label}</div>
                    <div style="font-size:1.5rem;font-weight:500;font-family:'DM Mono',monospace;
                                color:{color};">{value}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _render_interpretation_box(msg: str, kind: str):
    border_color = _interp_color(kind)
    bg = {
        "positive": "rgba(29,158,117,0.08)",
        "negative": "rgba(200,50,50,0.08)",
        "warning":  "rgba(230,180,50,0.08)",
    }.get(kind, "#0D1018")
    st.markdown(
        f"""<div style="background:{bg};border-left:3px solid {border_color};
                        border-radius:0 8px 8px 0;padding:12px 16px;
                        font-size:0.82rem;color:{COLORS['text']};margin:12px 0;">
            {msg}
        </div>""",
        unsafe_allow_html=True,
    )


def _render_heatmap(alertas: list):
    tickers_list = [a["ticker"] for a in alertas]
    z    = [[SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS] for a in alertas]
    text = [[a.get(k, "—") for k in IND_KEYS] for a in alertas]

    fig = go.Figure(go.Heatmap(
        z=z, x=IND_LABELS, y=tickers_list,
        colorscale=[[0, "#2E0D10"], [0.5, "#0D1018"], [1, "#0D2E20"]],
        zmid=0, zmin=-1, zmax=1,
        text=text, texttemplate="%{text}",
        textfont=dict(size=10, family="DM Sans, sans-serif"),
        showscale=False,
        hovertemplate="<b>%{y}</b> · %{x}<br>Señal: %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=max(240, len(alertas) * 42 + 60),
        title=dict(
            text="Verde = alcista · Rojo = bajista · Gris = neutral",
            font=dict(size=11, color=COLORS["muted"]),
        ),
        margin=dict(l=70, r=20, t=48, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["muted"]),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_gauge(ticker: str, score_total: int):
    bar_color = (
        COLORS["positive"] if score_total > 0 else
        COLORS["negative"] if score_total < 0 else
        COLORS["warning"]
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_total,
        title={"text": f"Score técnico — {ticker}", "font": {"size": 12, "color": COLORS["muted"]}},
        gauge={
            "axis": {"range": [-5, 5], "tickwidth": 1, "tickcolor": COLORS["muted"]},
            "bar":  {"color": bar_color},
            "bgcolor": COLORS["surface"],
            "borderwidth": 0,
            "steps": [
                {"range": [-5, -2], "color": "#2E0D10"},
                {"range": [-2,  2], "color": "#1C2030"},
                {"range": [ 2,  5], "color": "#0D2E20"},
            ],
            "threshold": {
                "line": {"color": COLORS["muted"], "width": 2},
                "thickness": 0.75,
                "value": 0,
            },
        },
        number={"font": {"size": 28, "family": "DM Mono, monospace", "color": COLORS["text"]}},
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=30, r=30, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["muted"]),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_compare_chart(alertas: list):
    sorted_alertas = sorted(alertas, key=_calc_score, reverse=True)
    tickers  = [a["ticker"] for a in sorted_alertas]
    scores   = [_calc_score(a) for a in sorted_alertas]
    colors   = [
        COLORS["positive"] if s > 0 else COLORS["negative"] if s < 0 else COLORS["warning"]
        for s in scores
    ]

    fig = go.Figure(go.Bar(
        x=scores,
        y=tickers,
        orientation="h",
        marker_color=colors,
        text=[f"{s:+d}" for s in scores],
        textposition="outside",
        textfont=dict(size=11, family="DM Mono, monospace", color=COLORS["text"]),
        hovertemplate="<b>%{y}</b><br>Score: %{x:+d}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color=COLORS["muted"], opacity=0.5)
    fig.update_layout(
        height=max(260, len(alertas) * 36 + 60),
        xaxis=dict(range=[-5.5, 5.5], title="Score técnico (-5 a +5)",
                   tickfont=dict(size=10), color=COLORS["muted"]),
        yaxis=dict(tickfont=dict(size=11, family="DM Mono, monospace"), color=COLORS["muted"]),
        margin=dict(l=80, r=60, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(color=COLORS["muted"]),
    )
    st.plotly_chart(fig, use_container_width=True)


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
        "🗺 Mapa de calor",
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
            <div style="display:flex;align-items:center;gap:16px;padding:14px 18px;
                        background:#0D1018;border:1px solid #1C2030;border-radius:10px;
                        border-left:3px solid {t_color};margin-bottom:14px;">
                <div style="font-family:'DM Mono',monospace;font-size:1.1rem;
                            font-weight:500;color:{t_color};">{ticker_sel}</div>
                <div style="width:2px;height:24px;background:{overall_color};border-radius:2px;"></div>
                {_badge(a.get('overall','Neutral'))}
                <div style="margin-left:auto;font-size:0.75rem;color:#3B4460;">
                    Score técnico: {score_total:+d} / 5
                </div>
            </div>
            """, unsafe_allow_html=True)

            # — Indicadores —
            st.markdown('<div class="summary-label" style="margin-bottom:8px;">Indicadores técnicos</div>',
                        unsafe_allow_html=True)
            cols = st.columns(5)
            for col, key, label in zip(cols, IND_KEYS, IND_LABELS):
                sig   = a.get(key, "Neutral")
                score = SIGNAL_SCORE.get(sig, 0)
                bar_color = (
                    COLORS["positive"] if score > 0 else
                    COLORS["negative"] if score < 0 else
                    COLORS["warning"]
                )
                with col:
                    st.markdown(f"""
                    <div style="text-align:center;padding:12px 6px;
                                background:#0D1018;border:1px solid #1C2030;
                                border-top:2px solid {bar_color};
                                border-radius:8px;height:100%;">
                        <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.08em;
                                    text-transform:uppercase;color:#2E3550;margin-bottom:8px;">
                            {label}
                        </div>
                        {_badge(sig)}
                        <div style="font-size:0.62rem;color:#2E3550;margin-top:8px;line-height:1.4;">
                            {IND_DESC[key]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # — Interpretación específica + gauge —
            interp_msg, interp_kind = _interpret_ticker(a)
            _render_interpretation_box(interp_msg, interp_kind)
            _render_gauge(ticker_sel, score_total)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 2 — Mapa de calor
    # ────────────────────────────────────────────────────────────────────────
    with tab_heatmap:
        st.markdown('<div class="summary-label" style="margin-bottom:12px;">Mapa de señales del portafolio</div>',
                    unsafe_allow_html=True)
        _render_heatmap(alertas_filtradas)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 3 — Comparativa
    # ────────────────────────────────────────────────────────────────────────
    with tab_comparativa:
        st.markdown('<div class="summary-label" style="margin-bottom:12px;">Ranking por score técnico</div>',
                    unsafe_allow_html=True)
        _render_compare_chart(alertas_filtradas)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="summary-label" style="margin-bottom:10px;">Tabla resumen — todos los activos</div>',
                    unsafe_allow_html=True)

        # — Expanders por activo (del código 2) —
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
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                    <div style="font-family:'DM Mono',monospace;font-size:1rem;
                                font-weight:500;color:{t_color};">{a['ticker']}</div>
                    <div style="width:3px;height:20px;background:{ov_color};border-radius:2px;"></div>
                    {_badge(a.get('overall','Neutral'))}
                    <span style="margin-left:auto;font-size:0.72rem;color:#3B4460;">
                        Score: {score:+d}/5
                    </span>
                </div>
                """, unsafe_allow_html=True)

                ind_cols = st.columns(len(indicators))
                for col, (key, label) in zip(ind_cols, indicators):
                    sig = a.get(key, "Neutral")
                    with col:
                        st.markdown(f"""
                        <div style="text-align:center;padding:10px 4px;
                                    background:#0D1018;border:1px solid #1C2030;border-radius:8px;">
                            <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.08em;
                                        text-transform:uppercase;color:#2E3550;margin-bottom:6px;">
                                {label}
                            </div>
                            {_badge(sig)}
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                t_msg, t_kind = _interpret_ticker(a)
                _render_interpretation_box(t_msg, t_kind)

        # — Tabla final plana (del código 2, con score añadido del código 1) —
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="summary-label" style="margin-bottom:8px;">Vista tabular completa</div>',
                    unsafe_allow_html=True)
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