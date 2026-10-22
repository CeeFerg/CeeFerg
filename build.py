#!/usr/bin/env python3
"""Build the neofetch-style profile card (dark_mode.svg + light_mode.svg).

Run locally:   python3 build.py
In the Action: same, with HONEYPOT_STATS_URL set as a repo variable.

Live honeypot numbers come from a public JSON URL (aggregate counts only,
never attacker IPs). If the URL is unset or unreachable, the last good
values in stats-cache.json are reused so the card never breaks.
"""

import json
import os
import urllib.request
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------- settings
HONEYPOT_LIVE_SINCE = date(2026, 9, 6)   # day the Cowrie sensor went live
STATS_URL = os.environ.get("HONEYPOT_STATS_URL", "").strip()

# Key names in your JSON -> card fields. Change the right-hand side to match
# whatever your heatmap pipeline already publishes.
JSON_KEYS = {
    "total": "total_sessions",
    "day": "sessions_24h",
    "country": "top_country",
}

LINE_WIDTH = 56          # characters per info line (dots pad to this)
INFO_FONT = 16           # px
INFO_STEP = 20           # px between info lines
ASCII_FONT = 10          # px
ASCII_STEP = 12.6        # px between ASCII rows
CHAR_W = 0.602           # monospace advance width as a fraction of font size

# ------------------------------------------------------------------ colours
# (background, text, key, value, dots, accent) per GitHub theme
THEMES = {
    "dark":  ("#161b22", "#c9d1d9", "#ffa657", "#a5d6ff", "#616e7f", "#39ff14"),
    "light": ("#f6f8fa", "#24292f", "#953800", "#0a3069", "#8c959f", "#1a7f37"),
}


