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

# --- 4. FUNCIONES DE VALIDACIÓN ---
def verificar_pin_admin():
    pin_ingresado = st.session_state.input_pin
    if pin_ingresado == "1903":  
        st.session_state.admin_unlocked = True
        st.session_state.show_login_form = True 
        st.success("✅ Acceso desbloqueado.")
    else:
        st.error("❌ PIN Incorrecto")

def validar_socio():
    db = cargar_tablas_login()
    if not db:
        st.error("Error de conexión.")
        return

    nro_input = st.session_state.input_socio.strip()
    
    df_user = db['users']
    user_match = df_user[df_user['nrosocio'].astype(str) == nro_input]

    if not user_match.empty:
        perfil = user_match.iloc[0]['perfil']
        
        if perfil in ["M", "P"] and not st.session_state.admin_unlocked:
            st.error("⚠️ Requiere validación de PIN.")
            return

        df_nad = db['nadadores']
        nad_data = df_nad[df_nad['nrosocio'].astype(str) == nro_input]
        
        nombre = "Usuario"
        uid = nro_input
        
        if not nad_data.empty:
            nombre = f"{nad_data.iloc[0]['nombre']} {nad_data.iloc[0]['apellido']}"
            uid = nad_data.iloc[0]['codnadador']
        
        st.session_state.role = perfil
        st.session_state.user_name = nombre
        st.session_state.user_id = uid
        st.session_state.nro_socio = nro_input
        
        st.success(f"¡Bienvenido, {nombre}!")
        time.sleep(1)
        st.rerun()
    else:
        st.error("❌ Número de socio no encontrado.")

# --- 5. INTERFAZ DE LOGIN ---
def login_screen():
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/46/Newell%27s_Old_Boys_shield.svg", width=100)
    st.markdown("<h1 style='text-align: center; color: #E30613;'>BIENVENIDO LEPROSO</h1>", unsafe_allow_html=True)
    st.markdown("---")

    if not st.session_state.show_login_form:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("SOY NADADOR 🏊", use_container_width=True):
                st.session_state.show_login_form = True
                st.rerun()
        with col2:
            if st.button("SOY PROFE ⏱️", use_container_width=True):
                st.session_state.show_login_form = "PIN_REQ"
                st.rerun()

    if st.session_state.show_login_form == "PIN_REQ" and not st.session_state.admin_unlocked:
        st.info("🔒 Área restringida")
        st.text_input("PIN", type="password", key="input_pin", on_change=verificar_pin_admin)
        if st.button("Volver"):
            st.session_state.show_login_form = False
            st.rerun()
        return 

    st.markdown("##### 🆔 Ingrese su Número de Socio")
    st.markdown("<span style='font-size:12px; color:gray'>Lo encontrarás en tu carnet digital</span>", unsafe_allow_html=True)
    st.text_input("Ingrese Nro de Socio", key="input_socio", placeholder="Ej: 123456-01", label_visibility="collapsed")
    
    if st.button("INGRESAR", type="primary", use_container_width=True):
        validar_socio()

# --- 6. DEFINICIÓN DE PÁGINAS ---
pg_inicio = st.Page("pages/1_inicio.py", title="Inicio", icon="🏠")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Fichero", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_entrenamientos = st.Page("pages/5_entrenamientos.py", title="Entrenamientos", icon="🏋️")
pg_categoria = st.Page("pages/6_mi_categoria.py", title="Mi Categoría", icon="🏅")
# --- NUEVA PÁGINA AGENDA ---
pg_agenda = st.Page("pages/7_agenda.py", title="Agenda", icon="📅")
# ---------------------------
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga de Datos", icon="⚙️")
pg_login_obj = st.Page(login_screen, title="Acceso", icon="🔒")

# --- 7. RUTEO Y MENÚ ---
if not st.session_state.role:
    pg = st.navigation([pg_login_obj])
    pg.run()
else:
    # --- MENÚ PRINCIPAL ---
    # Se agrega pg_agenda a la lista principal
    menu_pages = {
        "Principal": [pg_inicio, pg_agenda, pg_datos, pg_entrenamientos, pg_categoria]
    }
    
    # --- MENÚ HERRAMIENTAS ---
    if st.session_state.role in ["M", "P"]:
        menu_pages["Herramientas"] = [pg_carga, pg_ranking, pg_simulador]
    
    pg = st.navigation(menu_pages)
    pg.run()
