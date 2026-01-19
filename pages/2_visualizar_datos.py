import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Datos", layout="centered")

if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Inicia sesión primero.")
    st.stop()

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

st.title("📊 Base de Datos del Club")

# --- CSS (Ajuste para diseño flex en cards) ---
st.markdown("""
<style>
    .ficha-header { background: linear-gradient(135deg, #8B0000 0%, #3E0000 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; border: 1px solid #550000; }
    .pb-row { background-color: #2b2c35; padding: 10px 15px; margin-bottom: 5px; border-radius: 6px; display: flex; justify-content: space-between; border-left: 4px solid #B71C1C; }
    .mobile-card { background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 12px; }
    .padron-card { background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between; }
    .swimmer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; color: #eee; }
    .swimmer-item { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="15m")
def get_data():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "categorias": conn.read(worksheet="Categorias"),
        }
    except: return None

data = get_data()
if not data: st.stop()

# --- PROCESAMIENTO GLOBAL ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

df_full = data['tiempos'].copy()
df_full = df_full.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
df_full = df_full.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})

# CORRECCIÓN DECIMALES
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
df_view = df_nad.merge(medallero, left_on='codnadador', right_index=True, how='left').fillna(0)
df_view['Total'] = df_view[1]+df_view[2]+df_view[3]

def tiempo_a_seg(t):
    try:
        p = str(t).replace('.', ':').split(':')
        return float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
    except: return None

def asignar_cat(edad):
    for _, r in data['categorias'].iterrows():
        if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
    return "-"

# --- RENDER FICHA ---
def render_ficha(id_n):
    if not id_n: return
    info = df_nad[df_nad['codnadador'] == id_n].iloc[0]
    try: 
        nac = pd.to_datetime(info['fechanac'])
        edad = datetime.now().year - nac.year
        nac_str = nac.strftime('%d/%m/%Y')
    except: edad = 0; nac_str = "-"
    cat = asignar_cat(edad)
    
    # Medallas
    row_m = df_view[df_view['codnadador'] == id_n]
    if not row_m.empty:
        o, p, b = int(row_m.iloc[0][1]), int(row_m.iloc[0][2]), int(row_m.iloc[0][3])
    else: o, p, b = 0, 0, 0

    st.markdown(f"""
    <div class="ficha-header">
        <div style="font-size:24px; font-weight:bold; margin-bottom:10px;">{info['nombre']} {info['apellido']}</div>
        <div style="font-size:14px;">📅 {nac_str} | 🎂 {edad} años | 🏷️ {cat} | ⚧️ {info['codgenero']}</div>
        <div style="margin-top:10px; font-size:18px;">🥇 {o} &nbsp; 🥈 {p} &nbsp; 🥉 {b}</div>
    </div>
    """, unsafe_allow_html=True)
    
    mis_t = df_full[df_full['codnadador'] == id_n].copy()
    
    # PB
    if not mis_t.empty:
        st.subheader("✨ Mejores Marcas")
        mis_t['seg'] = mis_t['tiempo'].apply(tiempo_a_seg)
        pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['seg'].idxmin()].sort_values(['Estilo', 'seg'])
        for est in pbs['Estilo'].unique():
            st.markdown(f"<div style='color:#e53935; font-weight:bold; margin-top:10px; border-bottom:1px solid #444;'>{est}</div>", unsafe_allow_html=True)
            for _, r in pbs[pbs['Estilo']==est].iterrows():
                st.markdown(f"<div class='pb-row'><span style='color:#eee;'>{r['Distancia']}</span><span style='color:#fff; font-weight:bold; font-family:monospace;'>{r['tiempo']}</span></div>", unsafe_allow_html=True)
        st.divider()
        
        # Grafico
        st.subheader("📈 Evolución")
        conteo = mis_t.groupby(['Estilo', 'Distancia']).size().reset_index(name='c')
        val = conteo[conteo['c']>=2]
        if not val.empty:
            c1, c2 = st.columns(2)
            ge = c1.selectbox("Estilo", val['Estilo'].unique(), key=f"e_{id_n}")
            gd = c2.selectbox("Distancia", val[val['Estilo']==ge]['Distancia'].unique(), key=f"d_{id_n}")
            dg = mis_t[(mis_t['Estilo']==ge) & (mis_t['Distancia']==gd)].sort_values('fecha')
            fig = px.line(dg, x='fecha', y='seg', markers=True, template="plotly_dark")
            fig.update_traces(line_color='#E53935')
            st.plotly_chart(fig, use_container_width=True)
        
        # --- HISTORIAL REDISEÑADO CON POSICIÓN ABAJO ---
        st.subheader("📜 Historial")
        for _, r in mis_t.sort_values('fecha', ascending=False).head(10).iterrows():
            # Lógica de formato posición
            try:
                pos_val = int(r['posicion'])
                if pos_val == 1: medal_str = "🥇 1º"
                elif pos_val == 2: medal_str = "🥈 2º"
                elif pos_val == 3: medal_str = "🥉 3º"
                elif pos_val > 3: medal_str = f"Pos: {pos_val}"
                else: medal_str = "-"
            except: medal_str = "-"

            st.markdown(f"""
            <div class="mobile-card" style="padding:10px; display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;"> <div style="font-weight:bold; color:white; font-size: 16px;">{r['Distancia']} {r['Estilo']}</div>
                    <div style="font-size:12px; color:#aaa; margin-top:4px;">📅 {r['fecha']} • {r['club']}</div>
                </div>
                <div style="text-align: right;"> <div style="font-family:monospace; font-weight:bold; color:#4CAF50; font-size: 18px;">{r['tiempo']}</div>
                    <div style="font-size: 13px; color: #ddd; margin-top: 2px;">{medal_str}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    # Relevos Personales
    st.subheader("🏊‍♂️ Mis Relevos")
    mr = data['relevos'].copy()
    cond = (mr['nadador_1']==id_n)|(mr['nadador_2']==id_n)|(mr['nadador_3']==id_n)|(mr['nadador_4']==id_n)
    mis_r = mr[cond].copy()
    if not mis_r.empty:
        mis_r = mis_r.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        for _, r in mis_r.sort_values('fecha', ascending=False).iterrows():
            grid = ""
            for k in range(1,5):
                nid = r[f'nadador_{k}']
                nm = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nm += f" ({t})"
                border = "border:1px solid #E91E63;" if nid == id_n else ""
                grid += f"<div class='swimmer-item' style='{border}'>{k}. {nm}</div>"
            
            # Formato posición en relevos también
            try:
                p_rel = int(r['posicion'])
                if p_rel == 1: pos_icon = "🥇 1º"
                elif p_rel == 2: pos_icon = "🥈 2º"
                elif p_rel == 3: pos_icon = "🥉 3º"
                else: pos_icon = f"Pos: {p_rel}"
            except: pos_icon = ""

            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                <div class="relay-header">
                    <div>{r['descripcion_y']} {r['descripcion_x']}</div>
                    <div style="text-align:right;">
                        <div style="color:#4CAF50; font-family:monospace; font-weight:bold;">{r['tiempo_final']}</div>
                        <div style="font-size:12px; color:#ddd;">{pos_icon}</div>
                    </div>
                </div>
                <div class="relay-meta">📅 {r['fecha']} • {r['club']}</div>
                <div class="swimmer-grid">{grid}</div>
            </div>""", unsafe_allow_html=True)
    else: st.info("Sin relevos.")

# ==========================================
#  LÓGICA PRINCIPAL
# ==========================================

if rol == "N":
    # NADADOR: Solo ve su ficha y busca DNI
    t_mi, t_otro = st.tabs(["👤 Mi Ficha", "🔍 Consultar Compañero"])
    with t_mi: render_ficha(mi_id)
    with t_otro:
        dni = st.text_input("DNI Compañero:")
        if dni:
            res = df_nad[df_nad['dni'].astype(str).str.contains(dni.strip())]
            if not res.empty: render_ficha(res.iloc[0]['codnadador'])
            else: st.error("No encontrado.")

else:
    # MASTER: Ve todo
    tab1, tab2, tab3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])
    
    with tab1:
        st.markdown("### 🏆 Padrón")
        filtro = st.text_input("Buscar Nadador:")
        view = df_view.sort_values('Total', ascending=False)
        if filtro: view = view[view['Nombre Completo'].str.contains(filtro.upper())]
        for _, r in view.head(20).iterrows():
            st.markdown(f"""
            <div class="padron-card">
                <div><b>{r['Nombre Completo']}</b><br><small>{r['codgenero']}</small></div>
                <div style="font-size:20px; color:#FFD700;">★ {int(r['Total'])}</div>
            </div>""", unsafe_allow_html=True)
            
            # Botón "Ver" desde Padrón
            if st.button("Ver", key=f"btn_p_{r['codnadador']}"):
                st.session_state.ver_nadador_especifico = r['Nombre Completo']
                st.rerun()

    with tab2:
        names = sorted(df_nad['Nombre Completo'].unique().tolist())
        
        # --- LÓGICA DE PRE-SELECCIÓN (SEGURA) ---
        idx_defecto = 0
        solicitado = st.session_state.get("ver_nadador_especifico")
        
        # 1. Si vengo con un nombre específico, lo uso
        if solicitado and solicitado in names:
            idx_defecto = names.index(solicitado)
        # 2. Si no, pero soy yo mismo y estoy en la lista, me pongo a mí
        elif mi_nombre in names:
            idx_defecto = names.index(mi_nombre)
            
        sel = st.selectbox("Seleccionar Atleta:", names, index=idx_defecto)
        
        if sel:
            idn = df_nad[df_nad['Nombre Completo']==sel].iloc[0]['codnadador']
            render_ficha(idn)

    with tab3:
        st.markdown("### Historial General")
        mr = data['relevos'].copy()
        mr = mr.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        for _, r in mr.sort_values('fecha', ascending=False).head(20).iterrows():
            grid = ""
            for k in range(1,5):
                nm = dict_id_nombre.get(r[f'nadador_{k}'], "??").split(',')[0]
                grid += f"<div class='swimmer-item'>{k}. {nm}</div>"
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #9C27B0;">
                <div class="relay-header"><div>{r['descripcion_y']} {r['descripcion_x']}</div><div style="color:#4CAF50;">{r['tiempo_final']}</div></div>
                <div class="swimmer-grid">{grid}</div>
            </div>""", unsafe_allow_html=True)
