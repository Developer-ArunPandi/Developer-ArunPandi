"""
Daily GFG activity tracker + heatmap generator.

GeeksforGeeks does not publish per-day submission history anywhere public,
so this script builds real history GOING FORWARD: every day it records your
current total-solved count, diffs it against yesterday's count to estimate
how many problems you solved *that day*, and renders a GitHub-style heatmap
SVG from the accumulated data.

Data file (data/gfg-activity.json) grows by one entry per day this Action
runs. The heatmap will be empty/flat until a few days of history exist.
"""

import json
import os
from datetime import date, timedelta

import requests

USERNAME = os.environ.get("GFG_USERNAME", "developeuw2s")
DATA_FILE = "data/gfg-activity.json"
OUTPUT_SVG = "dist/gfg-heatmap.svg"

# Unofficial GFG scrapers - tried in order, first success wins.
# These can break if GFG changes their site structure.
API_URLS = [
    f"https://geeks-for-geeks-api.vercel.app/{USERNAME}",
    f"https://gfg-api-fefa.onrender.com/{USERNAME}",
]

FIELD_CANDIDATES = ["totalProblemsSolved", "totalSolved", "total_problems_solved", "totalSolvedProblems"]


def fetch_total_solved():
    last_error = None
    for url in API_URLS:
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            payload = r.json()
            for container in (payload, payload.get("info", {}), payload.get("data", {})):
                if not isinstance(container, dict):
                    continue
                for key in FIELD_CANDIDATES:
                    if key in container and container[key] not in (None, ""):
                        return int(container[key])
        except Exception as e:  # noqa: BLE001
            last_error = e
            print(f"[warn] {url} failed: {e}")
    raise RuntimeError(f"Could not fetch GFG stats from any known source. Last error: {last_error}")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def compute_deltas(data):
    """Map date -> problems solved that day (best-effort, floor at 0)."""
    days = sorted(data.keys())
    deltas = {}
    prev_total = None
    for d in days:
        total = data[d]
        deltas[d] = 0 if prev_total is None else max(0, total - prev_total)
        prev_total = total
    return deltas


def color_for(count):
    # Neon purple/cyan scale to match a dark cyberpunk theme
    if count <= 0:
        return "#161b22"
    if count == 1:
        return "#3b1e5e"
    if count <= 3:
        return "#6a2fb0"
    if count <= 6:
        return "#a239f7"
    return "#00f5ff"


def generate_svg(deltas, weeks=26):
    today = date.today()
    # Align to the most recent Sunday so columns read like GitHub's grid
    end = today
    start = end - timedelta(days=weeks * 7 - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back up to Sunday

    cell = 11
    gap = 3
    top_pad = 20
    left_pad = 10

    total_days = (end - start).days + 1
    num_weeks = -(-total_days // 7)  # ceil

    width = left_pad * 2 + num_weeks * (cell + gap)
    height = top_pad + 7 * (cell + gap) + 10

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Fira Code, monospace">',
        f'<rect width="100%" height="100%" fill="#0d1117" rx="8"/>',
        f'<text x="{left_pad}" y="14" fill="#B829F7" font-size="12" font-weight="600">'
        f'GeeksforGeeks Activity (tracked since setup)</text>',
    ]

    d = start
    week_idx = 0
    while d <= end:
        day_of_week = (d.weekday() + 1) % 7  # Sunday = 0
        x = left_pad + week_idx * (cell + gap)
        y = top_pad + day_of_week * (cell + gap)
        key = d.isoformat()
        count = deltas.get(key, 0)
        fill = color_for(count) if key in deltas else "#0d1117"
        stroke = "#21262d" if key not in deltas else "none"
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1">'
            f'<title>{key}: {count} solved</title></rect>'
        )
        if day_of_week == 6:
            week_idx += 1
        d += timedelta(days=1)

    svg_parts.append("</svg>")

    os.makedirs(os.path.dirname(OUTPUT_SVG), exist_ok=True)
    with open(OUTPUT_SVG, "w") as f:
        f.write("\n".join(svg_parts))


def main():
    today_key = date.today().isoformat()
    total = fetch_total_solved()

    data = load_data()
    data[today_key] = total
    save_data(data)

    deltas = compute_deltas(data)
    generate_svg(deltas)
    print(f"Recorded {today_key}: total_solved={total}. Heatmap written to {OUTPUT_SVG}")


if __name__ == "__main__":
    main()
