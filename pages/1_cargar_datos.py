import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Carga - Natación", layout="wide", initial_sidebar_state="collapsed")
st.title("📥 Panel de Carga de Datos")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. INICIALIZAR COLAS EN SESSION STATE ---
if "cola_nadadores" not in st.session_state: st.session_state.cola_nadadores = []
if "cola_tiempos" not in st.session_state: st.session_state.cola_tiempos = []
if "cola_relevos" not in st.session_state: st.session_state.cola_relevos = []

def refrescar_datos():
    st.cache_data.clear()
    st.rerun()

# --- 3. CARGA DE METADATOS Y PRE-CALCULO DE HASHES ---
@st.cache_data(ttl="1h")
def cargar_referencias():
    return {
        "nadadores": conn.read(worksheet="Nadadores"),
        "tiempos": conn.read(worksheet="Tiempos"),
        "relevos": conn.read(worksheet="Relevos"),
        "estilos": conn.read(worksheet="Estilos"),
        "distancias": conn.read(worksheet="Distancias"),
        "piletas": conn.read(worksheet="Piletas"),
        "cat_relevos": conn.read(worksheet="Categorias_Relevos")
    }

data = cargar_referencias()
if not data: st.stop()

# --- PRE-PROCESAMIENTO PARA VALIDACIÓN RÁPIDA (O(1)) ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.strip().str.upper() + ", " + df_nad['nombre'].astype(str).str.strip().str.upper()
set_nadadores_existentes = set(df_nad['Nombre Completo'].unique())

df_t = data['tiempos'].copy()
# Hash compuesto para evitar duplicados de carrera
df_t['hash_validacion'] = df_t['codnadador'].astype(str) + "_" + df_t['codestilo'].astype(str) + "_" + df_t['coddistancia'].astype(str) + "_" + df_t['fecha'].astype(str)
set_tiempos_existentes = set(df_t['hash_validacion'].unique())

# Listas para Selectores
lista_nombres = sorted(df_nad['Nombre Completo'].unique())
df_pil = data['piletas'].copy()
df_pil['Detalle'] = df_pil['club'].astype(str) + " (" + df_pil['medida'].astype(str) + ")"
lista_piletas = df_pil['Detalle'].unique()
lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist() if not data['cat_relevos'].empty else ["FED"]

# Estilos visuales
sep = "<div style='text-align: center; font-size: 20px; font-weight: bold; margin-top: 30px;'>:</div>"
sep_dot = "<div style='text-align: center; font-size: 20px; font-weight: bold; margin-top: 30px;'>.</div>"

# ==========================================
# 4. PANEL DE SINCRONIZACIÓN
# ==========================================
total = len(st.session_state.cola_tiempos) + len(st.session_state.cola_nadadores) + len(st.session_state.cola_relevos)

if total > 0:
    st.info(f"📢 Tienes **{total}** registros en cola.")
    col_s1, col_s2 = st.columns(2)
    if col_s1.button("☁️ SUBIR A GOOGLE SHEETS", type="primary", use_container_width=True):
        try:
            with st.spinner("Subiendo datos..."):
                if st.session_state.cola_nadadores:
                    conn.update(worksheet="Nadadores", data=pd.concat([data['nadadores'], pd.DataFrame(st.session_state.cola_nadadores)], ignore_index=True))
                    st.session_state.cola_nadadores = []
                if st.session_state.cola_tiempos:
                    conn.update(worksheet="Tiempos", data=pd.concat([data['tiempos'], pd.DataFrame(st.session_state.cola_tiempos)], ignore_index=True))
                    st.session_state.cola_tiempos = []
                if st.session_state.cola_relevos:
                    conn.update(worksheet="Relevos", data=pd.concat([data['relevos'], pd.DataFrame(st.session_state.cola_relevos)], ignore_index=True))
                    st.session_state.cola_relevos = []
                st.success("✅ ¡Sincronización completada!")
                refrescar_datos()
        except Exception as e: st.error(str(e))
    
    if col_s2.button("🗑️ Descartar Cambios", use_container_width=True):
        st.session_state.cola_tiempos, st.session_state.cola_nadadores, st.session_state.cola_relevos = [], [], []
        st.rerun()

# ==========================================
# 5. MENÚ DE NAVEGACIÓN
# ==========================================
seccion_activa = st.radio("📍 Sección:", 
                          ["👤 Nadadores", "⏱️ Individuales", "🏊‍♂️ Relevos"], 
                          horizontal=True, label_visibility="collapsed")
st.divider()

