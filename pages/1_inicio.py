import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, timezone, date
import time
import uuid
import random
import html
from nob_ui import hero, seccion
import base64
import resumen_anual
import actividad

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inicio", layout="centered")

# --- INICIALIZACIÓN SEGURA DE VARIABLES ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

if "show_login_form" not in st.session_state: 
    st.session_state.show_login_form = False

if "admin_unlocked" not in st.session_state: 
    st.session_state.admin_unlocked = False

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- OPTIMIZACIÓN DE CARGA DE DATOS (FIX ERROR 429) ---
# Separamos los datos estáticos de los dinámicos para no saturar la API

@st.cache_data(ttl="1h")
def cargar_datos_generales():
    """Carga datos pesados que no cambian frecuentemente."""
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias")
        }
    except: return None

@st.cache_data(ttl="10m")
def cargar_datos_rutinas():
    """Carga solo las rutinas y el seguimiento, que cambian seguido."""
    try:
        return {
            "rutinas": conn.read(worksheet="Rutinas"),
            "seguimiento": conn.read(worksheet="Rutinas_Seguimiento")
        }
    except: return None

# --- FUNCIONES DE INSCRIPCIÓN RÁPIDA ---
@st.cache_data(ttl="5s")
def cargar_datos_inscripcion_inicio():
    try:
        try:
            df_comp = conn.read(worksheet="Competencias").copy()
            if not df_comp.empty:
                df_comp['fecha_evento'] = pd.to_datetime(df_comp['fecha_evento'], errors='coerce')
                df_comp['fecha_limite'] = pd.to_datetime(df_comp['fecha_limite'], errors='coerce')
        except: df_comp = pd.DataFrame()
            
        try:
            df_ins = conn.read(worksheet="Inscripciones").copy()
            if not df_ins.empty:
                df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
        except: df_ins = pd.DataFrame()
            
        try:
            df_pil = conn.read(worksheet="Piletas").copy()
        except: df_pil = pd.DataFrame()

        return df_comp, df_ins, df_pil
    except:
        return None, None, None

def actualizar_con_retry_inicio(worksheet, data, max_retries=5):
    for i in range(max_retries):
        try:
            conn.update(worksheet=worksheet, data=data)
            return True, None 
        except Exception as e:
            if "429" in str(e) or "quota" in str(e):
                time.sleep((2 ** i) + random.uniform(0, 1))
                continue 
            else:
                return False, e
    return False, "Error de conexión."

def leer_dataset_fresco_inicio(worksheet):
    try: return conn.read(worksheet=worksheet, ttl=0).copy()
    except: return None

def gestionar_inscripcion_inicio(id_comp, id_nadador, lista_pruebas):
    df_ins = leer_dataset_fresco_inicio("Inscripciones")
    if df_ins is None: df_ins = pd.DataFrame(columns=["id_inscripcion", "id_competencia", "codnadador", "pruebas", "fecha_inscripcion"])
    if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)

    pruebas_str = ", ".join(lista_pruebas)
    mask = (df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador)
    
    if not df_ins[mask].empty:
        df_ins.loc[mask, 'pruebas'] = pruebas_str
        df_ins.loc[mask, 'fecha_inscripcion'] = datetime.now().strftime("%Y-%m-%d")
        msg = "Modificado."
    else:
        nuevo = {"id_inscripcion": str(uuid.uuid4()), "id_competencia": id_comp, "codnadador": int(id_nadador), "pruebas": pruebas_str, "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d")}
        df_ins = pd.concat([df_ins, pd.DataFrame([nuevo])], ignore_index=True)
        msg = "Inscripto."

    exito, _ = actualizar_con_retry_inicio("Inscripciones", df_ins)
    if exito: 
        cargar_datos_inscripcion_inicio.clear()
        return True, msg
    return False, "Error."

def eliminar_inscripcion_inicio(id_comp, id_nadador):
    df_ins = leer_dataset_fresco_inicio("Inscripciones")
    if df_ins is None: return False, "Error."
    if not df_ins.empty: df_ins['codnadador'] = pd.to_numeric(df_ins['codnadador'], errors='coerce').fillna(0).astype(int)
    
    df_ins = df_ins[~((df_ins['id_competencia'] == id_comp) & (df_ins['codnadador'] == id_nadador))]
    exito, _ = actualizar_con_retry_inicio("Inscripciones", df_ins)
    if exito: 
        cargar_datos_inscripcion_inicio.clear()
        return True, "Baja exitosa."
    return False, "Error."

# Función unificadora para mantener compatibilidad con el código existente
def get_db():
    general = cargar_datos_generales()
    rutinas = cargar_datos_rutinas()
    
    if general and rutinas:
        return {**general, **rutinas}
    elif general:
        return general
    elif rutinas:
        return rutinas
    return None

db = get_db()

# --- FUNCIONES AUXILIARES ---
def calcular_cat_exacta(edad, df_cat):
    try:
        for _, r in df_cat.iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

def calcular_categoria_grafico(anio_nac):
    anio_actual = datetime.now().year
    edad = anio_actual - anio_nac
    if edad < 20: return "Juvenil"
    elif 20 <= edad <= 24: return "PRE"
    elif 25 <= edad <= 29: return "A"
    elif 30 <= edad <= 34: return "B"
    elif 35 <= edad <= 39: return "C"
    elif 40 <= edad <= 44: return "D"
    elif 45 <= edad <= 49: return "E"
    elif 50 <= edad <= 54: return "F"
    elif 55 <= edad <= 59: return "G"
    elif 60 <= edad <= 64: return "H"
    elif 65 <= edad <= 69: return "I"
    elif 70 <= edad <= 74: return "J"
    else: return "K+"

def intentar_desbloqueo():
    # Solo se pide la palabra clave (sin usuario): secrets o clave de respaldo
    try:
        sec_pass = str(st.secrets["admin"]["password"])
    except:
        sec_pass = "nob1903"

    if str(st.session_state.p_in).strip() == sec_pass:
        st.session_state.admin_unlocked = True
        st.session_state.show_login_form = False
        st.rerun()
    else:
        st.error("Palabra clave incorrecta")

def guardar_seguimiento_inicio(id_rutina, id_nadador):
    try:
        df_seg = conn.read(worksheet="Rutinas_Seguimiento", ttl=0)
        
        # OBTENER HORA ARGENTINA (UTC-3)
        ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
        hora_str = ahora_arg.strftime("%Y-%m-%d %H:%M:%S")
        
        nuevo_registro = pd.DataFrame([{
            "id_rutina": id_rutina,
            "codnadador": int(id_nadador),
            "fecha_realizada": hora_str
        }])
        df_final = pd.concat([df_seg, nuevo_registro], ignore_index=True)
        conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
        
        cargar_datos_rutinas.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# FUNCIONES PARA BUSCAR TIEMPOS EN INSCRIPCIONES (COMO EN AGENDA)
def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 999999.0

