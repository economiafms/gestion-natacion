import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Acceso NOB", layout="centered", initial_sidebar_state="collapsed")

# --- 2. ESTADO DE SESIÓN ---
if "role" not in st.session_state: st.session_state.role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nro_socio" not in st.session_state: st.session_state.nro_socio = None
if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False 
if "show_login_form" not in st.session_state: st.session_state.show_login_form = False 
# Variable "Puente" para llevar el nombre a la otra página
if "ver_nadador_especifico" not in st.session_state: st.session_state.ver_nadador_especifico = None

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_data():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "users": conn.read(worksheet="User"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias")
        }
    except: return None

db = cargar_data()

# --- 4. FUNCIONES AUXILIARES ---
def limpiar_socio(valor):
    if pd.isna(valor): return ""
    return str(valor).split('.')[0].strip()

def calcular_categoria(anio_nac):
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
    elif 75 <= edad <= 79: return "K"
    else: return "L+"

def calcular_cat_exacta(edad, df_cat):
    try:
        for _, r in df_cat.iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

# --- 5. LOGICA LOGIN ---
def validar_socio():
    raw_input = st.session_state.input_socio
    socio_limpio = raw_input.split("-")[0].strip()
    
    if not socio_limpio:
        st.warning("Ingrese un número.")
        return

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
            else: st.error("Sin datos de nadador.")
        else: st.error("Socio no registrado.")

def cerrar_sesion():
    st.session_state.role = None
    st.session_state.admin_unlocked = False
    st.session_state.ver_nadador_especifico = None
    st.rerun()

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
    else: st.error("Credenciales incorrectas")

# --- 6. RENDERIZADO VISUAL ---
def render_personal_card(user_id, db):
    df_nad = db['nadadores']
    me_rows = df_nad[df_nad['codnadador'] == user_id]
    if me_rows.empty: return
    me = me_rows.iloc[0]
    
    try: edad = datetime.now().year - pd.to_datetime(me['fechanac']).year
    except: edad = 0
    cat = calcular_cat_exacta(edad, db['categorias'])
    
    # CORRECCIÓN DECIMALES: .fillna(0).astype(int)
    df_t = db['tiempos'].copy(); df_r = db['relevos'].copy()
    df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0).astype(int)
    df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0).astype(int)
    
    mi_oro = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==1)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==1)])
    mi_plata = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==2)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==2)])
    mi_bronce = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==3)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==3)])
    mi_total = mi_oro + mi_plata + mi_bronce

    st.write("### 👤 Tu Perfil")
    st.markdown(f"""
    <style>
        .padron-card {{ background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }}
        .padron-card:hover {{ border-color: #E30613; transform: scale(1.02); }}
        .p-total {{ font-size: 26px; color: #FFD700; font-weight: bold; }}
    </style>
    <div class="padron-card">
        <div style="flex: 2; border-right: 1px solid #555;">
            <div style="font-weight: bold; font-size: 18px; color: white;">{me['nombre']} {me['apellido']}</div>
            <div style="font-size: 13px; color: #ccc;">{edad} años • {me['codgenero']}</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <div style="display: flex; justify-content: center; gap: 8px; font-size: 16px;">
                <span>🥇{mi_oro}</span> <span>🥈{mi_plata}</span> <span>🥉{mi_bronce}</span>
            </div>
        </div>
        <div style="flex: 1; text-align: right; border-left: 1px solid #555; padding-left: 10px;">
            <div class="p-total">★ {mi_total}</div>
            <div style="font-size: 16px; color: #4CAF50; font-weight: bold;">{cat}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Ver Mi Ficha Completa ➝", key="btn_ficha_main", type="primary", use_container_width=True):
        st.session_state.ver_nadador_especifico = st.session_state.user_name
        st.switch_page("pages/2_visualizar_datos.py")
    
    st.divider()

# --- 7. DASHBOARDS ---
def dashboard_common_structure():
    st.markdown("""<div style='text-align: center; margin-bottom: 20px;'><h3 style='color: white; font-size: 20px; margin: 0;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3><h1 style='color: #E30613; font-size: 32px; margin: 0; font-weight: 800;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1></div>""", unsafe_allow_html=True)
    st.divider()
    if db:
        if st.session_state.user_id: render_personal_card(st.session_state.user_id, db)
        
        # CORRECCIÓN DECIMALES EN CLUB STATS
        df_t = db['tiempos'].copy(); df_r = db['relevos'].copy()
        df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0).astype(int)
        df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0).astype(int)
        
        t_oro = len(df_t[df_t['posicion']==1]) + len(df_r[df_r['posicion']==1])
        t_plata = len(df_t[df_t['posicion']==2]) + len(df_r[df_r['posicion']==2])
        t_bronce = len(df_t[df_t['posicion']==3]) + len(df_r[df_r['posicion']==3])
        total_med = t_oro + t_plata + t_bronce

        st.markdown("<h5 style='text-align: center; color: #888;'>ESTADÍSTICAS DEL CLUB</h5>", unsafe_allow_html=True)
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
        
        # Gráficos
        df_n = db['nadadores'].copy()
        df_n['Anio'] = pd.to_datetime(df_n['fechanac']).dt.year
        df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria)
        t_g, t_c = st.tabs(["Género", "Categorías"])
        colors = alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#FF69B4'])
        with t_g:
            base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=80, innerRadius=50).encode(color=alt.Color("codgenero", scale=colors, legend=None))
            text = base.mark_text(radius=100).encode(text="count()", order=alt.Order("codgenero"), color=alt.value("white"))
            st.altair_chart(pie + text, use_container_width=True)
        with t_c:
            orden = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L+"]
            chart = alt.Chart(df_n).mark_bar(cornerRadius=3).encode(x=alt.X('Categoria', sort=orden), y='count()', color=alt.Color('codgenero', legend=None, scale=colors)).properties(height=200)
            st.altair_chart(chart, use_container_width=True)

