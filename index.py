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
if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False # Para el candado
if "show_password" not in st.session_state: st.session_state.show_password = False

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
    # Lógica simple para gráficos (puedes ajustar si tienes la tabla exacta)
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

# --- 5. LÓGICA LOGIN ---
def validar_socio():
    raw_input = st.session_state.input_socio
    socio_limpio = raw_input.split("-")[0].strip()
    
    if not socio_limpio:
        st.warning("Ingrese un número.")
        return

    if db:
        df_u = db['users']
        df_n = db['nadadores']
        
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
            else: st.error("Sin datos de nadador asociados.")
        else: st.error("Socio no registrado.")

def cerrar_sesion():
    st.session_state.role = None
    st.session_state.admin_unlocked = False
    st.rerun()

def intentar_desbloqueo():
    # Contraseña simple para el candado
    if st.session_state.pass_input == "nob1903": 
        st.session_state.admin_unlocked = True
        st.session_state.show_password = False
        st.rerun()
    else:
        st.error("Incorrecto")

# --- 6. COMPONENTE COMPARTIDO: EL INDEX VISUAL (GRÁFICOS + KPIs) ---
def render_index_visual(df_n, df_t, df_r):
    # 1. KPIs Numéricos
    df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0)
    df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0)
    
    t_oro = len(df_t[df_t['posicion']==1]) + len(df_r[df_r['posicion']==1])
    t_plata = len(df_t[df_t['posicion']==2]) + len(df_r[df_r['posicion']==2])
    t_bronce = len(df_t[df_t['posicion']==3]) + len(df_r[df_r['posicion']==3])
    total_med = t_oro + t_plata + t_bronce
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; gap: 10px; margin-bottom: 10px;">
        <div style="background-color: #262730; padding: 15px; border-radius: 10px; width: 48%; text-align: center; border: 1px solid #444; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            <div style="font-size: 32px; font-weight: bold; color: white;">{len(df_n)}</div>
            <div style="font-size: 13px; color: #ccc; text-transform: uppercase;">🏊‍♂️ Nadadores</div>
        </div>
        <div style="background-color: #262730; padding: 15px; border-radius: 10px; width: 48%; text-align: center; border: 1px solid #444; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            <div style="font-size: 32px; font-weight: bold; color: white;">{len(df_t)+len(df_r)}</div>
            <div style="font-size: 13px; color: #ccc; text-transform: uppercase;">⏱️ Registros</div>
        </div>
    </div>
    <div style="background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; padding: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <div style="text-align:center; font-size:11px; color:#aaa; margin-bottom:8px; letter-spacing:2px; font-weight:bold;">MEDALLERO HISTÓRICO (IND + RELEVOS)</div>
        <div style="display: flex; justify-content: space-between; gap: 2px;">
            <div style="flex:1; text-align:center;"><div style="font-size:22px; font-weight:bold; color:#FFD700;">🥇 {t_oro}</div><div style="font-size:10px; color:#888;">ORO</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; font-weight:bold; color:#C0C0C0;">🥈 {t_plata}</div><div style="font-size:10px; color:#888;">PLATA</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; font-weight:bold; color:#CD7F32;">🥉 {t_bronce}</div><div style="font-size:10px; color:#888;">BRONCE</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333; background:rgba(255,255,255,0.05); border-radius:4px;"><div style="font-size:22px; font-weight:bold; color:#fff;">★ {total_med}</div><div style="font-size:10px; color:#888;">TOTAL</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Gráficos (Recuperados)
    if not df_n.empty:
        df_n['Anio'] = pd.to_datetime(df_n['fechanac']).dt.year
        df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria)
        
        t_g, t_c = st.tabs(["Género", "Categorías Master"])
        colors = alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#FF69B4'])
        
        with t_g:
            base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=80, innerRadius=50).encode(
                color=alt.Color("codgenero", scale=colors, legend=None),
                tooltip=["codgenero", "count()"]
            )
            text = base.mark_text(radius=100).encode(text="count()", order=alt.Order("codgenero"), color=alt.value("white"))
            st.altair_chart(pie + text, use_container_width=True)
            st.markdown("""<div style="text-align: center; font-size: 12px; margin-bottom: 5px;"><span style="color: #1f77b4;">● Masc</span> &nbsp; <span style="color: #FF69B4;">● Fem</span></div>""", unsafe_allow_html=True)

        with t_c:
            orden = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L+"]
            chart = alt.Chart(df_n).mark_bar(cornerRadius=3).encode(
                x=alt.X('Categoria', sort=orden, title=None),
                y=alt.Y('count()', title=None),
                color=alt.Color('codgenero', legend=None, scale=colors),
                tooltip=['Categoria', 'codgenero', 'count()']
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)

