import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Base de Datos", layout="centered")

# --- SEGURIDAD ---
# --- SEGURIDAD: VERIFICACIÓN DE ROL ---
if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Acceso denegado. Por favor, inicia sesión desde el Inicio.")
    st.stop()

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

st.title("📊 Base de Datos del Club")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* TARJETA PADRÓN */
    .padron-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 3px 6px rgba(0,0,0,0.3);
@@ -161,49 +161,48 @@
df_view['Total'] = df_view['Oro'] + df_view['Plata'] + df_view['Bronce']


# ==============================================================================
#  FUNCIONES REUTILIZABLES
# ==============================================================================

def render_tab_ficha(target_id, unique_key_suffix=""):
    if not target_id: return

    info = df_nad[df_nad['codnadador'] == target_id].iloc[0]

    try: 
        nac = pd.to_datetime(info['fechanac'])
        edad = datetime.now().year - nac.year
        nac_str = nac.strftime('%d/%m/%Y')
    except: edad = 0; nac_str = "-"
    cat = asignar_cat(edad)

    row_m = df_view[df_view['codnadador'] == target_id]
    if not row_m.empty:
        o, pl, br = int(row_m.iloc[0]['Oro']), int(row_m.iloc[0]['Plata']), int(row_m.iloc[0]['Bronce'])
    else: o, pl, br = 0, 0, 0

    # CABECERA
    st.markdown(f"""
    <div class="ficha-header">
        <div class="ficha-name">{info['nombre']} {info['apellido']}</div>
        <div class="ficha-grid">
            <div>📅 Nacimiento: <b>{nac_str}</b></div>
            <div>🎂 Edad (al 31/12): <b>{edad} años</b></div>
            <div>🏷️ Categoría: <b>{cat}</b></div>
            <div>⚧️ Género: <b>{info['codgenero']}</b></div>
        </div>
        <div class="ficha-medals">
            🥇 {o} &nbsp; | &nbsp; 🥈 {pl} &nbsp; | &nbsp; 🥉 {br}
        </div>
    </div>
    """, unsafe_allow_html=True)

    mis_t = df_full[df_full['codnadador'] == target_id].copy()

    # MEJORES MARCAS
    if not mis_t.empty:
        st.subheader("✨ Mejores Marcas (PB)")
        mis_t['segundos'] = mis_t['tiempo'].apply(tiempo_a_segundos)
        pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()].sort_values(['Estilo', 'segundos'])

        for estilo in pbs['Estilo'].unique():
@@ -268,154 +267,153 @@
            </div>
        </div>""", unsafe_allow_html=True)

    # MIS RELEVOS
    st.subheader("🏊‍♂️ Mis Relevos")
    mr_base = data['relevos'].copy()
    cond_rel = (mr_base['nadador_1'] == target_id) | (mr_base['nadador_2'] == target_id) | (mr_base['nadador_3'] == target_id) | (mr_base['nadador_4'] == target_id)
    mis_relevos = mr_base[cond_rel].copy()

    if not mis_relevos.empty:
        mis_relevos = mis_relevos.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mis_relevos = mis_relevos.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        mis_relevos = mis_relevos.sort_values('fecha', ascending=False)

        for _, r in mis_relevos.iterrows():
            html_grid = ""
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nom += f" ({t})"

                # Resaltar si soy yo
                border_style = "border: 1px solid #E91E63;" if nid == target_id else ""
                html_grid += f"<div class='swimmer-item' style='{border_style}'>{k}. {nom}</div>"

            pos_icon = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else ""))
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                <div class="relay-header">
                    <div class="relay-title">{r['Distancia']} {r['Estilo']}</div>
                    <div class="relay-time">{r['tiempo_final']}</div>
                </div>
                <div class="relay-meta">
                    <span>📅 {r['fecha']} • {r['club']}</span>
                    <span style="font-weight:bold; color:#FFD700;">{pos_icon} Pos: {r['posicion']}</span>
                </div>
                <div class="swimmer-grid">{html_grid}</div>
            </div>""", unsafe_allow_html=True)
    else: st.info("Sin relevos.")

