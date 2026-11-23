import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import random
import uuid
import io

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agenda de Competencias", layout="centered")

# ==========================================
# 2. SEGURIDAD Y SESIÓN
# ==========================================
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

if "active_usr_tab" not in st.session_state: st.session_state.active_usr_tab = None
if "active_coach_tab" not in st.session_state: st.session_state.active_coach_tab = None

# ==========================================
# 3. CONEXIÓN Y DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

LISTA_PRUEBAS = [
    "50m Libre", "100m Libre", "200m Libre", "400m Libre", "800m Libre", "1500m Libre",
    "50m Espalda", "100m Espalda", "200m Espalda",
    "50m Pecho", "100m Pecho", "200m Pecho",
    "50m Mariposa", "100m Mariposa", "200m Mariposa",
    "100m Combinado", "200m Combinado", "400m Combinado",
    "Posta 4x50 Libre", "Posta 4x50 Combinada", "Posta 4x100 Libre"
]

# ==========================================
# 4. FUNCIONES AUXILIARES
# ==========================================

def actualizar_con_retry(worksheet, data, max_retries=5):
    """Manejo robusto de la API con reintentos para guardar."""
    for i in range(max_retries):
        try:
            conn.update(worksheet=worksheet, data=data)
            return True, None 
        except Exception as e:
            if "429" in str(e) or "quota" in str(e):
                import time
                time.sleep((2 ** i) + random.uniform(0, 1))
                continue 
            else:
                return False, e
    return False, "Tiempo de espera agotado."

def leer_dataset_fresco(worksheet, max_retries=5):
    """Manejo robusto de la API con reintentos para leer."""
    for i in range(max_retries):
        try: 
            return conn.read(worksheet=worksheet, ttl=0).copy()
        except Exception as e: 
            if "429" in str(e) or "quota" in str(e):
                import time
                time.sleep((2 ** i) + random.uniform(0, 1))
                continue
            else:
                return None
    return None

def calcular_categoria_master(anio_nac):
    """Calcula la categoría Master completa."""
    if pd.isna(anio_nac) or anio_nac == "": return "-"
    try:
        edad = datetime.now().year - int(anio_nac)
        if edad < 20: return "Juvenil"
        elif 20 <= edad <= 24: return "Pre-Master"
        elif 25 <= edad <= 29: return "Master A"
        elif 30 <= edad <= 34: return "Master B"
        elif 35 <= edad <= 39: return "Master C"
        elif 40 <= edad <= 44: return "Master D"
        elif 45 <= edad <= 49: return "Master E"
        elif 50 <= edad <= 54: return "Master F"
        elif 55 <= edad <= 59: return "Master G"
        elif 60 <= edad <= 64: return "Master H"
        elif 65 <= edad <= 69: return "Master I"
        elif 70 <= edad <= 74: return "Master J"
        elif 75 <= edad <= 79: return "Master K"
        else: return "Master K+"
    except: return "-"

def tiempo_a_seg(t_str):
    """Convierte string de tiempo a segundos para buscar el menor (mejor tiempo)"""
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 9999.0

@st.cache_data(ttl="5s")
def cargar_datos_agenda():
    """Carga todas las tablas necesarias."""
    try:
        try:
            df_comp = conn.read(worksheet="Competencias").copy()
            if not df_comp.empty:
                if 'fecha_evento' in df_comp.columns: df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento']).dt.date
                if 'fecha_limite' in df_comp.columns: df_comp['fecha_limite'] = pd.to_datetime(df_comp['fecha_limite']).dt.date
                if 'pruebas_habilitadas' not in df_comp.columns: df_comp['pruebas_habilitadas'] = ""
                if 'max_pruebas' not in df_comp.columns: df_comp['max_pruebas'] = 10
        except:
            df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion", "pruebas_habilitadas", "max_pruebas"])

        try:
            df_ins = conn.read(worksheet="Inscripciones").copy()
            if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
        except:
            df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])

        try:
            df_nad = conn.read(worksheet="Nadadores").copy()
            df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce').fillna(0).astype(int)
            df_nad['fechanac'] = pd.to_datetime(df_nad['fechanac'], errors='coerce')
        except:
            df_nad = pd.DataFrame(columns=["codnadador", "nombre", "apellido", "fechanac", "codgenero"])

        try: df_pil = conn.read(worksheet="Piletas").copy()
        except: df_pil = pd.DataFrame(columns=["codpileta", "club", "medida", "ubicacion"])

        try: df_tiempos = conn.read(worksheet="Tiempos").copy()
        except: df_tiempos = pd.DataFrame()
        
        try: df_estilos = conn.read(worksheet="Estilos").copy()
        except: df_estilos = pd.DataFrame()
        
        try: df_dist = conn.read(worksheet="Distancias").copy()
        except: df_dist = pd.DataFrame()

        return df_comp, df_ins, df_nad, df_pil, df_tiempos, df_estilos, df_dist
    except: return None, None, None, None, None, None, None

def buscar_mejor_tiempo(prueba, df_t_nadador):
    if df_t_nadador.empty: return ""
    p_lower = prueba.lower()
    
    dist_k = ""
    if "50m" in p_lower or " 50" in p_lower: dist_k = "50"
    if "100m" in p_lower or " 100" in p_lower: dist_k = "100"
    if "200m" in p_lower or " 200" in p_lower: dist_k = "200"
    if "400m" in p_lower or " 400" in p_lower: dist_k = "400"
    if "800m" in p_lower or " 800" in p_lower: dist_k = "800"
    if "1500m" in p_lower or " 1500" in p_lower: dist_k = "1500"
    if "4x50" in p_lower: dist_k = "4x50"
    if "4x100" in p_lower: dist_k = "4x100"
    
    est_k = []
    if "libre" in p_lower or "crol" in p_lower: est_k = ["libre", "crol"]
    elif "espalda" in p_lower: est_k = ["espalda"]
    elif "pecho" in p_lower: est_k = ["pecho"]
    elif "mariposa" in p_lower: est_k = ["mariposa"]
    elif "combinado" in p_lower or "medley" in p_lower: est_k = ["combinado", "medley"]
    
    if not dist_k or not est_k: return ""
    
    try:
        mask_dist = df_t_nadador['dist_desc'].str.lower().str.contains(dist_k, na=False)
        mask_est = df_t_nadador['estilo_desc'].str.lower().apply(lambda x: any(k in str(x) for k in est_k))
        
        matches = df_t_nadador[mask_dist & mask_est]
        if not matches.empty:
            best = matches.loc[matches['segundos'].idxmin()]
            return best['tiempo']
    except:
        return ""
    return ""

