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
            "tiempos": conn.read(worksheet="Tiempos"),  # Tabla OFICIAL de Tiempos
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "categorias": conn.read(worksheet="Categorias")
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
        return hoy.year - nac.year
    except: return None

def asignar_categoria(edad, df_cat):
    """Busca la categoría correspondiente a la edad en la tabla de referencia."""
    if edad is None: return "S/D"
    # Filtrar rango de edad
    match = df_cat[(df_cat['edad_min'] <= edad) & (df_cat['edad_max'] >= edad)]
    if not match.empty:
        return match.iloc[0]['nombre_cat'] # Usamos 'nombre_cat' de tu tabla
    return "Sin Categoría"

def a_segundos(t_str):
    try:
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        # Maneja formato MM:SS.CC
        parts = str(t_str).split(':')
        if len(parts) == 2:
            m = int(parts[0])
            s_parts = parts[1].split('.')
            s = int(s_parts[0])
            c = int(s_parts[1]) if len(s_parts) > 1 else 0
            return (m * 60) + s + (c / 100)
        # Manejo opcional de formato solo segundos (SS.CC)
        elif len(parts) == 1:
             return float(parts[0])
        return None
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

# Normalizar columnas para evitar errores de espacios/mayúsculas
df_nad.columns = df_nad.columns.str.strip().str.lower()
df_cat.columns = df_cat.columns.str.strip().str.lower()

