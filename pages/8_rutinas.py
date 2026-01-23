import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Rutinas", layout="centered")

# --- 2. SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. FUNCIONES AUXILIARES ---
def obtener_nombre_mes(n):
    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    try:
        return meses[int(n)]
    except:
        return "Desconocido"

@st.cache_data(ttl="10s")
def cargar_datos_rutinas():
    try:
        # Rutinas
        try:
            df_rut = conn.read(worksheet="Rutinas")
        except:
            df_rut = pd.DataFrame(columns=["id_rutina", "anio_rutina", "mes_rutina", "nro_sesion", "texto_rutina"])
        
        # Seguimiento
        try:
            df_seg = conn.read(worksheet="Rutinas_Seguimiento")
        except:
            df_seg = pd.DataFrame(columns=["id_rutina", "codnadador", "fecha_realizada"])

        # Nadadores (Para el filtro del profesor)
        try:
            df_nad = conn.read(worksheet="Nadadores")
        except:
            df_nad = pd.DataFrame(columns=["codnadador", "nombre", "apellido"])
            
        # Asegurar tipos de datos
        if not df_rut.empty:
            df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)
            
        if not df_seg.empty:
            df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)

        if not df_nad.empty:
             df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce').fillna(0).astype(int)
            
        return df_rut, df_seg, df_nad
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None, None, None

def calcular_proxima_sesion(df, anio, mes):
    """Devuelve el número de sesión siguiente al último cargado para ese mes."""
    if df is None or df.empty: return 1
    filtro = df[(df['anio_rutina'] == anio) & (df['mes_rutina'] == mes)]
    if filtro.empty: return 1
    return int(filtro['nro_sesion'].max()) + 1

def guardar_seguimiento(id_rutina, id_nadador):
    df_rut, df_seg, df_nad = cargar_datos_rutinas()
    existe = df_seg[(df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador)]
    
    if existe.empty:
        # AJUSTE HORARIO: Restamos 3 horas para Argentina
        hora_arg = datetime.now() - timedelta(hours=3)
        
        nuevo_registro = pd.DataFrame([{
            "id_rutina": id_rutina,
            "codnadador": id_nadador,
            "fecha_realizada": hora_arg.strftime("%Y-%m-%d %H:%M:%S")
        }])
        df_final = pd.concat([df_seg, nuevo_registro], ignore_index=True)
        conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
        st.cache_data.clear()
        return True
    return False

def borrar_seguimiento(id_rutina, id_nadador):
    df_rut, df_seg, df_nad = cargar_datos_rutinas()
    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
    st.cache_data.clear()
    return True

def guardar_rutina_admin(anio, mes, sesion, texto):
    df_rut, df_seg, df_nad = cargar_datos_rutinas()
    nuevo_id = f"{anio}-{mes:02d}-S{sesion:02d}"
    mask = df_rut['id_rutina'] == nuevo_id
    
    nueva_fila = {
        "id_rutina": nuevo_id,
        "anio_rutina": int(anio),
        "mes_rutina": int(mes),
        "nro_sesion": int(sesion),
        "texto_rutina": texto
    }
    
    if df_rut[mask].empty:
        df_rut = pd.concat([df_rut, pd.DataFrame([nueva_fila])], ignore_index=True)
        msg = "Rutina creada correctamente."
    else:
        df_rut.loc[mask, "texto_rutina"] = texto
        df_rut.loc[mask, "anio_rutina"] = int(anio)
        df_rut.loc[mask, "mes_rutina"] = int(mes)
        df_rut.loc[mask, "nro_sesion"] = int(sesion)
        msg = "Rutina actualizada correctamente."
        
    conn.update(worksheet="Rutinas", data=df_rut)
    st.cache_data.clear()
    return msg

def activar_calculo_auto():
    st.session_state.trigger_calculo = True

# --- COMPONENTES DE VISUALIZACIÓN ---

