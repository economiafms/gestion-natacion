"""Tema visual compartido y componentes motivacionales para todas las páginas."""
import base64
import html
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

ROJO = "#E30613"
RAIZ = Path(__file__).parent
ESCUDO_PATH = RAIZ / "escudo.png"
ESCUDO_URL = "https://raw.githubusercontent.com/economiafms/gestion-natacion/main/escudo.png"
# Escudo de Newell's (lado derecho del banner). Se muestra solo si el archivo está en la raíz del proyecto.
ESCUDO_NOB_CANDIDATOS = ["escudonob.png", "escudonob.svg", "escudonob.jpg", "escudonob.jpeg", "escudonob.webp"]

# Palabras que nunca deben aparecer en las frases motivadoras
PALABRAS_EXCLUIDAS = ["pecho", "gigante", "central"]

_FRASES_BASE = [
    "Cada largo cuenta. Hoy sumás uno más.",
    "La constancia le gana al talento cuando el talento no entrena.",
    "No se trata de ser el mejor, se trata de ser mejor que ayer.",
    "El agua no miente: lo que entrenás, se nota.",
    "Una brazada a la vez. Así se construyen los récords.",
    "Tu único rival está en el carril de tu propio reloj.",
    "Los campeones se hacen cuando nadie los mira.",
    "Cansado no es terminado. Una serie más.",
    "Disciplina hoy, orgullo mañana.",
    "Del deporte sos la gloria. ¡Vamos Newell's!",
    "Cada centésima que bajás es trabajo que se ve.",
    "Entrenar es invertir en tu mejor versión.",
    "El progreso no siempre se ve, pero siempre suma.",
    "Que el cronómetro sea tu motivación, no tu miedo.",
    "Hoy es un buen día para nadar tu mejor marca.",
    "El esfuerzo de hoy es la marca de mañana.",
    "Nadie se arrepiente de haber entrenado.",
    "La pileta es el lugar donde se forja el carácter.",
    "Pequeñas mejoras, todos los días, hacen grandes nadadores.",
    "El talento te pone en el agua; la disciplina te lleva al podio.",
    "Respirá, empujá la pared y andá por más.",
    "Los límites están para nadarlos de largo.",
    "Entrená como si la próxima competencia fuera mañana.",
    "Con la rojinegra, cada brazada vale doble.",
    "La mejor versión de vos está a un entrenamiento de distancia.",
]

FRASES = [f for f in _FRASES_BASE if not any(p in f.lower() for p in PALABRAS_EXCLUIDAS)]

_MIME = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _img_data_uri(ruta: Path) -> str:
    return f"data:{_MIME.get(ruta.suffix.lower(), 'image/png')};base64," + base64.b64encode(ruta.read_bytes()).decode()


@st.cache_data
def escudo_src() -> str:
    """Escudo embebido en base64 (no depende de internet); si falta el archivo usa GitHub."""
    try:
        return _img_data_uri(ESCUDO_PATH)
    except Exception:
        return ESCUDO_URL


@st.cache_data
def escudo_nob_src() -> str | None:
    """Escudo de Newell's para el lado derecho del banner, o None si el archivo no está."""
    for nombre in ESCUDO_NOB_CANDIDATOS:
        ruta = RAIZ / nombre
        if ruta.exists():
            try:
                if ruta.suffix.lower() == ".svg":
                    return _img_data_uri(ruta)
                # Achicar a 256 px: se muestra a 84 px y viaja embebido en cada página
                from io import BytesIO
                from PIL import Image
                img = Image.open(ruta).convert("RGBA")
                img.thumbnail((256, 256))
                buf = BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
            except Exception:
                return None
    return None


def ahora_arg():
    return datetime.now(timezone.utc) - timedelta(hours=3)


def frase_motivadora(pagina: str = "") -> str:
    """Frase al azar que cambia en cada ingreso (login) y es distinta en cada página.

    El orden se baraja una vez por sesión, así la frase no cambia con cada clic
    dentro de la misma página, pero sí la próxima vez que el nadador ingrese.
    """
    if "nob_frases_orden" not in st.session_state:
        orden = list(range(len(FRASES)))
        random.shuffle(orden)
        st.session_state.nob_frases_orden = orden
        st.session_state.nob_frases_pag = {}
    asignadas = st.session_state.nob_frases_pag
    if pagina not in asignadas:
        asignadas[pagina] = st.session_state.nob_frases_orden[len(asignadas) % len(FRASES)]
    return FRASES[asignadas[pagina]]


def hero(titulo: str, icono: str | None = None, subtitulo: str | None = None,
         saludar: bool | None = None, eyebrow: str = "Newell's Old Boys"):
    """Encabezado institucional: escudo, título y frase motivadora.

    `icono` y `saludar` se mantienen por compatibilidad con llamadas existentes, pero ya no se usan.
    """
    frase = html.escape(subtitulo) if subtitulo else html.escape(frase_motivadora(titulo))
    nob = escudo_nob_src()
    escudo_der = f'<img class="nob-hero-crest der" src="{nob}" alt="Escudo Newell\'s Old Boys">' if nob else ""
    st.markdown(
        f"""
        <div class="nob-hero">
            <div class="nob-hero-wave"></div>
            <img class="nob-hero-crest" src="{escudo_src()}" alt="Escudo Complejo Acuático">
            <div class="nob-hero-body">
                <div class="nob-hero-eyebrow">{html.escape(eyebrow)}</div>
                <div class="nob-hero-title">{html.escape(titulo)}</div>
                <div class="nob-hero-sub">“{frase}”</div>
            </div>
            {escudo_der}
        </div>
        """,
        unsafe_allow_html=True,
    )


def barra_movil(principales, nombre, extras, activo=None, web_izq=None, web_der=None, web_gestion=False):
    """Barra de navegación fija abajo, SOLO en el celular (en computadora no se muestra).

    Estructura (de arriba hacia abajo):
      - Panel desplegable con `extras`. Se abre/cierra con el "+" directamente en el navegador
        (un checkbox + CSS), sin recargar la página.
      - Fila principal fija de 5 botones `principales` (icono, etiqueta); el del medio es el
        botón central elevado y, si su icono es "escudo", muestra el escudo del club.
      - Franja inferior: nombre del nadador (va a Mi Ficha), botón "+" (solo si hay `extras`) y
        botón de cerrar sesión (siempre). El rincón derecho queda libre para el sello de Streamlit Cloud.

    Solo en la computadora (el celular no los muestra):
      - `web_izq` / `web_der`: (icono, etiqueta, activo) a la izquierda y a la derecha de la fila principal
        (para el manager: Simulador y Ranking).
      - `web_gestion`: "rueda" (pide clave) o "carga" (gestión desbloqueada: botón Cargar datos),
        en lugar del "+". None si no corresponde.

    `activo`: índice (0-4) de la página actual en la fila principal, o None.
    Devuelve ("principal", i) | ("ficha",) | ("extra", i) | ("salir",) |
             ("web_izq",) | ("web_der",) | ("gestion",) | ("carga",) | None.
    """
    css = [f'.st-key-bn_{i} button::after {{ content: "{e.replace(chr(34), "")}"; }}'
           for i, (_, e) in enumerate(principales)]
    if principales[2][0] == "escudo":
        css.append(
            '.st-key-bn_2 button p { visibility: hidden; }'
            f'.st-key-bn_2 button {{ background-image: url("{ESCUDO_URL}") !important; '
            'background-size: 50px 50px !important; background-position: center 6px !important; '
            'background-repeat: no-repeat !important; }'
        )
    if activo is not None:
        css.append(
            f'.st-key-bn_{activo} button::after {{ color: #FF4D57 !important; font-weight: 800 !important; }}'
            f'.st-key-bn_{activo} button {{ box-shadow: inset 0 2px 0 #E30613 !important; }}'
            if activo != 2 else
            # Rojo solo cuando se está en Inicio; en las demás secciones el escudo queda neutro
            '.st-key-nob_bottom_nav .st-key-bn_2 button { border-color: #E30613 !important; '
            'box-shadow: 0 0 0 3px rgba(227,6,19,0.35), 0 6px 18px rgba(227,6,19,0.45) !important; }'
            '.st-key-nob_bottom_nav .st-key-bn_2 button::after { color: #FF6A72 !important; }'
        )
    css += [f'.st-key-bnx_{i} button::after {{ content: "{e.replace(chr(34), "")}"; }}'
            for i, (_, e) in enumerate(extras)]
    for clave, lateral in (("bnw_izq", web_izq), ("bnw_der", web_der)):
        if lateral:
            css.append(f'.st-key-{clave} button::after {{ content: "{lateral[1].replace(chr(34), "")}"; }}')
            if lateral[2]:
                css.append(f'.st-key-{clave} button::after {{ color: #FF4D57 !important; font-weight: 800 !important; }}'
                           f'.st-key-{clave} button {{ box-shadow: inset 0 2px 0 #E30613 !important; }}')

    accion = None
    with st.container(key="nob_bottom_nav"):
        # Los estilos van dentro de la barra fija para no sumar espacio arriba de la página
        st.html(f"<style>{''.join(css)}</style>")

        if extras:
            # Siempre presente; se muestra solo cuando el "+" (checkbox) está activado
            with st.container(key="bn_panel"):
                for fila in range(0, len(extras), 2):
                    for col, (j, (icono, _)) in zip(st.columns(2, gap="small"),
                                                    list(enumerate(extras))[fila:fila + 2]):
                        with col:
                            if st.button(icono, key=f"bnx_{j}", use_container_width=True):
                                accion = ("extra", j)

        # Solo computadora: rueda de Gestión (en lugar del "+"); desbloqueada, se reemplaza por "Cargar datos"
        if web_gestion == "rueda":
            if st.button("", key="bnw_gestion", icon=":material/settings:", help="Gestión de competencias"):
                accion = ("gestion",)
        elif web_gestion == "carga":
            if st.button("", key="bnw_carga", icon=":material/upload_file:", help="Cargar datos"):
                accion = ("carga",)

        with st.container(key="bn_row"):
            # Simulador y Ranking (manager) son columnas más de la misma fila, a los extremos:
            # en la computadora se ven 7 accesos iguales; en el celular esas dos columnas se ocultan.
            n_cols = 5 + (1 if web_izq else 0) + (1 if web_der else 0)
            cols = list(st.columns(n_cols, gap="small"))
            if web_izq:
                with cols.pop(0):
                    if st.button(web_izq[0], key="bnw_izq", use_container_width=True):
                        accion = ("web_izq",)
            if web_der:
                with cols.pop():
                    if st.button(web_der[0], key="bnw_der", use_container_width=True):
                        accion = ("web_der",)
            for i, (col, (icono, _)) in enumerate(zip(cols, principales)):
                with col:
                    if st.button("·" if icono == "escudo" else icono, key=f"bn_{i}", use_container_width=True):
                        accion = ("principal", i)

        with st.container(key="bn_strip", horizontal=True, vertical_alignment="center"):
            if st.button(nombre, key="bn_nombre"):
                accion = ("ficha",)
            if extras:
                # `data-v` cambia en cada actualización de la página: el navegador redibuja el
                # interruptor y el panel vuelve a quedar cerrado (p. ej. después de elegir una opción).
                st.session_state.nob_nav_v = st.session_state.get("nob_nav_v", 0) + 1
                st.html(f'<label class="nob-mas-btn" title="Más opciones" data-v="{st.session_state.nob_nav_v}">'
                        '<input type="checkbox" id="nob-mas-chk">'
                        '<span class="mas">+</span><span class="cerrar">✕</span></label>')
            if st.button("", key="bn_salir", icon=":material/logout:", help="Cerrar sesión"):
                accion = ("salir",)

    return accion


