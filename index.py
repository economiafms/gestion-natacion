import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Login - Gestión Natación", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. INYECCIÓN DE CSS (DISEÑO TAILWIND)
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@700;900&family=Inter:wght@400;700&family=JetBrains+Mono:wght@500;700&display=swap');

/* Reset de la aplicación para pantalla completa */
.stApp { background-color: #101319; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; height: 100vh !important; overflow: hidden !important; }

/* Estructura de columnas para el Split-Screen */
div[data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: center; height: 100vh; }
div[data-testid="column"] { padding: 0 !important; }

/* LADO IZQUIERDO: Imagen y Gradiente */
div[data-testid="column"]:nth-child(1) {
    background-image: linear-gradient(to top, #101319, rgba(16,19,25,0.5), transparent), url('https://lh3.googleusercontent.com/aida-public/AB6AXuAMImSYqudmvJAmPD0Phr4ZLP83MuhD9gER7FYwOcbdHShvlBwjDrZHfuCzvTK5SLGBU4QyXBq1u26JxNMbOmC6LPM_h89zpTZPRqSXFUyynCpinKtV0Epm-C911nEwPJtuXFva7BueE33Rqxf14YlEef9Jeg-4wEfBr_91ynAqTL-35-FYWXcJprpJQ7Oz7p1Eu3ouf2cTescVEqDFxWscFDlvIVFHG33RQwKys75VypSce4pvWZVKS5IeX1gawVmOuQ');
    background-size: cover;
    background-position: center;
    border-right: 1px solid #5e3f3b;
    height: 100vh !important;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    position: relative;
}

/* Ocultar lado izquierdo en móviles */
@media (max-width: 1024px) {
    div[data-testid="column"]:nth-child(1) { display: none !important; }
}

/* LADO DERECHO: Centrado del formulario */
div[data-testid="column"]:nth-child(2) > div[data-testid="stVerticalBlock"] {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 24px;
    height: 100vh;
}

/* Contenedor del Formulario (La Tarjeta) */
div[data-testid="stForm"] {
    background-color: #1d2026 !important;
    border-radius: 12px !important;
    padding: 40px 32px 32px 32px !important;
    border: 1px solid #5e3f3b !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
    position: relative !important;
    max-width: 450px !important;
    margin: 0 auto !important;
    width: 100% !important;
}

/* Barra lateral roja de acento */
div[data-testid="stForm"]::before {
    content: '';
    position: absolute; top: 0; left: 0; width: 4px; height: 100%; 
    background-color: #e30613; 
    border-top-left-radius: 12px; border-bottom-left-radius: 12px;
}

/* Tipografías y Inputs Nativos de Streamlit */
label[data-testid="stWidgetLabel"] p {
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase !important;
    color: #e9bcb6 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
}

div[data-testid="stTextInput"] input {
    background-color: #1E1E1E !important;
    border: 1px solid #444444 !important;
    color: white !important;
    padding: 12px 16px !important;
    border-radius: 4px !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #e30613 !important;
    box-shadow: none !important;
}

/* Estilo del Botón Acceder */
div[data-testid="stFormSubmitButton"] button {
    background-color: #e30613 !important;
    color: white !important;
    width: 100% !important;
    border: none !important;
    padding: 12px !important;
    border-radius: 4px !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    height: 48px !important;
    font-family: 'Inter', sans-serif !important;
    margin-top: 16px !important;
    transition: all 0.3s ease;
}
div[data-testid="stFormSubmitButton"] button:hover {
    background-color: #c0000c !important;
}

/* Estilo del Checkbox */
label[data-testid="stWidgetLabel"] div[role="button"] { background-color: #1E1E1E !important; border: 1px solid #444444 !important;}
label[data-testid="stWidgetLabel"] div[role="button"][aria-checked="true"] { background-color: #e30613 !important; border-color: #e30613 !important; }

/* Ocultar header móvil en desktop */
@media (min-width: 1024px) { .mobile-brand { display: none !important; } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE CONEXIÓN
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="10m")
def obtener_nadadores():
    try:
        return conn.read(worksheet="Nadadores")
    except Exception:
        return pd.DataFrame()

# ==========================================
# 4. ESTRUCTURA VISUAL (SPLIT SCREEN)
# ==========================================
col1, col2 = st.columns([1, 1])

# --- LADO IZQUIERDO (IMAGEN Y MARCA) ---
with col1:
    st.markdown("""
    <div style="height: 100vh; display: flex; flex-direction: column; justify-content: flex-end; padding: 48px; position: absolute; bottom: 0; left: 0; width: 100%; z-index: 10;">
        <div style="border-left: 4px solid #e30613; padding-left: 20px; margin-bottom: 24px;">
            <h1 style="font-family: 'Hanken Grotesk', sans-serif; font-size: 42px; font-weight: 900; color: #ffb4aa; text-transform: uppercase; margin:0; line-height: 1.1;">Gestión Natación</h1>
            <p style="font-family: 'Inter', sans-serif; font-size: 18px; color: #e9bcb6; margin-top: 8px; font-weight: 400;">Elite Performance Dashboard</p>
        </div>
        <div style="display: flex; gap: 12px;">
            <div style="background-color: rgba(39, 42, 49, 0.8); backdrop-filter: blur(4px); padding: 8px 16px; border-radius: 6px; border: 1px solid #5e3f3b; display: flex; align-items: center; gap: 8px;">
                <span style="color: #e30613; font-size: 20px;">⏱️</span>
                <span style="color: #e1e2eb; font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 700;">00:21.45</span>
            </div>
            <div style="background-color: rgba(39, 42, 49, 0.8); backdrop-filter: blur(4px); padding: 8px 16px; border-radius: 6px; border: 1px solid #5e3f3b; display: flex; align-items: center; gap: 8px;">
                <span style="color: #e9c400; font-size: 20px;">🏆</span>
                <span style="color: #e1e2eb; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700;">RECORD</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- LADO DERECHO (FORMULARIO DE LOGIN) ---
with col2:
    # Encabezado móvil (Solo se ve si la pantalla es chica)
    st.markdown("""
    <div class="mobile-brand" style="display: flex; align-items: center; gap: 12px; margin-bottom: 32px; justify-content: center;">
        <span style="font-size: 32px; color: #e30613;">🏊‍♂️</span>
        <span style="font-family: 'Hanken Grotesk', sans-serif; font-size: 28px; font-weight: 900; color: #ffb4aa; text-transform: uppercase;">Gestión Natación</span>
    </div>
    """, unsafe_allow_html=True)

    # Contenedor principal del formulario
    with st.form("login_form"):
        st.markdown("""
        <div style="margin-bottom: 24px;">
            <h2 style="font-family: 'Hanken Grotesk', sans-serif; font-size: 26px; font-weight: 700; color: #e1e2eb; margin:0 0 8px 0;">Acceso al Sistema</h2>
            <p style="font-family: 'Inter', sans-serif; color: #e9bcb6; font-size: 14px; margin:0;">Ingresa tus credenciales para acceder al panel de rendimiento.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Campos Nativos de Streamlit
        socio_id = st.text_input("NÚMERO DE SOCIO", placeholder="Ej: 123456")
        recordarme = st.checkbox("Recordarme en este dispositivo")
        submit = st.form_submit_button("Acceder ➔")
        
        # Pie de página del formulario
        st.markdown("""
        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #5e3f3b;">
            <p style="font-family: 'Inter', sans-serif; font-size: 12px; color: #e9bcb6; text-align: center; margin:0; line-height: 1.5;">
                Conexión segura bajo protocolos de Rojinegro Performance. <br/>
                ¿Necesitas ayuda? <a href="#" style="color: #ffb4aa; text-decoration: none; font-weight: 700;">Contactar a Soporte</a>
            </p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 5. LÓGICA DE AUTENTICACIÓN
# ==========================================
if submit:
    if not socio_id:
        st.error("⚠️ Por favor, ingresa tu número de socio.")
    else:
        with st.spinner("Validando credenciales..."):
            df_nadadores = obtener_nadadores()
            
            if df_nadadores.empty:
                st.error("❌ Error de conexión con la base de datos.")
            else:
                # Buscar al socio en la base
                match = df_nadadores[df_nadadores['codnadador'].astype(str) == str(socio_id).strip()]
                
                if not match.empty:
                    fila = match.iloc[0]
                    
                    # Identificar rol (M/P para Entrenadores, U para Nadadores)
                    rol = str(fila.get('rol', 'U')).strip().upper()
                    if rol not in ["M", "P"]:
                        rol = "U"
                    
                    # Generar Nombre Completo (Apellido, Nombre)
                    nombre_completo = f"{fila.get('apellido', '')}, {fila.get('nombre', '')}".upper()
                    
                    # Guardar variables de sesión globales
                    st.session_state.role = rol
                    st.session_state.user_id = int(fila['codnadador'])
                    st.session_state.user_name = nombre_completo
                    
                    # Redirigir al Dashboard Principal
                    st.switch_page("pages/1_inicio.py")
                
                # Acceso de contingencia/Desarrollador (Opcional, podés borrarlo si no lo necesitás)
                elif str(socio_id).strip().lower() == "admin":
                    st.session_state.role = "M"
                    st.session_state.user_id = 999999
                    st.session_state.user_name = "ADMINISTRADOR DEL SISTEMA"
                    st.switch_page("pages/1_inicio.py")
                    
                else:
                    st.error("🚫 Credenciales incorrectas. Verifica tu número de socio.")
