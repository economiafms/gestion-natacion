import streamlit as st
import datos
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import time
import numpy as np
import html
from nob_ui import select_flechas

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Entrenamientos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id 
mi_nombre = st.session_state.user_name

# Control de estado
if "form_reset_id" not in st.session_state:
    st.session_state.form_reset_id = 0

def reset_carga():
    st.session_state.form_reset_id += 1

# --- FUNCIONES AUXILIARES ---
def a_segundos(t_str):
    """Convierte MM:SS.CC a segundos (float)"""
    try:
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

# Gráficos estáticos: no se pueden mover ni hacer zoom; tocar un punto o barra muestra su cartel
CONFIG_FIJO = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}

def grafico_fijo(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(dragmode=False, hovermode="closest",
                      legend=dict(itemclick=False, itemdoubleclick=False),
                      hoverlabel=dict(bgcolor="#1A0204", bordercolor="#E30613", font_size=13))
    st.plotly_chart(fig, use_container_width=True, config=CONFIG_FIJO)

def fmt_mm_ss(seconds):
    """Genera etiquetas de eje Y en formato MM:SS.CC"""
    if seconds is None or np.isnan(seconds): return ""
    m = int(seconds // 60)
    s = int(seconds % 60)
    c = int(round((seconds - int(seconds)) * 100))
    return f"{m:02d}:{s:02d}.{c:02d}"

from nob_ui import hero, seccion
hero("Centro de Entrenamiento", "🏋️")

# --- ESTILOS (mismo lenguaje visual que Inicio y Rutinas) ---
st.markdown("""
<style>
/* Promedios y ritmos: tarjetas con el diseño original */
    .test-card { 
        background-color: #262730; 
        border: 1px solid #444; 
        border-radius: 10px; 
        padding: 15px; 
        margin-bottom: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
        border-left: 5px solid #E30613; 
    }
    .test-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: flex-start; 
        margin-bottom: 8px; 
        border-bottom: 1px solid #444; 
        padding-bottom: 8px; 
    }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #aaa; font-weight: bold; }
    .test-date { font-size: 12px; color: #888; margin-left: 5px; }
    .final-time { 
        font-family: 'Courier New', monospace; 
        font-size: 24px; 
        font-weight: bold; 
        color: #E30613; 
        text-align: right; 
        background: rgba(0,0,0,0.2); 
        padding: 2px 8px; 
        border-radius: 4px; 
    }
/* Tarjetas de promedio por prueba */
.tst-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-bottom: 4px; }
.tst-tile, .tst-rec {
  padding: 12px 14px; border-radius: 16px; position: relative; overflow: hidden;
  background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
  border: 1px solid rgba(255,255,255,0.08);
}
.tst-tile::before, .tst-rec::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, #E30613, #FF6A72); }
.tst-e { font-size: 15px; font-weight: 800; color: #fff; text-transform: uppercase; letter-spacing: .3px; }
.tst-d { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 1px; }
.tst-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; margin-top: 10px; }
.tst-k { display: block; font-size: 9.5px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;
  color: rgba(255,255,255,0.45); margin-bottom: 3px; }
.tst-time { font-size: 24px; font-weight: 900; color: #fff; line-height: 1; font-variant-numeric: tabular-nums; }
.tst-pace { text-align: right; }
.tst-pace b { font-size: 16px; font-weight: 800; color: #FF6B72; font-variant-numeric: tabular-nums; }
.tst-n { display: inline-block; margin-top: 10px; padding: 2px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 700;
  color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); }
/* Registro individual */
.tst-rec { margin-bottom: 8px; }
.tst-rec-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.tst-rec .tst-time { font-size: 26px; color: #fff; }
.tst-fecha { display: inline-block; margin-left: 6px; font-size: 11px; color: rgba(255,255,255,0.5); }
.tst-splits { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.tst-split { flex: 1 1 0; min-width: 62px; text-align: center; padding: 6px 4px; border-radius: 10px;
  background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.06); }
.tst-split small { display: block; font-size: 9.5px; font-weight: 700; letter-spacing: 1px; color: rgba(255,255,255,0.45); }
.tst-split b { font-size: 14px; color: #eee; font-variant-numeric: tabular-nums; }
/* Aviso de configuración de la prueba */
.tst-info { padding: 12px 14px; border-radius: 14px; margin: 6px 0 10px; font-size: 13.5px; color: rgba(255,255,255,0.85);
  background: rgba(227,6,19,0.08); border: 1px solid rgba(227,6,19,0.30); }
.tst-info b { color: #fff; }
/* Etiqueta de cada parcial en la carga */
.tst-plab { padding-top: 8px; font-size: 13px; font-weight: 800; color: #fff; }
.tst-plab small { display: block; font-size: 10.5px; font-weight: 600; color: rgba(255,255,255,0.5); }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def leer_entrenamientos_fresco():
    """Hoja Entrenamientos recién leída (sin caché). None si falla la lectura."""
    try:
        return conn.read(worksheet="Entrenamientos", ttl=0).copy()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()   # hoja totalmente vacía: no hay nada que proteger
    except Exception:
        return None

def cargar_entrenamientos():
    try:
        return {
            "nadadores": datos.leer("Nadadores"),
            "entrenamientos": datos.leer("Entrenamientos"),
            "estilos": datos.leer("Estilos"),
            "distancias": datos.leer("Distancias")
        }
    except: return None

db = cargar_entrenamientos()
if not db: st.stop()

# --- PROCESAMIENTO ROBUSTO DE DATOS ---
df_nad = db['nadadores'].copy()
df_ent = db['entrenamientos'].copy()
df_est = db['estilos'].copy()
df_dist = db['distancias'].copy()

# Normalizar columnas (minúsculas y sin espacios)
df_nad.columns = df_nad.columns.str.strip().str.lower()
df_ent.columns = df_ent.columns.str.strip().str.lower()
df_est.columns = df_est.columns.str.strip().str.lower()
df_dist.columns = df_dist.columns.str.strip().str.lower()

# Normalizar claves de cruce (IDs)
for df in [df_ent, df_est, df_dist]:
    if 'codestilo' in df.columns:
        df['codestilo'] = df['codestilo'].astype(str).str.strip()
    if 'coddistancia' in df.columns:
        df['coddistancia'] = df['coddistancia'].astype(str).str.strip()

# Preparar datos de usuario
nad_info = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_info.iloc[0]['apellido'].upper()}, {nad_info.iloc[0]['nombre']}" if not nad_info.empty else mi_nombre
lista_noms = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in df_dist['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

# --- DEFINICIÓN DE PESTAÑAS SEGÚN ROL ---
if rol == "M":
    tab_ver, tab_cargar, tab_equipo = st.tabs(["📂 Historial", "📝 Cargar Test", "👥 Promedios Equipo"])
else:
    tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    with st.container(key=f"carga_container_{st.session_state.form_reset_id}"):
        
        # --- PASO 1 ---
        seccion("1 · Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        # En la carga usamos lista_noms completa (todos los nadadores)
        n_in = c2.selectbox("Nadador", [mi_nom_comp] if rol=="N" else lista_noms, index=0 if rol=="N" else None)
        id_nad_target = mi_id if rol=="N" else (df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None)
        
        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", df_est['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        mostrar_paso_2 = False
        
        if n_in and est_val and dist_t_val:
            id_est = df_est[df_est['descripcion'] == est_val].iloc[0]['codestilo']
            id_dt = df_dist[df_dist['descripcion'] == dist_t_val].iloc[0]['coddistancia']
            fecha_str = f_val.strftime('%Y-%m-%d')
            
            # Validación duplicados
            duplicado = False
            if not df_ent.empty:
                existe = df_ent[
                    (df_ent['codnadador'].astype(str) == str(id_nad_target)) & 
                    (df_ent['fecha'].astype(str) == fecha_str) & 
                    (df_ent['codestilo'].astype(str) == str(id_est)) &
                    (df_ent['coddistancia'].astype(str) == str(id_dt))
                ]
                if not existe.empty: duplicado = True
            
            if duplicado:
                st.error(f"⛔ Ya existe un registro de {est_val} {dist_t_val} para esta fecha.")
            else:
                mostrar_paso_2 = True
                m_tot = int(dist_t_val.split(" ")[0])
                m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
                msg_par = f"Se habilitarán tomas de parciales cada <b>{m_par} mts</b>." if m_par > 0 else "Distancia corta o relevo: Sin toma de parciales."
                
                st.markdown(f"<div class='tst-info'><b>{dist_t_val} {est_val}</b><br>{msg_par}</div>", unsafe_allow_html=True)
                
                quiere_p = False
                if m_par > 0:
                    quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True)
                    if quiere_p:
                        st.caption("ℹ️ Podés cargar parciales cronometrados o individuales. El sistema los detecta automáticamente.")

        # --- PASO 2 ---
        if mostrar_paso_2:
            seccion("2 · Tiempos")
            
            with st.form("form_reg", clear_on_submit=False):
                st.markdown(f'<div class="nob-top-tit">Tiempo final · {dist_t_val}</div>', unsafe_allow_html=True)
                
                tf1, tf2, tf3 = st.columns(3)
                mf = tf1.number_input("Min", 0, 59, 0)
                sf = tf2.number_input("Seg", 0, 59, 0)
                cf = tf3.number_input("Cent", 0, 99, 0)
                
                lp = []
                if quiere_p:
                    st.markdown(f'<div class="nob-top-tit" style="margin-top:10px;">Parciales cada {m_par} m</div>', unsafe_allow_html=True)
                    for i in range(1, 5):
                        px1, px2, px3, px4 = st.columns([1.2, 1, 1, 1], vertical_alignment="center")
                        px1.markdown(f'<div class="tst-plab">P{i}<small>{m_par * (i - 1)}–{m_par * i} m</small></div>', unsafe_allow_html=True)
                        pm = px2.number_input("M", 0, 59, 0, key=f"pm_{i}_{m_tot}", label_visibility="collapsed")
                        ps = px3.number_input("S", 0, 59, 0, key=f"ps_{i}_{m_tot}", label_visibility="collapsed")
                        pc = px4.number_input("C", 0, 99, 0, key=f"pc_{i}_{m_tot}", label_visibility="collapsed")
                        lp.append(f"{pm:02d}:{ps:02d}.{pc:02d}" if (pm+ps+pc)>0 else "")
                
                submitted = st.form_submit_button("Guardar registro", type="primary", icon=":material/save:", use_container_width=True)
                
                if submitted:
                    s_final = (mf*60) + sf + (cf/100)
                    if s_final == 0:
                        st.error("⚠️ El tiempo final es obligatorio.")
                    else:
                        lp_final = [] 
                        s_parciales_norm = 0
                        tipo_detectado = "INDIVIDUALES"
                        
                        raw_secs = []
                        for p_str in lp:
                            sec = a_segundos(p_str)
                            if sec is not None and sec > 0:
                                raw_secs.append(sec)
                        
                        if raw_secs:
                            sum_raw = sum(raw_secs)
                            last_raw = raw_secs[-1]
                            is_increasing = all(x < y for x, y in zip(raw_secs, raw_secs[1:]))
                            tolerance = 2.0 
                            
                            es_acumulado = False
                            
                            if abs(sum_raw - s_final) <= tolerance:
                                es_acumulado = False
                                tipo_detectado = "INDIVIDUALES"
                            elif is_increasing and abs(last_raw - s_final) <= tolerance:
                                es_acumulado = True
                                tipo_detectado = "CRONOMETRADOS (Acumulados)"
                            elif is_increasing and sum_raw > (s_final * 1.5):
                                es_acumulado = True
                                tipo_detectado = "CRONOMETRADOS (Acumulados)"
                            else:
                                es_acumulado = False
                                tipo_detectado = "INDIVIDUALES"

                            norm_secs = []
                            if es_acumulado:
                                prev = 0
                                for curr in raw_secs:
                                    diff = curr - prev
                                    if diff <= 0: diff = 0.01 
                                    norm_secs.append(diff)
                                    prev = curr
                            else:
                                norm_secs = raw_secs
                            
                            lp_final = [fmt_mm_ss(s) for s in norm_secs]
                            s_parciales_norm = sum(norm_secs)
                            
                            st.info(f"ℹ️ Detección automática: **{tipo_detectado}**. Se guardaron como tramos individuales.")

                            if abs(s_parciales_norm - s_final) > 1.0:
                                st.warning(f"⚠️ Atención: La suma de los parciales ({fmt_mm_ss(s_parciales_norm)}) difiere del Tiempo Final ({fmt_mm_ss(s_final)}).")
                        else:
                            lp_final = []

                        while len(lp_final) < 4: lp_final.append("")
                        
                        with st.spinner("Guardando..."):
                            try:
                                # Se relee la hoja en fresco antes de escribir: así no se pisan tests que
                                # otro haya guardado mientras tanto (la copia en caché puede estar vieja).
                                df_fresco = leer_entrenamientos_fresco()
                                if df_fresco is None:
                                    st.error("⚠️ No se pudo leer la planilla. No se guardó nada para proteger los datos; probá de nuevo.")
                                    st.stop()
                                ya_existe = False
                                if not df_fresco.empty:
                                    _f = df_fresco.copy()
                                    _f.columns = _f.columns.str.strip().str.lower()
                                    ya_existe = not _f[
                                        (_f['codnadador'].astype(str).str.replace(r'\.0$', '', regex=True) == str(int(id_nad_target))) &
                                        (_f['fecha'].astype(str) == fecha_str) &
                                        (_f['codestilo'].astype(str).str.strip() == str(id_est)) &
                                        (_f['coddistancia'].astype(str).str.strip() == str(id_dt))
                                    ].empty
                                if ya_existe:
                                    st.error(f"⛔ Ya existe un registro de {est_val} {dist_t_val} para esta fecha.")
                                    st.stop()

                                _ids = df_fresco['id_entrenamiento'] if 'id_entrenamiento' in df_fresco.columns else pd.Series(dtype=float)
                                max_id = pd.to_numeric(_ids, errors='coerce').max() if not df_fresco.empty else 0
                                new_id = int(0 if pd.isna(max_id) else max_id) + 1
                                id_dp = df_dist[df_dist['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia'] if quiere_p else ""

                                row = pd.DataFrame([{
                                    "id_entrenamiento": new_id, "fecha": fecha_str,
                                    "codnadador": int(id_nad_target), "codestilo": id_est,
                                    "coddistancia": id_dt, "coddistancia_parcial": id_dp,
                                    "tiempo_final": f"{mf:02d}:{sf:02d}.{cf:02d}",
                                    "parcial_1": lp_final[0], "parcial_2": lp_final[1],
                                    "parcial_3": lp_final[2], "parcial_4": lp_final[3],
                                    "observaciones": ""
                                }])
                                conn.update(worksheet="Entrenamientos", data=pd.concat([df_fresco, row], ignore_index=True))
                                st.success("✅ Guardado."); time.sleep(1); reset_carga(); datos.invalidar("Entrenamientos"); st.rerun()  # la pausa es a propósito: deja terminar la escritura en Google
                            except Exception as e: st.error(f"Error: {e}")

# ==============================================================================
#  HISTORIAL (NADADOR INDIVIDUAL)
# ==============================================================================
with tab_ver:
    target_id = mi_id if rol == "N" else None
    
    # 1. Selector de Nadador (Solo para M o P)
    if rol in ["M", "P"]:
        # FILTRO INTELIGENTE:
        if not df_ent.empty:
            ids_con_historia = df_ent['codnadador'].unique().astype(str)
            df_nad_con_historia = df_nad[df_nad['codnadador'].astype(str).isin(ids_con_historia)]
            lista_noms_filtrada = sorted((df_nad_con_historia['apellido'].astype(str).str.upper() + ", " + df_nad_con_historia['nombre'].astype(str)).unique().tolist())
        else:
            lista_noms_filtrada = []

        sel_n = select_flechas("Nadador", lista_noms_filtrada, "h_nad") if lista_noms_filtrada else None
        if sel_n: 
            target_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel_n].iloc[0]['codnadador']
    
    if target_id:
        df_h = df_ent[df_ent['codnadador'].astype(str) == str(target_id)].copy()
        
        if not df_h.empty:
            df_h = df_h.merge(df_est, on='codestilo', how='left').merge(df_dist, on='coddistancia', how='left')
            
            # --- SECCIÓN: PROMEDIOS Y RITMOS (100% LECTURA SEGURA) ---
            seccion("Promedios y ritmos")
            
            df_stats = df_h.copy()
            df_stats['seg_final'] = df_stats['tiempo_final'].apply(a_segundos)

            def get_dist(text):
                try: 
                    return int(''.join(filter(str.isdigit, str(text))))
                except: 
                    return 0

            df_stats['dist_num'] = df_stats['descripcion_y'].apply(get_dist)
            
            # Solo consideramos distancias >= 50m con tiempo válido
            df_stats = df_stats[(df_stats['dist_num'] >= 50) & (df_stats['seg_final'].notna())]

            if not df_stats.empty:
                stats_grouped = df_stats.groupby(['descripcion_x', 'descripcion_y', 'dist_num']).agg(
                    veces=('id_entrenamiento', 'count'),
                    promedio_seg=('seg_final', 'mean')
                ).reset_index()

                # LÓGICA DE RITMO SEGÚN DISTANCIA
                stats_grouped['dist_ritmo'] = np.where(stats_grouped['dist_num'] == 50, 25, 50)
                stats_grouped['ritmo_seg'] = stats_grouped['promedio_seg'] / (stats_grouped['dist_num'] / stats_grouped['dist_ritmo'])
                stats_grouped = stats_grouped.sort_values(['descripcion_x', 'dist_num'])

                # Renderizar tarjetas lado a lado
                for idx, row in stats_grouped.iterrows():
                    label_ritmo = f"Ritmo c/{int(row['dist_ritmo'])}m:"
                    texto_registros = f"{row['veces']} registro" if row['veces'] == 1 else f"{row['veces']} registros"
                    
                    st.markdown(f"""
                    <div class="test-card">
                        <div class="test-header" style="border-bottom: none; margin-bottom: 0; padding-bottom: 0; align-items: center;">
                            <div>
                                <div class="test-style">{row['descripcion_x']}</div>
                                <div class="test-dist">{row['descripcion_y']}</div>
                                <div class="test-date" style="margin-left: 0; margin-top: 2px;">{texto_registros}</div>
                            </div>
                            <div style="display: flex; gap: 20px; align-items: center; text-align: right;">
                                <div>
                                    <div style="font-size: 11px; color: #aaa; margin-bottom: 2px; letter-spacing: 0.5px;">TIEMPO MEDIO</div>
                                    <div class="final-time" style="background: transparent; padding: 0; color: #eee;">{fmt_mm_ss(row['promedio_seg'])}</div>
                                </div>
                                <div style="border-left: 1px solid #444; padding-left: 20px;">
                                    <div style="font-size: 11px; color: #888; margin-bottom: 2px; text-transform: uppercase;">{label_ritmo}</div>
                                    <div style="font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; color: #E30613;">{fmt_mm_ss(row['ritmo_seg'])}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aún no hay suficientes registros de distancia (≥ 50m) para calcular promedios y ritmos.")


            # --- FILTROS DINÁMICOS ---
            seccion("Registros")
            
            est_opts = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            c_f1, c_f2 = st.columns(2)
            f_est = select_flechas("Estilo", est_opts, "h_f_est", contenedor=c_f1)
            
            if f_est == "Todos":
                valid_dists = sorted(df_h['descripcion_y'].unique().tolist())
            else:
                valid_dists = sorted(df_h[df_h['descripcion_x'] == f_est]['descripcion_y'].unique().tolist())
                
            f_dist = select_flechas("Distancia", ["Todos"] + valid_dists, "h_f_dist", contenedor=c_f2)

            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # --- GRÁFICO RESUMEN ---
            if f_est == "Todos" and f_dist == "Todos" and not df_filt.empty:
                st.markdown('<div class="nob-top-tit" style="margin-top:8px;">Tests por estilo</div>', unsafe_allow_html=True)
                
                conteo = df_filt.groupby(['descripcion_x', 'descripcion_y']).size().reset_index(name='Cantidad')
                conteo['Etiqueta'] = conteo['Cantidad'].apply(lambda x: str(x) if x > 1 else "")
                
                fig_count = px.bar(
                    conteo, 
                    x='descripcion_x', 
                    y='Cantidad', 
                    color='descripcion_y',
                    text='Etiqueta',
                    color_discrete_sequence=px.colors.sequential.OrRd[::-1],
                    labels={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'},
                    custom_data=['descripcion_y']
                )
                
                fig_count.update_traces(
                    textposition='inside', 
                    textfont=dict(size=20, color='white'), 
                    hovertemplate='<b>%{x}</b> · %{customdata[0]}<br>Tests: %{y}<extra></extra>'
                )
                
                fig_count.update_layout(
                    height=300, 
                    template="plotly_dark", 
                    showlegend=True, 
                    legend_title_text="Distancia",
                    margin=dict(l=0, r=0, t=30, b=0),
                    yaxis=dict(showticklabels=False, title="Cantidad", showgrid=False), 
                    xaxis_title=""
                )
                grafico_fijo(fig_count)

            # --- GRÁFICO EVOLUCIÓN ---
            if f_est != "Todos" and f_dist != "Todos" and len(df_filt) >= 2:
                st.markdown('<div class="nob-top-tit" style="margin-top:8px;">Evolución</div>', unsafe_allow_html=True)
                df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                
                min_val, max_val = df_filt['seg'].min(), df_filt['seg'].max()
                tick_vals = np.linspace(min_val, max_val, 5) if max_val > min_val else [min_val]
                tick_text = [fmt_mm_ss(v) for v in tick_vals]

                fig = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, line_shape='spline', 
                              color_discrete_sequence=['#E30613'], custom_data=['tiempo_final'])
                
                fig.update_traces(hovertemplate='📅 %{x|%d/%m/%Y}<br>⏱️ %{customdata[0]}<extra></extra>', marker=dict(size=10))
                
                fig.update_layout(
                    height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", 
                    yaxis=dict(title="Tiempo", tickmode='array', tickvals=tick_vals, ticktext=tick_text),
                    xaxis_title=""
                )
                grafico_fijo(fig)

            # --- LISTADO ---
            st.markdown(f'<div class="nob-top-tit" style="margin-top:8px;">{len(df_filt)} {"registro" if len(df_filt) == 1 else "registros"}</div>', unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                p_validos = [p for p in ps if p and str(p).lower() not in ['nan', 'none', '', '00:00.00']]
                
                splits_block = ""
                if p_validos:
                    grid = "".join(f'<div class="tst-split"><small>P{i+1}</small><b>{html.escape(str(p))}</b></div>'
                                   for i, p in enumerate(p_validos))
                    splits_block = f'<div class="tst-splits">{grid}</div>'

                st.markdown(f"""<div class="tst-rec"><div class="tst-rec-top"><div>
<div class="tst-e">{html.escape(str(r.get('descripcion_x', '-')))}</div>
<div class="tst-d">{html.escape(str(r.get('descripcion_y', '-')))}<span class="tst-fecha">· {f_fmt}</span></div></div>
<div><span class="tst-k" style="text-align:right">Final</span><span class="tst-time">{html.escape(str(r['tiempo_final']))}</span></div>
</div>{splits_block}</div>""", unsafe_allow_html=True)

                if p_validos and st.toggle("Analizar tramos", key=f"chk_{r['id_entrenamiento']}"):
                    p_seg = [a_segundos(p) for p in p_validos]
                    p_labels = [fmt_mm_ss(s) for s in p_seg]
                    
                    df_bar = pd.DataFrame({
                        'Tramo': [f"P{i+1}" for i in range(len(p_seg))],
                        'Segundos': p_seg,
                        'Etiqueta': p_labels
                    })

                    fig_bar = px.bar(df_bar, x='Tramo', y='Segundos', text='Etiqueta',
                                     color_discrete_sequence=['#E30613'])
                    
                    fig_bar.update_traces(textposition='auto', textfont=dict(size=18), hovertemplate='<b>%{x}</b><br>⏱️ %{text}<extra></extra>')
                    
                    fig_bar.update_layout(
                        height=200, 
                        template="plotly_dark", 
                        showlegend=False, 
                        margin=dict(l=0, r=0, t=10, b=0),
                        yaxis=dict(showticklabels=False, title=None, showgrid=False), 
                        xaxis_title="Parcial"
                    )
                    grafico_fijo(fig_bar)
        else:
            st.info("Todavía no hay tests cargados.")

# ==============================================================================
#  PROMEDIOS DEL EQUIPO (SOLO USUARIOS 'M')
# ==============================================================================
if rol == "M":
    with tab_equipo:
        seccion("Promedios del equipo")
        
        if not df_ent.empty:
            # Unir toda la información para cruzar entrenamientos con datos de los nadadores
            df_global = df_ent.merge(df_est, on='codestilo', how='left') \
                              .merge(df_dist, on='coddistancia', how='left') \
                              .merge(df_nad, on='codnadador', how='left')
            
            # --- FILTROS DE LA PRUEBA ---
            c_f1_eq, c_f2_eq = st.columns(2)
            estilos_disp = sorted(df_global['descripcion_x'].dropna().unique().tolist())
            f_est_eq = select_flechas("Estilo", estilos_disp, "eq_est", contenedor=c_f1_eq)
            
            if f_est_eq:
                dist_disp = sorted(df_global[df_global['descripcion_x'] == f_est_eq]['descripcion_y'].dropna().unique().tolist())
                f_dist_eq = select_flechas("Distancia", dist_disp, "eq_dist", contenedor=c_f2_eq)
                
                if f_dist_eq:
                    # Filtrar por la prueba seleccionada
                    df_eq_filt = df_global[(df_global['descripcion_x'] == f_est_eq) & (df_global['descripcion_y'] == f_dist_eq)].copy()
                    
                    df_eq_filt['seg_final'] = df_eq_filt['tiempo_final'].apply(a_segundos)
                    
                    def get_dist_eq(text):
                        try: 
                            return int(''.join(filter(str.isdigit, str(text))))
                        except: 
                            return 0
                            
                    dist_num_eq = get_dist_eq(f_dist_eq)
                    df_eq_filt = df_eq_filt[df_eq_filt['seg_final'].notna()]
                    
                    if not df_eq_filt.empty:
                        # Agrupar por nadador calculando su promedio para esta prueba
                        stats_eq = df_eq_filt.groupby(['codnadador', 'apellido', 'nombre']).agg(
                            promedio_seg=('seg_final', 'mean')
                        ).reset_index()
                        
                        # Calcular ritmo según distancia
                        if dist_num_eq >= 50:
                            dist_ritmo_eq = 25 if dist_num_eq == 50 else 50
                            stats_eq['ritmo_seg'] = stats_eq['promedio_seg'] / (dist_num_eq / dist_ritmo_eq)
                        else:
                            dist_ritmo_eq = dist_num_eq
                            stats_eq['ritmo_seg'] = stats_eq['promedio_seg']
                            
                        # Ordenar del más rápido al más lento
                        stats_eq = stats_eq.sort_values('promedio_seg')
                        
                        st.markdown(f'<div class="nob-top-tit">{html.escape(f_est_eq)} · {html.escape(f_dist_eq)} · '
                                    f'{len(stats_eq)} nadadores</div>', unsafe_allow_html=True)
                        label_ritmo_eq = f"c/{int(dist_ritmo_eq)} m" if dist_num_eq >= 50 else "ritmo"
                        filas_eq = []
                        for pos, (_, row_eq) in enumerate(stats_eq.iterrows(), start=1):
                            nombre_nadador = f"{str(row_eq['apellido']).upper()}, {row_eq['nombre']}"
                            filas_eq.append(
                                f'<div class="nob-top"><span class="p">{pos}</span>'
                                f'<span class="n">{html.escape(nombre_nadador)}</span>'
                                f'<span class="m">{label_ritmo_eq} {fmt_mm_ss(row_eq["ritmo_seg"])}</span>'
                                f'<span class="t">{fmt_mm_ss(row_eq["promedio_seg"])}</span></div>')
                        st.markdown("".join(filas_eq), unsafe_allow_html=True)
                    else:
                        st.info("No hay tiempos registrados para esta prueba específica.")
        else:
            st.info("No hay registros de entrenamientos en la base de datos.")
