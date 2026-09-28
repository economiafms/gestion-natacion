import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Ranking NOB", layout="centered", initial_sidebar_state="collapsed")

# --- 2. SEGURIDAD (SOLO PERFIL M o P) ---
if "role" not in st.session_state or st.session_state.role not in ["M", "P"]:
    st.warning("⚠️ Acceso restringido.")
    st.switch_page("pages/1_inicio.py")

st.title("🏆 Ranking Histórico")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. CARGA DE DATOS ---
@st.cache_data(ttl="1h")
def cargar_datos_ranking():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "relevos": conn.read(worksheet="Relevos"),
            "cat_relevos": conn.read(worksheet="Categorias_Relevos")
        }
    except: return None

data = cargar_datos_ranking()
if not data: st.stop()

# --- 4. PROCESAMIENTO GENERAL ---
def tiempo_a_seg(t_str):
    try:
        if isinstance(t_str, str):
            partes = t_str.replace('.', ':').split(':')
            if len(partes) == 3: return float(partes[0])*60 + float(partes[1]) + float(partes[2])/100
            elif len(partes) == 2: return float(partes[0])*60 + float(partes[1])
            else: return float(t_str)
        return float(t_str)
    except: return 999999

# --- ESTRUCTURAS DE TABS ---
tab_indiv, tab_relevos = st.tabs(["🏊‍♂️ INDIVIDUALES", "🤝 RELEVOS"])

