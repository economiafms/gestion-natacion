import streamlit as st
import datos
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import time
import random

# --- NUEVAS IMPORTACIONES PARA GENERAR WORD ---
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import html

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Sesiones de Entrenamiento", layout="centered")

# ==========================================
# 2. SEGURIDAD Y SESIÓN
# ==========================================
if "role" not in st.session_state or not st.session_state.role:
    st.switch_page("index.py")

rol = st.session_state.role
mi_id = st.session_state.user_id
mi_nombre = st.session_state.user_name

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 4. FUNCIONES AUXILIARES Y GLOSARIO
# ==========================================

# --- NUEVA FUNCIÓN: GENERAR WORD 1/6 DE HOJA ---
def generar_word_sexto_hoja(entrenamiento_texto, fecha, titulo):
    doc = Document()
    
    # Configuración de márgenes para 1/6 de hoja (A4 aprox)
    # 4.5 pulgadas de margen izquierdo desplaza el texto a la derecha
    # 7.5 pulgadas de margen inferior asegura que no baje de la parte superior
    section = doc.sections[0]
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(7.5) 
    section.left_margin = Inches(4.5)   
    section.right_margin = Inches(0.5)
    
    # Título de la sesión
    p_titulo = doc.add_paragraph()
    run_t = p_titulo.add_run(f"{titulo} - {fecha}")
    run_t.bold = True
    run_t.font.size = Pt(10)
    p_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Contenido del entrenamiento
    p_cont = doc.add_paragraph()
    # Limpiamos posibles saltos de línea excesivos
    texto_limpio = str(entrenamiento_texto).replace('\n\n', '\n')
    run_c = p_cont.add_run(texto_limpio)
    run_c.font.size = Pt(8.5) # Fuente pequeña para que entre en el recorte
    p_cont.alignment = WD_ALIGN_PARAGRAPH.LEFT

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def obtener_nombre_mes(n):
    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    try:
        return meses[int(n)]
    except:
        return "Desconocido"

def get_periodo_mas_cercano(fecha_actual, registros_disponibles):
    """
    Calcula el período (año, mes) más cercano a la fecha actual basándose en los registros disponibles.
    Prioridad: 1. Actual, 2. Más cercano pasado, 3. Más cercano futuro.
    registros_disponibles: lista de tuplas [(anio, mes), ...]
    """
    if not registros_disponibles:
        return fecha_actual.year, fecha_actual.month

    # Convertir a objetos datetime para comparación (día 1)
    target = datetime(fecha_actual.year, fecha_actual.month, 1)
    fechas_disp = []
    
    # Filtrar y validar fechas
    for y, m in registros_disponibles:
        try:
            fechas_disp.append(datetime(int(y), int(m), 1))
        except:
            continue
            
    if not fechas_disp:
        return fecha_actual.year, fecha_actual.month

    # 1. Coincidencia exacta
    if target in fechas_disp:
        return target.year, target.month

    # 2. Buscar hacia atrás (Max del pasado)
    pasado = [d for d in fechas_disp if d < target]
    if pasado:
        mejor_pasado = max(pasado)
        return mejor_pasado.year, mejor_pasado.month

    # 3. Buscar hacia adelante (Min del futuro)
    futuro = [d for d in fechas_disp if d > target]
    if futuro:
        mejor_futuro = min(futuro)
        return mejor_futuro.year, mejor_futuro.month

    return fecha_actual.year, fecha_actual.month