# --- SECCIÓN 1: NADADORES ---
if seccion_activa == "👤 Nadadores":
    with st.container(border=True):
        st.subheader("Nuevo Nadador")
        with st.form("f_nad", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n_nom = c1.text_input("Nombre")
            n_ape = c2.text_input("Apellido")
            
            c3, c4 = st.columns(2)
            n_gen = c3.selectbox("Género", ["M", "F"], index=None, placeholder="Seleccionar...")
            
            hoy = date.today()
            n_fec = c4.date_input("Fecha Nacimiento", value=date(1990, 1, 1), 
                                  min_value=date(hoy.year - 100, 1, 1), 
                                  max_value=date(hoy.year - 18, 12, 31),
                                  format="DD/MM/YYYY")

            st.write("") 
            if st.form_submit_button("Guardar Nadador", use_container_width=True):
                if n_nom and n_ape and n_gen:
                    nombre_completo_nuevo = f"{n_ape.strip().upper()}, {n_nom.strip().upper()}"
                    
                    if nombre_completo_nuevo in set_nadadores_existentes:
                        st.error(f"⛔ Error: **{nombre_completo_nuevo}** ya existe.")
                    else:
                        base_id = data['nadadores']['codnadador'].max() if not data['nadadores'].empty else 0
                        cola_id = pd.DataFrame(st.session_state.cola_nadadores)['codnadador'].max() if st.session_state.cola_nadadores else 0
                        st.session_state.cola_nadadores.append({
                            'codnadador': int(max(base_id, cola_id) + 1), 
                            'nombre': n_nom.title(), 'apellido': n_ape.title(),
                            'fechanac': n_fec.strftime('%Y-%m-%d'), 'codgenero': n_gen
                        })
                        set_nadadores_existentes.add(nombre_completo_nuevo)
                        st.success(f"Nadador {n_nom} añadido.")
                        st.rerun()
                else: st.warning("Completa todos los datos.")

# --- SECCIÓN 2: TIEMPOS INDIVIDUALES ---
elif seccion_activa == "⏱️ Individuales":
    with st.container(border=True):
        st.subheader("Carga Individual")
        with st.form("f_ind", clear_on_submit=True):
            t_nad = st.selectbox("Nadador", lista_nombres, index=None, placeholder="Buscar apellido...")
            
            c1, c2 = st.columns(2)
            t_est = c1.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None, placeholder="Estilo...")
            t_dis = c2.selectbox("Distancia", data['distancias']['descripcion'].unique(), index=None, placeholder="Distancia...")
            
            t_pil = st.selectbox("Sede / Pileta", lista_piletas, index=None, placeholder="Seleccionar sede...") 
            
            st.divider()
            st.write("**Tiempo Realizado**")
            cm, cs1, cs, cs2, cc = st.columns([1, 0.2, 1, 0.2, 1])
            with cm: vm = st.number_input("Min", 0, 59, 0, format="%02d")
            with cs1: st.markdown(sep, unsafe_allow_html=True)
            with cs: vs = st.number_input("Seg", 0, 59, 0, format="%02d")
            with cs2: st.markdown(sep_dot, unsafe_allow_html=True)
            with cc: vc = st.number_input("Cent", 0, 99, 0, format="%02d")
            
            c3, c4 = st.columns(2)
            v_fec = c3.date_input("Fecha Torneo", value=date.today(), format="DD/MM/YYYY")
            v_pos = c4.number_input("Posición", 1, 100, 1)

            st.write("")
            if st.form_submit_button("Guardar Tiempo", use_container_width=True):
                if t_nad and t_est and t_dis and t_pil:
                    # Recuperar valores (CORRECCIÓN: NO FORZAR INT EN CÓDIGOS)
                    id_nad = df_nad[df_nad['Nombre Completo'] == t_nad]['codnadador'].values[0]
                    id_est = data['estilos'][data['estilos']['descripcion'] == t_est]['codestilo'].values[0]
                    id_dis = data['distancias'][data['distancias']['descripcion'] == t_dis]['coddistancia'].values[0]
                    fecha_str = v_fec.strftime('%Y-%m-%d')

                    # Validación de Hash
                    hash_nuevo = f"{id_nad}_{id_est}_{id_dis}_{fecha_str}"
                    
                    if hash_nuevo in set_tiempos_existentes:
                        st.error(f"⛔ Error: Tiempo duplicado para **{t_nad}**.")
                    else:
                        base_id = data['tiempos']['id_registro'].max() if not data['tiempos'].empty else 0
                        cola_id = pd.DataFrame(st.session_state.cola_tiempos)['id_registro'].max() if st.session_state.cola_tiempos else 0
                        st.session_state.cola_tiempos.append({
                            'id_registro': int(max(base_id, cola_id) + 1),
                            'codnadador': id_nad, # Sin int() por si acaso
                            'codpileta': df_pil[df_pil['Detalle'] == t_pil]['codpileta'].values[0],
                            'codestilo': id_est,  # Sin int()
                            'coddistancia': id_dis, # Sin int()
                            'tiempo': f"{vm:02d}:{vs:02d}.{vc:02d}", 'fecha': fecha_str, 'posicion': int(v_pos)
                        })
                        set_tiempos_existentes.add(hash_nuevo)
                        st.success("✅ Tiempo guardado.")
                        st.rerun()
                else: st.warning("Faltan datos obligatorios.")

