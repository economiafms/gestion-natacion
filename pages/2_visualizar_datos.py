import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

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

# --- 3. DICCIONARIOS Y PROCESAMIENTO GLOBAL ---
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

# --- 4. INTERFAZ DE USUARIO ---
tab1, tab2, tab3 = st.tabs(["👥 Padrón General", "👤 Ficha del Nadador", "🏊‍♂️ Todos los Relevos"])

# --- TAB 1: PADRÓN ---
with tab1:
    st.subheader("Listado de Nadadores")
    df_p = df_nad.copy()
    df_p['fechanac'] = pd.to_datetime(df_p['fechanac'])
    df_p['Edad'] = 2026 - df_p['fechanac'].dt.year
    def asignar_cat(edad):
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    df_p['Categoría'] = df_p['Edad'].apply(asignar_cat)
    st.dataframe(df_p[['Nombre Completo', 'Edad', 'Categoría', 'codgenero']].sort_values('Nombre Completo'), use_container_width=True, hide_index=True)

# --- TAB 2: FICHA DEL NADADOR ---
with tab2:
    df_t = data['tiempos'].copy()
    df_t = df_t.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
    df_t['Sede_Full'] = df_t['club'].astype(str) + " (" + df_t['medida'].astype(str) + ")"
    df_t = df_t.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
    
    f_nad = st.selectbox("Seleccione un Nadador:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        # --- DATOS PERSONALES ---
        info_nadador = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_actual = info_nadador['codnadador']
        fecha_nac_dt = pd.to_datetime(info_nadador['fechanac'])
        
        anio_actual = 2026 
        edad_master = anio_actual - fecha_nac_dt.year
        
        def obtener_categoria_texto(edad):
            for _, r in data['categorias'].iterrows():
                if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
            return "S/C"
        
        categoria_actual = obtener_categoria_texto(edad_master)

        st.header(f"👤 {info_nadador['apellido'].upper()}, {info_nadador['nombre']}")
        
        c_info1, c_info2, c_info3, c_info4 = st.columns(4)
        c_info1.metric("Nacimiento", fecha_nac_dt.strftime('%d/%m/%Y'))
        c_info2.metric("Edad (al 31/12)", f"{edad_master} años")
        c_info3.metric("Categoría", categoria_actual)
        c_info4.metric("Género", info_nadador['codgenero'])
        
        st.divider()

        # --- MEDALLERO ---
        pos_ind = df_t[df_t['codnadador'] == id_actual]['posicion'].value_counts()
        df_r_base = data['relevos'].copy()
        cond_rel = (df_r_base['nadador_1'] == id_actual) | (df_r_base['nadador_2'] == id_actual) | \
                   (df_r_base['nadador_3'] == id_actual) | (df_r_base['nadador_4'] == id_actual)
        pos_rel = df_r_base[cond_rel]['posicion'].value_counts()
        oro, plata, bronce = pos_ind.get(1,0)+pos_rel.get(1,0), pos_ind.get(2,0)+pos_rel.get(2,0), pos_ind.get(3,0)+pos_rel.get(3,0)
        
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("🥇 Oros", int(oro))
        c_m2.metric("🥈 Platas", int(plata))
        c_m3.metric("🥉 Bronces", int(bronce))
        c_m4.metric("📊 Total Podios", int(oro+plata+bronce))

        st.divider()

        # --- MEJORES MARCAS ---
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
                        st.caption(f"{row['Distancia']}"); st.code(row['tiempo'], language=None)
        
        st.divider()

        # --- HISTORIAL INDIVIDUAL ---
        st.subheader("📜 Historial Individual")
        c1, c2 = st.columns(2)
        h_est_sel = c1.selectbox("Filtrar por Estilo:", ["Todos"] + sorted(mis_tiempos['Estilo'].unique().tolist()), key="h_ind_est")
        df_temp_dis = mis_tiempos.copy()
        if h_est_sel != "Todos":
            df_temp_dis = df_temp_dis[df_temp_dis['Estilo'] == h_est_sel]
        
        h_dis_sel = c2.selectbox("Filtrar por Distancia:", ["Todos"] + sorted(df_temp_dis['Distancia'].unique().tolist()), key="h_ind_dis")
        df_hist = df_temp_dis.copy()
        if h_dis_sel != "Todos":
            df_hist = df_hist[df_hist['Distancia'] == h_dis_sel]
        
        st.dataframe(df_hist[['fecha', 'Estilo', 'Distancia', 'tiempo', 'posicion', 'Sede_Full']].sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

        st.divider()

        # --- MIS RELEVOS ---
        st.subheader("🏊‍♂️ Mis Relevos")
        mis_r = df_r_base[cond_rel].copy()
        if not mis_r.empty:
            mis_r = mis_r.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
            mis_r['Sede_Full'] = mis_r['club'].astype(str) + " (" + mis_r['medida'].astype(str) + ")"
            mis_r = mis_r.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
            
            cr1, cr2 = st.columns(2)
            fr_est_sel = cr1.selectbox("Estilo Relevo:", ["Todos"] + sorted(mis_r['Estilo'].unique().tolist()), key="fr_rel_est")
            df_rel_temp = mis_r.copy()
            if fr_est_sel != "Todos":
                df_rel_temp = df_rel_temp[df_rel_temp['Estilo'] == fr_est_sel]
            
            fr_gen_sel = cr2.selectbox("Género Relevo:", ["Todos"] + sorted(df_rel_temp['codgenero'].unique().tolist()), key="fr_rel_gen")
            if fr_gen_sel != "Todos":
                df_rel_temp = df_rel_temp[df_rel_temp['codgenero'] == fr_gen_sel]

            def obtener_equipo_pro(row):
                detalles = []
                for i in range(1, 5):
                    nom = dict_id_nombre.get(row[f'nadador_{i}'], "?")
                    t = str(row[f'tiempo_{i}']).strip()
                    if t and t not in ["00.00", "00:00.00", "0", "None", "nan"]:
                        detalles.append(f"{nom} ({t})")
                    else:
                        detalles.append(nom)
                return " / ".join(detalles)
            
            df_rel_temp['Equipo y Marcas'] = df_rel_temp.apply(obtener_equipo_pro, axis=1)
            st.dataframe(df_rel_temp[['fecha', 'Estilo', 'codgenero', 'tiempo_final', 'posicion', 'Sede_Full', 'Equipo y Marcas']].sort_values('fecha', ascending=False),
                         use_container_width=True, hide_index=True)

# --- TAB 3: TODOS LOS RELEVOS ---
with tab3:
    st.subheader("Historial General de Relevos")
    if not data['relevos'].empty:
        mr = data['relevos'].copy()
        mr = mr.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
        mr['Sede_Full'] = mr['club'].astype(str) + " (" + mr['medida'].astype(str) + ")"
        mr = mr.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        
        c_rf1, c_rf2, c_rf3 = st.columns(3)
        f_re = c_rf1.selectbox("Filtrar Estilo:", ["Todos"] + sorted(mr['Estilo'].unique().tolist()), key="r_g_est")
        mr_temp = mr.copy()
        if f_re != "Todos": mr_temp = mr_temp[mr_temp['Estilo'] == f_re]
        
        f_rg = c_rf2.selectbox("Filtrar Género:", ["Todos"] + sorted(mr_temp['codgenero'].unique().tolist()), key="r_g_gen")
        if f_rg != "Todos": mr_temp = mr_temp[mr_temp['codgenero'] == f_rg]
        
        f_rr = c_rf3.selectbox("Filtrar Reglamento:", ["Todos"] + sorted(mr_temp['tipo_reglamento'].unique().tolist()), key="r_g_reg")
        if f_rr != "Todos": mr_temp = mr_temp[mr_temp['tipo_reglamento'] == f_rr]
        
        mr_temp['suma_edades'] = 0
        for i in range(1, 5):
            mr_temp[f'Nadador {i}'] = mr_temp[f'nadador_{i}'].map(dict_id_nombre).fillna("?")
            nacs = pd.to_datetime(mr_temp[f'nadador_{i}'].map(dict_id_nac))
            mr_temp['suma_edades'] += (2026 - nacs.dt.year).fillna(0)

        def cat_p(row):
            reg = row.get('tipo_reglamento', 'FED'); regs = data['cat_relevos'][data['cat_relevos']['tipo_reglamento'] == reg]
            for _, r in regs.iterrows():
                if r['suma_min'] <= row['suma_edades'] <= r['suma_max']: return r['descripcion']
            return f"Suma {int(row['suma_edades'])}"

        mr_temp['Cat. Posta'] = mr_temp.apply(cat_p, axis=1)
        st.dataframe(mr_temp[['fecha', 'Sede_Full', 'Estilo', 'Distancia', 'codgenero', 'Cat. Posta', 'tiempo_final', 'posicion', 'Nadador 1', 'Nadador 2', 'Nadador 3', 'Nadador 4']].sort_values('fecha', ascending=False), 
                     use_container_width=True, hide_index=True)# --- TAB 2: FICHA DEL NADADOR ---
with tab2:
    df_t = data['tiempos'].copy()
    df_t = df_t.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
    df_t['Sede_Full'] = df_t['club'].astype(str) + " (" + df_t['medida'].astype(str) + ")"
    df_t = df_t.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
    
    f_nad = st.selectbox("Seleccione un Nadador:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        # --- DATOS PERSONALES ---
        info_nadador = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_actual = info_nadador['codnadador']
        fecha_nac_dt = pd.to_datetime(info_nadador['fechanac'])
        
        anio_actual = 2026 
        edad_master = anio_actual - fecha_nac_dt.year
        
        def obtener_categoria_texto(edad):
            for _, r in data['categorias'].iterrows():
                if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
            return "S/C"
        
        categoria_actual = obtener_categoria_texto(edad_master)

        st.header(f"👤 {info_nadador['apellido'].upper()}, {info_nadador['nombre']}")
        
        c_info1, c_info2, c_info3, c_info4 = st.columns(4)
        c_info1.metric("Nacimiento", fecha_nac_dt.strftime('%d/%m/%Y'))
        c_info2.metric("Edad (al 31/12)", f"{edad_master} años")
        c_info3.metric("Categoría", categoria_actual)
        c_info4.metric("Género", info_nadador['codgenero'])
        
        st.divider()

        # --- MEDALLERO ---
        pos_ind = df_t[df_t['codnadador'] == id_actual]['posicion'].value_counts()
        df_r_base = data['relevos'].copy()
        cond_rel = (df_r_base['nadador_1'] == id_actual) | (df_r_base['nadador_2'] == id_actual) | \
                   (df_r_base['nadador_3'] == id_actual) | (df_r_base['nadador_4'] == id_actual)
        pos_rel = df_r_base[cond_rel]['posicion'].value_counts()
        oro, plata, bronce = pos_ind.get(1,0)+pos_rel.get(1,0), pos_ind.get(2,0)+pos_rel.get(2,0), pos_ind.get(3,0)+pos_rel.get(3,0)
        
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("🥇 Oros", int(oro))
        c_m2.metric("🥈 Platas", int(plata))
        c_m3.metric("🥉 Bronces", int(bronce))
        c_m4.metric("📊 Total Podios", int(oro+plata+bronce))

        st.divider()

        # --- MEJORES MARCAS ---
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
                        st.caption(f"{row['Distancia']}"); st.code(row['tiempo'], language=None)
        
        st.divider()

        # --- HISTORIAL INDIVIDUAL Y GRÁFICO ---
        st.subheader("📜 Historial y Evolución")
        c1, c2 = st.columns(2)
        h_est_sel = c1.selectbox("Filtrar por Estilo:", ["Todos"] + sorted(mis_tiempos['Estilo'].unique().tolist()), key="h_ind_est")
        
        df_temp_dis = mis_tiempos.copy()
        if h_est_sel != "Todos":
            df_temp_dis = df_temp_dis[df_temp_dis['Estilo'] == h_est_sel]
        
        h_dis_sel = c2.selectbox("Filtrar por Distancia:", ["Todos"] + sorted(df_temp_dis['Distancia'].unique().tolist()), key="h_ind_dis")
        
        df_hist = df_temp_dis.copy()
        if h_dis_sel != "Todos":
            df_hist = df_hist[df_hist['Distancia'] == h_dis_sel]

        # --- LÓGICA DEL GRÁFICO ---
        if h_est_sel != "Todos" and h_dis_sel != "Todos":
            if len(df_hist) > 0:
                import plotly.express as px
                df_grafico = df_hist.copy()
                df_grafico['fecha'] = pd.to_datetime(df_grafico['fecha'])
                df_grafico = df_grafico.sort_values('fecha')

                fig = px.line(
                    df_grafico, x='fecha', y='segundos', 
                    markers=True, title=f"Evolución en {h_dis_sel} {h_est_sel}",
                    labels={'segundos': 'Tiempo (seg)', 'fecha': 'Fecha'},
                    hover_data={'segundos': False, 'tiempo': True, 'fecha': '|%d/%m/%Y', 'Sede_Full': True}
                )
                fig.update_yaxes(autorange="reversed") # Menos tiempo es mejor (arriba)
                fig.update_layout(hovermode="x unified", height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos suficientes para graficar esta combinación.")

        st.dataframe(df_hist[['fecha', 'Estilo', 'Distancia', 'tiempo', 'posicion', 'Sede_Full']].sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

        st.divider()

        # --- MIS RELEVOS ---
        st.subheader("🏊‍♂️ Mis Relevos")
        mis_r = df_r_base[cond_rel].copy()
        if not mis_r.empty:
            mis_r = mis_r.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
            mis_r['Sede_Full'] = mis_r['club'].astype(str) + " (" + mis_r['medida'].astype(str) + ")"
            mis_r = mis_r.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
            
            cr1, cr2 = st.columns(2)
            fr_est_sel = cr1.selectbox("Estilo Relevo:", ["Todos"] + sorted(mis_r['Estilo'].unique().tolist()), key="fr_rel_est")
            
            df_rel_temp = mis_r.copy()
            if fr_est_sel != "Todos":
                df_rel_temp = df_rel_temp[df_rel_temp['Estilo'] == fr_est_sel]
            
            fr_gen_sel = cr2.selectbox("Género Relevo:", ["Todos"] + sorted(df_rel_temp['codgenero'].unique().tolist()), key="fr_rel_gen")
            
            if fr_gen_sel != "Todos":
                df_rel_temp = df_rel_temp[df_rel_temp['codgenero'] == fr_gen_sel]

            def obtener_equipo_pro(row):
                detalles = []
                for i in range(1, 5):
                    nom = dict_id_nombre.get(row[f'nadador_{i}'], "?")
                    t = str(row[f'tiempo_{i}']).strip()
                    if t and t not in ["00.00", "00:00.00", "0", "None", "nan"]:
                        detalles.append(f"{nom} ({t})")
                    else:
                        detalles.append(nom)
                return " / ".join(detalles)
            
            df_rel_temp['Equipo y Marcas'] = df_rel_temp.apply(obtener_equipo_pro, axis=1)
            st.dataframe(df_rel_temp[['fecha', 'Estilo', 'codgenero', 'tiempo_final', 'posicion', 'Sede_Full', 'Equipo y Marcas']].sort_values('fecha', ascending=False),
                         use_container_width=True, hide_index=True)

