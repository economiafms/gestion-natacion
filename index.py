import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from nob_ui import aplicar_tema, barra_movil

# --- 1. CONFIGURACIÓN DEL ÍCONO (ENLACE GITHUB RAW) ---
# Usamos el enlace RAW directo de GitHub. Esto es lo más compatible que existe.
# Asegúrate de que el archivo 'escudo.png' esté en la raíz de tu repo.
ICON_URL = "https://raw.githubusercontent.com/economiafms/gestion-natacion/main/escudo.png"

st.set_page_config(
    page_title="Acceso NOB", 
    layout="centered",
    page_icon=ICON_URL
)

# --- TRUCO PARA FORZAR ÍCONO EN ANDROID/IOS ---
# Inyectamos código HTML para intentar engañar al navegador del celular
# y que use nuestro escudo en lugar del logo de Streamlit.
st.markdown(f"""
    <style>
        /* Esto oculta el código inyectado para que no se vea en la pantalla */
        .app-icon-fix {{display: none;}}
    </style>
    <div class="app-icon-fix">
        <link rel="apple-touch-icon" sizes="180x180" href="{ICON_URL}">
        <link rel="icon" type="image/png" sizes="32x32" href="{ICON_URL}">
        <link rel="icon" type="image/png" sizes="16x16" href="{ICON_URL}">
    </div>
""", unsafe_allow_html=True)

# --- 2. GESTIÓN DE ESTADO ---
if "role" not in st.session_state: st.session_state.role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nro_socio" not in st.session_state: st.session_state.nro_socio = None
if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False 
if "ver_nadador_especifico" not in st.session_state: st.session_state.ver_nadador_especifico = None
if "show_login_form" not in st.session_state: st.session_state.show_login_form = False 

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_tablas_login():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "users": conn.read(worksheet="User")
        }
    except: return None

# --- 4. FUNCIONES LOGIN / LOGOUT ---
def limpiar_socio(valor):
    if pd.isna(valor): return ""
    return str(valor).split('.')[0].strip()

def validar_socio():
    raw_input = st.session_state.input_socio
    socio_limpio = raw_input.split("-")[0].strip()
    
    if not socio_limpio:
        st.warning("Ingrese un número.")
        return

    db = cargar_tablas_login()
    if db:
        df_u = db['users'].copy()
        df_n = db['nadadores'].copy()
        
        df_u['nrosocio_str'] = df_u['nrosocio'].apply(limpiar_socio)
        df_n['nrosocio_str'] = df_n['nrosocio'].apply(limpiar_socio)
        
        usuario = df_u[df_u['nrosocio_str'] == socio_limpio]
        
        if not usuario.empty:
            perfil = usuario.iloc[0]['perfil'].upper()
            datos = df_n[df_n['nrosocio_str'] == socio_limpio]
            
            if not datos.empty:
                st.session_state.role = perfil
                st.session_state.user_name = f"{datos.iloc[0]['nombre']} {datos.iloc[0]['apellido']}"
                st.session_state.user_id = datos.iloc[0]['codnadador']
                st.session_state.nro_socio = socio_limpio
                st.success(f"¡Bienvenido {datos.iloc[0]['nombre']}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Socio válido pero sin ficha de nadador activa.")
        else:
            st.error("Número de socio no registrado.")

def ir_a_mi_ficha_nav():
    """Abre el Fichero directo en la ficha del usuario (nadador: Mi Ficha; manager: Ficha Técnica)."""
    st.session_state.ver_nadador_especifico = st.session_state.user_name
    st.session_state.fichero_tab_inicial = "ficha"
    db = cargar_tablas_login()
    if db:
        me = db['nadadores'][db['nadadores']['codnadador'] == st.session_state.user_id]
        if not me.empty:
            st.session_state.nadador_seleccionado = f"{str(me.iloc[0]['apellido']).upper()}, {me.iloc[0]['nombre']}"
    st.switch_page("pages/2_visualizar_datos.py")


