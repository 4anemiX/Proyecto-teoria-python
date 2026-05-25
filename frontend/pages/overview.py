import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_activos, fetch_precios, PORTFOLIO_META, TICKERS, BENCHMARK
from utils.theme import ticker_color, COLORS


# ── Bloque educativo reutilizable ─────────────────────────────────────────────

def _info_block(titulo: str, cuerpo: str, color: str = "#3B82F6", icon: str = "ℹ️") -> None:
    st.markdown(
        f'<div style="margin:14px 0;padding:14px 18px;background:#0D1018;'
        f'border:1px solid #1C2030;border-left:3px solid {color};border-radius:0 8px 8px 0;'
        f'font-size:0.83rem;color:#A0AABE;line-height:1.75;">'
        f'<span style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{color};display:block;margin-bottom:6px;">'
        f'{icon} {titulo}</span>'
        f'{cuerpo}</div>',
        unsafe_allow_html=True,
    )


def _interpret_correlation(corr_matrix: pd.DataFrame) -> str:
    pairs = []
    tickers = corr_matrix.columns.tolist()
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            pairs.append((tickers[i], tickers[j], corr_matrix.iloc[i, j]))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    highest = pairs[0]
    lowest  = pairs[-1]
    highly_correlated = [(a, b, c) for a, b, c in pairs if c > 0.7]

    msg = f"<strong>Par más correlacionado:</strong> {highest[0]}–{highest[1]} ({highest[2]:.2f}), "
    if len(highly_correlated) > 1:
        msg += (
            f"junto con {len(highly_correlated) - 1} par(es) adicional(es) con correlación >0.70, "
            "lo que reduce la diversificación efectiva del portafolio. "
            "Activos muy correlacionados se mueven juntos y no compensan las pérdidas del otro. "
        )
    else:
        msg += "sin otros pares con correlación excesiva — diversificación razonable entre activos. "
    msg += (
        f"<strong>Menor correlación:</strong> {lowest[0]}–{lowest[1]} ({lowest[2]:.2f}), "
        "lo que favorece la cobertura natural de riesgo entre estos dos activos. "
        "Una correlación cercana a 0 o negativa es el escenario ideal para reducir la volatilidad del portafolio sin sacrificar retorno."
    )
    return msg