def render_tarjeta_individual(row, df_seg, key_suffix):
    r_id = row['id_rutina']
    r_sesion = row['nro_sesion']
    r_texto = row['texto_rutina']
    
    # Verificar estado
    check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == mi_id)]
    esta_realizada = not check.empty
    fecha_str = ""
    if esta_realizada:
        fecha_obj = pd.to_datetime(check.iloc[0]['fecha_realizada'])
        fecha_str = fecha_obj.strftime("%d/%m")

    # Estilos
    borde = "#2E7D32" if esta_realizada else "#444" 
    bg = "#1B2E1B" if esta_realizada else "#262730"
    
    with st.container():
        st.markdown(f"""<div style="border: 2px solid {borde}; border-radius: 10px; background-color: {bg}; padding: 15px; margin-bottom: 15px;">""", unsafe_allow_html=True)
        
        # --- COLUMNAS DINÁMICAS ---
        if esta_realizada:
            # Si está completada, damos mucho espacio al texto (8) y poco al botón (1) para pegarlo a la derecha
            c_head, c_act = st.columns([8, 1])
            
            with c_head:
                st.markdown(f"#### ✅ Sesión {r_sesion} <span style='font-size:14px; color:#888'>({fecha_str})</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-decoration: line-through; color: #aaa;'>", unsafe_allow_html=True)
                st.markdown(r_texto)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with c_act:
                st.write("") # Alineación vertical
                if st.button("❌", key=f"un_{r_id}_{key_suffix}", help="Desmarcar (No realizada)"):
                    borrar_seguimiento(r_id, mi_id)
                    st.rerun()
        else:
            # Si está pendiente, mantenemos espacio para el botón grande "DÍA GANADO"
            c_head, c_act = st.columns([5, 2])
            
            with c_head:
                st.markdown(f"#### ⭕ Sesión {r_sesion}")
                st.markdown(r_texto)
            
            with c_act:
                st.write("") # Alineación vertical
                if st.button("🏊 DÍA GANADO", key=f"do_{r_id}_{key_suffix}", type="primary", help="Marcar como Completada"):
                    guardar_seguimiento(r_id, mi_id)
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

def render_feed_activo(df_rut, df_seg, anio_ver, mes_ver, key_suffix=""):
    """Muestra las tarjetas con lógica de reordenamiento (Completadas arriba)."""
    rutinas_filtradas = df_rut[
        (df_rut['anio_rutina'] == anio_ver) & 
        (df_rut['mes_rutina'] == mes_ver)
    ].copy()
    rutinas_filtradas.sort_values(by='nro_sesion', ascending=True, inplace=True)

    if rutinas_filtradas.empty:
        st.info(f"No hay rutinas cargadas para {obtener_nombre_mes(mes_ver)} {anio_ver}.")
        return

    # Separar en Pendientes y Completadas
    l_pendientes = []
    l_completadas = []

    for index, row in rutinas_filtradas.iterrows():
        check = df_seg[(df_seg['id_rutina'] == row['id_rutina']) & (df_seg['codnadador'] == mi_id)]
        if not check.empty:
            l_completadas.append(row)
        else:
            l_pendientes.append(row)

    # 1. MOSTRAR COMPLETADAS (ARRIBA - COLAPSADAS)
    if l_completadas:
        with st.expander(f"✅ Historial: {len(l_completadas)} Sesiones Completadas", expanded=False):
            # Invertimos el orden para ver la última completada primero
            for row in reversed(l_completadas):
                render_tarjeta_individual(row, df_seg, key_suffix)
        st.write("---")

    # 2. MOSTRAR PENDIENTES (ABAJO - EXPANDIDAS)
    if l_pendientes:
        st.markdown("#### 🚀 Próximas Sesiones")
        for row in l_pendientes:
            render_tarjeta_individual(row, df_seg, key_suffix)
    else:
        # Si no hay pendientes y sí había completadas
        if l_completadas:
            st.success("¡Excelente! Has completado todas las sesiones del mes. 🏆")