# --- SECCIÓN 3: RELEVOS ---
elif seccion_activa == "🏊‍♂️ Relevos":
    with st.container(border=True):
        st.subheader("Configuración del Relevo")
        r_gen = st.selectbox("Género del Equipo", ["M", "F", "X"], index=None, placeholder="Seleccionar género primero...")
        
        if r_gen == "M":
            ld = df_nad[df_nad['codgenero'] == 'M']['Nombre Completo'].sort_values().unique()
        elif r_gen == "F":
            ld = df_nad[df_nad['codgenero'] == 'F']['Nombre Completo'].sort_values().unique()
        else:
            ld = lista_nombres 
        
        lista_dist_4x50 = data['distancias'][data['distancias']['descripcion'].str.contains("4x50", case=False, na=False)]['descripcion'].unique()

    with st.container(border=True):
        with st.form("f_rel", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            r_pil = c1.selectbox("Sede", lista_piletas, index=None, placeholder="Sede...")
            r_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None, placeholder="Estilo...")
            r_dis = c3.selectbox("Distancia", lista_dist_4x50, index=None, placeholder="Solo 4x50")
            r_reg = st.selectbox("Reglamento", lista_reglamentos, index=None, placeholder="Reglamento...")

            st.divider()
            st.write("👥 **Integrantes**")
            
            r_n, r_p = [], []
            for i in range(1, 5):
                ca, cb = st.columns([0.7, 0.3]) 
                with ca:
                    r_n.append(st.selectbox(f"Nadador {i}", ld, index=None, key=f"rn_{r_gen}_{i}", placeholder="Buscar..."))
                with cb:
                    r_p.append(st.text_input(f"P{i}", placeholder="00.00", key=f"rp_{i}"))
            
            st.divider()
            st.write("⏱️ **Tiempo Final**")
            rm, rs1, rs, rs2, rc = st.columns([1, 0.2, 1, 0.2, 1])
            with rm: rvm = st.number_input("Min", 0, 59, 0, key="rmr", format="%02d")
            with rs1: st.markdown(sep, unsafe_allow_html=True)
            with rs: rvs = st.number_input("Seg", 0, 59, 0, key="rsr", format="%02d")
            with rs2: st.markdown(sep_dot, unsafe_allow_html=True)
            with rc: rvc = st.number_input("Cent", 0, 99, 0, key="rcr", format="%02d")
            
            c4, c5 = st.columns(2)
            rf_r = c4.date_input("Fecha", value=date.today(), format="DD/MM/YYYY", key="rf_r")
            rp_r = c5.number_input("Posición", 1, 100, 1, key="rp_r")

            st.write("")
            if st.form_submit_button("Guardar Relevo", use_container_width=True):
                if r_gen and all(r_n) and r_dis and r_pil:
                    if len(set(r_n)) != 4:
                        st.error("⛔ Error: Nadadores repetidos.")
                    else:
                        base_id = data['relevos']['id_relevo'].max() if not data['relevos'].empty else 0
                        cola_id = pd.DataFrame(st.session_state.cola_relevos)['id_relevo'].max() if st.session_state.cola_relevos else 0
                        ids_n = [df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0] for n in r_n]
                        
                        st.session_state.cola_relevos.append({
                            'id_relevo': int(max(base_id, cola_id) + 1),
                            'codpileta': df_pil[df_pil['Detalle'] == r_pil]['codpileta'].values[0],
                            'codestilo': data['estilos'][data['estilos']['descripcion'] == r_est]['codestilo'].values[0],
                            'coddistancia': data['distancias'][data['distancias']['descripcion'] == r_dis]['coddistancia'].values[0],
                            'codgenero': r_gen, 'nadador_1': ids_n[0], 'tiempo_1': r_p[0], 'nadador_2': ids_n[1], 'tiempo_2': r_p[1],
                            'nadador_3': ids_n[2], 'tiempo_3': r_p[2], 'nadador_4': ids_n[3], 'tiempo_4': r_p[3],
                            'tiempo_final': f"{rvm:02d}:{rvs:02d}.{rvc:02d}", 'posicion': int(rp_r), 'fecha': rf_r.strftime('%Y-%m-%d'), 'tipo_reglamento': r_reg
                        })
                        st.success("✅ Relevo guardado.")
                        st.rerun()
                else:
                    st.error("Faltan datos obligatorios.")
