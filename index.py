import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- 1. CONFIGURACIÓN DEL ÍCONO (ENLACE GITHUB RAW) ---
# IMPORTANTE: usar imagen 512x512
ICON_URL = "https://raw.githubusercontent.com/economiafms/gestion-natacion/main/escudo.png"

st.set_page_config(
    page_title="Acceso NOB",
    layout="centered",
    page_icon=ICON_URL,
    initial_sidebar_state="collapsed"
)

# --- FORZADO AVANZADO PARA ANDROID / PWA ---
st.markdown(f"""
    <meta name="theme-color" content="#000000">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">

    <link rel="apple-touch-icon" sizes="180x180" href="{ICON_URL}">
    <link rel="icon" type="image/png" sizes="32x32" href="{ICON_URL}">
    <link rel="icon" type="image/png" sizes="192x192" href="{ICON_URL}">
    <link rel="icon" type="image/png" sizes="512x512" href="{ICON_URL}">
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
    except:
        return None

# --- 4. FUNCIONES LOGIN / LOGOUT ---
def limpiar_socio(valor):
    if pd.isna(valor):
        return ""
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

# --- NUEVA FUNCIÓN: INSTRUCCIONES DE INSTALACIÓN ---
def pwa_install_button():
    st.write("---")
    with st.expander("📲 INSTALAR APP EN TU CELULAR"):
        st.markdown("""
        Puedes agregar esta aplicación a tu pantalla de inicio para un acceso más rápido:

        **🤖 Android (Chrome):**
        1. Toca los tres puntos (⋮)
        2. Selecciona 'Instalar aplicación'

        **🍎 iPhone (Safari):**
        1. Botón Compartir
        2. 'Agregar al inicio'
        """)
        st.info("Si aparece el ícono viejo, borra caché de Chrome y reinstala.")

# --- 5. PANTALLA DE LOGIN ---
def login_screen():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

    st.markdown("""
        <div style="text-align:center;padding:30px;border-radius:20px;
        background:linear-gradient(180deg,#121212 0%,#000000 100%);
        border:2px solid #333;margin-bottom:20px;">
            <div style="font-size:40px;">🔴⚫ 🏊 ⚫🔴</div>
            <h2 style="color:#E30613;margin:5px;">NEWELL'S OLD BOYS</h2>
            <p style="color:white;font-style:italic;">"Del deporte sos la gloria"</p>
        </div>
    """, unsafe_allow_html=True)

    st.text_input("Ingrese Nro de Socio",
                  key="input_socio",
                  placeholder="Ej: 123456-01",
                  label_visibility="collapsed")

    if st.button("INGRESAR", type="primary", use_container_width=True):
        validar_socio()

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
    menu_pages = {
        "Principal": [pg_inicio, pg_datos, pg_rutinas,
                      pg_entrenamientos, pg_categoria, pg_agenda]
    }

    if st.session_state.role in ["M", "P"]:
        menu_pages["Herramientas"] = [pg_ranking, pg_simulador]

        if st.session_state.admin_unlocked:
            menu_pages["Administración"] = [pg_carga]

    pg = st.navigation(menu_pages)

    with st.sidebar:
        if st.button("Cerrar Sesión",
                     type="secondary",
                     use_container_width=True):
            cerrar_sesion()

    pg.run()
