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

# --- DEFINICIÓN DE PRUEBAS ESTÁNDAR ---
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
    """Intenta actualizar la hoja de cálculo con reintentos."""
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
    """Carga Competencias, Inscripciones, Nadadores y Piletas."""
    try:
        # 1. Competencias
        try:
            df_comp = conn.read(worksheet="Competencias").copy()
            if not df_comp.empty:
                # Convertir columnas de fecha
                if 'fecha_evento' in df_comp.columns:
                    df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento']).dt.date
                if 'fecha_limite' in df_comp.columns:
                    df_comp['fecha_limite'] = pd.to_datetime(df_comp['fecha_limite']).dt.date
        except:
            # Estructura Nueva: Usamos 'descripcion' en lugar de 'observaciones'
            df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion"])

        # 2. Inscripciones
        try:
            df_ins = conn.read(worksheet="Inscripciones").copy()
            if not df_ins.empty:
                df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
        except:
            df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])

        # 3. Nadadores (Solo lectura nombres)
        try:
            df_nad = conn.read(worksheet="Nadadores").copy()
            df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce').fillna(0).astype(int)
        except:
            df_nad = pd.DataFrame(columns=["codnadador", "nombre", "apellido"])

        # 4. Piletas (Para el selector de lugares)
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

def guardar_competencia(id_comp, nombre, fecha_ev, hora, cod_pil, fecha_lim, costo, desc):
    df_comp = leer_dataset_fresco("Competencias")
    if df_comp is None:
        df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion"])
    
    if not df_comp.empty and 'fecha_evento' in df_comp.columns:
        df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento']).dt.date

    nuevo_registro = {
        "id_competencia": id_comp if id_comp else str(uuid.uuid4()),
        "nombre_evento": nombre,
        "fecha_evento": fecha_ev,
        "hora_inicio": str(hora),
        "cod_pileta": cod_pil,
        "fecha_limite": fecha_lim,
        "costo": costo,
        "descripcion": desc  # Usamos descripcion
    }

    if id_comp and not df_comp.empty and id_comp in df_comp['id_competencia'].values:
        # Editar
        idx = df_comp.index[df_comp['id_competencia'] == id_comp].tolist()[0]
        for key, val in nuevo_registro.items():
            df_comp.at[idx, key] = val
        msg = "✅ Evento actualizado."
    else:
        # Crear
        df_comp = pd.concat([df_comp, pd.DataFrame([nuevo_registro])], ignore_index=True)
        msg = "✅ Evento creado."

    # Convertir fechas a string para guardar
    df_comp['fecha_evento'] = df_comp['fecha_evento'].astype(str)
    df_comp['fecha_limite'] = df_comp['fecha_limite'].astype(str)
    df_comp['hora_inicio'] = df_comp['hora_inicio'].astype(str)
    
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

# Carga
df_competencias, df_inscripciones, df_nadadores, df_piletas = cargar_datos_agenda()

st.title("📅 Agenda de Torneos")
st.markdown(f"Usuario: **{mi_nombre}**")

