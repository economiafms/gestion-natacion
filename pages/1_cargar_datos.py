# --- 1_cargar_datos.py (Fragmento Sección Relevos) ---

import streamlit as st
import pandas as pd

# ... (Carga de datos previa)

st.header("🏁 Carga de Relevos")

# 1. PARAMETROS DE FILTRADO (Fuera del form para que sean dinámicos)
c1, c2, c3 = st.columns(3)
r_gen = c1.selectbox("Género del Relevo", ["M", "F", "X"], key="r_gen_filtro")
r_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique(), key="r_est_rel")

# Filtro estricto de distancia: Solo 4x50
dist_4x50 = data['distancias'][data['distancias']['descripcion'].str.contains("4x50", case=False)]
if dist_4x50.empty:
    st.error("No se encontró la distancia '4x50' en la base de datos.")
    r_dis = None
else:
    r_dis = c3.selectbox("Distancia", dist_4x50['descripcion'].unique(), key="r_dis_rel")

# 2. FILTRADO DE NADADORES POR GÉNERO
if r_gen == "M":
    df_aptos = df_nad[df_nad['codgenero'] == 'M']
elif r_gen == "F":
    df_aptos = df_nad[df_nad['codgenero'] == 'F']
else: # Mixto (X)
    df_aptos = df_nad[df_nad['codgenero'].isin(['M', 'F'])]

lista_aptos = sorted(df_aptos['Nombre Completo'].tolist())

# 3. FORMULARIO DE CARGA DE TIEMPOS Y POSICIONES
with st.form("form_relevos", clear_on_submit=True):
    st.write(f"### Detalle del Relevo {r_gen} - {r_est}")
    
    # Creamos 4 filas para los 4 integrantes
    r_n = []
    r_p = []
    
    col_n, col_t = st.columns([3, 1])
    for i in range(4):
        with col_n:
            # Usamos un key dinámico basado en el género para forzar el refresco
            n = st.selectbox(f"Nadador {i+1}", lista_aptos, index=None, key=f"rel_n_{r_gen}_{i}")
            r_n.append(n)
        with col_t:
            t = st.text_input(f"Tiempo {i+1} (mm:ss.cc)", value="00:00.00", key=f"rel_t_{i}")
            r_p.append(t)
            
    st.divider()
    c_p1, c_p2, c_p3 = st.columns(3)
    r_pil = c_p1.selectbox("Pileta", df_pil['Detalle'].unique(), key="rel_pil")
    r_fec = c_p2.date_input("Fecha", value=date.today(), key="rel_fec")
    rp_r = c_p3.number_input("Posición Final", 1, 100, 1, key="rel_pos")

    if st.form_submit_button("➕ Añadir Relevo a la Cola"):
        if all(r_n) and r_dis:
            # Lógica de guardado en session_state
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
                'tiempo_final': "00:00.00", # Podrías calcular la suma aquí
                'posicion': rp_r,
                'fecha': r_fec.strftime("%Y-%m-%d")
            })
            st.success(f"✅ Relevo {r_gen} añadido correctamente.")
            st.rerun() # Forzamos el refresco para limpiar selectores
        else:
            st.error("Por favor, selecciona los 4 nadadores.")
