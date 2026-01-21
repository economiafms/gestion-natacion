import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Agenda NOB", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role

st.title("📅 Agenda del Equipo")

# --- CSS PERSONALIZADO (Estilo Newell's) ---
st.markdown("""
<style>
    .event-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 5px solid #E30613; /* Rojo NOB */
        display: flex;
        flex-direction: column;
    }
    .event-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
    }
    .event-date {
        font-size: 14px;
        font-weight: bold;
        color: #E30613;
        text-transform: uppercase;
    }
    .event-type {
        font-size: 11px;
        background-color: #333;
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .event-title {
        font-size: 18px;
        font-weight: bold;
        color: white;
        margin-bottom: 5px;
    }
    .event-details {
        font-size: 13px;
        color: #aaa;
        display: flex;
        gap: 15px;
    }
    .event-desc {
        margin-top: 10px;
        font-size: 14px;
        color: #ddd;
        background: rgba(255,255,255,0.05);
        padding: 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="10m")
def cargar_agenda():
    try:
        # Intenta leer la hoja 'Agenda'. Si no existe, devuelve estructura vacía
        return conn.read(worksheet="Agenda")
    except:
        return pd.DataFrame(columns=['id_evento', 'fecha', 'hora', 'titulo', 'tipo', 'lugar', 'descripcion'])

df_agenda = cargar_agenda()

# --- PANEL DE ADMINISTRACIÓN (Solo M y P) ---
if rol in ["M", "P"]:
    with st.expander("➕ Agregar Nuevo Evento (Solo Entrenadores)"):
        with st.form("form_evento"):
            c1, c2 = st.columns(2)
            fecha_in = c1.date_input("Fecha", min_value=date.today())
            hora_in = c2.time_input("Hora")
            
            titulo_in = st.text_input("Título del Evento")
            
            c3, c4 = st.columns(2)
            tipo_in = c3.selectbox("Tipo", ["Competencia", "Entrenamiento", "Reunión", "Social", "Viaje"])
            lugar_in = c4.text_input("Lugar / Pileta")
            
            desc_in = st.text_area("Descripción / Observaciones")
            
            submitted = st.form_submit_button("Guardar Evento", use_container_width=True)
            
            if submitted:
                if not titulo_in:
                    st.error("El título es obligatorio.")
                else:
                    try:
                        # Generar ID
                        max_id = pd.to_numeric(df_agenda['id_evento'], errors='coerce').max()
                        new_id = int(0 if pd.isna(max_id) else max_id) + 1
                        
                        nuevo_evento = pd.DataFrame([{
                            "id_evento": new_id,
                            "fecha": fecha_in.strftime('%Y-%m-%d'),
                            "hora": hora_in.strftime('%H:%M'),
                            "titulo": titulo_in,
                            "tipo": tipo_in,
                            "lugar": lugar_in,
                            "descripcion": desc_in
                        }])
                        
                        updated_df = pd.concat([df_agenda, nuevo_evento], ignore_index=True)
                        conn.update(worksheet="Agenda", data=updated_df)
                        st.success("Evento agregado exitosamente.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# --- VISUALIZACIÓN DE AGENDA ---

# Procesar fechas
if not df_agenda.empty:
    df_agenda['fecha_dt'] = pd.to_datetime(df_agenda['fecha'], errors='coerce')
    
    # Separar eventos futuros y pasados
    hoy = pd.to_datetime(date.today())
    
    futuros = df_agenda[df_agenda['fecha_dt'] >= hoy].sort_values('fecha_dt', ascending=True)
    pasados = df_agenda[df_agenda['fecha_dt'] < hoy].sort_values('fecha_dt', ascending=False)
    
    tab_fut, tab_hist = st.tabs(["🚀 Próximos Eventos", "📜 Historial"])
    
    # --- RENDERIZADOR DE TARJETAS ---
    def render_eventos(df_source):
        if df_source.empty:
            st.info("No hay eventos en esta sección.")
            return

        for _, row in df_source.iterrows():
            f_fmt = row['fecha_dt'].strftime('%d/%m/%Y')
            
            # Icono según tipo
            iconos = {"Competencia": "🏆", "Entrenamiento": "🏊", "Reunión": "🤝", "Social": "🎉", "Viaje": "🚌"}
            icono = iconos.get(row['tipo'], "📅")
            
            st.markdown(f"""
            <div class="event-card">
                <div class="event-header">
                    <span class="event-date">{icono} {f_fmt} - {row['hora']} hs</span>
                    <span class="event-type">{row['tipo']}</span>
                </div>
                <div class="event-title">{row['titulo']}</div>
                <div class="event-details">
                    <span>📍 {row['lugar']}</span>
                </div>
                <div class="event-desc">{row['descripcion']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón eliminar (Solo M/P)
            if rol in ["M", "P"]:
                if st.button("Eliminar", key=f"del_{row['id_evento']}"):
                    try:
                        clean_df = df_agenda[df_agenda['id_evento'] != row['id_evento']]
                        # Eliminar columnas auxiliares antes de guardar
                        if 'fecha_dt' in clean_df.columns: del clean_df['fecha_dt']
                        conn.update(worksheet="Agenda", data=clean_df)
                        st.warning("Evento eliminado.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except:
                        st.error("Error al eliminar.")

    with tab_fut:
        render_eventos(futuros)
        
    with tab_hist:
        render_eventos(pasados)

else:
    st.info("Aún no hay eventos cargados en la agenda.")
