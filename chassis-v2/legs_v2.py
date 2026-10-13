"""v2 legs (brainstorm, 2026-10-05): longer ground contact, a wider printed TPU track, sprung road wheels, a
flipper-ready front axle, and a geared motor driving each rear sprocket directly. Not printed; sizes of parts not
yet bought are datasheet guesses (marked *).

    python chassis-v2/legs_v2.py       # side view sketch -> out/legs_v2_side.png, numbers -> out/legs_v2.json

Zach (2026-10-05): goals longer contact, wider track, suspension, flipper-ready; a new printed TPU track; open to
new motors; design first, then he buys (shopping list in SHOP).

Layout (hull frame, mm; Y offsets are from the centre line YC):
- Ground at G0 = -26: the body sits 7 higher than on the v1 legs.
- Rear drive sprocket, 11 teeth on a 14 mm pitch, at the motor's axis (X -104, Z 30). The motor (37 mm gearbox*)
  lies across the hull, its gearbox in a hole through the hull wall and the leg's frame, its shaft out to the
  sprocket. Z 30 is the only height where the motor clears the floor and the track's top run clears the fender.
- Five road wheels per side on trailing arms with TPU springs; the flat contact runs X -89..115 (204 mm; v1: 77).
- Front idler raised (approach), on a hollow 20 mm boss: the idler turns on a 6704 (you have these), and a
  flipper can later turn on a second 6704 at the boss's outer end, driven by a shaft through the boss.
- Track: a TPU band 52 wide, 3 thick, chevron grousers outside; centre horns inside do both jobs, guide (the
  wheels are split round them) and drive (the sprocket's teeth sit between them). Printed as one ring.
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tail_arms as TA
from tail_arms import C, cq, cq_tris, cyl_tris, YC, OUT
wp = lambda: cq.Workplane('XY')

G0 = -26.0                                   # ground
PITCH, TEETH = 14.0, 11                      # track pitch; sprocket teeth
R_SP = PITCH / (2 * np.sin(np.pi / TEETH))   # 24.85: sprocket pitch radius
BAND, GROUSER, HORN = 3.0, 3.0, 6.0          # band thickness, grouser height outside, horn height inside
TW = 52.0                                    # track width
Y_FRAME = (66.4, 70.4)                       # leg frame plate (offsets from YC): against the hull wall (65.75)
Y_TRACK = (73.5, 73.5 + TW)                  # 73.5..125.5
Y_MID = (Y_TRACK[0] + Y_TRACK[1]) / 2        # 99.5: horns, sprocket
GAP = 12.0                                   # horn gap between the wheel halves
SPROCKET = (-104.0, 30.0)                    # X, Z (motor axis)
R_W = 17.0                                   # road wheel radius
Z_W = G0 + BAND + GROUSER + R_W              # road wheel centre at static load: -3
X_W = [-72.0, -29.5, 13.0, 55.5, 98.0]
IDLER_R = 24.0
IDLER = [130.0, 36.0]                        # X is set by the link count (tension); Z raised for approach
ROLLERS = [(-35.0, 47.0, 8.0), (55.0, 48.5, 8.0)]    # return rollers under the top run
TRAVEL = (12.0, 5.0)                         # wheel travel up, down from static
ARM_L = 28.0                                 # trailing arm: pivot this far ahead of the wheel axle, ARM_UP up
ARM_UP = 6.0
MOTOR = dict(gb_d=37.0, gb_l=22.0, m_d=34.5, m_l=33.0, enc_l=11.0, shaft_d=6.0, shaft_l=15.5, face_holes=6, mass=205.0)  # 37D-class*
HUB_R, BOSS_R = 9.0, 10.0                    # sprocket hub; idler boss (6704 bore 20)
TOWER = 80.0                                 # the frame's bearing tower reaches out to here: the sprocket's hub tube turns in it

def circles(idler_x=None):
    ix = IDLER[0] if idler_x is None else idler_x
    return [(SPROCKET[0], SPROCKET[1], R_SP - BAND / 2), (ix, IDLER[1], IDLER_R)] + [(x, Z_W, R_W) for x in X_W] + list(ROLLERS)

def loop_length(circ, r_add=BAND / 2):
    """length of the band's centre line wrapped round the circles (convex hull of the grown circles)"""
    from scipy.spatial import ConvexHull
    th = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    P = np.vstack([np.c_[x + (r + r_add) * np.cos(th), z + (r + r_add) * np.sin(th)] for x, z, r in circ])
    H = P[ConvexHull(P).vertices]; return float(np.sum(np.linalg.norm(np.diff(np.vstack([H, H[:1]]), axis=0), axis=1)))

