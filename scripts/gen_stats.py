#!/usr/bin/env python3
"""Render profile stat cards from GitHub's public REST API.

Public endpoints need no authentication, so this has no token to expire and
no third-party service in the render path. Uses GITHUB_TOKEN when the
workflow provides one, purely to lift the rate limit.
"""
import json
import os
import urllib.request
from html import escape

USER = "SaiPisey2"
# Repositories holding a copy of an upstream project rather than original work.
# GitHub does not mark these as forks, so they have to be named explicitly or
# their vendored code drowns out everything actually written here.
EXCLUDE = {"kong"}
API = "https://api.github.com"
OUT = "metrics"

BG = "#0d1117"
FG = "#c9d1d9"
TITLE = "#58a6ff"
MUTED = "#8b949e"
BORDER = "#30363d"

PALETTE = {
    "Python": "#3572A5", "Go": "#00ADD8", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "HCL": "#844FBA", "Shell": "#89e051",
    "HTML": "#e34c26", "CSS": "#563d7c", "C++": "#f34b7d", "C": "#555555",
    "Java": "#b07219", "Ruby": "#701516", "Rust": "#dea584",
    "Dockerfile": "#384d54", "Makefile": "#427819", "Smarty": "#f0c040",
    "Jinja": "#a52a22", "Mustache": "#724b3b", "PowerShell": "#012456",
}
FALLBACK = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff",
            "#39c5cf", "#db61a2", "#a371f7"]


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-stats",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    repos, page = [], 1
    while True:
        batch = get(f"{API}/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos += batch
        if len(batch) < 100:
            break
        page += 1

    own = [r for r in repos
           if not r["fork"] and not r["archived"] and r["name"] not in EXCLUDE]
    langs = {}
    for r in own:
        for name, size in get(r["languages_url"]).items():
            langs[name] = langs.get(name, 0) + size

    prs = get(f"{API}/search/issues?q=is:pr+author:{USER}&per_page=100")
    merged = get(f"{API}/search/issues?q=is:pr+author:{USER}+is:merged&per_page=1")

    # An upstream project is any repository owned by someone else.
    upstream = {
        item["repository_url"].split("/repos/")[1].split("/")[0]
        for item in prs["items"]
    } - {USER}

    return {
        "repos": len(own),
        "prs": prs["total_count"],
        "merged": merged["total_count"],
        "upstream": len(upstream),
        "langs": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        "bytes": sum(langs.values()),
    }


def human(n):
    for unit in ("B", "kB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def card(width, height, title, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <style>
    .t {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .k {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {FG}; }}
    .v {{ font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .m {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {MUTED}; }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{BG}" stroke="{BORDER}"/>
  <text x="24" y="34" class="t">{escape(title)}</text>
  {body}
</svg>
'''


def stats_card(d):
    rows = [
        ("Pull requests opened", f'{d["prs"]}'),
        ("Pull requests merged", f'{d["merged"]}'),
        ("Upstream projects", f'{d["upstream"]}'),
        ("Public repositories", f'{d["repos"]}'),
        ("Languages used", f'{len(d["langs"])}'),
        ("Code written", human(d["bytes"])),
    ]
    body = "".join(
        f'<text x="24" y="{68 + i * 26}" class="k">{escape(k)}</text>'
        f'<text x="276" y="{68 + i * 26}" class="v" text-anchor="end">{escape(v)}</text>'
        for i, (k, v) in enumerate(rows)
    )
    return card(300, 68 + len(rows) * 26, "Open Source Activity", body)


def lang_card(d, limit=8):
    top = list(d["langs"].items())[:limit]
    total = sum(v for _, v in top) or 1
    colors = {}
    for i, (name, _) in enumerate(top):
        colors[name] = PALETTE.get(name, FALLBACK[i % len(FALLBACK)])

    x, bar = 24, ""
    for name, size in top:
        w = (size / total) * 252
        bar += f'<rect x="{x:.1f}" y="52" width="{w:.1f}" height="10" fill="{colors[name]}"/>'
        x += w

    legend = ""
    for i, (name, size) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 132, 92 + row * 24
        pct = size / total * 100
        legend += (
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{colors[name]}"/>'
            f'<text x="{lx + 18}" y="{ly}" class="k">{escape(name)}</text>'
            f'<text x="{lx + 118}" y="{ly}" class="m" text-anchor="end">{pct:.1f}%</text>'
        )

    rows = (len(top) + 1) // 2
    return card(300, 92 + rows * 24 + 8, "Most Used Languages", bar + legend)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    data = collect()
    open(f"{OUT}/stats.svg", "w").write(stats_card(data))
    open(f"{OUT}/languages.svg", "w").write(lang_card(data))
    print(json.dumps({k: v for k, v in data.items() if k != "langs"}, indent=2))
    print("top languages:", list(data["langs"].items())[:8])
