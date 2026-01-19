import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Ranking - NOB", layout="wide")
st.title("🏆 Ranking de Mejores Nadadores")
st.markdown("Visualizá los mejores tiempos históricos del equipo filtrando por prueba.")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="1h")
def cargar_datos_ranking():
    try:
        data = {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas")
        }
        return data
    except Exception as e:
        st.error(f"Error al conectar con GSheets: {e}")
        return None

data = cargar_datos_ranking()
if not data: st.stop()

# --- 3. PRE-PROCESAMIENTO ---
def tiempo_a_seg(t_str):
    """Convierte mm:ss.cc a segundos para graficar."""
    try:
        if isinstance(t_str, str):
            partes = t_str.replace('.', ':').split(':')
            if len(partes) == 3:
                return float(partes[0]) * 60 + float(partes[1]) + float(partes[2])/100
            elif len(partes) == 2: # Caso ss.cc
                return float(partes[0]) + float(partes[1])/100
        return 999.0
    except: return 999.0

# Preparamos el DataFrame Maestro
df_t = data['tiempos'].copy()
df_n = data['nadadores'].copy()
df_e = data['estilos'].copy()
df_d = data['distancias'].copy()
df_p = data['piletas'].copy()

# Crear Nombre Completo
df_n['Nadador'] = df_n['apellido'].astype(str).str.upper() + ", " + df_n['nombre'].astype(str)

# Merges (Unir todas las tablas en una sola para filtrar fácil)
df_full = df_t.merge(df_n, on='codnadador', how='left')
df_full = df_full.merge(df_e, on='codestilo', how='left', suffixes=('', '_est'))
df_full = df_full.merge(df_d, on='coddistancia', how='left', suffixes=('', '_dist'))
df_full = df_full.merge(df_p, on='codpileta', how='left', suffixes=('', '_pil'))

# Calcular segundos para ordenamiento
df_full['Segundos'] = df_full['tiempo'].apply(tiempo_a_seg)
df_full['Año'] = pd.to_datetime(df_full['fecha']).dt.year

# Renombrar columnas para claridad
df_full.rename(columns={
    'descripcion': 'Estilo', 
    'descripcion_dist': 'Distancia',
    'medida': 'Pileta',
    'club': 'Sede'
}, inplace=True)

# --- 4. FILTROS LATERALES ---
with st.sidebar:
    st.header("🔍 Filtros de Ranking")
    
    # Filtro Género
    f_gen = st.radio("Género", ["Masculino", "Femenino", "Todos"], index=0)
    map_gen = {"Masculino": "M", "Femenino": "F"}
    
    # Filtro Pileta (Importante: 25m vs 50m son tiempos distintos)
    opt_pil = sorted(df_full['Pileta'].dropna().unique())
    f_pil = st.selectbox("Tamaño de Pileta", opt_pil, index=0 if opt_pil else None)
    
    # Filtro Estilo
    opt_est = df_full['Estilo'].dropna().unique()
    f_est = st.selectbox("Estilo", opt_est, index=0 if len(opt_est)>0 else None)
    
    # Filtro Distancia
    # Filtramos distancias disponibles para ese estilo para que sea reactivo
    dist_disponibles = df_full[df_full['Estilo'] == f_est]['Distancia'].unique() if f_est else []
    f_dist = st.selectbox("Distancia", sorted(dist_disponibles), index=0 if len(dist_disponibles)>0 else None)

    top_n = st.slider("Mostrar Top", 5, 50, 10)

# --- 5. LÓGICA DE FILTRADO Y MEJORES MARCAS ---
if f_est and f_dist and f_pil:
    # 1. Filtrar base
    df_filtrado = df_full[
        (df_full['Estilo'] == f_est) & 
        (df_full['Distancia'] == f_dist) & 
        (df_full['Pileta'] == f_pil)
    ]
    
    # 2. Filtrar género
    if f_gen != "Todos":
        df_filtrado = df_filtrado[df_filtrado['codgenero'] == map_gen[f_gen]]

    # 3. OBTENER PERSONAL BEST (PB)
    # Agrupamos por nadador y nos quedamos con el tiempo mínimo (el más rápido)
    # idx_min obtendrá los índices de las filas con el tiempo mínimo
    if not df_filtrado.empty:
        idx_min = df_filtrado.groupby('codnadador')['Segundos'].idxmin()
        df_ranking = df_filtrado.loc[idx_min].sort_values('Segundos').head(top_n).reset_index(drop=True)
        
        # Agregamos columna de Puesto
        df_ranking.index = df_ranking.index + 1
        df_ranking['Puesto'] = df_ranking.index

        # --- 6. VISUALIZACIÓN ---
        
        # Tarjetas de Podio
        if len(df_ranking) >= 3:
            c1, c2, c3 = st.columns(3)
            c2.metric("🥇 1er Puesto", f"{df_ranking.iloc[0]['Nadador']}", f"{df_ranking.iloc[0]['tiempo']}")
            c1.metric("🥈 2do Puesto", f"{df_ranking.iloc[1]['Nadador']}", f"{df_ranking.iloc[1]['tiempo']}")
            c3.metric("🥉 3er Puesto", f"{df_ranking.iloc[2]['Nadador']}", f"{df_ranking.iloc[2]['tiempo']}")
            st.divider()

        # Gráfico de Barras con Altair
        st.subheader(f"📊 Gráfico: {f_dist} {f_est} ({f_pil})")
        
        chart = alt.Chart(df_ranking).mark_bar().encode(
            x=alt.X('Segundos', title='Segundos', scale=alt.Scale(zero=False)), # Zero=False para resaltar diferencias
            y=alt.Y('Nadador', sort='x', title=''),
            color=alt.Color('Segundos', legend=None, scale=alt.Scale(scheme='teals')),
            tooltip=['Nadador', 'tiempo', 'fecha', 'Sede']
        ).properties(height=400)
        
        text = chart.mark_text(
            align='left',
            baseline='middle',
            dx=3,
            color='white' 
        ).encode(
            text='tiempo'
        )

        st.altair_chart(chart + text, use_container_width=True)

        # Tabla de Datos
        st.subheader("📝 Tabla de Posiciones")
        st.dataframe(
            df_ranking[['Puesto', 'Nadador', 'tiempo', 'fecha', 'Sede']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay tiempos registrados con estos filtros.")
else:
    st.warning("Selecciona los filtros en la barra lateral para ver el ranking.")
