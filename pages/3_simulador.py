import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Simulador - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Optimización de Postas - Vamos por la Copa</h3>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS (Centralizada) ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    return {
        "nadadores": conn.read(worksheet="Nadadores"),
        "tiempos": conn.read(worksheet="Tiempos"),
        "relevos": conn.read(worksheet="Relevos"),
        "estilos": conn.read(worksheet="Estilos"),
        "distancias": conn.read(worksheet="Distancias"),
        "cat_relevos": conn.read(worksheet="Categorias_Relevos")
    }

data = cargar_datos_sim()
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())
lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist()

# --- 3. FUNCIONES DE CÁLCULO ---
def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return 99.0
        partes = t_str.replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 99.0

def segundos_a_tiempo(seg):
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def asignar_cat_posta(suma_edades, reglamento):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reglamento]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma_edades <= r['suma_max']: return r['descripcion']
    return f"Suma {int(suma_edades)}"

# --- 4. MÓDULO 1: SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación Manual de Equipo")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", lista_reglamentos)
    s_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique())
    s_gen = c3.selectbox("Género de la Posta", ["M", "F", "X"])

    st.write("**Seleccione el orden de los 4 nadadores:**")
    # Para Combinado (Medley), definimos el orden oficial
    orden_medley = ["Espalda", "Pecho", "Mariposa", "Crol"] if "Combinado" in s_est else [f"Relevista {i+1}" for i in range(4)]
    
    n_sel = []
    cols = st.columns(4)
    for i in range(4):
        # Filtro de género por posición
        ld = df_nad if s_gen == "X" else df_nad[df_nad['codgenero'] == s_gen]
        n_sel.append(cols[i].selectbox(orden_medley[i], lista_nombres, index=None, key=f"s{i}"))

    if st.button("🚀 Calcular Simulación", use_container_width=True):
        if len(set(n_sel)) < 4 or None in n_sel:
            st.error("Error: Debes seleccionar 4 nadadores distintos.")
        elif s_gen == "X" and [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].values[0] for n in n_sel].count("M") != 2:
            st.error("Regla Mixto: La posta debe tener exactamente 2 hombres y 2 mujeres.")
        else:
            # A. Cálculo de Categoría
            edades = [(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].values[0]).year) for n in n_sel]
            suma_e = sum(edades)
            cat_p = asignar_cat_posta(suma_e, s_reg)
            
            # B. Tiempo Proyectado (Mejor 50m de cada uno en ese estilo)
            t_total = 0
            id_est = data['estilos'][data['estilos']['descripcion'] == s_est]['codestilo'].values[0]
            for n in n_sel:
                id_n = df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0]
                marcas = data['tiempos'][(data['tiempos']['codnadador'] == id_n) & (data['tiempos']['codestilo'] == id_est)]
                t_total += marcas['tiempo'].apply(tiempo_a_segundos).min() if not marcas.empty else 40.0
            
            # C. Búsqueda de Antecedentes (Independiente del orden)
            ids_actuales = sorted([df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0] for n in n_sel])
            
            def es_el_mismo_equipo(row):
                return sorted([row['nadador_1'], row['nadador_2'], row['nadador_3'], row['nadador_4']]) == ids_actuales
            
            antecedentes = data['relevos'][data['relevos'].apply(es_el_mismo_equipo, axis=1)]

            # RESULTADOS
            st.success(f"📍 Categoría Proyectada: {cat_p} (Suma: {suma_e})")
            res1, res2 = st.columns(2)
            res1.metric("⏱️ Tiempo Simulado", segundos_a_tiempo(t_total))
            
            if not antecedentes.empty:
                mejor = antecedentes.sort_values('tiempo_final').iloc[0]
                res2.metric("📋 Récord Histórico de este equipo", mejor['tiempo_final'])
                st.info(f"Antecedente encontrado el {mejor['fecha']} en {mejor['codpileta']}.")
            else:
                res2.info("Este equipo no tiene registros previos juntos.")

# --- 5. MÓDULO 2: OPTIMIZADOR ALEATORIO ---
st.divider()
st.subheader("🎲 Generador de Combinación Óptima")

pool = st.multiselect("Nadadores disponibles para el torneo:", lista_nombres)
col_opt1, col_opt2 = st.columns(2)
opt_reg = col_opt1.selectbox("Reglamento Torneo", lista_reglamentos, key="opt_reg")
opt_est = col_opt2.selectbox("Estilo Posta", data['estilos']['descripcion'].unique(), key="opt_est")

if st.button("🪄 Buscar Mejor Posta Posible"):
    if len(pool) < 4:
        st.warning("Selecciona al menos 4 nadadores.")
    else:
        todas_combis = list(itertools.combinations(pool, 4))
        resultados = []
        id_est_opt = data['estilos'][data['estilos']['descripcion'] == opt_est]['codestilo'].values[0]

        for c in todas_combis:
            # Solo permitimos 2M-2F si es para simular algo equilibrado o si el pool lo permite
            t_combi = 0
            for nad in c:
                id_n = df_nad[df_nad['Nombre Completo'] == nad]['codnadador'].values[0]
                m = data['tiempos'][(data['tiempos']['codnadador'] == id_n) & (data['tiempos']['codestilo'] == id_est_opt)]
                t_combi += m['tiempo'].apply(tiempo_a_segundos).min() if not m.empty else 45.0
            
            sum_e = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].values[0]).year) for n in c])
            resultados.append({'equipo': c, 'tiempo': t_combi, 'suma': sum_e})
        
        mejor_opcion = min(resultados, key=lambda x: x['tiempo'])
        
        st.write("### 🏆 Propuesta ganadora:")
        st.write(f"**Integrantes:** {', '.join(mejor_opcion['equipo'])}")
        st.write(f"**Tiempo estimado:** {segundos_a_tiempo(mejor_opcion['tiempo'])}")
        st.write(f"**Categoría:** {asignar_cat_posta(mejor_opcion['suma'], opt_reg)}")
