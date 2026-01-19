import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Base de Datos", layout="centered", initial_sidebar_state="collapsed")
st.title("🗃️ Base de Datos")

# --- CSS RESPONSIVE (Tarjetas) ---
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
    .card-header {
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;
    }
    .card-title { font-weight: bold; font-size: 16px; color: #fff; }
    .card-time { font-family: monospace; font-weight: bold; font-size: 18px; color: #4CAF50; }
    .card-sub { font-size: 12px; color: #b0b0b0; }
    .tag { background-color: #1E3A8A; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 5px; }
    .medal-count { font-size: 13px; color: #FFD700; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

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
        st.error(f"Error de conexión: {e}")
        return None

data = cargar_visualizacion()
if not data: st.stop()

# --- 3. PROCESAMIENTO GLOBAL ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
dict_id_nac = pd.to_datetime(df_nad.set_index('codnadador')['fechanac']).to_dict()

# Función de categoría robusta
def asignar_cat(edad):
    try:
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

# --- 4. PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha", "🏊‍♂️ Relevos"])

# ==========================================
# TAB 1: PADRÓN GENERAL (CORREGIDO)
# ==========================================
with tab1:
    st.markdown("### 🏆 Medallero del Club")
    
    # 1. Limpieza de datos (Evitar ValueError)
    df_t_clean = data['tiempos'].copy()
    df_t_clean['posicion'] = pd.to_numeric(df_t_clean['posicion'], errors='coerce').fillna(0).astype(int)
    
    df_r_clean = data['relevos'].copy()
    df_r_clean['posicion'] = pd.to_numeric(df_r_clean['posicion'], errors='coerce').fillna(0).astype(int)
    
    # 2. Cálculo Medallero
    med_ind = df_t_clean[df_t_clean['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    
    # Relevos
    relevistas = []
    for i in range(1, 5):
        relevistas.append(df_r_clean[['nadador_' + str(i), 'posicion']].rename(columns={'nadador_' + str(i): 'codnadador'}))
    df_rel_all = pd.concat(relevistas)
    med_rel = df_rel_all[df_rel_all['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
    
    # Suma Total
    medallero = med_ind.add(med_rel, fill_value=0)
    
    # Asegurar columnas 1, 2, 3 (Oro, Plata, Bronce)
    for p in [1, 2, 3]:
        if p not in medallero.columns: medallero[p] = 0
    
    # 3. KPIs Totales
    oros = int(medallero[1].sum())
    platas = int(medallero[2].sum())
    bronces = int(medallero[3].sum())
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🥇 Oro", oros)
    c2.metric("🥈 Plata", platas)
    c3.metric("🥉 Bronce", bronces)
    
    st.divider()
    
    # 4. Lista de Nadadores
    filtro = st.text_input("Buscar Nadador:", placeholder="Nombre...")
    
    # Unimos medallero al padrón
    df_view = df_nad.merge(medallero, left_on='codnadador', right_index=True, how='left').fillna(0)
    df_view['Total'] = df_view[1] + df_view[2] + df_view[3]
    
    # Filtro
    if filtro:
        df_view = df_view[df_view['Nombre Completo'].str.contains(filtro.upper())]
    
    df_view = df_view.sort_values('Total', ascending=False)

    # 5. Renderizado Seguro (Aquí estaba el error)
    for _, row in df_view.head(20).iterrows():
        # Cálculo seguro de edad
        try:
            edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        
        # Tarjeta Mobile
        st.markdown(f"""
        <div class="mobile-card" style="padding: 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:bold; font-size:15px; color:white;">{row['Nombre Completo']}</span>
                <span class="medal-count">★ {int(row['Total'])}</span>
            </div>
            <div style="font-size:12px; color:#aaa; margin-top:4px;">
                {edad} años ({cat}) • 
                <span style="color:#FFD700;">🥇{int(row[1])}</span> 
                <span style="color:#C0C0C0;">🥈{int(row[2])}</span> 
                <span style="color:#CD7F32;">🥉{int(row[3])}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    if len(df_view) > 20:
        st.caption("Mostrando primeros 20. Usa el buscador para ver más.")

# ==========================================
# TAB 2: FICHA DEL NADADOR
# ==========================================
with tab2:
    f_nad = st.selectbox("Seleccionar Atleta:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        # Datos personales
        info = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_n = info['codnadador']
        
        # Cálculo edad
        try:
            nac = pd.to_datetime(info['fechanac'])
            edad = datetime.now().year - nac.year
            cat = asignar_cat(edad)
        except: edad, cat = 0, "-"

        st.markdown(f"""
        <div style="background: #1E3A8A; padding: 15px; border-radius: 10px; color: white; margin-bottom: 15px;">
            <h3 style="margin:0; font-size:18px;">{info['nombre']} {info['apellido']}</h3>
            <div style="font-size:13px; opacity:0.8;">
                Categoría: {cat} ({edad} años) • Género: {info['codgenero']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Historial
        df_t_full = data['tiempos'].copy()
        # Enriquecer datos
        df_t_full = df_t_full.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mis_t = df_t_full[df_t_full['codnadador'] == id_n].sort_values('fecha', ascending=False)
        
        if mis_t.empty:
            st.info("No hay tiempos registrados.")
        else:
            # Filtros colapsables
            with st.expander("Filtrar Historial"):
                c1, c2 = st.columns(2)
                f_est = c1.selectbox("Estilo", ["Todos"] + sorted(mis_t['descripcion_x'].unique().tolist()))
                f_dis = c2.selectbox("Distancia", ["Todos"] + sorted(mis_t['descripcion_y'].unique().tolist()))

            if f_est != "Todos": mis_t = mis_t[mis_t['descripcion_x'] == f_est]
            if f_dis != "Todos": mis_t = mis_t[mis_t['descripcion_y'] == f_dis]

            for _, r in mis_t.iterrows():
                medalla = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else ""))
                
                st.markdown(f"""
                <div class="mobile-card">
                    <div class="card-header">
                        <div class="card-title">{r['descripcion_y']} {r['descripcion_x']}</div>
                        <div class="card-time">{r['tiempo']}</div>
                    </div>
                    <div class="card-sub">
                        📅 {r['fecha']} • {r['club']} ({r['medida']}) {medalla}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 3: RELEVOS
# ==========================================
with tab3:
    st.write("#### Historial de Postas")
    
    mr = data['relevos'].copy()
    if not mr.empty:
        mr = mr.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        
        with st.expander("Filtrar Relevos"):
            c1, c2 = st.columns(2)
            fil_est = c1.selectbox("Estilo Posta", ["Todos"] + sorted(mr['descripcion_x'].unique().tolist()))
            fil_gen = c2.selectbox("Género", ["Todos", "M", "F", "X"])

        if fil_est != "Todos": mr = mr[mr['descripcion_x'] == fil_est]
        if fil_gen != "Todos": mr = mr[mr['codgenero'] == fil_gen]
        
        mr = mr.sort_values('fecha', ascending=False)
        
        for _, r in mr.head(30).iterrows():
            # Integrantes
            integrantes_html = ""
            suma = 0
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nname = dict_id_nombre.get(nid, "Desconocido").split(',')[0]
                tpar = r[f'tiempo_{k}'] if r[f'tiempo_{k}'] else "--"
                
                # Edad
                if nid in dict_id_nac:
                    ed = datetime.now().year - dict_id_nac[nid].year
                    suma += ed
                
                integrantes_html += f"<div>{k}. {nname} <span style='color:#888;'>({tpar})</span></div>"
            
            medal = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else ""))
            
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                <div class="card-header">
                    <div class="card-title">{r['descripcion_y']} {r['descripcion_x']} ({r['codgenero']})</div>
                    <div class="card-time">{r['tiempo_final']}</div>
                </div>
                <div class="card-sub" style="margin-bottom: 8px;">
                    {medal} Pos: {r['posicion']} • Suma Edades: {suma}
                </div>
                <div style="font-size:12px; color:#ccc; border-top:1px solid #444; padding-top:5px;">
                    {integrantes_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
