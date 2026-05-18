import streamlit as st
from data.client import fetch_portafolios, crear_portafolio, eliminar_portafolio, TICKERS
from utils.theme import COLORS


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
            for p in portfolios:
                col1, col2, col3 = st.columns([4, 2, 1])
                tickers_str = ", ".join(p.get("tickers", []))
                weights     = p.get("weights", {})
                weights_str = " | ".join(f"{t}: {v*100:.1f}%" for t, v in weights.items())

                with col1:
                    muted = COLORS["muted"]
                    accent = COLORS["accent"]
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