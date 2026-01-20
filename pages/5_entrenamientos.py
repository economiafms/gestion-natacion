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

def reset_carga():
    st.session_state.form_reset_id += 1

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO (Historial original restaurado) ---
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
    .section-title { color: #E30613; font-weight: bold; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #333; font-size: 14px; text-transform: uppercase; }
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

# --- PROCESAMIENTO ---
df_nad = db_data['nadadores'].copy()
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db_data['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

def to_sec(m, s, c): return (int(m) * 60) + int(s) + (int(c) / 100)
def to_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST (UNO A UNO)
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_directa_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nom_comp], disabled=True)
            id_nad_final = mi_id
        else:
            n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar...")
            id_nad_final = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db_data['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            id_est = db_data['estilos'][db_data['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = db_data['distancias'][db_data['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_s = f_val.strftime('%Y-%m-%d')
            
            # Validación de duplicados
            df_ent = db_data['entrenamientos']
            existe = False
            if not df_ent.empty:
                existe = not df_ent[(df_ent['codnadador'].astype(str) == str(id_nad_final)) & 
                                    (df_ent['fecha'].astype(str) == str(fecha_s)) & 
                                    (df_ent['codestilo'].astype(str) == str(id_est)) &
                                    (df_ent['coddistancia'].astype(str) == str(id_dt))].empty
            
            if existe:
                st.error("🚫 Ya existe un registro para esta configuración en la fecha seleccionada.")
            else:
                # Regla de parciales
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                
                quiere_p = False
                if m_par > 0:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Parciales cada {m_par} mts.</div>", unsafe_allow_html=True)
                    quiere_p = st.toggle("¿Deseas cargar tiempos parciales?", value=True)
                else:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Regla automática: Sin parciales.</div>", unsafe_allow_html=True)

                st.divider()
                st.subheader("2. Registrar Tiempos")
                
                with st.form("form_carga_final"):
                    st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                    tf1, ts1, tf2, ts2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                    mf = tf1.number_input("Min", 0, 59, 0, format="%02d")
                    sf = tf2.number_input("Seg", 0, 59, 0, format="%02d")
                    cf = tf3.number_input("Cent", 0, 99, 0, format="%02d")

                    lista_parciales = []
                    if quiere_p:
                        st.markdown(f"<div class='section-title'>PARCIALES ({m_par} mts)</div>", unsafe_allow_html=True)
                        for i in range(1, 5):
                            st.write(f"Parcial {i}")
                            px1, px2, px3, px4 = st.columns([1, 1, 1, 1])
                            px1.text_input(f"D_{i}", value=f"{m_par} mts", disabled=True, label_visibility="collapsed")
                            pm = px2.number_input("M", 0, 59, 0, key=f"pm_{i}", format="%02d", label_visibility="collapsed")
                            ps = px3.number_input("S", 0, 59, 0, key=f"ps_{i}", format="%02d", label_visibility="collapsed")
                            pc = px4.number_input("C", 0, 99, 0, key=f"pc_{i}", format="%02d", label_visibility="collapsed")
                            lista_parciales.append((pm, ps, pc))

                    st.write("")
                    obs = st.text_area("Observaciones")

                    if st.form_submit_button("GUARDAR Y REINICIAR", use_container_width=True):
                        s_final = to_sec(mf, sf, cf)
                        if s_final == 0:
                            st.error("El tiempo final es obligatorio.")
                        else:
                            # Validación de Coherencia Bloqueante
                            valido = True
                            if quiere_p:
                                s_parciales = sum([to_sec(p[0], p[1], p[2]) for p in lista_parciales])
                                if s_parciales > 0 and abs(s_parciales - s_final) > 0.5:
                                    st.error(f"❌ Error: La suma de parciales ({s_parciales:.2f}s) no coincide con el final ({s_final:.2f}s). Corrija antes de guardar.")
                                    valido = False
                            
                            if valido:
                                try:
                                    max_id = pd.to_numeric(df_ent['id_entrenamiento'], errors='coerce').max() if not df_ent.empty else 0
                                    new_id = int(0 if pd.isna(max_id) else max_id) + 1
                                    id_dp = db_data['distancias'][db_data['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_p else ""
                                    
                                    nuevo_reg = pd.DataFrame([{
                                        "id_entrenamiento": new_id, "fecha": fecha_s,
                                        "codnadador": int(id_nad_final), "codestilo": id_est,
                                        "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                        "tiempo_final": to_str(mf, sf, cf),
                                        "parcial_1": to_str(*lista_parciales[0]) if len(lista_parciales)>0 and sum(lista_parciales[0])>0 else "",
                                        "parcial_2": to_str(*lista_parciales[1]) if len(lista_parciales)>1 and sum(lista_parciales[1])>0 else "",
                                        "parcial_3": to_str(*lista_parciales[2]) if len(lista_parciales)>2 and sum(lista_parciales[2])>0 else "",
                                        "parcial_4": to_str(*lista_parciales[3]) if len(lista_parciales)>3 and sum(lista_parciales[3])>0 else "",
                                        "observaciones": obs
                                    }])
                                    
                                    conn.update(worksheet="Entrenamientos", data=pd.concat([df_ent, nuevo_reg], ignore_index=True))
                                    st.cache_data.clear()
                                    reset_carga() # Limpia Paso 1 y Paso 2
                                    st.success("✅ Guardado con éxito.")
                                    st.rerun()
                                except Exception as e: st.error(f"Error al guardar: {e}")

# ==============================================================================
#  HISTORIAL (ORIGINAL RESTAURADO)
# ==============================================================================
with tab_ver:
    t_id_h = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        s_n_h = st.selectbox("Historial de:", lista_nombres, index=None, key="hist_nad")
        if s_n_h: t_id_h = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == s_n_h].iloc[0]['codnadador']
    
    if t_id_h:
        df_h = db_data['entrenamientos'][db_data['entrenamientos']['codnadador'].astype(str) == str(t_id_h)].copy()
        if not df_h.empty:
            df_h = df_h.merge(db_data['estilos'], on='codestilo', how='left').merge(db_data['distancias'], left_on='coddistancia', right_on='coddistancia', how='left').merge(db_data['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            for _, r in df_h.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                ps = [r.get(f'parcial_{i}') for i in range(1,5)]
                splits = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(ps) if p and str(p) not in ['nan','']])
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_tot', '-')}</div>
                            <div class="test-date">📅 {f_fmt}</div>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    <div class="splits-grid">{splits}</div>
                    <div class="obs-box">📝 {r['observaciones'] if str(r['observaciones']) not in ['nan','None',''] else 'Sin observaciones.'}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("No hay registros.")
