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

def a_segundos(t_str):
    try:
        if not t_str or str(t_str) in ['nan', 'None', '']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO (ROJO Y GRIS) ---
st.markdown("""
<style>
    .test-card { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        border-radius: 12px; 
        padding: 15px; 
        margin-bottom: 15px; 
        border-left: 5px solid #E30613;
    }
    .test-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .test-style { font-size: 16px; font-weight: bold; color: #E30613; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #fff; font-weight: bold; }
    .test-date { font-size: 12px; color: #888; }
    
    .final-time-badge {
        background-color: #E30613;
        color: white;
        padding: 5px 12px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 18px;
        font-weight: bold;
    }
    
    .splits-grid { 
        display: grid; 
        grid-template-columns: repeat(4, 1fr); 
        gap: 8px; 
        margin-top: 10px; 
        padding: 10px; 
        background: #252525; 
        border-radius: 8px; 
    }
    .split-item { text-align: center; }
    .split-label { font-size: 10px; color: #E30613; font-weight: bold; display: block; }
    .split-val { font-family: monospace; font-size: 13px; color: #eee; }
    
    .obs-box { 
        margin-top: 12px; 
        font-size: 13px; 
        color: #ddd; 
        background: #2a2a2a; 
        padding: 10px; 
        border-radius: 6px; 
        border-left: 3px solid #666;
    }
    .section-title { 
        color: #fff; 
        font-weight: bold; 
        margin-top: 25px; 
        margin-bottom: 10px; 
        border-bottom: 2px solid #E30613; 
        font-size: 14px; 
        text-transform: uppercase; 
    }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def cargar_db():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "entrenamientos": conn.read(worksheet="Entrenamientos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias")
        }
    except: return None

db = cargar_db()
if not db: st.stop()

df_nad = db['nadadores'].copy()
mi_nom_comp = f"{df_nad[df_nad['codnadador'].astype(str) == str(mi_id)].iloc[0]['apellido'].upper()}, {df_nad[df_nad['codnadador'].astype(str) == str(mi_id)].iloc[0]['nombre']}" if not df_nad[df_nad['codnadador'].astype(str) == str(mi_id)].empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST (Mantenida según código anterior)
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        n_in = c2.selectbox("Nadador", [mi_nom_comp] if rol=="N" else lista_nombres, index=0 if rol=="N" else None)
        id_nad_final = mi_id if rol=="N" else (df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None)
        
        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            m_tot = int(dist_t_val.split(" ")[0])
            m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
            quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True) if m_par > 0 else False
            
            st.divider()
            with st.form("form_reg_def"):
                st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                tf1, tf2, tf3 = st.columns(3)
                mf, sf, cf = tf1.number_input("Min", 0, 59, 0), tf2.number_input("Seg", 0, 59, 0), tf3.number_input("Cent", 0, 99, 0)
                
                lp = []
                if quiere_p:
                    st.markdown(f"<div class='section-title'>PARCIALES ({m_par}m)</div>", unsafe_allow_html=True)
                    for i in range(1, 5):
                        st.write(f"P{i}")
                        px1, px2, px3, px4 = st.columns(4)
                        px1.text_input(f"d{i}", value=f"{m_par}m", disabled=True, label_visibility="collapsed")
                        p_m, p_s, p_c = px2.number_input("M", 0, 59, 0, key=f"p_m{i}"), px3.number_input("S", 0, 59, 0, key=f"p_s{i}"), px4.number_input("C", 0, 99, 0, key=f"p_c{i}")
                        lp.append(f"{p_m:02d}:{p_s:02d}.{p_c:02d}" if (p_m+p_s+p_c)>0 else "")
                
                obs = st.text_area("Observaciones")
                if st.form_submit_button("GUARDAR"):
                    # Lógica de guardado...
                    reset_carga()
                    st.success("Guardado.")
                    st.rerun()

# ==============================================================================
#  HISTORIAL INTELIGENTE
# ==============================================================================
with tab_ver:
    tid_h = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sn_h = st.selectbox("Consultar Historial de:", lista_nombres, index=None)
        if sn_h: tid_h = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sn_h].iloc[0]['codnadador']
    
    if tid_h:
        df_h = db['entrenamientos'][db['entrenamientos']['codnadador'].astype(str) == str(tid_h)].copy()
        
        if not df_h.empty:
            df_h = df_h.merge(db['estilos'], on='codestilo', how='left').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            
            # Filtros dinámicos basados en lo que realmente existe
            st.markdown("<div class='section-title'>🔍 Filtros</div>", unsafe_allow_html=True)
            f_est_opt = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            f_dist_opt = ["Todos"] + sorted(df_h['descripcion_y'].unique().tolist())
            
            c_f1, c_f2 = st.columns(2)
            f_est = c_f1.selectbox("Estilo", f_est_opt)
            f_dist = c_f2.selectbox("Distancia", f_dist_opt)

            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # Gráfico de Progresión (Solo si hay filtros específicos y >= 2 registros)
            if f_est != "Todos" and f_dist != "Todos" and len(df_filt) >= 2:
                st.markdown("<div class='section-title'>📈 Evolución Temporal</div>", unsafe_allow_html=True)
                df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                fig = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, color_discrete_sequence=['#E30613'])
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", yaxis_title="Segundos", xaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

            # Tarjetas de registros
            st.markdown("<div class='section-title'>📋 Registros</div>", unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                ps_v = [p for p in ps if p and str(p) not in ['nan', 'None', '', '00:00.00']]
                
                # HTML dinámico parciales
                grid_html = ""
                if ps_v:
                    items = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(ps_v)])
                    grid_html = f"<div class='splits-grid'>{items}</div>"
                
                # HTML dinámico notas
                notas_html = f"<div class='obs-box'>📝 {r['observaciones']}</div>" if r['observaciones'] and str(r['observaciones']) not in ['nan','None',''] else ""
                
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion_x', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_y', '-')} <span class="test-date">| {f_fmt}</span></div>
                        </div>
                        <div class="final-time-badge">{r['tiempo_final']}</div>
                    </div>
                    {grid_html}
                    {notas_html}
                </div>""", unsafe_allow_html=True)

                if ps_v and st.checkbox(f"Analizar técnica de parciales", key=f"chk_{r['id_entrenamiento']}"):
                    p_s = [a_segundos(p) for p in ps_v]
                    fig_p = px.bar(x=[f"Tramo {i+1}" for i in range(len(p_s))], y=p_s, color_discrete_sequence=['#E30613'])
                    fig_p.update_layout(height=200, template="plotly_dark", yaxis_title="Seg", xaxis_title="")
                    st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("No hay registros para mostrar.")
