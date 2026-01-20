import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Entrenamientos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id 
mi_nombre = st.session_state.user_name

if "form_reset_id" not in st.session_state:
    st.session_state.form_reset_id = 0

def reset_carga():
    st.session_state.form_reset_id += 1

# Helper: Convierte tiempo MM:SS.CC a segundos para gráficos
def a_segundos(t_str):
    try:
        if not t_str or str(t_str) in ['nan', 'None', '']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO (Diseño original con ajuste de color en tiempo) ---
st.markdown("""
<style>
    .test-card { background-color: #262730; border: 1px solid #444; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
    .test-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px; }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #4CAF50; font-weight: bold; }
    .final-time { font-family: monospace; font-size: 22px; font-weight: bold; color: #E30613; text-align: right; } /* Color Rojo Newell's aplicado */
    
    .splits-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #444; }
    .split-item { background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; text-align: center; }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; }
    
    .obs-box { margin-top: 8px; font-size: 12px; color: #bbb; font-style: italic; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; border-left: 3px solid #E30613;}
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

# --- DATOS NADADOR ---
df_nad = db['nadadores'].copy()
nad_info = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_info.iloc[0]['apellido'].upper()}, {nad_info.iloc[0]['nombre']}" if not nad_info.empty else mi_nombre
lista_noms = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST (Lógica Robusta)
# ==============================================================================
with tab_cargar:
    with st.container(key=f"c_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        n_in = c2.selectbox("Nadador", [mi_nom_comp] if rol=="N" else lista_noms, index=0 if rol=="N" else None)
        id_nad_target = mi_id if rol=="N" else (df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None)
        
        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            m_tot = int(dist_t_val.split(" ")[0])
            m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
            quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True) if m_par > 0 else False
            
            st.divider()
            with st.form("form_reg"):
                st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                st.text_input("Ref", value=dist_t_val, disabled=True, label_visibility="collapsed")
                tf1, tf2, tf3 = st.columns(3)
                mf, sf, cf = tf1.number_input("Min", 0, 59, 0), tf2.number_input("Seg", 0, 59, 0), tf3.number_input("Cent", 0, 99, 0)
                
                lp = []
                if quiere_p:
                    st.markdown(f"<div class='section-title'>PARCIALES ({m_par}m)</div>", unsafe_allow_html=True)
                    for i in range(1, 5):
                        st.write(f"P{i}")
                        px1, px2, px3, px4 = st.columns(4)
                        px1.text_input(f"d{i}", value=f"{m_par}m", disabled=True, label_visibility="collapsed")
                        p_m = px2.number_input("M", 0, 59, 0, key=f"pm_{i}")
                        p_s = px3.number_input("S", 0, 59, 0, key=f"ps_{i}")
                        p_c = px4.number_input("C", 0, 99, 0, key=f"pc_{i}")
                        lp.append(f"{p_m:02d}:{p_s:02d}.{p_c:02d}" if (p_m+p_s+p_c)>0 else "")
                
                obs = st.text_area("Observaciones")
                if st.form_submit_button("GUARDAR REGISTRO"):
                    # [Lógica de guardado omitida aquí para brevedad, mantener la aprobada]
                    reset_carga(); st.rerun()

# ==============================================================================
#  HISTORIAL INTELIGENTE Y ANÁLISIS
# ==============================================================================
with tab_ver:
    target_id = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sel_n = st.selectbox("Consultar Historial de:", lista_noms, index=None, key="h_nad")
        if sel_n: target_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel_n].iloc[0]['codnadador']
    
    if target_id:
        df_h = db['entrenamientos'][db['entrenamientos']['codnadador'].astype(str) == str(target_id)].copy()
        
        if not df_h.empty:
            df_h = df_h.merge(db['estilos'], on='codestilo', how='left').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            
            # FILTROS BASADOS SOLO EN DATOS EXISTENTES PARA EL NADADOR
            st.markdown("<div class='section-title'>🔍 Filtros de Búsqueda</div>", unsafe_allow_html=True)
            f_col1, f_col2 = st.columns(2)
            est_opts = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            dist_opts = ["Todos"] + sorted(df_h['descripcion_y'].unique().tolist())
            
            f_est = f_col1.selectbox("Estilo", est_opts)
            f_dist = f_col2.selectbox("Distancia", dist_opts)

            # Filtrado
            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # GRÁFICA DE PROGRESO (Solo si no es "Todos" y hay al menos 2 registros)
            if f_est != "Todos" and f_dist != "Todos":
                if len(df_filt) >= 2:
                    st.markdown("<div class='section-title'>📈 Progresión del Test</div>", unsafe_allow_html=True)
                    df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                    df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                    fig_prog = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, 
                                       labels={'seg': 'Segundos', 'fecha_dt': 'Fecha'}, color_discrete_sequence=['#E30613'])
                    fig_prog.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark")
                    st.plotly_chart(fig_prog, use_container_width=True)
                else:
                    st.info("💡 Se requieren al menos 2 registros para visualizar el gráfico de progresión.")

            # LISTADO DE TARJETAS
            st.markdown("<div class='section-title'>📋 Registros</div>", unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                # Lógica de parciales dinámica
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                p_validos = [p for p in ps if p and str(p) not in ['nan', 'None', '', '00:00.00']]
                
                splits_html = ""
                if p_validos:
                    grid = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(p_validos)])
                    splits_html = f"<div class='splits-grid'>{grid}</div>"
                
                obs_html = f"<div class='obs-box'>📝 {r['observaciones']}</div>" if r['observaciones'] and str(r['observaciones']) not in ['nan','None',''] else ""
                
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion_x', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_y', '-')}</div>
                            <div class="test-date">📅 {f_fmt}</div>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    {splits_html}
                    {obs_html}
                </div>""", unsafe_allow_html=True)

                # Gráfico individual de parciales (Color anterior al azul = Rojo/Gris oscuro)
                if p_validos:
                    if st.checkbox(f"Analizar técnica", key=f"chk_{r['id_entrenamiento']}"):
                        p_seg = [a_segundos(p) for p in p_validos]
                        fig_bar = px.bar(x=[f"P{i+1}" for i in range(len(p_seg))], y=p_seg, 
                                         labels={'x': 'Tramo', 'y': 'Segundos'}, color_discrete_sequence=['#E30613'])
                        fig_bar.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, template="plotly_dark")
                        st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No se encontraron registros para este nadador.")
