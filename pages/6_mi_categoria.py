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
        border-left: 5px solid #E30613;
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
            "categorias_ref": conn.read(worksheet="Categorias") 
        }
    except: return None

db = cargar_datos()
if not db: st.stop()

# --- FUNCIONES AUXILIARES ---
def calcular_edad(fecha_nac):
    """Calcula edad al 31 de diciembre del año actual"""
    if pd.isna(fecha_nac): return None
    try:
        # Intenta convertir a fecha
        nac = pd.to_datetime(fecha_nac, errors='coerce')
        if pd.isna(nac): return None
        hoy = date.today()
        return hoy.year - nac.year
    except: return None

def obtener_categoria_db(edad, df_cat_ref):
    if edad is None: return "S/D"
    try:
        match = df_cat_ref[
            (df_cat_ref['edad_min'] <= edad) & 
            (df_cat_ref['edad_max'] >= edad)
        ]
        if not match.empty:
            return match.iloc[0]['descripcion']
    except: pass
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

# --- PROCESAMIENTO ROBUSTO ---
df_nad = db['nadadores'].copy()
df_ref_cat = db['categorias_ref'].copy()

# 1. Normalizar nombres de columnas (minusculas y sin espacios) para evitar KeyError
df_nad.columns = df_nad.columns.str.strip().str.lower()
df_ref_cat.columns = df_ref_cat.columns.str.strip().str.lower()

# 2. Verificar columnas críticas
required_cols = ['fecha_nacimiento', 'genero', 'codnadador', 'apellido', 'nombre']
missing = [c for c in required_cols if c not in df_nad.columns]

if missing:
    st.error(f"❌ Error de Datos: No se encuentran las columnas: {', '.join(missing)}")
    st.info("Por favor verifica en tu Google Sheet (hoja 'Nadadores') que los nombres de columna sean exactos.")
    st.stop()

# 3. Calcular Edad y Categoría
df_nad['edad_calc'] = df_nad['fecha_nacimiento'].apply(calcular_edad)
df_nad['categoria_actual'] = df_nad['edad_calc'].apply(lambda x: obtener_categoria_db(x, df_ref_cat))

# --- LÓGICA DE ROLES ---
target_categoria = None
target_genero = None

if rol == "N":
    me = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
    
    if not me.empty:
        my_data = me.iloc[0]
        target_categoria = my_data['categoria_actual']
        target_genero = my_data['genero']
        
        # Validación extra por si la edad no se pudo calcular
        edad_str = int(my_data['edad_calc']) if pd.notna(my_data['edad_calc']) else "S/D"
        
        st.info(f"👋 Hola **{mi_nombre}**. Edad calculada: {edad_str} años.")
        st.markdown(f"### 🏷️ <span style='color:#E30613'>{target_categoria}</span> ({target_genero})", unsafe_allow_html=True)
    else:
        st.error("No se encontró tu perfil en la base de datos.")
        st.stop()

elif rol in ["M", "P"]:
    st.markdown("<div class='section-title'>🔍 Panel de Categorías</div>", unsafe_allow_html=True)
    
    # Opciones seguras
    if 'descripcion' in df_ref_cat.columns:
        opciones_cat = sorted(df_ref_cat['descripcion'].unique().tolist())
    else:
        st.error("La hoja 'Categorias' debe tener una columna 'descripcion'.")
        st.stop()
        
    opciones_gen = sorted(df_nad['genero'].dropna().unique().tolist())
    
    c1, c2 = st.columns(2)
    target_categoria = c1.selectbox("Categoría", opciones_cat, index=0)
    target_genero = c2.selectbox("Género", opciones_gen, index=0)

