import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import entrenador
import html
import time
from datetime import date

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Carga - Natación", layout="centered", initial_sidebar_state="collapsed")

# ==========================================
#  SEGURIDAD
# ==========================================
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

if not st.session_state.get("admin_unlocked", False):
    st.error("⛔ Acceso Denegado: Requiere permisos de administrador desbloqueados.")
    if st.button("Volver al Inicio"):
        st.switch_page("pages/1_inicio.py")
    st.stop()
# ==========================================

from nob_ui import hero, seccion
hero("Panel de Carga y Gestión", "⚙️", "Administración de nadadores, tiempos y relevos.", saludar=False)

st.markdown("""<style>
.cg-tit { font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
  color: rgba(255,255,255,0.5); margin: 6px 0 4px; }
.cg-sync { padding: 14px 16px; border-radius: 18px; margin-bottom: 10px;
  background: linear-gradient(135deg, rgba(227,6,19,0.16), rgba(227,6,19,0.03)); border: 1px solid rgba(227,6,19,0.30); }
.cg-sync-top { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.cg-sync-top b { font-size: 15px; color: #fff; }
.cg-sync-top span { font-size: 26px; font-weight: 900; color: #fff; line-height: 1; }
.cg-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.cg-chip { padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.85);
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); }
.cg-item { font-size: 13px; color: rgba(255,255,255,0.8); padding: 6px 10px; margin-bottom: 4px; border-radius: 10px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); }
.cg-item b { color: #fff; }
.cg-perfil { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 800; }
.cg-perfil.m { background: rgba(227,6,19,0.18); color: #FF6B72; border: 1px solid rgba(227,6,19,0.5); }
.cg-perfil.n { background: rgba(76,175,80,0.16); color: #7EE083; border: 1px solid rgba(76,175,80,0.5); }
.cg-sep { text-align: center; font-size: 20px; font-weight: 800; padding-top: 30px; color: rgba(255,255,255,0.6); }
</style>""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. INICIALIZAR COLAS EN SESSION STATE ---
if "cola_nadadores" not in st.session_state: st.session_state.cola_nadadores = []
if "cola_users" not in st.session_state: st.session_state.cola_users = []
if "cola_tiempos" not in st.session_state: st.session_state.cola_tiempos = []
if "cola_relevos" not in st.session_state: st.session_state.cola_relevos = []


def refrescar_datos():
    st.cache_data.clear()
    st.rerun()


# --- 3. CARGA DE METADATOS ---
@st.cache_data(ttl="1h")
def cargar_referencias():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "users": conn.read(worksheet="User"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except: return None


def leer_fresco(hoja):
    """Hoja recién leída de Google (sin caché). None si falla la lectura."""
    try:
        return conn.read(worksheet=hoja, ttl=0).copy()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception:
        return None


def nombre_completo(df):
    return df['apellido'].astype(str).str.strip().str.upper() + ", " + df['nombre'].astype(str).str.strip().str.upper()


def socios_de(df):
    """Números de socio de una tabla como texto limpio ('12345')."""
    if df.empty or 'nrosocio' not in df.columns:
        return set()
    s = pd.to_numeric(df['nrosocio'], errors='coerce').dropna()
    return set(s.astype(int).astype(str))


def max_id(df, col):
    if df.empty or col not in df.columns:
        return 0
    m = pd.to_numeric(df[col], errors='coerce').max()
    return 0 if pd.isna(m) else int(m)


def hash_tiempo(cod, est, dis, fecha):
    return f"{cod}_{est}_{dis}_{fecha}"


data = cargar_referencias()
if not data: st.stop()

# Pre-procesamiento
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = nombre_completo(df_nad)
set_nadadores_existentes = set(df_nad['Nombre Completo'].unique())
set_socios_existentes = socios_de(data['users'])

df_t = data['tiempos'].copy()
df_t['hash_validacion'] = df_t['codnadador'].astype(str) + "_" + df_t['codestilo'].astype(str) + "_" + df_t['coddistancia'].astype(str) + "_" + df_t['fecha'].astype(str)
set_tiempos_existentes = set(df_t['hash_validacion'].unique())

df_nad_sel = df_nad[df_nad['codnadador'].isin(entrenador.sin_entrenador(df_nad)['codnadador'])]  # sin el entrenador
lista_nombres = sorted(df_nad_sel['Nombre Completo'].dropna().unique())
df_pil = data['piletas'].copy()
col_club_pil = 'club' if 'club' in df_pil.columns else df_pil.columns[1]
df_pil['Detalle'] = df_pil[col_club_pil].astype(str) + " (" + df_pil['medida'].astype(str) + ")"
lista_piletas = df_pil['Detalle'].unique()
lista_reglamentos = data['cat_relevos']['tipo_reglamento'].unique().tolist() if not data['cat_relevos'].empty else ["FED"]
nombre_por_id = dict(zip(pd.to_numeric(df_nad['codnadador'], errors='coerce'), df_nad['Nombre Completo']))


def entrada_tiempo(prefijo, keys=None):
    """Minutos : segundos . centésimas en una fila."""
    keys = keys or {}
    cm, cs1, cs, cs2, cc = st.columns([1, 0.25, 1, 0.25, 1])
    with cm: m = st.number_input("Min", 0, 59, 0, format="%02d", key=keys.get("m"))
    with cs1: st.markdown('<div class="cg-sep">:</div>', unsafe_allow_html=True)
    with cs: s = st.number_input("Seg", 0, 59, 0, format="%02d", key=keys.get("s"))
    with cs2: st.markdown('<div class="cg-sep">.</div>', unsafe_allow_html=True)
    with cc: c = st.number_input("Cent", 0, 99, 0, format="%02d", key=keys.get("c"))
    return m, s, c


# ==========================================
# 4. SINCRONIZACIÓN (con protección de datos)
# ==========================================
def sincronizar():
    """Sube las colas. Antes de escribir relee cada hoja en fresco y no escribe si algo no cuadra.

    Resguardos:
      - Si alguna lectura fresca falla, no se escribe nada.
      - Si una hoja fresca tiene MENOS filas que la copia conocida (lectura vacía o a medias), no se escribe.
      - Los IDs se recalculan sobre la hoja fresca y los duplicados se vuelven a controlar contra ella.
    """
    cola = st.session_state
    a_escribir = {"Nadadores": ("nadadores", cola.cola_nadadores), "User": ("users", cola.cola_users),
                  "Tiempos": ("tiempos", cola.cola_tiempos), "Relevos": ("relevos", cola.cola_relevos)}
    a_escribir = {h: v for h, v in a_escribir.items() if v[1]}

    frescos = {}
    for hoja, (clave, _) in a_escribir.items():
        df = leer_fresco(hoja)
        if df is None:
            return False, f"No se pudo leer la hoja {hoja}. No se subió nada; probá de nuevo."
        if len(df) < len(data[clave]):
            return False, (f"La hoja {hoja} se leyó con {len(df)} filas y se esperaban al menos {len(data[clave])}. "
                           "No se subió nada para no perder datos. Tocá «Recargar datos» y volvé a intentar.")
        frescos[hoja] = df

    avisos, subidos = [], 0

    def escribir(hoja, df_final):
        conn.update(worksheet=hoja, data=df_final)
        time.sleep(1)  # pausa a propósito: deja que Google termine de escribir

    # Nadadores: IDs nuevos sobre la hoja fresca; se omiten los que ya existen
    if "Nadadores" in frescos:
        df = frescos["Nadadores"]
        existentes = set(nombre_completo(df)) if not df.empty else set()
        base = max_id(df, 'codnadador')
        nuevos = []
        for r in cola.cola_nadadores:
            nom = f"{str(r['apellido']).strip().upper()}, {str(r['nombre']).strip().upper()}"
            if nom in existentes:
                avisos.append(f"Nadador {nom}: ya existía, se omitió.")
                continue
            base += 1
            nuevos.append({**r, 'codnadador': base})
            existentes.add(nom)
        if nuevos:
            escribir("Nadadores", pd.concat([df, pd.DataFrame(nuevos)], ignore_index=True))
            subidos += len(nuevos)
        cola.cola_nadadores = []

    # Usuarios: se omiten socios ya registrados
    if "User" in frescos:
        df = frescos["User"]
        existentes = socios_de(df)
        nuevos = []
        for r in cola.cola_users:
            soc = str(r['nrosocio']).strip()
            if soc in existentes:
                avisos.append(f"Socio {soc}: ya estaba registrado, se omitió.")
                continue
            nuevos.append(r)
            existentes.add(soc)
        if nuevos:
            escribir("User", pd.concat([df, pd.DataFrame(nuevos)], ignore_index=True))
            subidos += len(nuevos)
        cola.cola_users = []

    # Tiempos: IDs nuevos y control de duplicados sobre la hoja fresca
    if "Tiempos" in frescos:
        df = frescos["Tiempos"]
        existentes = set()
        if not df.empty:
            existentes = set(df['codnadador'].astype(str) + "_" + df['codestilo'].astype(str) + "_"
                             + df['coddistancia'].astype(str) + "_" + df['fecha'].astype(str))
        base = max_id(df, 'id_registro')
        nuevos = []
        for r in cola.cola_tiempos:
            h = hash_tiempo(r['codnadador'], r['codestilo'], r['coddistancia'], r['fecha'])
            if h in existentes:
                avisos.append(f"Tiempo de {nombre_por_id.get(r['codnadador'], r['codnadador'])} del {r['fecha']}: ya existía, se omitió.")
                continue
            base += 1
            nuevos.append({**r, 'id_registro': base})
            existentes.add(h)
        if nuevos:
            escribir("Tiempos", pd.concat([df, pd.DataFrame(nuevos)], ignore_index=True))
            subidos += len(nuevos)
        cola.cola_tiempos = []

    # Relevos: IDs nuevos sobre la hoja fresca
    if "Relevos" in frescos:
        df = frescos["Relevos"]
        base = max_id(df, 'id_relevo')
        nuevos = []
        for r in cola.cola_relevos:
            base += 1
            nuevos.append({**r, 'id_relevo': base})
        escribir("Relevos", pd.concat([df, pd.DataFrame(nuevos)], ignore_index=True))
        subidos += len(nuevos)
        cola.cola_relevos = []

    return True, (subidos, avisos)


# Resultado de la última sincronización (se muestra una vez, después de recargar)
if "cg_resultado" in st.session_state:
    subidos, avisos = st.session_state.pop("cg_resultado")
    st.success(f"✅ Base de datos actualizada: {subidos} {'registro subido' if subidos == 1 else 'registros subidos'}.")
    for a in avisos:
        st.warning(a)

cola = st.session_state
total = len(cola.cola_tiempos) + len(cola.cola_nadadores) + len(cola.cola_relevos) + len(cola.cola_users)

if total > 0:
    seccion("Pendiente de subir")
    chips = [(len(cola.cola_nadadores), "nadadores"), (len(cola.cola_users), "usuarios"),
             (len(cola.cola_tiempos), "tiempos"), (len(cola.cola_relevos), "relevos")]
    chips_html = "".join(f'<span class="cg-chip">{n} {t}</span>' for n, t in chips if n)
    st.markdown(f'<div class="cg-sync"><div class="cg-sync-top"><b>Listo para subir a Google Sheets</b>'
                f'<span>{total}</span></div><div class="cg-chips">{chips_html}</div></div>', unsafe_allow_html=True)

    with st.expander("Ver detalle"):
        items = []
        for r in cola.cola_nadadores:
            items.append(f"👤 <b>{html.escape(str(r['apellido']).upper())}, {html.escape(str(r['nombre']))}</b> · socio {html.escape(str(r['nrosocio']))}")
        for r in cola.cola_tiempos:
            items.append(f"⏱️ <b>{html.escape(str(nombre_por_id.get(r['codnadador'], r['codnadador'])))}</b> · {html.escape(r['tiempo'])} · {html.escape(r['fecha'])}")
        for r in cola.cola_relevos:
            items.append(f"🏊 <b>Relevo {html.escape(str(r['codgenero']))}</b> · {html.escape(r['tiempo_final'])} · {html.escape(r['fecha'])}")
        st.markdown("".join(f'<div class="cg-item">{i}</div>' for i in items), unsafe_allow_html=True)

    col_s1, col_s2 = st.columns(2)
    if col_s1.button("Subir todo", type="primary", icon=":material/cloud_upload:", use_container_width=True):
        try:
            with st.spinner("Sincronizando con la nube..."):
                ok, res = sincronizar()
            if ok:
                st.session_state.cg_resultado = res
                refrescar_datos()
            else:
                st.error(f"⚠️ {res}")
        except Exception as e:
            st.error(f"Error al subir: {e}. Lo que no se llegó a subir sigue en la cola.")

    if col_s2.button("Descartar cola", icon=":material/delete:", use_container_width=True):
        cola.cola_tiempos, cola.cola_nadadores, cola.cola_relevos, cola.cola_users = [], [], [], []
        st.rerun()

st.button("Recargar datos", icon=":material/refresh:", on_click=st.cache_data.clear,
          help="Vuelve a leer la planilla de Google (por ejemplo, si se editó a mano).")

# ==========================================
# 5. MENÚ DE NAVEGACIÓN
# ==========================================
HERRAMIENTAS = ["👤 Nuevo nadador", "⏱️ Individuales", "🏊‍♂️ Relevos", "🔑 Permisos"]
seccion_activa = st.segmented_control("Herramienta", HERRAMIENTAS, default=HERRAMIENTAS[0],
                                      key="cg_herramienta", label_visibility="collapsed") or HERRAMIENTAS[0]

# --- SECCIÓN 1: NADADORES ---
if seccion_activa == HERRAMIENTAS[0]:
    seccion("Alta de nadador y usuario")
    with st.form("f_nad", clear_on_submit=True):
        st.markdown('<div class="cg-tit">Datos personales</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        n_nom = c1.text_input("Nombre")
        n_ape = c2.text_input("Apellido")

        c3, c4 = st.columns(2)
        n_gen = c3.selectbox("Género", ["M", "F"], index=None, placeholder="Seleccionar...")
        hoy = date.today()
        n_fec = c4.date_input("Fecha de nacimiento", value=date(1990, 1, 1),
                              min_value=date(hoy.year - 100, 1, 1), max_value=date(hoy.year - 18, 12, 31),
                              format="DD/MM/YYYY")

        st.markdown('<div class="cg-tit" style="margin-top:12px">Acceso al sistema</div>', unsafe_allow_html=True)
        c_dni, c_perfil = st.columns(2)
        n_dni = c_dni.text_input("DNI")
        n_perfil_sel = c_perfil.selectbox("Perfil de acceso", ["N - Nadador (Normal)", "M - Maestro (Admin)"])
        n_perfil = "M" if "Maestro" in str(n_perfil_sel) else "N"

        # Nro de socio: se guarda solo la parte principal; la que va después del guion se ignora
        c_soc_main, c_soc_sep, c_soc_trash = st.columns([2, 0.25, 1])
        with c_soc_main:
            n_socio = st.text_input("Nro de socio (login)", placeholder="Ej: 12345")
        with c_soc_sep:
            st.markdown('<div class="cg-sep">-</div>', unsafe_allow_html=True)
        with c_soc_trash:
            st.text_input("Sufijo", placeholder="00", help="Este número se ignora")

        if st.form_submit_button("Agregar a la cola", type="primary", icon=":material/person_add:", use_container_width=True):
            if n_nom and n_ape and n_gen and n_socio and n_dni:
                nombre_completo_nuevo = f"{n_ape.strip().upper()}, {n_nom.strip().upper()}"
                socio_str = str(n_socio).strip()
                if nombre_completo_nuevo in set_nadadores_existentes:
                    st.error(f"⛔ El nadador **{nombre_completo_nuevo}** ya existe.")
                elif socio_str in set_socios_existentes:
                    st.error(f"⛔ El Nro de Socio **{socio_str}** ya está registrado en el sistema.")
                else:
                    # El codnadador definitivo se recalcula al subir, sobre la hoja fresca
                    base_id = max_id(data['nadadores'], 'codnadador')
                    cola_id = max([r['codnadador'] for r in cola.cola_nadadores], default=0)
                    cola.cola_nadadores.append({
                        'codnadador': int(max(base_id, cola_id) + 1),
                        'nombre': n_nom.title(), 'apellido': n_ape.title(),
                        'fechanac': n_fec.strftime('%Y-%m-%d'), 'codgenero': n_gen,
                        'dni': n_dni, 'nrosocio': n_socio
                    })
                    cola.cola_users.append({'nrosocio': n_socio, 'perfil': n_perfil})
                    set_nadadores_existentes.add(nombre_completo_nuevo)
                    set_socios_existentes.add(socio_str)
                    st.success(f"✅ Ficha agregada para {n_nom} (socio {n_socio}, perfil {n_perfil}).")
                    st.rerun()
            else:
                st.warning("Completá todos los campos obligatorios (nombre, apellido, género, DNI y socio).")

# --- SECCIÓN 2: TIEMPOS INDIVIDUALES ---
elif seccion_activa == HERRAMIENTAS[1]:
    seccion("Tiempo individual")
    with st.form("f_ind", clear_on_submit=True):
        st.markdown('<div class="cg-tit">Prueba</div>', unsafe_allow_html=True)
        t_nad = st.selectbox("Nadador", lista_nombres, index=None, placeholder="Buscar apellido...")
        c1, c2 = st.columns(2)
        t_est = c1.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None, placeholder="Estilo...")
        t_dis = c2.selectbox("Distancia", data['distancias']['descripcion'].unique(), index=None, placeholder="Distancia...")
        t_pil = st.selectbox("Sede / pileta", lista_piletas, index=None, placeholder="Seleccionar sede...")

        st.markdown('<div class="cg-tit" style="margin-top:12px">Resultado</div>', unsafe_allow_html=True)
        vm, vs, vc = entrada_tiempo("ind")
        c3, c4 = st.columns(2)
        v_fec = c3.date_input("Fecha del torneo", value=date.today(), format="DD/MM/YYYY")
        v_pos = c4.number_input("Posición", 1, 100, 1)

        if st.form_submit_button("Agregar a la cola", type="primary", icon=":material/add_task:", use_container_width=True):
            if t_nad and t_est and t_dis and t_pil:
                id_nad = df_nad[df_nad['Nombre Completo'] == t_nad]['codnadador'].values[0]
                id_est = data['estilos'][data['estilos']['descripcion'] == t_est]['codestilo'].values[0]
                id_dis = data['distancias'][data['distancias']['descripcion'] == t_dis]['coddistancia'].values[0]
                fecha_str = v_fec.strftime('%Y-%m-%d')
                hash_nuevo = hash_tiempo(id_nad, id_est, id_dis, fecha_str)
                if hash_nuevo in set_tiempos_existentes:
                    st.error(f"⛔ Ya hay un tiempo de **{t_nad}** en esa prueba y fecha.")
                else:
                    # El id_registro definitivo se recalcula al subir, sobre la hoja fresca
                    base_id = max_id(data['tiempos'], 'id_registro')
                    cola_id = max([r['id_registro'] for r in cola.cola_tiempos], default=0)
                    id_pil = df_pil[df_pil['Detalle'] == t_pil]['codpileta'].values[0]
                    cola.cola_tiempos.append({
                        'id_registro': int(max(base_id, cola_id) + 1),
                        'codnadador': id_nad, 'codpileta': id_pil, 'codestilo': id_est, 'coddistancia': id_dis,
                        'tiempo': f"{vm:02d}:{vs:02d}.{vc:02d}", 'fecha': fecha_str, 'posicion': int(v_pos)
                    })
                    set_tiempos_existentes.add(hash_nuevo)
                    st.success("✅ Tiempo agregado a la cola.")
                    st.rerun()
            else:
                st.warning("Faltan datos obligatorios.")

# --- SECCIÓN 3: RELEVOS ---
elif seccion_activa == HERRAMIENTAS[2]:
    seccion("Relevo")
    r_gen = st.selectbox("Género del equipo", ["M", "F", "X"], index=None, placeholder="Elegí el género primero...")

    # Filtro estricto del género para la lista de integrantes
    ld = []
    if r_gen in ["M", "F"]:
        mask_gen = df_nad_sel['codgenero'].astype(str).str.strip().str.upper()
        valores = ['M', 'MASCULINO'] if r_gen == "M" else ['F', 'FEMENINO']
        ld = df_nad_sel[mask_gen.isin(valores)]['Nombre Completo'].dropna().sort_values().tolist()
    elif r_gen == "X":
        ld = lista_nombres

    lista_dist_4x50 = data['distancias'][data['distancias']['descripcion'].str.contains("4x50", case=False, na=False)]['descripcion'].unique()

    with st.form("f_rel", clear_on_submit=True):
        st.markdown('<div class="cg-tit">Datos generales</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        r_pil = c1.selectbox("Sede", lista_piletas, index=None, placeholder="Sede...")
        r_est = c2.selectbox("Estilo", data['estilos']['descripcion'].unique(), index=None, placeholder="Estilo...")
        r_dis = c3.selectbox("Distancia", lista_dist_4x50, index=None, placeholder="Solo 4x50")
        r_reg = st.selectbox("Reglamento", lista_reglamentos, index=None, placeholder="Reglamento...")

        st.markdown('<div class="cg-tit" style="margin-top:12px">Integrantes y parciales</div>', unsafe_allow_html=True)
        r_n, r_p = [], []
        for i in range(1, 5):
            ca, cb = st.columns([0.7, 0.3])
            with ca:
                r_n.append(st.selectbox(f"Nadador {i}", ld, index=None, key=f"rn_{r_gen}_{i}", placeholder="Buscar..."))
            with cb:
                r_p.append(st.text_input(f"P{i}", placeholder="00.00", key=f"rp_{i}"))

        st.markdown('<div class="cg-tit" style="margin-top:12px">Resultado final</div>', unsafe_allow_html=True)
        rvm, rvs, rvc = entrada_tiempo("rel", {"m": "rmr", "s": "rsr", "c": "rcr"})
        c4, c5 = st.columns(2)
        rf_r = c4.date_input("Fecha", value=date.today(), format="DD/MM/YYYY", key="rf_r")
        rp_r = c5.number_input("Posición", 1, 100, 1, key="rp_r")

        if st.form_submit_button("Agregar a la cola", type="primary", icon=":material/add_task:", use_container_width=True):
            if r_gen and all(r_n) and r_dis and r_pil:
                if len(set(r_n)) != 4:
                    st.error("⛔ Hay nadadores repetidos.")
                else:
                    # El id_relevo definitivo se recalcula al subir, sobre la hoja fresca
                    base_id = max_id(data['relevos'], 'id_relevo')
                    cola_id = max([r['id_relevo'] for r in cola.cola_relevos], default=0)
                    ids_n = [int(df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0]) for n in r_n]
                    id_pil_rel = df_pil[df_pil['Detalle'] == r_pil]['codpileta'].values[0]
                    cola.cola_relevos.append({
                        'id_relevo': int(max(base_id, cola_id) + 1),
                        'codpileta': id_pil_rel,
                        'codestilo': data['estilos'][data['estilos']['descripcion'] == r_est]['codestilo'].values[0],
                        'coddistancia': data['distancias'][data['distancias']['descripcion'] == r_dis]['coddistancia'].values[0],
                        'codgenero': r_gen, 'nadador_1': ids_n[0], 'tiempo_1': r_p[0], 'nadador_2': ids_n[1], 'tiempo_2': r_p[1],
                        'nadador_3': ids_n[2], 'tiempo_3': r_p[2], 'nadador_4': ids_n[3], 'tiempo_4': r_p[3],
                        'tiempo_final': f"{rvm:02d}:{rvs:02d}.{rvc:02d}", 'posicion': int(rp_r),
                        'fecha': rf_r.strftime('%Y-%m-%d'), 'tipo_reglamento': r_reg
                    })
                    st.success("✅ Relevo agregado a la cola.")
                    st.rerun()
            else:
                st.error("Faltan datos obligatorios.")

# --- SECCIÓN 4: GESTIÓN DE PERMISOS ---
elif seccion_activa == HERRAMIENTAS[3]:
    seccion("Perfil de usuario")

    # Users y Nadadores con el nro de socio limpio ("12345") para cruzarlos
    df_users = data['users'].copy()
    df_users['nrosocio'] = pd.to_numeric(df_users['nrosocio'], errors='coerce')
    df_users = df_users.dropna(subset=['nrosocio'])
    df_users['nrosocio'] = df_users['nrosocio'].astype(int).astype(str)

    df_nad_info = df_nad[['nrosocio', 'Nombre Completo', 'dni']].copy()
    df_nad_info['nrosocio'] = pd.to_numeric(df_nad_info['nrosocio'], errors='coerce')
    df_nad_info = df_nad_info.dropna(subset=['nrosocio'])
    df_nad_info['nrosocio'] = df_nad_info['nrosocio'].astype(int).astype(str)
    df_merged = df_nad_info.merge(df_users, on='nrosocio', how='inner')

    st.caption("Buscá un socio para cambiar su nivel de acceso (N = Nadador, M = Maestro).")
    lista_socios_display = sorted(f"{row['Nombre Completo']} (Socio: {row['nrosocio']})" for _, row in df_merged.iterrows())
    sel_socio = st.selectbox("Nadador / usuario", lista_socios_display, index=None, placeholder="Escribí el nombre...")

    if sel_socio:
        nro_socio_sel = sel_socio.split("Socio: ")[1].replace(")", "")
        perfil_actual = df_users[df_users['nrosocio'] == nro_socio_sel].iloc[0]['perfil']
        es_m = perfil_actual == "M"
        st.markdown(f'<div class="cg-tit" style="margin-top:8px">Perfil actual</div>'
                    f'<span class="cg-perfil {"m" if es_m else "n"}">{"M · Maestro (Admin)" if es_m else "N · Nadador (Normal)"}</span>',
                    unsafe_allow_html=True)
        nuevo_perfil_sel = st.segmented_control("Nuevo perfil", ["N - Nadador", "M - Maestro"],
                                                default="M - Maestro" if es_m else "N - Nadador", key=f"perfil_{nro_socio_sel}")
        nuevo_perfil_code = "M" if nuevo_perfil_sel and "Maestro" in nuevo_perfil_sel else "N"

        if st.button("Actualizar permisos", type="primary", icon=":material/save:", use_container_width=True):
            if nuevo_perfil_code == perfil_actual:
                st.info("El perfil elegido es el mismo que el actual.")
            else:
                try:
                    # Se relee la hoja User en fresco y se cambia solo esa celda
                    df_u = leer_fresco("User")
                    if df_u is None or len(df_u) < len(data['users']):
                        st.error("⚠️ No se pudo leer bien la hoja User. No se cambió nada; probá de nuevo.")
                    else:
                        idx_match = df_u[pd.to_numeric(df_u['nrosocio'], errors='coerce') == int(nro_socio_sel)].index
                        if idx_match.empty:
                            st.error("No se encontró el socio en la planilla.")
                        else:
                            df_u.at[idx_match[0], 'perfil'] = nuevo_perfil_code
                            conn.update(worksheet="User", data=df_u)
                            time.sleep(1)  # pausa a propósito: deja que Google termine de escribir
                            st.success(f"✅ Perfil actualizado a '{nuevo_perfil_code}' para el socio {nro_socio_sel}.")
                            refrescar_datos()
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")