GLOSARIO = [
    ("Intensidades", [
        ("T", "Tolerancia: intensidad alta 100–110%"),
        ("VC", "Velocidad corta: máxima velocidad"),
        ("VS", "Velocidad sostenida: mantener velocidad alta"),
        ("F1", "Vo2: intensidad 100%"),
        ("F2", "Súper aeróbico: 80–90%"),
        ("F3", "Sub aeróbico: 70%"),
        ("Prog.", "Progresivo: de menor a mayor"),
        ("Reg", "Regresivo: de mayor a menor"),
    ]),
    ("Activación y entrada en calor", [
        ("Ec", "Entrada en calor: nado suave inicial"),
        ("EcT", "Ec tensor: bíceps, tríceps, dorsales, hombros, pecho, antebrazos"),
        ("EcM", "Ec movilidad, fuera del agua: brazos, cintura, piernas, tobillos, cuello"),
        ("Act", "Activación, fuera del agua: piernas, brazos, core"),
    ]),
    ("Técnica y estilos", [
        ("B", "Brazada: C (crol), E (espalda), P (pecho), M (mariposa)"),
        ("Pat Ph", "Patada en posición hidrodinámica"),
        ("Pat Tabla", "Patada con tabla"),
        ("PB", "Pull brazada: con pullboy (c/e/p/m)"),
        ("CT", "Corrección técnica"),
    ]),
    ("Otros", [
        ("m", "Metros"),
        ("p", "Pausa estática"),
        ("p act", "Pausa activa"),
        ("D/", "Dentro del tiempo"),
        ("C/", "Con tiempo de pausa"),
    ]),
]


def mostrar_referencias():
    """Glosario de siglas de las rutinas, agrupado en tarjetas."""
    with st.expander("📖 Glosario de referencias"):
        bloques = []
        for titulo, items in GLOSARIO:
            filas = "".join(f'<div class="rut-glo-f"><b>{html.escape(s)}</b><span>{html.escape(d)}</span></div>'
                            for s, d in items)
            bloques.append(f'<div class="rut-glo-b"><div class="rut-glo-t">{html.escape(titulo)}</div>{filas}</div>')
        st.markdown(f'<div class="rut-glo">{"".join(bloques)}</div>', unsafe_allow_html=True)

# --- MANEJO DE RETRYS PARA API ---
def actualizar_con_retry(worksheet, data, max_retries=5):
    for i in range(max_retries):
        try:
            conn.update(worksheet=worksheet, data=data)
            return True, None 
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                wait_time = (2 ** i) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue 
            else:
                return False, e
    return False, "Tiempo de espera agotado (API ocupada)."

# --- LECTURA DE DATOS (CON CACHÉ) ---
def cargar_datos_rutinas_view():
    try:
        try:
            df_rut = datos.leer("Rutinas").copy()
        except:
            df_rut = pd.DataFrame(columns=["id_rutina", "anio_rutina", "mes_rutina", "nro_sesion", "texto_rutina"])
        
        try:
            df_seg = datos.leer("Rutinas_Seguimiento").copy()
        except:
            df_seg = pd.DataFrame(columns=["id_rutina", "codnadador", "fecha_realizada"])

        try:
            df_nad = datos.leer("Nadadores").copy()
        except:
            df_nad = pd.DataFrame(columns=["codnadador", "nombre", "apellido"])
            
        # Normalización de tipos
        if not df_rut.empty:
            df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
            df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)
            
        if not df_seg.empty:
            df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)

        if not df_nad.empty:
             df_nad['codnadador'] = pd.to_numeric(df_nad['codnadador'], errors='coerce').fillna(0).astype(int)
            
        return df_rut, df_seg, df_nad
    except Exception as e:
        st.error(f"Error visual al cargar datos: {e}")
        return None, None, None

def leer_dataset_fresco(worksheet):
    try:
        df = conn.read(worksheet=worksheet, ttl=0).copy()
        return df
    except Exception as e:
        st.error(f"Error de conexión fresca con {worksheet}: {e}")
        return None

def calcular_proxima_sesion(df, anio, mes):
    if df is None or df.empty: return 1
    filtro = df[(df['anio_rutina'] == anio) & (df['mes_rutina'] == mes)]
    if filtro.empty: return 1
    return int(filtro['nro_sesion'].max()) + 1

# ==========================================
# 5. FUNCIONES DE ESCRITURA
# ==========================================

def guardar_seguimiento(id_rutina, id_nadador):
    df_seg = leer_dataset_fresco("Rutinas_Seguimiento")
    if df_seg is None: return False 
    
    if not df_seg.empty:
        df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)

    existe = df_seg[(df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador)]
    
    if existe.empty:
        hora_arg = datetime.now() - timedelta(hours=3)
        nuevo_registro = pd.DataFrame([{
            "id_rutina": id_rutina,
            "codnadador": id_nadador,
            "fecha_realizada": hora_arg.strftime("%Y-%m-%d %H:%M:%S")
        }])
        df_final = pd.concat([df_seg, nuevo_registro], ignore_index=True)
        
        exito, error = actualizar_con_retry("Rutinas_Seguimiento", df_final)
        if exito:
            datos.invalidar("Rutinas_Seguimiento")
            return True
        else:
            st.error(f"Error al guardar: {error}")
            return False
    return False

