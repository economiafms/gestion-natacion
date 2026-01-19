import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime
import time

# --- 1. CONFIGURACIÓN DEL SITIO ---
st.set_page_config(page_title="NOB Natación", layout="centered", initial_sidebar_state="collapsed")

# --- 2. GESTIÓN DE ESTADO Y LOGIN ---
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

if "show_login" not in st.session_state:
    st.session_state.show_login = False

# Función de verificación
def verificar_login():
    try:
        sec_user = st.secrets["admin"]["usuario"]
        sec_pass = st.secrets["admin"]["password"]
    except:
        st.error("Falta configurar secrets.toml")
        return

    input_user = st.session_state.get("input_user", "")
    input_pass = st.session_state.get("input_pass", "")

    if input_user == sec_user and input_pass == sec_pass:
        st.session_state.admin_mode = True
        st.session_state.show_login = False
        st.success("¡Bienvenido Leproso!")
        time.sleep(1)
        st.rerun()
    else:
        st.error("Usuario o contraseña incorrectos")

def logout():
    st.session_state.admin_mode = False
    st.rerun()

# --- 3. SISTEMA DE NAVEGACIÓN ---
pg_dashboard = st.Page(lambda: dashboard_main(), title="Inicio", icon="🏠")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Base de Datos", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga", icon="⚙️")

if st.session_state.admin_mode:
    pg = st.navigation({
        "Club": [pg_dashboard, pg_datos, pg_ranking, pg_simulador],
        "Admin": [pg_carga]
    })
else:
    pg = st.navigation([pg_dashboard, pg_datos, pg_ranking, pg_simulador])

# --- 4. CONEXIÓN DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_kpis():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos")
        }
    except: return None

# --- 5. FUNCIÓN AUXILIAR ---
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

# --- 6. DASHBOARD PRINCIPAL ---
def dashboard_main():
    # --- TÍTULO PERSONALIZADO (ROJO Y NEGRO) ---
    st.markdown("""
        <div style='text-align: center; margin-bottom: 25px;'>
            <h3 style='color: white; font-size: 22px; margin: 0; padding: 0; font-weight: normal; letter-spacing: 1px;'>
                BIENVENIDOS AL COMPLEJO ACUÁTICO
            </h3>
            <h1 style='color: #E30613; font-size: 36px; margin-top: 5px; padding: 0; font-weight: 800; text-transform: uppercase; text-shadow: 2px 2px 4px #000000;'>
                🔴⚫ NEWELL'S OLD BOYS ⚫🔴
            </h1>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    data = cargar_kpis()
    
    if data:
        df_n = data['nadadores']
        df_t = data['tiempos']
        
        # --- SECCIÓN 1: KPIs (Lado a Lado en Mobile) ---
        cant_nad = len(df_n)
        cant_reg = len(df_t)
        
        # Usamos Flexbox para asegurar que queden horizontales en celular
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; gap: 10px; margin-bottom: 20px;">
            <div style="background-color: #262730; padding: 15px; border-radius: 10px; width: 48%; text-align: center; border: 1px solid #444; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <div style="font-size: 32px; font-weight: bold; color: white;">{cant_nad}</div>
                <div style="font-size: 13px; color: #ccc; text-transform: uppercase;">🏊‍♂️ Nadadores</div>
            </div>
            <div style="background-color: #262730; padding: 15px; border-radius: 10px; width: 48%; text-align: center; border: 1px solid #444; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <div style="font-size: 32px; font-weight: bold; color: white;">{cant_reg}</div>
                <div style="font-size: 13px; color: #ccc; text-transform: uppercase;">⏱️ Registros</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- SECCIÓN 2: ACCESOS RÁPIDOS ---
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("🗃️ Base de Datos", type="secondary", use_container_width=True):
                st.switch_page("pages/2_visualizar_datos.py")
        with c_btn2:
            if st.button("🏆 Ver Ranking", type="secondary", use_container_width=True):
                st.switch_page("pages/4_ranking.py")

        st.write("")
        if st.button("⏱️ Ir al Simulador de Postas", type="primary", use_container_width=True):
            st.switch_page("pages/3_simulador.py")

        st.divider()

        # --- SECCIÓN 3: GRÁFICOS ---
        if not df_n.empty:
            df_n['Anio'] = pd.to_datetime(df_n['fechanac']).dt.year
            df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria)
            
            tab_gen, tab_cat = st.tabs(["Género", "Categorías Master"])
            escala_colores = alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#FF69B4']) # Azul y Rosa

            with tab_gen:
                base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
                pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                    color=alt.Color("codgenero", scale=escala_colores, legend=None),
                    tooltip=["codgenero", "count()"]
                )
                text = base.mark_text(radius=130).encode(
                    text=alt.Text("count()"), order=alt.Order("codgenero"), color=alt.value("white") 
                )
                st.altair_chart(pie + text, use_container_width=True)
                st.markdown("""<div style="text-align: center; font-size: 14px; margin-bottom: 10px;">
                    <span style="color: #1f77b4; font-weight: bold;">● Masculino</span> &nbsp;&nbsp;&nbsp; 
                    <span style="color: #FF69B4; font-weight: bold;">● Femenino</span></div>""", unsafe_allow_html=True)

            with tab_cat:
                orden_cat = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L+"]
                chart_cat = alt.Chart(df_n).mark_bar(cornerRadius=3).encode(
                    x=alt.X('Categoria', sort=orden_cat, title=None),
                    y=alt.Y('count()', title='Nadadores'),
                    color=alt.Color('codgenero', legend=None, scale=escala_colores),
                    tooltip=['Categoria', 'codgenero', 'count()']
                ).properties(height=250)
                st.altair_chart(chart_cat, use_container_width=True)

    else: st.info("Conectando con Google Sheets...")

    # --- ZONA DE LOGIN OCULTA ---
    st.write(""); st.write("")
    
    if st.session_state.admin_mode:
        if st.button("🔒 Cerrar Sesión Admin", type="primary"):
            logout()
    else:
        # Candado oculto
        _, c_oculto = st.columns([10, 1]) 
        with c_oculto:
            if st.button("🔒", key="btn_unlock", type="tertiary"):
                st.session_state.show_login = not st.session_state.show_login

        if st.session_state.show_login:
            st.markdown("### Acceso Entrenadores")
            with st.form("login_form"):
                st.text_input("Usuario", key="input_user")
                st.text_input("Contraseña", type="password", key="input_pass")
                st.form_submit_button("Ingresar", on_click=verificar_login)

# --- EJECUCIÓN ---
pg.run()
