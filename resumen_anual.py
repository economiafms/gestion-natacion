"""Resumen anual del nadador ("Mi año en el agua"): estadísticas del año e imagen para redes."""
import io
import re
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = Path(__file__).parent
FUENTES = BASE / "assets" / "fonts"
ROJO = (227, 6, 19)
ORO, PLATA, BRONCE = (255, 200, 40), (205, 212, 222), (214, 134, 72)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

FORMATOS = {"Historia (1080×1920)": (1080, 1920), "Posteo (1080×1350)": (1080, 1350)}


# ---------------------------------------------------------------- datos
def _seg(t):
    try:
        p = str(t).strip().replace(",", ".").split(":")
        return int(p[0]) * 60 + float(p[1]) if len(p) == 2 else float(p[0])
    except Exception:
        return None


METROS_RELEVO = 50   # cada nadador nada una posta de 50 m en los relevos


def _metros(dist):
    """Metros de una prueba individual ('50m', '100 m', '1500m')."""
    nums = [int(n) for n in re.findall(r"\d+", str(dist))]
    return max(nums) if nums else 0


def _fmt_seg(s):
    return f"{s:.2f}".replace(".", ",")


def _fechas(serie):
    """Fechas con formatos mezclados (con o sin hora) sin perder registros."""
    return pd.to_datetime(serie, errors='coerce', format='mixed')


def _pileta_norm(v):
    """'3', 3, 3.0 y ' 3 ' son la misma pileta; vacío -> None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s_ = str(v).strip()
    if s_ == "" or s_.lower() in ("nan", "none"):
        return None
    try:
        f = float(s_)
        return str(int(f)) if f.is_integer() else s_
    except ValueError:
        return s_.upper()


def _club_norm(txt):
    """Nombre de club comparable: sin tildes, mayúsculas y espacios de más."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return " ".join(t.upper().split())


def detalle_fechas(df, clubes=None):
    """Fechas de competencia del nadador: una sede (club) en un día.
    - Piletas distintas del mismo club (p. ej. 25 m y 50 m) cuentan como la misma sede.
    - Un registro sin pileta se suma a la fecha de ese mismo día.
    Devuelve una lista ordenada de (fecha, nombre_sede, [índices de las filas de esa fecha])."""
    if df.empty:
        return []
    clubes = {(_pileta_norm(k)): v for k, v in (clubes or {}).items() if _pileta_norm(k) is not None}
    dias = _fechas(df['fecha']).dt.date
    pil = df['codpileta'].map(_pileta_norm) if 'codpileta' in df.columns else pd.Series([None] * len(df), index=df.index)
    nombre, filas = {}, {}
    for i, d, p in zip(df.index, dias, pil):
        if pd.isna(d) or pd.isna(p):
            continue
        club = clubes.get(p, f"Pileta {p}")
        clave = _club_norm(club)
        nombre.setdefault(clave, str(club))
        filas.setdefault((d, clave), []).append(i)
    for i, d, p in zip(df.index, dias, pil):
        if pd.isna(d) or pd.notna(p):
            continue
        # Sin pileta: va a la sede de ese día; si no hay ninguna, queda como "Sede sin cargar"
        clave = next((c for (dd, c) in filas if dd == d), None)
        if clave is None:
            clave = "SIN SEDE"
            nombre.setdefault(clave, "Sede sin cargar")
        filas.setdefault((d, clave), []).append(i)
    # Cada día en cada sede es una fecha (dos días seguidos en el mismo club son dos fechas)
    return sorted((d, nombre[c], idx) for (d, c), idx in filas.items())


def contar_torneos(df, clubes=None):
    return len(detalle_fechas(df, clubes))


