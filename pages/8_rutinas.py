import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import time
import random

# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================
st.set_page_config(page_title="Sesiones de Entrenamiento", layout="centered")

# --- PLANTILLA PARA EL TEST (Modificable) ---
PLANTILLA_TEST = """OBJETIVO: EVALUACIÓN MENSUAL
------------------------------------------------
Ec: 400m (200m crol + 200m estilos)
Act: 5 min fuera del agua
------------------------------------------------
T: TEST DE VELOCIDAD / TOLERANCIA
(Detallar aquí el protocolo específico del mes)
------------------------------------------------
Vuelta a la calma: 200m suaves"""

# --- FUNCIÓN: GLOSARIO DE REFERENCIAS ---
def mostrar_referencias():
    """Muestra el glosario en un desplegable consultivo."""
    with st.expander("📖 Glosario de Referencias y Abreviaturas (Clic para abrir)"):
        st.markdown("""
        | Sigla | Significado | Detalle / Intensidad |
        | :--- | :--- | :--- |
        | **T** | Tolerancia | Intensidad alta 100 – 110% |
        | **VC** | Velocidad Corta | Máxima velocidad |
        | **VS** | Velocidad Sostenida | Mantener velocidad alta |
        | **Prog.**| Progresivo | De menor a mayor |
        | **Reg** | Regresivo | De mayor a menor |
        | **F1** | Vo2 | Intensidad 100% |
        | **F2** | Super Aeróbico | Intensidad 80-90% |
        | **F3** | Sub Aeróbico | Intensidad 70% |
        | **Ec** | Entrada en Calor | Nado suave inicial |
        | **EcT** | Ec Tensor | Bíceps/Tríceps/Dorsales/Hombros/Pecho |
        | **EcM** | Ec Movilidad | Fuera del agua (Brazos/Cintura/Piernas) |
        | **Act** | Activación | Fuera del agua (Piernas/Brazos/Core) |
        | **m** | Metros | Distancia |
        | **p** | Pausa estática | Descanso quieto |
        | **p act**| Pausa Activa | Descanso en movimiento suave |
        | **D/** | Dentro del tiempo | Intervalo fijo |
        | **C/** | Con tiempo | Pausa fija entre repeticiones |
        | **Pat Ph**| Patada Pos. Hidro.| Cuerpo alineado |
        | **B** | Brazada | C: Crol / E: Espalda / P: Pecho / M: Mariposa |
        | **Pat Tabla**| Patada c/ tabla | |
        | **PB** | Pull Brazada | Uso de pullboy (c/e/p/m) |
        | **CT** | Corrección Técnica| Foco en el estilo |
        """)
        st.info("💡 Consulta esta tabla cuando veas una sigla desconocida en tu rutina.")

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
    try: return meses[int(n)]
    except: return "Desconocido"

def actualizar_con_retry(worksheet, data, max_retries=5):
    for i in range(max_retries):
        try:
            conn.update(worksheet=worksheet, data=data)
            return True, None 
        except Exception as e:
            if "429" in str(e) or "quota" in str(e):
                time.sleep((2 ** i) + random.uniform(0, 1))
                continue 
            else: return False, e
    return False, "Tiempo de espera agotado."

@st.cache_data(ttl="10s")
def cargar_datos_rutinas_view():
    try:
        df_rut = conn.read(worksheet="Rutinas").copy()
        df_seg = conn.read(worksheet="Rutinas_Seguimiento").copy()
        df_nad = conn.read(worksheet="Nadadores").copy()
        
        # Normalización
        if not df_rut.empty:
            df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)
        if not df_seg.empty:
            df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
        if not df_nad.empty:
             df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce').fillna(0).astype(int)
        return df_rut, df_seg, df_nad
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def leer_dataset_fresco(worksheet):
    try: return conn.read(worksheet=worksheet, ttl=0).copy()
    except: return None