# --- 7. DASHBOARD M (MASTER - CON TODO + CANDADO) ---
def dashboard_m():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h3 style='color: white; font-size: 20px; margin: 0;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
            <h1 style='color: #E30613; font-size: 32px; margin: 0; font-weight: 800;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    if db:
        render_index_visual(db['nadadores'].copy(), db['tiempos'].copy(), db['relevos'].copy())
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("🗃️ Base de Datos", use_container_width=True): st.switch_page("pages/2_visualizar_datos.py")
        with c2: 
            if st.button("🏆 Ver Ranking", use_container_width=True): st.switch_page("pages/4_ranking.py")
        
        st.write("")
        if st.button("⏱️ Simulador de Postas", type="primary", use_container_width=True): st.switch_page("pages/3_simulador.py")

        # --- CANDADO PARA CARGA ---
        st.write(""); st.write("")
        col_space, col_lock = st.columns([8, 1])
        with col_lock:
            # Si ya es admin, mostramos candado abierto o nada
            if not st.session_state.admin_unlocked:
                if st.button("🔒", key="lock_m", help="Acceso Admin", type="tertiary"):
                    st.session_state.show_password = not st.session_state.show_password
        
        if st.session_state.show_password and not st.session_state.admin_unlocked:
            c_pass, c_ok = st.columns([3, 1])
            st.session_state.pass_input = c_pass.text_input("Clave Admin", type="password", label_visibility="collapsed")
            if c_ok.button("OK"): intentar_desbloqueo()
        
        if st.session_state.admin_unlocked:
            st.success("🔓 Modo Admin Activo: Pestaña 'Carga' habilitada.")
        
        st.divider()
        if st.button("Cerrar Sesión"): cerrar_sesion()

# --- 8. DASHBOARD N (NADADOR - INDEX COMPLETO + CARD) ---
def dashboard_n():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h3 style='color: white; font-size: 20px; margin: 0;'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
            <h1 style='color: #E30613; font-size: 32px; margin: 0; font-weight: 800;'>🔴⚫ NEWELL'S OLD BOYS ⚫🔴</h1>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    if db:
        # 1. MOSTRAR TODO EL INDEX (Como pidió el usuario)
        render_index_visual(db['nadadores'].copy(), db['tiempos'].copy(), db['relevos'].copy())
        
        st.divider()
        st.write("### 👤 Tu Perfil")
        
        # 2. CALCULAR DATOS DE LA CARD PERSONAL
        my_id = st.session_state.user_id
        df_nad = db['nadadores']
        me = df_nad[df_nad['codnadador'] == my_id].iloc[0]
        
        try: edad = datetime.now().year - pd.to_datetime(me['fechanac']).year
        except: edad = 0
        cat = calcular_cat_exacta(edad, db['categorias'])
        
        # Medallas propias
        df_t = db['tiempos'].copy(); df_r = db['relevos'].copy()
        df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0)
        df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0)
        
        mi_oro = len(df_t[(df_t['codnadador']==my_id)&(df_t['posicion']==1)]) + len(df_r[((df_r['nadador_1']==my_id)|(df_r['nadador_2']==my_id)|(df_r['nadador_3']==my_id)|(df_r['nadador_4']==my_id))&(df_r['posicion']==1)])
        mi_plata = len(df_t[(df_t['codnadador']==my_id)&(df_t['posicion']==2)]) + len(df_r[((df_r['nadador_1']==my_id)|(df_r['nadador_2']==my_id)|(df_r['nadador_3']==my_id)|(df_r['nadador_4']==my_id))&(df_r['posicion']==2)])
        mi_bronce = len(df_t[(df_t['codnadador']==my_id)&(df_t['posicion']==3)]) + len(df_r[((df_r['nadador_1']==my_id)|(df_r['nadador_2']==my_id)|(df_r['nadador_3']==my_id)|(df_r['nadador_4']==my_id))&(df_r['posicion']==3)])
        mi_total = mi_oro + mi_plata + mi_bronce
        
        # 3. CARD PERSONAL (Estilo CSS en st.markdown abajo)
        st.markdown(f"""
        <style>
            .padron-card {{ background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s; }}
            .padron-card:hover {{ border-color: #E30613; transform: scale(1.02); cursor: pointer; }}
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
        
        # Botón de acción
        if st.button("Ver Mi Ficha Completa ➝", type="primary", use_container_width=True):
            st.switch_page("pages/2_visualizar_datos.py")
            
        st.divider()
        if st.button("Cerrar Sesión", type="secondary"): cerrar_sesion()

# --- 9. RUTEO FINAL ---
pg_dash_m = st.Page(dashboard_m, title="Inicio", icon="🏠")
pg_dash_n = st.Page(dashboard_n, title="Mi Perfil", icon="🏊")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Base de Datos", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga", icon="⚙️")

if not st.session_state.role:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/4e/Newell%27s_Old_Boys_shield.svg", width=100)
    st.title("Acceso Socios")
    st.text_input("Nº Socio", key="input_socio", placeholder="Ej: 123456-01")
    if st.button("Ingresar", type="primary", use_container_width=True): validar_socio()

elif st.session_state.role == "M":
    # M ve Inicio, Datos, Ranking, Simulador... y si desbloqueó, Carga
    pages_m = [pg_dash_m, pg_datos, pg_ranking, pg_simulador]
    if st.session_state.admin_unlocked: pages_m.append(pg_carga)
    
    pg = st.navigation(pages_m)
    pg.run()

elif st.session_state.role == "N":
    # N solo ve Inicio (con su card) y Datos (restringido)
    pg = st.navigation([pg_dash_n, pg_datos])
    pg.run()