# --- SECCIÓN ADMIN: CREAR COMPETENCIA ---
if rol in ["M", "P"]:
    with st.expander("🛠️ Crear Nuevo Evento", expanded=False):
        with st.form("form_crear_comp"):
            st.markdown("##### Datos del Evento")
            c1, c2 = st.columns(2)
            nombre_in = c1.text_input("Nombre del Evento (Ej: Torneo Aniversario)")
            
            # Selector de Piletas
            opciones_piletas = df_piletas['codpileta'].tolist() if not df_piletas.empty else []
            def format_pileta(cod):
                row = df_piletas[df_piletas['codpileta']==cod].iloc[0]
                return f"{row['club']} ({row['medida']}) - {row['ubicacion']}"
            
            cod_pil_in = c2.selectbox("Sede / Pileta", opciones_piletas, format_func=format_pileta if opciones_piletas else str)
            
            c3, c4 = st.columns(2)
            fecha_in = c3.date_input("Fecha del Torneo", min_value=datetime.today())
            hora_in = c4.time_input("Hora Inicio", value=datetime.strptime("08:30", "%H:%M").time())
            
            st.markdown("##### Configuración de Inscripción")
            c5, c6 = st.columns(2)
            fecha_lim_in = c5.date_input("Fecha Límite Inscripción", min_value=datetime.today())
            costo_in = c6.number_input("Costo Inscripción ($)", min_value=0, step=1000)
            
            desc_in = st.text_area("Descripción (Reglamento, info de pago, etc.)")
            
            if st.form_submit_button("Guardar Evento en Agenda"):
                if nombre_in and cod_pil_in:
                    ok, msg = guardar_competencia(None, nombre_in, fecha_in, hora_in, cod_pil_in, fecha_lim_in, costo_in, desc_in)
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

        # Fechas y Estados
        f_limite = pd.to_datetime(row['fecha_limite']).dt.date
        dias_para_torneo = (row['fecha_dt'] - hoy).days
        dias_para_cierre = (f_limite - hoy).days
        
        # Badge Estado
        inscripcion_abierta = True
        if dias_para_torneo < 0:
            badge = "🔴 FINALIZADO"
            badge_bg = "#333"
            inscripcion_abierta = False
        elif dias_para_cierre < 0:
            badge = "🔒 INSCRIPCIÓN CERRADA"
            badge_bg = "#E30613" # Rojo
            inscripcion_abierta = False
        else:
            badge = f"🟢 ABIERTA (Cierra en {dias_para_cierre} días)"
            badge_bg = "#2E7D32" # Verde

        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; border: 1px solid #555; border-radius: 10px; padding: 15px; margin-bottom: 20px;">
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
                    <div>📍 <strong>Sede:</strong> {nom_pil}</div>
                    <div>🏙️ <strong>Ciudad:</strong> {ubic_pil}</div>
                    <div>💰 <strong>Costo:</strong> ${row['costo']}</div>
                </div>
                
                <div style="background-color:#333; padding:10px; border-radius:5px; font-size:13px; color:#ccc; white-space: pre-wrap;">{row['descripcion'] if row['descripcion'] else 'Sin información adicional.'}</div>
            """, unsafe_allow_html=True)

            # --- LÓGICA USUARIO (INSCRIPCIÓN) ---
            inscripcion_user = df_inscripciones[
                (df_inscripciones['id_competencia'] == comp_id) & 
                (df_inscripciones['codnadador'] == mi_id)
            ]
            esta_inscripto = not inscripcion_user.empty
            permiso_editar = inscripcion_abierta or rol in ["M", "P"]
            
            if permiso_editar:
                exp_label = "✅ Gestionar mi Inscripción" if esta_inscripto else "📝 Inscribirme al Torneo"
                with st.expander(exp_label):
                    pruebas_sel = []
                    if esta_inscripto:
                        raw_p = inscripcion_user.iloc[0]['pruebas']
                        if pd.notna(raw_p): pruebas_sel = [p.strip() for p in raw_p.split(",")]

                    with st.form(f"ins_{comp_id}"):
                        st.write("**Selecciona tus pruebas:**")
                        sel = st.multiselect("Pruebas Oficiales", LISTA_PRUEBAS, default=[p for p in pruebas_sel if p in LISTA_PRUEBAS])
                        otro = st.text_input("Otras Pruebas", value=", ".join([p for p in pruebas_sel if p not in LISTA_PRUEBAS]))
                        
                        c_s, c_d = st.columns([3, 1])
                        with c_s: submitted = st.form_submit_button("💾 Guardar Inscripción")
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
                    st.markdown(f"""
                    <div style="margin-top:10px; padding:10px; border:1px solid #2E7D32; border-radius:5px; background-color:#1B2E1B;">
                        <strong>✅ Estás inscripto en:</strong> {inscripcion_user.iloc[0]['pruebas']}
                    </div>
                    """, unsafe_allow_html=True)

            # --- LÓGICA ADMIN (PLANILLA) ---
            if rol in ["M", "P"]:
                with st.expander(f"🛡️ Gestión Entrenador ({row['nombre_evento']})"):
                    t1, t2 = st.tabs(["📋 Inscriptos", "⚙️ Editar"])
                    
                    with t1:
                        filtro_ins = df_inscripciones[df_inscripciones['id_competencia'] == comp_id]
                        if filtro_ins.empty:
                            st.caption("Sin inscriptos.")
                        else:
                            data_full = filtro_ins.merge(df_nadadores, on="codnadador", how="left")
                            data_full['Nadador'] = data_full['apellido'] + " " + data_full['nombre']
                            st.dataframe(data_full[['Nadador', 'pruebas']], hide_index=True, use_container_width=True)
                            
                            c_b1, c_b2 = st.columns([3, 1])
                            with c_b1:
                                n_del = st.selectbox("Dar de baja a:", data_full['codnadador'].unique(), format_func=lambda x: data_full[data_full['codnadador']==x]['Nadador'].values[0], key=f"d_{comp_id}")
                            with c_b2:
                                if st.button("Baja", key=f"btn_d_{comp_id}"):
                                    eliminar_inscripcion(comp_id, n_del); st.rerun()

                    with t2:
                        with st.form(f"edit_{comp_id}"):
                            new_n = st.text_input("Nombre", value=row['nombre_evento'])
                            new_f = st.date_input("Fecha Evento", value=pd.to_datetime(row['fecha_dt']))
                            new_l = st.date_input("Cierre Inscripción", value=pd.to_datetime(f_limite))
                            new_desc = st.text_area("Descripción", value=row['descripcion'])
                            
                            if st.form_submit_button("Actualizar Datos"):
                                guardar_competencia(comp_id, new_n, new_f, row['hora_inicio'], row['cod_pileta'], new_l, row['costo'], new_desc)
                                st.rerun()
                            
                            if st.form_submit_button("⚠️ ELIMINAR EVENTO"):
                                eliminar_competencia(comp_id); st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
