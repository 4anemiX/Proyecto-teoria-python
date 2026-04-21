import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_alertas, fetch_indicadores, TICKERS
from utils.theme import ticker_color, COLORS

# ── Constantes ───────────────────────────────────────────────────────────────

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

IND_EXPLAIN = {
    "rsi_signal": {
        "Compra":      "RSI por debajo de 30: zona de sobreventa. Históricamente precede rebotes alcistas.",
        "Sobreventa":  "RSI en sobreventa extrema (<30). Alta probabilidad de reversión al alza.",
        "Venta":       "RSI supera 70: sobrecompra. El activo puede corregir en el corto plazo.",
        "Sobrecompra": "RSI en sobrecompra extrema (>70). Riesgo de corrección; considerar reducir.",
        "Neutral":     "RSI entre 30 y 70. Sin presión compradora ni vendedora dominante.",
    },
    "macd_signal": {
        "Compra":      "MACD cruzó sobre la señal: momentum alcista activado. EMAs cortas aceleran.",
        "Sobreventa":  "Cruce alcista del MACD desde niveles bajos: recuperación del momentum.",
        "Venta":       "MACD cruzó bajo la señal: pérdida de momentum. Presión bajista creciente.",
        "Sobrecompra": "MACD en niveles altos con posible agotamiento del impulso alcista.",
        "Neutral":     "MACD y señal convergentes. Sin cruce definido ni dirección clara.",
    },
    "bb_signal": {
        "Compra":      "Precio en banda inferior: extensión bajista extrema. Rebote frecuente desde aquí.",
        "Sobreventa":  "Precio bajo banda inferior. Alta probabilidad de rebote hacia la media.",
        "Venta":       "Precio en banda superior: extensión alcista que puede estar agotándose.",
        "Sobrecompra": "Precio sobre banda superior. Posible reversión o consolidación inminente.",
        "Neutral":     "Precio dentro de bandas. Volatilidad contenida, sin señales extremas.",
    },
    "sma_cross": {
        "Compra":      "EMA cruzó sobre SMA: Golden Cross. Señal clásica de cambio a tendencia alcista.",
        "Sobreventa":  "Cruce alcista de medias desde niveles bajos, refuerza señal de recuperación.",
        "Venta":       "EMA cayó bajo SMA: Death Cross. Cambio de tendencia bajista confirmado.",
        "Sobrecompra": "Medias en tendencia alcista pero divergencia con otros indicadores.",
        "Neutral":     "Medias casi alineadas. Tendencia lateral o en transición de fase.",
    },
    "stoch_signal": {
        "Compra":      "Estocástico salió de sobreventa (<20) con cruce alcista. Momentum recuperándose.",
        "Sobreventa":  "Estocástico en sobreventa extrema (<20). Listo para posible rebote técnico.",
        "Venta":       "Estocástico entró en sobrecompra (>80). Momentum alcista puede agotarse.",
        "Sobrecompra": "Estocástico en sobrecompra extrema (>80). Alta probabilidad de corrección.",
        "Neutral":     "Estocástico entre 20 y 80 sin cruces. Momentum neutro sin señal de reversión.",
    },
}

LOOKBACK = 60  # días de historia para mini-gráficas

# ── Helpers ──────────────────────────────────────────────────────────────────

def _badge(signal: str) -> str:
    cls, label = SIGNAL_BADGE.get(signal, ("badge-blue", signal))
    return f'<span class="badge {cls}">{label}</span>'


def _calc_score(a: dict) -> int:
    return sum(SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS)


def _tail(lst: list, n: int = LOOKBACK) -> list:
    """Últimos N valores no-None de una lista."""
    clean = [v for v in (lst or []) if v is not None]
    return clean[-n:]


def _interp_color(kind: str) -> str:
    return {"positive": COLORS["positive"], "negative": COLORS["negative"],
            "warning": COLORS["warning"]}.get(kind, COLORS["muted"])


