import streamlit as st
import plotly.graph_objects as go
from data.client import fetch_curva_rendimiento, fetch_bono
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
    <div class="section-title">Renta Fija</div>
    <div class="section-subtitle">Curva de rendimiento Nelson-Siegel · Duración · Convexidad · Sensibilidad de precio</div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📈 Curva de Rendimiento", "🔖 Valoración de Bono"])

    # ─────────────────────────────────────────────────────────────────────────
    with tab1:

        _info_block(
            "La curva de rendimiento del Tesoro de EE.UU.",
            "La <strong>curva de rendimiento</strong> (yield curve) muestra la tasa de interés "
            "que el mercado exige a los bonos del Tesoro de EE.UU. según su plazo de vencimiento. "
            "Normalmente tiene <em>pendiente positiva</em>: plazos más largos ofrecen mayores tasas "
            "para compensar la incertidumbre del tiempo. Cuando se <strong>invierte</strong> "
            "(tasas cortas &gt; tasas largas), históricamente anticipa recesiones económicas — "
            "el mercado descuenta que las tasas bajarán en el futuro por menor actividad. "
            "Una curva <strong>plana</strong> indica transición e incertidumbre. "
            "Los datos se obtienen en tiempo real de la <strong>FRED (Federal Reserve Bank of St. Louis)</strong> "
            "y se ajustan con el modelo de Nelson-Siegel, que suaviza la curva y permite extraer "
            "parámetros interpretables sobre nivel, pendiente y curvatura.",
            color="#6366F1",
            icon="📐",
        )

        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:12px 0 8px;">'
            'Tasas del Tesoro US (FRED) — ajuste Nelson-Siegel</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("Descargando tasas desde FRED..."):
            data = fetch_curva_rendimiento()

        if not data:
            st.warning("No se pudo obtener la curva de rendimiento. Verifica FRED_API_KEY.")
            return

        shape     = data.get("shape", "")
        shape_msg = data.get("shape_interpretation", "")
        color_shape = {
            "normal":    COLORS["positive"],
            "invertida": COLORS["negative"],
            "plana":     COLORS["warning"],
        }.get(shape, COLORS["muted"])

        st.markdown(
            f"<div class='insight-box' style='border-color:{color_shape}'>"
            f"<strong>Forma de la curva: {shape.upper()}</strong><br>{shape_msg}</div>",
            unsafe_allow_html=True,
        )

        # Gráfico
        pts   = data["curve_points"]
        obs_x = data["maturities_obs"]
        obs_y = data["yields_obs_pct"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pts["tau_ns"], y=pts["yield_ns"],
            mode="lines", name="Curva Nelson-Siegel (ajuste)",
            line=dict(color=COLORS["accent"], width=2.5),
            hovertemplate="Plazo: %{x:.2f} años<br>Tasa: %{y:.3f}%<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=obs_x, y=obs_y,
            mode="markers", name="Tasas observadas (FRED)",
            marker=dict(color=COLORS["warning"], size=10, symbol="circle"),
            hovertemplate="Plazo: %{x:.2f} años<br>Tasa observada: %{y:.3f}%<extra></extra>",
        ))
        fig.add_hline(
            y=obs_y[0] if obs_y else 5,
            line_dash="dot", line_color="#2E3550", line_width=1, opacity=0.5,
            annotation_text="Tasa corta", annotation_font=dict(size=9, color="#3B4460"),
        )
        fig.update_layout(
            xaxis_title="Vencimiento (años)",
            yaxis_title="Tasa de rendimiento (%)",
            legend=dict(orientation="h", y=1.08),
            margin=dict(t=40, b=40),
            paper_bgcolor=COLORS["surface"],
            plot_bgcolor=COLORS["bg"],
            font=dict(color=COLORS["text"]),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Parámetros Nelson-Siegel con explicación ──────────────────────────
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:12px 0 8px;">'
            'Parámetros del modelo Nelson-Siegel</div>',
            unsafe_allow_html=True,
        )

        _info_block(
            "Qué significan los parámetros β₀, β₁, β₂ y λ",
            "<strong>β₀ (nivel de largo plazo):</strong> Es la tasa a la que converge la curva "
            "cuando el plazo tiende a infinito — representa la inflación esperada de largo plazo "
            "más la prima por riesgo permanente. "
            "<strong>β₁ (pendiente):</strong> Controla la diferencia entre tasas largas y cortas. "
            "Negativo indica curva con pendiente positiva (normal); positivo indica curva invertida. "
            "<strong>β₂ (curvatura):</strong> Captura si la curva tiene forma de joroba — "
            "positivo indica tasas intermedias más altas que las extremas (curva con corcova). "
            "<strong>λ (velocidad de decaimiento):</strong> Determina en qué plazo se alcanza "
            "el máximo efecto de la curvatura. Un λ mayor desplaza ese máximo hacia plazos más cortos.",
            color="#8B5CF6",
            icon="🔢",
        )

        ns    = data["nelson_siegel"]
        col1, col2, col3, col4 = st.columns(4)
        params = [
            ("β₀ — Nivel LP", ns["beta0"], "Tasa de largo plazo", col1),
            ("β₁ — Pendiente", ns["beta1"], "Inclinación de la curva (−: positiva)", col2),
            ("β₂ — Curvatura", ns["beta2"], "Concavidad / joroba intermedia", col3),
            ("λ — Decaimiento", ns["lambda"], "Velocidad de ajuste al LP", col4),
        ]
        for label, val, desc, col in params:
            val_color = (COLORS["positive"] if val > 0 else COLORS["negative"])
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="color:{val_color}; font-size:1.1rem;">{val:.4f}</div>
                    <div class="metric-label">{label}</div>
                    <div style="font-size:0.61rem;color:#3B4460;margin-top:4px;line-height:1.4;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        # Interpretación dinámica de la forma
        beta1 = ns["beta1"]
        beta2 = ns["beta2"]
        beta0 = ns["beta0"]

        st.markdown(f"""
        <div class="interpretation-box" style="margin-top:12px;">
            <strong>Lectura de los parámetros actuales:</strong>
            La tasa de largo plazo estimada es <strong>{beta0:.2f}%</strong>
            {"— nivel moderado, consistente con expectativas de inflación controlada."
             if beta0 < 5 else
             "— nivel elevado, sugiere expectativas de inflación persistente o prima de riesgo alta."}.
            La pendiente (β₁ = {beta1:.4f})
            {"es negativa, lo que implica curva con pendiente positiva — escenario normal de expansión económica."
             if beta1 < 0 else
             "es positiva, indicando curva invertida — señal histórica de desaceleración o recesión próxima."}.
            {f"La curvatura (β₂ = {beta2:.4f}) indica una joroba en los plazos intermedios, "
             f"lo que puede reflejar expectativas de un ciclo de tasas con punto de inflexión en el mediano plazo."
             if abs(beta2) > 0.5 else
             f"La curvatura (β₂ = {beta2:.4f}) es baja — la curva es relativamente suave sin corcova marcada."}
        </div>
        """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    with tab2:

        _info_block(
            "Conceptos clave: Duración, Convexidad y Sensibilidad",
            "La <strong>Duración de Macaulay</strong> es el promedio ponderado del tiempo hasta "
            "cada flujo de caja del bono — mide en años cuándo recupera el inversionista su capital. "
            "La <strong>Duración Modificada</strong> es la más usada en práctica: indica el "
            "<em>porcentaje de cambio en el precio del bono ante un cambio de 1% en la tasa (YTM)</em>. "
            "Un bono con duración modificada de 7 pierde aproximadamente 7% de valor si las tasas "
            "suben 100 pb. La <strong>Convexidad</strong> corrige esta aproximación lineal: "
            "los bonos con más convexidad pierden menos ante subidas de tasa y ganan más ante bajadas "
            "(siempre deseable). La <strong>sensibilidad al precio</strong> modela estos efectos "
            "bajo diferentes shocks de tasa — herramienta esencial para gestión de riesgo en portafolios "
            "de renta fija y para el módulo de Stress Testing.",
            color="#6366F1",
            icon="🔖",
        )

        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin-bottom:10px;">'
            'Parámetros del bono sintético</div>',
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4, col5 = st.columns(5)
        face_value     = col1.number_input("Valor nominal ($)", 100.0, 1_000_000.0, 1000.0, 100.0)
        coupon_rate    = col2.slider("Cupón anual (%)", 0.0, 20.0, 5.0, 0.25) / 100
        maturity_years = col3.slider("Vencimiento (años)", 1, 30, 10)
        frequency      = col4.selectbox("Pagos/año", [1, 2, 4, 12], index=1,
                                        help="1=anual, 2=semestral, 4=trimestral, 12=mensual")
        ytm            = col5.slider("YTM (%)", 0.01, 20.0, 5.0, 0.25) / 100

        # Nota de contexto sobre la relación cupón/YTM
        precio_estimado = "par" if abs(coupon_rate - ytm) < 0.001 else (
            "sobre par (prima)" if coupon_rate > ytm else "bajo par (descuento)"
        )
        st.markdown(
            f'<div style="font-size:0.74rem;color:#3B4460;margin-bottom:10px;">'
            f'Cupón {coupon_rate*100:.2f}% vs YTM {ytm*100:.2f}% — '
            f'el bono se negocia a <strong style="color:#A0AABE;">{precio_estimado}</strong>. '
            f'Cuando el cupón &gt; YTM el precio supera el nominal; cuando cupón &lt; YTM, '
            f'el precio cae bajo el nominal.</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("Calculando métricas del bono..."):
            bond = fetch_bono(face_value, coupon_rate, maturity_years, frequency, ytm)

        if not bond:
            st.warning("Error al calcular las métricas del bono.")
            return

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precio", f"${bond['price']:,.2f}",
                    delta=f"{(bond['price']/face_value - 1)*100:+.2f}% vs nominal")
        col2.metric("Duración Macaulay", f"{bond['macaulay_duration']:.4f} años")
        col3.metric("Duración Modificada", f"{bond['modified_duration']:.4f}",
                    help="Sensibilidad porcentual del precio ante 1% de cambio en tasas")
        col4.metric("Convexidad", f"{bond['convexity']:.4f}",
                    help="Corrección de segundo orden — mayor convexidad = mejor comportamiento")

        # ── Sensibilidad a shocks ─────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:14px 0 6px;">'
            'Sensibilidad del precio a shocks de tasa</div>',
            unsafe_allow_html=True,
        )

        _info_block(
            "Cómo leer la tabla de sensibilidad",
            "La columna <strong>Δ Precio (duración)</strong> usa solo la duración modificada "
            "para estimar el cambio de precio — es la aproximación de primer orden (línea recta). "
            "La columna <strong>Δ Precio (dur. + convexidad)</strong> añade la corrección cuadrática "
            "de la convexidad — más precisa, especialmente en shocks grandes (&gt;100 pb). "
            "El <strong>precio exacto</strong> recalcula el valor presente de todos los flujos "
            "bajo la nueva tasa — es la referencia real. La diferencia entre el precio exacto y "
            "la aproximación muestra la magnitud del error si se ignora la convexidad.",
            color="#8B5CF6",
            icon="📋",
        )

        sens = bond.get("price_sensitivity", {})
        if sens:
            shocks = sorted(
                sens.keys(),
                key=lambda x: int(x.replace("shock_", "").replace("bp", "").replace("+", "")),
            )
            rows = []
            for s in shocks:
                info = sens[s]
                rows.append({
                    "Shock de tasa": f"{info['delta_ytm_bp']:+.0f} pb",
                    "Precio exacto ($)": f"${info['price_exact']:,.4f}",
                    "Δ Precio duración": f"${info['dp_linear']:,.4f}",
                    "Δ Precio dur.+conv.": f"${info['dp_convex']:,.4f}",
                    "Cambio % exacto": f"{info['pct_exact']:+.4f}%",
                    "Error aprox. (dur. sola)": f"${abs(info['price_exact'] - (bond['price'] + info['dp_linear'])):,.4f}",
                })

            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Gráfico de sensibilidad
            delta_ytm_bp = [sens[s]["delta_ytm_bp"] for s in shocks]
            dp_exact     = [sens[s]["pct_exact"] for s in shocks]
            dp_convex    = [sens[s]["pct_convex"] for s in shocks]
            dp_linear    = [sens[s]["pct_linear"] for s in shocks]

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=delta_ytm_bp, y=dp_exact,
                mode="lines+markers", name="Precio exacto (valor real)",
                line=dict(color=COLORS["accent"], width=2.5),
                marker=dict(size=7),
            ))
            fig2.add_trace(go.Scatter(
                x=delta_ytm_bp, y=dp_convex,
                mode="lines+markers", name="Aprox. duración + convexidad",
                line=dict(color=COLORS["warning"], width=1.8, dash="dot"),
                marker=dict(size=5),
            ))
            fig2.add_trace(go.Scatter(
                x=delta_ytm_bp, y=dp_linear,
                mode="lines", name="Aprox. solo duración (lineal)",
                line=dict(color=COLORS["negative"], width=1.2, dash="dash"),
            ))
            fig2.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"], line_width=1)
            fig2.update_layout(
                xaxis_title="Shock de tasa (puntos básicos)",
                yaxis_title="Cambio en precio (%)",
                title="Relación precio–tasa: curvatura real vs aproximaciones lineales y cuadráticas",
                legend=dict(orientation="h", y=1.08),
                margin=dict(t=50, b=40),
                paper_bgcolor=COLORS["surface"],
                plot_bgcolor=COLORS["bg"],
                font=dict(color=COLORS["text"]),
                hovermode="x unified",
            )
            st.plotly_chart(fig2, use_container_width=True)

            d_mod = bond["modified_duration"]
            conv  = bond["convexity"]
            precio = bond["price"]

            # Calcular el error máximo de solo usar duración
            max_shock = max(delta_ytm_bp, key=abs)
            max_exact  = sens[shocks[-1]]["pct_exact"] if delta_ytm_bp[-1] == max_shock else sens[shocks[0]]["pct_exact"]
            max_linear = sens[shocks[-1]]["pct_linear"] if delta_ytm_bp[-1] == max_shock else sens[shocks[0]]["pct_linear"]
            error_dur = abs(max_exact - max_linear)

            st.markdown(f"""
            <div class="interpretation-box">
                <strong>Interpretación de duración y convexidad:</strong><br>
                Con duración modificada de <strong>{d_mod:.4f}</strong>, un alza de
                <strong>100 pb</strong> en la tasa reduciría el precio aproximadamente
                <strong>{d_mod:.2f}%</strong> usando solo la aproximación lineal.
                La convexidad de <strong>{conv:.4f}</strong> significa que esta estimación
                <em>sobreestima la pérdida</em> ante subidas de tasa y
                <em>subestima la ganancia</em> ante bajadas — la relación real es convexa, no lineal.
                Para el shock más extremo analizado ({max_shock:+.0f} pb), ignorar la convexidad
                generaría un error de <strong>{error_dur:.4f} pp</strong> en la estimación del cambio porcentual.
                {"Este error es pequeño — la duración sola es suficiente para shocks moderados."
                 if error_dur < 0.5 else
                 "Este error es significativo — siempre incluir la convexidad para shocks mayores a 100 pb."}
            </div>
            """, unsafe_allow_html=True)