import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Carga - Natación", layout="wide")
st.title("📥 Panel de Carga de Datos")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. INICIALIZAR COLAS EN SESSION STATE ---
if "cola_nadadores" not in st.session_state: st.session_state.cola_nadadores = []
if "cola_tiempos" not in st.session_state: st.session_state.cola_tiempos = []
if "cola_relevos" not in st.session_state: st.session_state.cola_relevos = []

def refrescar_datos():
    st.cache_data.clear()
    st.rerun()

# --- 3. CARGA DE METADATOS (Tablas de referencia) ---
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

# Auxiliares
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
lista_nombres = df_nad['Nombre Completo'].sort_values().unique()

df_pil = data['piletas'].copy()
df_pil['Detalle'] = df_pil['club'].astype(str) + " (" + df_pil['medida'].astype(str) + ")"
lista_piletas = df_pil['Detalle'].unique()

# Predeterminar P02 (Echesortu)
idx_p02 = 0
if 'P02' in df_pil['codpileta'].values:
    nom_p02 = df_pil.loc[df_pil['codpileta'] == 'P02', 'Detalle'].iloc[0]
    idx_p02 = list(lista_piletas).index(nom_p02)

lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist() if not data['cat_relevos'].empty else ["FED"]
sep = "<div style='text-align: center; font-size: 25px; font-weight: bold; margin-top: 28px;'>{}</div>"

# ==========================================
# 4. PANEL DE SINCRONIZACIÓN UNIFICADO
# ==========================================
total = len(st.session_state.cola_tiempos) + len(st.session_state.cola_nadadores) + len(st.session_state.cola_relevos)

if total > 0:
    with st.container(border=True):
        st.warning(f"🚨 Tienes **{total}** registros en espera de ser subidos.")
        cs, cv = st.columns(2)
        if cs.button("🚀 SINCRONIZAR TODO CON GOOGLE", type="primary", use_container_width=True):
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
                    st.success("✅ ¡Base de datos sincronizada!")
                    refrescar_datos()
            except Exception as e: st.error(str(e))
        if cv.button("🗑️ VACIAR LISTAS", use_container_width=True):
            st.session_state.cola_tiempos, st.session_state.cola_nadadores, st.session_state.cola_relevos = [], [], []
            st.rerun()

# ==========================================
# 5. FORMULARIOS DE CARGA
# ==========================================
col_nad, col_tiem = st.columns(2)

with col_nad:
    with st.expander("👤 Nuevo Nadador", expanded=False):
        with st.form("f_nad", clear_on_submit=True):
            n_nom = st.text_input("Nombre")
            n_ape = st.text_input("Apellido")
            n_gen = st.selectbox("Género", ["M", "F"], index=None)
            n_fec = st.date_input("Nacimiento", value=date(1990, 1, 1))
            if st.form_submit_button("➕ Añadir a lista"):
                base_id = data['nadadores']['codnadador'].max() if not data['nadadores'].empty else 0
                cola_id = pd.DataFrame(st.session_state.cola_nadadores)['codnadador'].max() if st.session_state.cola_nadadores else 0
                st.session_state.cola_nadadores.append({
                    'codnadador': int(max(base_id, cola_id) + 1), 'nombre': n_nom.title(), 'apellido': n_ape.title(),
                    'fechanac': n_fec.strftime('%Y-%m-%d'), 'codgenero': n_gen
                })
                st.rerun()

