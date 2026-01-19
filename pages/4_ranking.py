import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Ranking NOB", layout="centered", initial_sidebar_state="collapsed")
st.title("🏆 Ranking Histórico")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
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

# --- 3. PROCESAMIENTO ---
def tiempo_a_seg(t_str):
    try:
        if isinstance(t_str, str):
            partes = t_str.replace('.', ':').split(':')
            if len(partes) == 3: return float(partes[0])*60 + float(partes[1]) + float(partes[2])/100
            elif len(partes) == 2: return float(partes[0]) + float(partes[1])/100
        return 9999.9
    except: return 9999.9

# Unificación
df_full = data['tiempos'].merge(data['nadadores'], on='codnadador')
df_full = df_full.merge(data['estilos'], on='codestilo')
df_full = df_full.merge(data['distancias'], on='coddistancia')
df_full = df_full.merge(data['piletas'], on='codpileta')

# Campos clave
df_full['Nadador'] = df_full['apellido'].str.upper() + " " + df_full['nombre'].str.title()
df_full['Segundos'] = df_full['tiempo'].apply(tiempo_a_seg)
df_full['Año'] = pd.to_datetime(df_full['fecha']).dt.year

# --- 4. FILTROS (SIN MEDIDA DE PILETA) ---
# Usamos columnas arriba para que sea fácil filtrar en móvil
with st.container(border=True):
    st.subheader("🔍 Filtros de Prueba")
    c1, c2 = st.columns(2)
    f_est = c1.selectbox("Estilo", df_full['descripcion_x'].unique(), index=0)
    
    # Distancias disponibles para ese estilo
    dist_disp = sorted(df_full[df_full['descripcion_x'] == f_est]['descripcion_y'].unique())
    f_dist = c2.selectbox("Distancia", dist_disp, index=0 if dist_disp else None)
    
    f_gen = st.radio("Género", ["Todos", "Masculino", "Femenino"], horizontal=True)

# --- 5. LÓGICA Y VISUALIZACIÓN ---
if f_est and f_dist:
    # Filtrado
    df_r = df_full[
        (df_full['descripcion_x'] == f_est) & 
        (df_full['descripcion_y'] == f_dist)
    ].copy()
    
    if f_gen != "Todos":
        cod_g = "M" if f_gen == "Masculino" else "F"
        df_r = df_r[df_r['codgenero'] == cod_g]

    if not df_r.empty:
        # Ranking: Mejor tiempo por nadador (Personal Best)
        df_ranking = df_r.sort_values('Segundos').drop_duplicates(subset=['codnadador'], keep='first')
        df_ranking = df_ranking.reset_index(drop=True)
        
        # --- ESTILOS CSS PERSONALIZADOS ---
        # Definimos tarjetas con CSS para que se vean lindas en cualquier celu
        st.markdown("""
        <style>
            .rank-card {
                padding: 15px;
                border-radius: 12px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .rank-pos {
                font-size: 24px;
                font-weight: bold;
                width: 40px;
                text-align: center;
            }
            .rank-info {
                flex-grow: 1;
                padding-left: 15px;
            }
            .rank-name {
                font-weight: bold;
                font-size: 16px;
                margin-bottom: 2px;
            }
            .rank-meta {
                font-size: 12px;
                opacity: 0.8;
            }
            .rank-time {
                text-align: right;
                font-family: monospace;
                font-weight: bold;
                font-size: 18px;
            }
            .tag-pool {
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 4px;
                background-color: rgba(255,255,255,0.2);
                margin-left: 5px;
            }
        </style>
        """, unsafe_allow_html=True)

        st.write("") # Espaciador

        # --- ITERADOR DE TARJETAS ---
        for i, row in df_ranking.iterrows():
            pos = i + 1
            
            # Colores según posición
            if pos == 1:
                bg_color = "linear-gradient(90deg, #FDB931 0%, #FFD700 100%)" # Oro
                text_color = "black"
                icono = "🥇"
            elif pos == 2:
                bg_color = "linear-gradient(90deg, #DEE1E6 0%, #C0C0C0 100%)" # Plata
                text_color = "black"
                icono = "🥈"
            elif pos == 3:
                bg_color = "linear-gradient(90deg, #D68D5E 0%, #CD7F32 100%)" # Bronce
                text_color = "black"
                icono = "🥉"
            else:
                bg_color = "#262730" # Fondo oscuro estándar de Streamlit (o gris si es light mode)
                text_color = "white"
                icono = f"#{pos}"

            # Badge de Pileta (25m o 50m)
            pileta_short = "25m" if "25" in str(row['medida']) else ("50m" if "50" in str(row['medida']) else row['medida'])

            # Renderizado HTML de la Tarjeta
            html_card = f"""
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
            """
            st.markdown(html_card, unsafe_allow_html=True)

    else:
        st.info("No se encontraron registros.")
else:
    st.warning("Selecciona Estilo y Distancia.")
