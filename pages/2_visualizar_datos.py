import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Resultados", layout="centered")
st.title("📊 Base de Datos y Estadísticas")

# --- CSS PERSONALIZADO (Grande y Horizontal) ---
st.markdown("""
<style>
    /* Estilo para filas de resultados horizontales */
    .result-row {
        background-color: #262730;
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 5px solid #1E88E5;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .result-info {
        font-size: 15px;
        font-weight: 500;
        color: #fff;
    }
    .result-meta {
        font-size: 12px;
        color: #aaa;
    }
    .result-time {
        font-family: 'Courier New', monospace;
        font-size: 18px;
        font-weight: bold;
        color: #4CAF50;
        text-align: right;
    }
    /* Estilo para tarjetas de padrón grandes */
    .swimmer-card {
        padding: 15px;
        border: 1px solid #444;
        border-radius: 10px;
        margin-bottom: 12px;
        background-color: #1e1e1e;
    }
    .big-name {
        font-size: 18px;
        font-weight: bold;
        color: #ffffff;
    }
    .medal-box {
        background-color: #333;
        padding: 4px 8px;
        border-radius: 5px;
        font-size: 14px;
        margin-left: 5px;
    }
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
        }
    except Exception as e:
        return None

data = cargar_visualizacion()
if not data: 
    st.error("Conectando con base de datos...")
    st.stop()

# --- 3. PROCESAMIENTO ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
dict_id_nac = pd.to_datetime(df_nad.set_index('codnadador')['fechanac']).to_dict()

def asignar_cat(edad):
    try:
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return 999.0
        p = t_str.replace('.', ':').split(':')
        return float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
    except: return 999.0

# --- 4. PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])

# ==========================================
# TAB 1: PADRÓN GENERAL (Grande y con Totales)
# ==========================================
with tab1:
    # 1. CÁLCULO DE MEDALLERO TOTAL (Recuperado)
    df_t_c = data['tiempos'].copy()
    df_t_c['posicion'] = pd.to_numeric(df_t_c['posicion'], errors='coerce').fillna(0)
    
    df_r_c = data['relevos'].copy()
    df_r_c['posicion'] = pd.to_numeric(df_r_c['posicion'], errors='coerce').fillna(0)
    
    # Medallas individuales
    m_ind = df_t_c[df_t_c['posicion'].isin([1,2,3])].groupby('posicion').size()
    # Medallas relevos (cuentan x1 para el club)
    m_rel = df_r_c[df_r_c['posicion'].isin([1,2,3])].groupby('posicion').size()
    
    t_oro = m_ind.get(1,0) + m_rel.get(1,0)
    t_plata = m_ind.get(2,0) + m_rel.get(2,0)
    t_bronce = m_ind.get(3,0) + m_rel.get(3,0)
    
    # KPIs Grandes
    st.markdown("### 🏆 Medallero Histórico del Club")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🥇 Oros", int(t_oro))
    k2.metric("🥈 Platas", int(t_plata))
    k3.metric("🥉 Bronces", int(t_bronce))
    k4.metric("📊 Total", int(t_oro + t_plata + t_bronce))
    
    st.divider()
    
    # 2. LISTA DE NADADORES (Diseño Grande)
    filtro = st.text_input("🔍 Buscar en Padrón:", placeholder="Apellido...")
    
    # Preparar datos por nadador
    df_p = df_nad.copy()
    
    # Calcular medallas por nadador para mostrar en la tarjeta
    # (Lógica simplificada para velocidad de visualización)
    med_ind_nad = df_t_c[df_t_c['posicion'].isin([1,2,3])].groupby('codnadador').size()
    df_p['Podios'] = df_p['codnadador'].map(med_ind_nad).fillna(0).astype(int)
    
    if filtro:
        df_p = df_p[df_p['Nombre Completo'].str.contains(filtro.upper())]
    
    df_p = df_p.sort_values('Podios', ascending=False)
    
    for _, row in df_p.head(15).iterrows():
        # Cálculo edad
        try: edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        
        # Tarjeta Grande
        st.markdown(f"""
        <div class="swimmer-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div class="big-name">{row['Nombre Completo']}</div>
                    <div style="color:#bbb; font-size:14px;">{edad} años ({cat}) • {row['codgenero']}</div>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:24px; color:#FFD700;">★ {row['Podios']}</span><br>
                    <span style="font-size:10px; color:#888;">PODIOS INDIV.</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 2: FICHA TÉCNICA (Funcionalidad Recuperada)
# ==========================================
with tab2:
    f_nad = st.selectbox("Seleccionar Atleta:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        info = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_n = info['codnadador']
        
        # Unir tablas para tener info completa
        df_full = data['tiempos'].copy()
        df_full = df_full.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        df_full = df_full.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        
        mis_t = df_full[df_full['codnadador'] == id_n].copy()
        
        # 1. MEJORES MARCAS (PB) - Recuperado
        if not mis_t.empty:
            st.subheader("✨ Mejores Marcas (PB)")
            mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)
            # Agrupar por estilo y distancia, tomar el menor tiempo
            pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].sort_values('Distancia')
            
            # Mostrar como tarjetas horizontales compactas
            estilos_unicos = pbs['Estilo'].unique()
            # Usamos pestañas internas para ordenar los PBs si son muchos, o columnas
            cols = st.columns(len(estilos_unicos)) if len(estilos_unicos) <= 4 else [st.container()]
            
            idx_col = 0
            for est in estilos_unicos:
                df_e = pbs[pbs['Estilo'] == est]
                with (cols[idx_col] if len(estilos_unicos) <= 4 else st.container()):
                    st.markdown(f"**{est}**")
                    for _, r in df_e.iterrows():
                         st.markdown(f"""
                         <div style="background:#333; padding:5px 10px; border-radius:5px; margin-bottom:5px; display:flex; justify-content:space-between;">
                            <span>{r['Distancia']}</span>
                            <span style="color:#4CAF50; font-weight:bold;">{r['tiempo']}</span>
                         </div>
                         """, unsafe_allow_html=True)
                idx_col += 1

            st.divider()

            # 2. GRÁFICO DE EVOLUCIÓN - Recuperado
            st.subheader("📈 Progresión")
            g_est = st.selectbox("Estilo para Graficar:", mis_t['Estilo'].unique())
            g_df = mis_t[mis_t['Estilo'] == g_est].sort_values('fecha')
            
            if not g_df.empty:
                fig = px.line(g_df, x='fecha', y='segundos', color='Distancia', markers=True, 
                              title=f"Evolución en {g_est}", template="plotly_dark")
                # Truco para que el eje Y muestre tiempo aprox (es difícil formatear exacto en Plotly sin helpers complejos, pero esto visualiza la tendencia)
                fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

            st.divider()

        # 3. LISTA DE CARRERAS (Diseño Horizontal)
        st.subheader("📜 Historial Completo")
        
        mis_t = mis_t.sort_values('fecha', ascending=False)
        
        for _, r in mis_t.head(30).iterrows(): # Top 30
            medalla = ""
            if r['posicion'] == 1: medalla = "🥇"
            elif r['posicion'] == 2: medalla = "🥈"
            elif r['posicion'] == 3: medalla = "🥉"
            
            # Diseño Horizontal con CSS
            st.markdown(f"""
            <div class="result-row">
                <div class="result-info">
                    {r['Distancia']} {r['Estilo']}
                    <div class="result-meta">📅 {r['fecha']} • {r['club']}</div>
                </div>
                <div style="text-align:right;">
                    <div class="result-time">{r['tiempo']}</div>
                    <div style="font-size:12px;">{medalla} Pos: {r['posicion']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# TAB 3: RELEVOS (Horizontal y Eficiente)
# ==========================================
with tab3:
    st.subheader("🏊‍♂️ Historial de Postas")
    
    mr = data['relevos'].copy()
    if not mr.empty:
        mr = mr.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mr = mr.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        
        # Filtros
        c1, c2 = st.columns(2)
        f_est_r = c1.selectbox("Estilo Posta", ["Todos"] + sorted(mr['Estilo'].unique().tolist()))
        f_gen_r = c2.selectbox("Género", ["Todos", "M", "F", "X"])
        
        if f_est_r != "Todos": mr = mr[mr['Estilo'] == f_est_r]
        if f_gen_r != "Todos": mr = mr[mr['codgenero'] == f_gen_r]
        
        mr = mr.sort_values('fecha', ascending=False)
        
        for _, r in mr.head(20).iterrows():
            # Crear string de integrantes
            integrantes = []
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0] # Solo apellido
                t = r[f'tiempo_{k}'] if r[f'tiempo_{k}'] else ""
                integrantes.append(f"{nom} ({t})")
            
            str_integrantes = " | ".join(integrantes)
            
            # Tarjeta Horizontal Relevo
            st.markdown(f"""
            <div class="result-row" style="border-left: 5px solid #E91E63; display:block;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                    <div class="result-info">
                        {r['Distancia']} {r['Estilo']} ({r['codgenero']})
                    </div>
                    <div class="result-time">{r['tiempo_final']}</div>
                </div>
                <div class="result-meta" style="margin-bottom:5px;">
                   📅 {r['fecha']} • {r['club']} • Pos: {r['posicion']}
                </div>
                <div style="font-size:11px; color:#ccc; border-top:1px solid #444; padding-top:4px;">
                    🏊‍♂️ {str_integrantes}
                </div>
            </div>
            """, unsafe_allow_html=True)
