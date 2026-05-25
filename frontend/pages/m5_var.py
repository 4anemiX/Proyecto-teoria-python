import streamlit as st
import plotly.graph_objects as go
import numpy as np
from data.client import fetch_var, fetch_rendimientos, TICKERS
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


def _interpret_var(data: dict, ticker: str, confidence: float) -> tuple[str, str]:
    vp   = data["var_parametric"]   * 100
    vh   = data["var_historical"]   * 100
    vm   = data["var_montecarlo"]   * 100
    cvar = data["cvar"]             * 100
    kupiec_ok = data["kupiec_pval"] > 0.05

    spread    = max(vp, vh, vm) - min(vp, vh, vm)
    consensus = np.mean([vp, vh, vm])

    msg = (
        f"Con un nivel de confianza del <strong>{confidence*100:.0f}%</strong>, "
        f"el VaR consenso para <strong>{ticker}</strong> es de "
        f"<strong>{consensus:.3f}%</strong> diario. "
        f"Traducido: en condiciones normales de mercado, existe solo un "
        f"{(1-confidence)*100:.0f}% de probabilidad de que las pérdidas de un día "
        f"superen este umbral. "
    )

    if spread < 0.1:
        msg += (
            f"Los tres métodos convergen en un rango de {spread:.3f}pp — "
            "alta consistencia del estimador, los supuestos distribucionales son adecuados para este activo. "
        )
        css = "positive"
    elif spread < 0.3:
        msg += (
            f"Divergencia moderada de {spread:.3f}pp entre métodos. "
            "El VaR histórico captura mejor las colas gruesas si los rendimientos no son normales. "
        )
        css = "warning"
    else:
        msg += (
            f"Divergencia significativa de {spread:.3f}pp entre métodos — "
            "el activo probablemente tiene distribución no normal con colas pesadas. "
            "El VaR paramétrico podría subestimar el riesgo real; preferir el histórico o Montecarlo. "
        )
        css = "negative"

    msg += (
        f"El <strong>CVaR (Expected Shortfall) de {cvar:.3f}%</strong> representa la pérdida "
        f"<em>promedio esperada</em> cuando sí se supera el VaR — siempre mayor al VaR y "
        f"más informativo en contextos de crisis donde las colas importan. "
    )

    if kupiec_ok:
        msg += (
            f"El test de Kupiec valida el modelo estadísticamente "
            f"(p={data['kupiec_pval']:.4f} > 0.05): el número de excepciones históricas "
            f"es consistente con lo que predice el modelo al {confidence*100:.0f}% de confianza."
        )
    else:
        msg += (
            f"El test de Kupiec <strong>rechaza el modelo</strong> "
            f"(p={data['kupiec_pval']:.4f} < 0.05): hay más excepciones reales de las esperadas "
            f"— el VaR subestima el riesgo. Considerar aumentar el nivel de confianza o usar CVaR."
        )
        css = "negative"

    return msg, css