def borrar_seguimiento(id_rutina, id_nadador):
    df_seg = leer_dataset_fresco("Rutinas_Seguimiento")
    if df_seg is None: return False
    
    if not df_seg.empty:
        df_seg['codnadador'] = pd.to_numeric(df_seg['codnadador'], errors='coerce').fillna(0).astype(int)

    df_final = df_seg[~((df_seg['id_rutina'] == id_rutina) & (df_seg['codnadador'] == id_nadador))]
    
    exito, error = actualizar_con_retry("Rutinas_Seguimiento", df_final)
    if exito:
        datos.invalidar("Rutinas_Seguimiento")
        return True
    else:
        st.error(f"Error al borrar: {error}")
        return False

def eliminar_sesion_admin(id_rutina):
    df_rut = leer_dataset_fresco("Rutinas")
    if df_rut is None: return "❌ Error de conexión."
    
    rutina_a_borrar = df_rut[df_rut['id_rutina'] == id_rutina]
    
    if rutina_a_borrar.empty:
        return "⚠️ La sesión no existe."
    
    r_anio = rutina_a_borrar.iloc[0]['anio_rutina']
    r_mes = rutina_a_borrar.iloc[0]['mes_rutina']
    r_sesion = rutina_a_borrar.iloc[0]['nro_sesion']
    
    rutinas_mes = df_rut[(df_rut['anio_rutina'] == r_anio) & (df_rut['mes_rutina'] == r_mes)]
    max_sesion = rutinas_mes['nro_sesion'].max()
    
    if r_sesion < max_sesion:
        return f"🚫 Solo se permite eliminar la última sesión del mes (Sesión {max_sesion})."

    df_rut_final = df_rut[df_rut['id_rutina'] != id_rutina]
    
    exito, error = actualizar_con_retry("Rutinas", df_rut_final)
    
    if exito:
        datos.invalidar("Rutinas")
        return "🗑️ Sesión eliminada correctamente."
    else:
        return f"❌ Error al eliminar: {error}"

def guardar_sesion_admin(anio, mes, sesion, texto):
    df_rut = leer_dataset_fresco("Rutinas")
    if df_rut is None: return "❌ Error CRÍTICO de conexión."

    if not df_rut.empty:
        df_rut['anio_rutina'] = pd.to_numeric(df_rut['anio_rutina'], errors='coerce').fillna(0).astype(int)
        df_rut['mes_rutina'] = pd.to_numeric(df_rut['mes_rutina'], errors='coerce').fillna(0).astype(int)
        df_rut['nro_sesion'] = pd.to_numeric(df_rut['nro_sesion'], errors='coerce').fillna(0).astype(int)

    nuevo_id = f"{anio}-{mes:02d}-S{sesion:02d}"
    mask = df_rut['id_rutina'] == nuevo_id
    
    nueva_fila = {
        "id_rutina": nuevo_id,
        "anio_rutina": int(anio),
        "mes_rutina": int(mes),
        "nro_sesion": int(sesion),
        "texto_rutina": texto
    }
    
    if df_rut[mask].empty:
        df_rut = pd.concat([df_rut, pd.DataFrame([nueva_fila])], ignore_index=True)
        msg = "✅ Sesión creada correctamente."
    else:
        df_rut.loc[mask, "texto_rutina"] = texto
        msg = "✅ Sesión actualizada correctamente."
        
    exito, error = actualizar_con_retry("Rutinas", df_rut)
    if exito:
        datos.invalidar("Rutinas")
    return msg if exito else f"❌ Error al escribir: {error}"

def activar_calculo_auto():
    st.session_state.trigger_calculo = True

# ==========================================
# 6. COMPONENTES VISUALES
# ==========================================

