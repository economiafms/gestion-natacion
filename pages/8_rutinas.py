import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import time
import random

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Sesiones de Entrenamiento", layout="centered")

# --- FUNCIÓN NUEVA: GLOSARIO CONSULTIVO ---
def mostrar_referencias():
    """Desplegable que no interrumpe la visual, solo se abre si se consulta."""
    with st.expander("📖 Ver Referencias y Abreviaturas (Ayuda)"):
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
        | **EcT** | Ec Tensor | Bíceps / Tríceps / Dorsales / Hombros... |
        | **EcM** | Ec Movilidad | Fuera del agua (Articulaciones) |
        | **Act** | Activación | Fuera del agua (Piernas / Core) |
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
        st.info("ℹ️ Estas referencias te ayudarán a interpretar la intensidad y técnica.")

# --- 2. SEGURIDAD Y CONEXIÓN ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. FUNCIONES DE DATOS ---
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
        # Normalización básica
        if not df_rut.empty:
            df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)
        if not df_seg.empty:
            df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
        return df_rut, df_seg
    except: return pd.DataFrame(), pd.DataFrame()

def guardar_seguimiento(id_rutina, id_nadador):
    df_seg = conn.read(worksheet="Rutinas_Seguimiento", ttl=0).copy()
    if not df_seg.empty: df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
    
    if df_seg[(df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador)].empty:
        nuevo = pd.DataFrame([{"id_rutina": id_rutina, "codnadador": id_nadador, "fecha_realizada": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
        exito, _ = actualizar_con_retry("Rutinas_Seguimiento", pd.concat([df_seg, nuevo], ignore_index=True))
        if exito: st.cache_data.clear(); return True
    return False

def borrar_seguimiento(id_rutina, id_nadador):
    df_seg = conn.read(worksheet="Rutinas_Seguimiento", ttl=0).copy()
    if not df_seg.empty: df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)
    
    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry("Rutinas_Seguimiento", df_final)
    if exito: st.cache_data.clear(); return True
    return False

# --- 4. COMPONENTES VISUALES ---
def render_tarjeta_individual(row, df_seg):
    r_id = row['id_rutina']
    r_sesion = row['nro_sesion']
    r_texto = row['texto_rutina']
    
    check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == mi_id)]
    esta_realizada = not check.empty
    
    borde = "#2E7D32" if esta_realizada else "#444"
    bg = "#1B2E1B" if esta_realizada else "#262730"
    
    # Contenedor visual
    st.markdown(f"""<div style="border: 2px solid {borde}; border-radius: 10px; background-color: {bg}; padding: 15px; margin-bottom: 15px;">""", unsafe_allow_html=True)
    
    c1, c2 = st.columns([6, 2])
    with c1:
        st.subheader(f"Sesión {r_sesion}")
        if esta_realizada: st.caption("✅ Completada")
    with c2:
        if esta_realizada:
            if st.button("Deshacer", key=f"un_{r_id}"):
                borrar_seguimiento(r_id, mi_id); st.rerun()
        else:
            if st.button("Listo", key=f"do_{r_id}", type="primary"):
                guardar_seguimiento(r_id, mi_id); st.rerun()
    
    st.divider()
    # Mostramos el entrenamiento
    st.code(r_texto, language="text")
    
    # === AQUÍ AGREGAMOS LAS REFERENCIAS ===
    mostrar_referencias()
    # ======================================
    
    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. INTERFAZ PRINCIPAL ---
df_rutinas, df_seguimiento = cargar_datos_rutinas_view()

st.title("📝 Sesiones de Entrenamiento")
st.markdown(f"👤 **Conectado como:** {mi_nombre}")

if df_rutinas.empty:
    st.info("No hay rutinas cargadas o error de conexión.")
    st.stop()

# Filtro simple por mes actual (puedes ajustar esto según tu lógica de agenda)
hoy = datetime.now()
rutinas_mes = df_rutinas[(df_rutinas['anio_rutina'] == hoy.year) & (df_rutinas['mes_rutina'] == hoy.month)]

if rutinas_mes.empty:
    st.warning(f"No hay sesiones para {hoy.strftime('%B %Y')}.")
else:
    for index, row in rutinas_mes.iterrows():
        render_tarjeta_individual(row, df_seguimiento)

# --- Vista Admin Simplificada (Opcional, si usas este archivo para editar) ---
if rol in ["M", "P"]:
    st.divider()
    with st.expander("🛠️ Admin: Cargar Nueva Sesión"):
        st.write("Funcionalidad de carga rápida...")
        # Aquí iría tu formulario de carga si lo tienes en este mismo archivo
