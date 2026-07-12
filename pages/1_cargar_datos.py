import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import random

# ==========================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# ==========================================
st.set_page_config(page_title="Carga de Datos", layout="wide")

if "role" not in st.session_state or st.session_state.role not in ["M", "P"]:
    st.switch_page("index.py")

if not st.session_state.get("admin_unlocked", False):
    st.switch_page("pages/1_inicio.py")

# ==========================================
# 2. CONEXIÓN A BASE DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def actualizar_con_retry(worksheet, data, max_retries=5):
    """Manejo robusto de la API con reintentos exponenciales"""
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
    return False, "Tiempo de espera agotado por límite de API de Google."

@st.cache_data(ttl="5m")
def cargar_tablas():
    """Carga inicial en caché"""
    try:
        n = conn.read(worksheet="Nadadores").copy()
        n['codnadador'] = pd.to_numeric(n['codnadador'], errors='coerce').fillna(0).astype(int)
        
        t = conn.read(worksheet="Tiempos").copy()
        r = conn.read(worksheet="Relevos").copy()
        c = conn.read(worksheet="Competencias").copy()
        
        # Parseo seguro de fecha en competencias
        if not c.empty and 'fecha_evento' in c.columns:
            c['fecha_evento'] = pd.to_datetime(c['fecha_evento'], errors='coerce')
            
        e = conn.read(worksheet="Estilos").copy()
        d = conn.read(worksheet="Distancias").copy()
        return n, t, r, c, e, d
    except Exception as e:
        st.error(f"Error crítico al leer datos: {e}")
        return None, None, None, None, None, None

def leer_dataset_fresco(worksheet):
    """Lectura sin caché para operaciones en tiempo real"""
    try:
        return conn.read(worksheet=worksheet, ttl=0).copy()
    except Exception as e:
        st.error(f"Error al leer hoja {worksheet}: {e}")
        return None

# Carga inicial
df_n, df_t, df_r, df_c, df_e, df_d = cargar_tablas()

# Verificaciones de seguridad
if df_n is None or df_e is None or df_d is None:
    st.stop()

# Diccionarios para selectores
dict_estilos = dict(zip(df_e['codestilo'], df_e['descripcion'])) if not df_e.empty else {}
dict_distancias = dict(zip(df_d['coddistancia'], df_d['descripcion'])) if not df_d.empty else {}

st.title("⚙️ Panel de Gestión Administrativa")
st.markdown("Carga y mantenimiento de datos del club.")

# ==========================================
# 3. INTERFAZ DE USUARIO CON TABS
# ==========================================
t1, t2, t3, t4, t5 = st.tabs([
    "⏱️ Cargar Tiempos", 
    "🏊‍♂️ Cargar Relevos", 
    "👥 Gestión Nadadores", 
    "📝 Fichas Técnicas",
    "🔒 Control Accesos"
])

