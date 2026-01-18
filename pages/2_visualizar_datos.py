import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Resultados - Natación", layout="wide")
st.title("📊 Visualización de Resultados y Padrón")

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

# --- 3. DICCIONARIOS Y PROCESAMIENTO ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str) + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
dict_id_nac = pd.to_datetime(df_nad.set_index('codnadador')['fechanac']).to_dict()

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
tab1, tab2, tab3 = st.tabs(["👥 Padrón General", "👤 Ficha del Nadador", "🏊‍♂️ Todos los Relevos"])

# --- TAB 1: PADRÓN ---
with tab1:
    st.subheader("Listado de Nadadores")
    df_p = df_nad.copy()
    df_p['fechanac'] = pd.to_datetime(df_p['fechanac'])
    anio_actual = 2026 
    df_p['Edad'] = anio_actual - df_p['fechanac'].dt.year
    
    def asignar_cat(edad):
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    
    df_p['Categoría'] = df_p['Edad'].apply(asignar_cat)
    st.dataframe(df_p[['Nombre Completo', 'Edad', 'Categoría', 'codgenero']].sort_values('Nombre Completo'), use_container_width=True, hide_index=True)

# --- TAB 2: FICHA DEL NADADOR ---
with tab2:
    # Preparación de datos de tiempos
    df_t = data['tiempos'].copy()
    df_t = df_t.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
    df_t['Sede_Full'] = df_t['club'].astype(str) + " (" + df_t['medida'].astype(str) + ")"
    df_t = df_t.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
    
    # Selectbox principal con Key Única
    f_nad = st.selectbox("Seleccione un Nadador:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None, key="key_main_search_nad")
    
    if f_nad:
        # 1. Info Personal Ordenada
        info_nadador = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_actual = info_nadador['codnadador']
        fecha_nac_dt = pd.to_datetime(info_nadador['fechanac'])
        edad_master = anio_actual - fecha_nac_dt.year
        cat_actual = asignar_cat(edad_master)

        st.header(f"👤 {info_nadador['apellido'].upper()}, {info_nadador['nombre']}")
        
        c_i1, c_i2, c_i3, c_i4 = st.columns(4)
        c_i1.metric("Nacimiento", fecha_nac_dt.strftime('%d/%m/%Y'))
        c_i2.metric("Edad (al 31/12)", f"{edad_master} años")
        c_i3.metric("Categoría", cat_actual)
        c_i4.metric("Género", info_nadador['codgenero'])
        
        st.divider()

        # 2. Medallero
        pos_ind = df_t[df_t['codnadador'] == id_actual]['posicion'].value_counts()
        df_r_base = data['relevos'].copy()
        cond_rel = (df_r_base['nadador_1'] == id_actual) | (df_r_base['nadador_2'] == id_actual) | \
                   (df_r_base['nadador_3'] == id_actual) | (df_r_base['nadador_4'] == id_actual)
        pos_rel = df_r_base[cond_rel]['posicion'].value_counts()
        oro, plata, bronce = pos_ind.get(1,0)+pos_rel.get(1,0), pos_ind.get(2,0)+pos_rel.get(2,0), pos_ind.get(3,0)+pos_rel.get(3,0)
        
        cm1, cm2, cm3, cm4 = st.columns(4)
        cm1.metric("🥇 Oros", int(oro))
        cm2.metric("🥈 Platas", int(plata))
        cm3.metric("🥉 Bronces", int(bronce))
        cm4.metric("📊 Total", int(oro+plata+bronce))

        st.divider()

        # 3. Mejores Marcas (Tarjetas)
        st.subheader("✨ Mejores Marcas Personales")
        mis_tiempos = df_t[df_t['codnadador'] == id_actual].copy()
        if not mis_tiempos.empty:
            mis_tiempos['segundos'] = mis_tiempos['tiempo'].apply(tiempo_a_segundos)
            idx_pb = mis_tiempos.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()
            df_pb = mis_tiempos.loc[idx_pb].sort_values('metros_totales')
            est_disp = [e for e in ['Mariposa', 'Espalda', 'Pecho', 'Crol', 'Combinado'] if e in df_pb['Estilo'].unique()]
            cols_est = st.columns(len(est_disp))
            for i, estilo in enumerate(est_disp):
                with cols_est[i]:
                    st.write(f"**{estilo}**")
                    df_e = df_pb[df_pb['Estilo'] == estilo]
                    for _, row in df_e.iterrows():
                        st.caption(f"{row['Distancia']}")
                        st.code(row['tiempo'], language=None)
        
        st.divider()

        # 4. Historial y Gráfico de Progresión
        st.subheader("📜 Historial y Evolución")
        f1, f2 = st.columns(2)
        h_est_sel = f1.selectbox("Estilo:", ["Todos"] + sorted(mis_tiempos['Estilo'].unique().tolist()), key="key_hist_est")
        
        df_tmp = mis_tiempos.copy()
        if h_est_sel != "Todos":
            df_tmp = df_tmp[df_tmp['Estilo'] == h_est_sel]
        
        h_dis_sel = f2.selectbox("Distancia:", ["Todos"] + sorted(df_tmp['Distancia'].unique().tolist()), key="key_hist_dist")
        
        df_final = df_tmp.copy()
        if h_dis_sel != "Todos":
            df_final = df_final[df_final['Distancia'] == h_dis_sel]

        # Gráfico dinámico
        if h_est_sel != "Todos" and h_dis_sel != "Todos" and len(df_final) > 0:
            df_g = df_final.copy()
            df_g['fecha'] = pd.to_datetime(df_g['fecha'])
            df_g = df_g.sort_values('fecha')
            fig = px.line(df_g, x='fecha', y='segundos', markers=True, 
                          title=f"Progreso: {h_dis_sel} {h_est_sel}",
                          hover_data={'segundos': False, 'tiempo': True, 'fecha': '|%d/%m/%Y', 'Sede_Full': True})
            fig.update_yaxes(autorange="reversed", title="Tiempo (seg)")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_final[['fecha', 'Estilo', 'Distancia', 'tiempo', 'posicion', 'Sede_Full']].sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

        st.divider()

        # 5. Mis Relevos (Sin columna Distancia)
        st.subheader("🏊‍♂️ Mis Relevos")
        mis_r = df_r_base[cond_rel].copy()
        if not mis_r.empty:
            mis_r = mis_r.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
            mis_r['Sede_Full'] = mis_r['club'].astype(str) + " (" + mis_r['medida'].astype(str) + ")"
            mis_r = mis_r.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
            
            r1, r2 = st.columns(2)
            fr_est = r1.selectbox("Estilo Relevo:", ["Todos"] + sorted(mis_r['Estilo'].unique().tolist()), key="key_rel_est")
            df_r_tmp = mis_r.copy()
            if fr_est != "Todos": df_r_tmp = df_r_tmp[df_r_tmp['Estilo'] == fr_est]
            
            fr_gen = r2.selectbox("Género Relevo:", ["Todos"] + sorted(df_r_tmp['codgenero'].unique().tolist()), key="key_rel_gen")
            if fr_gen != "Todos": df_r_tmp = df_r_tmp[df_r_tmp['codgenero'] == fr_gen]

            def fmt_equipo(row):
                items = []
                for i in range(1, 5):
                    n = dict_id_nombre.get(row[f'nadador_{i}'], "?")
                    t = str(row[f'tiempo_{i}']).strip()
                    if t and t not in ["00.00", "00:00.00", "0", "None", "nan"]:
                        items.append(f"{n} ({t})")
                    else:
                        items.append(n)
                return " / ".join(items)
            
            df_r_tmp['Equipo'] = df_r_tmp.apply(fmt_equipo, axis=1)
            st.dataframe(df_r_tmp[['fecha', 'Estilo', 'codgenero', 'tiempo_final', 'posicion', 'Sede_Full', 'Equipo']].sort_values('fecha', ascending=False),
                         use_container_width=True, hide_index=True)

# --- TAB 3: TODOS LOS RELEVOS ---
with tab3:
    st.subheader("Historial General de Relevos")
    mr = data['relevos'].copy()
    if not mr.empty:
        mr = mr.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
        mr['Sede_Full'] = mr['club'].astype(str) + " (" + mr['medida'].astype(str) + ")"
        mr = mr.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        
        g1, g2, g3 = st.columns(3)
        gr_est = g1.selectbox("Estilo:", ["Todos"] + sorted(mr['Estilo'].unique().tolist()), key="key_all_rel_est")
        mr_g = mr.copy()
        if gr_est != "Todos": mr_g = mr_g[mr_g['Estilo'] == gr_est]
        
        gr_gen = g2.selectbox("Género:", ["Todos"] + sorted(mr_g['codgenero'].unique().tolist()), key="key_all_rel_gen")
        if gr_gen != "Todos": mr_g = mr_g[mr_g['codgenero'] == gr_gen]
        
        gr_reg = g3.selectbox("Reglamento:", ["Todos"] + sorted(mr_g['tipo_reglamento'].unique().tolist()), key="key_all_rel_reg")
        if gr_reg != "Todos": mr_g = mr_g[mr_g['tipo_reglamento'] == gr_reg]
        
        mr_g['suma_edades'] = 0
        for i in range(1, 5):
            mr_g[f'Nadador {i}'] = mr_g[f'nadador_{i}'].map(dict_id_nombre).fillna("?")
            nacs = pd.to_datetime(mr_g[f'nadador_{i}'].map(dict_id_nac))
            mr_g['suma_edades'] += (anio_actual - nacs.dt.year).fillna(0)

        mr_g['Cat. Posta'] = mr_g['suma_edades'].apply(asignar_cat)
        st.dataframe(mr_g[['fecha', 'Sede_Full', 'Estilo', 'Distancia', 'codgenero', 'Cat. Posta', 'tiempo_final', 'posicion', 'Nadador 1', 'Nadador 2', 'Nadador 3', 'Nadador 4']].sort_values('fecha', ascending=False), 
                     use_container_width=True, hide_index=True)
