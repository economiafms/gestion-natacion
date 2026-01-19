import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Ranking NOB", layout="centered", initial_sidebar_state="collapsed")

# --- 2. SEGURIDAD (SOLO PERFIL M o P) ---
if "role" not in st.session_state or st.session_state.role not in ["M", "P"]:
    st.warning("⚠️ Acceso restringido.")
    st.switch_page("pages/1_inicio.py")

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

# --- UNIFICACIÓN LIMPIA (IGNORANDO 'CLUB' DE TIEMPOS) ---
df = data['tiempos'].copy()

# 1. Eliminar 'club' de Tiempos si existe (para evitar conflictos y 'nan')
if 'club' in df.columns:
    df = df.drop(columns=['club'])

# 2. Merges (Cruces de tablas)
df = df.merge(data['nadadores'], on='codnadador', how='left')
df = df.merge(data['estilos'], on='codestilo', how='left')
df = df.merge(data['distancias'], on='coddistancia', how='left')
# Al hacer merge con piletas, nos trae 'club' (SEDE REAL) y 'medida'
df = df.merge(data['piletas'], on='codpileta', how='left')

# 3. Renombrado y Limpieza
cols_map = {
    'nombre': 'Nombre', 
    'apellido': 'Apellido',
    'descripcion_x': 'Estilo', 
    'descripcion_y': 'Distancia',
    'descripcion': 'Estilo',
    'club': 'sede' # Renombramos explícitamente la columna que vino de Piletas
}
df = df.rename(columns=cols_map)

# 4. Cálculo de campos finales
df['Nadador'] = df['Apellido'].astype(str).str.upper() + ", " + df['Nombre'].astype(str)
df['Segundos'] = df['tiempo'].apply(tiempo_a_seg)
df['Año'] = pd.to_datetime(df['fecha']).dt.year

# Asegurar valores por defecto para que no falle la tarjeta
if 'sede' not in df.columns: df['sede'] = 'Sede desconocida'
if 'medida' not in df.columns: df['medida'] = '-'

# --- 5. FILTROS ---
st.markdown("### 🔍 Filtrar Ranking")

c1, c2, c3 = st.columns(3)

lista_estilos = sorted(df['Estilo'].unique()) if 'Estilo' in df.columns else []
lista_distancias = sorted(df['Distancia'].unique()) if 'Distancia' in df.columns else []
lista_generos = ["Todos"] + sorted(df['codgenero'].unique().tolist()) if 'codgenero' in df.columns else ["Todos"]

idx_estilo = 0
idx_distancia = 0

for i, e in enumerate(lista_estilos):
    if "Libre" in str(e) or "Crol" in str(e): idx_estilo = i; break
for i, d in enumerate(lista_distancias):
    if "50" in str(d): idx_distancia = i; break

with c1: f_estilo = st.selectbox("Estilo", lista_estilos, index=idx_estilo)
with c2: f_distancia = st.selectbox("Distancia", lista_distancias, index=idx_distancia)
with c3: f_genero = st.selectbox("Género", lista_generos)

# Aplicar filtros
if 'Estilo' in df.columns and 'Distancia' in df.columns:
    df_filtrado = df[
        (df['Estilo'] == f_estilo) & 
        (df['Distancia'] == f_distancia)
    ]
else:
    df_filtrado = df.copy()

if f_genero != "Todos":
    df_filtrado = df_filtrado[df_filtrado['codgenero'] == f_genero]

df_ranking = df_filtrado.sort_values('Segundos').head(50).reset_index(drop=True)

# --- 6. VISUALIZACIÓN ---
st.divider()

if df_ranking.empty:
    st.info("No hay registros para esta selección.")
else:
    for i, row in df_ranking.iterrows():
        pos = i + 1
        
        if pos == 1:
            bg_color, text_color, icono = "linear-gradient(90deg, #FFD700 0%, #FDB931 100%)", "black", "🥇"
        elif pos == 2:
            bg_color, text_color, icono = "linear-gradient(90deg, #E0E0E0 0%, #BDBDBD 100%)", "black", "🥈"
        elif pos == 3:
            bg_color, text_color, icono = "linear-gradient(90deg, #D68D5E 0%, #CD7F32 100%)", "black", "🥉"
        else:
            bg_color, text_color, icono = "#262730", "white", f"#{pos}"

        # Usamos .get() para mayor seguridad, aunque la limpieza previa lo garantiza
        medida_val = str(row.get('medida', '-'))
        sede_val = str(row.get('sede', 'Sede desconocida'))
        
        pileta_badge = "25m" if "25" in medida_val else ("50m" if "50" in medida_val else medida_val)

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
                    {sede_val} • {row['Año']} 
                    <span class="tag-pool" style="border: 1px solid {text_color};">{pileta_badge}</span>
                </div>
            </div>
            <div class="rank-time">{row['tiempo']}</div>
        </div>
        """, unsafe_allow_html=True)
