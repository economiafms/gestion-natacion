"""Lectura de hojas de Google Sheets con caché por hoja.

Cada hoja se guarda en caché por separado (1 hora, igual que la caché interna de
conn.read). Al guardar o borrar algo, se invalida solo la hoja que cambió con
invalidar("Hoja"), en lugar de borrar toda la caché de la app: así la recarga
siguiente vuelve a pedir a Google solo esa hoja y no todas.

Las escrituras no pasan por acá: antes de escribir, cada página sigue leyendo la
hoja en fresco (conn.read(..., ttl=0)) para no pisar cambios de otros.
"""
import streamlit as st
from streamlit_gsheets import GSheetsConnection


@st.cache_data(ttl="1h", show_spinner=False)
def _leer(hoja):
    conn = st.connection("gsheets", type=GSheetsConnection)
    # ttl=0: se saltea la caché interna de conn.read; la caché es la de esta función
    return conn.read(worksheet=hoja, ttl=0)


def leer(hoja):
    """Hoja como DataFrame (cada llamada devuelve una copia: se puede modificar sin afectar la caché)."""
    return _leer(hoja)


def invalidar(*hojas):
    """Descarta de la caché solo las hojas indicadas (llamar después de escribirlas)."""
    for h in hojas:
        _leer.clear(h)
