"""The "Modular Floor" page from grid_eval.py's and retention.py's numbers: twin/grid_eval.html (2026-11-08).

    python twin/grid_eval.py            # first: the fit and the slices -> twin/out/grid_eval.json
    python twin/retention.py frames frames_open    # the drops -> twin/out/retention.json
    python twin/grid_eval_page.py       # the check on the rough layout, then the page
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
sys.path.insert(0, HERE)
import grid_layouts as GL

E = json.load(open(os.path.join(config.TWIN_OUT, 'grid_eval.json')))
D = json.load(open(os.path.join(config.TWIN_OUT, 'retention.json')))
N = json.load(open(os.path.join(config.GAUGES_OUT, 'noisy', 'single.json')))['T3']
P, T, F = E['pieces'], E['totals'], E['fit']
BODY = (-142.0, 108.0, -66.0, 73.5)           # a 250 mm body, print 1's width; the tub's own frame
WALL = 2.6
FRAME = 1.45                                  # a frame's wall and clearance
T3_G = 4651.0                                 # g: the sim's T3


def hm(m):
    return '%d h %02d' % (m // 60, m % 60) if m >= 60 else '%d min' % m


# The rough layout, tub frame: x0, x1, y0, y1. Packs and ESCs where the sim has them. Not a design: it shows the parts fit.
LAYOUT = {'Pack': (-41, 100, 40.4, 66.4), 'Pack ': (-41, 100, -58.9, -32.9), 'ESC': (-89, -44, 42.4, 66.4), 'ESC ': (-89, -44, -58.9, -34.9),
          'Pi box': (-49, 49.5, -29.05, 36.55), 'PCA9685': (-114.5, -52.3, 7.5, 33.2), 'ESP32': (-114.5, -59.5, -24, 4),
          'IMU': (-137.9, -117.9, -10, 15), 'Pololu': (-137.5, -112.1, -61.5, -36.1), 'INA219': (-137.5, -111.9, 44, 64.4),
          'Servo BEC': (53, 101, -28, 2), 'Alarm': (53, 93, 6, 31)}


def overlaps(L):
    """frames touching each other or past the body's inside: pairs and names. Empty is the pass"""
    bad, ks = [], list(L)
    x0, x1, y0, y1 = BODY[0] + WALL, BODY[1] - WALL, BODY[2] + WALL, BODY[3] - WALL
    for k, (a, b, c, d) in L.items():
        if a - FRAME < x0 - 0.1 or b + FRAME > x1 + 0.1 or c - FRAME < y0 - 0.1 or d + FRAME > y1 + 0.1:
            bad.append(k + ' past the body')
    for i, p in enumerate(ks):
        for q in ks[i + 1:]:
            a, b, c, d = L[p]; e, f, g, h = L[q]
            if a - FRAME < f + FRAME and e - FRAME < b + FRAME and c - FRAME < h + FRAME and g - FRAME < d + FRAME:
                bad.append(p + ' into ' + q)
    return bad


def check():
    bad = overlaps(LAYOUT)
    print('rough layout, frames against each other and the body: %s' % (bad or 'all clear'))
    L2 = dict(LAYOUT); a, b, c, d = L2['PCA9685']; L2['PCA9685'] = (a + 5, b + 5, c, d)
    bad2 = overlaps(L2)
    print('control, the PCA 5 mm forward: %s' % (bad2 or 'all clear: THE CHECK IS BROKEN'))
    if bad or not bad2:
        raise SystemExit('layout check failed')


