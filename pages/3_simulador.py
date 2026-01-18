import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import itertools

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Técnico - NOB", layout="wide")
st.markdown("<h1 style='text-align: center; color: red;'>🔴⚫ SIMULADOR DE RELEVOS TÉCNICO</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Validación por Estilo Individual y Tiempos Reales</h4>", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
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
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

# Mapeo de IDs de Estilos (E1: Mariposa, E2: Espalda, E3: Pecho, E4: Crol)
MAP_ESTILOS = {"Mariposa": "E1", "Espalda": "E2", "Pecho": "E3", "Crol": "E4"}
ID_50M = "D1"

# --- 3. FUNCIONES DE APOYO ---
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 0.0

def seg_a_tiempo(seg):
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}.{int((seg % 1) * 100):02d}"

def obtener_nadadores_aptos(id_estilo, genero="X"):
    """Filtra nadadores que tienen marca real en el estilo y distancia (50m) requerida."""
    tiempos_filt = data['tiempos'][(data['tiempos']['codestilo'] == id_estilo) & (data['tiempos']['coddistancia'] == ID_50M)]
    ids_validos = tiempos_filt['codnadador'].unique()
    nadadores = df_nad[df_nad['codnadador'].isin(ids_validos)]
    if genero != "X":
        nadadores = nadadores[nadadores['codgenero'] == genero]
    return sorted(nadadores['Nombre Completo'].tolist())

def obtener_mejor_marca(nombre_completo, id_estilo):
    """Obtiene el mejor tiempo real de 50m de un nadador para un estilo específico."""
    idn = df_nad[df_nad['Nombre Completo'] == nombre_completo]['codnadador'].iloc[0]
    marcas = data['tiempos'][(data['tiempos']['codnadador'] == idn) & 
                            (data['tiempos']['codestilo'] == id_estilo) & 
                            (data['tiempos']['coddistancia'] == ID_50M)]
    return marcas['tiempo'].apply(tiempo_a_seg).min()

def calcular_categoria(suma, reg):
    regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
    for _, r in regs.iterrows():
        if r['suma_min'] <= suma <= r['suma_max']: return r['descripcion']
    return f"Suma {int(suma)}"

# --- 4. SIMULADOR MANUAL ---
st.divider()
st.subheader("🧪 Configuración de Posta Manual")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    s_reg = c1.selectbox("Reglamento", data['cat_relevos']['tipo_reglamento'].unique())
    s_tipo_rel = c2.selectbox("Tipo de Relevo", ["Libre (Crol)", "Combinado (Medley)"])
    s_gen = c3.selectbox("Género", ["M", "F", "X"])

    # Definir estilos por posición
    if s_tipo_rel == "Combinado (Medley)":
        # Orden solicitado: Espalda - Mariposa - Pecho - Crol
        legs = [("Espalda", "E2"), ("Mariposa", "E1"), ("Pecho", "E3"), ("Crol", "E4")]
    else:
        legs = [("Crol", "E4")] * 4

    n_sel = []
    cols = st.columns(4)
    for i, (nombre_estilo, cod_estilo) in enumerate(legs):
        aptos = obtener_nadadores_aptos(cod_estilo, s_gen)
        n_sel.append(cols[i].selectbox(f"Pos {i+1}: {nombre_estilo}", aptos, index=None, key=f"pos{i}"))

    if st.button("🚀 Simular Tiempo con Marcas de Tabla", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # Validación Género Mixto
            generos = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in n_sel]
            if s_gen == "X" and generos.count("M") != 2:
                st.error("Error: El relevo mixto debe tener exactamente 2 hombres y 2 mujeres.")
            else:
                total_seg = 0
                st.write("### ⏱️ Desglose de Marcas Individuales (50m)")
                res_cols = st.columns(4)
                for i, (nombre_estilo, cod_estilo) in enumerate(legs):
                    t = obtener_mejor_marca(n_sel[i], cod_estilo)
                    total_seg += t
                    res_cols[i].metric(f"{n_sel[i].split(',')[1]} ({nombre_estilo})", seg_a_tiempo(t))
                
                suma_e = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in n_sel])
                st.success(f"**Categoría Proyectada: {calcular_categoria(suma_e, s_reg)} | Tiempo Final Simulado: {seg_a_tiempo(total_seg)}**")
                
                # Búsqueda de antecedente exacto
                ids_busqueda = sorted([df_nad[df_nad['Nombre Completo'] == n]['codnadador'].iloc[0] for n in n_sel])
                def check_eq(row): return sorted([row['nadador_1'], row['nadador_2'], row['nadador_3'], row['nadador_4']]) == ids_busqueda
                hist = data['relevos'][data['relevos'].apply(check_eq, axis=1)]
                if not hist.empty:
                    ant = hist.sort_values('tiempo_final').iloc[0]
                    st.info(f"📋 Antecedente en tabla: {ant['tiempo_final']} (Fecha: {ant['fecha']})")
        else:
            st.error("Seleccione 4 nadadores únicos que tengan marcas en los estilos requeridos.")

