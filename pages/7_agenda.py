import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import time
import random
import uuid

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

# ==========================================
# 3. CONEXIÓN Y DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DEFINICIÓN GLOBAL DE PRUEBAS ---
LISTA_PRUEBAS = [
    "50m Libre", "100m Libre", "200m Libre", "400m Libre", "800m Libre", "1500m Libre",
    "50m Espalda", "100m Espalda", "200m Espalda",
    "50m Pecho", "100m Pecho", "200m Pecho",
    "50m Mariposa", "100m Mariposa", "200m Mariposa",
    "100m Combinado", "200m Combinado", "400m Combinado",
    "Posta 4x50 Libre", "Posta 4x50 Combinada", "Posta 4x100 Libre"
]

# ==========================================
# 4. FUNCIONES AUXILIARES (BACKEND)
# ==========================================

def actualizar_con_retry(worksheet, data, max_retries=5):
    for i in range(max_retries):
        try:
            conn.update(worksheet=worksheet, data=data)
            return True, None 
        except Exception as e:
            if "429" in str(e) or "quota" in str(e):
                time.sleep((2 ** i) + random.uniform(0, 1))
                continue 
            else:
                return False, e
    return False, "Tiempo de espera agotado."

@st.cache_data(ttl="5s")
def cargar_datos_agenda():
    try:
        # 1. Competencias
        try:
            df_comp = conn.read(worksheet="Competencias").copy()
            if not df_comp.empty:
                # Normalizar Fechas
                if 'fecha_evento' in df_comp.columns:
                    df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento']).dt.date
                if 'fecha_limite' in df_comp.columns:
                    df_comp['fecha_limite'] = pd.to_datetime(df_comp['fecha_limite']).dt.date
                # Asegurar que exista la columna nueva
                if 'pruebas_habilitadas' not in df_comp.columns:
                    df_comp['pruebas_habilitadas'] = ""
        except:
            df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion", "pruebas_habilitadas"])

        # 2. Inscripciones
        try:
            df_ins = conn.read(worksheet="Inscripciones").copy()
            if not df_ins.empty:
                df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
        except:
            df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])

        # 3. Nadadores
        try:
            df_nad = conn.read(worksheet="Nadadores").copy()
            df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce').fillna(0).astype(int)
        except:
            df_nad = pd.DataFrame(columns=["codnadador", "nombre", "apellido"])

        # 4. Piletas
        try:
            df_pil = conn.read(worksheet="Piletas").copy()
        except:
            df_pil = pd.DataFrame(columns=["codpileta", "club", "medida", "ubicacion"])

        return df_comp, df_ins, df_nad, df_pil

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None, None, None, None

def leer_dataset_fresco(worksheet):
    try:
        return conn.read(worksheet=worksheet, ttl=0).copy()
    except:
        return None

# --- GESTIÓN DE COMPETENCIAS (ADMIN) ---

def guardar_competencia(id_comp, nombre, fecha_ev, hora, cod_pil, fecha_lim, costo, desc, lista_pruebas_hab):
    df_comp = leer_dataset_fresco("Competencias")
    if df_comp is None:
        df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion", "pruebas_habilitadas"])
    
    if 'pruebas_habilitadas' not in df_comp.columns:
        df_comp['pruebas_habilitadas'] = ""

    str_pruebas = ", ".join(lista_pruebas_hab) if lista_pruebas_hab else ""

    nuevo_registro = {
        "id_competencia": id_comp if id_comp else str(uuid.uuid4()),
        "nombre_evento": nombre,
        "fecha_evento": str(fecha_ev),
        "hora_inicio": str(hora),
        "cod_pileta": cod_pil,
        "fecha_limite": str(fecha_lim),
        "costo": costo,
        "descripcion": desc,
        "pruebas_habilitadas": str_pruebas
    }

    if id_comp and not df_comp.empty and id_comp in df_comp['id_competencia'].values:
        idx = df_comp.index[df_comp['id_competencia'] == id_comp].tolist()[0]
        for key, val in nuevo_registro.items():
            df_comp.at[idx, key] = val
        msg = "✅ Evento actualizado correctamente."
    else:
        df_comp = pd.concat([df_comp, pd.DataFrame([nuevo_registro])], ignore_index=True)
        msg = "✅ Evento creado correctamente."

    exito, err = actualizar_con_retry("Competencias", df_comp)
    if exito:
        st.cache_data.clear()
        return True, msg
    return False, f"Error: {err}"

