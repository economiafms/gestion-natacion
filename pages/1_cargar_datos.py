import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Carga de Datos", layout="centered")

# --- 2. SEGURIDAD (GATEKEEPER) ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

if not st.session_state.get("admin_unlocked", False):
    st.error("⛔ Acceso Denegado: Requiere permisos de administrador (Profesor).")
    if st.button("Volver al Inicio"):
        st.switch_page("pages/1_inicio.py")
    st.stop()

st.title("⚙️ Carga de Datos")
st.markdown("---")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. CARGA DE DATOS DE REFERENCIA ---
@st.cache_data(ttl="5m")
def cargar_referencias():
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "estilos": conn.read(worksheet="Estilos"),
            "distancias": conn.read(worksheet="Distancias"),
            "piletas": conn.read(worksheet="Piletas"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias")
        }
    except: return None

db = cargar_referencias()

if not db:
    st.error("Error crítico: No se pudo conectar a la base de datos.")
    st.stop()

# --- 4. FUNCIONES AUXILIARES DE GUARDADO ---
def limpiar_cache():
    st.cache_data.clear()

def obtener_nuevo_id(df, col_id):
    if df.empty: return 1
    # Intentar convertir a numero si es string
    try:
        return int(df[col_id].max()) + 1
    except:
        return len(df) + 1

# Mapeos inversos para guardar códigos, no nombres
map_estilos = dict(zip(db['estilos']['descripcion'], db['estilos']['codestilo']))
map_distancias = dict(zip(db['distancias']['descripcion'], db['distancias']['coddistancia']))
map_piletas = dict(zip(db['piletas']['descripcion'], db['piletas']['codpileta']))

# Crear columna nombre completo para el selector
df_nad_view = db['nadadores'].copy()
df_nad_view['full_name'] = df_nad_view['apellido'].astype(str) + ", " + df_nad_view['nombre'].astype(str)
map_nadadores = dict(zip(df_nad_view['full_name'], df_nad_view['codnadador']))

# --- 5. INTERFAZ ---
tab_tiempos, tab_relevos, tab_nadadores = st.tabs(["⏱️ Tiempos Individuales", "🏊‍♂️ Relevos", "👤 Nuevo Nadador"])

# ==============================================================================
# TAB 1: TIEMPOS INDIVIDUALES
# ==============================================================================
with tab_tiempos:
    st.subheader("Cargar Tiempo Individual")
    with st.form("form_tiempos"):
        nad_sel = st.selectbox("Nadador", sorted(map_nadadores.keys()))
        c1, c2 = st.columns(2)
        est_sel = c1.selectbox("Estilo", list(map_estilos.keys()))
        dist_sel = c2.selectbox("Distancia", list(map_distancias.keys()))
        
        c3, c4 = st.columns(2)
        pil_sel = c3.selectbox("Pileta / Torneo", list(map_piletas.keys()))
        fecha_in = c4.date_input("Fecha", datetime.today())
        
        c5, c6 = st.columns(2)
        tiempo_in = c5.text_input("Tiempo (mm:ss.cc)", placeholder="00:00.00")
        pos_in = c6.number_input("Posición", min_value=1, step=1)
        
        btn_t = st.form_submit_button("Guardar Tiempo", type="primary")
        
        if btn_t:
            if not tiempo_in or ":" not in tiempo_in:
                st.error("Formato de tiempo incorrecto.")
            else:
                try:
                    df_t = db['tiempos'].copy()
                    nuevo_id = obtener_nuevo_id(df_t, 'id_tiempo')
                    
                    nueva_fila = pd.DataFrame([{
                        'id_tiempo': nuevo_id,
                        'codnadador': map_nadadores[nad_sel],
                        'codestilo': map_estilos[est_sel],
                        'coddistancia': map_distancias[dist_sel],
                        'codpileta': map_piletas[pil_sel],
                        'tiempo': tiempo_in,
                        'posicion': int(pos_in),
                        'fecha': fecha_in.strftime('%Y-%m-%d'),
                        'club': 'NOB' # Default
                    }])
                    
                    df_final = pd.concat([df_t, nueva_fila], ignore_index=True)
                    conn.update(worksheet="Tiempos", data=df_final)
                    limpiar_cache()
                    st.success(f"✅ Tiempo guardado correctamente (ID: {nuevo_id})")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==============================================================================
