import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import time
import random

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Sesiones de Entrenamiento", layout="centered")

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

# --- GLOSARIO DE REFERENCIAS ---
def mostrar_referencias():
    with st.expander("📖 Glosario de Referencias (Clic para ver)"):
        st.markdown("""
        **INTENSIDADES**
        * **T (Tolerancia):** Intensidad alta 100 – 110%
        * **VC (Velocidad Corta):** Máxima velocidad
        * **VS (Velocidad Sostenida):** Mantener velocidad alta
        * **F1 (Vo2):** Intensidad 100%
        * **F2 (Super Aeróbico):** Intensidad 80-90%
        * **F3 (Sub Aeróbico):** Intensidad 70%
        * **Prog. (Progresivo):** De menor a mayor
        * **Reg (Regresivo):** De mayor a menor

        **ACTIVACIÓN Y ENTRADA EN CALOR**
        * **Ec (Entrada en Calor):** Nado suave inicial
        * **EcT (Ec Tensor):** Bíceps, Tríceps, Dorsales, Hombros, Pecho, Antebrazos
        * **EcM (Ec Movilidad):** Fuera del agua (Brazos, Cintura, Piernas, Tobillos, Cuello)
        * **Act (Activación):** Fuera del agua (Piernas, Brazos, Core)

        **TÉCNICA Y ESTILOS**
        * **B (Brazada):** C (Crol), E (Espalda), P (Pecho), M (Mariposa)
        * **Pat Ph:** Patada en Posición Hidrodinámica
        * **Pat Tabla:** Patada con tabla
        * **PB (Pull Brazada):** Uso de pullboy
        * **CT:** Corrección Técnica
        
        **OTROS**
        * **m:** Metros
        * **p:** Pausa estática
        * **p act:** Pausa Activa
        * **D/:** Dentro del tiempo
        * **C/:** Con tiempo de pausa
        """)

# --- FUNCIÓN DE RETRY ---
def actualizar_con_retry(worksheet, data, max_retries=5):
    for i in range(max_retries):
        try:
            conn.update(worksheet=worksheet, data=data)
            return True, None 
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                wait_time = (2 ** i) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue 
            else:
                return False, e
    return False, "Tiempo de espera agotado (API ocupada)."

# --- LECTURA ---
@st.cache_data(ttl="10s")
def cargar_datos_rutinas_view():
    try:
        try:
            df_rut = conn.read(worksheet="Rutinas").copy()
        except:
            df_rut = pd.DataFrame(columns=["id_rutina", "anio_rutina", "mes_rutina", "nro_sesion", "texto_rutina"])
        
        try:
            df_seg = conn.read(worksheet="Rutinas_Seguimiento").copy()
        except:
            df_seg = pd.DataFrame(columns=["id_rutina", "codnadador", "fecha_realizada"])

        try:
            df_nad = conn.read(worksheet="Nadadores").copy()
        except:
            df_nad = pd.DataFrame(columns=["codnadador", "nombre", "apellido"])
            
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
        st.error(f"Error visual: {e}")
        return None, None, None

def leer_dataset_fresco(worksheet):
    try:
        df = conn.read(worksheet=worksheet, ttl=0).copy()
        return df
    except Exception as e:
        st.error(f"Error de conexión con {worksheet}: {e}")
        return None

def calcular_proxima_sesion(df, anio, mes):
    if df is None or df.empty: return 1
    filtro = df[(df['anio_rutina'] == anio) & (df['mes_rutina'] == mes)]
    if filtro.empty: return 1
    return int(filtro['nro_sesion'].max()) + 1

# --- FUNCIONES DE GUARDADO ---
def guardar_seguimiento(id_rutina, id_nadador):
    df_seg = leer_dataset_fresco("Rutinas_Seguimiento")
    if df_seg is None: return False 
    if not df_seg.empty:
        df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
    existe = df_seg[(df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador)]
    if existe.empty:
        hora_arg = datetime.now() - timedelta(hours=3)
        nuevo_registro = pd.DataFrame([{"id_rutina": id_rutina, "codnadador": id_nadador, "fecha_realizada": hora_arg.strftime("%Y-%m-%d %H:%M:%S")}])
        exito, _ = actualizar_con_retry("Rutinas_Seguimiento", pd.concat([df_seg, nuevo_registro], ignore_index=True))
        if exito: st.cache_data.clear(); return True
    return False

def borrar_seguimiento(id_rutina, id_nadador):
    df_seg = leer_dataset_fresco("Rutinas_Seguimiento")
    if df_seg is None: return False
    if not df_seg.empty:
        df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry("Rutinas_Seguimiento", df_final)
    if exito: st.cache_data.clear(); return True
    return False

