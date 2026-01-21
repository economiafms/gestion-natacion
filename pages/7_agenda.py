import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, timedelta
import urllib.parse
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Agenda de Competencias", layout="centered")

# --- SEGURIDAD ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = str(st.session_state.user_id) # ID del usuario actual

st.title("📅 Calendario de Competencias")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .comp-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #E30613;
    }
    .comp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .comp-date { font-size: 16px; font-weight: bold; color: #E30613; }
    .comp-title { font-size: 20px; font-weight: bold; color: white; margin: 0; }
    .comp-loc { font-size: 14px; color: #aaa; margin-bottom: 5px; }
    .comp-pruebas { background: rgba(255,255,255,0.05); padding: 8px; border-radius: 4px; font-size: 13px; color: #ddd; margin-top: 5px; }
    .btn-cal { text-decoration: none; color: #4285F4; font-size: 12px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="1m")
def cargar_agenda():
    try:
        return conn.read(worksheet="Agenda")
    except:
        # Estructura fallback por si la hoja está vacía o nueva
        return pd.DataFrame(columns=['id_evento', 'fecha', 'hora', 'titulo', 'lugar', 'pruebas', 'inscritos'])

df_agenda = cargar_agenda()

# --- FUNCIONES AUXILIARES ---
def generar_link_calendar(titulo, fecha, hora, lugar):
    try:
        fmt = '%Y-%m-%d %H:%M'
        start_dt = datetime.strptime(f"{fecha} {hora}", fmt)
        end_dt = start_dt + timedelta(hours=4) # Duración estimada
        
        dates = f"{start_dt.strftime('%Y%m%dT%H%M00')}/{end_dt.strftime('%Y%m%dT%H%M00')}"
        base = "https://www.google.com/calendar/render?action=TEMPLATE"
        params = {
            "text": f"🏊 {titulo}",
            "dates": dates,
            "details": "Competencia de Natación Master NOB.",
            "location": lugar,
            "sf": "true",
            "output": "xml"
        }
        return f"{base}&{urllib.parse.urlencode(params)}"
    except: return "#"

# --- PANEL DE ADMINISTRACIÓN (Solo M/P) ---
if rol in ["M", "P"]:
    with st.expander("🛠️ Administrar Eventos"):
        with st.form("add_event"):
            st.markdown("##### Nuevo Evento")
            c1, c2 = st.columns(2)
            f_in = c1.date_input("Fecha", min_value=date.today())
            h_in = c2.time_input("Hora", value=datetime.strptime("09:00", "%H:%M").time())
            t_in = st.text_input("Título", placeholder="Ej: Torneo Regional")
            l_in = st.text_input("Lugar", placeholder="Ej: Club Echesortu")
            p_in = st.text_area("Pruebas / Detalles", placeholder="50 Libres, 100 Pecho, Posta 4x50...")
            
            if st.form_submit_button("💾 Guardar Competencia"):
                if t_in:
                    # Crear ID y guardar
                    max_id = pd.to_numeric(df_agenda['id_evento'], errors='coerce').max()
                    new_id = int(0 if pd.isna(max_id) else max_id) + 1
                    
                    nuevo = pd.DataFrame([{
                        "id_evento": new_id, "fecha": f_in.strftime('%Y-%m-%d'), "hora": h_in.strftime('%H:%M'),
                        "titulo": t_in, "lugar": l_in, "pruebas": p_in, "inscritos": ""
                    }])
                    conn.update(worksheet="Agenda", data=pd.concat([df_agenda, nuevo], ignore_index=True))
                    st.success("Evento creado"); st.cache_data.clear(); time.sleep(1); st.rerun()
                else:
                    st.error("Falta el título.")

# --- VISUALIZACIÓN ---
if not df_agenda.empty:
    df_agenda['fecha_dt'] = pd.to_datetime(df_agenda['fecha'], errors='coerce')
    hoy = pd.to_datetime(date.today())
    
    # Eventos Futuros
    futuros = df_agenda[df_agenda['fecha_dt'] >= hoy].sort_values('fecha_dt')
    
    if not futuros.empty:
        st.markdown(f"### 🚀 Próximas Fechas ({len(futuros)})")
        
        for _, row in futuros.iterrows():
            f_txt = row['fecha_dt'].strftime('%d/%m/%Y')
            link_cal = generar_link_calendar(row['titulo'], row['fecha'], row['hora'], row['lugar'])
            
            # Lógica de Inscripción
            lista_inscritos = str(row['inscritos']).split(',') if pd.notna(row['inscritos']) and str(row['inscritos']) != "" else []
            ya_inscrito = mi_id in lista_inscritos
            
            # Tarjeta UI
            st.markdown(f"""
            <div class="comp-card">
                <div class="comp-header">
                    <div class="comp-date">{f_txt} | {row['hora']} hs</div>
                    <a href="{link_cal}" target="_blank" class="btn-cal">📅 Agregar a Calendar</a>
                </div>
                <div class="comp-title">{row['titulo']}</div>
                <div class="comp-loc">📍 {row['lugar']}</div>
                <div class="comp-pruebas">🏊 <b>Pruebas:</b> {row['pruebas']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botonera Acciones
            c_actions = st.columns([1, 1, 3])
            
            # Acción 1: Inscribirse (Solo N)
            if rol == "N":
                with c_actions[0]:
                    if ya_inscrito:
                        if st.button("❌ Bajarme", key=f"out_{row['id_evento']}"):
                            lista_inscritos.remove(mi_id)
                            row['inscritos'] = ",".join(lista_inscritos)
                            # Actualizar DF completo
                            df_agenda.loc[df_agenda['id_evento'] == row['id_evento'], 'inscritos'] = row['inscritos']
                            # Limpiar columna temporal antes de guardar
                            save_df = df_agenda.drop(columns=['fecha_dt'])
                            conn.update(worksheet="Agenda", data=save_df)
                            st.rerun()
                    else:
                        if st.button("✅ Inscribirme", key=f"in_{row['id_evento']}"):
                            lista_inscritos.append(mi_id)
                            row['inscritos'] = ",".join(lista_inscritos)
                            df_agenda.loc[df_agenda['id_evento'] == row['id_evento'], 'inscritos'] = row['inscritos']
                            save_df = df_agenda.drop(columns=['fecha_dt'])
                            conn.update(worksheet="Agenda", data=save_df)
                            st.success("¡Inscrito!")
                            time.sleep(1); st.rerun()
                            
            # Acción 2: Eliminar (Solo M)
            if rol in ["M", "P"]:
                with c_actions[0]:
                    if st.button("🗑️ Eliminar", key=f"del_{row['id_evento']}"):
                        save_df = df_agenda[df_agenda['id_evento'] != row['id_evento']].drop(columns=['fecha_dt'])
                        conn.update(worksheet="Agenda", data=save_df)
                        st.warning("Evento borrado"); time.sleep(1); st.rerun()
                
                with c_actions[2]:
                    # Mostrar conteo de inscritos al profe
                    cant = len(lista_inscritos) if lista_inscritos and lista_inscritos[0] != '' else 0
                    st.caption(f"👥 Nadadores inscritos: **{cant}**")

    else:
        st.info("No hay competencias programadas próximamente.")
else:
    st.info("La agenda está vacía.")