def set_flash_message(mensaje, tipo="success"):
    st.session_state.flash_msg = {"texto": mensaje, "tipo": tipo}

# ==========================================
# 5. FUNCIONES CRUD (USANDO CALLBACKS)
# ==========================================
def guardar_competencia(id_comp, nombre, fecha_ev, hora, cod_pil, fecha_lim, costo, desc, lista_pruebas_hab, max_pru=10):
    df_comp = leer_dataset_fresco("Competencias")
    
    # ⚠️ BLOQUEO DE SEGURIDAD
    if df_comp is None: 
        return False, "⚠️ Error de red al leer la base de datos. Operación cancelada para proteger el historial."
    
    if df_comp.empty: 
        df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion", "pruebas_habilitadas", "max_pruebas"])
    
    if 'pruebas_habilitadas' not in df_comp.columns: df_comp['pruebas_habilitadas'] = ""
    if 'max_pruebas' not in df_comp.columns: df_comp['max_pruebas'] = 10

    str_pruebas = ", ".join(lista_pruebas_hab) if lista_pruebas_hab else ""
    nuevo = {
        "id_competencia": id_comp if id_comp else str(uuid.uuid4()),
        "nombre_evento": nombre,
        "fecha_evento": str(fecha_ev),
        "hora_inicio": str(hora),
        "cod_pileta": cod_pil,
        "fecha_limite": str(fecha_lim),
        "costo": costo,
        "descripcion": desc,
        "pruebas_habilitadas": str_pruebas,
        "max_pruebas": int(max_pru)
    }

    if id_comp and not df_comp.empty and id_comp in df_comp['id_competencia'].values:
        idx = df_comp.index[df_comp['id_competencia'] == id_comp].tolist()[0]
        for k, v in nuevo.items(): df_comp.at[idx, k] = v
        msg = "✅ Evento actualizado correctamente."
    else:
        df_comp = pd.concat([df_comp, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "✅ Evento creado exitosamente."

    exito, _ = actualizar_con_retry("Competencias", df_comp)
    if exito: st.cache_data.clear(); return True, msg
    return False, "Error al guardar."

def eliminar_competencia(id_comp):
    df_comp = leer_dataset_fresco("Competencias")
    df_ins = leer_dataset_fresco("Inscripciones")
    
    # ⚠️ BLOQUEO DE SEGURIDAD
    if df_comp is None or df_ins is None: 
        return False, "⚠️ Error al leer historial. Operación cancelada."
    
    df_comp = df_comp[df_comp['id_competencia'] != id_comp]
    if not df_ins.empty:
        df_ins = df_ins[df_ins['id_competencia'] != id_comp]
        actualizar_con_retry("Inscripciones", df_ins)
    
    exito, _ = actualizar_con_retry("Competencias", df_comp)
    if exito: st.cache_data.clear(); return True, "Eliminado."
    return False, "Error."

def gestionar_inscripcion(id_comp, id_nadador, lista_pruebas):
    df_ins = leer_dataset_fresco("Inscripciones")
    
    # ⚠️ BLOQUEO DE SEGURIDAD
    if df_ins is None: 
        return False, "⚠️ Error de lectura de red. Operación cancelada para evitar sobreescribir el historial."
    
    if df_ins.empty: 
        df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])
    
    df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)

    pruebas_str = ", ".join(lista_pruebas)
    mask = (df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador)
    
    if not df_ins[mask].empty:
        df_ins.loc[mask, 'pruebas'] = pruebas_str
        df_ins.loc[mask, 'fecha_inscripcion'] = datetime.now().strftime("%Y-%m-%d")
        msg = "✏️ Inscripción modificada."
    else:
        nuevo = {"id_inscripcion": str(uuid.uuid4()), "id_competencia": id_comp, "codnadador": int(id_nadador), "pruebas": pruebas_str, "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d")}
        df_ins = pd.concat([df_ins, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "✅ Inscripción confirmada."
        
    exito, _ = actualizar_con_retry("Inscripciones", df_ins)
    if exito: st.cache_data.clear(); return True, msg
    return False, "Error al procesar inscripción."

def eliminar_inscripcion(id_comp, id_nadador):
    df_ins = leer_dataset_fresco("Inscripciones")
    
    # ⚠️ BLOQUEO DE SEGURIDAD
    if df_ins is None: 
        return False, "⚠️ Error de red. Operación cancelada."
    
    if not df_ins.empty: 
        df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
    
    df_ins = df_ins[~((df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry("Inscripciones", df_ins)
    if exito: st.cache_data.clear(); return True, "Baja exitosa."
    return False, "Error."

# --- LOGICA DE CALLBACKS PARA ESTABILIDAD DE PANTALLA ---
def cb_crear_evento():
    n = st.session_state.f_cr_nom
    p = st.session_state.f_cr_sede
    f = st.session_state.f_cr_fec
    h = st.session_state.f_cr_hor
    c = st.session_state.f_cr_cie
    cost = st.session_state.f_cr_cost
    hab = st.session_state.f_cr_pru
    m = st.session_state.f_cr_max
    d = st.session_state.f_cr_desc
    if n and p:
        ok, msg = guardar_competencia(None, n, f, h, p, c, cost, d, hab, m)
        if ok: set_flash_message(msg, "success")
        else: set_flash_message(msg, "error")
    else:
        set_flash_message("Faltan datos obligatorios.", "warning")

def cb_guardar_usr(c_id):
    st.session_state.active_usr_tab = c_id
    sel = st.session_state[f"usr_pru_{c_id}"]
    if not sel:
        set_flash_message("Selecciona al menos una prueba.", "error")
    else:
        ok, m = gestionar_inscripcion(c_id, mi_id, sel)
        if ok: set_flash_message(m, "success")
        else: set_flash_message(m, "error")

def cb_baja_usr(c_id):
    st.session_state.active_usr_tab = c_id
    ok, m = eliminar_inscripcion(c_id, mi_id)
    if ok: set_flash_message("Inscripción cancelada.", "warning")

def cb_baja_grid(c_id, n_id, nom):
    st.session_state.active_coach_tab = c_id
    ok, m = eliminar_inscripcion(c_id, n_id)
    if ok: set_flash_message(f"Inscripción de {nom} eliminada.", "warning")

def cb_alta_adm(c_id, k_nad, k_pru):
    st.session_state.active_coach_tab = c_id
    nad = st.session_state[k_nad]
    pru = st.session_state.get(k_pru, [])
    if not pru:
        set_flash_message("Selecciona al menos una prueba.", "error")
    else:
        ok, m = gestionar_inscripcion(c_id, nad, pru)
        if ok: set_flash_message("Inscripción registrada por el entrenador.", "success")
        else: set_flash_message(m, "error")

def cb_editar_evento(c_id, h_in, p_in):
    st.session_state.active_coach_tab = c_id
    nn = st.session_state[f"ed_nom_{c_id}"]
    nc = st.session_state[f"ed_cost_{c_id}"]
    nf = st.session_state[f"ed_fec_{c_id}"]
    nl = st.session_state[f"ed_cie_{c_id}"]
    nh = st.session_state[f"ed_hab_{c_id}"]
    nm = st.session_state[f"ed_max_{c_id}"]
    nd = st.session_state[f"ed_desc_{c_id}"]
    ok, m = guardar_competencia(c_id, nn, nf, h_in, p_in, nl, nc, nd, nh, nm)
    if ok: set_flash_message("Evento actualizado correctamente.", "success")
    else: set_flash_message(m, "error")

def cb_elim_evento(c_id):
    st.session_state.active_coach_tab = None
    ok, m = eliminar_competencia(c_id)
    if ok: set_flash_message("Evento eliminado.", "warning")

def cb_nadador_change(c_id):
    """Mantiene la pestaña de entrenador abierta al seleccionar a otro nadador"""
    st.session_state.active_coach_tab = c_id

def cb_set_sort(c_id, col):
    """Maneja el ordenamiento de la grilla de nadadores"""
    st.session_state.active_coach_tab = c_id
    c_key = f"sort_c_{c_id}"
    a_key = f"sort_a_{c_id}"
    if st.session_state.get(c_key) == col:
        st.session_state[a_key] = not st.session_state.get(a_key, True)
    else:
        st.session_state[c_key] = col
        st.session_state[a_key] = True

# ==========================================
# 6. UI PRINCIPAL
# ==========================================

df_competencias, df_inscripciones, df_nadadores, df_piletas, df_tiempos, df_estilos, df_distancias = cargar_datos_agenda()

mi_cat_actual = "-"
mi_genero = ""
if df_nadadores is not None and not df_nadadores.empty:
    mi_row = df_nadadores[df_nadadores['codnadador'] == mi_id]
    if not mi_row.empty:
        mi_anio = pd.to_datetime(mi_row.iloc[0]['fechanac']).year
        mi_cat_actual = calcular_categoria_master(mi_anio)
        mi_genero = str(mi_row.iloc[0]['codgenero']).strip().upper()

df_t_global = pd.DataFrame()
if df_tiempos is not None and not df_tiempos.empty:
    df_t_global = df_tiempos.copy()
    if not df_estilos.empty:
        df_t_global = df_t_global.merge(df_estilos.rename(columns={'descripcion': 'estilo_desc'}), on='codestilo', how='left')
    if not df_distancias.empty:
        df_t_global = df_t_global.merge(df_distancias.rename(columns={'descripcion': 'dist_desc'}), on='coddistancia', how='left')
        
    df_t_global['segundos'] = df_t_global['tiempo'].apply(lambda x: tiempo_a_seg(x) if pd.notnull(x) else 9999.0)
    df_t_global['codnadador'] = pd.to_numeric(df_t_global['codnadador'], errors='coerce').fillna(0).astype(int)

from nob_ui import hero
import html as _html
hero("Agenda de Torneos", "📅")

ES_MANAGER = rol in ["M", "P"]
MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def esc(x):
    if x is None:
        return ""
    s_ = str(x)
    return "" if s_ == "nan" else _html.escape(s_)


st.markdown("""
<style>
/* ---------- Carrete de eventos ---------- */
.st-key-ag_reel {
    flex-wrap: nowrap !important; overflow-x: auto; overflow-y: hidden; gap: 10px !important;
    padding: 4px 2px 10px; scroll-snap-type: x proximity; scrollbar-width: thin;
}
.st-key-ag_reel > div { flex: 0 0 auto !important; width: auto !important; }
[class*="st-key-agc_"] { position: relative; width: 138px !important; min-width: 138px; max-width: 138px; overflow: hidden;
    scroll-snap-align: start; gap: 0 !important; border-radius: 16px; }
[class*="st-key-agc_"] > [data-testid="stElementContainer"]:has(button) {
    position: absolute !important; inset: 0; width: 100% !important; z-index: 2; margin: 0 !important;
}
[class*="st-key-agc_"] [data-testid="stButton"], [class*="st-key-agc_"] button {
    width: 100% !important; height: 100% !important; min-height: 100% !important;
}
[class*="st-key-agc_"] button { opacity: 0 !important; cursor: pointer; }
.ag-card {
    height: 150px; box-sizing: border-box; border-radius: 16px; padding: 10px 10px 8px;
    background: linear-gradient(160deg, #1d1d24, #121216); border: 1px solid rgba(255,255,255,0.10);
    display: flex; flex-direction: column; position: relative; transition: border-color .15s;
}
[class*="st-key-agc_"]:hover .ag-card { border-color: rgba(227,6,19,0.55); }
.ag-card.sel { border: 2px solid #E30613; box-shadow: 0 6px 18px rgba(227,6,19,0.30); background: linear-gradient(160deg, #2a0a0d, #141014); }
.ag-card.pasado { opacity: .62; }
.ag-card.pasado.sel { opacity: 1; }
.ag-card .d { font-size: 32px; font-weight: 900; line-height: 1; color: #fff; }
.ag-card .m { font-size: 13px; font-weight: 800; letter-spacing: 1px; color: #FF6A72; margin-top: 2px; }
.ag-card .n { font-size: 14px; font-weight: 700; color: #fff; margin-top: 8px; line-height: 1.25;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ag-card .pill { margin-top: auto; align-self: flex-start; font-size: 12px; font-weight: 800; padding: 3px 10px; border-radius: 999px; }
.ag-card .yo { position: absolute; top: 8px; right: 9px; font-size: 16px; }
.pill.abierta { background: rgba(76,175,80,0.16); color: #7EE083; border: 1px solid rgba(76,175,80,0.45); }
.pill.cerrada { background: rgba(255,193,7,0.14); color: #FFD54F; border: 1px solid rgba(255,193,7,0.45); }
.pill.fin { background: rgba(255,255,255,0.08); color: #bbb; border: 1px solid rgba(255,255,255,0.18); }
.ag-card.nuevo { align-items: center; justify-content: center; border: 2px dashed rgba(227,6,19,0.55); background: rgba(227,6,19,0.06); }
.ag-card.nuevo .plus { font-size: 40px; font-weight: 300; color: #FF6A72; line-height: 1; }
.ag-card.nuevo .t { font-size: 14px; font-weight: 800; color: #eee; margin-top: 6px; }
.ag-sep { height: 150px; display: flex; align-items: center; justify-content: center; writing-mode: vertical-rl; transform: rotate(180deg);
    font-size: 10px; font-weight: 800; letter-spacing: 2px; color: #888; border-right: 1px solid rgba(255,255,255,0.15); padding-right: 6px; }

/* ---------- Detalle del evento ---------- */
.ag-head { display: flex; gap: 14px; align-items: center; margin: 4px 0 12px; }
.ag-date { flex: 0 0 64px; height: 70px; border-radius: 14px; background: #E30613; color: #fff; display: flex; flex-direction: column;
    align-items: center; justify-content: center; box-shadow: 0 6px 16px rgba(227,6,19,0.35); }
.ag-date b { font-size: 28px; line-height: 1; font-weight: 900; }
.ag-date span { font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.ag-title { font-size: 21px; font-weight: 900; color: #fff; line-height: 1.15; }
.ag-sub { font-size: 13px; color: #bbb; margin-top: 4px; }
.ag-head .pill { display: inline-block; margin-top: 6px; font-size: 11px; font-weight: 800; padding: 2px 10px; border-radius: 999px; }
.ag-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }
.ag-tile { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 8px 10px; min-width: 0; }
.ag-tile small { display: block; font-size: 11px; font-weight: 700; letter-spacing: .6px; text-transform: uppercase; color: #999; }
.ag-tile b { display: block; font-size: 15px; color: #fff; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ag-tile i { display: block; font-style: normal; font-size: 12px; color: #aaa; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ag-tile.alerta b { color: #FFD54F; }
.ag-desc { font-size: 13px; color: #ccc; background: rgba(255,255,255,0.03); border-left: 3px solid #E30613; border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; }
.ag-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.ag-chip { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14); border-radius: 999px; padding: 4px 11px; font-size: 13.5px; color: #eee; }
.ag-chip em { font-style: normal; color: #FFD700; font-family: monospace; font-weight: 700; margin-left: 6px; font-size: 13.5px; }
.ag-mine { border: 1px solid rgba(76,175,80,0.45); background: rgba(76,175,80,0.08); border-radius: 14px; padding: 12px; margin-bottom: 10px; }
.ag-mine .h { font-weight: 800; color: #7EE083; margin-bottom: 8px; }
.ag-mine .nota { font-size: 11px; color: #9a9; margin-top: 8px; }
.ag-ins { background: rgba(255,255,255,0.04); border-left: 4px solid #E30613; border-radius: 10px; padding: 9px 12px; margin-bottom: 6px; }
.ag-ins.yo { border-left-color: #FFD700; background: rgba(255,215,0,0.07); }
.ag-ins .top { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 6px; }
.ag-ins .nom { font-weight: 800; color: #fff; font-size: 14.5px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ag-ins .tags { display: flex; gap: 4px; flex: 0 0 auto; }
.ag-ins .tags span { font-size: 12px; font-weight: 800; background: rgba(255,255,255,0.10); padding: 2px 7px; border-radius: 6px; color: #ddd; }
[class*="st-key-agrow_"] { flex-wrap: nowrap !important; align-items: center; }
[class*="st-key-agrow_"] > [data-testid="stElementContainer"]:first-child { flex: 1 1 auto; min-width: 0; }
.ag-paso { font-size: 12px; font-weight: 800; letter-spacing: .8px; color: #FF6A72; text-transform: uppercase; margin: 6px 0 2px; }
.ag-ok { font-size: 12px; color: #7EE083; margin: -4px 0 6px; }
@media (max-width: 640px) {
    .ag-grid { grid-template-columns: repeat(2, 1fr); }
    .ag-title { font-size: 18px; }
}
</style>
""", unsafe_allow_html=True)

if "flash_msg" in st.session_state:
    msg = st.session_state.flash_msg
    if msg["tipo"] == "success": st.success(msg["texto"])
    elif msg["tipo"] == "warning": st.warning(msg["texto"])
    elif msg["tipo"] == "error": st.error(msg["texto"])
    del st.session_state.flash_msg

hoy = date.today()

# ==========================================
# 7. AUXILIARES DE PRESENTACIÓN
# ==========================================
def _hora_txt(h):
    try: return pd.to_datetime(str(h)).strftime("%H:%M")
    except Exception: return str(h) if pd.notna(h) else "-"

def _hora_time(h):
    try: return pd.to_datetime(str(h)).time()
    except Exception: return datetime.strptime("08:30", "%H:%M").time()

def _pileta(cod):
    d = df_piletas[df_piletas['codpileta'] == cod] if df_piletas is not None and not df_piletas.empty else pd.DataFrame()
    if d.empty: return str(cod), "-", ""
    r = d.iloc[0]
    return str(r['club']), str(r['ubicacion']), str(r['medida'])

def _fecha_limite(row):
    return pd.to_datetime(row['fecha_limite']).date() if pd.notna(row['fecha_limite']) else row['fecha_dt']

def _estado(row):
    """Devuelve (clave, texto corto, abierta)."""
    f_lim = _fecha_limite(row)
    if row['fecha_dt'] < hoy: return "fin", "Finalizado", False
    if f_lim < hoy: return "cerrada", "Inscripción cerrada", False
    dias = (f_lim - hoy).days
    return "abierta", ("Cierra hoy" if dias == 0 else f"Abierta · {dias} d"), True

def _pruebas_hab(row):
    txt = str(row.get('pruebas_habilitadas', "") or "")
    lista = [x.strip() for x in txt.split(",") if x.strip()] if txt != "nan" else []
    return lista or LISTA_PRUEBAS

def _max_pruebas(row):
    v = row.get('max_pruebas', 10)
    try: return int(v) if pd.notna(v) else 10
    except Exception: return 10

def _inscriptos(comp_id):
    if df_inscripciones is None or df_inscripciones.empty: return pd.DataFrame()
    f_ins = df_inscripciones[df_inscripciones['id_competencia'] == comp_id]
    if f_ins.empty: return pd.DataFrame()
    d = f_ins.merge(df_nadadores, on="codnadador", how="left")
    d['Anio'] = d['fechanac'].dt.year
    d['Cat'] = d['Anio'].apply(calcular_categoria_master)
    d['Nombre'] = d['apellido'].astype(str) + ", " + d['nombre'].astype(str)
    return d

def _lista(txt):
    return [x.strip() for x in str(txt).split(",") if x.strip() and x.strip() != "nan"]

def _orden_pruebas(lista):
    return sorted(lista, key=lambda x: LISTA_PRUEBAS.index(x) if x in LISTA_PRUEBAS else 999)

def _chips_pruebas(pruebas, cod_nad, mostrar_tiempo=True):
    df_t_n = df_t_global[df_t_global['codnadador'] == cod_nad] if not df_t_global.empty else pd.DataFrame()
    html_c = ""
    for p_ in _orden_pruebas(pruebas):
        mt = buscar_mejor_tiempo(p_, df_t_n) if mostrar_tiempo else ""
        extra = f"<em>{esc(mt)}</em>" if mt else ""
        html_c += f"<span class='ag-chip'>{esc(p_)}{extra}</span>"
    return f"<div class='ag-chips'>{html_c}</div>"

def _fmt_pileta(cod):
    c, u, m = _pileta(cod)
    return f"{c} · {u}" + (f" ({m})" if m else "")

# ==========================================
# 8. FORMULARIO DE EVENTO (crear y editar con los mismos pasos)
# ==========================================
def form_evento(pref, row=None):
    """Campos del evento agrupados en pasos claros. Las claves quedan como f'{pref}_campo'."""
    opc_pil = df_piletas['codpileta'].tolist() if df_piletas is not None and not df_piletas.empty else []

    st.markdown("<div class='ag-paso'>1 · El torneo</div>", unsafe_allow_html=True)
    st.text_input("Nombre del evento *", value=(str(row['nombre_evento']) if row is not None else ""),
                  placeholder="Ej.: Torneo Apertura Master", key=f"{pref}_nom")
    idx_pil = opc_pil.index(row['cod_pileta']) if row is not None and row['cod_pileta'] in opc_pil else 0
    st.selectbox("Sede (pileta) *", opc_pil, index=idx_pil if opc_pil else None, format_func=_fmt_pileta, key=f"{pref}_sede")

    st.markdown("<div class='ag-paso'>2 · Fecha y horario</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.date_input("Día del torneo", value=(row['fecha_dt'] if row is not None else hoy), format="DD/MM/YYYY", key=f"{pref}_fec")
    hora_def = _hora_time(row['hora_inicio']) if row is not None else datetime.strptime("08:30", "%H:%M").time()
    c2.time_input("Hora de inicio", value=hora_def, key=f"{pref}_hor")
    st.date_input("Último día para inscribirse", value=(_fecha_limite(row) if row is not None else hoy),
                  format="DD/MM/YYYY", key=f"{pref}_cie",
                  help="Después de esta fecha los nadadores ya no pueden anotarse ni darse de baja.")

    st.markdown("<div class='ag-paso'>3 · Inscripción</div>", unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    costo_def = int(row['costo']) if row is not None and pd.notna(row['costo']) else 0
    c3.number_input("Costo por nadador ($)", min_value=0, step=500, value=costo_def, key=f"{pref}_cost")
    max_def = _max_pruebas(row) if row is not None else 10
    c4.selectbox("Pruebas por nadador (máx.)", list(range(1, 11)), index=(max_def - 1 if 1 <= max_def <= 10 else 9), key=f"{pref}_max")
    pre = [x for x in _pruebas_hab(row) if x in LISTA_PRUEBAS] if row is not None else LISTA_PRUEBAS
    st.multiselect("Pruebas que se nadan en el torneo", LISTA_PRUEBAS, default=pre, key=f"{pref}_pru",
                   help="Los nadadores solo podrán elegir entre estas pruebas.")

    st.markdown("<div class='ag-paso'>4 · Información para los nadadores</div>", unsafe_allow_html=True)
    desc_def = "" if row is None or pd.isna(row['descripcion']) else str(row['descripcion'])
    st.text_area("Descripción (opcional)", value=desc_def,
                 placeholder="Ej.: Pileta de 25 m, control electrónico, llevar gorra del club…", key=f"{pref}_desc")

def guardar_form_evento(pref, id_comp):
    g = lambda k: st.session_state.get(f"{pref}_{k}")
    nom, sede, fec, cie = (g("nom") or "").strip(), g("sede"), g("fec"), g("cie")
    if not nom or not sede:
        return False, "Completá el nombre del evento y la sede."
    if cie and fec and cie > fec:
        return False, "El cierre de inscripción no puede ser posterior al día del torneo."
    if not g("pru"):
        return False, "Elegí al menos una prueba habilitada."
    return guardar_competencia(id_comp, nom, fec, g("hor"), sede, cie, g("cost"), g("desc") or "", g("pru"), g("max"))

@st.dialog("Nuevo evento", width="medium")
def dialogo_nuevo_evento():
    with st.form("form_nuevo_evento", border=False):
        form_evento("nv")
        enviar = st.form_submit_button("Crear evento", type="primary", use_container_width=True)
    if enviar:
        nuevo_id = str(uuid.uuid4())
        ok, m = guardar_form_evento("nv", nuevo_id)
        if ok:
            set_flash_message("✅ Evento creado. Ya aparece en el carrete.", "success")
            st.session_state.ag_sel = nuevo_id
            st.rerun()
        else:
            st.error(m)

# ==========================================
# 9. CARRETE DE EVENTOS
# ==========================================
if df_competencias is None or df_competencias.empty:
    df_view = pd.DataFrame(columns=["id_competencia", "fecha_dt"])
else:
    df_view = df_competencias.copy()
    df_view['fecha_dt'] = pd.to_datetime(df_view['fecha_evento']).dt.date
df_proximos = df_view[df_view['fecha_dt'] >= hoy].sort_values('fecha_dt') if not df_view.empty else df_view
df_pasados = df_view[df_view['fecha_dt'] < hoy].sort_values('fecha_dt', ascending=False) if not df_view.empty else df_view

ids_validos = df_view['id_competencia'].tolist()
if st.session_state.get("ag_sel") not in ids_validos:
    st.session_state.ag_sel = (df_proximos.iloc[0]['id_competencia'] if not df_proximos.empty
                               else (df_pasados.iloc[0]['id_competencia'] if not df_pasados.empty else None))

mis_eventos = set()
if df_inscripciones is not None and not df_inscripciones.empty:
    mis_eventos = set(df_inscripciones[df_inscripciones['codnadador'] == mi_id]['id_competencia'])

CORTO = {"abierta": "Abierta", "cerrada": "Cerrada", "fin": "Finalizado"}

def _seleccionar(cid):
    st.session_state.ag_sel = cid

def _tarjeta_reel(row, i):
    clave, txt, _ = _estado(row)
    sel = " sel" if row['id_competencia'] == st.session_state.ag_sel else ""
    pas = " pasado" if clave == "fin" else ""
    yo = "<span class='yo' title='Estás inscripto'>✅</span>" if row['id_competencia'] in mis_eventos else ""
    f = row['fecha_dt']
    with st.container(key=f"agc_{i}"):
        st.markdown(f"""<div class="ag-card{sel}{pas}">{yo}
<div class="d">{f.day:02d}</div><div class="m">{MESES[f.month - 1]}{(" " + str(f.year)) if f.year != hoy.year else ""}</div>
<div class="n">{esc(row['nombre_evento'])}</div><div class="pill {clave}">{CORTO[clave]}</div></div>""", unsafe_allow_html=True)
        st.button("Ver", key=f"agb_{i}", on_click=_seleccionar, args=(row['id_competencia'],))

with st.container(key="ag_reel", horizontal=True):
    if ES_MANAGER:
        with st.container(key="agc_nuevo"):
            st.markdown('<div class="ag-card nuevo"><div class="plus">+</div><div class="t">Nuevo evento</div></div>', unsafe_allow_html=True)
            if st.button("Nuevo evento", key="agb_nuevo"):
                dialogo_nuevo_evento()
    n = 0
    for _, r in df_proximos.iterrows():
        _tarjeta_reel(r, n); n += 1
    if not df_pasados.empty:
        st.markdown('<div class="ag-sep">FINALIZADOS</div>', unsafe_allow_html=True)
        for _, r in df_pasados.iterrows():
            _tarjeta_reel(r, n); n += 1

if df_view.empty:
    st.info("Todavía no hay eventos cargados." + (" Tocá **+ Nuevo evento** para crear el primero." if ES_MANAGER else ""))
    st.stop()

# ==========================================
# 10. DETALLE DEL EVENTO ELEGIDO
# ==========================================
row = df_view[df_view['id_competencia'] == st.session_state.ag_sel].iloc[0]
comp_id = row['id_competencia']
clave, txt_estado, abierta = _estado(row)
club, ubic, medida = _pileta(row['cod_pileta'])
f_ev = row['fecha_dt']
f_lim = _fecha_limite(row)
dias_ev, dias_cie = (f_ev - hoy).days, (f_lim - hoy).days
d_full = _inscriptos(comp_id)
p_hab = _pruebas_hab(row)
max_permitidas = _max_pruebas(row)
costo = int(row['costo']) if pd.notna(row['costo']) else 0
costo_txt = "Sin costo" if costo == 0 else ("$ " + f"{costo:,}".replace(",", "."))

if dias_ev > 1: cuando = f"Faltan {dias_ev} días"
elif dias_ev == 1: cuando = "Es mañana"
elif dias_ev == 0: cuando = "¡Es hoy!"
else: cuando = f"Fue hace {-dias_ev} días"

if clave == "abierta":
    cierre_b = f_lim.strftime("%d/%m")
    cierre_i = "cierra hoy" if dias_cie == 0 else f"quedan {dias_cie} días"
    cierre_cls = " alerta" if dias_cie <= 3 else ""
else:
    cierre_b = "Cerrada" if clave == "cerrada" else "Finalizado"
    cierre_i = f"cerró el {f_lim.strftime('%d/%m')}"
    cierre_cls = ""

medida_txt = f" · {esc(medida)}" if medida else ""
desc_txt = esc(row['descripcion']).strip()
desc_html = f'<div class="ag-desc">{desc_txt}</div>' if desc_txt else ""

st.markdown(f"""
<div class="ag-head">
  <div class="ag-date"><b>{f_ev.day:02d}</b><span>{MESES[f_ev.month - 1]}</span></div>
  <div><div class="ag-title">{esc(row['nombre_evento'])}</div>
  <div class="ag-sub">{DIAS[f_ev.weekday()]} {f_ev.strftime('%d/%m/%Y')} · {_hora_txt(row['hora_inicio'])} hs · {cuando}</div>
  <span class="pill {clave}">{txt_estado}</span></div>
</div>
<div class="ag-grid">
  <div class="ag-tile"><small>📍 Sede</small><b>{esc(club)}</b><i>{esc(ubic)}{medida_txt}</i></div>
  <div class="ag-tile"><small>💰 Costo</small><b>{costo_txt}</b><i>por nadador</i></div>
  <div class="ag-tile{cierre_cls}"><small>⏳ Inscripción</small><b>{cierre_b}</b><i>{cierre_i}</i></div>
  <div class="ag-tile"><small>👥 Inscriptos</small><b>{len(d_full)}</b><i>nadadores</i></div>
  <div class="ag-tile"><small>🏊 Pruebas</small><b>Hasta {max_permitidas}</b><i>por nadador</i></div>
  <div class="ag-tile"><small>📋 Habilitadas</small><b>{len(p_hab)}</b><i>pruebas</i></div>
</div>
{desc_html}
""", unsafe_allow_html=True)

# ---------- Bloques reutilizables ----------
def bloque_mi_inscripcion():
    ins_user = df_inscripciones[(df_inscripciones['id_competencia'] == comp_id) & (df_inscripciones['codnadador'] == mi_id)]
    esta = not ins_user.empty
    prev = _lista(ins_user.iloc[0]['pruebas']) if esta else []

    if esta:
        plural = "s" if len(prev) != 1 else ""
        st.markdown(f"""<div class="ag-mine"><div class="h">✅ Estás inscripto en {len(prev)} prueba{plural}</div>
{_chips_pruebas(prev, mi_id)}<div class="nota">En dorado, tu mejor tiempo en cada prueba.</div></div>""",
                    unsafe_allow_html=True)

    if abierta:
        st.markdown(f"<div class='ag-paso'>{'Modificar mis pruebas' if esta else 'Elegí tus pruebas'}</div>", unsafe_allow_html=True)
        st.caption(f"Podés anotarte en hasta **{max_permitidas}** pruebas. La inscripción cierra el **{f_lim.strftime('%d/%m')}**.")
        with st.form(f"f_usr_{comp_id}", border=False):
            st.multiselect("Pruebas", p_hab, default=[x for x in prev if x in p_hab][:max_permitidas],
                           max_selections=max_permitidas, key=f"usr_pru_{comp_id}", label_visibility="collapsed",
                           placeholder="Tocá para elegir pruebas")
            c_ok, c_no = st.columns([2, 1])
            with c_ok:
                st.form_submit_button("💾 Guardar cambios" if esta else "✅ Inscribirme", type="primary",
                                      use_container_width=True, on_click=cb_guardar_usr, args=(comp_id,))
            with c_no:
                if esta:
                    st.form_submit_button("Darme de baja", use_container_width=True, on_click=cb_baja_usr, args=(comp_id,))
    elif not esta:
        if clave == "fin":
            st.info("Este torneo ya se realizó y no estuviste inscripto.")
        else:
            st.info(f"La inscripción cerró el {f_lim.strftime('%d/%m')}. Si necesitás anotarte, consultá con tu entrenador.")

def bloque_inscriptos(puede_borrar=False):
    if d_full.empty:
        st.caption("Todavía no hay nadadores inscriptos.")
        return
    pruebas_ins = _orden_pruebas({p_ for lst in d_full['pruebas'] for p_ in _lista(lst)})
    c1, c2, c3 = st.columns(3)
    f_pru = c1.selectbox("Prueba", ["Todas"] + pruebas_ins, key=f"fpru_{comp_id}")
    f_cat = c2.selectbox("Categoría", ["Todas"] + sorted(d_full['Cat'].unique().tolist()), key=f"fcat_{comp_id}")
    f_gen = c3.selectbox("Género", ["Todos"] + sorted(d_full['codgenero'].dropna().unique().tolist()), key=f"fgen_{comp_id}")

    df_f = d_full.copy()
    if f_pru != "Todas": df_f = df_f[df_f['pruebas'].apply(lambda s_: f_pru in _lista(s_))]
    if f_cat != "Todas": df_f = df_f[df_f['Cat'] == f_cat]
    if f_gen != "Todos": df_f = df_f[df_f['codgenero'] == f_gen]
    if df_f.empty:
        st.info("Ningún inscripto coincide con estos filtros.")
        return
    st.caption(f"{len(df_f)} de {len(d_full)} inscriptos")

    for _, r_ in df_f.sort_values(['Cat', 'codgenero', 'Nombre']).iterrows():
        es_yo = r_['codnadador'] == mi_id
        pruebas_l = _lista(r_['pruebas'])
        if f_pru != "Todas": pruebas_l = [x for x in pruebas_l if x == f_pru]
        # El nadador ve los tiempos de los de su misma categoría y género
        ver_t = ES_MANAGER or es_yo or (str(r_['Cat']) == str(mi_cat_actual)
                                       and str(r_['codgenero']).strip().upper() == mi_genero)
        tarjeta = f"""<div class="ag-ins{' yo' if es_yo else ''}"><div class="top">
<div class="nom">{'⭐ ' if es_yo else ''}{esc(r_['Nombre'])}{' (vos)' if es_yo else ''}</div>
<div class="tags"><span>{esc(r_['Cat'])}</span><span>{esc(r_['codgenero'])}</span></div></div>
{_chips_pruebas(pruebas_l, r_['codnadador'], ver_t)}</div>"""
        if puede_borrar:
            with st.container(key=f"agrow_{comp_id}_{r_['codnadador']}", horizontal=True, gap="small"):
                st.markdown(tarjeta, unsafe_allow_html=True)
                st.button("", key=f"del_ins_{comp_id}_{r_['codnadador']}", icon=":material/person_remove:",
                          on_click=cb_baja_grid, args=(comp_id, r_['codnadador'], r_['Nombre']))
        else:
            st.markdown(tarjeta, unsafe_allow_html=True)

def bloque_exportar():
    if d_full.empty: return
    export_list = []
    for _, r_ in d_full.sort_values('Nombre').iterrows():
        df_t_n = df_t_global[df_t_global['codnadador'] == r_['codnadador']] if not df_t_global.empty else pd.DataFrame()
        p_txt = []
        for p_ in _lista(r_['pruebas']):
            mt = buscar_mejor_tiempo(p_, df_t_n)
            p_txt.append(f"{p_} ({mt})" if mt else f"{p_} (S/T)")
        export_list.append({"Nadador": r_['Nombre'], "Género": r_['codgenero'], "Categoría": r_['Cat'],
                            "Pruebas Inscriptas (Tiempos)": " | ".join(p_txt)})
    df_exp = pd.DataFrame(export_list)
    nombre_arch = "Inscriptos_" + str(row['nombre_evento']).replace(" ", "_")
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_exp.to_excel(writer, index=False, sheet_name='Inscriptos')
        st.download_button("📥 Descargar planilla de inscriptos", data=buffer.getvalue(), file_name=f"{nombre_arch}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    except Exception:
        st.download_button("📥 Descargar CSV de inscriptos", data=df_exp.to_csv(index=False).encode('utf-8-sig'),
                           file_name=f"{nombre_arch}.csv", mime="text/csv", use_container_width=True)

def bloque_alta_manual():
    st.caption("Elegí un nadador y sus pruebas. Si ya está inscripto, se cargan sus pruebas para modificarlas.")
    opc = dict(zip(df_nadadores['codnadador'], df_nadadores['apellido'].astype(str) + ", " + df_nadadores['nombre'].astype(str)))
    opc = dict(sorted(opc.items(), key=lambda it: it[1]))
    nad_sel = st.selectbox("Nadador", list(opc.keys()), format_func=lambda x: opc[x], key=f"adm_nad_{comp_id}",
                           on_change=cb_nadador_change, args=(comp_id,))
    prev = []
    if not d_full.empty:
        ex = d_full[d_full['codnadador'] == nad_sel]
        if not ex.empty:
            prev = _lista(ex.iloc[0]['pruebas'])
            st.markdown(f"<div class='ag-ok'>✅ Ya inscripto en {len(prev)} prueba(s)</div>", unsafe_allow_html=True)
    k_pru = f"adm_pru_{comp_id}_{nad_sel}"
    st.multiselect(f"Pruebas (hasta {max_permitidas})", p_hab, default=[x for x in prev if x in p_hab][:max_permitidas],
                   max_selections=max_permitidas, key=k_pru, placeholder="Tocá para elegir pruebas")
    st.button("💾 Guardar inscripción", key=f"btn_adm_save_{comp_id}", type="primary", use_container_width=True,
              on_click=cb_alta_adm, args=(comp_id, f"adm_nad_{comp_id}", k_pru))

def bloque_editar():
    with st.form(f"ed_{comp_id}", border=False):
        form_evento(f"ed_{comp_id}", row)
        guardar = st.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
    if guardar:
        ok, m = guardar_form_evento(f"ed_{comp_id}", comp_id)
        if ok:
            set_flash_message("✅ Evento actualizado.", "success"); st.rerun()
        else:
            st.error(m)
    st.markdown("<div class='ag-paso' style='margin-top:18px'>Eliminar evento</div>", unsafe_allow_html=True)
    conf = st.checkbox(f"Confirmo que quiero eliminar este evento y sus {len(d_full)} inscripciones", key=f"conf_del_{comp_id}")
    st.button("🗑️ Eliminar evento", key=f"btn_del_{comp_id}", disabled=not conf, use_container_width=True,
              on_click=cb_elim_evento, args=(comp_id,))

def bloque_simulador():
    st.caption("Lleva a todos los inscriptos de este evento al Simulador para armar las postas.")
    if d_full.empty:
        st.info("Cuando haya inscriptos vas a poder enviarlos al Simulador.")
        return
    nombres = (d_full['apellido'].astype(str).str.upper() + ", " + d_full['nombre'].astype(str)).tolist()
    def cb_ir_sim():
        st.session_state.simulador_pre_pool = nombres
        if "pool_opt_g" in st.session_state: del st.session_state["pool_opt_g"]
    if st.button(f"🚀 Ir al Simulador con los {len(nombres)} inscriptos", key=f"btn_sim_comp_{comp_id}", type="primary",
                 use_container_width=True, on_click=cb_ir_sim):
        st.switch_page("pages/3_simulador.py")

# ---------- Pestañas según el perfil ----------
if ES_MANAGER:
    t_ins, t_alta, t_ed, t_sim = st.tabs([f"👥 Inscriptos ({len(d_full)})", "➕ Inscribir", "⚙️ Editar", "🚀 Simulador"],
                                         key="ag_tabs_m", on_change="rerun")
    with t_ins:
        bloque_exportar()
        bloque_inscriptos(puede_borrar=True)
    with t_alta: bloque_alta_manual()
    with t_ed: bloque_editar()
    with t_sim: bloque_simulador()
else:
    t_mia, t_ins = st.tabs(["📝 Mi inscripción", f"👥 Inscriptos ({len(d_full)})"], key="ag_tabs_n", on_change="rerun")
    with t_mia: bloque_mi_inscripcion()
    with t_ins: bloque_inscriptos()
