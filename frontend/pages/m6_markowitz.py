import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_frontera, TICKERS
from utils.theme import ticker_color, COLORS


def _info_block(titulo: str, cuerpo: str, color: str = "#3B82F6", icon: str = "ℹ️") -> None:
    st.markdown(
        f'<div style="margin:10px 0;padding:13px 17px;background:#0D1018;'
        f'border:1px solid #1C2030;border-left:3px solid {color};border-radius:0 8px 8px 0;'
        f'font-size:0.82rem;color:#A0AABE;line-height:1.75;">'
        f'<span style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{color};display:block;margin-bottom:6px;">'
        f'{icon} {titulo}</span>'
        f'{cuerpo}</div>',
        unsafe_allow_html=True,
    )


def render():
    st.markdown("""
    <div class="section-title">Frontera Eficiente de Markowitz</div>
    <div class="section-subtitle">Optimización media-varianza — portafolios de mínima varianza y máximo Sharpe Ratio</div>
    """, unsafe_allow_html=True)

    # ── Introducción conceptual ───────────────────────────────────────────────
    _info_block(
        "Teoría Moderna de Portafolios — Harry Markowitz (1952)",
        "La idea central de Markowitz es que un inversionista racional no evalúa los activos de "
        "forma individual, sino en función de cómo interactúan dentro de un portafolio. "
        "Combinando activos con <strong>baja correlación entre sí</strong>, es posible construir "
        "un portafolio que, para un mismo nivel de riesgo, ofrezca mayor retorno esperado — o para "
        "el mismo retorno, menos riesgo. Este conjunto de portafolios óptimos forma la "
        "<strong>Frontera Eficiente</strong>: la curva que muestra la mejor combinación posible de "
        "riesgo y retorno. Todo portafolio por debajo de la frontera es sub-óptimo — existe una "
        "combinación mejor con el mismo riesgo. En este módulo se calculan dos portafolios especiales: "
        "el de <strong>mínima varianza</strong> (menor volatilidad posible) y el de "
        "<strong>máximo Sharpe</strong> (mejor relación retorno/riesgo).",
        color="#6366F1",
        icon="◈",
    )

    n = len(TICKERS)
    weights = [1 / n] * n

    with st.spinner("Calculando frontera eficiente..."):
        start_str = str(st.session_state["global_start"])
        end_str   = str(st.session_state["global_end"])
        data = fetch_frontera(TICKERS, weights, start=start_str, end=end_str)

    if not data:
        st.warning("No se pudo calcular la frontera eficiente.")
        return

    # ── Métricas rápidas pre-gráfico ──────────────────────────────────────────
    col_mv, col_ms, col_sr = st.columns(3)
    with col_mv:
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{COLORS['positive']};">
            <div class="metric-value" style="color:{COLORS['positive']};">{data['min_var_vol']*100:.2f}%</div>
            <div class="metric-label">Volatilidad mínima alcanzable</div>
            <div style="font-size:0.62rem;color:#3B4460;margin-top:4px;">
                Con la asignación óptima de mínima varianza
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_ms:
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{COLORS['warning']};">
            <div class="metric-value" style="color:{COLORS['warning']};">{data['max_sharpe_return']*100:.2f}%</div>
            <div class="metric-label">Retorno máximo Sharpe (anual)</div>
            <div style="font-size:0.62rem;color:#3B4460;margin-top:4px;">
                Con la asignación de máximo Sharpe Ratio
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_sr:
        sr_color = (COLORS["positive"] if data["max_sharpe_ratio"] > 1
                    else COLORS["warning"] if data["max_sharpe_ratio"] > 0.5
                    else COLORS["negative"])
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{sr_color};">
            <div class="metric-value" style="color:{sr_color};">{data['max_sharpe_ratio']:.3f}</div>
            <div class="metric-label">Sharpe Ratio máximo</div>
            <div style="font-size:0.62rem;color:#3B4460;margin-top:4px;">
                {"Excelente (>1)" if data['max_sharpe_ratio'] > 1 else
                 "Aceptable (0.5–1)" if data['max_sharpe_ratio'] > 0.5 else
                 "Bajo (<0.5) — revisar selección de activos"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gráfico frontera ──────────────────────────────────────────────────────
    _info_block(
        "Cómo leer el gráfico de frontera eficiente",
        "Cada punto de la curva es un portafolio con pesos distintos. "
        "El <strong>eje X es la volatilidad anualizada</strong> (riesgo) y el "
        "<strong>eje Y el retorno esperado anualizado</strong>. "
        "La curva se extiende desde el punto de mínima varianza (extremo izquierdo) hacia portafolios "
        "de mayor retorno pero también mayor riesgo. "
        "El <strong>diamante verde</strong> marca el portafolio de mínima varianza: el punto donde ya no "
        "es posible reducir más el riesgo, independientemente de cómo se redistribuyan los pesos. "
        "La <strong>estrella amarilla</strong> marca el portafolio de máximo Sharpe Ratio — "
        "el que maximiza la unidad de retorno por unidad de riesgo. "
        "La <em>Línea del Mercado de Capitales (CML)</em> partiría de la tasa libre de riesgo "
        "y sería tangente a la frontera justo en el punto de máximo Sharpe.",
        color="#6366F1",
        icon="📈",
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["volatilities"], y=data["returns"],
        mode="lines", name="Frontera Eficiente",
        line=dict(color=COLORS["accent"], width=2.5),
        hovertemplate="Volatilidad: %{x:.2%}<br>Retorno: %{y:.2%}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=[data["min_var_vol"]], y=[data["min_var_return"]],
        mode="markers+text", name="Mínima Varianza",
        marker=dict(color=COLORS["positive"], size=14, symbol="diamond",
                    line=dict(width=2, color=COLORS["positive"])),
        text=["Min Var"], textposition="top right",
        textfont=dict(size=10, family="DM Mono, monospace"),
        hovertemplate=(
            f"Mínima Varianza<br>"
            f"Volatilidad: {data['min_var_vol']:.2%}<br>"
            f"Retorno: {data['min_var_return']:.2%}<extra></extra>"
        ),
    ))

    fig.add_trace(go.Scatter(
        x=[data["max_sharpe_vol"]], y=[data["max_sharpe_return"]],
        mode="markers+text", name=f"Máx. Sharpe ({data['max_sharpe_ratio']:.2f})",
        marker=dict(color=COLORS["warning"], size=14, symbol="star",
                    line=dict(width=2, color=COLORS["warning"])),
        text=["Max Sharpe"], textposition="top right",
        textfont=dict(size=10, family="DM Mono, monospace"),
        hovertemplate=(
            f"Máximo Sharpe<br>"
            f"Sharpe: {data['max_sharpe_ratio']:.3f}<br>"
            f"Volatilidad: {data['max_sharpe_vol']:.2%}<br>"
            f"Retorno: {data['max_sharpe_return']:.2%}<extra></extra>"
        ),
    ))

    fig.update_layout(
        height=480,
        title="Frontera eficiente — portafolios óptimos para el período seleccionado",
        xaxis_title="Volatilidad anual (riesgo)",
        yaxis_title="Rendimiento esperado anual",
        xaxis=dict(tickformat=".1%"),
        yaxis=dict(tickformat=".1%"),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Interpretación dinámica
    sharpe   = data["max_sharpe_ratio"]
    ret_diff = (data["max_sharpe_return"] - data["min_var_return"]) * 100
    vol_diff = (data["max_sharpe_vol"] - data["min_var_vol"]) * 100

    st.markdown(f"""
    <div class="interpretation-box">
        <strong>Trade-off entre los dos portafolios óptimos:</strong>
        El portafolio de máximo Sharpe ({sharpe:.2f}) ofrece
        <strong>{ret_diff:+.2f} pp de retorno adicional</strong> frente al de mínima varianza,
        a costa de <strong>{vol_diff:+.2f} pp de volatilidad adicional</strong>.
        {"Este intercambio es muy favorable — el retorno adicional justifica ampliamente el riesgo extra asumido."
         if ret_diff / vol_diff > 1.5 and vol_diff > 0 else
         "El intercambio es moderado — dependiendo del perfil de riesgo del inversionista, "
         "puede ser preferible el portafolio de mínima varianza." if vol_diff > 0 else
         "Los portafolios son casi idénticos en este período."}
        {" Un Sharpe > 1 es considerado excelente en renta variable — cada unidad de riesgo genera más de una de retorno." if sharpe > 1 else
         " Un Sharpe entre 0.5 y 1 es aceptable para un portafolio de acciones — retorno razonable por unidad de riesgo." if sharpe > 0.5 else
         " Un Sharpe < 0.5 sugiere que el retorno no compensa la volatilidad — revisar si la selección de activos es adecuada para el período."}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Composición de los portafolios ────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:6px;">'
        'Composición Óptima de los Portafolios</div>',
        unsafe_allow_html=True,
    )

    _info_block(
        "Cómo interpretar los pesos óptimos",
        "Los pesos representan la fracción del capital que el algoritmo de optimización asigna a cada activo. "
        "El portafolio de <strong>mínima varianza</strong> tiende a concentrar en activos "
        "<em>defensivos y de baja volatilidad histórica</em> (típicamente KO y JPM en este portafolio). "
        "El de <strong>máximo Sharpe</strong> concentra en el activo con la mejor relación "
        "retorno/riesgo en el período analizado — puede variar significativamente con el tiempo. "
        "Pesos muy concentrados (&gt;60% en un solo activo) indican <em>baja diversificación efectiva</em>. "
        "Nota: estos pesos son óptimos <em>ex-post</em> para el período seleccionado — "
        "no garantizan el mismo desempeño en períodos futuros (riesgo de sobreajuste).",
        color="#8B5CF6",
        icon="⚖️",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            '<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">'
            'Portafolio Mínima Varianza</div>',
            unsafe_allow_html=True,
        )
        mv_c1, mv_c2 = st.columns(2)
        mv_c1.metric("Retorno anual", f"{data['min_var_return']*100:.2f}%")
        mv_c2.metric("Volatilidad anual", f"{data['min_var_vol']*100:.2f}%")

        mv_w = {k: v for k, v in data["min_var_weights"].items() if v > 0.001}
        fig2 = go.Figure(go.Pie(
            labels=list(mv_w.keys()),
            values=list(mv_w.values()),
            marker_colors=[ticker_color(t) for t in mv_w],
            hole=0.5,
            textfont=dict(size=11, family="DM Mono, monospace"),
            hovertemplate="%{label}: %{percent}<extra></extra>",
        ))
        fig2.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=True,
            legend=dict(font=dict(size=10)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown(
            '<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">'
            'Portafolio Máximo Sharpe</div>',
            unsafe_allow_html=True,
        )
        ms_c1, ms_c2, ms_c3 = st.columns(3)
        ms_c1.metric("Retorno anual", f"{data['max_sharpe_return']*100:.2f}%")
        ms_c2.metric("Volatilidad anual", f"{data['max_sharpe_vol']*100:.2f}%")
        ms_c3.metric("Sharpe Ratio", f"{data['max_sharpe_ratio']:.3f}")

        ms_w = {k: v for k, v in data["max_sharpe_weights"].items() if v > 0.001}
        fig3 = go.Figure(go.Pie(
            labels=list(ms_w.keys()),
            values=list(ms_w.values()),
            marker_colors=[ticker_color(t) for t in ms_w],
            hole=0.5,
            textfont=dict(size=11, family="DM Mono, monospace"),
            hovertemplate="%{label}: %{percent}<extra></extra>",
        ))
        fig3.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=True,
            legend=dict(font=dict(size=10)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Interpretación de concentración
    dominant_mv = max(data["min_var_weights"], key=data["min_var_weights"].get)
    dominant_ms = max(data["max_sharpe_weights"], key=data["max_sharpe_weights"].get)
    w_mv_dom    = data["min_var_weights"][dominant_mv] * 100
    w_ms_dom    = data["max_sharpe_weights"][dominant_ms] * 100

    st.markdown(f"""
    <div class="interpretation-box">
        <strong>Concentración:</strong>
        El portafolio de mínima varianza está dominado por
        <strong>{dominant_mv}</strong> ({w_mv_dom:.1f}%),
        que históricamente tiene la menor volatilidad relativa en este portafolio.
        El portafolio de máximo Sharpe concentra en
        <strong>{dominant_ms}</strong> ({w_ms_dom:.1f}%),
        que ofrece la mejor relación retorno/riesgo en el período analizado.
        {"Una concentración del " + f"{w_mv_dom:.0f}%" + " en un solo activo limita la diversificación — "
         "considera ampliar el universo de activos o restringir el peso máximo por activo al 40–50%."
         if w_mv_dom > 60 or w_ms_dom > 60 else
         "La concentración está dentro de rangos razonables — ambos portafolios mantienen "
         "diversificación efectiva entre los activos del portafolio."}
        Recuerda que estos pesos son óptimos para el período histórico seleccionado y
        deben rebalancearse periódicamente a medida que cambien las condiciones de mercado.
    </div>
    """, unsafe_allow_html=True)

    # ── Tabla comparativa de pesos ────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin:16px 0 8px;">'
        'Tabla comparativa de pesos óptimos</div>',
        unsafe_allow_html=True,
    )

    rows = []
    for t in TICKERS:
        w_mv = data["min_var_weights"].get(t, 0) * 100
        w_ms = data["max_sharpe_weights"].get(t, 0) * 100
        rows.append({
            "Ticker": t,
            "Peso Mín. Varianza": f"{w_mv:.2f}%",
            "Peso Máx. Sharpe": f"{w_ms:.2f}%",
            "Diferencia (pp)": f"{w_ms - w_mv:+.2f}",
            "Mayor peso en": "Mín. Varianza" if w_mv > w_ms else ("Máx. Sharpe" if w_ms > w_mv else "Igual"),
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)