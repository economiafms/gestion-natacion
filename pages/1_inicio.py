import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, timezone
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inicio", layout="centered")

# --- INICIALIZACIÓN SEGURA DE VARIABLES ---
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

if "show_login_form" not in st.session_state: 
    st.session_state.show_login_form = False

if "admin_unlocked" not in st.session_state: 
    st.session_state.admin_unlocked = False

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- OPTIMIZACIÓN DE CARGA DE DATOS (FIX ERROR 429) ---
# Separamos los datos estáticos de los dinámicos para no saturar la API

@st.cache_data(ttl="1h")
def cargar_datos_generales():
    """Carga datos pesados que no cambian frecuentemente."""
    try:
        return {
            "nadadores": conn.read(worksheet="Nadadores"),
            "tiempos": conn.read(worksheet="Tiempos"),
            "relevos": conn.read(worksheet="Relevos"),
            "categorias": conn.read(worksheet="Categorias"),
            "estilos": conn.read(worksheet="Estilos")
        }
    except: return None

@st.cache_data(ttl="10m")
def cargar_datos_rutinas():
    """Carga solo las rutinas y el seguimiento, que cambian seguido."""
    try:
        return {
            "rutinas": conn.read(worksheet="Rutinas"),
            "seguimiento": conn.read(worksheet="Rutinas_Seguimiento")
        }
    except: return None

# Función unificadora para mantener compatibilidad con el código existente
def get_db():
    general = cargar_datos_generales()
    rutinas = cargar_datos_rutinas()
    
    if general and rutinas:
        return {**general, **rutinas}
    elif general:
        return general
    elif rutinas:
        return rutinas
    return None

db = get_db()

# --- FUNCIONES AUXILIARES ---
def calcular_cat_exacta(edad, df_cat):
    try:
        for _, r in df_cat.iterrows():
            if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
        return "-"
    except: return "-"

def calcular_categoria_grafico(anio_nac):
    anio_actual = datetime.now().year
    edad = anio_actual - anio_nac
    if edad < 20: return "Juvenil"
    elif 20 <= edad <= 24: return "PRE"
    elif 25 <= edad <= 29: return "A"
    elif 30 <= edad <= 34: return "B"
    elif 35 <= edad <= 39: return "C"
    elif 40 <= edad <= 44: return "D"
    elif 45 <= edad <= 49: return "E"
    elif 50 <= edad <= 54: return "F"
    elif 55 <= edad <= 59: return "G"
    elif 60 <= edad <= 64: return "H"
    elif 65 <= edad <= 69: return "I"
    elif 70 <= edad <= 74: return "J"
    else: return "K+"

def intentar_desbloqueo():
    try:
        sec_user = st.secrets["admin"]["usuario"]
        sec_pass = st.secrets["admin"]["password"]
    except:
        sec_user = "entrenador"; sec_pass = "nob1903"

    if st.session_state.u_in == sec_user and st.session_state.p_in == sec_pass: 
        st.session_state.admin_unlocked = True
        st.session_state.show_login_form = False
        st.rerun()
    else: 
        st.error("Credenciales incorrectas")

def guardar_seguimiento_inicio(id_rutina, id_nadador):
    try:
        # Leemos solo la hoja necesaria sin caché para tener el último estado
        df_seg = conn.read(worksheet="Rutinas_Seguimiento", ttl=0)
        
        # OBTENER HORA ARGENTINA (UTC-3)
        ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
        hora_str = ahora_arg.strftime("%Y-%m-%d %H:%M:%S")
        
        nuevo_registro = pd.DataFrame([{
            "id_rutina": id_rutina,
            "codnadador": int(id_nadador),
            "fecha_realizada": hora_str
        }])
        df_final = pd.concat([df_seg, nuevo_registro], ignore_index=True)
        conn.update(worksheet="Rutinas_Seguimiento", data=df_final)
        
        # --- FIX IMPORTANTE ---
        # Solo limpiamos el caché de RUTINAS, no el general.
        # Esto evita recargar las 7 hojas y previene el error 429.
        cargar_datos_rutinas.clear()
        
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- VISUALIZACIÓN ---

