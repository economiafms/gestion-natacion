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
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO (DISEÑO ORIGINAL RESTAURADO + PALETA NEWELL'S) ---
st.markdown("""
<style>
    /* Tarjeta Principal */
    .test-card { 
        background-color: #262730; 
        border: 1px solid #444; 
        border-radius: 8px; 
        padding: 0; /* Padding controlado internamente */
        margin-bottom: 15px; 
        overflow: hidden; /* Para contener los hijos */
    }
    
    /* Cabecera: Estilo, Distancia, Fecha y Tiempo */
    .test-header { 
        padding: 15px 15px 10px 15px;
        display: flex; 
        justify-content: space-between; 
        align-items: flex-start; 
    }
    
    .header-info { display: flex; flex-direction: column; }
    
    .test-style { 
        font-size: 18px; 
        font-weight: 800; 
        color: white; 
        text-transform: uppercase; 
        margin-bottom: 4px;
    }
    
    .test-sub { 
        font-size: 14px; 
        color: #E30613; /* Rojo Newell's para la distancia */
        font-weight: bold; 
    }
    
    .test-date {
        font-size: 12px;
        color: #999;
        font-weight: normal;
        margin-left: 8px;
    }
    
    .final-time { 
        font-family: 'Courier New', monospace; 
        font-size: 26px; 
        font-weight: bold; 
        color: #E30613; /* Rojo Newell's */
        text-align: right; 
        background: rgba(0,0,0,0.3);
        padding: 4px 10px;
        border-radius: 6px;
    }
    
    /* Sección de Parciales */
    .splits-section {
        padding: 0 15px 10px 15px;
    }
    .splits-grid { 
        display: grid; 
        grid-template-columns: repeat(4, 1fr); 
        gap: 6px; 
        padding-top: 10px; 
        border-top: 1px solid #444; 
    }
    .split-item { 
        background: rgba(255,255,255,0.05); 
        padding: 6px; 
        border-radius: 4px; 
        text-align: center; 
    }
    .split-label { font-size: 10px; color: #aaa; display: block; margin-bottom: 2px; }
    .split-val { font-family: monospace; font-size: 14px; color: #fff; }
    
    /* Sección de Observaciones (Footer) */
    .obs-footer {
        background-color: #1a1a1a;
        padding: 10px 15px;
        border-top: 1px solid #333;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .obs-icon { font-size: 16px; }
    .obs-text { 
        font-size: 13px; 
        color: #ccc; 
        font-style: italic; 
    }
    
    /* Títulos de Streamlit */
    .section-title { 
        color: #E30613; 
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        border-bottom: 1px solid #555; 
        font-size: 14px; 
        text-transform: uppercase; 
    }
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

# --- DATOS ---
df_nad = db['nadadores'].copy()
nad_info = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_info.iloc[0]['apellido'].upper()}, {nad_info.iloc[0]['nombre']}" if not nad_info.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        n_in = c2.selectbox("Nadador", [mi_nom_comp] if rol=="N" else lista_nombres, index=0 if rol=="N" else None)
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
                st.text_input("Distancia", value=dist_t_val, disabled=True, label_visibility="collapsed")
                tf1, tf2, tf3 = st.columns(3)
                mf = tf1.number_input("Min", 0, 59, 0)
                sf = tf2.number_input("Seg", 0, 59, 0)
                cf = tf3.number_input("Cent", 0, 99, 0)
                
                lp = []
                if quiere_p:
                    st.markdown(f"<div class='section-title'>PARCIALES ({m_par} mts)</div>", unsafe_allow_html=True)
                    for i in range(1, 5):
                        st.write(f"Parcial {i}")
                        px1, px2, px3, px4 = st.columns(4)
                        px1.text_input(f"d{i}", value=f"{m_par} mts", disabled=True, label_visibility="collapsed")
                        pm = px2.number_input("M", 0, 59, 0, key=f"pm_{i}")
                        ps = px3.number_input("S", 0, 59, 0, key=f"ps_{i}")
                        pc = px4.number_input("C", 0, 99, 0, key=f"pc_{i}")
                        lp.append(f"{pm:02d}:{ps:02d}.{pc:02d}" if (pm+ps+pc)>0 else "")
                
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("GUARDAR REGISTRO"):
                    try:
                        max_id = pd.to_numeric(db['entrenamientos']['id_entrenamiento'], errors='coerce').max() if not db['entrenamientos'].empty else 0
                        new_id = int(0 if pd.isna(max_id) else max_id) + 1
                        
                        id_dp = ""
                        if quiere_p:
                             id_dp = db['distancias'][db['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia']

                        row = pd.DataFrame([{
                            "id_entrenamiento": new_id, "fecha": f_val.strftime('%Y-%m-%d'), 
                            "codnadador": int(id_nad_target), "codestilo": db['estilos'][db['estilos']['descripcion'] == est_val].iloc[0]['codestilo'],
                            "coddistancia": db['distancias'][db['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia'],
                            "coddistancia_parcial": id_dp,
                            "tiempo_final": f"{mf:02d}:{sf:02d}.{cf:02d}",
                            "parcial_1": lp[0] if len(lp)>0 else "", "parcial_2": lp[1] if len(lp)>1 else "",
                            "parcial_3": lp[2] if len(lp)>2 else "", "parcial_4": lp[3] if len(lp)>3 else "",
                            "observaciones": obs
                        }])
                        conn.update(worksheet="Entrenamientos", data=pd.concat([db['entrenamientos'], row], ignore_index=True))
                        reset_carga()
                        st.cache_data.clear()
                        st.success("Guardado.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

# ==============================================================================
#  HISTORIAL
# ==============================================================================
with tab_ver:
    target_id = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sel_n = st.selectbox("Consultar Historial de:", lista_nombres, index=None, key="h_nad")
        if sel_n: target_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel_n].iloc[0]['codnadador']
    
    if target_id:
        df_h = db['entrenamientos'][db['entrenamientos']['codnadador'].astype(str) == str(target_id)].copy()
        
        if not df_h.empty:
            df_h = df_h.merge(db['estilos'], on='codestilo', how='left').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            
            # Filtros
            st.markdown("<div class='section-title'>🔍 Filtros de Búsqueda</div>", unsafe_allow_html=True)
            est_opts = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            dist_opts = ["Todos"] + sorted(df_h['descripcion_y'].unique().tolist())
            
            c_f1, c_f2 = st.columns(2)
            f_est = c_f1.selectbox("Estilo", est_opts)
            f_dist = c_f2.selectbox("Distancia", dist_opts)

            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # Gráfico de Progresión
            if f_est != "Todos" and f_dist != "Todos" and len(df_filt) >= 2:
                st.markdown("<div class='section-title'>📈 Evolución Temporal</div>", unsafe_allow_html=True)
                df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                fig = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, 
                              color_discrete_sequence=['#E30613'])
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", 
                                  yaxis_title="Segundos", xaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

            # Listado
            st.markdown("<div class='section-title'>📋 Registros</div>", unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                
                # --- Preparar Bloques HTML ---
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                
                # 1. Parciales
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                p_validos = [p for p in ps if p and str(p).lower() not in ['nan', 'none', '', '00:00.00']]
                
                html_splits = ""
                if p_validos:
                    grid_items = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(p_validos)])
                    html_splits = f"<div class='splits-section'><div class='splits-grid'>{grid_items}</div></div>"
                
                # 2. Observaciones
                html_obs = ""
                obs_txt = str(r.get('observaciones', '')).strip()
                if obs_txt and obs_txt.lower() not in ['nan', 'none', '']:
                    html_obs = f"""
                    <div class='obs-footer'>
                        <span class='obs-icon'>📝</span>
                        <span class='obs-text'>{obs_txt}</span>
                    </div>
                    """
                
                # 3. Ensamblar Tarjeta
                # Usamos una estructura donde los bloques vacíos (splits u obs) simplemente no se añaden
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div class="header-info">
                            <span class="test-style">{r.get('descripcion_x', '-')}</span>
                            <span class="test-sub">{r.get('descripcion_y', '-')} <span class="test-date">| {f_fmt}</span></span>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    {html_splits}
                    {html_obs}
                </div>
                """, unsafe_allow_html=True)

                if p_validos and st.checkbox(f"Analizar tramos", key=f"chk_{r['id_entrenamiento']}"):
                    p_seg = [a_segundos(p) for p in p_validos]
                    fig_bar = px.bar(
                        x=[f"P{i+1}" for i in range(len(p_seg))], y=p_seg, 
                        labels={'x': 'Tramo', 'y': 'Segundos'},
                        color_discrete_sequence=['#E30613']
                    )
                    fig_bar.update_layout(height=200, template="plotly_dark", showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay registros.")
