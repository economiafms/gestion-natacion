import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Acceso NOB", layout="centered", initial_sidebar_state="collapsed")

# --- 2. ESTADO DE SESIÓN ---
if "role" not in st.session_state: st.session_state.role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nro_socio" not in st.session_state: st.session_state.nro_socio = None

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_auth():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "users": conn.read(worksheet="User"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias") 
        }
    except: return None

db = cargar_auth()

# --- 4. FUNCIONES AUXILIARES ---
def calcular_categoria(edad, df_cat):
    try:
        for _, r in df_cat.iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

# Función para limpiar el Nro de Socio (Quitar decimales .0 y espacios)
def limpiar_socio(valor):
    if pd.isna(valor): return ""
    # Convertir a string, quitar decimales si es float (ej: 123.0 -> 123) y espacios
    return str(valor).split('.')[0].strip()

# --- 5. LÓGICA DE LOGIN ---
def validar_socio():
    raw_input = st.session_state.input_socio
    # Tomamos lo que está antes del guion
    socio_input_limpio = raw_input.split("-")[0].strip()
    
    if not socio_input_limpio:
        st.warning("Ingrese un número.")
        return

    if db:
        df_u = db['users']
        df_n = db['nadadores']
        
        # --- CORRECCIÓN CRÍTICA: Estandarizar columnas a texto plano ---
        # Aplicamos la limpieza a toda la columna para que coincida con el input
        df_u['nrosocio_str'] = df_u['nrosocio'].apply(limpiar_socio)
        df_n['nrosocio_str'] = df_n['nrosocio'].apply(limpiar_socio)
        
        # Buscar en tabla User usando la nueva columna limpia
        usuario = df_u[df_u['nrosocio_str'] == socio_input_limpio]
        
        if not usuario.empty:
            perfil = usuario.iloc[0]['perfil'].upper()
            
            # Buscar en Nadadores también con la columna limpia
            datos = df_n[df_n['nrosocio_str'] == socio_input_limpio]
            
            if not datos.empty:
                st.session_state.role = perfil
                st.session_state.user_name = f"{datos.iloc[0]['nombre']} {datos.iloc[0]['apellido']}"
                st.session_state.user_id = datos.iloc[0]['codnadador']
                st.session_state.nro_socio = socio_input_limpio
                
                st.success(f"¡Bienvenido {datos.iloc[0]['nombre']}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Perfil activo en User, pero no encontramos tus datos en la hoja Nadadores.")
        else:
            st.error("Número de socio no registrado en el sistema.")

def cerrar_sesion():
    st.session_state.role = None
    st.session_state.user_name = None
    st.rerun()

# --- ESTILOS CSS ---
st.markdown("""
<style>
    /* Tarjeta tipo Padrón */
    .padron-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        margin-top: 10px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    .padron-card:hover {
        border-color: #E30613;
        transform: scale(1.01);
    }
    .p-col-left { flex: 2; text-align: left; border-right: 1px solid #555; padding-right: 10px; }
    .p-col-center { flex: 2; text-align: center; padding: 0 10px; }
    .p-col-right { flex: 1; text-align: right; padding-left: 10px; border-left: 1px solid #555; }
    
    .p-name { font-weight: bold; font-size: 18px; color: white; margin-bottom: 5px; }
    .p-meta { font-size: 13px; color: #ccc; }
    .p-medals { font-size: 16px; display: flex; justify-content: center; gap: 8px; margin-top: 5px;}
    .p-total { font-size: 26px; color: #FFD700; font-weight: bold; line-height: 1; }
    .p-cat { font-size: 18px; color: #4CAF50; font-weight: bold; margin-top: 5px; }
    
    /* KPI Boxes del Club */
    .kpi-box { background-color: #262730; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #444; width: 48%; }
    .medallero-box { background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; padding: 12px; margin-bottom: 25px; }
</style>
""", unsafe_allow_html=True)


# --- 6. DASHBOARD "M" (MASTER / GENERAL) ---
def dashboard_m():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 25px;'>
            <h3 style='color: white; font-size: 22px; margin: 0; font-weight: normal; letter-spacing: 1px;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
            <h1 style='color: #E30613; font-size: 36px; margin-top: 5px; padding: 0; font-weight: 800; text-transform: uppercase; text-shadow: 2px 2px 4px #000000;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    if db:
        df_nad = db['nadadores']
        df_t = db['tiempos'].copy()
        df_r = db['relevos'].copy()
        
        # Cálculos Globales
        df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0)
        df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0)
        
        t_oro = len(df_t[df_t['posicion']==1]) + len(df_r[df_r['posicion']==1])
        t_plata = len(df_t[df_t['posicion']==2]) + len(df_r[df_r['posicion']==2])
        t_bronce = len(df_t[df_t['posicion']==3]) + len(df_r[df_r['posicion']==3])
        total_med = t_oro + t_plata + t_bronce
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; gap: 10px; margin-bottom: 10px;">
            <div class="kpi-box"><div style="font-size: 32px; font-weight: bold; color: white;">{len(df_nad)}</div><div style="font-size: 13px; color: #ccc;">🏊‍♂️ Nadadores</div></div>
            <div class="kpi-box"><div style="font-size: 32px; font-weight: bold; color: white;">{len(df_t)+len(df_r)}</div><div style="font-size: 13px; color: #ccc;">⏱️ Registros</div></div>
        </div>
        <div class="medallero-box">
            <div style="text-align:center; font-size:11px; color:#aaa; margin-bottom:8px; font-weight:bold;">MEDALLERO HISTÓRICO</div>
            <div style="display: flex; justify-content: space-between; gap: 2px;">
                <div style="flex:1; text-align:center;"><div style="font-size:22px; color:#FFD700;">🥇 {t_oro}</div></div>
                <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#C0C0C0;">🥈 {t_plata}</div></div>
                <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#CD7F32;">🥉 {t_bronce}</div></div>
                <div style="flex:1; text-align:center; border-left:1px solid #333; background:rgba(255,255,255,0.05);"><div style="font-size:22px; color:#fff;">★ {total_med}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("🗃️ Base de Datos", use_container_width=True): st.switch_page("pages/2_visualizar_datos.py")
        with c2: 
            if st.button("🏆 Ver Ranking", use_container_width=True): st.switch_page("pages/4_ranking.py")
        st.write("")
        if st.button("⏱️ Simulador de Postas", type="primary", use_container_width=True): st.switch_page("pages/3_simulador.py")
        
        st.divider()
        if st.button("Cerrar Sesión"): cerrar_sesion()

