import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Simulador Real - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS (TIEMPOS REALES)</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Basado exclusivamente en marcas registradas de 50m</h3>", unsafe_allow_html=True)

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
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist()

# --- 3. FUNCIONES DE APOYO TÉCNICO ---
def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return 0.0
        partes = t_str.replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 0.0

def segundos_a_tiempo(seg):
    if seg == 0: return "--:--.--"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def asignar_cat_posta(suma_edades, reglamento):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reglamento]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma_edades <= r['suma_max']: return r['descripcion']
    return f"Suma {int(suma_edades)}"

# Identificar ID de distancia 50m una sola vez
df_dist = data['distancias']
ID_50M = df_dist[df_dist['descripcion'].str.contains("50", na=False)]['coddistancia'].iloc[0]

def obtener_nadadores_con_tiempo(id_estilo, genero="X"):
    """Filtra nadadores que tengan al menos un tiempo en 50m de ese estilo."""
    tiempos_validos = data['tiempos'][
        (data['tiempos']['codestilo'] == id_estilo) & 
        (data['tiempos']['coddistancia'] == ID_50M)
    ]
    ids_con_tiempo = tiempos_validos['codnadador'].unique()
    
    # Cruzar con tabla de nadadores y filtrar por género
    res = df_nad[df_nad['codnadador'].isin(ids_con_tiempo)]
    if genero != "X":
        res = res[res['codgenero'] == genero]
    return sorted(res['Nombre Completo'].tolist())

def obtener_mejor_marca_real(id_nadador, id_estilo):
    """Busca la mejor marca real de 50m en la tabla."""
    marcas = data['tiempos'][
        (data['tiempos']['codnadador'] == id_nadador) & 
        (data['tiempos']['codestilo'] == id_estilo) &
        (data['tiempos']['coddistancia'] == ID_50M)
    ]
    return marcas['tiempo'].apply(tiempo_a_segundos).min()

# --- 4. MÓDULO 1: SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación Manual (Solo nadadores con marca)")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", lista_reglamentos, key="m_reg")
    s_est_nom = c2.selectbox("Estilo Relevo", data['estilos']['descripcion'].unique(), key="m_est")
    s_gen = c3.selectbox("Género Relevo", ["M", "F", "X"], key="m_gen")

    id_est_sel = data['estilos'][data['estilos']['descripcion'] == s_est_nom]['codestilo'].iloc[0]
    
    # FILTRO CRÍTICO: Solo nadadores que tienen tiempo en ese estilo
    nadadores_aptos = obtener_nadadores_con_tiempo(id_est_sel, s_gen)
    
    if not nadadores_aptos:
        st.warning(f"⚠️ No hay nadadores con marcas registradas de 50m en {s_est_nom} para el género {s_gen}.")
    else:
        st.write(f"Nadadores disponibles con marca en {s_est_nom}: {len(nadadores_aptos)}")
        orden_et = ["Espalda", "Pecho", "Mariposa", "Crol"] if "Combinado" in s_est_nom else [f"Relevista {i+1}" for i in range(4)]
        n_sel = []
        cols = st.columns(4)
        for i in range(4):
            n_sel.append(cols[i].selectbox(orden_et[i], nadadores_aptos, index=None, key=f"ms{i}"))

        if st.button("🚀 Simular con Tiempos de Tabla", use_container_width=True):
            if len(set(n_sel)) == 4 and None not in n_sel:
                # Validación Mixto
                gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].values[0] for n in n_sel]
                if s_gen == "X" and gens.count("M") != 2:
                    st.error("Error: Relevo Mixto requiere 2 hombres y 2 mujeres.")
                else:
                    # Cálculo con desgloses
                    detalles = []
                    for n in n_sel:
                        idn = df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]
                        t_seg = obtener_mejor_marca_real(idn, id_est_sel)
                        detalles.append({'nombre': n, 'parcial': t_seg})
                    
                    t_total = sum([d['parcial'] for d in detalles])
                    edades = [(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in n_sel]
                    
                    st.write("### ⏱️ Parciales Reales (Mejor 50m en tabla)")
                    cp = st.columns(4)
                    for i, d in enumerate(detalles):
                        cp[i].metric(d['nombre'].split(',')[1], segundos_a_tiempo(d['parcial']))
                    
                    st.success(f"**Categoría: {asignar_cat_posta(sum(edades), s_reg)} | Tiempo Simulado: {segundos_a_tiempo(t_total)}**")

# --- 5. MÓDULO 2: OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador Estratégico (Detección de equipos ganadores)")

with st.container(border=True):
    # El pool ya viene filtrado por el estilo
    est_opt_nom = st.selectbox("Seleccione Estilo para Optimizar", data['estilos']['descripcion'].unique(), key="opt_est_nom")
    id_est_opt = data['estilos'][data['estilos']['descripcion'] == est_opt_nom]['codestilo'].iloc[0]
    
    nadadores_con_marca = obtener_nadadores_con_tiempo(id_est_opt)
    pool = st.multiselect("Pool de nadadores disponibles (Solo con marca registrada):", nadadores_con_marca)
    
    g1, g2 = st.columns(2)
    o_reg = g1.selectbox("Reglamento Torneo", lista_reglamentos, key="o_reg")
    o_gen = g2.selectbox("Género Postas", ["M", "F", "X"], key="o_gen")

    if st.button("🪄 Generar Mejores Combinaciones", type="primary"):
        if len(pool) < 4:
            st.error("Se necesitan al menos 4 nadadores con marcas registradas.")
        else:
            pool_actual = list(pool)
            propuestas = []
            
            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                for c in combis:
                    gs = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in c]
                    if (o_gen == "M" and all(g == "M" for g in gs)) or \
                       (o_gen == "F" and all(g == "F" for g in gs)) or \
                       (o_gen == "X" and gs.count("M") == 2):
                        validas.append(c)
                
                if not validas: break
                
                # Buscar el equipo más rápido
                mejor_c, mejor_t, mejor_s = None, 9999.0, 0
                for c in validas:
                    t = sum([obtener_mejor_marca_real(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0], id_est_opt) for n in c])
                    if t < mejor_t:
                        mejor_t, mejor_c = t, c
                        mejor_s = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in c])
                
                if mejor_c:
                    propuestas.append({'equipo': mejor_c, 'tiempo': mejor_t, 'cat': asignar_cat_posta(mejor_s, o_reg)})
                    for n in mejor_c: pool_actual.remove(n)
                else: break

            if propuestas:
                for i, p in enumerate(propuestas):
                    with st.expander(f"Posta #{i+1} - {p['cat']}", expanded=True):
                        st.write(f"**Integrantes:** {', '.join(p['equipo'])}")
                        st.metric("Tiempo Total Real", segundos_a_tiempo(p['tiempo']))
            else:
                st.error("No hay combinaciones posibles que cumplan la regla de género.")
