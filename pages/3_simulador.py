import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro - NOB", layout="wide")
st.markdown("<h3 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS - NOB</h3>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    try:
        data = {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos"),
            "piletas": conn.read(worksheet="Piletas")
        }
        df_n = data['nadadores'].copy()
        df_n['Nombre Completo'] = df_n['apellido'].astype(str).str.upper() + ", " + df_n['nombre'].astype(str)
        df_n['Edad_Master'] = 2026 - pd.to_datetime(df_n['fechanac']).dt.year
        df_t_50 = data['tiempos'][data['tiempos']['coddistancia'] == 'D1'].copy()
        return data, df_n, df_t_50
    except: return None, None, None

data, df_nad, df_tiempos_50 = cargar_datos_sim()
if not data: st.stop()

dict_piletas = data['piletas'].set_index('codpileta').to_dict('index')

# --- 3. GESTIÓN DE ESTADO (PARA QUITAR PERSONAS) ---
if 'bloqueados' not in st.session_state:
    st.session_state.bloqueados = []
if 'confirmadas' not in st.session_state:
    st.session_state.confirmadas = []

def seg_a_tiempo(seg):
    if seg >= 900: return "S/T"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999.0

def get_cat_info(suma, reg):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: return r['descripcion']
    return f"Suma {int(suma)}"

def analizar_competitividad(tiempo_seg, suma_edades, genero):
    benchmarks = {"M": {119: 112, 159: 115, 199: 119, 239: 130}, "F": {119: 132, 159: 135, 199: 145, 239: 165}, "X": {119: 120, 159: 124, 199: 128, 239: 145}}
    limites = sorted(benchmarks.get(genero, {}).keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks.get(genero, {}):
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **NIVEL CENARD.** Podio ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 10: return f"✨ **NIVEL COMPETITIVO.** Cerca de podio."
    return ""

# --- 4. PANEL DE CONTROL ---
with st.sidebar:
    st.header("📋 Planilla de Torneo")
    if st.button("🔄 Reiniciar Todo", use_container_width=True):
        st.session_state.bloqueados = []
        st.session_state.confirmadas = []
        st.rerun()
    
    for idx, p in enumerate(st.session_state.confirmadas):
        with st.expander(f"Posta {idx+1}: {p['cat']}"):
            st.write(f"**{p['tiempo']}**")
            st.caption("\n".join(p['eq']))

# --- 5. SIMULADOR PASO A PASO ---
pool_libre = [n for n in df_nad['Nombre Completo'].tolist() if n not in st.session_state.bloqueados]

with st.container(border=True):
    st.subheader("1. Configurar Prueba")
    c1, c2, c3 = st.columns(3)
    o_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique())
    o_tipo = c2.radio("Estilo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
    o_gen_in = c3.radio("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
    o_gen = "X" if "Mixto" in o_gen_in else ("M" if "(M)" in o_gen_in else "F")

st.subheader(f"2. Seleccionar Nadadores Disponibles ({len(pool_libre)})")
seleccion = st.multiselect("Buscá por Apellido y Nombre:", sorted(pool_libre))

if st.button("🪄 Buscar Alternativas de Armado", type="primary", use_container_width=True):
    if len(seleccion) < 4:
        st.warning("Elegí al menos 4 nadadores para conformar el equipo.")
    else:
        m_map = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in seleccion}
        for n in seleccion:
            m_map[n].update({'gen': df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0], 'edad': df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]})
        
        legs_o = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
        combis = [c for c in itertools.combinations(seleccion, 4) if (o_gen=="M" and all(m_map[n]['gen']=="M" for n in c)) or (o_gen=="F" and all(m_map[n]['gen']=="F" for n in c)) or (o_gen=="X" and [m_map[n]['gen'] for n in c].count("M")==2 and [m_map[n]['gen'] for n in c].count("F")==2)]
        
        resultados = []
        for c in combis:
            mt, mo = 999.0, None
            for p in itertools.permutations(c):
                tp = sum([m_map[p[idx]].get(legs_o[idx][0], 999.0) for idx in range(4)])
                if tp < mt: mt, mo = tp, p
            if mo:
                se = sum([m_map[n]['edad'] for n in mo])
                resultados.append({'eq': mo, 't': mt, 'se': se, 'cat': get_cat_info(se, o_reg)})

        if not resultados:
            st.error("No hay combinaciones válidas para este género/estilo con los nadadores elegidos.")
        else:
            st.write("### 🥇 Mejores Opciones Encontradas")
            df_res = pd.DataFrame(resultados).sort_values('t').head(3)
            
            for i, row in df_res.iterrows():
                with st.container(border=True):
                    # TARJETA COMPACTA PARA CELULAR
                    st.markdown(f"""
                    <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid red; color: #333;'>
                        <div style='display: flex; justify-content: space-between; font-size: 14px;'>
                            <span><b>TIEMPO:</b> {seg_a_tiempo(row['t'])}</span>
                            <span><b>CAT:</b> {row['cat'].upper()}</span>
                            <span><b>SUMA:</b> {row['se']} años</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    cols = st.columns(4)
                    for j in range(4):
                        cols[j].caption(legs_o[j][1])
                        cols[j].write(row['eq'][j])
                    
                    # OBSERVACIONES Y ANTECEDENTES
                    obs = analizar_competitividad(row['t'], row['se'], o_gen)
                    ids_a = sorted([int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]) for n in row['eq']])
                    hist = data['relevos'][data['relevos'].apply(lambda r: sorted([int(r['nadador_1']), int(r['nadador_2']), int(r['nadador_3']), int(r['nadador_4'])]) == ids_a if pd.notnull(r['nadador_1']) else False, axis=1)]
                    if not hist.empty:
                        ant = hist.sort_values('tiempo_final').iloc[0]
                        ip = dict_piletas.get(ant['codpileta'], {"club": "Sede ?", "medida": "-"})
                        obs += f" | 📋 **ANT:** {ant['tiempo_final']} en {ip['club']}."
                    
                    if obs: st.info(obs)
                    
                    if st.button(f"✅ Confirmar Equipo {i+1}", key=f"btn_{i}"):
                        st.session_state.bloqueados.extend(row['eq'])
                        st.session_state.confirmadas.append({'cat': row['cat'], 'tiempo': seg_a_tiempo(row['t']), 'eq': row['eq']})
                        st.success("Equipo confirmado. Nadadores quitados del pool.")
                        st.rerun()
