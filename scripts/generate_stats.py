"""Genera las tarjetas de estadísticas y lenguajes (tema oscuro).

Usa solo la API pública de GitHub. Con la variable GH_TOKEN definida
(en la Action) el límite de peticiones es mayor.

Uso:  python3 scripts/generate_stats.py [carpeta_salida]
Salida: stats.svg, langs.svg
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

USER = "VMichael1999"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    Path(__file__).resolve().parent.parent / "assets"

# código generado por las plantillas de Flutter/iOS que no refleja lo que escribo
IGNORED_LANGS = {"CMake", "C", "C++", "Objective-C", "Ruby", "Shell",
                 "Batchfile", "Makefile", "Dockerfile", "Procfile", "Groovy",
                 "Go Template", "Mustache", "Starlark"}
LANG_COLORS = {
    "Dart": "#00B4AB", "TypeScript": "#3178C6", "JavaScript": "#F1E05A",
    "Kotlin": "#A97BFF", "Swift": "#F05138", "Java": "#B07219",
    "C#": "#178600", "Python": "#3572A5", "HTML": "#E34C26",
    "CSS": "#663399", "SCSS": "#C6538C", "Go": "#00ADD8", "Vue": "#41B883",
}

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
T = {
    "bg": "#0B1120", "panel": "#0F172A", "border": "#1E293B",
    "text": "#E2E8F0", "muted": "#94A3B8", "dim": "#64748B",
    "primary": "#38BDF8", "violet": "#A78BFA", "green": "#34D399",
    "track": "#1E293B",
}
W, H = 580, 250


def get(url, raw=False):
    headers = {"User-Agent": USER}
    token = os.environ.get("GH_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                timeout=30) as r:
        body = r.read().decode("utf-8")
    return body if raw else json.loads(body)


def search_count(q):
    return get(f"https://api.github.com/search/issues?q={q}&per_page=1")[
        "total_count"]


def collect():
    repos = [r for r in get(f"https://api.github.com/users/{USER}/repos"
                            f"?per_page=100&type=owner")
             if not r["fork"]]
    # peso = √bytes × √repos, para que un repo enorme no tape al resto
    size, count = {}, {}
    for r in repos:
        for lang, n in get(r["languages_url"]).items():
            if lang not in IGNORED_LANGS:
                size[lang] = size.get(lang, 0) + n
                count[lang] = count.get(lang, 0) + 1
    langs = {k: (size[k] ** 0.5) * (count[k] ** 0.5) for k in size}
    user = get(f"https://api.github.com/users/{USER}")
    years = max(1, date.today().year - int(user["created_at"][:4]))

    html = get(f"https://github.com/users/{USER}/contributions", raw=True)
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    contributions = int(m.group(1).replace(",", "")) if m else 0

    commits = get(f"https://api.github.com/search/commits?q=author:{USER}"
                  f"&per_page=1")["total_count"]
    return {
        "contributions": contributions,
        "commits": commits,
        "prs": search_count(f"author:{USER}+type:pr"),
        "issues": search_count(f"author:{USER}+type:issue"),
        "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "years": years,
        "langs": langs,
    }


def frame(title, subtitle, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{MONO}" role="img" '
        f'aria-label="{escape(title)}">'
        f'<defs><linearGradient id="acc" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{T["primary"]}"/>'
        f'<stop offset="1" stop-color="{T["violet"]}"/></linearGradient>'
        f'</defs>'
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" '
        f'fill="{T["bg"]}" stroke="{T["border"]}"/>'
        f'<text x="24" y="34" font-size="11" letter-spacing="2" '
        f'fill="{T["primary"]}">{escape(title)}</text>'
        f'<text x="{W - 24}" y="34" font-size="11" text-anchor="end" '
        f'fill="{T["dim"]}">{escape(subtitle)}</text>'
        f'<line x1="24" y1="48" x2="{W - 24}" y2="48" stroke="url(#acc)" '
        f'stroke-width="1.5" opacity="0.8"/>'
        f'{body}</svg>'
    )


def stats_card(d):
    rows = [
        ("Repositorios públicos", d["repos"]),
        ("Lenguajes usados", len(d["langs"])),
        ("Pull requests", d["prs"]),
        ("Estrellas", d["stars"]),
        ("Issues", d["issues"]),
        ("Años en GitHub", d["years"]),
    ]
    # solo las métricas con valor, hasta 5 filas
    palette = [T["primary"], T["violet"], T["green"]]
    rows = [(label, value, palette[i % 3]) for i, (label, value)
            in enumerate([r for r in rows if r[1] > 0][:5])]
    body = []
    for i, (label, value, color) in enumerate(rows):
        y = 84 + (5 - len(rows)) * 16 + i * 32  # centradas en vertical
        body.append(
            f'<g>'
            f'<rect x="24" y="{y - 10}" width="8" height="8" rx="2" '
            f'fill="{color}"/>'
            f'<text x="44" y="{y}" font-size="14" fill="{T["muted"]}">'
            f'{escape(label)}</text>'
            f'<text x="300" y="{y}" font-size="14" font-weight="700" '
            f'text-anchor="end" fill="{T["text"]}">{value:,}</text></g>'
        )
    # anillo con los commits (las contribuciones ya salen en la racha)
    cx, cy, r = 450, 145, 64
    body.append(
        f'<g>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="{T["track"]}" stroke-width="8"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#acc)" '
        f'stroke-width="8" stroke-linecap="round" '
        f'transform="rotate(-90 {cx} {cy})">'
        f'</circle>'
        f'<text x="{cx}" y="{cy + 6}" font-size="30" font-weight="700" '
        f'font-family="{SANS}" text-anchor="middle" fill="{T["text"]}">'
        f'{d["commits"]:,}</text>'
        f'<text x="{cx}" y="{cy + 26}" font-size="10" text-anchor="middle" '
        f'fill="{T["muted"]}">commits</text>'
        f'<text x="{cx}" y="{cy + 94}" font-size="10" text-anchor="middle" '
        f'fill="{T["dim"]}">públicos</text></g>'
    )
    return frame("ESTADÍSTICAS", f"github.com/{USER}", "".join(body))


def langs_card(d, top=8):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:top]
    total = sum(v for _, v in items) or 1
    body = []
    # barra apilada
    x, bw = 24, W - 48
    body.append(f'<clipPath id="bar"><rect x="24" y="72" width="{bw}" '
                f'height="10" rx="5"/></clipPath>'
                f'<rect x="24" y="72" width="{bw}" height="10" rx="5" '
                f'fill="{T["track"]}"/><g clip-path="url(#bar)">')
    for lang, size in items:
        w = bw * size / total
        body.append(f'<rect x="{x:.1f}" y="72" width="{w + 0.5:.1f}" '
                    f'height="10" fill="{LANG_COLORS.get(lang, T["dim"])}"/>')
        x += w
    body.append("</g>")
    # leyenda en dos columnas
    for i, (lang, size) in enumerate(items):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 272, 122 + row * 32
        pct = 100 * size / total
        color = LANG_COLORS.get(lang, T["dim"])
        body.append(
            f'<g>'
            f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" font-size="14" fill="{T["text"]}">'
            f'{escape(lang)}</text>'
            f'<text x="{lx + 248}" y="{ly}" font-size="13" text-anchor="end" '
            f'fill="{T["muted"]}">{pct:.1f}%</text></g>'
        )
    return frame("LENGUAJES", "repos propios",
                 "".join(body))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "stats.json"
    # STATS_CACHE=1 redibuja con los datos guardados sin llamar a la API
    if os.environ.get("STATS_CACHE") and cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
    else:
        d = collect()
        cache.write_text(json.dumps(d), encoding="utf-8")
    (OUT / "stats.svg").write_text(stats_card(d), encoding="utf-8")
    (OUT / "langs.svg").write_text(langs_card(d), encoding="utf-8")
    print(json.dumps({k: v for k, v in d.items() if k != "langs"}))
    print(sorted(d["langs"].items(), key=lambda kv: -kv[1])[:8])


if __name__ == "__main__":
    main()
