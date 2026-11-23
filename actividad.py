"""Nadadores activos: tienen al menos una marca de competencia (individual o relevo)
este año o el anterior. El resto se considera inactivo."""
from datetime import date

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


# Números de socio de los entrenadores: tienen ficha en Nadadores pero no compiten,
# así que no ven funciones de nadador (rutinas, inscripción, medallero, resumen del año).
SOCIOS_ENTRENADOR = {"364604"}


def es_entrenador():
    return str(st.session_state.get("nro_socio") or "").strip() in SOCIOS_ENTRENADOR


def anios_activos():
    hoy = date.today().year
    return [hoy - 1, hoy]


def id_txt(v):
    """Normaliza un código de nadador (66, 66.0, '66') a texto para comparar."""
    try:
        return str(int(float(v)))
    except Exception:
        return str(v).strip()


def ids_activos(tiempos, relevos, anios=None):
    """Códigos (texto) de los nadadores con alguna marca en los años dados."""
    anios = anios or anios_activos()
    ids = set()
    if tiempos is not None and not tiempos.empty and 'fecha' in tiempos.columns:
        t = tiempos[pd.to_datetime(tiempos['fecha'], errors='coerce').dt.year.isin(anios)]
        ids.update(id_txt(x) for x in t['codnadador'].dropna())
    if relevos is not None and not relevos.empty and 'fecha' in relevos.columns:
        r = relevos[pd.to_datetime(relevos['fecha'], errors='coerce').dt.year.isin(anios)]
        for k in range(1, 5):
            col = f'nadador_{k}'
            if col in r.columns:
                ids.update(id_txt(x) for x in r[col].dropna())
    return ids


@st.cache_data(ttl="1h", show_spinner=False)
def _ids_activos_cache(anios):
    conn = st.connection("gsheets", type=GSheetsConnection)
    return ids_activos(conn.read(worksheet="Tiempos"), conn.read(worksheet="Relevos"), list(anios))


def usuario_inactivo():
    """True solo para un nadador (rol N) sin marcas este año ni el anterior.
    Ante un error de lectura no se bloquea a nadie."""
    if st.session_state.get("role") != "N":
        return False
    try:
        return id_txt(st.session_state.get("user_id")) not in _ids_activos_cache(tuple(anios_activos()))
    except Exception:
        return False


def aviso_inactivo(que):
    anios = anios_activos()
    st.info(f"🔒 {que} está disponible para nadadores activos: con al menos una marca de competencia "
            f"en {anios[0]} o {anios[1]}. Hablá con tu entrenador si creés que es un error.")