# ------------------------------------------
# TAB 1: CARGAR TIEMPOS
# ------------------------------------------
with t1:
    st.header("Cargar Nuevo Registro Individual")
    with st.form("form_tiempo"):
        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)
        c7, c8, c9 = st.columns(3)
        
        opc_nad = dict(zip(df_n['codnadador'], df_n['apellido'] + ", " + df_n['nombre']))
        sel_n = c1.selectbox("Nadador", options=opc_nad.keys(), format_func=lambda x: opc_nad[x])
        sel_comp = c2.selectbox("Torneo", options=["-"] + df_c['id_competencia'].tolist(), format_func=lambda x: df_c[df_c['id_competencia']==x]['nombre_evento'].values[0] if x != "-" else "Sin especificar")
        sel_d = c3.selectbox("Distancia", options=dict_distancias.keys(), format_func=lambda x: dict_distancias[x])
        sel_e = c4.selectbox("Estilo", options=dict_estilos.keys(), format_func=lambda x: dict_estilos[x])
        sel_f = c5.date_input("Fecha")
        sel_p = c6.number_input("Posición (1=Oro, 2=Plata, 3=Bronce)", min_value=0, step=1)
        
        # Ingreso de tiempos (Min:Seg.Cent)
        m = c7.number_input("Min", 0, 59, 0)
        s = c8.number_input("Seg", 0, 59, 0)
        cen = c9.number_input("Cent", 0, 99, 0)
        
        t_form = f"{m:02d}:{s:02d}.{cen:02d}"
        
        if st.form_submit_button("Guardar Tiempo", type="primary"):
            df_t_fresh = leer_dataset_fresco("Tiempos")
            if df_t_fresh is not None:
                # Determinar evento y fecha final
                if sel_comp != "-" and not df_c[df_c['id_competencia'] == sel_comp].empty:
                    ev_nom = df_c[df_c['id_competencia'] == sel_comp]['nombre_evento'].values[0]
                    ev_fec = pd.to_datetime(df_c[df_c['id_competencia'] == sel_comp]['fecha_evento'].values[0]).strftime("%Y-%m-%d")
                else:
                    ev_nom = "-"
                    ev_fec = sel_f.strftime("%Y-%m-%d")

                nuevo = pd.DataFrame([{
                    "id_tiempo": str(uuid.uuid4()),
                    "codnadador": sel_n,
                    "id_competencia": sel_comp if sel_comp != "-" else "",
                    "coddistancia": sel_d,
                    "codestilo": sel_e,
                    "tiempo": t_form,
                    "fecha": ev_fec,
                    "evento": ev_nom,
                    "posicion": sel_p
                }])
                
                df_final = pd.concat([df_t_fresh, nuevo], ignore_index=True)
                exito, err = actualizar_con_retry("Tiempos", df_final)
                
                if exito:
                    st.success("✅ Tiempo guardado con éxito")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Error al guardar: {err}")

