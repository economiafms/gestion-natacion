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

# --- 2. CARGA Y PRE-PROCESAMIENTO ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    try:
        data = {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
        df_n = data['nadadores'].copy()
        df_n['Nombre Completo'] = df_n['apellido'].astype(str).str.upper() + ", " + df_n['nombre'].astype(str)
        df_n['AnioNac'] = pd.to_datetime(df_n['fechanac']).dt.year
        
        # Mapa de IDs para evitar búsquedas repetitivas
        df_t_50 = data['tiempos'][data['tiempos']['coddistancia'] == 'D1'].copy()
        
        return data, df_n, df_t_50
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None, None, None

data, df_nad, df_tiempos_50 = cargar_datos_sim()
if not data: st.stop()

# --- 3. FUNCIONES TÉCNICAS ---
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999.0

def seg_a_tiempo(seg):
    if seg >= 900: return "S/T"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def get_cat_info(suma, reg):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: return r['descripcion'], r['suma_max']
    return f"Suma {int(suma)}", 999

def analizar_competitividad(tiempo_seg, suma_edades, genero):
    # Benchmarks oficiales Federación / CENARD
    benchmarks = {
        "M": {119: 112, 159: 115, 199: 119, 239: 130}, 
        "F": {119: 132, 159: 135, 199: 145, 239: 165}, 
        "X": {119: 120, 159: 124, 199: 128, 239: 145}  
    }
    limites = sorted(benchmarks[genero].keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks[genero]:
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **NIVEL FEDERACIÓN/CENARD.** Tiempo de élite ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 10: return f"✨ **NIVEL COMPETITIVO.** Cerca de marcas de podio nacional."
    return ""

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Configuración de Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Prueba de Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m3")

    legs_desc = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    n_sel, cols = [], st.columns(4)
    for i, (nombre_est, cod_est) in enumerate(legs_desc):
        ids_est = df_tiempos_50[df_tiempos_50['codestilo'] == cod_est]['codnadador'].unique()
        aptos = df_nad[df_nad['codnadador'].isin(ids_est)]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nombre_est}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Estrategia y Parciales", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Diccionario local de marcas para velocidad
            marcas_locales = {}
            for nad in n_sel:
                idn = df_nad[df_nad['Nombre Completo'] == nad]['codnadador'].iloc[0]
                m_nad = df_tiempos_50[df_tiempos_50['codnadador'] == idn]
                marcas_locales[nad] = {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in m_nad.iterrows()}

            total_actual = sum([marcas_locales[n].get(legs_desc[i][1], 999.0) for i, n in enumerate(n_sel)])
            cols_res = st.columns(4)
            for i, (nom_est, cod_est) in enumerate(legs_desc):
                cols_res[i].metric(n_sel[i], seg_a_tiempo(marcas_locales[n_sel[i]].get(cod_est, 999.0)))
            
            se = sum([(2026 - df_nad[df_nad['Nombre Completo'] == n]['AnioNac'].iloc[0]) for n in n_sel])
            cat_desc, _ = get_cat_info(se, s_reg)
            
            st.success(f"**Categoría: {cat_desc} | Tiempo Total Simulado: {seg_a_tiempo(total_actual)}**")
            
            # --- BÚSQUEDA DE ANTECEDENTE HISTÓRICO ---
            ids_act = sorted([df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0] for n in n_sel])
            def check_eq(row): return sorted([int(row['nadador_1']), int(row['nadador_2']), int(row['nadador_3']), int(row['nadador_4'])]) == ids_act
            hist_rel = data['relevos'][data['relevos'].apply(check_eq, axis=1)]
            
            obs_final = analizar_competitividad(total_actual, se, s_gen)
            
            if not hist_rel.empty:
                ant = hist_rel.sort_values('tiempo_final').iloc[0]
                obs_final += f"\n\n📋 **ANTECEDENTE REGISTRADO:** Este grupo ya compitió el {ant['fecha']} con un tiempo de **{ant['tiempo_final']}**."

            # Análisis de reordenamiento eficiente
            mejor_t_var, mejor_ord_var = total_actual, n_sel
            if "Medley" in s_tipo_rel:
                for p in itertools.permutations(n_sel):
                    t_p = sum([marcas_locales[p[idx]].get(legs_desc[idx][1], 999.0) for idx in range(4)])
                    if t_p < mejor_t_var: mejor_t_var, mejor_ord_var = t_p, p
            
            if mejor_t_var < (total_actual - 0.1):
                obs_final += f"\n\n💡 **VARIANTE MÁS EFICIENTE:** Cambiando el orden a: " + " / ".join([f"{mejor_ord_var[i]} ({legs_desc[i][0]})" for i in range(4)]) + f". El tiempo bajaría a **{seg_a_tiempo(mejor_t_var)}**."
            
            if obs_final: st.info(obs_final)
        else: st.error("Seleccione 4 nadadores con marcas.")

