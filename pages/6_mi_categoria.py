import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime
import plotly.express as px
import numpy as np

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Mi Categoría", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id 
mi_nombre = st.session_state.user_name

st.title("🏆 Ranking por Categoría")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* Tarjeta de Nadador */
    .swimmer-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #555;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .swimmer-card.is-me {
        border-left: 5px solid #E30613; /* Rojo Newell's */
        background-color: #2b1e1e;
    }
    .card-name { font-size: 16px; font-weight: bold; color: white; text-transform: uppercase; }
    .card-sub { font-size: 12px; color: #aaa; }
    
    .section-title { 
        color: #E30613; 
        font-weight: bold; 
        margin-top: 25px; 
        margin-bottom: 15px; 
        border-bottom: 1px solid #444; 
        font-size: 16px; 
        text-transform: uppercase; 
    }
    .filter-box {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #444;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN Y DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def cargar_datos():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "entrenamientos": conn.read(worksheet="Entrenamientos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias")
        }
    except: return None

db = cargar_datos()
if not db: st.stop()

# --- FUNCIONES AUXILIARES ---
def calcular_categoria(fecha_nac):
    """Calcula la categoría MASTER basada en edad al 31/Dic"""
    if pd.isna(fecha_nac): return "S/D"
    try:
        nac = pd.to_datetime(fecha_nac)
        hoy = date.today()
        edad = hoy.year - nac.year
        
        if edad < 20: return "JUVENIL"
        elif 20 <= edad <= 24: return "PRE-MASTER"
        else:
            base = int((edad - 25) / 5)
            letra = chr(65 + base) # A, B, C...
            inicio = 25 + (base * 5)
            fin = inicio + 4
            return f"MASTER {letra} ({inicio}-{fin})"
    except: return "ERROR"

def a_segundos(t_str):
    try:
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

def fmt_mm_ss(seconds):
    if seconds is None or np.isnan(seconds): return ""
    m = int(seconds // 60)
    s = int(seconds % 60)
    c = int(round((seconds - int(seconds)) * 100))
    return f"{m:02d}:{s:02d}.{c:02d}"

# --- PROCESAMIENTO INICIAL ---
df_nad = db['nadadores'].copy()
# Calcular categoría para TODOS los nadadores
df_nad['categoria_calculada'] = df_nad['fecha_nacimiento'].apply(calcular_categoria)

# --- LÓGICA DE ROLES ---
target_categoria = None
target_genero = None
user_in_category = False

if rol == "N":
    # MODO NADADOR: Automático
    me = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
    if not me.empty:
        target_categoria = me.iloc[0]['categoria_calculada']
        target_genero = me.iloc[0]['genero']
        user_in_category = True
        st.markdown(f"#### 👤 Mi Categoría: <span style='color:#E30613'>{target_categoria} - {target_genero}</span>", unsafe_allow_html=True)
    else:
        st.error("No se encontró tu perfil de nadador.")
        st.stop()

elif rol in ["M", "P"]:
    # MODO ENTRENADOR: Filtros manuales
    st.markdown("<div class='section-title'>🔍 Consultar Categoría</div>", unsafe_allow_html=True)
    
    # Obtener listas únicas ordenadas
    cats_disponibles = sorted(df_nad['categoria_calculada'].unique().tolist())
    gens_disponibles = sorted(df_nad['genero'].unique().tolist())
    
    with st.container():
        c1, c2 = st.columns(2)
        target_categoria = c1.selectbox("Seleccionar Categoría", cats_disponibles)
        target_genero = c2.selectbox("Seleccionar Género", gens_disponibles)
        
    user_in_category = False # El entrenador no compite en la gráfica

# --- FILTRADO DE RIVALES ---
if target_categoria and target_genero:
    # Filtrar padrón
    rivales = df_nad[
        (df_nad['categoria_calculada'] == target_categoria) & 
        (df_nad['genero'] == target_genero)
    ].copy()
    
    ids_rivales = rivales['codnadador'].tolist()
    
    # 1. VISUALIZACIÓN DE CARDS
    st.markdown(f"<div class='section-title'>🏊 Padrón: {target_categoria} ({target_genero})</div>", unsafe_allow_html=True)
    
    if not rivales.empty:
        cols = st.columns(2)
        for i, (idx, row) in enumerate(rivales.iterrows()):
            es_yo = (str(row['codnadador']) == str(mi_id)) if rol == "N" else False
            clase = "swimmer-card is-me" if es_yo else "swimmer-card"
            tag = " (TÚ)" if es_yo else ""
            
            with cols[i % 2]:
                st.markdown(f"""
                <div class="{clase}">
                    <div>
                        <div class="card-name">{row['apellido'].upper()}, {row['nombre']}{tag}</div>
                        <div class="card-sub">{row['categoria_calculada']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No hay nadadores registrados en esta categoría.")

    # 2. GRÁFICA COMPARATIVA
    st.markdown("<div class='section-title'>📊 Comparativa de Tiempos</div>", unsafe_allow_html=True)
    
    # Traer entrenamientos solo de estos nadadores
    df_ent = db['entrenamientos'][db['entrenamientos']['codnadador'].isin(ids_rivales)].copy()
    
    if not df_ent.empty:
        df_ent = df_ent.merge(db['estilos'], on='codestilo').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia')
        
        # Filtros para la gráfica (Solo lo que hay disponible)
        c_e, c_d = st.columns(2)
        est_opts = sorted(df_ent['descripcion_x'].unique())
        sel_est = c_e.selectbox("Estilo", est_opts)
        
        dist_opts = sorted(df_ent[df_ent['descripcion_x'] == sel_est]['descripcion_y'].unique())
        sel_dist = c_d.selectbox("Distancia", dist_opts) if dist_opts else None
        
        if sel_est and sel_dist:
            # Datos para el gráfico
            data_chart = df_ent[
                (df_ent['descripcion_x'] == sel_est) & 
                (df_ent['descripcion_y'] == sel_dist)
            ].copy()
            
            # Quedarse con el mejor tiempo de cada nadador
            data_chart['segundos'] = data_chart['tiempo_final'].apply(a_segundos)
            best_times = data_chart.groupby('codnadador')['segundos'].min().reset_index()
            
            # Unir con nombres
            best_times = best_times.merge(rivales[['codnadador', 'apellido', 'nombre']], on='codnadador')
            best_times['Atleta'] = best_times['apellido'].str.upper() + " " + best_times['nombre'].str[0] + "."
            best_times['Etiqueta'] = best_times['segundos'].apply(fmt_mm_ss)
            
            # Definir colores (Yo = Rojo, Resto = Gris)
            # Si soy Rol M, todos gris salvo que quiera destacar algo (aquí todos gris oscuro o por defecto)
            def get_color(cod):
                if rol == "N" and str(cod) == str(mi_id): return "#E30613" # Rojo Newell's
                return "#555555" # Gris
            
            best_times['Color'] = best_times['codnadador'].apply(get_color)
            best_times = best_times.sort_values('segundos', ascending=True) # Ranking
            
            # Gráfico de Barras
            fig = px.bar(
                best_times, 
                x='Atleta', 
                y='segundos', 
                text='Etiqueta',
                color='Color',
                color_discrete_map="identity"
            )
            
            # Ejes limpios
            min_y = best_times['segundos'].min() * 0.9
            max_y = best_times['segundos'].max() * 1.1
            tick_vals = np.linspace(min_y, max_y, 5)
            tick_text = [fmt_mm_ss(v) for v in tick_vals]
            
            fig.update_traces(textposition='auto', hovertemplate='⏱️ %{text}<extra></extra>')
            fig.update_layout(
                height=300, 
                template="plotly_dark", 
                showlegend=False, 
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis=dict(title="Tiempo", tickmode='array', tickvals=tick_vals, ticktext=tick_text, range=[0, max_y]),
                xaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Mensaje de posición para el Nadador
            if rol == "N":
                mi_pos = best_times[best_times['codnadador'].astype(str) == str(mi_id)]
                if not mi_pos.empty:
                    rank = best_times.index.get_loc(mi_pos.index[0]) + 1
                    total = len(best_times)
                    st.success(f"🏅 Ranking: **#{rank}** de {total} nadadores.")
                else:
                    st.warning(f"Aún no tienes tiempos registrados en {sel_dist} {sel_est}.")
        else:
            st.warning("No hay registros disponibles para este estilo en esta categoría.")
    else:
        st.info("Esta categoría aún no tiene registros de tiempos cargados.")
