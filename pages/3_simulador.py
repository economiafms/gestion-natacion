import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador de Élite - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS ESTRATÉGICO</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Análisis Federativo CENARD - Optimización de Estilos</h4>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

data = cargar_datos_sim()
if not data: st.stop()

df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

MAP_ESTILOS = {"Mariposa": "E1", "Espalda": "E2", "Pecho": "E3", "Crol": "E4"}
ID_50M = "D1"

# --- 3. FUNCIONES TÉCNICAS ---
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999.0

def seg_a_tiempo(seg):
    if seg >= 900: return "S/T"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def obtener_nadadores_aptos(id_estilo, genero="X"):
    t_filt = data['tiempos'][(data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    ids = t_filt['codnadador'].unique()
    res = df_nad[df_nad['codnadador'].isin(ids)]
    if genero != "X": res = res[res['codgenero'] == genero]
    return sorted(res['Nombre Completo'].tolist())

def obtener_mejor_marca(nombre, id_estilo):
    idn = df_nad[df_nad['Nombre Completo'] == nombre]['codnadador'].iloc[0]
    m = data['tiempos'][(data['tiempos']['codnadador'] == idn) & (data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    if m.empty: return 999.0
    return m['tiempo'].apply(tiempo_a_seg).min()

def get_cat_info(suma, reg):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: return r['descripcion'], r['suma_max']
    return f"Suma {int(suma)}", 999

def analizar_competitividad(tiempo_seg, suma_edades, genero):
    # Benchmarks FEDERACIÓN / CENARD (Tiempos de punta)
    benchmarks = {
        "M": {119: 112, 159: 115, 199: 119, 239: 130}, 
        "F": {119: 132, 159: 135, 199: 145, 239: 165}, 
        "X": {119: 120, 159: 124, 199: 128, 239: 145}  
    }
    limites = sorted(benchmarks[genero].keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks[genero]:
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **NIVEL FEDERACIÓN/CENARD.** Tiempo de élite."
        elif tiempo_seg <= meta + 10: return f"✨ **NIVEL COMPETITIVO.** Cerca de marcas de podio nacional."
    return "📈 **Nivel de entrenamiento.** Objetivo: Bajar marcas individuales."

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Configuración de Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Prueba de Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m3")

    # Estilos según el tipo de relevo
    legs_desc = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    
    n_sel, cols = [], st.columns(4)
    for i, (nombre_est, cod_est) in enumerate(legs_desc):
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nombre_est}", obtener_nadadores_aptos(cod_est, s_gen), index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Estrategia y Parciales", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # 1. Cálculo de la posta seleccionada
            total_actual = 0
            cols_res = st.columns(4)
            for i, (nom_est, cod_est) in enumerate(legs_desc):
                t = obtener_mejor_marca(n_sel[i], cod_est)
                total_actual += t
                cols_res[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(t))
                cols_res[i].caption(f"Estilo: {nom_est}")
            
            se = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in n_sel])
            cat_desc, _ = get_cat_info(se, s_reg)
            st.success(f"**Categoría: {cat_desc} | Tiempo Total: {seg_a_tiempo(total_actual)}**")
            
            # 2. Análisis de Eficiencia (Buscando variantes con los mismos 4)
            mejor_t_variante, mejor_ord_variante = 999.0, None
            for p in itertools.permutations(n_sel):
                t_p, skip = 0, False
                for idx, (nom_e, cod_e) in enumerate(legs_desc):
                    mv = obtener_mejor_marca(p[idx], cod_e)
                    if mv >= 900: skip = True; break
                    t_p += mv
                if not skip and t_p < mejor_t_variante:
                    mejor_t_variante, mejor_ord_variante = t_p, p
            
            obs = analizar_competitividad(total_actual, se, s_gen)
            if mejor_ord_variante and mejor_t_variante < (total_actual - 0.1): # Si bajan más de una décima
                obs_variante = f"\n\n💡 **VARIANTE EFICIENTE:** Si reordenan a los nadadores de la siguiente forma: "
                detalles = [f"{mejor_ord_variante[i].split(',')[0]} en {legs_desc[i][0]}" for i in range(4)]
                obs_variante += " / ".join(detalles) + f". El tiempo bajaría a **{seg_a_tiempo(mejor_t_variante)}**."
                st.info(obs + obs_variante)
            else:
                st.info(obs)
        else:
            st.error("Error: Seleccione 4 nadadores distintos con marcas registradas.")

# --- 5. OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador Estratégico Multi-Posta")
pool = st.multiselect("Nadadores convocados:", sorted(df_nad['Nombre Completo'].tolist()))
g1, g2, g3 = st.columns(3)
o_reg = g1.selectbox("Reglamento Torneo", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = g2.selectbox("Estilo", ["Libre (Crol)", "Combinado (Medley)"], key="o2")
o_gen = g3.selectbox("Género", ["M", "F", "X"], key="o3")

if st.button("🪄 Generar Estrategia Ganadora", type="primary", use_container_width=True):
    if len(pool) < 4: st.error("Mínimo 4 nadadores.")
    else:
        legs_opt = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
        pool_actual, propuestas = list(pool), []
        
        while len(pool_actual) >= 4:
            combis = list(itertools.combinations(pool_actual, 4))
            validas = []
            for c in combis:
                gs = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in c]
                if (o_gen == "M" and all(g == "M" for g in gs)) or (o_gen == "F" and all(g == "F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2):
                    m_t, m_ord = 999.0, None
                    for p in itertools.permutations(c):
                        tp, skip = 0, False
                        for idx, (cod_e, nom_e) in enumerate(legs_opt):
                            mv = obtener_mejor_marca(p[idx], cod_e)
                            if mv >= 900: skip = True; break
                            tp += mv
                        if not skip and tp < m_t: m_t, m_ord = tp, p
                    if m_ord: validas.append({'equipo': m_ord, 'tiempo': m_t})
            
            if not validas: break
            mejor_eq = min(validas, key=lambda x: x['tiempo'])
            se_e = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in mejor_eq['equipo']])
            cat_nom, cat_max = get_cat_info(se_e, o_reg)
            propuestas.append({'equipo': mejor_eq['equipo'], 'tiempo': mejor_eq['tiempo'], 'cat': cat_nom, 'suma': se_e, 'suma_max': cat_max,
                               'parciales': [obtener_mejor_marca(mejor_eq['equipo'][idx], legs_opt[idx][0]) for idx in range(4)]})
            for n in mejor_eq['equipo']: pool_actual.remove(n)

        for i, p in enumerate(propuestas):
            with st.expander(f"Posta #{i+1}: {p['cat']} ({seg_a_tiempo(p['tiempo'])})", expanded=True):
                cols_p = st.columns(4)
                for j in range(4):
                    cols_p[j].write(f"**{legs_opt[j][1]}**")
                    cols_p[j].write(f"{p['equipo'][j]}")
                    cols_p[j].code(seg_a_tiempo(p['parciales'][j]))
                
                st.write(analizar_competitividad(p['tiempo'], p['suma'], o_gen))
                faltante = p['suma_max'] - p['suma']
                if faltante <= 8:
                    st.info(f"💡 **TIP ESTRATÉGICO:** Están a {faltante} años del límite. Evaluar subir de categoría para ganar.")
