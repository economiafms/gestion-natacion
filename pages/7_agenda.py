import streamlit as st

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Agenda", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

# --- CONTENIDO ---
st.title("📅 Agenda")
st.info("Sección en construcción. Esperando requerimientos.")
