"""Wheels for training (brainstorm, 2026-10-05): four identical corner modules in place of the v2 tracks. Zach: "the
side portions covering the top of the tracks have to go ... we have to use wheels, tracks get too complicated and we
need to be able to run en masse to train." Not printed; sizes of parts not yet bought are datasheet guesses (*).

    python chassis-v2/trainer.py       # the body on these wheels -> out/trainer.html (this file is the geometry)

A corner module (hull frame, mm; Y as offsets from the centre line YC, outward positive):
- Pod: a printed tube round the gearmotor, its flange on a pad on the hull wall (4 M3 into inserts), a lip at its
  outer end that the gearbox face screws to. Nothing of the drive is inside the hull: the nose holds the head and the
  packs, so a front motor can't lie across it the way the v2 rear motors lay across the tail.
- Gearmotor*: the v2 legs' 37 mm 30:1-class motor with encoder, axle along Y, shaft outward.
- Wheel: a dish (rim + outer disc) that wraps back over the pod, on the motor's D shaft (printed hub, M3 set screw),
  with a printed TPU tyre, chevron lugs. 110 across, 46 wide.
- Axles at Z 30 (the v2 sprocket's height), front X 91 and rear X -93 (world): the ends of the hull wall's straight run.
- Rigid: no suspension. In a simulator the whole drive is one body, four hinge joints and four tyre contacts.

Six wheels (2026-10-09, Zach: "a version of the trainer with 6 wheels"): `SCORPION_WHEELS=6`. The same module, six times,
three a side. Three Ø110 wheels don't fit the wall's straight run (232 long), so the wheels are Ø100 and the wheelbase
grows 184 -> 216: the middle axle under the centre of mass (X 10), the front axle past the wall's end, its pad filled
back to the slanted nose wall (a cheek, part of the tub). Axles at Z 25 keep the ground, so the body rides as high.

Step layout (2026-10-25, Zach: "turn the best-under-380 mm layout into a chassis-v2 change"): `SCORPION_WHEELS=step`.
research/tumble/chassis3.py's best layout for driving down steps at the Trainer's length: Ø92 wheels on axles at X 53
and -77 (wheelbase 130), the belly 54 over the ground (was 32). The gain is the short wheelbase with the raised belly
together (research/results/chassis3/sensitivity.json: the belly alone, 0.505; the Trainer's Ø110 wheels on these axles
did as well as Ø92, 0.652, so `SCORPION_STEP_R=55` builds that). The axle now sits under the tub's floor, so each pod's
flange is a drop plate: 5 thick, up the wall to the tub's top, screwed to inserts in a full-height wall pad above the
floor. The packs stay put: the search moved them 28 forward, but they already reach the nose wall (2 mm short).
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tail_arms as TA
from tail_arms import C, cq, cq_tris, cyl_tris, YC, OUT
wp = lambda: cq.Workplane('XY')

SIX = os.environ.get('SCORPION_WHEELS', '4') == '6'
STEP = os.environ.get('SCORPION_WHEELS', '4') == 'step'
FLOOR0, TUB_TOP = 7.4, 57.4                  # hull.py's: the tub's underside and top
if SIX:
    R_T, Z_A = 50.0, 25.0                    # Ø100; the axle 5 lower, so the ground stays at -25
    XM, PITCH = 10.0, 108.0                  # middle axle under the centre of mass (4 wheels: X 10.7); 8 between tyres
    AXLES = {'F': XM + PITCH, 'M': XM, 'R': XM - PITCH}
elif STEP:
    R_T = float(os.environ.get('SCORPION_STEP_R', '46'))   # Ø92 (the search's); 55: the Trainer's wheels, same score
    BELLY = 54.0                             # the tub's underside over the ground
    Z_A = FLOOR0 - BELLY + R_T               # -0.6 for Ø92: 8 under the tub's floor
    AXLES = {'F': 53.0, 'R': -77.0}          # wheelbase 130, both on the wall's straight run
else:
    R_T = 55.0                               # tyre radius over the lugs
    Z_A = 30.0                               # axle height
    AXLES = {'F': 91.0, 'R': -93.0}          # world X: the hull wall's straight run is X -117..115
G0 = Z_A - R_T                               # -25: ground (the v2 legs' was -26)
WALL_Y = 65.75                               # hull wall's outer face
PAD = 4.0                                    # insert pad on the wall (part of the tub)
CHEEK = 12.0 if SIX else 0.0                 # the pad also fills this far in behind its face, where the wall curves away
PAD_Z0 = Z_A - 23.0 if SIX else None         # pad's bottom (None: the tub's floor); six: down to the flange, 5 under the tub
PAD_Z1 = TUB_TOP if STEP else None           # pad's top (None: the flange's top); step: the wall's full height
HOLE_Z = (22.0, 47.0) if STEP else (Z_A - 17.0, Z_A + 17.0)          # the pad's two rows of inserts (X +-17)
LEAD_X = {c: min(max(x, -110.0), 105.0) for c, x in AXLES.items()}   # where each motor's leads enter: on the straight wall
GAP = 0.2                                    # between mating faces: touching, not one solid
FLANGE = 5.0 if STEP else 4.0              # step: the drop plate
POD_R, POD_IR = 22.0, 19.0                   # pod tube: OD 44, ID 38 round the 37 gearbox
LIP = 2.5
HALF = 23.0                                  # pad and flange: 46 x 46
MOTOR = dict(gb_d=37.0, gb_l=22.0, m_d=34.5, m_l=33.0, enc_d=30.5, enc_l=11.0, shaft_d=6.0, shaft_l=15.5, mass=205.0)  # 37D-class*
Y_FL0 = WALL_Y + PAD + GAP                   # 69.95: flange's inner face
Y_MOT0 = Y_FL0 + 1.0                         # encoder end
Y_FACE = Y_MOT0 + MOTOR['enc_l'] + MOTOR['m_l'] + MOTOR['gb_l']   # 136.95: gearbox face
Y_SHAFT = Y_FACE + MOTOR['shaft_l']          # 152.45
TW = 46.0                                    # tyre width
Y_OUT = Y_SHAFT + 1.55                       # 154: the wheel's outer face, just past the shaft's end
Y_IN = Y_OUT - TW                            # 108
DISC = 5.0
RIM_R0, RIM_R1 = R_T - 11.5, R_T - 8.0       # dish: 43.5..47, 21 mm round the pod tube (six: 38.5..42, 16 round it)
BAND_R1 = R_T - 3.5                          # tyre band; lugs from here to R_T
LUGS = 18

# ---------------------------------------------------------------- one corner, in its own frame: axle on the local Y
# axis, local Y = distance out from the centre line, local X/Z about the axle
def ycyl(r0, r1, y0, y1):
    s = cq.Workplane('XZ').circle(r1)
    if r0 > 0: s = s.circle(r0)
    return s.extrude(-(y1 - y0)).translate((0, y0, 0))

def pod():
    z0, z1 = -HALF, (PAD_Z1 - Z_A if PAD_Z1 is not None else HALF)    # the flange; step: a drop plate up to the pad's top
    f = wp().box(2 * HALF, FLANGE, z1 - z0).edges('|Y').fillet(6).translate((0, Y_FL0 + FLANGE / 2, (z0 + z1) / 2))
    f = f.cut(ycyl(0, POD_IR + 0.5, Y_FL0 - 1, Y_FL0 + FLANGE + 1))
    for x in (-17, 17):
        for z in HOLE_Z:
            f = f.cut(cq.Workplane('XZ').circle(1.7).extrude(-(FLANGE + 2)).translate((x, Y_FL0 - 1, z - Z_A)))
    t = ycyl(POD_IR, POD_R, Y_FL0, Y_FACE)
    lip = ycyl(6.5, POD_R, Y_FACE, Y_FACE + LIP)
    for i in range(6):                                                  # the gearbox face's 6 M3 holes, on a 31 circle*
        a = np.radians(30 + 60 * i)
        lip = lip.cut(cq.Workplane('XZ').circle(1.6).extrude(-(LIP + 2)).translate((15.5 * np.cos(a), Y_FACE - 1, 15.5 * np.sin(a))))
    p = f.union(t).union(lip)
    p = p.cut(wp().box(10, 10, 8).translate((0, Y_FL0 + FLANGE + 5, POD_R - 1.5)))   # cable slot at the top, by the flange
    return p.val()

def motor():
    g = MOTOR; y = Y_MOT0; segs = []
    for d, l in ((g['enc_d'], g['enc_l']), (g['m_d'], g['m_l']), (g['gb_d'], g['gb_l']), (g['shaft_d'], g['shaft_l'])):
        segs.append(cyl_tris((0, y, 0), (0, y + l, 0), d / 2, 40)); y += l
    return np.vstack(segs)

def wheel():
    """rim + outer disc + hub boss: one print"""
    w = ycyl(RIM_R0, RIM_R1, Y_IN, Y_OUT)
    w = w.union(ycyl(9.0, RIM_R1, Y_OUT - DISC, Y_OUT))
    w = w.union(ycyl(3.1, 9.0, Y_FACE + LIP + 2.0, Y_OUT))             # hub boss: 6 mm D bore (drawn 6.2), 2 off the pod's lip
    for i in range(6):                                                  # lightening holes in the disc
        a = np.radians(60 * i)
        w = w.cut(cq.Workplane('XZ').circle(7.5).extrude(-(DISC + 2)).translate((28 * np.cos(a), Y_OUT - DISC - 1, 28 * np.sin(a))))
    return w.val()

def tyre():
    """TPU band and chevron lugs; one lug centred straight down, so every tyre stands on a lug tip at G0"""
    t = ycyl(RIM_R1, BAND_R1, Y_IN, Y_OUT)
    h = R_T - BAND_R1 + 0.4; ym = (Y_IN + Y_OUT) / 2; hl = TW / 2 - 2.0
    for i in range(LUGS):
        a = -90.0 + 360.0 * i / LUGS
        for sg in (1, -1):                                              # two halves of a chevron, pointing forward
            l = wp().box(5.0, hl, h).rotate((0, 0, 0), (0, 0, 1), sg * 25).translate((0, ym + sg * hl / 2, -(BAND_R1 - 0.4 + h / 2)))
            t = t.union(l.rotate((0, 0, 0), (0, 1, 0), -(a + 90.0)))
    return t.val()

def place(tris, x, side):
    """local corner frame -> world: side +1 left (Y up), -1 right (mirrored)"""
    t = np.asarray(tris, float).reshape(-1, 3, 3).copy()
    t[:, :, 1] = YC + side * t[:, :, 1]; t[:, :, 0] += x; t[:, :, 2] += Z_A
    return t

PARTS = {  # key prefix: (builder, label, grp, rgb, note)
    'pod_': (pod, 'Motor pod (printed)' + (': drop plate' if STEP else ''), 'legs', (0.30, 0.33, 0.36),
             ('A tube round the gearmotor on a 5 mm drop plate that runs up the hull wall to the tub\'s top: 4 M3 into the pad\'s inserts, above the floor. The axle hangs %.0f under the floor; ' % (FLOOR0 - Z_A) if STEP else
              'A tube round the gearmotor; its flange on the hull wall\'s pad (4 M3 into inserts), ') + 'its lip screwed to the gearbox face (6 M3). Identical at all four corners.'),
    'motor_': (motor, 'Gearmotor* (37 mm gearbox, 30:1 class, encoder)', 'legs', (0.55, 0.58, 0.62), 'One per wheel. Its leads leave by the slot at the pod\'s top and go into the hull over the pack.'),
    'rim_': (wheel, 'Wheel (printed): dish, disc and hub', 'legs', (0.91, 0.64, 0.23), 'Wraps back over the pod: %.0f mm round it, so stones fall out. D bore on the 6 mm shaft, M3 set screw.' % (RIM_R0 - POD_R)),
    'tire_': (tyre, 'Tyre (TPU, printed): %.0f x %.0f, chevron lugs' % (2 * R_T, TW), 'legs', (0.11, 0.12, 0.12), 'A stretch fit over the rim. Same part at all four corners.'),
}
def meshes():
    """the four corners as rugged.py meshes: {key: dict(t, label, grp, rgb, note)}"""
    M = {}; local = {}
    for pre, (fn, lab, grp, rgb, note) in PARTS.items():
        t = fn(); local[pre] = np.asarray(t if isinstance(t, np.ndarray) else cq_tris(t), float).reshape(-1, 3, 3)
    for c, x in AXLES.items():
        for side, s in (('L', 1), ('R', -1)):
            for pre, (fn, lab, grp, rgb, note) in PARTS.items():
                M[pre + c + side] = dict(t=place(local[pre], x, s), label=lab, grp=grp, rgb=rgb, note=note)
    return M

# ---------------------------------------------------------------- numbers
N_W = 2 * len(AXLES)                         # wheels (and motors)
_NUM = {4: 'Four', 6: 'Six'}[N_W]
SHOP = [  # (item, qty, note)
    ('37 mm metal gearmotor, ~30:1, 6 mm D shaft, with encoder (e.g. Pololu 37D 30:1, or a JGB37-520 at ~330 rpm)', N_W,
     'Same motor as the v2 legs, now one per wheel. Buy one first and caliper it: the pod is sized to a datasheet*.'),
    ('TPU 95A filament, ~%.1f kg' % (0.1 * N_W), 1, _NUM + ' tyres (~%d g each*).'),
    ('M3 heat-set inserts', 4 * N_W, 'In the wall pads, four per pod.'),
    ('M3 x 10 button screws', 4 * N_W, 'Pod flange to the pad (you have these).'),
    ('M3 x 8 button screws (check the gearbox face holes\' depth)', 6 * N_W, 'Gearbox face to the pod\'s lip, six per motor (you have these).'),
    ('M3 x 5 set screws', N_W, 'Wheel hub onto the shaft\'s flat.'),
    ('Rubber grommets, 8 mm', N_W, 'Where each motor\'s leads enter the hull.'),
]

def numbers(M):
    t = M['tire_FL']['t']; vol = abs(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)
    return dict(axles=AXLES, wheelbase=AXLES['F'] - AXLES['R'], gauge=2 * (Y_IN + Y_OUT) / 2, width=2 * Y_OUT, r=R_T, tw=TW,
                ground=G0, z_a=Z_A, tire_g=float(vol * 1.21e-3 * 0.8), speed_200rpm=2 * np.pi * R_T * 200 / 60 / 1000)

def sketch(M, path, body=None, before=None, circles=(), title=None):
    """one side from outside: wheels, pods, the body's outline, the v2 track (triangles) or older wheels (circles
    (x, z, r)) ghosted behind"""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig, ax = plt.subplots(figsize=(12, 4.8))
    if before is not None:
        ax.add_collection(PolyCollection(before[:, :, [0, 2]], facecolor='#9AA3AE', edgecolor='none', alpha=0.25))
    for x, z, r in circles:
        ax.add_patch(plt.Circle((x, z), r, facecolor='none', edgecolor='#2F6FB0', lw=1.6, ls='--', zorder=5))
    if body is not None:
        ax.add_collection(PolyCollection(body[:, :, [0, 2]], facecolor='#6B7A69', edgecolor='none', alpha=0.35))
    for k, col in (('pod_', '#4D5459'), ('motor_', '#8C9399'), ('rim_', '#D9A441'), ('tire_', '#222')):
        for c in AXLES:
            t = M[k + c + 'L']['t']; ax.add_collection(PolyCollection(t[:, :, [0, 2]], facecolor=col, edgecolor='none', alpha=0.85))
    ax.axhline(G0, color='#444', lw=1)
    for c, x in AXLES.items(): ax.plot([x], [Z_A], '+', color='w', ms=9, mew=2)
    ax.annotate('', xy=(AXLES['R'], G0 - 9), xytext=(AXLES['F'], G0 - 9), arrowprops=dict(arrowstyle='<->', color='#2F7A5A', lw=1.6))
    ax.text(0, G0 - 17, 'wheelbase %d mm' % (AXLES['F'] - AXLES['R']), ha='center', fontsize=9, color='#2F7A5A')
    ax.set_xlim(-175, 215); ax.set_ylim(G0 - 24, 160); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.set_title(title or 'Left side from outside: two corner modules (wheel Ø%d on its pod), the body (green), the v2 track it replaces (grey)' % (2 * R_T), fontsize=10, loc='left')
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig); print('wrote', path)

if __name__ == '__main__':
    M = meshes(); N = numbers(M); print(json.dumps(N, indent=1, default=float))
    for k in ('pod_FL', 'motor_FL', 'rim_FL', 'tire_FL'):
        t = M[k]['t'].reshape(-1, 3); print(k, t.min(0).round(1), t.max(0).round(1))
