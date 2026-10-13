"""Bench stand for the v2 head (2026-10-11): a plate with a shallow socket the pan coil's base drops into.

Zach: "a bottom part that i can stand the pan tilt in that is stable and does not lock the gears up", for the bench
until the body is printed. The base stands on its gear bay, whose floor plate is 1.5 thick with four M2 heads under
it and the small gear's M3 head 0.35 over its underside, so a table can press on the plate or the screws. The stand
holds the bay by its outline (CLEAR a side, WALL_H up the side, below the well's overhang at FLOOR_Z) and carries the
floor plate on a ledge round its edge. Inside the ledge it is open: nothing under the gears or the screw heads, the
M2 heads in notches, and a driver reaches both axis screws from below with the head standing in it.

V2 (2026-10-12), Zach: "more room for the gears on height and a spot to pin the black wires to the base so they dont
fly in the gears". Set 10 sends the tilt servo's wires straight down the pan axis and out the floor plate's middle hole,
where the small gear's three M3 heads turn (r 3.05..8.75, just inside the plate's underside). V1 stood the floor plate
3 mm over the table, so the wires coming out had nowhere to go but sideways, through the heads. V2 (RAISED) stands the
head RISE higher on a hollow riser, as a section of the body's nose floor would (Zach: "the stand should be like a
section out of that"; chassis-v2/hull.py stands the base straight on the hull floor, which needs this same pocket): the ledge now has a 30 deg (off vertical) chamfer under it, and under the axis a
slotted tube (the post) takes the wires straight down, inside the heads' sweep, to the floor; they leave through a
doorway at its foot, run along the floor toward +X (the servo side, where his PCA9685 sits) and out an arch, and press
into a V cleat on the plate. The post's slot faces -X, away from their pull. Superseded: v1 (a 3 mm plate, the window
open to the table, a driver from below; the head lifts out for the screws now).

Writes out/print-pan/bench_stand.stl (print-oriented, plate down) and _fig_bench_stand.stl (head frame, for the
fit view), and prints the checks.

    python head-v2/fixes/bench_stand.py [--checks]      # --checks: the checks only, no STL
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from skimage import measure
import tree_parts as T
from tree_parts import U, box, cyl_z, sample, project, unfold, decimate, report, quiet, mesh_set
import pan_coil_b as P
import pan_coil_b_check as C
import pan_coil_b_print as PP

TIP = P.R_IN_G + P.TOOTH
BX0, BX1, BY, BRC = -P.BARREL_R - 9, P.CENTRE + TIP + 3.5, TIP + 4, 3.0   # the bay shell's outline: bay(), floor()
REST_Z = P.BAY_Z0                  # the floor plate's underside
CLEAR = 0.4                        # a side: a loose drop-in, it only has to stop the base walking or turning
WALL_T, WALL_H, LEAD = 2.4, 8.0, 1.0   # its top 3 under FLOOR_Z, where the well overhangs the bay
WALL_TOP = REST_Z + WALL_H
LEDGE = 6.0                        # the ledge reaches this far in under the outline; the floor plate's flat starts at 3
PLATE_T = 3.0
PX0, PX1, PY, PRC = -55.0, 75.0, 60.0, 10.0   # the footprint: 55 to 75 from the pan axis
NOTCH_R = 2.6                      # round each floor M2's head
M2_HEAD_R, M2_HEAD_H = 1.9, 2.0    # M2 socket head, ISO 4762 (his are socket heads: a guess they're these)
# ---- v2 (2026-10-12): raised, a wire post under the axis, an arch and a V cleat toward +X -------------------------------
RAISED = True
RISE = 12.0 if RAISED else 0.0    # clear height from the stand's floor up to the floor plate's underside: the wires drop
                                   # straight ~6 inside the post, then turn; shallow enough for a sump in the body's floor
LEDGE_DEG = 30.0                   # the ledge's underside chamfer, off vertical (Zach's limit): no supports in the riser
POST_R, BORE_R, SLOT_W = 5.0, 2.4, 2.2   # the wire post: 4.8 bore (a jumper plug's 3.5 diagonal passes), slot to lay them in
POST_GAP = 3.0                     # its top under the floor plate; the funnel on it opens to FUNNEL_R
FUNNEL_R = 3.4
DOOR_H = 4.0                       # the doorway at its foot, toward +X: straight sides, then a pointed roof (30 deg)
ARCH_W, ARCH_H = 8.0, 4.0          # the riser's +X arch: width; straight sides, then a pointed roof (top 10.9 up)
CLEAT_X, CLEAT_L, CLEAT_W, CLEAT_H = 65.0, 8.0, 10.0, 8.0   # the V cleat outside the arch, along X
CLEAT_V0, CLEAT_V1 = 0.6, 3.2      # the V: gap at its bottom (1.0 up) and at its top; any wire wedges at its own width
Z0 = REST_Z - PLATE_T - RISE
FLOOR_TOP = Z0 + PLATE_T
PRINT = config.out('print-pan', 'bench_stand.stl')
FIG = config.out('print-pan', '_fig_bench_stand.stl')
FIG_WIRES = config.out('print-pan', '_fig_stand_wires.stl')   # v2: the wires' way under the head, for the fit view


def rrect(p, x0, x1, y0, y1, r):
    """Rounded rectangle in plan, corner radius r: a 2D signed distance."""
    qx = np.abs(p[0] - (x0 + x1) / 2) - ((x1 - x0) / 2 - r)
    qy = np.abs(p[1] - (y0 + y1) / 2) - ((y1 - y0) / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def prism(d2, p, z0, z1):
    return T._cyl(d2, np.abs(p[2] - (z0 + z1) / 2) - (z1 - z0) / 2)


def outline(p):
    return rrect(p, BX0, BX1, -BY, BY, BRC)


def pointed(u, w, z0, z1, p):
    """A slot |u| <= w/2 from z0 up, straight to z1, then a roof LEDGE_DEG off vertical to a point (prints unsupported)."""
    a = np.radians(LEDGE_DEG)
    roof = (np.abs(u) - w / 2) * np.cos(a) + (p[2] - z1) * np.sin(a)
    return np.maximum(np.maximum(np.abs(u) - w / 2, z0 - p[2]), roof)


def stand(p, features=True, window=True, notches=True, arch=True):
    if RAISED:
        return stand_v2(p, features, window, notches, arch)
    o = outline(p)
    s = U(prism(rrect(p, PX0, PX1, -PY, PY, PRC), p, Z0, REST_Z), prism(o - CLEAR - WALL_T, p, REST_Z - 1.0, WALL_TOP))
    # the socket, with a 45 deg lead-in round its mouth
    cuts = [prism(o - CLEAR - np.maximum(0, p[2] - (WALL_TOP - LEAD)), p, REST_Z, WALL_TOP + 1)]
    if window:
        cuts.append(prism(o + LEDGE, p, Z0 - 1, REST_Z + 1))
    if notches:
        cuts += [prism(np.hypot(p[0] - x, p[1] - y) - NOTCH_R, p, Z0 - 1, REST_Z + 1) for x, y in P.floor_screws()]
    return np.maximum(s, -U(*cuts))


def stand_v2(p, features=True, window=True, notches=True, arch=True):
    """V2: the plate, a hollow riser up to the socket, the ledge chamfered under, the wire post, the arch and the cleat.
    `window` off fills the riser's hollow (the control); `arch` off closes the arch (the wire path's control)."""
    o = outline(p)
    a = np.radians(LEDGE_DEG)
    s = U(prism(rrect(p, PX0, PX1, -PY, PY, PRC), p, Z0, FLOOR_TOP), prism(o - CLEAR - WALL_T, p, FLOOR_TOP - 1.0, WALL_TOP))
    cuts = [prism(o - CLEAR - np.maximum(0, p[2] - (WALL_TOP - LEAD)), p, REST_Z, WALL_TOP + 1)]   # the socket, as v1
    if window:   # the hollow: the socket's outline down low, closing in at LEDGE_DEG to the ledge's inner edge
        zc = REST_Z - (LEDGE + CLEAR) / np.tan(a)
        cuts.append(prism(o - CLEAR + np.maximum(0, p[2] - zc) * np.tan(a), p, FLOOR_TOP, REST_Z + 0.5))
    if notches:   # round the floor's M2 heads, straight down through the ledge (a blind floor met its slope in slivers)
        cuts += [prism(np.hypot(p[0] - x, p[1] - y) - NOTCH_R, p, FLOOR_TOP + 0.5, REST_Z + 1)
                 for x, y in P.floor_screws()]
    # clear of the small gear's three M3 heads, which turn just inside the floor plate's 18.7 hole (0.35 off its underside)
    if window:
        cuts.append(cyl_z(p, 0, 0, P.AX_FLOOR_HOLE_R + 1.0, FLOOR_TOP + 0.5, REST_Z + 0.5))
    if arch:   # out through the +X wall at the floor
        cuts.append(np.maximum(pointed(p[1], ARCH_W, FLOOR_TOP, FLOOR_TOP + ARCH_H, p),
                               np.maximum(BX1 - 3.0 - p[0], p[0] - (BX1 + CLEAR + WALL_T + 1.0))))
    s = np.maximum(s, -U(*cuts))
    # the wire post on the axis, with a funnel on top, its slot facing -X, a doorway at its foot toward +X
    top = REST_Z - POST_GAP
    r = np.hypot(p[0], p[1])
    s = U(s, cyl_z(p, 0, 0, POST_R, FLOOR_TOP - 0.5, top))
    funnel = np.maximum(r - (BORE_R + (FUNNEL_R - BORE_R) * np.clip((p[2] - (top - 1.2)) / 1.2, 0, 1)), top - 1.2 - p[2])
    bore = cyl_z(p, 0, 0, BORE_R, FLOOR_TOP, top + 1)
    near = np.abs(p[0]) - (POST_R + 1.0)                       # the slot and the door go through the post's wall only
    slot = np.maximum(np.maximum(np.abs(p[1]) - SLOT_W / 2, np.maximum(p[0], near)), np.maximum(FLOOR_TOP - p[2], p[2] - (top + 1)))
    door = np.maximum(pointed(p[1], 2 * BORE_R, FLOOR_TOP, FLOOR_TOP + DOOR_H, p), np.maximum(-p[0], near))
    s = np.maximum(s, -U(funnel, bore, slot, door))
    # the V cleat outside the arch: press the wires down into it
    cl = box(p, (CLEAT_X - CLEAT_L / 2, -CLEAT_W / 2, FLOOR_TOP - 0.5), (CLEAT_X + CLEAT_L / 2, CLEAT_W / 2, FLOOR_TOP + CLEAT_H))
    hw = CLEAT_V0 / 2 + (CLEAT_V1 - CLEAT_V0) / 2 * np.clip((p[2] - (FLOOR_TOP + 1.0)) / (CLEAT_H - 1.0), 0, 1)
    v = np.maximum(np.abs(p[1]) - hw, (FLOOR_TOP + 1.0) - p[2])
    return U(s, np.maximum(cl, -v))


def wire_path(p, features=True, r=1.2):
    """Set 10's wires, as a bundle r 1.2: down the axis from the floor plate to the stand's floor, out the post's door,
    along the floor and out the arch into the cleat."""
    zf = FLOOR_TOP + r + 0.3
    down = cyl_z(p, 0, 0, r, zf, REST_Z + 2.0)
    run = T.cyl_x(p, 0, zf, r, 0, CLEAT_X - CLEAT_L / 2 - 1.0)
    return U(down, run)


def m2_heads(p, features=True):
    return U(*[cyl_z(p, x, y, M2_HEAD_R, REST_Z - M2_HEAD_H, REST_Z) for x, y in P.floor_screws()])


HEAD = {n: P.PARTS[n][0] for n in ('base', 'floor', 'tab_block', 'servo', 'gear_in', 'gear_out', 'screw_out', 'horn',
                                    'drum', 'bearing6704', 'bearing')}
HEAD['m2_heads'] = m2_heads
TURNING = ('gear_in', 'gear_out', 'screw_out', 'horn')
LO, HI = (BX0 - 5, -BY - 5, Z0 - 1), (max(BX1 + 5, CLEAT_X + CLEAT_L), BY + 5, WALL_TOP + 1)   # where the head can meet it


def moved(fn, dz):
    return lambda q, features=True: fn((q[0], q[1], q[2] - dz), features)


def clearance(fn_stand, names, dz=0.0, step=0.2):
    """The nearest the stand comes to any of `names` (mm), point to point: the stand's surface points against every
    grid point inside them. Not the stand's SDF read at those points: after the cuts it is only a lower bound, and the
    first run read 0.55 off the window's own top face, where there is no stand."""
    from scipy.spatial import cKDTree
    xs = [np.arange(LO[i], HI[i] + step, step) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing='ij')
    f = fn_stand((X, Y, Z))
    skin = (f < 0) & (f > -1.5 * step)
    tree = cKDTree(np.stack([X[skin], Y[skin], Z[skin]], -1))
    best = 1e9
    for n in names:
        lo, hi = np.array(P.PARTS[n][1], float), np.array(P.PARTS[n][2], float)
        xs = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
        X, Y, Z = np.meshgrid(*xs, indexing='ij')
        inside = HEAD[n]((X, Y, Z)) < 0
        best = min(best, float(tree.query(np.stack([X[inside], Y[inside], Z[inside] + dz], -1))[0].min()))
    return best