# BANNER TÍTULO
st.markdown("""
    <style>
        .banner-box {
            background-color: #262730;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #444;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .banner-sub {
            color: white !important;
            font-size: 20px;
            margin: 0;
            font-weight: normal;
        }
        .banner-main {
            color: #E30613 !important;
            font-size: 32px;
            margin: 0;
            font-weight: 800;
        }
    </style>
    <div class='banner-box'>
        <h3 class='banner-sub'>BIENVENIDOS AL COMPLEJO ACUÁTICO</h3>
        <h1 class='banner-main'>NEWELL'S OLD BOYS</h1>
    </div>
""", unsafe_allow_html=True)

# 1. GUÍA RÁPIDA
if st.session_state.role == "M":
    with st.expander("📖 Guía rápida de uso – Perfil Manager", expanded=False):
        st.markdown("""
        Esta guía detalla las herramientas disponibles para mi gestión, facilitando el análisis y la toma de decisiones.
        
        **📂 Fichero**
        Puedo consultar la ficha técnica completa de todos mis nadadores, incluyendo historial de competencias, mejores tiempos y relevos, con filtros para facilitar mi análisis.
        
        **📝 Rutinas**
        Permite crear, editar y asignar rutinas a mis nadadores, y verificar quiénes cumplen con los entrenamientos planificados.
        
        **🏋️ Entrenamientos**
        Visualización de los tiempos de test de todos los nadadores para evaluar evolución y rendimiento.
        
        **🏅 Mi categoría**
        Visualización de nadadores agrupados por categorías para análisis comparativo.
        
        **📅 Agenda**
        Carga y edición de competencias, junto con la gestión de nadadores inscriptos.

        **🏆 Ranking**
        Visualización de los mejores tiempos por prueba para identificar a los nadadores más destacados.

        **⏱️ Simulador**
        Simulación de escenarios manuales y automáticos de relevos para estimar tiempos basados en datos reales.

        **➕ Cargar competencias (Inicio)**
        Desde el botón CARGAR COMPETENCIAS puedo cargar nuevos nadadores, asignar permisos de Manager o Nadador y cargar tiempos de competencias y relevos.
        
        ---
        **Aclaración final:**
        * La carga diaria de datos deportivos es responsabilidad del nadador.
        * Mi rol es analizar y tomar decisiones a partir de esa información.
        """)

elif st.session_state.role == "N":
    with st.expander("📖 Guía rápida de uso – Perfil Nadador", expanded=False):
        st.markdown("""
        Este sistema está diseñado para que cada nadador gestione y registre su propia información deportiva.
        Cuantos más datos cargues, mejor vas a poder analizar tu rendimiento y evolución en el tiempo.
        
        **👤 Ficha**
        Encontrás todo lo relacionado a tu perfil deportivo: competencias, mejores tiempos, historial y relevos.
        También podés consultar la ficha de un compañero si conocés su DNI.
        
        **📝 Rutinas**
        Accedés a las rutinas mensuales del entrenador, con una barra de progreso para saber en qué sesión estás y llevar un registro ordenado de tus entrenamientos.
        
        **🏋️ Entrenamientos**
        Este módulo se utiliza para cargar los test de rendimiento.
        Los test pueden incluir parciales, divididos en cuatro tramos según la distancia de la prueba. Recorda anotar los parciales según esta tabla.
        **50mts = 1x50  /  100mts = 4x25   /    200mts = 4x50 /     400mts = 4x100
        
        **🏅 Mi categoría**
        Visualizás los valores promedio de tu categoría y los nadadores que la integran, para comparar tus tiempos y rendimiento en competencias.
        
        **📅 Agenda**
        Encontrás las próximas competencias del equipo y podés registrarte de forma simple, reemplazando el registro en Excel por un sistema más dinámico.
        
        ---
        **Aclaraciones importantes**
        * La información es autogestionada por el nadador
        * El entrenador no carga ni corrige datos
        * Cada registro suma para tu mejora futura
        * Uso personal, voluntario y a libre demanda
        """)

