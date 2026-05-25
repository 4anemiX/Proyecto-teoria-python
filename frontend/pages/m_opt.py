import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_opcion, fetch_opcion_curvas, TICKERS
from utils.theme import COLORS


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
    <div class="section-title">Opciones Europeas — Black-Scholes</div>
    <div class="section-subtitle">Valoración · Greeks · Paridad put-call · Volatilidad implícita</div>
    """, unsafe_allow_html=True)

    # ── Introducción conceptual ───────────────────────────────────────────────
    _info_block(
        "El modelo de Black-Scholes (1973)",
        "El modelo de <strong>Black-Scholes-Merton</strong> es el estándar para valorar opciones europeas. "
        "Una opción es un contrato que da el <em>derecho, pero no la obligación</em>, de comprar (<strong>call</strong>) "
        "o vender (<strong>put</strong>) un activo a un precio predeterminado (strike K) en una fecha futura. "
        "El modelo asume que el precio del activo sigue un proceso de movimiento browniano geométrico "
        "con volatilidad constante σ. El precio de la opción depende de cinco factores: "
        "<strong>S</strong> (precio actual), <strong>K</strong> (strike), <strong>T</strong> (tiempo al vencimiento), "
        "<strong>r</strong> (tasa libre de riesgo) y <strong>σ</strong> (volatilidad implícita). "
        "Las opciones son instrumentos de cobertura y especulación ampliamente usados en mercados financieros.",
        color="#6366F1",
        icon="◈",
    )

    # ── Parámetros ────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">'
        'Parámetros de la opción</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    S     = col1.number_input("S — Precio subyacente", 1.0, 10000.0, 100.0, 1.0,
                               help="Precio actual del activo en el mercado")
    K     = col2.number_input("K — Strike", 1.0, 10000.0, 100.0, 1.0,
                               help="Precio al que se ejercerá la opción")
    T     = col3.slider("T — Tiempo (años)", 0.01, 5.0, 1.0, 0.01,
                         help="Tiempo restante al vencimiento en años")
    r     = col4.slider("r — Tasa libre (%)", 0.0, 20.0, 5.0, 0.25) / 100
    sigma = col5.slider("σ — Volatilidad (%)", 1.0, 150.0, 20.0, 1.0) / 100
    tipo  = col6.selectbox("Tipo", ["call", "put"])

    # Contexto de los parámetros seleccionados
    moneyness = S / K
    if moneyness > 1.05:
        mon_label = "In-the-money (ITM)" if tipo == "call" else "Out-of-the-money (OTM)"
        mon_color = COLORS["positive"] if tipo == "call" else COLORS["negative"]
    elif moneyness < 0.95:
        mon_label = "Out-of-the-money (OTM)" if tipo == "call" else "In-the-money (ITM)"
        mon_color = COLORS["negative"] if tipo == "call" else COLORS["positive"]
    else:
        mon_label = "At-the-money (ATM)"
        mon_color = COLORS["warning"]

    st.markdown(
        f'<div style="font-size:0.74rem;color:#3B4460;margin:8px 0 14px;">'
        f'Moneyness S/K = <strong style="color:{mon_color};">{moneyness:.3f} ({mon_label})</strong> · '
        f'σ anual {sigma*100:.1f}% · T = {T:.2f} años · r = {r*100:.2f}% · Tipo: {tipo.upper()}</div>',
        unsafe_allow_html=True,
    )

    market_price = st.number_input(
        "Precio de mercado observado (opcional — para calcular volatilidad implícita)",
        min_value=0.0, value=0.0, step=0.01,
        help="Si conoces el precio de mercado de la opción, deja aquí el valor para calcular la vol. implícita",
    )
    market_price_val = market_price if market_price > 0 else None

    with st.spinner("Valorando opción..."):
        data   = fetch_opcion(S, K, T, r, sigma, tipo, market_price_val)
        curvas = fetch_opcion_curvas(S, K, T, r, sigma, tipo)

    if not data:
        st.warning("Error al valorar la opción.")
        return

    # ── Métricas principales ──────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">'
        'Resultado Black-Scholes</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    price_color = COLORS["positive"] if data["price"] > 0 else COLORS["muted"]
    col1.metric(f"Precio {tipo.upper()}", f"${data['price']:.4f}")
    col2.metric("d₁", f"{data['d1']:.4f}", help="Probabilidad ajustada de ejercicio call (distribución normal estándar)")
    col3.metric("d₂", f"{data['d2']:.4f}", help="Probabilidad de que la opción expire in-the-money bajo la medida risk-neutral")

    _info_block(
        "Qué son d₁ y d₂",
        f"<strong>d₁ = {data['d1']:.4f}</strong>: representa la probabilidad ajustada de que el call sea ejercido, "
        "ponderada por el precio del activo subyacente. N(d₁) es el delta de la opción call. "
        f"<strong>d₂ = {data['d2']:.4f}</strong>: es la probabilidad (bajo medida risk-neutral) de que la opción "
        "expire en-el-dinero, es decir, que S > K al vencimiento para un call. "
        f"N(d₂) = {max(0, min(1, data['d2']))*100:.1f}% es la probabilidad de ejercicio. "
        "La diferencia d₁ − d₂ = σ√T refleja el efecto de la volatilidad sobre la distribución de precios futuros.",
        color="#6366F1",
        icon="🔢",
    )

    # ── Greeks ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin:14px 0 4px;">'
        'Las Griegas — sensibilidades del precio</div>',
        unsafe_allow_html=True,
    )

    _info_block(
        "¿Para qué sirven las Griegas?",
        "Las <strong>Griegas</strong> cuantifican cómo varía el precio de la opción ante pequeños cambios "
        "en cada parámetro — son las herramientas fundamentales para gestionar riesgos en portafolios de opciones. "
        "<strong>Delta (Δ)</strong>: cambio del precio de la opción por cada $1 de cambio en S — también indica la "
        "cantidad de activo subyacente necesaria para cubrir (hedgear) la opción. "
        "<strong>Gamma (Γ)</strong>: velocidad de cambio del Delta — alto gamma implica que el Delta cambia "
        "rápidamente con el precio (especialmente ATM y cerca del vencimiento). "
        "<strong>Vega (ν)</strong>: sensibilidad al cambio en volatilidad — cuánto cambia el precio ante un 1% de "
        "cambio en σ. <strong>Theta (Θ)</strong>: caída diaria del valor de la opción por el paso del tiempo "
        "(time decay) — generalmente negativo para el comprador. "
        "<strong>Rho (ρ)</strong>: sensibilidad a cambios en la tasa de interés.",
        color="#8B5CF6",
        icon="⚙️",
    )

    g = data["greeks"]
    col1, col2, col3, col4, col5 = st.columns(5)

    greek_items = [
        ("Δ Delta",  g["delta"],  f"Por cada $1↑ en S, la opción cambia ${g['delta']:.4f}", col1),
        ("Γ Gamma",  g["gamma"],  f"El Delta cambia {g['gamma']:.6f} por cada $1 en S", col2),
        ("ν Vega",   g["vega"],   f"Por cada 1% de σ, la opción cambia ${g['vega']:.4f}", col3),
        ("Θ Theta",  g["theta"],  f"La opción pierde ${abs(g['theta']):.4f} por día por el tiempo", col4),
        ("ρ Rho",    g["rho"],    f"Por cada 1% de tasa, la opción cambia ${g['rho']:.4f}", col5),
    ]

    for label, val, desc, col in greek_items:
        val_color = (COLORS["positive"] if val > 0 else
                     COLORS["negative"] if val < 0 else COLORS["muted"])
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{val_color}; font-size:1.05rem;">{val:.4f}</div>
                <div class="metric-label">{label}</div>
                <div style="font-size:0.61rem;color:#3B4460;margin-top:4px;line-height:1.4;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("📖 Interpretación detallada de cada griega para este escenario"):
        for greek, interp in g.get("interpretation", {}).items():
            st.markdown(f"**{greek}**: {interp}")

    # ── Paridad put-call ──────────────────────────────────────────────────────
    parity = data.get("parity", {})
    if parity:
        ok    = parity.get("parity_holds", False)
        color = COLORS["positive"] if ok else COLORS["negative"]
        label = "✅ Paridad put-call verificada" if ok else "⚠️ Paridad put-call no verificada"
        error = parity.get("error", 0)

        st.markdown(
            f"<div class='insight-box' style='border-color:{color};margin-top:14px;'>"
            f"<strong>{label}</strong><br>"
            f"LHS (C − P): {parity.get('lhs_C_minus_P', 0):.4f} | "
            f"RHS (S − Ke⁻ʳᵀ): {parity.get('rhs_S_minus_Ke', 0):.4f} | "
            f"Error: {error:.6f}</div>",
            unsafe_allow_html=True,
        )

        _info_block(
            "La paridad put-call",
            "La relación <strong>C − P = S − Ke⁻ʳᵀ</strong> es una identidad fundamental: el precio de un "
            "call menos el put del mismo strike y vencimiento debe igualar el precio del activo menos el "
            "valor presente del strike. Si no se cumple, existe una oportunidad de arbitraje libre de riesgo. "
            f"En este caso, el error es de <strong>{error:.6f}</strong> — "
            f"{'prácticamente cero, confirma que el modelo es internamente consistente.' if ok else 'hay una discrepancia detectable, posiblemente por supuestos simplificados del modelo o insumos imprecisos.'}",
            color=color,
            icon="⚖️",
        )

    # ── Volatilidad implícita ─────────────────────────────────────────────────
    if data.get("implied_vol"):
        iv = data["implied_vol"]
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:14px 0 4px;">'
            'Volatilidad Implícita</div>',
            unsafe_allow_html=True,
        )

        _info_block(
            "¿Qué es la volatilidad implícita?",
            "La <strong>volatilidad implícita (IV)</strong> es la volatilidad que, al introducirla en el modelo "
            "Black-Scholes, reproduce exactamente el precio de mercado observado. "
            "A diferencia de la volatilidad histórica (calculada con datos pasados), la IV es "
            "<em>forward-looking</em>: refleja lo que el mercado espera que ocurra con la volatilidad "
            "del activo hasta el vencimiento. Si la IV &gt; σ ingresada, la opción está más cara de lo "
            "que predice el modelo con tu supuesto de volatilidad — el mercado es más pesimista. "
            "Comparar la IV entre opciones de mismo activo pero distintos strikes genera la "
            "<em>sonrisa de volatilidad</em> — fenómeno que el modelo B-S clásico no puede explicar.",
            color="#F59E0B",
            icon="🔭",
        )

        col1, col2, col3 = st.columns(3)
        iv_val = iv.get("sigma_implicita_pct", 0)
        diff   = iv_val - sigma * 100
        col1.metric("σ implícita del mercado", f"{iv_val:.2f}%")
        col2.metric("σ ingresada en el modelo", f"{sigma*100:.2f}%")
        col3.metric(
            "Diferencia",
            f"{diff:+.2f} pp",
            delta=f"{'Mercado más volátil' if diff > 0 else 'Mercado menos volátil que modelo'}",
        )

    # ── Curvas de payoff y delta ──────────────────────────────────────────────
    if curvas:
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:14px 0 4px;">'
            'Curvas de Payoff y Delta</div>',
            unsafe_allow_html=True,
        )

        _info_block(
            "Cómo leer las curvas de payoff y delta",
            "El <strong>gráfico de payoff</strong> muestra dos cosas: la línea sólida (<em>payoff al vencimiento</em>) "
            "es la ganancia/pérdida si se ejerce en T — forma el ángulo recto característico de las opciones. "
            "La línea punteada (<em>precio Black-Scholes</em>) es el valor actual de la opción antes del vencimiento "
            "— siempre mayor que el payoff al vencimiento por el valor temporal (time value). "
            "El <strong>gráfico de delta</strong> muestra cómo varía el Delta con el precio del subyacente: "
            "para un call, Delta → 0 cuando S &lt;&lt; K (OTM) y Delta → 1 cuando S &gt;&gt; K (ITM). "
            "Cerca del strike (ATM), Delta ≈ 0.5. Las líneas adicionales muestran el efecto del tiempo "
            "sobre la curva de Delta (el Delta se vuelve más pronunciado cerca del vencimiento).",
            color="#6366F1",
            icon="📉",
        )

        col1, col2 = st.columns(2)

        with col1:
            payoff = curvas.get("payoff_curve", {})
            spots  = payoff.get("spots", [])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=spots, y=payoff.get("payoffs", []),
                mode="lines", name="Payoff al vencimiento (T)",
                line=dict(color=COLORS["accent"], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=spots, y=payoff.get("prices", []),
                mode="lines", name="Precio Black-Scholes (hoy)",
                line=dict(color=COLORS["warning"], width=2, dash="dash"),
            ))
            fig.add_vline(x=K, line_dash="dot", line_color=COLORS["muted"],
                          annotation_text=f"Strike K={K}",
                          annotation_position="top right",
                          annotation_font=dict(size=9))
            fig.add_hline(y=0, line_dash="dot", line_color="#2E3550", line_width=1)
            fig.update_layout(
                title=f"Payoff del {tipo.upper()} — vencimiento vs valor actual",
                xaxis_title="Precio del subyacente ($)",
                yaxis_title="Valor / Ganancia ($)",
                margin=dict(t=40, b=40),
                paper_bgcolor=COLORS["surface"],
                plot_bgcolor=COLORS["bg"],
                font=dict(color=COLORS["text"]),
                legend=dict(font=dict(size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            delta_c      = curvas.get("delta_curve", {})
            spots_d      = delta_c.get("spots", [])
            delta_curves = delta_c.get("delta_curves", {})

            fig2 = go.Figure()
            colors_list = [COLORS["positive"], COLORS["warning"], COLORS["accent"]]
            for i, (label, vals) in enumerate(delta_curves.items()):
                fig2.add_trace(go.Scatter(
                    x=spots_d, y=vals,
                    mode="lines", name=f"Delta {label}",
                    line=dict(
                        color=colors_list[i % len(colors_list)],
                        width=2.5 if i == 0 else 1.2,
                        dash="solid" if i == 0 else "dot",
                    ),
                ))
            fig2.add_vline(x=K, line_dash="dot", line_color=COLORS["muted"],
                           annotation_text=f"K={K}",
                           annotation_font=dict(size=9))
            fig2.add_hline(y=0.5, line_dash="dot", line_color=COLORS["muted"],
                           opacity=0.4,
                           annotation_text="Delta=0.5 (ATM)",
                           annotation_font=dict(size=9, color=COLORS["muted"]))
            fig2.add_hline(y=0, line_dash="dot", line_color=COLORS["muted"])
            fig2.update_layout(
                title="Delta vs precio subyacente — por horizonte temporal",
                xaxis_title="Precio del subyacente ($)",
                yaxis_title="Delta",
                margin=dict(t=40, b=40),
                paper_bgcolor=COLORS["surface"],
                plot_bgcolor=COLORS["bg"],
                font=dict(color=COLORS["text"]),
                legend=dict(font=dict(size=10)),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Interpretación dinámica
        delta_val = g["delta"]
        theta_val = g["theta"]
        vega_val  = g["vega"]

        st.markdown(f"""
        <div class="interpretation-box">
            <strong>Lectura de este escenario ({tipo.upper()}, S={S}, K={K}, T={T:.2f}a, σ={sigma*100:.0f}%):</strong><br>
            La opción tiene un Delta de <strong>{delta_val:.4f}</strong>: por cada $1 de movimiento en el
            subyacente, el precio de la opción cambia ${abs(delta_val):.4f}
            {"en la misma dirección." if tipo == "call" else "(inversamente para el put)."}<br>
            El Theta de <strong>{theta_val:.4f}</strong> indica que la opción pierde
            ${abs(theta_val):.4f} de valor cada día por el paso del tiempo (time decay).
            Con {T:.2f} años al vencimiento, el costo total de time decay estimado es
            ~${abs(theta_val) * T * 365:.2f} si σ y S no cambian.<br>
            Vega = <strong>{vega_val:.4f}</strong>: si la volatilidad implícita del mercado
            sube 1%, la opción se encarece ${vega_val:.4f}.
            {"A mayor tiempo al vencimiento, mayor Vega — las opciones largas son más sensibles a cambios de volatilidad."
             if T > 0.5 else
             "Con poco tiempo al vencimiento, el Vega es bajo — la opción ya es principalmente valor intrínseco."}
        </div>
        """, unsafe_allow_html=True)