GUIA_MANAGER = """
Esta guía detalla las herramientas disponibles para mi gestión, facilitando el análisis y la toma de decisiones.

**📂 Fichero**
Puedo consultar la ficha técnica completa de todos mis nadadores, incluyendo historial de competencias, mejores tiempos y relevos, con filtros para facilitar mi análisis.

**📝 Rutinas**
Permite crear, editar y asignar rutinas a mis nadadores, y verificar quiénes cumplen con los entrenamientos planificados.

**🏋️ Test**
Visualización de los tiempos de test de todos los nadadores para evaluar evolución y rendimiento.

**🏅 Mi categoría**
Visualización de nadadores agrupados por categorías para análisis comparativo.

**📅 Agenda**
Carga y edición de competencias, junto con la gestión de nadadores inscriptos.

**🏆 Ranking**
Visualización de los mejores tiempos por prueba para identificar a los nadadores más destacados.

**🏊 Simulador**
Simulación de escenarios manuales y automáticos de relevos para estimar tiempos basados en datos reales.

**⚙️ Cargar competencias**
Desde el botón CARGAR COMPETENCIAS de Inicio (o la rueda del menú en la computadora), con la palabra clave, puedo cargar nuevos nadadores, asignar permisos de Manager o Nadador y cargar tiempos de competencias y relevos.

---
**Aclaración final:**
* La carga diaria de datos deportivos es responsabilidad del nadador.
* Mi rol es analizar y tomar decisiones a partir de esa información.
"""

GUIA_NADADOR = """
Este sistema está diseñado para que cada nadador gestione y registre su propia información deportiva.
Cuantos más datos cargues, mejor vas a poder analizar tu rendimiento y evolución en el tiempo.

**👤 Ficha**
Encontrás todo lo relacionado a tu perfil deportivo: competencias, mejores tiempos, historial y relevos.
También podés consultar la ficha de un compañero si conocés su DNI.

**📝 Rutinas**
Accedés a las rutinas mensuales del entrenador, con una barra de progreso para saber en qué sesión estás y llevar un registro ordenado de tus entrenamientos.

**🏋️ Test**
Este módulo se utiliza para cargar los test de rendimiento.
Los test pueden incluir parciales, divididos en cuatro tramos según la distancia de la prueba. Recordá anotar los parciales según esta tabla.

50mts = 1x50  /  100mts = 4x25   /    200mts = 4x50 /     400mts = 4x100

**🏅 Mi categoría**
Visualizás los valores promedio de tu categoría y los nadadores que la integran, para comparar tus tiempos y rendimiento en competencias.

**📅 Agenda**
Encontrás las próximas competencias del equipo y podés registrarte de forma simple, reemplazando el registro en Excel por un sistema más dinámico.

---
**Aclaraciones importantes**
* La información es autogestionada por el nadador
* El entrenador no carga ni corrige datos
* Cada registro suma para tu mejora futura
* Uso personal, voluntario y a libre demanda
"""


# Ayuda de la página actual (lo que se puede tocar y qué muestra cada pestaña).
# Clave: título de la página en el menú. "comun" vale para ambos perfiles; "manager" se suma para el manager.
AYUDA_PAGINAS = {
    "Inicio": {
        "comun": """
- **Tu nombre** abre tu ficha completa.
- **Medallas (Oro, Plata, Bronce):** tocá una para ver tus podios de esa medalla. Dentro de la ventana podés cambiar de medalla tocando las otras.
- **Mis estilos frecuentes:** tocá un estilo para ver todos tus registros de ese estilo; si nadaste varias distancias, podés filtrarlas.
- **Mi entrenamiento de hoy:** marcá **DÍA GANADO** cuando termines la sesión.
- **El club y vos:** tu aporte a las medallas del club y el top medallistas del año. *Ver más estadísticas* abre los gráficos del club.
- **Botón central (escudo):** desde Inicio te lleva a tu ficha; desde otras páginas vuelve a Inicio.""",
        "manager": """
- **Ver padrón de nadadores** y el **botón central** (desde Inicio) abren el padrón.
- **Gestión:** con la palabra clave se habilita la carga de competencias.""",
    },
    "Fichero": {
        "comun": """
**Ficha**
- **Mejores marcas:** tocá una marca para ver todas las carreras de esa prueba, cuánto mejoraste, el promedio de tu categoría y tu puesto en ella.
- **📈 Evolución:** elegí estilo y distancia. Arriba: mejor marca, promedio, mejora desde la 1ª carrera (en rojo y negativo si empeoró) y la última carrera. En el gráfico, pasá el dedo o el mouse por cada punto para ver tiempo, fecha, sede, categoría y puesto; la ⭐ dorada es la mejor marca.
- **📜 Historial:** tus últimas 20 carreras; usá *Filtrar Historial* para elegir estilo y distancia.
- **🏊‍♂️ Mis relevos:** las postas en las que participaste, con los parciales de cada integrante.""",
        "nadador": """
**Compañero**
- Escribí el DNI de un compañero para ver su ficha.""",
        "manager": """
**Padrón**
- Todos los nadadores ordenados por medallas. Usá el buscador por nombre o apellido; **tocá una tarjeta** para abrir su ficha.

**Ficha**
- Elegí el atleta en la lista (podés escribir para buscarlo).

**Relevos**
- Historial de postas del club, con filtros por estilo y género.""",
    },
    "Rutinas": {"comun": """
- **Mes en curso:** las sesiones del mes; marcá **DÍA GANADO** al terminar cada una.
- **Historial:** tu asistencia de meses anteriores.
- Abrí el **Glosario de Referencias** para entender las abreviaturas de las rutinas."""},
    "Test": {"comun": """
- **Historial:** promedios y ritmos de tus tests, gráfico por estilo y registros con parciales.
- **Cargar Test:** registrá un test nuevo con sus parciales (50 = 1x50 · 100 = 4x25 · 200 = 4x50 · 400 = 4x100)."""},
    "Mi Categoría": {"comun": """
- Los nadadores de tu categoría y los tiempos promedio por estilo y distancia, para comparar tu rendimiento."""},
    "Categorías": {"comun": """
- Elegí una categoría y un género para ver sus nadadores (ordenados por edad, con quién está en su primer o último año) y los tiempos promedio por estilo y distancia."""},
    "Agenda": {
        "comun": """
- **Carrete de torneos (arriba):** deslizá para ver todos los eventos. Primero los próximos y, después de la línea *Finalizados*, los pasados. Tocá uno para ver sus datos debajo.
- Cada tarjeta muestra la fecha y el estado: **Abierta** (con los días que quedan para anotarse), **Inscripción cerrada** o **Finalizado**. El ✅ indica que estás inscripto.
- **Datos del torneo:** sede, costo, cierre de inscripción, cantidad de inscriptos y cuántas pruebas podés nadar.""",
        "nadador": """
- **📝 Mi inscripción:** elegí tus pruebas y tocá *Inscribirme*. Mientras la inscripción esté abierta podés cambiarlas o darte de baja. Al lado de cada prueba aparece tu mejor tiempo.
- **👥 Inscriptos:** quiénes van, filtrando por prueba, categoría o género.""",
        "manager": """
- **＋ Nuevo evento** (primera tarjeta del carrete): completá los 4 pasos (torneo, fecha y horario, inscripción e información) y tocá *Crear evento*.
- **👥 Inscriptos:** la lista con filtros, la planilla para descargar y el botón para dar de baja a un nadador.
- **➕ Inscribir:** anotá a cualquier nadador (o modificá sus pruebas si ya está inscripto).
- **⚙️ Editar:** cambiá cualquier dato del evento. Para eliminarlo, marcá la confirmación primero.
- **🚀 Simulador:** lleva a los inscriptos al Simulador para armar las postas.""",
    },
    "Ranking": {"comun": """
- Los mejores tiempos del club por prueba. Filtrá por estilo, distancia y género; en *Relevos*, las mejores postas."""},
    "Simulador": {"comun": """
- Armá postas manuales o automáticas para estimar el tiempo del relevo con los tiempos reales de los nadadores."""},
    "Carga de Datos": {"comun": """
- Cargá nadadores, tiempos individuales y relevos, y administrá los permisos (Manager / Nadador)."""},
}