def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- NUEVA FUNCIÓN: INSTRUCCIONES DE INSTALACIÓN ---
def pwa_install_button():
    st.write("---")
    with st.expander("📲 INSTALAR APP EN TU CELULAR"):
        st.markdown("""
        Puedes agregar esta aplicación a tu pantalla de inicio para un acceso más rápido:
        
        **🤖 Android (Chrome):**
        1. Toca los tres puntos **(⋮)** arriba a la derecha.
        2. Selecciona **'Instalar aplicación'** o 'Agregar a la pantalla de inicio'.
        
        **🍎 iPhone (Safari):**
        1. Toca el botón **Compartir** (cuadrado con flecha arriba) en la barra inferior.
        2. Desliza hacia abajo y toca en **'Agregar al inicio'**.
        """)
        st.info("Nota: Tenerla instalada te permite acceder más rápido a tus tiempos, rutinas, categoría y seguimiento personal. Es una herramienta pensada para acompañar tu evolución deportiva día a día. Tu progreso también se construye con constancia.")

# --- 5. PANTALLA DE LOGIN ---
def login_screen():
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800;900&display=swap');

            /* Ocultar sidebar, header y footer de Streamlit en el login */
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
            header[data-testid="stHeader"], footer {{ display: none !important; }}

            /* Fondo: negro profundo con resplandores rojos y textura de agua */
            [data-testid="stAppViewContainer"] {{
                background:
                    radial-gradient(900px 500px at 15% -10%, rgba(227,6,19,0.28), transparent 60%),
                    radial-gradient(700px 450px at 110% 110%, rgba(227,6,19,0.18), transparent 60%),
                    repeating-linear-gradient(170deg, rgba(255,255,255,0.015) 0 2px, transparent 2px 14px),
                    #07080B;
            }}
            .block-container {{ max-width: 440px; padding-top: 3.5rem; padding-bottom: 2rem; }}
            .block-container {{ font-family: 'Inter', sans-serif; }}
            .block-container p, .block-container input, .block-container button,
            .block-container summary span:not([data-testid="stIconMaterial"]) {{ font-family: 'Inter', sans-serif; }}

            /* Tarjeta de marca */
            .nob-card {{
                position: relative;
                text-align: center;
                padding: 38px 28px 26px;
                border-radius: 24px;
                background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
                border: 1px solid rgba(255,255,255,0.08);
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                box-shadow: 0 24px 60px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.06);
                overflow: hidden;
                animation: nobFadeUp .6s ease-out both;
            }}
            .nob-card::before {{
                content: "";
                position: absolute; inset: 0 0 auto 0; height: 4px;
                background: linear-gradient(90deg, #E30613 0 50%, #111 50% 100%);
            }}
            .nob-crest {{
                width: 96px; height: 96px; object-fit: contain;
                filter: drop-shadow(0 10px 22px rgba(227,6,19,0.45));
                animation: nobFloat 4s ease-in-out infinite;
            }}
            .nob-eyebrow {{
                margin-top: 18px;
                font-size: 11px; font-weight: 600;
                letter-spacing: 3px; text-transform: uppercase;
                color: #E30613;
            }}
            .nob-title {{
                margin: 6px 0 8px;
                font-size: 28px; font-weight: 900; line-height: 1.05;
                letter-spacing: -0.5px; text-transform: uppercase;
                color: #FFFFFF;
            }}
            .nob-quote {{
                font-size: 15px; font-style: italic;
                color: rgba(255,255,255,0.6);
            }}
            .nob-divider {{
                height: 1px; margin: 24px 0 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
            }}
            .nob-label {{
                margin: 22px 0 8px 2px;
                font-size: 12px; font-weight: 600;
                letter-spacing: 1.5px; text-transform: uppercase;
                color: rgba(255,255,255,0.55);
            }}

            /* Input */
            [data-testid="stTextInput"] div[data-baseweb="input"] {{
                background: rgba(255,255,255,0.04) !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                border-radius: 14px !important;
                transition: border-color .2s, box-shadow .2s;
            }}
            [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {{
                border-color: #E30613 !important;
                box-shadow: 0 0 0 4px rgba(227,6,19,0.18) !important;
            }}
            [data-testid="stTextInput"] input {{
                background: transparent !important;
                color: #fff !important;
                font-size: 17px !important; font-weight: 500;
                letter-spacing: 1px;
                padding: 14px 16px !important;
            }}
            [data-testid="stTextInput"] input::placeholder {{ color: rgba(255,255,255,0.3); }}

            /* Botón principal */
            .stButton > button[kind="primary"] {{
                margin-top: 6px;
                height: 52px;
                border: none; border-radius: 14px;
                background: linear-gradient(135deg, #FF1F2D 0%, #E30613 55%, #A8040E 100%);
                font-weight: 800; font-size: 15px; letter-spacing: 2px;
                box-shadow: 0 10px 24px rgba(227,6,19,0.35);
                transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
            }}
            .stButton > button[kind="primary"]:hover {{
                transform: translateY(-1px);
                filter: brightness(1.08);
                box-shadow: 0 14px 30px rgba(227,6,19,0.45);
            }}
            .stButton > button[kind="primary"]:active {{ transform: translateY(1px); }}

            /* Expander de instalación */
            [data-testid="stExpander"] details {{
                border-radius: 14px !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                background: rgba(255,255,255,0.025);
            }}
            hr {{ border-color: rgba(255,255,255,0.06) !important; }}

            .nob-foot {{
                text-align: center; margin-top: 18px;
                font-size: 12px; color: rgba(255,255,255,0.3);
            }}

            @keyframes nobFadeUp {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
            @keyframes nobFloat {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-6px); }} }}
        </style>

        <div class="nob-card">
            <img class="nob-crest" src="{ICON_URL}" alt="Escudo NOB">
            <div class="nob-eyebrow">Natación · Gestión deportiva</div>
            <div class="nob-title">Newell's Old Boys</div>
            <div class="nob-quote">"Del deporte sos la gloria"</div>
            <div class="nob-divider"></div>
        </div>
        <div class="nob-label">Número de socio</div>
    """, unsafe_allow_html=True)

    st.text_input("Ingrese Nro de Socio", key="input_socio", placeholder="Ej: 123456-01", label_visibility="collapsed")
    if st.button("INGRESAR", type="primary", use_container_width=True):
        validar_socio()
    
    # AGREGADO: Llamada a la función de instrucciones
    pwa_install_button()

# --- 6. DEFINICIÓN DE PÁGINAS ---
pg_inicio = st.Page("pages/1_inicio.py", title="Inicio", icon="🏠")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Fichero", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_entrenamientos = st.Page("pages/5_entrenamientos.py", title="Entrenamientos", icon="🏋️")
pg_categoria = st.Page("pages/6_mi_categoria.py", title="Mi Categoría", icon="🏅")
pg_agenda = st.Page("pages/7_agenda.py", title="Agenda", icon="📅")
pg_rutinas = st.Page("pages/8_rutinas.py", title="Rutinas", icon="📝")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga de Datos", icon="⚙️")
pg_login_obj = st.Page(login_screen, title="Acceso", icon="🔒")

# --- 7. RUTEO Y MENÚ ---
if not st.session_state.role:
    pg = st.navigation([pg_login_obj])
    pg.run()
else:
    # --- MENÚ PRINCIPAL ---
    menu_pages = {
        "Principal": [pg_inicio, pg_datos, pg_rutinas, pg_entrenamientos, pg_categoria, pg_agenda]
    }

    # --- MENÚ HERRAMIENTAS ---
    if st.session_state.role in ["M", "P"]:
        menu_pages["Herramientas"] = [pg_ranking, pg_simulador]

        if st.session_state.admin_unlocked:
            menu_pages["Administración"] = [pg_carga]

    pg = st.navigation(menu_pages)
    aplicar_tema()

    # --- BARRA INFERIOR (SOLO CELULAR) ---
    # [Rutinas][Entrenamientos][ CENTRO ][Mi Categoría][Agenda]
    # Centro: Inicio (escudo); estando en Inicio, el centro es Mi Ficha.
    # Si estoy en una de las laterales, ese lugar pasa a ser Mi Ficha.
    FICHA = ("👤", "Mi Ficha", "ficha")
    actual = pg.url_path
    laterales = [("📝", "Rutinas", pg_rutinas), ("⏱️", "Entrenamientos", pg_entrenamientos),
                 ("🏅", "Mi Categoría", pg_categoria), ("📅", "Agenda", pg_agenda)]
    slots = []
    for icono, etiqueta, destino in laterales:
        slots.append(FICHA if destino.url_path == actual else (icono, etiqueta, destino))
    centro = FICHA if actual == pg_inicio.url_path else ("escudo", "Inicio", pg_inicio)
    slots.insert(2, centro)

    tocado = barra_movil([(s[0], s[1]) for s in slots])
    if tocado is not None:
        destino = slots[tocado][2]
        if destino == "ficha":
            ir_a_mi_ficha_nav()
        else:
            st.switch_page(destino)

    with st.sidebar:
        st.write("") 
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            cerrar_sesion()

    pg.run()