def buscar_mejor_tiempo(prueba, df_t_nadador):
    if df_t_nadador.empty: return ""
    p_lower = prueba.lower()
    
    dist_k = ""
    if "50m" in p_lower or " 50" in p_lower: dist_k = "50"
    if "100m" in p_lower or " 100" in p_lower: dist_k = "100"
    if "200m" in p_lower or " 200" in p_lower: dist_k = "200"
    if "400m" in p_lower or " 400" in p_lower: dist_k = "400"
    if "800m" in p_lower or " 800" in p_lower: dist_k = "800"
    if "1500m" in p_lower or " 1500" in p_lower: dist_k = "1500"
    if "4x50" in p_lower: dist_k = "4x50"
    if "4x100" in p_lower: dist_k = "4x100"
    
    est_k = []
    if "libre" in p_lower or "crol" in p_lower: est_k = ["libre", "crol"]
    elif "espalda" in p_lower: est_k = ["espalda"]
    elif "pecho" in p_lower: est_k = ["pecho"]
    elif "mariposa" in p_lower: est_k = ["mariposa"]
    elif "combinado" in p_lower or "medley" in p_lower: est_k = ["combinado", "medley"]
    
    if not dist_k or not est_k: return ""
    
    try:
        mask_dist = df_t_nadador['dist_desc'].str.lower().str.contains(dist_k, na=False)
        mask_est = df_t_nadador['estilo_desc'].str.lower().apply(lambda x: any(k in str(x) for k in est_k))
        
        matches = df_t_nadador[mask_dist & mask_est]
        if not matches.empty:
            best = matches.loc[matches['segundos'].idxmin()]
            return best['tiempo']
    except:
        return ""
    return ""

# --- NAVEGACIÓN A LA FICHA Y VISTA RÁPIDA DE PODIOS / RÉCORDS ---
def ir_al_padron():
    """Abre el Fichero directamente en la pestaña Padrón (manager)."""
    st.session_state.fichero_tab_inicial = "padron"
    st.switch_page("pages/2_visualizar_datos.py")


def ir_a_mi_ficha():
    """Abre el Fichero directamente en la ficha del usuario (en ambos roles)."""
    me_row = db['nadadores'][db['nadadores']['codnadador'] == st.session_state.user_id].iloc[0]
    st.session_state.ver_nadador_especifico = st.session_state.user_name
    st.session_state.nadador_seleccionado = f"{str(me_row['apellido']).upper()}, {me_row['nombre']}"
    st.session_state.fichero_tab_inicial = "ficha"
    st.switch_page("pages/2_visualizar_datos.py")


# ---------------------------------------------------------------------------
# RESUMEN ANUAL ("Mi año en el agua"): solo en diciembre
# ---------------------------------------------------------------------------
def resumen_anual_visible():
    """Visible para todos en diciembre (hora de Argentina).
    Excepción de lanzamiento: en noviembre de 2026 también se muestra, para poder revisarlo antes."""
    ahora = datetime.now(timezone.utc) - timedelta(hours=3)
    return ahora.month == 12 or (ahora.year == 2026 and ahora.month == 11)


@st.cache_data(ttl="1h", show_spinner=False)
def _imagen_resumen(claves, nombre, formato):
    return resumen_anual.generar_imagen(dict(claves), nombre, formato)


@st.dialog("Mi año en el agua", width="medium")
def dialogo_resumen_anual(id_nadador, nombre, anio):
    r = resumen_anual.calcular_resumen(db, id_nadador, anio, mis_resultados, mapa_clubes())
    if not r.get("carreras"):
        st.info(f"No hay carreras tuyas registradas en {anio}. ¡El año que viene armamos el resumen juntos!")
        return
    formato = st.segmented_control("Formato", list(resumen_anual.FORMATOS), default=list(resumen_anual.FORMATOS)[0],
                                   key="ra_formato", label_visibility="collapsed") or list(resumen_anual.FORMATOS)[0]
    with st.spinner("Armando tu resumen…"):
        png = _imagen_resumen(tuple(sorted((k, v) for k, v in r.items() if k != "fechas_detalle")), nombre, formato)
    st.image(png, use_container_width=True)
    if r.get("fechas_detalle"):
        filas = "".join(
            f"<div class='ra-fecha'><b>{html.escape(t)}</b>"
            + "".join(f"<div class='ra-prueba'>{html.escape(c)}</div>" for c in carreras) + "</div>"
            for t, carreras in r["fechas_detalle"])
        st.markdown(f"""<style>
.ra-fechas h4 {{ font-size: 15px; font-weight: 800; margin: 10px 0 6px; }}
.ra-fecha {{ background: rgba(255,255,255,0.04); border-left: 3px solid #E30613; border-radius: 8px; padding: 7px 10px; margin-bottom: 6px; }}
.ra-fecha b {{ display: block; font-size: 13.5px; color: #fff; margin-bottom: 2px; }}
.ra-prueba {{ font-size: 13px; color: #ccc; }}
</style><div class="ra-fechas"><h4>📅 Fechas contadas ({r['torneos']})</h4>{filas}</div>""", unsafe_allow_html=True)
    archivo = f"mi_{anio}_en_el_agua.png"
    st.download_button("⬇️ Descargar imagen", data=png, file_name=archivo, mime="image/png",
                       type="primary", use_container_width=True, key="ra_descargar")
    b64 = base64.b64encode(png).decode()
    st.html(f"""
<button id="ra-share" style="width:100%;padding:10px 14px;border-radius:12px;border:1px solid rgba(255,255,255,0.25);
  background:linear-gradient(90deg,#833AB4,#E1306C,#F77737);color:#fff;font-weight:800;font-size:15px;cursor:pointer">
  📲 Compartir</button>
<div id="ra-share-msg" style="font-size:12px;color:#bbb;margin-top:6px"></div>
<script>
(function() {{
  const btn = document.getElementById("ra-share"), msg = document.getElementById("ra-share-msg");
  if (!btn || btn.dataset.ok) return; btn.dataset.ok = "1";
  btn.addEventListener("click", async () => {{
    try {{
      const blob = await (await fetch("data:image/png;base64,{b64}")).blob();
      const file = new File([blob], "{archivo}", {{ type: "image/png" }});
      if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
        await navigator.share({{ files: [file], title: "Mi {anio} en el agua" }});
      }} else {{
        msg.textContent = "Este navegador no permite compartir. Descargá la imagen.";
      }}
    }} catch (e) {{
      if (e && e.name !== "AbortError") msg.textContent = "No se pudo compartir. Descargá la imagen.";
    }}
  }});
}})();
</script>""", unsafe_allow_javascript=True)


def tarjeta_resumen_anual(me):
    """Acceso al resumen del año, debajo de los botones de ficha / padrón."""
    if not resumen_anual_visible():
        return
    anio = (datetime.now(timezone.utc) - timedelta(hours=3)).year
    st.markdown(f"""<div class="nob-wrap-card"><div class="k">Resumen del año</div>
<div class="t">Tu {anio} en el agua</div>
<div class="s">Medallas, fechas, récords, pruebas nuevas y más, en una imagen para compartir.</div></div>""", unsafe_allow_html=True)
    if st.button(f"✨ Ver mi {anio}", key="btn_resumen_anual", use_container_width=True):
        # En la imagen para redes el apellido va solo con la inicial (privacidad)
        _ap = str(me['apellido']).strip()
        _nombre_pub = f"{str(me['nombre']).strip()} {_ap[0].upper()}." if _ap and _ap.lower() != "nan" else str(me['nombre']).strip()
        dialogo_resumen_anual(me['codnadador'], _nombre_pub, anio)


