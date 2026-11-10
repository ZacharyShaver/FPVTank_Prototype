"""Would a Gridfinity-like floor work in the brain box? (2026-11-08) Zach: "print bottom patterns that either snap in or friction
fit to the base ... each component gets a gridfinity like box to hold it ... evaluate this idea, see where it would help and hurt."

    python twin/grid_eval.py          # the fit table, then real pieces as STLs, sliced: twin/out/grid/ and grid_eval.json

Two things Gridfinity's rules set, tested against his real parts:
  - a module's outline is a whole number of cells, so every part rounds up;
  - a part stands on a stepped foot, so it rises.
The second half builds both kinds of piece, so the grams and minutes come from the slicer, not from an estimate:
  grid     real Gridfinity: 42 mm cells, the stepped foot (0.8 + 1.8 + 2.15), a 1.2 mm floor on it
  holes    the outline free of the grid: a floor with a hole every HOLE_PITCH mm, and a wall frame round each part with pegs that
           drop into the holes. No floor of its own, so the part stays on the body's floor. Printed upside down, pegs up.
"""
import json, math, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
from export import write_stl

OUT = os.path.join(config.TWIN_OUT, 'grid')
INNER = (244.8, 134.3)            # mm: inside a 250 long, 139.5 wide body with print 1's 2.6 walls
FLOOR = 2.6                       # print 1's floor
WALL, FIT, RIM = 1.2, 0.25, 0.25  # a module's wall (picked), the room round a part (picked), Gridfinity's 0.25 a side off the cell
HOLE_PITCH, PEG, HOLE = 15.0, 5.0, 5.3   # the hole floor: picked; 0.15 a side is his tested slide fit
# (name, long, wide, tall, count, wall height, source). As they sit in the sim: packs and ESCs on edge. * = not calipered.
PARTS = [('Pack', 141.0, 26.0, 45.7, 2, 23, 'his model'), ('ESC', 45.0, 24.0, 34.0, 2, 17, 'his caliper'),
         ('Pi box', 98.5, 65.6, 36.5, 1, 15, 'the printed box'), ('PCA9685', 62.2, 25.7, 12.4, 1, 8, 'Adafruit size*'),
         ('ESP32', 55.0, 28.0, 12.0, 1, 8, 'typical dev board*'), ('Servo BEC slot', 48.0, 30.0, 15.0, 1, 8, 'the sims*'),
         ('LiPo alarm', 40.0, 25.0, 12.0, 1, 8, 'the review*'), ('Pololu', 25.4, 25.4, 9.5, 1, 8, 'listing'),
         ('INA219', 25.6, 20.4, 4.7, 1, 8, 'listing'), ('IMU', 25.0, 20.0, 4.6, 1, 8, 'the sims*')]


def cells(mm, pitch):
    """how many cells a part this long needs: the outline is n x pitch less the rim, inside it the walls and the fit"""
    return max(1, math.ceil((mm + 2 * (WALL + FIT) + 2 * RIM) / pitch))


