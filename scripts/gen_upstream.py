#!/usr/bin/env python3
"""Render a card of the upstream projects this account has contributed to.

Brand marks come from simple-icons and are inlined at generation time, so the
finished SVG has no external dependency when GitHub renders it.
"""
import json
import os
import re
import urllib.request
from html import escape

USER = "SaiPisey2"
API = "https://api.github.com"
ICON_CDN = "https://cdn.jsdelivr.net/npm/simple-icons@13/icons"
OUT = "metrics/upstream.svg"

BG = "#0d1117"
FG = "#e6edf3"
TITLE = "#58a6ff"
MUTED = "#8b949e"
BORDER = "#30363d"
TILE = "#161b22"

# Upstream repositories do not map onto icon slugs by name, so the mark and its
# brand colour are pinned per project. `None` falls back to a lettered tile.
BRAND = {
    "prometheus": ("prometheus", "#E6522C"),
    "prometheus-community": ("prometheus", "#E6522C"),
    "prometheus-operator": ("prometheus", "#E6522C"),
    "argoproj": ("argo", "#EF7B4D"),
    "traefik": ("traefikproxy", "#24A1C1"),
    "tektoncd": ("tekton", "#FD495C"),
    "metallb": ("kubernetes", "#326CE5"),
    "oauth2-proxy": (None, "#7B61FF"),
    "runatlantis": (None, "#5C4EE5"),
}


def api(path):
    req = urllib.request.Request(f"{API}{path}", headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-stats",
    })
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def icon_path(slug):
    """Return the `d` attribute of a simple-icons mark, or None if absent."""
    if not slug:
        return None
    try:
        with urllib.request.urlopen(f"{ICON_CDN}/{slug}.svg", timeout=30) as r:
            svg = r.read().decode()
    except Exception:
        return None
    m = re.search(r'\sd="([^"]+)"', svg)
    return m.group(1) if m else None


def collect():
    prs = api(f"/search/issues?q=is:pr+author:{USER}&per_page=100")
    projects = {}
    for item in prs["items"]:
        full = item["repository_url"].split("/repos/")[1]
        owner, name = full.split("/")
        if owner not in BRAND:      # own repos and private org work
            continue
        entry = projects.setdefault(full, {"owner": owner, "name": name, "prs": 0})
        entry["prs"] += 1
    return sorted(projects.values(), key=lambda p: (-p["prs"], p["name"]))


def render(projects, cols=3):
    pad, tile_w, tile_h, gap = 24, 268, 64, 14
    rows = (len(projects) + cols - 1) // cols
    width = pad * 2 + cols * tile_w + (cols - 1) * gap
    height = 78 + rows * (tile_h + gap) - gap + pad

    tiles = ""
    for i, p in enumerate(projects):
        col, row = i % cols, i // cols
        x = pad + col * (tile_w + gap)
        y = 78 + row * (tile_h + gap)
        slug, color = BRAND[p["owner"]]
        d = icon_path(slug)

        if d:
            # simple-icons marks are drawn on a 24x24 grid.
            size = 24
            mark = (f'<g transform="translate({x + 18},{y + 20}) '
                    f'scale({size / 24})"><path d="{d}" fill="{color}"/></g>')
        else:
            mark = (f'<circle cx="{x + 30}" cy="{y + 32}" r="12" fill="{color}"/>'
                    f'<text x="{x + 30}" y="{y + 37}" class="i" text-anchor="middle">'
                    f'{escape(p["name"][0].upper())}</text>')

        count = f'{p["prs"]} PR' + ("s" if p["prs"] > 1 else "")
        tiles += (
            f'<rect x="{x}" y="{y}" width="{tile_w}" height="{tile_h}" rx="8" '
            f'fill="{TILE}" stroke="{BORDER}"/>{mark}'
            f'<text x="{x + 56}" y="{y + 28}" class="n">{escape(p["name"])}</text>'
            f'<text x="{x + 56}" y="{y + 46}" class="o">{escape(p["owner"])}</text>'
            f'<text x="{x + tile_w - 16}" y="{y + 38}" class="c" '
            f'text-anchor="end">{count}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Upstream projects contributed to">
  <style>
    .t {{ font: 600 17px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .s {{ font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {MUTED}; }}
    .n {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {FG}; }}
    .o {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {MUTED}; }}
    .c {{ font: 600 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .i {{ font: 700 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <text x="24" y="34" class="t">Upstream Projects</text>
  <text x="24" y="54" class="s">Open source contributions to CNCF and cloud native projects</text>
  {tiles}
</svg>
'''


if __name__ == "__main__":
    os.makedirs("metrics", exist_ok=True)
    projects = collect()
    open(OUT, "w").write(render(projects))
    for p in projects:
        print(f'{p["owner"]}/{p["name"]}: {p["prs"]}')