CSS_RUTINAS = """<style>
/* Tarjeta de sesión */
[class*="st-key-rut_card_"] {
  position: relative; overflow: hidden; gap: 10px !important; padding: 14px 14px 12px; margin-bottom: 4px;
  border-radius: 16px; background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
  border: 1px solid rgba(255,255,255,0.08);
}
[class*="st-key-rut_card_"]::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: rgba(255,255,255,0.18); }
[class*="st-key-rut_card_prox_"] { border-color: rgba(227,6,19,0.40);
  background: linear-gradient(160deg, rgba(227,6,19,0.14), rgba(227,6,19,0.02)); box-shadow: 0 8px 22px rgba(0,0,0,0.28); }
[class*="st-key-rut_card_prox_"]::before { background: linear-gradient(180deg, #E30613, #FF6A72); }
[class*="st-key-rut_card_done_"]::before { background: linear-gradient(180deg, #2E7D32, #66BB6A); }
.rut-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rut-head .t { font-size: 17px; font-weight: 800; color: #fff; }
.rut-head .s { font-size: 12px; color: rgba(255,255,255,0.55); margin-left: auto; }
.rut-pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 10px; font-weight: 800; letter-spacing: .8px; }
.rut-pill.prox { background: rgba(227,6,19,0.18); color: #FF6B72; border: 1px solid rgba(227,6,19,0.5); }
.rut-pill.pend { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.15); }
.rut-pill.ok   { background: rgba(76,175,80,0.16); color: #7EE083; border: 1px solid rgba(76,175,80,0.5); }
/* Texto de la rutina */
[class*="st-key-rut_txt_"] { padding: 10px 12px; border-radius: 12px; background: rgba(0,0,0,0.22);
  border: 1px solid rgba(255,255,255,0.05); }
[class*="st-key-rut_txt_"] p, [class*="st-key-rut_txt_"] li { font-size: 14.5px; line-height: 1.55; color: rgba(255,255,255,0.88); }
[class*="st-key-rut_txt_done_"] p, [class*="st-key-rut_txt_done_"] li { color: rgba(255,255,255,0.55); }
/* Acciones: botones del mismo ancho */
[class*="st-key-rut_acc_"] { gap: 8px !important; flex-wrap: nowrap !important; }
[class*="st-key-rut_acc_"] > div { flex: 1 1 0 !important; min-width: 0 !important; width: auto !important; }
[class*="st-key-rut_acc_"] button { width: 100%; border-radius: 12px; }
/* Historial: filas por sesión */
.rut-row { display: flex; align-items: center; gap: 10px; padding: 9px 12px; margin-bottom: 6px; border-radius: 12px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); }
.rut-row .i { width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; flex: 0 0 auto;
  font-size: 12px; font-weight: 900; background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.6); }
.rut-row.ok .i { background: rgba(76,175,80,0.22); color: #7EE083; }
.rut-row .n { flex: 1; font-size: 14px; font-weight: 700; color: #fff; }
.rut-row .f { font-size: 12px; color: rgba(255,255,255,0.55); min-width: 40px; text-align: right; }
/* Glosario */
.rut-glo { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 10px; }
.rut-glo-b { padding: 10px 12px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); }
.rut-glo-t { font-size: 10.5px; font-weight: 800; letter-spacing: 1.4px; text-transform: uppercase; color: #FF6B72; margin-bottom: 6px; }
.rut-glo-f { display: flex; gap: 8px; font-size: 13px; padding: 3px 0; color: rgba(255,255,255,0.75); }
.rut-glo-f b { flex: 0 0 64px; color: #fff; }
/* Mes completo */
.rut-celeb { text-align: center; padding: 18px 16px; margin-bottom: 14px; border-radius: 18px;
  background: linear-gradient(135deg, rgba(227,6,19,0.35), rgba(0,0,0,0.6)); border: 1px solid rgba(255,215,0,0.45);
  box-shadow: 0 8px 24px rgba(227,6,19,0.25); }
.rut-celeb .e { font-size: 38px; }
.rut-celeb .t { font-size: 20px; font-weight: 900; color: #fff; text-transform: uppercase; letter-spacing: .5px; }
.rut-celeb .s { font-size: 13.5px; color: rgba(255,255,255,0.8); margin-top: 4px; }
</style>"""


