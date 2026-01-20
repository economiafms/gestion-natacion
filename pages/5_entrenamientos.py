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

# --- PROCESAMIENTO ---
df_nad = data['nadadores'].copy()
nadador_logueado_row = df_nad[df_nad['codnadador'] == mi_id]
mi_nombre_completo = f"{nadador_logueado_row.iloc[0]['apellido'].upper()}, {nadador_logueado_row.iloc[0]['nombre']}" if not nadador_logueado_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())

# Filtros de Distancia
dist_options = data['distancias']['descripcion'].unique().tolist()
list_dist_total = [d for d in dist_options if "25" not in d and "4x" not in d.lower()]
list_dist_parcial = ["Sin parciales"] + [d for d in dist_options if any(x in d for x in ["25 ", "50 ", "100 "])]

def tiempo_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

def extraer_metros(texto):
    try: return int(texto.split(" ")[0])
    except: return 0

# ==============================================================================
#  LÓGICA DE CARGA DINÁMICA (REGLA AUTOMÁTICA)
# ==============================================================================
tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

with tab_cargar:
    with st.form("f_test", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nombre_completo], disabled=True)
        else:
            n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar atleta...")

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)
        
        # Aplicación de Regla Automática de Parciales
        metros_tot = extraer_metros(dist_t_val)
        idx_parcial_sugerido = 0 # "Sin parciales" por defecto
        
        if metros_tot == 400:
            # Buscar el index de "100 mts" en list_dist_parcial
            sugerencia = [i for i, d in enumerate(list_dist_parcial) if d.startswith("100 ")]
            if sugerencia: idx_parcial_sugerido = sugerencia[0]
        elif metros_tot == 200:
            sugerencia = [i for i, d in enumerate(list_dist_parcial) if d.startswith("50 ")]
            if sugerencia: idx_parcial_sugerido = sugerencia[0]
        elif metros_tot == 100:
            sugerencia = [i for i, d in enumerate(list_dist_parcial) if d.startswith("25 ")]
            if sugerencia: idx_parcial_sugerido = sugerencia[0]

        st.markdown("---")
        c5, c6 = st.columns([2, 1])
        dist_p_val = c5.selectbox("Distancia PARCIAL", list_dist_parcial, index=idx_parcial_sugerido)
        cargar_p_check = c6.checkbox("¿Cargar parciales?", value=(dist_p_val != "Sin parciales"))
        
        st.markdown("##### ⏱️ Tiempo Final (MM:SS.CC)")
        tf1, tf_s1, tf2, tf_s2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
        tm_m = tf1.number_input("Min", 0, 59, 0, key="tfm", format="%02d")
        tf_s1.markdown("<div class='time-sep'>:</div>", unsafe_allow_html=True)
        tm_s = tf2.number_input("Seg", 0, 59, 0, key="tfs", format="%02d")
        tf_s2.markdown("<div class='time-sep'>.</div>", unsafe_allow_html=True)
        tm_c = tf3.number_input("Cent", 0, 99, 0, key="tfc", format="%02d")

        t_metros = extraer_metros(dist_t_val) if dist_t_val else 0
        p_metros = extraer_metros(dist_p_val) if dist_p_val and dist_p_val != "Sin parciales" else 0
        num_parciales = min(int(t_metros / p_metros), 4) if p_metros > 0 else 0

        tps = ["", "", "", ""]
        if cargar_p_check and num_parciales > 0:
            st.markdown(f"##### 📊 Parciales (cada {dist_p_val})")
            for i in range(1, num_parciales + 1):
                st.markdown(f"**Parcial {i}**")
                col_d, col_m, col_s1, col_s, col_s2, col_c = st.columns([1.5, 1, 0.2, 1, 0.2, 1])
                col_d.text_input(f"D{i}", value=dist_p_val, disabled=True, key=f"pd{i}", label_visibility="collapsed")
                m = col_m.number_input("M", 0, 59, 0, key=f"p{i}m", format="%02d", label_visibility="collapsed")
                col_s1.markdown("<div style='margin-top:8px; text-align:center;'>:</div>", unsafe_allow_html=True)
                s = col_s.number_input("S", 0, 59, 0, key=f"p{i}s", format="%02d", label_visibility="collapsed")
                col_s2.markdown("<div style='margin-top:8px; text-align:center;'>.</div>", unsafe_allow_html=True)
                c = col_c.number_input("C", 0, 99, 0, key=f"p{i}c", format="%02d", label_visibility="collapsed")
                if (m+s+c) > 0: tps[i-1] = tiempo_str(m, s, c)

        obs_val = st.text_area("Observaciones (Máx 400 car.)", max_chars=400, height=70)
        
        if st.form_submit_button("📥 Agregar a la Cola", use_container_width=True):
            if (rol != "N" and not n_in) or not est_val or not dist_t_val:
                st.error("⚠️ Faltan campos obligatorios.")
            else:
                # 1. Obtener IDs
                final_codnadador = mi_id if rol == "N" else df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador']
                id_est = data['estilos'][data['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
                fecha_str = f_val.strftime('%Y-%m-%d')

                # 2. VALIDACIÓN DE DUPLICADOS (Base de datos + Cola)
                df_existente = data['entrenamientos']
                ya_existe_db = not df_existente[(df_existente['codnadador'] == int(final_codnadador)) & 
                                                (df_existente['fecha'] == fecha_str) & 
                                                (df_existente['codestilo'] == id_est)].empty
                
                ya_existe_cola = any(x for x in st.session_state.cola_tests if x['codnadador'] == int(final_codnadador) and x['fecha'] == fecha_str and x['codestilo'] == id_est)

                if ya_existe_db or ya_existe_cola:
                    st.error(f"🚫 Ya existe un registro para este nadador el día {f_val.strftime('%d/%m/%Y')} en el estilo {est_val}.")
                else:
                    id_dp = data['distancias'][data['distancias']['descripcion'] == dist_p_val].iloc[0]['coddistancia'] if dist_p_val != "Sin parciales" else ""
                    new_id = (data['entrenamientos']['id_entrenamiento'].max() if not data['entrenamientos'].empty else 0) + len(st.session_state.cola_tests) + 1
                    
                    st.session_state.cola_tests.append({
                        "id_entrenamiento": int(new_id), "fecha": fecha_str,
                        "codnadador": int(final_codnadador), "codestilo": id_est,
                        "coddistancia": data['distancias'][data['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia'],
                        "coddistancia_parcial": id_dp, "tiempo_final": tiempo_str(tm_m, tm_s, tm_c),
                        "parcial_1": tps[0], "parcial_2": tps[1], "parcial_3": tps[2], "parcial_4": tps[3],
                        "observaciones": obs_val
                    })
                    st.success("✅ Agregado correctamente."); st.rerun()

# ==============================================================================
#  VISUALIZACIÓN E HISTORIAL
# ==============================================================================
with tab_ver:
    target_id = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sel = st.selectbox("Consultar Historial de:", lista_nombres)
        if sel: target_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel].iloc[0]['codnadador']
    
    if target_id:
        df_t_h = data['entrenamientos'][data['entrenamientos']['codnadador'] == target_id].copy()
        if not df_t_h.empty:
            df_t_h = df_t_h.merge(data['estilos'], on='codestilo', how='left')
            df_t_h = df_t_h.merge(data['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            df_t_h = df_t_h.merge(data['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            
            for _, r in df_t_h.sort_values('fecha', ascending=False).iterrows():
                ps = [r.get(f'parcial_{i}') for i in range(1,5)]
                splits = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(ps) if p and str(p) not in ['nan','']])
                
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_tot', '-')} <span style='color:#888; font-size:11px;'>(Parciales: {r.get('descripcion_par', 'N/A')})</span></div>
                            <div class="test-date">📅 {datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')}</div>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    <div class="splits-grid">{splits}</div>
                    <div class="obs-box">📝 {r['observaciones']}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("Sin registros.")

# PANEL DE SINCRONIZACIÓN (Fuera del form)
if st.session_state.cola_tests:
    st.divider()
    st.info(f"📋 **{len(st.session_state.cola_tests)} tests** pendientes.")
    c_sync1, c_sync2 = st.columns(2)
    if c_sync1.button("🚀 SUBIR A GOOGLE SHEETS", type="primary", use_container_width=True):
        df_final = pd.concat([data['entrenamientos'], pd.DataFrame(st.session_state.cola_tests)], ignore_index=True)
        conn.update(worksheet="Entrenamientos", data=df_final)
        st.session_state.cola_tests = []
        st.cache_data.clear()
        st.success("✅ Sincronizado correctamente."); st.rerun()
    if c_sync2.button("🗑️ Vaciar Cola", use_container_width=True):
        st.session_state.cola_tests = []; st.rerun()
