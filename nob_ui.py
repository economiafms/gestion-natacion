"""Tema visual compartido y componentes motivacionales para todas las páginas."""
import base64
import html
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

ROJO = "#E30613"
RAIZ = Path(__file__).parent
ESCUDO_PATH = RAIZ / "escudo.png"
ESCUDO_URL = "https://raw.githubusercontent.com/economiafms/gestion-natacion/main/escudo.png"
# Escudo de Newell's (lado derecho del banner). Se muestra solo si el archivo está en la raíz del proyecto.
ESCUDO_NOB_CANDIDATOS = ["escudonob.png", "escudonob.svg", "escudonob.jpg", "escudonob.jpeg", "escudonob.webp"]

# Palabras que nunca deben aparecer en las frases motivadoras
PALABRAS_EXCLUIDAS = ["pecho", "gigante", "central"]

_FRASES_BASE = [
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
    "El esfuerzo de hoy es la marca de mañana.",
    "Nadie se arrepiente de haber entrenado.",
    "La pileta es el lugar donde se forja el carácter.",
    "Pequeñas mejoras, todos los días, hacen grandes nadadores.",
    "El talento te pone en el agua; la disciplina te lleva al podio.",
    "Respirá, empujá la pared y andá por más.",
    "Los límites están para nadarlos de largo.",
    "Entrená como si la próxima competencia fuera mañana.",
    "Con la rojinegra, cada brazada vale doble.",
    "La mejor versión de vos está a un entrenamiento de distancia.",
]

FRASES = [f for f in _FRASES_BASE if not any(p in f.lower() for p in PALABRAS_EXCLUIDAS)]

_MIME = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _img_data_uri(ruta: Path) -> str:
    return f"data:{_MIME.get(ruta.suffix.lower(), 'image/png')};base64," + base64.b64encode(ruta.read_bytes()).decode()


@st.cache_data
def escudo_src() -> str:
    """Escudo embebido en base64 (no depende de internet); si falta el archivo usa GitHub."""
    try:
        return _img_data_uri(ESCUDO_PATH)
    except Exception:
        return ESCUDO_URL


@st.cache_data
def escudo_nob_src() -> str | None:
    """Escudo de Newell's para el lado derecho del banner, o None si el archivo no está."""
    for nombre in ESCUDO_NOB_CANDIDATOS:
        ruta = RAIZ / nombre
        if ruta.exists():
            try:
                if ruta.suffix.lower() == ".svg":
                    return _img_data_uri(ruta)
                # Achicar a 256 px: se muestra a 84 px y viaja embebido en cada página
                from io import BytesIO
                from PIL import Image
                img = Image.open(ruta).convert("RGBA")
                img.thumbnail((256, 256))
                buf = BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
            except Exception:
                return None
    return None


def ahora_arg():
    return datetime.now(timezone.utc) - timedelta(hours=3)


def frase_motivadora(pagina: str = "") -> str:
    """Frase al azar que cambia en cada ingreso (login) y es distinta en cada página.

    El orden se baraja una vez por sesión, así la frase no cambia con cada clic
    dentro de la misma página, pero sí la próxima vez que el nadador ingrese.
    """
    if "nob_frases_orden" not in st.session_state:
        orden = list(range(len(FRASES)))
        random.shuffle(orden)
        st.session_state.nob_frases_orden = orden
        st.session_state.nob_frases_pag = {}
    asignadas = st.session_state.nob_frases_pag
    if pagina not in asignadas:
        asignadas[pagina] = st.session_state.nob_frases_orden[len(asignadas) % len(FRASES)]
    return FRASES[asignadas[pagina]]


