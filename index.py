import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

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

# --- 5. PANTALLA DE LOGIN (NUEVO DISEÑO TAILWIND) ---
def login_screen():
    # Inyectamos CSS específico de Tailwind solo para esta pantalla
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@700;900&family=Inter:wght@400;700&family=JetBrains+Mono:wght@500;700&display=swap');

    /* Ocultar elementos nativos de Streamlit */
    [data-testid="stSidebar"] {display: none;}
    header[data-testid="stHeader"] { display: none !important; }

    /* Expandir la pantalla completa (anula el layout=centered solo aquí) */
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    /* Configurar el layout de las dos columnas generadas abajo */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
        min-height: 100vh !important;
        gap: 0 !important;
        background-color: #101319;
    }
    div[data-testid="column"] { padding: 0 !important; }

    /* LADO IZQUIERDO: Imagen de fondo y Gradiente */
    div[data-testid="column"]:nth-child(1) {
        background-image: linear-gradient(to top, #101319, rgba(16,19,25,0.4), transparent), url('https://lh3.googleusercontent.com/aida-public/AB6AXuAMImSYqudmvJAmPD0Phr4ZLP83MuhD9gER7FYwOcbdHShvlBwjDrZHfuCzvTK5SLGBU4QyXBq1u26JxNMbOmC6LPM_h89zpTZPRqSXFUyynCpinKtV0Epm-C911nEwPJtuXFva7BueE33Rqxf14YlEef9Jeg-4wEfBr_91ynAqTL-35-FYWXcJprpJQ7Oz7p1Eu3ouf2cTescVEqDFxWscFDlvIVFHG33RQwKys75VypSce4pvWZVKS5IeX1gawVmOuQ');
        background-size: cover;
        background-position: center;
        border-right: 1px solid #5e3f3b;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }

    /* Ocultar lado izquierdo en celulares */
    @media (max-width: 1024px) {
        div[data-testid="column"]:nth-child(1) { display: none !important; }
    }

    /* LADO DERECHO: Centrado del formulario */
    div[data-testid="column"]:nth-child(2) {
        background-color: #101319 !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 2rem !important;
    }
    
    /* Ajustes dentro de la columna derecha para centrar el formulario */
    div[data-testid="column"]:nth-child(2) > div[data-testid="stVerticalBlock"] {
        margin: auto;
        max-width: 450px;
        width: 100%;
    }

    /* Contenedor del Formulario */
    div[data-testid="stForm"] {
        background-color: #1d2026 !important;
        border-radius: 12px !important;
        padding: 40px 32px 32px 32px !important;
        border: 1px solid #5e3f3b !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
        position: relative !important;
    }

    /* Barra lateral roja */
    div[data-testid="stForm"]::before {
        content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
        background-color: #e30613;
        border-top-left-radius: 12px; border-bottom-left-radius: 12px;
    }

    /* Label de Inputs */
    label[data-testid="stWidgetLabel"] p {
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase !important;
        color: #e9bcb6 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }

    /* Input Streamlit Nativos */
    div[data-testid="stTextInput"] input {
        background-color: #1E1E1E !important;
        border: 1px solid #444444 !important;
        color: white !important;
        padding: 12px !important;
        border-radius: 4px !important;
        font-family: 'Inter', sans-serif !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #e30613 !important;
        box-shadow: 0 0 0 1px #e30613 !important;
    }

    /* Botón Acceder */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #e30613 !important;
        color: white !important;
        width: 100% !important;
        border: none !important;
        padding: 12px !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
        margin-top: 10px !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #c0000c !important;
        color: white !important;
    }

    /* General Body de Streamlit para el login */
    .stApp { background-color: #101319; }

    @media (min-width: 1024px) { .mobile-brand { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

    # Creamos las dos columnas para el split screen
    c1, c2 = st.columns([1, 1])

    # --- Lado Izquierdo ---
    with c1:
        st.markdown("""
        <div style="padding: 48px; position: absolute; bottom: 0; left: 0; width: 100%; z-index: 10;">
            <div style="border-left: 4px solid #e30613; padding-left: 20px; margin-bottom: 24px;">
                <h1 style="font-family: 'Hanken Grotesk', sans-serif; font-size: 42px; font-weight: 900; color: #e30613; text-transform: uppercase; margin:0; line-height: 1.1;">Gestión Natación</h1>
                <p style="font-family: 'Inter', sans-serif; font-size: 18px; color: #e9bcb6; margin-top: 8px; font-weight: 400;">Elite Performance Dashboard</p>
            </div>
            <div style="display: flex; gap: 12px;">
                <div style="background-color: rgba(39, 42, 49, 0.8); backdrop-filter: blur(4px); padding: 8px 16px; border-radius: 6px; border: 1px solid #5e3f3b; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #e30613; font-size: 20px;">⏱️</span>
                    <span style="color: #e1e2eb; font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 700;">00:21.45</span>
                </div>
                <div style="background-color: rgba(39, 42, 49, 0.8); backdrop-filter: blur(4px); padding: 8px 16px; border-radius: 6px; border: 1px solid #5e3f3b; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #e9c400; font-size: 20px;">🏆</span>
                    <span style="color: #e1e2eb; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700;">RECORD</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- Lado Derecho ---
    with c2:
        # Cabecera para celulares
        st.markdown("""
        <div class="mobile-brand" style="display: flex; align-items: center; gap: 12px; margin-bottom: 32px; justify-content: center;">
            <span style="font-size: 32px; color: #e30613;">🏊‍♂️</span>
            <span style="font-family: 'Hanken Grotesk', sans-serif; font-size: 28px; font-weight: 900; color: #e30613; text-transform: uppercase;">Gestión Natación</span>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("""
            <div style="margin-bottom: 24px;">
                <h2 style="font-family: 'Hanken Grotesk', sans-serif; font-size: 26px; font-weight: 700; color: #e1e2eb; margin:0 0 8px 0;">Acceso al Sistema</h2>
                <p style="font-family: 'Inter', sans-serif; color: #e9bcb6; font-size: 14px; margin:0;">Ingresa tus credenciales para acceder al panel de rendimiento.</p>
            </div>
            """, unsafe_allow_html=True)

            # Acoplado a tu estado original "input_socio"
            st.text_input("NÚMERO DE SOCIO", key="input_socio", placeholder="Ej: 123456-01")
            
            st.checkbox("Recordarme en este dispositivo")
            
            # Botón que ejecuta el formulario
            submit_btn = st.form_submit_button("Acceder ➔")

            st.markdown("""
            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #5e3f3b;">
                <p style="font-family: 'Inter', sans-serif; font-size: 12px; color: #e9bcb6; text-align: center; margin:0; line-height: 1.5;">
                    Conexión segura bajo protocolos de Rojinegro Performance. <br/>
                    ¿Necesitas ayuda? <a href="#" style="color: #e30613; text-decoration: none; font-weight: 700;">Contactar a Soporte</a>
                </p>
            </div>
            """, unsafe_allow_html=True)

        # Si se hace click, llamamos directamente a tu lógica original.
        if submit_btn:
            validar_socio()

        # Tu botón de PWA original debajo del login
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