# ==============================================================================
# FIX DEFINITIVO: EXCLUSIÓN DE NADADOR 66 (FRANCO MINACORI)
# ==============================================================================
# Creamos una columna temporal normalizada para el ID (sin decimales ni espacios)
df_nad['temp_id_str'] = df_nad['codnadador'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

# 1. Filtro por ID
condicion_id = df_nad['temp_id_str'] == '66'

# 2. Filtro por Nombre y Apellido (Doble seguridad)
# Asumimos que las columnas se llaman 'nombre' y 'apellido' tras la normalización
condicion_nombre = (df_nad['nombre'].astype(str).str.upper().str.strip() == 'FRANCO') & \
                   (df_nad['apellido'].astype(str).str.upper().str.strip() == 'MINACORI')

# Aplicamos la exclusión: Nos quedamos con los que NO cumplan ninguna de las dos condiciones
df_nad = df_nad[~(condicion_id | condicion_nombre)]

# Limpiamos la columna temporal
df_nad = df_nad.drop(columns=['temp_id_str'])
# ==============================================================================

# 2. Calcular Edad y Categoría para todos
if 'fechanac' in df_nad.columns:
    df_nad['edad_calculada'] = df_nad['fechanac'].apply(calcular_edad_fina)
else:
    st.error("Error: No se encuentra la columna 'fechanac' en la tabla Nadadores.")
    st.stop()

if 'nombre_cat' in df_cat.columns:
    df_nad['categoria_actual'] = df_nad['edad_calculada'].apply(lambda x: asignar_categoria(x, df_cat))
else:
    st.error("Error: No se encuentra la columna 'nombre_cat' en la tabla Categorias.")
    st.stop()

# --- LÓGICA DE ROLES ---
target_categoria = None
target_genero = None

if rol == "N":
    # MODO NADADOR
    # Usamos normalización robusta también para encontrar al usuario actual
    me = df_nad[df_nad['codnadador'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True) == str(mi_id)]
    
    if not me.empty:
        my_data = me.iloc[0]
        target_categoria = my_data['categoria_actual']
        target_genero = my_data['codgenero']
        
        edad_str = int(my_data['edad_calculada']) if pd.notna(my_data['edad_calculada']) else "-"
        st.info(f"👋 Hola **{mi_nombre}**. Edad: {edad_str} años.")
        st.markdown(f"### 🏷️ Categoría: <span style='color:#E30613'>{target_categoria}</span> ({target_genero})", unsafe_allow_html=True)
    else:
        # Si el usuario logueado es el excluido (66), caerá aquí
        st.error("Perfil no encontrado o acceso restringido para esta sección.")
        st.stop()

elif rol in ["M", "P"]:
    # MODO ENTRENADOR
    st.markdown("<div class='section-title'>🔍 Panel de Control</div>", unsafe_allow_html=True)
    opciones_cat = sorted(df_cat['nombre_cat'].unique().tolist())
    opciones_gen = sorted(df_nad['codgenero'].dropna().unique().tolist())
    
    c1, c2 = st.columns(2)
    target_categoria = c1.selectbox("Categoría", opciones_cat)
    target_genero = c2.selectbox("Género", opciones_gen)

# --- VISUALIZACIÓN ---

if target_categoria and target_genero:
    
    # 1. FILTRAR RIVALES
    rivales = df_nad[
        (df_nad['categoria_actual'] == target_categoria) & 
        (df_nad['codgenero'] == target_genero)
    ].copy()
    
    ids_rivales = rivales['codnadador'].tolist()
    
    # --- MOSTRAR PADRÓN ---
    st.markdown(f"<div class='section-title'>🏊 Padrón ({len(rivales)})</div>", unsafe_allow_html=True)
    
    if not rivales.empty:
        cols = st.columns(2)
        for i, (idx, row) in enumerate(rivales.iterrows()):
            # Comparación robusta para resaltar al usuario
            row_id_str = str(row['codnadador']).strip().replace('.0', '')
            user_id_str = str(mi_id).strip().replace('.0', '')
            es_yo = (row_id_str == user_id_str) if rol == "N" else False
            
            clase = "swimmer-card is-me" if es_yo else "swimmer-card"
            yo_lbl = " (TÚ)" if es_yo else ""
            edad_txt = int(row['edad_calculada']) if pd.notna(row['edad_calculada']) else "-"
            
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

    # --- GRÁFICA COMPARATIVA (PROMEDIOS) ---
    if not rivales.empty:
        st.markdown("<div class='section-title'>📊 Tiempos promedios de la categoría</div>", unsafe_allow_html=True)
        
        # 1. Cargar Tiempos y filtrar
        df_tiempos = db['tiempos'].copy()
        # Filtramos tiempos usando los IDs de rivales (que YA excluyen al 66)
        df_tiempos = df_tiempos[df_tiempos['codnadador'].isin(ids_rivales)]
        
        if not df_tiempos.empty:
            # 2. Unir con Estilos y Distancias
            df_tiempos = df_tiempos.merge(db['estilos'], on='codestilo', how='left')
            df_tiempos = df_tiempos.merge(db['distancias'], on='coddistancia', how='left')
            
            # 3. Filtros Dinámicos
            c_e, c_d = st.columns(2)
            
            estilos_disp = sorted(df_tiempos['descripcion_x'].dropna().unique())
            sel_est = c_e.selectbox("Estilo", estilos_disp)
            
            dist_disp = sorted(df_tiempos[df_tiempos['descripcion_x'] == sel_est]['descripcion_y'].dropna().unique())
            
            sel_dist = None
            if dist_disp:
                sel_dist = c_d.selectbox("Distancia", dist_disp)
            else:
                c_d.warning("Sin distancias.")

            if sel_est and sel_dist:
                # 4. Filtrar datos finales
                data_chart = df_tiempos[
                    (df_tiempos['descripcion_x'] == sel_est) & 
                    (df_tiempos['descripcion_y'] == sel_dist)
                ].copy()
                
                # 5. Procesar tiempos (PROMEDIO)
                data_chart['segundos'] = data_chart['tiempo'].apply(a_segundos)
                data_chart = data_chart[data_chart['segundos'] > 0]
                
                if not data_chart.empty:
                    # Promedio por nadador
                    avg_times = data_chart.groupby('codnadador')['segundos'].mean().reset_index()
                    
                    # Pegar nombres
                    avg_times = avg_times.merge(rivales[['codnadador', 'apellido', 'nombre']], on='codnadador')
                    avg_times['Atleta'] = avg_times['apellido'].str.upper() + " " + avg_times['nombre'].str[0] + "."
                    avg_times['Etiqueta'] = avg_times['segundos'].apply(fmt_mm_ss)
                    
                    # Colores
                    def get_color(cod):
                        c_str = str(cod).strip().replace('.0', '')
                        u_str = str(mi_id).strip().replace('.0', '')
                        if rol == "N" and c_str == u_str: return "#E30613" # Rojo Usuario
                        return "#666666" # Gris Rival
                    
                    avg_times['Color'] = avg_times['codnadador'].apply(get_color)
                    
                    # ORDENAR DE MENOR A MAYOR TIEMPO (El mejor primero)
                    avg_times = avg_times.sort_values('segundos', ascending=True) 
                    
                    # 6. Graficar
                    fig = px.bar(
                        avg_times, 
                        x='Atleta', 
                        y='segundos', 
                        text='Etiqueta', 
                        color='Color', 
                        color_discrete_map="identity"
                    )
                    
                    # Ajuste de Ejes
                    max_y = avg_times['segundos'].max() * 1.15
                    
                    # Forzar ordenamiento visual
                    fig.update_xaxes(categoryorder='array', categoryarray=avg_times['Atleta'])

                    # Texto grande en las barras
                    fig.update_traces(textposition='auto', textfont=dict(size=16), hovertemplate='Promedio: %{text}<extra></extra>')
                    
                    fig.update_layout(
                        height=320, 
                        template="plotly_dark", 
                        showlegend=False,
                        margin=dict(l=0, r=0, t=30, b=0),
                        # EJE Y: Título visible, números ocultos
                        yaxis=dict(title="TIEMPO", showticklabels=False, showgrid=False, range=[0, max_y]),
                        xaxis_title=None
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mensaje de posición
                    if rol == "N":
                        user_id_norm = str(mi_id).strip().replace('.0', '')
                        # Búsqueda robusta en el dataframe de promedios
                        mi_dato = avg_times[avg_times['codnadador'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True) == user_id_norm]
                        
                        if not mi_dato.empty:
                            rank = avg_times.index.get_loc(mi_dato.index[0]) + 1
                            st.success(f"🏅 Tu promedio te ubica **#{rank}** de {len(avg_times)} en {sel_dist} {sel_est}.")
                        else:
                            st.info("Aún no tienes un tiempo oficial registrado para esta prueba.")
                else:
                    st.warning("No se encontraron tiempos válidos para esta selección.")
            else:
                st.info("Selecciona una distancia para ver el ranking.")
        else:
            st.info("Esta categoría aún no tiene tiempos oficiales registrados.")
