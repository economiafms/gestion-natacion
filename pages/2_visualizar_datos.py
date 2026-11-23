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

def _cat_actual_de(cod):
    anio = dict_id_anionac.get(cod, 0)
    return asignar_cat(datetime.now().year - anio) if anio else "-"


@st.dialog("Detalle de la mejor marca", width="large")
def dialogo_marca(target_id, estilo, distancia):
    """Al tocar una mejor marca: sus registros, cuánto mejoró y cómo está en su categoría."""
    d = df_full[(df_full['codnadador'] == target_id) & (df_full['Estilo'] == estilo) & (df_full['Distancia'] == distancia)].copy()
    d['segundos'] = d['tiempo'].apply(tiempo_a_segundos)
    d['fecha_dt'] = pd.to_datetime(d['fecha'], errors='coerce')
    d = d.dropna(subset=['segundos']).sort_values('fecha_dt')
    if d.empty:
        st.caption("Sin registros.")
        return
    pb = d.loc[d['segundos'].idxmin()]
    sede_pb = f"{pb.get('sede', '-')} ({pb.get('medida', '-')})"

    st.markdown(f"""<div class="nob-est-head">
<div class="nob-est-name">{html.escape(f"{distancia} {estilo}")}</div>
<div class="nob-mm-time">{html.escape(str(pb['tiempo']))}</div>
<div class="nob-est-desc">Mejor marca · {html.escape(_fecha_txt(pb['fecha']))} · {html.escape(sede_pb)}</div>
</div>""", unsafe_allow_html=True)

    # Progreso del nadador en la prueba (en frases claras)
    frases = []
    previas = d[d['fecha_dt'] < pb['fecha_dt']]
    ant = None
    if not previas.empty:
        ant = previas['segundos'].min()
        frases.append(f"⬇️ Mejoró <b>{ant - pb['segundos']:.2f} s</b> respecto de su marca anterior ({seg_a_tiempo(ant)}).")
    else:
        frases.append("⭐ Es su primera marca registrada en esta prueba.")
    if len(d) > 1:
        dif_1 = d['segundos'].iloc[0] - pb['segundos']
        # Solo si aporta algo distinto a la frase anterior (la 1ª carrera no fue la marca anterior)
        if dif_1 > 0 and (ant is None or d['segundos'].iloc[0] != ant):
            frases.append(f"📉 Desde su primera carrera ({seg_a_tiempo(d['segundos'].iloc[0])}) bajó <b>{dif_1:.2f} s</b>.")
        frases.append(f"⏱️ Nadó esta prueba <b>{len(d)}</b> veces, con un promedio de <b>{seg_a_tiempo(d['segundos'].mean())}</b>.")

    # Comparación con su categoría y género (mejores marcas de cada nadador en la misma prueba)
    todos = df_full[(df_full['Estilo'] == estilo) & (df_full['Distancia'] == distancia)][['codnadador', 'tiempo']].copy()
    todos['segundos'] = todos['tiempo'].apply(tiempo_a_segundos)
    todos = todos.dropna(subset=['segundos']).groupby('codnadador', as_index=False)['segundos'].min()
    mi_cat = _cat_actual_de(target_id)
    generos = df_nad.set_index('codnadador')['codgenero']
    mi_gen = generos.get(target_id)
    gen_txt = {"F": "Femenino", "M": "Masculino"}.get(str(mi_gen).strip().upper(), str(mi_gen))
    de_cat = todos[todos['codnadador'].map(lambda c: _cat_actual_de(c) == mi_cat and generos.get(c) == mi_gen)]
    otros = de_cat[de_cat['codnadador'] != target_id]
    if otros.empty:
        frases.append(f"👥 No hay otros nadadores de su categoría ({mi_cat} · {gen_txt}) con esta prueba para comparar.")
    else:
        prom = otros['segundos'].mean()
        dif = pb['segundos'] - prom
        sentido = "más rápido" if dif < 0 else "más lento"
        frases.append(f"👥 En su categoría ({mi_cat} · {gen_txt}) el promedio de las mejores marcas es "
                      f"<b>{seg_a_tiempo(prom)}</b>: está <b>{abs(dif):.2f} s {sentido}</b>.")
        puesto = int((de_cat['segundos'] < pb['segundos']).sum()) + 1
        frases.append(f"🏅 Es <b>{puesto}° de {len(de_cat)}</b> en su categoría en esta prueba.")

    st.markdown('<div class="nob-mm-frases">' + "".join(f"<div>{f}</div>" for f in frases) + "</div>",
                unsafe_allow_html=True)

    # Todos los registros de la prueba (el más reciente primero)
    seccion(f"Registros · {len(d)}")
    filas = []
    for _, r in d.sort_values('fecha_dt', ascending=False).iterrows():
        try: pos = int(r['posicion'])
        except Exception: pos = 0
        icono = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f'<span class="nob-rec-pos">{pos}°</span>' if pos > 0 else '<span class="nob-rec-pos">–</span>')
        tag = '<span class="nob-rec-tag pb">MEJOR MARCA</span>' if r['segundos'] == pb['segundos'] else ""
        filas.append(
            f'<div class="nob-rec m{pos if pos in (1, 2, 3) else 0}"><div class="nob-rec-med">{icono}</div>'
            f'<div class="nob-rec-body"><div class="nob-rec-t">{html.escape(_fecha_txt(r["fecha"]))} {tag}</div>'
            f'<div class="nob-rec-m">{html.escape(str(r.get("sede", "-")))} ({html.escape(str(r.get("medida", "-")))})</div></div>'
            f'<div class="nob-rec-time">{html.escape(str(r["tiempo"]))}</div></div>')
    st.markdown("".join(filas), unsafe_allow_html=True)

    st.write("")
    with st.container(key="pie_dlg_marca"):
        if st.button("← Volver", key="dlg_marca_volver", use_container_width=True):
            st.rerun()