def eliminar_sesion_admin(id_rutina):
    df_rut = leer_dataset_fresco("Rutinas")
    if df_rut is None: return "❌ Error de conexión."
    rutina_a_borrar = df_rut[df_rut['id_rutina'] == id_rutina]
    if rutina_a_borrar.empty: return "⚠️ La sesión no existe."
    r_anio = rutina_a_borrar.iloc[0]['anio_rutina']
    r_mes = rutina_a_borrar.iloc[0]['mes_rutina']
    r_sesion = rutina_a_borrar.iloc[0]['nro_sesion']
    rutinas_mes = df_rut[(df_rut['anio_rutina'] == r_anio) & (df_rut['mes_rutina'] == r_mes)]
    max_sesion = rutinas_mes['nro_sesion'].max()
    if r_sesion < max_sesion: return f"🚫 Solo se permite eliminar la última sesión (Sesión {max_sesion})."
    df_rut_final = df_rut[df_rut['id_rutina'] != id_rutina]
    exito, error = actualizar_con_retry("Rutinas", df_rut_final)
    if exito: st.cache_data.clear(); return "🗑️ Sesión eliminada."
    else: return f"❌ Error: {error}"

def guardar_sesion_admin(anio, mes, sesion, texto):
    df_rut = leer_dataset_fresco("Rutinas")
    if df_rut is None: return "❌ Error conexión."
    if not df_rut.empty:
        df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
        df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
        df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)
    nuevo_id = f"{anio}-{mes:02d}-S{sesion:02d}"
    mask = df_rut['id_rutina'] == nuevo_id
    nueva_fila = {"id_rutina": nuevo_id, "anio_rutina": int(anio), "mes_rutina": int(mes), "nro_sesion": int(sesion), "texto_rutina": texto}
    if df_rut[mask].empty:
        df_rut = pd.concat([df_rut, pd.DataFrame([nueva_fila])], ignore_index=True)
        msg = "✅ Sesión creada."
    else:
        df_rut.loc[mask, "texto_rutina"] = texto
        msg = "✅ Sesión actualizada."
    exito, error = actualizar_con_retry("Rutinas", df_rut)
    return msg if exito else f"❌ Error: {error}"

def activar_calculo_auto():
    st.session_state.trigger_calculo = True

# --- COMPONENTES VISUALES ---

def render_tarjeta_individual(row, df_seg, key_suffix):
    r_id = row['id_rutina']
    r_sesion = row['nro_sesion']
    r_texto = row['texto_rutina']
    
    check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == mi_id)]
    esta_realizada = not check.empty
    fecha_str = ""
    if esta_realizada:
        fecha_obj = pd.to_datetime(check.iloc[0]['fecha_realizada'])
        fecha_str = fecha_obj.strftime("%d/%m")

    if esta_realizada:
        borde = "#2E7D32"
        bg = "#1B2E1B"
    else:
        borde = "#444"
        bg = "#262730"
    
    with st.container():
        st.markdown(f"""<div style="border: 2px solid {borde}; border-radius: 10px; background-color: {bg}; padding: 15px; margin-bottom: 15px;">""", unsafe_allow_html=True)
        
        if esta_realizada:
            c_head, c_act = st.columns([8, 1])
            with c_head:
                st.markdown(f"#### ✅ Sesión {r_sesion} <span style='font-size:14px; color:#888'>({fecha_str})</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-decoration: line-through; color: #aaa;'>", unsafe_allow_html=True)
                st.markdown(r_texto)
                st.markdown("</div>", unsafe_allow_html=True)
            with c_act:
                if st.button("❌", key=f"un_{r_id}_{key_suffix}", help="Desmarcar"):
                    borrar_seguimiento(r_id, mi_id); st.rerun()
        else:
            c_head, c_act = st.columns([5, 2])
            with c_head:
                st.markdown(f"#### ⭕ Sesión {r_sesion}")
                st.markdown(r_texto)
            with c_act:
                st.write("") 
                if st.button("🏊 DÍA GANADO", key=f"do_{r_id}_{key_suffix}", type="primary"):
                    guardar_seguimiento(r_id, mi_id); st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def render_feed_activo(df_rut, df_seg, anio_ver, mes_ver, key_suffix=""):
    rutinas_filtradas = df_rut[
        (df_rut['anio_rutina'] == anio_ver) & 
        (df_rut['mes_rutina'] == mes_ver)
    ].copy()

    if rutinas_filtradas.empty:
        st.info(f"No hay sesiones cargadas para {obtener_nombre_mes(mes_ver)} {anio_ver}.")
        return

    rutinas_filtradas.sort_values(by='nro_sesion', ascending=True, inplace=True)
    
    mostrar_referencias()

    l_pendientes = []
    l_completadas = []

    for index, row in rutinas_filtradas.iterrows():
        check = df_seg[(df_seg['id_rutina'] == row['id_rutina']) & (df_seg['codnadador'] == mi_id)]
        if not check.empty: l_completadas.append(row)
        else: l_pendientes.append(row)

    if l_completadas:
        with st.expander(f"✅ Completadas ({len(l_completadas)})", expanded=False):
            for row in reversed(l_completadas):
                render_tarjeta_individual(row, df_seg, key_suffix)
        st.write("---")

    if l_pendientes:
        st.markdown("#### 🚀 Próximas Sesiones")
        for row in l_pendientes:
            render_tarjeta_individual(row, df_seg, key_suffix)
    else:
        if l_completadas: st.success("¡Excelente! Has completado todo el mes. 🏆")

