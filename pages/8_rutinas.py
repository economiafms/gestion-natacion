import streamlit as st

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Rutinas", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

# --- CONTENIDO ---
st.title("📝 Rutinas")
st.info("Sección en construcción. Esperando requerimientos.")
