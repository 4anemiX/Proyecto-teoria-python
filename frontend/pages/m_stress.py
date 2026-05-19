import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.client import fetch_stress, TICKERS
from utils.theme import COLORS, ticker_color


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sev_color(val: float) -> str:
    if val < -20: return "#F43F5E"
    if val < -10: return COLORS["negative"]
    if val < -5:  return COLORS["warning"]
    if val < 0:   return "#FBBF24"
    return COLORS["positive"]


def _badge(val: float) -> str:
    color = _sev_color(val)
    bg    = "rgba(248,113,113,0.10)" if val < 0 else "rgba(52,211,153,0.10)"
    arrow = "▼" if val < 0 else "▲"
    return (
        f'<span style="font-family:\'DM Mono\',monospace;font-size:0.8rem;font-weight:600;'
        f'color:{color};background:{bg};padding:2px 8px;border-radius:4px;">'
        f'{arrow} {val:.2f}%</span>'
    )


def _mini_card(label: str, value: str, color: str) -> str:
    return f"""
    <div style="background:#0D1018;border:1px solid #1C2030;border-top:2px solid {color};
                border-radius:8px;padding:14px 16px;text-align:center;">
        <div style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
                    color:#3B4460;margin-bottom:6px;">{label}</div>
        <div style="font-family:'DM Mono',monospace;font-size:1rem;font-weight:500;
                    color:{color};">{value}</div>
    </div>"""


def _interp_box(texto: str, color: str = "#3B82F6", icon: str = "💡") -> None:
    st.markdown(
        f'<div style="margin:12px 0;padding:14px 18px;background:#0D1018;'
        f'border:1px solid #1C2030;border-left:3px solid {color};border-radius:0 8px 8px 0;'
        f'font-size:0.83rem;color:#A0AABE;line-height:1.7;">'
        f'<span style="font-size:1rem;margin-right:8px;">{icon}</span>{texto}</div>',
        unsafe_allow_html=True,
    )


# ── Interpretaciones automáticas ───────────────────────────────────────────────

def _interpretar_resumen(results: list) -> None:
    """Interpretación global de todos los escenarios."""
    # Filtrar escenario base si existe
    stress_results = [r for r in results if r.get("scenario", "") != "Base (sin estrés)"]
    base = next((r for r in results if r.get("scenario", "") == "Base (sin estrés)"), None)

    rets  = [r.get("portfolio_return_pct", 0) for r in stress_results]
    names = [r.get("scenario", "") for r in stress_results]

    if not rets:
        return

    peor_ret  = min(rets)
    peor_name = names[rets.index(peor_ret)]
    mejor_ret = max(rets)
    mejor_name = names[rets.index(mejor_ret)]
    n_severos = sum(1 for v in rets if v < -10)
    n_totales = len(rets)

    # Severidad general
    if peor_ret < -25:
        severidad = "alta vulnerabilidad"
        sev_color = "#F43F5E"
        sev_icon  = "🔴"
    elif peor_ret < -10:
        severidad = "vulnerabilidad moderada"
        sev_color = COLORS["warning"]
        sev_icon  = "🟡"
    else:
        severidad = "resiliencia aceptable"
        sev_color = COLORS["positive"]
        sev_icon  = "🟢"

    texto = (
        f"El portafolio muestra <strong style='color:{sev_color}'>{severidad}</strong> ante shocks extremos. "
        f"En el peor escenario (<em>{peor_name}</em>), el portafolio perdería "
        f"<strong style='color:{_sev_color(peor_ret)}'>{peor_ret:.2f}%</strong> de su valor. "
    )

    if base:
        base_ret = base.get("portfolio_return_pct", 0)
        diff = peor_ret - base_ret
        texto += (
            f"Comparado con el escenario base sin estrés ({base_ret:+.2f}%), "
            f"el impacto adicional del peor shock es de <strong>{diff:.2f} pp</strong>. "
        )

    texto += (
        f"De los {n_totales} escenarios de estrés, "
        f"<strong>{n_severos}</strong> generan pérdidas superiores al 10%. "
        f"El escenario menos severo es <em>{mejor_name}</em> con {mejor_ret:.2f}%."
    )

    _interp_box(texto, sev_color, sev_icon)


