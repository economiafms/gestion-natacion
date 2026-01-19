import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Base de Datos", layout="centered")
st.title("📊 Base de Datos del Club")

# --- CSS PERSONALIZADO (Mobile & Clean) ---
st.markdown("""
<style>
    /* Tarjeta General */
    .mobile-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    /* Estilos para Relevos */
    .relay-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px;
    }
    .relay-title { font-weight: bold; font-size: 15px; color: white; }
    .relay-time { font-family: monospace; font-weight: bold; font-size: 20px; color: #4CAF50; }
    .relay-meta { font-size: 12px; color: #aaa; display: flex; justify-content: space-between; margin-bottom: 10px; }
    .swimmer-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        font-size: 13px;
        color: #eee;
    }
    .swimmer-item { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }
    
    /* Medallas */
    .medal-row { font-size: 14px; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_visualizacion():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "categorias": conn.read(worksheet="Categorias"),
        }
    except Exception as e: return None

data = cargar_visualizacion()
if not data: st.stop()

# --- 3. PROCESAMIENTO GLOBAL ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
dict_id_nac = pd.to_datetime(df_nad.set_index('codnadador')['fechanac']).to_dict()

# Función auxiliar de tiempo
def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return None
        p = t_str.replace('.', ':').split(':')
        val = float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
        return val
    except: return None

# Función categoría
def asignar_cat(edad):
    try:
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

# --- 4. PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])

# ==========================================
# TAB 1: PADRÓN (Medallas Recuperadas)
# ==========================================
with tab1:
    st.markdown("### 🏆 Padrón y Medallero")
    
    # 1. LÓGICA DE MEDALLAS (INDIVIDUAL + RELEVOS)
    df_t_c = data['tiempos'].copy()
    df_t_c['posicion'] = pd.to_numeric(df_t_c['posicion'], errors='coerce').fillna(0)
    
    df_r_c = data['relevos'].copy()
    df_r_c['posicion'] = pd.to_numeric(df_r_c['posicion'], errors='coerce').fillna(0)

    # Medallas individuales
    med_ind = df_t_c[df_t_c['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    
    # Medallas Relevos (Hay que contar para CADA nadador del equipo)
    dfs_rel_exploded = []
    for i in range(1, 5):
        tmp = df_r_c[['nadador_' + str(i), 'posicion']].rename(columns={'nadador_' + str(i): 'codnadador'})
        dfs_rel_exploded.append(tmp)
    df_rel_all = pd.concat(dfs_rel_exploded)
    med_rel = df_rel_all[df_rel_all['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    
    # Suma Total
    medallero = med_ind.add(med_rel, fill_value=0)
    for p in [1, 2, 3]: 
        if p not in medallero.columns: medallero[p] = 0
    
    # Unir al padrón para visualizar
    df_view = df_nad.merge(medallero, left_on='codnadador', right_index=True, how='left').fillna(0)
    df_view['Total'] = df_view[1] + df_view[2] + df_view[3]
    
    # Buscador
    filtro = st.text_input("Buscar Nadador:", placeholder="Nombre...")
    if filtro: df_view = df_view[df_view['Nombre Completo'].str.contains(filtro.upper())]
    
    df_view = df_view.sort_values('Total', ascending=False)

    # Renderizado Tarjetas
    for _, row in df_view.head(20).iterrows():
        try: edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        
        st.markdown(f"""
        <div class="mobile-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:bold; font-size:16px; color:white;">{row['Nombre Completo']}</span>
                <span style="font-size:14px; font-weight:bold; color:#FFD700;">★ {int(row['Total'])}</span>
            </div>
            <div style="font-size:12px; color:#aaa;">{edad} años ({cat}) • {row['codgenero']}</div>
            <div class="medal-row">
                🥇 <span style="color:#fff">{int(row[1])}</span> &nbsp; 
                🥈 <span style="color:#fff">{int(row[2])}</span> &nbsp; 
                🥉 <span style="color:#fff">{int(row[3])}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 2: FICHA TÉCNICA
# ==========================================
with tab2:
    f_nad = st.selectbox("Seleccionar Atleta:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        # Info Básica
        info = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_n = info['codnadador']
        
        # DataFrame Completo
        df_full = data['tiempos'].copy()
        df_full = df_full.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        df_full = df_full.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        mis_t = df_full[df_full['codnadador'] == id_n].copy()

        # 1. MEJORES MARCAS (PB)
        if not mis_t.empty:
            st.subheader("✨ Mejores Marcas")
            mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)
            # PB Logic
            pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].sort_values(['Estilo', 'Distancia'])
            
            # Mostrar PBs compactos
            for _, r in pbs.iterrows():
                st.markdown(f"""
                <div style="background:#333; padding:8px; border-radius:5px; margin-bottom:5px; display:flex; justify-content:space-between;">
                    <span style="color:#ddd;">{r['Distancia']} {r['Estilo']}</span>
                    <span style="color:#4CAF50; font-weight:bold;">{r['tiempo']}</span>
                </div>""", unsafe_allow_html=True)
            
            st.divider()

            # 2. GRÁFICO DE PROGRESIÓN (Con Filtros y Formato MM:SS)
            st.subheader("📈 Evolución")
            c1, c2 = st.columns(2)
            g_est = c1.selectbox("Estilo", mis_t['Estilo'].unique(), key="g_est")
            # Filtrar distancias disponibles para ese estilo
            dist_disp = mis_t[mis_t['Estilo'] == g_est]['Distancia'].unique()
            g_dist = c2.selectbox("Distancia", dist_disp, key="g_dist")
            
            # Datos para el gráfico
            df_graph = mis_t[(mis_t['Estilo'] == g_est) & (mis_t['Distancia'] == g_dist)].sort_values('fecha')
            
            if len(df_graph) >= 2:
                # Truco para formato de tiempo en eje Y: Usar datetime arbitrario
                # Sumamos los segundos a una fecha base (ej: 2024-01-01 00:00:00)
                df_graph['TimeObj'] = pd.to_datetime('2024-01-01') + pd.to_timedelta(df_graph['segundos'], unit='s')
                
                fig = px.line(df_graph, x='fecha', y='TimeObj', markers=True, 
                              template="plotly_dark")
                
                # Formatear eje Y para mostrar solo Minutos:Segundos.Centésimas
                fig.update_yaxes(tickformat="%M:%S.%f", title="Tiempo")
                fig.update_xaxes(title="Fecha")
                fig.update_layout(height=300, margin=dict(t=20, b=20, l=40, r=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Se necesitan al menos 2 registros en esta prueba para graficar.")
            
            st.divider()

        # 3. HISTORIAL COMPLETO (Con Filtros)
        st.subheader("📜 Historial de Carreras")
        with st.expander("Filtrar Historial"):
            h1, h2 = st.columns(2)
            hf_est = h1.selectbox("Filtrar Estilo", ["Todos"] + sorted(mis_t['Estilo'].unique().tolist()), key="h_est")
            hf_dis = h2.selectbox("Filtrar Distancia", ["Todos"] + sorted(mis_t['Distancia'].unique().tolist()), key="h_dis")
        
        df_hist = mis_t.copy()
        if hf_est != "Todos": df_hist = df_hist[df_hist['Estilo'] == hf_est]
        if hf_dis != "Todos": df_hist = df_hist[df_hist['Distancia'] == hf_dis]
        
        df_hist = df_hist.sort_values('fecha', ascending=False)
        
        for _, r in df_hist.head(20).iterrows():
            pos_icon = f"Pos: {r['posicion']}"
            if r['posicion'] == 1: pos_icon = "🥇 1er Puesto"
            elif r['posicion'] == 2: pos_icon = "🥈 2do Puesto"
            elif r['posicion'] == 3: pos_icon = "🥉 3er Puesto"

            st.markdown(f"""
            <div class="mobile-card">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:bold; color:white;">{r['Distancia']} {r['Estilo']}</span>
                    <span style="font-family:monospace; font-weight:bold; color:#4CAF50;">{r['tiempo']}</span>
                </div>
                <div style="font-size:12px; color:#aaa; margin-top:5px;">
                    📅 {r['fecha']} • {r['club']} • {pos_icon}
                </div>
            </div>""", unsafe_allow_html=True)

        # 4. MIS RELEVOS (Recuperado y Filtrado)
        st.subheader("🏊‍♂️ Mis Relevos")
        mr_base = data['relevos'].copy()
        # Filtrar donde aparece el nadador
        cond_rel = (mr_base['nadador_1'] == id_n) | (mr_base['nadador_2'] == id_n) | \
                   (mr_base['nadador_3'] == id_n) | (mr_base['nadador_4'] == id_n)
        mis_relevos = mr_base[cond_rel].copy()
        
        if not mis_relevos.empty:
            mis_relevos = mis_relevos.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
            mis_relevos = mis_relevos.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
            mis_relevos = mis_relevos.sort_values('fecha', ascending=False)
            
            for _, r in mis_relevos.iterrows():
                # Renderizar tarjeta de relevo
                # Construir Grid de Nadadores
                html_grid = ""
                for k in range(1, 5):
                    nid = r[f'nadador_{k}']
                    nom = dict_id_nombre.get(nid, "??").split(',')[0] # Solo apellido
                    t = str(r[f'tiempo_{k}']).strip()
                    # Mostrar parcial solo si existe y no es 0
                    if t and t not in ["00.00", "0", "None", "nan"]:
                        nom += f" ({t})"
                    html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"
                
                pos_icon = f"Pos: {r['posicion']}"
                if r['posicion'] == 1: pos_icon = "🥇 1ro"
                elif r['posicion'] == 2: pos_icon = "🥈 2do"
                elif r['posicion'] == 3: pos_icon = "🥉 3ro"

                st.markdown(f"""
                <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                    <div class="relay-header">
                        <div class="relay-title">{r['Distancia']} {r['Estilo']}</div>
                        <div class="relay-time">{r['tiempo_final']}</div>
                    </div>
                    <div class="relay-meta">
                        <span>📅 {r['fecha']} • {r['club']}</span>
                        <span style="color:#FFD700;">{pos_icon}</span>
                    </div>
                    <div class="swimmer-grid">
                        {html_grid}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No ha participado en relevos aún.")

# ==========================================
# TAB 3: TODOS LOS RELEVOS (General)
# ==========================================
with tab3:
    st.markdown("### Historial de Postas")
    
    mr_all = data['relevos'].copy()
    if not mr_all.empty:
        mr_all = mr_all.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mr_all = mr_all.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})

        # Filtros Globales
        c1, c2 = st.columns(2)
        fg_est = c1.selectbox("Estilo", ["Todos"] + sorted(mr_all['Estilo'].unique().tolist()), key="fg_est")
        fg_gen = c2.selectbox("Género", ["Todos", "M", "F", "X"], key="fg_gen")
        
        if fg_est != "Todos": mr_all = mr_all[mr_all['Estilo'] == fg_est]
        if fg_gen != "Todos": mr_all = mr_all[mr_all['codgenero'] == fg_gen]
        
        mr_all = mr_all.sort_values('fecha', ascending=False)
        
        for _, r in mr_all.head(20).iterrows():
            html_grid = ""
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]:
                    nom += f" <b>({t})</b>"
                html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"
            
            medal_icon = ""
            if r['posicion'] == 1: medal_icon = "🥇"
            elif r['posicion'] == 2: medal_icon = "🥈"
            elif r['posicion'] == 3: medal_icon = "🥉"

            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #9C27B0;">
                <div class="relay-header">
                    <div class="relay-title">{r['Distancia']} {r['Estilo']} ({r['codgenero']})</div>
                    <div class="relay-time">{r['tiempo_final']}</div>
                </div>
                <div class="relay-meta">
                    <span>📅 {r['fecha']} • {r['club']}</span>
                    <span style="font-weight:bold; color:#FFD700;">{medal_icon} Pos: {r['posicion']}</span>
                </div>
                <div class="swimmer-grid">
                    {html_grid}
                </div>
            </div>
            """, unsafe_allow_html=True)
