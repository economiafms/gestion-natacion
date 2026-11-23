"""Tema visual compartido y componentes motivacionales para todas las páginas."""
import hashlib
import html
from datetime import datetime, timedelta, timezone

import streamlit as st

ROJO = "#E30613"

FRASES = [
    "Cada largo cuenta. Hoy sumás uno más.",
    "La constancia le gana al talento cuando el talento no entrena.",
    "No se trata de ser el mejor, se trata de ser mejor que ayer.",
    "El agua no miente: lo que entrenás, se nota.",
    "Una brazada a la vez. Así se construyen los récords.",
    "Tu único rival está en el carril de tu propio reloj.",
    "Los campeones se hacen cuando nadie los mira.",
    "Cansado no es terminado. Una serie más.",
    "Disciplina hoy, orgullo mañana.",
    "Del deporte sos la gloria. ¡Vamos Newell's!",
    "Cada centésima que bajás es trabajo que se ve.",
    "Entrenar es invertir en tu mejor versión.",
    "El progreso no siempre se ve, pero siempre suma.",
    "Que el cronómetro sea tu motivación, no tu miedo.",
    "Hoy es un buen día para nadar tu mejor marca.",
]


def ahora_arg():
    return datetime.now(timezone.utc) - timedelta(hours=3)


def primer_nombre():
    nombre = st.session_state.get("user_name") or ""
    return nombre.split(" ")[0].strip().title() if nombre else "Nadador"


def saludo():
    h = ahora_arg().hour
    if 5 <= h < 13:
        return "Buen día"
    if 13 <= h < 20:
        return "Buenas tardes"
    return "Buenas noches"


def frase_del_dia(extra: str = ""):
    """Frase estable durante el día para cada nadador (cambia al día siguiente)."""
    clave = f"{st.session_state.get('user_id')}-{ahora_arg().date()}-{extra}"
    idx = int(hashlib.md5(clave.encode()).hexdigest(), 16) % len(FRASES)
    return FRASES[idx]