# --- 5. OPTIMIZADOR ESTRATÉGICO ---
st.divider()
st.subheader("🎯 Optimizador Estratégico de Postas")
st.caption("Arma las mejores combinaciones posibles con los nadadores disponibles sin repetir atletas.")

pool = st.multiselect("Pool de nadadores disponibles:", lista_nombres)
g1, g2, g3 = st.columns(3)
o_reg = g1.selectbox("Reglamento Torneo", data['cat_relevos']['tipo_reglamento'].unique(), key="o1")
o_tipo = g2.selectbox("Estilo del Relevo", ["Libre (Crol)", "Combinado (Medley)"], key="o2")
o_gen = g3.selectbox("Género Relevo", ["M", "F", "X"], key="o3")

if st.button("🪄 Generar Mejores Postas Posibles"):
    if len(pool) < 4:
        st.error("Faltan nadadores para formar una posta.")
    else:
        # Definir piernas del optimizador
        legs_opt = [("E2", "Espalda"), ("E1", "Mariposa"), ("E3", "Pecho"), ("E4", "Crol")] if o_tipo == "Combinado (Medley)" else [("E4", "Crol")]*4
        
        pool_actual = list(pool)
        propuestas = []
        
        while len(pool_actual) >= 4:
            combis = list(itertools.combinations(pool_actual, 4))
            validas = []
            for c in combis:
                gs = [df_nad[df_nad['Nombre Completo'] == n]['codgenero'].iloc[0] for n in c]
                if (o_gen == "M" and all(g == "M" for g in gs)) or (o_gen == "F" and all(g == "F" for g in gs)) or (o_gen == "X" and gs.count("M") == 2):
                    # Encontrar el mejor orden interno para este grupo de 4
                    mejor_t_int = 9999.0
                    mejor_ord_int = None
                    for p in itertools.permutations(c):
                        t_p = 0
                        posible = True
                        for idx, (cod_e, _) in enumerate(legs_opt):
                            try:
                                t_p += obtener_mejor_marca(p[idx], cod_e)
                            except: posible = False; break
                        if posible and t_p < mejor_t_int:
                            mejor_t_int = t_p
                            mejor_ord_int = p
                    if mejor_ord_int:
                        validas.append({'equipo': mejor_ord_int, 'tiempo': mejor_t_int})
            
            if not validas: break
            mejor_global = min(validas, key=lambda x: x['tiempo'])
            se = sum([(2026 - pd.to_datetime(df_nad[df_nad['Nombre Completo'] == n]['fechanac'].iloc[0]).year) for n in mejor_global['equipo']])
            propuestas.append({'equipo': mejor_global['equipo'], 'tiempo': mejor_global['tiempo'], 'cat': calcular_categoria(se, o_reg)})
            for n in mejor_global['equipo']: pool_actual.remove(n)

        for i, p in enumerate(propuestas):
            with st.expander(f"Posta #{i+1}: {p['cat']}", expanded=True):
                st.write(f"**Orden Sugerido:** {', '.join(p['equipo'])}")
                st.metric("Tiempo Proyectado", seg_a_tiempo(p['tiempo']))
