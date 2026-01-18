import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Estratégico NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS ESTRATÉGICO</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Análisis de Marcas, Antecedentes y Salto de Categoría</h4>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_datos_sim():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

data = cargar_datos_sim()
if not data: st.stop()

df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

MAP_ESTILOS = {"Mariposa": "E1", "Espalda": "E2", "Pecho": "E3", "Crol": "E4"}
ID_50M = "D1"

# --- 3. FUNCIONES TÉCNICAS ---
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999.0

def seg_a_tiempo(seg):
    if seg >= 900: return "S/T"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def obtener_nadadores_aptos(id_estilo, genero="X"):
    t_filt = data['tiempos'][(data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    ids = t_filt['codnadador'].unique()
    res = df_nad[df_nad['codnadador'].isin(ids)]
    if genero != "X": res = res[res['codgenero'] == genero]
    return sorted(res['Nombre Completo'].tolist())

def obtener_mejor_marca(nombre, id_estilo):
    idn = df_nad[df_nad['Nombre Completo'] == nombre]['codnadador'].iloc[0]
    m = data['tiempos'][(data['tiempos']['codnadador'] == idn) & (data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    if m.empty: return 999.0
    return m['tiempo'].apply(tiempo_a_seg).min()

def get_cat_info(suma, reg):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: return r['descripcion'], r['suma_max']
    return f"Suma {int(suma)}", 999

def analizar_competitividad(tiempo_seg, suma_edades, genero):
    benchmarks = {
        "M": {119: 122, 159: 125, 199: 132, 239: 145},
        "F": {119: 140, 159: 150, 199: 160, 239: 180},
        "X": {119: 128, 159: 135, 199: 140, 239: 160}
    }
    limites = sorted(benchmarks[genero].keys())
    cat_techo = next((l for l in limites if suma_edades <= l), 999)
    if cat_techo in benchmarks[genero]:
        meta = benchmarks[genero][cat_techo]
        if tiempo_seg <= meta: return f"🔥 **TIEMPO COMPETITIVO.** Están por debajo de la marca de referencia ({seg_a_tiempo(meta)})."
        elif tiempo_seg <= meta + 8: return f"✨ **CERCA DEL PODIO.** A solo {seg_a_tiempo(tiempo_seg - meta)} del tiempo objetivo."
    return "📈 **Nivel de entrenamiento.** Objetivo: Bajar marcas individuales."

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Simulación Manual con Antecedentes")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Prueba de Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m3")

    legs = [("Espalda", "E2"), ("Mariposa", "E1"), ("Pecho", "E3"), ("Crol", "E4")] if "Medley" in s_tipo_rel else [("Crol", "E4")] * 4
    n_sel, cols = [], st.columns(4)
    for i, (nombre_est, cod_est) in enumerate(legs):
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nombre_est}", obtener_nadadores_aptos(cod_est, s_gen), index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Simulación e Historial", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            total = 0
            cols_res = st.columns(4)
            for i, (nom_est, cod_est) in enumerate(legs):
                t = obtener_mejor_marca(n_sel[i], cod_est)
                total += t
                cols_res[i].metric(n_sel[i].split(',')[0], seg_a_tiempo(t))
            
            se = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in n_sel])
            cat_desc, _ = get_cat_info(se, s_reg)
            st.success(f"**Categoría: {cat_desc} | Tiempo Simulado: {seg_a_tiempo(total)}**")
            
            # --- COMPARACIÓN CON REGISTRO HISTÓRICO ---
            ids_actuales = sorted([df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0] for n in n_sel])
            def check_eq(row): return sorted([row['nadador_1'], row['nadador_2'], row['nadador_3'], row['nadador_4']]) == ids_actuales
            hist = data['relevos'][data['relevos'].apply(check_eq, axis=1)]
            
            if not hist.empty:
                ant = hist.sort_values('tiempo_final').iloc[0]
                st.info(f"📋 **Antecedente Real Encontrado:** {ant['tiempo_final']} (Fecha: {ant['fecha']})")
                dif = total - tiempo_a_seg(ant['tiempo_final'])
                st.write(f"Diferencia: {'+' if dif > 0 else ''}{dif:.2f}s respecto a la mejor marca real del grupo.")
            
            st.write(analizar_competitividad(total, se, s_gen))
        else:
            st.error("Seleccione 4 nadadores con marcas.")

# --- 5. OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador Estratégico Multi-Posta")
pool = st.multiselect("Nadadores convocados:", sorted(df_nad['Nombre Completo'].tolist()))
g1, g2, g3 = st.columns(3)
o_reg = g1.selectbox("Reglamento Torneo", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = g2.selectbox("Estilo", ["Libre (Crol)", "Combinado (Medley)"], key="o2")
o_gen = g3.selectbox("Género", ["M", "F", "X"], key="o3")

if st.button("🪄 Generar Estrategia de Podios", type="primary", use_container_width=True):
    if len(pool) < 4: st.error("Mínimo 4 nadadores.")
    else:
        legs_opt = [("E2", "Espalda"), ("E1", "Mariposa"), ("E3", "Pecho"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
        pool_actual, propuestas = list(pool), []
        
        with st.spinner("Buscando combinaciones óptimas..."):
            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                for c in combis:
                    gs = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in c]
                    if (o_gen == "M" and all(g == "M" for g in gs)) or (o_gen == "F" and all(g == "F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2):
                        mejor_t, mejor_ord = 999.0, None
                        for p in itertools.permutations(c):
                            t_p, skip = 0, False
                            for idx, (cod_e, _) in enumerate(legs_opt):
                                mv = obtener_mejor_marca(p[idx], cod_e)
                                if mv >= 900: skip = True; break
                                t_p += mv
                            if not skip and t_p < mejor_t: mejor_t, mejor_ord = t_p, p
                        if mejor_ord: validas.append({'equipo': mejor_ord, 'tiempo': mejor_t})
                
                if not validas: break
                mejor_eq = min(validas, key=lambda x: x['tiempo'])
                se_e = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in mejor_eq['equipo']])
                cat_nom, cat_max = get_cat_info(se_e, o_reg)
                propuestas.append({'equipo': mejor_eq['equipo'], 'tiempo': mejor_eq['tiempo'], 'cat': cat_nom, 'suma': se_e, 'suma_max': cat_max,
                                   'parciales': [obtener_mejor_marca(mejor_eq['equipo'][idx], legs_opt[idx][0]) for idx in range(4)]})
                for n in mejor_eq['equipo']: pool_actual.remove(n)

        for i, p in enumerate(propuestas):
            with st.expander(f"Posta #{i+1}: {p['cat']} ({seg_a_tiempo(p['tiempo'])})", expanded=True):
                cols_p = st.columns(4)
                for j in range(4):
                    cols_p[j].write(f"**{legs_opt[j][1]}**")
                    cols_p[j].write(f"{p['equipo'][j]}")
                    cols_p[j].code(seg_a_tiempo(p['parciales'][j]))
                
                st.write(analizar_competitividad(p['tiempo'], p['suma'], o_gen))
                faltante = p['suma_max'] - p['suma']
                if faltante <= 8:
                    st.info(f"💡 **TIP ESTRATÉGICO:** Están a {faltante} años del límite. Evaluar subir de categoría para ganar.")