def fit():
    out = dict(across={}, bare=26 + 65.6 + 26, framed=2 * (26 + 2 * (WALL + FIT)) + 65.6 + 2 * (WALL + FIT), inner=INNER)
    print('Across the body, the row that sets its width: pack, Pi box, pack. Inside %.1f mm.' % INNER[1])
    print('  bare parts        %5.1f' % out['bare'])
    print('  framed, off-grid  %5.1f  yes' % out['framed'])
    for p in (42, 21, 14, 10, 7):
        w = (2 * cells(26, p) + cells(65.6, p)) * p
        out['across'][p] = w
        print('  %4d mm grid       %5.0f  %s' % (p, w, 'yes' if w <= INNER[1] else 'NO'))
    print('\nEvery part on a 42 mm grid:')
    tot, real, rows = 0, 0.0, []
    for n, a, b, h, c, _, src in PARTS:
        ca, cb = cells(a, 42), cells(b, 42)
        tot += ca * cb * c; real += a * b * c
        rows.append(dict(name=n, long=a, wide=b, n=c, cells=[ca, cb], used=a * b / (ca * cb * 42 * 42), src=src))
        print('  %-15s %5.1f x %5.1f x%d -> %d x %d cells, %3d %% of them used (%s)' % (n, a, b, c, ca, cb, 100 * rows[-1]['used'], src))
    cap = (int(INNER[0] // 42), int(INNER[1] // 42))
    print('  needs %d cells; the body holds %d x %d = %d. The parts themselves cover %.0f %% of the floor, %.0f %% of the cells they take.'
          % (tot, cap[0], cap[1], cap[0] * cap[1], 100 * real / (INNER[0] * INNER[1]), 100 * real / (tot * 42 * 42)))
    out.update(cells=tot, cap=cap, rows=rows, floor_used=real / (INNER[0] * INNER[1]))
    return out


# ---------------------------------------------------------------- the pieces
def foot(cq, x, y):
    """one cell's stepped foot, top at z 4.75. Corners left square: it overstates the volume by about 1 %"""
    def lvl(w, z):
        return cq.Workplane('XY').workplane(offset=z).center(x, y).rect(w, w)
    a = lvl(35.6, 0).workplane(offset=0.8).rect(37.2, 37.2).loft()
    b = lvl(37.2, 0.8).extrude(1.8)
    c = lvl(37.2, 2.6).workplane(offset=2.15).rect(41.5, 41.5).loft()
    return a.union(b).union(c)


def grid_module(cq, nx, ny, wall_h, floor=1.2):
    """a real Gridfinity module: its feet, a floor on them, and a wall round the outline"""
    W, D = 42.0 * nx - 2 * RIM, 42.0 * ny - 2 * RIM
    body = cq.Workplane('XY').workplane(offset=4.75).rect(W, D).extrude(floor + wall_h)
    body = body.cut(cq.Workplane('XY').workplane(offset=4.75 + floor).rect(W - 2 * WALL, D - 2 * WALL).extrude(wall_h + 1))
    for i in range(nx):
        for j in range(ny):
            body = body.union(foot(cq, 42.0 * (i - (nx - 1) / 2), 42.0 * (j - (ny - 1) / 2)))
    return body


def grid_plate(cq, nx, ny, skin=0.0):
    """the baseplate: open cells, the foot's shape upside down. skin > 0 closes the bottom"""
    H = 4.65
    p = cq.Workplane('XY').rect(42.0 * nx, 42.0 * ny).extrude(H + skin)
    for i in range(nx):
        for j in range(ny):
            x, y = 42.0 * (i - (nx - 1) / 2), 42.0 * (j - (ny - 1) / 2)
            def lvl(w, z):
                return cq.Workplane('XY').workplane(offset=z + skin).center(x, y).rect(w, w)
            p = p.cut(lvl(36.3, -0.01 if not skin else 0).workplane(offset=0.71 if not skin else 0.7).rect(37.7, 37.7).loft())
            p = p.cut(lvl(37.7, 0.7).extrude(1.8))
            p = p.cut(lvl(37.7, 2.5).workplane(offset=2.16).rect(42.0, 42.0).loft())
    return p


def frame_module(cq, L, W, wall_h, n_peg):
    """the off-grid module, as printed: upside down, the frame's rim on the bed and the pegs up. Posts sit outside the short ends."""
    a, b = L + 2 * FIT, W + 2 * FIT
    m = cq.Workplane('XY').rect(a + 2 * WALL, b + 2 * WALL).extrude(wall_h).cut(cq.Workplane('XY').rect(a, b).extrude(wall_h + 1).translate((0, 0, -0.5)))
    xs = [(a / 2 + WALL + 2.5) * s for s in (-1, 1)]
    ys = [0.0] if n_peg == 2 else [-b / 4, b / 4]
    for x in xs:
        for y in ys:
            m = m.union(cq.Workplane('XY').center(x, y).circle(3.5).extrude(wall_h))
            m = m.union(cq.Workplane('XY').workplane(offset=wall_h).center(x, y).circle(PEG / 2).extrude(FLOOR - 0.2))
    return m


def hole_floor(cq, x, y, pitch=None):
    p = cq.Workplane('XY').rect(x, y).extrude(FLOOR)
    if pitch:
        nx, ny = int(x // pitch) - 1, int(y // pitch) - 1
        pts = [(pitch * (i - (nx - 1) / 2), pitch * (j - (ny - 1) / 2)) for i in range(nx) for j in range(ny)]
        p = p.cut(cq.Workplane('XY').pushPoints(pts).circle(HOLE / 2).extrude(FLOOR + 1).translate((0, 0, -0.5)))
    return p


def pieces():
    import cadquery as cq
    P = {'floor_plain': hole_floor(cq, 210, 126), 'floor_holes': hole_floor(cq, 210, 126, HOLE_PITCH),
         'plate_open': grid_plate(cq, 5, 3), 'plate_on_skin': grid_plate(cq, 5, 3, skin=FLOOR)}
    for n, a, b, h, c, wh, _ in PARTS:
        k = re.sub(r'\W+', '_', n.lower())
        P['grid_' + k] = grid_module(cq, cells(a, 42), cells(b, 42), wh)
        P['frame_' + k] = frame_module(cq, a, b, wh, 4 if a > 90 else 2)
    return P


def slice_all(P):
    os.makedirs(OUT, exist_ok=True)
    res = {}
    for k, w in P.items():
        path = os.path.join(OUT, k + '.stl')
        write_stl(w.val().wrapped, path, lin=0.05, ang=0.3)
        vol = w.val().Volume() / 1000.0
        r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'orca.py'), path, '--draft', '--name', k, '--out', os.path.join(OUT, 'gcode')],
                           capture_output=True, text=True, timeout=300)
        s = r.stdout + r.stderr
        t = re.search(r'(?:(\d+)h\s*)?(\d+)m\s*(\d+)?s?', s)
        g = re.search(r'([\d.]+)\s*g\b', s)
        res[k] = dict(cm3=round(vol, 2), g=float(g.group(1)) if g else None, min=(int(t.group(1) or 0) * 60 + int(t.group(2))) if t else None, line=s.strip().splitlines()[-1][:160] if s.strip() else '')
        print('%-24s %6.1f cm3  %s g  %s min' % (k, vol, res[k]['g'], res[k]['min']), flush=True)
    return res


def totals(res):
    """the whole set of modules, each kind, against the plain floor"""
    print('\nThe whole set:')
    out = {}
    for kind in ('grid', 'frame'):
        g = sum(res['%s_%s' % (kind, re.sub(r'\W+', '_', p[0].lower()))]['g'] * p[4] for p in PARTS)
        m = sum(res['%s_%s' % (kind, re.sub(r'\W+', '_', p[0].lower()))]['min'] * p[4] for p in PARTS)
        out[kind] = dict(g=round(g, 1), min=m)
        print('  %-6s modules: %5.0f g, %d min' % (kind, g, m))
    print('  the 210 x 126 floor patch: plain %.0f g, hole grid %.0f g, Gridfinity plate open %.0f g, on a skin %.0f g' % (
        res['floor_plain']['g'], res['floor_holes']['g'], res['plate_open']['g'], res['plate_on_skin']['g']))
    return out


if __name__ == '__main__':
    F = fit()
    print()
    R = slice_all(pieces())
    T = totals(R)
    json.dump(dict(fit=F, pieces=R, totals=T), open(os.path.join(config.TWIN_OUT, 'grid_eval.json'), 'w'), indent=1, default=float)
