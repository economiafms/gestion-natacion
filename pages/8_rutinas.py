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
        # Intentamos leer las hojas. Si no existen, devolvemos DataFrames vacíos con la estructura correcta
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

def guardar_seguimiento(id_rutina, id_nadador):
    df_rut, df_seg = cargar_datos_rutinas()
    
    # Verificar si ya existe
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
    
    # Filtrar para excluir el registro
    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    
    conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
    st.cache_data.clear()
    return True

def guardar_rutina_admin(anio, mes, sesion, texto):
    df_rut, df_seg = cargar_datos_rutinas()
    
    # Generar ID
    nuevo_id = f"{anio}-{mes:02d}-S{sesion:02d}"
    
    # Verificar si ya existe para sobrescribir
    mask = df_rut['id_rutina'] == nuevo_id
    
    nueva_fila = {
        "id_rutina": nuevo_id,
        "anio_rutina": int(anio),
        "mes_rutina": int(mes),
        "nro_sesion": int(sesion),
        "texto_rutina": texto
    }
    
    if df_rut[mask].empty:
        # Nuevo
        df_rut = pd.concat([df_rut, pd.DataFrame([nueva_fila])], ignore_index=True)
        msg = "Rutina creada correctamente."
    else:
        # Actualizar existente
        df_rut.loc[mask, "texto_rutina"] = texto
        df_rut.loc[mask, "anio_rutina"] = int(anio)
        df_rut.loc[mask, "mes_rutina"] = int(mes)
        df_rut.loc[mask, "nro_sesion"] = int(sesion)
        msg = "Rutina actualizada correctamente."
        
    conn.update(worksheet="Rutinas", data=df_rut)
    st.cache_data.clear()
    return msg

# --- 5. INTERFAZ ---
st.title("📝 Rutinas de Entrenamiento")

# Carga de datos
df_rutinas, df_seguimiento = cargar_datos_rutinas()

if df_rutinas is None:
    st.stop()

# --- BARRA DE FILTROS ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    anio_actual = datetime.now().year
    anios_disponibles = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [anio_actual])), reverse=True)
    sel_anio = st.selectbox("Año", anios_disponibles, index=0)

with col_f2:
    mes_actual = datetime.now().month
    meses_indices = list(range(1, 13))
    # Mapear nombres para el selectbox
    mapa_meses = {i: obtener_nombre_mes(i) for i in meses_indices}
    sel_mes = st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], index=meses_indices.index(mes_actual))

st.divider()

# --- SECCIÓN ADMIN (Cargar Rutinas) ---
if rol in ["M", "P"]:
    with st.expander("⚙️ Gestión de Rutinas (Solo Profes)", expanded=False):
        st.markdown("##### Cargar / Editar Rutina")
        
        # Formulario
        with st.form("form_rutina"):
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1: f_anio = st.number_input("Año", value=sel_anio, min_value=2020, max_value=2030)
            with c2: f_mes = st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], index=meses_indices.index(sel_mes))
            # CAMBIO: Agregado key 'ui_sesion' para controlarlo programáticamente
            with c3: f_sesion = st.number_input("Nro Sesión", min_value=1, max_value=31, value=1, key="ui_sesion")
            
            # Buscar si ya existe texto para precargar
            id_busqueda = f"{f_anio}-{f_mes:02d}-S{f_sesion:02d}"
            texto_previo = ""
            row_existente = df_rutinas[df_rutinas['id_rutina'] == id_busqueda]
            if not row_existente.empty:
                texto_previo = row_existente.iloc[0]['texto_rutina']
                st.info(f"Editando rutina existente: {id_busqueda}")
            
            # CAMBIO: Key dinámica basada en sesión para forzar limpieza/recarga
            f_texto = st.text_area("Detalle del Entrenamiento", value=texto_previo, height=200, key=f"txt_rut_{f_anio}_{f_mes}_{f_sesion}")
            
            btn_guardar = st.form_submit_button("Guardar Rutina")
            
            if btn_guardar:
                if f_texto.strip() == "":
                    st.error("El texto de la rutina no puede estar vacío.")
                else:
                    res = guardar_rutina_admin(f_anio, f_mes, f_sesion, f_texto)
                    st.success(res)
                    
                    # CAMBIO: Auto-incrementar sesión si es menor a 31 para agilizar carga
                    if st.session_state.ui_sesion < 31:
                        st.session_state.ui_sesion += 1
                        
                    time.sleep(1)
                    st.rerun()

# --- SECCIÓN VISUALIZACIÓN (Feed) ---

# 1. Filtrar rutinas del mes seleccionado
rutinas_filtradas = df_rutinas[
    (df_rutinas['anio_rutina'] == sel_anio) & 
    (df_rutinas['mes_rutina'] == sel_mes)
].copy()

# 2. Ordenar por número de sesión
rutinas_filtradas.sort_values(by='nro_sesion', ascending=True, inplace=True)

if rutinas_filtradas.empty:
    st.info(f"No hay rutinas cargadas para {obtener_nombre_mes(sel_mes)} {sel_anio}.")
else:
    st.markdown(f"### {obtener_nombre_mes(sel_mes)} {sel_anio}")
    
    for index, row in rutinas_filtradas.iterrows():
        r_id = row['id_rutina']
        r_sesion = row['nro_sesion']
        r_texto = row['texto_rutina']
        
        # Verificar estado (Individual por usuario)
        # Filtramos el DF de seguimiento para este usuario y esta rutina
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
        # Definir estilos según estado
        borde_color = "#2E7D32" if esta_realizada else "#444" # Verde si ok, gris si no
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
                    st.markdown(f"<div style='text-decoration: line-through; color: #aaa;'>{r_texto}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"#### ⭕ Sesión {r_sesion}")
                    st.write(r_texto)
            
            with c_action:
                st.write("") # Espaciador vertical
                if esta_realizada:
                    if st.button("Desmarcar", key=f"undo_{r_id}", help="Marcar como no realizada"):
                        borrar_seguimiento(r_id, mi_id)
                        st.rerun()
                else:
                    if st.button("Completar", key=f"do_{r_id}", type="primary"):
                        guardar_seguimiento(r_id, mi_id)
                        st.rerun()
        
        container.markdown("</div>", unsafe_allow_html=True)