@st.dialog("Guía rápida de uso", width="large")
def dialogo_guia(pagina=None):
    es_manager = st.session_state.get("role") in ["M", "P"]
    ayuda = AYUDA_PAGINAS.get(pagina or "")
    if ayuda:
        seccion(f"En esta página · {pagina}")
        texto = ayuda.get("comun", "") + (ayuda.get("manager", "") if es_manager else ayuda.get("nadador", ""))
        st.markdown(texto)
        st.write("")
    with st.expander("Guía general · " + ("Perfil Manager" if es_manager else "Perfil Nadador"), expanded=not ayuda):
        st.markdown(GUIA_MANAGER if es_manager else GUIA_NADADOR)


def chip_ayuda(pagina=None):
    """Chip "Guía rápida" arriba del banner; abre la ayuda de la página actual y la guía general."""
    with st.container(key="nob_ayuda"):
        if st.button("Guía rápida", key="nob_ayuda_btn", icon=":material/help:"):
            dialogo_guia(pagina)


def select_flechas(label, opciones, key, index=0, contenedor=None):
    """Selectbox con flechas ‹ › a los costados para pasar rápido de opción (da la vuelta al llegar al final)."""
    import streamlit as st
    opciones = list(opciones)
    if not opciones:
        return None
    if key in st.session_state and st.session_state[key] not in opciones:
        del st.session_state[key]

    def _mover(paso):
        actual = st.session_state.get(key, opciones[index])
        i = opciones.index(actual) if actual in opciones else 0
        st.session_state[key] = opciones[(i + paso) % len(opciones)]

    destino = contenedor if contenedor is not None else st
    with destino.container(key=f"selflecha_{key}", horizontal=True, vertical_alignment="bottom", gap="small"):
        st.button("", key=f"{key}_prev", icon=":material/chevron_left:", on_click=_mover, args=(-1,))
        # Si la flecha ya fijó el valor en session_state, no se pasa index (evita el aviso de Streamlit)
        extra = {} if key in st.session_state else {"index": index}
        valor = st.selectbox(label, opciones, key=key, **extra)
        st.button("", key=f"{key}_next", icon=":material/chevron_right:", on_click=_mover, args=(1,))
    return valor


def seccion(texto: str):
    st.markdown(f'<div class="nob-section">{html.escape(texto)}</div>', unsafe_allow_html=True)


