"""Render the last year of GitHub contributions as an oscilloscope trace.

    GITHUB_TOKEN=... python scripts/activity_scope.py [assets]
    python scripts/activity_scope.py assets --demo     # random data, for styling

Runs daily from .github/workflows/activity-scope.yml. Weekly totals are drawn
as a step trace on a scope graticule; the beam sweeps, holds, and re-triggers.
"""

import datetime as dt
import json
import os
import random
import sys
import urllib.request

USER = os.environ.get("GH_USER", "OfirSipp")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT_DIR = ARGS[0] if ARGS else "assets"
DEMO = "--demo" in sys.argv

BG, DEEP, PANEL = "#0d1117", "#080b10", "#161b22"
BORDER, GRID, GRID_HI = "#30363d", "#161c24", "#232b36"
TEXT, MUTED, DIM = "#e6edf3", "#8b949e", "#6e7681"
ACCENT, AMBER = "#2dd4bf", "#f0b429"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

W, H = 1200, 320
SX0, SX1, SY0, SY1 = 64, 1136, 70, 262          # screen
BASE, CEIL = SY1 - 14, SY0 + 18                  # trace range
DIV_X, DIV_Y = 12, 6
SWEEP = 9.0                                      # seconds per sweep cycle

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def demo():
    rnd = random.Random(42)
    start = dt.date.today() - dt.timedelta(days=dt.date.today().weekday() + 1 + 52 * 7)
    weeks = []
    for w in range(53):
        days = []
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            n = rnd.choice([0, 0, 0, 1, 2, 3, 5]) if rnd.random() < 0.6 else 0
            days.append({"date": day.isoformat(), "contributionCount": n})
        weeks.append({"contributionDays": days})
    return {"totalContributions": sum(d["contributionCount"] for w in weeks for d in w["contributionDays"]), "weeks": weeks}


def empty():
    start = dt.date.today() - dt.timedelta(days=dt.date.today().weekday() + 1 + 52 * 7)
    weeks = [{"contributionDays": [{"date": (start + dt.timedelta(days=w * 7 + d)).isoformat(), "contributionCount": 0}
                                   for d in range(7)]} for w in range(53)]
    return {"totalContributions": 0, "weeks": weeks}