# --- 7. DASHBOARD "N" (NADADOR - HÍBRIDO) ---
def dashboard_n():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 25px;'>
            <h3 style='color: white; font-size: 22px; margin: 0; font-weight: normal; letter-spacing: 1px;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
            <h1 style='color: #E30613; font-size: 36px; margin-top: 5px; padding: 0; font-weight: 800; text-transform: uppercase; text-shadow: 2px 2px 4px #000000;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    if db:
        df_nad_club = db['nadadores']
        df_t_club = db['tiempos']
        df_r_club = db['relevos']
        
        my_id = st.session_state.user_id
        
        # Datos Personales
        me = df_nad_club[df_nad_club['codnadador'] == my_id].iloc[0]
        try:
            edad = datetime.now().year - pd.to_datetime(me['fechanac']).year
        except: edad = 0
        cat = calcular_categoria(edad, db['categorias'])
        
        # Datos Medallas
        df_t_club['posicion'] = pd.to_numeric(df_t_club['posicion'], errors='coerce').fillna(0)
        df_r_club['posicion'] = pd.to_numeric(df_r_club['posicion'], errors='coerce').fillna(0)
        
        # Indiv
        mis_oros_i = len(df_t_club[(df_t_club['codnadador']==my_id) & (df_t_club['posicion']==1)])
        mis_platas_i = len(df_t_club[(df_t_club['codnadador']==my_id) & (df_t_club['posicion']==2)])
        mis_bronces_i = len(df_t_club[(df_t_club['codnadador']==my_id) & (df_t_club['posicion']==3)])
        
        # Relevos
        cond_rel = (df_r_club['nadador_1'] == my_id) | (df_r_club['nadador_2'] == my_id) | (df_r_club['nadador_3'] == my_id) | (df_r_club['nadador_4'] == my_id)
        mis_relevos = df_r_club[cond_rel]
        mis_oros_r = len(mis_relevos[mis_relevos['posicion']==1])
        mis_platas_r = len(mis_relevos[mis_relevos['posicion']==2])
        mis_bronces_r = len(mis_relevos[mis_relevos['posicion']==3])
        
        m_oro = mis_oros_i + mis_oros_r
        m_plata = mis_platas_i + mis_platas_r
        m_bronce = mis_bronces_i + mis_bronces_r
        m_total = m_oro + m_plata + m_bronce

        # Contexto Club
        cant_nad = len(df_nad_club)
        cant_reg = len(df_t_club) + len(df_r_club)
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; gap: 10px; margin-bottom: 20px;">
            <div class="kpi-box"><div style="font-size: 32px; font-weight: bold; color: white;">{cant_nad}</div><div style="font-size: 13px; color: #ccc;">🏊‍♂️ Nadadores</div></div>
            <div class="kpi-box"><div style="font-size: 32px; font-weight: bold; color: white;">{cant_reg}</div><div style="font-size: 13px; color: #ccc;">⏱️ Registros</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("### 👤 Tu Perfil")
        
        st.markdown(f"""
        <div class="padron-card">
            <div class="p-col-left">
                <div class="p-name">{me['nombre']} {me['apellido']}</div>
                <div class="p-meta">{edad} años (al 31/12) • {me['codgenero']}</div>
            </div>
            <div class="p-col-center">
                <div class="p-medals">
                    <span>🥇{m_oro}</span> <span>🥈{m_plata}</span> <span>🥉{m_bronce}</span>
                </div>
            </div>
            <div class="p-col-right">
                <div class="p-total">★ {m_total}</div>
                <div class="p-cat">{cat}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Ver Mi Ficha Completa ➝", type="primary", use_container_width=True):
            st.switch_page("pages/2_visualizar_datos.py")
        
        st.divider()
        if st.button("Cerrar Sesión", type="secondary"): cerrar_sesion()

# --- 8. RUTEO ---
pg_dash_m = st.Page(dashboard_m, title="Inicio", icon="🏠")
pg_dash_n = st.Page(dashboard_n, title="Mi Perfil", icon="🏊")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Base de Datos", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")

if not st.session_state.role:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/4e/Newell%27s_Old_Boys_shield.svg", width=100)
    st.title("Acceso Socios")
    st.text_input("Nº Socio", key="input_socio", placeholder="Ej: 123456-01")
    if st.button("Ingresar", type="primary", use_container_width=True): validar_socio()

elif st.session_state.role == "M":
    pg = st.navigation({"Principal": [pg_dash_m], "Herramientas": [pg_datos, pg_ranking, pg_simulador]})
    pg.run()

elif st.session_state.role == "N":
    pg = st.navigation([pg_dash_n, pg_datos])
    pg.run()
