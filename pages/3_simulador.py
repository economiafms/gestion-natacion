import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Analista Pro - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ ANALISTA ESTRATÉGICO DE RELEVOS</h1>", unsafe_allow_html=True)

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
        df_n['Edad_Master'] = 2026 - pd.to_datetime(df_n['fechanac']).dt.year
        
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
        if tiempo_seg <= meta:
            return True, f"🔥 **NIVEL FEDERACIÓN/CENARD.** Tiempo de podio ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 10:
            return False, f"✨ **NIVEL COMPETITIVO.** A solo {seg_a_tiempo(tiempo_seg - meta)} del podio nacional."
    return False, ""

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación de Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Prueba", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m3")

    legs = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    n_sel, cols = [], st.columns(4)
    for i, (nom_e, cod_e) in enumerate(legs):
        ids_e = df_tiempos_50[df_tiempos_50['codestilo'] == cod_e]['codnadador'].unique()
        aptos = df_nad[df_nad['codnadador'].isin(ids_e)]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nom_e}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Estrategia de Victoria", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            marcas = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
            total = sum([marcas[n].get(legs[i][1], 999.0) for i, n in enumerate(n_sel)])
            se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
            cat_nom, _ = get_cat_info(se, s_reg)
            
            # --- VISUALIZACIÓN DESTACADA ---
            st.markdown(f"""
                <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 10px solid red; text-align: center;">
                    <h1 style="margin: 0; color: white;">{seg_a_tiempo(total)}</h1>
                    <h2 style="margin: 0; color: #ff4b4b;">CATEGORÍA: {cat_nom.upper()}</h2>
                    <p style="margin: 5px; color: gray;">Suma de edades: {se} años</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("### ⏱️ Desglose Técnico")
            res_c = st.columns(4)
            for i in range(4):
                res_c[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(marcas[n_sel[i]].get(legs[i][1])))
                res_c[i].caption(legs[i][0])

            # --- OBSERVACIONES ---
            mejor_t_var, mejor_ord_var = total, n_sel
            for p in itertools.permutations(n_sel):
                t_p = sum([marcas[p[idx]].get(legs[idx][1], 999.0) for idx in range(4)])
                if t_p < mejor_t_var: mejor_t_var, mejor_ord_var = t_p, p
            
            is_podio, txt_podio = analizar_competitividad(total, se, s_gen)
            obs_final = txt_podio
            if mejor_t_var < (total - 0.1):
                detalles_v = [f"{mejor_ord_var[i].split(',')[0]} en {legs[i][0]}" for i in range(4)]
                obs_final += f"\n\n💡 **VARIANTE MÁS EFICIENTE:** {seg_a_tiempo(mejor_t_var)} con el orden: {' / '.join(detalles_v)}."
            
            # Antecedente
            ids_act = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
            def check_eq(row): return sorted([int(row['nadador_1']), int(row['nadador_2']), int(row['nadador_3']), int(row['nadador_4'])]) == ids_act
            hist = data['relevos'][data['relevos'].apply(check_eq, axis=1)]
            if not hist.empty:
                ant = hist.sort_values('tiempo_final').iloc[0]
                ip = dict_piletas.get(ant['codpileta'], {"club": "Sede ?", "medida": "-"})
                obs_final += f"\n\n📋 **ANTECEDENTE:** {ant['tiempo_final']} en {ip['club']} ({ip['medida']}) el {ant['fecha']}."
            
            st.info(obs_final)
        else: st.error("Seleccione 4 nadadores únicos.")

# --- 5. OPTIMIZADOR DE VICTORIA ---
st.divider()
st.subheader("🎯 Optimizador de Podios por Categoría")
pool = st.multiselect("Pool de Convocados:", sorted(df_nad['Nombre Completo'].tolist()))
o_reg = st.selectbox("Reglamento Torneo", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = st.radio("Relevo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
o_gen = st.radio("Género", ["M", "F", "X"], horizontal=True)

if st.button("🪄 Armar Equipos Ganadores", type="primary", use_container_width=True):
    if len(pool) < 4: st.error("Faltan nadadores.")
    else:
        with st.spinner("Priorizando categorías competitivas..."):
            m_map = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
            for n in pool:
                m_map[n]['gen'] = df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0]
                m_map[n]['edad'] = df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]

            legs_opt = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
            pool_actual, propuestas = list(pool), []
            categorias_cubiertas = []

            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                for c in combis:
                    gs = [m_map[n]['gen'] for n in c]
                    if (o_gen == "M" and all(g=="M" for g in gs)) or (o_gen == "F" and all(g=="F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2):
                        mt, mo = 999.0, None
                        for p in itertools.permutations(c):
                            tp = sum([m_map[p[idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)])
                            if tp < mt: mt, mo = tp, p
                        if mo:
                            se = sum([m_map[n]['edad'] for n in mo])
                            c_nom, c_max = get_cat_info(se, o_reg)
                            is_comp, _ = analizar_competitividad(mt, se, o_gen)
                            # CRITERIO: Si la categoría ya tiene un ganador, solo aceptamos otro si es competitivo
                            if c_nom not in categorias_cubiertas or is_comp:
                                validas.append({'eq': mo, 't': mt, 'cat': c_nom, 'se': se, 'cmax': c_max})
                
                if not validas: break
                
                # Priorizar el equipo que más se acerque al podio nacional o sea el más rápido absoluto
                mejor = min(validas, key=lambda x: x['t'])
                
                # --- BUSCAR SALTO ESTRATÉGICO PARA ASEGURAR CATEGORÍA ---
                sugerencia = None
                faltante = mejor['cmax'] - mejor['se']
                if faltante <= 10:
                    suplentes = [n for n in pool_actual if n not in mejor['eq']]
                    mejor_rec = None
                    min_dif = 999.0
                    for s in suplentes:
                        for idx in range(4):
                            sale = mejor['eq'][idx]
                            if o_gen == "X" and m_map[s]['gen'] != m_map[sale]['gen']: continue
                            n_suma = mejor['se'] - m_map[sale]['edad'] + m_map[s]['edad']
                            if n_suma > mejor['cmax']:
                                perd = m_map[s].get(legs_opt[idx][0], 999.0) - m_map[sale].get(legs_opt[idx][0], 999.0)
                                if perd < min_dif: min_dif, mejor_rec = perd, (sale, s, n_suma)
                    if mejor_rec:
                        c_nueva, _ = get_cat_info(mejor_rec[2], o_reg)
                        sugerencia = f"💡 **ESTRATEGIA:** Sacando a **{mejor_rec[0]}** y poniendo a **{mejor_rec[1]}**, el equipo sube a **{c_nueva.upper()}**. Se pierden solo {min_dif:.2f}s pero se compite contra nadadores más grandes."

                propuestas.append({
                    'eq': mejor['eq'], 't': mejor['t'], 'cat': mejor['cat'], 'se': mejor['se'], 
                    'parc': [m_map[mejor['eq'][idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)],
                    'tip': sugerencia
                })
                categorias_cubiertas.append(mejor['cat'])
                for n in mejor['eq']: pool_actual.remove(n)

            # RENDER DE RESULTADOS OPTIMIZADOS
            for i, p in enumerate(propuestas):
                with st.expander(f"POSTA #{i+1}: {p['cat'].upper()} ({seg_a_tiempo(p['t'])})", expanded=True):
                    st.markdown(f"### ⏱️ {seg_a_tiempo(p['t'])} | {p['cat'].upper()}")
                    cols = st.columns(4)
                    for j in range(4):
                        cols[j].write(f"**{legs_opt[j][1]}**\n\n{p['eq'][j]}")
                        cols[j].code(seg_a_tiempo(p['parc'][j]))
                    
                    is_podio, txt_p = analizar_competitividad(p['t'], p['se'], o_gen)
                    if is_podio: st.success(txt_p)
                    else: st.warning(txt_p)
                    if p['tip']: st.info(p['tip'])
