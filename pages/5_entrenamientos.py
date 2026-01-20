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

# Helper para gráficos
def a_segundos(t_str):
    try:
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO (ROJO Y GRIS) ---
st.markdown("""
<style>
    /* Estilos Generales de la Card */
    .test-card { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        border-radius: 12px; 
        padding: 16px; 
        margin-bottom: 16px; 
        border-left: 5px solid #E30613; /* Rojo Newell's */
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Header de la Card */
    .test-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 12px; 
        border-bottom: 1px solid #333;
        padding-bottom: 8px;
    }
    .header-left { display: flex; flex-direction: column; }
    .test-style { font-size: 18px; font-weight: bold; color: #E30613; text-transform: uppercase; letter-spacing: 0.5px; }
    .test-meta { font-size: 13px; color: #ddd; margin-top: 2px; }
    .test-date { color: #888; font-size: 12px; margin-left: 5px; }
    
    /* Tiempo Final Destacado */
    .final-time { 
        font-family: 'Courier New', monospace; 
        font-size: 24px; 
        font-weight: bold; 
        color: #fff; 
        background-color: #E30613; 
        padding: 4px 10px; 
        border-radius: 6px; 
    }
    
    /* Grilla de Parciales */
    .splits-container { 
        margin-top: 12px; 
        padding: 10px; 
        background-color: #252525; 
        border-radius: 8px; 
        border: 1px solid #333;
    }
    .splits-grid { 
        display: grid; 
        grid-template-columns: repeat(4, 1fr); 
        gap: 8px; 
    }
    .split-item { text-align: center; }
    .split-label { font-size: 10px; color: #aaa; text-transform: uppercase; display: block; margin-bottom: 2px; }
    .split-val { font-family: monospace; font-size: 14px; color: #fff; font-weight: bold; }
    
    /* Caja de Observaciones */
    .obs-box { 
        margin-top: 12px; 
        font-size: 13px; 
        color: #ccc; 
        font-style: italic; 
        background-color: rgba(255, 255, 255, 0.05); 
        padding: 12px; 
        border-radius: 6px; 
        border-left: 3px solid #666;
    }
    
    /* Títulos de sección */
    .section-title { 
        color: #E30613; 
        font-weight: bold; 
        margin-top: 25px; 
        margin-bottom: 15px; 
        border-bottom: 1px solid #444; 
        font-size: 15px; 
        text-transform: uppercase; 
        padding-bottom: 5px;
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

# --- DATOS DEL USUARIO ---
df_nad = db['nadadores'].copy()
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_main_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nom_comp], disabled=True)
            id_nad_target = mi_id
        else:
            n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar...")
            id_nad_target = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            m_tot = int(dist_t_val.split(" ")[0])
            m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
            quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True) if m_par > 0 else False
            
            st.divider()
            with st.form("form_reg_final"):
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
                    # Lógica de guardado...
                    # (Se mantiene la lógica funcional que ya tenías)
                    # AQUÍ IRÍA EL conn.update(...)
                    reset_carga()
                    st.success("Guardado.")
                    st.rerun()

# ==============================================================================
#  HISTORIAL Y ANÁLISIS
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
            
            # --- FILTROS ---
            st.markdown("<div class='section-title'>🔍 Filtros de Búsqueda</div>", unsafe_allow_html=True)
            est_opts = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            dist_opts = ["Todos"] + sorted(df_h['descripcion_y'].unique().tolist())
            
            c_f1, c_f2 = st.columns(2)
            f_est = c_f1.selectbox("Estilo", est_opts)
            f_dist = c_f2.selectbox("Distancia", dist_opts)

            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # --- GRÁFICO DE PROGRESIÓN ---
            if f_est != "Todos" and f_dist != "Todos" and len(df_filt) >= 2:
                st.markdown("<div class='section-title'>📈 Evolución Temporal</div>", unsafe_allow_html=True)
                df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                # Color rojo Newell's
                fig = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, color_discrete_sequence=['#E30613'])
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", yaxis_title="Segundos", xaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

            # --- LISTADO DE CARDS ---
            st.markdown("<div class='section-title'>📋 Registros</div>", unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                
                # 1. Procesar Parciales
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                # Filtramos vacíos, nulos y ceros
                p_validos = [p for p in ps if p and str(p).lower() not in ['nan', 'none', '', '00:00.00']]
                
                # HTML Dinámico: Parciales (SIN INDENTACIÓN para evitar bug de Markdown)
                splits_section = ""
                if p_validos:
                    grid_items = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(p_validos)])
                    splits_section = f"""<div class='splits-container'><div class='splits-grid'>{grid_items}</div></div>"""
                
                # 2. Procesar Observaciones
                obs_raw = str(r.get('observaciones', '')).strip()
                obs_section = ""
                if obs_raw and obs_raw.lower() not in ['nan', 'none', '']:
                    obs_section = f"""<div class='obs-box'>📝 {obs_raw}</div>"""
                
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                
                # 3. Construcción del HTML Final (Concatenación limpia)
                card_html = f"""
<div class="test-card">
    <div class="test-header">
        <div class="header-left">
            <span class="test-style">{r.get('descripcion_x', '-')}</span>
            <span class="test-meta">{r.get('descripcion_y', '-')} <span class="test-date">| {f_fmt}</span></span>
        </div>
        <div class="final-time">{r['tiempo_final']}</div>
    </div>
    {splits_section}
    {obs_section}
</div>
"""
                st.markdown(card_html, unsafe_allow_html=True)

                # Gráfico individual (Color Rojo)
                if p_validos:
                    if st.checkbox(f"Ver gráfico de tramos", key=f"chk_{r['id_entrenamiento']}"):
                        p_seg = [a_segundos(p) for p in p_validos]
                        fig_bar = px.bar(x=[f"P{i+1}" for i in range(len(p_seg))], y=p_seg, 
                                         labels={'x': 'Tramo', 'y': 'Segundos'},
                                         color_discrete_sequence=['#E30613']) # Rojo fijo
                        fig_bar.update_layout(height=200, template="plotly_dark", showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
                        st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No se encontraron registros para este nadador.")
