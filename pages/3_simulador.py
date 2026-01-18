import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Estrategia Pro - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ ANALISTA ESTRATÉGICO DE RELEVOS</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Optimización de Categorías para Máximo Rendimiento</h4>", unsafe_allow_html=True)

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
            "cat_relevos": conn.read(worksheet="Categorias_Relevos"),
            "piletas": conn.read(worksheet="Piletas")
        }
        df_n = data['nadadores'].copy()
        df_n['Nombre Completo'] = df_n['apellido'].astype(str).str.upper() + ", " + df_n['nombre'].astype(str)
        df_n['AnioNac'] = pd.to_datetime(df_n['fechanac']).dt.year
        df_n['Edad_Master'] = 2026 - df_n['AnioNac']
        
        df_t_50 = data['tiempos'][data['tiempos']['coddistancia'] == 'D1'].copy()
        return data, df_n, df_t_50
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None, None, None

data, df_nad, df_tiempos_50 = cargar_datos_sim()
if not data: st.stop()

dict_piletas = data['piletas'].set_index('codpileta').to_dict('index')

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
    benchmarks = {
        "M": {119: 112, 159: 115, 199: 119, 239: 130}, 
        "F": {119: 132, 159: 135, 199: 145, 239: 165}, 
        "X": {119: 120, 159: 124, 199: 128, 239: 145}  
    }
    limites = sorted(benchmarks[genero].keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks[genero]:
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **NIVEL CENARD.** Tiempo de podio nacional ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 10: return f"✨ **NIVEL COMPETITIVO.** Cerca del podio."
    return ""

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación de Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Tipo Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m3")

    legs_desc = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    n_sel, cols = [], st.columns(4)
    for i, (nombre_est, cod_est) in enumerate(legs_desc):
        ids_est = df_tiempos_50[df_tiempos_50['codestilo'] == cod_est]['codnadador'].unique()
        aptos = df_nad[df_nad['codnadador'].isin(ids_est)]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nombre_est}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Estrategia", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Diccionario marcas local
            marcas_locales = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
            total_actual = sum([marcas_locales[n].get(legs_desc[i][1], 999.0) for i, n in enumerate(n_sel)])
            
            res_c = st.columns(4)
            for i in range(4):
                res_c[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(marcas_locales[n_sel[i]].get(legs_desc[i][1])))
            
            se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
            cat_nom, _ = get_cat_info(se, s_reg)
            st.success(f"**Categoría: {cat_nom} | Tiempo: {seg_a_tiempo(total_actual)}**")
            
            # Antecedente
            ids_act = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
            def check_eq(row): return sorted([int(row['nadador_1']), int(row['nadador_2']), int(row['nadador_3']), int(row['nadador_4'])]) == ids_act
            hist = data['relevos'][data['relevos'].apply(check_eq, axis=1)]
            obs = analizar_competitividad(total_actual, se, s_gen)
            if not hist.empty:
                ant = hist.sort_values('tiempo_final').iloc[0]
                ip = dict_piletas.get(ant['codpileta'], {"club": "Sede ?", "medida": "-"})
                obs += f"\n\n📋 **RÉCORD GRUPAL:** {ant['tiempo_final']} en {ip['club']} ({ip['medida']}) el {ant['fecha']}."
            st.info(obs)
        else: st.error("Seleccione 4 nadadores con marcas.")

