import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime, date
import random
import uuid

# --- 1. CONFIGURACIÓN DEL ÍCONO (ENLACE GITHUB RAW) ---
# Usamos el enlace RAW directo de GitHub. Esto es lo más compatible que existe.
# Asegúrate de que el archivo 'escudo.png' esté en la raíz de tu repo.
ICON_URL = "https://raw.githubusercontent.com/economiafms/gestion-natacion/main/escudo.png"

st.set_page_config(
    page_title="Acceso NOB", 
    layout="centered",
    page_icon=ICON_URL
)

# --- TRUCO PARA FORZAR ÍCONO EN ANDROID/IOS ---
# Inyectamos código HTML para intentar engañar al navegador del celular
# y que use nuestro escudo en lugar del logo de Streamlit.
st.markdown(f"""
    <style>
        /* Esto oculta el código inyectado para que no se vea en la pantalla */
        .app-icon-fix {{display: none;}}
    </style>
    <div class="app-icon-fix">
        <link rel="apple-touch-icon" sizes="180x180" href="{ICON_URL}">
        <link rel="icon" type="image/png" sizes="32x32" href="{ICON_URL}">
        <link rel="icon" type="image/png" sizes="16x16" href="{ICON_URL}">
    </div>
""", unsafe_allow_html=True)

# --- 2. GESTIÓN DE ESTADO ---
if "role" not in st.session_state: st.session_state.role = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "nro_socio" not in st.session_state: st.session_state.nro_socio = None
if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False 
if "ver_nadador_especifico" not in st.session_state: st.session_state.ver_nadador_especifico = None
if "show_login_form" not in st.session_state: st.session_state.show_login_form = False 

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1h")
def cargar_tablas_login():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "users": conn.read(worksheet="User")
        }
    except: return None

# --- 4. FUNCIONES LOGIN / LOGOUT ---
def limpiar_socio(valor):
    if pd.isna(valor): return ""
    return str(valor).split('.')[0].strip()

def validar_socio():
    raw_input = st.session_state.input_socio
    socio_limpio = raw_input.split("-")[0].strip()
    
    if not socio_limpio:
        st.warning("Ingrese un número.")
        return

    db = cargar_tablas_login()
    if db:
        df_u = db['users'].copy()
        df_n = db['nadadores'].copy()
        
        df_u['nrosocio_str'] = df_u['nrosocio'].apply(limpiar_socio)
        df_n['nrosocio_str'] = df_n['nrosocio'].apply(limpiar_socio)
        
        usuario = df_u[df_u['nrosocio_str'] == socio_limpio]
        
        if not usuario.empty:
            perfil = usuario.iloc[0]['perfil'].upper()
            datos = df_n[df_n['nrosocio_str'] == socio_limpio]
            
            if not datos.empty:
                st.session_state.role = perfil
                st.session_state.user_name = f"{datos.iloc[0]['nombre']} {datos.iloc[0]['apellido']}"
                st.session_state.user_id = datos.iloc[0]['codnadador']
                st.session_state.nro_socio = socio_limpio
                st.success(f"¡Bienvenido {datos.iloc[0]['nombre']}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Socio válido pero sin ficha de nadador activa.")
        else:
            st.error("Número de socio no registrado.")

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- FUNCIONES DE INSCRIPCIÓN RÁPIDA (AGREGADAS PARA WIDGET EN EL INDEX) ---
def actualizar_con_retry_index(worksheet, data, max_retries=5):
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
    return False, "Error de conexión."

@st.cache_data(ttl="5s")
def cargar_datos_inscripcion_index():
    try:
        df_comp = conn.read(worksheet="Competencias").copy()
        if not df_comp.empty:
            df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento'], errors='coerce')
            df_comp['fecha_limite'] = pd.to_datetime(df_comp['fecha_limite'], errors='coerce')
            
        df_ins = conn.read(worksheet="Inscripciones").copy()
        if not df_ins.empty:
            df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
        return df_comp, df_ins
    except:
        return None, None

def leer_dataset_fresco_index(worksheet):
    try: return conn.read(worksheet=worksheet, ttl=0).copy()
    except: return None

