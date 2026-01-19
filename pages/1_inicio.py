import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inicio", layout="centered")

# --- INICIALIZACIÓN SEGURA DE VARIABLES (FIX ERROR) ---
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
        st.rerun()
    else: 
        st.error("Credenciales incorrectas")

# --- VISUALIZACIÓN ---

st.markdown("""
    <div style='text-align: center; margin-bottom: 25px;'>
        <h3 style='color: white; font-size: 20px; margin: 0;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
        <h1 style='color: #E30613; font-size: 32px; margin: 0; font-weight: 800;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
    </div>
""", unsafe_allow_html=True)
st.divider()

if db and st.session_state.user_id:
    # 1. TARJETA PERSONAL
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
        .padron-card {{ background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }}
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
    
    if st.button("Ver Mi Ficha Completa ➝", type="primary", use_container_width=True, key="btn_ficha_inicio"):
        st.session_state.ver_nadador_especifico = st.session_state.user_name
        st.switch_page("pages/2_visualizar_datos.py")
    
    st.divider()

    # 2. ESTADÍSTICAS GLOBALES
    st.markdown("<h5 style='text-align: center; color: #888;'>ESTADÍSTICAS DEL CLUB</h5>", unsafe_allow_html=True)
    
    t_oro = len(df_t[df_t['posicion']==1]) + len(df_r[df_r['posicion']==1])
    t_plata = len(df_t[df_t['posicion']==2]) + len(df_r[df_r['posicion']==2])
    t_bronce = len(df_t[df_t['posicion']==3]) + len(df_r[df_r['posicion']==3])
    total_med = t_oro + t_plata + t_bronce

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; gap: 10px; margin-bottom: 10px;">
        <div style="background-color: #262730; padding: 15px; border-radius: 10px; width: 48%; text-align: center; border: 1px solid #444;">
            <div style="font-size: 32px; font-weight: bold; color: white;">{len(db['nadadores'])}</div><div style="font-size: 13px; color: #ccc;">NADADORES</div>
        </div>
        <div style="background-color: #262730; padding: 15px; border-radius: 10px; width: 48%; text-align: center; border: 1px solid #444;">
            <div style="font-size: 32px; font-weight: bold; color: white;">{len(df_t)+len(df_r)}</div><div style="font-size: 13px; color: #ccc;">REGISTROS</div>
        </div>
    </div>
    <div style="background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; padding: 12px; margin-bottom: 25px;">
        <div style="text-align:center; font-size:11px; color:#aaa; margin-bottom:8px; font-weight:bold;">MEDALLERO HISTÓRICO</div>
        <div style="display: flex; justify-content: space-between; gap: 2px;">
            <div style="flex:1; text-align:center;"><div style="font-size:22px; color:#FFD700;">🥇 {t_oro}</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#C0C0C0;">🥈 {t_plata}</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#CD7F32;">🥉 {t_bronce}</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#fff;">★ {total_med}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. GRÁFICOS
    df_n = db['nadadores'].copy()
    df_n['Anio'] = pd.to_datetime(df_n['fechanac'], errors='coerce').dt.year
    df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria_grafico)
    
    t_g, t_c = st.tabs(["Género", "Categorías Master"])
    colors = alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#FF69B4'])
    
    with t_g:
        base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
        pie = base.mark_arc(outerRadius=80, innerRadius=50).encode(color=alt.Color("codgenero", scale=colors, legend=None))
        text = base.mark_text(radius=100).encode(text="count()", order=alt.Order("codgenero"), color=alt.value("white"))
        st.altair_chart(pie + text, use_container_width=True)
    with t_c:
        orden = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K+"]
        chart = alt.Chart(df_n).mark_bar(cornerRadius=3).encode(
            x=alt.X('Categoria', sort=orden, title=None), 
            y=alt.Y('count()', title=None), 
            color=alt.Color('codgenero', legend=None, scale=colors)
        ).properties(height=200)
        st.altair_chart(chart, use_container_width=True)

# --- 4. ZONA DE HERRAMIENTAS Y CANDADO (Solo Rol M o P) ---
if st.session_state.role in ["M", "P"]:
    st.divider()
    
    # Botones de navegación extra en el cuerpo (Opcional, si te gustaban)
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("🗃️ Base de Datos", use_container_width=True, key="btn_bd_home"): 
            st.session_state.ver_nadador_especifico = None
            st.switch_page("pages/2_visualizar_datos.py")
    with c2: 
        if st.button("🏆 Ver Ranking", use_container_width=True, key="btn_rk_home"): st.switch_page("pages/4_ranking.py")
    
    st.write("")
    if st.button("⏱️ Simulador de Postas", type="primary", use_container_width=True, key="btn_sim_home"): st.switch_page("pages/3_simulador.py")

    # --- CANDADO DEL PROFE ---
    st.write(""); st.write("")
    col_space, col_lock = st.columns([8, 1])
    with col_lock:
        if not st.session_state.admin_unlocked:
            if st.button("🔒", help="Desbloquear Admin", type="tertiary", key="btn_lock_open"):
                st.session_state.show_login_form = not st.session_state.show_login_form
        else:
            if st.button("🔓", help="Bloquear Admin", key="btn_lock_close"):
                st.session_state.admin_unlocked = False
                st.rerun()

    if st.session_state.show_login_form and not st.session_state.admin_unlocked:
        with st.form("admin_login_form"):
            st.write("**Acceso Profesor**")
            st.text_input("Usuario", key="u_in")
            st.text_input("Contraseña", type="password", key="p_in")
            st.form_submit_button("Desbloquear", on_click=intentar_desbloqueo)
    
    if st.session_state.admin_unlocked:
        st.success("🔓 Gestión Habilitada: Ver menú lateral")