# ---------------------------------------------------------------- the two plans, to one scale
S = 1.45
def plan_frames():
    x0, x1, y0, y1 = BODY
    W, H = (x1 - x0) * S, (y1 - y0) * S
    ox, oy = 12, 62 + (210 * S - H) / 2
    X = lambda x: round(ox + (x - x0) * S, 1)
    Y = lambda y: round(oy + (y1 - y) * S, 1)
    o = ['<svg viewBox="0 0 390 372" role="img" aria-label="Every part fits inside the 250 by 140 millimetre body when its holder is free of the grid: a low frame round each part, with pegs into a floor of holes every 15 millimetres.">']
    o.append(f'<rect class="body" x="{X(x0)}" y="{Y(y1)}" width="{W:.1f}" height="{H:.1f}" rx="5"/>')
    p, xs = 15.0, []
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = int((x1 - x0 - 2 * WALL) // p), int((y1 - y0 - 2 * WALL) // p)
    for i in range(nx):
        for j in range(ny):
            a, b = cx + p * (i - (nx - 1) / 2), cy + p * (j - (ny - 1) / 2)
            o.append(f'<circle class="hole" cx="{X(a)}" cy="{Y(b)}" r="{2.65 * S:.1f}"/>')
    for k, (a, b, c, d) in LAYOUT.items():
        o.append(f'<rect class="fr" x="{X(a - FRAME)}" y="{Y(d + FRAME)}" width="{(b - a + 2 * FRAME) * S:.1f}" height="{(d - c + 2 * FRAME) * S:.1f}" rx="1.5"/>')
        o.append(f'<rect class="pt" x="{X(a)}" y="{Y(d)}" width="{(b - a) * S:.1f}" height="{(d - c) * S:.1f}" rx="1"/>')
        o.append(f'<text class="lb" x="{X((a + b) / 2)}" y="{Y((c + d) / 2) + 3.6}" text-anchor="middle">{k.strip()}</text>')
    o.append(f'<text class="ts" x="{X(x0)}" y="{Y(y1) - 7}">250 × 140 body</text>')
    o.append('</svg>')
    return ''.join(o)


def plan_grid():
    # a 6 x 5 grid, the smallest near-square that takes 29 cells without breaking a pack; cells: col, row, cols, rows, part long, wide, name
    M = [(0, 0, 4, 1, 141, 26, 'Pack'), (4, 0, 2, 1, 45, 24, 'ESC'), (0, 4, 4, 1, 141, 26, 'Pack'), (4, 4, 2, 1, 45, 24, 'ESC'),
         (0, 1, 3, 2, 98.5, 65.6, 'Pi box'), (3, 1, 2, 1, 62.2, 25.7, 'PCA9685'), (3, 2, 2, 1, 55, 28, 'ESP32'), (5, 1, 1, 1, 25.4, 25.4, 'Pololu'),
         (5, 2, 1, 1, 25.6, 20.4, 'INA219'), (0, 3, 2, 1, 48, 30, 'Servo BEC'), (2, 3, 2, 1, 40, 25, 'Alarm'), (4, 3, 1, 1, 25, 20, 'IMU')]
    ox, oy = 12, 62
    o = ['<svg viewBox="0 0 390 372" role="img" aria-label="On a real 42 millimetre Gridfinity grid the same parts need 29 cells, a grid of 252 by 210 millimetres, which overflows the 250 by 140 body at top and bottom.">']
    GW, GH = 6 * 42 * S, 5 * 42 * S
    # the body, centred on the grid
    bw, bh = 250 * S, 139.5 * S; bx, by = ox + (GW - bw) / 2, oy + (GH - bh) / 2
    for i in range(6):
        for j in range(5):
            o.append(f'<rect class="cell" x="{ox + i * 42 * S:.1f}" y="{oy + j * 42 * S:.1f}" width="{42 * S:.1f}" height="{42 * S:.1f}"/>')
    for c, r, nc, nr, a, b, n in M:
        x, y = ox + c * 42 * S, oy + r * 42 * S; w, h = nc * 42 * S, nr * 42 * S
        o.append(f'<rect class="mod" x="{x + 0.4:.1f}" y="{y + 0.4:.1f}" width="{w - 0.8:.1f}" height="{h - 0.8:.1f}" rx="3"/>')
        px, py = x + (w - a * S) / 2, y + (h - b * S) / 2
        o.append(f'<rect class="pt" x="{px:.1f}" y="{py:.1f}" width="{a * S:.1f}" height="{b * S:.1f}" rx="1"/>')
        o.append(f'<text class="lb" x="{x + w / 2:.1f}" y="{y + h / 2 + 3.6:.1f}" text-anchor="middle">{n}</text>')
    o.append(f'<rect class="bodyline" x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5"/>')
    o.append(f'<rect class="over" x="{ox:.1f}" y="{oy:.1f}" width="{GW:.1f}" height="{by - oy:.1f}"/>')
    o.append(f'<rect class="over" x="{ox:.1f}" y="{by + bh:.1f}" width="{GW:.1f}" height="{oy + GH - by - bh:.1f}"/>')
    o.append(f'<text class="ts" x="{ox}" y="{oy - 28}">The same parts, each rounded up to whole cells</text>')
    o.append(f'<text class="ts over-t" x="{ox}" y="{oy - 11}">Tinted bands: past the 250 × 140 body</text>')
    o.append('</svg>')
    return ''.join(o)


# ---------------------------------------------------------------- the side view
def section():
    s = 8.0; base = 128; gap = 40; W = 21 * s
    def stack(i):
        ox = 14 + i * (W + gap)
        return (lambda x: round(ox + x * s, 1)), (lambda z: round(base - z * s, 1)), ox
    o = ['<svg viewBox="0 0 616 172" role="img" aria-label="Side views at eight times scale. On today\'s floor and the hole floor the part sits on the 2.6 millimetre floor. On a Gridfinity foot in an open baseplate it sits at 6 millimetres.">']
    def poly(cls, pts, X, Z):
        return f'<polygon class="{cls}" points="' + ' '.join(f'{X(a)},{Z(b)}' for a, b in pts) + '"/>'
    # today
    X, Z, ox = stack(0)
    o.append(poly('pl', [(0, 0), (21, 0), (21, 2.6), (0, 2.6)], X, Z))
    o.append(poly('pl', [(0, 2.6), (2, 2.6), (2, 13), (0, 13)], X, Z))
    o.append(poly('prt', [(2.5, 2.6), (21, 2.6), (21, 13), (2.5, 13)], X, Z))
    o.append(f'<text class="tb" x="{ox}" y="16">Print 1: bay in the body</text>')
    o.append(f'<text class="ts" x="{X(11.5)}" y="{Z(8)}" text-anchor="middle">part</text>')
    o.append(f'<text class="lb" x="{X(11.5)}" y="{Z(0.7)}" text-anchor="middle">floor</text>')
    o.append(f'<text class="tm" x="{ox}" y="{base + 18}">part sits at 2.6</text>')
    # gridfinity
    X, Z, ox = stack(1); c = 21.0
    o.append(poly('pl', [(0, 0), (c - 18.15, 0), (c - 18.85, 0.7), (c - 18.85, 2.5), (0.0, 4.65)], X, Z))
    foot = [(c - 17.8, 0.1), (c, 0.1), (c, 4.75), (0.25, 4.75), (c - 18.6, 2.6), (c - 18.6, 0.9)]
    o.append(poly('mdl', foot, X, Z))
    o.append(poly('mdl', [(0.25, 4.75), (21, 4.75), (21, 5.95), (0.25, 5.95)], X, Z))
    o.append(poly('mdl', [(0.25, 5.95), (1.45, 5.95), (1.45, 13), (0.25, 13)], X, Z))
    o.append(poly('prt', [(1.7, 5.95), (21, 5.95), (21, 13), (1.7, 13)], X, Z))
    o.append(f'<text class="tb" x="{ox}" y="16">Gridfinity: stepped foot</text>')
    o.append(f'<text class="ts" x="{X(11.5)}" y="{Z(9)}" text-anchor="middle">part</text>')
    o.append(f'<text class="lb" x="{X(12)}" y="{Z(1.9)}" text-anchor="middle">foot</text>')
    o.append(f'<text class="tm" x="{ox}" y="{base + 18}">part sits at 6.0</text>')
    o.append(f'<text class="tm dim" x="{ox}" y="{base + 34}">8.6 on a closed floor</text>')
    # holes + frame
    X, Z, ox = stack(2); pc = 6.5
    o.append(poly('pl', [(0, 0), (pc - 2.65, 0), (pc - 2.65, 2.6), (0, 2.6)], X, Z))
    o.append(poly('pl', [(pc + 2.65, 0), (21, 0), (21, 2.6), (pc + 2.65, 2.6)], X, Z))
    o.append(poly('mdl', [(pc - 2.5, 0.2), (pc + 2.5, 0.2), (pc + 2.5, 2.6), (pc - 2.5, 2.6)], X, Z))
    o.append(poly('mdl', [(pc - 3.5, 2.6), (pc + 3.5, 2.6), (pc + 3.5, 13), (pc - 3.5, 13)], X, Z))
    o.append(poly('mdl', [(pc + 3.5, 2.6), (pc + 4.7, 2.6), (pc + 4.7, 13), (pc + 3.5, 13)], X, Z))
    o.append(poly('prt', [(pc + 4.95, 2.6), (21, 2.6), (21, 13), (pc + 4.95, 13)], X, Z))
    o.append(f'<text class="tb" x="{ox}" y="16">Holes: frame with a peg</text>')
    o.append(f'<text class="ts" x="{X(16)}" y="{Z(8)}" text-anchor="middle">part</text>')
    o.append(f'<text class="lb" x="{X(pc)}" y="{Z(8)}" text-anchor="middle">frame</text>')
    o.append(f'<text class="lb" x="{X(pc)}" y="{Z(0.7)}" text-anchor="middle">peg</text>')
    o.append(f'<text class="lb" x="{X(16)}" y="{Z(0.7)}" text-anchor="middle">floor</text>')
    o.append(f'<text class="tm" x="{ox}" y="{base + 18}">part sits at 2.6</text>')
    o.append('</svg>')
    return ''.join(o)


# ---------------------------------------------------------------- numbers for the words
key = lambda p: p
g_lo, g_hi = min(v['g'] for k, v in P.items() if k.startswith('grid_')), max(v['g'] for k, v in P.items() if k.startswith('grid_'))
gm_lo, gm_hi = min(v['min'] for k, v in P.items() if k.startswith('grid_')), max(v['min'] for k, v in P.items() if k.startswith('grid_'))
f_lo, f_hi = min(v['g'] for k, v in P.items() if k.startswith('frame_')), max(v['g'] for k, v in P.items() if k.startswith('frame_'))
fm_lo, fm_hi = min(v['min'] for k, v in P.items() if k.startswith('frame_')), max(v['min'] for k, v in P.items() if k.startswith('frame_'))
fl, fh = P['floor_plain'], P['floor_holes']
add_open = T['grid']['g'] + P['plate_open']['g'] - fl['g']
add_skin = T['grid']['g'] + P['plate_on_skin']['g'] - fl['g']
add_hole = T['frame']['g'] + fh['g'] - fl['g']
FR, OP = D['frames'], D['frames_open']
moved = max(max(FR[h]['final_p90'].values()) for h in FR)
pk_pack = max(FR['1.0']['peak_p90']['frame pack_L'], FR['1.0']['peak_p90']['frame pack_R'])
pad_pack = max(FR['1.0']['peak_p90']['pad pack_L'], FR['1.0']['peak_p90']['pad pack_R'])
peg_n = pk_pack / 4; peg_mpa = peg_n / (3.14159 * 2.5 ** 2)
drops = sum(FR[h]['trials'] for h in FR)
out_open = {k: sum(OP[h]['out_of_place'][k] for h in OP) for k in ('pack_L', 'pack_R', 'pi_stack', 'pca', 'esc_L', 'esc_R')}
one = 300.0 * 15 / T3_G
TUB_MIN, TUB_G = 420, 196.3


LAY = GL.report()
PITCH = GL.cells_table()
GF_TALL = 6.0 + 45.7 + GL.GAP + 6.0 + GL.STACK + 2.6     # two full 42 mm layers: foot, pack, gap, foot, the Pi's stack, a lid
NAMES = dict(pack='Pack', esc='ESC', pi='Pi box')


def cut(pts, n):
    """a path's first n mm, and the rest of it"""
    head, left = [pts[0]], n
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        d = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if d >= left:
            t = left / d if d else 0
            m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            return head + [m], [m] + pts[i + 1:]
        head.append(b); left -= d
    return head, []


def lay_svg(L):
    s = 0.98; ox = 6; H = 139.5 * s; top = 6; side = top + H + 12; zmax = 110.0
    Y = lambda y: top + (69.75 - y) * s
    Z = lambda z: side + (zmax - z) * s
    o = [f"""<svg viewBox="0 0 260 {side + zmax * s + 8:.0f}" role="img" aria-label="{L['name']}, from above and from the side, to scale.">"""]
    o.append(f"""<rect class="body" x="{ox}" y="{top}" width="{250 * s:.1f}" height="{H:.1f}" rx="4"/>""")
    for lvl in (0, 1):
        for d in L['decks']:
            if lvl == 1:
                o.append(f"""<rect class="dk" x="{ox + d[0] * s:.1f}" y="{Y(d[3]):.1f}" width="{(d[1] - d[0]) * s:.1f}" height="{(d[3] - d[2]) * s:.1f}"/>""")
        for p in L['parts']:
            if p['lvl'] != lvl:
                continue
            a, b, c, e, f, g = p['b']
            o.append(f"""<rect class="{'up' if lvl else 'pt'}" x="{ox + a * s:.1f}" y="{Y(e):.1f}" width="{(b - a) * s:.1f}" height="{(e - c) * s:.1f}" rx="1"/>""")
            n = NAMES.get(p['k'])
            if n and (b - a) * s > 24:
                o.append(f"""<text class="lb" x="{ox + (a + b) / 2 * s:.1f}" y="{Y((c + e) / 2) + 3.6:.1f}" text-anchor="middle">{n}</text>""")
    # the wires, from above: the drive pack to both ESCs, each ESC to its two motors. Dashed is past the ESC's own yellow and blue
    w = L['wires']
    line = lambda c, pts: f"""<polyline class="{c}" points="{' '.join(f'{ox + x * s:.1f},{Y(y):.1f}' for x, y in pts)}"/>""" if len(pts) > 1 else ''
    for x, y, _ in w['leads']:
        o.append(line('wb', [(w['x'], w['y']), (x, w['y']), (x, y)]))
        yw = GL.MOTOR_Y if y > 0 else -GL.MOTOR_Y
        for ax in GL.AXLES:
            a, b = cut([(x, y), (x, yw), (ax, yw)], GL.ESC_MOTOR - GL.UP_OVER)
            o.append(line('wm', a)); o.append(line('wm dash', b))
            o.append(f"""<circle class="mt" cx="{ox + ax * s:.1f}" cy="{Y(yw):.1f}" r="2.6"/>""")
    # from the side: the floor, the body's height for this layout, every part seen through the wall
    tp = L['stats']['top']
    o.append(f"""<rect class="body" x="{ox}" y="{Z(tp):.1f}" width="{250 * s:.1f}" height="{tp * s:.1f}" rx="3"/>""")
    for d in L['decks']:
        o.append(f"""<rect class="dk" x="{ox + d[0] * s:.1f}" y="{Z(d[5]):.1f}" width="{(d[1] - d[0]) * s:.1f}" height="{(d[5] - d[4]) * s:.1f}"/>""")
    for p in sorted(L['parts'], key=lambda q: -q['b'][5]):
        a, b, c, e, f, g = p['b']
        o.append(f"""<rect class="{'up' if p['lvl'] else 'pt'}" x="{ox + a * s:.1f}" y="{Z(g):.1f}" width="{(b - a) * s:.1f}" height="{(g - f) * s:.1f}" rx="1"/>""")
    o.append(f"""<text class="ts dim" x="{ox + 4}" y="{Z(tp) - 3:.1f}">{tp:.0f} mm tall</text></svg>""")
    return ''.join(o)


def lay_cards():
    o = []
    for L in LAY:
        t = L['stats']
        o.append(f"""<div class="panel"><h3>{L['name']}</h3><figure>{lay_svg(L)}</figure><dl>
          <dt>Parts need</dt><dd class="m">{t['long']:.0f} × {t['wide']:.0f} × {t['top']:.0f} mm</dd>
          <dt>Packs' center</dt><dd class="m">{t['pack_z']:.1f} mm up</dd>
          <dt>Robot's CoM</dt><dd class="m">{t['dz']:+.1f} mm</dd>
          <dt>Swap a pack</dt><dd>{L['swap']}</dd>
          <dt>Battery wire</dt><dd class="m">{min(L['wires']['bat']):.0f} and {max(L['wires']['bat']):.0f} of {GL.BATTERY:.0f} mm</dd>
          <dt>Motor wire</dt><dd class="m">{min(L['wires']['mot'][0]):.0f} and {max(L['wires']['mot'][0]):.0f} mm; the ESC gives {GL.ESC_MOTOR:.0f}</dd></dl></div>""")
    return ''.join(o)


def page():
    return f'''<meta charset="utf-8">
<title>Modular Floor</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: the verdict first, then the two plans to one scale, the numbers, then helps and hurts. Same type and palette as the Brain Box review. */
:root{{
  --paper:#eef1f4; --card:#ffffff; --ink:#1b2330; --muted:#5a6575; --line:#d3dae3; --accent:#2c64a8; --chip:#eef2f7;
  --good:#2e7d4f; --bad:#b8402f; --tint:#f7dcd6; --part:#c9d6e6; --mod:#e7c98f; --plate:#aab4c0; --hole:#c7cfd9;
  --f-display:"Barlow Semi Condensed","Arial Narrow",system-ui,sans-serif;
  --f-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{
  --paper:#10151c; --card:#171e28; --ink:#e4e9f0; --muted:#94a1b2; --line:#283240; --accent:#6ea6e6; --chip:#1f2835;
  --good:#5fbf86; --bad:#ef7a66; --tint:#4a2620; --part:#3a5273; --mod:#7d6230; --plate:#566272; --hole:#39434f; color-scheme:dark}}}}
:root[data-theme="dark"]{{
  --paper:#10151c; --card:#171e28; --ink:#e4e9f0; --muted:#94a1b2; --line:#283240; --accent:#6ea6e6; --chip:#1f2835;
  --good:#5fbf86; --bad:#ef7a66; --tint:#4a2620; --part:#3a5273; --mod:#7d6230; --plate:#566272; --hole:#39434f; color-scheme:dark}}
body{{background:var(--paper);color:var(--ink);font:15px/1.55 var(--f-body);margin:0}}
.wrap{{max-width:1040px;margin:0 auto;display:flex;flex-direction:column;gap:24px;box-sizing:border-box;
  padding-block:22px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
h1{{font:600 34px/1.05 var(--f-display);margin:0;text-wrap:balance}}
h2{{font:600 22px/1.15 var(--f-display);margin:0;text-wrap:balance}}
p{{margin:0;max-width:74ch}}
.lede{{color:var(--muted)}}
section{{display:flex;flex-direction:column;gap:10px;min-width:0}}
.verdict{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--good);border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px}}
.plans{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
figure{{margin:0;display:flex;flex-direction:column;gap:6px;min-width:0}}
figcaption{{font-size:13px;color:var(--muted);max-width:74ch}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:8px;min-width:0}}
.panel h3{{font:600 17px/1.2 var(--f-display);margin:0}}
svg{{display:block;width:100%;height:auto;color:var(--ink)}}
.scroll{{overflow-x:auto}}
.scroll svg{{min-width:560px;max-width:680px}}
.tbl{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:680px;font-size:14px}}
th,td{{text-align:left;padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
th{{font:600 12px var(--f-body);letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}}
td.r{{color:var(--muted);white-space:nowrap}}
.m{{font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:13px}}
.no{{color:var(--bad);font-weight:600}} .yes{{color:var(--good);font-weight:600}}
.lays{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
.lays dl{{margin:0;display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 10px;font-size:13px}}
.lays dt{{color:var(--muted)}}
.lays dd{{margin:0;font-variant-numeric:tabular-nums}}
table.pitch{{min-width:520px}}
.up{{fill:var(--accent);fill-opacity:.55;stroke:var(--muted);stroke-width:.6}}
.wb,.wm{{fill:none;stroke-width:1.5;stroke-linejoin:round}}
.wb{{stroke:#d8392b}}
.wm{{stroke:#c28a00}}
.wm.dash{{stroke-dasharray:3 2.5}}
.mt{{fill:#c28a00;stroke:var(--card);stroke-width:.8}}
.key{{display:inline-block;width:22px;height:0;vertical-align:middle;margin:0 3px 0 0;border-top:2px solid #d8392b}}
.key.y{{border-top-color:#c28a00}}
.key.d{{border-top:2px dashed #c28a00}}
.dk{{fill:var(--accent);fill-opacity:.18;stroke:var(--accent);stroke-width:.6;stroke-dasharray:3 2}}
.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
.two ul,.plain{{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px;font-size:14px}}
.notes{{font-size:13px;color:var(--muted);display:flex;flex-direction:column;gap:6px}}
a{{color:var(--accent)}}
.body{{fill:var(--chip);stroke:var(--muted);stroke-width:1.6}}
.bodyline{{fill:none;stroke:var(--ink);stroke-width:2}}
.hole{{fill:var(--hole)}}
.cell{{fill:none;stroke:var(--line)}}
.mod{{fill:var(--mod);fill-opacity:.55;stroke:var(--muted);stroke-width:.8}}
.fr{{fill:var(--mod);stroke:var(--muted);stroke-width:.6}}
.pt{{fill:var(--part);stroke:var(--muted);stroke-width:.8}}
.over{{fill:var(--bad);fill-opacity:.2}}
.over-t{{fill:var(--bad)}}
.lb{{font:500 10.5px var(--f-body);fill:currentColor}}
.ts{{font:400 11.5px var(--f-body);fill:currentColor}}
.tb{{font:600 13px var(--f-body);fill:currentColor}}
.tm{{font:500 11.5px var(--f-mono);fill:currentColor}}
.dim{{fill:var(--muted)}}
.pl{{fill:var(--plate)}}
.mdl{{fill:var(--mod);stroke:var(--muted);stroke-width:.5}}
.prt{{fill:var(--part);stroke:var(--muted);stroke-width:.6}}
@media (max-width:760px){{.plans,.two,.lays{{grid-template-columns:minmax(0,1fr)}}h1{{font-size:28px}}}}
</style>

<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:8px">
    <h1>Modular Floor</h1>
    <p class="lede">Your idea: one base, and a small printed holder for each part, so a bad fit costs one small reprint instead of a whole body. Checked against your real parts, the slicer and the drop sim.</p>
  </header>

  <div class="verdict">
    <p><b>Keep the idea.</b> One base with cheap holders takes a fit change from {hm(TUB_MIN)} to {fm_lo}-{fm_hi} minutes. And there are lots of ways to lay it out, as you said. Real 42 mm cells fit in two full layers, though the body grows to about {GF_TALL:.0f} mm tall against {LAY[0]['stats']['top']:.0f}.</p>
    <p>My pick is smaller still: a floor of holes, with a low frame round each part. It fits on one level, adds about {add_hole:.0f} g, and kept every part within {moved:.1f} mm over {drops} sim drops. The same floor also takes different layouts, so choosing one isn't final. Weight isn't the deciding problem, and you don't need snaps, because the lid does the holding.</p>
  </div>

  <section aria-labelledby="h-plan">
    <h2 id="h-plan">What full-size cells cost</h2>
    <p>A Gridfinity holder is always a whole number of cells, so every part rounds up. On one floor with the packs on the walls, pack, Pi box, pack is {F['bare']:.0f} mm of parts but {F['across']['42']:.0f} mm on the grid, against {F['inner'][1]:.0f} mm inside the body. I first called that "doesn't fit". That only holds for one floor and the sim's layout: two full layers take the {F['cells']} cells in {2 * F['cap'][0] * F['cap'][1]}, but they stand about {GF_TALL:.0f} mm tall.</p>
    <div class="plans">
      <div class="panel"><h3>Real Gridfinity, 42 mm, one floor</h3><figure>{plan_grid()}<figcaption>{F['cells']} cells need a grid of 252 × 210 on one floor. The tan is what each holder wastes round its part.</figcaption></figure></div>
      <div class="panel"><h3>Holes every 15 mm, frames off the grid</h3><figure>{plan_frames()}<figcaption>A frame can be any size, because only its pegs have to land on holes. A rough layout to show the fit, not a design: pegs aren't placed, and these sizes aren't all measured. The row across comes to {F['framed']:.0f} mm.</figcaption></figure></div>
    </div>
  </section>

  <section aria-labelledby="h-lay">
    <h2 id="h-lay">Layers and other layouts</h2>
    <p><b>On hold.</b> Holders come first: nothing here matters until each part stays in its holder and each holder stays in the floor.</p>
    <p>All four fit a 250 × 140 footprint as holes and frames, checked for collisions and against your wire lengths. Blue parts sit on a shelf or deck, and the rest stand on the floor. These are rough layouts for comparing, and only A has a sim behind it.</p>
    <p><b>The wires moved three of these.</b> A pack's lead leaves by its end, and I'd drawn that end about 3 mm from an ESC. So A's ESCs moved 19.5 mm back, and B's and C's packs moved 20 mm forward. C's deck also came off its ESCs: lying flat, their leads come out of the top, with 3 mm to the deck. That took C from 201 to {LAY[2]['stats']['long']:.0f} mm long.</p>
    <p><b>Nothing is out of reach, and A has wire to spare.</b> One pack feeds both ESCs, so its {GL.PACK_LEAD:.0f} mm lead plus an ESC's {GL.ESC_POWER:.0f} mm red and black gives {GL.BATTERY:.0f} mm, before the Y-harness adds more. A uses {min(LAY[0]['wires']['bat']):.0f} and {max(LAY[0]['wires']['bat']):.0f} of that, so about {min(LAY[0]['wires']['spare']):.0f} to {max(LAY[0]['wires']['spare']):.0f} mm a run has to be tucked away, and there's room over the ESCs while the box stays {LAY[0]['stats']['top']:.0f} mm tall. D uses {min(LAY[3]['wires']['bat']):.0f} and {max(LAY[3]['wires']['bat']):.0f}, so almost nothing to tuck. Each ESC feeds two motors, so its yellow and blue get spliced anyway, and past {GL.ESC_MOTOR:.0f} mm is just more of the 18 AWG wire on the list.</p>
    <p class="notes"><span><span class="key"></span>Battery: pack to both ESCs.</span><span><span class="key y"></span>Motor: ESC to its two motors (dots), on T3's wheelbase centered in the body.</span><span><span class="key d"></span>Past the ESC's own {GL.ESC_MOTOR:.0f} mm.</span><span>Runs are measured along x then y, plus {GL.UP_OVER:.0f} mm for climbing over a wall.</span></p>
    <div class="lays">{lay_cards()}</div>
    <p><b>My pick for the first robot is A.</b> The sim already reads that layout, so sim against reality stays clean, and a pack swap only takes the lid off. The hole floor makes that cheap to change: D uses the same floor with the frames moved. D is the one I'd try next. The packs' share of the roll inertia drops to {LAY[3]['stats']['roll_ratio']:.2f} of A's, but the sim has no knob for that yet, so I can't say if it helps. D's leads leave by the front and run back along the packs, which uses up the spare wire. B and C also need a shelf or deck, and whatever sits on it has to come off to swap a pack.</p>
    <div class="tbl"><table class="pitch"><thead><tr><th>Smaller cells</th>{''.join(f"<th>{r['pitch']} mm</th>" for r in PITCH)}<th>Holes + frames</th></tr></thead><tbody>
      <tr><td class="r">Cells needed</td>{''.join(f'<td class="m">{r["need"]}</td>' for r in PITCH)}<td class="m">no cells</td></tr>
      <tr><td class="r">Cells on one floor</td>{''.join(f'<td class="m">{r["cap"]}</td>' for r in PITCH)}<td class="m">-</td></tr>
      <tr><td class="r">Layers, at least</td>{''.join(f'<td class="m">{r["layers"]}</td>' for r in PITCH)}<td class="m">1</td></tr>
    </tbody></table></div>
    <p class="notes">That table counts area only, with the packs on edge, so it's a lower limit. 10 mm squeaks through on area but almost certainly won't pack. Smaller cells waste less, and holes with frames are the far end of that: the holder is exactly the part's size.</p>
  </section>

  <section aria-labelledby="h-num">
    <h2 id="h-num">The numbers</h2>
    <div class="tbl"><table>
      <thead><tr><th></th><th>Print 1 style: bays in the body</th><th>Real Gridfinity</th><th>Holes + frames</th></tr></thead>
      <tbody>
        <tr><td class="r">Fits a 250 × 140 body</td><td><span class="yes">Yes</span></td><td>One floor: <span class="no">no</span>, needs about 257 × 215. Two layers: <span class="yes">yes</span>, about {GF_TALL:.0f} mm tall</td><td><span class="yes">Yes</span>: {F['framed']:.0f} of {F['inner'][1]:.0f} mm across</td></tr>
        <tr><td class="r">Mass added</td><td class="m">-</td><td class="m">+{add_open:.0f} to +{add_skin:.0f} g ({100 * add_open / T3_G:.1f}-{100 * add_skin / T3_G:.1f} % of T3)</td><td class="m">+{add_hole:.0f} g ({100 * add_hole / T3_G:.1f} %)</td></tr>
        <tr><td class="r">How much the parts rise</td><td class="m">0</td><td class="m">+3.4 to +6.0 mm</td><td class="m">0</td></tr>
        <tr><td class="r">Reprint to change one fit</td><td class="m">{hm(TUB_MIN)}, {TUB_G:.0f} g (the whole tub)</td><td class="m">{gm_lo}-{gm_hi} min, {g_lo:.0f}-{g_hi:.0f} g</td><td class="m">{fm_lo}-{fm_hi} min, {f_lo:.1f}-{f_hi:.0f} g</td></tr>
        <tr><td class="r">Print every holder</td><td class="m">-</td><td class="m">{hm(T['grid']['min'])}, {T['grid']['g']:.0f} g</td><td class="m">{hm(T['frame']['min'])}, {T['frame']['g']:.0f} g</td></tr>
        <tr><td class="r">Sim drops, worst part</td><td class="m">1.6 mm (fitted bays)</td><td>Not simulated</td><td class="m">{moved:.1f} mm, 0 of {drops} out of place</td></tr>
      </tbody>
    </table></div>
    <figure class="scroll">{section()}</figure>
    <p class="notes">Grams and times are from the slicer, on your draft settings, with walls at about half each part's height. "Mass added" is holders plus the floor's change, for a 210 × 126 patch of floor. It leaves out the bay walls the base would lose, so the real figures are lower. The base itself wasn't sliced.</p>
  </section>

  <section aria-labelledby="h-weight">
    <h2 id="h-weight">Your guess on weight</h2>
    <p>Right direction, small effect. The sim's T3 reads almost the same at 5 % heavier, which is more than Gridfinity would add, and with its center of mass 3 mm higher, which is more than either would move it. Upright goes {N['drawn']['up']:.2f} to {N['mass+5%']['up']:.2f} and {N['z+3']['up']:.2f}, the step stays at {N['drawn']['climb']:.0f} mm, and the turn goes {N['drawn']['turn']:.0f} to {N['mass+5%']['turn']:.0f} and {N['z+3']['turn']:.0f} mm. Those are one design's readings. Height costs more in the box itself: its stack is already too tall for the lid, and Gridfinity would add up to 6 mm.</p>
  </section>

  <section aria-labelledby="h-hh">
    <h2 id="h-hh">Where it helps and hurts</h2>
    <div class="two">
      <div class="panel"><h3>Helps</h3><ul>
        <li><b>Fit changes.</b> Print 1 came back with every fit loose. With holders, a second try costs {hm(T['frame']['min'])} in all, and the base stays.</li>
        <li><b>Parts you haven't measured.</b> The PCA, ESP32, IMU and alarm can start from a guess, because a wrong guess costs minutes.</li>
        <li><b>Balance you can adjust on the robot.</b> T3's step falls from 150 to 57 mm with its center of mass 5 mm forward. Moving one pack 15 mm shifts it about {one:.0f} mm, so the sim's pack knob becomes a real one.</li>
        <li><b>The same insides in different bodies.</b> Any body with this hole pattern takes the same holders, and every design in the search carries the same parts.</li>
        <li><b>Repairs.</b> A broken holder is a small reprint.</li>
      </ul></div>
      <div class="panel"><h3>Hurts</h3><ul>
        <li><b>Pegs take the side loads.</b> A pack hit its frame with {pk_pack:.0f} N (90th percentile, 1 m onto hard ground, no tyres). That's about {peg_n:.0f} N a peg with four 5 mm pegs, or {peg_mpa:.0f} MPa. I don't know what your printed pegs can take, so this gets tested first.</li>
        <li><b>Thin walls may not last.</b> The sim treats frames as rigid. At 1.2 mm, the walls round the packs may need to be thicker.</li>
        <li><b>It needs a flat floor.</b> Print 1's tunnel ridge gives two levels. Putting the Pi on the floor also helps the box's height problem.</li>
        <li><b>Holes open the floor.</b> Dirt can get in from below, and blind holes would add about 1 mm of floor. The hole patch also takes {fh['min'] - fl['min']} minutes longer to print.</li>
        <li><b>The first build takes longer.</b> Add {hm(T['frame']['min'])} of holders on top of the base.</li>
      </ul></div>
    </div>
  </section>

  <section aria-labelledby="h-snap">
    <h2 id="h-snap">Snap, friction or lid?</h2>
    <p><b>Withdrawn: this isn't a result.</b> The drop test welds every frame to the floor, so the pegs never get pulled. Its lid presses through solid rubber columns it counts at 1 g each; solid, they'd be about 109 g in all. With the lid over a Pi on a flat floor, the ESC's column would be about 39 mm tall and the PCA's about 60. So what holds each part is still open, and C10 with it. What follows is kept for the record.</p>
    <p>The lid. I dropped the same frames with no lid as a control. Over {drops} drops the Pi ended out of place {out_open['pi_stack']} times, the PCA {out_open['pca']}, and the packs {out_open['pack_L']} and {out_open['pack_R']}. With the lid's TPU pads, none did. Those pads saw up to {pad_pack:.0f} N per pack, which I wouldn't expect a printed snap or friction fit to hold. <a href="https://printables.com/model/452675-gridfinity-clickfinity-baseplate-no-magnets-univer">One Gridfinity latch design</a> has a user report that PLA deforms under the constant load, and standard Gridfinity only holds by gravity or magnets.</p>
    <p>So let the pegs stop sideways movement and the lid stop everything lifting. A slight friction fit is still handy for keeping holders in place while the lid is off. This also backs one lid for C10.</p>
  </section>

  <section aria-labelledby="h-next">
    <h2 id="h-next">Not tested, and the guesses</h2>
    <ul class="plain">
      <li><b>Not tested:</b> how strong printed pegs are, how a frame flexes, or base warp over a long frame. The sim's ESC is a plain box with no wires, so it can't see them wedging the ESC in an open frame, as yours does on the bench. The sim's hard ground with no tyres is harsher than the robot will see.</li>
      <li><b>Gridfinity's foot under side loads:</b> not simulated. Its 45° taper could push a holder upward against the lid.</li>
      <li><b>My picks:</b> holes every 15 mm, 1.2 mm walls, 0.25 mm round each part, walls at about half each part's height.</li>
      <li><b>Your bench:</b> a 5 mm peg wants a 5.1 mm hole. My 5.3 fell out when tipped.</li>
      <li><b>Wire guesses:</b> {GL.PACK_ROOM:.0f} mm of straight lead off a pack's end, {GL.ESC_ROOM:.0f} off an ESC, a pack's lead leaving by its short end, and where the motors' wires come in. The first robot's axles aren't drawn yet, so those are T3's. The Y-harness's length is left out.</li>
      <li><b>Sizes not measured:</b> PCA, ESP32, servo BEC, alarm and IMU. Gridfinity's foot profile comes from secondary sources, and I couldn't open the official spec file.</li>
    </ul>
  </section>
</div>
'''


if __name__ == '__main__':
    check()
    p = os.path.join(HERE, 'grid_eval.html')
    open(p, 'w', encoding='utf-8').write(page())
    print('wrote', p)
    print('added g: grid %.0f to %.0f, frames %.0f | moved %.2f | pack frame %.0f N, per peg %.0f N, %.1f MPa | pad %.0f N | open %s | one pack 15 mm moves CoM %.2f mm' % (
        add_open, add_skin, add_hole, moved, pk_pack, peg_n, peg_mpa, pad_pack, out_open, one))
