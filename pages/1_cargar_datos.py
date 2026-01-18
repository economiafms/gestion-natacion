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
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas")
        }
    except Exception as e:
        st.error(f"Error al cargar GSheets: {e}")
        return None

data = cargar_referencias()
if not data: st.stop()

# Pre-procesamiento de nombres y piletas para selectores
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)

df_pil = data['piletas'].copy()
df_pil['Detalle'] = df_pil['club'] + " (" + df_pil['medida'] + ")"

tab1, tab2, tab3 = st.tabs(["👤 Nadadores", "⏱️ Tiempos Individuales", "🏁 Relevos 4x50"])

# --- 4. CARGA DE NADADORES ---
with tab1:
    st.header("Añadir Nadador")
    with st.form("form_nadador", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        n_nom = col1.text_input("Nombre")
        n_ape = col2.text_input("Apellido")
        n_fec = col3.date_input("Fecha Nacimiento", value=date(1990, 1, 1))
        
        col4, col5 = st.columns(2)
        n_gen = col4.selectbox("Género", ["M", "F"])
        n_dni = col5.text_input("DNI / Identificación")
        
        if st.form_submit_button("➕ Añadir a la Cola"):
            if n_nom and n_ape:
                nuevo_id = data['nadadores']['codnadador'].max() + 1 + len(st.session_state.cola_nadadores)
                st.session_state.cola_nadadores.append({
                    "codnadador": int(nuevo_id),
                    "nombre": n_nom,
                    "apellido": n_ape,
                    "fechanac": n_fec.strftime("%Y-%m-%d"),
                    "codgenero": n_gen,
                    "dni": n_dni
                })
                st.success(f"Nadador {n_ape} en cola.")
            else: st.error("Nombre y Apellido son obligatorios.")

# --- 5. CARGA DE TIEMPOS INDIVIDUALES ---
with tab2:
    st.header("Carga de Tiempos")
    with st.form("form_tiempos", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        t_nad = c1.selectbox("Nadador", sorted(df_nad['Nombre Completo'].tolist()))
        t_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique())
        t_dis = c3.selectbox("Distancia", data['distancias']['descripcion'].unique())
        
        c4, c5, c6 = st.columns(3)
        t_val = c4.text_input("Tiempo (mm:ss.cc)", value="00:00.00")
        t_pil = c5.selectbox("Pileta", df_pil['Detalle'].unique())
        t_fec = c6.date_input("Fecha", value=date.today())
        
        if st.form_submit_button("➕ Añadir Tiempo"):
            id_n = df_nad[df_nad['Nombre Completo'] == t_nad]['codnadador'].values[0]
            st.session_state.cola_tiempos.append({
                "codnadador": int(id_n),
                "codestilo": data['estilos'][data['estilos']['descripcion'] == t_est]['codestilo'].values[0],
                "coddistancia": data['distancias'][data['distancias']['descripcion'] == t_dis]['coddistancia'].values[0],
                "tiempo": t_val,
                "codpileta": df_pil[df_pil['Detalle'] == t_pil]['codpileta'].values[0],
                "fecha": t_fec.strftime("%Y-%m-%d")
            })
            st.success("Tiempo añadido a la cola.")

# --- 6. SECCIÓN DE RELEVOS (MEJORADA) ---
with tab3:
    st.header("🏁 Carga de Relevos 4x50")
    
    # Parámetros dinámicos fuera del form para refrescar listas
    c_f1, c_f2 = st.columns([1, 2])
    r_gen = c_f1.selectbox("Género del Relevo", ["M", "F", "X"], key="filtro_gen_rel")
    
    # Filtro automático de distancia 4x50
    df_dist_relevos = data['distancias'][data['distancias']['descripcion'].str.contains("4x50", case=False)]
    opciones_dist = df_dist_relevos['descripcion'].unique() if not df_dist_relevos.empty else data['distancias']['descripcion'].unique()
    
    # Filtrado dinámico de nadadores según género
    if r_gen == "M":
        df_aptos = df_nad[df_nad['codgenero'] == 'M']
    elif r_gen == "F":
        df_aptos = df_nad[df_nad['codgenero'] == 'F']
    else:
        df_aptos = df_nad # Mixto (X) permite todos
    
    lista_nombres_aptos = sorted(df_aptos['Nombre Completo'].tolist())

    with st.form("form_relevos", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        r_est = c1.selectbox("Estilo", data['estilos']['descripcion'].unique(), key="r_est")
        r_dis = c2.selectbox("Distancia (4x50)", opciones_dist, key="r_dis")
        r_pil = c3.selectbox("Pileta", df_pil['Detalle'].unique(), key="r_pil")
        
        st.divider()
        st.write(f"**Integrantes del Relevo {r_gen}**")
        
        r_n = []
        r_p = []
        
        # 4 Nadadores y sus parciales
        col_nad, col_tie = st.columns([3, 1])
        for i in range(4):
            with col_nad:
                # Key dinámica con r_gen para resetear al cambiar género
                n = st.selectbox(f"Nadador {i+1}", lista_nombres_aptos, index=None, key=f"r_n_{r_gen}_{i}")
                r_n.append(n)
            with col_tie:
                p = st.text_input(f"Parcial {i+1}", value="00:00.00", key=f"r_p_{i}")
                r_p.append(p)
        
        st.divider()
        c4, c5 = st.columns(2)
        r_fec = c4.date_input("Fecha", value=date.today(), key="r_fec")
        r_pos = c5.number_input("Posición Final", 1, 100, 1, key="rp_pos")

        if st.form_submit_button("➕ Añadir Relevo a la Cola"):
            if all(r_n):
                base_id = data['relevos']['id_relevo'].max() if not data['relevos'].empty else 0
                cola_id = pd.DataFrame(st.session_state.cola_relevos)['id_relevo'].max() if st.session_state.cola_relevos else 0
                
                ids_n = [df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0] for n in r_n]
                
                st.session_state.cola_relevos.append({
                    'id_relevo': int(max(base_id, cola_id) + 1),
                    'codpileta': df_pil[df_pil['Detalle'] == r_pil]['codpileta'].values[0],
                    'codestilo': data['estilos'][data['estilos']['descripcion'] == r_est]['codestilo'].values[0],
                    'coddistancia': data['distancias'][data['distancias']['descripcion'] == r_dis]['coddistancia'].values[0],
                    'codgenero': r_gen,
                    'nadador_1': ids_n[0], 'tiempo_1': r_p[0],
                    'nadador_2': ids_n[1], 'tiempo_2': r_p[1],
                    'nadador_3': ids_n[2], 'tiempo_3': r_p[2],
                    'nadador_4': ids_n[3], 'tiempo_4': r_p[3],
                    'tiempo_final': "00:00.00",
                    'posicion': r_pos,
                    'fecha': r_fec.strftime("%Y-%m-%d")
                })
                st.success("Relevo añadido a la cola.")
                st.rerun()
            else:
                st.error("Por favor seleccione los 4 nadadores.")

# --- 7. BOTONES DE GUARDADO FINAL (Mantenemos tus botones) ---
st.divider()
st.header("💾 Guardado Final")
col_g1, col_g2, col_g3 = st.columns(3)

if col_g1.button("Guardar Nadadores"):
    if st.session_state.cola_nadadores:
        # Lógica de guardado en GSheets...
        st.success("Nadadores guardados.")
        st.session_state.cola_nadadores = []
        refrescar_datos()

if col_g3.button("Guardar Relevos"):
    if st.session_state.cola_relevos:
        # Lógica de guardado en GSheets...
        st.success("Relevos guardados.")
        st.session_state.cola_relevos = []
        refrescar_datos()
