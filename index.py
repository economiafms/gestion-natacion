import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import json
import base64

# --- 1. CONFIGURACIÓN DEL ÍCONO ---
ICON_URL = "https://raw.githubusercontent.com/economiafms/gestion-natacion/main/escudo.png"

st.set_page_config(
    page_title="Acceso NOB", 
    layout="centered",
    page_icon=ICON_URL
)

# --- 💀 MANIFEST HACK V2: JAVASCRIPT ENFORCER ---
# Este bloque NO SOLO inyecta el manifiesto, sino que usa JavaScript
# para buscar y ELIMINAR cualquier manifiesto predeterminado de Streamlit
# que esté bloqueando el nuestro.

manifest_data = {
    "name": "Acceso NOB",
    "short_name": "NOB",
    "start_url": "./",
    "display": "standalone",
    "background_color": "#000000",
    "theme_color": "#E30613",
    "icons": [
        {"src": ICON_URL, "sizes": "192x192", "type": "image/png"},
        {"src": ICON_URL, "sizes": "512x512", "type": "image/png"}
    ]
}

manifest_json = json.dumps(manifest_data)
manifest_b64 = base64.b64encode(manifest_json.encode()).decode()

st.markdown(f"""
    <script>
        // Función para forzar el cambio de manifiesto
        function forceManifest() {{
            // 1. Buscar y eliminar manifiestos existentes (el de Streamlit)
            var existingManifests = document.querySelectorAll('link[rel="manifest"]');
            existingManifests.forEach(function(link) {{
                link.remove();
            }});

            // 2. Crear e inyectar nuestro manifiesto
            var newManifest = document.createElement('link');
            newManifest.rel = 'manifest';
            newManifest.href = 'data:application/manifest+json;base64,{manifest_b64}';
            document.head.appendChild(newManifest);

            // 3. Forzar iconos de Apple y Favicon
            var appleIcons = document.querySelectorAll('link[rel="apple-touch-icon"]');
            appleIcons.forEach(l => l.remove());
            
            var newApple = document.createElement('link');
            newApple.rel = 'apple-touch-icon';
            newApple.href = '{ICON_URL}';
            document.head.appendChild(newApple);
            
            console.log("Escudo NOB inyectado con éxito.");
        }}

        // Ejecutar inmediatamente y también esperar a que cargue todo
        forceManifest();
        window.addEventListener('load', forceManifest);
        
        // Ejecutar una vez más a los 2 segundos por si Streamlit lo sobreescribe tarde
        setTimeout(forceManifest, 2000);
    </script>
""", unsafe_allow_html=True)
# -----------------------------------------------------------

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

# --- NUEVA FUNCIÓN: INSTRUCCIONES DE INSTALACIÓN ---
def pwa_install_button():
    st.write("---")
    with st.expander("📲 INSTALAR APP EN TU CELULAR"):
        st.markdown("""
        **Instrucciones para ver el nuevo ícono:**
        
        Si ya tenías la app instalada, es muy probable que Android guarde el ícono viejo en caché.
        
        1. **Desinstala** la app actual.
        2. Abre Chrome y borra el caché (Configuración > Privacidad > Borrar datos de navegación > Imágenes y archivos en caché).
        3. Recarga esta página.
        4. Vuelve a instalar la aplicación.
        """)
        st.info("Nota: Este parche intenta forzar el ícono del club. Si persiste el logo de Streamlit, es una limitación forzosa del servidor gratuito.")

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

    pg.run()