def tension():
    """slide the idler (its slot is the tensioner) so the loop is a whole number of links"""
    L0 = loop_length(circles()); n = int(round(L0 / PITCH))
    lo, hi = IDLER[0] - 15, IDLER[0] + 15
    for _ in range(40):
        m = (lo + hi) / 2
        if loop_length(circles(m)) < n * PITCH: lo = m
        else: hi = m
    IDLER[0] = round((lo + hi) / 2, 2); return n

def flat_contact():
    return X_W[0] - R_W * 0.6, X_W[-1] + R_W * 0.6

# ---------------------------------------------------------------- parts, one side; mirrored for the other
def yy(sg, off): return YC + sg * off
def disc(x, z, r, y0, y1):
    return cq.Workplane('XZ').circle(r).extrude(-(y1 - y0)).translate((x, min(y0, y1), z)).val()

def sprocket(sg):
    pts = []
    for i in range(TEETH * 2):
        a = np.pi * i / TEETH; rr = R_SP + 3.2 if i % 2 == 0 else R_SP - 3.5
        pts.append((rr * np.cos(a), rr * np.sin(a)))
    w = GAP - 3.0
    s = cq.Workplane('XZ').polyline(pts).close().extrude(-w).translate((SPROCKET[0], yy(sg, Y_MID) - w / 2, SPROCKET[1]))
    for yo in (Y_MID - GAP / 2 - 9, Y_MID + GAP / 2):                    # flanges each side of the teeth: guide the horns
        s = s.union(cq.Workplane('XZ').circle(R_SP - 4).extrude(-9).translate((SPROCKET[0], yy(sg, yo) if sg > 0 else yy(sg, yo + 9), SPROCKET[1])))
    s = s.union(cq.Workplane('XZ').circle(HUB_R).extrude(-(Y_MID - TOWER)).translate((SPROCKET[0], yy(sg, TOWER) if sg > 0 else yy(sg, Y_MID), SPROCKET[1])))   # hub tube from the tower
    return s.val()

def wheel_pair(x, z, r, sg):
    a = (Y_TRACK[0] + 1, Y_MID - GAP / 2); b = (Y_MID + GAP / 2, Y_TRACK[1] - 1)
    out = []
    for y0, y1 in (a, b):
        w = cq.Workplane('XZ').circle(r).circle(r * 0.45).extrude(-(y1 - y0)).translate((x, min(yy(sg, y0), yy(sg, y1)), z))
        w = w.union(cq.Workplane('XZ').circle(r * 0.5).circle(2.6).extrude(-(y1 - y0)).translate((x, min(yy(sg, y0), yy(sg, y1)), z)))
        out.append(w.val())
    return out

def frame_profile():
    """the leg's plate, side view: round the arm pivots, the idler boss, the sprocket and the mounting strip"""
    from scipy.spatial import ConvexHull
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    pts = [np.c_[SPROCKET[0] + 24 * np.cos(th), SPROCKET[1] + 24 * np.sin(th)], np.c_[IDLER[0] + 16 * np.cos(th), IDLER[1] + 16 * np.sin(th)]]
    for x in X_W: pts.append(np.c_[x + ARM_L + 9 * np.cos(th), Z_W + ARM_UP + 9 * np.sin(th)])
    pts.append(np.array([[-100, 52], [125, 52]]))
    P = np.vstack(pts); return P[ConvexHull(P).vertices]

