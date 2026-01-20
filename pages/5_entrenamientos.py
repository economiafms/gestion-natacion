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

st.title("⏱️ Centro de Entrenamiento")

# --- CSS ---
st.markdown("""
<style>
    .test-card { background-color: #262730; border: 1px solid #444; border-radius: 10px; padding: 15px; margin-bottom: 12px; }
    .test-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px; }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #4CAF50; font-weight: bold; }
    .final-time { font-family: monospace; font-size: 22px; font-weight: bold; color: #FFD700; text-align: right; }
    .splits-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #444; }
    .split-item { background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; text-align: center; }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; }
    .time-sep { text-align: center; font-size: 18px; font-weight: bold; margin-top: 32px; color: #666; }
    .dist-hint { font-size: 12px; color: #888; background: #1e1e1e; padding: 5px 10px; border-radius: 5px; border-left: 3px solid #E30613; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

if "cola_tests" not in st.session_state: st.session_state.cola_tests = []

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

data = cargar_entrenamientos()
if not data: st.stop()

df_nad = data['nadadores'].copy()
nad_row = df_nad[df_nad['codnadador'] == mi_id]
mi_nom_comp = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())

dist_options = data['distancias']['descripcion'].unique().tolist()
list_dist_total = [d for d in dist_options if "25" not in d and "4x" not in d.lower()]

def tiempo_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  SECCIÓN CARGA (FLUJO DINÁMICO)
# ==============================================================================
with tab_cargar:
    st.subheader("Paso 1: Datos de la Prueba")
    
    c1, c2 = st.columns([1, 2])
    f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    
    if rol == "N":
        n_in = c2.selectbox("Nadador", [mi_nom_comp], disabled=True)
        id_nad_final = mi_id
    else:
        n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar...")
        id_nad_final = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

    c3, c4 = st.columns(2)
    est_val = c3.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
    dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

    if n_in and est_val and dist_t_val:
        # VALIDACIÓN DE DUPLICADOS
        id_est = data['estilos'][data['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
        fecha_s = f_val.strftime('%Y-%m-%d')
        
        existe_db = not data['entrenamientos'][(data['entrenamientos']['codnadador'] == int(id_nad_final)) & 
                                              (data['entrenamientos']['fecha'] == fecha_s) & 
                                              (data['entrenamientos']['codestilo'] == id_est)].empty
        existe_cola = any(x for x in st.session_state.cola_tests if x['codnadador'] == int(id_nad_final) and x['fecha'] == fecha_s and x['codestilo'] == id_est)

        if existe_db or existe_cola:
            st.error(f"🚫 Ya existe un test registrado para {n_in} el {f_val.strftime('%d/%m/%Y')} en {est_val}.")
        else:
            st.divider()
            st.subheader("Paso 2: Registro de Tiempos")
            
            # REGLA AUTOMÁTICA DE PARCIALES
            m_tot = int(dist_t_val.split(" ")[0])
            m_par = 0
            if m_tot == 400: m_par = 100
            elif m_tot == 200: m_par = 50
            elif m_tot == 100: m_par = 25
            
            p_desc = f"{m_par} mts" if m_par > 0 else "Sin parciales"
            st.markdown(f"<div class='dist-hint'>Configuración detectada: <b>{dist_t_val}</b> | Parciales sugeridos: <b>{p_desc}</b></div>", unsafe_allow_html=True)
            
            with st.form("f_tiempos", clear_on_submit=True):
                st.markdown("##### ⏱️ Tiempo Final")
                tf1, tf_s1, tf2, tf_s2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                tm_m = tf1.number_input("Min", 0, 59, 0, key="tm", format="%02d")
                tf_s1.markdown("<div class='time-sep'>:</div>", unsafe_allow_html=True)
                tm_s = tf2.number_input("Seg", 0, 59, 0, key="ts", format="%02d")
                tf_s2.markdown("<div class='time-sep'>.</div>", unsafe_allow_html=True)
                tm_c = tf3.number_input("Cent", 0, 99, 0, key="tc", format="%02d")

                tps = ["", "", "", ""]
                if m_par > 0:
                    st.markdown(f"##### 📊 Parciales (cada {p_desc})")
                    for i in range(1, 5):
                        st.markdown(f"**Parcial {i}**")
                        cd, cm, cs1, cs, cs2, cc = st.columns([1.5, 1, 0.2, 1, 0.2, 1])
                        cd.text_input(f"D{i}", value=p_desc, disabled=True, label_visibility="collapsed")
                        pm = cm.number_input("M", 0, 59, 0, key=f"pm{i}", format="%02d", label_visibility="collapsed")
                        cs1.markdown("<div style='margin-top:8px; text-align:center;'>:</div>", unsafe_allow_html=True)
                        ps = cs.number_input("S", 0, 59, 0, key=f"ps{i}", format="%02d", label_visibility="collapsed")
                        cs2.markdown("<div style='margin-top:8px; text-align:center;'>.</div>", unsafe_allow_html=True)
                        pc = cc.number_input("C", 0, 99, 0, key=f"pc{i}", format="%02d", label_visibility="collapsed")
                        if (pm+ps+pc) > 0: tps[i-1] = tiempo_str(pm, ps, pc)

                obs = st.text_area("Observaciones (Máx 400 car.)", max_chars=400)
                
                if st.form_submit_button("📥 Agregar a la Cola", use_container_width=True):
                    id_dp = data['distancias'][data['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if m_par > 0 else ""
                    id_dt = data['distancias'][data['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
                    
                    new_id = (data['entrenamientos']['id_entrenamiento'].max() if not data['entrenamientos'].empty else 0) + len(st.session_state.cola_tests) + 1
                    
                    st.session_state.cola_tests.append({
                        "id_entrenamiento": int(new_id), "fecha": fecha_s,
                        "codnadador": int(id_nad_final), "codestilo": id_est,
                        "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                        "tiempo_final": tiempo_str(tm_m, tm_s, tm_c),
                        "parcial_1": tps[0], "parcial_2": tps[1], "parcial_3": tps[2], "parcial_4": tps[3],
                        "observaciones": obs
                    })
                    st.success("✅ Añadido a la cola."); st.rerun()

# ==============================================================================
#  HISTORIAL Y SINCRONIZACIÓN
# ==============================================================================
with tab_ver:
    t_id = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        s_n = st.selectbox("Historial de:", lista_nombres)
        if s_n: t_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == s_n].iloc[0]['codnadador']
    
    if t_id:
        df_h = data['entrenamientos'][data['entrenamientos']['codnadador'] == t_id].copy()
        if not df_h.empty:
            df_h = df_h.merge(data['estilos'], on='codestilo', how='left')
            df_h = df_h.merge(data['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            df_h = df_h.merge(data['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            for _, r in df_h.sort_values('fecha', ascending=False).iterrows():
                ps = [r.get(f'parcial_{i}') for i in range(1,5)]
                splits = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(ps) if p and str(p) not in ['nan','']])
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_tot', '-')} <span style='color:#888; font-size:11px;'>(Parciales: {r.get('descripcion_par', 'N/A')})</span></div>
                            <div class="test-date">📅 {f_fmt}</div>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    <div class="splits-grid">{splits}</div>
                    <div class="obs-box">📝 {r['observaciones']}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("Sin registros.")

if st.session_state.cola_tests:
    st.divider()
    st.info(f"📋 {len(st.session_state.cola_tests)} tests pendientes.")
    c_s1, c_s2 = st.columns(2)
    if c_s1.button("🚀 SUBIR TODO", type="primary", use_container_width=True):
        df_f = pd.concat([data['entrenamientos'], pd.DataFrame(st.session_state.cola_tests)], ignore_index=True)
        conn.update(worksheet="Entrenamientos", data=df_f)
        st.session_state.cola_tests = []
        st.cache_data.clear()
        st.success("✅ Sincronizado."); st.rerun()
    if c_s2.button("🗑️ Vaciar", use_container_width=True):
        st.session_state.cola_tests = []; st.rerun()
