import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Seguro - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS ESTRATÉGICO</h1>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="15m")
def cargar_datos_sim():
    return {
        "nadadores": conn.read(worksheet="Nadadores"),
        "tiempos": conn.read(worksheet="Tiempos"),
        "relevos": conn.read(worksheet="Relevos"),
        "estilos": conn.read(worksheet="Estilos"),
        "distancias": conn.read(worksheet="Distancias"),
        "cat_relevos": conn.read(worksheet="Categorias_Relevos")
    }

data = cargar_datos_sim()
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

MAP_ESTILOS = {"Mariposa": "E1", "Espalda": "E2", "Pecho": "E3", "Crol": "E4"}
ID_50M = "D1"

# --- FUNCIONES TÉCNICAS ---
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999.0

def seg_a_tiempo(seg):
    if seg >= 900: return "S/T"
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

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

# --- OPTIMIZADOR (VERSIÓN PROTEGIDA) ---
st.divider()
st.subheader("🎯 Optimizador Estratégico")
pool = st.multiselect("Convocados:", sorted(df_nad['Nombre Completo'].tolist()), help="Si seleccionas más de 12, el cálculo puede demorar.")

g1, g2, g3 = st.columns(3)
o_reg = g1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique())
o_tipo = g2.selectbox("Estilo", ["Libre (Crol)", "Combinado (Medley)"])
o_gen = g3.selectbox("Género", ["M", "F", "X"])

if st.button("🪄 Generar Estrategia", type="primary"):
    if len(pool) < 4:
        st.error("Mínimo 4 personas.")
    elif len(pool) > 16:
        st.warning("⚠️ Demasiados nadadores. Selecciona hasta 16 para evitar que la página se congele.")
    else:
        legs_opt = [("E2", "Espalda"), ("E1", "Mariposa"), ("E3", "Pecho"), ("E4", "Crol")] if "Medley" in o_tipo else [("E4", "Crol")]*4
        pool_actual, propuestas = list(pool), []
        
        # Limitador de iteraciones para proteger el servidor
        with st.spinner("Calculando combinaciones óptimas..."):
            while len(pool_actual) >= 4:
                combis = list(itertools.combinations(pool_actual, 4))
                validas = []
                
                # Solo analizamos una muestra de combinaciones si el pool es gigante
                for c in combis:
                    gs = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in c]
                    if (o_gen == "M" and all(g == "M" for g in gs)) or (o_gen == "F" and all(g == "F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2):
                        
                        mejor_t_int, mejor_ord_int = 999.0, None
                        # Solo permutamos si el equipo es válido para los estilos
                        for p in itertools.permutations(c):
                            t_p, skip = 0, False
                            for idx, (cod_e, _) in enumerate(legs_opt):
                                mv = obtener_mejor_marca(p[idx], cod_e)
                                if mv >= 900: skip = True; break
                                t_p += mv
                            if not skip and t_p < mejor_t_int:
                                mejor_t_int, mejor_ord_int = t_p, p
                        
                        if mejor_ord_int:
                            validas.append({'equipo': mejor_ord_int, 'tiempo': mejor_t_int})

                if not validas: break
                mejor_eq = min(validas, key=lambda x: x['tiempo'])
                se_e = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in mejor_eq['equipo']])
                cat_nom, cat_max = get_cat_info(se_e, o_reg)
                
                propuestas.append({'equipo': mejor_eq['equipo'], 'tiempo': mejor_eq['tiempo'], 'cat': cat_nom, 'suma': se_e, 'suma_max': cat_max,
                                   'parciales': [obtener_mejor_marca(mejor_eq['equipo'][idx], legs_opt[idx][0]) for idx in range(4)]})
                for n in mejor_eq['equipo']: pool_actual.remove(n)

        # Mostrar resultados (Benchmarks razonables)
        for i, p in enumerate(propuestas):
            with st.expander(f"Posta #{i+1}: {p['cat']} ({seg_a_tiempo(p['tiempo'])})"):
                st.write(f"**Integrantes:** {', '.join(p['equipo'])}")
                # Aquí iría el análisis de competitividad y salto de categoría previo
