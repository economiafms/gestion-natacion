import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inicio", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py") # Si entran directo por URL, los manda al login

# --- ESTADO LOCAL ---
if "show_login_form" not in st.session_state: st.session_state.show_login_form = False

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_data_dashboard():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias")
        }
    except: return None

db = cargar_data_dashboard()

# --- FUNCIONES AUXILIARES ---
def calcular_cat_exacta(edad, df_cat):
    try:
        for _, r in df_cat.iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

def calcular_categoria_grafico(anio_nac):
    anio_actual = datetime.now().year
    edad = anio_actual - anio_nac
    if edad < 20: return "Juvenil"
    elif 20 <= edad <= 24: return "PRE"
    elif 25 <= edad <= 29: return "A"
    elif 30 <= edad <= 34: return "B"
    elif 35 <= edad <= 39: return "C"
    elif 40 <= edad <= 44: return "D"
    elif 45 <= edad <= 49: return "E"
    elif 50 <= edad <= 54: return "F"
    elif 55 <= edad <= 59: return "G"
    elif 60 <= edad <= 64: return "H"
    elif 65 <= edad <= 69: return "I"
    elif 70 <= edad <= 74: return "J"
    else: return "K+"

def intentar_desbloqueo():
    try:
        sec_user = st.secrets["admin"]["usuario"]
        sec_pass = st.secrets["admin"]["password"]
    except:
        sec_user = "entrenador"; sec_pass = "nob1903"

    if st.session_state.u_in == sec_user and st.session_state.p_in == sec_pass: 
        st.session_state.admin_unlocked = True
        st.session_state.show_login_form = False
        st.rerun() # Al recargar, index.py detectará el unlock y agregará "Carga" al menú
    else: 
        st.error("Credenciales incorrectas")

# --- VISUALIZACIÓN ---

# Header
st.markdown("""
    <div style='text-align: center; margin-bottom: 25px;'>
        <h3 style='color: white; font-size: 20px; margin: 0;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
        <h1 style='color: #E30613; font-size: 32px; margin: 0; font-weight: 800;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
    </div>
""", unsafe_allow_html=True)

# Tarjeta Personal
if db and st.session_state.user_id:
    user_id = st.session_state.user_id
    me = db['nadadores'][db['nadadores']['codnadador'] == user_id].iloc[0]
    
    try: edad = datetime.now().year - pd.to_datetime(me['fechanac']).year
    except: edad = 0
    cat = calcular_cat_exacta(edad, db['categorias'])
    
    df_t = db['tiempos'].copy(); df_r = db['relevos'].copy()
    df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0).astype(int)
    df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0).astype(int)
    
    mis_oros = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==1)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==1)])
    mis_platas = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==2)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==2)])
    mis_bronces = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==3)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==3)])
    mi_total = mis_oros + mis_platas + mis_bronces

    st.write("### 👤 Tu Perfil")
    st.markdown(f"""
    <style>
        .padron-card {{ background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; transition: transform 0.2s; }}
        .padron-card:hover {{ border-color: #E30613; transform: scale(1.01); cursor: pointer; }}
        .p-total {{ font-size: 26px; color: #FFD700; font-weight: bold; }}
    </style>
    <div class="padron-card">
        <div style="flex: 2; border-right: 1px solid #555;">
            <div style="font-weight: bold; font-size: 18px; color: white;">{me['nombre']} {me['apellido']}</div>
            <div style="font-size: 13px; color: #ccc;">{edad} años • {me['codgenero']}</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <div style="display: flex; justify-content: center; gap: 8px; font-size: 16px;">
                <span>🥇{mis_oros}</span> <span>🥈{mis_platas}</span> <span>🥉{mis_bronces}</span>
            </div>
        </div>
        <div style="flex: 1; text-align: right; border-left: 1px solid #555; padding-left: 10px;">
            <div class="p-total">★ {mi_total}</div>
            <div style="font-size: 16px; color: #4CAF50; font-weight: bold;">{cat}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botón Ver Ficha (Redirige)
    if st.button("Ver Mi Ficha Completa ➝", type="primary", use_container_width=True):
        st.session_state.ver_nadador_especifico = st.session_state.user_name
        st.switch_page("pages/2_visualizar_datos.py")

# Estadísticas Generales
st.divider()
with st.expander("📊 Ver Estadísticas Globales del Club", expanded=False):
    if db:
        df_n = db['nadadores'].copy()
        df_n['Anio'] = pd.to_datetime(df_n['fechanac'], errors='coerce').dt.year
        df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria_grafico)
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Nadadores", len(df_n))
            base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=60).encode(color=alt.Color("codgenero", legend=None))
            st.altair_chart(pie, use_container_width=True)
            
        with c2:
            st.metric("Registros", len(db['tiempos']) + len(db['relevos']))
            chart = alt.Chart(df_n).mark_bar().encode(
                x=alt.X('Categoria', sort=["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K+"]), 
                y='count()', color='codgenero'
            ).properties(height=150)
            st.altair_chart(chart, use_container_width=True)

# Candado del Profesor (Solo si es M o P)
if st.session_state.role in ["M", "P"]:
    st.write(""); st.write("")
    col_space, col_lock = st.columns([8, 1])
    with col_lock:
        if not st.session_state.admin_unlocked:
            if st.button("🔒", help="Desbloquear Funciones Admin", type="tertiary"):
                st.session_state.show_login_form = not st.session_state.get("show_login_form", False)
        else:
            if st.button("🔓", help="Bloquear Funciones Admin"):
                st.session_state.admin_unlocked = False
                st.rerun()

    if st.session_state.get("show_login_form") and not st.session_state.get("admin_unlocked"):
        with st.form("admin_login"):
            st.write("**Acceso Profesor**")
            st.text_input("Usuario", key="u_in")
            st.text_input("Contraseña", type="password", key="p_in")
            st.form_submit_button("Desbloquear", on_click=intentar_desbloqueo)
    
    if st.session_state.admin_unlocked:
        st.success("✅ Modo Administración Activo: Se agregó 'Carga' al menú lateral.")