def eliminar_competencia(id_comp):
    df_comp = leer_dataset_fresco("Competencias")
    df_ins = leer_dataset_fresco("Inscripciones")
    
    if df_comp is None: return False, "Error conexión."

    df_comp_final = df_comp[df_comp['id_competencia'] != id_comp]
    
    if df_ins is not None and not df_ins.empty:
        df_ins_final = df_ins[df_ins['id_competencia'] != id_comp]
        actualizar_con_retry("Inscripciones", df_ins_final)

    exito, err = actualizar_con_retry("Competencias", df_comp_final)
    if exito:
        st.cache_data.clear()
        return True, "🗑️ Evento eliminado."
    return False, f"Error: {err}"

# --- GESTIÓN DE INSCRIPCIONES ---

def gestionar_inscripcion(id_comp, id_nadador, lista_pruebas):
    df_ins = leer_dataset_fresco("Inscripciones")
    if df_ins is None:
        df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])
    
    if not df_ins.empty:
        df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)

    pruebas_str = ", ".join(lista_pruebas)
    
    mask = (df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador)
    
    if not df_ins[mask].empty:
        df_ins.loc[mask, 'pruebas'] = pruebas_str
        df_ins.loc[mask, 'fecha_inscripcion'] = datetime.now().strftime("%Y-%m-%d")
        msg = "✏️ Inscripción modificada."
    else:
        nuevo = {
            "id_inscripcion": str(uuid.uuid4()),
            "id_competencia": id_comp,
            "codnadador": int(id_nadador),
            "pruebas": pruebas_str,
            "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d")
        }
        df_ins = pd.concat([df_ins, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "✅ Inscripción exitosa."

    exito, err = actualizar_con_retry("Inscripciones", df_ins)
    if exito:
        st.cache_data.clear()
        return True, msg
    return False, f"Error: {err}"

def eliminar_inscripcion(id_comp, id_nadador):
    df_ins = leer_dataset_fresco("Inscripciones")
    if df_ins is None: return False, "Error conexión."
    
    if not df_ins.empty:
        df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)

    df_final = df_ins[~((df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador))]
    
    exito, err = actualizar_con_retry("Inscripciones", df_final)
    if exito:
        st.cache_data.clear()
        return True, "🗑️ Inscripción eliminada."
    return False, f"Error: {err}"

# ==========================================
# 5. UI PRINCIPAL
# ==========================================

df_competencias, df_inscripciones, df_nadadores, df_piletas = cargar_datos_agenda()

st.title("📅 Agenda de Torneos")
st.markdown(f"Usuario: **{mi_nombre}**")

# --- SECCIÓN ADMIN: CREAR COMPETENCIA ---
if rol in ["M", "P"]:
    with st.expander("🛠️ Crear Nuevo Evento", expanded=False):
        with st.form("form_crear_comp"):
            st.markdown("##### Datos Principales")
            c1, c2 = st.columns(2)
            nombre_in = c1.text_input("Nombre del Evento")
            
            # Selector de Piletas
            opciones_piletas = df_piletas['codpileta'].tolist() if not df_piletas.empty else []
            def format_pileta(cod):
                row = df_piletas[df_piletas['codpileta']==cod].iloc[0]
                return f"{row['club']} ({row['medida']}) - {row['ubicacion']}"
            
            cod_pil_in = c2.selectbox("Sede / Pileta", opciones_piletas, format_func=format_pileta if opciones_piletas else str)
            
            c3, c4 = st.columns(2)
            fecha_in = c3.date_input("Fecha del Torneo", min_value=datetime.today(), format="DD/MM/YYYY")
            hora_in = c4.time_input("Hora Inicio", value=datetime.strptime("08:30", "%H:%M").time())
            
            st.markdown("##### Configuración")
            c5, c6 = st.columns(2)
            fecha_lim_in = c5.date_input("Fecha Límite Inscripción", min_value=datetime.today(), format="DD/MM/YYYY")
            costo_in = c6.number_input("Costo Inscripción ($)", min_value=0, step=1000)
            
            # --- PRESELECCIÓN DE PRUEBAS ---
            st.markdown("##### Definir Programa de Pruebas")
            pruebas_hab_in = st.multiselect("Seleccione las pruebas que se nadarán en este torneo:", LISTA_PRUEBAS, default=LISTA_PRUEBAS)
            
            desc_in = st.text_area("Descripción (Reglamento, info de pago, etc.)")
            
            if st.form_submit_button("Guardar Evento en Agenda"):
                if nombre_in and cod_pil_in:
                    ok, msg = guardar_competencia(None, nombre_in, fecha_in, hora_in, cod_pil_in, fecha_lim_in, costo_in, desc_in, pruebas_hab_in)
                    if ok: st.success(msg); time.sleep(1); st.rerun()
                    else: st.error(msg)
                else:
                    st.warning("Nombre y Sede son obligatorios.")

st.divider()

# --- VISUALIZACIÓN DE COMPETENCIAS ---

if df_competencias is None or df_competencias.empty:
    st.info("No hay competencias programadas.")
else:
    hoy = date.today()
    
    df_view = df_competencias.copy()
    if not df_view.empty:
        df_view['fecha_dt'] = pd.to_datetime(df_view['fecha_evento']).dt.date
        df_view = df_view.sort_values(by='fecha_dt', ascending=True)

    st.subheader("Próximas Competencias")

    for idx, row in df_view.iterrows():
        comp_id = row['id_competencia']
        
        # Datos Pileta
        datos_pil = df_piletas[df_piletas['codpileta'] == row['cod_pileta']]
        if not datos_pil.empty:
            nom_pil = f"{datos_pil.iloc[0]['club']} ({datos_pil.iloc[0]['medida']})"
            ubic_pil = datos_pil.iloc[0]['ubicacion']
        else:
            nom_pil = row['cod_pileta']
            ubic_pil = "-"

        # Fechas
        f_limite = pd.to_datetime(row['fecha_limite']).date()
        dias_para_torneo = (row['fecha_dt'] - hoy).days
        dias_para_cierre = (f_limite - hoy).days
        
        # Badge Estado
        inscripcion_abierta = True
        if dias_para_torneo < 0:
            badge = "🔴 FINALIZADO"
            badge_bg = "#333"
            inscripcion_abierta = False
        elif dias_para_cierre < 0:
            badge = "🔒 CERRADA"
            badge_bg = "#E30613"
            inscripcion_abierta = False
        else:
            badge = f"🟢 ABIERTA ({dias_para_cierre} días)"
            badge_bg = "#2E7D32"

        # --- TARJETA VISUAL ---
        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; border: 1px solid #555; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div>
                        <h3 style="margin:0; color:white;">{row['nombre_evento']}</h3>
                        <div style="color:#4CAF50; font-weight:bold; font-size:14px; margin-top:5px;">
                            📅 {row['fecha_dt'].strftime('%d/%m/%Y')} &nbsp; ⏰ {row['hora_inicio']} hs
                        </div>
                    </div>
                    <span style="background-color:{badge_bg}; color:white; padding:5px 10px; border-radius:5px; font-size:11px; font-weight:bold;">
                        {badge}
                    </span>
                </div>
                <hr style="border-color:#444; margin:10px 0;">
                <div style="display:flex; gap:20px; color:#ddd; font-size:14px; margin-bottom:10px;">
                    <div>📍 {nom_pil}</div>
                    <div>🏙️ {ubic_pil}</div>
                    <div>💰 ${row['costo']}</div>
                </div>
                <div style="background-color:#333; padding:10px; border-radius:5px; font-size:13px; color:#ccc; white-space: pre-wrap;">{row['descripcion'] if row['descripcion'] else 'Sin información adicional.'}</div>
            </div>
            """, unsafe_allow_html=True)

            # --- LÓGICA USUARIO (INSCRIPCIÓN) ---
            inscripcion_user = df_inscripciones[
                (df_inscripciones['id_competencia'] == comp_id) & 
                (df_inscripciones['codnadador'] == mi_id)
            ]
            esta_inscripto = not inscripcion_user.empty
            permiso_editar = inscripcion_abierta or rol in ["M", "P"]
            
            pruebas_disponibles_str = row.get('pruebas_habilitadas', "")
            if pd.isna(pruebas_disponibles_str) or str(pruebas_disponibles_str).strip() == "":
                opciones_usuario = LISTA_PRUEBAS
            else:
                opciones_usuario = [p.strip() for p in str(pruebas_disponibles_str).split(",")]

            if permiso_editar:
                exp_label = "✅ Gestionar Inscripción" if esta_inscripto else "📝 Inscribirse"
                with st.expander(exp_label):
                    pruebas_sel_usuario = []
                    if esta_inscripto:
                        raw_p = inscripcion_user.iloc[0]['pruebas']
                        if pd.notna(raw_p): pruebas_sel_usuario = [p.strip() for p in raw_p.split(",")]

                    with st.form(f"ins_{comp_id}"):
                        st.caption("Selecciona las pruebas en las que vas a participar:")
                        
                        sel = st.multiselect("Pruebas Habilitadas", opciones_usuario, default=[p for p in pruebas_sel_usuario if p in opciones_usuario])
                        otro = st.text_input("Otras Pruebas (Solo si autoriza el entrenador)", value=", ".join([p for p in pruebas_sel_usuario if p not in opciones_usuario]))
                        
                        c_s, c_d = st.columns([3, 1])
                        with c_s: submitted = st.form_submit_button("💾 Confirmar Inscripción")
                        with c_d:
                            eliminar = False
                            if esta_inscripto: eliminar = st.form_submit_button("🗑️ Baja", type="secondary")
                        
                        if submitted:
                            final = sel.copy()
                            if otro: final.extend([x.strip() for x in otro.split(",") if x.strip()])
                            
                            if not final: st.error("Selecciona al menos una prueba.")
                            else:
                                ok, m = gestionar_inscripcion(comp_id, mi_id, final)
                                if ok: st.success(m); time.sleep(1); st.rerun()
                        
                        if eliminar:
                            ok, m = eliminar_inscripcion(comp_id, mi_id)
                            if ok: st.warning(m); time.sleep(1); st.rerun()
            else:
                if esta_inscripto:
                    st.success(f"✅ Inscripto en: {inscripcion_user.iloc[0]['pruebas']}")

            # --- LÓGICA ADMIN (PLANILLA Y EDICIÓN) ---
            if rol in ["M", "P"]:
                with st.expander(f"🛡️ Panel Entrenador ({row['nombre_evento']})"):
                    t1, t2 = st.tabs(["📋 Inscriptos", "⚙️ Editar Evento"])
                    
                    # --- PESTAÑA 1: LISTA PROLIJA DE INSCRIPTOS ---
                    with t1:
                        filtro_ins = df_inscripciones[df_inscripciones['id_competencia'] == comp_id]
                        if filtro_ins.empty:
                            st.caption("Sin inscriptos.")
                        else:
                            data_full = filtro_ins.merge(df_nadadores, on="codnadador", how="left")
                            
                            # Cabecera de la lista
                            h1, h2, h3 = st.columns([3, 4, 1])
                            h1.markdown("**Nadador**")
                            h2.markdown("**Pruebas**")
                            h3.markdown("**Baja**")
                            st.divider()

                            # Filas dinámicas
                            for idx_nad, r_nad in data_full.iterrows():
                                n_col1, n_col2, n_col3 = st.columns([3, 4, 1])
                                with n_col1:
                                    st.write(f"{r_nad['apellido']}, {r_nad['nombre']}")
                                with n_col2:
                                    st.caption(r_nad['pruebas'])
                                with n_col3:
                                    # Botón "X" limpio alineado
                                    if st.button("❌", key=f"del_{comp_id}_{r_nad['codnadador']}", help="Eliminar inscripción"):
                                        eliminar_inscripcion(comp_id, r_nad['codnadador'])
                                        st.rerun()
                                st.markdown("<hr style='margin: 5px 0; border-color: #333;'>", unsafe_allow_html=True)

                    # --- PESTAÑA 2: EDITAR EVENTO ---
                    with t2:
                        pruebas_actuales_db = row.get('pruebas_habilitadas', "")
                        lista_pre = [p.strip() for p in str(pruebas_actuales_db).split(",")] if pd.notna(pruebas_actuales_db) and str(pruebas_actuales_db).strip() != "" else LISTA_PRUEBAS

                        with st.form(f"edit_{comp_id}"):
                            col_e1, col_e2 = st.columns(2)
                            new_n = col_e1.text_input("Nombre", value=row['nombre_evento'])
                            new_c = col_e2.number_input("Costo", value=int(row['costo']) if pd.notna(row['costo']) else 0)
                            
                            col_e3, col_e4 = st.columns(2)
                            new_f = col_e3.date_input("Fecha Evento", value=pd.to_datetime(row['fecha_dt']), format="DD/MM/YYYY")
                            new_l = col_e4.date_input("Cierre Inscripción", value=pd.to_datetime(f_limite), format="DD/MM/YYYY")
                            
                            new_pruebas = st.multiselect("Pruebas Habilitadas", LISTA_PRUEBAS, default=[p for p in lista_pre if p in LISTA_PRUEBAS])
                            
                            new_desc = st.text_area("Descripción", value=row['descripcion'])
                            
                            if st.form_submit_button("Actualizar Datos"):
                                guardar_competencia(comp_id, new_n, new_f, row['hora_inicio'], row['cod_pileta'], new_l, new_c, new_desc, new_pruebas)
                                st.rerun()
                            
                            st.markdown("---")
                            if st.form_submit_button("⚠️ ELIMINAR EVENTO COMPLETO", type="primary"):
                                eliminar_competencia(comp_id); st.rerun()
            
            st.divider()