def _fecha_txt(valor):
    try: return pd.to_datetime(valor).strftime('%d/%m/%Y')
    except Exception: return str(valor)


def render_tab_ficha(target_id, unique_key_suffix=""):
    if not target_id: return

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

    st.markdown(f"""
    <div class="ficha-header">
        <div class="ficha-name">{info['nombre']} {info['apellido']}</div>
        <div class="ficha-grid">
            <div>📅 Nacimiento: <b>{nac_str}</b></div>
            <div>🎂 Edad (al 31/12): <b>{edad_actual} años</b></div>
            <div>🏷️ Categoría: <b>{cat_actual}</b></div>
            <div>⚧️ Género: <b>{info['codgenero']}</b></div>
        </div>
        <div class="ficha-medals">
            🥇 {o} &nbsp; | &nbsp; 🥈 {pl} &nbsp; | &nbsp; 🥉 {br}
        </div>
    </div>
    """, unsafe_allow_html=True)

    mis_t = df_full[df_full['codnadador'] == target_id].copy()
    mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)

    # --- MEJORES MARCAS (mismo diseño; al tocar una se abre su detalle) ---
    if not mis_t.empty:
        st.subheader("✨ Mejores Marcas (PB)")
        pbs = mis_t.loc[mis_t.dropna(subset=['segundos']).groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].sort_values(['Estilo', 'segundos'])

        for ie, estilo in enumerate(pbs['Estilo'].unique()):
            st.markdown(f"<div class='pb-style-header'>{estilo}</div>", unsafe_allow_html=True)
            for idist, (_, r) in enumerate(pbs[pbs['Estilo'] == estilo].iterrows()):
                with st.container(key=f"pbo_{unique_key_suffix}_{target_id}_{ie}_{idist}"):
                    st.markdown(f"""
                    <div class="pb-row">
                        <span class="pb-dist">{r['Distancia']}</span>
                        <span class="pb-time">{r['tiempo']}</span>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"Detalle {r['Distancia']} {estilo}", key=f"pbo_btn_{unique_key_suffix}_{target_id}_{ie}_{idist}"):
                        dialogo_marca(target_id, estilo, r['Distancia'])
        st.caption("Tocá una marca para ver sus registros, cuánto mejoró y cómo está en su categoría.")

    tab_evo, tab_his, tab_rel = st.tabs(["📈 Evolución", "📜 Historial", "🏊‍♂️ Mis relevos"])

    # --- EVOLUCIÓN ---
    with tab_evo:
        conteo = mis_t.dropna(subset=['segundos']).groupby(['Estilo', 'Distancia']).size().reset_index(name='count')
        validos = conteo[conteo['count'] >= 2]

        if not validos.empty:
            # Arranca en la prueba más nadada
            top = validos.sort_values('count', ascending=False).iloc[0]
            c1, c2 = st.columns(2)
            estilos_ok = sorted(validos['Estilo'].unique())
            g_est = c1.selectbox("Estilo Gráfico", estilos_ok, index=estilos_ok.index(top['Estilo']), key=f"g_est{unique_key_suffix}")

            dist_ok = sorted(validos[validos['Estilo'] == g_est]['Distancia'].unique())
            idx_dist = dist_ok.index(top['Distancia']) if (g_est == top['Estilo'] and top['Distancia'] in dist_ok) else 0
            g_dist = c2.selectbox("Distancia Gráfico", dist_ok, index=idx_dist, key=f"g_dist{unique_key_suffix}")

            df_graph = mis_t[(mis_t['Estilo'] == g_est) & (mis_t['Distancia'] == g_dist)].dropna(subset=['segundos']).copy()
            df_graph['fecha_dt'] = pd.to_datetime(df_graph['fecha'], errors='coerce')
            df_graph = df_graph.sort_values('fecha_dt')

            # Datos de la prueba: mejor marca, promedio y mejora desde la primera carrera
            mejor_seg = df_graph['segundos'].min()
            promedio_seg = df_graph['segundos'].mean()
            mejora = df_graph['segundos'].iloc[0] - mejor_seg
            # Última carrera: cómo viene nadando ahora frente a su mejor marca
            ultima_seg = df_graph['segundos'].iloc[-1]
            dif_ultima = ultima_seg - mejor_seg
            txt_ultima = "Última · ¡es su mejor marca!" if dif_ultima <= 0 else f"Última · +{dif_ultima:.2f}s de la mejor"
            st.markdown(f"""<div class="nob-kpis">
<div><b>{seg_a_tiempo(mejor_seg)}</b><small>Mejor marca</small></div>
<div><b>{seg_a_tiempo(promedio_seg)}</b><small>Tiempo promedio</small></div>
<div><b class="{'up' if mejora > 0 else ''}">{f'↓ {mejora:.2f}s' if mejora > 0 else '—'}</b><small>Mejora desde la 1ª carrera</small></div>
<div><b class="{'up' if dif_ultima <= 0 else ''}">{seg_a_tiempo(ultima_seg)}</b><small>{txt_ultima}</small></div>
</div>""", unsafe_allow_html=True)

            # Calcular categoría histórica para tooltip
            if anio_nacimiento_nadador > 0:
                df_graph['cat_hist'] = df_graph['fecha_dt'].apply(lambda x: asignar_cat(x.year - anio_nacimiento_nadador))
            else: df_graph['cat_hist'] = "-"

            # Eje Y: Tiempo (Fake date para plot)
            df_graph['TimeObj'] = pd.to_datetime('2024-01-01') + pd.to_timedelta(df_graph['segundos'], unit='s')

            fig = px.line(df_graph, x='fecha', y='TimeObj', markers=True, template="plotly_dark",
                          hover_data={
                              'fecha': False, 'TimeObj': False,
                              'sede': True, 'Distancia': True, 'cat_hist': True, 'tiempo': True
                          })

            fig.update_traces(line_color='#E53935', name="Registro",
                              hovertemplate="<b>%{customdata[3]}</b><br>📅 %{x|%d/%m/%Y}<br>📍 %{customdata[0]}<br>🏷️ %{customdata[2]}")
            # Línea de referencia: mejor marca
            fig.add_hline(y=pd.to_datetime('2024-01-01') + pd.to_timedelta(mejor_seg, unit='s'),
                          line_dash="dash", line_color="#FFD54F", opacity=0.8,
                          annotation_text=f"Mejor marca {seg_a_tiempo(mejor_seg)}", annotation_position="top left",
                          annotation_font_color="#FFD54F")

            fig.update_yaxes(tickformat="%M:%S.%f", title="Tiempo")
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=40, r=20), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, key=f"graf_evo{unique_key_suffix}")
        else:
            st.info("Necesitas al menos 2 carreras en la misma prueba para ver la evolución.")

    # --- HISTORIAL COMPLETO ---
    with tab_his:
        with st.expander("Filtrar Historial"):
            h1, h2 = st.columns(2)
            hf_est = h1.selectbox("Estilo", ["Todos"] + sorted(mis_t['Estilo'].unique().tolist()), key=f"h_est{unique_key_suffix}")
            hf_dis = h2.selectbox("Distancia", ["Todos"] + sorted(mis_t['Distancia'].unique().tolist()), key=f"h_dis{unique_key_suffix}")

        df_hist = mis_t.copy()
        if hf_est != "Todos": df_hist = df_hist[df_hist['Estilo'] == hf_est]
        if hf_dis != "Todos": df_hist = df_hist[df_hist['Distancia'] == hf_dis]
        df_hist = df_hist.sort_values('fecha', ascending=False)

        for _, r in df_hist.head(20).iterrows():
            try:
                pos_val = int(r['posicion'])
                if pos_val == 1: medal_str = "🥇 1º"
                elif pos_val == 2: medal_str = "🥈 2º"
                elif pos_val == 3: medal_str = "🥉 3º"
                elif pos_val > 0: medal_str = f"Pos: {pos_val}"
                else: medal_str = "-"
            except: medal_str = "-"

            sede_txt = r.get('sede', '-')
            medida_txt = r.get('medida', '-')

            # Calcular categoría en esa fecha
            try:
                anio_carrera = pd.to_datetime(r['fecha']).year
                edad_en_carrera = anio_carrera - anio_nacimiento_nadador
                cat_torneo = asignar_cat(edad_en_carrera)
            except: cat_torneo = "-"

            st.markdown(f"""
            <div class="mobile-card" style="padding:10px;">
                <div style="display:flex; justify-content:space-between; align-items: flex-start;">
                    <div style="flex:1;">
                        <div style="font-weight:bold; color:white; font-size:15px;">{r['Distancia']} {r['Estilo']}</div>
                        <div style="font-size:14px; color:#aaa; margin-top:2px;">📅 {r['fecha']} • {sede_txt} ({medida_txt})</div>
                    </div>
                    <div style="text-align: right; min-width: 100px;">
                        <div style="font-family:monospace; font-weight:bold; color:#4CAF50; font-size:18px;">{r['tiempo']}</div>
                        <div style="font-size:14px; color:#ddd; font-weight:bold; margin-top:2px;">
                            {medal_str} <span style="font-size:13px; color:#999; font-weight:normal;">({cat_torneo})</span>
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

    # --- MIS RELEVOS ---
    with tab_rel:
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

            for _, r in mis_relevos.iterrows():
                grupo_txt = calcular_grupo_relevo(r, data['cat_relevos'])
                html_grid = ""
                for k in range(1, 5):
                    nid = r[f'nadador_{k}']
                    nom = dict_id_nombre.get(nid, "??").split(',')[0]
                    t = str(r[f'tiempo_{k}']).strip()
                    if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                    border_style = "border: 1px solid #E91E63;" if nid == target_id else ""
                    html_grid += f"<div class='swimmer-item' style='{border_style}'>{k}. {nom}</div>"

                try: p_rel = int(r['posicion'])
                except: p_rel = 0
                if p_rel == 1: pos_icon = "🥇 1º"
                elif p_rel == 2: pos_icon = "🥈 2º"
                elif p_rel == 3: pos_icon = "🥉 3º"
                elif p_rel > 0: pos_icon = f"Pos: {p_rel}"
                else: pos_icon = ""

                sede_r = r.get('sede', '-')

                st.markdown(f"""
                <div class="mobile-card" style="border-left: 4px solid #E91E63;">
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
        else: st.info("Sin relevos.")


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

        f_nad = st.selectbox("Seleccionar Atleta:", lista_nombres, index=idx_defecto)
        if f_nad:
            st.session_state.nadador_seleccionado = f_nad
            id_actual = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]['codnadador']
            render_tab_ficha(id_actual, unique_key_suffix="_master")
            
    with tab3: render_tab_relevos_general()