def render_historial_compacto(df_rut, df_seg, anio, mes, id_usuario_objetivo):
    """Muestra tabla de cumplimiento SIN TEXTO."""
    
    rutinas_mes = df_rut[
        (df_rut['anio_rutina'] == anio) & 
        (df_rut['mes_rutina'] == mes)
    ].sort_values('nro_sesion')

    if rutinas_mes.empty:
        st.info("No hay rutinas definidas para este mes.")
        return

    datos_tabla = []
    total_rutinas = len(rutinas_mes)
    completadas = 0

    for _, r in rutinas_mes.iterrows():
        r_id = r['id_rutina']
        check = df_seg[
            (df_seg['id_rutina'] == r_id) & 
            (df_seg['codnadador'] == id_usuario_objetivo)
        ]
        
        hecho = not check.empty
        fecha_txt = "-"
        if hecho:
            completadas += 1
            fecha_obj = pd.to_datetime(check.iloc[0]['fecha_realizada'])
            fecha_txt = fecha_obj.strftime("%d/%m/%Y %H:%M")

        datos_tabla.append({
            "Sesión": f"Sesión {r['nro_sesion']}",
            "Estado": "✅ Completado" if hecho else "❌ Pendiente",
            "Fecha Realización": fecha_txt,
            "_sort": r['nro_sesion']
        })

    porcentaje = int((completadas / total_rutinas) * 100) if total_rutinas > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sesiones", total_rutinas)
    c2.metric("Completadas", completadas)
    c3.metric("Asistencia", f"{porcentaje}%")

    st.progress(porcentaje / 100)
    
    df_view = pd.DataFrame(datos_tabla).sort_values('_sort')
    st.dataframe(
        df_view[["Sesión", "Estado", "Fecha Realización"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Estado": st.column_config.TextColumn("Estado", width="medium")
        }
    )

# --- 5. LÓGICA DE CARGA ---
df_rutinas, df_seguimiento, df_nadadores = cargar_datos_rutinas()

# Inicializar gestión (Solo Admins)
if rol in ["M", "P"]:
    if "g_anio" not in st.session_state: st.session_state.g_anio = datetime.now().year
    if "g_mes" not in st.session_state: st.session_state.g_mes = datetime.now().month

    if st.session_state.get("trigger_calculo", False) or "admin_sesion" not in st.session_state:
        if df_rutinas is not None:
            prox = calcular_proxima_sesion(df_rutinas, st.session_state.g_anio, st.session_state.g_mes)
            st.session_state.admin_sesion = min(prox, 31)
        else:
            st.session_state.admin_sesion = 1
        st.session_state.trigger_calculo = False

# --- 6. INTERFAZ ---
st.title("📝 Rutinas de Entrenamiento")

if df_rutinas is None:
    st.stop()

st.write("---")

# ==========================
# ROL: PROFESOR (M)
# ==========================
if rol in ["M", "P"]:
    
    # 1. BLOQUE DE GESTIÓN (Carga)
    with st.expander("⚙️ Gestión de Rutinas (Crear/Editar)", expanded=False):
        st.markdown("##### Editor de Rutinas")
        c1, c2, c3 = st.columns([1, 1, 1])
        
        anio_actual = datetime.now().year
        anios_gest = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [anio_actual])), reverse=True)
        meses_indices = list(range(1, 13))
        mapa_meses = {i: obtener_nombre_mes(i) for i in meses_indices}

        with c1: 
            st.number_input("Año", min_value=2020, max_value=2030, key="g_anio", on_change=activar_calculo_auto)
        with c2: 
            st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], key="g_mes", on_change=activar_calculo_auto)
        with c3: 
            st.number_input("Nro Sesión", min_value=1, max_value=31, key="admin_sesion")
            
        id_busqueda = f"{st.session_state.g_anio}-{st.session_state.g_mes:02d}-S{st.session_state.admin_sesion:02d}"
        row_existente = df_rutinas[df_rutinas['id_rutina'] == id_busqueda]
        texto_previo = row_existente.iloc[0]['texto_rutina'] if not row_existente.empty else ""
        
        st.caption(f"ID: {id_busqueda} | {'✏️ Editando' if not row_existente.empty else '✨ Nueva'}")
        
        with st.form("form_rutina"):
            f_texto = st.text_area("Contenido", value=texto_previo, height=200, key=f"txt_{id_busqueda}")
            if st.form_submit_button("Guardar"):
                if f_texto.strip() == "":
                    st.error("Texto vacío.")
                else:
                    guardar_rutina_admin(st.session_state.g_anio, st.session_state.g_mes, st.session_state.admin_sesion, f_texto)
                    st.success("Guardado.")
                    st.session_state.trigger_calculo = True
                    time.sleep(0.5)
                    st.rerun()

    st.divider()

    # 2. BLOQUE DE CONSULTA (Tabs)
    tab_explorar, tab_seguimiento = st.tabs(["📖 Explorar Rutinas (Textos)", "📊 Seguimiento Alumnos"])
    
    with tab_explorar:
        col_v1, col_v2 = st.columns(2)
        v_anios = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [datetime.now().year])), reverse=True)
        
        with col_v1: sel_a = st.selectbox("Año", v_anios, key="adm_v_a")
        with col_v2: sel_m = st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], index=meses_indices.index(datetime.now().month), key="adm_v_m")
        
        render_feed_activo(df_rutinas, df_seguimiento, sel_a, sel_m, key_suffix="admin_view")

    with tab_seguimiento:
        st.info("Seleccione un alumno para ver su cumplimiento histórico.")
        
        df_nadadores['NombreCompleto'] = df_nadadores['apellido'] + ", " + df_nadadores['nombre']
        lista_nads = df_nadadores[['codnadador', 'NombreCompleto']].sort_values('NombreCompleto')
        
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        with col_s1:
            sel_nad_id = st.selectbox(
                "Alumno", 
                lista_nads['codnadador'], 
                format_func=lambda x: lista_nads[lista_nads['codnadador'] == x]['NombreCompleto'].values[0]
            )
        with col_s2:
            sel_a_seg = st.selectbox("Año", v_anios, key="seg_a")
        with col_s3:
            sel_m_seg = st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], index=meses_indices.index(datetime.now().month), key="seg_m")
            
        st.markdown(f"**Reporte para:** {lista_nads[lista_nads['codnadador']==sel_nad_id]['NombreCompleto'].values[0]}")
        render_historial_compacto(df_rutinas, df_seguimiento, sel_a_seg, sel_m_seg, sel_nad_id)

