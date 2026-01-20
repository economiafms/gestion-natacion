import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Entrenamientos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Acceso restringido.")
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* TARJETA DE ENTRENAMIENTO (VISUALIZACIÓN) */
    .test-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
    .test-header {
        display: flex; justify-content: space-between; align-items: flex-start;
        border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px;
    }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #4CAF50; font-weight: bold; margin-top: 2px; }
    .test-date { font-size: 12px; color: #aaa; margin-top: 4px; }
    
    .test-result { text-align: right; }
    .final-time { font-family: monospace; font-size: 22px; font-weight: bold; color: #FFD700; }
    .final-label { font-size: 10px; color: #888; text-transform: uppercase; }

    /* PARCIALES EN CARD */
    .splits-grid {
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px;
        margin-top: 10px; padding-top: 8px; border-top: 1px dashed #444;
    }
    .split-item {
        background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; text-align: center;
    }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; font-weight: bold; }
    
    .obs-box { margin-top: 8px; font-size: 12px; color: #bbb; font-style: italic; background: rgba(0,0,0,0.2); padding: 5px; border-radius: 4px;}

    /* ESTILOS DE CARGA (INPUTS) */
    .time-sep { text-align: center; font-size: 20px; font-weight: bold; margin-top: 28px; color: #fff; }
    .partial-label { font-size: 12px; color: #888; margin-bottom: 2px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. INICIALIZAR COLA DE CARGA ---
if "cola_tests" not in st.session_state: st.session_state.cola_tests = []

def refrescar_datos():
    st.cache_data.clear()
    st.rerun()

# --- 3. CARGA DE DATOS ---
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
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())

# Filtrado de Distancias para Selectores
all_dist = data['distancias']['descripcion'].unique().tolist()
# Lista Total: Excluir 25 y 4x...
list_dist_total = [d for d in all_dist if "25" not in d and "4x" not in d.lower()]
# Lista Parcial: Solo 25, 50, 100
list_dist_parcial = [d for d in all_dist if d.startswith("25 ") or d.startswith("50 ") or d.startswith("100 ")]

# Separadores visuales
sep_html = "<div class='time-sep'>:</div>"
sep_dot_html = "<div class='time-sep'>.</div>"

# --- FUNCIONES ---
def tiempo_str(m, s, c):
    return f"{int(m):02d}:{int(s):02d}.{int(c):02d}"

# ==============================================================================
#  PANEL DE SINCRONIZACIÓN (COLA DE CARGA)
# ==============================================================================
if len(st.session_state.cola_tests) > 0:
    st.markdown("### ☁️ Sincronización Pendiente")
    st.info(f"Tienes **{len(st.session_state.cola_tests)} tests** listos para guardar en la nube.")
    
    c1, c2 = st.columns([1, 1])
    if c1.button("🚀 SUBIR TODO A GOOGLE SHEETS", type="primary", use_container_width=True):
        try:
            with st.spinner("Guardando datos..."):
                df_cola = pd.DataFrame(st.session_state.cola_tests)
                df_final = pd.concat([data['entrenamientos'], df_cola], ignore_index=True)
                conn.update(worksheet="Entrenamientos", data=df_final)
                
                st.session_state.cola_tests = []
                st.success("✅ ¡Entrenamientos guardados correctamente!")
                refrescar_datos()
        except Exception as e:
            st.error(f"Error al guardar: {str(e)}")
            
    if c2.button("🗑️ Descartar Cola", use_container_width=True):
        st.session_state.cola_tests = []
        st.rerun()
    st.divider()

# ==============================================================================
#  PESTAÑAS PRINCIPALES
# ==============================================================================
tab_ver, tab_cargar = st.tabs(["📂 Historial de Tests", "📝 Cargar Test"])

# ------------------------------------------------------------------------------
#  PESTAÑA 1: VER HISTORIAL
# ------------------------------------------------------------------------------
with tab_ver:
    target_id = None
    if rol in ["M", "P"]:
        st.markdown("##### 🔍 Consultar Nadador")
        idx_def = 0
        if "nadador_seleccionado" in st.session_state and st.session_state.nadador_seleccionado in lista_nombres:
            idx_def = lista_nombres.index(st.session_state.nadador_seleccionado)
        sel_nadador = st.selectbox("Seleccionar Atleta:", lista_nombres, index=idx_def)
        if sel_nadador:
            st.session_state.nadador_seleccionado = sel_nadador
            target_id = df_nad[df_nad['Nombre Completo'] == sel_nadador].iloc[0]['codnadador']
    else:
        st.markdown(f"##### 👤 Mis Tests: {mi_nombre}")
        target_id = mi_id

    if target_id:
        df_show = data['entrenamientos'][data['entrenamientos']['codnadador'] == target_id].copy()
        
        if not df_show.empty:
            df_show = df_show.merge(data['estilos'], on='codestilo', how='left')
            df_show = df_show.merge(data['distancias'], left_on='coddistancia', right_on='coddistancia', how='left', suffixes=('', '_tot'))
            df_show = df_show.merge(data['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            
            col_est = 'descripcion' if 'descripcion' in df_show.columns else 'descripcion_tot'
            if 'descripcion_x' in df_show.columns: col_est = 'descripcion_x'
            
            df_show = df_show.sort_values('fecha', ascending=False)
            
            for _, r in df_show.iterrows():
                estilo_nom = r.get(col_est, '-')
                dist_tot = r.get('descripcion_tot', '-')
                dist_par = r.get('descripcion_par', '-')
                
                ps = [r.get('parcial_1'), r.get('parcial_2'), r.get('parcial_3'), r.get('parcial_4')]
                splits_html = ""
                if any(p and str(p) not in ['nan', 'None', '', '0'] for p in ps):
                    items = ""
                    for i, p in enumerate(ps):
                        if p and str(p) not in ['nan', 'None', '', '0', '00:00.00']:
                            items += f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>"
                    splits_html = f"<div class='splits-grid'>{items}</div>"

                st.markdown(f"""
                <div class="test-card">
                    <div class="test-header">
                        <div style="flex:1;">
                            <div class="test-style">{estilo_nom}</div>
                            <div class="test-dist">{dist_tot} <span style="font-weight:normal; color:#888; font-size:12px;">(Parciales: {dist_par})</span></div>
                            <div class="test-date">📅 {r['fecha']}</div>
                        </div>
                        <div class="test-result">
                            <div class="final-time">{r['tiempo_final']}</div>
                            <div class="final-label">TIEMPO FINAL</div>
                        </div>
                    </div>
                    {splits_html}
                    <div class="obs-box">
                        📝 {r['observaciones'] if str(r['observaciones']) not in ['nan', 'None'] else 'Sin observaciones.'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No se encontraron registros de entrenamiento.")

# ------------------------------------------------------------------------------
#  PESTAÑA 2: CARGAR TEST (MODIFICADO)
# ------------------------------------------------------------------------------
with tab_cargar:
    st.subheader("Alta de Test de Progreso")
    
    with st.form("form_test", clear_on_submit=True):
        # FILA 1: FECHA Y NADADOR
        c_fec, c_nad = st.columns([1, 2])
        fecha = c_fec.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        # Selección inteligente de nadador
        if rol in ["M", "P"]:
            nadador_input = c_nad.selectbox("Nadador", lista_nombres, index=None, placeholder="Buscar...")
        else:
            try: idx_me = lista_nombres.index(mi_nombre)
            except: idx_me = 0
            nadador_input = c_nad.selectbox("Nadador", lista_nombres, index=idx_me, disabled=True)
        
        # FILA 2: CONFIGURACIÓN
        st.markdown("🏊 **Configuración de la Prueba**")
        c_est, c_dtot, c_dpar = st.columns(3)
        estilo = c_est.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
        
        # Distancias Filtradas
        dist_total = c_dtot.selectbox("Distancia TOTAL", list_dist_total, index=None, placeholder="Ej: 200 mts")
        dist_parcial = c_dpar.selectbox("Distancia PARCIAL", list_dist_parcial, index=None, placeholder="Ej: 50 mts")
        
        st.markdown("---")
        
        # FILA 3: TIEMPO FINAL (CAJA GRANDE)
        st.markdown("##### ⏱️ Tiempo Final")
        
        ct1, ct2, ct3, ct4, ct5 = st.columns([1, 0.2, 1, 0.2, 1])
        with ct1: tm_m = st.number_input("Min", 0, 59, 0, key="main_m", format="%02d")
        with ct2: st.markdown(sep_html, unsafe_allow_html=True)
        with ct3: tm_s = st.number_input("Seg", 0, 59, 0, key="main_s", format="%02d")
        with ct4: st.markdown(sep_dot_html, unsafe_allow_html=True)
        with ct5: tm_c = st.number_input("Cent", 0, 99, 0, key="main_c", format="%02d")
        
        st.markdown("") # Espacio

        # FILA 4: PARCIALES (GRILLA 2x2 con CAJAS COMPLETAS)
        label_parcial = dist_parcial if dist_parcial else "---"
        st.markdown(f"##### 📊 Parciales (cada {label_parcial})")
        
        # PARCIALES 1 y 2
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            st.markdown(f"<div class='partial-label'>PARCIAL 1 ({label_parcial})</div>", unsafe_allow_html=True)
            p1_m, s1, p1_s, s2, p1_c = st.columns([1, 0.2, 1, 0.2, 1])
            pm1 = p1_m.number_input("m1", 0, 59, 0, label_visibility="collapsed", key="p1m", format="%02d")
            p1_s.number_input("s1", 0, 59, 0, label_visibility="collapsed", key="p1s", format="%02d")
            p1_c.number_input("c1", 0, 99, 0, label_visibility="collapsed", key="p1c", format="%02d")
            
        with col_p2:
            st.markdown(f"<div class='partial-label'>PARCIAL 2 ({label_parcial})</div>", unsafe_allow_html=True)
            p2_m, s1, p2_s, s2, p2_c = st.columns([1, 0.2, 1, 0.2, 1])
            pm2 = p2_m.number_input("m2", 0, 59, 0, label_visibility="collapsed", key="p2m", format="%02d")
            p2_s.number_input("s2", 0, 59, 0, label_visibility="collapsed", key="p2s", format="%02d")
            p2_c.number_input("c2", 0, 99, 0, label_visibility="collapsed", key="p2c", format="%02d")

        # PARCIALES 3 y 4 (Nueva Fila)
        st.write("") # Margin
        col_p3, col_p4 = st.columns(2)
        
        with col_p3:
            st.markdown(f"<div class='partial-label'>PARCIAL 3 ({label_parcial})</div>", unsafe_allow_html=True)
            p3_m, s1, p3_s, s2, p3_c = st.columns([1, 0.2, 1, 0.2, 1])
            pm3 = p3_m.number_input("m3", 0, 59, 0, label_visibility="collapsed", key="p3m", format="%02d")
            p3_s.number_input("s3", 0, 59, 0, label_visibility="collapsed", key="p3s", format="%02d")
            p3_c.number_input("c3", 0, 99, 0, label_visibility="collapsed", key="p3c", format="%02d")

        with col_p4:
            st.markdown(f"<div class='partial-label'>PARCIAL 4 ({label_parcial})</div>", unsafe_allow_html=True)
            p4_m, s1, p4_s, s2, p4_c = st.columns([1, 0.2, 1, 0.2, 1])
            pm4 = p4_m.number_input("m4", 0, 59, 0, label_visibility="collapsed", key="p4m", format="%02d")
            p4_s.number_input("s4", 0, 59, 0, label_visibility="collapsed", key="p4s", format="%02d")
            p4_c.number_input("c4", 0, 99, 0, label_visibility="collapsed", key="p4c", format="%02d")

        st.markdown("---")
        
        # OBSERVACIONES
        obs = st.text_area("Observaciones (Máx 400 car.)", placeholder="Aspectos técnicos a mejorar...", max_chars=400, height=80)
        
        submitted = st.form_submit_button("Agregar a la Cola 📥", use_container_width=True)
        
        if submitted:
            if nadador_input and estilo and dist_total and dist_parcial:
                # Recuperar IDs
                id_nad = df_nad[df_nad['Nombre Completo'] == nadador_input]['codnadador'].values[0]
                id_est = data['estilos'][data['estilos']['descripcion'] == estilo]['codestilo'].values[0]
                id_dtot = data['distancias'][data['distancias']['descripcion'] == dist_total]['coddistancia'].values[0]
                id_dpar = data['distancias'][data['distancias']['descripcion'] == dist_parcial]['coddistancia'].values[0]
                
                # ID incremental base + cola
                base_id = data['entrenamientos']['id_entrenamiento'].max() if not data['entrenamientos'].empty else 0
                new_id = int(base_id) + len(st.session_state.cola_tests) + 1
                
                # Formatear tiempos (solo si son distintos de 00:00.00 para parciales)
                t_final = tiempo_str(tm_m, tm_s, tm_c)
                
                # Función auxiliar para parciales: si es 0, guarda string vacio o 00:00.00? Mejor guardar el string formateado si > 0
                def get_p_val(m, s, c):
                    return tiempo_str(m, s, c) if (m+s+c) > 0 else ""

                # Recuperar valores de los widgets de parciales (accediendo a session state por key)
                # Nota: dentro del form, los widgets se bindean al submit.
                # Usamos st.session_state["p1m"] etc.
                
                # REGLA STREAMLIT FORM: Los valores ya están disponibles en las variables asignadas arriba (pm1, etc) al momento del submit
                # pero st.number_input devuelve el valor.
                # Re-lectura: asigne el return a variables (pm1, etc). Usamos esas.
                # Pero en las columnas comprimidas no asigne variables a segundos/cent.
                # Corrección rápida: Acceder por key es más seguro en layouts complejos.
                
                tp1 = get_p_val(st.session_state.p1m, st.session_state.p1s, st.session_state.p1c)
                tp2 = get_p_val(st.session_state.p2m, st.session_state.p2s, st.session_state.p2c)
                tp3 = get_p_val(st.session_state.p3m, st.session_state.p3s, st.session_state.p3c)
                tp4 = get_p_val(st.session_state.p4m, st.session_state.p4s, st.session_state.p4c)

                nuevo_registro = {
                    "id_entrenamiento": new_id,
                    "fecha": fecha.strftime('%Y-%m-%d'),
                    "codnadador": id_nad,
                    "codestilo": id_est,
                    "coddistancia": id_dtot,
                    "coddistancia_parcial": id_dpar,
                    "tiempo_final": t_final,
                    "parcial_1": tp1, "parcial_2": tp2, "parcial_3": tp3, "parcial_4": tp4,
                    "observaciones": obs
                }
                
                st.session_state.cola_tests.append(nuevo_registro)
                st.success(f"✅ Test para {nadador_input} agregado a la cola.")
                st.rerun()
            else:
                st.warning("⚠️ Faltan datos obligatorios (Nadador, Estilo o Distancias).")
