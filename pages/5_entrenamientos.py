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
    /* TARJETA DE ENTRENAMIENTO */
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

    /* PARCIALES */
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
                # Concatenar asegurando columnas
                df_final = pd.concat([data['entrenamientos'], df_cola], ignore_index=True)
                conn.update(worksheet="Entrenamientos", data=df_final)
                
                st.session_state.cola_tests = [] # Limpiar cola
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
#  PESTAÑA 1: VER HISTORIAL (LÓGICA DIFERENCIADA POR ROL)
# ------------------------------------------------------------------------------
with tab_ver:
    target_id = None
    
    # --- ROL MAESTRO (M): SELECCIONA A CUALQUIERA ---
    if rol in ["M", "P"]:
        st.markdown("##### 🔍 Consultar Nadador")
        
        # Lógica de preselección para mantener el estado
        idx_def = 0
        if "nadador_seleccionado" in st.session_state and st.session_state.nadador_seleccionado in lista_nombres:
            idx_def = lista_nombres.index(st.session_state.nadador_seleccionado)
            
        sel_nadador = st.selectbox("Seleccionar Atleta:", lista_nombres, index=idx_def)
        
        if sel_nadador:
            st.session_state.nadador_seleccionado = sel_nadador
            target_id = df_nad[df_nad['Nombre Completo'] == sel_nadador].iloc[0]['codnadador']
            
    # --- ROL NADADOR (N): SOLO SE VE A SÍ MISMO ---
    else:
        st.markdown(f"##### 👤 Mis Tests: {mi_nombre}")
        target_id = mi_id

    # --- RENDERIZADO DE TARJETAS (IGUAL PARA AMBOS) ---
    if target_id:
        df_show = data['entrenamientos'][data['entrenamientos']['codnadador'] == target_id].copy()
        
        if not df_show.empty:
            # Cruces de Datos
            df_show = df_show.merge(data['estilos'], on='codestilo', how='left')
            # Cruce Distancia Total
            df_show = df_show.merge(data['distancias'], left_on='coddistancia', right_on='coddistancia', how='left', suffixes=('', '_tot'))
            # Cruce Distancia Parcial
            df_show = df_show.merge(data['distancias'], left_on='coddistancia_parcial', right_on='coddistancia', how='left', suffixes=('_tot', '_par'))
            
            # Limpieza de nombres de columnas tras merge
            # Estilo
            col_est = 'descripcion' if 'descripcion' in df_show.columns else 'descripcion_tot' # Fallback
            if 'descripcion_x' in df_show.columns: col_est = 'descripcion_x' # Si pandas hizo suffixes raros
            
            # Ordenar
            df_show = df_show.sort_values('fecha', ascending=False)
            
            for _, r in df_show.iterrows():
                # Obtener nombres seguros
                estilo_nom = r.get(col_est, r.get('descripcion', '-'))
                # Distancia Total (descripcion_tot)
                dist_tot = r.get('descripcion_tot', '-')
                # Distancia Parcial (descripcion_par)
                dist_par = r.get('descripcion_par', '-')
                
                # Armar HTML Parciales
                ps = [r.get('parcial_1'), r.get('parcial_2'), r.get('parcial_3'), r.get('parcial_4')]
                splits_html = ""
                if any(p and str(p) not in ['nan', 'None', '', '0'] for p in ps):
                    items = ""
                    for i, p in enumerate(ps):
                        if p and str(p) not in ['nan', 'None', '', '0']:
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
#  PESTAÑA 2: CARGAR TEST (COMÚN PARA AMBOS, CON SELECTOR INTELIGENTE)
# ------------------------------------------------------------------------------
with tab_cargar:
    st.subheader("Alta de Test de Progreso")
    
    with st.form("form_test", clear_on_submit=True):
        # 1. Quién y Cuándo
        c_fec, c_nad = st.columns([1, 2])
        fecha = c_fec.date_input("Fecha", date.today())
        
        # Lógica Selector Nadador en Carga
        if rol in ["M", "P"]:
            # Profe ve a todos
            nadador_input = c_nad.selectbox("Nadador", lista_nombres, index=None, placeholder="Buscar...")
        else:
            # Nadador se ve a sí mismo (bloqueado o única opción)
            # Usamos index del usuario actual
            try:
                idx_me = lista_nombres.index(mi_nombre)
            except: idx_me = 0
            nadador_input = c_nad.selectbox("Nadador", lista_nombres, index=idx_me, disabled=True)
        
        # 2. Configuración
        st.markdown("🏊 **Configuración de la Prueba**")
        c_est, c_dtot, c_dpar = st.columns(3)
        
        estilo = c_est.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
        lista_dist = data['distancias']['descripcion'].unique()
        dist_total = c_dtot.selectbox("Distancia TOTAL", lista_dist, index=None, placeholder="Ej: 200 mts")
        dist_parcial = c_dpar.selectbox("Distancia PARCIAL", lista_dist, index=None, placeholder="Ej: 50 mts")
        
        st.markdown("---")
        
        # 3. Tiempos
        st.markdown("⏱️ **Resultados**")
        c_tf, c_obs = st.columns([1, 2])
        with c_tf:
            st.caption("**Tiempo Final**")
            mr, sr, cr = st.columns(3)
            tm_m = mr.number_input("Min", 0, 59, 0)
            tm_s = sr.number_input("Seg", 0, 59, 0)
            tm_c = cr.number_input("Cent", 0, 99, 0)
        
        with c_obs:
            obs = st.text_area("Observaciones", placeholder="Comentarios...", height=82)

        st.caption("**Parciales (Opcional)**")
        cp1, cp2, cp3, cp4 = st.columns(4)
        p1 = cp1.text_input("P1", placeholder="00.00")
        p2 = cp2.text_input("P2", placeholder="00.00")
        p3 = cp3.text_input("P3", placeholder="00.00")
        p4 = cp4.text_input("P4", placeholder="00.00")
        
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
                cola_len = len(st.session_state.cola_tests)
                new_id = int(base_id) + cola_len + 1
                
                nuevo_registro = {
                    "id_entrenamiento": new_id,
                    "fecha": fecha.strftime('%Y-%m-%d'),
                    "codnadador": id_nad,
                    "codestilo": id_est,
                    "coddistancia": id_dtot,
                    "coddistancia_parcial": id_dpar,
                    "tiempo_final": tiempo_str(tm_m, tm_s, tm_c),
                    "parcial_1": p1, "parcial_2": p2, "parcial_3": p3, "parcial_4": p4,
                    "observaciones": obs
                }
                
                st.session_state.cola_tests.append(nuevo_registro)
                st.success(f"Test para {nadador_input} agregado a la cola.")
                st.rerun() # Recargar para mostrar el panel de arriba
            else:
                st.warning("Faltan datos obligatorios.")
