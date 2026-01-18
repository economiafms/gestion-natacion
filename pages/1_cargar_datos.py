import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Carga - Natación", layout="wide")
st.title("📥 Panel de Carga de Datos")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS (Asegurar que 'data' exista) ---
@st.cache_data(ttl="1h")
def cargar_referencias():
    return {
        "nadadores": conn.read(worksheet="Nadadores"),
        "tiempos": conn.read(worksheet="Tiempos"),
        "relevos": conn.read(worksheet="Relevos"),
        "estilos": conn.read(worksheet="Estilos"),
        "distancias": conn.read(worksheet="Distancias"),
        "piletas": conn.read(worksheet="Piletas")
    }

# EJECUCIÓN DE LA CARGA (Esto define la variable 'data' para todo el script)
data = cargar_referencias()

# Procesamiento de nombres y piletas
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)

df_pil = data['piletas'].copy()
df_pil['Detalle'] = df_pil['club'] + " (" + df_pil['medida'] + ")"

# --- 3. SECCIÓN DE RELEVOS ---
st.divider()
st.header("🏁 Carga de Relevos (4x50)")

# Filtros fuera del form para que la lista de nadadores sea dinámica
c1, c2, c3 = st.columns(3)

# 1. Filtro de Género
r_gen = c1.selectbox("Género del Relevo", ["M", "F", "X"], key="r_gen_rel")

# 2. Filtro de Estilo
r_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique(), key="r_est_rel")

# 3. Filtro de Distancia (FORZADO A 4x50)
dist_4x50 = data['distancias'][data['distancias']['descripcion'].str.contains("4x50", case=False)]
if dist_4x50.empty:
    st.error("No se encontró la distancia '4x50' en la tabla de Distancias.")
    r_dis = None
else:
    # Si hay varias (ej. 4x50 Libre y 4x50 Combinado), dejamos elegir, sino toma la única
    r_dis = c3.selectbox("Distancia", dist_4x50['descripcion'].unique(), key="r_dis_rel")

# FILTRADO DINÁMICO DE NADADORES
# Esto evita que queden nadadores del género anterior al cambiar el selector
if r_gen == "M":
    df_aptos = df_nad[df_nad['codgenero'] == 'M']
elif r_gen == "F":
    df_aptos = df_nad[df_nad['codgenero'] == 'F']
else: # Mixto (X)
    df_aptos = df_nad # Pueden ser todos

lista_nombres_aptos = sorted(df_aptos['Nombre Completo'].tolist())

# FORMULARIO DE CARGA
with st.form("form_relevos", clear_on_submit=True):
    st.write(f"### Detalle: {r_gen} - {r_est}")
    
    # Usamos columnas para que no ocupe tanto espacio vertical
    col_n, col_t = st.columns([3, 1])
    
    r_n = []
    r_t = []
    
    for i in range(4):
        with col_n:
            # El key incluye r_gen para que Streamlit resetee el componente al cambiar de género
            n = st.selectbox(f"Nadador {i+1}", lista_nombres_aptos, index=None, key=f"n_{r_gen}_{i}")
            r_n.append(n)
        with col_t:
            t = st.text_input(f"Tiempo {i+1}", value="00:00.00", key=f"t_{i}")
            r_t.append(t)
            
    st.divider()
    f1, f2, f3 = st.columns(3)
    r_pil = f1.selectbox("Pileta", df_pil['Detalle'].unique(), key="rp_pil")
    r_fec = f2.date_input("Fecha", value=date.today(), key="rp_fec")
    r_pos = f3.number_input("Posición Final", 1, 100, 1, key="rp_pos")

    if st.form_submit_button("➕ Añadir Relevo"):
        if all(r_n) and r_dis:
            # Aquí va tu lógica de guardado en session_state o base de datos
            st.success(f"Relevo {r_gen} cargado para procesar.")
            # st.session_state.cola_relevos.append(...)
        else:
            st.error("Faltan completar nadadores o la distancia no es válida.")
