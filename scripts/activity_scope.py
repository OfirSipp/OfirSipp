"""Render the last year of GitHub contributions as an oscilloscope trace.

    GITHUB_TOKEN=... python scripts/activity_scope.py [assets]
    python scripts/activity_scope.py assets --demo     # random data, for styling

Runs daily from .github/workflows/activity-scope.yml. The window runs from
account creation (or a year back) to today: CH1 is contributions per day (per
week once the window passes ~4 months), CH2 is the running total. The beam
sweeps, holds, and re-triggers.
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
    createdAt
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
    user = data["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    cal["createdAt"] = user["createdAt"][:10]
    return cal


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
    created = (dt.date.today() - dt.timedelta(days=40)).isoformat()
    for w in weeks:
        for d in w["contributionDays"]:
            if d["date"] < created:
                d["contributionCount"] = 0
    return {"totalContributions": sum(d["contributionCount"] for w in weeks for d in w["contributionDays"]),
            "weeks": weeks, "createdAt": created}


def empty():
    start = dt.date.today() - dt.timedelta(days=dt.date.today().weekday() + 1 + 52 * 7)
    weeks = [{"contributionDays": [{"date": (start + dt.timedelta(days=w * 7 + d)).isoformat(), "contributionCount": 0}
                                   for d in range(7)]} for w in range(53)]
    return {"totalContributions": 0, "weeks": weeks}


def f(x):
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


MIN_SPAN = 21            # days; a brand-new account still gets a readable window
DAILY_MAX = 120          # beyond this many days, bin by week


def window(cal):
    """Chronological (date, count) pairs from account creation (or a year ago) to today."""
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort()
    today = days[-1][0]
    created = dt.date.fromisoformat(cal.get("createdAt") or days[0][0].isoformat())
    start = max(min(created, today - dt.timedelta(days=MIN_SPAN - 1)), days[0][0])
    return [(d, n) for d, n in days if d >= start], created


def bins_of(days):
    if len(days) <= DAILY_MAX:
        return [(d, n) for d, n in days], "day"
    out = []
    for i in range(0, len(days), 7):
        chunk = days[i:i + 7]
        out.append((chunk[0][0], sum(n for _, n in chunk)))
    return out, "week"


def streak(days):
    run = 0
    for i, (_, n) in enumerate(reversed(days)):
        if n:
            run += 1
        elif i == 0:
            continue          # today can still be empty
        else:
            break
    return run


def render(cal):
    days, created = window(cal)
    bins, unit = bins_of(days)
    counts = [n for _, n in bins]
    total = sum(n for _, n in days)
    peak = max(counts) if counts else 0
    active = sum(1 for _, n in days if n)
    run = streak(days)

    nb = len(bins)
    sw = (SX1 - SX0) / nb
    y_of = lambda c: BASE - (c / peak) * (BASE - CEIL) if peak else BASE

    # CH1: per-bin contributions, step trace
    trace = [f"M{SX0} {f(y_of(counts[0]))}"]
    x, prev = SX0, None
    for c in counts:
        y = y_of(c)
        if prev is not None and y != prev:
            trace.append(f"V{f(y)}")
        x += sw
        trace.append(f"H{f(x)}")
        prev = y
    trace_d = "".join(trace)
    area_d = f"{trace_d}V{BASE}H{SX0}Z"

    # CH2: running total, ramps across each bin
    acc, pts = 0, [f"M{SX0} {BASE}"]
    for i, c in enumerate(counts):
        acc += c
        y = BASE - (acc / total) * (BASE - CEIL) if total else BASE
        pts.append(f"L{f(SX0 + (i + 1) * sw)} {f(y)}")
    cum_d = "".join(pts)

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

    # date labels, ~8 across
    step = max(1, round(nb / 8))
    labels = "".join(
        f'<text x="{f(SX0 + (i + 0.5) * sw)}" y="{SY1 + 20}" text-anchor="middle">{d:%b} {d.day}</text>'
        for i, (d, _) in enumerate(bins) if i % step == 0 and i < nb - step / 2)

    # account-creation marker when it falls inside the window
    join = ""
    for i, (d, _) in enumerate(bins):
        if d >= created and d.isoformat() != bins[0][0].isoformat():
            jx = SX0 + i * sw
            join = (f'<line x1="{f(jx)}" y1="{SY0 + 6}" x2="{f(jx)}" y2="{SY1 - 1}" stroke="{DIM}" stroke-dasharray="2 4"/>'
                    f'<text x="{f(jx + 6)}" y="{SY0 + 16}" font-family="{MONO}" font-size="10" fill="{DIM}">joined GitHub</text>')
            break
        if d >= created:
            break

    quiet = "" if total else (
        f'<text x="{f(cxm)}" y="{f(cym - 10)}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{DIM}">'
        f'no signal yet · waiting for first commits</text>')

    reveal_kt = "0;0.45;1"
    updated = dt.date.today().isoformat()
    since = f"{max(created, bins[0][0]):%b %Y}"
    readout = (f"Σ {total} since {since}   ·   {active} active day{"" if active == 1 else "s"}   ·   "
               f"streak {run} d   ·   peak {peak}/{unit}")
    span_txt = f"{len(days)} days" if unit == "day" else f"{nb} weeks"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions since {since}, drawn as an oscilloscope trace">
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
  {join}
  {quiet}

  <!-- channel + trigger markers -->
  <path d="M{SX0 - 14} {BASE - 6}H{SX0 - 6}L{SX0 - 1} {BASE}L{SX0 - 6} {BASE + 6}H{SX0 - 14}Z" fill="{ACCENT}"/>
  <text x="{SX0 - 11}" y="{BASE + 3.5}" font-family="{MONO}" font-size="9" font-weight="700" fill="{BG}" text-anchor="middle">1</text>
  <path d="M{SX1 + 1} {f(cym)}L{SX1 + 9} {f(cym - 6)}V{f(cym + 6)}Z" fill="{AMBER}"/>
  <text x="{SX1 + 13}" y="{f(cym + 4)}" font-family="{MONO}" font-size="10" fill="{AMBER}">T</text>

  <!-- traces -->
  <g>
    <animate attributeName="opacity" values="1;1;0.35;0;1" keyTimes="0;0.86;0.95;0.99;1" dur="{SWEEP}s" repeatCount="indefinite"/>
    <g clip-path="url(#sweep)">
      <path d="{area_d}" fill="url(#area)"/>
      <path d="{cum_d}" fill="none" stroke="{AMBER}" stroke-width="1.6" stroke-opacity="0.85" stroke-linejoin="round"/>
      <path d="{trace_d}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linejoin="round" filter="url(#glow)"/>
    </g>
  </g>
  <rect x="{SX0}" y="{SY0 + 1}" width="2" height="{SY1 - SY0 - 2}" fill="{ACCENT}" filter="url(#glow)" opacity="0">
    <animate attributeName="x" values="{SX0};{SX1 - 2};{SX1 - 2}" keyTimes="{reveal_kt}" dur="{SWEEP}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.9;0.9;0;0" keyTimes="0;0.45;0.47;1" dur="{SWEEP}s" repeatCount="indefinite"/>
  </rect>

  <g font-family="{MONO}" font-size="11" fill="{DIM}">
    {labels}
    <text x="{SX0}" y="{H - 16}">updated {updated} · re-rendered daily by GitHub Actions</text>
    <text x="{SX1}" y="{H - 16}" text-anchor="end" xml:space="preserve"><tspan fill="{ACCENT}">━</tspan> CH1 contributions / {unit}   <tspan fill="{AMBER}">━</tspan> CH2 running total   ·   {span_txt}</text>
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
