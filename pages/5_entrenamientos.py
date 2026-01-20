import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

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

st.title("⏱️ Centro de Entrenamiento")

# --- 🎨 DISEÑO Y ESTILOS (MEJORADOS) ---
st.markdown("""
<style>
    /* Tarjetas de Historial */
    .test-card { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        border-radius: 12px; 
        padding: 20px; 
        margin-bottom: 15px; 
        border-left: 6px solid #E30613; /* Rojo Newell's */
    }
    .test-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .test-style { font-size: 16px; font-weight: bold; color: #E30613; text-transform: uppercase; letter-spacing: 1px; }
    .test-date { font-size: 13px; color: #888; }
    
    /* Tiempo Final en Historial */
    .final-time-box {
        background: #000;
        padding: 5px 15px;
        border-radius: 8px;
        border: 1px solid #444;
        font-family: 'Courier New', monospace;
        font-size: 20px;
        font-weight: bold;
        color: #FFD700;
    }

    /* Grilla de Parciales */
    .splits-grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); 
        gap: 10px; 
        margin-top: 15px; 
        background: #252525;
        padding: 10px;
        border-radius: 8px;
    }
    .split-item { text-align: center; border-right: 1px solid #444; }
    .split-item:last-child { border-right: none; }
    .split-label { font-size: 10px; color: #aaa; text-transform: uppercase; display: block; }
    .split-val { font-family: monospace; font-size: 13px; color: #fff; font-weight: bold; }

    /* Estilos de Formulario */
    .section-title { 
        color: #fff; 
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        padding-bottom: 5px;
        border-bottom: 2px solid #E30613; 
        font-size: 14px; 
        text-transform: uppercase; 
    }
    .dist-ref-box {
        background: #E30613;
        color: white;
        padding: 2px 10px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 5px;
        display: inline-block;
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

db_data = cargar_entrenamientos()
if not db_data: st.stop()

df_nad = db_data['nadadores'].copy()
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db_data['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

def to_sec(m, s, c): return (int(m) * 60) + int(s) + (int(c) / 100)
def to_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_container_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nom_comp], disabled=True)
            id_nad_final = mi_id
        else:
            n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Buscar nadador...")
            id_nad_final = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db_data['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            id_est = db_data['estilos'][db_data['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = db_data['distancias'][db_data['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_s = f_val.strftime('%Y-%m-%d')
            
            df_ent = db_data['entrenamientos']
            existe = not df_ent[(df_ent['codnadador'].astype(str) == str(id_nad_final)) & 
                                (df_ent['fecha'].astype(str) == str(fecha_s)) & 
                                (df_ent['codestilo'].astype(str) == str(id_est)) &
                                (df_ent['coddistancia'].astype(str) == str(id_dt))].empty if not df_ent.empty else False
            
            if existe:
                st.error("🚫 Ya existe un registro para esta configuración en la fecha seleccionada.")
            else:
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                
                quiere_p = False
                if m_par > 0:
                    st.info(f"💡 Se sugerirán parciales cada {m_par} mts para esta distancia.")
                    quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True)
                
                st.divider()
                st.subheader("2. Registrar Tiempos")
                
                with st.form("form_registro_def"):
                    # SECCIÓN TIEMPO FINAL
                    st.markdown(f"<div class='dist-ref-box'>{dist_t_val}</div>", unsafe_allow_html=True)
                    st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                    
                    tf1, ts1, tf2, ts2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                    mf = tf1.number_input("Min", 0, 59, 0, format="%02d")
                    sf = tf2.number_input("Seg", 0, 59, 0, format="%02d")
                    cf = tf3.number_input("Cent", 0, 99, 0, format="%02d")

                    lista_parciales = []
                    if quiere_p:
                        st.markdown("<div class='section-title'>PARCIALES</div>", unsafe_allow_html=True)
                        for i in range(1, 5):
                            st.write(f"**Parcial {
