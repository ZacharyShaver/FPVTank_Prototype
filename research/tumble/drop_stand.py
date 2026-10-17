"""Workstream E (2026-10-17): a drop stand for the 15 cm drops (H3c). Holds a scale body still at a set height, in
any of the six starts, and lets it go with a pinch.

A base with a socket, a post with pin holes, an arm that pins to the post, and a pinch clamp: two jaws on their
own pivots, held shut on the body by a rubber band and snapped open together by pinching their handles. A gauge
whose top is at 150 mm sets the body's lowest point. Release is a pinch rather than a twist: a twist lets the body
slide out slowly at an uneven moment, which is the randomness the stand exists to remove.

    python research/tumble/drop_stand.py   -> research/models/drop_stand_*.stl, plus checks with controls

Frame (as used): Z up from the floor, the post at the origin, the arm along +Y to the clamp. Clamp frame: the
pivots at (+-PIV_A, 0) on axes along Y; a jaw's angle psi > 0 turns its tip inward.

Hardware: 1-2 rubber bands; tape on the jaw pads (grip); a heavy book on the base (the arm sticks out).
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
import cadquery as cq

DROP = 150.0                  # lowest point of the body above the floor at release, mm
# pinch clamp
PIV_A = 25.0                  # half the pivot spacing
ARM_T, ARM_D = 8.0, 12.0      # jaw arm: thickness in the jaw plane (X), depth (Y)
H_UP, L_DN = 60.0, 115.0      # handle above the pivot, jaw below it
PAD = (-115.0, -75.0)         # gripping zone on the jaw's inner face (z, clamp frame)
NOTCH_Z = (-28.0, -42.0)      # rubber-band grooves, both faces (above the tallest body's top)
PIN_D, ARM_HOLE, CHEEK_HOLE = 4.0, 4.6, 4.3
CHEEK_T, Y_GAP = 4.0, 0.4
CHEEK_X, CHEEK_Z = 38.0, (-12.0, 12.0)
BRIDGE_X = 12.0
# arm, post, base
REACH = 170.0                 # post centre to clamp centre (Y)
BEAM_X, BEAM_Z = 12.0, (-12.0, 6.0)
POST = 20.0
SLEEVE_IN, SLEEVE_WALL, SLEEVE_Z = POST + 0.6, 5.0, (-12.0, 24.0)
SLEEVE_HOLES = (0.0, 15.0)    # pin holes in the sleeve, above the pivot level (15 = 5 mod 10: 5 mm steps)
H_PIN_D, POST_HOLE, SLEEVE_HOLE = 5.0, 5.4, 5.6
POST_L, POST_HOLES = 290.0, [float(h) for h in range(250, 290, 10)]   # 290 prints straight on the 300 bed
PLATE, PLATE_T, SOCKET_OUT, SOCKET_H, SOCKET_IN = 170.0, 5.0, 34.0, 40.0, POST + 0.5
BED = 300.0                   # K2 Pro


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def jaw():
    """one jaw arm, clamp frame for the right-hand jaw at psi = 0 (vertical): pivot at the origin"""
    a = box(-ARM_T / 2, ARM_T / 2, -ARM_D / 2, ARM_D / 2, -L_DN, H_UP).edges('|Y').fillet(1.0)
    a = a.cut(cq.Workplane('XZ').circle(ARM_HOLE / 2).extrude(ARM_D, both=True))
    for z in NOTCH_Z:                                        # band grooves on both faces: one part makes both jaws
        for s in (-1, 1):
            a = a.cut(box(s * ARM_T / 2 - 1.5 if s > 0 else -ARM_T / 2 - 0.5, s * ARM_T / 2 + 0.5 if s > 0 else -ARM_T / 2 + 1.5,
                          -ARM_D, ARM_D, z - 1.5, z + 1.5))
    return a


def jaw_at(psi_deg, side):
    """a jaw placed in the clamp frame: side +1 right (pivot +PIV_A), -1 left; psi > 0 tip inward"""
    j = jaw()
    if side < 0:
        j = j.mirror('YZ')
    return j.rotate((0, 0, 0), (0, 1, 0), side * psi_deg).translate((side * PIV_A, 0, 0))


def hanger():
    """clamp head + beam + sleeve, one part, in the clamp frame (the post at y = -REACH)"""
    yc = ARM_D / 2 + Y_GAP
    h = box(-CHEEK_X, CHEEK_X, yc, yc + CHEEK_T, *CHEEK_Z).union(box(-CHEEK_X, CHEEK_X, -yc - CHEEK_T, -yc, *CHEEK_Z))
    h = h.union(box(-BRIDGE_X, BRIDGE_X, -yc, yc, CHEEK_Z[0], 6.0))
    for s in (-1, 1):
        h = h.cut(cq.Workplane('XZ').center(s * PIV_A, 0).circle(CHEEK_HOLE / 2).extrude(40, both=True))
    so = SLEEVE_IN / 2 + SLEEVE_WALL
    h = h.union(box(-BEAM_X / 2, BEAM_X / 2, -REACH + so - 1, -yc - CHEEK_T + 0.5, *BEAM_Z))
    h = h.union(box(-so, so, -REACH - so, -REACH + so, *SLEEVE_Z))
    h = h.cut(box(-SLEEVE_IN / 2, SLEEVE_IN / 2, -REACH - SLEEVE_IN / 2, -REACH + SLEEVE_IN / 2, SLEEVE_Z[0] - 1, SLEEVE_Z[1] + 1))
    for z in SLEEVE_HOLES:
        h = h.cut(cq.Workplane('YZ').center(-REACH, z).circle(SLEEVE_HOLE / 2).extrude(40, both=True))
    return h


def post():
    p = box(-POST / 2, POST / 2, -POST / 2, POST / 2, 0, POST_L).edges('|Z').chamfer(1.0)
    for z in POST_HOLES:
        p = p.cut(cq.Workplane('YZ').center(0, z).circle(POST_HOLE / 2).extrude(30, both=True))
    return p


def base():
    """an open H-frame (a solid plate was most of a 5 h print): a spine under the arm's line, a back crossbar for
    the book, and a front foot against tipping forward, 125 mm short of the drop point"""
    t, w = 6.0, 20.0
    b = box(-w / 2, w / 2, -150.0, 45.0, 0, t)                                  # spine along Y
    b = b.union(box(-PLATE / 2, PLATE / 2, -150.0, -150.0 + 2 * w, 0, t))       # back crossbar (the book goes here)
    b = b.union(box(-60.0, 60.0, 45.0 - w, 45.0, 0, t))                         # front foot
    b = b.union(box(-SOCKET_OUT / 2, SOCKET_OUT / 2, -SOCKET_OUT / 2, SOCKET_OUT / 2, 0, SOCKET_H))
    return b.cut(box(-SOCKET_IN / 2, SOCKET_IN / 2, -SOCKET_IN / 2, SOCKET_IN / 2, -1, SOCKET_H + 1))


def gauge():
    """an F, printed flat (Z is its thickness): foot, a 150 mm upright, and a finger whose top is at DROP"""
    t = 10.0
    g = box(0, 70, 0, 6, 0, t).union(box(0, 10, 0, DROP, 0, t)).union(box(-45, 10, DROP - 6, DROP, 0, t))
    return g


def pins():
    out = []
    for i in range(3):                                       # pivot pins (2 + a spare): head 8 x 2, shank 4 x 21
        shank = 2 * CHEEK_T + ARM_D + 2 * Y_GAP + 0.5
        out.append(cq.Workplane('XY').circle(4.0).extrude(2.0).union(cq.Workplane('XY').circle(PIN_D / 2 - 0.05).extrude(2.0 + shank))
                   .translate((i * 12.0, 0, 0)))
    shank = SLEEVE_IN + 2 * SLEEVE_WALL + 4.0                # height pin: head 10 x 3, shank 5 x 34.6
    out.append(cq.Workplane('XY').circle(5.0).extrude(3.0).union(cq.Workplane('XY').circle(H_PIN_D / 2 - 0.05).extrude(3.0 + shank))
               .translate((40.0, 0, 0)))
    p = out[0]
    for q in out[1:]:
        p = p.union(q)
    return p


# ---------- checks ----------
def vol(a, b):
    try:
        return a.intersect(b).val().Volume()
    except Exception:
        return 0.0


def gap(psi_deg, z):
    """inner-face gap between the jaws at height z (clamp frame) at angle psi"""
    s, c = np.sin(np.radians(psi_deg)), np.cos(np.radians(psi_deg))
    return 2 * (PIV_A - ARM_T / 2 * c + z * s)


def handle_stop(h_up=H_UP):
    """the angle at which the handles' inner faces meet (the jaws' widest opening): longer handles meet sooner"""
    for psi in np.arange(0, -45, -0.1):
        if gap(psi, h_up) <= 0.5:
            return psi
    return None


def starts():
    """per body and start: vertical extent and the narrowest horizontal dimension (the grip)"""
    sys.path.insert(0, HERE)
    import scale_model as S
    from scipy.spatial.transform import Rotation as Rot
    out = {}
    for n in ('E1_tub', 'E2_dome', 'E3_tall'):
        info = json.load(open(os.path.join(ROOT, 'models', n + '.json'))); P = S.hull_points(info['params'], info['scale'])
        for att, (r, p) in S.ATTITUDES.items():
            e = np.ptp(P @ Rot.from_euler('xyz', [r, p, 0], degrees=True).as_matrix().T, 0)
            out[(n, att)] = dict(vertical=float(e[2]), grip=float(min(e[0], e[1])))
    return out


def pivot_heights(holes=None):
    holes = POST_HOLES if holes is None else holes
    return sorted({h - o for h in holes for o in SLEEVE_HOLES})


def settings(st, holes=None):
    """for each start, a pivot height that puts the lowest point at DROP with the grip centre inside the pad zone"""
    res = {}
    for k, v in st.items():
        half = v['vertical'] / 2
        ok = [ph for ph in pivot_heights(holes) if PAD[0] + 5 <= (DROP + half) - ph <= PAD[1] - 5]
        res[k] = min(ok, key=lambda ph: abs((DROP + half) - ph - (PAD[0] + PAD[1]) / 2)) if ok else None
    return res


if __name__ == '__main__':
    out = os.path.join(ROOT, 'models'); os.makedirs(out, exist_ok=True)
    stop = handle_stop()
    print(f'jaws: widest opening at psi {stop:.1f} deg (handles meet): gap {gap(stop, PAD[1]):.1f} mm at the top of the pads, '
          f'{gap(stop, PAD[0]):.1f} at the tips; closed: tips meet at psi {np.degrees(np.arcsin((PIV_A - ARM_T / 2) / L_DN)):.1f} deg')
    st = starts(); widest = max(v['grip'] for v in st.values()); narrowest = min(v['grip'] for v in st.values())
    print(f'grip widths over 3 bodies x 6 starts: {narrowest:.1f} to {widest:.1f} mm')
    ok_open = gap(stop, PAD[1]) >= widest + 8
    print(f'  open check: the widest grip passes the top of the pads with >= 8 mm to spare: {ok_open}  (want True)')
    print(f'  control, handles 90 mm long: {gap(handle_stop(90.0), PAD[1]) >= widest + 8}  (want False)')

    # collisions through the jaws' travel: jaw vs hanger, jaw vs jaw (they may touch only at the handle stop)
    hg = hanger(); bad = []
    for psi in (stop + 1.0, -10.0, 0.0, 5.0, 10.0):
        L, R = jaw_at(psi, -1), jaw_at(psi, 1)
        c = (vol(L, hg), vol(R, hg), vol(L, R))
        if max(c) > 1e-3: bad.append((psi, c))
    print(f'travel {stop + 1:.0f} to +10 deg: overlaps {bad if bad else "none"}  (want none)')
    wide = hg.union(box(-22, 22, -ARM_D / 2 - Y_GAP, ARM_D / 2 + Y_GAP, CHEEK_Z[0], 6.0))
    print(f'  control, bridge widened to +-22 mm: overlap {vol(jaw_at(0.0, 1), wide):.1f} mm3  (want > 0)')
    print(f'  pivot pin {PIN_D} in jaw holes {ARM_HOLE} (turns freely) and cheek holes {CHEEK_HOLE} (snug); '
          f'height pin {H_PIN_D} in post {POST_HOLE} / sleeve {SLEEVE_HOLE}')

    # height: every start must get its lowest point to 150 mm with the grip on the pads
    S1 = settings(st)
    miss = [k for k, v in S1.items() if v is None]
    print(f'heights: {len(S1) - len(miss)} of {len(S1)} starts can be set  (want all)  pivot heights {pivot_heights()[0]:.0f}-{pivot_heights()[-1]:.0f} mm in 5s')
    S2 = settings(st, holes=[250.0])
    print(f'  control, one post hole at 250 only: {sum(v is None for v in S2.values())} starts cannot be set  (want > 0)')

    j = jaw().rotate((0, 0, 0), (1, 0, 0), 90)
    parts = {'base': base(), 'post': post().rotate((0, 0, 0), (0, 1, 0), 90),
             'arm': hanger(), 'jaws': j.union(j.translate((14, 0, 0))), 'gauge': gauge(), 'pins': pins()}
    for n, s in parts.items():
        bb = s.val().BoundingBox()
        fits = bb.xlen <= BED - 10 and bb.ylen <= BED - 10 and bb.zlen <= BED
        p = os.path.join(out, f'drop_stand_{n}.stl'); cq.exporters.export(s, p, tolerance=0.02, angularTolerance=0.15)
        print(f'{n:6s} {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:5.1f} mm  fits the bed: {fits}  -> {os.path.relpath(p, ROOT)}')

    # the setup card: which post hole and which sleeve hole for each start
    rows = []
    for (n, att), ph in sorted(S1.items()):
        if ph is None: continue
        h = next((h, o) for h in POST_HOLES for o in SLEEVE_HOLES if abs(h - o - ph) < 1e-6)
        grip_c = DROP + st[(n, att)]['vertical'] / 2 - ph
        rows.append(dict(body=n, start=att, post_hole_mm=h[0], sleeve_hole='lower' if h[1] == 0 else 'upper', grip_centre_below_pivot=round(-grip_c)))
    json.dump(dict(drop_mm=DROP, settings=rows), open(os.path.join(out, 'drop_stand_settings.json'), 'w'), indent=1)
    for r in rows:
        print(f"  {r['body']:8s} {r['start']:28s} post hole {r['post_hole_mm']:.0f} mm, sleeve {r['sleeve_hole']}")
