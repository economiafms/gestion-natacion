import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Base de Datos", layout="centered", initial_sidebar_state="collapsed")
st.title("🗃️ Base de Datos")

# Estilos CSS para Tarjetas Mobile
st.markdown("""
<style>
    .mobile-card {
        background-color: #262730;
        border: 1px solid #464855;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .card-title { font-weight: bold; font-size: 16px; color: #ffffff; }
    .card-time { font-family: monospace; font-weight: bold; font-size: 18px; color: #4CAF50; }
    .card-sub { font-size: 12px; color: #b0b0b0; }
    .relay-member { font-size: 13px; border-bottom: 1px solid #3a3b42; padding: 4px 0; }
    .tag {
        background-color: #1E3A8A; color: white;
        padding: 2px 8px; border-radius: 4px; font-size: 10px; margin-left: 5px;
    }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS (Lógica Intacta) ---
@st.cache_data(ttl="15m")
def cargar_visualizacion():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet=\"Relevos\"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except Exception as e:
        return None

data = cargar_visualizacion()
if not data: 
    st.error("Error de conexión. Intenta recargar.")
    st.stop()

# --- 3. PROCESAMIENTO PREVIO ---
# Preparamos nombres legibles
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

# --- 4. NAVEGACIÓN POR PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["👤 Padrón", "⏱️ Individuales", "🏊‍♂️ Relevos"])

# ==========================================
# TAB 1: PADRÓN (Perfil de Nadador)
# ==========================================
with tab1:
    st.markdown("### Perfil de Atleta")
    # Buscador principal
    busqueda = st.selectbox("Buscar Nadador:", df_nad['Nombre Completo'].sort_values().unique(), index=None, placeholder="Escribe un apellido...")
    
    if busqueda:
        perfil = df_nad[df_nad['Nombre Completo'] == busqueda].iloc[0]
        anio_nac = pd.to_datetime(perfil['fechanac']).year
        edad = datetime.now().year - anio_nac
        
        # Tarjeta de Perfil
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1f77b4 0%, #0d47a1 100%); padding: 20px; border-radius: 12px; color: white; text-align: center;">
            <h2 style="margin:0; color:white;">{perfil['nombre']} {perfil['apellido']}</h2>
            <p style="opacity:0.9; margin-top:5px;">{edad} Años | Categoría {perfil['codgenero']}</p>
            <div style="font-size:12px; margin-top:10px; opacity:0.7;">DNI: {perfil['dni']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("👆 Busca un nadador para ver su ficha completa.")
        
        # Opción: Ver lista completa si no busca nada (Expandible para no molestar)
        with st.expander("Ver lista completa de nadadores"):
            st.dataframe(df_nad[['apellido', 'nombre', 'codgenero', 'fechanac']], hide_index=True, use_container_width=True)

# ==========================================
# TAB 2: RESULTADOS INDIVIDUALES
# ==========================================
with tab2:
    # Preparar datos
    mi = data['tiempos'].copy()
    mi = mi.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
    mi['Nadador'] = mi['codnadador'].map(dict_id_nombre)
    mi['Fecha_dt'] = pd.to_datetime(mi['fecha'])
    
    # --- FILTROS OCULTABLES (Acordeón) ---
    with st.expander("🔍 Filtros de Búsqueda", expanded=False):
        f1, f2 = st.columns(2)
        f_nad = f1.selectbox("Filtrar Nadador", ["Todos"] + sorted(df_nad['Nombre Completo'].unique().tolist()))
        f_est = f2.selectbox("Estilo", ["Todos"] + sorted(mi['descripcion_x'].unique().tolist()))
        f_pil = st.select_slider("Tipo de Pileta", options=["Todas", "25m", "50m"])

    # Aplicar filtros
    df_view = mi.copy()
    if f_nad != "Todos": df_view = df_view[df_view['Nadador'] == f_nad]
    if f_est != "Todos": df_view = df_view[df_view['descripcion_x'] == f_est]
    if f_pil != "Todas": df_view = df_view[df_view['medida'].str.contains(f_pil[:2])]

    # Ordenar: Más reciente primero
    df_view = df_view.sort_values(by='Fecha_dt', ascending=False)

    # --- RENDERIZADO TIPO "LISTA DE SPOTIFY" ---
    st.write(f"**Resultados encontrados:** {len(df_view)}")
    
    if df_view.empty:
        st.warning("No hay registros con esos filtros.")
    else:
        # Limitamos a los últimos 50 para no trabar el celular
        for _, row in df_view.head(50).iterrows():
            # Icono según pileta
            icon_pool = "🟦" if "50" in str(row['medida']) else "Small"
            
            # HTML Card
            st.markdown(f"""
            <div class="mobile-card">
                <div class="card-header">
                    <div class="card-title">{row['descripcion_y']} {row['descripcion_x']}</div>
                    <div class="card-time">{row['tiempo']}</div>
                </div>
                <div class="card-sub">
                    👤 {row['Nadador']}<br>
                    📅 {row['fecha']} • {row['club']} <span class="tag">{row['medida']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# TAB 3: RELEVOS (Con Tarjetas de Equipo)
# ==========================================
with tab3:
    mr = data['relevos'].copy()
    mr = mr.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
    mr = mr.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})

    # --- FILTROS ---
    with st.expander("🔍 Filtros de Relevos", expanded=False):
        c1, c2 = st.columns(2)
        r_gen = c1.selectbox("Género Relevo", ["Todos", "M", "F", "X"])
        r_est = c2.selectbox("Estilo Relevo", ["Todos"] + sorted(mr['Estilo'].unique().tolist()))

    if r_gen != "Todos": mr = mr[mr['codgenero'] == r_gen]
    if r_est != "Todos": mr = mr[mr['Estilo'] == r_est]

    # --- RENDERIZADO DE TARJETAS DE EQUIPO ---
    st.write(f"**Equipos encontrados:** {len(mr)}")

    for _, row in mr.iterrows():
        # Calcular Suma de Edades (Lógica que pediste mantener)
        nombres_integrantes = []
        suma_edades = 0
        
        for i in range(1, 5):
            id_n = row[f'nadador_{i}']
            # Buscamos datos del nadador
            nad = df_nad[df_nad['codnadador'] == id_n]
            if not nad.empty:
                nombre = nad.iloc[0]['Nombre Completo']
                # Cálculo edad
                edad = datetime.now().year - pd.to_datetime(nad.iloc[0]['fechanac']).year
                suma_edades += edad
                parcial = row[f'tiempo_{i}'] if row[f'tiempo_{i}'] else "-.-"
                nombres_integrantes.append(f"{nombre} <b>({parcial})</b>")
            else:
                nombres_integrantes.append("Desconocido")
        
        # Tarjeta Compleja de Relevo
        st.markdown(f"""
        <div class="mobile-card" style="border-left: 5px solid #FF4B4B;">
            <div class="card-header">
                <div class="card-title">{row['Distancia']} {row['Estilo']} ({row['codgenero']})</div>
                <div class="card-time">{row['tiempo_final']}</div>
            </div>
            <div class="card-sub" style="margin-bottom:8px;">
                📅 {row['fecha']} • {row['club']} • <b>Suma Edades: {suma_edades}</b>
            </div>
            <div style="background-color: rgba(255,255,255,0.05); padding: 8px; border-radius: 5px;">
                <div class="relay-member">1. {nombres_integrantes[0]}</div>
                <div class="relay-member">2. {nombres_integrantes[1]}</div>
                <div class="relay-member">3. {nombres_integrantes[2]}</div>
                <div class="relay-member" style="border:none;">4. {nombres_integrantes[3]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