def f(x):
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def render(cal):
    weeks = cal["weeks"]
    counts = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    days = [d for w in weeks for d in w["contributionDays"]]
    total = cal["totalContributions"]
    peak = max(counts) if counts else 0
    active = sum(1 for d in days if d["contributionCount"] > 0)

    n = len(counts)
    sw = (SX1 - SX0) / n
    y_of = lambda c: BASE - (c / peak) * (BASE - CEIL) if peak else BASE

    trace = [f"M{SX0} {f(y_of(counts[0]))}"]
    x = SX0
    prev = None
    for c in counts:
        y = y_of(c)
        if prev is not None and y != prev:
            trace.append(f"V{f(y)}")
        x += sw
        trace.append(f"H{f(x)}")
        prev = y
    trace_d = "".join(trace)
    area_d = f"{trace_d}V{BASE}H{SX0}Z"

    # graticule
    gx = (SX1 - SX0) / DIV_X
    gy = (SY1 - SY0) / DIV_Y
    grid = "".join(f'<line x1="{f(SX0 + i * gx)}" y1="{SY0}" x2="{f(SX0 + i * gx)}" y2="{SY1}"/>' for i in range(1, DIV_X))
    grid += "".join(f'<line x1="{SX0}" y1="{f(SY0 + j * gy)}" x2="{SX1}" y2="{f(SY0 + j * gy)}"/>' for j in range(1, DIV_Y))
    cxm, cym = (SX0 + SX1) / 2, (SY0 + SY1) / 2
    ticks = "".join(f'<line x1="{f(SX0 + i * gx / 5)}" y1="{f(cym - 3)}" x2="{f(SX0 + i * gx / 5)}" y2="{f(cym + 3)}"/>'
                    for i in range(1, DIV_X * 5) if i % 5)
    ticks += "".join(f'<line x1="{f(cxm - 3)}" y1="{f(SY0 + j * gy / 5)}" x2="{f(cxm + 3)}" y2="{f(SY0 + j * gy / 5)}"/>'
                     for j in range(1, DIV_Y * 5) if j % 5)

    months, last = [], None
    for i, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last:
            if i > 0 and i < n - 2:
                months.append(f'<text x="{f(SX0 + i * sw)}" y="{SY1 + 20}">{first.strftime("%b")}</text>')
            last = first.month

    quiet = "" if total else (
        f'<text x="{f(cxm)}" y="{f(cym - 10)}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{DIM}">'
        f'no signal yet · waiting for first commits</text>')

    reveal_kt = "0;0.45;1"
    updated = dt.date.today().isoformat()
    readout = f"Σ {total}   ·   peak {peak}/wk   ·   {active} active days"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year, drawn as an oscilloscope trace">
  <defs>
    <filter id="glow" x="-10%" y="-40%" width="120%" height="180%">
      <feGaussianBlur stdDeviation="2.4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="area" x1="0" y1="{CEIL}" x2="0" y2="{BASE}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity="0.32"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0.02"/>
    </linearGradient>
    <clipPath id="sweep">
      <rect x="{SX0}" y="{SY0}" width="0" height="{SY1 - SY0}">
        <animate attributeName="width" values="0;{SX1 - SX0};{SX1 - SX0}" keyTimes="{reveal_kt}" dur="{SWEEP}s" repeatCount="indefinite"/>
      </rect>
    </clipPath>
  </defs>

  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>

  <rect x="64" y="30" width="3" height="20" fill="{ACCENT}"/>
  <text x="78" y="47" font-family="{SANS}" font-size="20" fill="{TEXT}"><tspan font-weight="600">Activity</tspan><tspan fill="{MUTED}">, on the scope</tspan></text>
  <text x="{SX1}" y="47" font-family="{MONO}" font-size="12.5" fill="{MUTED}" text-anchor="end" xml:space="preserve">{readout}</text>

  <rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}" rx="6" fill="{DEEP}" stroke="{BORDER}"/>
  <g stroke="{GRID}">{grid}</g>
  <g stroke="{GRID_HI}">
    <line x1="{SX0}" y1="{f(cym)}" x2="{SX1}" y2="{f(cym)}"/>
    <line x1="{f(cxm)}" y1="{SY0}" x2="{f(cxm)}" y2="{SY1}"/>
    {ticks}
  </g>
  {quiet}

  <!-- channel + trigger markers -->
  <path d="M{SX0 - 14} {BASE - 6}H{SX0 - 6}L{SX0 - 1} {BASE}L{SX0 - 6} {BASE + 6}H{SX0 - 14}Z" fill="{ACCENT}"/>
  <text x="{SX0 - 11}" y="{BASE + 3.5}" font-family="{MONO}" font-size="9" font-weight="700" fill="{BG}" text-anchor="middle">1</text>
  <path d="M{SX1 + 1} {f(cym)}L{SX1 + 9} {f(cym - 6)}V{f(cym + 6)}Z" fill="{AMBER}"/>
  <text x="{SX1 + 13}" y="{f(cym + 4)}" font-family="{MONO}" font-size="10" fill="{AMBER}">T</text>

  <!-- trace -->
  <g>
    <animate attributeName="opacity" values="1;1;0.35;0;1" keyTimes="0;0.86;0.95;0.99;1" dur="{SWEEP}s" repeatCount="indefinite"/>
    <g clip-path="url(#sweep)">
      <path d="{area_d}" fill="url(#area)"/>
      <path d="{trace_d}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linejoin="round" filter="url(#glow)"/>
    </g>
  </g>
  <rect x="{SX0}" y="{SY0 + 1}" width="2" height="{SY1 - SY0 - 2}" fill="{ACCENT}" filter="url(#glow)" opacity="0">
    <animate attributeName="x" values="{SX0};{SX1 - 2};{SX1 - 2}" keyTimes="{reveal_kt}" dur="{SWEEP}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.9;0.9;0;0" keyTimes="0;0.45;0.47;1" dur="{SWEEP}s" repeatCount="indefinite"/>
  </rect>

  <g font-family="{MONO}" font-size="11" fill="{DIM}">
    {"".join(months)}
    <text x="{SX0}" y="{H - 16}">updated {updated} · re-rendered daily by GitHub Actions</text>
    <text x="{SX1}" y="{H - 16}" text-anchor="end">CH1 commits / week  ·  ≈1 month / div</text>
  </g>
</svg>
'''


def main():
    cal = demo() if DEMO else (fetch() or empty())
    path = os.path.join(OUT_DIR, "activity.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(cal))
    print(f"{cal['totalContributions']} contributions -> {path}")


if __name__ == "__main__":
    main()
