import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
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
        try:
            df_rut = conn.read(worksheet="Rutinas")
        except:
            df_rut = pd.DataFrame(columns=["id_rutina", "anio_rutina", "mes_rutina", "nro_sesion", "texto_rutina"])
        
        try:
            df_seg = conn.read(worksheet="Rutinas_Seguimiento")
        except:
            df_seg = pd.DataFrame(columns=["id_rutina", "codnadador", "fecha_realizada"])
            
        # Asegurar tipos de datos
        if not df_rut.empty:
            df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)
            
        if not df_seg.empty:
            df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
            
        return df_rut, df_seg
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None, None

def calcular_proxima_sesion(df, anio, mes):
    """Devuelve el número de sesión siguiente al último cargado para ese mes."""
    if df is None or df.empty:
        return 1
    
    filtro = df[(df['anio_rutina'] == anio) & (df['mes_rutina'] == mes)]
    if filtro.empty:
        return 1
    
    max_sesion = filtro['nro_sesion'].max()
    return int(max_sesion) + 1

def guardar_seguimiento(id_rutina, id_nadador):
    df_rut, df_seg = cargar_datos_rutinas()
    existe = df_seg[(df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador)]
    
    if existe.empty:
        nuevo_registro = pd.DataFrame([{
            "id_rutina": id_rutina,
            "codnadador": id_nadador,
            "fecha_realizada": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df_final = pd.concat([df_seg, nuevo_registro], ignore_index=True)
        conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
        st.cache_data.clear()
        return True
    return False

def borrar_seguimiento(id_rutina, id_nadador):
    df_rut, df_seg = cargar_datos_rutinas()
    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
    st.cache_data.clear()
    return True

def guardar_rutina_admin(anio, mes, sesion, texto):
    df_rut, df_seg = cargar_datos_rutinas()
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

# Callback para activar recálculo
def activar_calculo_auto():
    st.session_state.trigger_calculo = True

# --- 5. LOGICA PREVIA AL RENDERIZADO (FIX PARA EL ERROR) ---
df_rutinas, df_seguimiento = cargar_datos_rutinas()

# Inicializar valores de gestión si no existen (Valores por defecto)
if "g_anio" not in st.session_state: st.session_state.g_anio = datetime.now().year
if "g_mes" not in st.session_state: st.session_state.g_mes = datetime.now().month

# Lógica de Autocompletado de Sesión
# Se ejecuta si: 1) Se activó el trigger (por guardar o cambiar mes), o 2) No existe la variable 'admin_sesion'
if st.session_state.get("trigger_calculo", False) or "admin_sesion" not in st.session_state:
    if df_rutinas is not None:
        prox = calcular_proxima_sesion(df_rutinas, st.session_state.g_anio, st.session_state.g_mes)
        st.session_state.admin_sesion = min(prox, 31)
    else:
        st.session_state.admin_sesion = 1
    
    # Apagamos el trigger
    st.session_state.trigger_calculo = False

# --- 6. INTERFAZ ---
st.title("📝 Rutinas de Entrenamiento")

if df_rutinas is None:
    st.stop()

# --- BARRA DE FILTROS SUPERIOR (Para visualización) ---
st.write("---")

# --- SECCIÓN ADMIN (Cargar Rutinas) ---
if rol in ["M", "P"]:
    with st.expander("⚙️ Gestión de Rutinas (Solo Profes)", expanded=False):
        st.markdown("##### Cargar / Editar Rutina")
        
        # 1. CONTROLES DE SELECCIÓN (Con callbacks para auto-actualizar sesión)
        c1, c2, c3 = st.columns([1, 1, 1])
        
        # Datos para los selectores
        anio_actual = datetime.now().year
        anios_gest = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [anio_actual])), reverse=True)
        meses_indices = list(range(1, 13))
        mapa_meses = {i: obtener_nombre_mes(i) for i in meses_indices}

        with c1: 
            # FIX APLICADO: Eliminado argumento 'value=' porque ya existe 'key' en session_state
            st.number_input("Año Gestión", min_value=2020, max_value=2030, key="g_anio", on_change=activar_calculo_auto)
        with c2: 
            # FIX APLICADO: Eliminado argumento 'index=' porque ya existe 'key' en session_state
            st.selectbox("Mes Gestión", meses_indices, format_func=lambda x: mapa_meses[x], key="g_mes", on_change=activar_calculo_auto)
        with c3: 
            # FIX APLICADO: Eliminado 'value='
            st.number_input("Nro Sesión", min_value=1, max_value=31, key="admin_sesion")
            
        # Valores actuales para buscar
        g_anio_val = st.session_state.g_anio
        g_mes_val = st.session_state.g_mes
        g_ses_val = st.session_state.admin_sesion
            
        # 2. LOGICA DE PRECARGA
        id_busqueda = f"{g_anio_val}-{g_mes_val:02d}-S{g_ses_val:02d}"
        texto_previo = ""
        row_existente = df_rutinas[df_rutinas['id_rutina'] == id_busqueda]
        
        msg_estado = "✨ Nueva Rutina"
        if not row_existente.empty:
            texto_previo = row_existente.iloc[0]['texto_rutina']
            msg_estado = "✏️ Editando Existente"
            
        st.caption(f"{msg_estado}: {id_busqueda}")

        # 3. HERRAMIENTAS DE FORMATO (RICH TEXT HELPER)
        with st.expander("🛠️ Herramientas de Formato (Negrita, Listas, etc.)"):
            st.markdown("""
            <small>Utilice estos códigos en el texto para dar formato:</small>
            
            | Estilo | Código a escribir | Resultado visual |
            | :--- | :--- | :--- |
            | **Negrita** | `**Texto**` | **Texto** |
            | *Cursiva* | `*Texto*` | *Texto* |
            | Título | `### Título` | <h3>Título</h3> |
            | Lista | `- Item` | <ul><li>Item</li></ul> |
            | Separador | `---` | Línea horizontal |
            """, unsafe_allow_html=True)

        # 4. FORMULARIO
        with st.form("form_rutina"):
            f_texto = st.text_area("Detalle del Entrenamiento", value=texto_previo, height=200, key=f"txt_{id_busqueda}", placeholder="Escriba aquí la rutina...")
            
            btn_guardar = st.form_submit_button("Guardar Rutina")
            
            if btn_guardar:
                if f_texto.strip() == "":
                    st.error("El texto de la rutina no puede estar vacío.")
                else:
                    res = guardar_rutina_admin(g_anio_val, g_mes_val, g_ses_val, f_texto)
                    st.success(res)
                    
                    # Activamos el trigger para que en la próxima recarga calcule la siguiente sesión
                    st.session_state.trigger_calculo = True
                    time.sleep(1)
                    st.rerun()