# --- 5. OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador Estratégico Multi-Posta")
pool = st.multiselect("Nadadores convocados:", sorted(df_nad['Nombre Completo'].tolist()), key="p_opt")
o_reg = st.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = st.radio("Estilo de Relevo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
o_gen = st.radio("Género Relevo", ["M", "F", "X"], horizontal=True)

if st.button("🪄 Generar Estrategia Ganadora", type="primary", use_container_width=True):
    if len(pool) < 4: st.error("Faltan nadadores.")
    else:
        with st.spinner("Procesando combinaciones óptimas..."):
            # Mapa de marcas del pool para máxima velocidad
            marks_map = {}
            for n in pool:
                idn = df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]
                m_nad = df_tiempos_50[df_tiempos_50['codnadador'] == idn]
                marks_map[n] = {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in m_nad.iterrows()}
                marks_map[n]['genero'] = df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0]
                marks_map[n]['anio'] = df_nad[df_nad['Nombre Completo'] == n]['AnioNac'].iloc[0]

            legs_opt = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
            pool_actual, propuestas = list(pool), []
            
            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                for c in combis:
                    gs = [marks_map[n]['genero'] for n in c]
                    if (o_gen == "M" and all(g=="M" for g in gs)) or (o_gen == "F" and all(g=="F" for g in gs)) or (o_gen == "X" and gs.count("M")==2):
                        m_t, m_ord = 999.0, None
                        if "Libre" in o_tipo:
                            m_t = sum([marks_map[n].get("E4", 999.0) for n in c])
                            m_ord = sorted(c, key=lambda x: marks_map[x].get("E4", 999.0), reverse=True)
                        else:
                            for p in itertools.permutations(c):
                                tp = sum([marks_map[p[idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)])
                                if tp < m_t: m_t, m_ord = tp, p
                        if m_ord and m_t < 400: validas.append({'eq': m_ord, 't': m_t})
                
                if not validas: break
                mejor = min(validas, key=lambda x: x['t'])
                se_e = sum([(2026 - marks_map[n]['anio']) for n in mejor['eq']])
                c_nom, c_max = get_cat_info(se_e, o_reg)
                propuestas.append({'eq': mejor['eq'], 't': mejor['t'], 'cat': c_nom, 'se': se_e, 'cmax': c_max, 'parc': [marks_map[mejor['eq'][idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)]})
                for n in mejor['eq']: pool_actual.remove(n)

            # --- RENDERIZACIÓN DE RESULTADOS ---
            for i, p in enumerate(propuestas):
                with st.expander(f"Posta #{i+1}: {p['cat']} ({seg_a_tiempo(p['t'])})", expanded=True):
                    # Título de grupo y tiempo resaltado
                    st.markdown(f"### ⏱️ Tiempo: {seg_a_tiempo(p['t'])} | 👥 Grupo: {p['cat']}")
                    
                    cols = st.columns(4)
                    for j in range(4):
                        cols[j].markdown(f"**{legs_opt[j][1]}**")
                        cols[j].write(p['eq'][j])
                        cols[j].code(seg_a_tiempo(p['parc'][j]))
                    
                    comp_text = analizar_competitividad(p['t'], p['se'], o_gen)
                    if comp_text: st.info(comp_text)
                    
                    falt = p['cmax'] - p['se']
                    if falt <= 8: st.success(f"💡 **TIP ESTRATÉGICO:** Este equipo suma {p['se']} años. Están a solo {falt} años del límite de categoría. Evaluar subir de grupo.")
