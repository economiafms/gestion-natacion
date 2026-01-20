import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Base de Datos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Acceso denegado. Por favor, inicia sesión desde el Inicio.")
    st.stop()

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

st.title("📊 Base de Datos del Club")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* TARJETAS GENERALES Y PADRÓN */
    .padron-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 5px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    }
    .p-col-left { flex: 2; text-align: left; border-right: 1px solid #555; padding-right: 10px; }
    .p-col-center { flex: 2; text-align: center; padding: 0 10px; }
    .p-col-right { flex: 1; text-align: right; padding-left: 10px; border-left: 1px solid #555; }
    .p-name { font-weight: bold; font-size: 18px; color: white; margin-bottom: 5px; }
    .p-meta { font-size: 13px; color: #ccc; }
    .p-medals { font-size: 16px; display: flex; justify-content: center; gap: 10px; margin-top: 5px;}
    .p-total { font-size: 28px; color: #FFD700; font-weight: bold; line-height: 1; }
    .p-cat { font-size: 18px; color: #4CAF50; font-weight: bold; margin-top: 5px; }

    /* ESTILOS FICHA */
    .ficha-header {
        background: linear-gradient(135deg, #8B0000 0%, #3E0000 100%);
        padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;
        border: 1px solid #550000; box-shadow: 0 4px 6px rgba(0,0,0,0.4);
    }
    .ficha-name { font-size: 24px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 10px; margin-bottom: 10px; }
    .ficha-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; }
    .ficha-medals { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; text-align: center; margin-top: 15px; font-size: 18px; }

    /* ESTILOS NUEVA CARD (CENTRADOS) */
    .mobile-card { 
        background-color: #262730; 
        border: 1px solid #444; 
        border-radius: 10px; 
        padding: 0; /* Padding controlado por hijos */
        margin-bottom: 12px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.3); 
        overflow: hidden;
    }
    
    .card-header-center {
        background-color: rgba(255, 255, 255, 0.05);
        text-align: center;
        font-weight: bold;
        color: white;
        font-size: 16px;
        padding: 8px 10px;
        border-bottom: 1px solid #444;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .card-body {
        padding: 10px 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .card-meta-data {
        font-size: 14px; /* Agrandado 2px */
        color: #bbb;
        line-height: 1.4;
    }
    
    .card-time-box {
        text-align: right;
    }
    .card-time-val {
        font-family: monospace; 
        font-weight: bold; 
        color: #4CAF50; 
        font-size: 20px;
    }
    .card-badge {
        font-size: 14px;
        color: #ddd;
        margin-top: 2px;
    }

    .swimmer-grid { 
        display: grid; 
        grid-template-columns: 1fr 1fr; 
        gap: 8px; 
        font-size: 13px; 
        color: #eee; 
        padding: 10px 15px; 
        border-top: 1px solid #444;
        background: rgba(0,0,0,0.1);
    }
    .swimmer-item { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }
    
    /* PB Styles */
    .pb-style-header { color: #e53935; font-weight: bold; font-size: 16px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; border-bottom: 1px solid #444; }
    .pb-row { background-color: #2b2c35; padding: 10px 15px; margin-bottom: 5px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #B71C1C; }
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
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except Exception as e: return None

data = cargar_visualizacion()
if not data: st.stop()

# --- 3. PROCESAMIENTO GLOBAL ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
df_nad['anio_nac'] = pd.to_datetime(df_nad['fechanac'], errors='coerce').dt.year.fillna(0).astype(int)
dict_id_anionac = df_nad.set_index('codnadador')['anio_nac'].to_dict()

def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return None
        p = t_str.replace('.', ':').split(':')
        val = float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
        return val
    except: return None

def seg_a_tiempo(seg):
    if seg is None or pd.isna(seg): return "-"
    try:
        m = int(seg // 60)
        s = int(seg % 60)
        c = int((seg % 1) * 100)
        return f"{m:02d}:{s:02d}.{c:02d}"
    except: return "-"

def asignar_cat(edad):
    try:
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

def calcular_grupo_relevo(row_rel, df_cats):
    try:
        suma_edades = 0
        anio_competencia = pd.to_datetime(row_rel['fecha']).year
        for k in range(1, 5):
            nid = row_rel[f'nadador_{k}']
            anio_nac = dict_id_anionac.get(nid, 0)
            if anio_nac > 0:
                suma_edades += (anio_competencia - anio_nac)
        
        reglamento = row_rel.get('tipo_reglamento', 'FED') 
        filtro = df_cats[
            (df_cats['tipo_reglamento'] == reglamento) & 
            (df_cats['suma_min'] <= suma_edades) & 
            (df_cats['suma_max'] >= suma_edades)
        ]
        if not filtro.empty: return filtro.iloc[0]['descripcion']
        return f"Suma {suma_edades}"
    except: return "-"

# --- UNIFICACIÓN DE DATOS (LIMPIEZA DE CLUB) ---
df_full = data['tiempos'].copy()

# Eliminar 'club' de Tiempos para evitar conflicto
if 'club' in df_full.columns: df_full = df_full.drop(columns=['club'])

df_full = df_full.merge(data['estilos'], on='codestilo', how='left')
df_full = df_full.merge(data['distancias'], on='coddistancia', how='left')
df_full = df_full.merge(data['piletas'], on='codpileta', how='left')

# Renombrar columnas conflictivas o faltantes
if 'descripcion_x' in df_full.columns: df_full = df_full.rename(columns={'descripcion_x': 'Estilo'})
elif 'descripcion' in df_full.columns: df_full = df_full.rename(columns={'descripcion': 'Estilo'})

if 'descripcion_y' in df_full.columns: df_full = df_full.rename(columns={'descripcion_y': 'Distancia'})

if 'club' in df_full.columns: df_full = df_full.rename(columns={'club': 'sede'})
else: df_full['sede'] = '-'

if 'medida' not in df_full.columns: df_full['medida'] = '-'

# Lógica Medallero
df_t_c = data['tiempos'].copy(); df_r_c = data['relevos'].copy()
df_t_c['posicion'] = pd.to_numeric(df_t_c['posicion'], errors='coerce').fillna(0).astype(int)
df_r_c['posicion'] = pd.to_numeric(df_r_c['posicion'], errors='coerce').fillna(0).astype(int)

med_ind = df_t_c[df_t_c['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
dfs_rel = [df_r_c[['nadador_'+str(i), 'posicion']].rename(columns={'nadador_'+str(i):'codnadador'}) for i in range(1,5)]
med_rel = pd.concat(dfs_rel)
med_rel = med_rel[med_rel['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
medallero = med_ind.add(med_rel, fill_value=0)
for p in [1,2,3]: 
    if p not in medallero.columns: medallero[p] = 0
medallero = medallero.rename(columns={1: 'Oro', 2: 'Plata', 3: 'Bronce'})

df_view = df_nad.merge(medallero, left_on='codnadador', right_index=True, how='left').fillna(0)
df_view['Total'] = df_view['Oro'] + df_view['Plata'] + df_view['Bronce']


# ==============================================================================
#  FUNCIONES REUTILIZABLES
# ==============================================================================

def render_tab_ficha(target_id, unique_key_suffix=""):
    if not target_id: return

    info = df_nad[df_nad['codnadador'] == target_id].iloc[0]
    
    # Datos básicos nadador
    try: 
        nac = pd.to_datetime(info['fechanac'])
        anio_nacimiento_nadador = nac.year
        edad_actual = datetime.now().year - anio_nacimiento_nadador
        nac_str = nac.strftime('%d/%m/%Y')
    except: 
        anio_nacimiento_nadador = 0
        edad_actual = 0; nac_str = "-"
    
    cat_actual = asignar_cat(edad_actual)
    
    row_m = df_view[df_view['codnadador'] == target_id]
    if not row_m.empty:
        o, pl, br = int(row_m.iloc[0]['Oro']), int(row_m.iloc[0]['Plata']), int(row_m.iloc[0]['Bronce'])
    else: o, pl, br = 0, 0, 0

    st.markdown(f"""
    <div class="ficha-header">
        <div class="ficha-name">{info['nombre']} {info['apellido']}</div>
        <div class="ficha-grid">
            <div>📅 Nacimiento: <b>{nac_str}</b></div>
            <div>🎂 Edad (al 31/12): <b>{edad_actual} años</b></div>
            <div>🏷️ Categoría Actual: <b>{cat_actual}</b></div>
            <div>⚧️ Género: <b>{info['codgenero']}</b></div>
        </div>
        <div class="ficha-medals">
            🥇 {o} &nbsp; | &nbsp; 🥈 {pl} &nbsp; | &nbsp; 🥉 {br}
        </div>
    </div>
    """, unsafe_allow_html=True)

    mis_t = df_full[df_full['codnadador'] == target_id].copy()

    # --- MEJORES MARCAS ---
    if not mis_t.empty:
        st.subheader("✨ Mejores Marcas (PB)")
        mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)
        pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].sort_values(['Estilo', 'segundos'])
        
        for estilo in pbs['Estilo'].unique():
            st.markdown(f"<div class='pb-style-header'>{estilo}</div>", unsafe_allow_html=True)
            for _, r in pbs[pbs['Estilo'] == estilo].iterrows():
                st.markdown(f"""
                <div class="pb-row">
                    <span class="pb-dist">{r['Distancia']}</span>
                    <span class="pb-time">{r['tiempo']}</span>
                </div>""", unsafe_allow_html=True)
        st.divider()

        # --- GRÁFICO ---
        conteo = mis_t.groupby(['Estilo', 'Distancia']).size().reset_index(name='count')
        validos = conteo[conteo['count'] >= 2]
        
        if not validos.empty:
            st.subheader(f"📈 Evolución de Tiempos - {info['nombre']} {info['apellido']}")
            
            c1, c2 = st.columns(2)
            estilos_ok = sorted(validos['Estilo'].unique())
            g_est = c1.selectbox("Estilo Gráfico", estilos_ok, key=f"g_est{unique_key_suffix}")
            
            dist_ok = sorted(validos[validos['Estilo'] == g_est]['Distancia'].unique())
            g_dist = c2.selectbox("Distancia Gráfico", dist_ok, key=f"g_dist{unique_key_suffix}")
            
            df_graph = mis_t[(mis_t['Estilo'] == g_est) & (mis_t['Distancia'] == g_dist)].sort_values('fecha')
            
            # Promedio
            promedio_seg = df_graph['segundos'].mean()
            tiempo_promedio = seg_a_tiempo(promedio_seg)
            st.markdown(f"<div style='font-size:16px; margin-bottom:10px;'>⏱️ Tiempo Promedio Histórico: <b>{tiempo_promedio}</b></div>", unsafe_allow_html=True)

            # Tooltip
            df_graph['fecha_dt'] = pd.to_datetime(df_graph['fecha'])
            if anio_nacimiento_nadador > 0:
                df_graph['cat_hist'] = df_graph['fecha_dt'].apply(lambda x: asignar_cat(x.year - anio_nacimiento_nadador))
            else: df_graph['cat_hist'] = "-"

            # Plot
            df_graph['TimeObj'] = pd.to_datetime('2024-01-01') + pd.to_timedelta(df_graph['segundos'], unit='s')
            
            fig = px.line(df_graph, x='fecha', y='TimeObj', markers=True, template="plotly_dark",
                          hover_data={
                              'fecha': False, 'TimeObj': False,
                              'sede': True, 'Distancia': True, 'cat_hist': True, 'tiempo': True
                          })
            
            fig.update_traces(line_color='#E53935', name="Registro",
                              hovertemplate="<b>%{customdata[3]}</b><br>📅 %{x|%d/%m/%Y}<br>📍 %{customdata[0]}<br>🏷️ %{customdata[2]}")
            
            fig.update_yaxes(tickformat="%M:%S.%f", title="Tiempo")
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=40, r=20), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Necesitas al menos 2 carreras en la misma prueba para ver la evolución.")
        st.divider()

    # --- HISTORIAL COMPLETO (NUEVA CARD CENTRADA) ---
    st.subheader("📜 Historial Completo")
    with st.expander("Filtrar Historial"):
        h1, h2 = st.columns(2)
        hf_est = h1.selectbox("Estilo", ["Todos"] + sorted(mis_t['Estilo'].unique().tolist()), key=f"h_est{unique_key_suffix}")
        hf_dis = h2.selectbox("Distancia", ["Todos"] + sorted(mis_t['Distancia'].unique().tolist()), key=f"h_dis{unique_key_suffix}")
    
    df_hist = mis_t.copy()
    if hf_est != "Todos": df_hist = df_hist[df_hist['Estilo'] == hf_est]
    if hf_dis != "Todos": df_hist = df_hist[df_hist['Distancia'] == hf_dis]
    df_hist = df_hist.sort_values('fecha', ascending=False)
    
    for _, r in df_hist.head(20).iterrows():
        try: 
            pos_val = int(r['posicion'])
            if pos_val == 1: medal_str = "🥇 1º"
            elif pos_val == 2: medal_str = "🥈 2º"
            elif pos_val == 3: medal_str = "🥉 3º"
            elif pos_val > 0: medal_str = f"Pos: {pos_val}"
            else: medal_str = "-"
        except: medal_str = "-"

        sede_txt = r.get('sede', '-')
        medida_txt = r.get('medida', '-')
        
        try:
            anio_carrera = pd.to_datetime(r['fecha']).year
            edad_en_carrera = anio_carrera - anio_nacimiento_nadador
            cat_torneo = asignar_cat(edad_en_carrera)
        except: cat_torneo = "-"

        # LAYOUT CENTRADO
        st.markdown(f"""
        <div class="mobile-card">
            <div class="card-header-center">{r['Estilo']} {r['Distancia']}</div>
            
            <div class="card-body">
                <div class="card-meta-data">
                    <div style="font-weight:bold; color: #ccc;">📅 {r['fecha']}</div>
                    <div style="margin-top:2px;">📍 {sede_txt} ({medida_txt})</div>
                </div>
                
                <div class="card-time-box">
                    <div class="card-time-val">{r['tiempo']}</div>
                    <div class="card-badge">
                        {medal_str} <span style="color:#999; margin-left:3px;">({cat_torneo})</span>
                    </div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

    # 5. MIS RELEVOS (NUEVA CARD CENTRADA)
    st.subheader("🏊‍♂️ Mis Relevos")
    mr_base = data['relevos'].copy()
    cond_rel = (mr_base['nadador_1'] == target_id) | (mr_base['nadador_2'] == target_id) | (mr_base['nadador_3'] == target_id) | (mr_base['nadador_4'] == target_id)
    mis_relevos = mr_base[cond_rel].copy()
    
    if not mis_relevos.empty:
        mis_relevos = mis_relevos.merge(data['estilos'], on='codestilo', how='left')
        mis_relevos = mis_relevos.merge(data['distancias'], on='coddistancia', how='left')
        mis_relevos = mis_relevos.merge(data['piletas'], on='codpileta', how='left')
        
        if 'descripcion_x' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'descripcion_x': 'Estilo'})
        elif 'descripcion' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'descripcion': 'Estilo'})
        
        if 'descripcion_y' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'descripcion_y': 'Distancia'})
        
        if 'club' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'club': 'sede'})
        else: mis_relevos['sede'] = '-'
        if 'medida' not in mis_relevos.columns: mis_relevos['medida'] = '-'

        mis_relevos = mis_relevos.sort_values('fecha', ascending=False)
        
        for _, r in mis_relevos.iterrows():
            grupo_txt = calcular_grupo_relevo(r, data['cat_relevos'])
            html_grid = ""
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                border_style = "border: 1px solid #E91E63;" if nid == target_id else ""
                html_grid += f"<div class='swimmer-item' style='{border_style}'>{k}. {nom}</div>"

            try: p_rel = int(r['posicion'])
            except: p_rel = 0
            if p_rel == 1: pos_icon = "🥇 1º"
            elif p_rel == 2: pos_icon = "🥈 2º"
            elif p_rel == 3: pos_icon = "🥉 3º"
            elif p_rel > 0: pos_icon = f"Pos: {p_rel}"
            else: pos_icon = ""

            sede_r = r.get('sede', '-')

            # CARD RELEVOS CENTRADA
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                <div class="card-header-center">{r['Estilo']} {r['Distancia']}</div>
                
                <div class="card-body">
                    <div class="card-meta-data">
                        <div style="font-weight:bold; color: #ccc;">📅 {r['fecha']}</div>
                        <div style="margin-top:2px;">📍 {sede_r} ({r['medida']})</div>
                        <div style="font-size:13px; color:#888; margin-top:3px;">{grupo_txt} ({r['codgenero']})</div>
                    </div>
                    <div class="card-time-box">
                        <div class="card-time-val">{r['tiempo_final']}</div>
                        <div class="card-badge">{pos_icon}</div>
                    </div>
                </div>
                <div class="swimmer-grid">{html_grid}</div>
            </div>""", unsafe_allow_html=True)
    else: st.info("Sin relevos.")

def render_tab_padron():
    st.markdown("### 🏆 Padrón y Medallero")
    filtro = st.text_input("Buscar Nadador:", placeholder="Nombre...")
    df_show = df_view.sort_values('Total', ascending=False)
    if filtro: df_show = df_show[df_show['Nombre Completo'].str.contains(filtro.upper())]

    for _, row in df_show.head(25).iterrows():
        try: edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        o, p, b, t = int(row.get('Oro',0)), int(row.get('Plata',0)), int(row.get('Bronce',0)), int(row.get('Total',0))
        
        st.markdown(f"""
        <div class="padron-card">
            <div class="p-col-left">
                <div class="p-name">{row['Nombre Completo']}</div>
                <div class="p-meta">{edad} años (al 31/12) • {row['codgenero']}</div>
            </div>
            <div class="p-col-center">
                <div class="p-medals"><span>🥇{o}</span> <span>🥈{p}</span> <span>🥉{b}</span></div>
            </div>
            <div class="p-col-right"><div class="p-total">★ {t}</div><div class="p-cat">{cat}</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"Ver Ficha {row['nombre']} ➝", key=f"btn_p_{row['codnadador']}", use_container_width=True):
            st.session_state.nadador_seleccionado = row['Nombre Completo']
            st.rerun()

def render_tab_relevos_general():
    st.markdown("### Historial de Postas")
    mr_all = data['relevos'].copy()
    if not mr_all.empty:
        mr_all = mr_all.merge(data['estilos'], on='codestilo', how='left')
        mr_all = mr_all.merge(data['distancias'], on='coddistancia', how='left')
        mr_all = mr_all.merge(data['piletas'], on='codpileta', how='left')
        
        if 'descripcion_x' in mr_all.columns: mr_all = mr_all.rename(columns={'descripcion_x': 'Estilo'})
        elif 'descripcion' in mr_all.columns: mr_all = mr_all.rename(columns={'descripcion': 'Estilo'})
        
        if 'descripcion_y' in mr_all.columns: mr_all = mr_all.rename(columns={'descripcion_y': 'Distancia'})
        
        if 'club' in mr_all.columns: mr_all = mr_all.rename(columns={'club': 'sede'})
        else: mr_all['sede'] = '-'
        if 'medida' not in mr_all.columns: mr_all['medida'] = '-'

        c1, c2 = st.columns(2)
        fg_est = c1.selectbox("Estilo", ["Todos"] + sorted(mr_all['Estilo'].unique().tolist()), key="fg_est")
        fg_gen = c2.selectbox("Género", ["Todos", "M", "F", "X"], key="fg_gen")
        
        if fg_est != "Todos": mr_all = mr_all[mr_all['Estilo'] == fg_est]
        if fg_gen != "Todos": mr_all = mr_all[mr_all['codgenero'] == fg_gen]
        
        for _, r in mr_all.sort_values('fecha', ascending=False).head(20).iterrows():
            grupo_txt = calcular_grupo_relevo(r, data['cat_relevos'])
            html_grid = ""
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"

            try: p_rel = int(r['posicion'])
            except: p_rel = 0
            if p_rel == 1: pos_icon = "🥇 1º"
            elif p_rel == 2: pos_icon = "🥈 2º"
            elif p_rel == 3: pos_icon = "🥉 3º"
            elif p_rel > 0: pos_icon = f"Pos: {p_rel}"
            else: pos_icon = ""

            sede_r = r.get('sede', '-')

            # CARD RELEVOS GENERAL CENTRADA
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #9C27B0;">
                <div class="card-header-center">{r['Estilo']} {r['Distancia']}</div>
                
                <div class="card-body">
                    <div class="card-meta-data">
                        <div style="font-weight:bold; color: #ccc;">📅 {r['fecha']}</div>
                        <div style="margin-top:2px;">📍 {sede_r} ({r['medida']})</div>
                        <div style="font-size:13px; color:#888; margin-top:3px;">{grupo_txt} ({r['codgenero']})</div>
                    </div>
                    <div class="card-time-box">
                        <div class="card-time-val">{r['tiempo_final']}</div>
                        <div class="card-badge">{pos_icon}</div>
                    </div>
                </div>
                <div class="swimmer-grid">{html_grid}</div>
            </div>""", unsafe_allow_html=True)

# ==============================================================================
#  LÓGICA PRINCIPAL
# ==============================================================================

if rol == "N":
    tab_yo, tab_otro = st.tabs(["👤 Mi Ficha", "🔍 Consultar Compañero"])
    with tab_yo: render_tab_ficha(mi_id, unique_key_suffix="_me")
    with tab_otro:
        st.markdown("##### Consulta por DNI")
        dni_in = st.text_input("DNI del Nadador", placeholder="Ej: 30123456")
        if dni_in:
            encontrado = df_nad[df_nad['dni'].astype(str).str.contains(dni_in.strip())]
            if not encontrado.empty: render_tab_ficha(encontrado.iloc[0]['codnadador'], unique_key_suffix="_friend")
            else: st.error("No encontrado.")

else:
    # ROL MASTER (M)
    tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])
    
    with tab1: render_tab_padron()
    
    with tab2:
        lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())
        idx_defecto = 0
        pre_seleccion = st.session_state.get("nadador_seleccionado")
        if not pre_seleccion and mi_nombre in lista_nombres: pre_seleccion = mi_nombre
        if pre_seleccion in lista_nombres: idx_defecto = lista_nombres.index(pre_seleccion)

        f_nad = st.selectbox("Seleccionar Atleta:", lista_nombres, index=idx_defecto)
        if f_nad:
            st.session_state.nadador_seleccionado = f_nad
            id_actual = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]['codnadador']
            render_tab_ficha(id_actual, unique_key_suffix="_master")
            
    with tab3: render_tab_relevos_general()
