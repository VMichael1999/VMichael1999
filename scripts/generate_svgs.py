"""Genera los SVG del perfil (banner animado y proyectos), tema oscuro.

El banner muestra el retrato en píxeles; el retrato se desintegra en
partículas que forman los logos de Flutter, Kotlin, Swift y React, y luego
vuelve a armarse la foto. Todo en bucle.

Uso:
    pip install -r scripts/requirements.txt
    python3 scripts/generate_svgs.py

Salida: assets/hero.svg, assets/projects.svg
"""

import random
from collections import deque
from pathlib import Path
from textwrap import wrap
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from svgelements import SVG, Path as SvgPath

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "assets"
PHOTO = ROOT / "source" / "michael.jpg"
LOGOS = ROOT / "source" / "logos"

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
CHAR_W = 0.61  # ancho aproximado de un carácter monoespaciado (em)

T = {
    "bg": "#0B1120", "panel": "#0F172A", "bar": "#131C31",
    "border": "#1E293B", "text": "#E2E8F0", "muted": "#94A3B8",
    "dim": "#64748B", "primary": "#38BDF8", "violet": "#A78BFA",
    "green": "#34D399", "chip": "#15203A",
}

# ---------------------------------------------------------------- contenido

NAME = "Michael Valdiviezo Maza"
ROLE = "Mobile Developer · Flutter | Android | iOS"
FOCUS = [
    "Clean Architecture · BLoC · MVVM · Riverpod",
    "Pagos multi-país · SSL Pinning · anti GPS-spoofing",
    "Offline-first con SQLite/Drift y sincronización",
    "Integración con APIs REST y WebSockets",
]
METRICS = [
    ("3+", "años en", "producción"),
    ("6", "años en", "tecnología"),
    ("3", "sectores: transporte,", "fintech y banca"),
]
STACK = ["Flutter", "Dart", "Kotlin", "Swift", "React Native", "Android",
         "Firebase"]

PROJECTS = [
    {
        "repo": "AsisGo",
        "desc": "Control de asistencia corporativo con geolocalización, "
                "marcación con selfie y auditoría multiempresa.",
        "tags": ["Flutter", "Maps", "Geolocalización"],
    },
    {
        "repo": "MiGasto",
        "desc": "Registra gastos leyendo notificaciones bancarias con un "
                "servicio nativo en Kotlin. Datos cifrados en el equipo.",
        "tags": ["Flutter", "Kotlin", "Isar"],
    },
    {
        "repo": "polyline_animation_plus",
        "desc": "Paquete Flutter para animar rutas sobre Google Maps. "
                "Pensado para apps de transporte y tracking.",
        "tags": ["Package", "Google Maps"],
    },
    {
        "repo": "floating_bubble_overlay",
        "desc": "Plugin Flutter para mostrar burbujas flotantes sobre "
                "otras apps en Android.",
        "tags": ["Plugin", "Android"],
    },
    {
        "repo": "mini-buki",
        "desc": "Sistema de reservas: API REST con Express, TypeScript y "
                "Prisma, y app Flutter con Riverpod.",
        "tags": ["Flutter", "Riverpod", "Node.js"],
    },
    {
        "repo": "BeatzPro",
        "desc": "App de música multiplataforma (Android, Windows, Linux) "
                "con caché, radio y playlists.",
        "tags": ["Flutter", "Desktop"],
    },
]

# ---------------------------------------------------------------- animación

GRID = 170          # resolución del retrato en celdas
CELL = 2.35         # px por celda  → retrato de ~400 px
PARTICLES = 1000
CHUNKS = 40         # grupos en que se dispersa el retrato
LOOP_BEGIN = 3.0    # s: el bucle arranca tras la intro
LOOP = 16.0         # s: duración de un ciclo completo

# (nombre, color, instante en que queda formado, instante en que se va)
STAGES = [
    ("flutter", "#54C5F8", 3.2, 5.0),
    ("kotlin", "#A97BFF", 6.0, 7.8),
    ("swift", "#F05138", 8.8, 10.6),
    ("react", "#61DAFB", 11.6, 13.4),
]
DISSOLVE = (2.0, 2.8)    # el retrato se dispersa
REASSEMBLE = (14.2, 15.0)  # el retrato vuelve
BACK = 14.8              # las partículas regresan a la foto
EASE = ".45 0 .2 1"