def frame(sg):
    prof = [tuple(p) for p in frame_profile()]
    f = cq.Workplane('XZ').polyline(prof).close().extrude(-(Y_FRAME[1] - Y_FRAME[0])).translate((0, yy(sg, Y_FRAME[0]) if sg > 0 else yy(sg, Y_FRAME[1]), 0))
    ym = (Y_FRAME[0] + Y_FRAME[1]) / 2
    tower = cq.Workplane('XZ').circle(13).extrude(-(TOWER - Y_FRAME[1])).translate((SPROCKET[0], yy(sg, Y_FRAME[1]) if sg > 0 else yy(sg, TOWER), SPROCKET[1]))
    f = f.union(tower)                                                  # bearing tower: a 6800 round the sprocket's hub tube
    f = f.cut(cq.Workplane('XZ').circle(MOTOR['gb_d'] / 2 + 0.5).extrude(20, both=True).translate((SPROCKET[0], yy(sg, ym), SPROCKET[1])))  # the gearbox passes through
    f = f.cut(cq.Workplane('XZ').circle(9.5).extrude(40, both=True).translate((SPROCKET[0], yy(sg, TOWER), SPROCKET[1])))
    for x0, x1 in ((-70, -40), (-20, 10), (30, 60), (80, 105)):         # lightening windows over the arms
        f = f.cut(wp().box(x1 - x0, 10, 18).edges('|Y').fillet(6).translate(((x0 + x1) / 2, yy(sg, ym), 34)))
    return f.val()

def arm(x, sg):
    p = np.array([x + ARM_L, Z_W + ARM_UP]); w = np.array([x, Z_W])
    d = w - p; L = np.hypot(*d); ang = np.degrees(np.arctan2(d[1], d[0])); c = (p + w) / 2
    y0 = Y_FRAME[1] + 0.3; y1 = Y_TRACK[0] + 0.7
    a = wp().box(L, y1 - y0, 10).edges('|Y').fillet(4.9).rotate((0, 0, 0), (0, 1, 0), -ang).translate((c[0], yy(sg, (y0 + y1) / 2), c[1]))
    for q, r in ((p, 7.0), (w, 6.0)):
        a = a.union(cq.Workplane('XZ').circle(r).extrude(-(y1 - y0)).translate((q[0], min(yy(sg, y0), yy(sg, y1)), q[1])))
    spring = wp().box(10, y1 - y0, 9).edges('|Y').fillet(2).translate((p[0] - 12, yy(sg, (y0 + y1) / 2), p[1] + 9))   # TPU spring pad, between frame and wheel
    return a.val(), spring.val()

def idler_boss(sg):
    """the hollow 20 mm boss across the track: the idler turns on it; a flipper hub will at its outer end"""
    y0, y1 = Y_FRAME[1], Y_TRACK[1] + 12
    b = cq.Workplane('XZ').circle(BOSS_R).circle(4.5).extrude(-(y1 - y0)).translate((IDLER[0], min(yy(sg, y0), yy(sg, y1)), IDLER[1]))
    return b.val()

def flipper_hub_ghost(sg):
    y0, y1 = Y_TRACK[1] + 2, Y_TRACK[1] + 12
    return cq.Workplane('XZ').circle(13.5).circle(BOSS_R).extrude(-(y1 - y0)).translate((IDLER[0], min(yy(sg, y0), yy(sg, y1)), IDLER[1])).val()

def motor(sg):
    """37 mm gearmotor* across the hull: gearbox face flush with the frame's outer face, body inboard"""
    face = Y_FRAME[1]; g = MOTOR
    segs = [(face - g['gb_l'], face, g['gb_d'] / 2), (face - g['gb_l'] - g['m_l'], face - g['gb_l'], g['m_d'] / 2),
            (face - g['gb_l'] - g['m_l'] - g['enc_l'], face - g['gb_l'] - g['m_l'], g['m_d'] / 2 - 2)]
    tris = [cyl_tris((SPROCKET[0], yy(sg, a), SPROCKET[1]), (SPROCKET[0], yy(sg, b), SPROCKET[1]), r, 40) for a, b, r in segs]
    tris.append(cyl_tris((SPROCKET[0], yy(sg, face), SPROCKET[1]), (SPROCKET[0], yy(sg, face + g['shaft_l']), SPROCKET[1]), g['shaft_d'] / 2, 16))
    return np.vstack(tris)

