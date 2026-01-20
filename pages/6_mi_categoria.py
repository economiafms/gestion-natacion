import streamlit as st

from streamlit_gsheets import GSheetsConnection

import pandas as pd



# --- CONFIGURACIÓN ---

st.set_page_config(page_title="Mi Categoría", layout="centered")



# --- SEGURIDAD ---

if "role" not in st.session_state or not st.session_state.role:

    st.warning("⚠️ Acceso denegado.")

    st.switch_page("index.py")



st.title("🏊 Mi Categoría y Objetivos")

st.info("🚧 Sección en construcción: Aquí verás el análisis de tu categoría y proyecciones.")