def sesiones_del_mes(df_rut, anio, mes):
    return df_rut[(df_rut['anio_rutina'] == anio) & (df_rut['mes_rutina'] == mes)].sort_values('nro_sesion')


def fecha_realizada(df_seg, r_id, id_nadador):
    """Fecha (dd/mm) en que el nadador marcó la sesión, o None si no la hizo."""
    check = df_seg[(df_seg['id_rutina'] == r_id) & (df_seg['codnadador'] == id_nadador)]
    if check.empty:
        return None
    f = pd.to_datetime(check.iloc[0]['fecha_realizada'], errors='coerce')
    return f.strftime("%d/%m") if pd.notna(f) else "-"


def tarjeta_progreso(completadas, total, anio, mes):
    """Asistencia del mes: porcentaje, barra y mensaje. Celebra el 100% (solo nadador)."""
    porcentaje = int(completadas / total * 100) if total else 0
    nombre_mes = obtener_nombre_mes(mes)
    if st.session_state.role == "N" and total and porcentaje == 100:
        celeb_key = f"celeb_{anio}_{mes}"
        if celeb_key not in st.session_state:
            st.balloons()
            st.session_state[celeb_key] = True
        st.markdown(f"""<div class="rut-celeb"><div class="e">🏆</div><div class="t">¡Mes completo!</div>
<div class="s">Lograste el 100% de asistencia en {nombre_mes}. Sumás constancia, sumás mejora.</div></div>""",
                    unsafe_allow_html=True)
    faltan = max(total - completadas, 0)
    if completadas == 0: msg = "La primera sesión es la más importante. Hoy es el día."
    elif porcentaje < 50: msg = f"Buen arranque. Faltan {faltan} sesiones, a sumar."
    elif porcentaje < 100: msg = f"Pasaste la mitad. Solo {faltan} más para cerrar el mes."
    else: msg = "Mes completo. Constancia de campeón."
    st.markdown(f"""<div class="nob-goal">
<div class="nob-goal-top"><b>Asistencia · {nombre_mes} {anio}</b><span>{completadas} de {total} sesiones</span></div>
<div class="nob-next-days" style="margin:0 0 10px;">{porcentaje}<small>%</small></div>
<div class="nob-bar"><div style="width:{max(0, min(100, porcentaje))}%"></div></div>
<div class="nob-goal-msg">{msg}</div>
</div>""", unsafe_allow_html=True)


