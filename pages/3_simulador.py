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
        # Año base para cálculo Master
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
        if r['suma_min'] <= suma <= r['suma_max']: 
            return r['descripcion'], r['suma_min'] # Retornamos suma_min para ordenar
    return f"Suma {int(suma)}", suma

# --- ESTILO DE TARJETA MEJORADA ---
def render_tarjeta_resumen(tiempo, categoria, suma, dark=False):
    bg = "#1e1e1e" if dark else "#f0f2f6"
    text = "#ffffff" if dark else "#31333F"
    border = "red"
    st.markdown(f"""
        <div style='background-color: {bg}; padding: 15px; border-radius: 10px; border-left: 8px solid {border}; color: {text}; margin-bottom: 20px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);'>
            <div style='display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;'>
                <div style='text-align: center; margin: 5px 15px;'>
                    <small style='text-transform: uppercase; color: #888; font-weight: bold;'>Tiempo</small><br>
                    <span style='font-size: 28px; font-family: monospace; font-weight: bold;'>{tiempo}</span>
                </div>
                <div style='text-align: center; margin: 5px 15px;'>
                    <small style='text-transform: uppercase; color: #888; font-weight: bold;'>Categoría</small><br>
                    <span style='font-size: 22px; color: #ff4b4b; font-weight: bold;'>{categoria.upper()}</span>
                </div>
                <div style='text-align: center; margin: 5px 15px;'>
                    <small style='text-transform: uppercase; color: #888; font-weight: bold;'>Suma</small><br>
                    <span style='font-size: 22px; font-weight: bold;'>{suma} <small>años</small></span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

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
            m_loc = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
            tiempos_p = [m_loc[n_sel[i]].get(legs[i][1], 999.0) for i in range(4)]
            total = sum(tiempos_p)
            se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
            cat_n, _ = get_cat_info(se, s_reg_m)

            # Render de tarjeta mejorada (Posta Manual)
            render_tarjeta_resumen(seg_a_tiempo(total), cat_n, se)

            t_cols = st.columns(4)
            for i in range(4):
                t_cols[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(tiempos_p[i]))
        else: st.error("Seleccione 4 nadadores.")

# --- 5. SIMULADOR POR GRUPO (ORDENADO Y MEJORADO) ---
st.divider()
st.subheader("🎯 Simulador por grupo de nadadores")
with st.container(border=True):
    pool = st.multiselect("Seleccionar nadadores del grupo:", sorted(df_nad['Nombre Completo'].tolist()), key="pool_opt_g")
    c1, c2, c3 = st.columns(3)
    o_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="o_reg_g")
    o_tipo = c2.radio("Estilo de Prueba", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
    o_gen_sel = c3.radio("Género Prueba", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
    o_gen = "X" if "Mixto" in o_gen_sel else ("M" if "(M)" in o_gen_sel else "F")

if st.button("🪄 Generar Estrategia Óptima", type="primary", use_container_width=True):
    if len(pool) < 4: st.warning("⚠️ Seleccione al menos 4 nadadores.")
    else:
        with st.spinner("Calculando mejores combinaciones..."):
            m_map = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
            for n in pool: m_map[n].update({'gen': df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0], 'edad': df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]})
            legs_o = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
            
            combis = [c for c in itertools.combinations(pool, 4) if (o_gen=="M" and all(m_map[n]['gen']=="M" for n in c)) or (o_gen=="F" and all(m_map[n]['gen']=="F" for n in c)) or (o_gen=="X" and [m_map[n]['gen'] for n in c].count("M")==2)]
            
            resultados = []
            for c in combis:
                mt, mo = 999.0, None
                for p in itertools.permutations(c):
                    tp = sum([m_map[p[idx]].get(legs_o[idx][0], 999.0) for idx in range(4)])
                    if tp < mt: mt, mo = tp, p
                if mo:
                    se = sum([m_map[n]['edad'] for n in mo])
                    cn, s_min = get_cat_info(se, o_reg)
                    resultados.append({'eq': mo, 't': mt, 'cat': cn, 'se': se, 's_min': s_min})

            if not resultados:
                st.info("No se encontraron combinaciones válidas.")
            else:
                # ORDENAMIENTO POR CATEGORÍA (Menor a mayor edad)
                df_res = pd.DataFrame(resultados).sort_values(by=['s_min', 't'])
                
                for cat_nombre, group in df_res.groupby('cat', sort=False):
                    st.markdown(f"### 🚩 {cat_nombre.upper()}")
                    for idx, row in group.head(2).iterrows():
                        label = "EQUIPO A" if idx == group.index[0] else "EQUIPO B"
                        with st.expander(f"{label} - {seg_a_tiempo(row['t'])}", expanded=True if idx == group.index[0] else False):
                            
                            # Render de tarjeta mejorada (Simulador Grupo)
                            render_tarjeta_resumen(seg_a_tiempo(row['t']), row['cat'], row['se'], dark=True)
                            
                            cs = st.columns(4)
                            for j in range(4):
                                cs[j].write(f"**{legs_o[j][1]}**")
                                cs[j].write(row['eq'][j].split(',')[0])
                                cs[j].code(seg_a_tiempo(m_map[row['eq'][j]].get(legs_o[j][0], 999.0)))