def outer_bracket(sg):
    """an arm from the frame's top, round the track's top run, holding the sprocket shaft's outer bearing*"""
    y_out = Y_TRACK[1] + 6
    top = wp().box(30, y_out - Y_FRAME[1] + 4, 4).translate((SPROCKET[0] + 8, yy(sg, (Y_FRAME[1] + y_out) / 2), 62))
    leg = cq.Workplane('XZ').polyline([(SPROCKET[0] - 12, 64), (SPROCKET[0] + 24, 64), (SPROCKET[0] + 14, SPROCKET[1]), (SPROCKET[0] - 12, SPROCKET[1] - 6)]).close() \
        .extrude(-4).translate((0, yy(sg, y_out) if sg > 0 else yy(sg, y_out + 4), 0))
    boss = cq.Workplane('XZ').circle(10).circle(3.1).extrude(-6).translate((SPROCKET[0], yy(sg, y_out - 2) if sg > 0 else yy(sg, y_out + 4), SPROCKET[1]))
    return top.union(leg).union(boss).val()

def track(sg):
    circ = circles()
    y0, y1 = sorted((yy(sg, Y_TRACK[0]), yy(sg, Y_TRACK[1])))
    band = C.track_loop([(x, z, r) for x, z, r in circ], y0, y1, t=BAND, lug=GROUSER, pitch=PITCH, lug_len=6.0)
    return band

def side(sg):
    k = 'L' if sg > 0 else 'R'; P = {}
    P['frame_' + k] = (frame(sg), 'Leg frame (new): the plate that bolts to the hull', (0.20, 0.22, 0.24))
    P['sprocket_' + k] = (sprocket(sg), 'Drive sprocket: 11 teeth, 14 pitch, between the horns', (0.91, 0.64, 0.23))
    ws, arms, springs = [], [], []
    for x in X_W:
        ws += wheel_pair(x, Z_W, R_W, sg); a, s = arm(x, sg); arms.append(a); springs.append(s)
    P['wheels_' + k] = (ws, 'Road wheels: 5 pairs, split round the horns', (0.91, 0.64, 0.23))
    P['arms_' + k] = (arms, 'Trailing arms: pivot ahead of each wheel, %d up / %d down' % TRAVEL, (0.34, 0.37, 0.40))
    P['springs_' + k] = (springs, 'TPU spring pads (printed)', (0.86, 0.56, 0.16))
    P['idler_' + k] = (wheel_pair(IDLER[0], IDLER[1], IDLER_R, sg), 'Front idler: raised, on a 6704 round the boss', (0.91, 0.64, 0.23))
    P['rollers_' + k] = ([w for x, z, r in ROLLERS for w in wheel_pair(x, z, r, sg)], 'Return rollers', (0.91, 0.64, 0.23))
    P['boss_' + k] = (idler_boss(sg), 'Idler boss, hollow 20 mm: a flipper can turn on its outer end later', (0.55, 0.58, 0.62))
    return P

def meshes():
    """the legs as rugged.py meshes: {key: dict(t, label, grp, rgb, note)}"""
    n = tension(); M = {}
    for sg in (1, -1):
        k = 'L' if sg > 0 else 'R'
        for key, (sh, lab, rgb) in side(sg).items():
            shs = sh if isinstance(sh, list) else [sh]
            M[key] = dict(t=np.vstack([np.asarray(cq_tris(s), float).reshape(-1, 3, 3) for s in shs]), label=lab, grp='legs', rgb=rgb, note='v2 legs (new).')
        M['track_' + k] = dict(t=np.asarray(track(sg), float).reshape(-1, 3, 3), label='TPU track (new): %d links of %g, %g wide' % (n, PITCH, TW), grp='legs', rgb=(0.11, 0.12, 0.12), note='Printed as one ring.')
        M['motor_' + k] = dict(t=motor(sg), label='Gearmotor* (37 mm gearbox, 30:1 class)', grp='legs', rgb=(0.55, 0.58, 0.62), note='Across the hull; its gearbox through the hull wall.')
        M['flipper_hub_' + k] = dict(t=np.asarray(cq_tris(flipper_hub_ghost(sg)), float).reshape(-1, 3, 3), label='Later: flipper hub (6704)', grp='reserved', rgb=(0.5, 0.7, 0.85), note='', ghost=True)
    return M, n