def render():
    st.markdown("""
    <div class="section-title">Vista General del Portafolio</div>
    <div class="section-subtitle">
        Economía Digital y Servicios Globales — empresas que transforman la economía global
        mediante tecnología, datos y servicios financieros.
    </div>
    """, unsafe_allow_html=True)

    # ── Introducción narrativa del portafolio ─────────────────────────────────
    _info_block(
        "Sobre este portafolio",
        "Este tablero analiza un portafolio temático de <strong>seis activos</strong> seleccionados "
        "bajo la narrativa de <em>Economía Digital y Servicios Globales</em>: empresas líderes en "
        "consultoría tecnológica (ACN), nube e inteligencia artificial (MSFT), semiconductores/IA (NVDA), "
        "consumo defensivo (KO) y servicios financieros digitales (JPM), con el ETF del S&P 500 (SPY) "
        "como <strong>benchmark de referencia</strong>. La combinación intencional de activos cíclicos "
        "(NVDA, MSFT) con defensivos (KO) busca equilibrar crecimiento y estabilidad. "
        "Todos los cálculos utilizan datos diarios de Yahoo Finance y una tasa libre de riesgo dinámica (^IRX, T-Bill 3M).",
        color="#6366F1",
        icon="◈",
    )

    fecha_inicio = st.session_state.get("global_start")
    fecha_fin    = st.session_state.get("global_end")

    if fecha_inicio is None or fecha_fin is None:
        st.warning("Configura el período de análisis en el panel lateral.")
        return

    if fecha_inicio >= fecha_fin:
        st.markdown(
            '<div class="interpretation-box negative">'
            'La fecha de inicio debe ser anterior a la fecha fin. '
            'Ajusta el período en el panel lateral.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    start_str = str(fecha_inicio)
    end_str   = str(fecha_fin)
    delta_days = (fecha_fin - fecha_inicio).days

    st.markdown(
        f'<div style="font-size:0.72rem; color:#3B4460; margin-bottom:20px;">'
        f'Período activo: <span style="color:#5A6480;">{start_str}</span> → '
        f'<span style="color:#5A6480;">{end_str}</span> '
        f'<span style="color:#2E3550;">({delta_days:,} días · {delta_days//365} año(s) aprox.)</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tarjetas de precios ───────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:10px;">Precios actuales y variación diaria</div>',
        unsafe_allow_html=True,
    )

    activos = fetch_activos()
    if not activos:
        st.warning("No se pudo conectar con el backend.")
        return

    cols    = st.columns(len(activos))
    bullish = sum(1 for a in activos if a["variacion_diaria"] >= 0)
    bearish = len(activos) - bullish

    for i, a in enumerate(activos):
        is_pos       = a["variacion_diaria"] >= 0
        sign         = "+" if is_pos else ""
        signal_class = "signal-positive" if is_pos else "signal-negative"
        color        = ticker_color(a["ticker"])
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{color};">
                <div class="metric-value" style="color:{color};">${a['precio_actual']:,.2f}</div>
                <div class="metric-label">{a['ticker']}</div>
                <div class="metric-label" style="color:#3B4460;">{a['empresa']}</div>
                <div class="metric-change {signal_class}">{sign}{a['variacion_diaria']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

    sentiment = (
        "predominantemente alcista" if bullish > bearish else
        "mixto"                     if bullish == bearish else
        "predominantemente bajista"
    )
    sentiment_class = (
        "positive" if bullish > bearish else
        "warning"  if bullish == bearish else
        "negative"
    )
    st.markdown(f"""
    <div class="interpretation-box {sentiment_class}" style="margin-top:16px;">
        <strong>Lectura de mercado hoy:</strong> El portafolio muestra un cierre {sentiment},
        con {bullish} activo(s) en verde y {bearish} en rojo.
        {"Una mayoría alcista sugiere momentum positivo en el sector de economía digital."
         if bullish > bearish else
         "La divergencia entre activos sugiere rotación sectorial o factores idiosincráticos — algunos activos defensivos compensan la caída de los cíclicos."
         if bullish != bearish else
         "El equilibrio refleja indecisión del mercado — esperar confirmación de dirección en las próximas sesiones."}
        La variación diaria es solo una instantánea; el análisis de largo plazo se desarrolla
        en los módulos de Rendimientos, CAPM y Markowitz.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Rendimiento normalizado ───────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:#3B4460;margin-bottom:6px;">'
        f'Rendimiento Normalizado — Base 100</div>',
        unsafe_allow_html=True,
    )

    _info_block(
        "Cómo leer este gráfico",
        "Todos los activos se reindexan a <strong>100 en la fecha de inicio</strong> del período seleccionado. "
        "Esto elimina las diferencias de precio absoluto y permite comparar el <em>retorno relativo</em> de cada activo. "
        "Un valor de 150 significa que el activo creció 50% desde el inicio. "
        "El <strong>SPY (línea de referencia)</strong> actúa como benchmark: activos por encima generaron "
        "<em>alpha positivo</em> (superaron al mercado), y los que quedan por debajo, <em>alpha negativo</em>. "
        "Cambia el período de análisis en el panel lateral para explorar diferentes ventanas históricas.",
        color="#6366F1",
        icon="📈",
    )

    fig      = go.Figure()
    all_data = {}

    for ticker in TICKERS + [BENCHMARK]:
        data = fetch_precios(ticker, start=start_str, end=end_str)
        if data and len(data["close"]) > 1:
            closes     = pd.Series(data["close"], index=data["fechas"])
            normalized = closes / closes.iloc[0] * 100
            all_data[ticker] = normalized
            is_bench = ticker == BENCHMARK
            fig.add_trace(go.Scatter(
                x=data["fechas"],
                y=normalized.tolist(),
                name=ticker,
                line=dict(
                    color=ticker_color(ticker),
                    width=2.5 if is_bench else 1.8,
                    dash="dash" if is_bench else "solid",
                ),
                hovertemplate=f"<b>{ticker}</b><br>%{{x}}<br>Base 100: %{{y:.2f}}<extra></extra>",
            ))

    fig.add_hline(y=100, line_dash="dot", line_color="#2E3550", line_width=1, opacity=0.5)
    fig.update_layout(
        height=400,
        title=f"Rendimiento relativo — {start_str} a {end_str} (base 100)",
        yaxis_title="Índice de precio (base 100)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    if all_data:
        final_values = {t: v.iloc[-1] for t, v in all_data.items() if t != BENCHMARK}
        best_ticker  = max(final_values, key=final_values.get)
        worst_ticker = min(final_values, key=final_values.get)
        spy_val      = all_data.get(BENCHMARK, pd.Series([100])).iloc[-1]
        beating_spy  = [t for t, v in final_values.items() if v > spy_val]

        st.markdown(f"""
        <div class="interpretation-box">
            <strong>Mejor desempeño en el período:</strong>
            {best_ticker} con base {final_values[best_ticker]:.1f}
            — retorno acumulado de {final_values[best_ticker]-100:+.1f}%.
            <strong>Menor desempeño:</strong> {worst_ticker}
            con base {final_values[worst_ticker]:.1f}
            ({final_values[worst_ticker]-100:+.1f}% acumulado).
            El benchmark SPY cerró en {spy_val:.1f} ({spy_val-100:+.1f}% acumulado).
            <strong>{len(beating_spy)} de {len(final_values)} activos</strong> superaron al SPY en este período
            ({', '.join(beating_spy) if beating_spy else 'ninguno'}),
            {"lo que indica que el portafolio como conjunto genera alpha frente al mercado."
             if len(beating_spy) >= 3 else
             "lo que sugiere que el índice ha sido difícil de superar — fenómeno frecuente en períodos alcistas sostenidos del S&P 500."}
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Matriz de correlaciones ───────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:6px;">Matriz de Correlaciones</div>',
        unsafe_allow_html=True,
    )

    _info_block(
        "Qué mide la correlación",
        "La correlación de Pearson entre rendimientos diarios va de <strong>−1 a +1</strong>. "
        "Un valor de <strong>+1</strong> significa que los activos se mueven exactamente igual "
        "(perfecta correlación positiva, cero diversificación). "
        "Un valor de <strong>0</strong> indica movimientos independientes — máxima diversificación. "
        "Un valor de <strong>−1</strong> significa que cuando uno sube, el otro baja — "
        "cobertura perfecta. En la práctica, correlaciones <strong>&lt; 0.5</strong> entre activos "
        "son deseables para reducir el riesgo de portafolio sin sacrificar retorno esperado "
        "(principio de Markowitz). Correlaciones <strong>&gt; 0.8</strong> sugieren que los activos "
        "no aportan diversificación real — el portafolio está implícitamente concentrado.",
        color="#8B5CF6",
        icon="🔗",
    )

    prices = {}
    for ticker in TICKERS:
        data = fetch_precios(ticker, start=start_str, end=end_str)
        if data:
            prices[ticker] = data["close"]

    if prices:
        df_prices = pd.DataFrame(prices)
        corr      = df_prices.pct_change().corr()

        purple_scale = [
            [0.0,  "#1a0a2e"],
            [0.25, "#2d1b4e"],
            [0.5,  "#0D1018"],
            [0.75, "#4a2080"],
            [1.0,  "#8b5cf6"],
        ]

        fig2 = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale=purple_scale,
            zmid=0, zmin=-1, zmax=1,
            text=corr.round(2).values,
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=13, family="DM Mono, monospace"),
            showscale=True,
            colorbar=dict(
                thickness=10,
                tickvals=[-1, -0.5, 0, 0.5, 1],
                ticktext=["−1 cobertura", "−0.5", "0 independiente", "+0.5", "+1 sin diversif."],
                tickfont=dict(size=9, color=COLORS["muted"]),
                outlinewidth=0,
            ),
            hovertemplate="%{y} / %{x}<br>Correlación: %{z:.3f}<extra></extra>",
        ))
        fig2.update_layout(
            height=340,
            title="Correlaciones de rendimientos logarítmicos diarios — morado brillante = alta correlación",
        )
        st.plotly_chart(fig2, use_container_width=True)

        interp = _interpret_correlation(corr)
        st.markdown(f'<div class="interpretation-box">{interp}</div>', unsafe_allow_html=True)

        # ── Tabla de resumen de correlaciones ─────────────────────────────────
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:16px 0 8px;">Pares de correlación extrema</div>',
            unsafe_allow_html=True,
        )
        pairs_all = []
        tickers_list = corr.columns.tolist()
        for i in range(len(tickers_list)):
            for j in range(i + 1, len(tickers_list)):
                pairs_all.append({
                    "Par": f"{tickers_list[i]} — {tickers_list[j]}",
                    "Correlación": round(corr.iloc[i, j], 4),
                    "Clasificación": (
                        "Alta (reduce diversificación)" if corr.iloc[i, j] > 0.70 else
                        "Moderada" if corr.iloc[i, j] > 0.40 else
                        "Baja (buena diversificación)" if corr.iloc[i, j] > 0 else
                        "Negativa (cobertura natural)"
                    ),
                })
        pairs_all.sort(key=lambda x: x["Correlación"], reverse=True)
        st.dataframe(pd.DataFrame(pairs_all), use_container_width=True, hide_index=True)