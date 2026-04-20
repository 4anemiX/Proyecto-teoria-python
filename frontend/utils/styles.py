GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0A0C10;
    color: #D4D8E2;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0D0F14;
    border-right: 1px solid #1C2030;
}
section[data-testid="stSidebar"] * {
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Metric cards ── */
.metric-card {
    background: linear-gradient(145deg, #111420, #0D1018);
    border: 1px solid #1E2436;
    border-radius: 10px;
    padding: 18px 16px;
    text-align: center;
    transition: border-color 0.2s ease, transform 0.2s ease;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--card-accent, #3B82F6);
    opacity: 0.6;
}
.metric-card:hover {
    border-color: #2E3850;
    transform: translateY(-1px);
}
.metric-value {
    font-family: 'DM Mono', monospace;
    font-size: 1.55rem;
    font-weight: 500;
    letter-spacing: -0.02em;
    line-height: 1;
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 500;
    color: #5A6480;
    margin-top: 5px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.metric-change {
    font-size: 0.78rem;
    font-weight: 500;
    margin-top: 4px;
    font-family: 'DM Mono', monospace;
}

/* ── Signal indicators ── */
.signal-positive { color: #34D399; }
.signal-negative { color: #F87171; }
.signal-neutral  { color: #FBBF24; }

/* ── Section titles ── */
.section-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: #E8EAF0;
    margin-bottom: 4px;
    letter-spacing: -0.02em;
}
.section-subtitle {
    font-size: 0.82rem;
    color: #4A5270;
    margin-bottom: 24px;
    letter-spacing: 0.03em;
}

/* ── Divider ── */
.divider {
    border: none;
    border-top: 1px solid #1C2030;
    margin: 24px 0;
}

/* ── Interpretation box ── */
.interpretation-box {
    background: #0D1018;
    border: 1px solid #1E2436;
    border-left: 3px solid #3B82F6;
    border-radius: 6px;
    padding: 14px 18px;
    margin-top: 12px;
    font-size: 0.84rem;
    color: #8A94B0;
    line-height: 1.65;
}
.interpretation-box strong {
    color: #B8C0D8;
    font-weight: 600;
}
.interpretation-box.positive { border-left-color: #34D399; }
.interpretation-box.negative { border-left-color: #F87171; }
.interpretation-box.warning  { border-left-color: #FBBF24; }

/* ── Tables ── */
.stDataFrame {
    border: 1px solid #1C2030 !important;
    border-radius: 8px !important;
}
thead tr th {
    background: #0D0F14 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: #4A5270 !important;
    font-weight: 600 !important;
}
tbody tr td {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── Selectbox & sliders ── */
.stSelectbox label, .stSlider label {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #4A5270 !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: #3B82F6 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #8A94B0 !important;
    letter-spacing: 0.02em !important;
}

/* ── Pill badge ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.badge-green  { background: #0D2E20; color: #34D399; border: 1px solid #1A4A30; }
.badge-red    { background: #2E0D10; color: #F87171; border: 1px solid #4A1A1E; }
.badge-yellow { background: #2E280D; color: #FBBF24; border: 1px solid #4A3F1A; }
.badge-blue   { background: #0D1A2E; color: #60A5FA; border: 1px solid #1A2A4A; }

/* ── Signal table ── */
.signal-row {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    background: #0D1018;
    border: 1px solid #1C2030;
    border-radius: 8px;
    margin-bottom: 8px;
    gap: 12px;
}
.signal-ticker {
    font-family: 'DM Mono', monospace;
    font-weight: 500;
    font-size: 0.88rem;
    color: #E8EAF0;
    min-width: 45px;
}
.signal-indicator {
    flex: 1;
    text-align: center;
    font-size: 0.75rem;
    font-weight: 500;
    color: #5A6480;
}

/* ── Chat IA ── */
.chat-container {
    background: #0D1018;
    border: 1px solid #1E2436;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 16px;
}
.chat-msg-user {
    background: #111C30;
    border-left: 3px solid #3B82F6;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 0.85rem;
    color: #C8D0E8;
    line-height: 1.6;
}
.chat-msg-assistant {
    background: #0A1020;
    border-left: 3px solid #34D399;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 0.85rem;
    color: #8A94B0;
    line-height: 1.6;
}
.chat-msg-assistant strong { color: #B8C0D8; }
.pydantic-tag {
    display: inline-block;
    background: #0D2010;
    color: #34D399;
    border: 1px solid #1A4A28;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 2px 10px;
    margin-bottom: 12px;
}
</style>
"""