# ---------------------------------------------------------------- numbers
SHOP = [  # (item, qty, note)
    ('37 mm metal gearmotor, ~30:1, 6 mm D shaft, with encoder (e.g. Pololu 37D 30:1 12 V, or a JGB37-520 at ~330 rpm)', 2,
     'Buy one first and caliper it: the mount is sized to a datasheet*.'),
    ('Mounting hub for a 6 mm D shaft (M3 holes)', 2, 'Sprocket bolts to it.'),
    ('625ZZ bearings (5 x 16 x 5)', 28, 'One per wheel half: road wheels 20, return rollers 8.'),
    ('6704 bearings (20 x 27 x 4)', 2, 'Idlers: you have 10 (some in the head). Two more per side later for flippers.'),
    ('6800ZZ bearings (10 x 19 x 5)', 2, 'The sprocket hub tube, in the frame bearing tower: the track pull goes to the frame, not the gearbox.'),
    ('M5 x 70 bolts + nylock nuts', 14, 'Road wheel and roller axles across the track.'),
    ('M4 x 20 shoulder bolts (or M4 bolts + printed bushings)', 10, 'Arm pivots.'),
    ('M3 heat-set inserts + M3 x 10 button screws', 24, 'Frame to hull (8 per side) and brackets.'),
    ('TPU 95A filament, ~0.5 kg', 1, 'Two tracks (~%d g each*) and the spring pads.'),
]

def numbers(M, n):
    x0, x1 = flat_contact()
    tr = M['track_L']['t'].reshape(-1, 3)
    t = M['track_L']['t']; vol = abs(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)
    return dict(links=n, loop=n * PITCH, contact=[x0, x1], contact_len=x1 - x0, width=TW, idler=list(IDLER), ground=G0,
                speed_200rpm=2 * np.pi * R_SP * 200 / 60 / 1000, track_g=float(vol * 1.21e-3), length=float(np.ptp(tr[:, 0])),
                half_width=float(Y_TRACK[1]), sprocket=list(SPROCKET), r_sp=R_SP)

def sketch(M, n, path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 4.6))
    for k, col in (('track_L', '#222'), ('frame_L', '#9aa'), ('wheels_L', '#d9a441'), ('idler_L', '#d9a441'), ('sprocket_L', '#c77d1e'),
                   ('arms_L', '#667'), ('motor_L', '#888'), ('rollers_L', '#d9a441')):
        t = M[k]['t']; ax.add_collection(__import__('matplotlib.collections', fromlist=['PolyCollection']).PolyCollection(t[:, :, [0, 2]], facecolor=col, edgecolor='none', alpha=0.35 if k == 'frame_L' else 0.8))
    ax.axhline(G0, color='#444', lw=1); x0, x1 = flat_contact(); ax.plot([x0, x1], [G0 - 2, G0 - 2], color='#2F7A5A', lw=4)
    ax.text((x0 + x1) / 2, G0 - 10, 'flat contact %d mm (v1: 77)' % (x1 - x0), ha='center', fontsize=9, color='#2F7A5A')
    ax.set_xlim(-150, 175); ax.set_ylim(G0 - 16, 80); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.set_title('v2 leg, left, from outside: %d links of %g mm, %g wide' % (n, PITCH, TW), fontsize=10, loc='left')
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig); print('wrote', path)

if __name__ == '__main__':
    M, n = meshes(); N = numbers(M, n); print(json.dumps(N, indent=1, default=float))
    json.dump(N, open(os.path.join(OUT, 'legs_v2.json'), 'w'), indent=1, default=float)
    sketch(M, n, os.path.join(OUT, 'legs_v2_side.png'))