def _interpret_global(alertas):
    buy  = sum(1 for a in alertas if "Compra" in a.get("overall", ""))
    sell = sum(1 for a in alertas if "Venta"  in a.get("overall", ""))
    neut = len(alertas) - buy - sell
    if buy > sell:
        return (f"Portafolio con sesgo <strong>alcista</strong>: {buy} activo(s) en compra "
                f"frente a {sell} en venta. Condiciones favorables para posiciones largas selectivas.",
                "positive")
    elif sell > buy:
        return (f"Portafolio con sesgo <strong>bajista</strong>: {sell} activo(s) en venta "
                f"frente a {buy} en compra. Considerar reducir exposición o implementar coberturas.",
                "negative")
    return (f"Señales <strong>mixtas</strong> ({neut} neutral, {buy} compra, {sell} venta). "
            "Esperar confirmación de dirección antes de tomar posiciones.", "warning")


def _interpret_ticker(a: dict):
    scores = [SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS]
    total  = sum(scores)
    buy_n  = sum(1 for s in scores if s > 0)
    sell_n = sum(1 for s in scores if s < 0)
    neut_n = sum(1 for s in scores if s == 0)
    conflicting = (
        [IND_LABELS[i] for i, s in enumerate(scores) if s < 0] if total > 0 else
        [IND_LABELS[i] for i, s in enumerate(scores) if s > 0] if total < 0 else []
    )
    if total >= 2:
        msg = f"<strong>Señal alcista consolidada</strong> ({buy_n}/5 indicadores positivos). "
        msg += (f"Señales contrarias en: {', '.join(conflicting)} — monitorear como riesgo de reversión."
                if conflicting else "Convergencia total de indicadores — alta convicción en la dirección.")
        return msg, "positive"
    elif total <= -2:
        msg = f"<strong>Señal bajista consolidada</strong> ({sell_n}/5 indicadores negativos). "
        msg += (f"Señales contrarias en: {', '.join(conflicting)} — posible soporte técnico."
                if conflicting else "Convergencia total a la baja — considerar salida o cobertura.")
        return msg, "negative"
    return (f"<strong>Señal mixta</strong> ({buy_n} alcista, {sell_n} bajista, {neut_n} neutral). "
            "Sin consenso claro — evitar posiciones direccionales hasta confirmar.", "warning")


# ── Mini-gráficas ─────────────────────────────────────────────────────────────

_CHART_H  = 155
_BG       = "rgba(0,0,0,0)"
_AXIS_CLR = "#1C2030"
_FONT_CLR = "#3B4460"
_MARGIN   = dict(l=4, r=4, t=4, b=4)


def _base_layout(height=_CHART_H, yrange=None):
    layout = dict(
        height=height,
        margin=_MARGIN,
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_FONT_CLR, size=9),
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=_AXIS_CLR, zeroline=False,
                   tickfont=dict(size=8, color=_FONT_CLR)),
    )
    if yrange:
        layout["yaxis"]["range"] = yrange
    return layout


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _mini_rsi(ind: dict, signal: str, t_color: str) -> go.Figure:
    rsi = _tail(ind.get("rsi", []))
    x   = list(range(len(rsi)))
    val = rsi[-1] if rsi else 50
    lc  = (COLORS["positive"] if signal in ("Compra", "Sobreventa") else
           COLORS["negative"] if signal in ("Venta", "Sobrecompra") else t_color)

    fig = go.Figure()
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(200,50,50,0.07)",  line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(29,158,117,0.07)", line_width=0)
    for lvl, clr in [(70, COLORS["negative"]), (30, COLORS["positive"]), (50, _FONT_CLR)]:
        fig.add_hline(y=lvl, line_dash="dot", line_color=clr, line_width=1, opacity=0.45)
    fig.add_trace(go.Scatter(
        x=x, y=rsi, mode="lines",
        line=dict(color=lc, width=1.8, shape="spline"),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(lc)},0.07)" if lc.startswith("#") else "rgba(100,150,255,0.07)",
        hovertemplate="RSI: %{y:.1f}<extra></extra>",
    ))
    if rsi:
        fig.add_trace(go.Scatter(
            x=[x[-1]], y=[val], mode="markers+text",
            marker=dict(color=lc, size=6, line=dict(width=1, color="#0D1018")),
            text=[f"{val:.0f}"], textposition="top right",
            textfont=dict(size=9, color=lc),
        ))
    fig.update_layout(**_base_layout(yrange=[0, 100]))
    return fig