def render_historial_compacto(df_rut, df_seg, anio, mes, id_usuario_objetivo):
    """Muestra tabla completa de asistencia + Métricas."""
    
    rutinas_mes = df_rut[
        (df_rut['anio_rutina'] == anio) & 
        (df_rut['mes_rutina'] == mes)
    ].sort_values('nro_sesion')

    if rutinas_mes.empty:
        st.info("No hay planificación cargada para este mes.")
        return

    datos_tabla = []
    total_rutinas = len(rutinas_mes)
    completadas = 0

    for _, r in rutinas_mes.iterrows():
        r_id = r['id_rutina']
        check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == id_usuario_objetivo)]
        
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
            "_nro": r['nro_sesion']
        })

    porcentaje = int((completadas / total_rutinas) * 100) if total_rutinas > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sesiones", total_rutinas)
    c2.metric("Completadas", completadas)
    c3.metric("Asistencia Global", f"{porcentaje}%")
    st.progress(porcentaje / 100)
    
    st.divider()
    
    df_view = pd.DataFrame(datos_tabla).sort_values('_nro')
    st.dataframe(
        df_view[["Sesión", "Estado", "Fecha Realización"]],
        use_container_width=True,
        hide_index=True
    )

# --- 5. LOGICA PRINCIPAL ---
df_rutinas, df_seguimiento, df_nadadores = cargar_datos_rutinas_view()

# --- GESTIÓN DE ESTADO ADMIN ---
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

# --- UI PRINCIPAL ---
st.title("📝 Sesiones de Entrenamiento")
st.subheader(f"{mi_nombre}") 

if df_rutinas is None:
    st.error("No se pudieron cargar los datos. Verifica tu conexión.")
    st.stop()

st.write("---")