def gestionar_inscripcion_index(id_comp, id_nadador, lista_pruebas):
    df_ins = leer_dataset_fresco_index("Inscripciones")
    if df_ins is None: df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])
    if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)

    pruebas_str = ", ".join(lista_pruebas)
    mask = (df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador)
    
    if not df_ins[mask].empty:
        df_ins.loc[mask, 'pruebas'] = pruebas_str
        df_ins.loc[mask, 'fecha_inscripcion'] = datetime.now().strftime("%Y-%m-%d")
        msg = "Modificado."
    else:
        nuevo = {"id_inscripcion": str(uuid.uuid4()), "id_competencia": id_comp, "codnadador": int(id_nadador), "pruebas": pruebas_str, "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d")}
        df_ins = pd.concat([df_ins, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "Inscripto."

    exito, _ = actualizar_con_retry_index("Inscripciones", df_ins)
    if exito: st.cache_data.clear(); return True, msg
    return False, "Error."

def eliminar_inscripcion_index(id_comp, id_nadador):
    df_ins = leer_dataset_fresco_index("Inscripciones")
    if df_ins is None: return False, "Error."
    if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
    
    df_ins = df_ins[~((df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry_index("Inscripciones", df_ins)
    if exito: st.cache_data.clear(); return True, "Baja exitosa."
    return False, "Error."


# --- NUEVA FUNCIÓN: INSTRUCCIONES DE INSTALACIÓN ---
def pwa_install_button():
    st.write("---")
    with st.expander("📲 INSTALAR APP EN TU CELULAR"):
        st.markdown("""
        Puedes agregar esta aplicación a tu pantalla de inicio para un acceso más rápido:
        
        **🤖 Android (Chrome):**
        1. Toca los tres puntos **(⋮)** arriba a la derecha.
        2. Selecciona **'Instalar aplicación'** o 'Agregar a la pantalla de inicio'.
        
        **🍎 iPhone (Safari):**
        1. Toca el botón **Compartir** (cuadrado con flecha arriba) en la barra inferior.
        2. Desliza hacia abajo y toca en **'Agregar al inicio'**.
        """)
        st.info("Nota: Tenerla instalada te permite acceder más rápido a tus tiempos, rutinas, categoría y seguimiento personal. Es una herramienta pensada para acompañar tu evolución deportiva día a día. Tu progreso también se construye con constancia.")

# --- 5. PANTALLA DE LOGIN ---
def login_screen():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    st.markdown("""
        <style>
            .login-container {
                text-align: center;
                padding: 30px;
                border-radius: 20px;
                background: linear-gradient(180deg, #121212 0%, #000000 100%);
                border: 2px solid #333;
                margin-bottom: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            }
            .nob-title {
                font-size: 32px;
                font-weight: 900;
                color: #E30613;
                text-transform: uppercase;
                margin: 10px 0 5px 0;
                line-height: 1;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            }
            .nob-quote {
                font-size: 18px;
                font-style: italic;
                color: #ffffff;
                margin-bottom: 20px;
                font-family: serif;
                letter-spacing: 1px;
                opacity: 0.9;
            }
        </style>
        <div class="login-container">
            <div style="font-size: 40px; margin-bottom: 10px;">🔴⚫ 🏊 ⚫🔴</div>
            <div class="nob-title">NEWELL'S OLD BOYS</div>
            <div class="nob-quote">"Del deporte sos la gloria"</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#aaa; font-size:14px; margin-bottom:5px;'>ACCESO SOCIOS</div>", unsafe_allow_html=True)
    st.text_input("Ingrese Nro de Socio", key="input_socio", placeholder="Ej: 123456-01", label_visibility="collapsed")
    if st.button("INGRESAR", type="primary", use_container_width=True):
        validar_socio()
    
    # AGREGADO: Llamada a la función de instrucciones
    pwa_install_button()

# --- 6. DEFINICIÓN DE PÁGINAS ---
pg_inicio = st.Page("pages/1_inicio.py", title="Inicio", icon="🏠")
pg_datos = st.Page("pages/2_visualizar_datos.py", title="Fichero", icon="🗃️")
pg_ranking = st.Page("pages/4_ranking.py", title="Ranking", icon="🏆")
pg_simulador = st.Page("pages/3_simulador.py", title="Simulador", icon="⏱️")
pg_entrenamientos = st.Page("pages/5_entrenamientos.py", title="Entrenamientos", icon="🏋️")
pg_categoria = st.Page("pages/6_mi_categoria.py", title="Mi Categoría", icon="🏅")
pg_agenda = st.Page("pages/7_agenda.py", title="Agenda", icon="📅")
pg_rutinas = st.Page("pages/8_rutinas.py", title="Rutinas", icon="📝")
pg_carga = st.Page("pages/1_cargar_datos.py", title="Carga de Datos", icon="⚙️")
pg_login_obj = st.Page(login_screen, title="Acceso", icon="🔒")

# --- 7. RUTEO Y MENÚ ---
if not st.session_state.role:
    pg = st.navigation([pg_login_obj])
    pg.run()
else:
    # --- MENÚ PRINCIPAL ---
    menu_pages = {
        "Principal": [pg_inicio, pg_datos, pg_rutinas, pg_entrenamientos, pg_categoria, pg_agenda]
    }

    # --- MENÚ HERRAMIENTAS ---
    if st.session_state.role in ["M", "P"]:
        menu_pages["Herramientas"] = [pg_ranking, pg_simulador]

        if st.session_state.admin_unlocked:
            menu_pages["Administración"] = [pg_carga]

    pg = st.navigation(menu_pages)

    with st.sidebar:
        st.write("") 
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            cerrar_sesion()

        # --- WIDGET DE INSCRIPCIÓN RÁPIDA (SOLO PARA NADADORES 'N') ---
        if st.session_state.role == "N":
            st.divider()
            st.markdown("### 🏆 Inscripción Rápida")
            
            df_comp, df_ins = cargar_datos_inscripcion_index()
            
            if df_comp is not None and not df_comp.empty:
                hoy = date.today()
                df_view = df_comp.copy()
                df_view = df_view.sort_values(by='fecha_evento', ascending=True, na_position='last')
                
                hay_activos = False
                for _, row in df_view.iterrows():
                    f_ev = row['fecha_evento']
                    f_lim = row['fecha_limite']
                    
                    dias_ev = (f_ev.date() - hoy).days if pd.notnull(f_ev) else 0
                    dias_cie = (f_lim.date() - hoy).days if pd.notnull(f_lim) else 0
                    
                    if dias_ev >= 0 and dias_cie >= 0 and pd.notnull(f_ev) and pd.notnull(f_lim):
                        hay_activos = True
                        comp_id = row['id_competencia']
                        nombre_ev = row['nombre_evento']
                        
                        ins_user = pd.DataFrame()
                        if df_ins is not None and not df_ins.empty:
                            ins_user = df_ins[(df_ins['id_competencia'] == comp_id) & (df_ins['codnadador'] == st.session_state.user_id)]
                        
                        esta = not ins_user.empty
                        p_hab_str = str(row.get('pruebas_habilitadas', ""))
                        p_hab = [x.strip() for x in p_hab_str.split(",")] if p_hab_str.strip() else []
                        max_permitidas = int(row.get('max_pruebas', 10)) if pd.notna(row.get('max_pruebas')) else 10
                        
                        with st.expander(f"{'✅' if esta else '📝'} {nombre_ev}"):
                            prev = [x.strip() for x in str(ins_user.iloc[0]['pruebas']).split(",")] if esta else []
                            with st.form(f"f_idx_{comp_id}"):
                                st.caption(f"Permitido hasta {max_permitidas} pruebas.")
                                def_sel = [x for x in prev if x in p_hab][:max_permitidas]
                                sel = st.multiselect("Pruebas", p_hab, default=def_sel, max_selections=max_permitidas, label_visibility="collapsed")
                                
                                c_ok, c_no = st.columns([2, 1])
                                with c_ok: sub = st.form_submit_button("Guardar")
                                with c_no: 
                                    delt = False
                                    if esta: delt = st.form_submit_button("Baja")
                                
                                if sub:
                                    if not sel: st.error("Selecciona pruebas.")
                                    else:
                                        ok, m = gestionar_inscripcion_index(comp_id, st.session_state.user_id, sel)
                                        if ok: st.success("OK"); time.sleep(1); st.rerun()
                                if delt:
                                    ok, m = eliminar_inscripcion_index(comp_id, st.session_state.user_id)
                                    if ok: st.warning("Baja"); time.sleep(1); st.rerun()
                
                if not hay_activos:
                    st.info("No hay torneos activos para inscribirse.")
            else:
                st.info("No hay torneos activos para inscribirse.")

    pg.run()
