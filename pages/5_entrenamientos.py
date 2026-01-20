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

# --- GESTIÓN DE REINICIO TOTAL ---
if "form_reset_id" not in st.session_state:
    st.session_state.form_reset_id = 0

def reset_aplicacion_total():
    st.session_state.form_reset_id += 1

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .test-card { background-color: #262730; border: 1px solid #444; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
    .test-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px; }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #4CAF50; font-weight: bold; }
    .final-time-label { font-family: monospace; font-size: 20px; font-weight: bold; color: #FFD700; text-align: right; }
    
    /* ESTILO PARCIALES HISTORIAL */
    .split-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #333; font-size: 14px; }
    .split-dist-label { color: #888; font-weight: normal; }
    .split-time-val { font-family: monospace; color: #eee; font-weight: bold; }
    
    .obs-box { margin-top: 10px; font-size: 12px; color: #bbb; font-style: italic; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px;}
    .section-title { color: #E30613; font-weight: bold; margin-top: 15px; margin-bottom: 8px; border-bottom: 1px solid #333; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }
    .config-box { background: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #E30613; margin-bottom: 20px; }
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

# --- PROCESAMIENTO ---
df_nad = db['nadadores'].copy()
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_full = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

def to_sec(m, s, c): return (int(m) * 60) + int(s) + (int(c) / 100)
def to_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST (CON REINICIO TOTAL)
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_root_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nom_full], disabled=True)
            id_nad_target = mi_id
        else:
            n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar...")
            id_nad_target = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            id_est = db['estilos'][db['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = db['distancias'][db['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_s = f_val.strftime('%Y-%m-%d')
            
            # Validación de duplicados
            df_ent = db['entrenamientos']
            existe = False
            if not df_ent.empty:
                existe = not df_ent[(df_ent['codnadador'].astype(str) == str(id_nad_target)) & 
                                    (df_ent['fecha'].astype(str) == str(fecha_s)) & 
                                    (df_ent['codestilo'].astype(str) == str(id_est)) &
                                    (df_ent['coddistancia'].astype(str) == str(id_dt))].empty
            
            if existe:
                st.error(f"🚫 Ya existe un test de {dist_t_val} para este nadador el {f_val.strftime('%d/%m/%Y')}.")
            else:
                # Lógica de parciales
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                
                if m_par > 0:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Parciales automáticos cada {m_par} mts.</div>", unsafe_allow_html=True)
                    quiere_p = st.toggle("¿Cargar parciales?", value=True)
                else:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Regla automática: Sin parciales.</div>", unsafe_allow_html=True)
                    quiere_p = False

                st.divider()
                st.subheader("2. Registrar Tiempos")
                
                with st.form("form_registro_directo"):
                    st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                    tf1, ts1, tf2, ts2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                    mf = tf1.number_input("Min", 0, 59, 0, format="%02d")
                    sf = tf2.number_input("Seg", 0, 59, 0, format="%02d")
                    cf = tf3.number_input("Cent", 0, 99, 0, format="%02d")

                    inputs_p = []
                    if quiere_p:
                        st.markdown(f"<div class='section-title'>PARCIALES ({m_par} mts)</div>", unsafe_allow_html=True)
                        for i in range(1, 5):
                            st.write(f"Parcial {i}")
                            px1, px2, px3 = st.columns(3)
                            pm = px1.number_input("M", 0, 59, 0, key=f"pm_{i}", format="%02d")
                            ps = px2.number_input("S", 0, 59, 0, key=f"ps_{i}", format="%02d")
                            pc = px3.number_input("C", 0, 99, 0, key=f"pc_{i}", format="%02d")
                            inputs_p.append((pm, ps, pc))

                    obs = st.text_area("Observaciones")

                    if st.form_submit_button("GUARDAR Y REINICIAR TODO", use_container_width=True):
                        s_final = to_sec(mf, sf, cf)
                        if s_final == 0:
                            st.error("Error: Tiempo final obligatorio.")
                        else:
                            # Validación de Coherencia
                            error_c = False
                            if quiere_p:
                                suma_p = sum([to_sec(p[0], p[1], p[2]) for p in inputs_p])
                                if suma_p > 0 and abs(suma_p - s_final) > 0.5:
                                    st.error(f"❌ Los parciales suman {suma_p:.2f}s, pero el final es {s_final:.2f}s. Corrige antes de guardar.")
                                    error_c = True
                            
                            if not error_c:
                                with st.spinner("Sincronizando..."):
                                    try:
                                        m_id = pd.to_numeric(df_ent['id_entrenamiento'], errors='coerce').max() if not df_ent.empty else 0
                                        nid = int(0 if pd.isna(m_id) else m_id) + 1
                                        id_dp = db['distancias'][db['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_p else ""
                                        
                                        row = pd.DataFrame([{
                                            "id_entrenamiento": nid, "fecha": fecha_s,
                                            "codnadador": int(id_nad_target), "codestilo": id_est,
                                            "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                            "tiempo_final": to_str(mf, sf, cf),
                                            "parcial_1": to_str(*inputs_p[0]) if len(inputs_p)>0 and sum(inputs_p[0])>0 else "",
                                            "parcial_2": to_str(*inputs_p[1]) if len(inputs_p)>1 and sum(inputs_p[1])>0 else "",
                                            "parcial_3": to_str(*inputs_p[2]) if len(inputs_p)>2 and sum(inputs_p[2])>0 else "",
                                            "parcial_4": to_str(*inputs_p[3]) if len(inputs_p)>3 and sum(inputs_p[3])>0 else "",
                                            "observaciones": obs
                                        }])
                                        
                                        conn.update(worksheet="Entrenamientos", data=pd.concat([df_ent, row], ignore_index=True))
                                        st.cache_data.clear()
                                        reset_aplicacion_total()
                                        st.rerun()
                                    except Exception as e: st.error(f"Error: {e}")

# ==============================================================================
#  HISTORIAL (VISUALIZACIÓN MEJORADA)
# ==============================================================================
with tab_ver:
    hid = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sn = st.selectbox("Ver historial de:", lista_nombres, index=None, key="hsel")
        if sn: hid = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sn].iloc[0]['codnadador']
    
    if hid:
        dfh = db['entrenamientos'][db['entrenamientos']['codnadador'].astype(str) == str(hid)].copy()
        if not dfh.empty:
            dfh = dfh.merge(db['estilos'], on='codestilo', how='left').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia', how='left').merge(db['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            for _, r in dfh.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                
                # Armar filas de parciales con el formato solicitado
                dist_p_label = r.get('descripcion_par', '')
                rows_html = ""
                for i in range(1, 5):
                    val_p = r.get(f'parcial_{i}')
                    if val_p and str(val_p) not in ['nan','']:
                        rows_html += f"""<div class='split-row'>
                            <span class='split-dist-label'>{dist_p_label}</span>
                            <span class='split-time-val'>{val_p}</span>
                        </div>"""

                fmt_f = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_tot', '-')}</div>
                            <div class="test-date">📅 {fmt_f}</div>
                        </div>
                        <div class="final-time-label">{r['tiempo_final']}</div>
                    </div>
                    {rows_html}
                    <div class="obs-box">📝 {r['observaciones'] if str(r['observaciones']) not in ['nan','None',''] else 'Sin notas.'}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("No hay registros.")
