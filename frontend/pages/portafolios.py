import streamlit as st
from data.client import fetch_portafolios, crear_portafolio, eliminar_portafolio, TICKERS
from utils.theme import COLORS, ticker_color


# ── Helpers de interpretación ──────────────────────────────────────────────────

def _interp_box(texto: str, color: str = "#3B82F6", icon: str = "💡") -> None:
    st.markdown(
        f'<div style="margin:10px 0;padding:12px 16px;background:#0D1018;'
        f'border:1px solid #1C2030;border-left:3px solid {color};border-radius:0 8px 8px 0;'
        f'font-size:0.82rem;color:#A0AABE;line-height:1.7;">'
        f'<span style="font-size:0.9rem;margin-right:8px;">{icon}</span>{texto}</div>',
        unsafe_allow_html=True,
    )


def _interpretar_portafolio(p: dict) -> None:
    """
    Analiza la composición de un portafolio guardado y genera observaciones
    dinámicas sobre concentración, diversificación y activos dominantes.
    """
    weights: dict = p.get("weights", {})
    tickers: list = p.get("tickers", [])

    if not weights or not tickers:
        return

    vals = list(weights.values())
    n    = len(vals)

    if n == 0:
        return

    # Activo dominante
    max_ticker = max(weights, key=weights.get)
    max_weight = weights[max_ticker] * 100
    min_ticker = min(weights, key=weights.get)
    min_weight = weights[min_ticker] * 100

    # Concentración: HHI simplificado (suma de cuadrados de pesos)
    hhi = sum(w ** 2 for w in vals)

    # Clasificar concentración
    if hhi > 0.40:
        conc_label = "alta concentración"
        conc_color = COLORS["negative"]
        conc_icon  = "⚠️"
        conc_txt   = (
            f"<strong style='color:{ticker_color(max_ticker)}'>{max_ticker}</strong> "
            f"domina con {max_weight:.1f}% del portafolio — un movimiento adverso en este activo "
            f"impacta significativamente el resultado total."
        )
    elif hhi > 0.25:
        conc_label = "concentración moderada"
        conc_color = COLORS["warning"]
        conc_icon  = "🟡"
        conc_txt   = (
            f"El peso de <strong style='color:{ticker_color(max_ticker)}'>{max_ticker}</strong> "
            f"({max_weight:.1f}%) es relevante pero no dominante. "
            f"Distribución aceptable para un portafolio temático."
        )
    else:
        conc_label = "bien diversificado"
        conc_color = COLORS["positive"]
        conc_icon  = "🟢"
        conc_txt   = (
            f"Los pesos están distribuidos de forma equilibrada — ningún activo supera "
            f"el {max_weight:.1f}%. Buen balance entre los {n} componentes."
        )

    texto = (
        f"Este portafolio de <strong>{n} activos</strong> presenta <strong style='color:{conc_color}'>"
        f"{conc_label}</strong>. {conc_txt} "
        f"El activo con menor peso es "
        f"<strong style='color:{ticker_color(min_ticker)}'>{min_ticker}</strong> "
        f"({min_weight:.1f}%)."
    )

    _interp_box(texto, conc_color, conc_icon)


def _interpretar_lista(portfolios: list) -> None:
    """Resumen general si hay múltiples portafolios guardados."""
    if len(portfolios) < 2:
        return

    # Detectar el ticker más repetido a través de los portafolios
    from collections import Counter
    all_tickers = [t for p in portfolios for t in p.get("tickers", [])]
    conteo = Counter(all_tickers)
    mas_usado = conteo.most_common(1)[0] if conteo else None

    texto = f"Tienes <strong>{len(portfolios)}</strong> portafolios guardados. "
    if mas_usado and mas_usado[1] > 1:
        t, n = mas_usado
        color = ticker_color(t)
        texto += (
            f"<strong style='color:{color}'>{t}</strong> aparece en {n} de ellos — "
            f"es el activo más recurrente en tus composiciones. "
        )

    # Diversidad de portafolios
    sizes = [len(p.get("tickers", [])) for p in portfolios]
    if max(sizes) - min(sizes) > 2:
        texto += (
            f"Los portafolios varían de {min(sizes)} a {max(sizes)} activos, "
            f"lo que sugiere que estás explorando distintos niveles de concentración."
        )

    _interp_box(texto, COLORS["accent"], "📂")