random.seed(7)
np.random.seed(7)


def mono_w(text, size):
    return len(text) * size * CHAR_W


def fade(begin, dur=0.4):
    return (f'<animate attributeName="opacity" from="0" to="1" '
            f'dur="{dur}s" begin="{begin:.2f}s" fill="freeze"/>')


def loop_anim(attr, values, times, transform=False):
    kt = ";".join(f"{t / LOOP:.4f}" for t in times)
    ks = ";".join([EASE] * (len(times) - 1))
    tag = "animateTransform" if transform else "animate"
    extra = ' type="translate"' if transform else ""
    return (f'<{tag} attributeName="{attr}"{extra} values="{";".join(values)}" '
            f'keyTimes="{kt}" calcMode="spline" keySplines="{ks}" '
            f'dur="{LOOP}s" begin="{LOOP_BEGIN}s" repeatCount="indefinite"/>')


# ---------------------------------------------------------------- retrato


def portrait_pixels():
    """Devuelve una matriz booleana GRID×GRID con el retrato tramado."""
    im = Image.open(PHOTO).convert("RGB")
    a = np.asarray(im).astype(float)
    h, w, _ = a.shape
    mx, mn = a.max(2), a.min(2)
    sat, lum = (mx - mn) / (mx + 1e-6), a.mean(2)
    cand = (sat < 0.10) & (lum > 140)  # fondo gris claro

    bg = np.zeros((h, w), bool)
    q = deque()
    seeds = [(0, x) for x in range(w)] + \
        [(y, x) for y in range(h) for x in (0, w - 1)]
    for y, x in seeds:
        if cand[y, x] and not bg[y, x]:
            bg[y, x] = True
            q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx] and cand[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    # la camisa blanca también es "gris claro": se recupera a mano
    bg[int(h * 0.70):, int(w * 0.38):int(w * 0.71)] = False

    fg = Image.fromarray((~bg * 255).astype("uint8")) \
        .filter(ImageFilter.MinFilter(3)).resize((GRID, GRID), Image.BILINEAR)
    mask = np.asarray(fg).astype(float) / 255 > 0.5
    lum = np.asarray(im.convert("L").resize((GRID, GRID), Image.LANCZOS))
    lum = lum.astype(float) / 255
    lo, hi = np.percentile(lum[mask], 3), np.percentile(lum[mask], 97)
    lum = np.clip((lum - lo) / (hi - lo), 0, 0.88) ** 1.05
    lum[~mask] = 0

    out = np.zeros_like(mask)
    e = lum.copy()
    for y in range(GRID):  # Floyd–Steinberg
        for x in range(GRID):
            on = e[y, x] > 0.5
            out[y, x] = on
            err = e[y, x] - on
            if x + 1 < GRID:
                e[y, x + 1] += err * 7 / 16
            if y + 1 < GRID:
                if x > 0:
                    e[y + 1, x - 1] += err * 3 / 16
                e[y + 1, x] += err * 5 / 16
                if x + 1 < GRID:
                    e[y + 1, x + 1] += err / 16
    return out & mask


# ---------------------------------------------------------------- logos


def logo_mask(name, size=GRID * 4):
    """Rasteriza un icono de Simple Icons (viewBox 24×24)."""
    svg = SVG.parse(str(LOGOS / f"{name}.svg"))
    m = Image.new("1", (size, size), 0)
    subs = []
    for el in svg.elements():
        if isinstance(el, SvgPath):
            for sub in el.as_subpaths():
                p = SvgPath(sub)
                pts = [p.point(t) for t in np.linspace(0, 1, 800)]
                pts = [(pt.x * size / 24, pt.y * size / 24) for pt in pts]
                layer = Image.new("1", (size, size), 0)
                ImageDraw.Draw(layer).polygon(pts, fill=1)
                subs.append(layer)
                m = ImageChops.logical_xor(m, layer)
    if name == "swift":
        # el icono es un cuadrado con el pájaro recortado: nos quedamos
        # con el pájaro (interior del contorno exterior menos el relleno)
        outer = max(subs, key=lambda l: np.asarray(l).sum())
        m = ImageChops.logical_and(outer, ImageChops.invert(m))
    return np.asarray(m)


def sample_points(mask, n, box):
    """n puntos repartidos sobre la máscara, llevados a la caja (x, y, lado)."""
    ys, xs = np.nonzero(mask)
    step = max(1, int(np.sqrt(len(xs) / (n * 1.3))))
    keep = (xs % step == 0) & (ys % step == 0)
    xs, ys = xs[keep], ys[keep]
    idx = np.random.choice(len(xs), n, replace=len(xs) < n)
    size = mask.shape[0]
    bx, by, side = box
    px = bx + (xs[idx] + np.random.rand(n) * step) / size * side
    py = by + (ys[idx] + np.random.rand(n) * step) / size * side
    return list(zip(px, py))


def spatial_order(points):
    """Orden que conserva la vecindad: franjas horizontales en zigzag."""
    band = int(np.sqrt(len(points)))
    pts = sorted(points, key=lambda p: p[1])
    ordered = []
    for i in range(0, len(pts), band):
        row = sorted(pts[i:i + band], key=lambda p: p[0])
        ordered.extend(row if (i // band) % 2 == 0 else row[::-1])
    return ordered


# ---------------------------------------------------------------- banner


def typed(uid, x, y, text, size, fill, begin, speed=0.045):
    """Texto que se 'escribe' carácter a carácter mediante un clipPath."""
    w = mono_w(text, size) + 4
    dur = max(len(text) * speed, 0.2)
    steps = ";".join(str(round(w * i / len(text))) for i in range(len(text) + 1))
    return (
        f'<clipPath id="{uid}"><rect x="{x}" y="{y - size}" width="0" '
        f'height="{size * 1.6}"><animate attributeName="width" '
        f'values="{steps}" calcMode="discrete" dur="{dur:.2f}s" '
        f'begin="{begin:.2f}s" fill="freeze"/></rect></clipPath>'
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'clip-path="url(#{uid})">{escape(text)}</text>'
    ), begin + dur


def chip(x, y, label, size=12, pad=10, color=None):
    w = mono_w(label, size) + pad * 2
    return (
        f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="24" rx="12" '
        f'fill="{T["chip"]}" stroke="{T["border"]}"/>'
        f'<text x="{x + w / 2:.1f}" y="{y + 16}" font-size="{size}" '
        f'text-anchor="middle" fill="{color or T["primary"]}">'
        f'{escape(label)}</text>'
    ), w


def gradient(uid):
    a, b, c = T["primary"], T["violet"], T["green"]
    return (
        f'<linearGradient id="{uid}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{a}"><animate attributeName="stop-color" '
        f'values="{a};{b};{c};{a}" dur="9s" repeatCount="indefinite"/></stop>'
        f'<stop offset="1" stop-color="{b}"><animate attributeName="stop-color" '
        f'values="{b};{c};{a};{b}" dur="9s" repeatCount="indefinite"/></stop>'
        f'</linearGradient>'
    )


def visual(px, py):
    """Panel izquierdo: retrato + partículas + leyenda."""
    p = []
    pix = portrait_pixels()
    on = list(zip(*np.nonzero(pix)))  # (y, x)

    # --- retrato: repartido en grupos que se dispersan
    groups = [[] for _ in range(CHUNKS)]
    for y, x in on:
        groups[random.randrange(CHUNKS)].append((x, y))
    t_hide = [0, DISSOLVE[0], DISSOLVE[1], REASSEMBLE[0], REASSEMBLE[1], LOOP]
    p.append(f'<g transform="translate({px},{py}) scale({CELL})" '
             f'fill="url(#face)" shape-rendering="crispEdges">')
    for i, grp in enumerate(groups):
        ang = random.uniform(0, 2 * np.pi)
        dist = random.uniform(15, 55)
        dx, dy = dist * np.cos(ang), dist * np.sin(ang) - 12
        d = "".join(f"M{x} {y}h1v1h-1z" for x, y in grp)
        p.append(
            f'<g opacity="0">{fade(0.2 + i * 0.03, 0.9)}<g>'
            + loop_anim("opacity", ["1", "1", "0", "0", "1", "1"], t_hide)
            + loop_anim("transform",
                        ["0 0", "0 0", f"{dx:.0f} {dy:.0f}", f"{dx:.0f} {dy:.0f}",
                         "0 0", "0 0"], t_hide, transform=True)
            + f'<path d="{d}"/></g></g>'
        )
    p.append("</g>")

    # --- partículas: foto → logos → foto
    start = spatial_order([(x + random.random(), y + random.random())
                           for y, x in random.sample(on, PARTICLES)])
    box = (GRID * 0.16, GRID * 0.14, GRID * 0.68)  # logo centrado, 68 % del lado
    shapes = [spatial_order(sample_points(logo_mask(n), PARTICLES, box))
              for n, *_ in STAGES]

    times = [0, DISSOLVE[0]]
    for _, _, t_in, t_out in STAGES:
        times += [t_in, t_out]
    times += [BACK, LOOP]

    colors = [T["violet"], T["violet"]]
    for _, c, *_ in STAGES:
        colors += [c, c]
    colors += [T["violet"], T["violet"]]
    fill_anim = (f'<animate attributeName="fill" values="{";".join(colors)}" '
                 f'keyTimes="{";".join(f"{t / LOOP:.4f}" for t in times)}" '
                 f'dur="{LOOP}s" begin="{LOOP_BEGIN}s" repeatCount="indefinite"/>')
    op_times = [0, DISSOLVE[0] - 0.1, DISSOLVE[0] + 0.1,
                REASSEMBLE[0] + 0.2, REASSEMBLE[1], LOOP]
    op_anim = loop_anim("opacity", ["0", "0", "1", "1", "0", "0"], op_times)

    p.append(f'<g transform="translate({px},{py}) scale({CELL})" '
             f'fill="{T["violet"]}">{fill_anim}')
    for i in range(PARTICLES):
        path = [start[i], start[i]]
        for s in shapes:
            path += [s[i], s[i]]
        path += [start[i], start[i]]
        vals = [f"{x:.1f} {y:.1f}" for x, y in path]
        p.append(f'<use href="#pt" opacity="0">{op_anim}'
                 f'{loop_anim("transform", vals, times, transform=True)}</use>')
    p.append("</g>")
    return "".join(p)


def caption(x, y):
    """Leyenda del panel: cambia con cada figura."""
    labels = [("michael.png", T["violet"])] + \
        [(f"{n}.svg", c) for n, c, *_ in STAGES]
    windows = [(None, DISSOLVE[0], REASSEMBLE[1])] + \
        [(t_in - 0.6, t_in, t_out) for _, _, t_in, t_out in STAGES]
    out = []
    for (label, color), (pre, t_in, t_out) in zip(labels, windows):
        if pre is None:  # la foto: visible al inicio y al volver
            vals, ts = ["1", "1", "0", "0", "1", "1"], \
                [0, DISSOLVE[0], DISSOLVE[0] + 0.3, REASSEMBLE[1] - 0.3,
                 REASSEMBLE[1], LOOP]
            init = f'{fade(0.3, 0.6)}'
            op = "0"
        else:
            vals, ts = ["0", "0", "1", "1", "0", "0"], \
                [0, pre, t_in, t_out, t_out + 0.3, LOOP]
            init, op = "", "1"
        kt = ";".join(f"{t / LOOP:.4f}" for t in ts)
        out.append(
            f'<g opacity="{op}">{init}<text x="{x}" y="{y}" font-size="13" '
            f'fill="{color}" opacity="{"1" if pre is None else "0"}"><animate attributeName="opacity" '
            f'values="{";".join(vals)}" keyTimes="{kt}" dur="{LOOP}s" '
            f'begin="{LOOP_BEGIN}s" repeatCount="indefinite"/>'
            f'<tspan fill="{T["dim"]}">▸ render </tspan>{label}</text></g>'
        )
    return "".join(out)


def hero():
    W, H = 1180, 610
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{MONO}" role="img" '
         f'aria-label="{NAME} — {ROLE}">']
    p.append(
        f'<defs>{gradient("acc")}'
        f'<linearGradient id="face" x1="0" y1="0" x2="0" y2="{GRID}" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{T["primary"]}"/>'
        f'<stop offset="0.55" stop-color="{T["violet"]}"/>'
        f'<stop offset="1" stop-color="#818CF8"/></linearGradient>'
        f'<rect id="pt" width="1.9" height="1.9" rx="0.5"/>'
        f'<clipPath id="win"><rect x="1" y="1" width="{W - 2}" '
        f'height="{H - 2}" rx="16"/></clipPath></defs>'
    )
    p.append('<g clip-path="url(#win)">')
    p.append(f'<rect width="{W}" height="{H}" fill="{T["bg"]}"/>')

    # barra de ventana
    p.append(f'<rect width="{W}" height="44" fill="{T["bar"]}"/>')
    p.append(f'<line x1="0" y1="44" x2="{W}" y2="44" stroke="{T["border"]}"/>')
    for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        p.append(f'<circle cx="{28 + i * 20}" cy="22" r="6" fill="{c}"/>')
    p.append(f'<text x="{W / 2}" y="27" font-size="12" text-anchor="middle" '
             f'fill="{T["dim"]}">michael@mobile: ~/perfil — ./profile.sh --live'
             f'</text>')

    # panel visual
    vx, vy, vw, vh = 32, 64, 432, 524
    p.append(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="12" '
             f'fill="{T["panel"]}" stroke="{T["border"]}"/>')
    p.append(f'<text x="{vx + 16}" y="{vy + 24}" font-size="10" '
             f'letter-spacing="3" fill="{T["dim"]}">VISUAL</text>')
    p.append(f'<circle cx="{vx + vw - 18}" cy="{vy + 20}" r="3.5" '
             f'fill="{T["green"]}"><animate attributeName="opacity" '
             f'values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    p.append(visual(vx + 16, vy + 40))
    p.append(f'<line x1="{vx + 16}" y1="{vy + vh - 46}" x2="{vx + vw - 16}" '
             f'y2="{vy + vh - 46}" stroke="{T["border"]}"/>')
    p.append(caption(vx + 16, vy + vh - 20))

    # columna derecha: terminal
    x, prompt = 500, "➜  ~ "
    pw = mono_w(prompt, 16)
    tcur = 0.4

    def cmd(y, command):
        nonlocal tcur
        p.append(f'<g opacity="0">{fade(tcur, 0.1)}'
                 f'<text x="{x}" y="{y}" font-size="16" fill="{T["green"]}">'
                 f'{escape(prompt)}</text></g>')
        svg, tcur = typed(f"c{y}", x + pw, y, command, 16, T["text"], tcur)
        p.append(svg)
        tcur += 0.2

    cmd(92, "nombre")
    p.append(f'<g opacity="0">{fade(tcur, 0.6)}'
             f'<text x="{x}" y="140" font-size="40" font-weight="700" '
             f'font-family="{SANS}" fill="url(#acc)">{escape(NAME)}</text></g>')
    tcur += 0.5

    cmd(186, "rol")
    p.append(f'<g opacity="0">{fade(tcur)}'
             f'<text x="{x}" y="216" font-size="19" fill="{T["primary"]}">'
             f'{escape(ROLE)}</text></g>')
    tcur += 0.4

    cmd(258, "experiencia")
    for i, item in enumerate(FOCUS):
        p.append(f'<g opacity="0">{fade(tcur + i * 0.25)}'
                 f'<text x="{x}" y="{288 + i * 26}" font-size="15" '
                 f'fill="{T["muted"]}"><tspan fill="{T["violet"]}">▸ </tspan>'
                 f'{escape(item)}</text></g>')
    tcur += len(FOCUS) * 0.25 + 0.2

    # métricas
    p.append(f'<g opacity="0">{fade(tcur, 0.6)}')
    p.append(f'<line x1="{x}" y1="408" x2="{W - 32}" y2="408" '
             f'stroke="url(#acc)" stroke-width="1.5" opacity="0.8"/>')
    for i, (num, *label) in enumerate(METRICS):
        mx = x + i * 216
        p.append(f'<text x="{mx}" y="452" font-size="34" font-weight="700" '
                 f'font-family="{SANS}" fill="{T["text"]}">{num}</text>')
        for j, line in enumerate(label):
            p.append(f'<text x="{mx}" y="{472 + j * 15}" font-size="12" '
                     f'font-family="{SANS}" fill="{T["muted"]}">'
                     f'{escape(line)}</text>')
    p.append("</g>")
    tcur += 0.4

    # stack
    p.append(f'<g opacity="0">{fade(tcur, 0.6)}')
    rx, ry = x, 516
    for label in STACK:
        w = mono_w(label, 11) + 16
        if rx + w > W - 32:
            rx, ry = x, ry + 32
        svg, w = chip(rx, ry, label, size=11, pad=8)
        p.append(svg)
        rx += w + 6
    p.append("</g>")
    tcur += 0.5

    # prompt final con cursor
    p.append(f'<g opacity="0">{fade(tcur, 0.1)}'
             f'<text x="{x}" y="{H - 34}" font-size="16" fill="{T["green"]}">'
             f'{escape(prompt)}</text>'
             f'<rect x="{x + pw + 2:.0f}" y="{H - 48}" width="9" height="18" '
             f'fill="{T["primary"]}"><animate attributeName="opacity" '
             f'values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" '
             f'repeatCount="indefinite"/></rect></g>')
    p.append(f'<text x="{W - 32}" y="{H - 34}" font-size="11" '
             f'text-anchor="end" fill="{T["dim"]}">Lima, Perú</text>')

    p.append("</g>")
    p.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" '
             f'fill="none" stroke="{T["border"]}"/>')
    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------- proyectos


def projects():
    W, G = 1180, 20
    cols, ch = 3, 196
    cw = (W - 2 * G) / cols
    rows = (len(PROJECTS) + cols - 1) // cols
    H = 56 + rows * (ch + G) - G + 2
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" '
         f'viewBox="0 0 {W} {H:.0f}" font-family="{MONO}" role="img" '
         f'aria-label="Proyectos destacados">',
         f'<defs>{gradient("acc")}</defs>',
         f'<text x="5" y="20" font-size="12" letter-spacing="2" '
         f'fill="{T["primary"]}">PROYECTOS</text>',
         f'<text x="117" y="20" font-size="11" fill="{T["dim"]}">'
         f'github.com/VMichael1999</text>',
         f'<line x1="1" y1="34" x2="{W - 1}" y2="34" stroke="url(#acc)" '
         f'stroke-width="1.5" opacity="0.8"/>']

    for i, pr in enumerate(PROJECTS):
        x = 1 + (i % cols) * (cw + G)
        y = 54 + (i // cols) * (ch + G)
        w = cw - 2 if i % cols == cols - 1 else cw
        begin = 0.2 + i * 0.15
        p.append(f'<g opacity="0" transform="translate({x:.1f},{y})">'
                 f'{fade(begin, 0.5)}')
        p.append(f'<rect width="{w:.1f}" height="{ch}" rx="12" '
                 f'fill="{T["panel"]}" stroke="{T["border"]}"/>')
        p.append(f'<text x="18" y="30" font-size="11" fill="{T["dim"]}">'
                 f'VMichael1999 /</text>')
        p.append(f'<text x="18" y="56" font-size="18" font-weight="700" '
                 f'fill="{T["text"]}">{escape(pr["repo"])}</text>')
        p.append(f'<circle cx="{w - 22:.1f}" cy="26" r="4" fill="{T["green"]}">'
                 f'<animate attributeName="opacity" values="1;0.3;1" dur="2s" '
                 f'begin="{begin:.2f}s" repeatCount="indefinite"/></circle>')
        for j, line in enumerate(wrap(pr["desc"], 46)[:3]):
            p.append(f'<text x="18" y="{88 + j * 20}" font-size="13.5" '
                     f'font-family="{SANS}" fill="{T["muted"]}">'
                     f'{escape(line)}</text>')
        tx = 18
        for tag in pr["tags"]:
            svg, tw = chip(tx, ch - 40, tag, size=11, pad=9, color=T["violet"])
            p.append(svg)
            tx += tw + 6
        p.append("</g>")

    p.append("</svg>")
    return "".join(p)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "hero.svg").write_text(hero(), encoding="utf-8")
    (OUT / "projects.svg").write_text(projects(), encoding="utf-8")
    for f in ("hero.svg", "projects.svg"):
        print(f"{f}: {(OUT / f).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