def guardar_seguimiento(id_rutina, id_nadador):
    df_seg = leer_dataset_fresco("Rutinas_Seguimiento")
    if df_seg is None: return False 
    if not df_seg.empty: df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
    
    if df_seg[(df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador)].empty:
        nuevo = pd.DataFrame([{"id_rutina": id_rutina, "codnadador": id_nadador, "fecha_realizada": (datetime.now()-timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")}])
        exito, _ = actualizar_con_retry("Rutinas_Seguimiento", pd.concat([df_seg, nuevo], ignore_index=True))
        if exito: st.cache_data.clear(); return True
    return False

def borrar_seguimiento(id_rutina, id_nadador):
    df_seg = leer_dataset_fresco("Rutinas_Seguimiento")
    if df_seg is None: return False
    if not df_seg.empty: df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
    
    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry("Rutinas_Seguimiento", df_final)
    if exito: st.cache_data.clear(); return True
    return False

def guardar_sesion_admin(anio, mes, sesion, texto):
    df_rut = leer_dataset_fresco("Rutinas")
    if df_rut is None: return "❌ Error conexión."
    
    # Asegurar tipos
    if not df_rut.empty:
        df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
        df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
        df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)

    # Identificar si es TEST para ajustar el ID (opcional) o dejarlo estándar
    nuevo_id = f"{anio}-{mes:02d}-S{sesion:02d}"
    
    mask = df_rut['id_rutina'] == nuevo_id
    fila = {"id_rutina": nuevo_id, "anio_rutina": int(anio), "mes_rutina": int(mes), "nro_sesion": int(sesion), "texto_rutina": texto}
    
    if df_rut[mask].empty:
        df_rut = pd.concat([df_rut, pd.DataFrame([fila])], ignore_index=True)
        msg = "✅ Sesión creada."
    else:
        df_rut.loc[mask, "texto_rutina"] = texto
        df_rut.loc[mask, "anio_rutina"] = int(anio)
        df_rut.loc[mask, "mes_rutina"] = int(mes)
        df_rut.loc[mask, "nro_sesion"] = int(sesion)
        msg = "✅ Sesión actualizada."
        
    exito, err = actualizar_con_retry("Rutinas", df_rut)
    return msg if exito else f"❌ Error: {err}"

# --- COMPONENTES VISUALES ---

def render_tarjeta_individual(row, df_seg, key_suffix):
    """Muestra el contenido de una sesión con botones de acción."""
    r_id = row['id_rutina']
    r_sesion = row['nro_sesion']
    r_texto = row['texto_rutina']
    
    # Detectar si es TEST para cambiar el título visualmente
    es_test = "TEST" in r_texto.upper() or "TEST" in str(r_id).upper()
    titulo_sesion = f"🧬 EVALUACIÓN / TEST" if es_test else f"Sesión {r_sesion}"
    
    check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == mi_id)]
    esta_realizada = not check.empty
    
    borde = "#2E7D32" if esta_realizada else ("#E30613" if es_test else "#444")
    bg = "#1B2E1B" if esta_realizada else "#262730"
    
    st.markdown(f"""<div style="border: 2px solid {borde}; border-radius: 10px; background-color: {bg}; padding: 15px; margin-bottom: 15px;">""", unsafe_allow_html=True)
    
    # Encabezado
    c1, c2 = st.columns([6, 2])
    with c1:
        st.subheader(titulo_sesion)
        if esta_realizada: 
            st.caption(f"✅ Completada el {pd.to_datetime(check.iloc[0]['fecha_realizada']).strftime('%d/%m')}")
    with c2:
        if esta_realizada:
            if st.button("Deshacer", key=f"un_{r_id}_{key_suffix}"):
                borrar_seguimiento(r_id, mi_id); st.rerun()
        else:
            if st.button("Marcar Lista", key=f"do_{r_id}_{key_suffix}", type="primary"):
                guardar_seguimiento(r_id, mi_id); st.rerun()
    
    st.divider()
    st.code(r_texto, language="text") # Usamos code para mantener formato
    
    # GLOSARIO CONSULTIVO
    mostrar_referencias()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_feed_activo(df_rut, df_seg, anio_ver, mes_ver, key_suffix=""):
    """
    Muestra las sesiones filtradas por mes/año.
    MODIFICADO: Botones lado a lado y TEST al final.
    """
    rutinas_filtradas = df_rut[
        (df_rut['anio_rutina'] == anio_ver) & 
        (df_rut['mes_rutina'] == mes_ver)
    ].copy()

    if rutinas_filtradas.empty:
        st.info("No hay sesiones cargadas para este mes.")
        return

    # --- LÓGICA DE ORDENAMIENTO (TEST AL FINAL) ---
    # Identificamos si es test buscando "TEST" en el texto (o podrías usar el ID/Título si tuvieras columna titulo)
    # Como solo tenemos 'texto_rutina', buscamos ahí.
    rutinas_filtradas['es_test'] = rutinas_filtradas['texto_rutina'].str.upper().str.contains("TEST")
    
    # Ordenamos primero por numero de sesion normal, y mandamos los tests al fondo
    # Truco: Ordenamos por 'es_test' (False=0 va antes, True=1 va despues) y luego por nro_sesion
    rutinas_filtradas.sort_values(by=['es_test', 'nro_sesion'], ascending=[True, True], inplace=True)
    
    # --- SELECTOR DE BOTONES (GRID) ---
    st.write("##### Selecciona una rutina:")
    
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    
    sesion_activa = None
    
    # Si ya seleccionó algo antes, tratamos de mantenerlo (usando session_state si quisieramos persistencia compleja)
    # Aquí usaremos un expander simple o renderizado condicional.
    
    # Usaremos session_state para guardar cuál está expandida
    k_sel = f"selected_session_{key_suffix}"
    if k_sel not in st.session_state: st.session_state[k_sel] = None

    for index, row in rutinas_filtradas.iterrows():
        r_id = row['id_rutina']
        label = "🧬 TEST" if row['es_test'] else f"Sesión {row['nro_sesion']}"
        
        # Check visual si está hecha
        check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == mi_id)]
        icon = "✅" if not check.empty else "📄"
        
        # Botón en Grid
        with cols[index % 3]:
            # Si es la seleccionada, la pintamos diferente (limitación streamlit: button no cambia color facil, pero el estado si)
            if st.button(f"{icon} {label}", key=f"btn_sel_{r_id}", use_container_width=True):
                st.session_state[k_sel] = r_id
    
    # --- MOSTRAR DETALLE DE LA SELECCIONADA ---
    if st.session_state[k_sel]:
        row_sel = rutinas_filtradas[rutinas_filtradas['id_rutina'] == st.session_state[k_sel]]
        if not row_sel.empty:
            st.write("") # Espacio
            render_tarjeta_individual(row_sel.iloc[0], df_seg, key_suffix)
    else:
        st.info("👆 Toca un botón para ver el entrenamiento.")

