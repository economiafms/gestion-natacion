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
        else:
            return False, f"⏳ A **{seg_a_tiempo(tiempo_seg - meta)}** del tiempo de podio nacional ({seg_a_tiempo(meta)})."
    return False, ""

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación de Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Prueba", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen_input = c3.selectbox("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], key="m3")
    
    # Mapeo interno del género
    s_gen = "X" if "Mixto" in s_gen_input else s_gen_input[s_gen_input.find("(")+1:s_gen_input.find(")")]

    legs = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    n_sel, cols = [], st.columns(4)
    for i, (nom_e, cod_e) in enumerate(legs):
        ids_e = df_tiempos_50[df_tiempos_50['codestilo'] == cod_e]['codnadador'].unique()
        aptos = df_nad[df_nad['codnadador'].isin(ids_e)]
        
        # Si es mixto, dejamos elegir de ambos géneros
        if s_gen != "X":
            aptos = aptos[aptos['codgenero'] == s_gen]
            
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nom_e}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Estrategia de Victoria", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Validar Género para Mixto
            generos_sel = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in n_sel]
            if s_gen == "X" and (generos_sel.count("M") != 2 or generos_sel.count("F") != 2):
                st.error("⚠️ Error: Un relevo MIXTO debe tener exactamente 2 hombres (M) y 2 mujeres (F).")
            else:
                marcas = {n: {row['codestilo']: tiempo_a_seg(row['tiempo']) for _, row in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
                total = sum([marcas[n].get(legs[i][1], 999.0) for i, n in enumerate(n_sel)])
                se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
                cat_nom, _ = get_cat_info(se, s_reg)
                
                # --- VISUALIZACIÓN ---
                st.markdown(f"""
                    <div style="background-color: #1e1e1e; padding: 30px; border-radius: 15px; border: 2px solid red; text-align: center; margin-bottom: 20px;">
                        <h1 style="margin: 0; color: white; font-size: 80px; font-family: monospace;">{seg_a_tiempo(total)}</h1>
                        <h2 style="margin: 0; color: #ff4b4b; font-size: 35px;">{cat_nom.upper()}</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                res_c = st.columns(4)
                for i in range(4):
                    res_c[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(marcas[n_sel[i]].get(legs[i][1])))

                # Observaciones
                mejor_t_var, mejor_ord_var = total, n_sel
                for p in itertools.permutations(n_sel):
                    t_p = sum([marcas[p[idx]].get(legs[idx][1], 999.0) for idx in range(4)])
                    if t_p < mejor_t_var: mejor_t_var, mejor_ord_var = t_p, p
                
                is_podio, txt_podio = analizar_competitividad(total, se, s_gen)
                st.write("### 📝 Observaciones")
                obs_txt = txt_podio
                if mejor_t_var < (total - 0.01):
                    obs_txt += f"\n\n💡 **ORDEN ÓPTIMO:** {seg_a_tiempo(mejor_t_var)} si nadan: " + " / ".join([f"**{mejor_ord_var[i].split(',')[0]}**" for i in range(4)])
                
                # Antecedente
                ids_act = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
                def check_eq(row): 
                    try: return sorted([int(row['nadador_1']), int(row['nadador_2']), int(row['nadador_3']), int(row['nadador_4'])]) == ids_act
                    except: return False
                hist = data['relevos'][data['relevos'].apply(check_eq, axis=1)]
                if not hist.empty:
                    ant = hist.sort_values('tiempo_final').iloc[0]
                    ip = dict_piletas.get(ant['codpileta'], {"club": "Sede ?", "medida": "-"})
                    obs_txt += f"\n\n📋 **ANTECEDENTE:** {ant['tiempo_final']} en **{ip['club']} ({ip['medida']})** el {ant['fecha']}."
                st.info(obs_txt)
        else: st.error("Seleccione 4 nadadores únicos.")

# --- 5. OPTIMIZADOR MIXTO ---
st.divider()
st.subheader("🎯 Optimizador de Podios (Incluye Mixto)")
pool = st.multiselect("Convocados:", sorted(df_nad['Nombre Completo'].tolist()))
o_reg = st.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_
