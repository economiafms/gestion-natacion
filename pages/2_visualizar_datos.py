import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Base de Datos", layout="centered")
st.title("📊 Base de Datos del Club")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* TARJETA PADRÓN (Horizontal y Optimizada) */
    .padron-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
    .p-col-left { flex: 2; text-align: left; padding-right: 5px; border-right: 1px solid #444; }
    .p-col-center { flex: 2; text-align: center; padding: 0 5px; }
    .p-col-right { flex: 1; text-align: right; padding-left: 5px; border-left: 1px solid #444; }
    
    .p-name { font-weight: bold; font-size: 15px; color: white; line-height: 1.2; margin-bottom: 4px; }
    .p-meta { font-size: 11px; color: #aaa; }
    .p-medals { font-size: 13px; color: #eee; font-weight: 500; display: flex; justify-content: center; gap: 8px; }
    .p-total { font-size: 22px; color: #FFD700; font-weight: bold; line-height: 1; }
    .p-cat { font-size: 16px; color: #4CAF50; font-weight: bold; margin-top: 2px; }

    /* TARJETA MEJORES MARCAS (Ordenada) */
    .pb-container {
        background-color: #2b2c35;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #1E88E5;
    }
    .pb-style-title { font-weight: bold; color: #fff; margin-bottom: 5px; border-bottom: 1px solid #444; padding-bottom: 2px;}
    .pb-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
    .pb-item { display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0; }
    .pb-dist { color: #ccc; }
    .pb-time { color: #4CAF50; font-weight: bold; font-family: monospace; }

    /* TARJETAS GENERALES Y RELEVOS */
    .mobile-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .relay-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px;
    }
    .relay-title { font-weight: bold; font-size: 15px; color: white; }
    .relay-time { font-family: monospace; font-weight: bold; font-size: 20px; color: #4CAF50; }
    .relay-meta { font-size: 12px; color: #aaa; display: flex; justify-content: space-between; margin-bottom: 10px; }
    .swimmer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; color: #eee; }
    .swimmer-item { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }
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

def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return None
        p = t_str.replace('.', ':').split(':')
        val = float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
        return val
    except: return None

def asignar_cat(edad):
    try:
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

# --- 4. PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])

# ==========================================
# TAB 1: PADRÓN Y MEDALLERO (REDISEÑO HORIZONTAL)
# ==========================================
with tab1:
    st.markdown("### 🏆 Padrón y Medallero")
    
    # Lógica de Medallas (Individual + Relevos)
    df_t_c = data['tiempos'].copy()
    df_t_c['posicion'] = pd.to_numeric(df_t_c['posicion'], errors='coerce').fillna(0).astype(int)
    df_r_c = data['relevos'].copy()
    df_r_c['posicion'] = pd.to_numeric(df_r_c['posicion'], errors='coerce').fillna(0).astype(int)

    med_ind = df_t_c[df_t_c['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    
    dfs_rel_exploded = []
    for i in range(1, 5):
        tmp = df_r_c[['nadador_' + str(i), 'posicion']].rename(columns={'nadador_' + str(i): 'codnadador'})
        dfs_rel_exploded.append(tmp)
    
    if dfs_rel_exploded:
        df_rel_all = pd.concat(dfs_rel_exploded)
        med_rel = df_rel_all[df_rel_all['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    else:
        med_rel = pd.DataFrame()

    medallero = med_ind.add(med_rel, fill_value=0)
    for p in [1, 2, 3]: 
        if p not in medallero.columns: medallero[p] = 0
    medallero = medallero.rename(columns={1: 'Oro', 2: 'Plata', 3: 'Bronce'})
    
    # KPIs Totales
    oros, platas, bronces = int(medallero['Oro'].sum()), int(medallero['Plata'].sum()), int(medallero['Bronce'].sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🥇 Oro", oros); c2.metric("🥈 Plata", platas); c3.metric("🥉 Bronce", bronces); c4.metric("📊 Total", oros+platas+bronces)
    
    st.divider()
    
    # Lista Nadadores
    filtro = st.text_input("Buscar Nadador:", placeholder="Nombre...")
    df_view = df_nad.merge(medallero, left_on='codnadador', right_index=True, how='left').fillna(0)
    df_view['Total'] = df_view['Oro'] + df_view['Plata'] + df_view['Bronce']
    
    if filtro: df_view = df_view[df_view['Nombre Completo'].str.contains(filtro.upper())]
    df_view = df_view.sort_values('Total', ascending=False)

    for _, row in df_view.head(25).iterrows():
        try: edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        o, p, b, t = int(row.get('Oro',0)), int(row.get('Plata',0)), int(row.get('Bronce',0)), int(row.get('Total',0))
        
        st.markdown(f"""
        <div class="padron-card">
            <div class="p-col-left">
                <div class="p-name">{row['Nombre Completo']}</div>
                <div class="p-meta">{edad} años • {row['codgenero']}</div>
            </div>
            <div class="p-col-center">
                <div class="p-medals">
                    <span>🥇{o}</span> <span>🥈{p}</span> <span>🥉{b}</span>
                </div>
            </div>
            <div class="p-col-right">
                <div class="p-total">★ {t}</div>
                <div class="p-cat">{cat}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 2: FICHA TÉCNICA
# ==========================================
with tab2:
    f_nad = st.selectbox("Seleccionar Atleta:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        info = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_n = info['codnadador']
        
        df_full = data['tiempos'].copy()
        df_full = df_full.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        df_full = df_full.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        mis_t = df_full[df_full['codnadador'] == id_n].copy()

        # 1. MEJORES MARCAS (Diseño Limpio y Agrupado)
        if not mis_t.empty:
            st.subheader("✨ Mejores Marcas (PB)")
            mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)
            # Obtenemos solo el mejor tiempo por estilo/distancia
            pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].sort_values(['Estilo', 'segundos'])
            
            # Agrupar por Estilo para mostrar en bloques
            estilos_presentes = pbs['Estilo'].unique()
            
            # Usar columnas para aprovechar ancho
            col_a, col_b = st.columns(2)
            
            for i, estilo in enumerate(estilos_presentes):
                df_e = pbs[pbs['Estilo'] == estilo]
                # Alternar columnas
                with (col_a if i % 2 == 0 else col_b):
                    html_items = ""
                    for _, r in df_e.iterrows():
                        html_items += f"""
                        <div class="pb-item">
                            <span class="pb-dist">{r['Distancia']}</span>
                            <span class="pb-time">{r['tiempo']}</span>
                        </div>
                        """
                    
                    st.markdown(f"""
                    <div class="pb-container">
                        <div class="pb-style-title">{estilo}</div>
                        <div>{html_items}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.divider()

            # 2. GRÁFICO INTELIGENTE (Solo datos válidos)
            st.subheader("📈 Evolución de Tiempos")
            
            # Paso 1: Encontrar combinaciones válidas (>= 2 registros)
            conteo = mis_t.groupby(['Estilo', 'Distancia']).size().reset_index(name='count')
            validos = conteo[conteo['count'] >= 2]
            
            if not validos.empty:
                col_g1, col_g2 = st.columns(2)
                
                # Filtro Estilo: Solo mostrar estilos que están en 'validos'
                estilos_validos = validos['Estilo'].unique()
                g_est = col_g1.selectbox("Estilo", sorted(estilos_validos), key="g_est")
                
                # Filtro Distancia: Solo mostrar distancias válidas para ese estilo
                dist_validas = validos[validos['Estilo'] == g_est]['Distancia'].unique()
                g_dist = col_g2.selectbox("Distancia", sorted(dist_validas), key="g_dist")
                
                # Graficar
                df_graph = mis_t[(mis_t['Estilo'] == g_est) & (mis_t['Distancia'] == g_dist)].sort_values('fecha')
                
                # Eje Y simulado
                df_graph['TimeObj'] = pd.to_datetime('2024-01-01') + pd.to_timedelta(df_graph['segundos'], unit='s')
                
                fig = px.line(df_graph, x='fecha', y='TimeObj', markers=True, template="plotly_dark")
                fig.update_yaxes(tickformat="%M:%S.%f", title="Tiempo") # Formato MM:SS.MS
                fig.update_layout(height=300, margin=dict(t=10, b=10, l=40, r=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tienes suficientes datos históricos (mínimo 2 registros en la misma prueba) para generar gráficos.")

            st.divider()

        # 3. HISTORIAL (Con Filtros)
        st.subheader("📜 Historial Completo")
        with st.expander("Filtrar Historial"):
            h1, h2 = st.columns(2)
            hf_est = h1.selectbox("Estilo", ["Todos"] + sorted(mis_t['Estilo'].unique().tolist()), key="h_est")
            hf_dis = h2.selectbox("Distancia", ["Todos"] + sorted(mis_t['Distancia'].unique().tolist()), key="h_dis")
        
        df_hist = mis_t.copy()
        if hf_est != "Todos": df_hist = df_hist[df_hist['Estilo'] == hf_est]
        if hf_dis != "Todos": df_hist = df_hist[df_hist['Distancia'] == hf_dis]
        df_hist = df_hist.sort_values('fecha', ascending=False)
        
        for _, r in df_hist.head(20).iterrows():
            medal = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else f"#{r['posicion']}"))
            st.markdown(f"""
            <div class="mobile-card" style="padding:10px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:bold; color:white;">{r['Distancia']} {r['Estilo']}</span>
                    <span style="font-family:monospace; font-weight:bold; color:#4CAF50;">{r['tiempo']}</span>
                </div>
                <div style="font-size:12px; color:#aaa; margin-top:5px;">
                    📅 {r['fecha']} • {r['club']} • {medal}
                </div>
            </div>""", unsafe_allow_html=True)

        # 4. MIS RELEVOS (Con Filtros Solicitados)
        st.subheader("🏊‍♂️ Mis Relevos")
        mr_base = data['relevos'].copy()
        cond_rel = (mr_base['nadador_1'] == id_n) | (mr_base['nadador_2'] == id_n) | (mr_base['nadador_3'] == id_n) | (mr_base['nadador_4'] == id_n)
        mis_relevos = mr_base[cond_rel].copy()
        
        if not mis_relevos.empty:
            mis_relevos = mis_relevos.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
            mis_relevos = mis_relevos.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
            
            # Filtros Mis Relevos
            with st.expander("Filtrar Mis Relevos"):
                mr1, mr2 = st.columns(2)
                f_mr_est = mr1.selectbox("Estilo", ["Todos"] + sorted(mis_relevos['Estilo'].unique().tolist()), key="mr_est")
                f_mr_gen = mr2.selectbox("Género", ["Todos"] + sorted(mis_relevos['codgenero'].unique().tolist()), key="mr_gen")
            
            if f_mr_est != "Todos": mis_relevos = mis_relevos[mis_relevos['Estilo'] == f_mr_est]
            if f_mr_gen != "Todos": mis_relevos = mis_relevos[mis_relevos['codgenero'] == f_mr_gen]
            
            mis_relevos = mis_relevos.sort_values('fecha', ascending=False)
            
            for _, r in mis_relevos.iterrows():
                html_grid = ""
                for k in range(1, 5):
                    nid = r[f'nadador_{k}']
                    nom = dict_id_nombre.get(nid, "??").split(',')[0]
                    t = str(r[f'tiempo_{k}']).strip()
                    if t and t not in ["00.00", "0", "None", "nan"]: nom += f" ({t})"
                    html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"
                
                pos_icon = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else ""))
                
                st.markdown(f"""
                <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                    <div class="relay-header">
                        <div class="relay-title">{r['Distancia']} {r['Estilo']} ({r['codgenero']})</div>
                        <div class="relay-time">{r['tiempo_final']}</div>
                    </div>
                    <div class="relay-meta">
                        <span>📅 {r['fecha']} • {r['club']}</span>
                        <span style="font-weight:bold; color:#FFD700;">{pos_icon} Pos: {r['posicion']}</span>
                    </div>
                    <div class="swimmer-grid">{html_grid}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("Sin relevos.")

# ==========================================
# TAB 3: TODOS LOS RELEVOS (Cerrada - Versión Final)
# ==========================================
with tab3:
    st.markdown("### Historial de Postas")
    mr_all = data['relevos'].copy()
    if not mr_all.empty:
        mr_all = mr_all.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mr_all = mr_all.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})

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
                if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"
            
            medal = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else ""))
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #9C27B0;">
                <div class="relay-header">
                    <div class="relay-title">{r['Distancia']} {r['Estilo']} ({r['codgenero']})</div>
                    <div class="relay-time">{r['tiempo_final']}</div>
                </div>
                <div class="relay-meta">
                    <span>📅 {r['fecha']} • {r['club']}</span>
                    <span style="font-weight:bold; color:#FFD700;">{medal} Pos: {r['posicion']}</span>
                </div>
                <div class="swimmer-grid">{html_grid}</div>
            </div>""", unsafe_allow_html=True)