def _mini_macd(ind: dict, signal: str, t_color: str) -> go.Figure:
    macd = _tail(ind.get("macd", []))
    msig = _tail(ind.get("macd_signal", []))
    n    = min(len(macd), len(msig))
    macd, msig = macd[-n:], msig[-n:]
    x    = list(range(n))
    hist = [m - s for m, s in zip(macd, msig)]

    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dot", line_color=_FONT_CLR, line_width=1, opacity=0.4)
    fig.add_trace(go.Bar(
        x=x, y=hist,
        marker_color=[COLORS["positive"] if v >= 0 else COLORS["negative"] for v in hist],
        marker_opacity=0.55,
        hovertemplate="Hist: %{y:.4f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(x=x, y=macd, mode="lines",
                             line=dict(color=t_color, width=1.6),
                             hovertemplate="MACD: %{y:.4f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=msig, mode="lines",
                             line=dict(color=COLORS["warning"], width=1.2, dash="dot"),
                             hovertemplate="Señal: %{y:.4f}<extra></extra>"))
    fig.update_layout(**_base_layout())
    return fig


def _mini_bb(ind: dict, signal: str, t_color: str) -> go.Figure:
    close = _tail(ind.get("close",    []))
    upper = _tail(ind.get("bb_upper", []))
    lower = _tail(ind.get("bb_lower", []))
    mid   = _tail(ind.get("bb_mid",   []))
    n     = min(len(close), len(upper), len(lower), len(mid))
    close, upper, lower, mid = close[-n:], upper[-n:], lower[-n:], mid[-n:]
    x     = list(range(n))

    fig = go.Figure()
    # Banda sombreada
    fig.add_trace(go.Scatter(
        x=x + x[::-1], y=upper + lower[::-1],
        fill="toself", fillcolor="rgba(100,100,200,0.06)",
        line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(x=x, y=upper, mode="lines",
                             line=dict(color="#2E3550", width=1, dash="dot"),
                             hovertemplate="BB sup: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=lower, mode="lines",
                             line=dict(color="#2E3550", width=1, dash="dot"),
                             hovertemplate="BB inf: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=mid, mode="lines",
                             line=dict(color="#3B4460", width=1, dash="longdash"),
                             hovertemplate="Media: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=close, mode="lines",
                             line=dict(color=t_color, width=1.8),
                             hovertemplate="Precio: %{y:.2f}<extra></extra>"))
    fig.update_layout(**_base_layout())
    return fig


def _mini_sma(ind: dict, signal: str, t_color: str) -> go.Figure:
    close = _tail(ind.get("close", []))
    ema   = _tail(ind.get("ema",   []))
    sma   = _tail(ind.get("sma",   []))
    n     = min(len(close), len(ema), len(sma))
    close, ema, sma = close[-n:], ema[-n:], sma[-n:]
    x = list(range(n))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=close, mode="lines",
                             line=dict(color=t_color, width=1.8, shape="spline"),
                             hovertemplate="Precio: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=ema, mode="lines",
                             line=dict(color=COLORS["positive"], width=1.3, dash="dot"),
                             hovertemplate="EMA: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=sma, mode="lines",
                             line=dict(color=COLORS["negative"], width=1.3, dash="dash"),
                             hovertemplate="SMA: %{y:.2f}<extra></extra>"))
    if ema and sma:
        label = "▲ EMA > SMA" if signal == "Compra" else "▼ EMA < SMA"
        color = COLORS["positive"] if signal == "Compra" else COLORS["negative"]
        fig.add_annotation(x=n - 1, y=ema[-1], text=label, showarrow=False,
                           font=dict(size=8, color=color), xanchor="right")
    fig.update_layout(**_base_layout())
    return fig


def _mini_stoch(ind: dict, signal: str, t_color: str) -> go.Figure:
    k = _tail(ind.get("stoch_k", []))
    d = _tail(ind.get("stoch_d", []))
    n = min(len(k), len(d))
    k, d = k[-n:], d[-n:]
    x   = list(range(n))
    val = k[-1] if k else 50

    fig = go.Figure()
    fig.add_hrect(y0=80, y1=100, fillcolor="rgba(200,50,50,0.07)",  line_width=0)
    fig.add_hrect(y0=0,  y1=20,  fillcolor="rgba(29,158,117,0.07)", line_width=0)
    for lvl, clr in [(80, COLORS["negative"]), (20, COLORS["positive"]), (50, _FONT_CLR)]:
        fig.add_hline(y=lvl, line_dash="dot", line_color=clr, line_width=1, opacity=0.4)
    fig.add_trace(go.Scatter(x=x, y=k, mode="lines",
                             line=dict(color=t_color, width=1.8),
                             hovertemplate="%%K: %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=d, mode="lines",
                             line=dict(color=COLORS["warning"], width=1.2, dash="dot"),
                             hovertemplate="%%D: %{y:.1f}<extra></extra>"))
    if k:
        fig.add_trace(go.Scatter(
            x=[x[-1]], y=[val], mode="markers+text",
            marker=dict(color=t_color, size=6, line=dict(width=1, color="#0D1018")),
            text=[f"{val:.0f}"], textposition="top right",
            textfont=dict(size=9, color=t_color),
        ))
    fig.update_layout(**_base_layout(yrange=[0, 100]))
    return fig


