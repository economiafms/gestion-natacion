import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Resultados - Natación", layout="centered") # Centered es mejor para mobile
st.title("📊 Visualización y Padrón")

# --- CSS PARA TARJETAS MOBILE (RESPONSIVE) ---
st.markdown("""
<style>
    .mobile-card {
        background-color: #262730;
        border: 1px solid #464855;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .card-top {
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;
    }
    .card-title { font-weight: bold; font-size: 16px; color: #fff; }
    .card-time { font-family: monospace; font-weight: bold; font-size: 18px; color: #4CAF50; }
    .card-meta { font-size: 12px; color: #b0b0b0; }
    .medal-icon { font-size: 18px; margin-right: 5px; }
    .relay-list { font-size: 12px; margin-top: 8px; border-top: 1px solid #444; padding-top: 5px; color: #ddd; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def refrescar_datos():
    st.cache_data.clear()
    st.rerun()

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_visualizacion():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "categorias": conn.read(worksheet="Categorias"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

data = cargar_visualizacion()
if not data: st.stop()

# --- 3. LÓGICA DE NEGOCIO (INTACTA) ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
dict_id_nac = pd.to_datetime(df_nad.set_index('codnadador')['fechanac']).to_dict()

def asignar_cat(edad):
    for _, r in data['categorias'].iterrows():
        if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
    return "-"

def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return 99999.0
        partes = t_str.replace('.', ':').split(':')
        mins = float(partes[0])
        segs = float(partes[1])
        cents = float(partes[2]) / 100 if len(partes) > 2 else 0
        return mins * 60 + segs + cents
    except: return 99999.0

# --- 4. ESTRUCTURA DE PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha", "🏊‍♂️ Relevos"])

# --- TAB 1: PADRÓN GENERAL Y MEDALLERO ---
with tab1:
    st.markdown("### 🏆 Medallero del Club")
    
    # LÓGICA ORIGINAL DE MEDALLERO (MANTENIDA)
    df_tiempos_nob = data['tiempos'].copy()
    df_relevos_nob = data['relevos'].copy()
    
    # Conteo Individual
    med_ind = df_tiempos_nob.groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    # Conteo Relevos
    relevistas = []
    for i in range(1, 5):
        relevistas.append(df_relevos_nob[['nadador_' + str(i), 'posicion']].rename(columns={'nadador_' + str(i): 'codnadador'}))
    df_rel_all = pd.concat(relevistas)
    med_rel = df_rel_all.groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    
    # Unir
    medallero_total = med_ind.add(med_rel, fill_value=0)
    for pos in [1, 2, 3]:
        if pos not in medallero_total.columns: medallero_total[pos] = 0

    # KPIs Totales
    total_oros = int(medallero_total[1].sum())
    total_platas = int(medallero_total[2].sum())
    total_bronces = int(medallero_total[3].sum())
    
    # Visualización Responsive de KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("🥇 Oro", total_oros)
    c2.metric("🥈 Plata", total_platas)
    c3.metric("🥉 Bronce", total_bronces)
    
    st.divider()

    # Padrón con Medallas
    df_p = df_nad.copy()
    df_p['fechanac'] = pd.to_datetime(df_p['fechanac'])
    anio_actual = datetime.now().year
    df_p['Edad'] = anio_actual - df_p['fechanac'].dt.year
    df_p['Categoría'] = df_p['Edad'].apply(asignar_cat)
    
    df_p = df_p.merge(medallero_total[[1, 2, 3]], left_on='codnadador', right_index=True, how='left').fillna(0)
    df_p['Total Podios'] = df_p[1] + df_p[2] + df_p[3]
    
    # ADAPTACIÓN MOBILE: Buscador en lugar de tabla gigante
    st.write("#### Lista de Nadadores")
    filtro_padron = st.text_input("Buscar por nombre:", placeholder="Ej: Perez...")
    
    df_show = df_p.sort_values(['Total Podios', 1], ascending=False)
    if filtro_padron:
        df_show = df_show[df_show['Nombre Completo'].str.contains(filtro_padron.upper())]

    # Renderizado como Tarjetas Compactas
    for _, row in df_show.head(20).iterrows(): # Limitamos a 20 para no saturar celular
        st.markdown(f"""
        <div class="mobile-card" style="padding: 10px;">
            <div style="display:flex; justify-content:space-between;">
                <b>{row['Nombre Completo']}</b>
                <span style="color:#FFD700;">★ {int(row['Total Podios'])}</span>
            </div>
            <div style="font-size:12px; color:#aaa;">
                {int(row['Edad'])} años • Cat: {row['Categoría']} • 
                🥇{int(row[1])} 🥈{int(row[2])} 🥉{int(row[3])}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if len(df_show) > 20:
        st.caption(f"Y {len(df_show)-20} nadadores más. Usa el buscador.")


# --- TAB 2: FICHA DEL NADADOR ---
with tab2:
    df_t = data['tiempos'].copy()
    df_t = df_t.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
    df_t['Sede_Full'] = df_t['club'].astype(str) + " (" + df_t['medida'].astype(str) + ")"
    df_t = df_t.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
    
    f_nad = st.selectbox("Buscar Nadador:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        info_nadador = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_actual = info_nadador['codnadador']
        fecha_nac_dt = pd.to_datetime(info_nadador['fechanac'])
        edad_master_actual = anio_actual - fecha_nac_dt.year
        cat_actual = asignar_cat(edad_master_actual)

        # Encabezado (Responsive)
        st.markdown(f"### {info_nadador['nombre']} {info_nadador['apellido']}")
        c_dat1, c_dat2 = st.columns(2)
        c_dat1.write(f"**Edad:** {edad_master_actual} ({cat_actual})")
        c_dat2.write(f"**Género:** {info_nadador['codgenero']}")
        
        # LÓGICA DE MEDALLERO INDIVIDUAL (MANTENIDA)
        pos_ind = df_t[df_t['codnadador'] == id_actual]['posicion'].value_counts()
        df_r_base = data['relevos'].copy()
        cond_rel = (df_r_base['nadador_1'] == id_actual) | (df_r_base['nadador_2'] == id_actual) | \
                   (df_r_base['nadador_3'] == id_actual) | (df_r_base['nadador_4'] == id_actual)
        pos_rel = df_r_base[cond_rel]['posicion'].value_counts()
        oro = pos_ind.get(1,0)+pos_rel.get(1,0)
        plata = pos_ind.get(2,0)+pos_rel.get(2,0)
        bronce = pos_ind.get(3,0)+pos_rel.get(3,0)

        # Medallero Visual
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("🥇", int(oro)); k2.metric("🥈", int(plata)); k3.metric("🥉", int(bronce)); k4.metric("Σ", int(oro+plata+bronce))

        st.divider()

        # HISTORIAL (ADAPTACIÓN VISUAL)
        st.subheader("📜 Historial de Carreras")
        
        # Filtros colapsables para mobile
        with st.expander("Filtrar Resultados"):
            f1, f2 = st.columns(2)
            h_est_sel = f1.selectbox("Estilo", ["Todos"] + sorted(df_t['Estilo'].unique().tolist()))
            h_dis_sel = f2.selectbox("Distancia", ["Todos"] + sorted(df_t['Distancia'].unique().tolist()))

        # Filtrado
        mis_tiempos = df_t[df_t['codnadador'] == id_actual].copy()
        if h_est_sel != "Todos": mis_tiempos = mis_tiempos[mis_tiempos['Estilo'] == h_est_sel]
        if h_dis_sel != "Todos": mis_tiempos = mis_tiempos[mis_tiempos['Distancia'] == h_dis_sel]
        
        mis_tiempos = mis_tiempos.sort_values('fecha', ascending=False)

        # RENDERIZADO DE TARJETAS (Reemplaza al dataframe)
        if mis_tiempos.empty:
            st.info("No se encontraron resultados.")
        else:
            for _, row in mis_tiempos.iterrows():
                medalla = "🥇" if row['posicion'] == 1 else ("🥈" if row['posicion'] == 2 else ("🥉" if row['posicion'] == 3 else f"#{row['posicion']}"))
                st.markdown(f"""
                <div class="mobile-card">
                    <div class="card-top">
                        <div class="card-title">{row['Distancia']} {row['Estilo']}</div>
                        <div class="card-time">{row['tiempo']}</div>
                    </div>
                    <div class="card-meta">
                        📅 {row['fecha']} • {row['Sede_Full']} • <span style="color:orange">{medalla}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# --- TAB 3: TODOS LOS RELEVOS ---
with tab3:
    st.markdown("### 🏊‍♂️ Historial de Relevos")
    mr = data['relevos'].copy()
    if not mr.empty:
        # LÓGICA DE UNIÓN Y CÁLCULO (MANTENIDA)
        mr = mr.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
        mr['Sede_Full'] = mr['club'].astype(str) + " (" + mr['medida'].astype(str) + ")"
        mr = mr.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        
        # Filtros Mobile
        with st.expander("Filtros"):
            c1, c2 = st.columns(2)
            gr_est = c1.selectbox("Estilo:", ["Todos"] + sorted(mr['Estilo'].unique().tolist()))
            gr_gen = c2.selectbox("Género:", ["Todos"] + sorted(mr['codgenero'].unique().tolist()))

        mr_g = mr.copy()
        if gr_est != "Todos": mr_g = mr_g[mr_g['Estilo'] == gr_est]
        if gr_gen != "Todos": mr_g = mr_g[mr_g['codgenero'] == gr_gen]

        mr_g = mr_g.sort_values('fecha', ascending=False)

        # RENDERIZADO DE TARJETAS DE EQUIPO (Reemplaza al dataframe)
        for _, row in mr_g.head(30).iterrows(): # Top 30 para velocidad
            # Calcular edades en tiempo real
            suma_edades = 0
            nombres_html = ""
            for i in range(1, 5):
                n_id = row[f'nadador_{i}']
                n_nom = dict_id_nombre.get(n_id, "Desconocido")
                
                # Cálculo de edad para la categoría
                if n_id in dict_id_nac:
                    nac = pd.to_datetime(dict_id_nac[n_id])
                    suma_edades += (anio_actual - nac.year)
                
                t_parcial = row[f'tiempo_{i}'] if row[f'tiempo_{i}'] else "--"
                nombres_html += f"<div>{i}. {n_nom} <span style='color:#aaa;'>({t_parcial})</span></div>"

            cat_posta = asignar_cat(suma_edades)
            medalla = "🥇" if row['posicion'] == 1 else ("🥈" if row['posicion'] == 2 else ("🥉" if row['posicion'] == 3 else ""))

            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #1E88E5;">
                <div class="card-top">
                    <div class="card-title">{row['Distancia']} {row['Estilo']} ({row['codgenero']})</div>
                    <div class="card-time">{row['tiempo_final']}</div>
                </div>
                <div class="card-meta">
                    {medalla} Pos: {row['posicion']} • Cat: {cat_posta} (Suma {int(suma_edades)})<br>
                    📅 {row['fecha']} • {row['Sede_Full']}
                </div>
                <div class="relay-list">
                    {nombres_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