# ------------------------------------------
# TAB 2: CARGAR RELEVOS
# ------------------------------------------
with t2:
    st.header("Cargar Nuevo Relevo")
    with st.form("form_relevo"):
        cr1, cr2, cr3 = st.columns(3)
        cr4, cr5, cr6 = st.columns(3)
        
        # Solución estricta para garantizar IDs numéricos en Relevos[cite: 7]
        opc_nad_rel = {int(k): v for k, v in opc_nad.items() if str(k).isdigit() and int(k) > 0} 
        lista_opciones_rel = list(opc_nad_rel.keys())

        # Manejo de fallback por si la lista queda vacía tras el filtro estricto
        if not lista_opciones_rel:
            lista_opciones_rel = [0]
            opc_nad_rel = {0: "Sin Nadadores Disponibles"}

        sel_r_comp = cr1.selectbox("Torneo (Relevo)", options=["-"] + df_c['id_competencia'].tolist(), format_func=lambda x: df_c[df_c['id_competencia']==x]['nombre_evento'].values[0] if x != "-" else "Sin especificar")
        sel_r_d = cr2.selectbox("Distancia Relevo", options=dict_distancias.keys(), format_func=lambda x: dict_distancias[x])
        sel_r_e = cr3.selectbox("Estilo Relevo", options=dict_estilos.keys(), format_func=lambda x: dict_estilos[x])
        
        # Selectores estables con lista garantizada[cite: 7]
        n1 = cr4.selectbox("Nadador 1", options=lista_opciones_rel, format_func=lambda x: opc_nad_rel.get(x, str(x)))
        n2 = cr5.selectbox("Nadador 2", options=lista_opciones_rel, format_func=lambda x: opc_nad_rel.get(x, str(x)))
        n3 = cr6.selectbox("Nadador 3", options=lista_opciones_rel, format_func=lambda x: opc_nad_rel.get(x, str(x)))
        
        cr7, cr8, cr9 = st.columns(3)
        n4 = cr7.selectbox("Nadador 4", options=lista_opciones_rel, format_func=lambda x: opc_nad_rel.get(x, str(x)))
        sel_r_f = cr8.date_input("Fecha Relevo")
        sel_r_p = cr9.number_input("Posición Relevo", min_value=0, step=1)
        
        ct1, ct2, ct3 = st.columns(3)
        rm = ct1.number_input("Min (Relevo)", 0, 59, 0)
        rs = ct2.number_input("Seg (Relevo)", 0, 59, 0)
        rcen = ct3.number_input("Cent (Relevo)", 0, 99, 0)
        
        tr_form = f"{rm:02d}:{rs:02d}.{rcen:02d}"
        
        if st.form_submit_button("Guardar Relevo", type="primary"):
            # Validación extra para evitar guardar datos corruptos[cite: 7]
            if n1 == 0 or n2 == 0 or n3 == 0 or n4 == 0:
                 st.error("❌ Faltan nadadores válidos para registrar el relevo.")
            else:
                 df_r_fresh = leer_dataset_fresco("Relevos")
                 if df_r_fresh is not None:
                     if sel_r_comp != "-" and not df_c[df_c['id_competencia'] == sel_r_comp].empty:
                         ev_nom_r = df_c[df_c['id_competencia'] == sel_r_comp]['nombre_evento'].values[0]
                         ev_fec_r = pd.to_datetime(df_c[df_c['id_competencia'] == sel_r_comp]['fecha_evento'].values[0]).strftime("%Y-%m-%d")
                     else:
                         ev_nom_r = "-"
                         ev_fec_r = sel_r_f.strftime("%Y-%m-%d")
                     
                     nuevo_r = pd.DataFrame([{
                         "id_relevo": str(uuid.uuid4()),
                         "id_competencia": sel_r_comp if sel_r_comp != "-" else "",
                         "coddistancia": sel_r_d,
                         "codestilo": sel_r_e,
                         "nadador_1": n1,
                         "nadador_2": n2,
                         "nadador_3": n3,
                         "nadador_4": n4,
                         "tiempo": tr_form,
                         "fecha": ev_fec_r,
                         "evento": ev_nom_r,
                         "posicion": sel_r_p
                     }])
                     
                     df_final_r = pd.concat([df_r_fresh, nuevo_r], ignore_index=True)
                     exito, err = actualizar_con_retry("Relevos", df_final_r)
                     
                     if exito:
                         st.success("✅ Relevo guardado con éxito")
                         st.cache_data.clear()
                         time.sleep(1)
                         st.rerun()
                     else:
                         st.error(f"❌ Error al guardar: {err}")

# ------------------------------------------
# TAB 3: GESTIÓN NADADORES
# ------------------------------------------
with t3:
    st.header("Alta de Nadador")
    with st.form("form_alta_nadador"):
        cn1, cn2 = st.columns(2)
        n_nom = cn1.text_input("Nombre")
        n_ape = cn2.text_input("Apellido")
        
        cn3, cn4, cn5 = st.columns(3)
        n_fec = cn3.date_input("Fecha Nacimiento", min_value=datetime(1930, 1, 1), max_value=datetime.today())
        n_gen = cn4.selectbox("Género", ["M", "F"])
        n_soc = cn5.text_input("Nro Socio (Sin el -00)")
        
        if st.form_submit_button("Crear Nadador", type="primary"):
            if not n_nom or not n_ape or not n_soc:
                st.warning("Complete todos los campos.")
            else:
                df_n_fresh = leer_dataset_fresco("Nadadores")
                if df_n_fresh is not None:
                    # Generar nuevo codnadador
                    if df_n_fresh.empty:
                        nuevo_id = 1
                    else:
                        df_n_fresh['codnadador'] = pd.to_numeric(df_n_fresh['codnadador'], errors='coerce').fillna(0).astype(int)
                        nuevo_id = df_n_fresh['codnadador'].max() + 1
                    
                    nuevo_n = pd.DataFrame([{
                        "codnadador": nuevo_id,
                        "nombre": n_nom.strip(),
                        "apellido": n_ape.strip(),
                        "fechanac": n_fec.strftime("%Y-%m-%d"),
                        "codgenero": n_gen,
                        "nrosocio": n_soc.strip()
                    }])
                    
                    df_final_n = pd.concat([df_n_fresh, nuevo_n], ignore_index=True)
                    exito, err = actualizar_con_retry("Nadadores", df_final_n)
                    
                    if exito:
                        st.success(f"✅ Nadador creado. ID Asignado: {nuevo_id}")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Error al guardar: {err}")