def calcular_resumen(db, id_nadador, anio, mis_resultados, clubes=None):
    """Estadísticas del año a partir de los registros de la ficha (individuales y relevos)."""
    ind, todos = mis_resultados(id_nadador)
    todos = todos.assign(_f=_fechas(todos['fecha']))
    ind = ind.assign(_f=_fechas(ind['fecha']), _s=ind['tiempo'].map(_seg))
    del_anio = todos[todos['_f'].dt.year == anio]
    ind_anio = ind[ind['_f'].dt.year == anio]

    r = {"anio": anio, "carreras": len(del_anio), "individuales": len(ind_anio),
         "relevos": int((del_anio['tipo'] == 'Relevo').sum())}
    if del_anio.empty:
        return r

    fechas = detalle_fechas(del_anio, clubes)
    r["torneos"] = len(fechas)
    detalle = []
    for dia, sede, idx in fechas:
        carreras = []
        for _, fila in del_anio.loc[idx].iterrows():
            prueba = " ".join(str(x) for x in (fila.get('Distancia'), fila.get('Estilo')) if pd.notna(x)) or "Prueba"
            if fila.get('tipo') == 'Relevo':
                prueba = f"Relevo 4x{prueba}"
            marca = fila.get('marca')
            pos = int(fila['posicion']) if pd.notna(fila.get('posicion')) else 0
            carreras.append(prueba + (f" ({marca})" if pd.notna(marca) and str(marca).strip() else "")
                            + (f" · {pos}°" if pos > 0 else ""))
        detalle.append((f"{dia.strftime('%d/%m')} · {sede}", carreras))
    r["fechas_detalle"] = detalle
    r["oro"] = int((del_anio['posicion'] == 1).sum())
    r["plata"] = int((del_anio['posicion'] == 2).sum())
    r["bronce"] = int((del_anio['posicion'] == 3).sum())
    r["podios"] = r["oro"] + r["plata"] + r["bronce"]
    # Individuales: la distancia de la prueba. Relevos: 50 m por posta nadada.
    es_rel = del_anio['tipo'] == 'Relevo'
    r["metros"] = int(del_anio.loc[~es_rel, 'Distancia'].map(_metros).sum() + METROS_RELEVO * int(es_rel.sum()))

    meses = del_anio['_f'].dt.month.value_counts()
    r["mes_activo"] = MESES[int(meses.idxmax()) - 1] if not meses.empty else None

    if not ind_anio.empty:
        est = ind_anio['Estilo'].value_counts()
        r["estilo_fav"] = str(est.idxmax())
        r["estilo_fav_n"] = int(est.max())

    # Pruebas que nadó por primera vez este año (y si estrenó un estilo completo)
    # (solo si ya nadaba antes de este año: en la primera temporada todo sería "nuevo")
    hist_ind = ind.dropna(subset=['_f'])
    if not hist_ind.empty and (hist_ind['_f'].dt.year < anio).any():
        primera_prueba = hist_ind.groupby(['Estilo', 'Distancia'])['_f'].min()
        nuevas = primera_prueba[primera_prueba.dt.year == anio].sort_values()
        primer_estilo = hist_ind.groupby('Estilo')['_f'].min()
        estilos_nuevos = [str(e) for e in primer_estilo[primer_estilo.dt.year == anio].sort_values().index]
        if not nuevas.empty:
            # Primero las pruebas de un estilo estrenado este año
            orden = sorted(nuevas.index, key=lambda k: (str(k[0]) not in estilos_nuevos, nuevas[k]))
            r["animo_pruebas"] = [f"{dist} {est}" for est, dist in orden]
            r["animo_estilos"] = estilos_nuevos

    # Récords personales batidos en el año (mejoran una marca anterior) y la mayor mejora
    records, mejor = 0, None
    for (e, d), g in ind.dropna(subset=['_s', '_f']).sort_values('_f').groupby(['Estilo', 'Distancia']):
        previo = None
        for _, fila in g.iterrows():
            if previo is not None and fila['_s'] < previo:
                if fila['_f'].year == anio:
                    records += 1
                    mejora = previo - fila['_s']
                    if mejor is None or mejora > mejor[2]:
                        mejor = (str(d), str(e), mejora)
            previo = fila['_s'] if previo is None else min(previo, fila['_s'])
    r["records"] = records
    if mejor:
        r["mejor_mejora"] = f"{mejor[0]} {mejor[1]} · -{_fmt_seg(mejor[2])} s"

    # Medallas totales con NOB (toda su historia en el club, individuales + relevos)
    hist = todos[todos['posicion'].between(1, 3)]
    r["medallas_nob"] = int(len(hist))
    return r


