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

def calcular_categoria_master(anio_nac):
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
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 9999.0

@st.cache_data(ttl="5s")
def cargar_datos_agenda():
    try:
        try:
            df_comp = conn.read(worksheet="Competencias").copy()
            if not df_comp.empty:
                if 'fecha_evento' in df_comp.columns: df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento']).dt.date
                if 'fecha_limite' in df_comp.columns: df_comp['fecha_limite'] = pd.to_datetime(df_comp['fecha_limite']).dt.date
                if 'pruebas_habilitadas' not in df_comp.columns: df_comp['pruebas_habilitadas'] = ""
        except:
            df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion", "pruebas_habilitadas"])

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

        try:
            df_pil = conn.read(worksheet="Piletas").copy()
        except:
            df_pil = pd.DataFrame(columns=["codpileta", "club", "medida", "ubicacion"])

        try: df_tiempos = conn.read(worksheet="Tiempos").copy()
        except: df_tiempos = pd.DataFrame()
        
        try: df_estilos = conn.read(worksheet="Estilos").copy()
        except: df_estilos = pd.DataFrame()
        
        try: df_dist = conn.read(worksheet="Distancias").copy()
        except: df_dist = pd.DataFrame()

        return df_comp, df_ins, df_nad, df_pil, df_tiempos, df_estilos, df_dist
    except: return None, None, None, None, None, None, None

def leer_dataset_fresco(worksheet):
    try: return conn.read(worksheet=worksheet, ttl=0).copy()
    except: return None

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

# ==========================================
# 5. FUNCIONES CRUD
# ==========================================

