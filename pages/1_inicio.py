import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Inicio", layout="centered", initial_sidebar_state="collapsed")

# --- 2. CSS PARA OCULTAR EL MENÚ LATERAL NATIVO (EL TRUCO) ---
st.markdown("""
<style>
    /* Ocultar la navegación de Streamlit */
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Estilos de las tarjetas del menú */
    .menu-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
        cursor: pointer;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .menu-card:hover {
        border-color: #E30613;
        transform: scale(1.02);
        background-color: #30303A;
    }
    .menu-icon { font-size: 40px; margin-bottom: 10px; }
    .menu-title { font-weight: bold; color: white; font-size: 18px; }
    .menu-desc { color: #aaa; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SEGURIDAD (Gatekeeper) ---
if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Debes iniciar sesión primero.")
    if st.button("Ir al Login"):
        st.switch_page("index.py")
    st.stop()

# --- 4. CONEXIÓN Y DATOS ---
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

# --- 5. FUNCIONES AUXILIARES ---
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

def cerrar_sesion():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.switch_page("index.py")

def intentar_desbloqueo():
    try:
        sec_user = st.secrets["admin"]["usuario"]
        sec_pass = st.secrets["admin"]["password"]
    except:
        sec_user = "entrenador"; sec_pass = "nob1903"

    if st.session_state.u_in == sec_user and st.session_state.p_in == sec_pass: 
        st.session_state.admin_unlocked = True
        st.session_state.show_login_form = False
        st.rerun()
    else: 
        st.error("Credenciales incorrectas")

# --- 6. RENDERIZADO VISUAL ---

# 6.1 HEADER
st.markdown("""
    <div style='text-align: center; margin-bottom: 25px;'>
        <h3 style='color: white; font-size: 20px; margin: 0;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
        <h1 style='color: #E30613; font-size: 32px; margin: 0; font-weight: 800;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
    </div>
""", unsafe_allow_html=True)

# 6.2 TARJETA PERSONAL (Común a ambos)
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

    st.markdown(f"""
    <div style="background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 25px;">
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
            <div style="font-size: 26px; color: #FFD700; font-weight: bold;">★ {mi_total}</div>
            <div style="font-size: 16px; color: #4CAF50; font-weight: bold;">{cat}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 6.3 MENÚ DE NAVEGACIÓN (Botones grandes)
st.write("### 🧭 Menú Principal")

if st.session_state.role == "N":
    # --- MENÚ NADADOR (SIMPLE) ---
    if st.button("👤 Ver Mi Ficha Completa", type="primary", use_container_width=True):
        st.session_state.ver_nadador_especifico = st.session_state.user_name
        st.switch_page("pages/2_visualizar_datos.py")
        
    st.info("ℹ️ Para ver tu historial detallado y buscar compañeros, ingresa a tu ficha.")

elif st.session_state.role == "M":
    # --- MENÚ MASTER (GRID COMPLETO) ---
    col1, col2 = st.columns(2)
    
    with col1:
        # Usamos botones nativos con un poco de hack CSS visual arriba
        if st.button("🗃️ Base de Datos", use_container_width=True, help="Fichas, Padrón y Tiempos"):
            st.session_state.ver_nadador_especifico = None # Entrar limpio
            st.switch_page("pages/2_visualizar_datos.py")
            
        st.write("")
        if st.button("⏱️ Simulador", use_container_width=True, help="Armado de postas"):
            st.switch_page("pages/3_simulador.py")

    with col2:
        if st.button("🏆 Ranking", use_container_width=True, help="Mejores tiempos del club"):
            st.switch_page("pages/4_ranking.py")
            
        st.write("")
        # BOTÓN CARGA (Solo aparece si está desbloqueado)
        if st.session_state.get("admin_unlocked", False):
            if st.button("⚙️ Cargar Datos", type="primary", use_container_width=True):
                st.switch_page("pages/1_cargar_datos.py")
        else:
            st.button("🔒 Cargar Datos (Bloqueado)", disabled=True, use_container_width=True)

    # --- ZONA CANDADO ---
    st.write(""); st.write("")
    c_pad, c_form = st.columns([1, 5])
    with c_pad:
        if not st.session_state.get("admin_unlocked", False):
            if st.button("🔒", help="Desbloquear Admin"):
                st.session_state.show_login_form = not st.session_state.get("show_login_form", False)
        else:
            if st.button("🔓", help="Bloquear Admin"):
                st.session_state.admin_unlocked = False
                st.rerun()

    if st.session_state.get("show_login_form") and not st.session_state.get("admin_unlocked"):
        with st.form("admin_login"):
            st.write("**Acceso Profesor**")
            st.text_input("Usuario", key="u_in")
            st.text_input("Contraseña", type="password", key="p_in")
            st.form_submit_button("Desbloquear", on_click=intentar_desbloqueo)

# 6.4 ESTADÍSTICAS GLOBALES (AL FINAL)
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
            st.caption("Distribución por Género")
            
        with c2:
            st.metric("Registros", len(db['tiempos']) + len(db['relevos']))
            chart = alt.Chart(df_n).mark_bar().encode(
                x=alt.X('Categoria', sort=["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K+"]), 
                y='count()', color='codgenero'
            ).properties(height=150)
            st.altair_chart(chart, use_container_width=True)
            st.caption("Distribución por Categoría")

st.write("")
if st.button("Cerrar Sesión", type="secondary"):
    cerrar_sesion()