def _interpretar_heatmap(results: list, tickers_sel: list) -> None:
    """Interpretación del mapa de calor: activos más y menos vulnerables."""
    stress_results = [r for r in results if r.get("scenario", "") != "Base (sin estrés)"]
    if not stress_results:
        return

    # Promedio de retorno por ticker a través de todos los escenarios
    avg_by_ticker: dict[str, list] = {t: [] for t in tickers_sel}
    for r in stress_results:
        for a in r.get("assets", []):
            t = a["ticker"]
            if t in avg_by_ticker:
                avg_by_ticker[t].append(a["return_pct"])

    avgs = {t: (sum(v) / len(v) if v else 0) for t, v in avg_by_ticker.items()}
    if not avgs:
        return

    mas_vulnerable  = min(avgs, key=avgs.get)
    menos_vulnerable = max(avgs, key=avgs.get)

    texto = (
        f"<strong style='color:{ticker_color(mas_vulnerable)}'>{mas_vulnerable}</strong> "
        f"es el activo más vulnerable en promedio ({avgs[mas_vulnerable]:.2f}% por escenario), "
        f"probablemente por su beta elevada que amplifica los movimientos del mercado. "
        f"En contraste, <strong style='color:{ticker_color(menos_vulnerable)}'>{menos_vulnerable}</strong> "
        f"muestra mayor resiliencia ({avgs[menos_vulnerable]:.2f}% en promedio), "
        f"comportándose como activo defensivo o de baja correlación con el mercado. "
        f"Una cartera con mayor peso en activos defensivos reduciría la pérdida máxima en crisis."
    )
    _interp_box(texto, COLORS["accent"], "🌡️")


def _interpretar_escenario(r: dict, base: dict = None) -> None:
    """Interpretación detallada de un escenario individual."""
    assets    = r.get("assets", [])
    port_ret  = r.get("portfolio_return_pct", 0)
    var_95    = r.get("var_95_stressed_pct", 0)
    escenario = r.get("scenario", "este escenario")
    rate_bp   = r.get("rate_shock_bp", 0)
    mkt_drop  = r.get("market_drop_pct", 0)
    vol_mult  = r.get("vol_multiplier", 1)

    if not assets:
        return

    worst_a = min(assets, key=lambda a: a["return_pct"])
    best_a  = max(assets, key=lambda a: a["return_pct"])

    # Construir texto basado en los parámetros reales del escenario
    partes = []

    # Contexto del shock
    if rate_bp != 0:
        dir_tasa = "sube" if rate_bp > 0 else "baja"
        partes.append(
            f"la tasa de interés {dir_tasa} {abs(rate_bp)} puntos básicos"
        )
    if mkt_drop != 0:
        partes.append(
            f"el mercado cae {abs(mkt_drop*100):.0f}%"
        )
    if vol_mult > 1:
        partes.append(
            f"la volatilidad se multiplica por {vol_mult:.1f}x"
        )

    contexto = " y ".join(partes) if partes else "se aplican condiciones de estrés"

    texto = (
        f"Bajo <em>{escenario}</em>, donde {contexto}, el portafolio pierde "
        f"<strong style='color:{_sev_color(port_ret)}'>{port_ret:.2f}%</strong> de su valor. "
        f"El activo más golpeado es "
        f"<strong style='color:{ticker_color(worst_a['ticker'])}'>{worst_a['ticker']}</strong> "
        f"({worst_a['return_pct']:.2f}%), mientras que "
        f"<strong style='color:{ticker_color(best_a['ticker'])}'>{best_a['ticker']}</strong> "
        f"es el más resiliente ({best_a['return_pct']:.2f}%). "
    )

    # Comparación con base si existe
    if base:
        base_ret = base.get("portfolio_return_pct", 0)
        impacto_adicional = port_ret - base_ret
        texto += (
            f"Respecto al escenario base ({base_ret:+.2f}%), "
            f"este shock añade <strong>{impacto_adicional:.2f} pp</strong> de pérdida adicional. "
        )

    # VaR estresado
    c_warn = COLORS["warning"]
    texto += (
        f"El VaR al 95% bajo estrés es <strong style='color:{c_warn}'>{var_95:.2f}%</strong>, "
        f"lo que significa que en el 5% de los peores días bajo estas condiciones "
        f"el portafolio podría perder más de ese porcentaje."
    )

    # Señal de alerta si es muy severo
    if port_ret < -20:
        color_box = "#F43F5E"
        icon = "⚠️"
    elif port_ret < -10:
        color_box = COLORS["warning"]
        icon = "⚠️"
    else:
        color_box = COLORS["accent"]
        icon = "💡"

    _interp_box(texto, color_box, icon)


# ── Sección: configurar portafolio ─────────────────────────────────────────────