def mis_resultados(id_nadador):
    """Devuelve (individuales, todos) con Estilo/Distancia legibles. 'todos' incluye relevos."""
    est = db['estilos'].rename(columns={'descripcion': 'Estilo'})[['codestilo', 'Estilo']]
    dis = db['distancias'].rename(columns={'descripcion': 'Distancia'})[['coddistancia', 'Distancia']]
    cols = ['tipo', 'Estilo', 'Distancia', 'marca', 'posicion', 'fecha', 'codpileta']

    # Los códigos se comparan como número: '123', 123 y 123.0 son el mismo nadador
    _id = pd.to_numeric(pd.Series([id_nadador]), errors='coerce').iloc[0]
    _es_yo = lambda serie: pd.to_numeric(serie, errors='coerce') == _id

    ind = db['tiempos'][_es_yo(db['tiempos']['codnadador'])].copy()
    ind = ind.merge(est, on='codestilo', how='left').merge(dis, on='coddistancia', how='left')
    ind['tipo'] = 'Individual'
    ind['marca'] = ind['tiempo']

    rel = db['relevos'].copy()
    mask = False
    for k in range(1, 5):
        if f'nadador_{k}' in rel.columns:
            mask = mask | _es_yo(rel[f'nadador_{k}'])
    rel = rel[mask] if not isinstance(mask, bool) else rel.iloc[0:0]
    if not rel.empty and 'codestilo' in rel.columns and 'coddistancia' in rel.columns:
        rel = rel.merge(est, on='codestilo', how='left').merge(dis, on='coddistancia', how='left')
    rel['tipo'] = 'Relevo'
    rel['marca'] = rel['tiempo_final'] if 'tiempo_final' in rel.columns else '-'

    todos = pd.concat([ind.reindex(columns=cols), rel.reindex(columns=cols)], ignore_index=True)
    todos['posicion'] = pd.to_numeric(todos['posicion'], errors='coerce').fillna(0).astype(int)
    return ind, todos


MEDALLAS = {1: "🥇", 2: "🥈", 3: "🥉"}


def mapa_clubes():
    """codpileta -> nombre del club (sin la medida), para agrupar fechas por sede."""
    clubes = {}
    try:
        _, _, df_pil = cargar_datos_inscripcion_inicio()
        if df_pil is not None and not df_pil.empty:
            for _, p in df_pil.iterrows():
                clubes[p.get('codpileta')] = str(p.get('club', '-'))
    except Exception:
        pass
    return clubes


def mapa_sedes():
    """codpileta -> 'Club (medida)'."""
    sedes = {}
    try:
        _, _, df_pil = cargar_datos_inscripcion_inicio()
        if df_pil is not None and not df_pil.empty:
            for _, p in df_pil.iterrows():
                med = f" ({p.get('medida')})" if pd.notna(p.get('medida')) and p.get('medida') else ""
                sedes[p.get('codpileta')] = f"{p.get('club', '-')}{med}"
    except Exception:
        pass
    return sedes


def html_resultados(df, sedes, titulo_con_estilo=True, pbs=None):
    """Filas de resultados (podios / historial). `pbs`: set de (Estilo, Distancia, marca) que son mejor marca."""
    df = df.assign(_f=pd.to_datetime(df['fecha'], errors='coerce')).sort_values('_f', ascending=False)
    filas = []
    for _, r in df.iterrows():
        pos = int(r['posicion']) if pd.notna(r['posicion']) else 0
        fecha = r['_f'].strftime('%d/%m/%Y') if pd.notnull(r['_f']) else "-"
        cod = r['codpileta']
        sede = html.escape(str(sedes.get(cod, cod if pd.notna(cod) else '-')))
        titulo = f"{r['Distancia']} {r['Estilo']}" if titulo_con_estilo else f"{r['Distancia']}"
        tags = ""
        if r['tipo'] == 'Relevo':
            tags += '<span class="nob-rec-tag">RELEVO</span>'
        if pbs and (r['Estilo'], r['Distancia'], r['marca']) in pbs and r['tipo'] == 'Individual':
            tags += '<span class="nob-rec-tag pb">MEJOR MARCA</span>'
        icono = MEDALLAS.get(pos, f'<span class="nob-rec-pos">{pos}°</span>' if pos > 0 else '<span class="nob-rec-pos">–</span>')
        filas.append(
            f'<div class="nob-rec m{pos}">'
            f'<div class="nob-rec-med">{icono}</div>'
            f'<div class="nob-rec-body"><div class="nob-rec-t">{html.escape(titulo)} {tags}</div>'
            f'<div class="nob-rec-m">{fecha} · {sede}</div></div>'
            f'<div class="nob-rec-time">{html.escape(str(r["marca"]))}</div></div>'
        )
    return "".join(filas)


def mejores_marcas(ind):
    """Mejor tiempo individual por (Estilo, Distancia), ordenado por estilo y distancia."""
    if ind.empty:
        return ind
    ind = ind.assign(_s=ind['tiempo'].apply(tiempo_a_seg),
                     _d=pd.to_numeric(ind['Distancia'].astype(str).str.extract(r'(\d+)')[0], errors='coerce'))
    return ind.sort_values('_s').drop_duplicates(['Estilo', 'Distancia']).sort_values(['Estilo', '_d'])


def pie_dialogo(key):
    """Botones al final de cada ventana: Volver y Ver ficha completa."""
    with st.container(key=f"pie_{key}"):
        c1, c2 = st.columns([1, 2], gap="small")
        with c1:
            if st.button("← Volver", key=f"{key}_volver", use_container_width=True):
                st.rerun()
        with c2:
            if st.button("Ver ficha completa →", type="primary", use_container_width=True, key=f"{key}_ficha"):
                ir_a_mi_ficha()


def html_medrow(n1, n2, n3, activa=None):
    """Fila informativa de medallas (sin acción). `activa` (1/2/3) resalta la medalla elegida."""
    datos = [(1, "gold", "🥇", n1, "Oro"), (2, "silver", "🥈", n2, "Plata"), (3, "bronze", "🥉", n3, "Bronce")]
    celdas = "".join(
        f'<div class="{cls}{" on" if activa == pos else (" off" if activa else "")}">'
        f'<div class="v">{emo} {n}</div><div class="l">{lab}</div></div>'
        for pos, cls, emo, n, lab in datos
    )
    total_cls = "total off" if activa else "total"
    return (f'<div class="nob-medrow">{celdas}'
            f'<div class="{total_cls}"><div class="v">★ {n1 + n2 + n3}</div><div class="l">Podios</div></div></div>')


def _elegir_medalla(pos):
    st.session_state.dlg_med_sel = pos


def abrir_podios(pos):
    """Abre la ventana de podios en la medalla tocada en Inicio."""
    st.session_state.dlg_med_sel = pos
    dialogo_medallas()