# ------------------------------------------------------------------- stats
def load_stats():
    cache = HERE / "stats-cache.json"
    stats = json.loads(cache.read_text()) if cache.exists() else {}
    if STATS_URL:
        try:
            req = urllib.request.Request(STATS_URL, headers={"User-Agent": "profile-card"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            fresh = {k: data[v] for k, v in JSON_KEYS.items() if v in data}
            if fresh:
                stats.update(fresh)
                cache.write_text(json.dumps(stats, indent=2) + "\n")
        except Exception as e:  # keep the cached values
            print(f"stats fetch failed, using cache: {e}")
    return stats


def fmt_num(v):
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "—"


# -------------------------------------------------------------------- card
def build():
    s = load_stats()
    for theme, colours in THEMES.items():
        render(s, theme, colours)


def render(s, theme, colours):
    BG, TEXT, KEY, VALUE, DOTS, ACCENT = colours
    days_up = (datetime.now(timezone.utc).date() - HONEYPOT_LIVE_SINCE).days

    # Each entry: ("kv", key, value) | ("header", title) | ("blank",)
    lines = [
        ("title", "curtis@homelab"),
        ("kv", "OS", "Fedora 44 KDE Plasma"),
        ("kv", "Host", "Proxmox VE homelab"),
        ("kv", "Kernel", "Cybersecurity graduate (NSCC)"),
        ("kv", "Shell", "bash"),
        ("kv", "Learning", "C, Python, Active Directory"),
        ("blank",),
        ("kv", "Focus.Defence", "Monitoring, logs, hardening"),
        ("kv", "Focus.Offence", "Pentesting, CTFs"),
        ("kv", "Lab.Stack", "Wazuh, Cowrie, AD domain, LFS"),
        ("blank",),
        ("header", "Honeypot"),
        ("kv", "Sensor", "Cowrie SSH, live"),
        ("kv", "Uptime", f"{days_up} days"),
        ("kv", "Campaigns.Tracked", "Mirai, RedTail, Outlaw, +1"),
        ("blank",),
        ("header", "Contact"),
        ("kv", "Portfolio", "curtisferguson.ca"),
        ("kv", "LinkedIn", "curtiswferguson"),
        ("kv", "Email", "curtiscyber@outlook.com"),
        ("kv", "GitHub", "CeeFerg"),
    ]

    # Live honeypot lines appear only once the stats URL has delivered data
    if s.get("total") is not None:
        i = lines.index(("kv", "Uptime", f"{days_up} days")) + 1
        lines[i:i] = [
            ("kv2", "Sessions", fmt_num(s.get("total")), "Last.24h", fmt_num(s.get("day"))),
            ("kv", "Top.Source", str(s.get("country", "—"))),
        ]

    # ASCII art: drop blank rows and the shared left margin
    rows = [r.rstrip() for r in (HERE / "ascii-art.txt").read_text().splitlines()]
    rows = [r for r in rows if r.strip()]
    margin = min(len(r) - len(r.lstrip()) for r in rows)
    rows = [r[margin:] for r in rows]
    art_w = max(len(r) for r in rows) * ASCII_FONT * CHAR_W

    pad = 20
    info_x = pad + art_w + 30
    info_w = LINE_WIDTH * INFO_FONT * CHAR_W
    width = round(info_x + info_w + pad + 25)
    info_h = pad + 12 + len(lines) * INFO_STEP
    art_h = pad + 8 + len(rows) * ASCII_STEP
    height = round(max(info_h, art_h) + pad)

    # vertically centre the art against the info block
    art_y0 = (height - len(rows) * ASCII_STEP) / 2 + ASCII_STEP * 0.8

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        'font-family="Consolas,\'DejaVu Sans Mono\',\'Liberation Mono\',Menlo,monospace" '
        'xml:space="preserve">',
        "<style>",
        f".k{{fill:{KEY}}} .v{{fill:{VALUE}}} .d{{fill:{DOTS}}} .a{{fill:{ACCENT}}}",
        "text,tspan{white-space:pre}",
        "</style>",
        f'<rect width="{width}" height="{height}" fill="{BG}" rx="15"/>',
        f'<text font-size="{ASCII_FONT}" fill="{ACCENT}" opacity="0.9">',
    ]
    for i, r in enumerate(rows):
        out.append(f'<tspan x="{pad}" y="{art_y0 + i * ASCII_STEP:.1f}">{escape(r)}</tspan>')
    out.append("</text>")

    out.append(f'<text font-size="{INFO_FONT}" fill="{TEXT}">')
    y = pad + 16
    for ln in lines:
        kind = ln[0]
        if kind == "title":
            rule = "—" * (LINE_WIDTH - len(ln[1]) - 1)
            out.append(f'<tspan x="{info_x:.0f}" y="{y}" class="a">{ln[1]}</tspan>'
                       f'<tspan class="d"> {rule}</tspan>')
        elif kind == "header":
            label = f"- {ln[1]} "
            rule = "—" * (LINE_WIDTH - len(label))
            out.append(f'<tspan x="{info_x:.0f}" y="{y}">{label}</tspan>'
                       f'<tspan class="d">{rule}</tspan>')
        elif kind == "blank":
            out.append(f'<tspan x="{info_x:.0f}" y="{y}" class="d">.</tspan>')
        elif kind == "kv":
            out.append(kv_line(info_x, y, ln[1], ln[2]))
        elif kind == "kv2":
            out.append(kv2_line(info_x, y, ln[1], ln[2], ln[3], ln[4]))
        y += INFO_STEP
    out.append("</text></svg>")

    name = f"{theme}_mode.svg"
    (HERE / name).write_text("\n".join(out) + "\n")
    print(f"wrote {name} ({width}x{height})")


def key_spans(key):
    parts = key.split(".")
    return '<tspan>.</tspan>'.join(f'<tspan class="k">{escape(p)}</tspan>' for p in parts)


def kv_line(x, y, key, value):
    # ". Key: ....... value"  padded to LINE_WIDTH
    used = 2 + len(key) + 1 + 2 + len(value)
    dots = "." * max(1, LINE_WIDTH - used)
    return (f'<tspan x="{x:.0f}" y="{y}" class="d">. </tspan>{key_spans(key)}:'
            f'<tspan class="d"> {dots} </tspan><tspan class="v">{escape(value)}</tspan>')


def kv2_line(x, y, k1, v1, k2, v2):
    # ". K1: .. v1 | K2: .... v2" with the bar at a fixed column
    half = LINE_WIDTH // 2 + 2
    left_used = 2 + len(k1) + 1 + 2 + len(v1)
    d1 = "." * max(1, half - left_used)
    right_used = 3 + len(k2) + 1 + 2 + len(v2)
    d2 = "." * max(1, LINE_WIDTH - (half + 1) - right_used + 1)
    return (f'<tspan x="{x:.0f}" y="{y}" class="d">. </tspan>{key_spans(k1)}:'
            f'<tspan class="d"> {d1} </tspan><tspan class="v">{escape(v1)}</tspan>'
            f' | {key_spans(k2)}:<tspan class="d"> {d2} </tspan>'
            f'<tspan class="v">{escape(v2)}</tspan>')


if __name__ == "__main__":
    build()