def _seccion_portafolio():
    st.markdown(
        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:10px;">Composición del portafolio</div>',
        unsafe_allow_html=True,
    )

    tickers_sel = st.multiselect(
        "Activos", TICKERS + ["SPY"], default=["MSFT", "KO", "JPM"],
        help="Selecciona entre 2 y 6 activos del portafolio",
    )
    if len(tickers_sel) < 2:
        st.warning("Selecciona al menos 2 activos.")
        return None

    cols  = st.columns(len(tickers_sel))
    raw_w = []
    for i, t in enumerate(tickers_sel):
        w = cols[i].number_input(
            f"{t} (%)", 0.0, 100.0,
            round(100.0 / len(tickers_sel), 1), 1.0,
            key=f"sw_{t}",
        )
        raw_w.append(w)

    total = sum(raw_w)
    if total > 0:
        st.markdown(
            '<div style="display:flex;gap:2px;height:5px;border-radius:4px;overflow:hidden;margin:6px 0 4px;">'
            + "".join(
                f'<div style="flex:{w};background:{ticker_color(t)};opacity:0.75;"></div>'
                for t, w in zip(tickers_sel, raw_w)
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    if abs(total - 100.0) > 0.1:
        st.error(f"Los pesos suman **{total:.1f}%** — deben sumar exactamente 100%.")
        return None

    st.caption(f"✅ Pesos válidos · suma: {total:.1f}%")
    return tickers_sel, [w / 100.0 for w in raw_w]


# ── Sección: escenario personalizado ──────────────────────────────────────────

def _seccion_custom() -> list:
    if not st.checkbox("Agregar escenario personalizado (además de los estándar)"):
        return []
    with st.expander("Configurar escenario", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        name       = col1.text_input("Nombre", "Mi escenario")
        rate_shock = col2.slider("Shock de tasa (pb)", -300, 300, 100, 25)
        mkt_drop   = col3.slider("Caída de mercado (%)", -80, 50, -20, 5) / 100
        vol_mult   = col4.slider("Mult. volatilidad ×", 0.5, 5.0, 2.0, 0.5)
        return [{"name": name, "rate_shock_bp": rate_shock,
                 "market_drop_pct": mkt_drop, "vol_multiplier": vol_mult}]


# ── Tarjetas resumen ───────────────────────────────────────────────────────────

def _render_summary(results: list):
    stress = [r for r in results if r.get("scenario", "") != "Base (sin estrés)"]
    rets   = [r.get("portfolio_return_pct", 0) for r in stress]
    vars_  = [r.get("var_95_stressed_pct",  0) for r in stress]
    names  = [r.get("scenario", f"Esc {i+1}") for i, r in enumerate(stress)]

    if not rets:
        return

    worst = names[rets.index(min(rets))]
    best  = names[rets.index(max(rets))]

    cols = st.columns(4)
    cols[0].markdown(_mini_card("Peor escenario",          worst,               COLORS["negative"]), unsafe_allow_html=True)
    cols[1].markdown(_mini_card("Pérdida máxima",          f"{min(rets):.2f}%", COLORS["negative"]), unsafe_allow_html=True)
    cols[2].markdown(_mini_card("Escenario más favorable", best,                COLORS["positive"]), unsafe_allow_html=True)
    cols[3].markdown(_mini_card("VaR 95% máx. estresado", f"{max(vars_):.2f}%",COLORS["warning"]),  unsafe_allow_html=True)


# ── Gráfico de barras ──────────────────────────────────────────────────────────

def _render_bars(results: list):
    names = [r.get("scenario", f"Esc {i+1}") for i, r in enumerate(results)]
    rets  = [r.get("portfolio_return_pct", 0) for r in results]
    vars_ = [r.get("var_95_stressed_pct",  0) for r in results]

    # Base en gris, resto con color por severidad
    bar_colors = [
        "#3B4460" if r.get("scenario", "") == "Base (sin estrés)"
        else _sev_color(v)
        for r, v in zip(results, rets)
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Retorno portafolio",
        x=names, y=rets,
        marker_color=bar_colors,
        marker_opacity=0.85,
        text=[f"{v:.1f}%" for v in rets],
        textposition="outside",
        textfont=dict(size=10, family="DM Mono, monospace"),
        hovertemplate="<b>%{x}</b><br>Retorno: %{y:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="VaR 95% estresado",
        x=names, y=[-v for v in vars_],
        mode="markers",
        marker=dict(color=COLORS["warning"], size=10, symbol="diamond"),
        hovertemplate="<b>%{x}</b><br>VaR estresado: %{customdata:.2f}%<extra></extra>",
        customdata=vars_,
    ))
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#2E3550")
    fig.update_layout(
        height=340,
        xaxis=dict(tickangle=-20),
        yaxis_title="Retorno estimado (%)",
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        margin=dict(t=30, b=60, l=50, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Heatmap ────────────────────────────────────────────────────────────────────

def _render_heatmap(results: list, tickers_sel: list):
    names = [r.get("scenario", f"Esc {i+1}") for i, r in enumerate(results)]
    z, text = [], []
    for r in results:
        assets = {a["ticker"]: a["return_pct"] for a in r.get("assets", [])}
        row_z  = [assets.get(t, 0.0) for t in tickers_sel]
        row_t  = [f"{v:.2f}%" for v in row_z]
        z.append(row_z)
        text.append(row_t)

    fig = go.Figure(go.Heatmap(
        z=z, x=tickers_sel, y=names,
        colorscale=[[0, "#3B0A0A"], [0.35, "#7B1A1A"], [0.5, "#1C2030"],
                    [0.65, "#0D2E1A"], [1, "#0D3B22"]],
        zmid=0,
        text=text, texttemplate="<b>%{text}</b>",
        textfont=dict(size=11, family="DM Mono, monospace"),
        showscale=True,
        colorbar=dict(title=dict(text="Retorno %", font=dict(size=10, color=COLORS["muted"])),
                      tickfont=dict(size=9, color=COLORS["muted"]), outlinewidth=0),
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=max(280, len(results) * 52 + 80),
        xaxis=dict(tickfont=dict(size=11, family="DM Mono, monospace"), side="top"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=180, r=60, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Tabla de activos ───────────────────────────────────────────────────────────

def _render_asset_table(assets: list):
    rows = []
    for a in assets:
        rows.append({
            "Ticker":           a["ticker"],
            "Peso":             f"{a['weight']*100:.1f}%",
            "Beta":             f"{a['beta']:.3f}",
            "Precio base":      f"${a['price_base']:.2f}",
            "Precio estresado": f"${a['price_stressed']:.2f}",
            "Retorno":          f"{a['return_pct']:.2f}%",
        })
    df = pd.DataFrame(rows)

    def color_ret(val):
        v = float(val.replace("%", ""))
        return f"color: {_sev_color(v)}; font-family: 'DM Mono', monospace; font-weight: 600"

    styled = df.style.applymap(color_ret, subset=["Retorno"]).set_properties(**{"font-size": "0.83rem"})
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ── Detalle de un escenario ────────────────────────────────────────────────────

def _render_detail(r: dict, tickers_sel: list, base: dict = None):
    assets = r.get("assets", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(_mini_card("Shock de tasa",     f"{r.get('rate_shock_bp', 0):+d} pb",      COLORS["warning"]),  unsafe_allow_html=True)
    col2.markdown(_mini_card("Caída de mercado",  f"{r.get('market_drop_pct', 0):+.1f}%",    COLORS["negative"]), unsafe_allow_html=True)
    col3.markdown(_mini_card("Mult. volatilidad", f"×{r.get('vol_multiplier', 1):.1f}",      COLORS["accent"]),   unsafe_allow_html=True)
    col4.markdown(_mini_card("VaR 95% estresado", f"{r.get('var_95_stressed_pct', 0):.2f}%", COLORS["warning"]),  unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Interpretación automática del escenario
    _interpretar_escenario(r, base)

    st.markdown("<br>", unsafe_allow_html=True)

    if not assets:
        st.info("Sin detalle de activos disponible.")
        return

    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">Impacto por activo</div>',
            unsafe_allow_html=True,
        )
        _render_asset_table(assets)

        port_ret = r.get("portfolio_return_pct", 0)
        color = _sev_color(port_ret)
        st.markdown(
            f'<div style="margin-top:10px;padding:10px 16px;background:#0D1018;'
            f'border:1px solid #1C2030;border-left:3px solid {color};border-radius:0 8px 8px 0;'
            f'display:flex;align-items:center;justify-content:space-between;">'
            f'<span style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:#3B4460;">Retorno total portafolio</span>'
            f'<span>{_badge(port_ret)}</span></div>',
            unsafe_allow_html=True,
        )

    with right:
        tickers_a = [a["ticker"] for a in assets]
        returns_a = [a["return_pct"] for a in assets]
        fig = go.Figure(go.Bar(
            x=returns_a, y=tickers_a,
            orientation="h",
            marker_color=[_sev_color(v) for v in returns_a],
            marker_opacity=0.85,
            text=[f"{v:.2f}%" for v in returns_a],
            textposition="outside",
            textfont=dict(size=10, family="DM Mono, monospace"),
            hovertemplate="<b>%{y}</b><br>Retorno: %{x:.2f}%<extra></extra>",
        ))
        fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="#2E3550")
        fig.update_layout(
            height=max(200, len(assets) * 46 + 50),
            xaxis_title="Retorno (%)",
            yaxis=dict(tickfont=dict(size=11, family="DM Mono, monospace")),
            margin=dict(l=10, r=60, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Render principal ───────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div class="section-title">Stress Testing</div>
    <div class="section-subtitle">Escenarios extremos — Crisis 2008 · COVID-19 · Dot-com · Shocks de tasa y volatilidad</div>
    """, unsafe_allow_html=True)

    # 1. Portafolio
    result = _seccion_portafolio()
    if result is None:
        return
    tickers_sel, weights = result

    st.markdown('<hr style="border-color:#1C2030;margin:20px 0;">', unsafe_allow_html=True)

    # 2. Escenario custom
    scenarios = _seccion_custom()

    # 3. Botón ejecutar
    if st.button("▶ Ejecutar Stress Test", type="primary"):
        with st.spinner("Aplicando escenarios de estrés..."):
            data = fetch_stress(tickers_sel, weights, scenarios)
        if not data:
            st.warning("Error al ejecutar el stress test. Verifica la conexión al backend.")
            return
        results = data if isinstance(data, list) else data.get("results", [])
        if not results:
            st.warning("No se obtuvieron resultados del backend.")
            return
        st.session_state["stress_results"] = results
        st.session_state["stress_tickers"] = tickers_sel

    # 4. Placeholder si no hay resultados
    if "stress_results" not in st.session_state:
        st.markdown("""
        <div style="margin-top:16px;padding:14px 18px;background:#0D1018;border:1px solid #1C2030;
                    border-left:3px solid #3B82F6;border-radius:0 8px 8px 0;
                    font-size:0.83rem;color:#5A6480;line-height:1.6;">
            Haz clic en <strong style="color:#D4D8E2;">Ejecutar Stress Test</strong> para aplicar
            los escenarios históricos estándar más el escenario base sobre el portafolio.
            Cada escenario aplica un shock de tasa, caída de mercado y multiplicador de volatilidad
            calibrados a crisis reales.
        </div>""", unsafe_allow_html=True)
        return

    results     = st.session_state["stress_results"]
    tickers_sel = st.session_state["stress_tickers"]

    # Escenario base para referencia en comparaciones
    base = next((r for r in results if r.get("scenario", "") == "Base (sin estrés)"), None)

    # 5. Resumen + interpretación global
    st.markdown('<hr style="border-color:#1C2030;margin:20px 0;">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#3B4460;margin-bottom:12px;">Resumen general</div>',
        unsafe_allow_html=True,
    )
    _render_summary(results)
    st.markdown("<br>", unsafe_allow_html=True)
    _interpretar_resumen(results)

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. Tres pestañas
    tab_bar, tab_heat, tab_det = st.tabs([
        "📊 Comparativa de escenarios",
        "🌡️ Mapa de calor por activo",
        "🔍 Detalle por escenario",
    ])

    with tab_bar:
        _render_bars(results)
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin:16px 0 8px;">Tabla resumen</div>',
            unsafe_allow_html=True,
        )
        rows = []
        for r in results:
            assets  = r.get("assets", [])
            worst_a = min(assets, key=lambda a: a["return_pct"]) if assets else {}
            rows.append({
                "Escenario":          r.get("scenario", "—"),
                "Shock tasa (pb)":    f"{r.get('rate_shock_bp', 0):+d}",
                "Caída mercado":      f"{r.get('market_drop_pct', 0):+.1f}%",
                "Mult. vol.":         f"×{r.get('vol_multiplier', 1):.1f}",
                "Retorno portafolio": f"{r.get('portfolio_return_pct', 0):.2f}%",
                "VaR 95% estresado":  f"{r.get('var_95_stressed_pct', 0):.2f}%",
                "Más afectado":       worst_a.get("ticker", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab_heat:
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#3B4460;margin-bottom:8px;">Retorno por activo y escenario</div>',
            unsafe_allow_html=True,
        )
        _render_heatmap(results, tickers_sel)
        _interpretar_heatmap(results, tickers_sel)

    with tab_det:
        names = [r.get("scenario", f"Esc {i+1}") for i, r in enumerate(results)]
        sel   = st.selectbox("Selecciona un escenario", names, key="stress_det_sel")
        r_sel = next((r for r in results if r.get("scenario") == sel), None)
        if r_sel:
            st.markdown("<br>", unsafe_allow_html=True)
            _render_detail(r_sel, tickers_sel, base=base if r_sel is not base else None)