import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from theme import inject_theme, hide_sidebar

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

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- INSTRUCCIONES DE INSTALACIÓN (PWA) ---
def pwa_install_button():
    with st.expander("Instalar la app en tu celular"):
        st.markdown("""
        Podés agregar esta aplicación a tu pantalla de inicio para un acceso más rápido:

        **Android (Chrome)**
        1. Tocá los tres puntos **(⋮)** arriba a la derecha.
        2. Seleccioná **"Instalar aplicación"** o "Agregar a la pantalla de inicio".

        **iPhone (Safari)**
        1. Tocá el botón **Compartir** (cuadrado con flecha hacia arriba) en la barra inferior.
        2. Deslizá hacia abajo y tocá **"Agregar al inicio"**.
        """)
        st.caption("Tenerla instalada te permite acceder más rápido a tus tiempos, rutinas, categoría y seguimiento personal.")

# --- 5. PANTALLA DE LOGIN ---
def login_screen():
    hide_sidebar()
    inject_theme()

    st.markdown("""
        <style>
            .nob-hero {
                text-align: center;
                padding: 36px 28px 30px;
                border-radius: 22px;
                background:
                    radial-gradient(120% 140% at 50% -20%, rgba(227,6,19,0.22) 0%, rgba(227,6,19,0) 55%),
                    linear-gradient(180deg, #15161c 0%, #0a0a0d 100%);
                border: 1px solid var(--nob-border);
                margin-bottom: 18px;
                box-shadow: 0 18px 40px rgba(0,0,0,0.45);
            }
            .nob-tag {
                display: inline-block;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.4px;
                color: var(--nob-gold);
                background: rgba(255, 201, 60, 0.1);
                border: 1px solid rgba(255, 201, 60, 0.35);
                border-radius: 999px;
                padding: 5px 14px;
                margin-bottom: 16px;
                text-transform: uppercase;
            }
            .nob-title {
                font-family: 'Oswald', sans-serif;
                font-size: 30px;
                font-weight: 800;
                color: var(--nob-text);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin: 4px 0 10px 0;
                line-height: 1.15;
            }
            .nob-title span { color: var(--nob-red); }
            .nob-quote {
                font-size: 15px;
                font-style: italic;
                color: var(--nob-muted);
                letter-spacing: 0.3px;
            }
            .nob-access-label {
                text-align: center;
                color: var(--nob-muted);
                font-family: 'Oswald', sans-serif;
                font-weight: 600;
                letter-spacing: 1.6px;
                font-size: 12px;
                text-transform: uppercase;
                margin: 4px 0 10px 0;
            }
        </style>
        <div class="nob-hero">
            <div class="nob-tag">Complejo Acuático</div>
            <div class="nob-title">NEWELL'S<br/><span>OLD BOYS</span></div>
            <div class="nob-quote">&ldquo;Del deporte sos la gloria&rdquo;</div>
        </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.image("escudo.png", use_container_width=True)

    st.markdown("<div class='nob-access-label'>Acceso Socios</div>", unsafe_allow_html=True)
    st.text_input("Ingrese Nro de Socio", key="input_socio", placeholder="Ej: 123456-01", label_visibility="collapsed")
    if st.button("INGRESAR", type="primary", use_container_width=True):
        validar_socio()

    st.write("")
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

    with st.sidebar:
        st.write("") 
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            cerrar_sesion()

    pg.run()