# ==========================
# ROL: PROFESOR (M)
# ==========================
if rol in ["M", "P"]:
    with st.expander("⚙️ Gestión de Sesiones (Crear/Editar)", expanded=False):
        st.markdown("##### Editor de Sesiones")
        c1, c2, c3 = st.columns([1, 1, 1])
        
        anio_actual = datetime.now().year
        meses_indices = list(range(1, 13))
        mapa_meses = {i: obtener_nombre_mes(i) for i in meses_indices}

        with c1: st.number_input("Año", min_value=2020, max_value=2030, key="g_anio", on_change=activar_calculo_auto)
        with c2: st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], key="g_mes", on_change=activar_calculo_auto)
        with c3: st.number_input("Nro Sesión", min_value=1, max_value=31, key="admin_sesion")
            
        id_busqueda = f"{st.session_state.g_anio}-{st.session_state.g_mes:02d}-S{st.session_state.admin_sesion:02d}"
        row_existente = df_rutinas[df_rutinas['id_rutina'] == id_busqueda]
        
        es_edicion = not row_existente.empty
        texto_previo = row_existente.iloc[0]['texto_rutina'] if es_edicion else ""
        estado_txt = "✏️ Editando Existente" if es_edicion else "✨ Nueva Sesión"
        st.caption(f"ID: {id_busqueda} | {estado_txt}")
        
        with st.form("form_rutina"):
            f_texto = st.text_area("Contenido", value=texto_previo, height=200)
            if es_edicion:
                c_del, c_save = st.columns([1, 2])
                with c_del: delete_btn = st.form_submit_button("🗑️ Eliminar Sesión", type="secondary")
                with c_save: submitted = st.form_submit_button("💾 Actualizar Sesión", type="primary")
            else:
                submitted = st.form_submit_button("💾 Crear Sesión", type="primary")
                delete_btn = False

            if submitted:
                msg = guardar_sesion_admin(st.session_state.g_anio, st.session_state.g_mes, st.session_state.admin_sesion, f_texto)
                if "Error" in msg: 
                    st.error(msg)
                else: 
                    st.success(msg)
                    # --- FIX: FORZAR INCREMENTO MANUAL PARA FLUJO DE CARGA ---
                    if st.session_state.admin_sesion < 31:
                        st.session_state.admin_sesion += 1
                    time.sleep(0.5)
                    st.rerun()
            
            if delete_btn:
                msg = eliminar_sesion_admin(id_busqueda)
                if "Error" in msg: st.error(msg)
                else: st.warning(msg); st.session_state.trigger_calculo = True; time.sleep(1); st.rerun()

    st.divider()
    tab_explorar, tab_seguimiento = st.tabs(["📖 Explorar Sesiones", "📊 Seguimiento Alumnos"])
    
    with tab_explorar:
        c1, c2 = st.columns(2)
        v_anios = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [datetime.now().year])), reverse=True)
        with c1: sel_a = st.selectbox("Año", v_anios, key="adm_v_a")
        meses_disp = sorted(df_rutinas[df_rutinas['anio_rutina'] == sel_a]['mes_rutina'].unique().tolist())
        if meses_disp:
             mapa = {i: obtener_nombre_mes(i) for i in meses_disp}
             with c2: sel_m = st.selectbox("Mes", meses_disp, format_func=lambda x: mapa[x], key="adm_v_m")
             render_feed_activo(df_rutinas, df_seguimiento, sel_a, sel_m, key_suffix="admin_view")
        else: st.warning("Sin datos")

    with tab_seguimiento:
        ids_activos = df_seguimiento['codnadador'].unique()
        df_nad_activos = df_nadadores[df_nadadores['codnadador'].isin(ids_activos)].copy()
        if df_nad_activos.empty:
            st.warning("⚠️ Aún no hay alumnos con registros.")
        else:
            df_nad_activos['NombreCompleto'] = df_nad_activos['apellido'] + ", " + df_nad_activos['nombre']
            lista = df_nad_activos[['codnadador', 'NombreCompleto']].sort_values('NombreCompleto')
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: sel_nad_id = st.selectbox("Alumno", lista['codnadador'], format_func=lambda x: lista[lista['codnadador'] == x]['NombreCompleto'].values[0])
            with c2: sel_a_seg = st.selectbox("Año", v_anios, key="seg_a")
            meses_seg = sorted(df_rutinas[df_rutinas['anio_rutina'] == sel_a_seg]['mes_rutina'].unique().tolist())
            if meses_seg:
                 mapa_seg = {i: obtener_nombre_mes(i) for i in meses_seg}
                 with c3: sel_m_seg = st.selectbox("Mes", meses_seg, format_func=lambda x: mapa_seg[x], key="seg_m")
                 st.markdown(f"**Reporte:** {lista[lista['codnadador']==sel_nad_id]['NombreCompleto'].values[0]}")
                 render_historial_compacto(df_rutinas, df_seguimiento, sel_a_seg, sel_m_seg, sel_nad_id)
            else: st.warning("Sin datos")

# ==========================
# ROL: NADADOR (N)
# ==========================
else:
    tab_curso, tab_hist = st.tabs(["📅 Mes en Curso", "📜 Historial"])
    
    with tab_curso:
        hoy = datetime.now()
        st.markdown(f"### Sesiones de {obtener_nombre_mes(hoy.month)} {hoy.year}")
        render_feed_activo(df_rutinas, df_seguimiento, hoy.year, hoy.month, key_suffix="nad_curso")
        
    with tab_hist:
        c1, c2 = st.columns(2)
        anios_disp = sorted(list(set(df_rutinas['anio_rutina'].unique())), reverse=True)
        if not anios_disp: anios_disp = [datetime.now().year]
        with c1: h_anio = st.selectbox("Año", anios_disp, key="h_a")
        meses_en_anio = sorted(df_rutinas[df_rutinas['anio_rutina'] == h_anio]['mes_rutina'].unique().tolist())
        if meses_en_anio:
            mapa = {i: obtener_nombre_mes(i) for i in meses_en_anio}
            with c2: h_mes = st.selectbox("Mes", meses_en_anio, format_func=lambda x: mapa[x], key="h_m")
            st.divider()
            render_historial_compacto(df_rutinas, df_seguimiento, h_anio, h_mes, mi_id)
        else:
            st.warning("Sin datos para este año.")