@st.dialog("Mis podios", width="large")
def dialogo_medallas():
    pos_sel = st.session_state.get("dlg_med_sel", 1)
    _, todos = mis_resultados(st.session_state.user_id)
    cuenta = todos['posicion'].value_counts()
    n1, n2, n3 = (int(cuenta.get(k, 0)) for k in (1, 2, 3))
    podios = todos[todos['posicion'] == pos_sel]
    n_sel = len(podios)

    # Ficha superior: medalla elegida + descripción, y debajo las medallas.
    # Oro / Plata / Bronce se pueden tocar para cambiar de medalla sin salir; Podios es informativo.
    otras = [k for k in (1, 2, 3) if k != pos_sel]
    estilo_sel = (
        "<style>"
        + f".st-key-dmed_{pos_sel} button {{ border-width: 2px !important; box-shadow: 0 0 0 3px rgba(255,255,255,0.06) !important; }}"
        + "".join(f".st-key-dmed_{k} button {{ opacity: .5; }}" for k in otras)
        + "</style>"
    )
    with st.container(key="dlg_med_head"):
        st.markdown(estilo_sel, unsafe_allow_html=True)
        cols = st.columns(4, gap="small")
        for col, (pos, emo, n) in zip(cols, [(1, "🥇", n1), (2, "🥈", n2), (3, "🥉", n3)]):
            with col:
                st.button(f"{emo} {n}", key=f"dmed_{pos}", use_container_width=True,
                          on_click=_elegir_medalla, args=(pos,))
        with cols[3]:
            st.markdown(f'<div class="nob-med-info dlg"><div class="v">★ {n1 + n2 + n3}</div><div class="l">Podios</div></div>',
                        unsafe_allow_html=True)

    # Después, solo los registros de esa medalla
    seccion(f"Registros · {n_sel}")
    if podios.empty:
        st.info("Todavía no hay podios de esta medalla. ¡El próximo puede ser tuyo! 💪")
    else:
        st.markdown(html_resultados(podios, mapa_sedes()), unsafe_allow_html=True)

    st.write("")
    pie_dialogo("dlg_med")


@st.dialog("Detalle por estilo", width="large")
def dialogo_estilo(estilo):
    ind, _ = mis_resultados(st.session_state.user_id)
    # Solo registros individuales: coincide con el número de la tarjeta en Inicio
    ind_e = ind[ind['Estilo'] == estilo].copy()
    ind_e['posicion'] = pd.to_numeric(ind_e['posicion'], errors='coerce').fillna(0).astype(int)

    # Filtro por distancia: solo si el estilo se nadó en más de una distancia (arranca en "Todas")
    distancias = (ind_e['Distancia'].dropna().astype(str).drop_duplicates()
                  .sort_values(key=lambda s: pd.to_numeric(s.str.extract(r'(\d+)')[0], errors='coerce')).tolist())
    if len(distancias) > 1:
        opciones = ["Todas"] + distancias
        with st.container(key="dlg_est_filtro"):
            elegida = st.segmented_control("Distancia", opciones, default="Todas", label_visibility="collapsed")
        if elegida and elegida != "Todas":
            ind_e = ind_e[ind_e['Distancia'].astype(str) == elegida]

    cuenta = ind_e['posicion'].value_counts()
    n1, n2, n3 = (int(cuenta.get(k, 0)) for k in (1, 2, 3))
    n_reg = len(ind_e)

    # Ficha superior: estilo + descripción, y debajo las medallas (solo informativas)
    st.markdown(f"""<div class="nob-est-head">
<div class="nob-est-name">{html.escape(str(estilo))}</div>
<div class="nob-est-desc" style="visibility:hidden" aria-hidden="true">&nbsp;</div>
{html_medrow(n1, n2, n3)}
</div>""", unsafe_allow_html=True)

    # Después, solo los registros (los mejores tiempos llevan la etiqueta MEJOR MARCA)
    seccion(f"Registros · {n_reg}")
    if ind_e.empty:
        st.caption("Aún no hay registros en este estilo.")
    else:
        pb = mejores_marcas(ind_e)
        pbs = {(r['Estilo'], r['Distancia'], r['tiempo']) for _, r in pb.iterrows()}
        st.markdown(html_resultados(ind_e, mapa_sedes(), titulo_con_estilo=False, pbs=pbs), unsafe_allow_html=True)

    st.write("")
    pie_dialogo("dlg_est")


@st.dialog("Estadísticas del club", width="large")
def dialogo_club(df_t, df_r):
    """Gráficos de nadadores por categoría y género (los totales y el medallero quedan en Inicio)."""
    seccion("Nadadores")
    df_n = db['nadadores'].copy()
    df_n['Anio'] = pd.to_datetime(df_n['fechanac'], errors='coerce').dt.year
    df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria_grafico)
    colors = alt.Scale(domain=['M', 'F'], range=['#E30613', '#E6E6E6'])
    leyenda = alt.Legend(title=None, orient="bottom", labelColor="#BBBBBB",
                         labelExpr="datum.label == 'M' ? 'Masculino' : 'Femenino'")

    t_c, t_g = st.tabs(["Categorías Master", "Género"])
    with t_c:
        orden = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K+"]
        graf_cat = alt.Chart(df_n).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('Categoria', sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y('count()', title=None, axis=alt.Axis(format='d', tickMinStep=1)),
            color=alt.Color('codgenero', legend=leyenda, scale=colors),
            tooltip=[alt.Tooltip('Categoria', title='Categoría'), alt.Tooltip('count()', title='Nadadores')],
        ).properties(height=220).configure(background='transparent').configure_view(stroke=None)
        st.altair_chart(graf_cat, use_container_width=True)
    with t_g:
        base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
        graf_gen = (base.mark_arc(outerRadius=80, innerRadius=50).encode(color=alt.Color("codgenero", scale=colors, legend=leyenda))
                    + base.mark_text(radius=100).encode(text="count()", order=alt.Order("codgenero"), color=alt.value("white"))
                    ).configure(background='transparent').configure_view(stroke=None)
        st.altair_chart(graf_gen, use_container_width=True)

    st.write("")
    with st.container(key="pie_dlg_club"):
        if st.button("← Volver", key="dlg_club_volver", use_container_width=True):
            st.rerun()


# --- VISUALIZACIÓN ---

# ENCABEZADO PERSONALIZADO
hero("Newell's Old Boys", eyebrow="Complejo Acuático")

# =====================================================================
# SISTEMA DE MENSAJES FLASH (PARA EVITAR ERRORES DE WEBSOCKET)
# =====================================================================
if "flash_msg" in st.session_state:
    if st.session_state.flash_type == "success":
        st.success(st.session_state.flash_msg)
    elif st.session_state.flash_type == "warning":
        st.warning(st.session_state.flash_msg)
    
    del st.session_state.flash_msg
    del st.session_state.flash_type


