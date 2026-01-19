import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Base de Datos", layout="centered")

if "role" not in st.session_state or not st.session_state.role:
    st.warning("⚠️ Inicia sesión primero.")
    st.stop()

rol = st.session_state.role
mi_id = st.session_state.user_id

st.title("📊 Base de Datos del Club")

# --- CSS (Mismo de siempre) ---
st.markdown("""
<style>
    .ficha-header { background: linear-gradient(135deg, #8B0000 0%, #3E0000 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; border: 1px solid #550000; }
    .pb-row { background-color: #2b2c35; padding: 10px 15px; margin-bottom: 5px; border-radius: 6px; display: flex; justify-content: space-between; border-left: 4px solid #B71C1C; }
    .mobile-card { background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 12px; }
    .padron-card { background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between; }
    .swimmer-item { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }
    .swimmer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; color: #eee; }
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

# --- PROCESAMIENTO ---
df_nad = data['nadadores'].copy()
df_nad['Nombre Completo'] = df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)
dict_id_nombre = df_nad.set_index('codnadador')['Nombre Completo'].to_dict()

df_full = data['tiempos'].copy()
df_full = df_full.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
df_full = df_full.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})

def tiempo_a_seg(t):
    try:
        p = str(t).replace('.', ':').split(':')
        return float(p[0])*60 + float(p[1]) + (float(p[2])/100 if len(p)>2 else 0)
    except: return None

def asignar_cat(edad):
    for _, r in data['categorias'].iterrows():
        if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
    return "-"

# --- RENDERIZADORES ---
def render_ficha(id_n):
    if not id_n: return
    info = df_nad[df_nad['codnadador'] == id_n].iloc[0]
    nac = pd.to_datetime(info['fechanac'])
    edad = datetime.now().year - nac.year
    cat = asignar_cat(edad)
    
    st.markdown(f"""
    <div class="ficha-header">
        <div style="font-size:24px; font-weight:bold; margin-bottom:10px;">{info['nombre']} {info['apellido']}</div>
        <div style="font-size:14px;">📅 {nac.strftime('%d/%m/%Y')} | 🎂 {edad} años | 🏷️ {cat} | ⚧️ {info['codgenero']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    mis_t = df_full[df_full['codnadador'] == id_n].copy()
    
    # PBs
    if not mis_t.empty:
        st.subheader("✨ Mejores Marcas")
        mis_t['seg'] = mis_t['tiempo'].apply(tiempo_a_seg)
        pbs = mis_t.loc[mis_t.groupby(['Estilo', 'Distancia'])['seg'].idxmin()].sort_values(['Estilo', 'seg'])
        for est in pbs['Estilo'].unique():
            st.markdown(f"<div style='color:#e53935; font-weight:bold; margin-top:10px; border-bottom:1px solid #444;'>{est}</div>", unsafe_allow_html=True)
            for _, r in pbs[pbs['Estilo']==est].iterrows():
                st.markdown(f"<div class='pb-row'><span style='color:#eee;'>{r['Distancia']}</span><span style='color:#fff; font-weight:bold; font-family:monospace;'>{r['tiempo']}</span></div>", unsafe_allow_html=True)
        
        st.divider()
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

        st.subheader("📜 Historial")
        for _, r in mis_t.sort_values('fecha', ascending=False).head(10).iterrows():
            st.markdown(f"""
            <div class="mobile-card" style="padding:10px;">
                <div style="display:flex; justify-content:space-between;"><b>{r['Distancia']} {r['Estilo']}</b><b style="color:#4CAF50;">{r['tiempo']}</b></div>
                <div style="font-size:12px; color:#aaa;">📅 {r['fecha']} • {r['club']}</div>
            </div>""", unsafe_allow_html=True)

    # MIS RELEVOS (Recuperado)
    st.subheader("🏊‍♂️ Mis Relevos")
    mr = data['relevos'].copy()
    cond = (mr['nadador_1']==id_n)|(mr['nadador_2']==id_n)|(mr['nadador_3']==id_n)|(mr['nadador_4']==id_n)
    mis_r = mr[cond].copy()
    
    if not mis_r.empty:
        mis_r = mis_r.merge(data['estilos'], on='codestilo').merge(data['distancias'], on='coddistancia').merge(data['piletas'], on='codpileta')
        mis_r = mis_r.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
        
        for _, r in mis_r.sort_values('fecha', ascending=False).iterrows():
            grid = ""
            for k in range(1,5):
                nid = r[f'nadador_{k}']
                nm = dict_id_nombre.get(nid, "??").split(',')[0]
                t = str(r[f'tiempo_{k}']).strip()
                if t and t not in ["00.00", "0", "None", "nan"]: nm += f" ({t})"
                style = "border:1px solid #E91E63;" if nid == id_n else ""
                grid += f"<div class='swimmer-item' style='{style}'>{k}. {nm}</div>"
            
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 4px solid #E91E63;">
                <div class="relay-header"><div>{r['Distancia']} {r['Estilo']}</div><div style="font-family:monospace; color:#4CAF50; font-weight:bold;">{r['tiempo_final']}</div></div>
                <div class="relay-meta">📅 {r['fecha']} • {r['club']} • Pos: {r['posicion']}</div>
                <div class="swimmer-grid">{grid}</div>
            </div>""", unsafe_allow_html=True)
    else: st.info("Sin relevos.")

# ==========================================
# LÓGICA PRINCIPAL
# ==========================================

if rol == "N":
    t_mi, t_otro = st.tabs(["👤 Mi Ficha", "🔍 Consultar Compañero"])
    with t_mi: render_ficha(mi_id)
    with t_otro:
        dni = st.text_input("DNI Compañero:")
        if dni:
            res = df_nad[df_nad['dni'].astype(str).str.contains(dni.strip())]
            if not res.empty: render_ficha(res.iloc[0]['codnadador'])
            else: st.error("No encontrado.")

else:
    # ROL M: Vista Completa
    t1, t2, t3 = st.tabs(["👥 Padrón", "👤 Ficha Técnica", "🏊‍♂️ Relevos"])
    
    with t1:
        st.markdown("### 🏆 Padrón")
        # (Aquí puedes poner la lógica de Padrón que tenías, simplificada para el ejemplo)
        # IMPORTANTE: Si pones un botón "Ver" aquí, usa la misma lógica:
        # st.session_state.ver_nadador_especifico = r['Nombre Completo']
        # st.rerun() (si estás en la misma página, o switch_page si vienes de otro lado)
        
        filtro = st.text_input("Buscar Nadador:")
        df_show = df_nad.copy()
        if filtro: df_show = df_show[df_show['Nombre Completo'].str.contains(filtro.upper())]
        
        for _, r in df_show.head(15).iterrows():
            c1, c2 = st.columns([4,1])
            with c1: st.markdown(f"**{r['Nombre Completo']}** - {r['codgenero']}")
            with c2:
                if st.button("Ver", key=f"p_{r['codnadador']}"):
                    st.session_state.ver_nadador_especifico = r['Nombre Completo']
                    st.rerun()

    with t2:
        names = sorted(df_nad['Nombre Completo'].unique().tolist())
        
        # --- LÓGICA DE PRE-SELECCIÓN ---
        idx_defecto = 0
        
        # 1. Recuperamos lo que viene del Index (o del Padrón)
        solicitado = st.session_state.get("ver_nadador_especifico")
        
        # 2. Si hay algo solicitado y existe en la lista, calculamos su índice
        if solicitado and solicitado in names:
            idx_defecto = names.index(solicitado)
            # Opcional: Limpiamos la variable para que futuras recargas no se queden "pegadas"
            # del st.session_state.ver_nadador_especifico 
        
        # 3. Dibujamos el selector con el index calculado
        f_nad = st.selectbox("Seleccionar Atleta:", names, index=idx_defecto)
        
        if f_nad:
            target_id = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]['codnadador']
            render_ficha(target_id)
            
    with t3:
        st.markdown("### Historial Relevos")
        # (Lógica de relevos general)
