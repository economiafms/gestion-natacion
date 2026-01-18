import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro - NOB", layout="wide")
st.markdown("<h3 style='text-align: center; color: red;'>🔴⚫ ARMADO DE POSTAS PASO A PASO</h3>", unsafe_allow_html=True)

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

# --- 3. GESTIÓN DE ESTADO (MEMORIA DEL PROFE) ---
if 'nadadores_bloqueados' not in st.session_state:
    st.session_state.nadadores_bloqueados = []
if 'postas_confirmadas' not in st.session_state:
    st.session_state.postas_confirmadas = []

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

# --- 4. PANEL DE CONTROL (IZQUIERDA) ---
with st.sidebar:
    st.header("⚙️ Gestión del Pool")
    if st.button("🔄 Reiniciar Todo", use_container_width=True):
        st.session_state.nadadores_bloqueados = []
        st.session_state.postas_confirmadas = []
        st.rerun()
    
    st.write(f"**Bloqueados:** {len(st.session_state.nadadores_bloqueados)}")
    for n in st.session_state.nadadores_bloqueados:
        st.caption(f"🚫 {n}")

# --- 5. SIMULADOR DINÁMICO ---
pool_disponible = [n for n in df_nad['Nombre Completo'].tolist() if n not in st.session_state.nadadores_bloqueados]

st.subheader("🏁 Paso 1: Configurar Prueba Actual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    o_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique())
    o_tipo = c2.radio("Estilo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
    o_gen_sel = c3.radio("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
    o_gen = "X" if "Mixto" in o_gen_sel else ("M" if "(M)" in o_gen_sel else "F")

st.subheader(f"👥 Paso 2: Nadadores Disponibles ({len(pool_disponible)})")
pool_seleccionado = st.multiselect("Seleccioná los candidatos para esta prueba:", sorted(pool_disponible))

if st.button("🪄 Buscar Mejores Alternativas", type="primary", use_container_width=True):
    if len(pool_seleccionado) < 4:
        st.warning("Se requieren al menos 4 nadadores.")
    else:
        # Pre-procesar marcas
        m_map = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool_seleccionado}
        for n in pool_seleccionado:
            m_map[n].update({'gen': df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0], 'edad': df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]})
        
        legs_o = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
        
        # Generar combinaciones válidas
        combis = [c for c in itertools.combinations(pool_seleccionado, 4) if (o_gen=="M" and all(m_map[n]['gen']=="M" for n in c)) or (o_gen=="F" and all(m_map[n]['gen']=="F" for n in c)) or (o_gen=="X" and [m_map[n]['gen'] for n in c].count("M")==2 and [m_map[n]['gen'] for n in c].count("F")==2)]
        
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
            st.error("No hay combinaciones posibles con estos nadadores para esta prueba.")
        else:
            st.write("### 🏆 Alternativas Encontradas")
            df_res = pd.DataFrame(resultados).sort_values('t').head(5)
            
            for idx, row in df_res.iterrows():
                with st.expander(f"OPCIÓN {idx+1}: {row['cat']} - Tiempo: {seg_a_tiempo(row['t'])}", expanded=(idx==0)):
                    st.markdown(f"**Suma:** {row['se']} años | **Categoría:** {row['cat']}")
                    cols = st.columns(4)
                    for j in range(4):
                        cols[j].caption(legs_o[j][1])
                        cols[j].write(row['eq'][j])
                        cols[j].code(seg_a_tiempo(m_map[row['eq'][j]].get(legs_o[j][0], 999.0)))
                    
                    if st.button(f"✅ Confirmar Equipo {idx+1}", key=f"conf_{idx}"):
                        st.session_state.nadadores_bloqueados.extend(row['eq'])
                        st.session_state.postas_confirmadas.append({
                            'prueba': f"{o_tipo} {o_gen_sel}",
                            'cat': row['cat'],
                            'tiempo': seg_a_tiempo(row['t']),
                            'integrantes': row['eq']
                        })
                        st.success("Equipo confirmado y nadadores bloqueados. Re-calculando...")
                        st.rerun()

# --- 6. RESUMEN DE POSTAS ARMADAS ---
if st.session_state.postas_confirmadas:
    st.divider()
    st.subheader("📋 Resumen de la Planilla")
    for p in st.session_state.postas_confirmadas:
        with st.container(border=True):
            st.write(f"**{p['prueba']}** | Categoría: **{p['cat']}** | Tiempo: **{p['tiempo']}**")
            st.caption(" / ".join(p['integrantes']))