if db and st.session_state.user_id:
    user_id = st.session_state.user_id
    me = db['nadadores'][db['nadadores']['codnadador'] == user_id].iloc[0]
    # Nadador inactivo (sin marcas este año ni el anterior): sin rutinas ni resumen del año
    # El entrenador tiene ficha en Nadadores pero no compite: su Inicio no muestra datos de nadador
    es_entrenador = str(st.session_state.get("nro_socio") or "").strip() == "253973"
    # El entrenador tampoco tiene rutinas: se trata como inactivo para esas tarjetas
    inactivo = es_entrenador or (st.session_state.role == "N" and actividad.id_txt(user_id) not in actividad.ids_activos(
        db.get('tiempos'), db.get('relevos')))
    
    try: edad = datetime.now().year - pd.to_datetime(me['fechanac']).year
    except: edad = 0
    cat = calcular_cat_exacta(edad, db['categorias'])
    
    df_t = db['tiempos'].copy(); df_r = db['relevos'].copy()
    df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0).astype(int)
    df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0).astype(int)
    
    mis_oros = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==1)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==1)])
    mis_platas = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==2)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==2)])
    mis_bronces = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==3)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==3)])
    mi_total = mis_oros + mis_platas + mis_bronces

    # 1. TARJETA PERFIL
    genero_txt = {"F": "Femenino", "M": "Masculino"}.get(str(me['codgenero']).strip().upper(), str(me['codgenero']))

    # Tarjeta centrada: nombre como protagonista (→ ficha) y fila Categoría | Edad | Género
    with st.container(key="nob_profile"):
        if st.button(f"{me['nombre']} {me['apellido']}", key="btn_nombre_perfil",
                     help="Ver padrón de nadadores" if es_entrenador else "Ver mi ficha completa"):
            ir_al_padron() if es_entrenador else ir_a_mi_ficha()
        # La celda Categoría lleva a Mi Categoría (botón invisible encima de la celda).
        # Entrenador: la celda dice "Entrenador" y lleva a Categorías sin preseleccionar ninguna.
        _cat_txt = "Entrenador" if es_entrenador else str(cat)
        _celda = f'<div class="cat-link"><small>Categoría</small><b class="cat">{html.escape(_cat_txt)}</b></div>'
        with st.container(key="nob_idrow"):
            st.markdown(f"""<div class="nob-id-row">
{_celda}
<div><small>Edad</small><b>{edad}</b></div>
<div><small>Género</small><b>{html.escape(genero_txt)}</b></div>
</div>""", unsafe_allow_html=True)
            if st.button("Categoría", key="btn_cat_perfil"):
                # Manager: la página Categorías abre directamente en su categoría y género
                if not es_entrenador:
                    st.session_state["cat_sel"] = cat
                    st.session_state["cat_gen"] = str(me['codgenero']).strip()
                st.switch_page("pages/6_mi_categoria.py")

    # Medallero personal: cada medalla abre la vista rápida de podios y marcas (no para el entrenador)
    if not es_entrenador:
        with st.container(key="nob_medals"):
            medallas_ui = [
                (f"🥇 {mis_oros}", "med_oro", 1),
                (f"🥈 {mis_platas}", "med_plata", 2),
                (f"🥉 {mis_bronces}", "med_bronce", 3),
            ]
            cols_med = st.columns(4, gap="small")
            for col, (label, key, pos) in zip(cols_med, medallas_ui):
                with col:
                    if st.button(label, key=key, use_container_width=True, help="Ver mis podios y mejores marcas"):
                        abrir_podios(pos)
            with cols_med[3]:  # total de podios: solo informativo
                st.markdown(f'<div class="nob-med-info"><div class="v">★ {mi_total}</div><div class="l">Podios</div></div>',
                            unsafe_allow_html=True)

    # Manager: debajo de sus datos, accesos a su ficha y al padrón completo
    if st.session_state.role in ["M", "P"]:
        if not es_entrenador and st.button("Ver mi ficha completa", type="primary", use_container_width=True,
                                           key="btn_ficha_inicio_m", icon=":material/person:"):
            ir_a_mi_ficha()
        if st.button("Ver padrón de nadadores", type="primary" if es_entrenador else "secondary",
                     use_container_width=True, key="btn_padron_inicio_m", icon=":material/groups:"):
            ir_al_padron()
        if not es_entrenador:
            tarjeta_resumen_anual(me)

    # RESUMEN: OBJETIVO DEL MES + PRÓXIMO TORNEO (solo nadadores)
    if st.session_state.role == "N":
        tarjetas = []

        # Objetivo del mes (rutinas completadas)
        try:
            _hoy = datetime.now(timezone.utc) - timedelta(hours=3)
            _rut = None if inactivo else db.get('rutinas'); _seg = db.get('seguimiento')
            if _rut is not None and _seg is not None:
                _mes = _rut[(_rut['anio_rutina'] == _hoy.year) & (_rut['mes_rutina'] == _hoy.month)]
                _total = len(_mes)
                if _total > 0:
                    _hechas = 0
                    if not _seg.empty:
                        _hechas = _seg[(_seg['codnadador'] == user_id) & (_seg['id_rutina'].isin(_mes['id_rutina']))]['id_rutina'].nunique()
                    _pct = int(round(_hechas / _total * 100))
                    if _hechas == 0: _msg = "Arrancá el mes con todo: la primera sesión es la más importante."
                    elif _pct < 50: _msg = f"Buen comienzo. Te faltan {_total - _hechas} sesiones, seguí sumando."
                    elif _pct < 100: _msg = f"Ya pasaste la mitad. Solo {_total - _hechas} más para completar el mes."
                    else: _msg = "Mes completo. Constancia de campeón."
                    tarjetas.append(f"""
                    <div class="nob-goal">
                        <div class="nob-goal-top"><b>Objetivo del mes</b><span>{_hechas} / {_total} sesiones</span></div>
                        <div class="nob-next-days" style="margin:0 0 10px;">{_pct}<small>%</small></div>
                        <div class="nob-bar"><div style="width:{_pct}%"></div></div>
                        <div class="nob-goal-msg">{_msg}</div>
                    </div>""")
        except Exception:
            pass

        # Próximo torneo (cuenta regresiva)
        try:
            _comp, _ins, _ = cargar_datos_inscripcion_inicio()
            if _comp is not None and not _comp.empty:
                _fut = _comp[_comp['fecha_evento'].dt.date >= date.today()].sort_values('fecha_evento')
                if not _fut.empty:
                    _ev = _fut.iloc[0]
                    _dias = (_ev['fecha_evento'].date() - date.today()).days
                    _inscripto = _ins is not None and not _ins.empty and not _ins[
                        (_ins['id_competencia'] == _ev['id_competencia']) & (_ins['codnadador'] == user_id)].empty
                    if es_entrenador:
                        _tag = ""
                    elif _inscripto:
                        _tag = '<span class="nob-tag ok">INSCRIPTO</span>'
                    elif pd.notnull(_ev['fecha_limite']) and _ev['fecha_limite'].date() >= date.today():
                        _cierre = (_ev['fecha_limite'].date() - date.today()).days
                        _tag = f'<span class="nob-tag warn">INSCRIPCIÓN CIERRA EN {_cierre} DÍAS</span>'
                    else:
                        _tag = ""
                    _txt_dias = "¡Es hoy!" if _dias == 0 else f"{_dias}<small>{'día' if _dias == 1 else 'días'}</small>"
                    tarjetas.append(f"""
                    <div class="nob-next">
                        <div class="nob-next-k">Próximo torneo</div>
                        <div class="nob-next-days">{_txt_dias}</div>
                        <div class="nob-next-name">{html.escape(str(_ev['nombre_evento']))}</div>
                        <div class="nob-next-meta">{_ev['fecha_evento'].strftime('%d/%m/%Y')}</div>
                        {_tag}
                    </div>""")
        except Exception:
            pass

        if tarjetas:
            clase = "nob-duo" if len(tarjetas) == 2 else ""
            _html = f'<div class="{clase}">{"".join(tarjetas)}</div>'
            st.markdown("\n".join(l.strip() for l in _html.splitlines() if l.strip()), unsafe_allow_html=True)
    
    if st.session_state.role == "N":
        if not es_entrenador and st.button("Ver Mi Ficha Completa ➝", type="primary", use_container_width=True, key="btn_ficha_inicio"):
            ir_a_mi_ficha()
        if not inactivo and not es_entrenador:
            tarjeta_resumen_anual(me)
    
    st.write("") 

    # // ATAJO RUTINA DIARIA
    if st.session_state.role == "N":
        hoy_arg = datetime.now(timezone.utc) - timedelta(hours=3)
        df_rut = None if inactivo else db.get('rutinas')  # inactivos y entrenador: sin rutina del día
        df_seg = db.get('seguimiento')
        
        if df_rut is not None and df_seg is not None:
            rutinas_mes = df_rut[(df_rut['anio_rutina'] == hoy_arg.year) & (df_rut['mes_rutina'] == hoy_arg.month)].copy()
            if not rutinas_mes.empty:
                seccion("Mi entrenamiento de hoy")
                with st.container(border=True):
                    hoy_str_corto = hoy_arg.strftime("%Y-%m-%d")
                    rutina_hoy_completada = None
                    
                    if not df_seg.empty:
                        mis_seg = df_seg[df_seg['codnadador'] == user_id].copy()
                        mis_seg['fecha_dt'] = pd.to_datetime(mis_seg['fecha_realizada']).dt.strftime("%Y-%m-%d")
                        hecho_hoy = mis_seg[mis_seg['fecha_dt'] == hoy_str_corto]
                        
                        if not hecho_hoy.empty:
                            ultimo_id_hoy = hecho_hoy.iloc[-1]['id_rutina']
                            rutina_hoy_completada = rutinas_mes[rutinas_mes['id_rutina'] == ultimo_id_hoy]
                        realizadas_historicas = mis_seg['id_rutina'].unique()
                    else:
                        realizadas_historicas = []

                    if rutina_hoy_completada is not None and not rutina_hoy_completada.empty:
                        r_row = rutina_hoy_completada.iloc[0]
                        pendientes_check = rutinas_mes[~rutinas_mes['id_rutina'].isin(realizadas_historicas)]
                        
                        if pendientes_check.empty:
                            st.balloons()
                            st.markdown(f"""
                            <div style="border: 2px solid #FFD700; border-radius: 12px; background-color: #1a1a1a; padding: 20px; text-align: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2); margin-bottom: 20px;">
                                <div style="font-size: 40px; margin-bottom: 10px;">🏆</div>
                                <h3 style="margin: 0; color: #FFD700; font-weight: 800; letter-spacing: 1px;">¡MES COMPLETADO!</h3>
                                <p style="color: #ccc; margin-top: 5px; font-size: 14px;">Sesión {int(r_row['nro_sesion'])} finalizada. ¡Completé todas las rutinas!</p>
                                <div style="margin-top: 15px; padding: 8px; background-color: rgba(255, 215, 0, 0.1); border-radius: 8px; color: #FFD700; font-size: 12px; font-weight: bold;">
                                    ¡Impresionante constancia! A descansar. 🔋
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.success(f"🏆 **¡Misión Cumplida!** Completé la **Sesión {int(r_row['nro_sesion'])}** hoy.")
                    else:
                        rutinas_pendientes = rutinas_mes[~rutinas_mes['id_rutina'].isin(realizadas_historicas)].sort_values('nro_sesion')
                        if not rutinas_pendientes.empty:
                            prox_sesion = rutinas_pendientes.iloc[0]
                            r_id = prox_sesion['id_rutina']
                            r_nro = int(prox_sesion['nro_sesion']) 
                            r_texto = prox_sesion['texto_rutina']
                            
                            st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
<span class="nob-tag warn" style="margin:0;">PENDIENTE</span>
<span style="font-size:18px;font-weight:800;color:#fff;">Sesión {r_nro} de {len(rutinas_mes)}</span>
</div>""", unsafe_allow_html=True)
                            st.markdown(r_texto)
                            st.write("") 
                            
                            if st.button("✅ DÍA GANADO", key=f"btn_ganado_inicio_{r_id}", type="primary", use_container_width=True):
                                # Evitamos usar progress bar con time.sleep para no romper websockets
                                st.toast(f"¡Excelente! Sesión {r_nro} registrada con éxito.", icon='🏆')
                                if guardar_seguimiento_inicio(r_id, user_id):
                                    st.rerun()
                        else:
                            st.info("🏅 ¡Mes completo! No tengo más rutinas pendientes.")
        st.write("") 

        # // =========================================================
        # // WIDGET INSCRIPCIÓN RÁPIDA (CON INFO DEL TORNEO Y TIEMPOS)
        # // =========================================================
        df_comp, df_ins, df_piletas = cargar_datos_inscripcion_inicio()
        if df_comp is not None and not df_comp.empty and not es_entrenador:  # el entrenador no se inscribe
            hoy = date.today()
            df_view = df_comp.copy()
            df_view = df_view.sort_values(by='fecha_evento', ascending=True, na_position='last')
            
            vista_eventos = []
            
            for _, row in df_view.iterrows():
                f_ev = row['fecha_evento']
                f_lim = row['fecha_limite']
                dias_ev = (f_ev.date() - hoy).days if pd.notnull(f_ev) else 0
                dias_cie = (f_lim.date() - hoy).days if pd.notnull(f_lim) else 0
                
                # Solo filtramos eventos que no pasaron todavía
                if dias_ev >= 0 and pd.notnull(f_ev):
                    comp_id = row['id_competencia']
                    
                    ins_user = pd.DataFrame()
                    if df_ins is not None and not df_ins.empty:
                        ins_user = df_ins[(df_ins['id_competencia'] == comp_id) & (df_ins['codnadador'] == user_id)]
                    
                    esta = not ins_user.empty
                    
                    if esta:
                        vista_eventos.append((row, esta, ins_user))
                    else:
                        if dias_cie >= 0 and pd.notnull(f_lim):
                            vista_eventos.append((row, esta, ins_user))
            
            if vista_eventos:
                # PREPARAMOS EL HISTORIAL DE TIEMPOS DEL NADADOR
                df_t_nadador = pd.DataFrame()
                df_t_base = db.get('tiempos')
                df_estilos = db.get('estilos')
                df_dist = db.get('distancias')
                
                if df_t_base is not None and not df_t_base.empty:
                    df_t_nadador = df_t_base[df_t_base['codnadador'] == user_id].copy()
                    if not df_t_nadador.empty:
                        if df_estilos is not None and not df_estilos.empty:
                            df_t_nadador = df_t_nadador.merge(df_estilos.rename(columns={'descripcion': 'estilo_desc'}), on='codestilo', how='left')
                        if df_dist is not None and not df_dist.empty:
                            df_t_nadador = df_t_nadador.merge(df_dist.rename(columns={'descripcion': 'dist_desc'}), on='coddistancia', how='left')
                        df_t_nadador['segundos'] = df_t_nadador['tiempo'].apply(lambda x: tiempo_a_seg(x) if pd.notnull(x) else 999999.0)

                seccion("🏆 Mis torneos e inscripciones")
                
                for row, esta, ins_user in vista_eventos:
                    comp_id = row['id_competencia']
                    nombre_ev = row['nombre_evento']
                    fecha_ev_str = row['fecha_evento'].strftime('%d/%m/%Y')
                    hora_inicio = row.get('hora_inicio', '')
                    costo = int(row['costo']) if pd.notna(row.get('costo')) else 0
                    desc = row.get('descripcion', '')
                    
                    # Info Pileta formateada
                    nom_pil = str(row.get('cod_pileta', '-'))
                    ubic_pil = "-"
                    if df_piletas is not None and not df_piletas.empty and 'codpileta' in df_piletas.columns:
                        d_pil = df_piletas[df_piletas['codpileta'] == nom_pil]
                        if not d_pil.empty:
                            club_val = d_pil.iloc[0].get('club', '')
                            med_val = d_pil.iloc[0].get('medida', '')
                            nom_pil = f"{club_val} ({med_val})" if med_val else str(club_val)
                            ubic_pil = str(d_pil.iloc[0].get('ubicacion', '-'))
                    
                    is_expanded = not esta
                    p_hab_str = str(row.get('pruebas_habilitadas', ""))
                    p_hab = [x.strip() for x in p_hab_str.split(",")] if p_hab_str.strip() else []
                    max_permitidas = int(row.get('max_pruebas', 10)) if pd.notna(row.get('max_pruebas')) else 10
                    
                    with st.expander(f"{'✅ Inscripto en' if esta else '📝 Inscribirme a'} {nombre_ev}", expanded=is_expanded):
                        prev = [x.strip() for x in str(ins_user.iloc[0]['pruebas']).split(",")] if esta else []
                        
                        # --- INFO BÁSICA DEL TORNEO (ESTILO AGENDA) ---
                        st.markdown(f"""
                        <div class="nob-card2" style="padding: 14px; margin-bottom: 12px;">
                            <div style="color:#4CAF50; font-weight:bold; font-size:13px; margin-bottom:8px;">📅 {fecha_ev_str} | ⏰ {hora_inicio}</div>
                            <div style="display:flex; gap:15px; color:#ddd; font-size:12px; margin-bottom:6px;">
                                <div>📍 {nom_pil}</div>
                                <div>🏙️ {ubic_pil}</div>
                                <div>💰 ${costo}</div>
                            </div>
                            <div style="font-size:12px; color:#aaa; font-style: italic;">{desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if esta:
                            # TARJETA INFORMATIVA CON CHIPS + MEJORES TIEMPOS
                            chips_html = ""
                            for p in prev:
                                mejor_tiempo = buscar_mejor_tiempo(p, df_t_nadador)
                                tiempo_badge = f" <span style='color:#FFD700; font-family:monospace; font-weight:bold;'>({mejor_tiempo})</span>" if mejor_tiempo else ""
                                chips_html += f"<span style='background-color:#444; color:#fff; padding:4px 10px; border-radius:15px; font-size:12px; margin-right:6px; margin-bottom:6px; display:inline-block; border:1px solid #555;'>{p}{tiempo_badge}</span>"
                            
                            st.markdown(f"""
                            <div style="background-color: #2b2c36; border-left: 5px solid #4CAF50; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                                <div style="font-size: 13px; color: #aaa; margin-bottom: 10px;">Mis pruebas seleccionadas:</div>
                                <div>{chips_html}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # BOTÓN DE BAJA SIN BLOCKING SLEEP
                            with st.form(f"f_baja_{comp_id}"):
                                c1, c2 = st.columns([3, 1])
                                with c1: st.caption("Si ya no vas a participar, puedes darte de baja:")
                                with c2: sub_baja = st.form_submit_button("🗑️ Darme de Baja")
                                
                                if sub_baja:
                                    ok, m = eliminar_inscripcion_inicio(comp_id, user_id)
                                    if ok: 
                                        st.session_state.flash_msg = "🗑️ Te has dado de baja. ¡Te esperamos en el próximo torneo!"
                                        st.session_state.flash_type = "warning"
                                        st.rerun()

                        else:
                            # FORMULARIO DE INSCRIPCIÓN SIN BLOCKING SLEEP
                            with st.form(f"f_idx_{comp_id}"):
                                st.caption(f"Permitido hasta {max_permitidas} pruebas.")
                                sel = st.multiselect("Seleccionar Pruebas", p_hab, default=[], max_selections=max_permitidas, label_visibility="collapsed", placeholder="Elegí tus pruebas")
                                sub = st.form_submit_button("Guardar Inscripción", type="primary")
                                
                                if sub:
                                    if not sel: st.error("Selecciona pruebas.")
                                    else:
                                        ok, m = gestionar_inscripcion_inicio(comp_id, user_id, sel)
                                        if ok: 
                                            st.session_state.flash_msg = f"🎯 **¡Inscripción guardada!** A entrenar con todo. ¡Te esperamos el {fecha_ev_str}, VAMOS NEWELL'S! 🔴⚫"
                                            st.session_state.flash_type = "success"
                                            st.rerun()
                st.write("")

    # 2. MIS REGISTROS (FRECUENCIA DE ESTILOS)
    mis_regs = db['tiempos'][db['tiempos']['codnadador'] == user_id].copy()
    if not mis_regs.empty and not es_entrenador:
        seccion("Mis estilos frecuentes")
        _ind_e, _todos_e = mis_resultados(user_id)
        conteo = _ind_e['Estilo'].dropna().value_counts()  # registros individuales, como antes

        # Tarjetas simples: número de registros + nombre del estilo. Al tocarlas se abre el detalle.
        items = list(conteo.items())
        # El nombre de cada estilo se muestra debajo del número (CSS por tarjeta)
        nombres_css = "".join(
            f'.st-key-est_{i} button::after {{ content: "{str(estilo).upper().replace(chr(34), "")}"; }}'
            for i, (estilo, _) in enumerate(items)
        )
        st.markdown(f"<style>{nombres_css}</style>", unsafe_allow_html=True)
        with st.container(key="nob_estilos"):
            for i, (col, (estilo, cantidad)) in enumerate(zip(st.columns(len(items), gap="small"), items)):
                with col:
                    if st.button(str(cantidad), key=f"est_{i}", use_container_width=True,
                                 help=f"Ver mejores marcas e historial de {estilo}"):
                        dialogo_estilo(estilo)
    
    # // 2️⃣ EL CLUB Y VOS: datos del año / del mes que cambian, aporte personal y top medallistas
    seccion("El club y vos")
    hoy_d = date.today()
    anio = hoy_d.year

    def _fechas(df):
        if 'fecha' in df.columns:
            return pd.to_datetime(df['fecha'], errors='coerce')
        return pd.Series(pd.NaT, index=df.index)

    t_f, r_f = _fechas(df_t), _fechas(df_r)
    pod_t = df_t[(t_f.dt.year == anio) & df_t['posicion'].isin([1, 2, 3])]
    pod_r = df_r[(r_f.dt.year == anio) & df_r['posicion'].isin([1, 2, 3])]
    med_club = len(pod_t) + len(pod_r)  # cada relevo cuenta una vez para el club

    # Activos: al menos una marca de competencia (individual o relevo) este año o el anterior
    _anios_act = [anio - 1, anio]
    _ids_act = set(pd.to_numeric(df_t.loc[t_f.dt.year.isin(_anios_act), 'codnadador'], errors='coerce').dropna())
    _rel_act = df_r[r_f.dt.year.isin(_anios_act)]
    for _k in range(1, 5):
        if f'nadador_{_k}' in _rel_act.columns:
            _ids_act.update(pd.to_numeric(_rel_act[f'nadador_{_k}'], errors='coerce').dropna())
    _n_activos = int(pd.to_numeric(db['nadadores']['codnadador'], errors='coerce').isin(_ids_act).sum())

    st.markdown(f"""<div class="nob-kpis tres">
<div><b>{len(db['nadadores'])}</b><small>Nadadores</small></div>
<div title="Compitieron en {anio - 1} o {anio}"><b>{_n_activos}</b><small>Activos</small></div>
<div><b>{len(df_t) + len(df_r)}</b><small>Registros</small></div>
</div>""", unsafe_allow_html=True)

    # Medallero total (histórico) del club
    _t_oro = len(df_t[df_t['posicion'] == 1]) + len(df_r[df_r['posicion'] == 1])
    _t_plata = len(df_t[df_t['posicion'] == 2]) + len(df_r[df_r['posicion'] == 2])
    _t_bronce = len(df_t[df_t['posicion'] == 3]) + len(df_r[df_r['posicion'] == 3])
    st.markdown(f'<div style="margin-bottom:12px;">{html_medrow(_t_oro, _t_plata, _t_bronce)}</div>', unsafe_allow_html=True)

    # Medallas del año por nadador (individuales + relevos de los que participó)
    _partes = [pod_t[['codnadador', 'posicion']]]
    for _k in range(1, 5):
        _col = f'nadador_{_k}'
        if _col in pod_r.columns:
            _partes.append(pod_r[[_col, 'posicion']].rename(columns={_col: 'codnadador'}))
    _med = pd.concat(_partes, ignore_index=True)
    _med['codnadador'] = pd.to_numeric(_med['codnadador'], errors='coerce')
    _med = _med.dropna(subset=['codnadador'])
    if not _med.empty:
        tabla = (_med.groupby('codnadador')['posicion'].value_counts().unstack(fill_value=0)
                 .reindex(columns=[1, 2, 3], fill_value=0))
        tabla['total'] = tabla.sum(axis=1)
        tabla = tabla.sort_values(['total', 1, 2, 3], ascending=False)
    else:
        tabla = pd.DataFrame(columns=[1, 2, 3, 'total'])

    try:
        _yo = float(user_id)
    except Exception:
        _yo = None

    # "Tu aporte": siempre para el nadador; para el manager solo si nadó en el año
    _corrio_en_anio = False
    if _yo is not None:
        _ids_t = pd.to_numeric(df_t.loc[t_f.dt.year == anio, 'codnadador'], errors='coerce')
        _corrio_en_anio = bool((_ids_t == _yo).any())
        if not _corrio_en_anio:
            _rel_anio = df_r[r_f.dt.year == anio]
            for _k in range(1, 5):
                _col = f'nadador_{_k}'
                if _col in _rel_anio.columns and (pd.to_numeric(_rel_anio[_col], errors='coerce') == _yo).any():
                    _corrio_en_anio = True
                    break

    if st.session_state.role == "N" or _corrio_en_anio:
        mias = int(tabla.loc[_yo, 'total']) if _yo in tabla.index else 0
        if med_club:
            pct = round(mias / med_club * 100)
            txt = f"🏅 Aportaste <b>{mias}</b> de las <b>{med_club}</b> medallas del club en {anio} ({pct}%)"
        else:
            txt = f"🏅 Todavía no hay medallas del club en {anio}. ¡La primera puede ser tuya!"
        st.markdown(f'<div class="nob-aporte">{txt}</div>', unsafe_allow_html=True)

    # Top 3 medallistas del año
    _nombres_por_id = {float(r['codnadador']): f"{r['nombre']} {r['apellido']}"
                       for _, r in db['nadadores'].iterrows() if pd.notna(pd.to_numeric(r['codnadador'], errors='coerce'))}

    def _fila_top(pos, cod, r, es_yo):
        meds = " ".join(f"{e}{int(r[k])}" for k, e in ((1, "🥇"), (2, "🥈"), (3, "🥉")) if r[k]) if r is not None else ""
        total = int(r["total"]) if r is not None else 0
        return (f'<div class="nob-top{" yo" if es_yo else ""}"><span class="p">{pos}</span>'
                f'<span class="n">{html.escape(_nombres_por_id.get(cod, "-"))}{" · vos" if es_yo else ""}</span>'
                f'<span class="m">{meds}</span><span class="t">★ {total}</span></div>')

    # El entrenador no compite: no figura en el top de medallistas
    if es_entrenador and _yo is not None:
        tabla = tabla.drop(index=_yo, errors="ignore")
    filas_top = [_fila_top(pos, cod, r, _yo is not None and cod == _yo)
                 for pos, (cod, r) in enumerate(tabla.head(10 if es_entrenador else 3).iterrows(), start=1)]
    # El usuario siempre aparece: si no está en el top 3, su fila va al final con su posición
    # (o "–" si todavía no tiene medallas en el año)
    if _yo is not None and not es_entrenador and _yo not in list(tabla.head(3).index):
        if _yo in tabla.index:
            filas_top.append(_fila_top(list(tabla.index).index(_yo) + 1, _yo, tabla.loc[_yo], True))
        else:
            filas_top.append(_fila_top("–", _yo, None, True))
    if filas_top:
        st.markdown(f'<div class="nob-top-tit">Top medallistas {anio}</div>{"".join(filas_top)}',
                    unsafe_allow_html=True)

    st.write("")
    if st.button("Ver más estadísticas", key="btn_club_stats", icon=":material/bar_chart:", use_container_width=True):
        dialogo_club(df_t, df_r)

    # Entrenador: nadadores por categoría (total, por género y activos)
    if es_entrenador:
        _dn = db['nadadores'].copy()
        _dn['_anio'] = pd.to_datetime(_dn['fechanac'], errors='coerce').dt.year
        _dn = _dn.dropna(subset=['_anio'])
        _dn['_cat'] = _dn['_anio'].apply(calcular_categoria_grafico)
        _dn['_gen'] = _dn['codgenero'].astype(str).str.strip().str.upper()
        _dn['_act'] = pd.to_numeric(_dn['codnadador'], errors='coerce').isin(_ids_act)
        _orden = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K+"]
        _cats = sorted(_dn['_cat'].unique(), key=lambda c: _orden.index(c) if c in _orden else len(_orden))
        _filas = []
        for _c in _cats:
            _g = _dn[_dn['_cat'] == _c]
            _filas.append(f'<div class="nob-top"><span class="n">{html.escape(str(_c))}</span>'
                          f'<span class="m">♂ {int((_g["_gen"] == "M").sum())} · ♀ {int((_g["_gen"] == "F").sum())}'
                          f' · {int(_g["_act"].sum())} activos</span><span class="t">{len(_g)}</span></div>')
        if _filas:
            st.markdown(f'<div class="nob-top-tit" style="margin-top:14px;">Nadadores por categoría</div>{"".join(_filas)}',
                        unsafe_allow_html=True)

    # --- 6. GESTIÓN (Perfil M) ---
    if st.session_state.role == "M":
        seccion("Gestión")
        label_btn = "⚙️ CARGAR COMPETENCIAS" if not st.session_state.admin_unlocked else "🔒 BLOQUEAR GESTIÓN"
        
        if st.button(label_btn, use_container_width=True, key="btn_lock_toggle_m"):
            if not st.session_state.admin_unlocked:
                st.session_state.show_login_form = not st.session_state.show_login_form
            else:
                st.session_state.admin_unlocked = False
                st.rerun()

        if st.session_state.show_login_form and not st.session_state.admin_unlocked:
            with st.form("admin_login_form"):
                st.write("**Acceso Profesor**")
                st.text_input("Palabra clave", type="password", key="p_in")
                st.form_submit_button("Desbloquear", on_click=intentar_desbloqueo)
        
        if st.session_state.admin_unlocked:
            st.success("🔓 Gestión Habilitada")
            if st.button("⚙️ IR AL PANEL DE CARGA", type="primary", use_container_width=True):
                st.switch_page("pages/1_cargar_datos.py")