# --- VISUALIZACIÓN ---
if target_categoria and target_genero:
    
    rivales = df_nad[
        (df_nad['categoria_actual'] == target_categoria) & 
        (df_nad['genero'] == target_genero)
    ].copy()
    
    ids_rivales = rivales['codnadador'].tolist()
    
    # 1. PADRÓN
    st.markdown(f"<div class='section-title'>🏊 Padrón ({len(rivales)})</div>", unsafe_allow_html=True)
    
    if not rivales.empty:
        cols = st.columns(2)
        for i, (idx, row) in enumerate(rivales.iterrows()):
            es_yo = (str(row['codnadador']) == str(mi_id)) if rol == "N" else False
            clase = "swimmer-card is-me" if es_yo else "swimmer-card"
            yo_lbl = " (TÚ)" if es_yo else ""
            
            edad_txt = int(row['edad_calc']) if pd.notna(row['edad_calc']) else "-"
            
            with cols[i % 2]:
                st.markdown(f"""
                <div class="{clase}">
                    <div class="card-info">
                        <div class="card-name">{row['apellido'].upper()}, {row['nombre']}{yo_lbl}</div>
                        <div class="card-sub">Edad: {edad_txt} | {row['categoria_actual']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(f"No hay nadadores {target_genero} en {target_categoria}.")

    # 2. GRÁFICA
    st.markdown("<div class='section-title'>📊 Ranking de Tiempos</div>", unsafe_allow_html=True)
    
    df_ent = db['entrenamientos'][db['entrenamientos']['codnadador'].isin(ids_rivales)].copy()
    
    if not df_ent.empty:
        df_ent = df_ent.merge(db['estilos'], on='codestilo').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia')
        
        c_e, c_d = st.columns(2)
        estilos_disp = sorted(df_ent['descripcion_x'].unique())
        sel_est = c_e.selectbox("Estilo", estilos_disp)
        
        dist_disp = sorted(df_ent[df_ent['descripcion_x'] == sel_est]['descripcion_y'].unique())
        sel_dist = c_d.selectbox("Distancia", dist_disp) if dist_disp else None
        
        if sel_est and sel_dist:
            data_chart = df_ent[
                (df_ent['descripcion_x'] == sel_est) & 
                (df_ent['descripcion_y'] == sel_dist)
            ].copy()
            
            data_chart['segundos'] = data_chart['tiempo_final'].apply(a_segundos)
            best_times = data_chart.groupby('codnadador')['segundos'].min().reset_index()
            best_times = best_times.merge(rivales[['codnadador', 'apellido', 'nombre']], on='codnadador')
            
            best_times['Atleta'] = best_times['apellido'].str.upper() + " " + best_times['nombre'].str[0] + "."
            best_times['Etiqueta'] = best_times['segundos'].apply(fmt_mm_ss)
            
            def get_color(cod):
                if rol == "N" and str(cod) == str(mi_id): return "#E30613"
                return "#666666"
            
            best_times['Color'] = best_times['codnadador'].apply(get_color)
            best_times = best_times.sort_values('segundos', ascending=True)
            
            fig = px.bar(best_times, x='Atleta', y='segundos', text='Etiqueta', color='Color', color_discrete_map="identity")
            
            max_y = best_times['segundos'].max() * 1.15
            tick_vals = np.linspace(0, max_y, 5)
            tick_text = [fmt_mm_ss(x) for x in tick_vals]

            fig.update_traces(textposition='auto', hovertemplate='⏱️ %{text}<extra></extra>')
            fig.update_layout(
                height=320, template="plotly_dark", showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis=dict(title="Tiempo", tickmode='array', tickvals=tick_vals, ticktext=tick_text, range=[0, max_y]),
                xaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            if rol == "N":
                mi_dato = best_times[best_times['codnadador'].astype(str) == str(mi_id)]
                if not mi_dato.empty:
                    rank = best_times.index.get_loc(mi_dato.index[0]) + 1
                    st.success(f"🏅 Tu posición: **#{rank}** de {len(best_times)}.")
                else:
                    st.caption("Sin tiempos registrados para esta prueba.")
        else:
            st.warning("No hay registros para los filtros seleccionados.")
    else:
        st.info("Sin tiempos de entrenamiento registrados.")
