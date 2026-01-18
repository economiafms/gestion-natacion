import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro - NOB", layout="wide")
st.markdown("<h3 style='text-align: center; color: red;'>🔴⚫ ARMADOR DE PLANILLA DE RELEVOS - NOB</h3>", unsafe_allow_html=True)

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

# --- 3. GESTIÓN DE LA PLANILLA (Session State) ---
if 'relevos_confirmados' not in st.session_state:
    st.session_state.relevos_confirmados = []
if 'nadadores_ocupados' not in st.session_state:
    st.session_state.nadadores_ocupados = set()

# --- 4. FUNCIONES TÉCNICAS ---
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
            return r['descripcion'], r['suma_min']
    return f"Suma {int(suma)}", suma

def render_tarjeta_resumen(tiempo, categoria, suma, dark=False):
    bg = "#1e1e1e" if dark else "#f8f9fa"
    text = "#ffffff" if dark else "#31333F"
    st.markdown(f"""
        <div style='background-color: {bg}; padding: 12px; border-radius: 10px; border-left: 8px solid red; color: {text}; margin-bottom: 10px;'>
            <div style='display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap;'>
                <div style='text-align: center;'><b>{tiempo}</b><br><small style='color: #888;'>TIEMPO</small></div>
                <div style='text-align: center;'><b style='color: #ff4b4b;'>{categoria.upper()}</b><br><small style='color: #888;'>CAT</small></div>
                <div style='text-align: center;'><b>{suma} <small>años</small></b><br><small style='color: #888;'>SUMA</small></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 5. PANEL DE CONTROL Y PLANILLA ACTUAL ---
with st.sidebar:
    st.header("📋 Planilla del Torneo")
    if st.button("🔄 Reiniciar Planilla"):
        st.session_state.relevos_confirmados = []
        st.session_state.nadadores_ocupados = set()
        st.rerun()
    
    st.write(f"Nadadores asignados: {len(st.session_state.nadadores_ocupados)}")
    for i, rel in enumerate(st.session_state.relevos_confirmados):
        with st.expander(f"POSTA {i+1}: {rel['cat']}"):
            st.write(f"⏱️ {rel['tiempo']}")
            st.caption(" / ".join([n.split(',')[0] for n in rel['eq']]))

# --- 6. CONFIGURACIÓN DEL TORNEO ---
st.subheader("1. Configuración de la Prueba")
c1, c2, c3 = st.columns(3)
o_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique())
o_tipo = c2.radio("Estilo", ["Libre (Crol)", "Combinado (Medley)"], horizontal=True)
o_gen_sel = c3.radio("Género", ["Masculino (M)", "Femenino (F)", "Mixto (2M-2F)"], horizontal=True)
o_gen = "X" if "Mixto" in o_gen_sel else ("M" if "(M)" in o_gen_sel else "F")

# Nadadores que todavía están en el mazo
pool_libre = [n for n in df_nad['Nombre Completo'].tolist() if n not in st.session_state.nadadores_ocupados]

# --- 7. SIMULADOR AUTOMÁTICO CON RESTO DEL POOL ---
st.subheader(f"2. Simulaciones Posibles con Nadadores Libres ({len(pool_libre)})")

if len(pool_libre) < 4:
    st.info("No hay suficientes nadadores libres para conformar un nuevo relevo.")
else:
    with st.spinner("Analizando mejores combinaciones con el pool restante..."):
        # Mapa de marcas solo para los libres
        m_map = {n: {r['codestilo']: tiempo_a_seg(r['tiempo']) for _, r in df_tiempos_50[df_tiempos_50['codnadador'] == df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0]].iterrows()} for n in pool_libre}
        for n in pool_libre: 
            m_map[n].update({'gen': df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0], 'edad': df_nad[df_nad['Nombre Completo'] == n]['Edad_Master'].iloc[0]})
        
        legs_o = [("E2", "Espalda"), ("E3", "Pecho"), ("E1", "Mariposa"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
        
        # Generar combinaciones válidas filtradas por género
        combis = [c for c in itertools.combinations(pool_libre, 4) if (o_gen=="M" and all(m_map[n]['gen']=="M" for n in c)) or (o_gen=="F" and all(m_map[n]['gen']=="F" for n in c)) or (o_gen=="X" and [m_map[n]['gen'] for n in c].count("M")==2)]
        
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
            st.warning("No se encontraron combinaciones válidas con los nadadores y el estilo seleccionados.")
        else:
            df_res = pd.DataFrame(resultados).sort_values(by=['s_min', 't'])
            
            # Mostramos agrupado por categoría
            for cat_nombre, group in df_res.groupby('cat', sort=False):
                st.markdown(f"#### 🚩 CATEGORÍA: {cat_nombre.upper()}")
                
                # Solo mostramos la mejor opción de cada categoría para no saturar
                mejor_opcion = group.iloc[0]
                
                with st.container(border=True):
                    render_tarjeta_resumen(seg_a_tiempo(mejor_opcion['t']), mejor_opcion['cat'], mejor_opcion['se'])
                    
                    cs = st.columns(4)
                    for j in range(4):
                        cs[j].write(f"**{legs_o[j][1]}**")
                        cs[j].write(mejor_opcion['eq'][j])
                        cs[j].code(seg_a_tiempo(m_map[mejor_opcion['eq'][j]].get(legs_o[j][0], 999.0)))
                    
                    # El botón clave: Confirma y guarda, quitando a los nadadores de la siguiente simulación
                    if st.button(f"✅ Confirmar {cat_nombre} y Guardar", key=f"save_{cat_nombre}"):
                        st.session_state.relevos_confirmados.append({
                            'cat': mejor_opcion['cat'],
                            'tiempo': seg_a_tiempo(mejor_opcion['t']),
                            'eq': mejor_opcion['eq']
                        })
                        for nad in mejor_opcion['eq']:
                            st.session_state.nadadores_ocupados.add(nad)
                        st.rerun()

# --- 8. VISTA DE PLANILLA FINAL ---
if st.session_state.relevos_confirmados:
    st.divider()
    st.subheader("📝 Planilla Provisoria de Relevos")
    for idx, p in enumerate(st.session_state.relevos_confirmados):
        st.info(f"**POSTA {idx+1}:** {p['cat']} | **Tiempo:** {p['tiempo']} | **Integrantes:** {' / '.join(p['eq'])}")
