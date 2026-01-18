import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro - NOB", layout="wide")
st.markdown("<h2 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE ESTRATEGIA - NOB</h2>", unsafe_allow_html=True)

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
        df_n['AnioNac'] = pd.to_datetime(df_n['fechanac']).dt.year
        df_n['Edad_Master'] = 2026 - df_n['AnioNac']
        
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
    benchmarks = {
        "M": {119: 112, 159: 115, 199: 119, 239: 130}, 
        "F": {119: 132, 159: 135, 199: 145, 239: 165}, 
        "X": {119: 120, 159: 124, 199: 128, 239: 145}  
    }
    limites = sorted(benchmarks.get(genero, {}).keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks.get(genero, {}):
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta:
            return f"🔥 **NIVEL CENARD.** Tiempo de podio nacional ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 10:
            return f"✨ **NIVEL COMPETITIVO.** A solo {seg_a_tiempo(tiempo_seg - meta)} del podio nacional."
    return ""

# --- 4. POSTA MANUAL ---
st.subheader("🧪 Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="reg_manual")
    s_tipo_rel = c2.selectbox("Prueba", ["Libre (Crol)", "Combinado (Medley)"], key="tipo_manual")
    s_gen_input = c3.selectbox("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], key="gen_manual")
    s_gen = "X" if "Mixto" in s_gen_input else ("M" if "(M)" in s_gen_input else "F")

    legs = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    
    n_sel = []
    cols = st.columns(4)
    for i, (nom_e, cod_e) in enumerate(legs):
        ids_e = df_tiempos_50[df_tiempos_50['codestilo'] == cod_e]['codnadador'].unique()
        aptos = df_nad[df_nad['codnadador'].isin(ids_e)]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        n_sel.append(cols[i].selectbox(f"{nom_e}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"man_{i}"))

    if st.button("🚀 Calcular Posta", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in n_sel]
            if s_gen == "X" and (gens.count("M") != 2 or gens.count("F") != 2):
                st.error("⚠️ Error: El relevo mixto requiere exactamente 2 hombres (M) y 2 mujeres (F).")
            else:
                marcas = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
                tiempos_p = [marcas[n_sel[i]].get(legs[i][1], 999.0) for i in range(4)]
                total = sum(tiempos_p)
                se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
                cat_nom, _ = get_cat_info(se, s_reg)

                # CORRECCIÓN DE COLOR: Fondo oscuro, texto blanco y rojo para alto contraste
                st.markdown(f"""<div style='background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 10px solid red; color: white;'>
                    <span style='font-size: 20px;'>TIEMPO TOTAL: <b style='color: #ffffff;'>{seg_a_tiempo(total)}</b></span><br>
                    <span style='font-size: 20px;'>CATEGORÍA: <b style='color: #ff4b4b;'>{cat_nom.upper()}</b></span><br>
                    <span style='font-size: 14px; color: #aaaaaa;'>Suma de edades: {se} años</span></div>""", unsafe_allow_html=True)

                t_cols = st.columns(4)
                for i in range(4):
                    t_cols[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(tiempos_p[i]))
                    t_cols[i].caption(f"Estilo: {legs[i][0]}")

                st.write("---")
                obs = analizar_competitividad(total, se, s_gen)
                ids_a = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
                hist = data['relevos'][data['relevos'].apply(lambda r: sorted([int(r['nadador_1']), int(r['nadador_2']), int(r['nadador_3']), int(r['nadador_4'])]) == ids_a if pd.notnull(r['nadador_1']) else False, axis=1)]
                
                if not hist.empty:
                    ant = hist.sort_values('tiempo_final').iloc[0]
                    ip = dict_piletas.get(ant['codpileta'], {"club": "Sede ?", "medida": "-"})
                    obs += f"\n\n📋 **ANTECEDENTE:** Ya compitieron en **{ip['club']} ({ip['medida']})** el {ant['fecha']} con un tiempo de **{ant['tiempo_final']}**."
                st.info(obs if obs != "" else "Cálculo finalizado sin observaciones adicionales.")
        else: st.error("Seleccione 4 nadadores únicos.")

# --- 5. SIMULADOR POR GRUPO (CON CATCH DE ERRORES) ---
st.divider()
st.subheader("🎯 Simulador de relevos por grupo de nadadores en competencia")

with st.container(border=True):
    pool = st.multiselect("Pool de Convocados:", sorted(df_nad['Nombre Completo'].tolist()))
    col1, col2, col3 = st.columns(3)
    o_reg = col1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="reg_group")
    o_tipo = col2.radio("Estilo de Prueba", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
    o_gen_in = col3.radio("Género Prueba", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
    o_gen = "X" if "Mixto" in o_gen_in else ("M" if "(M)" in o_gen_in else "F")

if st.button("🪄 Generar Estrategia Óptima", type="primary", use_container_width=True):
    # CATCH 1: Validación de cantidad mínima
    if len(pool) < 4: 
        st.warning("⚠️ **CATCH:** Se requieren al menos 4 nadadores seleccionados para procesar un relevo.")
    else:
        try:
            with st.spinner("Procesando mejores combinaciones..."):
                m_map = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
                for n in pool:
                    m_map[n]['gen'] = df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0]
                    m_map[n]['edad'] = df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]

                # CATCH 2: Validación de Géneros en el pool
                p_m = [n for n in pool if m_map[n]['gen'] == "M"]
                p_f = [n for n in pool if m_map[n]['gen'] == "F"]
                
                continuar = True
                if o_gen == "M" and len(p_m) < 4:
                    st.error(f"❌ **CATCH:** No hay suficientes hombres (M). Tenés {len(p_m)}, necesitás 4."); continuar = False
                elif o_gen == "F" and len(p_f) < 4:
                    st.error(f"❌ **CATCH:** No hay suficientes mujeres (F). Tenés {len(p_f)}, necesitás 4."); continuar = False
                elif o_gen == "X" and (len(p_m) < 2 or len(p_f) < 2):
                    st.error(f"❌ **CATCH:** No hay balance para Mixto. Tenés {len(p_m)}M y {len(p_f)}F (necesitás 2 y 2)."); continuar = False

                if continuar:
                    legs_o = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
                    pool_act, propuestas, cats_ok = list(pool), [], []

                    # CATCH 3: Lógica de búsqueda optimizada
                    combis = list(itertools.combinations(pool_act, 4))
                    validas = []
                    for c in combis:
                        gs = [m_map[n]['gen'] for n in c]
                        if (o_gen == "M" and all(g=="M" for g in gs)) or (o_gen == "F" and all(g=="F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2 and gs.count("F") == 2):
                            mt, mo = 999.0, None
                            for p in itertools.permutations(c):
                                tp = sum([m_map[p[idx]].get(legs_o[idx][0], 999.0) for idx in range(4)])
                                if tp < mt: mt, mo = tp, p
                            if mo:
                                se = sum([m_map[n]['edad'] for n in mo])
                                cn, cm = get_cat_info(se, o_reg)
                                validas.append({'eq': mo, 't': mt, 'cat': cn, 'se': se})

                    if not validas:
                        st.info("⚠️ **CATCH:** Los nadadores seleccionados no tienen marcas cargadas suficientes para conformar este relevo.")
                    else:
                        while len(pool_act) >= 4 and validas:
                            dispo = [v for v in validas if all(n in pool_act for n in v['eq'])]
                            if not dispo: break
                            mejor = min(dispo, key=lambda x: x['t'])
                            propuestas.append(mejor)
                            for n in mejor['eq']: pool_act.remove(n)

                        for i, p in enumerate(propuestas):
                            with st.expander(f"POSTA #{i+1}: {p['cat']} ({seg_a_tiempo(p['t'])})", expanded=True):
                                st.markdown(f"**Tiempo Final: {seg_a_tiempo(p['t'])}**")
                                cs = st.columns(4)
                                for j in range(4):
                                    cs[j].write(f"*{legs_o[j][1]}*\n\n{p['eq'][j]}")
                                    cs[j].code(seg_a_tiempo(m_map[p['eq'][j]].get(legs_o[j][0], 999.0)))
        except Exception as e:
            st.error(f"⚠️ **CATCH DE SISTEMA:** Ocurrió un error inesperado en el procesamiento ({e}). Intente con menos nadadores.")