# ==============================================================================
# TAB 1: INDIVIDUALES (CÓDIGO ORIGINAL INTACTO)
# ==============================================================================
with tab_indiv:
    # --- UNIFICACIÓN LIMPIA (IGNORANDO 'CLUB' DE TIEMPOS) ---
    df = data['tiempos'].copy()

    # 1. Eliminar 'club' de Tiempos si existe (para evitar conflictos y 'nan')
    if 'club' in df.columns:
        df = df.drop(columns=['club'])

    # 2. Merges (Cruces de tablas)
    df = df.merge(data['nadadores'], on='codnadador', how='left')
    df = df.merge(data['estilos'], on='codestilo', how='left')
    df = df.merge(data['distancias'], on='coddistancia', how='left')
    # Al hacer merge con piletas, nos trae 'club' (SEDE REAL) y 'medida'
    df = df.merge(data['piletas'], on='codpileta', how='left')

    # 3. Renombrado y Limpieza
    cols_map = {
        'nombre': 'Nombre', 
        'apellido': 'Apellido',
        'descripcion_x': 'Estilo', 
        'descripcion_y': 'Distancia',
        'descripcion': 'Estilo',
        'club': 'sede' # Renombramos explícitamente la columna que vino de Piletas
    }
    df = df.rename(columns=cols_map)

    # 4. Cálculo de campos finales
    df['Nadador'] = df['Apellido'].astype(str).str.upper() + ", " + df['Nombre'].astype(str)
    df['Segundos'] = df['tiempo'].apply(tiempo_a_seg)
    df['Año'] = pd.to_datetime(df['fecha']).dt.year

    # Asegurar valores por defecto para que no falle la tarjeta
    if 'sede' not in df.columns: df['sede'] = 'Sede desconocida'
    if 'medida' not in df.columns: df['medida'] = '-'

    # --- 5. FILTROS ---
    st.markdown("### 🔍 Filtrar Ranking")

    c1, c2, c3 = st.columns(3)

    lista_estilos = sorted(df['Estilo'].unique()) if 'Estilo' in df.columns else []
    lista_distancias = sorted(df['Distancia'].unique()) if 'Distancia' in df.columns else []
    lista_generos = ["Todos"] + sorted(df['codgenero'].unique().tolist()) if 'codgenero' in df.columns else ["Todos"]

    idx_estilo = 0
    idx_distancia = 0

    for i, e in enumerate(lista_estilos):
        if "Libre" in str(e) or "Crol" in str(e): idx_estilo = i; break
    for i, d in enumerate(lista_distancias):
        if "50" in str(d): idx_distancia = i; break

    with c1: f_estilo = st.selectbox("Estilo", lista_estilos, index=idx_estilo)
    with c2: f_distancia = st.selectbox("Distancia", lista_distancias, index=idx_distancia)
    with c3: f_genero = st.selectbox("Género", lista_generos)

    # Aplicar filtros básicos
    if 'Estilo' in df.columns and 'Distancia' in df.columns:
        df_filtrado = df[
            (df['Estilo'] == f_estilo) & 
            (df['Distancia'] == f_distancia)
        ]
    else:
        df_filtrado = df.copy()

    if f_genero != "Todos":
        df_filtrado = df_filtrado[df_filtrado['codgenero'] == f_genero]

    # --- LÓGICA DE RANKING (MEJORES MARCAS ÚNICAS) ---
    # 1. Ordenamos por tiempo (el más rápido primero)
    df_filtrado = df_filtrado.sort_values('Segundos', ascending=True)

    # 2. Eliminamos duplicados por nadador, quedándonos solo con el primero (su mejor tiempo)
    df_filtrado = df_filtrado.drop_duplicates(subset=['codnadador'], keep='first')

    # 3. Tomamos los primeros 50
    df_ranking = df_filtrado.head(50).reset_index(drop=True)

    # --- 6. VISUALIZACIÓN ---
    st.divider()

    if df_ranking.empty:
        st.info("No hay registros para esta selección.")
    else:
        for i, row in df_ranking.iterrows():
            pos = i + 1
            
            if pos == 1:
                bg_color, text_color, icono = "linear-gradient(90deg, #FFD700 0%, #FDB931 100%)", "black", "🥇"
            elif pos == 2:
                bg_color, text_color, icono = "linear-gradient(90deg, #E0E0E0 0%, #BDBDBD 100%)", "black", "🥈"
            elif pos == 3:
                bg_color, text_color, icono = "linear-gradient(90deg, #D68D5E 0%, #CD7F32 100%)", "black", "🥉"
            else:
                bg_color, text_color, icono = "#262730", "white", f"#{pos}"

            medida_val = str(row.get('medida', '-'))
            sede_val = str(row.get('sede', 'Sede desconocida'))
            
            pileta_badge = "25m" if "25" in medida_val else ("50m" if "50" in medida_val else medida_val)

            st.markdown(f"""
            <style>
                .rank-card {{
                    border-radius: 10px;
                    padding: 10px 15px;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }}
                .rank-pos {{ font-size: 24px; font-weight: bold; width: 50px; text-align: center; margin-right: 10px; }}
                .rank-info {{ flex-grow: 1; }}
                .rank-name {{ font-weight: bold; font-size: 16px; margin-bottom: 2px; }}
                .rank-meta {{ font-size: 12px; opacity: 0.8; }}
                .rank-time {{ font-family: monospace; font-weight: bold; font-size: 20px; text-align: right; }}
                .tag-pool {{ 
                    font-size: 10px; padding: 2px 6px; border-radius: 4px; 
                    margin-left: 8px; font-weight: normal; 
                    vertical-align: middle;
                }}
            </style>
            
            <div class="rank-card" style="background: {bg_color}; color: {text_color};">
                <div class="rank-pos">{icono}</div>
                <div class="rank-info">
                    <div class="rank-name">{row['Nadador']}</div>
                    <div class="rank-meta">
                        {sede_val} • {row['Año']} 
                        <span class="tag-pool" style="border: 1px solid {text_color};">{pileta_badge}</span>
                    </div>
                </div>
                <div class="rank-time">{row['tiempo']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==============================================================================
# TAB 2: RELEVOS
# ==============================================================================
with tab_relevos:
    df_rel = data['relevos'].copy() if 'relevos' in data else pd.DataFrame()
    df_cat_rel = data['cat_relevos'].copy() if 'cat_relevos' in data else pd.DataFrame()
    
    if df_rel.empty:
        st.info("No hay registros de relevos históricos.")
    else:
        if not df_cat_rel.empty:
            df_cat_rel.columns = df_cat_rel.columns.str.strip().str.lower()

        # 1. Preparar Diccionarios para Mapeo Rápido
        df_n = data['nadadores']
        df_p = data['piletas']
        df_e = data['estilos']
        df_d = data['distancias']
        
        # Diccionarios de búsqueda
        dict_nad = {}
        dict_anio_nac = {}
        for _, r in df_n.iterrows():
            try: 
                c_id = float(r['codnadador'])
                dict_nad[c_id] = f"{str(r['apellido']).upper()}, {r['nombre']}"
                
                # Extraer año de nacimiento para la categoría
                fn = pd.to_datetime(r['fechanac'], errors='coerce')
                if pd.notna(fn):
                    dict_anio_nac[c_id] = fn.year
            except: pass
            
        dict_est = dict(zip(df_e['codestilo'].astype(str), df_e['descripcion'])) if not df_e.empty else {}
        dict_dist = dict(zip(df_d['coddistancia'].astype(str), df_d['descripcion'])) if not df_d.empty else {}
        dict_pil = dict(zip(df_p['codpileta'].astype(str), df_p['club'])) if not df_p.empty else {}
        dict_med = dict(zip(df_p['codpileta'].astype(str), df_p['medida'])) if not df_p.empty else {}

        # 2. Enriquecer Tabla de Relevos
        df_rel['Estilo'] = df_rel['codestilo'].astype(str).map(dict_est).fillna(df_rel['codestilo'])
        df_rel['Distancia'] = df_rel['coddistancia'].astype(str).map(dict_dist).fillna(df_rel['coddistancia'])
        df_rel['Sede'] = df_rel['codpileta'].astype(str).map(dict_pil).fillna('Sede desconocida')
        df_rel['Medida'] = df_rel['codpileta'].astype(str).map(dict_med).fillna('-')
        df_rel['Año'] = pd.to_datetime(df_rel['fecha']).dt.year
        df_rel['Segundos'] = df_rel['tiempo_final'].apply(tiempo_a_seg)
        
        # Mapear nombres de los 4 nadadores
        for i in range(1, 5):
            df_rel[f'Nom_{i}'] = pd.to_numeric(df_rel[f'nadador_{i}'], errors='coerce').map(dict_nad).fillna("S/D")

        # --- CÁLCULO DE CATEGORÍA DEL RELEVO ---
        def obtener_categoria_relevo(row):
            try:
                anio_ev = row.get('Año')
                if pd.isna(anio_ev): return ""
                
                suma = 0
                for i in range(1, 5):
                    n_id = float(row.get(f'nadador_{i}', 0))
                    if n_id in dict_anio_nac:
                        suma += (anio_ev - dict_anio_nac[n_id])
                    else:
                        return "" # Faltan datos de nacimiento para calcular
                
                reglamento = str(row.get('tipo_reglamento', '')).strip()
                if not df_cat_rel.empty and reglamento and reglamento != 'nan':
                    match = df_cat_rel[
                        (df_cat_rel['tipo_reglamento'].astype(str).str.strip() == reglamento) &
                        (pd.to_numeric(df_cat_rel['suma_min'], errors='coerce') <= suma) &
                        (pd.to_numeric(df_cat_rel['suma_max'], errors='coerce') >= suma)
                    ]
                    if not match.empty:
                        return f" | {match.iloc[0]['descripcion']}"
                return f" | Suma {int(suma)}"
            except:
                return ""

        df_rel['Categoria_Posta'] = df_rel.apply(obtener_categoria_relevo, axis=1)

        # --- 3. FILTROS ---
        st.markdown("### 🔍 Filtrar Relevos")
        cr1, cr2, cr3, cr4 = st.columns(4)
        
        lista_reg_rel = ["Todos"] + sorted(df_rel['tipo_reglamento'].dropna().unique().tolist()) if 'tipo_reglamento' in df_rel else ["Todos"]
        lista_gen_rel = ["Todos"] + sorted(df_rel['codgenero'].dropna().unique().tolist()) if 'codgenero' in df_rel else ["Todos"]
        lista_est_rel = sorted(df_rel['Estilo'].dropna().unique().tolist())
        lista_dist_rel = sorted(df_rel['Distancia'].dropna().unique().tolist())

        with cr1: f_reg_rel = st.selectbox("Reglamento", lista_reg_rel)
        with cr2: f_gen_rel = st.selectbox("Género", lista_gen_rel)
        with cr3: f_est_rel = st.selectbox("Estilo", ["Todos"] + lista_est_rel)
        with cr4: f_dist_rel = st.selectbox("Distancia", ["Todas"] + lista_dist_rel)

        # Aplicar Filtros
        df_r_filt = df_rel.copy()
        if f_reg_rel != "Todos": df_r_filt = df_r_filt[df_r_filt['tipo_reglamento'] == f_reg_rel]
        if f_gen_rel != "Todos": df_r_filt = df_r_filt[df_r_filt['codgenero'] == f_gen_rel]
        if f_est_rel != "Todos": df_r_filt = df_r_filt[df_r_filt['Estilo'] == f_est_rel]
        if f_dist_rel != "Todas": df_r_filt = df_r_filt[df_r_filt['Distancia'] == f_dist_rel]

        # 4. Ordenamiento
        df_r_filt = df_r_filt.sort_values('Segundos', ascending=True).reset_index(drop=True)

        st.divider()
        
        if df_r_filt.empty:
            st.info("No hay formaciones para estos filtros.")
        else:
            for i, row in df_r_filt.iterrows():
                pos = i + 1
                
                if pos == 1:
                    bg_color, text_color, icono = "linear-gradient(90deg, #FFD700 0%, #FDB931 100%)", "black", "🥇"
                elif pos == 2:
                    bg_color, text_color, icono = "linear-gradient(90deg, #E0E0E0 0%, #BDBDBD 100%)", "black", "🥈"
                elif pos == 3:
                    bg_color, text_color, icono = "linear-gradient(90deg, #D68D5E 0%, #CD7F32 100%)", "black", "🥉"
                else:
                    bg_color, text_color, icono = "#262730", "white", f"#{pos}"

                medida_val = str(row.get('Medida', '-'))
                pileta_badge = "25m" if "25" in medida_val else ("50m" if "50" in medida_val else medida_val)
                
                # Función para obtener nombre + tiempo
                def get_nom_t(idx):
                    nom = row.get(f'Nom_{idx}', 'S/D')
                    t = row.get(f'tiempo_{idx}')
                    if pd.notna(t) and str(t).strip() and str(t) != '00:00.00':
                        return f"<b>{idx}.</b> {nom} <b>({t})</b>"
                    return f"<b>{idx}.</b> {nom}"

                nad1 = get_nom_t(1)
                nad2 = get_nom_t(2)
                nad3 = get_nom_t(3)
                nad4 = get_nom_t(4)

                # HTML plano sin sangrías para evitar el bug de Markdown
                grid_nadadores = f"<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px; margin-top: 5px; color: {text_color}; opacity: 0.95;'><div>{nad1}</div><div>{nad3}</div><div>{nad2}</div><div>{nad4}</div></div>"

                tarjeta_html = f"""<div class="rank-card" style="background: {bg_color}; color: {text_color};">
<div class="rank-pos">{icono}</div>
<div class="rank-info">
<div class="rank-name">{row['Estilo']} {row['Distancia']} <span style="font-weight: normal; opacity: 0.85; font-size: 0.9em;">{row['Categoria_Posta']}</span></div>
<div class="rank-meta">{row['Sede']} • {row['Año']} <span class="tag-pool" style="border: 1px solid {text_color};">{pileta_badge}</span></div>
{grid_nadadores}
</div>
<div class="rank-time">{row['tiempo_final']}</div>
</div>"""
                
                st.markdown(tarjeta_html, unsafe_allow_html=True)
