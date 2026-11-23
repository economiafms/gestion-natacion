import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import html
import unicodedata

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Base de Datos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Acceso denegado. Por favor, inicia sesión desde el Inicio.")
    st.stop()

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

from nob_ui import hero, seccion
hero("Fichero del Club", "🗃️")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .padron-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 5px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    }
    .p-col-left { flex: 2; text-align: left; border-right: 1px solid #555; padding-right: 10px; }
    .p-col-center { flex: 2; text-align: center; padding: 0 10px; }
    .p-col-right { flex: 1; text-align: right; padding-left: 10px; border-left: 1px solid #555; }
    .p-name { font-weight: bold; font-size: 18px; color: white; margin-bottom: 5px; }
    .p-meta { font-size: 13px; color: #ccc; }
    .p-medals { font-size: 16px; display: flex; justify-content: center; gap: 10px; margin-top: 5px;}
    .p-total { font-size: 28px; color: #FFD700; font-weight: bold; line-height: 1; }
    .p-cat { font-size: 18px; color: #4CAF50; font-weight: bold; margin-top: 5px; }

    .ficha-header {
        background: linear-gradient(135deg, #8B0000 0%, #3E0000 100%);
        padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;
        border: 1px solid #550000; box-shadow: 0 4px 6px rgba(0,0,0,0.4);
    }
    .ficha-name { font-size: 24px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 10px; margin-bottom: 10px; }
    .ficha-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; }
    .ficha-medals { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; text-align: center; margin-top: 15px; font-size: 18px; }

    .pb-style-header { color: #e53935; font-weight: bold; font-size: 16px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; border-bottom: 1px solid #444; }
    .pb-row { background-color: #2b2c35; padding: 10px 15px; margin-bottom: 5px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #B71C1C; }
    .pb-dist { font-size: 15px; color: #eee; }
    .pb-time { font-size: 18px; font-weight: bold; font-family: monospace; color: #fff; }

    .mobile-card { background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .relay-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #555; padding-bottom: 8px; margin-bottom: 8px; }
    .relay-title { font-weight: bold; font-size: 15px; color: white; }
    .relay-time { font-family: monospace; font-weight: bold; font-size: 20px; color: #4CAF50; }
    
    /* MODIFICADO: Agrandar fuente fecha/sede en relevos (de 12 a 14px) */
    .relay-meta { font-size: 14px; color: #aaa; display: flex; justify-content: space-between; margin-bottom: 5px; margin-top: -2px; }
    
    .swimmer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; color: #eee; }
    .swimmer-item { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CARGA DE DATOS ---
@st.cache_data(ttl="15m")
def cargar_visualizacion():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "categorias": conn.read(worksheet="Categorias"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except Exception as e: return None

data = cargar_visualizacion()
if not data: st.stop()

# --- 3. PROCESAMIENTO GLOBAL ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()
df_nad['anio_nac'] = pd.to_datetime(df_nad['fechanac'], errors='coerce').dt.year.fillna(0).astype(int)
dict_id_anionac = df_nad.set_index('codnadador')['anio_nac'].to_dict()

def tiempo_a_segundos(t_str):
    try:
        if not isinstance(t_str, str) or ":" not in t_str: return None
        p = t_str.replace('.', ':').split(':')
        val = float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
        return val
    except: return None

def seg_a_tiempo(seg):
    if seg is None or pd.isna(seg): return "-"
    try:
        # Se trabaja en centésimas redondeadas (evita que 30.90 se muestre como 30.89)
        cent = int(round(float(seg) * 100))
        m, resto = divmod(cent, 6000)
        s, c = divmod(resto, 100)
        return f"{m:02d}:{s:02d}.{c:02d}"
    except: return "-"

def asignar_cat(edad):
    try:
        for _, r in data['categorias'].iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

def calcular_grupo_relevo(row_rel, df_cats):
    try:
        suma_edades = 0
        anio_competencia = pd.to_datetime(row_rel['fecha']).year
        for k in range(1, 5):
            nid = row_rel[f'nadador_{k}']
            anio_nac = dict_id_anionac.get(nid, 0)
            if anio_nac > 0:
                suma_edades += (anio_competencia - anio_nac)
        
        reglamento = row_rel.get('tipo_reglamento', 'FED') 
        filtro = df_cats[
            (df_cats['tipo_reglamento'] == reglamento) & 
            (df_cats['suma_min'] <= suma_edades) & 
            (df_cats['suma_max'] >= suma_edades)
        ]
        if not filtro.empty: return filtro.iloc[0]['descripcion']
        return f"Suma {suma_edades}"
    except: return "-"

# --- UNIFICACIÓN DE DATOS ---
df_full = data['tiempos'].copy()

if 'club' in df_full.columns: df_full = df_full.drop(columns=['club'])

df_full = df_full.merge(data['estilos'], on='codestilo', how='left')
df_full = df_full.merge(data['distancias'], on='coddistancia', how='left')
df_full = df_full.merge(data['piletas'], on='codpileta', how='left')

if 'descripcion_x' in df_full.columns: df_full = df_full.rename(columns={'descripcion_x': 'Estilo'})
elif 'descripcion' in df_full.columns: df_full = df_full.rename(columns={'descripcion': 'Estilo'})

if 'descripcion_y' in df_full.columns: df_full = df_full.rename(columns={'descripcion_y': 'Distancia'})

if 'club' in df_full.columns: df_full = df_full.rename(columns={'club': 'sede'})
else: df_full['sede'] = '-'

if 'medida' not in df_full.columns: df_full['medida'] = '-'

# Lógica Medallero
df_t_c = data['tiempos'].copy(); df_r_c = data['relevos'].copy()
df_t_c['posicion'] = pd.to_numeric(df_t_c['posicion'], errors='coerce').fillna(0).astype(int)
df_r_c['posicion'] = pd.to_numeric(df_r_c['posicion'], errors='coerce').fillna(0).astype(int)

med_ind = df_t_c[df_t_c['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
dfs_rel = [df_r_c[['nadador_'+str(i), 'posicion']].rename(columns={'nadador_'+str(i):'codnadador'}) for i in range(1,5)]
med_rel = pd.concat(dfs_rel)
med_rel = med_rel[med_rel['posicion'].isin([1,2,3])].groupby(['codnadador', 'posicion']).size().unstack(fill_value=0)
medallero = med_ind.add(med_rel, fill_value=0)
for p in [1,2,3]: 
    if p not in medallero.columns: medallero[p] = 0
medallero = medallero.rename(columns={1: 'Oro', 2: 'Plata', 3: 'Bronce'})

df_view = df_nad.merge(medallero, left_on='codnadador', right_index=True, how='left').fillna(0)
df_view['Total'] = df_view['Oro'] + df_view['Plata'] + df_view['Bronce']


# ==============================================================================
#  FUNCIONES REUTILIZABLES
# ==============================================================================

MEDALLA_ICONO = {1: "🥇", 2: "🥈", 3: "🥉"}


def _dist_num(serie):
    return pd.to_numeric(serie.astype(str).str.extract(r'(\d+)')[0], errors='coerce')


def _fecha_txt(valor):
    try: return pd.to_datetime(valor).strftime('%d/%m/%Y')
    except Exception: return str(valor)


def _cat_actual_de(cod):
    anio = dict_id_anionac.get(cod, 0)
    return asignar_cat(datetime.now().year - anio) if anio else "-"


@st.cache_data(ttl="15m", show_spinner=False)
def _mejores_por_nadador(_df, firma):
    """Mejor tiempo de cada nadador en cada prueba (para comparar con su categoría)."""
    d = _df[['codnadador', 'Estilo', 'Distancia', 'tiempo']].copy()
    d['segundos'] = d['tiempo'].apply(tiempo_a_segundos)
    d = d.dropna(subset=['segundos'])
    return d.groupby(['codnadador', 'Estilo', 'Distancia'], as_index=False)['segundos'].min()


def _promedio_categoria(target_id, estilo, distancia):
    """Promedio de las mejores marcas de los nadadores de su misma categoría y género (sin él)."""
    pbs = _mejores_por_nadador(df_full, len(df_full))
    pbs = pbs[(pbs['Estilo'] == estilo) & (pbs['Distancia'] == distancia) & (pbs['codnadador'] != target_id)]
    if pbs.empty: return None
    mi_cat = _cat_actual_de(target_id)
    mi_gen = df_nad.loc[df_nad['codnadador'] == target_id, 'codgenero'].iloc[0]
    gen = df_nad.set_index('codnadador')['codgenero']
    pbs = pbs[pbs['codnadador'].map(lambda c: _cat_actual_de(c) == mi_cat and gen.get(c) == mi_gen)]
    return float(pbs['segundos'].mean()) if not pbs.empty else None


def _filas_resultados(df, pbs_set, con_estilo=True, cat_por_fecha=None):
    filas = []
    for _, r in df.iterrows():
        try: pos = int(r['posicion'])
        except Exception: pos = 0
        icono = MEDALLA_ICONO.get(pos, f'<span class="nob-rec-pos">{pos}°</span>' if pos > 0 else '<span class="nob-rec-pos">–</span>')
        titulo = f"{r['Distancia']} {r['Estilo']}" if con_estilo else f"{r['Distancia']}"
        tag = '<span class="nob-rec-tag pb">MEJOR MARCA</span>' if (r['Estilo'], r['Distancia'], r['tiempo']) in pbs_set else ""
        cat = f" · Cat. {html.escape(str(cat_por_fecha(r['fecha'])))}" if cat_por_fecha else ""
        filas.append(
            f'<div class="nob-rec m{pos if pos in (1, 2, 3) else 0}"><div class="nob-rec-med">{icono}</div>'
            f'<div class="nob-rec-body"><div class="nob-rec-t">{html.escape(titulo)} {tag}</div>'
            f'<div class="nob-rec-m">{_fecha_txt(r["fecha"])} · {html.escape(str(r.get("sede", "-")))} '
            f'({html.escape(str(r.get("medida", "-")))}){cat}</div></div>'
            f'<div class="nob-rec-time">{html.escape(str(r["tiempo"]))}</div></div>')
    return "".join(filas)


@st.dialog("Detalle por estilo", width="large")
def dialogo_estilo_ficha(target_id, estilo, distancia_ini=None):
    """Mismo detalle por estilo que en Inicio, para cualquier nadador del fichero."""
    d = df_full[(df_full['codnadador'] == target_id) & (df_full['Estilo'] == estilo)].copy()
    d['posicion'] = pd.to_numeric(d['posicion'], errors='coerce').fillna(0).astype(int)
    d['segundos'] = d['tiempo'].apply(tiempo_a_segundos)
    distancias = d['Distancia'].dropna().astype(str).drop_duplicates().sort_values(key=_dist_num).tolist()
    if len(distancias) > 1:
        opciones = ["Todas"] + distancias
        ini = distancia_ini if distancia_ini in distancias else "Todas"
        with st.container(key="dlg_est_filtro"):
            elegida = st.segmented_control("Distancia", opciones, default=ini, label_visibility="collapsed")
        if elegida and elegida != "Todas":
            d = d[d['Distancia'].astype(str) == elegida]
    cuenta = d['posicion'].value_counts()
    n1, n2, n3 = (int(cuenta.get(k, 0)) for k in (1, 2, 3))
    st.markdown(f"""<div class="nob-est-head">
<div class="nob-est-name">{html.escape(str(estilo))}</div>
<div class="nob-est-desc" style="visibility:hidden" aria-hidden="true">&nbsp;</div>
<div class="nob-medrow">
<div class="gold"><div class="v">🥇 {n1}</div><div class="l">Oro</div></div>
<div class="silver"><div class="v">🥈 {n2}</div><div class="l">Plata</div></div>
<div class="bronze"><div class="v">🥉 {n3}</div><div class="l">Bronce</div></div>
<div class="total"><div class="v">★ {n1 + n2 + n3}</div><div class="l">Podios</div></div>
</div></div>""", unsafe_allow_html=True)
    seccion(f"Registros · {len(d)}")
    if d.empty:
        st.caption("Sin registros.")
    else:
        pb = d.loc[d.dropna(subset=['segundos']).groupby('Distancia')['segundos'].idxmin()]
        pbs_set = {(r['Estilo'], r['Distancia'], r['tiempo']) for _, r in pb.iterrows()}
        d = d.assign(_f=pd.to_datetime(d['fecha'], errors='coerce')).sort_values('_f', ascending=False)
        st.markdown(_filas_resultados(d, pbs_set, con_estilo=False), unsafe_allow_html=True)
    st.write("")
    with st.container(key="pie_dlg_ficha_est"):
        if st.button("← Volver", key="dlg_ficha_est_volver", use_container_width=True):
            st.rerun()


def render_tab_ficha(target_id, unique_key_suffix=""):
    if not target_id: return
    sfx = f"{unique_key_suffix}_{target_id}"

    info = df_nad[df_nad['codnadador'] == target_id].iloc[0]

    # Datos básicos nadador
    try:
        nac = pd.to_datetime(info['fechanac'])
        anio_nacimiento_nadador = nac.year
        edad_actual = datetime.now().year - anio_nacimiento_nadador
        nac_str = nac.strftime('%d/%m/%Y')
    except:
        anio_nacimiento_nadador = 0
        edad_actual = 0; nac_str = "-"

    cat_actual = asignar_cat(edad_actual)

    row_m = df_view[df_view['codnadador'] == target_id]
    if not row_m.empty:
        o, pl, br = int(row_m.iloc[0]['Oro']), int(row_m.iloc[0]['Plata']), int(row_m.iloc[0]['Bronce'])
    else: o, pl, br = 0, 0, 0

    genero_txt = {"F": "Femenino", "M": "Masculino"}.get(str(info['codgenero']).strip().upper(), str(info['codgenero']))
    # Cabecera con el mismo estilo que la tarjeta de Inicio (siempre visible, arriba de las pestañas)
    st.markdown(f"""<div class="nob-fh">
<div class="nob-fh-name">{html.escape(f"{info['nombre']} {info['apellido']}")}</div>
<div class="nob-fh-sub">Nacimiento {nac_str}</div>
<div class="nob-id-row">
<div><small>Categoría</small><b class="cat">{html.escape(str(cat_actual))}</b></div>
<div><small>Edad</small><b>{edad_actual}</b></div>
<div><small>Género</small><b>{html.escape(genero_txt)}</b></div>
</div>
<div class="nob-medrow" style="margin-top:14px;">
<div class="gold"><div class="v">🥇 {o}</div><div class="l">Oro</div></div>
<div class="silver"><div class="v">🥈 {pl}</div><div class="l">Plata</div></div>
<div class="bronze"><div class="v">🥉 {br}</div><div class="l">Bronce</div></div>
<div class="total"><div class="v">★ {o + pl + br}</div><div class="l">Podios</div></div>
</div>
</div>""", unsafe_allow_html=True)

    mis_t = df_full[df_full['codnadador'] == target_id].copy()
    mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)
    mis_t['_f'] = pd.to_datetime(mis_t['fecha'], errors='coerce')
    validas = mis_t.dropna(subset=['segundos'])
    pbs = validas.loc[validas.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].copy() if not validas.empty else validas
    pbs_set = {(r['Estilo'], r['Distancia'], r['tiempo']) for _, r in pbs.iterrows()}

    def cat_por_fecha(fecha):
        try: return asignar_cat(pd.to_datetime(fecha).year - anio_nacimiento_nadador)
        except Exception: return "-"

    t_res, t_evo, t_his, t_rel = st.tabs(["Resumen", "Evolución", "Historial", "Relevos"])

    # ---------------------------------------------------------------- RESUMEN
    with t_res:
        seccion("Mejores marcas")
        if pbs.empty:
            st.caption("Todavía no hay tiempos registrados.")
        else:
            pbs = pbs.assign(_d=_dist_num(pbs['Distancia'])).sort_values(['Estilo', '_d'])
            # Una tarjeta por estilo; adentro, una fila por distancia (toda la fila es tocable)
            for ie, estilo in enumerate(pbs['Estilo'].unique()):
                with st.container(key=f"pbcard_{sfx}_{ie}"):
                    st.markdown(f'<div class="nob-pbc-tit">{html.escape(str(estilo))}</div>', unsafe_allow_html=True)
                    for idist, (_, r) in enumerate(pbs[pbs['Estilo'] == estilo].iterrows()):
                        # Mejora respecto de la mejor marca anterior a esta
                        prev = validas[(validas['Estilo'] == estilo) & (validas['Distancia'] == r['Distancia'])
                                       & (validas['_f'] < r['_f'])]
                        if not prev.empty:
                            dif = r['segundos'] - prev['segundos'].min()
                            mejora = f'<span class="up">↓ {abs(dif):.2f}s</span>' if dif < 0 else '<span class="eq">=</span>'
                        else:
                            mejora = '<span class="eq">1ª marca</span>'
                        # Comparación con el promedio de su categoría
                        prom = _promedio_categoria(target_id, estilo, r['Distancia'])
                        if prom is None:
                            comp = '<span class="cmp">⚪ sin ref.</span>'
                        else:
                            dc = r['segundos'] - prom
                            comp = f'<span class="cmp">{"🟢" if dc <= 0 else "🔴"} {"-" if dc <= 0 else "+"}{abs(dc):.2f}s cat.</span>'
                        with st.container(key=f"pbr_{sfx}_{ie}_{idist}"):
                            st.markdown(
                                f'<div class="nob-pbr"><div class="d">{html.escape(str(r["Distancia"]))}</div>'
                                f'<div class="t"><b>{html.escape(str(r["tiempo"]))}</b><small>{_fecha_txt(r["fecha"])}</small></div>'
                                f'<div class="x">{mejora}{comp}</div><div class="ir">›</div></div>',
                                unsafe_allow_html=True)
                            if st.button(f"Detalle {estilo} {r['Distancia']}", key=f"pbb_{sfx}_{ie}_{idist}"):
                                dialogo_estilo_ficha(target_id, estilo, str(r['Distancia']))
            st.caption("🟢 / 🔴: mejor o peor que el promedio de las mejores marcas de su categoría y género. "
                       "Tocá una marca para ver el detalle del estilo.")

    # --------------------------------------------------------------- EVOLUCIÓN
    with t_evo:
        conteo = validas.groupby(['Estilo', 'Distancia']).size().reset_index(name='n')
        conteo = conteo[conteo['n'] >= 2]
        if conteo.empty:
            st.caption("Se necesitan al menos 2 carreras en la misma prueba para ver la evolución.")
        else:
            # Arranca en la prueba más nadada
            top = conteo.sort_values('n', ascending=False).iloc[0]
            estilos_ok = sorted(conteo['Estilo'].unique().tolist())
            g_est = st.segmented_control("Estilo", estilos_ok, default=top['Estilo'], key=f"ev_est_{sfx}",
                                         label_visibility="collapsed") or top['Estilo']
            dists = conteo[conteo['Estilo'] == g_est].sort_values('Distancia', key=_dist_num)
            dist_ini = top['Distancia'] if g_est == top['Estilo'] else dists.sort_values('n', ascending=False).iloc[0]['Distancia']
            g_dist = st.segmented_control("Distancia", dists['Distancia'].tolist(), default=dist_ini,
                                          key=f"ev_dis_{sfx}_{g_est}", label_visibility="collapsed") or dist_ini

            df_graph = validas[(validas['Estilo'] == g_est) & (validas['Distancia'] == g_dist)].sort_values('_f')
            mejor = df_graph['segundos'].min()
            promedio = df_graph['segundos'].mean()
            mejora_total = df_graph['segundos'].iloc[-1] - df_graph['segundos'].iloc[0]
            st.markdown(f"""<div class="nob-kpis">
<div><b>{seg_a_tiempo(mejor)}</b><small>Mejor marca</small></div>
<div><b>{seg_a_tiempo(promedio)}</b><small>Promedio</small></div>
<div><b class="{'up' if mejora_total < 0 else ''}">{'↓ ' if mejora_total < 0 else ('↑ ' if mejora_total > 0 else '')}{abs(mejora_total):.2f}s</b><small>Desde la 1ª carrera</small></div>
</div>""", unsafe_allow_html=True)

            if anio_nacimiento_nadador > 0:
                df_graph = df_graph.assign(cat_hist=df_graph['_f'].apply(lambda x: asignar_cat(x.year - anio_nacimiento_nadador)))
            else:
                df_graph = df_graph.assign(cat_hist="-")
            df_graph = df_graph.assign(TimeObj=pd.to_datetime('2024-01-01') + pd.to_timedelta(df_graph['segundos'], unit='s'))

            fig = px.line(df_graph, x='fecha', y='TimeObj', markers=True, template="plotly_dark",
                          hover_data={'fecha': False, 'TimeObj': False, 'sede': True, 'Distancia': True, 'cat_hist': True, 'tiempo': True})
            fig.update_traces(line_color='#E53935', name="Registro",
                              hovertemplate="<b>%{customdata[3]}</b><br>📅 %{x|%d/%m/%Y}<br>📍 %{customdata[0]}<br>🏷️ %{customdata[2]}")
            # Línea de referencia: mejor marca
            fig.add_hline(y=pd.to_datetime('2024-01-01') + pd.to_timedelta(mejor, unit='s'),
                          line_dash="dash", line_color="#FFD54F", opacity=0.8,
                          annotation_text=f"Mejor marca {seg_a_tiempo(mejor)}", annotation_position="top left",
                          annotation_font_color="#FFD54F")
            fig.update_yaxes(tickformat="%M:%S.%f", title="Tiempo")
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=40, r=20), hovermode="x unified",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, key=f"ev_graf_{sfx}")

    # --------------------------------------------------------------- HISTORIAL
    with t_his:
        if mis_t.empty:
            st.caption("Todavía no hay carreras registradas.")
        else:
            estilos_h = ["Todos"] + sorted(mis_t['Estilo'].dropna().unique().tolist())
            hf_est = st.segmented_control("Estilo", estilos_h, default="Todos", key=f"h_est_{sfx}",
                                          label_visibility="collapsed") or "Todos"
            base = mis_t if hf_est == "Todos" else mis_t[mis_t['Estilo'] == hf_est]
            dist_h = ["Todas"] + base['Distancia'].dropna().astype(str).drop_duplicates().sort_values(key=_dist_num).tolist()
            hf_dis = st.segmented_control("Distancia", dist_h, default="Todas", key=f"h_dis_{sfx}_{hf_est}",
                                          label_visibility="collapsed") or "Todas"
            df_hist = base if hf_dis == "Todas" else base[base['Distancia'].astype(str) == hf_dis]
            df_hist = df_hist.sort_values('_f', ascending=False)

            clave_n = f"hist_n_{sfx}"
            mostrar = st.session_state.get(clave_n, 20)
            seccion(f"Carreras · {len(df_hist)}")
            st.markdown(_filas_resultados(df_hist.head(mostrar), pbs_set, cat_por_fecha=cat_por_fecha)
                        or "<small>Sin carreras para este filtro.</small>", unsafe_allow_html=True)
            if len(df_hist) > mostrar:
                if st.button(f"Ver más ({len(df_hist) - mostrar} restantes)", key=f"hist_mas_{sfx}", use_container_width=True):
                    st.session_state[clave_n] = mostrar + 20
                    st.rerun()

    # ----------------------------------------------------------------- RELEVOS
    with t_rel:
        mr_base = data['relevos'].copy()
        cond_rel = (mr_base['nadador_1'] == target_id) | (mr_base['nadador_2'] == target_id) | (mr_base['nadador_3'] == target_id) | (mr_base['nadador_4'] == target_id)
        mis_relevos = mr_base[cond_rel].copy()

        if not mis_relevos.empty:
            mis_relevos = mis_relevos.merge(data['estilos'], on='codestilo', how='left')
            mis_relevos = mis_relevos.merge(data['distancias'], on='coddistancia', how='left')
            mis_relevos = mis_relevos.merge(data['piletas'], on='codpileta', how='left')

            if 'descripcion_x' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'descripcion_x': 'Estilo'})
            elif 'descripcion' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'descripcion': 'Estilo'})
            if 'descripcion_y' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'descripcion_y': 'Distancia'})
            if 'club' in mis_relevos.columns: mis_relevos = mis_relevos.rename(columns={'club': 'sede'})
            else: mis_relevos['sede'] = '-'
            if 'medida' not in mis_relevos.columns: mis_relevos['medida'] = '-'

            mis_relevos = mis_relevos.sort_values('fecha', ascending=False)
            seccion(f"Relevos · {len(mis_relevos)}")
            for _, r in mis_relevos.iterrows():
                grupo_txt = calcular_grupo_relevo(r, data['cat_relevos'])
                html_grid = ""
                for k in range(1, 5):
                    nid = r[f'nadador_{k}']
                    nom = dict_id_nombre.get(nid, "??").split(',')[0]
                    t = str(r[f'tiempo_{k}']).strip()
                    if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                    border_style = "border: 1px solid #E30613;" if nid == target_id else ""
                    html_grid += f"<div class='swimmer-item' style='{border_style}'>{k}. {nom}</div>"

                try: p_rel = int(r['posicion'])
                except: p_rel = 0
                pos_icon = {1: "🥇 1º", 2: "🥈 2º", 3: "🥉 3º"}.get(p_rel, f"Pos: {p_rel}" if p_rel > 0 else "")
                sede_r = r.get('sede', '-')

                st.markdown(f"""
                <div class="mobile-card" style="border-left: 4px solid #E30613;">
                    <div class="relay-header">
                        <div>
                            <div class="relay-title">{r['Distancia']} {r['Estilo']}</div>
                            <div style="font-size:11px; color:#aaa;">{grupo_txt} ({r['codgenero']})</div>
                        </div>
                        <div style="text-align:right;">
                            <div class="relay-time">{r['tiempo_final']}</div>
                            <div style="font-size:12px; color:#ddd; font-weight:bold;">{pos_icon}</div>
                        </div>
                    </div>
                    <div class="relay-meta" style="margin-top:-3px; margin-bottom:8px;">
                        <span>📅 {_fecha_txt(r['fecha'])} • {sede_r} ({r['medida']})</span>
                    </div>
                    <div class="swimmer-grid">{html_grid}</div>
                </div>""", unsafe_allow_html=True)
        else: st.caption("Sin relevos.")


def _sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if unicodedata.category(c) != "Mn")


def _abrir_ficha_desde_padron(nombre_completo):
    """Selecciona al nadador y cambia a la pestaña Ficha Técnica (sin pasos intermedios)."""
    st.session_state.nadador_seleccionado = nombre_completo
    st.session_state["fichero_tabs_m"] = "Ficha"


def render_tab_padron():
    seccion("Padrón y medallero")
    filtro = st.text_input("Buscar nadador", placeholder="Buscar por nombre o apellido...", label_visibility="collapsed")
    df_show = df_view.copy()
    df_show['_orden_nombre'] = df_show['Nombre Completo'].map(_sin_tildes)
    df_show = df_show.sort_values(['Total', 'Oro', 'Plata', '_orden_nombre'], ascending=[False, False, False, True])
    if filtro.strip():
        busca = _sin_tildes(filtro.strip())
        df_show = df_show[(df_show['nombre'].map(_sin_tildes) + " " + df_show['apellido'].map(_sin_tildes)).str.contains(busca, regex=False)
                          | df_show['_orden_nombre'].str.contains(busca, regex=False)]
    st.caption(f"{len(df_show)} de {len(df_view)} nadadores")

    # Todos los nadadores (sin límite), con la tarjeta clásica del padrón:
    # nombre y datos | medallas | total y categoría
    for _, row in df_show.iterrows():
        try: edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        o, p, b, t = int(row.get('Oro', 0)), int(row.get('Plata', 0)), int(row.get('Bronce', 0)), int(row.get('Total', 0))

        with st.container(key=f"pad_{row['codnadador']}", horizontal=True, vertical_alignment="center"):
            st.markdown(f"""<div class="padron-card nob-pad">
<div class="p-col-left">
<div class="p-name">{html.escape(str(row['Nombre Completo']))}</div>
<div class="p-meta">{edad} años<span class="p-al"> (al 31/12)</span> • {html.escape(str(row['codgenero']))}</div>
</div>
<div class="p-col-center"><div class="p-medals"><span>🥇{o}</span> <span>🥈{p}</span> <span>🥉{b}</span></div></div>
<div class="p-col-right"><div class="p-total">★ {t}</div><div class="p-cat">{html.escape(str(cat))}</div></div>
</div>""", unsafe_allow_html=True)
            # Botón invisible que cubre toda la tarjeta: tocar la tarjeta abre la ficha
            st.button(f"Ver ficha de {row['nombre']}", key=f"btn_p_{row['codnadador']}",
                      on_click=_abrir_ficha_desde_padron, args=(row['Nombre Completo'],))

def render_tab_relevos_general():
    st.markdown("### Historial de Postas")
    mr_all = data['relevos'].copy()
    if not mr_all.empty:
        mr_all = mr_all.merge(data['estilos'], on='codestilo', how='left')
        mr_all = mr_all.merge(data['distancias'], on='coddistancia', how='left')
        mr_all = mr_all.merge(data['piletas'], on='codpileta', how='left')
        
        if 'descripcion_x' in mr_all.columns: mr_all = mr_all.rename(columns={'descripcion_x': 'Estilo'})
        elif 'descripcion' in mr_all.columns: mr_all = mr_all.rename(columns={'descripcion': 'Estilo'})
        
        if 'descripcion_y' in mr_all.columns: mr_all = mr_all.rename(columns={'descripcion_y': 'Distancia'})
        
        if 'club' in mr_all.columns: mr_all = mr_all.rename(columns={'club': 'sede'})
        else: mr_all['sede'] = '-'
        if 'medida' not in mr_all.columns: mr_all['medida'] = '-'

        c1, c2 = st.columns(2)
        fg_est = c1.selectbox("Estilo", ["Todos"] + sorted(mr_all['Estilo'].unique().tolist()), key="fg_est")
        fg_gen = c2.selectbox("Género", ["Todos", "M", "F", "X"], key="fg_gen")
        
        if fg_est != "Todos": mr_all = mr_all[mr_all['Estilo'] == fg_est]
        if fg_gen != "Todos": mr_all = mr_all[mr_all['codgenero'] == fg_gen]
        
        for _, r in mr_all.sort_values('fecha', ascending=False).head(20).iterrows():
            grupo_txt = calcular_grupo_relevo(r, data['cat_relevos'])
            html_grid = ""
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"

            try: p_rel = int(r['posicion'])
            except: p_rel = 0
            if p_rel == 1: pos_icon = "🥇 1º"
            elif p_rel == 2: pos_icon = "🥈 2º"
            elif p_rel == 3: pos_icon = "🥉 3º"
            elif p_rel > 0: pos_icon = f"Pos: {p_rel}"
            else: pos_icon = ""

            sede_r = r.get('sede', '-')

            # MODIFICADO: Aumentada fuente por CSS
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #9C27B0;">
                <div class="relay-header">
                    <div>
                        <div class="relay-title">{r['Distancia']} {r['Estilo']}</div>
                        <div style="font-size:11px; color:#aaa;">{grupo_txt} ({r['codgenero']})</div>
                    </div>
                    <div style="text-align:right;">
                        <div class="relay-time">{r['tiempo_final']}</div>
                        <div style="font-size:12px; color:#ddd; font-weight:bold;">{pos_icon}</div>
                    </div>
                </div>
                <div class="relay-meta" style="margin-top:-3px; margin-bottom:8px;">
                    <span>📅 {r['fecha']} • {sede_r} ({r['medida']})</span>
                </div>
                <div class="swimmer-grid">{html_grid}</div>
            </div>""", unsafe_allow_html=True)

# ==============================================================================
#  LÓGICA PRINCIPAL
# ==============================================================================

if rol == "N":
    st.session_state.pop("fichero_tab_inicial", None)
    tab_yo, tab_otro = st.tabs(["Mi Ficha", "Compañero"])
    with tab_yo: render_tab_ficha(mi_id, unique_key_suffix="_me")
    with tab_otro:
        st.markdown("##### Consulta por DNI")
        dni_in = st.text_input("DNI del Nadador", placeholder="Ej: 30123456")
        if dni_in:
            encontrado = df_nad[df_nad['dni'].astype(str).str.contains(dni_in.strip())]
            if not encontrado.empty: render_tab_ficha(encontrado.iloc[0]['codnadador'], unique_key_suffix="_friend")
            else: st.error("No encontrado.")

else:
    # ROL MASTER (M)
    # Si se llega desde Inicio (nombre o medallas), abrir directo en la Ficha Técnica
    _tab_ini = st.session_state.pop("fichero_tab_inicial", None)
    if _tab_ini == "ficha":
        st.session_state["fichero_tabs_m"] = "Ficha"
    elif _tab_ini == "padron":
        st.session_state["fichero_tabs_m"] = "Padrón"
    tab1, tab2, tab3 = st.tabs(["Padrón", "Ficha", "Relevos"], key="fichero_tabs_m", on_change="rerun")
    
    with tab1: render_tab_padron()
    
    with tab2:
        lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())
        idx_defecto = 0
        pre_seleccion = st.session_state.get("nadador_seleccionado")
        if not pre_seleccion and mi_nombre in lista_nombres: pre_seleccion = mi_nombre
        if pre_seleccion in lista_nombres: idx_defecto = lista_nombres.index(pre_seleccion)

        def _mover_nadador(paso):
            actual = st.session_state.get("nadador_seleccionado") or lista_nombres[idx_defecto]
            i = lista_nombres.index(actual) if actual in lista_nombres else idx_defecto
            st.session_state.nadador_seleccionado = lista_nombres[(i + paso) % len(lista_nombres)]

        # ← [buscador / lista de nadadores] →
        with st.container(key="ficha_selector", horizontal=True, vertical_alignment="center", gap="small"):
            st.button("", key="ficha_prev", icon=":material/chevron_left:", help="Nadador anterior",
                      on_click=_mover_nadador, args=(-1,))
            f_nad = st.selectbox("Nadador", lista_nombres, index=idx_defecto, label_visibility="collapsed",
                                 placeholder="Buscar nadador...")
            st.button("", key="ficha_next", icon=":material/chevron_right:", help="Nadador siguiente",
                      on_click=_mover_nadador, args=(1,))
        if f_nad:
            st.session_state.nadador_seleccionado = f_nad
            id_actual = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]['codnadador']
            render_tab_ficha(id_actual, unique_key_suffix="_master")
            
    with tab3: render_tab_relevos_general()