# --- 5. OPTIMIZADOR CON SUGERENCIA DE SALTO ---
st.divider()
st.subheader("🎯 Optimizador con Sugerencia de Salto de Categoría")
pool = st.multiselect("Convocados:", sorted(df_nad['Nombre Completo'].tolist()))
o_reg = st.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = st.radio("Relevo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
o_gen = st.radio("Género", ["M", "F", "X"], horizontal=True)

if st.button("🪄 Generar Estrategia de Victoria", type="primary", use_container_width=True):
    if len(pool) < 4: st.error("Mínimo 4 nadadores.")
    else:
        with st.spinner("Analizando miles de combinaciones..."):
            # Mapa de marcas completo del pool
            m_map = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
            for n in pool:
                m_map[n]['gen'] = df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0]
                m_map[n]['edad'] = df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]

            legs_opt = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
            pool_actual, propuestas = list(pool), []
            
            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                for c in combis:
                    gs = [m_map[n]['gen'] for n in c]
                    if (o_gen == "M" and all(g=="M" for g in gs)) or (o_gen == "F" and all(g=="F" for g in gs)) or (o_gen == "X" and gs.count("M")==2):
                        mt, mo = 999.0, None
                        for p in itertools.permutations(c):
                            tp = sum([m_map[p[idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)])
                            if tp < mt: mt, mo = tp, p
                        if mo: validas.append({'eq': mo, 't': mt})
                
                if not validas: break
                mejor = min(validas, key=lambda x: x['t'])
                se_e = sum([m_map[n]['edad'] for n in mejor['eq']])
                c_nom, c_max = get_cat_info(se_e, o_reg)
                
                # --- LÓGICA DE SUGERENCIA DE SALTO ---
                sugerencia_salto = None
                faltante = c_max - se_e
                if faltante <= 12: # Si están cerca del límite
                    # Buscamos en el pool restante a alguien que nos haga saltar perdiendo lo menos posible
                    nadadores_fuera = [n for n in pool if n not in mejor['eq']]
                    mejor_reemplazo = None
                    min_perdida = 999.0
                    
                    for r in nadadores_fuera:
                        # Debe cumplir género
                        if o_gen != "X" and m_map[r]['gen'] != o_gen: continue
                        if o_gen == "X": # Si es mixto, el que sale debe ser del mismo género que el que entra
                            pass # Simplificación: buscamos por tiempo para la idea

                        for idx_sale in range(4):
                            n_sale = mejor['eq'][idx_sale]
                            if o_gen == "X" and m_map[r]['gen'] != m_map[n_sale]['gen']: continue
                            
                            nueva_suma = se_e - m_map[n_sale]['edad'] + m_map[r]['edad']
                            if nueva_suma > c_max: # ¡Saltamos de categoría!
                                perdida = m_map[r].get(legs_opt[idx_sale][0], 999.0) - m_map[n_sale].get(legs_opt[idx_sale][0], 999.0)
                                if perdida < min_perdida:
                                    min_perdida = perdida
                                    mejor_reemplazo = (n_sale, r, nueva_suma, perdida)

                    if mejor_reemplazo:
                        n_sale, n_entra, s_nueva, perd = mejor_reemplazo
                        c_nueva, _ = get_cat_info(s_nueva, o_reg)
                        sugerencia_salto = f"🏅 **OPCIÓN ESTRATÉGICA:** Cambiando a **{n_sale}** por **{n_entra}**, el equipo suma **{s_nueva}** años y sube a la categoría **{c_nueva}**. Solo se pierden {perd:.2f}s, pero se compite contra nadadores más grandes."

                propuestas.append({
                    'eq': mejor['eq'], 't': mejor['t'], 'cat': c_nom, 'se': se_e, 
                    'parc': [m_map[mejor['eq'][idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)],
                    'tip': sugerencia_salto
                })
                for n in mejor['eq']: pool_actual.remove(n)

            # Render
            for i, p in enumerate(propuestas):
                with st.expander(f"Posta #{i+1}: {p['cat']} ({seg_a_tiempo(p['t'])})", expanded=True):
                    st.markdown(f"### ⏱️ {seg_a_tiempo(p['t'])} | {p['cat']}")
                    cols = st.columns(4)
                    for j in range(4):
                        cols[j].write(f"**{legs_opt[j][1]}**\n\n{p['eq'][j]}")
                        cols[j].code(seg_a_tiempo(p['parc'][j]))
                    
                    if p['tip']: st.success(p['tip'])
                    st.write(analizar_competitividad(p['t'], p['se'], o_gen))