def render():
    st.markdown("""
    <div class="section-title">VaR &amp; CVaR</div>
    <div class="section-subtitle">Value at Risk paramétrico, histórico y Montecarlo — Expected Shortfall y backtesting de Kupiec</div>
    """, unsafe_allow_html=True)

    # ── Introducción conceptual ───────────────────────────────────────────────
    _info_block(
        "¿Qué es el Value at Risk (VaR)?",
        "El <strong>VaR</strong> responde a: <em>\"¿Cuánto podría perder este activo en un día malo?\"</em> "
        "Un VaR de 2% al 95% significa que, en el 95% de los días, la pérdida no superará el 2%. "
        "Solo en el 5% restante (los peores días) la pérdida será mayor. "
        "Este tablero calcula tres versiones: "
        "<strong>(1) Paramétrico</strong>: asume que los rendimientos siguen una distribución normal — "
        "rápido pero puede subestimar en activos con colas gruesas; "
        "<strong>(2) Histórico</strong>: usa directamente los rendimientos pasados sin supuestos distribucionales — "
        "más robusto ante no-normalidad; "
        "<strong>(3) Montecarlo</strong>: simula miles de trayectorias aleatorias de precio — "
        "el más flexible pero computacionalmente intensivo.",
        color="#6366F1",
        icon="⚠️",
    )

    col1, col2, col3 = st.columns(3)
    ticker      = col1.selectbox("Activo", TICKERS)
    confidence  = col2.slider("Nivel de confianza", 0.90, 0.99, 0.95, 0.01, format="%.2f")
    simulations = col3.select_slider("Simulaciones Montecarlo", [1000, 5000, 10000, 50000], 10000)

    # Nota sobre nivel de confianza
    st.markdown(
        f'<div style="font-size:0.75rem;color:#3B4460;margin-bottom:12px;">'
        f'Nivel seleccionado: <strong style="color:#A0AABE;">{confidence*100:.0f}%</strong> — '
        f'esto significa que el VaR cubre el {confidence*100:.0f}% de los peores días históricos. '
        f'Reguladores como Basilea III requieren mínimo el 99% para capital en riesgo. '
        f'El {(1-confidence)*100:.0f}% de los días restantes (las excepciones) son capturados por el CVaR.</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Calculando VaR..."):
        start_str = str(st.session_state["global_start"])
        end_str   = str(st.session_state["global_end"])
        data = fetch_var(ticker, confidence, simulations, start=start_str, end=end_str)

    if not data:
        st.warning("No se pudieron calcular los modelos VaR.")
        return

    color = ticker_color(ticker)

    # ── Tarjetas VaR ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">'
        'Estimaciones de riesgo diario</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    var_items = [
        ("VaR Paramétrico",    data["var_parametric"],  COLORS["negative"], c1,
         "Basado en media y desviación estándar — asume normalidad"),
        ("VaR Histórico",      data["var_historical"],  COLORS["warning"],  c2,
         "Percentil directo de los rendimientos pasados reales"),
        ("VaR Montecarlo",     data["var_montecarlo"],  "#A78BFA",          c3,
         f"Basado en {simulations:,} simulaciones de trayectorias aleatorias"),
        ("CVaR / Exp. Shortfall", data["cvar"],         "#F43F5E",          c4,
         "Pérdida promedio esperada en los peores días — siempre > VaR"),
    ]
    for label, val, col_c, col, desc in var_items:
        with col:
            st.markdown(f"""
            <div class="metric-card" style="--card-accent:{col_c};">
                <div class="metric-value" style="color:{col_c}; font-size:1.3rem;">{val*100:.3f}%</div>
                <div class="metric-label">{label}</div>
                <div style="font-size:0.62rem;color:#3B4460;margin-top:4px;line-height:1.4;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Backtesting de Kupiec ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">'
        'Validación del modelo — Test de Kupiec</div>',
        unsafe_allow_html=True,
    )

    kupiec_ok    = data["kupiec_pval"] > 0.05
    kupiec_color = COLORS["positive"] if kupiec_ok else COLORS["negative"]

    k1, k2 = st.columns(2)
    with k1:
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{kupiec_color};">
            <div class="metric-value" style="color:{kupiec_color}; font-size:1.2rem;">{data['kupiec_stat']:.4f}</div>
            <div class="metric-label">Kupiec LR Estadístico</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="metric-card" style="--card-accent:{kupiec_color};">
            <div class="metric-value" style="color:{kupiec_color}; font-size:1.2rem;">{data['kupiec_pval']:.4f}</div>
            <div class="metric-label">Kupiec p-valor</div>
            <div class="metric-change" style="color:{kupiec_color};">{"✔ Modelo estadísticamente válido" if kupiec_ok else "✖ Revisar supuestos del modelo"}</div>
        </div>
        """, unsafe_allow_html=True)

    _info_block(
        "Test de Kupiec — validación del backtesting",
        "El <strong>test de Kupiec (1995)</strong> verifica si el número de veces que las pérdidas reales "
        "superaron el VaR histórico es estadísticamente consistente con el nivel de confianza elegido. "
        f"A un {confidence*100:.0f}% de confianza, se espera que el VaR sea violado en exactamente "
        f"el <strong>{(1-confidence)*100:.0f}%</strong> de los días. "
        "Si hay demasiadas excepciones, el modelo subestima el riesgo (error tipo II). "
        "Un <strong>p-valor &gt; 0.05</strong> indica que las excepciones observadas son estadísticamente "
        "normales y el modelo es adecuado. Un p-valor &lt; 0.05 rechaza el modelo — "
        "señal de que los supuestos distribucionales no se ajustan bien a la realidad del activo.",
        color=kupiec_color,
        icon="🧪",
    )

    # Interpretación narrativa
    interp_msg, interp_class = _interpret_var(data, ticker, confidence)
    st.markdown(
        f'<div class="interpretation-box {interp_class}" style="margin-top:16px;">{interp_msg}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Distribución con líneas VaR ───────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:6px;">'
        'Distribución de Rendimientos y Umbrales de Pérdida</div>',
        unsafe_allow_html=True,
    )

    _info_block(
        "Cómo leer este histograma",
        "Cada barra representa qué tan frecuente fue un rango de rendimiento diario en el período analizado. "
        "La cola izquierda (rendimientos muy negativos) refleja los días de pérdidas extremas. "
        "Las <strong>líneas verticales punteadas</strong> marcan los umbrales de cada método de VaR: "
        "todo lo que queda a la izquierda de cada línea son las pérdidas que ese método <em>no cubre</em> "
        "(las excepciones). El <strong>CVaR</strong> (línea roja) siempre está más a la izquierda — "
        "cubre las pérdidas más extremas y representa el promedio de lo que ocurre en los peores escenarios. "
        "Si la distribución es asimétrica (cola izquierda más larga), los métodos paramétricos subestimarán el riesgo real.",
        color="#6366F1",
        icon="📊",
    )

    ret_data = fetch_rendimientos(ticker, start=start_str, end=end_str)
    if ret_data:
        rets = [r for r in ret_data["logaritmicos"] if r is not None]
        fig  = go.Figure()

        fig.add_trace(go.Histogram(
            x=rets, nbinsx=80, name="Rendimientos diarios",
            marker_color=color, opacity=0.55,
            hovertemplate="Rendimiento: %{x:.4f}<br>Frecuencia: %{y}<extra></extra>",
        ))

        var_lines = [
            (data["var_parametric"], f"VaR Paramétrico ({data['var_parametric']*100:.3f}%)", COLORS["negative"]),
            (data["var_historical"], f"VaR Histórico ({data['var_historical']*100:.3f}%)",   COLORS["warning"]),
            (data["var_montecarlo"], f"VaR Montecarlo ({data['var_montecarlo']*100:.3f}%)",  "#A78BFA"),
            (data["cvar"],           f"CVaR ({data['cvar']*100:.3f}%)",                       "#F43F5E"),
        ]
        for val, label, lcolor in var_lines:
            fig.add_vline(
                x=val, line_dash="dot", line_color=lcolor, line_width=1.5,
                annotation_text=label,
                annotation_font=dict(size=9, color=lcolor),
                annotation_position="top right",
            )

        fig.update_layout(
            height=400,
            title=f"Distribución de rendimientos diarios y umbrales de pérdida — {ticker} (confianza {confidence*100:.0f}%)",
            xaxis_title="Rendimiento logarítmico diario",
            yaxis_title="Frecuencia (número de días)",
            hovermode="x",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Estadísticas de la distribución de rendimientos como contexto
        arr = np.array(rets)
        n_excepciones_var_h = int(np.sum(arr < data["var_historical"]))
        pct_excep = n_excepciones_var_h / len(arr) * 100

        st.markdown(f"""
        <div class="interpretation-box">
            <strong>Excepciones históricas (VaR histórico):</strong>
            En el período analizado, las pérdidas superaron el VaR histórico en
            <strong>{n_excepciones_var_h} de {len(arr)} días</strong>
            ({pct_excep:.2f}% del tiempo).
            A un nivel de confianza del {confidence*100:.0f}%, se esperaba que esto ocurriera en
            el {(1-confidence)*100:.1f}% de los días ({int(len(arr)*(1-confidence))} días).
            {"La tasa de excepciones es similar a lo esperado — el modelo es consistente."
             if abs(pct_excep - (1-confidence)*100) < 1 else
             "La tasa de excepciones difiere de lo esperado — revisa el test de Kupiec arriba."}
        </div>
        """, unsafe_allow_html=True)