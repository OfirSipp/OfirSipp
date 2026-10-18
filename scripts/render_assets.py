"""Render the static, animated SVGs used by the profile README.

    python scripts/render_assets.py [assets]

Everything is plain SVG + SMIL so it keeps animating inside a GitHub README,
where scripts are stripped and images are served through a proxy.

  banner.svg    name plate with an FPGA package whose fabric configures itself
  wave.svg      a waveform viewer decoding a real 8N1 UART stream
  timeline.svg  career and education drawn as a timing diagram
"""

import os
import random
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"

# ---------------------------------------------------------------- palette ---
BG = "#0d1117"
PANEL = "#161b22"
DEEP = "#0a0d12"
BORDER = "#30363d"
GRID = "#21262d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
DIM = "#6e7681"
ACCENT = "#2dd4bf"      # signal teal
AMBER = "#f0b429"       # cursor / markers

SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

GLOW = """<filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>"""


def f(x):
    """Compact number formatting for coordinates."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def write(name, svg):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"{name:14s} {len(svg) / 1024:6.1f} KB")


# ================================================================= banner ===
def banner():
    W, H = 1200, 340
    cx, cy = 950, 160
    PKG = 196
    px0, py0 = cx - PKG / 2, cy - PKG / 2          # package top-left
    N_PINS, PITCH, PIN_L = 18, 9.5, 10
    off = (PKG - (N_PINS - 1) * PITCH) / 2

    def pin_pos(i):
        return off + i * PITCH

    traced = {"left": [2, 6, 11, 15], "right": [3, 7, 10, 14], "top": [5, 12], "bottom": [4, 13]}
    lit = {(side, i) for side, idx in traced.items() for i in idx}

    pins = []
    for i in range(N_PINS):
        p = pin_pos(i)
        for side, (x, y, w, h) in {
            "top": (px0 + p - 2, py0 - PIN_L, 4, PIN_L),
            "bottom": (px0 + p - 2, py0 + PKG, 4, PIN_L),
            "left": (px0 - PIN_L, py0 + p - 2, PIN_L, 4),
            "right": (px0 + PKG, py0 + p - 2, PIN_L, 4),
        }.items():
            fill = ACCENT if (side, i) in lit else BORDER
            op = ' fill-opacity="0.55"' if (side, i) in lit else ""
            pins.append(f'<rect x="{f(x)}" y="{f(y)}" width="{w}" height="{h}" rx="1" fill="{fill}"{op}/>')

    # traces: (path from outside -> pin for inputs, pin -> outside for outputs)
    traces = []
    fan = [-28, -10, 10, 28]
    for k, i in enumerate(traced["left"]):
        y = py0 + pin_pos(i)
        y2 = y + fan[k]
        traces.append((f"M760 {f(y2)} H{f(px0 - 52)} L{f(px0 - 34)} {f(y)} H{f(px0 - PIN_L)}", (760, y2), True))
    for k, i in enumerate(traced["right"]):
        y = py0 + pin_pos(i)
        y2 = y + fan[k]
        x = px0 + PKG + PIN_L
        traces.append((f"M{f(x)} {f(y)} H{f(x + 24)} L{f(x + 42)} {f(y2)} H1150", (1150, y2), False))
    for k, i in enumerate(traced["top"]):
        x = px0 + pin_pos(i)
        x2 = x + (-20 if k == 0 else 20)
        traces.append((f"M{f(x2)} 16 V{f(py0 - PIN_L - 26)} L{f(x)} {f(py0 - PIN_L - 10)} V{f(py0 - PIN_L)}", (x2, 16), True))
    for k, i in enumerate(traced["bottom"]):
        x = px0 + pin_pos(i)
        x2 = x + (-20 if k == 0 else 20)
        y0 = py0 + PKG + PIN_L
        traces.append((f"M{f(x)} {f(y0)} V{f(y0 + 8)} L{f(x2)} {f(y0 + 22)} V{f(y0 + 28)}", (x2, y0 + 28), False))

    trace_paths, vias, packets = [], [], []
    rnd = random.Random(7020)
    for n, (d, (vx, vy), _inp) in enumerate(traces):
        trace_paths.append(f'<path d="{d}"/>')
        vias.append(f'<circle cx="{f(vx)}" cy="{f(vy)}" r="3.5"/>')
        dur = round(rnd.uniform(1.8, 2.8), 2)
        begin = round(-rnd.uniform(0, dur), 2)
        packets.append(
            f'<circle r="2.4" fill="{ACCENT}" filter="url(#glow)" opacity="0">'
            f'<animateMotion path="{d}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.85;1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'</circle>')

    # die: 7x7 logic cells, a diagonal configuration wave, some cells "in use"
    DIE = 144
    dx0, dy0 = cx - DIE / 2, cy - DIE / 2
    CELL, GAP, COUNT = 15, 3.5, 7
    pad = (DIE - (COUNT * CELL + (COUNT - 1) * GAP)) / 2
    used = set(rnd.sample(range(COUNT * COUNT), 18))
    cells = []
    for r in range(COUNT):
        for c in range(COUNT):
            x = dx0 + pad + c * (CELL + GAP)
            y = dy0 + pad + r * (CELL + GAP)
            base = 0.30 if r * COUNT + c in used else 0.07
            begin = round((r + c) * 0.11, 2)
            cells.append(
                f'<rect x="{f(x)}" y="{f(y)}" width="{CELL}" height="{CELL}" rx="2" fill="{ACCENT}" fill-opacity="{base}">'
                f'<animate attributeName="fill-opacity" values="{base};{base};0.9;{base + 0.12:.2f};{base}" '
                f'keyTimes="0;0.02;0.1;0.4;1" dur="3.4s" begin="{begin}s" repeatCount="indefinite"/></rect>')

    status = "DONE   ·   TIMING MET   ·   WNS +0.214 ns"
    status_w = len(status) * 7.3          # 10.5px mono + 1px letter-spacing
    led_x = cx - status_w / 2 - 14

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Ofir Sipouren - Practical Engineer, Embedded Systems and FPGA">
  <defs>
    {GLOW}
    <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity="0.13"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">
      <circle cx="9" cy="9" r="1" fill="{GRID}"/>
    </pattern>
    <linearGradient id="fadeIn" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset="0.45" stop-color="#fff" stop-opacity="1"/>
    </linearGradient>
    <mask id="dotMask"><rect x="560" y="0" width="640" height="{H}" fill="url(#fadeIn)"/></mask>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="12"/></clipPath>
  </defs>

  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}"/>
  <g clip-path="url(#frame)">
    <rect x="560" y="0" width="640" height="{H}" fill="url(#dots)" mask="url(#dotMask)"/>
    <circle cx="{cx}" cy="{cy}" r="240" fill="url(#halo)"/>
  </g>

  <!-- identity -->
  <rect x="64" y="83" width="3" height="17" fill="{ACCENT}"/>
  <text x="76" y="97" font-family="{SANS}" font-size="14" font-weight="600" letter-spacing="3" fill="{ACCENT}">EMBEDDED · FPGA · HW VALIDATION</text>
  <text x="61" y="170" font-family="{SANS}" font-size="60" font-weight="600" fill="{TEXT}">Ofir Sipouren</text>
  <text x="64" y="211" font-family="{SANS}" font-size="24" font-weight="400" fill="{MUTED}">Practical Engineer · Embedded Systems &amp; FPGA</text>
  <line x1="64" y1="238" x2="600" y2="238" stroke="{BORDER}"/>
  <text x="64" y="268" font-family="{MONO}" font-size="14.5" fill="{MUTED}" xml:space="preserve">VHDL  ·  Zynq SoC  ·  Python test automation  ·  Failure analysis <tspan fill="{ACCENT}">▌<animate attributeName="fill-opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" repeatCount="indefinite"/></tspan></text>

  <!-- traces -->
  <g fill="none" stroke="{BORDER}" stroke-width="1.5" stroke-linejoin="round">{"".join(trace_paths)}</g>
  <g fill="{BG}" stroke="{BORDER}" stroke-width="1.5">{"".join(vias)}</g>
  <g>{"".join(packets)}</g>

  <!-- package -->
  {"".join(pins)}
  <rect x="{f(px0)}" y="{f(py0)}" width="{PKG}" height="{PKG}" rx="8" fill="{PANEL}" stroke="{BORDER}"/>
  <circle cx="{f(px0 + 11)}" cy="{f(py0 + 11)}" r="3" fill="{BORDER}"/>
  <rect x="{f(dx0)}" y="{f(dy0)}" width="{DIE}" height="{DIE}" rx="3" fill="{DEEP}" stroke="{BORDER}"/>
  {"".join(cells)}
  <text x="{cx}" y="{f(py0 + PKG - 11)}" font-family="{MONO}" font-size="9" fill="{DIM}" text-anchor="middle" letter-spacing="1.5">OS-7020 · 2026</text>

  <!-- status -->
  <circle cx="{f(led_x)}" cy="318" r="4.5" fill="{ACCENT}" filter="url(#glow)">
    <animate attributeName="fill-opacity" values="1;0.35;1" dur="2.4s" repeatCount="indefinite"/>
  </circle>
  <text x="{cx}" y="322" font-family="{MONO}" font-size="10.5" fill="{MUTED}" text-anchor="middle" letter-spacing="1" xml:space="preserve">{status}</text>

  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{BORDER}"/>
</svg>
'''


# =================================================================== wave ===
def wave():
    """A waveform viewer scrolling past a cursor while it decodes a UART line.

    uart_tx carries a real 8N1 stream (start bit, 8 data bits LSB first,
    stop bit), so the bits on screen actually spell the message.
    """
    MSG = "designed & verified by Ofir Sipouren   "
    W, H = 1200, 276
    B = 14                      # px per bit
    FRAME_BITS = 12             # idle, start, d0..d7, stop, idle
    FW = B * FRAME_BITS
    N = len(MSG)
    L = N * FW                  # one full message, px
    SPEED = 170                 # px / s
    T = L / SPEED

    NAME_W = 196
    X0, X1 = NAME_W + 1, W - 14
    PANE_W = X1 - X0
    TOP = 34
    ROW0, RH = 48, 34
    ROWS = ["clk", "uart_tx", "rx_valid", "rx_data[7:0]", "rx_char"]
    RULER_Y = ROW0 + len(ROWS) * RH
    BAR_Y = RULER_Y + 22
    CURSOR_X = X0 + round(0.68 * PANE_W)

    hi = lambda r: ROW0 + r * RH + 8
    lo = lambda r: ROW0 + r * RH + RH - 8
    mid = lambda r: ROW0 + r * RH + RH / 2

    # char 0's rx_valid edge sits just right of the cursor at t = 0.4 s
    A = CURSOR_X - X0 - 11 * B + 0.4 * SPEED

    def frame(ch):
        v = ord(ch)
        return [1, 0] + [(v >> i) & 1 for i in range(8)] + [1, 1]

    copies = (-1, 0, 1)
    chars = [(cp * N + k, MSG[k]) for cp in copies for k in range(N)]  # global index

    # uart_tx
    bits = []
    for _, ch in chars:
        bits += frame(ch)
    x = -L
    level = bits[0]
    tx = [f"M{f(x)} {lo(1) if level == 0 else hi(1)}"]
    for b in bits:
        if b != level:
            tx.append(f"V{hi(1) if b else lo(1)}")
            level = b
        x += B
        tx.append(f"H{f(x)}")
    # merge consecutive H commands
    merged = []
    for cmd in tx:
        if merged and cmd[0] == "H" and merged[-1][0] == "H":
            merged[-1] = cmd
        else:
            merged.append(cmd)
    tx_d = "".join(merged)

    # rx_valid: one bit wide, in the idle bit after the stop bit
    valid = [f"M{f(-L)} {lo(2)}"]
    for g, _ in chars:
        s = g * FW + 11 * B
        valid.append(f"H{f(s)}V{hi(2)}H{f(s + B)}V{lo(2)}")
    valid.append(f"H{f(2 * L)}")
    valid_d = "".join(valid)

    # buses: value k holds from char k's valid edge to char k+1's
    def bus(row, label_of):
        shapes, labels = [], []
        for g, ch in chars:
            a = g * FW + 11 * B
            b = a + FW
            t, m, bt = hi(row), mid(row), lo(row)
            shapes.append(f"M{f(a)} {m}L{f(a + 4)} {t}H{f(b - 4)}L{f(b)} {m}L{f(b - 4)} {bt}H{f(a + 4)}Z")
            lab, color = label_of(ch)
            labels.append(f'<text x="{f(a + FW / 2)}" y="{m + 4}" fill="{color}">{lab}</text>')
        return "".join(shapes), "".join(labels)

    data_d, data_t = bus(3, lambda ch: (f"{ord(ch):02X}", TEXT))
    char_d, char_t = bus(4, lambda ch: ("SP", DIM) if ch == " " else (f"'{escape(ch)}'", TEXT))

    # decoded line: each char appears when its rx_valid edge crosses the cursor
    shown = MSG.rstrip()
    decoded = []
    for k, ch in enumerate(shown):
        t_k = 0.4 + k * FW / SPEED
        kt = round(t_k / T, 4)
        decoded.append(
            f'<tspan fill-opacity="0">{escape(ch)}<animate attributeName="fill-opacity" values="0;1" '
            f'keyTimes="0;{kt}" calcMode="discrete" dur="{T:.3f}s" repeatCount="indefinite"/></tspan>')
    caret_on = round((0.4 + len(shown) * FW / SPEED) / T, 4)

    names = "".join(
        f'<text x="18" y="{mid(r) + 4}"><tspan fill="{DIM}">/tb/</tspan>{escape(n)}</text>'
        for r, n in enumerate(ROWS))
    seps = "".join(f'<line x1="0" y1="{ROW0 + r * RH}" x2="{W}" y2="{ROW0 + r * RH}"/>' for r in range(1, len(ROWS)))

    x_start = X0 + A
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Waveform: a UART receiver decoding the text '{escape(shown)}'">
  <defs>
    {GLOW}
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="12"/></clipPath>
    <clipPath id="pane"><rect x="{X0}" y="{TOP}" width="{PANE_W}" height="{RULER_Y + 16 - TOP}"/></clipPath>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset="0.04" stop-color="#fff" stop-opacity="1"/>
      <stop offset="0.96" stop-color="#fff" stop-opacity="1"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <mask id="fade"><rect x="{X0}" y="{TOP}" width="{PANE_W}" height="{RULER_Y + 16 - TOP}" fill="url(#edge)"/></mask>
    <pattern id="clk" x="-3.5" y="{hi(0) - 2}" width="{B}" height="{lo(0) - hi(0) + 4}" patternUnits="userSpaceOnUse">
      <path d="M0 {lo(0) - hi(0) + 2}H3.5V2H10.5V{lo(0) - hi(0) + 2}H{B}" fill="none" stroke="{DIM}" stroke-width="1.3"/>
    </pattern>
    <pattern id="ticks" x="-0.5" y="{RULER_Y}" width="{FW}" height="12" patternUnits="userSpaceOnUse">
      <rect x="0" y="0" width="1" height="9" fill="{DIM}"/>
      {"".join(f'<rect x="{i * B}" y="0" width="1" height="4" fill="{BORDER}"/>' for i in range(1, FRAME_BITS))}
    </pattern>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{BG}"/>

    <!-- title bar -->
    <rect width="{W}" height="{TOP}" fill="{PANEL}"/>
    <line x1="0" y1="{TOP}" x2="{W}" y2="{TOP}" stroke="{BORDER}"/>
    <g font-family="{MONO}" font-size="12">
      <text x="18" y="22" fill="{MUTED}">wave <tspan fill="{DIM}">—</tspan> tb_uart_rx.vhd</text>
      <text x="{W - 18}" y="22" fill="{DIM}" text-anchor="end" xml:space="preserve">115200 8N1   ·   run -all   ·   <tspan fill="{ACCENT}">SIM RUNNING</tspan></text>
    </g>
    <circle cx="{W - 120}" cy="17" r="3.5" fill="{ACCENT}" filter="url(#glow)">
      <animate attributeName="fill-opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/>
    </circle>

    <!-- signal names -->
    <rect x="0" y="{TOP + 1}" width="{NAME_W}" height="{RULER_Y + 16 - TOP - 1}" fill="{DEEP}"/>
    <line x1="{NAME_W}" y1="{TOP}" x2="{NAME_W}" y2="{RULER_Y + 16}" stroke="{BORDER}"/>
    <g stroke="{PANEL}">{seps}</g>
    <g font-family="{MONO}" font-size="12.5" fill="{TEXT}">{names}</g>

    <!-- waves -->
    <g clip-path="url(#pane)">
      <g mask="url(#fade)">
        <g transform="translate({f(x_start)} 0)">
          <animateTransform attributeName="transform" type="translate" values="{f(x_start)} 0;{f(x_start - L)} 0" dur="{T:.3f}s" repeatCount="indefinite"/>
          <rect x="{f(-L)}" y="{hi(0) - 2}" width="{3 * L}" height="{lo(0) - hi(0) + 4}" fill="url(#clk)"/>
          <path d="{tx_d}" fill="none" stroke="{ACCENT}" stroke-width="1.6" stroke-linejoin="round"/>
          <path d="{valid_d}" fill="none" stroke="{AMBER}" stroke-width="1.6" stroke-linejoin="round"/>
          <path d="{data_d}" fill="{ACCENT}" fill-opacity="0.08" stroke="{ACCENT}" stroke-opacity="0.8" stroke-width="1.2"/>
          <path d="{char_d}" fill="{ACCENT}" fill-opacity="0.14" stroke="{ACCENT}" stroke-width="1.2"/>
          <g font-family="{MONO}" font-size="11.5" text-anchor="middle">{data_t}</g>
          <g font-family="{MONO}" font-size="12.5" font-weight="600" text-anchor="middle">{char_t}</g>
          <rect x="{f(-L)}" y="{RULER_Y}" width="{3 * L}" height="12" fill="url(#ticks)"/>
        </g>
      </g>
    </g>
    <line x1="{NAME_W}" y1="{RULER_Y}" x2="{W}" y2="{RULER_Y}" stroke="{BORDER}"/>

    <!-- cursor -->
    <line x1="{CURSOR_X}" y1="{TOP + 4}" x2="{CURSOR_X}" y2="{RULER_Y + 12}" stroke="{AMBER}" stroke-width="1.2" stroke-opacity="0.9"/>
    <path d="M{CURSOR_X - 5} {TOP + 1}H{CURSOR_X + 5}L{CURSOR_X} {TOP + 8}Z" fill="{AMBER}"/>

    <!-- decoded output -->
    <rect x="0" y="{RULER_Y + 16}" width="{W}" height="{H - RULER_Y - 16}" fill="{PANEL}"/>
    <line x1="0" y1="{RULER_Y + 16}" x2="{W}" y2="{RULER_Y + 16}" stroke="{BORDER}"/>
    <text x="18" y="{BAR_Y + 18}" font-family="{MONO}" font-size="14" fill="{TEXT}" xml:space="preserve"><tspan fill="{DIM}">uart_rx </tspan><tspan fill="{ACCENT}">▸ </tspan>{"".join(decoded)}<tspan fill="{ACCENT}" fill-opacity="0"> ▌<animate attributeName="fill-opacity" values="0;1;0;1;0;1;0" keyTimes="0;{caret_on};{caret_on + (1 - caret_on) / 6:.4f};{caret_on + 2 * (1 - caret_on) / 6:.4f};{caret_on + 3 * (1 - caret_on) / 6:.4f};{caret_on + 4 * (1 - caret_on) / 6:.4f};{caret_on + 5 * (1 - caret_on) / 6:.4f}" calcMode="discrete" dur="{T:.3f}s" repeatCount="indefinite"/></tspan></text>
    <text x="{W - 18}" y="{BAR_Y + 18}" font-family="{MONO}" font-size="11" fill="{DIM}" text-anchor="end">{N} bytes · 0 framing errors</text>
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{BORDER}"/>
</svg>
'''


# =============================================================== timeline ===
def timeline():
    W, H = 1200, 268
    X_A, X_B = 200, 1150
    Y_A, Y_B = 2022.0, 2028.5
    NOW = 2026.79                      # Oct 2026
    X = lambda yr: X_A + (yr - Y_A) * (X_B - X_A) / (Y_B - Y_A)
    xn = X(NOW)

    ROLE_Y, EDU_Y = 112, 182
    AXIS_Y = 230

    def hexagon(a, b, cy, hh, s=8):
        return f"M{f(a)} {cy}L{f(a + s)} {cy - hh}H{f(b - s)}L{f(b)} {cy}L{f(b - s)} {cy + hh}H{f(a + s)}Z"

    iaf = hexagon(X(2022.42), X(2025.96), ROLE_Y, 24)
    gate = hexagon(X(2026.25), X_B + 40, ROLE_Y, 24)
    bsc = hexagon(X(2026.3), X(2028.3), EDU_Y, 20)

    years = "".join(
        f'<line x1="{f(X(y))}" y1="{AXIS_Y}" x2="{f(X(y))}" y2="{AXIS_Y + 6}"/>'
        f'<text x="{f(X(y))}" y="{AXIS_Y + 22}" stroke="none">{y}</text>'
        for y in range(2022, 2029))
    grid = "".join(f'<line x1="{f(X(y))}" y1="70" x2="{f(X(y))}" y2="{AXIS_Y}"/>' for y in range(2022, 2029))

    dia_x = X(2022.38)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Timeline: Israeli Air Force navigation and GNSS specialist 2022-2025; Gate Technologies hardware development since April 2026; practical electronics engineering diploma 2022 summa cum laude; B.Sc. Electrical Engineering at HIT, expected 2028">
  <defs>
    {GLOW}
    <linearGradient id="ongoing" gradientUnits="userSpaceOnUse" x1="{f(X(2026.25))}" y1="0" x2="{X_B + 30}" y2="0">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity="0.16"/>
      <stop offset="0.55" stop-color="{ACCENT}" stop-opacity="0.12"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="ongoingStroke" gradientUnits="userSpaceOnUse" x1="{f(X(2026.25))}" y1="0" x2="{X_B + 30}" y2="0">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity="1"/>
      <stop offset="0.6" stop-color="{ACCENT}" stop-opacity="0.8"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="studying" gradientUnits="userSpaceOnUse" x1="{f(X(2026.3))}" y1="0" x2="{f(xn + 10)}" y2="0">
      <stop offset="0" stop-color="{AMBER}" stop-opacity="0"/>
      <stop offset="1" stop-color="{AMBER}" stop-opacity="0.14"/>
    </linearGradient>
    <linearGradient id="studyingStroke" gradientUnits="userSpaceOnUse" x1="{f(X(2026.3))}" y1="0" x2="{f(xn + 10)}" y2="0">
      <stop offset="0" stop-color="{AMBER}" stop-opacity="0"/>
      <stop offset="1" stop-color="{AMBER}" stop-opacity="1"/>
    </linearGradient>
    <clipPath id="past"><rect x="0" y="0" width="{f(xn)}" height="{H}"/></clipPath>
    <clipPath id="future"><rect x="{f(xn)}" y="0" width="{f(W - xn)}" height="{H}"/></clipPath>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="12"/></clipPath>
    <clipPath id="reveal">
      <rect x="0" y="0" width="{X_A}" height="{H}">
        <animate attributeName="width" values="{X_A};{W}" dur="2.4s" begin="0.2s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
      </rect>
    </clipPath>
  </defs>

  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>

  <rect x="64" y="30" width="3" height="20" fill="{ACCENT}"/>
  <text x="78" y="47" font-family="{SANS}" font-size="20" fill="{TEXT}"><tspan font-weight="600">Career</tspan><tspan fill="{MUTED}">, as a timing diagram</tspan></text>

  <g font-family="{MONO}" font-size="12" fill="{DIM}">
    <text x="64" y="{ROLE_Y + 4}">role</text>
    <text x="64" y="{EDU_Y + 4}">edu</text>
  </g>

  <g stroke="{GRID}" stroke-dasharray="2 5">{grid}</g>

  <g clip-path="url(#reveal)">
    <!-- idle lines (high-Z between segments) -->
    <g stroke="{BORDER}" stroke-width="1.5" fill="none">
      <path d="M{X_A} {ROLE_Y}H{f(X(2022.42))}M{f(X(2025.96))} {ROLE_Y}H{f(X(2026.25))}"/>
      <path d="M{X_A} {EDU_Y}H{f(X(2026.3))}"/>
    </g>

    <!-- role -->
    <path d="{iaf}" fill="{ACCENT}" fill-opacity="0.10" stroke="{ACCENT}" stroke-opacity="0.75" stroke-width="1.4"/>
    <path d="{gate}" fill="url(#ongoing)" stroke="url(#ongoingStroke)" stroke-width="1.4" clip-path="url(#past)"/>
    <path d="{gate}" fill="url(#ongoing)" stroke="url(#ongoingStroke)" stroke-width="1.4" stroke-dasharray="5 5" clip-path="url(#future)"/>
    <text x="{f(X(2022.42) + 18)}" y="{ROLE_Y - 3}" font-family="{SANS}" font-size="15" font-weight="600" fill="{TEXT}">Israeli Air Force <tspan font-weight="400" fill="{MUTED}">· Navigation &amp; GNSS Specialist</tspan></text>
    <text x="{f(X(2022.42) + 18)}" y="{ROLE_Y + 15}" font-family="{MONO}" font-size="11.5" fill="{DIM}">FPGA development · VHDL / Python test automation</text>
    <text x="{f(X(2026.25) + 16)}" y="{ROLE_Y - 3}" font-family="{SANS}" font-size="15" font-weight="600" fill="{TEXT}">Gate Technologies</text>
    <text x="{f(X(2026.25) + 16)}" y="{ROLE_Y + 15}" font-family="{MONO}" font-size="11.5" fill="{DIM}">HW dev · validation · failure analysis</text>

    <!-- edu -->
    <path d="M{f(dia_x)} {EDU_Y - 9}L{f(dia_x + 9)} {EDU_Y}L{f(dia_x)} {EDU_Y + 9}L{f(dia_x - 9)} {EDU_Y}Z" fill="{AMBER}"/>
    <text x="{f(dia_x + 20)}" y="{EDU_Y - 3}" font-family="{SANS}" font-size="15" font-weight="600" fill="{TEXT}">Practical Electronics Eng. <tspan font-weight="400" fill="{MUTED}">· summa cum laude</tspan></text>
    <text x="{f(dia_x + 20)}" y="{EDU_Y + 15}" font-family="{MONO}" font-size="11.5" fill="{DIM}">Amal B College · 2022</text>
    <path d="{bsc}" fill="url(#studying)" stroke="url(#studyingStroke)" stroke-width="1.4" clip-path="url(#past)"/>
    <path d="{bsc}" fill="{AMBER}" fill-opacity="0.14" stroke="{AMBER}" stroke-width="1.4" stroke-dasharray="5 5" clip-path="url(#future)"/>
    <text x="{f(xn + 14)}" y="{EDU_Y - 3}" font-family="{SANS}" font-size="15" font-weight="600" fill="{TEXT}">B.Sc. EE <tspan font-weight="400" fill="{MUTED}">· HIT</tspan></text>
    <text x="{f(xn + 14)}" y="{EDU_Y + 15}" font-family="{MONO}" font-size="11.5" fill="{DIM}">expected 2028</text>
  </g>

  <!-- axis -->
  <line x1="{X_A}" y1="{AXIS_Y}" x2="{X_B}" y2="{AXIS_Y}" stroke="{BORDER}"/>
  <g stroke="{BORDER}" font-family="{MONO}" font-size="11" fill="{DIM}" text-anchor="middle">{years}</g>

  <!-- now -->
  <line x1="{f(xn)}" y1="74" x2="{f(xn)}" y2="{AXIS_Y}" stroke="{AMBER}" stroke-opacity="0.75" stroke-dasharray="3 3"/>
  <text x="{f(xn)}" y="66" font-family="{MONO}" font-size="11" fill="{AMBER}" text-anchor="middle" letter-spacing="1">NOW</text>
  <circle cx="{f(xn)}" cy="{AXIS_Y}" r="4" fill="{AMBER}"/>
  <circle cx="{f(xn)}" cy="{AXIS_Y}" r="4" fill="none" stroke="{AMBER}">
    <animate attributeName="r" values="4;14" dur="2.2s" repeatCount="indefinite"/>
    <animate attributeName="stroke-opacity" values="0.8;0" dur="2.2s" repeatCount="indefinite"/>
  </circle>

  <!-- sampling sweep -->
  <g clip-path="url(#frame)">
    <rect x="{X_A}" y="70" width="2" height="{AXIS_Y - 70}" fill="{ACCENT}" opacity="0" filter="url(#glow)">
      <animate attributeName="x" values="{X_A};{f(xn)};{f(xn)}" keyTimes="0;0.55;1" dur="7s" begin="2.8s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0;0.7;0.7;0;0" keyTimes="0;0.05;0.5;0.56;1" dur="7s" begin="2.8s" repeatCount="indefinite"/>
    </rect>
  </g>
</svg>
'''


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write("banner.svg", banner())
    write("wave.svg", wave())
    write("timeline.svg", timeline())
