import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import time
import numpy as np

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Entrenamientos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id 
mi_nombre = st.session_state.user_name

# Control de estado
if "form_reset_id" not in st.session_state:
    st.session_state.form_reset_id = 0

def reset_carga():
    st.session_state.form_reset_id += 1

# --- FUNCIONES AUXILIARES ---
def a_segundos(t_str):
    """Convierte MM:SS.CC a segundos (float)"""
    try:
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

def fmt_mm_ss(seconds):
    """Genera etiquetas de eje Y en formato MM:SS.CC"""
    if seconds is None or np.isnan(seconds): return ""
    m = int(seconds // 60)
    s = int(seconds % 60)
    c = int((seconds - int(seconds)) * 100)
    return f"{m:02d}:{s:02d}.{c:02d}"

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .test-card { 
        background-color: #262730; 
        border: 1px solid #444; 
        border-radius: 10px; 
        padding: 15px; 
        margin-bottom: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
        border-left: 5px solid #E30613; 
    }
    .test-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: flex-start; 
        margin-bottom: 8px; 
        border-bottom: 1px solid #444; 
        padding-bottom: 8px; 
    }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #aaa; font-weight: bold; }
    .test-date { font-size: 12px; color: #888; margin-left: 5px; }
    .final-time { 
        font-family: 'Courier New', monospace; 
        font-size: 24px; 
        font-weight: bold; 
        color: #E30613; 
        text-align: right; 
        background: rgba(0,0,0,0.2); 
        padding: 2px 8px; 
        border-radius: 4px; 
    }
    .splits-container { 
        margin-top: 10px; 
        padding: 10px; 
        background: #1e1e1e; 
        border-radius: 6px; 
        border: 1px solid #333; 
    }
    .splits-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
    .split-item { text-align: center; background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; }
    
    .config-box { 
        background-color: #1e1e1e; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 4px solid #E30613; 
        margin-top: 10px;
        margin-bottom: 15px; 
        color: #eee;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .section-title { color: #E30613; font-weight: bold; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #333; font-size: 14px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def cargar_entrenamientos():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "entrenamientos": conn.read(worksheet="Entrenamientos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias")
        }
    except: return None

db = cargar_entrenamientos()
if not db: st.stop()

# --- PROCESAMIENTO ROBUSTO DE DATOS ---
df_nad = db['nadadores'].copy()
df_ent = db['entrenamientos'].copy()
df_est = db['estilos'].copy()
df_dist = db['distancias'].copy()

# Normalizar columnas (minúsculas y sin espacios)
df_nad.columns = df_nad.columns.str.strip().str.lower()
df_ent.columns = df_ent.columns.str.strip().str.lower()
df_est.columns = df_est.columns.str.strip().str.lower()
df_dist.columns = df_dist.columns.str.strip().str.lower()

# Normalizar claves de cruce (IDs)
for df in [df_ent, df_est, df_dist]:
    if 'codestilo' in df.columns:
        df['codestilo'] = df['codestilo'].astype(str).str.strip()
    if 'coddistancia' in df.columns:
        df['coddistancia'] = df['coddistancia'].astype(str).str.strip()

# Preparar datos de usuario
nad_info = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_info.iloc[0]['apellido'].upper()}, {nad_info.iloc[0]['nombre']}" if not nad_info.empty else mi_nombre
lista_noms = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in df_dist['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_container_{st.session_state.form_reset_id}"):
        
        # --- PASO 1 ---
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        # En la carga usamos lista_noms completa (todos los nadadores)
        n_in = c2.selectbox("Nadador", [mi_nom_comp] if rol=="N" else lista_noms, index=0 if rol=="N" else None)
        id_nad_target = mi_id if rol=="N" else (df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None)
        
        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", df_est['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        mostrar_paso_2 = False
        
        if n_in and est_val and dist_t_val:
            id_est = df_est[df_est['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = df_dist[df_dist['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_str = f_val.strftime('%Y-%m-%d')
            
            # Validación duplicados
            duplicado = False
            if not df_ent.empty:
                existe = df_ent[
                    (df_ent['codnadador'].astype(str) == str(id_nad_target)) & 
                    (df_ent['fecha'].astype(str) == fecha_str) & 
                    (df_ent['codestilo'].astype(str) == str(id_est)) &
                    (df_ent['coddistancia'].astype(str) == str(id_dt))
                ]
                if not existe.empty: duplicado = True
            
            if duplicado:
                st.error(f"⛔ Ya existe un registro de {est_val} {dist_t_val} para esta fecha.")
            else:
                mostrar_paso_2 = True
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                msg_par = f"Se habilitarán tomas de parciales cada <b>{m_par} mts</b>." if m_par > 0 else "Distancia corta o relevo: Sin toma de parciales."
                
                st.markdown(f"<div class='config-box'><strong>CONFIGURACIÓN:</strong> {dist_t_val} {est_val}.<br>{msg_par}</div>", unsafe_allow_html=True)
                
                quiere_p = False
                if m_par > 0:
                    quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True)
                    if quiere_p:
                        st.caption("ℹ️ Podés cargar parciales cronometrados o individuales. El sistema los detecta automáticamente.")

        # --- PASO 2 ---
        if mostrar_paso_2:
            st.divider()
            st.subheader("2. Registrar Tiempos")
            
            with st.form("form_reg", clear_on_submit=False):
                st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                st.text_input("Ref", value=dist_t_val, disabled=True, label_visibility="collapsed")
                
                tf1, tf2, tf3 = st.columns(3)
                mf = tf1.number_input("Min", 0, 59, 0)
                sf = tf2.number_input("Seg", 0, 59, 0)
                cf = tf3.number_input("Cent", 0, 99, 0)
                
                lp = []
                if quiere_p:
                    st.markdown(f"<div class='section-title'>PARCIALES ({m_par} mts)</div>", unsafe_allow_html=True)
                    for i in range(1, 5):
                        st.write(f"Parcial {i}")
                        px1, px2, px3, px4 = st.columns([1.2, 1, 1, 1])
                        px1.text_input(f"d{i}", value=f"{m_par} mts", disabled=True, label_visibility="collapsed", key=f"d_vis_{i}")
                        pm = px2.number_input("M", 0, 59, 0, key=f"pm_{i}", label_visibility="collapsed")
                        ps = px3.number_input("S", 0, 59, 0, key=f"ps_{i}", label_visibility="collapsed")
                        pc = px4.number_input("C", 0, 99, 0, key=f"pc_{i}", label_visibility="collapsed")
                        lp.append(f"{pm:02d}:{ps:02d}.{pc:02d}" if (pm+ps+pc)>0 else "")
                
                submitted = st.form_submit_button("💾 GUARDAR REGISTRO", use_container_width=True)
                
                if submitted:
                    s_final = (mf*60) + sf + (cf/100)
                    if s_final == 0:
                        st.error("⚠️ El tiempo final es obligatorio.")
                    else:
                        lp_final = [] 
                        s_parciales_norm = 0
                        tipo_detectado = "INDIVIDUALES"
                        
                        raw_secs = []
                        for p_str in lp:
                            sec = a_segundos(p_str)
                            if sec is not None and sec > 0:
                                raw_secs.append(sec)
                        
                        if raw_secs:
                            sum_raw = sum(raw_secs)
                            last_raw = raw_secs[-1]
                            is_increasing = all(x < y for x, y in zip(raw_secs, raw_secs[1:]))
                            tolerance = 2.0 
                            
                            es_acumulado = False
                            
                            if abs(sum_raw - s_final) <= tolerance:
                                es_acumulado = False
                                tipo_detectado = "INDIVIDUALES"
                            elif is_increasing and abs(last_raw - s_final) <= tolerance:
                                es_acumulado = True
                                tipo_detectado = "CRONOMETRADOS (Acumulados)"
                            elif is_increasing and sum_raw > (s_final * 1.5):
                                es_acumulado = True
                                tipo_detectado = "CRONOMETRADOS (Acumulados)"
                            else:
                                es_acumulado = False
                                tipo_detectado = "INDIVIDUALES"

                            norm_secs = []
                            if es_acumulado:
                                prev = 0
                                for curr in raw_secs:
                                    diff = curr - prev
                                    if diff <= 0: diff = 0.01 
                                    norm_secs.append(diff)
                                    prev = curr
                            else:
                                norm_secs = raw_secs
                            
                            lp_final = [fmt_mm_ss(s) for s in norm_secs]
                            s_parciales_norm = sum(norm_secs)
                            
                            st.info(f"ℹ️ Detección automática: **{tipo_detectado}**. Se guardaron como tramos individuales.")

                            if abs(s_parciales_norm - s_final) > 1.0:
                                st.warning(f"⚠️ Atención: La suma de los parciales ({fmt_mm_ss(s_parciales_norm)}) difiere del Tiempo Final ({fmt_mm_ss(s_final)}).")
                        else:
                            lp_final = []

                        while len(lp_final) < 4: lp_final.append("")
                        
                        with st.spinner("Guardando..."):
                            try:
                                max_id = pd.to_numeric(db['entrenamientos']['id_entrenamiento'], errors='coerce').max() if not db['entrenamientos'].empty else 0
                                new_id = int(0 if pd.isna(max_id) else max_id) + 1
                                id_dp = df_dist[df_dist['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_p else ""

                                row = pd.DataFrame([{
                                    "id_entrenamiento": new_id, "fecha": fecha_str, 
                                    "codnadador": int(id_nad_target), "codestilo": id_est,
                                    "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                    "tiempo_final": f"{mf:02d}:{sf:02d}.{cf:02d}",
                                    "parcial_1": lp_final[0], "parcial_2": lp_final[1],
                                    "parcial_3": lp_final[2], "parcial_4": lp_final[3],
                                    "observaciones": ""
                                }])
                                conn.update(worksheet="Entrenamientos", data=pd.concat([db['entrenamientos'], row], ignore_index=True))
                                st.success("✅ Guardado."); time.sleep(1); reset_carga(); st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

# ==============================================================================
#  HISTORIAL
# ==============================================================================
with tab_ver:
    target_id = mi_id if rol == "N" else None
    
    # 1. Selector de Nadador (Solo para M o P)
    if rol in ["M", "P"]:
        # FILTRO INTELIGENTE:
        # Solo mostramos nadadores que tengan registros en 'entrenamientos'
        if not df_ent.empty:
            ids_con_historia = df_ent['codnadador'].unique().astype(str)
            df_nad_con_historia = df_nad[df_nad['codnadador'].astype(str).isin(ids_con_historia)]
            lista_noms_filtrada = sorted((df_nad_con_historia['apellido'].astype(str).str.upper() + ", " + df_nad_con_historia['nombre'].astype(str)).unique().tolist())
        else:
            lista_noms_filtrada = []

        sel_n = st.selectbox("Consultar Historial de:", lista_noms_filtrada, index=None, key="h_nad")
        if sel_n: 
            target_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel_n].iloc[0]['codnadador']
    
    if target_id:
        df_h = df_ent[df_ent['codnadador'].astype(str) == str(target_id)].copy()
        
        if not df_h.empty:
            df_h = df_h.merge(df_est, on='codestilo', how='left').merge(df_dist, on='coddistancia', how='left')
            
            # --- FILTROS DINÁMICOS ---
            st.markdown("<div class='section-title'>🔍 Filtros</div>", unsafe_allow_html=True)
            
            # 2. Filtro Estilo
            est_opts = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            c_f1, c_f2 = st.columns(2)
            f_est = c_f1.selectbox("Estilo", est_opts)
            
            # 3. Filtro Distancia
            if f_est == "Todos":
                valid_dists = sorted(df_h['descripcion_y'].unique().tolist())
            else:
                valid_dists = sorted(df_h[df_h['descripcion_x'] == f_est]['descripcion_y'].unique().tolist())
                
            f_dist = c_f2.selectbox("Distancia", ["Todos"] + valid_dists)

            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # --- GRÁFICO RESUMEN ---
            if f_est == "Todos" and f_dist == "Todos" and not df_filt.empty:
                st.markdown("<div class='section-title'>📊 Distribución por Estilos</div>", unsafe_allow_html=True)
                
                conteo = df_filt.groupby(['descripcion_x', 'descripcion_y']).size().reset_index(name='Cantidad')
                
                # Etiqueta vacía si es 1
                conteo['Etiqueta'] = conteo['Cantidad'].apply(lambda x: str(x) if x > 1 else "")
                
                fig_count = px.bar(
                    conteo, 
                    x='descripcion_x', 
                    y='Cantidad', 
                    color='descripcion_y',
                    text='Etiqueta',
                    color_discrete_sequence=px.colors.sequential.OrRd[::-1], # Colores Anaranjados
                    labels={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'},
                    custom_data=['descripcion_y']
                )
                
                # Tooltip Detallado y Texto Grande
                fig_count.update_traces(
                    textposition='inside', 
                    textfont=dict(size=20, color='white'), 
                    hovertemplate='Metros: %{customdata[0]}<br>Cantidad: %{y}<extra></extra>'
                )
                
                fig_count.update_layout(
                    height=300, 
                    template="plotly_dark", 
                    showlegend=True, 
                    legend_title_text="Distancia",
                    margin=dict(l=0, r=0, t=30, b=0),
                    yaxis=dict(showticklabels=False, title="Cantidad", showgrid=False), 
                    xaxis_title=""
                )
                st.plotly_chart(fig_count, use_container_width=True)

            # --- GRÁFICO EVOLUCIÓN ---
            if f_est != "Todos" and f_dist != "Todos" and len(df_filt) >= 2:
                st.markdown("<div class='section-title'>📈 Evolución</div>", unsafe_allow_html=True)
                df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                
                min_val, max_val = df_filt['seg'].min(), df_filt['seg'].max()
                tick_vals = np.linspace(min_val, max_val, 5) if max_val > min_val else [min_val]
                tick_text = [fmt_mm_ss(v) for v in tick_vals]

                fig = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, 
                              color_discrete_sequence=['#E30613'], custom_data=['tiempo_final'])
                
                fig.update_traces(hovertemplate='📅 %{x|%d/%m/%Y}<br>⏱️ %{customdata[0]}<extra></extra>')
                
                fig.update_layout(
                    height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", 
                    yaxis=dict(title="Tiempo", tickmode='array', tickvals=tick_vals, ticktext=tick_text),
                    xaxis_title=""
                )
                st.plotly_chart(fig, use_container_width=True)

            # --- LISTADO ---
            st.markdown("<div class='section-title'>📋 Registros</div>", unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                p_validos = [p for p in ps if p and str(p).lower() not in ['nan', 'none', '', '00:00.00']]
                
                splits_block = ""
                if p_validos:
                    grid = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(p_validos)])
                    splits_block = f"<div class='splits-container'><div class='splits-grid'>{grid}</div></div>"
                
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion_x', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_y', '-')} <span class="test-date">| {f_fmt}</span></div>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    {splits_block}
                </div>
                """, unsafe_allow_html=True)

                if p_validos and st.checkbox(f"Analizar tramos", key=f"chk_{r['id_entrenamiento']}"):
                    p_seg = [a_segundos(p) for p in p_validos]
                    p_labels = [fmt_mm_ss(s) for s in p_seg]
                    
                    df_bar = pd.DataFrame({
                        'Tramo': [f"P{i+1}" for i in range(len(p_seg))],
                        'Segundos': p_seg,
                        'Etiqueta': p_labels
                    })

                    fig_bar = px.bar(df_bar, x='Tramo', y='Segundos', text='Etiqueta',
                                     color_discrete_sequence=['#E30613'])
                    
                    # AUMENTO DE TAMAÑO DE TEXTO AQUÍ (size=18)
                    fig_bar.update_traces(textposition='auto', textfont=dict(size=18), hovertemplate='⏱️ %{text}<extra></extra>')
                    
                    fig_bar.update_layout(
                        height=200, 
                        template="plotly_dark", 
                        showlegend=False, 
                        margin=dict(l=0, r=0, t=10, b=0),
                        yaxis=dict(showticklabels=False, title=None, showgrid=False), 
                        xaxis_title="Parcial"
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay registros.")
