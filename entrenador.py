"""El entrenador del club: tiene ficha en la hoja Nadadores pero no compite.

Se identifica por su número de socio (un solo lugar para cambiarlo). Su código de
nadador se busca en la hoja Nadadores, así no queda escrito en ninguna página.
No cuenta en categorías, padrones de categoría, activos ni top de medallistas.
"""
import pandas as pd
import streamlit as st

SOCIOS_ENTRENADOR = {"253973"}


def socio_txt(valor):
    """Número de socio limpio, igual que en el login: '253973.0' o '253973-01' -> '253973'."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    return str(valor).split("-")[0].split(".")[0].strip()


def es_entrenador():
    """True si quien inició sesión es el entrenador."""
    return socio_txt(st.session_state.get("nro_socio")) in SOCIOS_ENTRENADOR


def ids_entrenador(df_nad):
    """Códigos de nadador (como texto, '66') del entrenador según la hoja Nadadores."""
    if df_nad is None or df_nad.empty or 'nrosocio' not in df_nad.columns:
        return set()
    filas = df_nad[df_nad['nrosocio'].map(socio_txt).isin(SOCIOS_ENTRENADOR)]
    return {str(int(float(c))) for c in pd.to_numeric(filas['codnadador'], errors='coerce').dropna()}


def sin_entrenador(df_nad):
    """La hoja Nadadores sin el entrenador."""
    ids = ids_entrenador(df_nad)
    if not ids:
        return df_nad
    cod = pd.to_numeric(df_nad['codnadador'], errors='coerce')
    return df_nad[~cod.map(lambda c: str(int(c)) if pd.notna(c) else "").isin(ids)]