def hero(titulo: str, icono: str = "", subtitulo: str | None = None, saludar: bool = True):
    """Encabezado de página personalizado y motivador."""
    nombre = html.escape(primer_nombre())
    sub = html.escape(subtitulo) if subtitulo else html.escape(frase_del_dia(titulo))
    saludo_html = (
        f'<div class="nob-hero-hi">{saludo()}, <b>{nombre}</b> 👋</div>' if saludar else ""
    )
    st.markdown(
        f"""
        <div class="nob-hero">
            <div class="nob-hero-wave"></div>
            {saludo_html}
            <div class="nob-hero-title"><span class="nob-hero-ico">{icono}</span>{html.escape(titulo)}</div>
            <div class="nob-hero-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def seccion(texto: str):
    st.markdown(f'<div class="nob-section">{html.escape(texto)}</div>', unsafe_allow_html=True)


def aplicar_tema():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        /* ---------- Base ---------- */
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(900px 420px at 0% -5%, rgba(227,6,19,0.16), transparent 60%),
                radial-gradient(700px 400px at 100% 105%, rgba(227,6,19,0.10), transparent 60%),
                #08090C;
        }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container { font-family: 'Inter', sans-serif; padding-top: 2.2rem; }
        .block-container p, .block-container li, .block-container label,
        .block-container input, .block-container textarea, .block-container button,
        .block-container h1, .block-container h2, .block-container h3,
        .block-container h4, .block-container h5 { font-family: 'Inter', sans-serif; }
        .block-container h1, .block-container h2, .block-container h3 { letter-spacing: -0.4px; }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111216 0%, #0A0B0E 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        [data-testid="stSidebarNav"] a { border-radius: 10px; }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: rgba(227,6,19,0.16);
        }

        /* ---------- Hero personalizado ---------- */
        .nob-hero {
            position: relative; overflow: hidden;
            padding: 22px 24px 20px; margin-bottom: 22px;
            border-radius: 20px;
            background: linear-gradient(135deg, #1B0204 0%, #2A0306 40%, #120F12 100%);
            border: 1px solid rgba(227,6,19,0.30);
            box-shadow: 0 18px 40px rgba(0,0,0,0.45);
            animation: nobUp .5s ease-out both;
        }
        .nob-hero::before {
            content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
            background: linear-gradient(90deg, #E30613, #FF4D57 50%, #111 50.1%);
        }
        .nob-hero-wave {
            position: absolute; right: -60px; top: -60px; width: 220px; height: 220px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(227,6,19,0.35), transparent 65%);
        }
        .nob-hero-hi { position: relative; font-size: 14px; color: rgba(255,255,255,0.72); margin-bottom: 4px; }
        .nob-hero-hi b { color: #fff; }
        .nob-hero-title {
            position: relative; font-size: 28px; font-weight: 900; line-height: 1.1;
            color: #fff; letter-spacing: -0.6px;
        }
        .nob-hero-ico { margin-right: 10px; }
        .nob-hero-sub {
            position: relative; margin-top: 10px; display: inline-block;
            padding: 6px 12px; border-radius: 999px;
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
            font-size: 13px; font-style: italic; color: rgba(255,255,255,0.78);
        }

        .nob-section {
            margin: 26px 0 12px; font-size: 12px; font-weight: 700;
            letter-spacing: 2px; text-transform: uppercase; color: rgba(255,255,255,0.55);
            display: flex; align-items: center; gap: 10px;
        }
        .nob-section::before { content: ""; width: 18px; height: 3px; border-radius: 3px; background: #E30613; }
        .nob-section::after { content: ""; flex: 1; height: 1px; background: rgba(255,255,255,0.08); }

        /* ---------- Superficie tipo "glass" para tarjetas existentes ---------- */
        .padron-card, .test-card, .swimmer-card, .mobile-card, .nob-card2 {
            background: linear-gradient(160deg, rgba(255,255,255,0.055), rgba(255,255,255,0.015)) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 28px rgba(0,0,0,0.35) !important;
            transition: transform .15s ease, border-color .15s ease;
        }
        .padron-card:hover, .test-card:hover, .swimmer-card:hover, .mobile-card:hover { border-color: rgba(227,6,19,0.35) !important; }
        .test-card { border-left: 4px solid #E30613 !important; }
        .swimmer-card { border-left: 4px solid rgba(255,255,255,0.18) !important; }
        .swimmer-card.is-me {
            border-left: 4px solid #E30613 !important;
            background: linear-gradient(135deg, rgba(227,6,19,0.20), rgba(227,6,19,0.04)) !important;
        }
        .ficha-header {
            background: linear-gradient(135deg, #3A0307 0%, #1A0204 60%, #111 100%) !important;
            border: 1px solid rgba(227,6,19,0.35) !important; border-radius: 18px !important;
            box-shadow: 0 16px 36px rgba(0,0,0,0.45) !important;
        }
        .pb-row {
            background: rgba(255,255,255,0.04) !important; border-radius: 12px !important;
            border-left: 3px solid #E30613 !important;
        }
        .splits-container { background: rgba(0,0,0,0.25) !important; border-radius: 12px !important; border-color: rgba(255,255,255,0.06) !important; }
        .final-time { color: #FF3B45 !important; font-family: 'JetBrains Mono', ui-monospace, monospace !important; }
        .section-title, .pb-style-header { color: #FF3B45 !important; border-bottom-color: rgba(255,255,255,0.08) !important; letter-spacing: 1px; }

        /* ---------- Botones ---------- */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
            border-radius: 12px; font-weight: 700; letter-spacing: .3px;
            min-height: 44px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            transition: transform .12s ease, box-shadow .12s ease, filter .12s ease, border-color .12s;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover { border-color: #E30613; transform: translateY(-1px); }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
            border: none;
            background: linear-gradient(135deg, #FF1F2D 0%, #E30613 55%, #A8040E 100%);
            box-shadow: 0 8px 20px rgba(227,6,19,0.28);
        }
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
            filter: brightness(1.08); box-shadow: 0 12px 26px rgba(227,6,19,0.40);
        }

        /* ---------- Inputs ---------- */
        div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
            border-radius: 12px !important;
            background: rgba(255,255,255,0.04) !important;
            border-color: rgba(255,255,255,0.10) !important;
        }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
            border-color: #E30613 !important; box-shadow: 0 0 0 3px rgba(227,6,19,0.18) !important;
        }

        /* ---------- Expanders, forms, tabs ---------- */
        [data-testid="stExpander"] details {
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            background: rgba(255,255,255,0.025);
        }
        [data-testid="stExpander"] summary:hover { color: #FF3B45; }
        [data-testid="stForm"] {
            border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.02);
        }
        [role="tablist"] { gap: 8px !important; border-bottom: none !important; box-shadow: none !important; padding-bottom: 6px; }
        [data-testid="stTab"] {
            border-radius: 999px !important; padding: 6px 16px !important; height: auto !important;
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stTab"] p { color: rgba(255,255,255,0.75) !important; font-weight: 600; }
        [data-testid="stTab"][aria-selected="true"] { background: rgba(227,6,19,0.18); border-color: rgba(227,6,19,0.55); }
        [data-testid="stTab"][aria-selected="true"] p { color: #fff !important; }
        [data-testid="stTab"] .react-aria-SelectionIndicator { display: none; }

        /* ---------- Métricas, alertas, tablas ---------- */
        [data-testid="stMetric"] {
            background: linear-gradient(160deg, rgba(255,255,255,0.055), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 14px 16px;
        }
        [data-testid="stMetricValue"] { font-weight: 800; }
        [data-testid="stAlert"] { border-radius: 14px; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: 14px; overflow: hidden; }
        hr { border-color: rgba(255,255,255,0.07) !important; }
        [data-testid="stProgressBarTrack"] { border-radius: 999px !important; height: 10px !important; background: rgba(255,255,255,0.08) !important; }
        [data-testid="stProgressBarTrack"] > div { border-radius: 999px !important; background: linear-gradient(90deg, #E30613, #FF6A72) !important; }

        /* ---------- Componentes de Inicio ---------- */
        .nob-profile {
            display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: center;
            padding: 18px; border-radius: 18px; margin-bottom: 14px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-avatar {
            width: 56px; height: 56px; border-radius: 16px;
            display: grid; place-items: center;
            font-size: 22px; font-weight: 900; color: #fff;
            background: linear-gradient(135deg, #FF1F2D, #8E030B);
            box-shadow: 0 8px 18px rgba(227,6,19,0.35);
        }
        .nob-p-name { font-size: 18px; font-weight: 800; color: #fff; line-height: 1.2; }
        .nob-p-meta { font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 2px; }
        .nob-cat-badge {
            text-align: center; padding: 8px 14px; border-radius: 14px;
            background: rgba(76,175,80,0.12); border: 1px solid rgba(76,175,80,0.35);
        }
        .nob-cat-badge small { display: block; font-size: 10px; letter-spacing: 1.5px; color: rgba(255,255,255,0.55); text-transform: uppercase; }
        .nob-cat-badge b { font-size: 20px; color: #6FDB74; }

        .nob-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
        .nob-stat {
            text-align: center; padding: 14px 6px; border-radius: 16px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
        }
        .nob-stat .v { font-size: 24px; font-weight: 900; color: #fff; line-height: 1.1; }
        .nob-stat .l { font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: rgba(255,255,255,0.5); margin-top: 4px; }
        .nob-stat.gold   { border-color: rgba(255,215,0,0.35);  background: rgba(255,215,0,0.07); }
        .nob-stat.silver { border-color: rgba(200,200,200,0.30); background: rgba(200,200,200,0.06); }
        .nob-stat.bronze { border-color: rgba(205,127,50,0.35); background: rgba(205,127,50,0.07); }
        .nob-stat.total  { border-color: rgba(227,6,19,0.40); background: rgba(227,6,19,0.10); }

        .nob-goal {
            padding: 16px 18px; border-radius: 18px; margin-bottom: 14px;
            background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03));
            border: 1px solid rgba(227,6,19,0.30);
        }
        .nob-goal-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
        .nob-goal-top b { color: #fff; font-size: 15px; }
        .nob-goal-top span { color: rgba(255,255,255,0.7); font-size: 13px; font-weight: 600; }
        .nob-bar { height: 10px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
        .nob-bar > div { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #E30613, #FF6A72); }
        .nob-goal-msg { margin-top: 10px; font-size: 13px; color: rgba(255,255,255,0.75); }

        .nob-chip-row { display: flex; flex-wrap: wrap; gap: 8px; }
        .nob-chip {
            flex: 1 1 90px; text-align: center; padding: 12px 8px; border-radius: 14px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
        }
        .nob-chip .v { font-size: 22px; font-weight: 800; color: #fff; }
        .nob-chip .l { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: rgba(255,255,255,0.5); }

        @media (max-width: 520px) {
            .nob-hero-title { font-size: 23px; }
            .nob-stats { grid-template-columns: repeat(2, 1fr); }
            .nob-profile { grid-template-columns: auto 1fr; }
            .nob-cat-badge { grid-column: 1 / -1; }
        }
        @keyframes nobUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