with col_tiem:
    st.write("### ⏱️ Carga de Resultados")
    es_relevo = st.toggle("🏊‍♂️ Modo Relevos", value=False)
    
    with st.expander("📝 Completar Formulario", expanded=True):
        if not es_relevo:
            with st.form("f_ind", clear_on_submit=True):
                t_nad = st.selectbox("Nadador", lista_nombres, index=None)
                tc1, tc2 = st.columns(2)
                with tc1: t_est = st.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
                with tc2: t_dis = st.selectbox("Distancia", data['distancias']['descripcion'].unique(), index=None)
                t_pil = st.selectbox("Sede", lista_piletas, index=idx_p02) # P02 Predet.
                
                st.write("**Tiempo:**")
                cm, cs1, cs, cs2, cc = st.columns([1, 0.2, 1, 0.2, 1])
                with cm: vm = st.number_input("Min", 0, 59, 0, format="%02d")
                with cs1: st.markdown(sep.format(":"), unsafe_allow_html=True)
                with cs: vs = st.number_input("Seg", 0, 59, 0, format="%02d")
                with cs2: st.markdown(sep.format("."), unsafe_allow_html=True)
                with cc: vc = st.number_input("Cent", 0, 99, 0, format="%02d")
                
                v_fec = st.date_input("Fecha", value=date(2025, 11, 30)) # 30/11 Predet.
                v_pos = st.number_input("Posición", 1, 100, 1)

                if st.form_submit_button("➕ Añadir Tiempo Individual"):
                    if t_nad and t_est and t_dis:
                        base_id = data['tiempos']['id_registro'].max() if not data['tiempos'].empty else 0
                        cola_id = pd.DataFrame(st.session_state.cola_tiempos)['id_registro'].max() if st.session_state.cola_tiempos else 0
                        st.session_state.cola_tiempos.append({
                            'id_registro': int(max(base_id, cola_id) + 1),
                            'codnadador': df_nad[df_nad['Nombre Completo'] == t_nad]['codnadador'].values[0],
                            'codpileta': df_pil[df_pil['Detalle'] == t_pil]['codpileta'].values[0],
                            'codestilo': data['estilos'][data['estilos']['descripcion'] == t_est]['codestilo'].values[0],
                            'coddistancia': data['distancias'][data['distancias']['descripcion'] == t_dis]['coddistancia'].values[0],
                            'tiempo': f"{vm:02d}:{vs:02d}.{vc:02d}", 'fecha': v_fec.strftime('%Y-%m-%d'), 'posicion': int(v_pos)
                        })
                        st.rerun()
        else:
            with st.form("f_rel", clear_on_submit=True):
                r_pil = st.selectbox("Sede", lista_piletas, index=idx_p02)
                r_reg = st.selectbox("Reglamento", lista_reglamentos)
                r_gen = st.selectbox("Género", ["M", "F", "X"], index=None)
                re1, re2 = st.columns(2)
                with re1: r_est = st.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None)
                with re2: r_dis = st.selectbox("Distancia", data['distancias']['descripcion'].unique(), index=None)
                
                ld = df_nad[df_nad['codgenero'] == r_gen]['Nombre Completo'].unique() if r_gen in ["M", "F"] else lista_nombres
                r_n, r_p = [], []
                for i in range(1, 5):
                    ca, cb = st.columns([3, 1])
                    r_n.append(ca.selectbox(f"Nadador {i}", ld, index=None, key=f"rn{i}"))
                    r_p.append(cb.text_input(f"P{i}", placeholder="00.00", key=f"rp{i}"))
                
                st.write("**Tiempo Final:**")
                rm, rs1, rs, rs2, rc = st.columns([1, 0.2, 1, 0.2, 1])
                with rm: rvm = st.number_input("Min", 0, 59, 0, key="rmr", format="%02d")
                with rs1: st.markdown(sep.format(":"), unsafe_allow_html=True)
                with rs: rvs = st.number_input("Seg", 0, 59, 0, key="rsr", format="%02d")
                with rs2: st.markdown(sep.format("."), unsafe_allow_html=True)
                with rc: rvc = st.number_input("Cent", 0, 99, 0, key="rcr", format="%02d")
                
                rf_r = st.date_input("Fecha", value=date(2025, 11, 30), key="rf_r")
                rp_r = st.number_input("Posición", 1, 100, 1, key="rp_r")

                if st.form_submit_button("➕ Añadir Relevo"):
                    if r_gen and all(r_n):
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
                        st.rerun()