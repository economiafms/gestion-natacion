import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Ránking NOB", layout="centered")

if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id 
mi_nombre = st.session_state.user_name

st.title("🏆 Ránking Oficial NOB")

st.markdown("""
<style>
    .rk-card { background-color: #262730; border: 1px solid #444; border-radius: 10px; padding: 12px; margin-bottom: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; }
    .rk-pos { font-size: 24px; font-weight: bold; width: 40px; text-align: center; color: #aaa; }
    .rk-pos-1 { color: #FFD700; font-size: 28px; } /* Oro */
    .rk-pos-2 { color: #C0C0C0; font-size: 26px; } /* Plata */
    .rk-pos-3 { color: #CD7F32; font-size: 24px; } /* Bronce */
    .rk-info { flex-grow: 1; padding-left: 15px; border-left: 1px solid #444; margin-left: 10px; }
    .rk-name { font-size: 18px; font-weight: bold; color: white; }
    .rk-det { font-size: 12px; color: #888; }
    .rk-time { font-family: 'Courier New', monospace; font-size: 22px; font-weight: bold; color: #E30613; background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 6px; }
    .my-card { border: 2px solid #E30613; background-color: #382525; }
    
    .test-card { background-color: #262730; border: 1px solid #444; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border-left: 5px solid #E30613; }
    .test-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; border-bottom: 1px solid #444; padding-bottom: 8px; }
    .test-style { font-size: 18px; font-weight: bold; color: white; text-transform: uppercase; }
    .test-dist { font-size: 14px; color: #aaa; font-weight: bold; }
    .test-date { font-size: 12px; color: #888; margin-left: 5px; }
    .final-time { font-family: 'Courier New', monospace; font-size: 24px; font-weight: bold; color: #E30613; text-align: right; background: rgba(0,0,0,0.2); padding: 2px 8px; border-radius: 4px; }
    .splits-container { margin-top: 10px; padding: 10px; background: #1e1e1e; border-radius: 6px; border: 1px solid #333; }
    .splits-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
    .split-item { text-align: center; background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def tiempo_a_seg(t_str):
    try:
        partes = str(t_str).replace('.', ':').split(':')
        return float(partes[0]) * 60 + float(partes[1]) + (float(partes[2])/100 if len(partes)>2 else 0)
    except: return 9999.0

@st.cache_data(ttl="5m")
def cargar_datos_ranking():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "relevos": conn.read(worksheet="Relevos")
        }
    except: return None

db = cargar_datos_ranking()
if not db: st.stop()

# --- PROCESAMIENTO BASE ---
df_nad = db['nadadores'].copy()
df_t = db['tiempos'].copy()
df_est = db['estilos'].copy()
df_dist = db['distancias'].copy()
df_rel = db['relevos'].copy() if 'relevos' in db else pd.DataFrame()

# Normalizar columnas
for df in [df_nad, df_t, df_est, df_dist, df_rel]:
    df.columns = df.columns.str.strip().str.lower()
    
# --- CRUZAR DATOS INDIVIDUALES ---
if not df_t.empty:
    df_t['codnadador'] = pd.to_numeric(df_t['codnadador'], errors='coerce')
    df_t['codestilo'] = df_t['codestilo'].astype(str).str.strip()
    df_t['coddistancia'] = df_t['coddistancia'].astype(str).str.strip()
    df_t['segundos'] = df_t['tiempo'].apply(tiempo_a_seg)
    
    df_est['codestilo'] = df_est['codestilo'].astype(str).str.strip()
    df_dist['coddistancia'] = df_dist['coddistancia'].astype(str).str.strip()
    df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce')
    
    df_full = df_t.merge(df_nad, on='codnadador', how='inner')
    df_full = df_full.merge(df_est, on='codestilo', how='left')
    df_full = df_full.merge(df_dist, on='coddistancia', how='left')
else:
    df_full = pd.DataFrame()

# --- PREPROCESAR DATOS DE RELEVOS ---
if not df_rel.empty:
    # Obtener un diccionario rápido de IDs a Nombres para armar los relevos
    dict_nad = {}
    for _, rn in df_nad.iterrows():
        try:
            dict_nad[float(rn['codnadador'])] = f"{str(rn.get('apellido','')).upper()}, {str(rn.get('nombre',''))}"
        except: pass

    # Mapeo de nombres de los 4 nadadores
    for i in range(1, 5):
        col_n = f'nadador_{i}'
        if col_n in df_rel.columns:
            df_rel[f'nom_{i}'] = pd.to_numeric(df_rel[col_n], errors='coerce').map(dict_nad).fillna("S/D")
        else:
            df_rel[f'nom_{i}'] = "S/D"
    
    # Mapeos inteligentes de columnas (por si usas los nombres directos o los códigos)
    if 'codestilo' in df_rel.columns:
        df_rel['codestilo'] = df_rel['codestilo'].astype(str).str.strip()
        df_rel = df_rel.merge(df_est[['codestilo', 'descripcion']], on='codestilo', how='left').rename(columns={'descripcion': 'estilo_desc'})
        df_rel['estilo_show'] = df_rel['estilo_desc'].fillna(df_rel['codestilo'])
    else:
        df_rel['estilo_show'] = df_rel.get('estilo', df_rel.get('prueba', 'Posta'))

    if 'coddistancia' in df_rel.columns:
        df_rel['coddistancia'] = df_rel['coddistancia'].astype(str).str.strip()
        df_rel = df_rel.merge(df_dist[['coddistancia', 'descripcion']], on='coddistancia', how='left').rename(columns={'descripcion': 'dist_desc'})
        df_rel['dist_show'] = df_rel['dist_desc'].fillna(df_rel['coddistancia'])
    else:
        df_rel['dist_show'] = df_rel.get('distancia', '4x50')
        
    df_rel['genero_show'] = df_rel.get('genero', df_rel.get('codgenero', 'Mixto'))
    
    # Calcular segundos para poder ordenar
    if 'tiempo_final' in df_rel.columns:
        df_rel['segundos'] = df_rel['tiempo_final'].apply(tiempo_a_seg)
    else:
        df_rel['segundos'] = 9999.0

    # Función para detectar si el usuario logueado es parte de la posta
    def is_my_relay(row):
        try:
            for i in range(1, 5):
                col = f'nadador_{i}'
                if col in row and pd.notna(row[col]):
                    if float(row[col]) == float(mi_id):
                        return True
        except: pass
        return False
        
    df_rel['es_mio'] = df_rel.apply(is_my_relay, axis=1)

# ==============================================================================
# TABS PRINCIPALES
# ==============================================================================
tab_indiv, tab_relevos = st.tabs(["🏊‍♂️ INDIVIDUALES", "🤝 RELEVOS"])

# ==============================================================================
# TAB 1: INDIVIDUALES (INTACTO)
# ==============================================================================
with tab_indiv:
    if df_full.empty:
        st.info("No hay tiempos registrados.")
    else:
        # Filtros
        c1, c2, c3 = st.columns(3)
        
        opts_gen = ["Todos"] + sorted(df_full['codgenero'].dropna().unique().tolist())
        f_gen = c1.selectbox("Género", opts_gen)
        
        df_f1 = df_full.copy()
        if f_gen != "Todos": df_f1 = df_f1[df_f1['codgenero'] == f_gen]
        opts_est = ["Todos"] + sorted(df_f1['descripcion_x'].dropna().unique().tolist())
        f_est = c2.selectbox("Estilo", opts_est)
        
        df_f2 = df_f1.copy()
        if f_est != "Todos": df_f2 = df_f2[df_f2['descripcion_x'] == f_est]
        opts_dist = ["Todas"] + sorted(df_f2['descripcion_y'].dropna().unique().tolist())
        f_dist = c3.selectbox("Distancia", opts_dist)
        
        st.divider()
        
        # Aplicar Filtros Finales
        df_show = df_f2.copy()
        if f_dist != "Todas": df_show = df_show[df_show['descripcion_y'] == f_dist]
        
        if df_show.empty:
            st.warning("No hay registros para estos filtros.")
        else:
            df_best = df_show.sort_values('segundos').drop_duplicates(subset=['codnadador'], keep='first')
            df_best = df_best.sort_values('segundos').reset_index(drop=True)
            df_best.index += 1
            
            st.markdown(f"#### Resultados: {f_est if f_est != 'Todos' else 'Todas'} - {f_dist if f_dist != 'Todas' else 'Todas'} ({f_gen})")
            
            for pos, row in df_best.iterrows():
                es_yo = (row['codnadador'] == mi_id)
                nom_completo = f"{str(row.get('apellido','')).upper()}, {str(row.get('nombre',''))}"
                
                clase_pos = f"rk-pos-{pos}" if pos <= 3 else ""
                clase_card = "my-card" if es_yo else ""
                icono_yo = "⭐ " if es_yo else ""
                
                detalles = f"{row.get('descripcion_x', '')} | {row.get('descripcion_y', '')}"
                if 'fecha' in row and pd.notna(row['fecha']):
                    try:
                        f_dt = pd.to_datetime(row['fecha']).strftime('%d/%m/%Y')
                        detalles += f" | 📅 {f_dt}"
                    except: pass
                
                st.markdown(f"""
                <div class="rk-card {clase_card}">
                    <div class="rk-pos {clase_pos}">#{pos}</div>
                    <div class="rk-info">
                        <div class="rk-name">{icono_yo}{nom_completo}</div>
                        <div class="rk-det">{detalles}</div>
                    </div>
                    <div class="rk-time">{row['tiempo']}</div>
                </div>
                """, unsafe_allow_html=True)


# ==============================================================================
# TAB 2: RELEVOS
# ==============================================================================
with tab_relevos:
    if df_rel.empty:
        st.info("No hay registros históricos de postas en la tabla Relevos.")
    else:
        st.markdown("Top histórico de las mejores formaciones de relevos del equipo.")
        
        # Filtros Relevos (Llenados dinámicamente con lo que existe en la tabla)
        cr1, cr2, cr3 = st.columns(3)
        
        opts_gen_rel = ["Todos"] + sorted(df_rel['genero_show'].dropna().unique().tolist())
        f_gen_rel = cr1.selectbox("Género Posta", opts_gen_rel)
        
        df_r1 = df_rel.copy()
        if f_gen_rel != "Todos": df_r1 = df_r1[df_r1['genero_show'] == f_gen_rel]
        
        opts_est_rel = ["Todos"] + sorted(df_r1['estilo_show'].dropna().unique().tolist())
        f_est_rel = cr2.selectbox("Estilo Posta", opts_est_rel)
        
        if f_est_rel != "Todos": df_r1 = df_r1[df_r1['estilo_show'] == f_est_rel]
        
        opts_dist_rel = ["Todas"] + sorted(df_r1['dist_show'].dropna().unique().tolist())
        f_dist_rel = cr3.selectbox("Distancia Posta", opts_dist_rel)
        
        if f_dist_rel != "Todas": df_r1 = df_r1[df_r1['dist_show'] == f_dist_rel]
        
        st.divider()
        
        if df_r1.empty:
            st.warning("No hay formaciones registradas para estos filtros.")
        else:
            # Ordenamos por los mejores tiempos
            df_r_show = df_r1.sort_values('segundos').reset_index(drop=True)
            df_r_show.index += 1
            
            st.markdown(f"#### Ránking Formaciones: {f_est_rel if f_est_rel != 'Todos' else 'Todas'} - {f_dist_rel if f_dist_rel != 'Todas' else 'Todas'}")
            
            for pos, eq in df_r_show.iterrows():
                clase_card = "my-card" if eq['es_mio'] else ""
                icono_yo = "⭐ " if eq['es_mio'] else ""
                
                try: f_dt = pd.to_datetime(eq['fecha']).strftime('%d/%m/%Y')
                except: f_dt = eq.get('fecha', '-')
                
                nombres_html = f"""
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 13px; color: #ccc; margin-top: 6px;'>
                    <div>1. {eq['nom_1']}</div>
                    <div>3. {eq['nom_3']}</div>
                    <div>2. {eq['nom_2']}</div>
                    <div>4. {eq['nom_4']}</div>
                </div>
                """
                
                st.markdown(f"""
                <div class="test-card {clase_card}" style="position: relative;">
                    <div style="position: absolute; top: 15px; right: 15px; font-size: 32px; font-weight: bold; color: rgba(255,255,255,0.05);">#{pos}</div>
                    <div class="test-header" style="border-bottom: none; margin-bottom: 0; padding-bottom: 0;">
                        <div style="flex-grow: 1;">
                            <div class="test-style">{icono_yo} {eq['estilo_show']} <span style="color:#aaa; font-size:14px; font-weight:normal;">| {eq['dist_show']} ({eq['genero_show']})</span></div>
                            <div class="test-date" style="margin-left: 0; margin-top: 4px; font-size: 13px;">📅 {f_dt}</div>
                            {nombres_html}
                        </div>
                        <div style="text-align: right; z-index: 1;">
                            <div style="font-size: 11px; color: #888; margin-bottom: 2px;">TIEMPO OFICIAL</div>
                            <div class="final-time" style="background: transparent; padding: 0;">{eq.get('tiempo_final', 'S/T')}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # --- PARCIALES SI EXISTEN ---
                ps = [eq.get(f'parcial_{i}') for i in range(1, 5)]
                p_validos = [p for p in ps if pd.notna(p) and str(p).strip() and str(p).lower() not in ['nan', 'none', '00:00.00']]
                
                if p_validos:
                    with st.expander("Ver Parciales"):
                        grid = "".join([f"<div class='split-item'><span class='split-label'>Relevo {i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(p_validos)])
                        st.markdown(f"<div class='splits-container' style='margin-top: 0;'><div class='splits-grid'>{grid}</div></div>", unsafe_allow_html=True)
