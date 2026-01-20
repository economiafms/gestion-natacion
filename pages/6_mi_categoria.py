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

st.title("🏆 Mi Categoría")

# --- ESTILOS CSS ---
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
        align-items: center;
        justify-content: space-between;
    }
    .swimmer-card.is-me {
        border-left: 5px solid #E30613; /* Rojo para el usuario actual */
        background-color: #2b1e1e;
    }
    .card-name { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .card-sub { font-size: 13px; color: #aaa; }
    .card-stat { font-size: 14px; color: #E30613; font-weight: bold; }
    
    .section-title { 
        color: #E30613; 
        font-weight: bold; 
        margin-top: 25px; 
        margin-bottom: 15px; 
        border-bottom: 1px solid #444; 
        font-size: 16px; 
        text-transform: uppercase; 
    }
    
    .empty-msg {
        text-align: center;
        padding: 30px;
        background: #1e1e1e;
        border-radius: 10px;
        color: #888;
        border: 1px dashed #444;
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

# --- LÓGICA DE CATEGORÍAS ---
def calcular_categoria_master(fecha_nac):
    if pd.isna(fecha_nac): return "S/D", 0
    try:
        nac = pd.to_datetime(fecha_nac)
        hoy = date.today()
        # Edad al 31 de diciembre del año actual (Regla FINA/Masters)
        edad = hoy.year - nac.year
        
        if edad < 20: return "JUVENIL", edad
        elif 20 <= edad <= 24: return "PRE-MASTER", edad
        else:
            # Bloques de 5 años: 25-29, 30-34, etc.
            base = int((edad - 25) / 5)
            letra = chr(65 + base) # A, B, C...
            inicio = 25 + (base * 5)
            fin = inicio + 4
            return f"MASTER {letra} ({inicio}-{fin})", edad
    except: return "ERROR", 0

# Helper Tiempo
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

# --- SELECCIÓN DE USUARIO (Si es admin, elige a quién analizar) ---
df_nad = db['nadadores'].copy()
id_analisis = mi_id

if rol in ["M", "P"]:
    lista_noms = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
    sel_nom = st.selectbox("Ver categoría de:", lista_noms, index=None, placeholder="Selecciona un nadador...")
    if sel_nom:
        id_analisis = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel_nom].iloc[0]['codnadador']
    else:
        st.info("Selecciona un nadador para ver su análisis de categoría.")
        st.stop()

# --- OBTENER DATOS DEL NADADOR ---
me_row = df_nad[df_nad['codnadador'].astype(str) == str(id_analisis)].iloc[0]
mi_genero = me_row.get('genero', 'M') # Asume columna 'genero' (M/F)
mi_cat_nombre, mi_edad = calcular_categoria_master(me_row.get('fecha_nacimiento'))

st.markdown(f"### 🏷️ Categoría: <span style='color:#E30613'>{mi_cat_nombre}</span> ({mi_genero})", unsafe_allow_html=True)

# --- FILTRAR RIVALES ---
# Calcular categorías para todos y filtrar
df_nad['cat_info'] = df_nad['fecha_nacimiento'].apply(calcular_categoria_master)
df_nad['categoria_str'] = df_nad['cat_info'].apply(lambda x: x[0])

# Filtrar: Misma categoría y mismo género
rivales = df_nad[
    (df_nad['categoria_str'] == mi_cat_nombre) & 
    (df_nad['genero'] == mi_genero)
].copy()

# IDs de todos los nadadores en la categoría (incluyéndome)
ids_categoria = rivales['codnadador'].tolist()

# --- MOSTRAR CARDS ---
st.markdown("<div class='section-title'>🏊 Nadadores en esta categoría</div>", unsafe_allow_html=True)

if len(rivales) > 1:
    cols = st.columns(2) # Grid de cards
    for idx, (_, r) in enumerate(rivales.iterrows()):
        es_yo = str(r['codnadador']) == str(id_analisis)
        clase = "swimmer-card is-me" if es_yo else "swimmer-card"
        yo_tag = " (TÚ)" if es_yo else ""
        nombre_completo = f"{r['apellido'].upper()}, {r['nombre']}"
        
        with cols[idx % 2]:
            st.markdown(f"""
            <div class="{clase}">
                <div>
                    <div class="card-name">{nombre_completo} {yo_tag}</div>
                    <div class="card-sub">Edad: {r['cat_info'][1]} años</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class='empty-msg'>
        🏁 <b>Eres el único nadador registrado en la categoría {mi_cat_nombre}.</b><br>
        ¡Tienes el camino libre para establecer todos los récords!
    </div>
    """, unsafe_allow_html=True)

# --- COMPARATIVA DE RENDIMIENTO ---
st.markdown("<div class='section-title'>📊 Comparativa de Tiempos</div>", unsafe_allow_html=True)

# 1. Traer entrenamientos de TODA la categoría
df_ent = db['entrenamientos'][db['entrenamientos']['codnadador'].isin(ids_categoria)].copy()

if not df_ent.empty:
    df_ent = df_ent.merge(db['estilos'], on='codestilo').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia')
    
    # 2. Filtros Dinámicos (Solo lo que la categoría ha nadado)
    estilos_disp = sorted(df_ent['descripcion_x'].unique())
    c1, c2 = st.columns(2)
    f_estilo = c1.selectbox("Estilo", estilos_disp)
    
    # Filtrar distancias disponibles para ese estilo en esta categoría
    distancias_disp = sorted(df_ent[df_ent['descripcion_x'] == f_estilo]['descripcion_y'].unique())
    
    if distancias_disp:
        f_dist = c2.selectbox("Distancia", distancias_disp)
        
        # 3. Preparar Datos para Gráfico
        df_chart = df_ent[
            (df_ent['descripcion_x'] == f_estilo) & 
            (df_ent['descripcion_y'] == f_dist)
        ].copy()
        
        if not df_chart.empty:
            # Tomar el mejor tiempo de cada nadador para esa prueba
            df_chart['segundos'] = df_chart['tiempo_final'].apply(a_segundos)
            df_best = df_chart.groupby('codnadador')['segundos'].min().reset_index()
            
            # Pegar nombres
            df_best = df_best.merge(rivales[['codnadador', 'nombre', 'apellido']], on='codnadador')
            df_best['Nombre'] = df_best['apellido'].str.upper() + ", " + df_best['nombre']
            df_best['Tiempo'] = df_best['segundos'].apply(fmt_mm_ss)
            
            # Colores: Rojo para Mí, Gris para Rivales
            df_best['Color'] = df_best['codnadador'].apply(lambda x: '#E30613' if str(x) == str(id_analisis) else '#888888')
            
            # Ordenar: El más rápido primero (menor tiempo)
            df_best = df_best.sort_values('segundos', ascending=True)

            # Gráfico
            fig = px.bar(
                df_best, 
                x='Nombre', 
                y='segundos', 
                text='Tiempo',
                color='Color',
                color_discrete_map="identity", # Usa los colores definidos en la columna
                title=f"Ranking: {f_dist} {f_estilo}"
            )
            
            fig.update_traces(textposition='auto', hovertemplate='%{x}<br>⏱️ %{text}<extra></extra>')
            
            # Limpiar Ejes
            min_val = df_best['segundos'].min() * 0.9 # Un poco de aire abajo
            max_val = df_best['segundos'].max() * 1.1
            
            # Crear ticks legibles
            tick_vals = np.linspace(min_val, max_val, 5)
            tick_text = [fmt_mm_ss(v) for v in tick_vals]

            fig.update_layout(
                template="plotly_dark",
                showlegend=False,
                height=350,
                xaxis_title=None,
                yaxis=dict(title="Tiempo", tickmode='array', tickvals=tick_vals, ticktext=tick_text, range=[0, max_val])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Mensaje de análisis
            mi_tiempo = df_best[df_best['codnadador'].astype(str) == str(id_analisis)]
            if not mi_tiempo.empty:
                pos = df_best.index.get_loc(mi_tiempo.index[0]) + 1
                total = len(df_best)
                st.caption(f"🏅 Te ubicas en la posición **{pos} de {total}** en esta prueba dentro de tu categoría.")
            else:
                st.warning(f"⚠️ Aún no tienes registros en {f_dist} {f_estilo}. ¡Es una oportunidad para sumar puntos!")
                
        else:
            st.info("Nadie en tu categoría ha registrado tiempos para esta prueba aún.")
    else:
        st.warning(f"No hay registros de {f_estilo} en ninguna distancia para esta categoría.")
else:
    st.info("⚠️ Aún no hay registros de entrenamiento cargados para los nadadores de esta categoría.")