def render_tab_padron():
    st.markdown("### 🏆 Padrón y Medallero")
    filtro = st.text_input("Buscar Nadador:", placeholder="Nombre...")
    df_show = df_view.sort_values('Total', ascending=False)
    if filtro: df_show = df_show[df_show['Nombre Completo'].str.contains(filtro.upper())]

    for _, row in df_show.head(25).iterrows():
        try: edad = datetime.now().year - pd.to_datetime(row['fechanac']).year
        except: edad = 0
        cat = asignar_cat(edad)
        o, p, b, t = int(row.get('Oro',0)), int(row.get('Plata',0)), int(row.get('Bronce',0)), int(row.get('Total',0))

        st.markdown(f"""
        <div class="padron-card">
            <div class="p-col-left">
                <div class="p-name">{row['Nombre Completo']}</div>
                <div class="p-meta">{edad} años (al 31/12) • {row['codgenero']}</div>
            </div>
            <div class="p-col-center">
                <div class="p-medals"><span>🥇{o}</span> <span>🥈{p}</span> <span>🥉{b}</span></div>
            </div>
            <div class="p-col-right"><div class="p-total">★ {t}</div><div class="p-cat">{cat}</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Botón VER
        if st.button(f"Ver Ficha {row['nombre']} ➝", key=f"btn_p_{row['codnadador']}", use_container_width=True):
            st.session_state.nadador_seleccionado = row['Nombre Completo']
            st.rerun()

def render_tab_relevos_general():
    st.markdown("### Historial de Postas")
    mr_all = data['relevos'].copy()
    if not mr_all.empty:
        mr_all = mr_all.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mr_all = mr_all.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})

        c1, c2 = st.columns(2)
        fg_est = c1.selectbox("Estilo", ["Todos"] + sorted(mr_all['Estilo'].unique().tolist()), key="fg_est")
        fg_gen = c2.selectbox("Género", ["Todos", "M", "F", "X"], key="fg_gen")

        if fg_est != "Todos": mr_all = mr_all[mr_all['Estilo'] == fg_est]
        if fg_gen != "Todos": mr_all = mr_all[mr_all['codgenero'] == fg_gen]

        for _, r in mr_all.sort_values('fecha', ascending=False).head(20).iterrows():
            html_grid = ""
            for k in range(1, 5):
                nid = r[f'nadador_{k}']
                nom = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nom += f" <b>({t})</b>"
                html_grid += f"<div class='swimmer-item'>{k}. {nom}</div>"

            medal = "🥇" if r['posicion'] == 1 else ("🥈" if r['posicion'] == 2 else ("🥉" if r['posicion'] == 3 else ""))
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #9C27B0;">
                <div class="relay-header">
                    <div class="relay-title">{r['Distancia']} {r['Estilo']} ({r['codgenero']})</div>
                    <div class="relay-time">{r['tiempo_final']}</div>
                </div>
                <div class="relay-meta">
                    <span>📅 {r['fecha']} • {r['club']}</span>
                    <span style="font-weight:bold; color:#FFD700;">{medal} Pos: {r['posicion']}</span>
                </div>
                <div class="swimmer-grid">{html_grid}</div>
            </div>""", unsafe_allow_html=True)


# ==============================================================================
#  LÓGICA PRINCIPAL
# ==============================================================================

if rol == "N":
    tab_yo, tab_otro = st.tabs(["👤 Mi Ficha", "🔍 Consultar Compañero"])
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
    tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])

    with tab1: render_tab_padron()

    with tab2:
        lista_nombres = sorted(df_nad['Nombre Completo'].unique().tolist())

        # --- LÓGICA INTELIGENTE DE PRESELECCIÓN ---
        idx_defecto = 0
        pre_seleccion = st.session_state.get("nadador_seleccionado")

        # Si NO hay selección previa, por defecto pongo al usuario actual (si está en la lista)
        if not pre_seleccion and mi_nombre in lista_nombres:
            pre_seleccion = mi_nombre

        # Si HAY selección (o la acabo de poner), busco su índice
        if pre_seleccion in lista_nombres:
            idx_defecto = lista_nombres.index(pre_seleccion)

        f_nad = st.selectbox("Seleccionar Atleta:", lista_nombres, index=idx_defecto)

        if f_nad:
            # Actualizo el estado para que se mantenga si recarga
            st.session_state.nadador_seleccionado = f_nad
            id_actual = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]['codnadador']
            render_tab_ficha(id_actual, unique_key_suffix="_master")

    with tab3: render_tab_relevos_general()