# ==========================
# ROL: NADADOR (N)
# ==========================
else:
    tab_curso, tab_hist = st.tabs(["📅 Mes en Curso", "📜 Historial / Registro"])
    
    with tab_curso:
        # Fijo a fecha actual
        hoy = datetime.now()
        st.markdown(f"### Rutinas de {obtener_nombre_mes(hoy.month)} {hoy.year}")
        render_feed_activo(df_rutinas, df_seguimiento, hoy.year, hoy.month, key_suffix="nad_curso")
        
    with tab_hist:
        st.markdown("#### Registro de Cumplimiento")
        st.caption("Aquí puedes verificar tu asistencia a las sesiones pasadas.")
        
        c_h1, c_h2 = st.columns(2)
        anios_disp = sorted(list(set(df_rutinas['anio_rutina'].unique())), reverse=True)
        if not anios_disp: anios_disp = [datetime.now().year]
        
        with c_h1: h_anio = st.selectbox("Año", anios_disp, key="h_a")
        
        # CAMBIO: Filtrado de meses que SÍ tienen datos
        meses_en_anio = sorted(df_rutinas[df_rutinas['anio_rutina'] == h_anio]['mes_rutina'].unique().tolist())
        
        if not meses_en_anio:
            with c_h2: 
                st.warning("Sin datos.")
                h_mes = None
        else:
            mapa_meses = {i: obtener_nombre_mes(i) for i in meses_en_anio}
            with c_h2: 
                h_mes = st.selectbox("Mes", meses_en_anio, format_func=lambda x: mapa_meses[x], key="h_m")
            
        if h_mes:
            render_historial_compacto(df_rutinas, df_seguimiento, h_anio, h_mes, mi_id)