def aplicar_tema():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        /* ---------- Base ---------- */
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(900px 420px at 0% -5%, rgba(227,6,19,0.16), transparent 60%),
                radial-gradient(700px 400px at 100% 105%, rgba(227,6,19,0.10), transparent 60%),
                #08090C;
        }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container { font-family: 'Inter', sans-serif; padding-top: 2.2rem; }
        .block-container p, .block-container li, .block-container label,
        .block-container input, .block-container textarea, .block-container button,
        .block-container h1, .block-container h2, .block-container h3,
        .block-container h4, .block-container h5 { font-family: 'Inter', sans-serif; }
        .block-container h1, .block-container h2, .block-container h3 { letter-spacing: -0.4px; }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111216 0%, #0A0B0E 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        [data-testid="stSidebarNav"] a { border-radius: 10px; }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: rgba(227,6,19,0.16);
        }

        /* ---------- Encabezado institucional ---------- */
        .nob-hero {
            position: relative; overflow: hidden;
            display: flex; align-items: center; gap: 20px;
            padding: 22px 24px; margin-bottom: 22px;
            border-radius: 20px;
            background: linear-gradient(120deg, #2A0306 0%, #160204 45%, #0E0F12 100%);
            border: 1px solid rgba(227,6,19,0.28);
            box-shadow: 0 18px 40px rgba(0,0,0,0.45);
            animation: nobUp .5s ease-out both;
        }
        .nob-hero::before {
            content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
            background: linear-gradient(90deg, #E30613 0%, #FF4D57 40%, rgba(227,6,19,0.15) 100%);
        }
        .nob-hero-wave {
            position: absolute; right: -80px; top: -90px; width: 260px; height: 260px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(227,6,19,0.28), transparent 65%);
        }
        .nob-hero-crest {
            position: relative; flex: 0 0 auto;
            width: 84px; height: 84px; object-fit: contain;
            filter: drop-shadow(0 8px 18px rgba(227,6,19,0.40));
        }
        .nob-hero-body { position: relative; min-width: 0; flex: 1 1 auto; }
        .nob-hero-crest.der { margin-left: auto; filter: drop-shadow(0 8px 18px rgba(0,0,0,0.5)); }
        .nob-hero-eyebrow {
            font-size: 11px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase;
            color: #FF4D57; margin-bottom: 4px; text-align: center;
        }
        .nob-hero-title {
            font-size: 28px; font-weight: 900; line-height: 1.1;
            color: #fff; letter-spacing: -0.6px; text-align: center;
        }
        .nob-hero-sub {
            margin-top: 8px; text-align: center;
            font-size: 14px; font-style: italic; line-height: 1.4; color: rgba(255,255,255,0.75);
        }
        /* Línea roja corta y centrada entre el título y la frase */
        .nob-hero-sub::before {
            content: ""; display: block; width: 36px; height: 2px; margin: 0 auto 8px;
            border-radius: 2px; background: rgba(227,6,19,0.8);
        }

        .nob-section {
            margin: 26px 0 12px; font-size: 12px; font-weight: 700;
            letter-spacing: 2px; text-transform: uppercase; color: rgba(255,255,255,0.55);
            display: flex; align-items: center; gap: 10px;
        }
        .nob-section::before { content: ""; width: 18px; height: 3px; border-radius: 3px; background: #E30613; }
        .nob-section::after { content: ""; flex: 1; height: 1px; background: rgba(255,255,255,0.08); }

        /* ---------- Superficie tipo "glass" para tarjetas existentes ---------- */
        .padron-card, .test-card, .swimmer-card, .mobile-card, .nob-card2 {
            background: linear-gradient(160deg, rgba(255,255,255,0.055), rgba(255,255,255,0.015)) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 28px rgba(0,0,0,0.35) !important;
            transition: transform .15s ease, border-color .15s ease;
        }
        /* Solo las tarjetas con acción se iluminan; las informativas no parecen seleccionables */
        .padron-card:hover { border-color: rgba(227,6,19,0.35) !important; }
        .swimmer-card, .test-card, .mobile-card { cursor: default; user-select: none; -webkit-user-select: none; }
        .cat-tag {
            display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 999px;
            font-size: 10px; font-weight: 800; letter-spacing: .4px; vertical-align: middle;
        }
        .cat-tag.sale  { background: rgba(255,193,7,0.14); color: #FFD54F; border: 1px solid rgba(255,193,7,0.45); }
        .cat-tag.entra { background: rgba(76,175,80,0.14); color: #7EE083; border: 1px solid rgba(76,175,80,0.45); }
        .test-card { border-left: 4px solid #E30613 !important; }
        .swimmer-card { border-left: 4px solid rgba(255,255,255,0.18) !important; }
        .swimmer-card.is-me {
            border-left: 4px solid #E30613 !important;
            background: linear-gradient(135deg, rgba(227,6,19,0.20), rgba(227,6,19,0.04)) !important;
        }
        .ficha-header {
            background: linear-gradient(135deg, #3A0307 0%, #1A0204 60%, #111 100%) !important;
            border: 1px solid rgba(227,6,19,0.35) !important; border-radius: 18px !important;
            box-shadow: 0 16px 36px rgba(0,0,0,0.45) !important;
        }
        .pb-row {
            background: rgba(255,255,255,0.04) !important; border-radius: 12px !important;
            border-left: 3px solid #E30613 !important;
        }
        .splits-container { background: rgba(0,0,0,0.25) !important; border-radius: 12px !important; border-color: rgba(255,255,255,0.06) !important; }
        .final-time { color: #FF3B45 !important; font-family: 'JetBrains Mono', ui-monospace, monospace !important; }
        .section-title, .pb-style-header { color: #FF3B45 !important; border-bottom-color: rgba(255,255,255,0.08) !important; letter-spacing: 1px; }

        /* ---------- Botones ---------- */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
            border-radius: 12px; font-weight: 700; letter-spacing: .3px;
            min-height: 44px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            transition: transform .12s ease, box-shadow .12s ease, filter .12s ease, border-color .12s;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover { border-color: #E30613; transform: translateY(-1px); }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
            border: none;
            background: linear-gradient(135deg, #FF1F2D 0%, #E30613 55%, #A8040E 100%);
            box-shadow: 0 8px 20px rgba(227,6,19,0.28);
        }
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
            filter: brightness(1.08); box-shadow: 0 12px 26px rgba(227,6,19,0.40);
        }

        /* ---------- Inputs ---------- */
        div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
            border-radius: 12px !important;
            background: rgba(255,255,255,0.04) !important;
            border-color: rgba(255,255,255,0.10) !important;
        }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
            border-color: #E30613 !important; box-shadow: 0 0 0 3px rgba(227,6,19,0.18) !important;
        }

        /* ---------- Expanders, forms, tabs ---------- */
        [data-testid="stExpander"] details {
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            background: rgba(255,255,255,0.025);
        }
        [data-testid="stExpander"] summary:hover { color: #FF3B45; }
        [data-testid="stForm"] {
            border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.02);
        }
        [role="tablist"] { gap: 8px !important; border-bottom: none !important; box-shadow: none !important; padding-bottom: 6px; }
        [data-testid="stTab"] {
            border-radius: 999px !important; padding: 6px 16px !important; height: auto !important;
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stTab"] p { color: rgba(255,255,255,0.75) !important; font-weight: 600; }
        [data-testid="stTab"][aria-selected="true"] { background: rgba(227,6,19,0.18); border-color: rgba(227,6,19,0.55); }
        [data-testid="stTab"][aria-selected="true"] p { color: #fff !important; }
        [data-testid="stTab"] .react-aria-SelectionIndicator { display: none; }

        /* ---------- Métricas, alertas, tablas ---------- */
        [data-testid="stMetric"] {
            background: linear-gradient(160deg, rgba(255,255,255,0.055), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 14px 16px;
        }
        [data-testid="stMetricValue"] { font-weight: 800; }
        [data-testid="stAlert"] { border-radius: 14px; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: 14px; overflow: hidden; }
        hr { border-color: rgba(255,255,255,0.07) !important; }
        [data-testid="stProgressBarTrack"] { border-radius: 999px !important; height: 10px !important; background: rgba(255,255,255,0.08) !important; }
        [data-testid="stProgressBarTrack"] > div { border-radius: 999px !important; background: linear-gradient(90deg, #E30613, #FF6A72) !important; }

        /* ---------- Componentes de Inicio ---------- */
        .nob-profile {
            display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: center;
            padding: 18px; border-radius: 18px; margin-bottom: 14px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-avatar {
            width: 56px; height: 56px; border-radius: 16px;
            display: grid; place-items: center;
            font-size: 22px; font-weight: 900; color: #fff;
            background: linear-gradient(135deg, #FF1F2D, #8E030B);
            box-shadow: 0 8px 18px rgba(227,6,19,0.35);
        }
        .nob-p-name { font-size: 18px; font-weight: 800; color: #fff; line-height: 1.2; }
        .nob-p-meta { font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 2px; }
        .nob-cat-badge {
            text-align: center; padding: 8px 14px; border-radius: 14px;
            background: rgba(76,175,80,0.12); border: 1px solid rgba(76,175,80,0.35);
        }
        .nob-cat-badge small { display: block; font-size: 10px; letter-spacing: 1.5px; color: rgba(255,255,255,0.55); text-transform: uppercase; }
        .nob-cat-badge b { font-size: 20px; color: #6FDB74; }

        .nob-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
        .nob-stat {
            text-align: center; padding: 14px 6px; border-radius: 16px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
        }
        .nob-stat .v { font-size: 24px; font-weight: 900; color: #fff; line-height: 1.1; }
        .nob-stat .l { font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: rgba(255,255,255,0.5); margin-top: 4px; }
        .nob-stat.gold   { border-color: rgba(255,215,0,0.35);  background: rgba(255,215,0,0.07); }
        .nob-stat.silver { border-color: rgba(200,200,200,0.30); background: rgba(200,200,200,0.06); }
        .nob-stat.bronze { border-color: rgba(205,127,50,0.35); background: rgba(205,127,50,0.07); }
        .nob-stat.total  { border-color: rgba(227,6,19,0.40); background: rgba(227,6,19,0.10); }

        .nob-goal {
            padding: 16px 18px; border-radius: 18px; margin-bottom: 14px;
            background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03));
            border: 1px solid rgba(227,6,19,0.30);
        }
        .nob-goal-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
        .nob-goal-top b { color: #fff; font-size: 15px; }
        .nob-goal-top span { color: rgba(255,255,255,0.7); font-size: 13px; font-weight: 600; }
        .nob-bar { height: 10px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
        .nob-bar > div { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #E30613, #FF6A72); }
        .nob-goal-msg { margin-top: 10px; font-size: 13px; color: rgba(255,255,255,0.75); }

        .nob-chip-row { display: flex; flex-wrap: wrap; gap: 8px; }
        .nob-chip {
            flex: 1 1 90px; text-align: center; padding: 12px 8px; border-radius: 14px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
        }
        .nob-chip .v { font-size: 22px; font-weight: 800; color: #fff; }
        .nob-chip .l { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: rgba(255,255,255,0.5); }

        /* ---------- Perfil interactivo (Inicio) ---------- */
        /* Tarjeta centrada estilo carnet */
        .st-key-nob_profile {
            padding: 22px 18px 18px; border-radius: 20px; margin-bottom: 4px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
            align-items: center; text-align: center; gap: 8px !important;
        }
        .st-key-nob_profile .nob-avatar { margin: 0 auto 12px; }
        .st-key-nob_profile [data-testid="stElementContainer"] { width: 100% !important; display: flex; justify-content: center; }
        .st-key-nob_profile [data-testid="stMarkdown"],
        .st-key-nob_profile [data-testid="stMarkdownContainer"] { width: 100% !important; }
        .nob-id-row {
            display: grid; grid-template-columns: repeat(3, 1fr);
            width: 100%; max-width: 460px; margin: 6px auto 0;
            padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.08);
        }
        .nob-id-row > div { padding: 2px 6px; text-align: center; }
        .nob-id-row > div + div { border-left: 1px solid rgba(255,255,255,0.10); }
        .nob-id-row small {
            display: block; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
            text-transform: uppercase; color: rgba(255,255,255,0.5);
        }
        .nob-id-row b { display: block; margin-top: 4px; font-size: 18px; font-weight: 800; color: #fff; }
        .nob-id-row b.cat { color: #6FDB74; }
        .st-key-nob_medals [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        .st-key-nob_medals [data-testid="stColumn"] { min-width: 0 !important; }

        /* Nombre como enlace a la ficha */
        .st-key-btn_nombre_perfil button {
            background: none !important; border: none !important; box-shadow: none !important;
            padding: 0 !important; min-height: 0 !important; justify-content: center !important;
            transform: none !important;
        }
        .st-key-btn_nombre_perfil button p {
            font-size: 26px !important; font-weight: 900 !important; color: #fff; text-align: center;
            line-height: 1.15; letter-spacing: -0.4px;
        }
        .st-key-btn_nombre_perfil button p::after {
            content: "  →"; color: #FF4D57; font-weight: 700; opacity: .0; transition: opacity .15s;
        }
        .st-key-btn_nombre_perfil button:hover p { color: #FF4D57 !important; }
        .st-key-btn_nombre_perfil button:hover p::after { opacity: 1; }
        .st-key-btn_nombre_perfil [data-testid="stTooltipHoverTarget"] { justify-content: center; }

        /* Medallas como tarjetas clicables */
        .st-key-nob_medals button {
            flex-direction: column !important; gap: 2px;
            min-height: 74px !important; border-radius: 16px !important;
        }
        .st-key-nob_medals button p { font-size: 22px !important; font-weight: 900 !important; color: #fff; }
        .st-key-nob_medals button::after {
            font-size: 10px; letter-spacing: 1.4px; font-weight: 700; color: rgba(255,255,255,0.5);
        }
        .st-key-med_oro button    { background: rgba(255,215,0,0.07) !important;  border-color: rgba(255,215,0,0.35) !important; }
        .st-key-med_plata button  { background: rgba(200,200,200,0.06) !important; border-color: rgba(200,200,200,0.30) !important; }
        .st-key-med_bronce button { background: rgba(205,127,50,0.07) !important; border-color: rgba(205,127,50,0.35) !important; }
        .st-key-med_oro button::after    { content: "ORO"; }
        .st-key-med_plata button::after  { content: "PLATA"; }
        .st-key-med_bronce button::after { content: "BRONCE"; }
        /* Total de podios: tarjeta informativa (sin acción) */
        .nob-med-info {
            min-height: 74px; border-radius: 16px; display: flex; flex-direction: column;
            align-items: center; justify-content: center; gap: 2px;
            background: rgba(227,6,19,0.10); border: 1px dashed rgba(227,6,19,0.40);
        }
        .nob-med-info .v { font-size: 22px; font-weight: 900; color: #fff; line-height: 1.3; }
        .nob-med-info .l { font-size: 10px; letter-spacing: 1.4px; font-weight: 700; color: rgba(255,255,255,0.5); text-transform: uppercase; }

        /* Estilos frecuentes: tarjetas simples (número + estilo), tocables */
        .st-key-nob_estilos [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        .st-key-nob_estilos [data-testid="stColumn"] { min-width: 0 !important; }
        .st-key-nob_estilos button {
            flex-direction: column !important; gap: 2px;
            min-height: 72px !important; border-radius: 14px !important;
            background: rgba(255,255,255,0.035) !important; border-color: rgba(255,255,255,0.08) !important;
        }
        .st-key-nob_estilos button p { font-size: 22px !important; font-weight: 800 !important; color: #fff; line-height: 1.1; }
        .st-key-nob_estilos button::after {
            font-size: 10px; letter-spacing: 1px; font-weight: 600; color: rgba(255,255,255,0.5);
            max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .st-key-nob_estilos button:hover { border-color: rgba(227,6,19,0.5) !important; transform: translateY(-2px); }

        /* Encabezado del detalle por estilo */
        .nob-est-head {
            padding: 14px 16px; border-radius: 16px; margin-bottom: 6px;
            background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03));
            border: 1px solid rgba(227,6,19,0.30);
        }
        .nob-est-head { text-align: center; padding: 18px 16px 16px; }
        .nob-est-name { font-size: 26px; font-weight: 900; color: #fff; text-transform: uppercase; letter-spacing: .5px; line-height: 1.1; }
        .nob-est-desc { margin-top: 4px; font-size: 13px; color: rgba(255,255,255,0.65); }
        .nob-medrow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; }
        .nob-medrow > div {
            padding: 10px 4px; border-radius: 14px; text-align: center;
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-medrow .v { font-size: 20px; font-weight: 900; color: #fff; line-height: 1.2; }
        .nob-medrow .l { font-size: 10px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: rgba(255,255,255,0.5); margin-top: 2px; }
        .nob-medrow .gold   { background: rgba(255,215,0,0.07);   border-color: rgba(255,215,0,0.35); }
        .nob-medrow .silver { background: rgba(200,200,200,0.06); border-color: rgba(200,200,200,0.30); }
        .nob-medrow .bronze { background: rgba(205,127,50,0.07);  border-color: rgba(205,127,50,0.35); }
        .nob-medrow .total  { background: rgba(227,6,19,0.10);    border-color: rgba(227,6,19,0.40); }
        /* ---------- Barra de navegación inferior: SOLO celular ---------- */
        .st-key-nob_bottom_nav { display: none !important; }
        /* El envoltorio de Streamlit alrededor de la barra no debe ocupar lugar ni sumar separación */
        :has(> .st-key-nob_bottom_nav) { display: contents !important; }
        .st-key-nob_bottom_nav > [data-testid="stElementContainer"]:has(style) { display: none; }

        /* ---------- El club y vos (Inicio) ---------- */
        .nob-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-bottom: 10px; }
        .nob-kpis > div {
            text-align: center; padding: 12px 6px; border-radius: 14px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
        }
        .nob-kpis b { display: block; font-size: 24px; font-weight: 900; color: #fff; line-height: 1.1; }
        .nob-kpis small { display: block; margin-top: 4px; font-size: 10px; font-weight: 700; letter-spacing: 1px;
                          text-transform: uppercase; color: rgba(255,255,255,0.5); }
        .nob-aporte {
            padding: 12px 14px; border-radius: 14px; margin-bottom: 12px; font-size: 14px; color: rgba(255,255,255,0.85);
            background: linear-gradient(135deg, rgba(227,6,19,0.14), rgba(227,6,19,0.03)); border: 1px solid rgba(227,6,19,0.28);
        }
        .nob-aporte b { color: #fff; }
        .nob-aporte summary { cursor: pointer; }
        .nob-aporte-lista { margin-top: 8px; font-size: 13px; color: rgba(255,255,255,0.7); line-height: 1.5; }
        .nob-top-tit { font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
                       color: rgba(255,255,255,0.5); margin: 4px 0 6px; }
        .nob-top {
            display: flex; align-items: center; gap: 10px; padding: 9px 12px; margin-bottom: 6px; border-radius: 12px;
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
        }
        .nob-top.yo { background: rgba(227,6,19,0.12); border-color: rgba(227,6,19,0.4); }
        .nob-top .p { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; flex: 0 0 auto;
                      font-size: 12px; font-weight: 800; background: rgba(255,255,255,0.08); color: #fff; }
        .nob-top .n { flex: 1; min-width: 0; font-size: 14px; font-weight: 700; color: #fff;
                      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .nob-top .m { font-size: 13px; color: rgba(255,255,255,0.8); white-space: nowrap; }
        .nob-top .t { font-size: 14px; font-weight: 800; color: #fff; white-space: nowrap; }
        .nob-top-pos { font-size: 12px; color: rgba(255,255,255,0.6); text-align: right; margin-top: 2px; }
        @media (max-width: 520px) { .nob-kpis { grid-template-columns: repeat(2, 1fr); } }

        /* ---------- Fichero: cabecera de la ficha y padrón, con el estilo de Inicio ---------- */
        .nob-fh {
            text-align: center; padding: 20px 16px 16px; border-radius: 20px; margin-bottom: 6px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-fh-name { font-size: 26px; font-weight: 900; color: #fff; line-height: 1.15; letter-spacing: -0.4px; }
        .nob-fh-sub { margin-top: 4px; font-size: 12px; color: rgba(255,255,255,0.5); }
        .nob-pb-est { margin: 10px 0 6px; font-size: 12px; font-weight: 800; letter-spacing: 1px;
                      text-transform: uppercase; color: #FF4D57; }
        .nob-pad { margin-bottom: 0 !important; flex: 1; min-width: 0; }
        /* ---------- Ficha técnica ---------- */
        /* Mejores marcas: una tarjeta por estilo con una fila por distancia (fila tocable) */
        [class*="st-key-pbcard_"] {
            gap: 0 !important; margin-bottom: 10px; border-radius: 16px; overflow: hidden;
            background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-pbc-tit {
            padding: 10px 14px 8px; font-size: 12px; font-weight: 800; letter-spacing: 1.2px;
            text-transform: uppercase; color: #FF4D57;
        }
        [class*="st-key-pbr_"] { position: relative; gap: 0 !important; }
        .nob-pbr { border-top: 1px solid rgba(255,255,255,0.06); }
        [class*="st-key-pbr_"] > [data-testid="stElementContainer"]:has(button) {
            position: absolute !important; inset: 0; width: 100% !important; z-index: 2; margin: 0 !important;
        }
        [class*="st-key-pbr_"] [data-testid="stButton"], [class*="st-key-pbr_"] button {
            width: 100% !important; height: 100% !important; min-height: 100% !important;
        }
        [class*="st-key-pbr_"] button { opacity: 0 !important; cursor: pointer; }
        [class*="st-key-pbr_"]:hover .nob-pbr { background: rgba(227,6,19,0.08); }
        .nob-pbr { display: flex; align-items: center; gap: 12px; padding: 10px 14px; }
        .nob-pbr .d {
            flex: 0 0 auto; min-width: 54px; text-align: center; padding: 6px 8px; border-radius: 10px;
            font-size: 14px; font-weight: 800; color: #fff; background: rgba(227,6,19,0.14); border: 1px solid rgba(227,6,19,0.35);
        }
        .nob-pbr .t { flex: 1 1 auto; min-width: 0; }
        .nob-pbr .t b { display: block; font-family: ui-monospace, 'JetBrains Mono', monospace; font-size: 20px; font-weight: 800; color: #fff; line-height: 1.2; }
        .nob-pbr .t small { display: block; margin-top: 2px; font-size: 12.5px; color: rgba(255,255,255,0.65); }
        .nob-pbr .ir { font-size: 22px; color: rgba(255,255,255,0.35); }
        .nob-kpis b.up { color: #6FDB74; }
        .nob-kpis b.down { color: #FF5A5F; }

        /* Pestañas en el celular: siempre todas visibles en una fila (sin tener que deslizar) */
        @media (max-width: 640px) {
            [role="tablist"] { flex-wrap: nowrap !important; overflow: hidden !important; gap: 4px !important; }
            [data-testid="stTab"] { flex: 1 1 0 !important; min-width: 0 !important; padding: 6px 4px !important; justify-content: center; }
            [data-testid="stTab"] p { font-size: 12.5px !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        }
        /* Ficha original: cada mejor marca es tocable (botón invisible encima, mismo aspecto) */
        [class*="st-key-pbo_"] { position: relative; gap: 0 !important; }
        [class*="st-key-pbo_"] > [data-testid="stElementContainer"]:has(button) {
            position: absolute !important; inset: 0; width: 100% !important; z-index: 2; margin: 0 !important;
        }
        [class*="st-key-pbo_"] [data-testid="stButton"], [class*="st-key-pbo_"] button {
            width: 100% !important; height: 100% !important; min-height: 100% !important;
        }
        [class*="st-key-pbo_"] button { opacity: 0 !important; cursor: pointer; }
        [class*="st-key-pbo_"]:hover .pb-row { background: rgba(227,6,19,0.10) !important; }
        /* Separación entre las mejores marcas y las pestañas Evolución / Historial / Mis relevos */
        .nob-sep-ficha {
            height: 1px; margin: 22px 0 14px;
            background: linear-gradient(90deg, transparent, rgba(227,6,19,0.55), transparent);
        }
        /* Ventana "Detalle de la mejor marca" */
        .nob-mm-time { margin-top: 6px; font-family: ui-monospace, 'JetBrains Mono', monospace; font-size: 30px; font-weight: 900; color: #fff; }
        .nob-mm-frases { display: flex; flex-direction: column; gap: 8px; margin: 12px 0 4px; }
        .nob-mm-frases > div {
            padding: 10px 12px; border-radius: 12px; font-size: 14px; line-height: 1.4; color: rgba(255,255,255,0.85);
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
        }
        .nob-mm-frases b { color: #fff; }

        /* Selector de nadador del manager: ← lista →, en una fila */
        /* Inicio: la celda Categoría de la tarjeta de perfil abre Mi Categoría */
        .st-key-nob_idrow { position: relative; gap: 0 !important; }
        .st-key-nob_idrow .st-key-btn_cat_perfil {
            position: absolute !important; left: 0; top: 0; width: 33.3% !important; height: 100%; z-index: 2;
        }
        .st-key-nob_idrow .st-key-btn_cat_perfil button {
            width: 100% !important; height: 100% !important; min-height: 0 !important; opacity: 0; cursor: pointer;
        }
        .st-key-nob_idrow:has(.st-key-btn_cat_perfil button:hover) .cat-link b { text-decoration: underline; }
        [class*="st-key-selflecha_"] { flex-wrap: nowrap !important; }
        [class*="st-key-selflecha_"] > [data-testid="stElementContainer"]:has([data-testid="stSelectbox"]) { flex: 1 1 auto; min-width: 0; }
        [class*="st-key-selflecha_"] button { min-height: 40px !important; min-width: 40px; padding: 0 6px !important; border-radius: 12px !important; }
        .st-key-ficha_selector { flex-wrap: nowrap !important; margin-bottom: 8px; }
        .st-key-ficha_selector > [data-testid="stElementContainer"]:has([data-testid="stSelectbox"]) { flex: 1 1 auto; min-width: 0; }
        .st-key-ficha_selector button { min-height: 42px !important; min-width: 42px; padding: 0 8px !important; border-radius: 12px !important; }

        /* Padrón: toda la tarjeta es tocable (un botón invisible la cubre) */
        [class*="st-key-pad_"] { position: relative; margin-bottom: 8px; flex-wrap: nowrap !important; }
        [class*="st-key-pad_"] > [data-testid="stElementContainer"]:first-child { flex: 1 1 auto; min-width: 0; }
        [class*="st-key-pad_"] > [data-testid="stElementContainer"]:has(button) {
            position: absolute !important; inset: 0; width: 100% !important; z-index: 2; margin: 0 !important;
        }
        [class*="st-key-pad_"] [data-testid="stButton"], [class*="st-key-pad_"] button {
            width: 100% !important; height: 100% !important; min-height: 100% !important;
        }
        [class*="st-key-pad_"] button { opacity: 0 !important; cursor: pointer; }
        [class*="st-key-pad_"]:hover .padron-card { border-color: rgba(227,6,19,0.55) !important; }
        /* Celular: la categoría siempre en un renglón; la columna derecha toma el espacio que necesita */
        .padron-card .p-cat, .padron-card .p-total { white-space: nowrap; }
        @media (max-width: 520px) {
            .padron-card .p-col-right { flex: 0 0 auto; padding-left: 8px; border-left-width: 1px; }
            .padron-card .p-col-center { flex: 1 1 auto; padding: 0 6px; }
            .padron-card .p-col-left { flex: 2 1 0; min-width: 0; padding-right: 8px; }
            /* Edad y género en un solo renglón (letra un poco menor en el celular) */
            .padron-card .p-meta { font-size: 11.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            /* El nombre se ve siempre completo (si es largo, usa dos renglones) */
            .padron-card .p-name { white-space: normal; overflow-wrap: anywhere; line-height: 1.2; }
            .padron-card .p-medals { gap: 4px; font-size: 14px; }
        }
        /* Celulares muy angostos: se omite "(al 31/12)" para que la edad entre completa */
        @media (max-width: 380px) {
            .padron-card .p-al { display: none; }
        }

        /* Filtro por distancia en el detalle por estilo: centrado arriba de la ficha */
        .st-key-dlg_est_filtro { align-items: center; margin-bottom: 4px; }

        /* Chip "Guía rápida": fijo arriba de todo a la izquierda, en la franja superior de la página */
        :has(> .st-key-nob_ayuda) { display: contents !important; }
        .st-key-nob_ayuda {
            position: fixed !important; top: 14px; left: 16px; z-index: 1000001;
            width: auto !important;
        }
        /* Computadora: alineado con el borde izquierdo del banner (columna central de 704 px) */
        @media (min-width: 901px) {
            .st-key-nob_ayuda { left: max(16px, calc(50% - 352px)); }
        }
        .st-key-nob_ayuda button {
            min-height: 30px !important; padding: 2px 12px !important; border-radius: 999px !important;
            background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.14) !important;
            box-shadow: none !important; gap: 6px;
        }
        .st-key-nob_ayuda button:hover { border-color: #E30613 !important; }
        .st-key-nob_ayuda button p { font-size: 12px !important; font-weight: 600 !important; color: rgba(255,255,255,0.8); }
        .st-key-nob_ayuda button [data-testid="stIconMaterial"] { font-size: 16px !important; color: #FF6A72; }

        /* Botón "+" (manager): interruptor del navegador, abre/cierra el panel SIN recargar la página */
        .nob-mas-btn {
            display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
            box-sizing: border-box; user-select: none; -webkit-tap-highlight-color: transparent;
            transition: border-color .15s ease, background .15s ease;
        }
        .nob-mas-btn input { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
        .nob-mas-btn span { font-size: 24px; font-weight: 400; line-height: 1; color: #fff; }
        .nob-mas-btn .cerrar { display: none; font-size: 20px; }
        .nob-mas-btn:has(input:checked) .mas { display: none; }
        .nob-mas-btn:has(input:checked) .cerrar { display: inline; }
        .nob-mas-btn:has(input:checked) { border-color: #E30613 !important; }
        .st-key-bn_panel { display: none !important; }
        /* Botones solo para la computadora (manager): ocultos por defecto */
        :is(.st-key-bnw_gestion, .st-key-bnw_carga) { display: none !important; }
        .st-key-nob_bottom_nav:has(#nob-mas-chk:checked) .st-key-bn_panel { display: flex !important; }
        @media (max-width: 900px) {
            .st-key-nob_bottom_nav {
                display: flex !important; position: fixed; left: 0; right: 0; bottom: 0; z-index: 999990;
                gap: 0 !important;
                padding: 4px 6px calc(4px + env(safe-area-inset-bottom));
                background: rgba(10,11,14,0.97); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                border-top: 1px solid rgba(255,255,255,0.08);
            }
            /* Ocultar el menú lateral en el celular / tablet: todo está en la barra */
            [data-testid="stExpandSidebarButton"], [data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"] { display: none !important; }

            /* Fila principal fija (Simulador / Ranking del manager solo se ven en la computadora) */
            .st-key-bn_row { margin-top: 4px; }
            .st-key-bn_row [data-testid="stColumn"]:has(.st-key-bnw_izq),
            .st-key-bn_row [data-testid="stColumn"]:has(.st-key-bnw_der) { display: none !important; }
            .st-key-bn_row [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 2px !important; align-items: flex-end; }
            .st-key-bn_row [data-testid="stColumn"] { min-width: 0 !important; }
            .st-key-bn_row button {
                flex-direction: column !important; gap: 2px; min-height: 64px !important; padding: 6px 0 !important;
                background: transparent !important; border: none !important; box-shadow: none !important; transform: none !important;
            }
            .st-key-bn_row button p { font-size: 26px !important; line-height: 1.1; }
            .st-key-bn_row button::after {
                font-size: 10.5px; font-weight: 600; color: rgba(255,255,255,0.65); white-space: nowrap;
                letter-spacing: -0.2px;
            }

            /* Franja inferior: nombre (→ Mi Ficha) + botón Más; el rincón derecho queda libre para el sello */
            .st-key-bn_strip {
                gap: 10px !important; padding: 4px 6px 0; margin-top: 2px;
                border-top: 1px solid rgba(255,255,255,0.06); min-height: 48px;
            }
            .st-key-bn_strip button {
                min-height: 40px !important; padding: 2px 8px !important; border: none !important;
                background: transparent !important; box-shadow: none !important; transform: none !important;
            }
            .st-key-bn_nombre button p { font-size: 16px !important; font-weight: 800 !important; color: #fff; white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }
            /* Botones a la derecha del nombre, medidos desde el borde derecho para quedar siempre
               fuera del sello de Streamlit (~130 px): salir termina a 140 px del borde, + a su izquierda */
            .st-key-bn_strip { position: relative; }
            .st-key-bn_salir, [data-testid="stElementContainer"]:has(.nob-mas-btn) {
                position: absolute !important; top: 50%; transform: translateY(-40%); width: auto !important;
            }
            .st-key-bn_salir { right: 140px; }
            [data-testid="stElementContainer"]:has(.nob-mas-btn)   { right: 198px; }
            /* El nombre no debe llegar a los botones */
            .st-key-bn_nombre { max-width: calc(100% - 204px) !important; }
            .st-key-nob_bottom_nav:has([data-testid="stElementContainer"]:has(.nob-mas-btn)) .st-key-bn_nombre { max-width: calc(100% - 262px) !important; }
            .st-key-nob_bottom_nav:has([data-testid="stElementContainer"]:has(.nob-mas-btn)) .st-key-bn_nombre button { padding-left: 4px !important; padding-right: 4px !important; }
            .st-key-nob_bottom_nav:has([data-testid="stElementContainer"]:has(.nob-mas-btn)) .st-key-bn_nombre button p { font-size: 14px !important; }
            .st-key-bn_nombre button { max-width: 100%; }
            .nob-mas-btn, .st-key-bn_salir button {
                border-radius: 999px !important; min-width: 52px !important; min-height: 40px !important; padding: 2px 12px !important;
                background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.16) !important;
                box-shadow: none !important;
            }
            .nob-mas-btn span,
            .st-key-bn_salir button [data-testid="stIconMaterial"] { font-size: 26px !important; color: #fff; margin: 0 !important; }

            /* Panel desplegable de más opciones */
            .st-key-bn_panel {
                gap: 6px !important; padding: 8px 4px 10px; margin-bottom: 4px;
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }
            .st-key-bn_panel [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 6px !important; }
            .st-key-bn_panel [data-testid="stColumn"] { min-width: 0 !important; }
            .st-key-bn_panel button {
                flex-direction: row !important; justify-content: flex-start !important; gap: 8px;
                min-height: 44px !important; border-radius: 12px !important; padding: 6px 12px !important;
                background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.10) !important;
            }
            .st-key-bn_panel button > div { flex: 0 0 auto !important; width: auto !important; }
            .st-key-bn_panel button p { font-size: 18px !important; }
            .st-key-bn_panel button::after { font-size: 13px; font-weight: 700; color: #fff; white-space: nowrap; }
            /* Botón central elevado */
            .st-key-bn_2 button {
                max-width: 96px; margin-left: auto !important; margin-right: auto !important;
                position: relative; min-height: 76px !important; margin-top: -20px;
                border-radius: 22px !important;
                background-color: #1A0204 !important;
                border: 2px solid rgba(255,255,255,0.16) !important;
                box-shadow: 0 6px 16px rgba(0,0,0,0.45) !important;
                padding-top: 58px !important;
                background-size: 50px 50px !important;
            }
            .st-key-bn_2 button p { position: absolute; top: 10px; left: 0; right: 0; }
            .st-key-bn_2 button::after { color: #D9D9D9; font-weight: 800; }
            .block-container { padding-bottom: 160px !important; }
        }

        /* ---------- Computadora: la misma barra como dock flotante abajo al centro ---------- */
        @media (min-width: 901px) {
            /* El menú lateral se reemplaza por el dock */
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
            [data-testid="stExpandSidebarButton"] { display: none !important; }

            .st-key-nob_bottom_nav {
                display: flex !important; flex-direction: row !important; align-items: center;
                position: fixed; z-index: 999990; bottom: 18px;
                /* Centrado dentro del espacio que deja libre el sello de Streamlit (abajo a la derecha) */
                left: 20px; right: 160px; margin: 0 auto; max-width: 880px; width: auto !important;
                gap: 14px !important; padding: 8px 12px 8px 18px;
                border-radius: 26px;
                background: rgba(14,15,19,0.92); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
                border: 1px solid rgba(255,255,255,0.10);
                box-shadow: 0 18px 40px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.05);
            }
            /* La franja se "disuelve": nombre a la izquierda, + y salir a la derecha de las secciones */
            .st-key-nob_bottom_nav > [data-testid="stLayoutWrapper"],
            .st-key-bn_strip { display: contents !important; }
            .st-key-bn_nombre { order: 0; flex: 0 1 auto !important; min-width: 0; width: auto !important; }
            .st-key-bn_row    { order: 1; flex: 1 1 auto !important; min-width: 0; width: auto !important;
                                /* Separador antes del grupo rueda / cerrar sesión (el nombre tiene el suyo) */
                                border-right: 1px solid rgba(255,255,255,0.10); padding-right: 14px; }
            [data-testid="stElementContainer"]:has(.nob-mas-btn)    { order: 2; flex: 0 0 auto !important; width: auto !important; }
            :is(.st-key-bnw_gestion, .st-key-bnw_carga) { order: 2; }
            .st-key-bn_salir  { order: 3; flex: 0 0 auto !important; width: auto !important; }

            /* Manager en la computadora: Simulador y Ranking son columnas de la misma fila (toman su
               estilo) y Gestión reemplaza al "+" */
            :is(.st-key-bnw_gestion, .st-key-bnw_carga) { display: block !important; flex: 0 0 auto !important; width: auto !important; }
            .st-key-nob_bottom_nav:has(:is(.st-key-bnw_gestion, .st-key-bnw_carga)) [data-testid="stElementContainer"]:has(.nob-mas-btn),
            .st-key-nob_bottom_nav:has(:is(.st-key-bnw_gestion, .st-key-bnw_carga)) .st-key-bn_panel { display: none !important; }
            :is(.st-key-bnw_gestion, .st-key-bnw_carga) button {
                border-radius: 999px !important; min-width: 48px !important; min-height: 44px !important; padding: 2px 12px !important;
                background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.16) !important;
                box-shadow: none !important; transform: none !important;
            }
            :is(.st-key-bnw_gestion, .st-key-bnw_carga) button:hover { border-color: #E30613 !important; }
            :is(.st-key-bnw_gestion, .st-key-bnw_carga) button [data-testid="stIconMaterial"] { font-size: 24px !important; color: #fff; margin: 0 !important; }
            /* Gestión desbloqueada: "Cargar datos" con borde rojo para indicar el acceso habilitado */
            .st-key-bnw_carga button { border-color: rgba(227,6,19,0.75) !important; background: rgba(227,6,19,0.12) !important; }

            .st-key-bn_nombre button {
                background: transparent !important; border: none !important; box-shadow: none !important;
                padding: 4px 16px 4px 0 !important; min-height: 44px !important; transform: none !important;
                border-right: 1px solid rgba(255,255,255,0.10) !important; border-radius: 0 !important;
            }
            .st-key-bn_nombre button p {
                font-size: 15px !important; font-weight: 800 !important; color: #fff; white-space: nowrap;
                max-width: 200px; overflow: hidden; text-overflow: ellipsis;
            }
            .st-key-bn_nombre button:hover p { color: #FF4D57 !important; }

            .st-key-bn_row [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 4px !important; align-items: flex-end; }
            .st-key-bn_row [data-testid="stColumn"] { min-width: 0 !important; }
            .st-key-bn_row button {
                flex-direction: column !important; gap: 2px; min-height: 56px !important; padding: 4px 0 !important;
                background: transparent !important; border: none !important; box-shadow: none !important;
                border-radius: 14px !important; transform: none !important;
            }
            /* Solo el color: "background" completo borraría la imagen del escudo del botón central */
            .st-key-bn_row button:hover { background-color: rgba(255,255,255,0.05) !important; }
            .st-key-bn_row button p { font-size: 22px !important; line-height: 1.1; }
            .st-key-bn_row button::after {
                font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.65); white-space: nowrap;
                /* El texto nunca sale de su botón (no invade al vecino) */
                display: block; max-width: 100%; overflow: hidden; text-overflow: ellipsis;
            }
            .st-key-bn_row button { overflow: visible; }
            /* Manager: 7 accesos, textos un poco más chicos para que "Entrenamientos" entre completo */
            .st-key-nob_bottom_nav:has(.st-key-bnw_izq) .st-key-bn_row button::after { font-size: 10px; letter-spacing: -0.2px; }
            /* Escudo central elevado */
            .st-key-bn_2 button {
                /* Ancho fijo y centrado: no ocupa toda la columna ni tapa a Entrenamientos / Mi Categoría */
                display: flex !important;
                width: 100% !important; max-width: 78px; margin-left: auto !important; margin-right: auto !important;
                position: relative; min-height: 70px !important; margin-top: -26px;
                border-radius: 22px !important; background-color: #1A0204 !important;
                border: 2px solid rgba(255,255,255,0.16) !important; box-shadow: 0 6px 16px rgba(0,0,0,0.45) !important;
                padding-top: 54px !important; background-size: 46px 46px !important;
            }
            .st-key-bn_2 button:hover { background-color: #2A0306 !important; }
            .st-key-bn_2 button p { position: absolute; top: 10px; left: 0; right: 0; }
            .st-key-bn_2 button::after { color: #D9D9D9; font-weight: 800; }

            .nob-mas-btn, .st-key-bn_salir button {
                border-radius: 999px !important; min-width: 48px !important; min-height: 44px !important; padding: 2px 12px !important;
                background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.16) !important;
                box-shadow: none !important;
            }
            .nob-mas-btn:hover, .st-key-bn_salir button:hover { border-color: #E30613 !important; }
            .nob-mas-btn span,
            .st-key-bn_salir button [data-testid="stIconMaterial"] { font-size: 24px !important; color: #fff; margin: 0 !important; }

            /* Panel del + (manager): se abre arriba del dock, a la derecha */
            .st-key-bn_panel {
                position: absolute !important; bottom: calc(100% + 10px); right: 0; width: 340px !important;
                gap: 8px !important; padding: 12px;
                border-radius: 18px; background: rgba(14,15,19,0.96);
                border: 1px solid rgba(255,255,255,0.10); box-shadow: 0 18px 40px rgba(0,0,0,0.55);
            }
            .st-key-bn_panel [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 8px !important; }
            .st-key-bn_panel [data-testid="stColumn"] { min-width: 0 !important; }
            .st-key-bn_panel button {
                flex-direction: row !important; justify-content: flex-start !important; gap: 8px;
                min-height: 44px !important; border-radius: 12px !important; padding: 6px 12px !important;
                background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.10) !important;
            }
            .st-key-bn_panel button > div { flex: 0 0 auto !important; width: auto !important; }
            .st-key-bn_panel button p { font-size: 18px !important; }
            .st-key-bn_panel button::after { font-size: 13px; font-weight: 700; color: #fff; white-space: nowrap; }

            .block-container { padding-bottom: 140px !important; }
        }
        /* Computadoras con pantalla mediana: el dock del manager tiene 7 accesos, se compacta un poco */
        @media (min-width: 901px) and (max-width: 1250px) {
            .st-key-nob_bottom_nav:has(.st-key-bnw_izq) { gap: 8px !important; padding-left: 14px; }
            .st-key-nob_bottom_nav:has(.st-key-bnw_izq) .st-key-bn_nombre button p { font-size: 13px !important; max-width: 110px; }
            .st-key-nob_bottom_nav:has(.st-key-bnw_izq) .st-key-bn_row button::after { font-size: 9px; letter-spacing: -0.2px; }
        }
        /* Pantallas anchas: dock centrado de verdad (alineado con el contenido), con el mismo margen
           a ambos lados para no tocar el sello de Streamlit de la derecha */
        @media (min-width: 1001px) {
            .st-key-nob_bottom_nav {
                left: 0; right: 0; margin: 0 auto;
                width: min(880px, calc(100% - 320px)) !important; max-width: none;
            }
        }

        /* Ficha superior de la ventana de podios: medallas tocables para cambiar de medalla */
        .st-key-dlg_med_head {
            text-align: center; gap: 4px !important;
            padding: 18px 16px 16px; border-radius: 16px; margin-bottom: 6px;
            background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03));
            border: 1px solid rgba(227,6,19,0.30);
        }
        .st-key-dlg_med_head [data-testid="stElementContainer"],
        .st-key-dlg_med_head [data-testid="stMarkdown"],
        .st-key-dlg_med_head [data-testid="stMarkdownContainer"] { width: 100% !important; text-align: center; }
        .st-key-dlg_med_head [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; margin-top: 10px; }
        .st-key-dlg_med_head [data-testid="stColumn"] { min-width: 0 !important; }
        .st-key-dlg_med_head button {
            flex-direction: column !important; gap: 0; min-height: 62px !important; border-radius: 14px !important;
            padding: 6px 4px !important;
        }
        .st-key-dlg_med_head button p { font-size: 20px !important; font-weight: 900 !important; color: #fff; }
        .st-key-dlg_med_head button::after {
            font-size: 10px; letter-spacing: 1.2px; font-weight: 700; color: rgba(255,255,255,0.5);
        }
        .st-key-dmed_1 button { background: rgba(255,215,0,0.07) !important;  border-color: rgba(255,215,0,0.35) !important; }
        .st-key-dmed_2 button { background: rgba(200,200,200,0.06) !important; border-color: rgba(200,200,200,0.30) !important; }
        .st-key-dmed_3 button { background: rgba(205,127,50,0.07) !important; border-color: rgba(205,127,50,0.35) !important; }
        .st-key-dmed_1 button::after { content: "ORO"; }
        .st-key-dmed_2 button::after { content: "PLATA"; }
        .st-key-dmed_3 button::after { content: "BRONCE"; }
        .nob-med-info.dlg { min-height: 62px; border-style: solid; opacity: .5; }
        .nob-med-info.dlg .v { font-size: 20px; }
        [class*="st-key-pie_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
        [class*="st-key-pie_"] [data-testid="stColumn"] { min-width: 0 !important; }
        .nob-medrow .off { opacity: .45; }
        .nob-medrow .on  { border-width: 2px; box-shadow: 0 0 0 3px rgba(255,255,255,0.06); }
        .st-key-nob_medals button:hover { transform: translateY(-2px); box-shadow: 0 10px 22px rgba(0,0,0,0.35); }

        /* Vista rápida: podios y mejores marcas */
        .nob-rec {
            display: flex; align-items: center; gap: 12px;
            padding: 10px 14px; margin-bottom: 8px; border-radius: 14px;
            background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
            border-left: 3px solid rgba(255,255,255,0.2);
        }
        .nob-rec.m1 { border-left-color: #FFD700; }
        .nob-rec.m2 { border-left-color: #C8C8C8; }
        .nob-rec.m3 { border-left-color: #CD7F32; }
        .nob-rec-med { font-size: 24px; }
        .nob-rec-body { flex: 1; min-width: 0; }
        .nob-rec-t { font-size: 15px; font-weight: 700; color: #fff; }
        .nob-rec-m { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 2px; }
        .nob-rec-time { font-family: ui-monospace, 'JetBrains Mono', monospace; font-size: 17px; font-weight: 800; color: #fff; }
        .nob-rec-tag {
            margin-left: 6px; padding: 1px 7px; border-radius: 999px; font-size: 10px; font-weight: 700;
            background: rgba(227,6,19,0.18); color: #FF6A72; border: 1px solid rgba(227,6,19,0.4); vertical-align: middle;
        }
        .nob-rec-tag.pb { background: rgba(255,215,0,0.12); color: #FFD54F; border-color: rgba(255,215,0,0.4); }
        .nob-rec-pos {
            display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%;
            font-size: 12px; font-weight: 800; color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.06);
        }
        .nob-pb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
        .nob-pb {
            padding: 12px 14px; border-radius: 14px;
            background: linear-gradient(160deg, rgba(227,6,19,0.12), rgba(227,6,19,0.02));
            border: 1px solid rgba(227,6,19,0.25);
        }
        .nob-pb .k { font-size: 11px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: rgba(255,255,255,0.6); }
        .nob-pb .v { font-family: ui-monospace, 'JetBrains Mono', monospace; font-size: 19px; font-weight: 800; color: #fff; margin-top: 4px; }

        /* Tarjetas de resumen (Inicio) */
        .nob-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
        .nob-duo .nob-goal { margin-bottom: 0; }
        .nob-next {
            padding: 16px 18px; border-radius: 18px;
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nob-next-k { font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(255,255,255,0.5); }
        .nob-next-days { font-size: 34px; font-weight: 900; color: #fff; line-height: 1.1; margin-top: 6px; }
        .nob-next-days small { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.6); margin-left: 4px; }
        .nob-next-name { font-size: 14px; font-weight: 700; color: #fff; margin-top: 6px; }
        .nob-next-meta { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 2px; }
        .nob-tag {
            display: inline-block; margin-top: 8px; padding: 3px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 700; letter-spacing: .5px;
        }
        .nob-tag.ok   { background: rgba(76,175,80,0.15); color: #7EE083; border: 1px solid rgba(76,175,80,0.4); }
        .nob-tag.warn { background: rgba(255,193,7,0.12); color: #FFD54F; border: 1px solid rgba(255,193,7,0.4); }

        @media (max-width: 520px) {
            .st-key-nob_estilos button { padding-left: 4px !important; padding-right: 4px !important; }
            .st-key-nob_estilos button::after { font-size: 9px; letter-spacing: 0.2px; }
            .nob-hero { gap: 14px; padding: 18px; }
            .nob-hero-crest { width: 56px; height: 56px; }
            .nob-hero-crest.der { width: 44px; height: 44px; }
            .nob-duo { grid-template-columns: 1fr; }
            .nob-hero-title { font-size: 23px; }
            .nob-stats { grid-template-columns: repeat(2, 1fr); }
            .nob-profile { gap: 12px; padding: 14px; }
            .nob-avatar { width: 46px; height: 46px; font-size: 18px; border-radius: 14px; }
            .nob-cat-badge { padding: 6px 10px; }
            .nob-cat-badge b { font-size: 17px; }
        }
        @keyframes nobUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        </style>
        """,
        unsafe_allow_html=True,
    )
