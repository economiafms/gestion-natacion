import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Simulador Estratégico - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS ESTRATÉGICO</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>¡VAMOS POR LA COPA!</h3>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    return {
        "nadadores": conn.read(worksheet="Nadadores"),
        "tiempos": conn.read(worksheet="Tiempos"),
        "relevos": conn.read(worksheet="Relevos"),
        "estilos": conn.read(worksheet="Estilos"),
        "distancias": conn.read(worksheet="Distancias"),
        "cat_relevos": conn.read(worksheet="Categorias_Relevos"),
        "categorias": conn.read(worksheet="Categorias")
    }

data = cargar_datos_sim()
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())
lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist()
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

# --- 3. FUNCIONES DE APOYO ---
def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return 99.0
        partes = t_str.replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 99.0

def segundos_a_tiempo(seg):
    if seg >= 300: return "--:--.--"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def asignar_cat_posta(suma_edades, reglamento):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reglamento]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma_edades <= r['suma_max']: return r['descripcion']
    return f"Suma {int(suma_edades)}"

def obtener_mejor_50m(id_nadador, id_estilo):
    df_d = data['distancias']
    # Buscamos específicamente la distancia de 50 metros
    id_50m = df_d[df_d['descripcion'].str.contains("50", na=False)]['coddistancia'].iloc[0]
    
    marcas = data['tiempos'][(data['tiempos']['codnadador'] == id_nadador) & 
                            (data['tiempos']['codestilo'] == id_estilo) &
                            (data['tiempos']['coddistancia'] == id_50m)]
    if not marcas.empty:
        return marcas['tiempo'].apply(tiempo_a_segundos).min()
    return 35.0 # Tiempo base competitivo por defecto

# --- 4. MÓDULO 1: SIMULADOR MANUAL CON DESGLOSE ---
st.divider()
st.subheader("🧪 Simulación de Equipo y Estrategia (4x50m)")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", lista_reglamentos, key="m_reg")
    s_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique(), key="m_est")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m_gen")

    orden_etiquetas = ["Espalda", "Pecho", "Mariposa", "Crol"] if "Combinado" in s_est else [f"Relevista {i+1}" for i in range(4)]
    n_sel = []
    cols = st.columns(4)
    for i in range(4):
        ld_filt = df_nad[df_nad['codgenero'] == s_gen] if s_gen in ["M", "F"] else df_nad
        n_sel.append(cols[i].selectbox(orden_etiquetas[i], ld_filt['Nombre Completo'].tolist(), index=None, key=f"ms{i}"))

    if st.button("🚀 Calcular Estrategia y Parciales", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Validación Mixto (2M - 2F)
            gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].values[0] for n in n_sel]
            if s_gen == "X" and gens.count("M") != 2:
                st.error("Error Regla Mixto: La posta debe tener exactamente 2 hombres y 2 mujeres.")
            else:
                # Obtención de Marcas Individuales
                detalles_sim = []
                id_est_sim = data['estilos'][data['estilos']['descripcion'] == s_est]['codestilo'].values[0]
                for nad in n_sel:
                    id_n = df_nad[df_nad['Nombre Completo'] == nad]['codnadador'].values[0]
                    detalles_sim.append({'nombre': nad, 'parcial': obtener_mejor_50m(id_n, id_est_sim)})
                
                t_total_sim = sum([d['parcial'] for d in detalles_sim])
                edades = [(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].values[0]).year) for n in n_sel]
                
                st.write("### 📋 Desglose de la Simulación")
                cols_p = st.columns(4)
                for i, d in enumerate(detalles_sim):
                    cols_p[i].metric(f"P{i+1}: {d['nombre'].split(',')[1]}", segundos_a_tiempo(d['parcial']))
                
                st.success(f"**Categoría: {asignar_cat_posta(sum(edades), s_reg)} | Tiempo Total Simulado: {segundos_a_tiempo(t_total_sim)}**")

                # Búsqueda de Antecedentes (Independiente del orden)
                ids_actuales = sorted([df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0] for n in n_sel])
                def es_el_mismo_equipo(row):
                    return sorted([row['nadador_1'], row['nadador_2'], row['nadador_3'], row['nadador_4']]) == ids_actuales
                
                antecedente = data['relevos'][data['relevos'].apply(es_el_mismo_equipo, axis=1)]

                if not antecedente.empty:
                    ant = antecedente.sort_values('tiempo_final').iloc[0]
                    st.write("---")
                    st.write(f"### 📜 Registro Histórico Encontrado ({ant['fecha']})")
                    res_ant = st.columns(4)
                    for i in range(1, 5):
                        res_ant[i-1].write(f"**Pos {i}:** {dict_id_nombre.get(ant[f'nadador_{i}'], '?')}")
                        res_ant[i-1].code(ant[f'tiempo_{i}'])
                    st.warning(f"**Mejor Marca Real: {ant['tiempo_final']}**")
        else:
            st.error("Por favor seleccione 4 nadadores distintos.")