def hero(titulo: str, icono: str | None = None, subtitulo: str | None = None,
         saludar: bool | None = None, eyebrow: str = "Newell's Old Boys"):
    """Encabezado institucional: escudo, título y frase motivadora.

    `icono` y `saludar` se mantienen por compatibilidad con llamadas existentes, pero ya no se usan.
    """
    frase = html.escape(subtitulo) if subtitulo else html.escape(frase_motivadora(titulo))
    nob = escudo_nob_src()
    escudo_der = f'<img class="nob-hero-crest der" src="{nob}" alt="Escudo Newell\'s Old Boys">' if nob else ""
    st.markdown(
        f"""
        <div class="nob-hero">
            <div class="nob-hero-wave"></div>
            <img class="nob-hero-crest" src="{escudo_src()}" alt="Escudo Complejo Acuático">
            <div class="nob-hero-body">
                <div class="nob-hero-eyebrow">{html.escape(eyebrow)}</div>
                <div class="nob-hero-title">{html.escape(titulo)}</div>
                <div class="nob-hero-sub">“{frase}”</div>
            </div>
            {escudo_der}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _alternar_panel_nav():
    st.session_state.nav_mas_abierto = not st.session_state.get("nav_mas_abierto", False)


def barra_movil(principales, nombre, extras, activo=None):
    """Barra de navegación fija abajo, SOLO en el celular (en computadora no se muestra).

    Estructura (de arriba hacia abajo):
      - Panel desplegable con `extras` (se abre/cierra con la flecha junto al nombre).
      - Fila principal fija de 5 botones `principales` (icono, etiqueta); el del medio es el
        botón central elevado y, si su icono es "escudo", muestra el escudo del club.
      - Franja inferior: nombre del nadador (va a Mi Ficha) + botón "Más" con flecha. El rincón derecho
        queda libre para el sello de Streamlit Cloud.

    `activo`: índice (0-4) de la página actual en la fila principal, o None.
    Devuelve ("principal", i) | ("ficha",) | ("extra", i) | None.
    """
    abierto = st.session_state.get("nav_mas_abierto", False)

    css = [f'.st-key-bn_{i} button::after {{ content: "{e.replace(chr(34), "")}"; }}'
           for i, (_, e) in enumerate(principales)]
    if principales[2][0] == "escudo":
        css.append(
            '.st-key-bn_2 button p { visibility: hidden; }'
            f'.st-key-bn_2 button {{ background-image: url("{ESCUDO_URL}") !important; '
            'background-size: 50px 50px !important; background-position: center 6px !important; '
            'background-repeat: no-repeat !important; }'
        )
    if activo is not None:
        css.append(
            f'.st-key-bn_{activo} button::after {{ color: #FF4D57 !important; font-weight: 800 !important; }}'
            f'.st-key-bn_{activo} button {{ box-shadow: inset 0 2px 0 #E30613 !important; }}'
            if activo != 2 else
            '.st-key-bn_2 button { box-shadow: 0 0 0 3px rgba(227,6,19,0.35), 0 6px 18px rgba(227,6,19,0.45) !important; }'
        )
    css += [f'.st-key-bnx_{i} button::after {{ content: "{e.replace(chr(34), "")}"; }}'
            for i, (_, e) in enumerate(extras)]

    accion = None
    with st.container(key="nob_bottom_nav"):
        # Los estilos van dentro de la barra fija para no sumar espacio arriba de la página
        st.html(f"<style>{''.join(css)}</style>")

        if abierto and len(extras) > 1:
            with st.container(key="bn_panel"):
                for fila in range(0, len(extras), 2):
                    for col, (j, (icono, _)) in zip(st.columns(2, gap="small"),
                                                    list(enumerate(extras))[fila:fila + 2]):
                        with col:
                            if st.button(icono, key=f"bnx_{j}", use_container_width=True):
                                accion = ("extra", j)

        with st.container(key="bn_row"):
            for i, (col, (icono, _)) in enumerate(zip(st.columns(5, gap="small"), principales)):
                with col:
                    if st.button("·" if icono == "escudo" else icono, key=f"bn_{i}", use_container_width=True):
                        accion = ("principal", i)

        with st.container(key="bn_strip", horizontal=True, vertical_alignment="center"):
            if st.button(nombre, key="bn_nombre"):
                accion = ("ficha",)
            if len(extras) == 1:
                # Una sola opción extra (hoy, para el nadador: Cerrar sesión): botón directo, sin panel
                if st.button("", key="bn_mas", icon=":material/logout:", help=extras[0][1]):
                    accion = ("extra", 0)
            elif extras:
                st.button("", key="bn_mas", on_click=_alternar_panel_nav,
                          icon=":material/close:" if abierto else ":material/add:",
                          help="Cerrar" if abierto else "Más opciones")

    if accion is not None:
        st.session_state.nav_mas_abierto = False
    return accion


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

        /* ---------- Encabezado institucional ---------- */
        .nob-hero {
            position: relative; overflow: hidden;
            display: flex; align-items: center; gap: 20px;
            padding: 22px 24px; margin-bottom: 22px;
            border-radius: 20px;
            background: linear-gradient(120deg, #2A0306 0%, #160204 45%, #0E0F12 100%);
            border: 1px solid rgba(227,6,19,0.28);
            box-shadow: 0 18px 40px rgba(0,0,0,0.45);
            animation: nobUp .5s ease-out both;
        }
        .nob-hero::before {
            content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
            background: linear-gradient(90deg, #E30613 0%, #FF4D57 40%, rgba(227,6,19,0.15) 100%);
        }
        .nob-hero-wave {
            position: absolute; right: -80px; top: -90px; width: 260px; height: 260px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(227,6,19,0.28), transparent 65%);
        }
        .nob-hero-crest {
            position: relative; flex: 0 0 auto;
            width: 84px; height: 84px; object-fit: contain;
            filter: drop-shadow(0 8px 18px rgba(227,6,19,0.40));
        }
        .nob-hero-body { position: relative; min-width: 0; flex: 1 1 auto; }
        .nob-hero-crest.der { margin-left: auto; filter: drop-shadow(0 8px 18px rgba(0,0,0,0.5)); }
        .nob-hero-eyebrow {
            font-size: 11px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase;
            color: #FF4D57; margin-bottom: 4px;
        }
        .nob-hero-title {
            font-size: 28px; font-weight: 900; line-height: 1.1;
            color: #fff; letter-spacing: -0.6px;
        }
        .nob-hero-sub {
            margin-top: 8px; padding-left: 12px;
            border-left: 2px solid rgba(227,6,19,0.7);
            font-size: 14px; font-style: italic; line-height: 1.4; color: rgba(255,255,255,0.75);
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

        /* ---------- Perfil interactivo (Inicio) ---------- */
        /* Tarjeta centrada estilo carnet */
        .st-key-nob_profile {
            padding: 22px 18px 18px; border-radius: 20px; margin-bottom: 4px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
            align-items: center; text-align: center; gap: 8px !important;
        }
        .st-key-nob_profile .nob-avatar { margin: 0 auto 12px; }
        .st-key-nob_profile [data-testid="stElementContainer"] { width: 100% !important; display: flex; justify-content: center; }
        .st-key-nob_profile [data-testid="stMarkdown"],
        .st-key-nob_profile [data-testid="stMarkdownContainer"] { width: 100% !important; }
        .nob-id-row {
            display: grid; grid-template-columns: repeat(3, 1fr);
            width: 100%; max-width: 460px; margin: 6px auto 0;
            padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.08);
        }
        .nob-id-row > div { padding: 2px 6px; text-align: center; }
        .nob-id-row > div + div { border-left: 1px solid rgba(255,255,255,0.10); }
        .nob-id-row small {
            display: block; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
            text-transform: uppercase; color: rgba(255,255,255,0.5);
        }
        .nob-id-row b { display: block; margin-top: 4px; font-size: 18px; font-weight: 800; color: #fff; }
        .nob-id-row b.cat { color: #6FDB74; }
        .st-key-nob_medals [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        .st-key-nob_medals [data-testid="stColumn"] { min-width: 0 !important; }

        /* Nombre como enlace a la ficha */
        .st-key-btn_nombre_perfil button {
            background: none !important; border: none !important; box-shadow: none !important;
            padding: 0 !important; min-height: 0 !important; justify-content: center !important;
            transform: none !important;
        }
        .st-key-btn_nombre_perfil button p {
            font-size: 26px !important; font-weight: 900 !important; color: #fff; text-align: center;
            line-height: 1.15; letter-spacing: -0.4px;
        }
        .st-key-btn_nombre_perfil button p::after {
            content: "  →"; color: #FF4D57; font-weight: 700; opacity: .0; transition: opacity .15s;
        }
        .st-key-btn_nombre_perfil button:hover p { color: #FF4D57 !important; }
        .st-key-btn_nombre_perfil button:hover p::after { opacity: 1; }
        .st-key-btn_nombre_perfil [data-testid="stTooltipHoverTarget"] { justify-content: center; }

        /* Medallas como tarjetas clicables */
        .st-key-nob_medals button {
            flex-direction: column !important; gap: 2px;
            min-height: 74px !important; border-radius: 16px !important;
        }
        .st-key-nob_medals button p { font-size: 22px !important; font-weight: 900 !important; color: #fff; }
        .st-key-nob_medals button::after {
            font-size: 10px; letter-spacing: 1.4px; font-weight: 700; color: rgba(255,255,255,0.5);
        }
        .st-key-med_oro button    { background: rgba(255,215,0,0.07) !important;  border-color: rgba(255,215,0,0.35) !important; }
        .st-key-med_plata button  { background: rgba(200,200,200,0.06) !important; border-color: rgba(200,200,200,0.30) !important; }
        .st-key-med_bronce button { background: rgba(205,127,50,0.07) !important; border-color: rgba(205,127,50,0.35) !important; }
        .st-key-med_oro button::after    { content: "OROS"; }
        .st-key-med_plata button::after  { content: "PLATAS"; }
        .st-key-med_bronce button::after { content: "BRONCES"; }
        /* Total de podios: tarjeta informativa (sin acción) */
        .nob-med-info {
            min-height: 74px; border-radius: 16px; display: flex; flex-direction: column;
            align-items: center; justify-content: center; gap: 2px;
            background: rgba(227,6,19,0.10); border: 1px dashed rgba(227,6,19,0.40);
        }
        .nob-med-info .v { font-size: 22px; font-weight: 900; color: #fff; line-height: 1.3; }
        .nob-med-info .l { font-size: 10px; letter-spacing: 1.4px; font-weight: 700; color: rgba(255,255,255,0.5); text-transform: uppercase; }

        /* Estilos frecuentes: tarjetas simples (número + estilo), tocables */
        .st-key-nob_estilos [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        .st-key-nob_estilos [data-testid="stColumn"] { min-width: 0 !important; }
        .st-key-nob_estilos button {
            flex-direction: column !important; gap: 2px;
            min-height: 72px !important; border-radius: 14px !important;
            background: rgba(255,255,255,0.035) !important; border-color: rgba(255,255,255,0.08) !important;
        }
        .st-key-nob_estilos button p { font-size: 22px !important; font-weight: 800 !important; color: #fff; line-height: 1.1; }
        .st-key-nob_estilos button::after {
            font-size: 10px; letter-spacing: 1px; font-weight: 600; color: rgba(255,255,255,0.5);
            max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .st-key-nob_estilos button:hover { border-color: rgba(227,6,19,0.5) !important; transform: translateY(-2px); }

        /* Encabezado del detalle por estilo */
        .nob-est-head {
            padding: 14px 16px; border-radius: 16px; margin-bottom: 6px;
            background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03));
            border: 1px solid rgba(227,6,19,0.30);
        }
        .nob-est-head { text-align: center; padding: 18px 16px 16px; }
        .nob-est-name { font-size: 26px; font-weight: 900; color: #fff; text-transform: uppercase; letter-spacing: .5px; line-height: 1.1; }
        .nob-est-desc { margin-top: 4px; font-size: 13px; color: rgba(255,255,255,0.65); }
        .nob-medrow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; }
        .nob-medrow > div {
            padding: 10px 4px; border-radius: 14px; text-align: center;
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-medrow .v { font-size: 20px; font-weight: 900; color: #fff; line-height: 1.2; }
        .nob-medrow .l { font-size: 10px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: rgba(255,255,255,0.5); margin-top: 2px; }
        .nob-medrow .gold   { background: rgba(255,215,0,0.07);   border-color: rgba(255,215,0,0.35); }
        .nob-medrow .silver { background: rgba(200,200,200,0.06); border-color: rgba(200,200,200,0.30); }
        .nob-medrow .bronze { background: rgba(205,127,50,0.07);  border-color: rgba(205,127,50,0.35); }
        .nob-medrow .total  { background: rgba(227,6,19,0.10);    border-color: rgba(227,6,19,0.40); }
        /* ---------- Barra de navegación inferior: SOLO celular ---------- */
        .st-key-nob_bottom_nav { display: none !important; }
        /* El envoltorio de Streamlit alrededor de la barra no debe ocupar lugar ni sumar separación */
        :has(> .st-key-nob_bottom_nav) { display: contents !important; }
        .st-key-nob_bottom_nav > [data-testid="stElementContainer"]:has(style) { display: none; }
        @media (max-width: 640px) {
            .st-key-nob_bottom_nav {
                display: flex !important; position: fixed; left: 0; right: 0; bottom: 0; z-index: 999990;
                gap: 0 !important;
                padding: 4px 6px calc(4px + env(safe-area-inset-bottom));
                background: rgba(10,11,14,0.97); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                border-top: 1px solid rgba(255,255,255,0.08);
            }
            /* Ocultar el menú lateral en el celular: todo está en la barra */
            [data-testid="stExpandSidebarButton"] { display: none !important; }

            /* Fila principal fija */
            .st-key-bn_row { margin-top: 4px; }
            .st-key-bn_row [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 2px !important; align-items: flex-end; }
            .st-key-bn_row [data-testid="stColumn"] { min-width: 0 !important; }
            .st-key-bn_row button {
                flex-direction: column !important; gap: 2px; min-height: 64px !important; padding: 6px 0 !important;
                background: transparent !important; border: none !important; box-shadow: none !important; transform: none !important;
            }
            .st-key-bn_row button p { font-size: 26px !important; line-height: 1.1; }
            .st-key-bn_row button::after {
                font-size: 10.5px; font-weight: 600; color: rgba(255,255,255,0.65); white-space: nowrap;
                letter-spacing: -0.2px;
            }

            /* Franja inferior: nombre (→ Mi Ficha) + botón Más; el rincón derecho queda libre para el sello */
            .st-key-bn_strip {
                gap: 10px !important; padding: 4px 6px 0; margin-top: 2px;
                border-top: 1px solid rgba(255,255,255,0.06); min-height: 48px;
            }
            .st-key-bn_strip button {
                min-height: 40px !important; padding: 2px 8px !important; border: none !important;
                background: transparent !important; box-shadow: none !important; transform: none !important;
            }
            .st-key-bn_nombre button p { font-size: 16px !important; font-weight: 800 !important; color: #fff; white-space: nowrap; }
            .st-key-bn_mas button {
                border-radius: 999px !important; min-width: 64px !important; padding: 2px 16px !important;
                background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.16) !important;
                box-shadow: none !important;
            }
            .st-key-bn_mas button [data-testid="stIconMaterial"] { font-size: 26px !important; color: #fff; margin: 0 !important; }

            /* Panel desplegable de más opciones */
            .st-key-bn_panel {
                gap: 6px !important; padding: 8px 4px 10px; margin-bottom: 4px;
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }
            .st-key-bn_panel [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 6px !important; }
            .st-key-bn_panel [data-testid="stColumn"] { min-width: 0 !important; }
            .st-key-bn_panel button {
                flex-direction: row !important; justify-content: flex-start !important; gap: 8px;
                min-height: 44px !important; border-radius: 12px !important; padding: 6px 12px !important;
                background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.10) !important;
            }
            .st-key-bn_panel button > div { flex: 0 0 auto !important; width: auto !important; }
            .st-key-bn_panel button p { font-size: 18px !important; }
            .st-key-bn_panel button::after { font-size: 13px; font-weight: 700; color: #fff; white-space: nowrap; }
            /* Botón central elevado */
            .st-key-bn_2 button {
                position: relative; min-height: 76px !important; margin-top: -20px;
                border-radius: 22px !important;
                background-color: #1A0204 !important;
                border: 2px solid #E30613 !important;
                box-shadow: 0 6px 18px rgba(227,6,19,0.45) !important;
                padding-top: 58px !important;
                background-size: 50px 50px !important;
            }
            .st-key-bn_2 button p { position: absolute; top: 10px; left: 0; right: 0; }
            .st-key-bn_2 button::after { color: #FF6A72; font-weight: 800; }
            .block-container { padding-bottom: 160px !important; }
        }

        /* Ficha superior de la ventana de podios: medallas tocables para cambiar de medalla */
        .st-key-dlg_med_head {
            text-align: center; gap: 4px !important;
            padding: 18px 16px 16px; border-radius: 16px; margin-bottom: 6px;
            background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03));
            border: 1px solid rgba(227,6,19,0.30);
        }
        .st-key-dlg_med_head [data-testid="stElementContainer"],
        .st-key-dlg_med_head [data-testid="stMarkdown"],
        .st-key-dlg_med_head [data-testid="stMarkdownContainer"] { width: 100% !important; text-align: center; }
        .st-key-dlg_med_head [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; margin-top: 10px; }
        .st-key-dlg_med_head [data-testid="stColumn"] { min-width: 0 !important; }
        .st-key-dlg_med_head button {
            flex-direction: column !important; gap: 0; min-height: 62px !important; border-radius: 14px !important;
            padding: 6px 4px !important;
        }
        .st-key-dlg_med_head button p { font-size: 20px !important; font-weight: 900 !important; color: #fff; }
        .st-key-dlg_med_head button::after {
            font-size: 10px; letter-spacing: 1.2px; font-weight: 700; color: rgba(255,255,255,0.5);
        }
        .st-key-dmed_1 button { background: rgba(255,215,0,0.07) !important;  border-color: rgba(255,215,0,0.35) !important; }
        .st-key-dmed_2 button { background: rgba(200,200,200,0.06) !important; border-color: rgba(200,200,200,0.30) !important; }
        .st-key-dmed_3 button { background: rgba(205,127,50,0.07) !important; border-color: rgba(205,127,50,0.35) !important; }
        .st-key-dmed_1 button::after { content: "OROS"; }
        .st-key-dmed_2 button::after { content: "PLATAS"; }
        .st-key-dmed_3 button::after { content: "BRONCES"; }
        .nob-med-info.dlg { min-height: 62px; border-style: solid; opacity: .5; }
        .nob-med-info.dlg .v { font-size: 20px; }
        [class*="st-key-pie_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        [class*="st-key-pie_"] [data-testid="stColumn"] { min-width: 0 !important; }
        .nob-medrow .off { opacity: .45; }
        .nob-medrow .on  { border-width: 2px; box-shadow: 0 0 0 3px rgba(255,255,255,0.06); }
        .st-key-nob_medals button:hover { transform: translateY(-2px); box-shadow: 0 10px 22px rgba(0,0,0,0.35); }

        /* Vista rápida: podios y mejores marcas */
        .nob-rec {
            display: flex; align-items: center; gap: 12px;
            padding: 10px 14px; margin-bottom: 8px; border-radius: 14px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
            border-left: 3px solid rgba(255,255,255,0.2);
        }
        .nob-rec.m1 { border-left-color: #FFD700; }
        .nob-rec.m2 { border-left-color: #C8C8C8; }
        .nob-rec.m3 { border-left-color: #CD7F32; }
        .nob-rec-med { font-size: 24px; }
        .nob-rec-body { flex: 1; min-width: 0; }
        .nob-rec-t { font-size: 15px; font-weight: 700; color: #fff; }
        .nob-rec-m { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 2px; }
        .nob-rec-time { font-family: ui-monospace, 'JetBrains Mono', monospace; font-size: 17px; font-weight: 800; color: #fff; }
        .nob-rec-tag {
            margin-left: 6px; padding: 1px 7px; border-radius: 999px; font-size: 10px; font-weight: 700;
            background: rgba(227,6,19,0.18); color: #FF6A72; border: 1px solid rgba(227,6,19,0.4); vertical-align: middle;
        }
        .nob-rec-tag.pb { background: rgba(255,215,0,0.12); color: #FFD54F; border-color: rgba(255,215,0,0.4); }
        .nob-rec-pos {
            display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%;
            font-size: 12px; font-weight: 800; color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.06);
        }
        .nob-pb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
        .nob-pb {
            padding: 12px 14px; border-radius: 14px;
            background: linear-gradient(160deg, rgba(227,6,19,0.12), rgba(227,6,19,0.02));
            border: 1px solid rgba(227,6,19,0.25);
        }
        .nob-pb .k { font-size: 11px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: rgba(255,255,255,0.6); }
        .nob-pb .v { font-family: ui-monospace, 'JetBrains Mono', monospace; font-size: 19px; font-weight: 800; color: #fff; margin-top: 4px; }

        /* Tarjetas de resumen (Inicio) */
        .nob-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
        .nob-duo .nob-goal { margin-bottom: 0; }
        .nob-next {
            padding: 16px 18px; border-radius: 18px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-next-k { font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(255,255,255,0.5); }
        .nob-next-days { font-size: 34px; font-weight: 900; color: #fff; line-height: 1.1; margin-top: 6px; }
        .nob-next-days small { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.6); margin-left: 4px; }
        .nob-next-name { font-size: 14px; font-weight: 700; color: #fff; margin-top: 6px; }
        .nob-next-meta { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 2px; }
        .nob-tag {
            display: inline-block; margin-top: 8px; padding: 3px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 700; letter-spacing: .5px;
        }
        .nob-tag.ok   { background: rgba(76,175,80,0.15); color: #7EE083; border: 1px solid rgba(76,175,80,0.4); }
        .nob-tag.warn { background: rgba(255,193,7,0.12); color: #FFD54F; border: 1px solid rgba(255,193,7,0.4); }

        @media (max-width: 520px) {
            .st-key-nob_estilos button { padding-left: 4px !important; padding-right: 4px !important; }
            .st-key-nob_estilos button::after { font-size: 9px; letter-spacing: 0.2px; }
            .nob-hero { gap: 14px; padding: 18px; }
            .nob-hero-crest { width: 56px; height: 56px; }
            .nob-hero-crest.der { width: 44px; height: 44px; }
            .nob-duo { grid-template-columns: 1fr; }
            .nob-hero-title { font-size: 23px; }
            .nob-stats { grid-template-columns: repeat(2, 1fr); }
            .nob-profile { gap: 12px; padding: 14px; }
            .nob-avatar { width: 46px; height: 46px; font-size: 18px; border-radius: 14px; }
            .nob-cat-badge { padding: 6px 10px; }
            .nob-cat-badge b { font-size: 17px; }
        }
        @keyframes nobUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
