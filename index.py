import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime

# --- 1. CONFIGURACIÓN DEL SITIO ---
st.set_page_config(page_title="NOB Natación", layout="centered", initial_sidebar_state="collapsed")

# --- 2. SISTEMA DE NAVEGACIÓN (Router) ---
# Definimos las páginas apuntando a tus archivos existentes
pg_dashboard = st.Page(lambda: dashboard_main(), title="Inicio", icon="🏠")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Base de Datos", icon="🗃️") # <--- CORREGIDO AQUÍ
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga", icon="⚙️")

# Lógica de Seguridad (Solo admin ve Carga)
params = st.query_params
es_admin = params.get("access") == "admin"

if es_admin:
    pg = st.navigation({
        "Club": [pg_dashboard, pg_datos, pg_ranking, pg_simulador],
        "Admin": [pg_carga]
    })
else:
    # Usuario normal ve todo menos Carga
    pg = st.navigation([pg_dashboard, pg_datos, pg_ranking, pg_simulador])

# --- 3. CONEXIÓN DE DATOS ---
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

# --- 4. FUNCIÓN AUXILIAR: CATEGORÍAS ---
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

# --- 5. DASHBOARD PRINCIPAL (Mobile Friendly) ---
def dashboard_main():
    # Encabezado Compacto
    c_img, c_txt = st.columns([1, 4])
    with c_img:
        st.image("https://upload.wikimedia.org/wikipedia/commons/4/4e/Newell%27s_Old_Boys_shield.svg", width=55)
    with c_txt:
        st.markdown("<h3 style='margin-bottom: 0px; padding-top: 10px;'>Natación NOB</h3>", unsafe_allow_html=True)
        st.caption("Panel de Gestión Deportiva")

    st.divider()

    data = cargar_kpis()
    
    if data:
        df_n = data['nadadores']
        df_t = data['tiempos']
        
        # --- SECCIÓN 1: KPIs ---
        k1, k2 = st.columns(2)
        k1.metric("🏊‍♂️ Plantel", f"{len(df_n)}", "Nadadores")
        k2.metric("⏱️ Registros", f"{len(df_t)}", "Total marcas")

        st.write("") 

        # --- SECCIÓN 2: ACCESOS RÁPIDOS (2 Columnas grandes) ---
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("🗃️ Base de Datos", type="secondary", use_container_width=True):
                st.switch_page("pages/2_visualizar_datos.py") # <--- CONECTADO
        with c_btn2:
            if st.button("🏆 Ver Ranking", type="secondary", use_container_width=True):
                st.switch_page("pages/4_ranking.py")

        # Botón extra ancho completo para Simulador
        st.write("")
        if st.button("⏱️ Ir al Simulador de Postas", type="primary", use_container_width=True):
            st.switch_page("pages/3_simulador.py")

        st.divider()

        # --- SECCIÓN 3: GRÁFICOS VISUALES ---
        if not df_n.empty:
            df_n['Anio'] = pd.to_datetime(df_n['fechanac']).dt.year
            df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria)
            
            # Pestañas limpias
            tab_gen, tab_cat = st.tabs(["Género", "Categorías Master"])

            with tab_gen:
                base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
                pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                    color=alt.Color("codgenero", scale=alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#ff7f0e']), legend=None),
                    tooltip=["codgenero", "count()"]
                )
                text = base.mark_text(radius=130).encode(
                    text=alt.Text("count()"), order=alt.Order("codgenero"), color=alt.value("white") 
                )
                st.altair_chart(pie + text, use_container_width=True)
                
                # Leyenda simple centrada
                st.markdown("""
                <div style="text-align: center; font-size: 14px; margin-bottom: 10px;">
                    <span style="color: #1f77b4;">● Masculino</span> &nbsp;&nbsp; 
                    <span style="color: #ff7f0e;">● Femenino</span>
                </div>
                """, unsafe_allow_html=True)

            with tab_cat:
                # Orden lógico de categorías (no alfabético)
                orden_cat = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L+"]
                
                chart_cat = alt.Chart(df_n).mark_bar(cornerRadius=3).encode(
                    x=alt.X('Categoria', sort=orden_cat, title=None),
                    y=alt.Y('count()', title='Nadadores'),
                    color=alt.Color('codgenero', legend=None, scale=alt.Scale(range=['#1f77b4', '#ff7f0e'])),
                    tooltip=['Categoria', 'codgenero', 'count()']
                ).properties(height=250)
                
                st.altair_chart(chart_cat, use_container_width=True)

    else: st.info("Conectando con Google Sheets...")

# --- EJECUCIÓN ---
pg.run()