# --- 5. MÓDULO 2: OPTIMIZADOR ESTRATÉGICO MULTI-POSTA ---
st.divider()
st.subheader("🎯 Optimizador de Postas Múltiples (Sin Repetir)")
st.caption("Distribuye nadadores disponibles para ganar en la mayor cantidad de categorías posibles.")

with st.container(border=True):
    pool = st.multiselect("Nadadores convocados:", lista_nombres, key="pool_opt")
    g1, g2, g3 = st.columns(3)
    g_reg = g1.selectbox("Reglamento", lista_reglamentos, key="g_reg_opt")
    g_est = g2.selectbox("Estilo", data['estilos']['descripcion'].unique(), key="g_est_opt")
    g_gen = g3.selectbox("Género", ["M", "F", "X"], key="g_gen_opt")

    if st.button("🪄 Generar Propuestas Óptimas", type="primary", use_container_width=True):
        if len(pool) < 4:
            st.error("Se necesitan al menos 4 nadadores.")
        else:
            id_est_g = data['estilos'][data['estilos']['descripcion'] == g_est]['codestilo'].values[0]
            pool_actual = list(pool)
            propuestas = []
            
            # Algoritmo de optimización codiciosa
            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                for c in combis:
                    gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].values[0] for n in c]
                    if (g_gen == "M" and all(g == "M" for g in gens)) or \
                       (g_gen == "F" and all(g == "F" for g in gens)) or \
                       (g_gen == "X" and gens.count("M") == 2):
                        validas.append(c)
                
                if not validas: break
                
                mejor_c, mejor_t, mejor_s = None, 9999.0, 0
                for c in validas:
                    t = sum([obtener_mejor_50m(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0], id_est_g) for n in c])
                    if t < mejor_t:
                        mejor_t, mejor_c = t, c
                        mejor_s = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].values[0]).year) for n in c])
                
                if mejor_c:
                    propuestas.append({'equipo': mejor_c, 'tiempo': mejor_t, 'cat': asignar_cat_posta(mejor_s, g_reg)})
                    for n in mejor_c: pool_actual.remove(n)
                else: break

            if propuestas:
                st.write(f"### 🚀 Se formaron {len(propuestas)} equipos sin repetir nadadores:")
                for i, p in enumerate(propuestas):
                    with st.expander(f"Posta #{i+1}: {p['cat']}", expanded=True):
                        st.write(f"**Integrantes:** {', '.join(p['equipo'])}")
                        st.metric("Tiempo Estimado (4x50m)", segundos_a_tiempo(p['tiempo']))
                if len(propuestas) < 3: st.warning("⚠️ No hay suficientes nadadores para cubrir 3 categorías.")
            else:
                st.error("No se pudieron formar equipos válidos con los criterios seleccionados.")