# TAB 2: RELEVOS
# ==============================================================================
with tab_relevos:
    st.subheader("Cargar Relevo")
    with st.form("form_relevos"):
        c1, c2, c3 = st.columns(3)
        r_est = c1.selectbox("Estilo", list(map_estilos.keys()), key="r_e")
        r_dist = c2.selectbox("Distancia", list(map_distancias.keys()), key="r_d")
        r_pil = c3.selectbox("Pileta", list(map_piletas.keys()), key="r_p")
        
        st.markdown("**Integrantes**")
        col_int = st.columns(4)
        integrantes = []
        tiempos_parciales = []
        for i in range(4):
            integrantes.append(col_int[i].selectbox(f"Nadador {i+1}", sorted(map_nadadores.keys()), key=f"rn_{i}"))
            # Opcional: Podríamos pedir parciales, pero simplificamos
        
        c4, c5, c6 = st.columns(3)
        r_tiempo = c4.text_input("Tiempo Final", placeholder="00:00.00")
        r_pos = c5.number_input("Posición", min_value=1, value=1, key="rp")
        r_fecha = c6.date_input("Fecha", datetime.today(), key="rd")
        r_genero = st.radio("Género Relevo", ["M", "F", "X"], horizontal=True)
        
        btn_r = st.form_submit_button("Guardar Relevo", type="primary")
        
        if btn_r:
            ids_ints = [map_nadadores[n] for n in integrantes]
            if len(set(ids_ints)) < 4:
                st.error("Los 4 nadadores deben ser distintos.")
            elif not r_tiempo:
                st.error("Falta tiempo final.")
            else:
                try:
                    df_r = db['relevos'].copy()
                    nuevo_id_r = obtener_nuevo_id(df_r, 'id_relevo')
                    
                    fila_r = pd.DataFrame([{
                        'id_relevo': nuevo_id_r,
                        'codpileta': map_piletas[r_pil],
                        'codestilo': map_estilos[r_est],
                        'coddistancia': map_distancias[r_dist],
                        'codgenero': r_genero,
                        'nadador_1': ids_ints[0], 'tiempo_1': '00.00',
                        'nadador_2': ids_ints[1], 'tiempo_2': '00.00',
                        'nadador_3': ids_ints[2], 'tiempo_3': '00.00',
                        'nadador_4': ids_ints[3], 'tiempo_4': '00.00',
                        'tiempo_final': r_tiempo,
                        'posicion': int(r_pos),
                        'fecha': r_fecha.strftime('%Y-%m-%d'),
                        'tipo_reglamento': 'FED'
                    }])
                    
                    df_r_final = pd.concat([df_r, fila_r], ignore_index=True)
                    conn.update(worksheet="Relevos", data=df_r_final)
                    limpiar_cache()
                    st.success(f"✅ Relevo guardado (ID: {nuevo_id_r})")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==============================================================================
# TAB 3: NUEVO NADADOR
# ==============================================================================
with tab_nadadores:
    st.subheader("Alta de Nadador")
    with st.form("form_nadador"):
        c1, c2 = st.columns(2)
        n_nom = c1.text_input("Nombre")
        n_ape = c2.text_input("Apellido")
        
        c3, c4 = st.columns(2)
        n_dni = c3.text_input("DNI")
        n_socio = c4.text_input("Nro Socio (Login)")
        
        c5, c6 = st.columns(2)
        n_nac = c5.date_input("Fecha Nacimiento", min_value=datetime(1940,1,1))
        n_gen = c6.selectbox("Género", ["M", "F"])
        
        btn_n = st.form_submit_button("Crear Nadador", type="primary")
        
        if btn_n:
            if n_nom and n_ape and n_socio:
                try:
                    df_nad = db['nadadores'].copy()
                    # Validar socio duplicado
                    if str(n_socio) in df_nad['nrosocio'].astype(str).values:
                        st.error("Ese número de socio ya existe.")
                    else:
                        nuevo_cod = obtener_nuevo_id(df_nad, 'codnadador')
                        
                        fila_nad = pd.DataFrame([{
                            'codnadador': nuevo_cod,
                            'nombre': n_nom,
                            'apellido': n_ape,
                            'fechanac': n_nac.strftime('%Y-%m-%d'),
                            'codgenero': n_gen,
                            'dni': n_dni,
                            'nrosocio': n_socio
                        }])
                        
                        # También habría que crear el usuario en hoja Users si se maneja separado
                        # Por ahora actualizamos Nadadores
                        df_n_final = pd.concat([df_nad, fila_nad], ignore_index=True)
                        conn.update(worksheet="Nadadores", data=df_n_final)
                        
                        # Actualizar Users (Login)
                        try:
                            df_u = conn.read(worksheet="User")
                            fila_u = pd.DataFrame([{
                                'id_user': obtener_nuevo_id(df_u, 'id_user'),
                                'nrosocio': n_socio,
                                'perfil': 'N' # Por defecto Nadador
                            }])
                            df_u_final = pd.concat([df_u, fila_u], ignore_index=True)
                            conn.update(worksheet="User", data=df_u_final)
                        except:
                            st.warning("Se creó el nadador pero hubo error al crear usuario en tabla User.")

                        limpiar_cache()
                        st.success(f"✅ Nadador {n_nom} {n_ape} creado con éxito.")
                except Exception as e:
                    st.error(f"Error al crear: {e}")
            else:
                st.warning("Nombre, Apellido y Socio son obligatorios.")