def checks():
    bad = 0
    def row(label, v, ok, note=''):
        nonlocal bad
        bad += not ok
        print(f'{label:<58}{v:>9.2f}   {note}' + ('' if ok else '   <==='))
    head = lambda q, features=True: U(*[f(q, features) for f in HEAD.values()])
    base_floor = lambda q, features=True: U(HEAD['base'](q), HEAD['floor'](q))
    print('seated (mm3 shared; 0 = clear)')
    v = C.overlap(head, stand, LO, HI, 0.25)
    row('  head (base, floor, M2 heads, gears, screws, servo) vs stand', v, v == 0)
    sx = lambda q, features=True: stand((q[0] - 1.0, q[1], q[2]))
    c = C.overlap(base_floor, sx, LO, HI, 0.25)
    row('  control: the stand 1.0 toward +X (must read > 0)', c, c > 0)
    nn = lambda q, features=True: stand(q, notches=False)
    c = C.overlap(m2_heads, nn, LO, HI, 0.1); row('  control: no notches, against the M2 heads (> 0)', c, c > 0)
    print('dropping in, 15 mm down to seated (worst mm3)')
    worst = 0.0
    for t in (15, 10, 6, 4, 2, 1, 0.5, 0.2, 0.0):
        worst = max(worst, C.overlap(moved(head, t), stand, LO, (HI[0], HI[1], HI[2] + 16), 0.3))
    row('  the whole head', worst, worst <= 0.0)
    print('turning parts: nearest stand surface (mm)')
    a = clearance(stand, TURNING); b = clearance(lambda q: stand(q, window=False), TURNING)
    row('  gears, horn, M3 head; floor plate on', a, a > 1.0)
    row('  control: no window (must read less)', b, b < a)
    a = clearance(stand, TURNING, dz=-(P.SPLIT_Z - REST_Z))
    row('  floor plate off (the base down on its rim)', a, a > 0.3)
    if RAISED:   # v2: the wires' way out, and the post keeping them inside the screw heads' sweep
        print("the wires' way, a bundle r 1.2: down the post, out its door, along the floor, out the arch (mm3)")
        v = C.overlap(wire_path, stand, LO, HI, 0.15)
        row('  against the stand', v, v == 0)
        c = C.overlap(wire_path, lambda q, features=True: stand(q, arch=False), LO, HI, 0.15)
        row('  control: no arch (> 0)', c, c > 0)
        sweep_r = P.AX_SCREW_R - P.AX_HEAD_R
        row("  the post's bore inside the M3 heads' sweep (r, mm)", BORE_R, BORE_R < sweep_r - 0.5,
            f'the heads turn from r {sweep_r:.2f} out')
    else:
        print('a driver from below, 4 across, up each axis (mm3 against the stand)')
        drv = lambda q, features=True: U(cyl_z(q, 0, 0, 2.0, Z0 - 20, REST_Z), cyl_z(q, P.CENTRE, 0, 2.0, Z0 - 20, REST_Z))
        lo2 = (LO[0], LO[1], Z0 - 21)
        v = C.overlap(drv, stand, lo2, HI, 0.2)
        row('  both axes', v, v == 0)
        c = C.overlap(drv, lambda q, features=True: stand(q, window=False), lo2, HI, 0.2)
        row('  control: no window (> 0)', c, c > 0)
    # the floor plate's flat underside on the ledge
    xs, ys = np.arange(BX0, BX1, 0.1), np.arange(-BY, BY, 0.1)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    on = (HEAD['floor']((X, Y, np.full_like(X, REST_Z + 0.05))) < 0) & (stand((X, Y, np.full_like(X, REST_Z - 0.05))) < 0)
    print(f'floor plate resting on the ledge: {on.sum() * 0.01:.0f} mm2')
    return bad