def _interpretar_nuevo(tickers_sel: list, raw_weights: dict) -> None:
    """
    Feedback en tiempo real mientras el usuario configura un nuevo portafolio.
    Solo se muestra si los pesos son válidos.
    """
    total = sum(raw_weights.values())
    if abs(total - 100.0) > 0.1 or len(tickers_sel) < 2:
        return

    weights_norm = {t: w / 100.0 for t, w in raw_weights.items()}
    vals = list(weights_norm.values())
    hhi  = sum(w ** 2 for w in vals)

    max_t = max(weights_norm, key=weights_norm.get)
    max_w = weights_norm[max_t] * 100

    # SPY como benchmark
    tiene_spy = "SPY" in tickers_sel

    partes = []

    if hhi > 0.40:
        partes.append(
            f"<strong style='color:{COLORS['negative']}'>Alta concentración</strong>: "
            f"{max_t} tiene {max_w:.1f}% del peso — considera reducirlo para mayor diversificación"
        )
    elif hhi < 0.20:
        partes.append(
            f"<strong style='color:{COLORS['positive']}'>Buena diversificación</strong>: "
            f"los pesos están bien distribuidos entre los {len(tickers_sel)} activos"
        )

    if tiene_spy:
        spy_w = weights_norm.get("SPY", 0) * 100
        partes.append(
            f"SPY ({spy_w:.1f}%) actúa como ancla de mercado — "
            f"reduce la volatilidad idiosincrática del portafolio"
        )

    if partes:
        _interp_box(" · ".join(partes) + ".", COLORS["accent"], "💡")


# ── Render principal ───────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div class="section-title">Portafolios Guardados</div>
    <div class="section-subtitle">Crear · consultar · eliminar portafolios persistidos en SQLite</div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📂 Mis portafolios", "➕ Nuevo portafolio"])

    # ── Tab 1: Listar y eliminar ───────────────────────────────────────────────
    with tab1:
        st.markdown("#### Portafolios guardados")
        with st.spinner("Cargando portafolios..."):
            portfolios = fetch_portafolios()

        if not portfolios:
            st.info("No hay portafolios guardados. Crea uno en la pestaña 'Nuevo portafolio'.")
        else:
            # Interpretación del conjunto de portafolios guardados
            _interpretar_lista(portfolios)

            for p in portfolios:
                col1, col2, col3 = st.columns([4, 2, 1])
                tickers_str = ", ".join(p.get("tickers", []))
                weights     = p.get("weights", {})
                weights_str = " | ".join(f"{t}: {v*100:.1f}%" for t, v in weights.items())

                with col1:
                    muted   = COLORS["muted"]
                    accent  = COLORS["accent"]
                    created = str(p.get("created_at", ""))[:16]
                    notes_html = f"<br><em>{p['notes']}</em>" if p.get("notes") else ""
                    st.markdown(
                        f"<div class='metric-card'>"
                        f"<strong>{p['name']}</strong><br>"
                        f"<span style='color:{muted}'>Activos: {tickers_str}</span><br>"
                        f"<span style='color:{accent}; font-size:0.85em'>{weights_str}</span><br>"
                        f"<span style='color:{muted}; font-size:0.8em'>Creado: {created}</span>"
                        f"{notes_html}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(f"ID: `{p['id']}`")

                with col3:
                    if st.button("🗑️", key=f"del_{p['id']}", help=f"Eliminar {p['name']}"):
                        ok = eliminar_portafolio(p["id"])
                        if ok:
                            st.success(f"Portafolio '{p['name']}' eliminado.")
                            st.rerun()
                        else:
                            st.error("Error al eliminar.")

                # Interpretación individual del portafolio
                _interpretar_portafolio(p)
                st.markdown('<hr style="border-color:#111520;margin:8px 0 16px;">', unsafe_allow_html=True)

    # ── Tab 2: Crear nuevo ─────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Nuevo portafolio")

        name  = st.text_input("Nombre del portafolio", placeholder="Ej: Portafolio conservador Q2")
        notes = st.text_area("Notas (opcional)", placeholder="Estrategia, contexto, observaciones...")

        all_tickers = TICKERS + ["SPY"]
        tickers_sel = st.multiselect("Activos", all_tickers, default=["MSFT", "KO", "JPM"])

        if len(tickers_sel) < 2:
            st.warning("Selecciona al menos 2 activos.")
            return

        st.markdown("**Pesos por activo (deben sumar 100%)**")
        cols = st.columns(len(tickers_sel))
        raw_weights = {}
        for i, t in enumerate(tickers_sel):
            raw_weights[t] = cols[i].number_input(
                f"{t} (%)", 0.0, 100.0,
                round(100.0 / len(tickers_sel), 1), 1.0,
                key=f"w_{t}",
            )

        total = sum(raw_weights.values())
        if abs(total - 100.0) > 0.1:
            st.error(f"Los pesos suman {total:.1f}% — deben sumar exactamente 100%.")
        else:
            st.success(f"✅ Pesos válidos — suma: {total:.1f}%")
            weights_norm = {t: w / 100.0 for t, w in raw_weights.items()}

            # Feedback en tiempo real sobre la composición que el usuario está configurando
            _interpretar_nuevo(tickers_sel, raw_weights)

            if st.button("💾 Guardar portafolio", type="primary", disabled=not name):
                if not name:
                    st.warning("Escribe un nombre para el portafolio.")
                else:
                    with st.spinner("Guardando..."):
                        result = crear_portafolio(name, tickers_sel, weights_norm, notes or None)
                    if result:
                        st.success(f"✅ Portafolio '{name}' guardado con ID {result['id']}.")
                        st.balloons()
                    else:
                        st.error("Error al guardar el portafolio.")