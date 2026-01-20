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

# --- 🎨 ESTILOS CSS (MEJORADOS) ---
st.markdown("""
<style>
    /* Estilos del Historial */
    .test-card { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        border-radius: 12px; 
        padding: 18px; 
        margin-bottom: 16px; 
        border-left: 6px solid #E30613; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .test-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
    .style-title { font-size: 16px; font-weight: bold; color: #E30613; text-transform: uppercase; letter-spacing: 0.5px; }
    .date-label { font-size: 12px; color: #888; }
    
    .test-body { display: flex; justify-content: space-between; align-items: center; }
    .dist-label { font-size: 18px; color: #fff; font-weight: 500; }
    
    .final-time-box {
        background: #000;
        padding: 6px 14px;
        border-radius: 8px;
        border: 1px solid #444;
        font-family: 'Courier New', monospace;
        font-size: 22px;
        font-weight: bold;
        color: #FFD700;
        text-shadow: 0 0 5px rgba(255, 215, 0, 0.3);
    }

    .splits-container { 
        display: grid; 
        grid-template-columns: repeat(4, 1fr); 
        gap: 8px; 
        margin-top: 15px; 
        padding-top: 12px;
        border-top: 1px solid #333;
    }
    .split-pill { 
        background: #282828; 
        padding: 5px; 
        border-radius: 6px; 
        text-align: center;
        border: 1px solid #383838;
    }
    .split-num { font-size: 9px; color: #E30613; display: block; font-weight: bold; margin-bottom: 2px; }
    .split-time { font-family: monospace; font-size: 12px; color: #eee; }

    .note-box { 
        margin-top: 12px; 
        font-size: 12px; 
        color: #aaa; 
        font-style: italic; 
        background: rgba(255,255,255,0.03); 
        padding: 8px; 
        border-radius: 6px;
        border-left: 2px solid #444;
    }

    /* Estilos del Formulario */
    .section-title { color: #E30613; font-weight: bold; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #333; font-size: 14px; text-transform: uppercase; }
    .config-box { background: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #E30613; margin-bottom: 20px; }
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
nad_row = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_full = f"{nad_row.iloc[0]['apellido'].upper()}, {nad_row.iloc[0]['nombre']}" if not nad_row.empty else mi_nombre
lista_noms = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

def to_sec(m, s, c): return (int(m) * 60) + int(s) + (int(c) / 100)
def to_str(m, s, c): return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    with st.container(key=f"flow_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        if rol == "N":
            n_in = c2.selectbox("Nadador", [mi_nom_full], disabled=True)
            id_nad_final = mi_id
        else:
            n_in = c2.selectbox("Nadador", lista_noms, index=None, placeholder="Seleccionar...")
            id_nad_final = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None

        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            id_est = db['estilos'][db['estilos']['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = db['distancias'][db['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_s = f_val.strftime('%Y-%m-%d')
            
            df_ent = db['entrenamientos']
            existe = not df_ent[(df_ent['codnadador'].astype(str) == str(id_nad_final)) & 
                                (df_ent['fecha'].astype(str) == str(fecha_s)) & 
                                (df_ent['codestilo'].astype(str) == str(id_est)) &
                                (df_ent['coddistancia'].astype(str) == str(id_dt))].empty if not df_ent.empty else False
            
            if existe:
                st.error("🚫 Ya existe un registro para esta configuración en la fecha seleccionada.")
            else:
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True) if m_par > 0 else False

                st.divider()
                st.subheader("2. Registrar Tiempos")
                with st.form("f_registro"):
                    st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                    st.text_input("Distancia", value=dist_t_val, disabled=True, label_visibility="collapsed")
                    tf1, ts1, tf2, ts2, tf3 = st.columns([1, 0.2, 1, 0.2, 1])
                    mf = tf1.number_input("Min", 0, 59, 0)
                    sf = tf2.number_input("Seg", 0, 59, 0)
                    cf = tf3.number_input("Cent", 0, 99, 0)

                    lp = []
                    if quiere_p:
                        st.markdown(f"<div class='section-title'>PARCIALES ({m_par}m)</div>", unsafe_allow_html=True)
                        for i in range(1, 5):
                            st.write(f"P{i}")
                            px1, px2, px3, px4 = st.columns([1, 1, 1, 1])
                            px1.text_input(f"d{i}", value=f"{m_par}m", disabled=True, label_visibility="collapsed")
                            pm = px2.number_input("M", 0, 59, 0, key=f"pm_{i}", label_visibility="collapsed")
                            ps = px3.number_input("S", 0, 59, 0, key=f"ps_{i}", label_visibility="collapsed")
                            pc = px4.number_input("C", 0, 99, 0, key=f"pc_{i}", label_visibility="collapsed")
                            lp.append((pm, ps, pc))

                    obs = st.text_area("Observaciones")
                    if st.form_submit_button("GUARDAR", use_container_width=True):
                        s_f = to_sec(mf, sf, cf)
                        if s_f == 0: st.error("Tiempo obligatorio.")
                        else:
                            valido = True
                            if quiere_p:
                                s_p = sum([to_sec(p[0], p[1], p[2]) for p in lp])
                                if s_p > 0 and abs(s_p - s_f) > 0.5:
                                    st.error(f"Incoherencia: Suma parciales {s_p:.2f}s vs Final {s_f:.2f}s.")
                                    valido = False
                            if valido:
                                mid = pd.to_numeric(df_ent['id_entrenamiento'], errors='coerce').max() if not df_ent.empty else 0
                                nid = int(0 if pd.isna(mid) else mid) + 1
                                id_dp = db['distancias'][db['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_p else ""
                                row = pd.DataFrame([{
                                    "id_entrenamiento": nid, "fecha": fecha_s, "codnadador": int(id_nad_final), "codestilo": id_est, "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                    "tiempo_final": to_str(mf, sf, cf),
                                    "parcial_1": to_str(*lp[0]) if len(lp)>0 and sum(lp[0])>0 else "",
                                    "parcial_2": to_str(*lp[1]) if len(lp)>1 and sum(lp[1])>0 else "",
                                    "parcial_3": to_str(*lp[2]) if len(lp)>2 and sum(lp[2])>0 else "",
                                    "parcial_4": to_str(*lp[3]) if len(lp)>3 and sum(lp[3])>0 else "",
                                    "observaciones": obs
                                }])
                                conn.update(worksheet="Entrenamientos", data=pd.concat([df_ent, row], ignore_index=True))
                                st.cache_data.clear()
                                reset_carga()
                                st.success("Guardado.")
                                st.rerun()

# ==============================================================================
#  HISTORIAL
# ==============================================================================
with tab_ver:
    tid_h = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sn_h = st.selectbox("Historial de:", lista_noms, index=None, key="hsel")
        if sn_h: tid_h = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sn_h].iloc[0]['codnadador']
    
    if tid_h:
        df_h = db['entrenamientos'][db['entrenamientos']['codnadador'].astype(str) == str(tid_h)].copy()
        if not df_h.empty:
            df_h = df_h.merge(db['estilos'], on='codestilo', how='left').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            for _, r in df_h.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                
                # HTML para Parciales
                p_html = ""
                for i in range(1, 5):
                    val = r.get(f'parcial_{i}')
                    if val and str(val) not in ['nan','None','']:
                        p_html += f"<div class='split-pill'><span class='split-num'>P{i}</span><span class='split-time'>{val}</span></div>"

                # HTML para Notas
                n_html = f"<div class='note-box'>📝 {r['observaciones']}</div>" if str(r['observaciones']) not in ['nan','None',''] else ""
                
                fmt_f = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <span class="style-title">{r.get('descripcion', '-')}</span>
                        <span class="date-label">📅 {fmt_f}</span>
                    </div>
                    <div class="test-body">
                        <span class="dist-label">{r.get('descripcion_tot', '-')}</span>
                        <div class="final-time-box">{r['tiempo_final']}</div>
                    </div>
                    <div class="splits-container">{p_html}</div>
                    {n_html}
                </div>""", unsafe_allow_html=True)
        else: st.info("No hay registros.")
