import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Acceso NOB", layout="centered", initial_sidebar_state="collapsed")

# --- 2. GESTIÓN DE ESTADO (Inicialización) ---
if "role" not in st.session_state: st.session_state.role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nro_socio" not in st.session_state: st.session_state.nro_socio = None
if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False 
if "ver_nadador_especifico" not in st.session_state: st.session_state.ver_nadador_especifico = None

# Ocultar sidebar en el login
st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

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

# --- 4. LÓGICA ---
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
                # GUARDAR EN SESIÓN
                st.session_state.role = perfil
                st.session_state.user_name = f"{datos.iloc[0]['nombre']} {datos.iloc[0]['apellido']}"
                st.session_state.user_id = datos.iloc[0]['codnadador']
                st.session_state.nro_socio = socio_limpio
                
                st.success(f"¡Bienvenido {datos.iloc[0]['nombre']}!")
                time.sleep(0.5)
                # REDIRIGIR AL DASHBOARD
                st.switch_page("pages/1_inicio.py")
            else:
                st.error("Socio válido pero sin ficha de nadador activa.")
        else:
            st.error("Número de socio no registrado.")

# --- 5. INTERFAZ VISUAL ---
st.markdown("""
    <style>
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
