import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt

# --- 1. CONFIGURACIÓN DEL SITIO ---
st.set_page_config(page_title="NOB Natación", layout="centered") # 'Centered' se ve mejor en celulares

# --- 2. SISTEMA DE NAVEGACIÓN (Router) ---
# Definimos las páginas disponibles en el sistema
pg_dashboard = st.Page(lambda: dashboard_main(), title="Inicio", icon="🏠")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking Histórico", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador de Postas", icon="⏱️")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Panel de Carga", icon="⚙️")

# Lógica de Seguridad: La carga solo aparece si la URL es ?access=admin
params = st.query_params
es_admin = params.get("access") == "admin"

if es_admin:
    pg = st.navigation({
        "Club": [pg_dashboard, pg_ranking, pg_simulador],
        "Admin": [pg_carga]
    })
else:
    pg = st.navigation([pg_dashboard, pg_ranking, pg_simulador])

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

# --- 4. CONTENIDO DEL DASHBOARD (La vista principal) ---
def dashboard_main():
    # Encabezado Mobile
    c_logo, c_tit = st.columns([1, 4])
    with c_logo:
        # Logo de NOB (URL pública estable)
        st.image("https://upload.wikimedia.org/wikipedia/commons/4/4e/Newell%27s_Old_Boys_shield.svg", width=60)
    with c_tit:
        st.markdown("<h1 style='font-size: 28px; margin-bottom: 0px;'>Natación NOB</h1>", unsafe_allow_html=True)
        st.caption("Panel de Rendimiento Deportivo")

    st.divider()

    # Carga de datos para KPIs
    data = cargar_kpis()
    
    if data:
        df_n = data['nadadores']
        df_t = data['tiempos']
        
        # --- SECCIÓN 1: KPIs (Tarjetas Grandes) ---
        # En mobile, st.metric se ve muy bien
        k1, k2 = st.columns(2)
        k1.metric("🏊‍♂️ Plantel Activo", f"{len(df_n)}", "Nadadores")
        k2.metric("⏱️ Marcas Históricas", f"{len(df_t)}", "Registros")

        # --- SECCIÓN 2: ACCESOS RÁPIDOS (Botones Gigantes) ---
        st.subheader("Accesos Directos")
        
        # Usamos contenedores para simular tarjetas de app
        with st.container(border=True):
            col_icon, col_text = st.columns([1, 4])
            with col_icon: st.markdown("# 🏆")
            with col_text:
                st.markdown("**Ranking y Mejores Tiempos**")
                st.caption("Consultá récords y comparativas.")
            if st.button("Ver Ranking", use_container_width=True):
                st.switch_page("pages/4_ranking.py")

        with st.container(border=True):
            col_icon2, col_text2 = st.columns([1, 4])
            with col_icon2: st.markdown("# 🤖")
            with col_text2:
                st.markdown("**Simulador de Postas IA**")
                st.caption("Armado inteligente de equipos.")
            if st.button("Abrir Simulador", use_container_width=True):
                st.switch_page("pages/3_simulador.py")
        
        st.divider()

        # --- SECCIÓN 3: GRÁFICO VISUAL (Simple y Bonito) ---
        st.subheader("📊 Distribución del Equipo")
        
        if not df_n.empty:
            # Gráfico de Donut: Género
            base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                color=alt.Color("codgenero", scale=alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#ff7f0e']), legend=None),
                tooltip=["codgenero", "count()"]
            )
            text = base.mark_text(radius=120).encode(
                text="count()",
                order=alt.Order("codgenero"),
                color=alt.value("white")  # Color del texto
            )
            
            # Gráfico de Barras: Edades
            df_n['Edad'] = 2026 - pd.to_datetime(df_n['fechanac']).dt.year
            bar = alt.Chart(df_n).mark_bar(color='#FF4B4B').encode(
                x=alt.X('Edad', bin=alt.Bin(maxbins=10), title='Rango de Edad'),
                y=alt.Y('count()', title='Cant.')
            ).properties(height=200)

            t1, t2 = st.tabs(["Por Género", "Por Edad"])
            with t1:
                st.altair_chart(pie + text, use_container_width=True)
                # Leyenda manual simple
                st.caption("🔵 Masculino | 🟠 Femenino")
            with t2:
                st.altair_chart(bar, use_container_width=True)

    else:
        st.info("Conectando con la base de datos...")

# --- 5. EJECUCIÓN ---
pg.run()