# --- 8. RUTEO ---
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Base de Datos", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga", icon="⚙️")

def page_dashboard_m():
    dashboard_common_structure()
    st.divider()
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("🗃️ Base de Datos", use_container_width=True): 
            st.session_state.ver_nadador_especifico = None 
            st.switch_page("pages/2_visualizar_datos.py")
    with c2: 
        if st.button("🏆 Ranking", use_container_width=True): st.switch_page("pages/4_ranking.py")
    st.write("")
    if st.button("⏱️ Simulador de Postas", type="primary", use_container_width=True): st.switch_page("pages/3_simulador.py")
    
    st.write(""); st.write("")
    col_space, col_lock = st.columns([8, 1])
    with col_lock:
        if not st.session_state.admin_unlocked:
            if st.button("🔒", type="tertiary"): st.session_state.show_login_form = not st.session_state.show_login_form
    
    if st.session_state.show_login_form and not st.session_state.admin_unlocked:
        with st.form("admin"):
            st.text_input("Usuario", key="u_in")
            st.text_input("Contraseña", type="password", key="p_in")
            st.form_submit_button("Entrar", on_click=intentar_desbloqueo)
    
    if st.session_state.admin_unlocked: st.success("🔓 Admin OK")
    st.divider()
    if st.button("Cerrar Sesión"): cerrar_sesion()

def page_dashboard_n():
    dashboard_common_structure()
    st.divider()
    if st.button("Cerrar Sesión", type="secondary"): cerrar_sesion()

pg_dash_m = st.Page(page_dashboard_m, title="Inicio", icon="🏠")
pg_dash_n = st.Page(page_dashboard_n, title="Mi Perfil", icon="🏊")

if not st.session_state.role:
    st.markdown("""
        <div style="text-align: center; padding: 30px; border-radius: 20px; background: linear-gradient(180deg, #121212 0%, #000000 100%); border: 2px solid #333; margin-bottom: 20px;">
            <div style="font-size: 40px; margin-bottom: 10px;">🔴⚫ 🏊 ⚫🔴</div>
            <div style="font-size: 38px; font-weight: 900; color: #E30613;">NEWELL'S OLD BOYS</div>
            <div style="font-size: 18px; font-style: italic; color: #fff;">"Del deporte sos la gloria"</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#aaa;'>ACCESO SOCIOS</div>", unsafe_allow_html=True)
    st.text_input("Nº Socio", key="input_socio", placeholder="Ej: 123456-01")
    if st.button("INGRESAR", type="primary", use_container_width=True): validar_socio()

elif st.session_state.role == "M":
    pages = [pg_dash_m, pg_datos, pg_ranking, pg_simulador]
    if st.session_state.admin_unlocked: pages.append(pg_carga)
    pg = st.navigation(pages)
    pg.run()

elif st.session_state.role == "N":
    pg = st.navigation([pg_dash_n, pg_datos])
    pg.run()
