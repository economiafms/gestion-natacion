"""Lectura de hojas de Google Sheets con caché por hoja.

Cada hoja se guarda en caché por separado (1 hora, igual que la caché interna de
conn.read). Al guardar o borrar algo, se invalida solo la hoja que cambió con
invalidar("Hoja"), en lugar de borrar toda la caché de la app: así la recarga
siguiente vuelve a pedir a Google solo esa hoja y no todas.

Antes de reescribir una hoja, las páginas usan leer_para_escribir("Hoja"): la lee en
fresco y no deja escribir si la lectura falla o llega incompleta (ver más abajo).
"""
import random
import time

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


# Columnas de las hojas que la app escribe, para cuando una hoja está totalmente vacía (sin títulos)
COLUMNAS = {
    "Inscripciones": ["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"],
    "Competencias": ["id_competencia", "nombre_evento", "fecha_evento", "hora_inicio", "cod_pileta", "fecha_limite",
                     "costo", "descripcion", "pruebas_habilitadas", "max_pruebas"],
    "Rutinas": ["id_rutina", "anio_rutina", "mes_rutina", "nro_sesion", "texto_rutina"],
    "Rutinas_Seguimiento": ["id_rutina", "codnadador", "fecha_realizada"],
    "Entrenamientos": ["id_entrenamiento", "fecha", "codnadador", "codestilo", "coddistancia", "coddistancia_parcial",
                       "tiempo_final", "parcial_1", "parcial_2", "parcial_3", "parcial_4", "observaciones"],
}


def _fresco(hoja, reintentos=4):
    """Hoja recién leída de Google, sin caché. None si no se pudo leer.
    Si Google pide esperar (cuota / error 429) se reintenta con pausas crecientes."""
    import pandas as pd
    conn = st.connection("gsheets", type=GSheetsConnection)
    for i in range(reintentos):
        try:
            return conn.read(worksheet=hoja, ttl=0).copy()
        except pd.errors.EmptyDataError:
            # La hoja está totalmente vacía (ni títulos): tabla vacía con sus columnas conocidas
            return pd.DataFrame(columns=COLUMNAS.get(hoja, []))
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                time.sleep(2 ** i + random.uniform(0, 1))
                continue
            return None
    return None


def leer_para_escribir(hoja):
    """Lectura segura justo antes de reescribir una hoja. None = NO escribir.

    Protege contra sobreescribir datos con una lectura vacía o a medias (por ejemplo,
    si se lee mientras otra sesión está escribiendo esa misma hoja):
      - Si la lectura falla -> None.
      - Si trae MENOS filas que la última copia conocida, espera y relee:
          * las dos lecturas no coinciden -> la hoja estaba cambiando -> None;
          * coinciden y no está vacía -> el cambio es real (se borró algo) -> se usa;
          * coinciden y está vacía habiendo datos antes -> None por esta vez (si de verdad
            se vació, el próximo intento ya la acepta).
    """
    df = _fresco(hoja)
    if df is None:
        return None
    try:
        esperado = len(_leer(hoja))
    except Exception:
        esperado = 0
    if len(df) >= esperado:
        return df
    time.sleep(1.5)
    df2 = _fresco(hoja)
    invalidar(hoja)                         # la copia conocida ya no sirve como referencia
    if df2 is None or len(df2) != len(df):
        return None
    if df2.empty and esperado > 0:
        return None
    return df2
