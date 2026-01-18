import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Estratégico - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ ARMADOR DE RELEVOS ESTRATÉGICO</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Optimización por Estilo y Género - Sin Repeticiones</h4>", unsafe_allow_html=True)

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
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

# Configuración de Identificadores (Basado en tu base de datos)
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
    """Filtra nadadores que tienen marca real en 50m del estilo requerido."""
    t_filt = data['tiempos'][(data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    ids = t_filt['codnadador'].unique()
    res = df_nad[df_nad['codnadador'].isin(ids)]
    if genero != "X": res = res[res['codgenero'] == genero]
    return sorted(res['Nombre Completo'].tolist())

def obtener_mejor_marca(nombre, id_estilo):
    """Retorna los segundos de la mejor marca de 50m. Si no existe, retorna 999.0."""
    idn = df_nad[df_nad['Nombre Completo'] == nombre]['codnadador'].iloc[0]
    m = data['tiempos'][(data['tiempos']['codnadador'] == idn) & (data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    if m.empty: return 999.0
    return m['tiempo'].apply(tiempo_a_seg).min()

def get_cat(suma, reg):
    for _, r in data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg].iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: return r['descripcion']
    return f"Suma {int(suma)}"

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Configuración de Posta Manual")
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique(), key="m1")
    s_tipo_rel = c2.selectbox("Prueba de Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="m2")
    s_gen = c3.selectbox("Género", ["M", "F", "X"], key="m3")

    if s_tipo_rel == "Combinado (Medley)":
        legs = [("Espalda", "E2"), ("Mariposa", "E1"), ("Pecho", "E3"), ("Crol", "E4")]
    else:
        legs = [("Crol", "E4")] * 4

    n_sel = []
    cols = st.columns(4)
    for i, (nombre_est, cod_est) in enumerate(legs):
        aptos = obtener_nadadores_aptos(cod_est, s_gen)
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nombre_est}", aptos, index=None, key=f"sel{i}"))

    if st.button("🚀 Calcular Simulación Real", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            total = 0
            cols_res = st.columns(4)
            for i, (nom_est, cod_est) in enumerate(legs):
                t = obtener_mejor_marca(n_sel[i], cod_est)
                total += t
                cols_res[i].metric(n_sel[i].split(',')[1], seg_a_tiempo(t))
            
            se = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in n_sel])
            st.success(f"**Categoría: {get_cat(se, s_reg)} | Tiempo Total: {seg_a_tiempo(total)}**")
        else:
            st.error("Error: Debes elegir 4 nadadores distintos que tengan marcas en esos estilos.")

# --- 5. OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador de Combinaciones Múltiples")
st.caption("Arma todos los equipos posibles sin repetir nadadores, buscando el mejor tiempo en cada categoría.")

pool = st.multiselect("Nadadores disponibles (Selecciona a todos los convocados):", sorted(df_nad['Nombre Completo'].tolist()))
g1, g2, g3 = st.columns(3)
o_reg = g1.selectbox("Reglamento Torneo", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = g2.selectbox("Estilo del Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="o2")
o_gen = g3.selectbox("Género Relevo", ["M", "F", "X"], key="o3")

if st.button("🪄 Generar Estrategia Ganadora", type="primary"):
    if len(pool) < 4:
        st.error("Se necesitan al menos 4 nadadores convocados.")
    else:
        # Piernas requeridas
        legs_opt = [("E2", "Espalda"), ("E1", "Mariposa"), ("E3", "Pecho"), ("E4", "Crol")] if o_tipo == "Combinado (Medley)" else [("E4", "Crol")]*4
        
        pool_actual = list(pool)
        propuestas = []
        
        while len(pool_actual) >= 4:
            # 1. Encontrar todas las combinaciones de 4 que cumplen género
            combis = list(itertools.combinations(pool_actual, 4))
            validas = []
            
            for c in combis:
                gs = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in c]
                # Validar género
                if (o_gen == "M" and all(g == "M" for g in gs)) or \
                   (o_gen == "F" and all(g == "F" for g in gs)) or \
                   (o_gen == "X" and gs.count("M") == 2):
                    
                    # 2. Encontrar el mejor orden interno para este grupo de 4
                    mejor_t_int = 999.0
                    mejor_ord_int = None
                    for p in itertools.permutations(c):
                        t_p = 0
                        skip = False
                        for idx, (cod_e, _) in enumerate(legs_opt):
                            m_val = obtener_mejor_marca(p[idx], cod_e)
                            if m_val >= 900: # No tiene tiempo en este estilo
                                skip = True; break
                            t_p += m_val
                        if not skip and t_p < mejor_t_int:
                            mejor_t_int = t_p
                            mejor_ord_int = p
                    
                    if mejor_ord_int:
                        validas.append({'equipo': mejor_ord_int, 'tiempo': mejor_t_int})

            if not validas: break
            
            # 3. Elegir el mejor equipo absoluto del pool actual
            mejor_equipo = min(validas, key=lambda x: x['tiempo'])
            se_e = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in mejor_equipo['equipo']])
            
            # Guardar y remover del pool
            propuestas.append({
                'equipo': mejor_equipo['equipo'], 
                'tiempo': mejor_equipo['tiempo'], 
                'cat': get_cat(se_e, o_reg),
                'parciales': [obtener_mejor_marca(mejor_equipo['equipo'][idx], legs_opt[idx][0]) for idx in range(4)]
            })
            for n in mejor_equipo['equipo']: pool_actual.remove(n)

        # 4. Mostrar Resultados
        if propuestas:
            st.success(f"✅ Se formaron {len(propuestas)} equipos competitivos.")
            for i, p in enumerate(propuestas):
                with st.expander(f"Posta #{i+1}: {p['cat']} (Proyección: {seg_a_tiempo(p['tiempo'])})", expanded=True):
                    cols_p = st.columns(4)
                    for j in range(4):
                        cols_p[j].write(f"**{legs_opt[j][1]}**")
                        cols_p[j].write(p['equipo'][j].split(',')[1])
                        cols_p[j].code(seg_a_tiempo(p['parciales'][j]))
        else:
            st.error("No se pudieron formar equipos. Verifica que los nadadores seleccionados tengan marcas en los estilos necesarios.")
