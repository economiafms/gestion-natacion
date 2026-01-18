import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Analista Pro - NOB", layout="wide")
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
            return True, f"✅ **TIEMPO NACIONAL.** Estás en marca de podio ({seg_a_tiempo(meta)})."
        else:
            return False, f"⏳ A **{seg_a_tiempo(tiempo_seg - meta)}** del podio nacional ({seg_a_tiempo(meta)})."
    return False, ""

# --- 4. SIMULADOR MANUAL ---
st.subheader("🧪 Configuración de Posta")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique())
    s_tipo_rel = c2.selectbox("Prueba", ["Libre (Crol)", "Combinado (Medley)"])
    s_gen_input = c3.selectbox("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"])
    s_gen = "X" if "Mixto" in s_gen_input else ("M" if "(M)" in s_gen_input else "F")

    legs = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    
    n_sel = []
    cols = st.columns(4)
    for i, (nom_e, cod_e) in enumerate(legs):
        # Filtro de nadadores aptos por estilo y género
        ids_e = df_tiempos_50[df_tiempos_50['codestilo'] == cod_e]['codnadador'].unique()
        aptos = df_nad[df_nad['codnadador'].isin(ids_e)]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        
        n_sel.append(cols[i].selectbox(f"{nom_e}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"manual_{i}"))

    if st.button("🚀 Calcular Posta", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Validar paridad en Mixto
            gens = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in n_sel]
            if s_gen == "X" and (gens.count("M") != 2 or gens.count("F") != 2):
                st.error("Error: El relevo mixto debe tener 2 hombres y 2 mujeres.")
            else:
                marcas = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
                tiempos_parciales = [marcas[n_sel[i]].get(legs[i][1], 999.0) for i in range(4)]
                total = sum(tiempos_parciales)
                se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
                cat_nom, _ = get_cat_info(se, s_reg)

                # --- RESULTADO DESTACADO (MÁS PEQUEÑO Y TÉCNICO) ---
                st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid red; margin: 10px 0;">
                        <span style="color: #555; font-size: 14px; font-weight: bold;">TIEMPO TOTAL:</span>
                        <span style="color: black; font-size: 28px; font-weight: bold; font-family: monospace; margin-left: 10px;">{seg_a_tiempo(total)}</span>
                        <span style="color: #555; font-size: 14px; font-weight: bold; margin-left: 30px;">CATEGORÍA:</span>
                        <span style="color: red; font-size: 22px; font-weight: bold; margin-left: 10px;">{cat_nom.upper()}</span>
                        <span style="color: #777; font-size: 14px; margin-left: 20px;">(Suma: {se} años)</span>
                    </div>
                """, unsafe_allow_html=True)

                # --- GRILLA TÉCNICA (Nombres, Estilos y Parciales) ---
                st.write("### ⏱️ Detalle por Nadador")
                t_cols = st.columns(4)
                for i in range(4):
                    with t_cols[i]:
                        st.markdown(f"**{legs[i][0]}**")
                        st.markdown(f"**{n_sel[i]}**")
                        st.code(seg_a_tiempo(tiempos_parciales[i]))

                # --- OBSERVACIONES ---
                st.write("---")
                is_podio, txt_podio = analizar_competitividad(total, se, s_gen)
                
                # Buscar mejor combinación
                mejor_t, mejor_o = total, n_sel
                for p in itertools.permutations(n_sel):
                    tp = sum([marcas[p[idx]].get(legs[idx][1], 999.0) for idx in range(4)])
                    if tp < mejor_t: mejor_t, mejor_o = tp, p
                
                obs_final = txt_podio
                if mejor_t < (total - 0.05):
                    det = " / ".join([f"{mejor_o[i].split(',')[0]} ({legs[i][0]})" for i in range(4)])
                    obs_final += f"\n\n💡 **OPTIMIZACIÓN:** Podés bajar a **{seg_a_tiempo(mejor_t)}** si ordenás así: {det}."
                
                # Antecedente Real
                ids_a = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
                hist = data['relevos'][data['relevos'].apply(lambda r: sorted([int(r['nadador_1']), int(r['nadador_2']), int(r['nadador_3']), int(r['nadador_4'])]) == ids_a if pd.notnull(r['nadador_1']) else False, axis=1)]
                if not hist.empty:
                    ant = hist.sort_values('tiempo_final').iloc[0]
                    obs_final += f"\n\n📋 **ANTECEDENTE:** Ya hicieron **{ant['tiempo_final']}** el {ant['fecha']}."

                st.info(obs_final)
        else: st.error("Seleccioná 4 nadadores para calcular.")

# --- 5. OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador de Victoria")
pool = st.multiselect("Convocados:", sorted(df_nad['Nombre Completo'].tolist()), key="pool_opt")
o_tipo = st.radio("Relevo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
o_gen_in = st.radio("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
o_gen = "X" if "Mixto" in o_gen_in else ("M" if "(M)" in o_gen_in else "F")

if st.button("🪄 Armar Mejores Equipos", type="primary"):
    if len(pool) < 4: st.error("Mínimo 4 nadadores.")
    else:
        with st.spinner("Priorizando categorías..."):
            m_map = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
            for n in pool:
                m_map[n]['gen'] = df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0]
                m_map[n]['edad'] = df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]

            legs_opt = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
            pool_actual, propuestas, cats_cubiertas = list(pool), [], []

            while len(pool_actual) >= 4:
                validas = []
                for c in itertools.combinations(pool_actual, 4):
                    gs = [m_map[n]['gen'] for n in c]
                    if (o_gen == "M" and all(g=="M" for g in gs)) or (o_gen == "F" and all(g=="F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2):
                        mt, mo = 999.0, None
                        for p in itertools.permutations(c):
                            tp = sum([m_map[p[idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)])
                            if tp < mt: mt, mo = tp, p
                        if mo:
                            se = sum([m_map[n]['edad'] for n in mo])
                            cn, cm = get_cat_info(se, s_reg)
                            isc, _ = analizar_competitividad(mt, se, o_gen)
                            if cn not in cats_cubiertas or isc:
                                validas.append({'eq': mo, 't': mt, 'cat': cn, 'se': se, 'cmax': cm})
                
                if not validas: break
                mejor = min(validas, key=lambda x: x['t'])
                
                propuestas.append({
                    'eq': mejor['eq'], 't': mejor['t'], 'cat': mejor['cat'], 'se': mejor['se'],
                    'parc': [m_map[mejor['eq'][idx]].get(legs_opt[idx][0], 999.0) for idx in range(4)]
                })
                cats_cubiertas.append(mejor['cat'])
                for n in mejor['eq']: pool_actual.remove(n)

            for i, p in enumerate(propuestas):
                with st.expander(f"POSTA #{i+1}: {p['cat']} ({seg_a_tiempo(p['t'])})", expanded=True):
                    st.write(f"**Tiempo: {seg_a_tiempo(p['t'])}** | Suma: {p['se']} años")
                    cs = st.columns(4)
                    for j in range(4):
                        cs[j].markdown(f"*{legs_opt[j][1]}*")
                        cs[j].write(p['eq'][j])
                        cs[j].code(seg_a_tiempo(p['parc'][j]))
                    is_p, txt_p = analizar_competitividad(p['t'], p['se'], o_gen)
                    st.info(txt_p)