MINI_CHART_FN = {
    "rsi_signal":   _mini_rsi,
    "macd_signal":  _mini_macd,
    "bb_signal":    _mini_bb,
    "sma_cross":    _mini_sma,
    "stoch_signal": _mini_stoch,
}

CHART_LEGEND = {
    "rsi_signal":   "Verde <30 (sobreventa) · Rojo >70 (sobrecompra)",
    "macd_signal":  "Barras: histograma · Línea: MACD · Puntos: señal",
    "bb_signal":    "Bandas · Media central · Precio del activo",
    "sma_cross":    "Precio · Verde EMA · Rojo SMA",
    "stoch_signal": "%K · %D punteado · Zonas extremas sombreadas",
}


# ── Subcomponentes UI ─────────────────────────────────────────────────────────

def _render_metric_cards(alertas: list):
    buy   = sum(1 for a in alertas if "Compra" in a.get("overall", ""))
    sell  = sum(1 for a in alertas if "Venta"  in a.get("overall", ""))
    neut  = len(alertas) - buy - sell
    scores    = [_calc_score(a) for a in alertas]
    avg_score = sum(scores) / len(scores) if scores else 0

    for col, (label, value, color, icon) in zip(st.columns(4), [
        ("Señales compra",  buy,                COLORS["positive"], "↑"),
        ("Señales venta",   sell,               COLORS["negative"], "↓"),
        ("Neutral",         neut,               COLORS["warning"],  "—"),
        ("Score promedio",  f"{avg_score:+.1f}", COLORS["text"],    "◈"),
    ]):
        with col:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0D1018 0%,#111520 100%);
                        border:1px solid #1C2030;border-top:2px solid {color};
                        border-radius:10px;padding:18px 20px;text-align:center;
                        position:relative;overflow:hidden;">
                <div style="position:absolute;top:10px;right:14px;font-size:1.2rem;
                            color:{color};opacity:0.15;">{icon}</div>
                <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;
                            text-transform:uppercase;color:#3B4460;margin-bottom:8px;">{label}</div>
                <div style="font-size:1.7rem;font-weight:300;font-family:'DM Mono',monospace;
                            color:{color};line-height:1;">{value}</div>
            </div>""", unsafe_allow_html=True)


def _render_interpretation_box(msg: str, kind: str):
    border = _interp_color(kind)
    icon   = {"positive": "▲", "negative": "▼", "warning": "◆"}.get(kind, "●")
    bg     = {"positive": "rgba(29,158,117,0.07)", "negative": "rgba(200,50,50,0.07)",
               "warning": "rgba(230,180,50,0.07)"}.get(kind, "#0D1018")
    st.markdown(f"""
    <div style="background:{bg};border-left:3px solid {border};border-radius:0 10px 10px 0;
                padding:14px 18px;font-size:0.82rem;color:#C8D0E0;margin:12px 0;
                display:flex;align-items:flex-start;gap:10px;">
        <span style="color:{border};font-size:0.7rem;margin-top:2px;flex-shrink:0;">{icon}</span>
        <span>{msg}</span>
    </div>""", unsafe_allow_html=True)


def _render_heatmap(alertas: list):
    tickers_list = [a["ticker"] for a in alertas]
    z    = [[SIGNAL_SCORE.get(a.get(k, "Neutral"), 0) for k in IND_KEYS] for a in alertas]
    text = [[a.get(k, "—") for k in IND_KEYS] for a in alertas]

    colorscale = [
        [0.0,  "#1A0A2E"],
        [0.25, "#3D1A6E"],
        [0.5,  "#1C2030"],
        [0.75, "#7B4FBF"],
        [1.0,  "#B48FFF"],
    ]
    fig = go.Figure(go.Heatmap(
        z=z, x=IND_LABELS, y=tickers_list,
        colorscale=colorscale, zmid=0, zmin=-1, zmax=1,
        text=text, texttemplate="%{text}",
        textfont=dict(size=10, family="DM Sans,sans-serif", color="#E0D8FF"),
        showscale=True,
        colorbar=dict(tickvals=[-1, 0, 1], ticktext=["Venta", "Neutral", "Compra"],
                      tickfont=dict(size=10, color="#8A8FAA"), outlinewidth=0,
                      bgcolor="rgba(0,0,0,0)", len=0.7),
        hovertemplate="<b>%{y}</b> · %{x}<br>Señal: %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=max(280, len(alertas) * 48 + 80),
        title=dict(text="Lila brillante = alcista · Violeta oscuro = bajista · Gris = neutral",
                   font=dict(size=10, color="#3B4460")),
        margin=dict(l=80, r=80, t=52, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8A8FAA"),
        xaxis=dict(side="top", tickfont=dict(size=11, family="DM Sans,sans-serif")),
        yaxis=dict(tickfont=dict(size=11, family="DM Mono,monospace")),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_gauge(ticker: str, score_total: int, t_color: str):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_total,
        title={"text": f"Score técnico — {ticker}", "font": {"size": 11, "color": "#3B4460"}},
        gauge={
            "axis": {"range": [-5, 5], "tickwidth": 1, "tickcolor": "#2E3550",
                     "tickvals": [-5, -3, -1, 0, 1, 3, 5]},
            "bar":  {"color": t_color, "thickness": 0.3},
            "bgcolor": COLORS["surface"],
            "borderwidth": 0,
            "steps": [
                {"range": [-5, -2], "color": "rgba(200,50,50,0.12)"},
                {"range": [-2,  2], "color": "rgba(255,255,255,0.03)"},
                {"range": [ 2,  5], "color": "rgba(29,158,117,0.12)"},
            ],
            "threshold": {"line": {"color": "#3B4460", "width": 1}, "thickness": 0.75, "value": 0},
        },
        number={"font": {"size": 32, "family": "DM Mono,monospace", "color": t_color}, "suffix": "/5"},
    ))
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=60, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#8A8FAA"))
    st.plotly_chart(fig, use_container_width=True)


def _render_compare_chart(alertas: list):
    sorted_a = sorted(alertas, key=_calc_score, reverse=True)
    fig = go.Figure(go.Bar(
        x=[_calc_score(a) for a in sorted_a],
        y=[a["ticker"] for a in sorted_a],
        orientation="h",
        marker=dict(color=[ticker_color(a["ticker"]) for a in sorted_a], opacity=0.85, line=dict(width=0)),
        text=[f"{_calc_score(a):+d}" for a in sorted_a], textposition="outside",
        textfont=dict(size=11, family="DM Mono,monospace", color="#C8D0E0"),
        hovertemplate="<b>%{y}</b><br>Score: %{x:+d}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="#2E3550", opacity=0.8)
    fig.update_layout(
        height=max(280, len(alertas) * 42 + 70),
        xaxis=dict(range=[-5.5, 5.5], title="Score técnico  (–5 bajista · +5 alcista)",
                   tickfont=dict(size=10, color="#3B4460"), color="#3B4460",
                   gridcolor="#111520", zeroline=False),
        yaxis=dict(tickfont=dict(size=12, family="DM Mono,monospace", color="#8A8FAA")),
        margin=dict(l=90, r=70, t=20, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, bargap=0.35, font=dict(color="#8A8FAA"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Panel de indicadores con mini-gráficas reales ────────────────────────────

def _render_indicator_panel(a: dict, ind: dict | None, t_color: str, key_prefix: str = ""):
    """
    5 tarjetas: badge + explicación narrativa + mini-gráfica con datos reales.
    ind es el dict devuelto por fetch_indicadores(); puede ser None si falla.
    """
    cols = st.columns(5)
    for col, key, label in zip(cols, IND_KEYS, IND_LABELS):
        sig       = a.get(key, "Neutral")
        score     = SIGNAL_SCORE.get(sig, 0)
        bar_color = (COLORS["positive"] if score > 0 else
                     COLORS["negative"] if score < 0 else COLORS["warning"])
        explanation = IND_EXPLAIN.get(key, {}).get(sig, "")
        legend      = CHART_LEGEND.get(key, "")

        with col:
            # Cabecera
            st.markdown(f"""
            <div style="padding:12px 10px 8px;
                        background:linear-gradient(160deg,#0D1018 0%,#0F1320 100%);
                        border:1px solid #1C2030;border-top:2px solid {bar_color};
                        border-radius:10px 10px 0 0;">
                <div style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;
                            text-transform:uppercase;color:#3B4460;
                            text-align:center;margin-bottom:8px;">{label}</div>
                <div style="text-align:center;margin-bottom:8px;">{_badge(sig)}</div>
                <div style="font-size:0.63rem;color:#3B4460;line-height:1.45;
                            padding-top:6px;border-top:1px solid #1C2030;">{explanation}</div>
            </div>""", unsafe_allow_html=True)

            # Mini-gráfica
            if ind:
                chart_fn = MINI_CHART_FN.get(key)
                if chart_fn:
                    fig = chart_fn(ind, sig, t_color)
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"{key_prefix}mini_{a['ticker']}_{key}",
                    )
            else:
                st.markdown(
                    '<div style="height:155px;display:flex;align-items:center;'
                    'justify-content:center;background:#0A0D14;'
                    'font-size:0.65rem;color:#2E3550;">sin datos</div>',
                    unsafe_allow_html=True,
                )

            # Leyenda inferior
            st.markdown(f"""
            <div style="padding:6px 10px 8px;background:#0A0D14;
                        border:1px solid #1C2030;border-top:none;border-radius:0 0 10px 10px;">
                <div style="font-size:0.58rem;color:#2E3550;line-height:1.4;">{legend}</div>
            </div>""", unsafe_allow_html=True)


# ── Render principal ──────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div class="section-title">Señales &amp; Alertas</div>
    <div class="section-subtitle">
        Síntesis de señales técnicas por activo — RSI · MACD · Bollinger · SMA Cross · Estocástico
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Cargando señales técnicas..."):
        alertas = fetch_alertas()
    if not alertas:
        st.warning("No se pudieron cargar las alertas.")
        return

    # Métricas resumen
    st.markdown('<div class="summary-label" style="margin-bottom:10px;">Resumen del portafolio</div>',
                unsafe_allow_html=True)
    _render_metric_cards(alertas)
    st.markdown("<br>", unsafe_allow_html=True)
    global_msg, global_kind = _interpret_global(alertas)
    _render_interpretation_box(global_msg, global_kind)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Filtros + exportar
    fil_col, exp_col = st.columns([4, 1])
    with fil_col:
        filtro = st.radio("Filtrar por señal global",
                          ["Todas", "Solo compras", "Solo ventas", "Solo neutral"],
                          horizontal=True, key="signals_filter")
    with exp_col:
        rows_export = [{
            "Ticker": a["ticker"],
            "RSI": a.get("rsi_signal", "—"), "MACD": a.get("macd_signal", "—"),
            "Bollinger": a.get("bb_signal", "—"), "SMA Cross": a.get("sma_cross", "—"),
            "Estocástico": a.get("stoch_signal", "—"), "Global": a.get("overall", "—"),
            "Score": f"{_calc_score(a):+d}/5",
        } for a in alertas]
        st.download_button("Exportar CSV",
                           pd.DataFrame(rows_export).to_csv(index=False).encode("utf-8"),
                           "señales_datarisk.csv", "text/csv",
                           use_container_width=True, key="signals_export")

    filtro_val = {"Todas": None, "Solo compras": "Compra",
                  "Solo ventas": "Venta", "Solo neutral": "Neutral"}[filtro]
    alertas_filtradas = [a for a in alertas
                         if filtro_val is None or filtro_val in a.get("overall", "")]

    if not alertas_filtradas:
        st.info("No hay activos con esa señal en este momento.")
        return

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    tab_detalle, tab_heatmap, tab_comparativa = st.tabs([
        "🔍 Análisis por activo",
        "🟣 Mapa de calor",
        "📊 Comparativa",
    ])

    # ── TAB 1: Análisis por activo con mini-gráficas ──────────────────────────
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
            t_color     = ticker_color(ticker_sel)
            score_total = _calc_score(a)

            # Cabecera del activo
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:16px;padding:16px 20px;
                        margin-bottom:16px;
                        background:linear-gradient(135deg,#0D1018 0%,#111520 100%);
                        border:1px solid #1C2030;border-radius:12px;
                        border-left:3px solid {t_color};">
                <div style="font-family:'DM Mono',monospace;font-size:1.15rem;
                            font-weight:500;color:{t_color};">{ticker_sel}</div>
                <div style="width:1px;height:28px;background:#1C2030;"></div>
                {_badge(a.get('overall', 'Neutral'))}
                <div style="margin-left:auto;font-size:0.7rem;color:#2E3550;
                            font-family:'DM Mono',monospace;">
                    Score: <span style="color:{t_color}">{score_total:+d}</span> / 5
                </div>
            </div>""", unsafe_allow_html=True)

            # Cargar indicadores reales
            with st.spinner(f"Cargando indicadores de {ticker_sel}..."):
                ind = fetch_indicadores(ticker_sel)

            st.markdown('<div class="summary-label" style="margin-bottom:10px;">Indicadores técnicos</div>',
                        unsafe_allow_html=True)
            _render_indicator_panel(a, ind, t_color, key_prefix="tab1_")

            st.markdown("<br>", unsafe_allow_html=True)
            interp_msg, interp_kind = _interpret_ticker(a)
            _render_interpretation_box(interp_msg, interp_kind)
            _render_gauge(ticker_sel, score_total, t_color)

    # ── TAB 2: Mapa de calor lila ─────────────────────────────────────────────
    with tab_heatmap:
        st.markdown('<div class="summary-label" style="margin-bottom:12px;">Mapa de señales del portafolio</div>',
                    unsafe_allow_html=True)
        _render_heatmap(alertas_filtradas)

    # ── TAB 3: Comparativa ────────────────────────────────────────────────────
    with tab_comparativa:
        st.markdown('<div class="summary-label" style="margin-bottom:12px;">Ranking por score técnico</div>',
                    unsafe_allow_html=True)
        _render_compare_chart(alertas_filtradas)
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="summary-label" style="margin-bottom:10px;">Detalle por activo</div>',
                    unsafe_allow_html=True)

        for a in alertas_filtradas:
            ov_color = OVERALL_COLOR.get(a.get("overall", "Neutral"), COLORS["muted"])
            t_color  = ticker_color(a["ticker"])
            score    = _calc_score(a)

            with st.expander(f"{a['ticker']}  ·  {a.get('overall','—')}  ·  Score {score:+d}/5",
                             expanded=False):
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                    <div style="font-family:'DM Mono',monospace;font-size:1rem;
                                font-weight:500;color:{t_color};">{a['ticker']}</div>
                    <div style="width:2px;height:20px;background:{ov_color};border-radius:2px;"></div>
                    {_badge(a.get('overall','Neutral'))}
                    <span style="margin-left:auto;font-size:0.7rem;color:#3B4460;
                                 font-family:'DM Mono',monospace;">
                        Score: <span style="color:{t_color}">{score:+d}</span>/5
                    </span>
                </div>""", unsafe_allow_html=True)

                with st.spinner(f"Cargando gráficas de {a['ticker']}..."):
                    ind_exp = fetch_indicadores(a["ticker"])
                _render_indicator_panel(a, ind_exp, t_color, key_prefix=f"tab3_{a['ticker']}_")

                st.markdown("<br>", unsafe_allow_html=True)
                t_msg, t_kind = _interpret_ticker(a)
                _render_interpretation_box(t_msg, t_kind)

        # Tabla final
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="summary-label" style="margin-bottom:8px;">Vista tabular completa</div>',
                    unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{
            "Ticker": a["ticker"],
            "RSI": a.get("rsi_signal", "—"), "MACD": a.get("macd_signal", "—"),
            "Bollinger": a.get("bb_signal", "—"), "SMA Cross": a.get("sma_cross", "—"),
            "Estocástico": a.get("stoch_signal", "—"), "Global": a.get("overall", "—"),
            "Score": f"{_calc_score(a):+d}/5",
        } for a in alertas_filtradas]), use_container_width=True, hide_index=True)