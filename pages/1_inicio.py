import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inicio", layout="centered")

# --- INICIALIZACIÓN SEGURA DE VARIABLES ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

if "show_login_form" not in st.session_state: 
    st.session_state.show_login_form = False

if "admin_unlocked" not in st.session_state: 
    st.session_state.admin_unlocked = False

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_data():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias")
        }
    except: return None

db = cargar_data()

# --- FUNCIONES AUXILIARES ---
def calcular_cat_exacta(edad, df_cat):
    try:
        for _, r in df_cat.iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "S/C"
    except: return "-"

# =======================================================
#  DISEÑO DEL TÍTULO (CAJA TIPO BANNER)
# =======================================================
st.markdown("""
<style>
    .banner-container {
        background-color: #262730; /* Fondo oscuro fijo */
        padding: 40px 20px;
        border-radius: 15px;
        border: 1px solid #444;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        margin-bottom: 30px;
    }
    .banner-title {
        color: white !important;
        font-size: 36px;
        font-weight: 800;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .banner-subtitle {
        color: #4CAF50 !important;
        font-size: 18px;
        font-weight: 600;
        margin-top: 10px;
    }
    /* Ajuste para botones */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        height: 50px;
    }
</style>

<div class="banner-container">
    <div class="banner-title">BIENVENIDOS AL COMPLEJO ACUÁTICO</div>
    <div class="banner-subtitle">Sistema de Gestión Deportiva • NOB</div>
</div>
""", unsafe_allow_html=True)

# =======================================================
#  CONTENIDO PRINCIPAL (MENU)
# =======================================================

# Métricas rápidas si hay datos
if db:
    total_nad = len(db['nadadores'])
    total_reg = len(db['tiempos'])
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("🏊‍♂️ Nadadores", total_nad)
    col_m2.metric("⏱️ Registros", total_reg)
    
    # Calcular próxima competencia o dato relevante (Simulado)
    col_m3.metric("📅 Temporada", datetime.now().year)

st.divider()

# --- BOTONES DE NAVEGACIÓN ---
c1, c2 = st.columns(2)

with c1: 
    if st.button("📊 Ver Base de Datos", type="primary", use_container_width=True, key="btn_bd_home"): 
        st.session_state.ver_nadador_especifico = None
        st.switch_page("pages/2_visualizar_datos.py")
with c2: 
    if st.button("🏆 Ver Ranking", use_container_width=True, key="btn_rk_home"): st.switch_page("pages/4_ranking.py")

st.write("")
if st.button("⏱️ Simulador de Postas", type="secondary", use_container_width=True, key="btn_sim_home"): st.switch_page("pages/3_simulador.py")

# --- ÁREA DE PROFESORES (CANDADO) ---
st.write(""); st.write("")
st.markdown("---")

col_space, col_lock = st.columns([8, 1])
with col_lock:
    if not st.session_state.admin_unlocked:
        if st.button("🔒", help="Acceso Profesores", type="tertiary", key="btn_lock_open"):
            st.session_state.show_login_form = not st.session_state.show_login_form
    else:
        if st.button("🔓", help="Cerrar Sesión Profe", key="btn_lock_close", type="primary"):
            st.session_state.admin_unlocked = False
            st.rerun()

if st.session_state.show_login_form and not st.session_state.admin_unlocked:
    with st.container(border=True):
        st.markdown("##### 🛡️ Acceso Profesor")
        p_pass = st.text_input("Contraseña:", type="password", key="login_pass_home")
        
        if st.button("Ingresar", use_container_width=True):
            if p_pass == "admin123": # O la contraseña que uses
                st.session_state.admin_unlocked = True
                st.session_state.show_login_form = False
                st.success("¡Acceso concedido!")
                st.switch_page("pages/1_cargar_datos.py")
            else:
                st.error("Contraseña incorrecta")
elif st.session_state.admin_unlocked:
    if st.button("⚙️ IR AL PANEL DE CARGA", type="primary", use_container_width=True):
        st.switch_page("pages/1_cargar_datos.py")
