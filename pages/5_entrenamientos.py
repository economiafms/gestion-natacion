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

# --- GESTIÓN DE RESETEO ---
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

def reset_form():
    st.session_state.form_key += 1

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .test-card { background-color: #262730; border: 1px solid #444; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
    .test-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px; }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #4CAF50; font-weight: bold; }
    .final-time { font-family: monospace; font-size: 22px; font-weight: bold; color: #FFD700; text-align: right; }
    .splits-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #444; }
    .split-item { background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; text-align: center; }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; }
    .time-sep { text-align: center; font-size: 18px; font-weight: bold; margin-top: 32px; color: #666; }
    .config-box { background: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #E30613; margin-bottom: 20px; }
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
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in data['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

def tiempo_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  SECCIÓN DE CARGA (Con Reseteo Dinámico)
# ==============================================================================
with tab_cargar:
    # Usamos el form_key para que todo este bloque se reinicie
    with st.container(key=f"carga_cont_{st.session_state.form_key}"):
        st.subheader("1️⃣ Definir Prueba")
        
        col1, col2 = st.columns([1, 2])
        f_val = col1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = col2.selectbox("Nadador", [mi_nom_comp], disabled=True)
            id_nad_final = mi_id
        else:
            n_in = col2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar...")
            id_nad_final = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        col3, col4 = st.columns(2)
        est_val = col3.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
        dist_t_val = col4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            id_est = data['estilos'][data['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = data['distancias'][data['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_s = f_val.strftime('%Y-%m-%d')
            
            # Validación
            df_ent = data['entrenamientos'].copy()
            existe_db = False
            if not df_ent.empty:
                existe_db = not df_ent[(df_ent['codnadador'].astype(str) == str(id_nad_final)) & 
                                      (df_ent['fecha'].astype(str) == str(fecha_s)) & 
                                      (df_ent['codestilo'].astype(str) == str(id_est)) &
                                      (df_ent['coddistancia'].astype(str) == str(id_dt))].empty
            
            if existe_db:
                st.error("🚫 Ya existe este registro en la base de datos.")
            else:
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                
                if m_par > 0:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Parciales cada {m_par} mts.</div>", unsafe_allow_html=True)
                    quiere_parciales = st.toggle("¿Deseas cargar parciales?", value=True)
                else:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Regla automática: Sin parciales.</div>", unsafe_allow_html=True)
                    quiere_parciales = False

                st.divider()
                st.subheader("2️⃣ Registrar Tiempos")
                with st.form("f_registro", clear_on_submit=True):
                    tf1, tf_s1, tf2, tf_s2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                    tm_m = tf1.number_input("Min", 0, 59, 0)
                    tm_s = tf2.number_input("Seg", 0, 59, 0)
                    tm_c = tf3.number_input("Cent", 0, 99, 0)

                    tps = ["", "", "", ""]
                    if quiere_parciales:
                        for i in range(1, 5):
                            st.write(f"Parcial {i} ({m_par}m)")
                            c1, c2, c3 = st.columns(3)
                            pm = c1.number_input("M", 0, 59, 0, key=f"m_{i}")
                            ps = c2.number_input("S", 0, 59, 0, key=f"s_{i}")
                            pc = c3.number_input("C", 0, 99, 0, key=f"c_{i}")
                            if (pm+ps+pc) > 0: tps[i-1] = tiempo_str(pm, ps, pc)

                    obs = st.text_area("Observaciones")

                    if st.form_submit_button("📥 AGREGAR A COLA", use_container_width=True):
                        if (tm_m + tm_s + tm_c) == 0:
                            st.error("Falta el tiempo final.")
                        else:
                            id_dp = data['distancias'][data['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_parciales else ""
                            base_id = pd.to_numeric(df_ent['id_entrenamiento'], errors='coerce').max() if not df_ent.empty else 0
                            new_id = int(base_id if not pd.isna(base_id) else 0) + len(st.session_state.cola_tests) + 1
                            
                            st.session_state.cola_tests.append({
                                "id_entrenamiento": int(new_id), "fecha": fecha_s,
                                "codnadador": int(id_nad_final), "codestilo": id_est,
                                "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                "tiempo_final": tiempo_str(tm_m, tm_s, tm_c),
                                "parcial_1": tps[0], "parcial_2": tps[1], "parcial_3": tps[2], "parcial_4": tps[3],
                                "observaciones": obs
                            })
                            reset_form() # Incrementa la clave para limpiar el Paso 1
                            st.rerun()

# --- HISTORIAL Y SUBIDA ---
with tab_ver:
    t_id = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        s_n = st.selectbox("Historial de:", lista_nombres, index=None)
        if s_n: t_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == s_n].iloc[0]['codnadador']
    
    if t_id:
        df_h = data['entrenamientos'][data['entrenamientos']['codnadador'].astype(str) == str(t_id)].copy()
        if not df_h.empty:
            df_h = df_h.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], left_on='coddistancia', right_on='coddistancia', how='left').merge(data['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            for _, r in df_h.sort_values('fecha', ascending=False).iterrows():
                ps = [r.get(f'parcial_{i}') for i in range(1,5)]
                splits = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(ps) if p and str(p) not in ['nan','']])
                st.markdown(f"""<div class="test-card"><div class="test-header"><div><div class="test-style">{r.get('descripcion', '-')}</div><div class="test-dist">{r.get('descripcion_tot', '-')}</div><div class="test-date">📅 {datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')}</div></div><div class="final-time">{r['tiempo_final']}</div></div><div class="splits-grid">{splits}</div><div class="obs-box">📝 {r['observaciones']}</div></div>""", unsafe_allow_html=True)
        else: st.info("No hay registros.")

if st.session_state.cola_tests:
    st.divider()
    st.info(f"📋 {len(st.session_state.cola_tests)} tests en cola.")
    c1, c2 = st.columns(2)
    if c1.button("🚀 SUBIR TODO", type="primary", use_container_width=True):
        df_f = pd.concat([data['entrenamientos'], pd.DataFrame(st.session_state.cola_tests)], ignore_index=True)
        conn.update(worksheet="Entrenamientos", data=df_f)
        st.session_state.cola_tests = []; st.cache_data.clear()
        st.success("✅ Sincronizado."); st.rerun()
    if c2.button("🗑️ VACIAR COLA", use_container_width=True):
        st.session_state.cola_tests = []; st.rerun()