# --- 5. CARGA DE DATOS ---
df_rutinas, df_seguimiento, df_nadadores = cargar_datos_rutinas_view()

# --- 6. GESTIÓN DE ESTADO ADMIN ---
if rol in ["M", "P"]:
    if "g_anio" not in st.session_state: st.session_state.g_anio = datetime.now().year
    if "g_mes" not in st.session_state: st.session_state.g_mes = datetime.now().month

# --- 7. INTERFAZ PRINCIPAL ---
st.title("📝 Sesiones de Entrenamiento")
st.markdown(f"👤 **Conectado como:** {mi_nombre}")

if df_rutinas is None: st.stop()

st.write("---")

# ==========================
# ROL: ENTRENADOR (M/P)
# ==========================
if rol in ["M", "P"]:
    with st.expander("⚙️ Editor de Sesiones", expanded=False):
        st.markdown("##### Crear / Editar")
        
        # --- BOTÓN DE CARGA RÁPIDA TEST ---
        if st.button("➕ Cargar Plantilla TEST (Autocompletar)", type="secondary"):
            st.session_state.temp_texto = PLANTILLA_TEST
            # Opcional: Forzar número de sesión alto para que quede al final visualmente si se usa orden numérico
            # st.session_state.admin_sesion = 31 
            st.rerun()

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: 
            anio_in = st.number_input("Año", 2024, 2030, st.session_state.g_anio)
        with c2: 
            mes_in = st.number_input("Mes", 1, 12, st.session_state.g_mes)
        with c3: 
            # Calculamos próxima sesión sugerida
            if not df_rutinas.empty:
                filtro = df_rutinas[(df_rutinas['anio_rutina'] == anio_in) & (df_rutinas['mes_rutina'] == mes_in)]
                sug = int(filtro['nro_sesion'].max()) + 1 if not filtro.empty else 1
            else: sug = 1
            ses_in = st.number_input("Nro Sesión", 1, 31, sug)

        # Verificar si existe para cargar texto
        id_gen = f"{anio_in}-{mes_in:02d}-S{ses_in:02d}"
        existente = df_rutinas[df_rutinas['id_rutina'] == id_gen]
        
        txt_val = ""
        if "temp_texto" in st.session_state:
            txt_val = st.session_state.temp_texto
            del st.session_state.temp_texto # Limpiar
        elif not existente.empty:
            txt_val = existente.iloc[0]['texto_rutina']
            st.caption("✏️ Editando sesión existente")
        
        with st.form("editor"):
            texto_final = st.text_area("Contenido", value=txt_val, height=200)
            if st.form_submit_button("💾 Guardar Sesión", use_container_width=True):
                msg = guardar_sesion_admin(anio_in, mes_in, ses_in, texto_final)
                if "Error" not in msg: st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)
    
    st.divider()
    # Vista previa admin
    render_feed_activo(df_rutinas, df_seguimiento, st.session_state.g_anio, st.session_state.g_mes, "admin")

# ==========================
# ROL: NADADOR (N)
# ==========================
else:
    tab1, tab2 = st.tabs(["📅 Rutinas del Mes", "📊 Mi Historial"])
    
    with tab1:
        hoy = datetime.now()
        render_feed_activo(df_rutinas, df_seguimiento, hoy.year, hoy.month, "nadador")
        
    with tab2:
        st.info("Resumen de asistencia (Compacto)")
        # Reutilizamos lógica de historial compacto si existe en tu versión original, 
        # o mostramos lista simple aquí.
        mis_hechas = df_seguimiento[df_seguimiento['codnadador'] == mi_id]
        if not mis_hechas.empty:
            st.dataframe(mis_hechas[['id_rutina', 'fecha_realizada']].sort_values('fecha_realizada', ascending=False), hide_index=True, use_container_width=True)
        else:
            st.write("No tienes sesiones registradas.")