# ---------------------------------------------------------------- imagen
def _f(peso, tam):
    try:
        return ImageFont.truetype(str(FUENTES / f"Poppins-{peso}.ttf"), tam)
    except Exception:
        return ImageFont.load_default(size=tam)


def _centrado(d, y, txt, fuente, color, W):
    w = d.textlength(txt, font=fuente)
    d.text(((W - w) / 2, y), txt, font=fuente, fill=color)


def _ajustar(d, txt, peso, tam, ancho_max):
    while tam > 20 and d.textlength(txt, font=_f(peso, tam)) > ancho_max:
        tam -= 2
    return _f(peso, tam)


def _fondo(W, H):
    img = Image.new("RGB", (W, H), (12, 6, 8))
    # Degradé vertical oscuro y manchas de luz roja difuminadas
    grad = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), (20, 8, 10)), Image.new("RGB", (W, H), (60, 4, 10)), grad)
    # Las luces se dibujan y difuminan en chico (rápido) y después se agrandan
    k = 8
    w_, h_ = W // k, H // k
    luz = Image.new("RGB", (w_, h_), (0, 0, 0))
    dl = ImageDraw.Draw(luz)
    dl.ellipse((-w_ * 0.35, -h_ * 0.12, w_ * 0.75, h_ * 0.38), fill=(150, 10, 25))
    dl.ellipse((w_ * 0.45, h_ * 0.62, w_ * 1.4, h_ * 1.15), fill=(120, 6, 18))
    luz = luz.filter(ImageFilter.GaussianBlur(160 / k)).resize((W, H), Image.BICUBIC)
    img = Image.blend(img, Image.composite(luz, img, luz.convert("L")), 0.85)
    # Ondas de pileta
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(7):
        y0 = int(H * 0.30) + i * 26
        d.arc((-200, y0, W + 200, y0 + 160), 190, 350, fill=(255, 255, 255, 14), width=3)
    return img


def _marca_agua(img, x, y, tam, opacidad=0.16):
    try:
        e = Image.open(BASE / "escudo.png").convert("RGBA")
        e = e.resize((tam, tam), Image.LANCZOS)
        e.putalpha(e.getchannel("A").point(lambda v: int(v * opacidad)))
        img.paste(e, (int(x), int(y)), e)
    except Exception:
        pass


def _escudo(img, x, y, tam):
    try:
        e = Image.open(BASE / "escudo.png").convert("RGBA")
        e.thumbnail((tam, tam))
        img.paste(e, (int(x), int(y)), e)
    except Exception:
        pass


def _medalla(d, cx, cy, rad, color, n, etiqueta):
    d.ellipse((cx - rad - 6, cy - rad - 6, cx + rad + 6, cy + rad + 6), fill=(255, 255, 255, 30))
    d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=color)
    d.ellipse((cx - rad + 10, cy - rad + 10, cx + rad - 10, cy + rad - 10), outline=(255, 255, 255, 110), width=3)
    f = _f("Black", int(rad * 0.95))
    t = str(n)
    w = d.textlength(t, font=f)
    d.text((cx - w / 2, cy - rad * 0.68), t, font=f, fill=(30, 18, 10))
    fe = _f("Bold", 30)
    w = d.textlength(etiqueta, font=fe)
    d.text((cx - w / 2, cy + rad + 18), etiqueta, font=fe, fill=(235, 235, 235))


