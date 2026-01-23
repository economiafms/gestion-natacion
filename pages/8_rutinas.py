import streamlit as st

# ==========================================
# 1. CONFIGURACIÓN Y DATOS
# ==========================================

# AQUI: Pega el contenido exacto de tu sesión TEST dentro de las comillas
PLANTILLA_TEST = """
OBJETIVO: EVALUACIÓN MENSUAL
Ec: 400m (200m crol + 200m estilos)
T: Test de 30 minutos o Test de 2000m (según planificación)
Vuelta a la calma: 200m suaves
"""

# Lista simulada de sesiones (esto vendría de tu base de datos o archivos)
# Nota cómo el TEST está mezclado al principio para probar el ordenamiento.
if 'db_sesiones' not in st.session_state:
    st.session_state['db_sesiones'] = [
        {"id": 1, "titulo": "TEST DE VELOCIDAD", "contenido": PLANTILLA_TEST},
        {"id": 2, "titulo": "Lunes Aeróbico", "contenido": "8x400m F2"},
        {"id": 3, "titulo": "Miércoles Potencia", "contenido": "10x50m F1"},
        {"id": 4, "titulo": "Viernes Técnica", "contenido": "Drills y Corrección"}
    ]

# ==========================================
# 2. FUNCIÓN: GLOSARIO DE REFERENCIAS
# ==========================================
def mostrar_referencias():
    """Muestra el glosario en un desplegable consultivo."""
    with st.expander("📖 Glosario de Referencias y Abreviaturas (Clic para consultar)"):
        st.markdown("""
        | Abrev. | Significado | Detalle / Intensidad |
        | :--- | :--- | :--- |
        | **T** | Tolerancia | Intensidad alta 100 – 110% |
        | **VC** | Velocidad Corta | Máxima velocidad |
        | **VS** | Velocidad Sostenida | Mantener velocidad alta |
        | **Prog.** | Progresivo | De menor a mayor |
        | **Reg** | Regresivo | De mayor a menor |
        | **F1** | Vo2 | Intensidad 100% |
        | **F2** | Super Aeróbico | Intensidad 80-90% |
        | **F3** | Sub Aeróbico | Intensidad 70% |
        | **Ec** | Entrada en Calor | Nado inicial |
        | **EcT** | Ec Tensor | Bíceps/Tríceps/Dorsales/etc. |
        | **EcM** | Ec Movilidad | Fuera del agua |
        | **Act** | Activación | Piernas / Brazos / Core |
        | **m** | Metros | Distancia |
        | **p** | Pausa estática | Descanso quieto |
        | **p act** | Pausa Activa | Descanso en movimiento |
        | **D/** | Dentro del tiempo | Intervalo fijo |
        | **C/** | Con tiempo | Pausa fija |
        | **Pat Ph** | Patada Pos. Hidro. | Cuerpo alineado |
        | **B** | Brazada | C/E/P/M |
        | **PB** | Pull Brazada | Uso de pullboy |
        | **CT** | Corrección Técnica | Foco técnico |
        """)
        st.info("💡 Consulta esta tabla si tienes dudas con la nomenclatura de la sesión.")

# ==========================================
# 3. INTERFAZ: CARGA DE SESIONES (Vista Entrenador)
# ==========================================
def vista_carga_entrenador():
    st.subheader("🛠️ Carga de Sesiones (Vista Entrenador)")
    
    col_accion, col_dummy = st.columns([1, 2])
    with col_accion:
        # BOTÓN MAGICO: Si se presiona, precarga el contenido del TEST
        if st.button("➕ Cargar Plantilla TEST"):
            st.session_state['form_titulo'] = "TEST MENSUAL"
            st.session_state['form_contenido'] = PLANTILLA_TEST

    # Formulario de carga (editable)
    with st.form("form_crear_sesion"):
        titulo = st.text_input("Nombre de la Sesión", value=st.session_state.get('form_titulo', ''))
        contenido = st.text_area("Detalle de la Rutina", value=st.session_state.get('form_contenido', ''), height=150)
        
        submitted = st.form_submit_button("Guardar Sesión")
        if submitted:
            nuevo_id = len(st.session_state['db_sesiones']) + 1
            st.session_state['db_sesiones'].append({"id": nuevo_id, "titulo": titulo, "contenido": contenido})
            st.success("✅ Sesión guardada correctamente")
            # Limpiar variables temporales
            if 'form_titulo' in st.session_state: del st.session_state['form_titulo']
            if 'form_contenido' in st.session_state: del st.session_state['form_contenido']
            st.rerun()

# ==========================================
# 4. INTERFAZ: VISTA NADADOR (Grilla del Mes)
# ==========================================
def vista_nadador():
    st.divider()
    st.subheader("🏊 Rutinas del Mes (Vista Nadador)")

    lista_sesiones = st.session_state['db_sesiones']

    # --- LÓGICA DE ORDENAMIENTO ---
    # Filtramos las sesiones que contienen "TEST" en el título (mayúsculas o minúsculas)
    rutinas_normales = [s for s in lista_sesiones if "TEST" not in s['titulo'].upper()]
    rutinas_test = [s for s in lista_sesiones if "TEST" in s['titulo'].upper()]
    
    # Unimos: primero las normales, al final el TEST
    lista_ordenada = rutinas_normales + rutinas_test

    # --- LÓGICA DE BOTONES LADO A LADO ---
    # Definimos cuántas columnas queremos (ej. 3 botones por fila)
    columnas_por_fila = 3
    cols = st.columns(columnas_por_fila)

    seleccionada = None

    for index, sesion in enumerate(lista_ordenada):
        # Calculamos en qué columna cae este botón (0, 1 o 2)
        col_idx = index % columnas_por_fila
        
        with cols[col_idx]:
            # Usamos use_container_width=True para que el botón ocupe todo el ancho de la columna
            if st.button(f"📄 {sesion['titulo']}", key=f"btn_{sesion['id']}", use_container_width=True):
                seleccionada = sesion

    # --- MOSTRAR DETALLE Y GLOSARIO ---
    if seleccionada:
        st.markdown(f"### 📌 Detalle: {seleccionada['titulo']}")
        st.code(seleccionada['contenido'], language="text")
        
        # Aquí insertamos el GLOSARIO CONSULTIVO
        mostrar_referencias()

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.title("Gestión Equipo de Natación")
    
    # Tabs para separar la simulación de carga y la vista del usuario
    tab1, tab2 = st.tabs(["Vista Nadador", "Carga (Admin)"])
    
    with tab1:
        vista_nadador()
    
    with tab2:
        vista_carga_entrenador()

if __name__ == "__main__":
    main()
