import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Ranking NOB", layout="centered", initial_sidebar_state="collapsed")

# --- 2. SEGURIDAD (SOLO PERFIL M) ---
if "role" not in st.session_state or st.session_state.role not in ["M", "P"]:
    st.warning("⚠️ Acceso restringido.")
    st.switch_page("pages/1_inicio.py") # Expulsar intrusos

st.title("🏆 Ranking Histórico")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. CARGA DE DATOS ---
@st.cache_data(ttl="1h")
def cargar_datos_ranking():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas")
        }
    except: return None

data = cargar_datos_ranking()
if not data: st.stop()

# --- 4. PROCESAMIENTO ---
def tiempo_a_seg(t_str):
    try:
        if isinstance(t_str, str):
            partes = t_str.replace('.', ':').split(':')
            if len(partes) == 3: return float(partes[0])*60 + float(partes[1]) + float(partes[2])/100
            elif len(partes) == 2: return float(partes[0])*60 + float(partes[1])
            else: return float(t_str)
        return float(t_str)
    except: return 999999

# Merge masivo para tener todo en una tabla
df = data['tiempos'].copy()
df = df.merge(data['nadadores'], on='codnadador')
df = df.merge(data['estilos'], on='codestilo')
df = df.merge(data['distancias'], on='coddistancia')
df = df.merge(data['piletas'], on='codpileta')

# Renombrar para claridad
df = df.rename(columns={
    'descripcion_x': 'Estilo', 
    'descripcion_y': 'Distancia',
    'nombre': 'Nombre', 
    'apellido': 'Apellido',
    'descripcion': 'Pileta'
})

df['Nadador'] = df['Apellido'].str.upper() + ", " + df['Nombre']
df['Segundos'] = df['tiempo'].apply(tiempo_a_seg)
df['Año'] = pd.to_datetime(df['fecha']).dt.year

# --- 5. FILTROS ---
st.markdown("### 🔍 Filtrar Ranking")

c1, c2, c3 = st.columns(3)

# Obtener listas únicas ordenadas
lista_estilos = sorted(df['Estilo'].unique())
lista_distancias = sorted(df['Distancia'].unique())
lista_generos = ["Todos"] + sorted(df['codgenero'].unique().tolist())

# --- LÓGICA DE PRESELECCIÓN (CROL 50MTS) ---
idx_estilo = 0
idx_distancia = 0

# Buscar "Libre" o "Crol" en la lista (ajustar según nombre real en tu Excel)
for i, e in enumerate(lista_estilos):
    if "Libre" in e or "Crol" in e: 
        idx_estilo = i; break

# Buscar "50" en la lista de distancias
for i, d in enumerate(lista_distancias):
    if "50" in str(d): 
        idx_distancia = i; break

with c1: f_estilo = st.selectbox("Estilo", lista_estilos, index=idx_estilo)
with c2: f_distancia = st.selectbox("Distancia", lista_distancias, index=idx_distancia)
with c3: f_genero = st.selectbox("Género", lista_generos)

# Aplicar filtros
df_filtrado = df[
    (df['Estilo'] == f_estilo) & 
    (df['Distancia'] == f_distancia)
]

if f_genero != "Todos":
    df_filtrado = df_filtrado[df_filtrado['codgenero'] == f_genero]

# Ordenar por tiempo (menor a mayor) y tomar top
df_ranking = df_filtrado.sort_values('Segundos').head(50).reset_index(drop=True)

# --- 6. VISUALIZACIÓN ---
st.divider()

if df_ranking.empty:
    st.info("No hay registros para esta selección.")
else:
    # Mostrar tarjetas tipo podio
    for i, row in df_ranking.iterrows():
        pos = i + 1
        
        # Colores Podio
        if pos == 1:
            bg_color = "linear-gradient(90deg, #FFD700 0%, #FDB931 100%)" # Oro
            text_color = "black"
            icono = "🥇"
        elif pos == 2:
            bg_color = "linear-gradient(90deg, #E0E0E0 0%, #BDBDBD 100%)" # Plata
            text_color = "black"
            icono = "🥈"
        elif pos == 3:
            bg_color = "linear-gradient(90deg, #D68D5E 0%, #CD7F32 100%)" # Bronce
            text_color = "black"
            icono = "🥉"
        else:
            bg_color = "#262730" # Fondo oscuro estándar
            text_color = "white"
            icono = f"#{pos}"

        # Badge de Pileta (25m o 50m)
        medida_str = str(row['medida']) if 'medida' in row else ""
        pileta_short = "25m" if "25" in medida_str else ("50m" if "50" in medida_str else medida_str)

        st.markdown(f"""
        <style>
            .rank-card {{
                border-radius: 10px;
                padding: 10px 15px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .rank-pos {{ font-size: 24px; font-weight: bold; width: 50px; text-align: center; margin-right: 10px; }}
            .rank-info {{ flex-grow: 1; }}
            .rank-name {{ font-weight: bold; font-size: 16px; margin-bottom: 2px; }}
            .rank-meta {{ font-size: 12px; opacity: 0.8; }}
            .rank-time {{ font-family: monospace; font-weight: bold; font-size: 20px; text-align: right; }}
            .tag-pool {{ 
                font-size: 10px; padding: 2px 6px; border-radius: 4px; 
                margin-left: 8px; font-weight: normal; 
                vertical-align: middle;
            }}
        </style>
        
        <div class="rank-card" style="background: {bg_color}; color: {text_color};">
            <div class="rank-pos">{icono}</div>
            <div class="rank-info">
                <div class="rank-name">{row['Nadador']}</div>
                <div class="rank-meta">
                    {row['club']} • {row['Año']} 
                    <span class="tag-pool" style="border: 1px solid {text_color};">{pileta_short}</span>
                </div>
            </div>
            <div class="rank-time">{row['tiempo']}</div>
        </div>
        """, unsafe_allow_html=True)
