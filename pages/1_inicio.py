import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Acceso NOB", layout="centered")

# --- 2. GESTIÓN DE ESTADO ---
if "role" not in st.session_state: st.session_state.role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nro_socio" not in st.session_state: st.session_state.nro_socio = None
if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False 
if "ver_nadador_especifico" not in st.session_state: st.session_state.ver_nadador_especifico = None

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
    st.session_state.role = None
    st.session_state.user_name = None
    st.session_state.user_id = None
    st.session_state.admin_unlocked = False
    st.rerun()

# --- 5. PANTALLA DE LOGIN ---
def login_screen():
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;} 
            .login-container {
                text-align: center;
                padding: 30px;
                border-radius: 20px;
                background: linear-gradient(180deg, #121212 0%, #000000 100%);
                border: 2px solid #333;
                margin-bottom: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            }
            .nob-title {
                font-size: 38px;
                font-weight: 900;
                color: #E30613;
                text-transform: uppercase;
                margin: 10px 0 5px 0;
                line-height: 1;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            }
            .nob-quote {
                font-size: 18px;
                font-style: italic;
                color: #ffffff;
                margin-bottom: 20px;
                font-family: serif;
                letter-spacing: 1px;
                opacity: 0.9;
            }
        </style>
        
        <div class="login-container">
            <div style="font-size: 40px; margin-bottom: 10px;">🔴⚫ 🏊 ⚫🔴</div>
            <div class="nob-title">NEWELL'S OLD BOYS</div>
            <div class="nob-quote">"Del deporte sos la gloria"</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='text-align:center; color:#aaa; font-size:14px; margin-bottom:5px;'>ACCESO SOCIOS</div>", unsafe_allow_html=True)
    st.text_input("Ingrese Nro de Socio", key="input_socio", placeholder="Ej: 123456-01", label_visibility="collapsed")
    if st.button("INGRESAR", type="primary", use_container_width=True):
        validar_socio()

# --- 6. DEFINICIÓN DE PÁGINAS ---
pg_inicio = st.Page("pages/1_inicio.py", title="Inicio", icon="🏠")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Base de Datos", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga de Datos", icon="⚙️")
pg_login_obj = st.Page(login_screen, title="Acceso", icon="🔒")

# --- 7. RUTEO Y NAVEGACIÓN ---

if not st.session_state.role:
    pg = st.navigation([pg_login_obj])
    pg.run()

else:
    # --- TRUCO CSS PARA SUBIR INFO DE USUARIO ARRIBA DEL MENÚ ---
    st.markdown("""
        <style>
            /* Esto empuja el menú de navegación hacia abajo (orden 2) */
            [data-testid="stSidebarNav"] {
                order: 2;
            }
            /* Esto asegura que el contenido personalizado suba (orden 1 implícito o forzado) */
            [data-testid="stSidebarUserContent"] {
                display: flex;
                flex-direction: column;
            }
            .user-header {
                padding: 15px 5px;
                margin-bottom: 10px;
                border-bottom: 1px solid #444;
                text-align: center;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
        </style>
    """, unsafe_allow_html=True)

    # DEFINICIÓN DEL MENÚ
    menu_pages = {"Principal": [pg_inicio, pg_datos]}
    
    if st.session_state.role in ["M", "P"]:
        menu_pages["Herramientas"] = [pg_ranking, pg_simulador]
        if st.session_state.admin_unlocked:
            menu_pages["Administración"] = [pg_carga]
            
    pg = st.navigation(menu_pages)
    
    # --- CONTENIDO SIDEBAR (Ahora aparecerá ARRIBA gracias al CSS) ---
    with st.sidebar:
        # Bloque de usuario
        st.markdown(f"""
        <div class="user-header">
            <div style="font-size: 28px;">🔴⚫</div>
            <div style="font-weight: bold; font-size: 16px; color: white; margin-top: 5px;">
                Hola, {st.session_state.user_name.split()[0]}
            </div>
            <div style="color: #aaa; font-size: 12px; text-transform: uppercase;">
                {st.session_state.role}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # El botón de cerrar sesión lo ponemos aquí también, o al final
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            cerrar_sesion()
            
    pg.run()
