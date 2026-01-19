import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Ranking NOB", layout="centered") # Centered es mejor para mobile que Wide
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
    """Convierte tiempo texto a segundos para poder ordenar"""
    try:
        if isinstance(t_str, str):
            partes = t_str.replace('.', ':').split(':')
            if len(partes) == 3: return float(partes[0])*60 + float(partes[1]) + float(partes[2])/100
            elif len(partes) == 2: return float(partes[0]) + float(partes[1])/100
        return 9999.9
    except: return 9999.9

# Unificación de tablas
df_full = data['tiempos'].merge(data['nadadores'], on='codnadador')
df_full = df_full.merge(data['estilos'], on='codestilo')
df_full = df_full.merge(data['distancias'], on='coddistancia')
df_full = df_full.merge(data['piletas'], on='codpileta')

# Nombre legible y segundos
df_full['Nadador'] = df_full['apellido'].str.upper() + ", " + df_full['nombre'].str.title()
df_full['Segundos'] = df_full['tiempo'].apply(tiempo_a_seg)

# --- 4. FILTROS (SIDEBAR) ---
with st.sidebar:
    st.header("Filtros")
    f_gen = st.radio("Género", ["Masculino", "Femenino", "Todos"], index=2)
    
    # Filtro Pileta (Esencial separar 25m de 50m)
    piletas_disp = sorted(df_full['medida'].unique())
    f_pil = st.selectbox("Pileta", piletas_disp, index=0 if piletas_disp else None)
    
    # Filtro Estilo
    estilos_disp = df_full['descripcion_x'].unique()
    f_est = st.selectbox("Estilo", estilos_disp)
    
    # Filtro Distancia (Reactivo al estilo)
    dist_disp = sorted(df_full[df_full['descripcion_x'] == f_est]['descripcion_y'].unique()) if f_est else []
    f_dist = st.selectbox("Distancia", dist_disp)

# --- 5. LÓGICA DE RANKING ---
if f_est and f_dist and f_pil:
    # 1. Filtrar
    df_r = df_full[
        (df_full['descripcion_x'] == f_est) & 
        (df_full['descripcion_y'] == f_dist) & 
        (df_full['medida'] == f_pil)
    ].copy()
    
    if f_gen != "Todos":
        cod_g = "M" if f_gen == "Masculino" else "F"
        df_r = df_r[df_r['codgenero'] == cod_g]

    if not df_r.empty:
        # 2. Personal Best (Mejor tiempo histórico por nadador)
        # Ordenamos por tiempo y quitamos duplicados de nadador (nos quedamos con el mejor)
        df_ranking = df_r.sort_values('Segundos').drop_duplicates(subset=['codnadador'], keep='first')
        df_ranking = df_ranking.reset_index(drop=True)
        df_ranking['Puesto'] = df_ranking.index + 1
        
        # Calcular diferencia con el 1ro para la barra visual
        mejor_tiempo = df_ranking.iloc[0]['Segundos']
        # Invertimos la lógica para la barra de progreso (1.0 es el mejor, el resto baja)
        df_ranking['Rendimiento'] = mejor_tiempo / df_ranking['Segundos'] 

        # --- 6. VISUALIZACIÓN MOBILE FIRST ---
        
        # EL CAMPEÓN (Tarjeta Gigante)
        top1 = df_ranking.iloc[0]
        st.markdown(f"""
        <div style="background-color: #FFD700; padding: 20px; border-radius: 15px; text-align: center; color: black; box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 20px;">
            <div style="font-size: 50px;">🥇</div>
            <div style="font-size: 24px; font-weight: bold;">{top1['tiempo']}</div>
            <div style="font-size: 18px;">{top1['Nadador']}</div>
            <div style="font-size: 12px; opacity: 0.8;">{top1['club']} - {top1['fecha']}</div>
        </div>
        """, unsafe_allow_html=True)

        # SEGUNDO Y TERCERO (Si existen)
        c2, c3 = st.columns(2)
        if len(df_ranking) > 1:
            top2 = df_ranking.iloc[1]
            c2.markdown(f"""
            <div style="background-color: #C0C0C0; padding: 15px; border-radius: 10px; text-align: center; color: black; margin-bottom: 10px;">
                <div style="font-size: 30px;">🥈</div>
                <div style="font-weight: bold; font-size: 18px;">{top2['tiempo']}</div>
                <div style="font-size: 14px;">{top2['Nadador'].split(',')[0]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if len(df_ranking) > 2:
            top3 = df_ranking.iloc[2]
            c3.markdown(f"""
            <div style="background-color: #CD7F32; padding: 15px; border-radius: 10px; text-align: center; color: black; margin-bottom: 10px;">
                <div style="font-size: 30px;">🥉</div>
                <div style="font-weight: bold; font-size: 18px;">{top3['tiempo']}</div>
                <div style="font-size: 14px;">{top3['Nadador'].split(',')[0]}</div>
            </div>
            """, unsafe_allow_html=True)

        # TABLA GENERAL (Mejorada para entender visualmente)
        st.subheader("Clasificación General")
        
        # Configuramos la tabla para que sea interactiva y visual
        st.dataframe(
            df_ranking[['Puesto', 'Nadador', 'tiempo', 'fecha', 'club', 'Rendimiento']],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Puesto": st.column_config.NumberColumn(
                    "#", format="%d", width="small"
                ),
                "Nadador": st.column_config.TextColumn(
                    "Atleta", width="medium"
                ),
                "tiempo": st.column_config.TextColumn(
                    "Marca", width="small"
                ),
                "fecha": st.column_config.DateColumn(
                    "Fecha", format="DD/MM/YY", width="small"
                ),
                "club": "Sede",
                "Rendimiento": st.column_config.ProgressColumn(
                    "Nivel",
                    help="Comparación visual con el primer puesto",
                    format=" ", # Oculta el número, deja solo la barra
                    min_value=0,
                    max_value=1,
                ),
            }
        )
    else:
        st.info("No hay tiempos registrados para esta prueba todavía.")
else:
    st.write("👈 Selecciona los filtros para ver el ranking.")