def render_tarjeta_individual(row, df_seg, key_suffix, total, es_proxima=False):
    r_id = row['id_rutina']
    r_sesion = int(row['nro_sesion'])
    r_texto = row['texto_rutina']
    r_anio = row.get('anio_rutina', '')
    r_mes = row.get('mes_rutina', '')
    fecha = fecha_realizada(df_seg, r_id, mi_id)
    hecha = fecha is not None
    k = f"{r_id}_{key_suffix}"

    tipo = "done" if hecha else ("prox" if es_proxima else "pend")
    if hecha:
        pill = f'<span class="rut-pill ok">NADADA · {fecha}</span>'
    elif es_proxima:
        pill = '<span class="rut-pill prox">PRÓXIMA</span>'
    else:
        pill = '<span class="rut-pill pend">PENDIENTE</span>'

    with st.container(key=f"rut_card_{tipo}_{k}"):
        st.markdown(f'<div class="rut-head">{pill}<span class="t">Sesión {r_sesion}</span>'
                    f'<span class="s">de {total}</span></div>', unsafe_allow_html=True)
        with st.container(key=f"rut_txt_{'done_' if hecha else ''}{k}"):
            st.markdown(r_texto)
        doc_buffer = generar_word_sexto_hoja(r_texto, f"{int(r_mes):02d}/{r_anio}", f"SESIÓN {r_sesion}")
        with st.container(key=f"rut_acc_{k}", horizontal=True):
            if hecha:
                if st.button("Desmarcar", key=f"un_{k}", icon=":material/undo:", use_container_width=True):
                    with st.spinner("Desmarcando..."):
                        borrar_seguimiento(r_id, mi_id)
                    st.rerun()
            else:
                if st.button("Día ganado", key=f"do_{k}", type="primary" if es_proxima else "secondary",
                             icon=":material/check_circle:", use_container_width=True):
                    with st.spinner("Guardando..."):
                        if guardar_seguimiento(r_id, mi_id):
                            st.toast(f"¡Excelente! Sesión {r_sesion} registrada.", icon="🏆")
                    st.rerun()
            st.download_button("Imprimir", data=doc_buffer, icon=":material/print:", use_container_width=True,
                               file_name=f"Rutina_S{r_sesion}_{r_mes}_{r_anio}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               key=f"dl_{k}")


def render_feed_activo(df_rut, df_seg, anio_ver, mes_ver, key_suffix=""):
    rutinas = sesiones_del_mes(df_rut, anio_ver, mes_ver)
    if rutinas.empty:
        st.info(f"No hay sesiones cargadas para {obtener_nombre_mes(mes_ver)} {anio_ver}.")
        return

    total = len(rutinas)
    hechas = rutinas['id_rutina'].map(lambda r: fecha_realizada(df_seg, r, mi_id) is not None)
    pendientes = rutinas[~hechas]
    completadas = rutinas[hechas]

    tarjeta_progreso(len(completadas), total, anio_ver, mes_ver)

    if not pendientes.empty:
        seccion("Próxima sesión")
        render_tarjeta_individual(pendientes.iloc[0], df_seg, key_suffix, total, es_proxima=True)
        if len(pendientes) > 1:
            seccion(f"Después ({len(pendientes) - 1})")
            for _, row in pendientes.iloc[1:].iterrows():
                render_tarjeta_individual(row, df_seg, key_suffix, total)

    if not completadas.empty:
        st.write("")
        with st.expander(f"✅ Sesiones completadas ({len(completadas)})", expanded=pendientes.empty):
            for _, row in completadas.iloc[::-1].iterrows():
                render_tarjeta_individual(row, df_seg, key_suffix, total)

    st.write("")
    mostrar_referencias()


def render_historial_compacto(df_rut, df_seg, anio, mes, id_usuario_objetivo):
    rutinas = sesiones_del_mes(df_rut, anio, mes)
    if rutinas.empty:
        st.info("No hay planificación cargada para este mes.")
        return

    filas, completadas = [], 0
    for _, r in rutinas.iterrows():
        nro = int(r["nro_sesion"])
        fecha = fecha_realizada(df_seg, r['id_rutina'], id_usuario_objetivo)
        if fecha is not None:
            completadas += 1
            filas.append(f'<div class="rut-row ok"><span class="i">✓</span><span class="n">Sesión {nro}</span>'
                         f'<span class="rut-pill ok">NADADA</span><span class="f">{fecha}</span></div>')
        else:
            filas.append(f'<div class="rut-row"><span class="i">{nro}</span><span class="n">Sesión {nro}</span>'
                         f'<span class="rut-pill pend">PENDIENTE</span><span class="f">–</span></div>')

    tarjeta_progreso(completadas, len(rutinas), anio, mes)
    seccion("Detalle de actividad")
    st.markdown("".join(filas), unsafe_allow_html=True)


def selector_periodo(df_rut, def_y, def_m, prefijo, contenedor_a=None, contenedor_m=None, anios_extra=()):
    """Año y mes con flechas (como en Categorías). Devuelve (año, mes) o (año, None) si no hay meses."""
    anios = sorted(set(df_rut['anio_rutina'].unique().tolist()) | set(anios_extra), reverse=True) or [datetime.now().year]
    anio = select_flechas("Año", anios, f"{prefijo}_a", index=anios.index(def_y) if def_y in anios else 0,
                          contenedor=contenedor_a)
    meses = sorted(df_rut[df_rut['anio_rutina'] == anio]['mes_rutina'].unique().tolist())
    if not meses:
        (contenedor_m or st).warning("Sin datos")
        return anio, None
    # Mes por defecto: el elegido si existe en ese año; si no, el más cercano
    if def_m in meses:
        idx = meses.index(def_m)
    else:
        idx = min(range(len(meses)), key=lambda i: abs(meses[i] - def_m))
    nombres = [obtener_nombre_mes(m) for m in meses]
    nombre = select_flechas("Mes", nombres, f"{prefijo}_m", index=idx, contenedor=contenedor_m)
    return anio, meses[nombres.index(nombre)]

# ==========================================

# 7. LÓGICA PRINCIPAL (MAIN)
# ==========================================

df_rutinas, df_seguimiento, df_nadadores = cargar_datos_rutinas_view()

# --- INTERFAZ DE USUARIO ---
from nob_ui import hero, seccion, select_flechas
hero("Sesiones de Entrenamiento", "📝")
st.markdown(CSS_RUTINAS, unsafe_allow_html=True)

# Nadadores inactivos (sin marcas este año ni el anterior) no ven las rutinas
import actividad
if actividad.usuario_inactivo():
    actividad.aviso_inactivo("Rutinas")
    st.stop()

if df_rutinas is None:
    st.error("No se pudieron cargar los datos. Verifica tu conexión.")
    st.stop()

# ==========================
# VISTA: PROFESOR (M) / ADMIN
# ==========================
if rol in ["M", "P"]:
    
    if "g_anio" not in st.session_state: st.session_state.g_anio = datetime.now().year
    if "g_mes" not in st.session_state: st.session_state.g_mes = datetime.now().month

    # Trigger de cálculo inicial
    if st.session_state.get("trigger_calculo", False) or "admin_sesion" not in st.session_state:
        if df_rutinas is not None:
            prox = calcular_proxima_sesion(df_rutinas, st.session_state.g_anio, st.session_state.g_mes)
            st.session_state.admin_sesion = min(prox, 31)
        else:
            st.session_state.admin_sesion = 1
        st.session_state.trigger_calculo = False

    # Lógica de avance manual seguro
    if st.session_state.get("forzar_avance_sesion", False):
        if "admin_sesion" in st.session_state and st.session_state.admin_sesion < 31:
             st.session_state.admin_sesion += 1
        st.session_state.forzar_avance_sesion = False

    with st.expander("⚙️ Crear o editar sesiones", expanded=False):
        
        c1, c2, c3 = st.columns([1, 1, 1])
        
        anio_actual = datetime.now().year
        anios_gest = sorted(list(set(df_rutinas['anio_rutina'].unique().tolist() + [anio_actual])), reverse=True)
        meses_indices = list(range(1, 13))
        mapa_meses = {i: obtener_nombre_mes(i) for i in meses_indices}

        with c1: 
            st.number_input("Año", min_value=2020, max_value=2030, key="g_anio", on_change=activar_calculo_auto)
        with c2: 
            st.selectbox("Mes", meses_indices, format_func=lambda x: mapa_meses[x], key="g_mes", on_change=activar_calculo_auto)
        with c3: 
            st.number_input("Nro Sesión", min_value=1, max_value=31, key="admin_sesion")
            
        id_busqueda = f"{st.session_state.g_anio}-{st.session_state.g_mes:02d}-S{st.session_state.admin_sesion:02d}"
        row_existente = df_rutinas[df_rutinas['id_rutina'] == id_busqueda]
        
        es_edicion = not row_existente.empty
        texto_previo = row_existente.iloc[0]['texto_rutina'] if es_edicion else ""
        
        estado_txt = "✏️ Editando Existente" if es_edicion else "✨ Nueva Sesión"
        st.markdown(f'<span class="rut-pill {"ok" if es_edicion else "prox"}">{estado_txt.upper()}</span> '
                    f'<span style="font-size:12px;color:rgba(255,255,255,0.5)">{id_busqueda}</span>', unsafe_allow_html=True)
        
        with st.form("form_rutina"):
            f_texto = st.text_area("Contenido", value=texto_previo, height=200, key=f"editor_texto_{id_busqueda}")
            
            if es_edicion:
                c_del, c_save = st.columns([1, 2])
                with c_del:
                    delete_btn = st.form_submit_button("🗑️ Eliminar Sesión", type="secondary")
                with c_save:
                    submitted = st.form_submit_button("💾 Actualizar Sesión", type="primary")
            else:
                submitted = st.form_submit_button("💾 Crear Sesión", type="primary")
                delete_btn = False

            if submitted:
                if f_texto.strip() == "":
                    st.error("Texto vacío.")
                else:
                    msg = guardar_sesion_admin(st.session_state.g_anio, st.session_state.g_mes, st.session_state.admin_sesion, f_texto)
                    if "Error" in msg:
                        st.error(msg)
                    else:
                        st.success(msg)
                        st.session_state.forzar_avance_sesion = True
                        time.sleep(0.5)  # pausa a propósito: deja que Google termine de escribir antes de releer
                        st.rerun()
            
            if delete_btn:
                msg = eliminar_sesion_admin(id_busqueda)
                if "Error" in msg:
                    st.error(msg)
                else:
                    st.warning(msg)
                    st.session_state.trigger_calculo = True
                    time.sleep(1)  # pausa a propósito: deja que Google termine de escribir antes de releer
                    st.rerun()

    tab_explorar, tab_seguimiento = st.tabs(["📖 Explorar Sesiones", "📊 Seguimiento Alumnos"])
    
    # --- LOGICA DE DEFAULT (PERFIL M - EXPLORAR) ---
    unique_periods_global = df_rutinas[['anio_rutina', 'mes_rutina']].drop_duplicates().values.tolist()
    def_y_ex, def_m_ex = get_periodo_mas_cercano(datetime.now(), unique_periods_global)

    with tab_explorar:
        col_v1, col_v2 = st.columns(2)
        sel_a, sel_m = selector_periodo(df_rutinas, def_y_ex, def_m_ex, "adm_v", col_v1, col_v2,
                                        anios_extra=[datetime.now().year])
        if sel_m:
            render_feed_activo(df_rutinas, df_seguimiento, sel_a, sel_m, key_suffix="admin_view")

    # --- LOGICA DE DEFAULT (PERFIL M - SEGUIMIENTO) ---
    # Usamos la misma logica global para los defaults de tiempo
    with tab_seguimiento:
        ids_con_seg = df_seguimiento['codnadador'].unique()
        df_nad_activos = df_nadadores[df_nadadores['codnadador'].isin(ids_con_seg)].copy()

        if df_nad_activos.empty:
            st.info("Aún no hay alumnos con sesiones completadas.")
        else:
            df_nad_activos['NombreCompleto'] = df_nad_activos['apellido'].astype(str).str.upper() + ", " + df_nad_activos['nombre'].astype(str)
            lista_nads = df_nad_activos[['codnadador', 'NombreCompleto']].sort_values('NombreCompleto')
            nombres_nads = lista_nads['NombreCompleto'].tolist()

            sel_nombre = select_flechas("Alumno", nombres_nads, "seg_alumno")
            sel_nad_id = lista_nads[lista_nads['NombreCompleto'] == sel_nombre]['codnadador'].values[0]
            col_s2, col_s3 = st.columns(2)
            sel_a_seg, sel_m_seg = selector_periodo(df_rutinas, def_y_ex, def_m_ex, "seg", col_s2, col_s3,
                                                    anios_extra=[datetime.now().year])
            if sel_m_seg:
                render_historial_compacto(df_rutinas, df_seguimiento, sel_a_seg, sel_m_seg, sel_nad_id)

# ==========================
# VISTA: NADADOR (N)
# ==========================
else:
    tab_curso, tab_hist = st.tabs(["📅 Mes en curso", "📜 Historial"])

    with tab_curso:
        hoy = datetime.now(timezone.utc) - timedelta(hours=3)  # hora de Argentina, como en Inicio
        render_feed_activo(df_rutinas, df_seguimiento, hoy.year, hoy.month, key_suffix="nad_curso")

    with tab_hist:
        # Por defecto: el mes con rutinas más cercano a hoy
        unique_periods_n = df_rutinas[['anio_rutina', 'mes_rutina']].drop_duplicates().values.tolist()
        def_y_n, def_m_n = get_periodo_mas_cercano(datetime.now(), unique_periods_n)
        c_h1, c_h2 = st.columns(2)
        h_anio, h_mes = selector_periodo(df_rutinas, def_y_n, def_m_n, "h", c_h1, c_h2)
        if h_mes:
            render_historial_compacto(df_rutinas, df_seguimiento, h_anio, h_mes, mi_id)
