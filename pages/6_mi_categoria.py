import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
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
    /* Estilo Tarjeta Nadador */
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
    .card-info { display: flex; flex-direction: column; }
    .card-name { font-size: 16px; font-weight: bold; color: white; text-transform: uppercase; }
    .card-sub { font-size: 12px; color: #aaa; margin-top: 2px; }
    
    .section-title { 
        color: #E30613; 
        font-weight: bold; 
        margin-top: 25px; 
        margin-bottom: 15px; 
        border-bottom: 1px solid #444; 
        font-size: 16px; 
        text-transform: uppercase; 
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
            "distancias": conn.read(worksheet="Distancias"),
            "categorias": conn.read(worksheet="Categorias") # Tabla de referencia
        }
    except: return None

db = cargar_datos()
if not db: st.stop()

# --- FUNCIONES AUXILIARES ---

def calcular_edad_fina(fecha_nac):
    """Calcula la edad al 31 de diciembre del año actual."""
    if pd.isna(fecha_nac): return None
    try:
        nac = pd.to_datetime(fecha_nac, errors='coerce')
        if pd.isna(nac): return None
        hoy = date.today()
        # Regla FINA/Masters: Año actual - Año de nacimiento
        return hoy.year - nac.year
    except: return None

def asignar_categoria(edad, df_cat):
    """Busca la categoría correspondiente a la edad en la tabla de referencia."""
    if edad is None: return "S/D"
    
    # Filtrar tabla donde la edad esté dentro del rango [edad_min, edad_max]
    match = df_cat[(df_cat['edad_min'] <= edad) & (df_cat['edad_max'] >= edad)]
    
    if not match.empty:
        return match.iloc[0]['nombre_cat'] # Retorna 'nombre_cat' (ej: Master A)
    return "Sin Categoría"

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

# --- PROCESAMIENTO DE DATOS ---
df_nad = db['nadadores'].copy()
df_cat = db['categorias'].copy()

# 1. Asegurar tipos de datos en Categorías
df_cat['edad_min'] = pd.to_numeric(df_cat['edad_min'], errors='coerce')
df_cat['edad_max'] = pd.to_numeric(df_cat['edad_max'], errors='coerce')

# 2. Calcular Edad para todos los nadadores
# Usamos 'fechanac' según tu base de datos
df_nad['edad_calculada'] = df_nad['fechanac'].apply(calcular_edad_fina)

# 3. Asignar Categoría a cada nadador
df_nad['categoria_actual'] = df_nad['edad_calculada'].apply(lambda x: asignar_categoria(x, df_cat))

# --- LÓGICA DE ROLES ---
target_categoria = None
target_genero = None

if rol == "N":
    # MODO NADADOR: Detectar mis datos
    me = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
    
    if not me.empty:
        my_data = me.iloc[0]
        target_categoria = my_data['categoria_actual']
        target_genero = my_data['codgenero'] # Usamos 'codgenero' (M/F)
        
        edad_str = int(my_data['edad_calculada']) if pd.notna(my_data['edad_calculada']) else "S/D"
        st.info(f"👋 Hola **{mi_nombre}**. Tienes {edad_str} años (al 31/12).")
        st.markdown(f"### 🏷️ Categoría: <span style='color:#E30613'>{target_categoria}</span> - {target_genero}", unsafe_allow_html=True)
    else:
        st.error("No se encontró tu perfil de nadador en el sistema.")
        st.stop()

elif rol in ["M", "P"]:
    # MODO ENTRENADOR: Selector Manual
    st.markdown("<div class='section-title'>🔍 Panel de Control</div>", unsafe_allow_html=True)
    
    # Opciones basadas en la tabla Categorias y Generos existentes
    opciones_cat = sorted(df_cat['nombre_cat'].unique().tolist())
    opciones_gen = sorted(df_nad['codgenero'].dropna().unique().tolist())
    
    c1, c2 = st.columns(2)
    target_categoria = c1.selectbox("Categoría", opciones_cat)
    target_genero = c2.selectbox("Género", opciones_gen)

# --- VISUALIZACIÓN ---

if target_categoria and target_genero:
    
    # 1. FILTRAR RIVALES (Misma Categoría y Género)
    rivales = df_nad[
        (df_nad['categoria_actual'] == target_categoria) & 
        (df_nad['codgenero'] == target_genero)
    ].copy()
    
    ids_rivales = rivales['codnadador'].tolist()
    
    # --- MOSTRAR PADRÓN DE LA CATEGORÍA ---
    st.markdown(f"<div class='section-title'>🏊 Nadadores ({len(rivales)})</div>", unsafe_allow_html=True)
    
    if not rivales.empty:
        cols = st.columns(2)
        for i, (idx, row) in enumerate(rivales.iterrows()):
            # Destacar si soy yo
            es_yo = (str(row['codnadador']) == str(mi_id)) if rol == "N" else False
            clase = "swimmer-card is-me" if es_yo else "swimmer-card"
            yo_lbl = " (TÚ)" if es_yo else ""
            
            edad_txt = int(row['edad_calculada']) if pd.notna(row['edad_calculada']) else "-"
            
            with cols[i % 2]:
                st.markdown(f"""
                <div class="{clase}">
                    <div class="card-info">
                        <div class="card-name">{row['apellido'].upper()}, {row['nombre']}{yo_lbl}</div>
                        <div class="card-sub">Edad: {edad_txt} | Cat: {row['categoria_actual']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(f"No hay nadadores {target_genero} registrados en la categoría {target_categoria}.")

    # --- GRÁFICA COMPARATIVA ---
    if not rivales.empty:
        st.markdown("<div class='section-title'>📊 Ranking de Tiempos</div>", unsafe_allow_html=True)
        
        # Obtener entrenamientos de estos nadadores
        df_ent = db['entrenamientos'][db['entrenamientos']['codnadador'].isin(ids_rivales)].copy()
        
        if not df_ent.empty:
            df_ent = df_ent.merge(db['estilos'], on='codestilo').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia')
            
            # Filtros dinámicos basados en la data disponible para esta categoría
            c_e, c_d = st.columns(2)
            
            estilos_disp = sorted(df_ent['descripcion_x'].unique())
            sel_est = c_e.selectbox("Estilo", estilos_disp)
            
            dist_disp = sorted(df_ent[df_ent['descripcion_x'] == sel_est]['descripcion_y'].unique())
            sel_dist = c_d.selectbox("Distancia", dist_disp) if dist_disp else None
            
            if sel_est and sel_dist:
                # Datos del gráfico
                data_chart = df_ent[
                    (df_ent['descripcion_x'] == sel_est) & 
                    (df_ent['descripcion_y'] == sel_dist)
                ].copy()
                
                # Calcular mejor tiempo (mínimo) por nadador
                data_chart['segundos'] = data_chart['tiempo_final'].apply(a_segundos)
                best_times = data_chart.groupby('codnadador')['segundos'].min().reset_index()
                
                # Unir con nombres
                best_times = best_times.merge(rivales[['codnadador', 'apellido', 'nombre']], on='codnadador')
                best_times['Atleta'] = best_times['apellido'].str.upper() + " " + best_times['nombre'].str[0] + "."
                best_times['Etiqueta'] = best_times['segundos'].apply(fmt_mm_ss)
                
                # Colores
                def get_color(cod):
                    if rol == "N" and str(cod) == str(mi_id): return "#E30613" # Rojo Usuario
                    return "#666666" # Gris Rival
                
                best_times['Color'] = best_times['codnadador'].apply(get_color)
                best_times = best_times.sort_values('segundos', ascending=True) # Ranking
                
                # Gráfico
                fig = px.bar(
                    best_times, 
                    x='Atleta', 
                    y='segundos', 
                    text='Etiqueta', 
                    color='Color', 
                    color_discrete_map="identity"
                )
                
                # Ajuste visual
                max_y = best_times['segundos'].max() * 1.15
                tick_vals = np.linspace(0, max_y, 5)
                tick_text = [fmt_mm_ss(x) for x in tick_vals]

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
                    mi_dato = best_times[best_times['codnadador'].astype(str) == str(mi_id)]
                    if not mi_dato.empty:
                        rank = best_times.index.get_loc(mi_dato.index[0]) + 1
                        st.success(f"🏅 Ranking: **#{rank}** de {len(best_times)} en {sel_dist} {sel_est}.")
                    else:
                        st.info("Aún no tienes registros en esta prueba específica.")
            else:
                st.warning("No hay datos para los filtros seleccionados.")
        else:
            st.info("Esta categoría aún no tiene registros de entrenamientos.")