st.divider()

# --- SECCIÓN VISUALIZACIÓN (Feed) ---
st.markdown("#### 📅 Explorar Rutinas")
col_f1, col_f2 = st.columns(2)
with col_f1:
    v_anios = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [datetime.now().year])), reverse=True)
    st.selectbox("Año", v_anios, index=0, key="view_anio")

with col_f2:
    v_mes_actual = datetime.now().month
    st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], index=meses_indices.index(v_mes_actual), key="view_mes")

# 1. Filtrar rutinas del mes seleccionado
rutinas_filtradas = df_rutinas[
    (df_rutinas['anio_rutina'] == st.session_state.view_anio) & 
    (df_rutinas['mes_rutina'] == st.session_state.view_mes)
].copy()

# 2. Ordenar por número de sesión
rutinas_filtradas.sort_values(by='nro_sesion', ascending=True, inplace=True)

if rutinas_filtradas.empty:
    st.info(f"No hay rutinas cargadas para {obtener_nombre_mes(st.session_state.view_mes)} {st.session_state.view_anio}.")
else:
    for index, row in rutinas_filtradas.iterrows():
        r_id = row['id_rutina']
        r_sesion = row['nro_sesion']
        r_texto = row['texto_rutina']
        
        # Verificar estado
        check = df_seguimiento[
            (df_seguimiento['id_rutina'] == r_id) & 
            (df_seguimiento['codnadador'] == mi_id)
        ]
        esta_realizada = not check.empty
        fecha_realizacion = ""
        if esta_realizada:
            fecha_obj = pd.to_datetime(check.iloc[0]['fecha_realizada'])
            fecha_realizacion = fecha_obj.strftime("%d/%m")

        # --- TARJETA VISUAL ---
        borde_color = "#2E7D32" if esta_realizada else "#444" 
        bg_color = "#1B2E1B" if esta_realizada else "#262730"
        
        container = st.container()
        container.markdown(f"""
        <div style="
            border: 2px solid {borde_color};
            border-radius: 10px;
            background-color: {bg_color};
            padding: 15px;
            margin-bottom: 15px;
        ">
        """, unsafe_allow_html=True)
        
        with container:
            c_header, c_action = st.columns([3, 1])
            
            with c_header:
                if esta_realizada:
                    st.markdown(f"#### ✅ Sesión {r_sesion} <span style='font-size:14px; color:#888'>({fecha_realizacion})</span>", unsafe_allow_html=True)
                    # Renderizamos el texto como Markdown pero tachado visualmente si está hecha
                    st.markdown(f"<div style='text-decoration: line-through; color: #aaa;'>", unsafe_allow_html=True)
                    st.markdown(r_texto)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"#### ⭕ Sesión {r_sesion}")
                    # Renderizado Markdown normal para ver negritas, listas, etc.
                    st.markdown(r_texto)
            
            with c_action:
                st.write("") 
                if esta_realizada:
                    if st.button("Desmarcar", key=f"undo_{r_id}", help="Marcar como no realizada"):
                        borrar_seguimiento(r_id, mi_id)
                        st.rerun()
                else:
                    if st.button("Completar", key=f"do_{r_id}", type="primary"):
                        guardar_seguimiento(r_id, mi_id)
                        st.rerun()
        
        container.markdown("</div>", unsafe_allow_html=True)
