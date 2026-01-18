import streamlit as st

st.set_page_config(page_title="Gestión Natación Master", layout="wide")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main-title { font-size: 50px; font-weight: bold; color: #1E3A8A; text-align: center; }
    .sub-title { font-size: 20px; color: #4B5563; text-align: center; margin-bottom: 40px; }
    .feature-card { border: 1px solid #E5E7EB; padding: 20px; border-radius: 10px; background-color: #F9FAFB; }
    </style>
    """, unsafe_allow_html=True)

# --- CONTENIDO ---
st.markdown("<div class='main-title'>🏊‍♂️ Sistema de Gestión Natación Master</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Optimización de registros, cálculo de categorías y análisis de marcas en tiempo real.</div>", unsafe_allow_html=True)

# --- EXPLICACIÓN DEL PRODUCTO ---
col_desc, col_img = st.columns([1.5, 1])

with col_desc:
    st.markdown("### ¿Para qué sirve esta herramienta?")
    st.write("""
    Este sistema fue diseñado para resolver el problema de la carga masiva de datos en torneos. 
    Permite a los entrenadores y delegados registrar tiempos de forma fluida, eliminando las esperas 
    y los errores manuales de cálculo de categorías.
    
    **Beneficios Clave:**
    * **Carga Off-line (Cola):** Guarda datos localmente y sincroniza con Google Sheets solo cuando estés listo, evitando el error 429.
    * **Cálculo Automático:** Determina categorías individuales y de relevos (suma de edades) al instante.
    * **Consolidación de Datos:** Todos los resultados del equipo en un solo lugar accesible desde cualquier dispositivo.
    """)

# --- MENÚ DE NAVEGACIÓN ---
st.divider()
st.markdown("### 🛠️ ¿Qué deseas hacer hoy?")

c1, c2 = st.columns(2)

with c1:
    with st.container(border=True):
        st.markdown("#### 📥 Módulo de Carga")
        st.write("Registra nuevos nadadores, tiempos individuales o postas de relevos. Utiliza la 'Cola de Carga' para mayor velocidad.")
        if st.button("Ir a Cargar Datos", use_container_width=True, type="primary"):
            st.switch_page("pages/1_cargar_datos.py")

with c2:
    with st.container(border=True):
        st.markdown("#### 📊 Módulo de Visualización")
        st.write("Consulta el padrón actualizado, revisa el historial de marcas y analiza el desempeño del equipo en torneos pasados.")
        if st.button("Ir a Visualización", use_container_width=True):
            st.switch_page("pages/2_visualizar_datos.py")