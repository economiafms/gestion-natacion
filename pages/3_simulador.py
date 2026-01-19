import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro - NOB", layout="wide")

# --- 2. SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

# CSS ESTILO RANKING (ADAPTADO PARA SIMULADOR)
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; }
        h3 { margin-bottom: 0; }
        
        /* ESTILO TARJETA TIPO RANKING */
        .relay-card {
            background-color: #262730;
            border: 1px solid #444;
            border-radius: 10px;
            padding: 12px 15px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .relay-pos { 
            font-size: 20px; 
            font-weight: bold; 
            color: #E30613; 
            width: 40px; 
            text-align: center; 
            border-right: 1px solid #444;
            margin-right: 15px;
        }
        .relay-info { flex-grow: 1; }
        .relay-name { font-weight: bold; font-size: 15px; color: white; margin-bottom: 2px; }
        .relay-style { font-size: 12px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
        .relay-time { font-family: monospace; font-weight: bold; font-size: 18px; color: #4CAF50; text-align: right; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; color: #E30613;'>🔴⚫ SIMULADOR DE ESTRATEGIA - NOB</h3>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN DE TIEMPO ---
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999.0

# --- 3. CARGA DE DATOS ---
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
        df_n['Edad_Master'] = datetime.now().year - pd.to_datetime(df_n['fechanac']).dt.year
        
        df_t = data['tiempos'][data['tiempos']['coddistancia'] == 'D1'].copy()
        df_t['segundos_calc'] = df_t['tiempo'].apply(tiempo_a_seg)
        df_t = df_t.sort_values(by=['codnadador', 'codestilo', 'segundos_calc'], ascending=[True, True, True])
        df_t_50_best = df_t.drop_duplicates(subset=['codnadador', 'codestilo'], keep='first')
        
        return data, df_n, df_t_50_best
    except: return None, None, None

data, df_nad, df_tiempos_50 = cargar_datos_sim()
if not data: st.stop()

dict_piletas = data['piletas'].set_index('codpileta').to_dict('index')

# --- 4. FUNCIONES TÉCNICAS ---
def seg_a_tiempo(seg):
    if seg >= 900: return "S/T"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def get_cat_info(suma, reg):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: 
            return r['descripcion'], r['suma_min']
    return f"Suma {int(suma)}", suma

def analizar_competitividad(tiempo_seg, suma_edades, genero):
    benchmarks = {"M": {119: 112, 159: 115, 199: 119, 239: 130}, "F": {119: 132, 159: 135, 199: 145, 239: 165}, "X": {119: 120, 159: 124, 199: 128, 239: 145}}
    limites = sorted(benchmarks.get(genero, {}).keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks.get(genero, {}):
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **NIVEL PODIO.** Tiempo ref: {seg_a_tiempo(meta)}."
        elif tiempo_seg <= meta + 10: return f"✨ **COMPETITIVO.** Cerca de marcas."
    return ""

def render_tarjeta_resumen(tiempo, categoria, suma, dark=False):
    bg = "#1e1e1e" if dark else "#f0f2f6"
    text = "#ffffff" if dark else "#31333F"
    st.markdown(f"""
        <div style='background-color: {bg}; padding: 15px; border-radius: 10px; border-left: 8px solid #E30613; color: {text}; margin-bottom: 20px; margin-top: 10px;'>
            <div style='display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;'>
                <div style='text-align: center;'>
                    <b style='font-size: 28px; font-family: monospace;'>{tiempo}</b><br>
                    <small style='color: #888;'>TIEMPO TOTAL</small>
                </div>
                <div style='text-align: center;'>
                    <b style='font-size: 20px; color: #E30613;'>{categoria.upper()}</b><br>
                    <small style='color: #888;'>CATEGORÍA</small>
                </div>
                <div style='text-align: center;'>
                    <b style='font-size: 22px;'>{suma} <small>años</small></b><br>
                    <small style='color: #888;'>SUMA</small>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 5. POSTA MANUAL ---
st.write("") 
st.subheader("🧪 Armar Posta Manual")

with st.container(border=True):
    # Selectores generales (Columnas para ahorrar espacio vertical al inicio)
    c1, c2, c3 = st.columns(3)
    s_reg_m = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="s_reg_m")
    s_tipo_m = c2.selectbox("Prueba", ["Libre (Crol)", "Combinado (Medley)"], key="s_tipo_m")
    s_gen_sel = c3.selectbox("Género", ["Masculino (M)", "Femenino (F)", "Mixto"], key="s_gen_m")
    
    s_gen = "X" if "Mixto" in s_gen_sel else ("M" if "(M)" in s_gen_sel else "F")
    legs = [("Espalda", "E2"), ("Pecho", "E3"), ("Mariposa", "E1"), ("Crol", "E4")] if "Medley" in s_tipo_m else [("Crol", "E4")] * 4
    n_sel = []
    
    # SELECTORES DE NADADORES (SIN COLUMNAS - APILADOS PARA MOBILE)
    for i, (nom_e, cod_e) in enumerate(legs):
        aptos = df_nad[df_nad['codnadador'].isin(df_tiempos_50[df_tiempos_50['codestilo'] == cod_e]['codnadador'])]
        if s_gen != "X": aptos = aptos[aptos['codgenero'] == s_gen]
        # Selector apilado (full width)
        n_sel.append(st.selectbox(f"Posta {i+1}: {nom_e}", sorted(aptos['Nombre Completo'].tolist()), index=None, key=f"man_sel_{i}"))

    btn_manual = st.button("🚀 Calcular Posta", type="primary", use_container_width=True)

# Contenedor resultados
res_manual_container = st.container()

if btn_manual:
    if None in n_sel:
        st.warning("⚠️ Faltan nadadores. Selecciona los 4 integrantes.")
    elif len(set(n_sel)) < 4:
        st.error("⛔ **Error:** Nadador repetido. El equipo debe tener 4 integrantes distintos.")
    else:
        with st.spinner("Calculando..."):
            m_loc = {n: {r['codestilo']: r['segundos_calc'] for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in n_sel}
            tiempos_p = [m_loc[n_sel[i]].get(legs[i][1], 999.0) for i in range(4)]
            total = sum(tiempos_p)
            se = sum([df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0] for n in n_sel])
            cat_n, _ = get_cat_info(se, s_reg_m)

            with res_manual_container:
                render_tarjeta_resumen(seg_a_tiempo(total), cat_n, se)

                # --- VISUALIZACIÓN TIPO RANKING (CARDS) ---
                st.markdown("##### ⏱️ Parciales")
                for i in range(4):
                    nadador_nombre = n_sel[i].split(',')[0] # Solo Apellido
                    estilo_nombre = legs[i][0]
                    tiempo_parcial = seg_a_tiempo(tiempos_p[i])
                    
                    st.markdown(f"""
                    <div class="relay-card">
                        <div class="relay-pos">{i+1}</div>
                        <div class="relay-info">
                            <div class="relay-name">{nadador_nombre}</div>
                            <div class="relay-style">{estilo_nombre}</div>
                        </div>
                        <div class="relay-time">{tiempo_parcial}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Observaciones
                obs_lista = []
                comp = analizar_competitividad(total, se, s_gen)
                if comp: obs_lista.append(comp)
                
                ids_a = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in n_sel])
                hist = data['relevos'][data['relevos'].apply(lambda r: sorted([int(r['nadador_1']), int(r['nadador_2']), int(r['nadador_3']), int(r['nadador_4'])]) == ids_a if pd.notnull(r['nadador_1']) else False, axis=1)]
                if not hist.empty:
                    ant = hist.sort_values('tiempo_final').iloc[0]
                    ip = dict_piletas.get(ant['codpileta'], {"club": "?", "medida": "-"})
                    obs_lista.append(f"⏱️ **ANTECEDENTE:** {ant['tiempo_final']} en {ip['club']} ({ip['medida']}) el {ant['fecha']}.")
                
                mejor_t, mejor_o = total, n_sel
                for p in itertools.permutations(n_sel):
                    tp = sum([m_loc[p[idx]].get(legs[idx][1], 999.0) for idx in range(4)])
                    if tp < (mejor_t - 0.05): mejor_t, mejor_o = tp, p
                if mejor_t < total:
                    obs_lista.append(f"💡 **ORDEN:** Bajan a **{seg_a_tiempo(mejor_t)}** cambiando orden.")

                if obs_lista:
                    st.divider()
                    st.markdown("##### 📋 Observaciones")
                    for item in obs_lista: st.info(item)

# --- 6. SIMULADOR POR GRUPO ---
st.divider()
st.subheader("🎯 Simulador por Grupo")
with st.container(border=True):
    pool = st.multiselect("Seleccionar nadadores:", sorted(df_nad['Nombre Completo'].tolist()), key="pool_opt_g")
    c1, c2, c3 = st.columns(3)
    o_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="o_reg_g")
    o_tipo = c2.radio("Estilo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
    o_gen_sel = c3.radio("Género", ["Masculino (M)", "Femenino (F)", "Mixto"], horizontal=True)
    o_gen = "X" if "Mixto" in o_gen_sel else ("M" if "(M)" in o_gen_sel else "F")

if st.button("🪄 Generar Estrategia Óptima", type="primary", use_container_width=True):
    if len(pool) < 4: st.warning("Seleccione al menos 4 nadadores.")
    else:
        with st.spinner("Calculando..."):
            m_map = {n: {r['codestilo']: r['segundos_calc'] for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool}
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

            if not resultados: st.info("No se encontraron combinaciones válidas.")
            else:
                df_res = pd.DataFrame(resultados).sort_values(by=['s_min', 't'])
                for cat_nombre, group in df_res.groupby('cat', sort=False):
                    st.markdown(f"### 🚩 {cat_nombre.upper()}")
                    for idx, row in group.head(2).iterrows():
                        label = "EQUIPO A" if idx == group.index[0] else "EQUIPO B"
                        with st.expander(f"{label} - {seg_a_tiempo(row['t'])}", expanded=True if idx == group.index[0] else False):
                            render_tarjeta_resumen(seg_a_tiempo(row['t']), row['cat'], row['se'], dark=True)
                            
                            # USAR TAMBIÉN ESTILO RANKING EN AUTOMÁTICO
                            for j in range(4):
                                nad = row['eq'][j].split(',')[0]
                                est = legs_o[j][1]
                                t = seg_a_tiempo(m_map[row['eq'][j]].get(legs_o[j][0], 999.0))
                                st.markdown(f"""
                                <div class="relay-card">
                                    <div class="relay-pos">{j+1}</div>
                                    <div class="relay-info"><div class="relay-name">{nad}</div><div class="relay-style">{est}</div></div>
                                    <div class="relay-time">{t}</div>
                                </div>""", unsafe_allow_html=True)
                            
                            comp_g = analizar_competitividad(row['t'], row['se'], o_gen)
                            if comp_g:
                                st.markdown("**Observaciones:**")
                                st.success(comp_g)