def _tarjeta(d, x, y, w, h, titulo, valor, sub=""):
    d.rounded_rectangle((x, y, x + w, y + h), radius=34, fill=(255, 255, 255, 22), outline=(255, 255, 255, 45), width=2)
    d.text((x + 32, y + 22), titulo.upper(), font=_f("Bold", 24), fill=(255, 130, 138))
    tam = 72 if h >= 190 else 60
    fv = _ajustar(d, valor, "Black", tam, w - 64)
    d.text((x + 32, y + 48), valor, font=fv, fill=(255, 255, 255))
    if sub:
        d.text((x + 32, y + h - 46), sub, font=_ajustar(d, sub, "Regular", 25, w - 64), fill=(215, 205, 207))


def generar_imagen(r, nombre, formato="Historia (1080×1920)"):
    """PNG (bytes) estilo resumen anual, en formato historia o posteo de Instagram."""
    W, H = FORMATOS.get(formato, (1080, 1920))
    historia = H > 1500
    img = _fondo(W, H)                      # RGB: los rellenos semitransparentes se mezclan con el fondo
    d = ImageDraw.Draw(img, "RGBA")
    M = 70
    y = 80 if historia else 56

    # Encabezado: escudo + club
    _escudo(img, M, y, 92)
    d.text((M + 112, y + 10), "COMPLEJO ACUÁTICO", font=_f("Bold", 26), fill=(255, 150, 156))
    d.text((M + 112, y + 42), "Newell's Old Boys", font=_f("SemiBold", 34), fill=(255, 255, 255))
    y += 150 if historia else 120

    # Título grande (con el escudo como marca de agua a la derecha)
    tam_ma = 560 if historia else 430
    _marca_agua(img, W - tam_ma * 0.72, y - (10 if historia else 20), tam_ma)
    d.text((M, y), "MI", font=_f("Black", 120 if historia else 96), fill=(255, 255, 255))
    d.text((M, y + (112 if historia else 90)), str(r["anio"]), font=_f("Black", 230 if historia else 170), fill=ROJO)
    y += 360 if historia else 270
    d.text((M, y), "en el agua", font=_f("SemiBold", 46 if historia else 38), fill=(235, 235, 235))
    y += 70 if historia else 58
    d.text((M, y), nombre, font=_ajustar(d, nombre, "Bold", 44 if historia else 38, W - 2 * M), fill=(255, 205, 210))
    y += 90 if historia else 68

    # Medallas
    rad = 78 if historia else 62
    cy = y + rad + 10
    for i, (col, n, et) in enumerate(((ORO, r.get("oro", 0), "ORO"), (PLATA, r.get("plata", 0), "PLATA"),
                                       (BRONCE, r.get("bronce", 0), "BRONCE"))):
        _medalla(d, W * (i + 1) / 4, cy, rad, col, n, et)
    y = cy + rad + (78 if historia else 70)

    # Tarjetas de datos
    gap = 24
    cw = (W - 2 * M - gap) / 2
    ch = 184 if historia else 168
    datos = [
        ("Carreras", str(r.get("carreras", 0)), f"{r.get('relevos', 0)} en relevos" if r.get("relevos") else "individuales"),
        ("Fechas", str(r.get("torneos", 0)), f"más activo: {r['mes_activo']}" if r.get("mes_activo") else ""),
        ("Metros", f"{r.get('metros', 0):,}".replace(",", ".") + " m", "en competencia"),
        ("Récords personales", str(r.get("records", 0)), "marcas mejoradas"),
    ]
    for i, (t, v, s) in enumerate(datos):
        x0 = M + (i % 2) * (cw + gap)
        y0 = y + (i // 2) * (ch + gap)
        _tarjeta(d, x0, y0, cw, ch, t, v, s)
    y += 2 * ch + gap + (30 if historia else 28)

    # Destacados en una lista
    destacados = []
    if r.get("animo_pruebas"):
        pr = r["animo_pruebas"]
        txt = " · ".join(pr[:2]) + (f" y {len(pr) - 2} más" if len(pr) > 2 else "")
        n_est = len(r.get("animo_estilos") or [])
        if n_est > 1:
            titulo = f"Me animé a {n_est} estilos nuevos"
        elif n_est == 1:
            titulo = f"Me animé a un estilo nuevo: {r['animo_estilos'][0]}"
        else:
            titulo = "Me animé a pruebas nuevas" if len(pr) > 1 else "Me animé a una prueba nueva"
        destacados.append((titulo, txt))
    if r.get("estilo_fav"):
        destacados.append(("Estilo favorito", f"{r['estilo_fav']} ({r['estilo_fav_n']} carreras)"))
    if r.get("mejor_mejora"):
        destacados.append(("Mayor mejora", r["mejor_mejora"]))
    if r.get("medallas_nob"):
        n = r["medallas_nob"]
        txt = f"{n} medalla{'s' if n != 1 else ''}"
        destacados.append(("Medallas totales en NOB", txt))
    if not historia:
        destacados = destacados[:1]   # el posteo es más bajo: solo el destacado principal
    for t, v in destacados:
        d.rounded_rectangle((M, y, W - M, y + 88), radius=26, fill=(0, 0, 0, 90))
        d.rectangle((M, y + 16, M + 8, y + 72), fill=ROJO)
        d.text((M + 32, y + 10), t.upper(), font=_f("Bold", 22), fill=(255, 140, 146))
        d.text((M + 32, y + 36), v, font=_ajustar(d, v, "Bold", 36, W - 2 * M - 64), fill=(255, 255, 255))
        y += 100

    # Pie
    pie = f"#NOB{r['anio']} · Natación Newell's"
    _centrado(d, H - (90 if historia else 62), pie, _f("SemiBold", 28), (255, 255, 255, 170), W)

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


# ================================================================ resumen del club (entrenador)
PROFE = "Profe. Franco Minacori"

# Logros del equipo por año, que no salen de las planillas: (línea 1, línea 2, puesto, total de clubes)
LOGROS_CLUB = {
    2026: [
        ("Circuito de Natación", "Master Aficionados", 2, 24),
        ("Master Open · agosto", "Parque Roca", 18, 150),
    ],
}


def _id(v):
    try:
        return str(int(float(v)))
    except Exception:
        return None


def calcular_resumen_club(db, anio, clubes=None, excluir=()):
    """Estadísticas del año de todo el equipo: individuales y relevos (un relevo cuenta como una carrera
    y un podio del equipo). `excluir`: códigos de nadador (texto) que no cuentan (el entrenador)."""
    excluir = set(excluir)
    t = db['tiempos'].copy()
    t['_id'] = t['codnadador'].map(_id)
    t = t[t['_id'].notna() & ~t['_id'].isin(excluir)].copy()
    t['_f'] = _fechas(t['fecha'])
    t['posicion'] = pd.to_numeric(t['posicion'], errors='coerce').fillna(0).astype(int) if 'posicion' in t.columns else 0
    ind = t[t['_f'].dt.year == anio]

    rel = db.get('relevos')
    if rel is not None and not rel.empty and 'fecha' in rel.columns:
        rel = rel.copy()
        rel['_f'] = _fechas(rel['fecha'])
        rel = rel[rel['_f'].dt.year == anio].copy()
        rel['posicion'] = (pd.to_numeric(rel['posicion'], errors='coerce').fillna(0).astype(int)
                           if 'posicion' in rel.columns else 0)
    else:
        rel = pd.DataFrame({'fecha': [], 'codpileta': [], 'posicion': [], '_f': pd.Series([], dtype='datetime64[ns]')})

    r = {"anio": anio, "individuales": len(ind), "relevos": len(rel), "carreras": len(ind) + len(rel)}
    if not r["carreras"]:
        return r

    pos = pd.concat([ind['posicion'], rel['posicion']], ignore_index=True)
    r["oro"], r["plata"], r["bronce"] = (int((pos == k).sum()) for k in (1, 2, 3))
    r["podios"] = r["oro"] + r["plata"] + r["bronce"]

    nadadores = set(ind['_id'])
    en_podio = set(ind.loc[ind['posicion'].between(1, 3), '_id'])
    for k in range(1, 5):
        col = f'nadador_{k}'
        if col in rel.columns:
            ids = rel[col].map(_id)
            nadadores.update(i for i in ids.dropna() if i not in excluir)
            en_podio.update(i for i in ids[rel['posicion'].between(1, 3)].dropna() if i not in excluir)
    r["nadadores"] = len(nadadores)
    r["nadadores_podio"] = len(en_podio)

    cols = ['fecha', 'codpileta', 'posicion']
    ambos = pd.concat([ind.reindex(columns=cols), rel.reindex(columns=cols)], ignore_index=True)
    # Para el equipo, un torneo de varios días seguidos en la misma sede es una sola fecha
    fechas = []   # [primer día, último día, sede, índices]
    for dia, sede, idx in sorted(detalle_fechas(ambos, clubes), key=lambda f: (_club_norm(f[1]), f[0])):
        ult = fechas[-1] if fechas else None
        if ult and _club_norm(ult[2]) == _club_norm(sede) and (dia - ult[1]).days <= 1:
            ult[1] = dia
            ult[3] = ult[3] + idx
        else:
            fechas.append([dia, dia, sede, list(idx)])
    fechas.sort(key=lambda f: f[0])
    r["torneos"] = len(fechas)
    r["fechas_detalle"] = [
        (f"{d1.strftime('%d/%m')}{'–' + d2.strftime('%d/%m') if d2 != d1 else ''} · {sede}", len(idx),
         int(pd.to_numeric(ambos.loc[idx, 'posicion'], errors='coerce').between(1, 3).sum()))
        for d1, d2, sede, idx in fechas]
    meses = pd.concat([ind['_f'], rel['_f']]).dt.month.value_counts()
    r["mes_activo"] = MESES[int(meses.idxmax()) - 1] if not meses.empty else None

    # Récords personales del equipo: marcas del año que mejoran la mejor marca anterior del nadador
    t['_s'] = t['tiempo'].map(_seg)
    records = 0
    for _, g in t.dropna(subset=['_s', '_f']).sort_values('_f').groupby(['_id', 'codestilo', 'coddistancia']):
        previo = None
        for f, s in zip(g['_f'], g['_s']):
            if previo is not None and s < previo and f.year == anio:
                records += 1
            previo = s if previo is None else min(previo, s)
    r["records"] = records
    r["logros"] = LOGROS_CLUB.get(anio, [])
    return r


def _logro(d, x, y, w, h, l1, l2, puesto, total):
    d.rounded_rectangle((x, y, x + w, y + h), radius=30, fill=(0, 0, 0, 95), outline=(255, 200, 40, 120), width=2)
    chico = h < 170
    for k, linea in enumerate((l1, l2)):
        txt = linea.upper()
        d.text((x + 28, y + (14 if chico else 20) + k * (26 if chico else 28)), txt,
               font=_ajustar(d, txt, "Bold", 22, w - 56), fill=(255, 140, 146))
    fp = _f("Black", 54 if chico else 70)
    tp = f"{puesto}°"
    yp = y + (66 if chico else 84)
    d.text((x + 28, yp), tp, font=fp, fill=ORO)
    xs = x + 28 + d.textlength(tp, font=fp) + 14
    sub = f"de {total} clubes"
    d.text((xs, yp + (22 if chico else 32)), sub, font=_ajustar(d, sub, "SemiBold", 30, x + w - 28 - xs),
           fill=(255, 255, 255))


def generar_imagen_club(r, formato="Historia (1080×1920)"):
    """PNG del resumen del año del equipo de Natación Master, firmado por el profe.
    Devuelve (png, y_fin): y_fin es dónde termina el contenido (para controlar que no pise el pie)."""
    W, H = FORMATOS.get(formato, (1080, 1920))
    historia = H > 1500
    img = _fondo(W, H)
    d = ImageDraw.Draw(img, "RGBA")
    M = 70
    y = 80 if historia else 56

    _escudo(img, M, y, 92)
    d.text((M + 112, y + 10), "COMPLEJO ACUÁTICO", font=_f("Bold", 26), fill=(255, 150, 156))
    d.text((M + 112, y + 42), "Newell's Old Boys", font=_f("SemiBold", 34), fill=(255, 255, 255))
    y += 150 if historia else 120

    tam_ma = 560 if historia else 430
    _marca_agua(img, W - tam_ma * 0.72, y - (10 if historia else 20), tam_ma)
    d.text((M, y), "NUESTRO", font=_f("Black", 120 if historia else 96), fill=(255, 255, 255))
    d.text((M, y + (112 if historia else 90)), str(r["anio"]), font=_f("Black", 230 if historia else 170), fill=ROJO)
    y += 360 if historia else 270
    if historia:
        d.text((M, y), "en el agua", font=_f("SemiBold", 46), fill=(235, 235, 235))
        y += 70
        d.text((M, y), "Natación Master", font=_f("Bold", 44), fill=(255, 205, 210))
        y += 90
    else:   # el posteo es más bajo: una sola línea
        fe = _f("SemiBold", 38)
        d.text((M, y), "en el agua · ", font=fe, fill=(235, 235, 235))
        d.text((M + d.textlength("en el agua · ", font=fe), y), "Natación Master", font=_f("Bold", 38), fill=(255, 205, 210))
        y += 68

    rad = 78 if historia else 62
    cy = y + rad + 10
    for i, (col, n, et) in enumerate(((ORO, r.get("oro", 0), "ORO"), (PLATA, r.get("plata", 0), "PLATA"),
                                       (BRONCE, r.get("bronce", 0), "BRONCE"))):
        _medalla(d, W * (i + 1) / 4, cy, rad, col, n, et)
    y = cy + rad + (78 if historia else 60)

    gap = 24
    cw = (W - 2 * M - gap) / 2
    ch = 184 if historia else 168
    datos = [
        ("Fechas", str(r.get("torneos", 0)), f"más activo: {r['mes_activo']}" if r.get("mes_activo") else ""),
        ("Carreras", str(r.get("carreras", 0)), f"{r.get('relevos', 0)} en relevos" if r.get("relevos") else "individuales"),
        ("Nadadores", str(r.get("nadadores", 0)), f"{r.get('nadadores_podio', 0)} subieron al podio"),
        ("Récords personales", str(r.get("records", 0)), "marcas mejoradas"),
    ]
    for i, (t, v, s) in enumerate(datos):
        _tarjeta(d, M + (i % 2) * (cw + gap), y + (i // 2) * (ch + gap), cw, ch, t, v, s)
    y += 2 * ch + gap + (30 if historia else 24)

    logros = list(r.get("logros") or [])[:2]
    if logros:
        lh = 190 if historia else 140
        for i, lg in enumerate(logros):
            _logro(d, M + i * (cw + gap), y, cw if len(logros) > 1 else W - 2 * M, lh, *lg)
        y += lh

    # Pie: firma del profe y hashtag
    _centrado(d, H - (150 if historia else 104), PROFE, _f("Bold", 36 if historia else 30), (255, 255, 255), W)
    _centrado(d, H - (96 if historia else 62), f"#NOB{r['anio']} · Natación Master Newell's",
              _f("SemiBold", 26), (255, 255, 255, 170), W)

    out = io.BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue(), y