st.divider()

if db and st.session_state.user_id:
    user_id = st.session_state.user_id
    me = db['nadadores'][db['nadadores']['codnadador'] == user_id].iloc[0]
    
    try: edad = datetime.now().year - pd.to_datetime(me['fechanac']).year
    except: edad = 0
    cat = calcular_cat_exacta(edad, db['categorias'])
    
    df_t = db['tiempos'].copy(); df_r = db['relevos'].copy()
    df_t['posicion'] = pd.to_numeric(df_t['posicion'], errors='coerce').fillna(0).astype(int)
    df_r['posicion'] = pd.to_numeric(df_r['posicion'], errors='coerce').fillna(0).astype(int)
    
    mis_oros = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==1)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==1)])
    mis_platas = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==2)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==2)])
    mis_bronces = len(df_t[(df_t['codnadador']==user_id)&(df_t['posicion']==3)]) + len(df_r[((df_r['nadador_1']==user_id)|(df_r['nadador_2']==user_id)|(df_r['nadador_3']==user_id)|(df_r['nadador_4']==user_id))&(df_r['posicion']==3)])
    mi_total = mis_oros + mis_platas + mis_bronces

    # 1. TARJETA PERFIL
    st.write("### 👤 Mi Perfil")
    st.markdown(f"""
    <style>
        .padron-card {{ background-color: #262730; border: 1px solid #444; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }}
        .p-total {{ font-size: 26px; color: #FFD700; font-weight: bold; }}
    </style>
    <div class="padron-card">
        <div style="flex: 2; border-right: 1px solid #555;">
            <div style="font-weight: bold; font-size: 18px; color: white;">{me['nombre']} {me['apellido']}</div>
            <div style="font-size: 13px; color: #ccc;">{edad} años • {me['codgenero']}</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <div style="display: flex; justify-content: center; gap: 8px; font-size: 16px;">
                <span>🥇{mis_oros}</span> <span>🥈{mis_platas}</span> <span>🥉{mis_bronces}</span>
            </div>
        </div>
        <div style="flex: 1; text-align: right; border-left: 1px solid #555; padding-left: 10px;">
            <div class="p-total">★ {mi_total}</div>
            <div style="font-size: 16px; color: #4CAF50; font-weight: bold;">{cat}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Ver Mi Ficha Completa ➝", type="primary", use_container_width=True, key="btn_ficha_inicio"):
        st.session_state.ver_nadador_especifico = st.session_state.user_name
        st.switch_page("pages/2_visualizar_datos.py")
    
    st.write("") 

    # // ATAJO RUTINA DIARIA (Logica Completa de Gamificación)
    if st.session_state.role == "N":
        # HORA ARGENTINA (UTC-3)
        hoy_arg = datetime.now(timezone.utc) - timedelta(hours=3)
        
        df_rut = db.get('rutinas')
        df_seg = db.get('seguimiento')
        
        if df_rut is not None and df_seg is not None:
            rutinas_mes = df_rut[
                (df_rut['anio_rutina'] == hoy_arg.year) & 
                (df_rut['mes_rutina'] == hoy_arg.month)
            ].copy()

            # REGLA 1: Si no hay rutinas en el mes, NO mostrar el expander
            if not rutinas_mes.empty:
                
                with st.expander("🏊‍♂️ ¿Hice mi rutina de hoy?", expanded=False):
                    
                    hoy_str_corto = hoy_arg.strftime("%Y-%m-%d")
                    rutina_hoy_completada = None
                    
                    if not df_seg.empty:
                        mis_seg = df_seg[df_seg['codnadador'] == user_id].copy()
                        mis_seg['fecha_dt'] = pd.to_datetime(mis_seg['fecha_realizada']).dt.strftime("%Y-%m-%d")
                        
                        hecho_hoy = mis_seg[mis_seg['fecha_dt'] == hoy_str_corto]
                        
                        if not hecho_hoy.empty:
                            ultimo_id_hoy = hecho_hoy.iloc[-1]['id_rutina']
                            rutina_hoy_completada = rutinas_mes[rutinas_mes['id_rutina'] == ultimo_id_hoy]
                        realizadas_historicas = mis_seg['id_rutina'].unique()
                    else:
                        realizadas_historicas = []

                    # --- LÓGICA DE ESTADOS ---
                    if rutina_hoy_completada is not None and not rutina_hoy_completada.empty:
                        # HOY GANÓ. Verificamos si era la ÚLTIMA rutina disponible del mes.
                        r_row = rutina_hoy_completada.iloc[0]
                        
                        # Calculamos si quedan pendientes (excluyendo la que ya se sabe realizada)
                        pendientes_check = rutinas_mes[~rutinas_mes['id_rutina'].isin(realizadas_historicas)]
                        
                        if pendientes_check.empty:
                            # REGLA 2: ULTIMA RUTINA -> PLACA DORADA + BALLOONS
                            st.balloons()
                            st.markdown(f"""
                            <div style="
                                border: 2px solid #FFD700; 
                                border-radius: 12px; 
                                background-color: #1a1a1a; 
                                padding: 20px; 
                                text-align: center;
                                box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2);
                                margin-bottom: 20px;">
                                <div style="font-size: 40px; margin-bottom: 10px;">🏆</div>
                                <h3 style="margin: 0; color: #FFD700; font-weight: 800; letter-spacing: 1px;">¡MES COMPLETADO!</h3>
                                <p style="color: #ccc; margin-top: 5px; font-size: 14px;">Sesión {int(r_row['nro_sesion'])} finalizada. ¡Completé todas las rutinas!</p>
                                <div style="margin-top: 15px; padding: 8px; background-color: rgba(255, 215, 0, 0.1); border-radius: 8px; color: #FFD700; font-size: 12px; font-weight: bold;">
                                    ¡Impresionante constancia! A descansar. 🔋
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # REGLA 3: DÍA NORMAL -> MENSAJE SIMPLE
                            st.success(f"🏆 **¡Misión Cumplida!** Completé la **Sesión {int(r_row['nro_sesion'])}** hoy.")
                        
                    else:
                        # PENDIENTE
                        rutinas_pendientes = rutinas_mes[~rutinas_mes['id_rutina'].isin(realizadas_historicas)].sort_values('nro_sesion')
                        
                        if not rutinas_pendientes.empty:
                            prox_sesion = rutinas_pendientes.iloc[0]
                            r_id = prox_sesion['id_rutina']
                            r_nro = int(prox_sesion['nro_sesion']) 
                            r_texto = prox_sesion['texto_rutina']
                            
                            st.markdown(f"#### ⚡ Mi entrenamiento de hoy: Sesión {r_nro}")
                            st.markdown(r_texto)
                            st.write("") 
                            
                            if st.button("✅ DÍA GANADO", key=f"btn_ganado_inicio_{r_id}", type="primary", use_container_width=True):
                                my_bar = st.progress(0, text="Registrando entrenamiento...")
                                for percent_complete in range(100):
                                    time.sleep(0.01) 
                                    my_bar.progress(percent_complete + 1, text="Registrando entrenamiento...")
                                time.sleep(0.2)
                                my_bar.empty()
                                
                                st.toast(f"¡Excelente! Sesión {r_nro} registrada con éxito.", icon='🏆')
                                
                                if guardar_seguimiento_inicio(r_id, user_id):
                                    time.sleep(1) 
                                    st.rerun()
                        else:
                            st.info("🏅 ¡Mes completo! No tengo más rutinas pendientes.")
        
        st.write("") 

    # 2. MIS REGISTROS (FRECUENCIA DE ESTILOS)
    mis_regs = db['tiempos'][db['tiempos']['codnadador'] == user_id].copy()
    if not mis_regs.empty:
        st.markdown("<h5 style='text-align: center; color: #aaa; margin-bottom: 15px;'>MIS ESTILOS FRECUENTES</h5>", unsafe_allow_html=True)
        mis_regs = mis_regs.merge(db['estilos'], on='codestilo', how='left')
        col_desc = 'descripcion' if 'descripcion' in mis_regs.columns and 'descripcion_x' in mis_regs.columns else 'descripcion_x'
        if col_desc not in mis_regs.columns: col_desc = 'descripcion' 
        
        conteo = mis_regs[col_desc].value_counts()
        cols = st.columns(len(conteo))
        
        for (estilo, cantidad), col in zip(conteo.items(), cols):
            with col:
                st.markdown(f"""
                <div style="background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 10px; text-align: center; height: 100%;">
                    <div style="font-size: 11px; color: #aaa; text-transform: uppercase; margin-bottom: 5px;">{estilo}</div>
                    <div style="font-size: 24px; font-weight: bold; color: white; line-height: 1;">{cantidad}</div>
                    <div style="font-size: 10px; color: #666;">carreras</div>
                </div>""", unsafe_allow_html=True)
    
    st.divider()

    # =================================================================
    # 3. BOTONERA PRINCIPAL (LÓGICA POR ROL)
    # =================================================================
    
    # --- ROL NADADOR (N) ---
    if st.session_state.role == "N":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⏱️ Entrenamientos", type="primary", use_container_width=True, key="btn_train_N"): 
                st.switch_page("pages/5_entrenamientos.py")
        with c2:
            if st.button("🏅 Mi Categoría", type="primary", use_container_width=True, key="btn_cat_N"): 
                st.switch_page("pages/6_mi_categoria.py")
        
        c3, c4 = st.columns(2)
        with c3:
            if st.button("📝 Rutinas", type="primary", use_container_width=True, key="btn_rut_N"):
                st.switch_page("pages/8_rutinas.py")
        with c4:
            if st.button("📅 Agenda", type="primary", use_container_width=True, key="btn_ag_N"):
                st.switch_page("pages/7_agenda.py")

    # --- ROL MAESTRO (M) ---
    else:
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("🗃️ Fichero", use_container_width=True, key="btn_bd_M"): 
                st.session_state.ver_nadador_especifico = None
                st.switch_page("pages/2_visualizar_datos.py")
        with c2: 
            if st.button("🏆 Ver Ranking", use_container_width=True, key="btn_rk_M"): 
                st.switch_page("pages/4_ranking.py")
        
        c3, c4 = st.columns(2)
        with c3:
            if st.button("⏱️ Entrenamientos", type="primary", use_container_width=True, key="btn_train_M"): 
                st.switch_page("pages/5_entrenamientos.py")
        with c4:
            if st.button("🏅 Mi Categoría", type="primary", use_container_width=True, key="btn_cat_M"): 
                st.switch_page("pages/6_mi_categoria.py")

        c5, c6 = st.columns(2)
        with c5:
            if st.button("📝 Rutinas", type="primary", use_container_width=True, key="btn_rut_M"):
                st.switch_page("pages/8_rutinas.py")
        with c6:
            if st.button("📅 Agenda", type="primary", use_container_width=True, key="btn_ag_M"):
                st.switch_page("pages/7_agenda.py")

        if st.button("🏊‍♂️ Simulador Postas", use_container_width=True, key="btn_sim_M"): 
            st.switch_page("pages/3_simulador.py")

    st.write("")

    # // 2️⃣ Estadísticas del club
    st.markdown("<h5 style='text-align: center; color: #888; margin-top: 20px;'>ESTADÍSTICAS DEL CLUB</h5>", unsafe_allow_html=True)
    
    total_nadadores = len(db['nadadores'])
    total_pruebas_reg = len(df_t) + len(df_r)

    st.markdown(f"""
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: #262730; border-top: 3px solid #E30613; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            <div style="font-size: 11px; color: #aaa; text-transform: uppercase;">Nadadores</div>
            <div style="font-size: 28px; font-weight: 800; color: white;">{total_nadadores}</div>
        </div>
        <div style="flex: 1; background-color: #262730; border-top: 3px solid #E30613; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            <div style="font-size: 11px; color: #aaa; text-transform: uppercase;">Pruebas Registradas</div>
            <div style="font-size: 28px; font-weight: 800; color: white;">{total_pruebas_reg}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    t_oro = len(df_t[df_t['posicion']==1]) + len(df_r[df_r['posicion']==1])
    t_plata = len(df_t[df_t['posicion']==2]) + len(df_r[df_r['posicion']==2])
    t_bronce = len(df_t[df_t['posicion']==3]) + len(df_r[df_r['posicion']==3])
    total_med = t_oro + t_plata + t_bronce

    st.markdown(f"""
    <div style="background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; padding: 12px; margin-bottom: 25px;">
        <div style="text-align:center; font-size:11px; color:#aaa; margin-bottom:8px; font-weight:bold;">MEDALLERO HISTÓRICO</div>
        <div style="display: flex; justify-content: space-between; gap: 2px;">
            <div style="flex:1; text-align:center;"><div style="font-size:22px; color:#FFD700;">🥇 {t_oro}</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#C0C0C0;">🥈 {t_plata}</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#CD7F32;">🥉 {t_bronce}</div></div>
            <div style="flex:1; text-align:center; border-left:1px solid #333;"><div style="font-size:22px; color:#fff;">★ {total_med}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 5. GRÁFICOS
    df_n = db['nadadores'].copy()
    df_n['Anio'] = pd.to_datetime(df_n['fechanac'], errors='coerce').dt.year
    df_n['Categoria'] = df_n['Anio'].apply(calcular_categoria_grafico)
    colors = alt.Scale(domain=['M', 'F'], range=['#1f77b4', '#FF69B4'])
    
    t_c, t_g = st.tabs(["Categorías Master", "Género"])
    with t_c:
        orden = ["Juvenil", "PRE", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K+"]
        st.altair_chart(alt.Chart(df_n).mark_bar(cornerRadius=3).encode(x=alt.X('Categoria', sort=orden, title=None), y=alt.Y('count()', title=None), color=alt.Color('codgenero', legend=None, scale=colors)).properties(height=200), use_container_width=True)
    with t_g:
        base = alt.Chart(df_n).encode(theta=alt.Theta("count()", stack=True))
        st.altair_chart((base.mark_arc(outerRadius=80, innerRadius=50).encode(color=alt.Color("codgenero", scale=colors, legend=None)) + base.mark_text(radius=100).encode(text="count()", order=alt.Order("codgenero"), color=alt.value("white"))), use_container_width=True)

    # --- 6. GESTIÓN (Perfil M) ---
    if st.session_state.role == "M":
        st.write(""); st.write("")
        label_btn = "⚙️ CARGAR COMPETENCIAS" if not st.session_state.admin_unlocked else "🔒 BLOQUEAR GESTIÓN"
        
        if st.button(label_btn, use_container_width=True, key="btn_lock_toggle_m"):
            if not st.session_state.admin_unlocked:
                st.session_state.show_login_form = not st.session_state.show_login_form
            else:
                st.session_state.admin_unlocked = False
                st.rerun()

        if st.session_state.show_login_form and not st.session_state.admin_unlocked:
            with st.form("admin_login_form"):
                st.write("**Acceso Profesor**")
                st.text_input("Usuario", key="u_in")
                st.text_input("Contraseña", type="password", key="p_in")
                st.form_submit_button("Desbloquear", on_click=intentar_desbloqueo)
        
        if st.session_state.admin_unlocked:
            st.success("🔓 Gestión Habilitada")
            if st.button("⚙️ IR AL PANEL DE CARGA", type="primary", use_container_width=True):
                st.switch_page("pages/1_cargar_datos.py")