def build():
    step = 0.25
    # v2: the grid sits 0.0371 off the round numbers. On them, v2's floor and ledge planes fell exactly on grid nodes and
    # marching cubes made 25 zero-area folds; and the decimator put self-intersections back in, so v2 isn't decimated.
    sh = 0.0371 if RAISED else 0.0
    lo, hi = (PX0 - 1 + sh, -PY - 1 + sh, Z0 - 1 + sh), (PX1 + 1, PY + 1, WALL_TOP + 1)
    f = lambda Q: stand(Q)
    vol = sample(f, lo, hi, step)
    v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
    v_raw = v + np.array(lo)
    v = project(f, v_raw, step)
    with quiet():
        v = unfold(v, v_raw, faces)
        if RAISED:
            ms = mesh_set(v, faces)
        else:
            ms, _ = decimate(v, faces, 120000)
            ms = PP.clean(ms)
        ok, msg = report(ms)
    V, F = ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix()
    with quiet():   # the fit view's copy: v2 isn't decimated for print, so thin this one out (looks only)
        mf = mesh_set(V, F)
        if RAISED:
            mf.meshing_decimation_quadric_edge_collapse(targetfacenum=40000, qualitythr=0.5, preservenormal=True,
                                                        planarquadric=True, planarweight=0.002, autoclean=True)
        mf.save_current_mesh(FIG, binary=True)
    W = V - np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
    with quiet():
        mesh_set(W, F).save_current_mesh(PRINT, binary=True)
    print('bench_stand', msg, '' if ok else '   <-- CHECK')
    if RAISED:   # the wires' way, drawn for the fit view (head frame)
        st = 0.15
        lo2, hi2 = (-2.0, -2.0, FLOOR_TOP - 0.5), (CLEAT_X + CLEAT_L / 2, 2.0, REST_Z + 2.5)
        vol = sample(lambda Q: wire_path(Q), lo2, hi2, st)
        v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(st,) * 3)
        with quiet():
            mesh_set(v + np.array(lo2), faces).save_current_mesh(FIG_WIRES, binary=True)
    print('  %.1f x %.1f x %.1f mm' % tuple(W.max(0) - W.min(0)))
    return ok


if __name__ == '__main__':
    bad = checks()
    ok = '--checks' in sys.argv or build()
    sys.exit(1 if bad or not ok else 0)