# ------------------------------------------
# TAB 4: FICHAS TÉCNICAS (ABM)
# ------------------------------------------
with t4:
    st.header("Fichas Técnicas (Altura/Peso/Envergadura)")
    st.info("Registre las medidas biométricas del nadador para análisis técnico.")
    
    with st.form("form_fichas"):
        cf1, cf2 = st.columns(2)
        f_nad = cf1.selectbox("Seleccione Nadador", options=opc_nad.keys(), format_func=lambda x: opc_nad[x])
        f_fec = cf2.date_input("Fecha de Medición")
        
        cf3, cf4, cf5 = st.columns(3)
        f_alt = cf3.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.1)
        f_peso = cf4.number_input("Peso (kg)", min_value=30.0, max_value=150.0, value=70.0, step=0.1)
        f_env = cf5.number_input("Envergadura (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.1)
        
        if st.form_submit_button("Guardar Ficha", type="primary"):
            df_fichas_fresh = leer_dataset_fresco("Fichas")
            if df_fichas_fresh is None:
                df_fichas_fresh = pd.DataFrame(columns=["id_ficha", "codnadador", "fecha", "altura", "peso", "envergadura"])
                
            nuevo_f = pd.DataFrame([{
                "id_ficha": str(uuid.uuid4()),
                "codnadador": int(f_nad),
                "fecha": f_fec.strftime("%Y-%m-%d"),
                "altura": float(f_alt),
                "peso": float(f_peso),
                "envergadura": float(f_env)
            }])
            
            df_final_f = pd.concat([df_fichas_fresh, nuevo_f], ignore_index=True)
            exito, err = actualizar_con_retry("Fichas", df_final_f)
            
            if exito:
                st.success("✅ Ficha técnica registrada con éxito")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Error al guardar: {err}")

# ------------------------------------------
# TAB 5: CONTROL ACCESOS
# ------------------------------------------
with t5:
    st.header("Control de Accesos (Usuarios)")
    
    df_u = leer_dataset_fresco("User")
    if df_u is not None and not df_u.empty:
        st.dataframe(df_u, use_container_width=True, hide_index=True)
    
    with st.form("form_usuarios"):
        st.subheader("Crear / Actualizar Acceso")
        st.caption("Si el Nro Socio ya existe, se actualizará su perfil.")
        cu1, cu2 = st.columns(2)
        
        # Validar nro de socio
        u_socio = cu1.text_input("Nro Socio (Asociado al login)")
        u_rol = cu2.selectbox("Perfil", ["N", "M", "P"], help="N=Nadador, M=Manager, P=Profe")
        
        if st.form_submit_button("Guardar Acceso", type="primary"):
            if not u_socio:
                st.warning("Debe indicar el Nro de Socio.")
            else:
                u_socio_clean = u_socio.strip()
                if df_u is None:
                    df_u = pd.DataFrame(columns=["nrosocio", "perfil"])
                
                # Check si existe
                if not df_u.empty and u_socio_clean in df_u['nrosocio'].astype(str).str.strip().values:
                    df_u.loc[df_u['nrosocio'].astype(str).str.strip() == u_socio_clean, 'perfil'] = u_rol
                    msg = "✅ Acceso actualizado."
                else:
                    nuevo_u = pd.DataFrame([{"nrosocio": u_socio_clean, "perfil": u_rol}])
                    df_u = pd.concat([df_u, nuevo_u], ignore_index=True)
                    msg = "✅ Acceso creado."
                
                exito, err = actualizar_con_retry("User", df_u)
                if exito:
                    st.success(msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Error: {err}")
