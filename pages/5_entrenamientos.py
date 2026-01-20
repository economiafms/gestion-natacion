import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Entrenamientos", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id 
mi_nombre = st.session_state.user_name

# Gestión de estado para limpiar formulario tras carga exitosa
if "form_reset_id" not in st.session_state:
    st.session_state.form_reset_id = 0

def reset_carga():
    st.session_state.form_reset_id += 1

def a_segundos(t_str):
    try:
        if not t_str or str(t_str).lower() in ['nan', 'none', '', '00:00.00']: return None
        m, rest = t_str.split(':')
        s, c = rest.split('.')
        return int(m) * 60 + int(s) + int(c) / 100
    except: return None

st.title("⏱️ Centro de Entrenamiento")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .test-card { 
        background-color: #262730; 
        border: 1px solid #444; 
        border-radius: 12px; 
        padding: 16px; 
        margin-bottom: 16px; 
        border-left: 5px solid #E30613; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
    }
    .test-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
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
    
    /* Contenedor de parciales */
    .splits-container { 
        margin-top: 10px; 
        padding: 10px; 
        background: #1e1e1e; 
        border-radius: 6px; 
        border: 1px solid #333; 
    }
    .splits-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
    .split-item { text-align: center; background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; }
    .split-label { font-size: 10px; color: #aaa; display: block; }
    .split-val { font-family: monospace; font-size: 14px; color: #eee; }
    
    .section-title { color: #E30613; font-weight: bold; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #333; font-size: 14px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def cargar_entrenamientos():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "entrenamientos": conn.read(worksheet="Entrenamientos"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias")
        }
    except: return None

db = cargar_entrenamientos()
if not db: st.stop()

df_nad = db['nadadores'].copy()
nad_info = df_nad[df_nad['codnadador'].astype(str) == str(mi_id)]
mi_nom_comp = f"{nad_info.iloc[0]['apellido'].upper()}, {nad_info.iloc[0]['nombre']}" if not nad_info.empty else mi_nombre
lista_noms = sorted((df_nad['apellido'].astype(str).str.upper() + ", " + df_nad['nombre'].astype(str)).unique().tolist())
list_dist_total = [d for d in db['distancias']['descripcion'].unique() if "25" not in d and "4x" not in d.lower()]

tab_ver, tab_cargar = st.tabs(["📂 Historial", "📝 Cargar Test"])

# ==============================================================================
#  CARGA DE TEST
# ==============================================================================
with tab_cargar:
    # Usamos un contenedor con key dinámico para resetear todo el formulario al guardar
    with st.container(key=f"c_{st.session_state.form_reset_id}"):
        st.subheader("1. Definir Prueba")
        c1, c2 = st.columns([1, 2])
        f_val = c1.date_input("Fecha", date.today(), format="DD/MM/YYYY")
        
        n_in = c2.selectbox("Nadador", [mi_nom_comp] if rol=="N" else lista_noms, index=0 if rol=="N" else None)
        id_nad_target = mi_id if rol=="N" else (df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == n_in].iloc[0]['codnadador'] if n_in else None)
        
        c3, c4 = st.columns(2)
        est_val = c3.selectbox("Estilo", db['estilos']['descripcion'].unique(), index=None)
        dist_t_val = c4.selectbox("Distancia TOTAL", list_dist_total, index=None)

        if n_in and est_val and dist_t_val:
            m_tot = int(dist_t_val.split(" ")[0])
            m_par = 100 if m_tot == 400 else (50 if m_tot == 200 else (25 if m_tot == 100 else 0))
            quiere_p = st.toggle("¿Cargar tiempos parciales?", value=True) if m_par > 0 else False
            
            st.divider()
            
            # FORMULARIO DE CARGA
            with st.form("form_registro_test", clear_on_submit=True):
                st.markdown("<div class='section-title'>TIEMPO FINAL</div>", unsafe_allow_html=True)
                # Input bloqueado solo visual
                st.text_input("Distancia", value=dist_t_val, disabled=True, label_visibility="collapsed")
                
                tf1, tf2, tf3 = st.columns(3)
                mf = tf1.number_input("Min", 0, 59, 0)
                sf = tf2.number_input("Seg", 0, 59, 0)
                cf = tf3.number_input("Cent", 0, 99, 0)
                
                lp = []
                if quiere_p:
                    st.markdown(f"<div class='section-title'>PARCIALES ({m_par} mts)</div>", unsafe_allow_html=True)
                    for i in range(1, 5):
                        st.write(f"Parcial {i}")
                        px1, px2, px3, px4 = st.columns(4)
                        px1.text_input(f"d{i}", value=f"{m_par} mts", disabled=True, label_visibility="collapsed")
                        pm = px2.number_input("M", 0, 59, 0, key=f"pm_{i}")
                        ps = px3.number_input("S", 0, 59, 0, key=f"ps_{i}")
                        pc = px4.number_input("C", 0, 99, 0, key=f"pc_{i}")
                        lp.append(f"{pm:02d}:{ps:02d}.{pc:02d}" if (pm+ps+pc)>0 else "")
                
                # Botón de envío
                submitted = st.form_submit_button("💾 GUARDAR REGISTRO", use_container_width=True)
                
                if submitted:
                    # Validaciones básicas
                    s_final = (mf*60) + sf + (cf/100)
                    if s_final == 0:
                        st.error("⚠️ El tiempo final no puede ser 0.")
                    else:
                        # Validación de coherencia (bloqueante)
                        valido = True
                        if quiere_p:
                            s_parciales = 0
                            for p_str in lp:
                                sec = a_segundos(p_str)
                                if sec: s_parciales += sec
                            
                            if s_parciales > 0 and abs(s_parciales - s_final) > 0.5:
                                st.error(f"❌ Error de coherencia: La suma de parciales ({s_parciales:.2f}s) no coincide con el tiempo final ({s_final:.2f}s).")
                                valido = False
                        
                        if valido:
                            with st.spinner("Guardando en la nube..."):
                                try:
                                    # Generar ID
                                    max_id = pd.to_numeric(db['entrenamientos']['id_entrenamiento'], errors='coerce').max() if not db['entrenamientos'].empty else 0
                                    new_id = int(0 if pd.isna(max_id) else max_id) + 1
                                    
                                    # Buscar ID distancia parcial
                                    id_dp = ""
                                    if quiere_p:
                                         id_dp = db['distancias'][db['distancias']['descripcion'].str.startswith(str(m_par))].iloc[0]['coddistancia']

                                    # Crear fila
                                    row = pd.DataFrame([{
                                        "id_entrenamiento": new_id, 
                                        "fecha": f_val.strftime('%Y-%m-%d'), 
                                        "codnadador": int(id_nad_target), 
                                        "codestilo": db['estilos'][db['estilos']['descripcion'] == est_val].iloc[0]['codestilo'],
                                        "coddistancia": db['distancias'][db['distancias']['descripcion'] == dist_t_val].iloc[0]['coddistancia'],
                                        "coddistancia_parcial": id_dp,
                                        "tiempo_final": f"{mf:02d}:{sf:02d}.{cf:02d}",
                                        "parcial_1": lp[0] if len(lp)>0 else "", 
                                        "parcial_2": lp[1] if len(lp)>1 else "",
                                        "parcial_3": lp[2] if len(lp)>2 else "", 
                                        "parcial_4": lp[3] if len(lp)>3 else "",
                                        "observaciones": "" # Campo vacío por eliminación solicitada
                                    }])
                                    
                                    # Actualizar GSheets
                                    nuevo_df = pd.concat([db['entrenamientos'], row], ignore_index=True)
                                    conn.update(worksheet="Entrenamientos", data=nuevo_df)
                                    
                                    # Limpiar caché y reiniciar
                                    st.cache_data.clear()
                                    reset_carga()
                                    st.success("✅ ¡Registro guardado exitosamente!")
                                    time.sleep(1) # Breve pausa para ver el mensaje
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error técnico al guardar: {e}")

# ==============================================================================
#  HISTORIAL
# ==============================================================================
with tab_ver:
    target_id = mi_id if rol == "N" else None
    if rol in ["M", "P"]:
        sel_n = st.selectbox("Consultar Historial de:", lista_noms, index=None, key="h_nad")
        if sel_n: target_id = df_nad[(df_nad['apellido'].str.upper() + ", " + df_nad['nombre']) == sel_n].iloc[0]['codnadador']
    
    if target_id:
        df_h = db['entrenamientos'][db['entrenamientos']['codnadador'].astype(str) == str(target_id)].copy()
        
        if not df_h.empty:
            df_h = df_h.merge(db['estilos'], on='codestilo', how='left').merge(db['distancias'], left_on='coddistancia', right_on='coddistancia', how='left')
            
            # Filtros
            st.markdown("<div class='section-title'>🔍 Filtros</div>", unsafe_allow_html=True)
            est_opts = ["Todos"] + sorted(df_h['descripcion_x'].unique().tolist())
            dist_opts = ["Todos"] + sorted(df_h['descripcion_y'].unique().tolist())
            
            c_f1, c_f2 = st.columns(2)
            f_est = c_f1.selectbox("Estilo", est_opts)
            f_dist = c_f2.selectbox("Distancia", dist_opts)

            df_filt = df_h.copy()
            if f_est != "Todos": df_filt = df_filt[df_filt['descripcion_x'] == f_est]
            if f_dist != "Todos": df_filt = df_filt[df_filt['descripcion_y'] == f_dist]

            # Gráfico Progresión
            if f_est != "Todos" and f_dist != "Todos" and len(df_filt) >= 2:
                st.markdown("<div class='section-title'>📈 Evolución</div>", unsafe_allow_html=True)
                df_filt['seg'] = df_filt['tiempo_final'].apply(a_segundos)
                df_filt['fecha_dt'] = pd.to_datetime(df_filt['fecha'])
                fig = px.line(df_filt.sort_values('fecha_dt'), x='fecha_dt', y='seg', markers=True, 
                              color_discrete_sequence=['#E30613'])
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", 
                                  yaxis_title="Segundos", xaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

            # Listado
            st.markdown("<div class='section-title'>📋 Registros</div>", unsafe_allow_html=True)
            for _, r in df_filt.sort_values(['fecha', 'id_entrenamiento'], ascending=False).iterrows():
                
                f_fmt = datetime.strptime(str(r['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                
                # Procesar Parciales
                ps = [r.get(f'parcial_{i}') for i in range(1, 5)]
                p_validos = [p for p in ps if p and str(p).lower() not in ['nan', 'none', '', '00:00.00']]
                
                splits_html_block = ""
                if p_validos:
                    grid_items = "".join([f"<div class='split-item'><span class='split-label'>P{i+1}</span><span class='split-val'>{p}</span></div>" for i, p in enumerate(p_validos)])
                    splits_html_block = f"""<div class='splits-container'><div class='splits-grid'>{grid_items}</div></div>"""
                
                # Tarjeta (Sin observaciones)
                card_html = f"""
                <div class="test-card">
                    <div class="test-header">
                        <div>
                            <div class="test-style">{r.get('descripcion_x', '-')}</div>
                            <div class="test-dist">{r.get('descripcion_y', '-')} <span class="test-date">| {f_fmt}</span></div>
                        </div>
                        <div class="final-time">{r['tiempo_final']}</div>
                    </div>
                    {splits_html_block}
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

                if p_validos and st.checkbox(f"Analizar tramos", key=f"chk_{r['id_entrenamiento']}"):
                    p_seg = [a_segundos(p) for p in p_validos]
                    fig_bar = px.bar(x=[f"P{i+1}" for i in range(len(p_seg))], y=p_seg, 
                                     labels={'x': 'Parcial', 'y': 'Segundos'},
                                     color_discrete_sequence=['#E30613'])
                    fig_bar.update_layout(height=200, template="plotly_dark", showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay registros.")
