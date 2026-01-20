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

# --- GESTIÓN DE RESETEO (Clave dinámica para limpiar Paso 1 y Paso 2) ---
if "form_reset_id" not in st.session_state:
    st.session_state.form_reset_id = 0

def ejecutar_reinicio():
    st.session_state.form_reset_id += 1

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO (Estructura completa restaurada) ---
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

db_all = cargar_entrenamientos()
if not db_all: st.stop()

# --- PROCESAMIENTO DE DATOS ---
df_nad = db_all['nadadores'].copy()
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_full = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_nombres = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db_all['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

def to_sec(m, s, c): return (int(m) * 60) + int(s) + (int(c) / 100)
def to_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

# Mantenemos la pestaña actual en el session_state para no saltar al Historial al guardar
if "tab_activa" not in st.session_state:
    st.session_state.tab_activa = 0

tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST (UNO A UNO - DIRECTO A SHEETS)
# ==============================================================================
with tab_cargar:
    # Contenedor con ID dinámico para limpiar todo al guardar
    with st.container(key=f"main_flow_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nom_full], disabled=True)
            id_nad_final = mi_id
        else:
            n_in = c2.selectbox("Nadador", lista_nombres, index=None, placeholder="Seleccionar nadador...")
            id_nad_final = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db_all['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            id_est = db_all['estilos'][db_all['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = db_all['distancias'][db_all['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_s = f_val.strftime('%Y-%m-%d')
            
            # Validación de duplicados en la base de datos
            df_ent = db_all['entrenamientos']
            existe = False
            if not df_ent.empty:
                existe = not df_ent[(df_ent['codnadador'].astype(str) == str(id_nad_final)) & 
                                    (df_ent['fecha'].astype(str) == str(fecha_s)) & 
                                    (df_ent['codestilo'].astype(str) == str(id_est)) &
                                    (df_ent['coddistancia'].astype(str) == str(id_dt))].empty
            
            if existe:
                st.error(f"🚫 Ya existe un test de {dist_t_val} en {est_val} para este nadador el día {f_val.strftime('%d/%m/%Y')}.")
            else:
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                
                if m_par > 0:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Regla automática: Parciales cada {m_par} mts.</div>", unsafe_allow_html=True)
                    quiere_parciales = st.toggle("¿Cargar tiempos parciales?", value=True)
                else:
                    st.markdown(f"<div class='config-box'><b>Configuración:</b> {dist_t_val} {est_val}.<br>Regla automática: Sin parciales.</div>", unsafe_allow_html=True)
                    quiere_parciales = False

                st.divider()
                st.subheader("2. Registrar Tiempos")
                
                with st.form("f_registro_final"):
                    st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                    tf1, ts1, tf2, ts2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                    m_f = tf1.number_input("Min", 0, 59, 0, format="%02d")
                    s_f = tf2.number_input("Seg", 0, 59, 0, format="%02d")
                    c_f = tf3.number_input("Cent", 0, 99, 0, format="%02d")

                    data_parciales = []
                    if quiere_parciales:
                        st.markdown(f"<div class='section-title'>PARCIALES ({m_par} mts)</div>", unsafe_allow_html=True)
                        for i in range(1, 5):
                            st.write(f"Parcial {i}")
                            px1, px2, px3 = st.columns(3)
                            pm = px1.number_input("M", 0, 59, 0, key=f"pm_{i}", format="%02d")
                            ps = px2.number_input("S", 0, 59, 0, key=f"ps_{i}", format="%02d")
                            pc = px3.number_input("C", 0, 99, 0, key=f"pc_{i}", format="%02d")
                            data_parciales.append((pm, ps, pc))

                    st.write("")
                    obs = st.text_area("Observaciones")

                    submit = st.form_submit_button("GUARDAR REGISTRO Y REINICIAR", use_container_width=True)

                    if submit:
                        seg_final = to_sec(m_f, s_f, c_f)
                        
                        if seg_final == 0:
                            st.error("El tiempo final es obligatorio.")
                        else:
                            # VALIDACIÓN DE COHERENCIA (BLOQUEANTE)
                            error_time = False
                            if quiere_parciales:
                                suma_p = sum([to_sec(p[0], p[1], p[2]) for p in data_parciales])
                                if suma_p > 0 and abs(suma_p - seg_final) > 0.5:
                                    st.error(f"❌ Error de Coherencia: La suma de parciales ({suma_p:.2f}s) no coincide con el tiempo final ({seg_final:.2f}s). Por favor corrige los tiempos.")
                                    error_time = True
                            
                            if not error_time:
                                with st.spinner("Guardando..."):
                                    try:
                                        max_id = pd.to_numeric(df_ent['id_entrenamiento'], errors='coerce').max() if not df_ent.empty else 0
                                        new_id = int(0 if pd.isna(max_id) else max_id) + 1
                                        id_dp = db_all['distancias'][db_all['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_parciales else ""
                                        
                                        nuevo_registro = pd.DataFrame([{
                                            "id_entrenamiento": new_id, "fecha": fecha_s,
                                            "codnadador": int(id_nad_final), "codestilo": id_est,
                                            "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                            "tiempo_final": to_str(m_f, s_f, c_f),
                                            "parcial_1": to_str(*data_parciales[0]) if len(data_parciales)>0 and sum(data_parciales[0])>0 else "",
                                            "parcial_2": to_str(*data_parciales[1]) if len(data_parciales)>1 and sum(data_parciales[1])>0 else "",
                                            "parcial_3": to_str(*data_parciales[2]) if len(data_parciales)>2 and sum(data_parciales[2])>0 else "",
                                            "parcial_4": to_str(*data_parciales[3]) if len(data_parciales)>3 and sum(data_parciales[3])>0 else "",
                                            "observaciones": obs
                                        }])
                                        
                                        df_upd = pd.concat([df_ent, nuevo_registro], ignore_index=True)
                                        conn.update(worksheet="Entrenamientos", data=df_upd)
                                        
                                        st.cache_data.clear()
                                        ejecutar_reinicio() # Esto limpia el Paso 1 y Paso 2
                                        st.success("✅ Registro guardado con éxito.")
                                        st.rerun() # Recarga y se mantiene en esta pestaña por defecto
                                    except Exception as e:
                                        st.error(f"Error técnico: {e}")

# ==============================================================================
#  HISTORIAL (Restaurado completo)
# ==============================================================================
with tab_ver:
    t_id_h = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        s_n_h = st.selectbox("Consultar historial de:", lista_nombres, index=None, key="hist_nad")
        if s_n_h: t_id_h = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == s_n_h].iloc[0]['codnadador']
    
    if t_id_h:
        df_h = db_all['entrenamientos'][db_all['entrenamientos']['codnadador'].astype(str) == str(t_id_h)].copy()
        if not df_h.empty:
            df_h = df_h.merge(db_all['estilos'], on='codestilo', how='left').merge(db_all['distancias'], left_on='coddistancia', right_on='coddistancia', how='left').merge(db_all['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
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
        else: st.info("No se encontraron registros.")
