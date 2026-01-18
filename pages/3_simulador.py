import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Simulador Estratégico - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS ESTRATÉGICO</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Planificación de Postas - ¡Vamos por la Copa!</h3>", unsafe_allow_html=True)

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
        "cat_relevos": conn.read(worksheet="Categorias_Relevos")
    }

data = cargar_datos_sim()
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())
lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist()

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
    # Buscamos el código de '50m'
    df_d = data['distancias']
    id_50m = df_d[df_d['descripcion'].str.contains("50", na=False)]['coddistancia'].iloc[0]
    
    marcas = data['tiempos'][(data['tiempos']['codnadador'] == id_nadador) & 
                            (data['tiempos']['codestilo'] == id_estilo) &
                            (data['tiempos']['coddistancia'] == id_50m)]
    if not marcas.empty:
        return marcas['tiempo'].apply(tiempo_a_segundos).min()
    return 35.0 # Tiempo base competitivo

# --- 4. MÓDULO 1: SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación de Equipo Puntual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", lista_reglamentos, key="m_reg")
    s_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique(), key="m_est")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m_gen")

    orden = ["Espalda", "Pecho", "Mariposa", "Crol"] if "Combinado" in s_est else [f"Relevista {i+1}" for i in range(4)]
    n_sel = []
    cols = st.columns(4)
    for i in range(4):
        ld_filt = df_nad[df_nad['codgenero'] == s_gen] if s_gen in ["M", "F"] else df_nad
        n_sel.append(cols[i].selectbox(orden[i], ld_filt['Nombre Completo'].tolist(), index=None, key=f"ms{i}"))

    if st.button("🚀 Calcular Tiempo", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Lógica Mixto
            gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].values[0] for n in n_sel]
            if s_gen == "X" and gens.count("M") != 2:
                st.error("Error Regla Mixto: Debe haber 2 hombres y 2 mujeres.")
            else:
                edades = [(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].values[0]).year) for n in n_sel]
                id_est = data['estilos'][data['estilos']['descripcion'] == s_est]['codestilo'].values[0]
                t_total = sum([obtener_mejor_50m(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0], id_est) for n in n_sel])
                st.success(f"Categoría: {asignar_cat_posta(sum(edades), s_reg)} | Tiempo Est.: {segundos_a_tiempo(t_total)}")
        else:
            st.error("Seleccione 4 nadadores únicos.")

# --- 5. MÓDULO 2: GENERADOR ESTRATÉGICO ÓPTIMO ---
st.divider()
st.subheader("🎯 Optimizador de Postas Múltiples")
st.caption("Genera la mejor distribución de nadadores para cubrir la mayor cantidad de categorías sin repetir atletas.")

with st.container(border=True):
    pool = st.multiselect("Seleccione todos los nadadores disponibles para el torneo:", lista_nombres)
    g1, g2, g3 = st.columns(3)
    g_reg = g1.selectbox("Reglamento", lista_reglamentos, key="g_reg")
    g_est = g2.selectbox("Estilo Posta", data['estilos']['descripcion'].unique(), key="g_est")
    g_gen = g3.selectbox("Género Requerido", ["M", "F", "X"], key="g_gen")

    if st.button("🪄 Generar Propuestas Óptimas", type="primary", use_container_width=True):
        if len(pool) < 4:
            st.error("Se necesitan al menos 4 nadadores.")
        else:
            id_est_g = data['estilos'][data['estilos']['descripcion'] == g_est]['codestilo'].values[0]
            pool_actual = list(pool)
            propuestas = []
            
            # Algoritmo de optimización codiciosa
            while len(pool_actual) >= 4:
                # Generar combinaciones posibles del pool restante
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                
                for c in combis:
                    gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].values[0] for n in c]
                    if g_gen == "M" and all(g == "M" for g in gens): validas.append(c)
                    elif g_gen == "F" and all(g == "F" for g in gens): validas.append(c)
                    elif g_gen == "X" and gens.count("M") == 2: validas.append(c)
                
                if not validas: break
                
                # Buscar la mejor de estas válidas
                mejor_c = None
                mejor_t = 9999.0
                mejor_s = 0
                
                for c in validas:
                    t = sum([obtener_mejor_50m(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0], id_est_g) for n in c])
                    if t < mejor_t:
                        mejor_t = t
                        mejor_c = c
                        mejor_s = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].values[0]).year) for n in c])
                
                if mejor_c:
                    propuestas.append({'equipo': mejor_c, 'tiempo': mejor_t, 'cat': asignar_cat_posta(mejor_s, g_reg)})
                    for n in mejor_c: pool_actual.remove(n)
                else: break

            if propuestas:
                st.write(f"### 🚀 Se formaron {len(propuestas)} equipos óptimos:")
                for i, p in enumerate(propuestas):
                    with st.expander(f"Posta #{i+1}: {p['cat']}", expanded=True):
                        col_a, col_b = st.columns([3, 1])
                        col_a.write(f"**Atletas:** {', '.join(p['equipo'])}")
                        col_b.metric("Proyección", segundos_a_tiempo(p['tiempo']))
                
                if len(propuestas) < 3:
                    st.warning("⚠️ Con los nadadores seleccionados no se logran cubrir 3 categorías. ¡Convocá más gente!")
            else:
                st.error("No se pudieron formar equipos válidos con el género seleccionado.")