def guardar_competencia(id_comp, nombre, fecha_ev, hora, cod_pil, fecha_lim, costo, desc, lista_pruebas_hab):
    df_comp = leer_dataset_fresco("Competencias")
    if df_comp is None: df_comp = pd.DataFrame(columns=["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite", "costo", "descripcion", "pruebas_habilitadas"])
    if 'pruebas_habilitadas' not in df_comp.columns: df_comp['pruebas_habilitadas'] = ""

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
        "pruebas_habilitadas": str_pruebas
    }

    if id_comp and not df_comp.empty and id_comp in df_comp['id_competencia'].values:
        idx = df_comp.index[df_comp['id_competencia'] == id_comp].tolist()[0]
        for k, v in nuevo.items(): df_comp.at[idx, k] = v
        msg = "✅ Evento actualizado."
    else:
        df_comp = pd.concat([df_comp, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "✅ Evento creado."

    exito, _ = actualizar_con_retry("Competencias", df_comp)
    if exito: st.cache_data.clear(); return True, msg
    return False, "Error al guardar."

def eliminar_competencia(id_comp):
    df_comp = leer_dataset_fresco("Competencias")
    df_ins = leer_dataset_fresco("Inscripciones")
    if df_comp is None: return False, "Error."
    
    df_comp = df_comp[df_comp['id_competencia'] != id_comp]
    if df_ins is not None and not df_ins.empty:
        df_ins = df_ins[df_ins['id_competencia'] != id_comp]
        actualizar_con_retry("Inscripciones", df_ins)
    
    exito, _ = actualizar_con_retry("Competencias", df_comp)
    if exito: st.cache_data.clear(); return True, "Eliminado."
    return False, "Error."

def gestionar_inscripcion(id_comp, id_nadador, lista_pruebas):
    df_ins = leer_dataset_fresco("Inscripciones")
    if df_ins is None: df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])
    if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)

    pruebas_str = ", ".join(lista_pruebas)
    mask = (df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador)
    
    if not df_ins[mask].empty:
        df_ins.loc[mask, 'pruebas'] = pruebas_str
        df_ins.loc[mask, 'fecha_inscripcion'] = datetime.now().strftime("%Y-%m-%d")
        msg = "✏️ Modificado."
    else:
        nuevo = {"id_inscripcion": str(uuid.uuid4()), "id_competencia": id_comp, "codnadador": int(id_nadador), "pruebas": pruebas_str, "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d")}
        df_ins = pd.concat([df_ins, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "✅ Inscripto."

    exito, _ = actualizar_con_retry("Inscripciones", df_ins)
    if exito: st.cache_data.clear(); return True, msg
    return False, "Error."

def eliminar_inscripcion(id_comp, id_nadador):
    df_ins = leer_dataset_fresco("Inscripciones")
    if df_ins is None: return False, "Error."
    if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
    
    df_ins = df_ins[~((df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry("Inscripciones", df_ins)
    if exito: st.cache_data.clear(); return True, "Baja exitosa."
    return False, "Error."

# ==========================================
# 6. UI PRINCIPAL
# ==========================================

df_competencias, df_inscripciones, df_nadadores, df_piletas, df_tiempos, df_estilos, df_distancias = cargar_datos_agenda()

df_t_global = pd.DataFrame()
if df_tiempos is not None and not df_tiempos.empty:
    df_t_global = df_tiempos.copy()
    if not df_estilos.empty:
        df_t_global = df_t_global.merge(df_estilos.rename(columns={'descripcion': 'estilo_desc'}), on='codestilo', how='left')
    if not df_distancias.empty:
        df_t_global = df_t_global.merge(df_distancias.rename(columns={'descripcion': 'dist_desc'}), on='coddistancia', how='left')
        
    df_t_global['segundos'] = df_t_global['tiempo'].apply(lambda x: tiempo_a_seg(x) if pd.notnull(x) else 9999.0)
    df_t_global['codnadador'] = pd.to_numeric(df_t_global['codnadador'], errors='coerce').fillna(0).astype(int)

st.title("📅 Agenda de Torneos")
st.markdown(f"Usuario: **{mi_nombre}**")

# --- ADMIN: CREAR ---
if rol in ["M", "P"]:
    with st.expander("🛠️ Crear Nuevo Evento", expanded=False):
        with st.form("form_crear"):
            c1, c2 = st.columns(2)
            n_in = c1.text_input("Nombre Evento")
            opc_pil = df_piletas['codpileta'].tolist() if not df_piletas.empty else []
            p_in = c2.selectbox("Sede", opc_pil, format_func=lambda x: f"{df_piletas[df_piletas['codpileta']==x].iloc[0]['club']} - {df_piletas[df_piletas['codpileta']==x].iloc[0]['ubicacion']}" if opc_pil else x)
            
            c3, c4 = st.columns(2)
            f_in = c3.date_input("Fecha", min_value=datetime.today(), format="DD/MM/YYYY")
            h_in = c4.time_input("Hora", value=datetime.strptime("08:30", "%H:%M").time())
            
            c5, c6 = st.columns(2)
            fl_in = c5.date_input("Cierre Inscripción", min_value=datetime.today(), format="DD/MM/YYYY")
            cost_in = c6.number_input("Costo $", min_value=0, step=1000)
            
            hab_in = st.multiselect("Pruebas Habilitadas", LISTA_PRUEBAS, default=LISTA_PRUEBAS)
            d_in = st.text_area("Descripción")
            
            if st.form_submit_button("Guardar Evento"):
                if n_in and p_in:
                    ok, m = guardar_competencia(None, n_in, f_in, h_in, p_in, fl_in, cost_in, d_in, hab_in)
                    if ok: st.success(m); time.sleep(1); st.rerun()
                else: st.warning("Faltan datos.")

st.divider()

# --- LISTADO DE EVENTOS ---
if df_competencias is None or df_competencias.empty:
    st.info("No hay eventos.")
else:
    hoy = date.today()
    df_view = df_competencias.copy()
    if not df_view.empty:
        df_view['fecha_dt'] = pd.to_datetime(df_view['fecha_evento']).dt.date
        df_view = df_view.sort_values(by='fecha_dt', ascending=True)

    for _, row in df_view.iterrows():
        comp_id = row['id_competencia']
        
        # Info Pileta
        d_pil = df_piletas[df_piletas['codpileta'] == row['cod_pileta']]
        nom_pil = f"{d_pil.iloc[0]['club']} ({d_pil.iloc[0]['medida']})" if not d_pil.empty else row['cod_pileta']
        ubic_pil = d_pil.iloc[0]['ubicacion'] if not d_pil.empty else "-"

        f_lim = pd.to_datetime(row['fecha_limite']).date()
        dias_ev = (row['fecha_dt'] - hoy).days
        dias_cie = (f_lim - hoy).days
        
        abierta = True
        if dias_ev < 0: badge = "🔴 FINALIZADO"; bg = "#333"; abierta = False
        elif dias_cie < 0: badge = "🔒 CERRADA"; bg = "#E30613"; abierta = False
        else: badge = f"🟢 ABIERTA ({dias_cie} días)"; bg = "#2E7D32"

        # Tarjeta Visual Evento
        with st.container():
            st.markdown(f"""
            <div style="background-color: #262730; border: 1px solid #555; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <h3 style="margin:0; color:white;">{row['nombre_evento']}</h3>
                        <div style="color:#4CAF50; font-weight:bold; font-size:14px; margin-top:4px;">📅 {row['fecha_dt'].strftime('%d/%m/%Y')} | ⏰ {row['hora_inicio']}</div>
                    </div>
                    <span style="background-color:{bg}; color:white; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold; height:fit-content;">{badge}</span>
                </div>
                <hr style="border-color:#444; margin:8px 0;">
                <div style="display:flex; gap:15px; color:#ddd; font-size:13px; margin-bottom:8px;">
                    <div>📍 {nom_pil}</div>
                    <div>🏙️ {ubic_pil}</div>
                    <div>💰 ${int(row['costo']) if pd.notna(row['costo']) else 0}</div>
                </div>
                <div style="font-size:13px; color:#ccc;">{row['descripcion'] or ''}</div>
            </div>""", unsafe_allow_html=True)

            f_ins = df_inscripciones[df_inscripciones['id_competencia'] == comp_id]
            d_full = pd.DataFrame()
            if not f_ins.empty:
                d_full = f_ins.merge(df_nadadores, on="codnadador", how="left")
                d_full['Anio'] = d_full['fechanac'].dt.year
                d_full['Cat'] = d_full['Anio'].apply(calcular_categoria_master)
                d_full['Nombre'] = d_full['apellido'] + ", " + d_full['nombre']

            # === A. LISTA PÚBLICA DE INSCRIPTOS (NUEVA VISTA ORDENADA) ===
            with st.expander("📋 Ver Lista de Inscriptos"):
                if d_full.empty:
                    st.caption("Aún no hay nadadores inscriptos.")
                else:
                    for _, r_pub in d_full.iterrows():
                        nadador_nom = f"{r_pub['apellido']}, {r_pub['nombre']}"
                        df_t_nadador = df_t_global[df_t_global['codnadador'] == r_pub['codnadador']] if not df_t_global.empty else pd.DataFrame()

                        cat_chip = f"<span style='font-size: 11px; font-weight: bold; background-color: #E30613; padding: 4px 10px; border-radius: 12px; color: #fff;'>{r_pub['Cat']}</span>"
                        gen_chip = f"<span style='font-size: 11px; font-weight: bold; background-color: #4CAF50; padding: 4px 10px; border-radius: 12px; color: #fff;'>{r_pub['codgenero']}</span>"
                        
                        pruebas_lista = [p.strip() for p in str(r_pub['pruebas']).split(",") if p.strip()]
                        
                        # NUEVA GRILLA DE TARJETAS PARA LAS PRUEBAS
                        chips_html = "<div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; margin-top: 15px;'>"
                        
                        for p in pruebas_lista:
                            mejor_tiempo = buscar_mejor_tiempo(p, df_t_nadador)
                            
                            if mejor_tiempo:
                                # Diseño destacado (con tiempo)
                                tiempo_ui = f"<div style='background-color: rgba(255, 215, 0, 0.15); color: #FFD700; font-family: monospace; font-size: 14px; font-weight: bold; padding: 4px; border-radius: 4px; border: 1px solid rgba(255, 215, 0, 0.5); text-align: center; letter-spacing: 0.5px;'>⏱️ {mejor_tiempo}</div>"
                            else:
                                # Diseño sutil (sin tiempo)
                                tiempo_ui = f"<div style='background-color: rgba(255, 255, 255, 0.05); color: #777; font-family: monospace; font-size: 12px; padding: 4px; border-radius: 4px; border: 1px dashed #555; text-align: center;'>S/T</div>"
                                
                            chips_html += f"""
                            <div style='background-color: #1e1e24; border: 1px solid #333; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; justify-content: space-between; gap: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                                <div style='color: #ddd; font-size: 13px; font-weight: 600; text-align: center; line-height: 1.2;'>{p}</div>
                                {tiempo_ui}
                            </div>
                            """
                        chips_html += "</div>"

                        st.markdown(f"""
                        <div style="
                            background-color: #2b2c36; 
                            padding: 15px 18px; 
                            border-radius: 8px; 
                            margin-bottom: 12px; 
                            border-left: 5px solid #E30613;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #444; padding-bottom: 10px;">
                                <div style="font-weight: 800; color: white; font-size: 16px; text-transform: uppercase;">{nadador_nom}</div>
                                <div style="display: flex; gap: 8px;">
                                    {cat_chip}
                                    {gen_chip}
                                </div>
                            </div>
                            {chips_html}
                        </div>
                        """, unsafe_allow_html=True)

            # === B. INSCRIPCIÓN USUARIO ===
            ins_user = df_inscripciones[(df_inscripciones['id_competencia'] == comp_id) & (df_inscripciones['codnadador'] == mi_id)]
            esta = not ins_user.empty
            
            p_hab_str = str(row.get('pruebas_habilitadas', ""))
            p_hab = [x.strip() for x in p_hab_str.split(",")] if p_hab_str.strip() else LISTA_PRUEBAS

            if abierta or rol in ["M", "P"]:
                label = "✅ Gestionar Inscripción" if esta else "📝 Inscribirse"
                with st.expander(label):
                    prev = [x.strip() for x in str(ins_user.iloc[0]['pruebas']).split(",")] if esta else []
                    with st.form(f"f_{comp_id}"):
                        sel = st.multiselect("Pruebas Habilitadas", p_hab, default=[x for x in prev if x in p_hab])
                        c_ok, c_no = st.columns([3, 1])
                        with c_ok: sub = st.form_submit_button("💾 Guardar")
                        with c_no: 
                            delt = False
                            if esta: delt = st.form_submit_button("🗑️ Baja", type="secondary")
                        
                        if sub:
                            if not sel: st.error("Selecciona pruebas.")
                            else:
                                ok, m = gestionar_inscripcion(comp_id, mi_id, sel)
                                if ok: st.success(m); time.sleep(1); st.rerun()
                        if delt:
                            ok, m = eliminar_inscripcion(comp_id, mi_id)
                            if ok: st.warning(m); time.sleep(1); st.rerun()
            elif esta:
                st.success(f"✅ Inscripto en: {ins_user.iloc[0]['pruebas']}")

            # === C. PANEL ENTRENADOR ===
            if rol in ["M", "P"]:
                with st.expander(f"🛡️ Panel Entrenador ({row['nombre_evento']})"):
                    t1, t2, t3 = st.tabs(["❌ Gestión Bajas", "⚙️ Editar Evento", "🚀 Simulador"])
                    
                    with t1:
                        if d_full.empty:
                            st.caption("Nada para gestionar.")
                        else:
                            st.markdown("##### 🏊‍♂️ Nómina de Nadadores")
                            st.dataframe(
                                d_full[['Nombre', 'codgenero', 'Cat', 'pruebas']].rename(columns={'codgenero':'Gen', 'pruebas':'Pruebas Inscriptas'}),
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Pruebas Inscriptas": st.column_config.TextColumn("Pruebas Inscriptas", width="large")
                                }
                            )
                            
                            st.divider()
                            st.markdown("##### ⚠️ Eliminar Inscripción")
                            with st.container(border=True):
                                u_del = st.selectbox(
                                    "Seleccionar nadador para dar de baja:", 
                                    d_full['codnadador'].unique(), 
                                    format_func=lambda x: d_full[d_full['codnadador']==x]['Nombre'].values[0],
                                    key=f"s_del_{comp_id}"
                                )
                                if st.button("Confirmar Baja", key=f"b_del_{comp_id}", type="primary", use_container_width=True):
                                    eliminar_inscripcion(comp_id, u_del)
                                    st.rerun()

                    with t2:
                        l_pre = [x.strip() for x in str(row.get('pruebas_habilitadas', "")).split(",")] if str(row.get('pruebas_habilitadas', "")).strip() else LISTA_PRUEBAS
                        with st.form(f"ed_{comp_id}"):
                            ce1, ce2 = st.columns(2)
                            nn = ce1.text_input("Nombre", value=row['nombre_evento'])
                            nc = ce2.number_input("Costo", value=int(row['costo']) if pd.notna(row['costo']) else 0)
                            
                            ce3, ce4 = st.columns(2)
                            nf = ce3.date_input("Fecha", value=pd.to_datetime(row['fecha_dt']), format="DD/MM/YYYY")
                            nl = ce4.date_input("Cierre", value=pd.to_datetime(f_lim), format="DD/MM/YYYY")
                            
                            nh = st.multiselect("Pruebas", LISTA_PRUEBAS, default=[x for x in l_pre if x in LISTA_PRUEBAS])
                            nd = st.text_area("Desc.", value=row['descripcion'])
                            
                            if st.form_submit_button("Actualizar"):
                                guardar_competencia(comp_id, nn, nf, row['hora_inicio'], row['cod_pileta'], nl, nc, nd, nh)
                                st.rerun()
                            
                            if st.form_submit_button("⚠️ ELIMINAR EVENTO", type="primary"):
                                eliminar_competencia(comp_id); st.rerun()

                    with t3:
                        st.markdown("##### 🚀 Enviar Inscriptos al Simulador")
                        st.info("Lleva a todos los inscriptos de este evento directamente al Simulador para armar estrategias de postas óptimas y automáticas.")
                        
                        if not d_full.empty:
                            nombres_inscriptos = (d_full['apellido'].astype(str).str.upper() + ", " + d_full['nombre'].astype(str)).tolist()
                            
                            if st.button("Ir al Simulador con estos nadadores", key=f"btn_sim_comp_{comp_id}", type="primary", use_container_width=True):
                                st.session_state.simulador_pre_pool = nombres_inscriptos
                                if "pool_opt_g" in st.session_state:
                                    del st.session_state["pool_opt_g"]
                                st.switch_page("pages/3_simulador.py")
                        else:
                            st.warning("No podés acceder al simulador si no hay nadadores inscriptos.")
            
            st.markdown("</div>", unsafe_allow_html=True)
