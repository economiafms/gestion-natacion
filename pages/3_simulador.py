import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro - NOB", layout="wide")
st.markdown("<h3 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE ESTRATEGIA - NOB</h3>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA Y PRE-PROCESAMIENTO ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    try:
        data = {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos"),
            "piletas": conn.read(worksheet="Piletas")
        }
        df_n = data['nadadores'].copy()
        df_n['Nombre Completo'] = df_n['apellido'].astype(str).str.upper() + ", " + df_n['nombre'].astype(str)
        df_n['Edad_Master'] = 2026 - pd.to_datetime(df_n['fechanac']).dt.year
        df_t_50 = data['tiempos'][data['tiempos']['coddistancia'] == 'D1'].copy()
        return data, df_n, df_t_50
    except Exception as e:
        st.error(f"Error de conexión: {e}")
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
    benchmarks = {"M": {119: 112, 159: 115, 199: 119, 239: 130}, "F": {119: 132, 159: 135, 199: 145, 239: 165}, "X": {119: 120, 159: 124, 199: 128, 239: 145}}
    limites = sorted(benchmarks.get(genero, {}).keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks.get(genero, {}):
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **NIVEL CENARD.** Podio ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 10: return f"✨ **NIVEL COMPETITIVO.** Cerca de podio nacional."
    return ""

# --- 4. POSTA MANUAL ---
st.subheader("🧪 Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg_m = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="s_reg_m")
    s_tipo_m = c2.selectbox("Prueba", ["Libre (Crol)", "Combinado (Medley)"], key="s_tipo_m")
    s_gen_sel = c3.selectbox("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], key="s_gen_m")
    s_gen = "X" if "Mixto" in s_gen_sel else ("M" if "(M)" in s_gen_sel else "F")

    legs = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_m else [("Crol", "E4")] * 4
    n_sel = []
    cols = st.columns(2)
    for i, (nom_e, cod_e) in enumerate(legs):
        aptos = df_nad[df_nad['codnadador'].isin(df_tiempos_50[df_tiempos_50['codestilo'] == cod_e]['codnadador'])]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        n_sel.append(cols[i % 2].selectbox(f"{nom_e}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"man_sel_{i}"))

    if st.button("🚀 Calcular Posta", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in n_sel]
            if s_gen == "X" and (gens.count("M") != 2 or gens.count("F") != 2):
                st.error("⚠️ Error: Mixto requiere 2 hombres y 2 mujeres.")
            else:
                m_loc = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
                tiempos_p = [m_loc[n_sel[i]].get(legs[i][1], 999.0) for i in range(4)]
                total = sum(tiempos_p)
                se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
                cat_n, _ = get_cat_info(se, s_reg_m)

                st.markdown(f"""
                <div style='background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid red; color: #333;'>
                    <div style='display: flex; justify-content: space-between; font-size: 14px;'>
                        <span><b>TIEMPO:</b> {seg_a_tiempo(total)}</span>
                        <span><b>CAT:</b> {cat_n.upper()}</span>
                        <span><b>SUMA:</b> {se} años</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                t_cols = st.columns(4)
                for i in range(4):
                    t_cols[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(tiempos_p[i]))

                st.write("---")
                obs = analizar_competitividad(total, se, s_gen)
                ids_a = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
                hist = data['relevos'][data['relevos'].apply(lambda r: sorted([int(r['nadador_1']), int(r['nadador_2']), int(r['nadador_3']), int(r['nadador_4'])]) == ids_a if pd.notnull(r['nadador_1']) else False, axis=1)]
                if not hist.empty:
                    ant = hist.sort_values('tiempo_final').iloc[0]
                    ip = dict_piletas.get(ant['codpileta'], {"club": "Sede ?", "medida": "-"})
                    obs += f"\n\n📋 **ANT:** {ant['tiempo_final']} en **{ip['club']}** ({ant['fecha']})."
                if obs: st.info(obs)
        else: st.error("Seleccione 4 nadadores.")

# --- 5. SIMULADOR POR GRUPO (AGRUPADO POR CATEGORÍA) ---
st.divider()
st.subheader("🎯 Simulador por grupo de nadadores en competencia")
with st.container(border=True):
    pool = st.multiselect("Pool de Convocados:", sorted(df_nad['Nombre Completo'].tolist()), key="pool_opt_g")
    c1, c2, c3 = st.columns(3)
    o_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="o_reg_g")
    o_tipo = c2.radio("Estilo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
    o_gen_sel = c3.radio("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
    o_gen = "X" if "Mixto" in o_gen_sel else ("M" if "(M)" in o_gen_sel else "F")

if st.button("🪄 Generar Estrategia Óptima", type="primary", use_container_width=True):
    if len(pool) < 4: st.warning("⚠️ Seleccione al menos 4 nadadores.")
    else:
        with st.spinner("Buscando alternativas..."):
            m_map = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
            for n in pool: m_map[n].update({'gen': df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0], 'edad': df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]})
            legs_o = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
            
            # 1. Encontrar TODAS las combinaciones posibles válidas
            pool_act, resultados_brutos = list(pool), []
            combis = [c for c in itertools.combinations(pool, 4) if (o_gen=="M" and all(m_map[n]['gen']=="M" for n in c)) or (o_gen=="F" and all(m_map[n]['gen']=="F" for n in c)) or (o_gen=="X" and [m_map[n]['gen'] for n in c].count("M")==2)]
            
            for c in combis:
                mt, mo = 999.0, None
                for p in itertools.permutations(c):
                    tp = sum([m_map[p[idx]].get(legs_o[idx][0], 999.0) for idx in range(4)])
                    if tp < mt: mt, mo = tp, p
                if mo:
                    se = sum([m_map[n]['edad'] for n in mo])
                    cn, _ = get_cat_info(se, o_reg)
                    resultados_brutos.append({'eq': mo, 't': mt, 'cat': cn, 'se': se})

            if not resultados_brutos:
                st.info("No se pudieron conformar relevos.")
            else:
                # 2. Agrupar por categoría
                # Ordenamos por tiempo para que al agrupar, la primera de cada categoría sea la mejor
                df_res = pd.DataFrame(resultados_brutos).sort_values(by=['cat', 't'])
                
                # 3. Mostrar visualmente agrupado
                for cat_nombre, group in df_res.groupby('cat'):
                    st.markdown(f"#### 🚩 Categoría: {cat_nombre.upper()}")
                    # Tomamos máximo 2 alternativas por categoría para no saturar
                    for idx, row in group.head(2).iterrows():
                        label = "Equipo A (Mejor)" if idx == group.index[0] else "Equipo B (Alternativa)"
                        with st.expander(f"{label}: {seg_a_tiempo(row['t'])}", expanded=True if idx == group.index[0] else False):
                            st.markdown(f"""
                            <div style='background-color: #1e1e1e; padding: 8px; border-radius: 5px; color: white; display: flex; justify-content: space-around; font-size: 13px;'>
                                <span><b>TIEMPO:</b> {seg_a_tiempo(row['t'])}</span>
                                <span><b>SUMA:</b> {row['se']} años</span>
                            </div>
                            """, unsafe_allow_html=True)
                            cs = st.columns(4)
                            for j in range(4):
                                cs[j].write(f"*{legs_o[j][1]}*\n\n{row['eq'][j].split(',')[0]}")
                                cs[j].code(seg_a_tiempo(m_map[row['eq'][j]].get(legs_o[j][0], 999.0)))
                            comp = analizar_competitividad(row['t'], row['se'], o_gen)
                            if comp: st.success(comp)
