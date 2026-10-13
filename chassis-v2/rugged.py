"""Scorpion rugged body (brainstorm, 2026-10-04): the tail-arms body made to survive falls, rolls and knock-overs,
climb steeper, keep dust out and clear taller rocks. Same v1 legs (unmodified), same head v2.

    python chassis-v2/hull.py          # first, if out/_hull_meshes.npz is older than the head meshes
    python chassis-v2/rugged.py        # ~4 min -> out/rugged.html, rugged_*.png, rugged.json, rugged_checks.json

What changes, and the check that measures it:
- Rolls back upright: side skirts and two roll hoops follow one circle round the centre of mass, a little larger than
  the distance to the tracks' bottom edges. On such an outline the distance from the centre of mass only grows from
  the tracks to the top, so the tracks are the only face it can settle on. Checked as the stable rest states of the
  whole robot's convex hull, against the tail-arms body as the control.
- Falls: the first part to touch the ground, over 4000 fall directions. Bumpers (TPU) where it lands; the antenna
  inside the rear hoop; the head never first.
- Climbing: packs stood on edge in bays along the walls, 73 mm forward beside the head; ESCs down from the
  sponsons to the floor; the deck 15 lower; the body 15 forward on the legs. Centre of mass and tip angles against the control.
- Rocks: a raised tunnel down the middle of the belly, the nose floor raised 10 (the head with it).
- Dust: a gasket at every seam, a wiper ring at the turret, boots on the motor windows, grommets, a filtered intake.
Masses are guesses (printed parts at 35 % of solid, packs 300 g); nothing is printed yet.
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tail_arms as TA
from tail_arms import Hm, IR, C, cq, cq_tris, cyl_tris, rbox, T, Rz, YR, YL, YC, OUT, G0
wp = lambda: cq.Workplane('XY')

# ---------------------------------------------------------------- numbers (guesses unless noted)
WALL = Hm.WALL                              # 2.6
FLOOR0 = Hm.FLOOR0                          # 7.4: the bays' floor, as hull.py
TUB_TOP = Hm.TUB_TOP                        # 57.4: the pods' pads are 50 tall (fixed by the legs)
TUB_X0 = -142.0                             # 6 longer than hull.py: room aft for the power parts
RAMP_X = -115.0                             # the belly ramps up 28 deg aft of here (body frame): departure
BODY_DX = 15.0                              # the whole body sits 15 further forward on the legs (the pods' holes move aft in it)
RAISE = 10.0                                # head, turret deck and nose floor up 10: a raised belly under the nose
Z0H = Hm.Z0H + RAISE                        # 59.4: the coil deck
TDECK = Hm.TDECK + RAISE                    # 66.0: turret deck, flush with the well's top
NOSE_Z = FLOOR0 + RAISE                     # 17.4: nose floor underside
TUN_HW, TUN_Z, TUN_ANG = 34.5, 28.0, 60.0   # belly tunnel: half-width at the bays' floor, roof underside, wall angle
TUN_X1 = 42.0                               # the tunnel ends at the head base, where the nose floor takes over
DECK = 72.0                                 # centre deck, 15 lower: no ESCs over it any more
PZ = 104.0                                  # pedestal top: the tail rises 32 deg to it
AX = -112.0                                 # arm yaw axis
PED_R = 33.0
FENDER = Hm.FENDER                          # 62: over the pods (59.4) and the tracks (54.3)
FEND_X0, FEND_X1 = -110.0, 124.0         # world frame: over the tracks
BAY = 26.0 + 0.5                            # a pack on edge is 26 wide
PACK_X0 = -41.0                             # packs X -41..100 (body frame): beside the head base, 73 forward of hull.py's (world)
ESC_X0 = -88.0                              # ESCs X -88..-42, on edge behind the packs
HOOP_XF, HOOP_XR, RAKE = 40.0, -140.0, 0.5  # front hoop (out of the cradle's sweep, X <= 56); rear hoop foot, leaning aft
REAR_HOOP = True
CAGE = True                                 # False: no hoops, brow bar, skirts or rub strips (the guard arm takes the job: guard_arm.py)
BROW = True                                 # a bar from the front hoop's top, forward over the ball
TUBE_R = 6.5                                # hoop tube
BROW_X, BROW_Z = 170.0, 135.0               # body frame: the brow bar's tip, ahead of the ball (top Z 142) and over the claws
BROW_Y = 0.0                                # 0: one bar; else two, their tips this far either side of the centre line
CORNER_CUT = 40.0                           # the fenders' and skirts' front outer corners cut back 45 deg in plan
R_MARGIN, SPIRAL = 2.0, 6.0                # the outline: a spiral round the centre of mass, starting this far past the
                                            # tracks' bottom edges and growing this many mm per radian up to the top
SKIRT_Z0 = 1.0                              # skirt bottom edge (20 over the ground)
SKIRT_BX = -70.0                            # world X: the skirt's bottom edge sweeps up 45 deg aft of here (departure)
TUN_X0 = TUB_X0                             # the tunnel's aft end (body frame)
MOTOR_G = 184.0                             # drive motor mass, g
LEGS = os.environ.get('SCORPION_LEGS', 'v1')  # 'v1': the legs you have; 'v2': legs_v2.py
SFX = '' if LEGS == 'v1' else '_' + LEGS
if LEGS == 'v2':
    import legs_v2 as L2
    G0 = L2.G0; IR.GROUND = G0                # the body rides 7 higher on the v2 legs
    FENDER = 68.0                            # over the v2 track's top run, which climbs to the raised idler
    FEND_X0, FEND_X1 = -135.0, 152.0
    SKIRT_BX = -95.0
    TUN_X0 = -100.0                          # the motors fill the tail's bottom, body X -138..-100
    RAMP_X = None                            # the track itself now reaches the back: no tail ramp
    MOTOR_G = L2.MOTOR['mass']
    BROW_Y = 55.0                            # a forked brow: with one bar, the wider track's front corner made a face-down rest
elif LEGS == 'wheels':                       # trainer.py: four corner modules (wheels.py), no fenders, no cage; the v1 insides
    import wheels as W
    G0 = W.G0; IR.GROUND = G0
    CAGE = False
    MOTOR_G = W.MOTOR['mass']
TPU, SEAL = (0.86, 0.56, 0.16), (0.16, 0.62, 0.66)
SAND, SAND_D, OLIVE, OLIVE_D, STEEL, DARK = (0.62, 0.56, 0.44), (0.50, 0.45, 0.35), (0.42, 0.48, 0.41), (0.33, 0.38, 0.33), (0.30, 0.32, 0.35), (0.14, 0.15, 0.16)

def plan_tub(off=0.0):
    from scipy.spatial import ConvexHull
    th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    pts = np.vstack([[[TUB_X0 + off, YR + off], [100, YR + off], [100, YL - off], [TUB_X0 + off, YL - off]],
                     np.c_[Hm.HX + (Hm.NOSE_R - off) * np.cos(th), Hm.HY + (Hm.NOSE_R - off) * np.sin(th)]])
    return [tuple(p) for p in pts[ConvexHull(pts).vertices]]

def belly(grow=0.0):
    """the material taken out of the underside: the tunnel (X TUB_X0..TUN_X1, roof TUN_Z), a ramp down to the nose
    floor, the nose floor (NOSE_Z) to the bow. grow > 0 gives the liner's outside (the cavity must keep off it)."""
    if LEGS in ('v1', 'wheels'):
        aft = [(TUB_X0 - 10, -5), (TUB_X0 - 10, TUN_Z + grow)]
    else:                                                               # a ramp up from the motor bay's floor
        aft = [(TUN_X0 - grow * 0.5, -5), (TUN_X0 - grow * 0.5, FLOOR0 - 0.01 + grow), (TUN_X0 + 25, TUN_Z + grow)]
    prof = aft + [(TUN_X1 - 18, TUN_Z + grow), (TUN_X1 + grow * 0.5, NOSE_Z + grow), (160, NOSE_Z + grow), (160, -5)]
    a = cq.Workplane("XZ").polyline(prof).close().extrude(-200).translate((0, YC - 100, 0))   # XZ extrudes to +Y when negative
    t = np.tan(np.radians(TUN_ANG)); hw0 = TUN_HW + grow / np.sin(np.radians(TUN_ANG))
    trap = [(YC - hw0 - 20 / t, FLOOR0 - 20), (YC + hw0 + 20 / t, FLOOR0 - 20), (YC + hw0 - 45 / t, FLOOR0 + 45), (YC - hw0 + 45 / t, FLOOR0 + 45)]
    b = cq.Workplane('YZ').polyline(trap).close().extrude(340).translate((TUB_X0 - 20, 0, 0))
    nose = wp().box(200, 300, NOSE_Z + grow + 10).translate((TUN_X1 + 60 + 100, YC, (NOSE_Z + grow - 10) / 2))   # bow: X > TUN_X1 + 60
    return a.intersect(b).union(nose)

def ramp(grow=0.0):
    if RAMP_X is None: return None
    t28 = np.tan(np.radians(28)); dz = grow / np.cos(np.radians(28))
    return cq.Workplane('XZ').polyline([(RAMP_X, FLOOR0 - 0.01 + dz), (RAMP_X - 120, FLOOR0 + dz + 120 * t28), (RAMP_X - 120, -60), (RAMP_X + dz, -60)]).close() \
        .extrude(150, both=True).translate((0, YC, 0))

V2_HOLES = [(x, z) for x in (-75.0, -30.0, 15.0, 60.0, 105.0) for z in (18.0, 46.0)]   # world X: frame-to-hull screws (M3 inserts)
def wheel_pad(x, y):
    """wheels: a corner pod's pad on the wall at y, centred on body X x. Where the wall curves away (the six-wheel's
    front pods, on the nose) a cheek fills back to it; its inboard top stops 1 under the claws' roots (Z 43), the outer
    3.5 mm stays full height round the inserts"""
    sg = 1 if y > YC else -1; z0 = FLOOR0 if W.PAD_Z0 is None else W.PAD_Z0; hz = W.Z_A + W.HALF - z0
    p = wp().box(2 * W.HALF, W.PAD, hz, centered=False).translate((x - W.HALF, y if sg > 0 else y - W.PAD, z0))
    if W.CHEEK:
        ck = wp().box(2 * W.HALF, W.CHEEK, hz, centered=False).translate((x - W.HALF, y - W.CHEEK if sg > 0 else y, z0))
        ck = ck.cut(wp().polyline(plan_tub()).close().extrude(200).translate((0, 0, -50)))
        if ck.solids().size():                                          # empty along the straight wall (and cut() on an
            ck = ck.cut(wp().box(2 * W.HALF + 2, W.CHEEK - 2.5, 30, centered=False)   # empty stack reaches back to the uncut box)
                        .translate((x - W.HALF - 1, y - W.CHEEK - 1 if sg > 0 else y + 3.5, W.Z_A + 17)))
            p = p.union(ck)
    return p
def tub():
    o = wp().polyline(plan_tub()).close().extrude(TUB_TOP - FLOOR0).translate((0, 0, FLOOR0)).edges('|Z and <X').fillet(10)
    i = wp().polyline(plan_tub(WALL)).close().extrude(TUB_TOP - FLOOR0 + 1).translate((0, 0, FLOOR0 + WALL)).edges('|Z and <X').fillet(7.4)
    i = i.cut(belly(WALL)); o = o.cut(belly())
    if RAMP_X is not None: i = i.cut(ramp(WALL)); o = o.cut(ramp())
    o = o.cut(i)
    for y in (YL, YR):
        if LEGS == 'v1':                                                # the pods' 6 screws (levelled pattern) and motor windows
            for x, z in Hm.POD_HOLES:
                px, _, pz = Hm.level(np.array([x, 0, z]))
                o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(1.7).extrude(20, both=True).translate((px - BODY_DX, y, pz)))
            o = o.cut(wp().box(66, 12, 41, centered=False).translate((-51 - BODY_DX, y - 6, 3.0)))
        elif LEGS == 'wheels':                                          # a pad per corner pod (4 M3 inserts), a notch for its leads
            sg = 1 if y > YC else -1
            for c, xa in W.AXLES.items():
                x = xa - BODY_DX
                o = o.union(wheel_pad(x, y))
                for dx in (-17, 17):
                    for dz in (-17, 17):
                        o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(2.0).extrude(6, both=True).translate((x + dx, y + sg * W.PAD, W.Z_A + dz)))
                o = o.cut(wp().box(9, 14, 8).translate((W.LEAD_X[c] - BODY_DX, y, TUB_TOP - 3)))   # leads in over the pack, under the side lid
        else:                                                           # v2: the gearbox's hole, and 10 M3 inserts for the leg frame
            o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(L2.MOTOR['gb_d'] / 2 + 0.75).extrude(20, both=True)
                      .translate((L2.SPROCKET[0] - BODY_DX, y, L2.SPROCKET[1])))
            for x, z in V2_HOLES:
                o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(2.0).extrude(20, both=True).translate((x - BODY_DX, y, z)))
    for y0, y1 in ((YR + WALL, YR + WALL + 3), (YL - WALL - 3, YL - WALL)):                                     # turret-deck ledges
        o = o.union(wp().box(52, y1 - y0, 2, centered=False).translate((Hm.CAR_X1, y0, TDECK - 4.4)))
    for x, y in ((46, Hm.HY - 30), (46, Hm.HY + 30), (110, Hm.HY - 30), (110, Hm.HY + 30)):                    # the base's feet
        o = o.union(wp().circle(3.5).extrude(4).translate((x, y, NOSE_Z + WALL)))
    for y0 in (YR + WALL, YL - WALL - 2):                                                                       # bay ends (pack stops)
        for x in (PACK_X0 - 1.5, ESC_X0 - 1.5):
            o = o.union(wp().box(1.5, 2, 20, centered=False).translate((x, y0, FLOOR0 + WALL)))
    return o.val()

def turret_deck():
    """the deck round the head, in three: a ring round the well (it can't lift past the cradle) and two side lids over
    the packs' front ends, so the packs lift out"""
    d = wp().polyline(plan_tub(WALL + 0.3)).close().extrude(2.4).translate((0, 0, TDECK - 2.4))
    d = d.intersect(wp().box(200, 300, 20, centered=False).translate((Hm.CAR_X1, -150, TDECK - 10)))
    d = d.cut(wp().circle(32.4).extrude(10).translate((Hm.HX, Hm.HY, TDECK - 5)))
    band = wp().box(300, 2 * 35.5, 30).translate((Hm.HX, YC, TDECK))
    return d.intersect(band).val(), d.cut(wp().box(300, 2 * 36.0, 30).translate((Hm.HX, YC, TDECK))).val()

BED = (-62.0, -48.0, 34.0, 55.5)
def carapace():
    """centre hull over the tub: glacis behind the head, the bed deck, the tail rising to the pedestal, raked back"""
    prof = [(TUB_X0, TUB_TOP), (50, TUB_TOP), (50, TDECK), (40, DECK), (BED[0], DECK), (-98, PZ), (-140, PZ), (TUB_X0 - 4, PZ - 14), (TUB_X0, TUB_TOP + 8)]
    w = YL - YR
    o = cq.Workplane('XZ').polyline(prof).close().extrude(-w).translate((0, YR, 0))
    o = o.union(wp().circle(PED_R).extrude(PZ - DECK).translate((AX, YC, DECK)))
    inner = cq.Workplane('XZ').polyline(prof).close().offset2D(-2.4).extrude(-(w - 4.8)).translate((0, YR + 2.4, 0))
    o = o.cut(inner).cut(wp().box(220, w - 4.8, 8, centered=False).translate((TUB_X0 + 2, YR + 2.4, TUB_TOP - 4)))
    o = o.cut(wp().circle(PED_R - 2.4).extrude(PZ - 2.4 - DECK + 4).translate((AX, YC, DECK - 4)))
    x0, y0, x1, y1 = BED
    o = o.cut(wp().box(x1 - x0 - 6, y1 - y0 - 6, 6, centered=False).translate((x0 + 3, y0 + 3, DECK - 4)))
    o = o.cut(wp().circle(4).extrude(10).translate((AX, YC, PZ - 5)))
    for i in range(5):                                                  # exhaust: louvres facing aft, under the tail's overhang
        o = o.cut(wp().box(8, 10, 4).translate((TUB_X0 - 1, YC - 30 + 15 * i, TUB_TOP + 14)))
    return o.val()

def bed():
    x0, y0, x1, y1 = BED
    h = wp().box(x1 - x0, y1 - y0, 2.4, centered=False).translate((x0, y0, DECK)).edges('|Z').fillet(6)
    h = h.union(wp().box(x1 - x0, y1 - y0, 6, centered=False).translate((x0, y0, DECK + 2.4)).edges('|Z').fillet(6)
                .cut(wp().box(x1 - x0 - 5, y1 - y0 - 5, 6, centered=False).translate((x0 + 2.5, y0 + 2.5, DECK + 2.4)).edges('|Z').fillet(4)))
    for x in (x0 + 9, x1 - 9):
        for y in (y0 + 9, y1 - 9):
            eye = cq.Workplane('XZ').circle(5).circle(2.5).extrude(2, both=True).translate((x, y, DECK + 8.4))
            h = h.union(eye.cut(wp().box(12, 6, 10).translate((x, y, DECK + 1.8))))
    return h.val()

def fenders(Wtop):
    """full-length fenders over the tracks, out to the skirts' top edge"""
    out = []
    for sg in (1, -1):
        y_in, y_out = (YL, YC + Wtop) if sg > 0 else (YC - Wtop, YR)
        f = wp().box(FEND_X1 - FEND_X0, y_out - y_in, 2.4, centered=False).translate((FEND_X0, y_in, FENDER))
        f = f.union(wp().box(2.4, y_out - y_in, 8, centered=False).translate((FEND_X1 - 2.4, y_in, FENDER - 5.6)))
        f = f.edges('|Y and >X').fillet(1.0)
        f = f.cut(wp().box(80, 80, 80).rotate((0, 0, 0), (0, 0, 1), 45).translate((FEND_X1, y_out if sg > 0 else y_in, FENDER)).translate((0, 0, 0)))
        out.append(f.val())
    return out

# ---------------------------------------------------------------- the outline: skirts and hoops
class Outline:
    """a spiral about the centre of mass (cy, cz) in the cross-section: r = r0 + SPIRAL * (a - a0), from the tracks'
    bottom outer edge (a0) round to the top (90 deg). The distance from the centre of mass then only grows from the
    tracks to the top, so no face on it can hold the robot."""
    def __init__(s, hw, cz, margin=R_MARGIN, grow=SPIRAL):
        s.cz = cz; s.a0 = np.arctan2(G0 - cz, hw); s.r0 = np.hypot(hw, cz - G0) + margin; s.grow = grow
        a = np.linspace(s.a0, np.pi / 2, 400); r = s.r0 + grow * (a - s.a0)
        s.y, s.z = r * np.cos(a), cz + r * np.sin(a)
    def at(s, z): return float(np.interp(z, s.z, s.y))
    def arc(s, z0, n=40, shrink=0.0):
        """points from height z0 on the left, over the top, down to z0 on the right: (y offset, z)"""
        a = np.linspace(np.arcsin(np.clip((z0 - s.cz) / (s.r0 + s.grow * (np.pi / 2 - s.a0)), -1, 1)), np.pi / 2, n)
        a = a[(s.cz + (s.r0 + s.grow * (a - s.a0)) * np.sin(a)) >= z0 - 1e-6]
        r = s.r0 + s.grow * (a - s.a0) - shrink; left = np.c_[r * np.cos(a), s.cz + r * np.sin(a)]
        return np.vstack([left, left[-2::-1] * [-1, 1]])
    @property
    def top(s): return s.cz + s.r0 + s.grow * (np.pi / 2 - s.a0)

def skirts(O):
    """armour outside the tracks, on the outline from the fender down to SKIRT_Z0; 2.4 thick"""
    zs = np.linspace(SKIRT_Z0, FENDER + 2.4, 24); out = []
    for sg in (1, -1):
        outer = [(YC + sg * O.at(z), z) for z in zs]; inner = [(YC + sg * (O.at(z) - 2.4), z) for z in zs[::-1]]
        p = cq.Workplane('YZ').polyline(outer + inner).close().extrude(FEND_X1 - 6 - FEND_X0).translate((FEND_X0, 0, 0))
        p = p.cut(wp().box(40, 300, 40).rotate((0, 0, 0), (0, 1, 0), 45).translate((FEND_X1 - 6, YC, SKIRT_Z0)))   # front: swept up
        p = p.cut(wp().box(120, 300, 120).rotate((0, 0, 0), (0, 1, 0), -45).translate((SKIRT_BX - 60 * 2 ** 0.5, YC, SKIRT_Z0)))      # back: swept up 45 deg
        p = p.cut(wp().box(80, 80, 120).rotate((0, 0, 0), (0, 0, 1), 45).translate((FEND_X1, YC + sg * (O.at(O.cz) + 2.4), 30)))   # front corner, in plan
        out.append(p.val())
    return out

def hoop_pts(O, x_foot, rake, n=40):
    """the hoop's centre line: the outline shrunk by the tube, from one skirt top over to the other; leaning aft by rake"""
    z0 = FENDER + 2.4; A = O.arc(z0 + TUBE_R, n, TUBE_R)
    return np.c_[x_foot - rake * (A[:, 1] - z0), YC + A[:, 0], A[:, 1]]

def tube_tris(P, r):
    return np.vstack([cyl_tris(P[i], P[i + 1], r, 20) for i in range(len(P) - 1)])

# ---------------------------------------------------------------- inside: what moves where
def box_at(x0, x1, y0, y1, z0, z1, r=1.5): return rbox(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), r)
YLi, YRi = YL - WALL - 0.5, YR + WALL + 0.5                 # bays' outer faces
LAYOUT = {  # key: (label, (x0, x1, y0, y1, z0, z1), colour, note)     * = guessed size
    'pack_L': ('Pack, left (Zeee 2S 5200), on edge', (PACK_X0, PACK_X0 + 141, YLi - 26, YLi, FLOOR0 + WALL + 0.2, FLOOR0 + WALL + 0.2 + 45.7), (0.88, 0.69, 0.25),
               'Your model\'s box (141 x 45.7 x 26), stood on edge in a bay along the wall, beside the head base: 99 forward of hull.py\'s spot. Lifts out from the top.'),
    'pack_R': ('Pack, right, on edge', (PACK_X0, PACK_X0 + 141, YRi, YRi + 26, FLOOR0 + WALL + 0.2, FLOOR0 + WALL + 0.2 + 45.7), (0.88, 0.69, 0.25), ''),
    'esc_L': ('ESC, left, on edge*', (ESC_X0, ESC_X0 + 46, YLi - 18, YLi, FLOOR0 + WALL + 0.2, FLOOR0 + WALL + 34.2), (0.18, 0.37, 0.69),
              'Down from the sponson to the floor, behind its pack: 55 mm lower. Size* 46 x 34 x 18.'),
    'esc_R': ('ESC, right, on edge*', (ESC_X0, ESC_X0 + 46, YRi, YRi + 18, FLOOR0 + WALL + 0.2, FLOOR0 + WALL + 34.2), (0.18, 0.37, 0.69), ''),
    'arm_ubec': ('Arm UBEC 8 A*, on edge, left bay', (-139.0, -91.0, YLi - 22.5, YLi - 7.5, 31.0, 61.0), (0.24, 0.6, 0.3), 'Behind the left ESC, on a shelf over the rear chamfer.'),
    'ubec': ('UBEC 5 V / 5 A (Pi only)*, on edge, right bay', (-139.0, -94.0, YRi + 7.5, YRi + 19.5, 31.0, 57.0), (0.24, 0.6, 0.3), 'Behind the right ESC.'),
    'pca': ('PCA9685 (Adafruit size)', (-122.0, -59.8, YC - 12.85, YC + 12.85, 31.4, 43.8), (0.12, 0.31, 0.63), 'On the tunnel roof behind the Pi.'),
    'ina219': ('INA219 pack monitor*', (-138.0, -112.0, YC - 25, YC - 4, 46.0, 50.0), (0.24, 0.6, 0.3), ''),
    'wifi': ('USB WiFi dongle*', (-138.0, -98.0, YC + 2, YC + 20, 46.0, 56.0), (0.24, 0.6, 0.3), 'Its antenna runs up inside the rear hoop.'),
    'alarm': ('LiPo alarm*', (-139.0, -131.0, YC - 20, YC + 20, 62.0, 76.0), (0.24, 0.6, 0.3), 'Buzzer at the back.'),
    'pi_switch': ('Pi power switch*', (-139.0, -131.0, YC + 21, YC + 39, 46.0, 59.0), (0.24, 0.6, 0.3), ''),
}
LAYOUT_V2 = {  # on v2 legs the motors fill the tail's bottom (body X -138..-100, Z 11..49): the power parts go over them
    'pca': ('PCA9685 (Adafruit size), over the motors', (-138.0, -75.8, YC - 12.85, YC + 12.85, 51.0, 63.4), (0.12, 0.31, 0.63), ''),
    'ubec': ('UBEC 5 V / 5 A (Pi only)*', (-138.0, -93.0, YC - 41, YC - 15, 51.0, 63.0), (0.24, 0.6, 0.3), 'Over the left motor.'),
    'arm_ubec': ('Arm UBEC 8 A*', (-138.0, -88.0, YC + 15, YC + 45, 51.0, 66.0), (0.24, 0.6, 0.3), 'Over the right motor.'),
    'ina219': ('INA219 pack monitor*', (-130.0, -104.0, YC - 10.5, YC + 10.5, 65.0, 69.0), (0.24, 0.6, 0.3), ''),
    'wifi': ('USB WiFi dongle*', (-138.0, -98.0, YC - 38, YC - 20, 66.0, 76.0), (0.24, 0.6, 0.3), 'Its antenna runs up inside the rear hoop.'),
    'alarm': ('LiPo alarm*', (-120.0, -112.0, YC - 20, YC + 20, 78.0, 92.0), (0.24, 0.6, 0.3), ''),
    'pi_switch': ('Pi power switch*', (-86.0, -78.0, YC - 45, YC - 25, 50.0, 63.0), (0.24, 0.6, 0.3), ''),
}
PI_DZ = (TUN_Z + WALL + 5.0) - 44.0          # the Pi stands on 5 mm TPU isolators on the tunnel roof

def build():
    t0 = time.time()
    src = np.load(os.path.join(OUT, '_hull_meshes.npz')); meta = json.load(open(os.path.join(OUT, '_hull_meta.json')))
    M = {}
    def add(k, tris, label, grp, rgb, note='', world=False):
        M[k] = dict(t=np.asarray(tris, float).reshape(-1, 3, 3) + ([0, 0, 0] if world or grp == 'legs' else [BODY_DX, 0, 0]),
                    label=label, grp=grp, rgb=rgb, note=note)
    hexrgb = TA.hexrgb
    if LEGS == 'v1':
        for k in src.files:                                             # the legs, unmoved
            if meta[k]['group'] == 'legs':
                add(k, src[k], meta[k]['label'], 'legs', hexrgb(meta[k]['color']), meta[k]['note'])
    elif LEGS == 'wheels':
        for k, v in W.meshes().items(): M[k] = dict(v, ghost=False)
    else:
        legs, n = L2.meshes()
        for k, v in legs.items(): M[k] = dict(v, ghost=v.get('ghost', False))
    up = np.array([0, 0, RAISE])
    for k in ('base', 'drum', 'cradle', 'ball'):
        add(k, src[k] + up, meta[k]['label'], 'head', hexrgb(meta[k]['color']), 'Raised 10 with the nose floor.')
    for k in ('pi', 'hat', 'hailo'):
        add(k, src[k] + [0, 0, PI_DZ], meta[k]['label'], 'elec', hexrgb(meta[k]['color']), 'On TPU isolators on the tunnel roof: 8 lower than in hull.py.')
    CLAW_UP = np.array([0, 0, RAISE + 10])
    for k in ('claw0', 'claw1', 'light0', 'light1'):
        add(k, src[k] + CLAW_UP, meta[k]['label'], 'hull' if k.startswith('claw') else 'elec', hexrgb(meta[k]['color']),
            'Up 20: the claws set the approach angle, and still guard the ball.' if k.startswith('claw') else '')
    add('tub', cq_tris(tub()), 'Tub (new)', 'hull', OLIVE_D,
        'Pack bays along both walls; a tunnel down the middle of the belly (roof %.0f over the ground); the nose floor raised 10; 20 longer, the back chamfered.' % (TUN_Z - G0))
    ring, lids = turret_deck()
    add('tdeck', cq_tris(ring), 'Turret deck ring', 'hull', OLIVE, '10 higher, with the head.')
    add('tdeck_lids', cq_tris(lids), 'Turret deck side lids', 'hull', OLIVE, 'Over the packs\' front ends: they lift off, so the packs come out the top.')
    add('carapace', cq_tris(carapace()), 'Carapace (new)', 'hull', SAND,
        'Lower: the bed at Z %.0f (was 87). Glacis behind the head; the tail rises 32 deg to the arm pedestal and leans aft; exhaust louvres face aft under the overhang.' % DECK)
    add('bed', cq_tris(bed()), 'Cargo bed (brain hatch)', 'hull', SAND_D, 'Screwed down (captive screws, not magnets: magnets let go in a fall), on a gasket.')
    lay = dict(LAYOUT)
    if LEGS == 'v2': lay.update(LAYOUT_V2)
    for k, (lab, b, rgb, note) in lay.items():
        add(k, cq_tris(box_at(*b)), lab, 'elec', rgb, note)
    print('body parts %.0f s' % (time.time() - t0))
    return M

def add_shell(M, O):
    """skirts, fenders, hoops, bumpers and seals, sized to the outline O"""
    def add(k, tris, label, grp, rgb, note='', world=False):
        M[k] = dict(t=np.asarray(tris, float).reshape(-1, 3, 3) + ([0, 0, 0] if world else [BODY_DX, 0, 0]), label=label, grp=grp, rgb=rgb, note=note)
    Wtop = O.at(FENDER + 2.4) if CAGE else corners(M) + 3.0
    for i, f in enumerate(fenders(Wtop) if LEGS != 'wheels' else ()):   # wheels: no fenders (Zach, 2026-10-05)
        add('fender%d' % i, cq_tris(f), 'Fender (full length)', 'hull', OLIVE, 'Over the whole track, out to the %s.' % ('skirt' if CAGE else 'track\'s edge'), world=True)
    for i, sk in (enumerate(skirts(O)) if CAGE else ()):
        add('skirt%d' % i, cq_tris(sk), 'Side skirt', 'hull', OLIVE,
            'Armour outside the track, on the outline: it rolls the robot back off its side, guards the track from side hits, and keeps thrown dirt off the top.', world=True)
    hoops = (('hoop_f', HOOP_XF, 0.0, 'Front roll hoop'),) + ((('hoop_r', HOOP_XR, RAKE, 'Rear roll hoop'),) if REAR_HOOP else ())
    for k, xf, rk, lab in (hoops if CAGE else ()):
        P = hoop_pts(O, xf, rk)
        add(k, tube_tris(P, TUBE_R), lab, 'cage', DARK,
            'On the outline: %.0f over the ground at the top. %s' % (P[:, 2].max() + TUBE_R - G0,
            'Behind the head, out of the cradle\'s sweep.' if k == 'hoop_f' else 'Leans aft so it won\'t stand on its tail; the WiFi antenna runs inside its top (printed: radio-clear).'))
        top = P[np.abs(P[:, 1] - YC) < 45]
        add(k + '_pad', tube_tris(top, TUBE_R + 2.0), lab + ': TPU sleeve', 'tpu', TPU, 'Where it lands upside down.')
        if k == 'hoop_f' and BROW:
            t0 = P[np.argmax(P[:, 2])]; bars, pads = [], []
            for yo in ((0.0,) if BROW_Y == 0 else (-BROW_Y, BROW_Y)):  # one bar, or a fork
                tip = np.array([BROW_X, YC + yo, BROW_Z]); B = np.vstack([t0 + (tip - t0) * f for f in np.linspace(0, 1, 12)])
                bars.append(tube_tris(B, 5.0)); pads.append(tube_tris(B[-4:], 7.0))
            add('brow', np.vstack(bars), 'Brow bar', 'cage', DARK,
                'From the hoop\'s top forward over the ball: in a nose-dive it lands here, not on the camera. Thin, and above the lens line.')
            add('brow_pad', np.vstack(pads), 'Brow bar: TPU tip', 'tpu', TPU, '')
    # TPU rub strips along the skirts' widest line, corner blocks at the back
    for sg in (1, -1):
        zr = O.cz + 6; y = YC + sg * (O.at(zr) - 3.2)
        if CAGE: add('rub%d' % (sg > 0), cyl_tris((FEND_X0 + 8, y, zr), (FEND_X1 - 75, y, zr), 3.2, 16), 'TPU rub strip', 'tpu', TPU, 'Where it lands on its side.', world=True)
        add('corner%d' % (sg > 0), cq_tris(box_at(TUB_X0 - 7, TUB_X0 + 3, YC + sg * 55 - 9, YC + sg * 55 + 9, 34.0, 58.0, 3)), 'TPU tail bumper', 'tpu', TPU, 'Takes the hits when it backs off a ledge.')
    for k in ('claw0', 'claw1'):
        c = M[k]['t'].reshape(-1, 3); tip = c[c[:, 0] > c[:, 0].max() - 14]
        lo, hi = tip.min(0), tip.max(0)
        add(k + '_tip', cq_tris(box_at(lo[0] + 2, hi[0] + 3, lo[1] - 1.5, hi[1] + 1.5, lo[2] - 1.5, hi[2] + 1.5, 3)), 'TPU claw cap', 'tpu', TPU, 'First to touch when it noses in.', world=True)
    # seals and dust blockers
    x0, y0, x1, y1 = BED
    ring = wp().box(x1 - x0 - 1, y1 - y0 - 1, 1.6, centered=False).translate((x0 + 0.5, y0 + 0.5, DECK - 1.6)).cut(
        wp().box(x1 - x0 - 9, y1 - y0 - 9, 2, centered=False).translate((x0 + 4.5, y0 + 4.5, DECK - 1.8)))
    add('seal_bed', cq_tris(ring.val()), 'Bed gasket (TPU cord)', 'seal', SEAL, 'In a groove round the bed opening.')
    rim = wp().polyline(plan_tub(0.4)).close().extrude(1.6).translate((0, 0, TUB_TOP - 1.6)).cut(
        wp().polyline(plan_tub(WALL - 0.4)).close().extrude(2).translate((0, 0, TUB_TOP - 1.8)))
    add('seal_rim', cq_tris(rim.intersect(wp().box(TUB_X0 * -1 + 50, 300, 10, centered=False).translate((TUB_X0, -150, TUB_TOP - 5))).val()),
        'Tub-to-carapace gasket', 'seal', SEAL, 'The long seam, sealed.')
    wiper = wp().circle(36.5).circle(30.0).extrude(2.0).translate((Hm.HX, Hm.HY, TDECK))
    add('seal_turret', cq_tris(wiper.val()), 'Turret wiper ring (TPU)', 'seal', SEAL, 'A lip from the deck onto the drum: the well\'s gap is the biggest opening on top.')
    for y in (YL, YR):
        if LEGS == 'v1':
            boot = wp().box(70, 3, 39, centered=False).translate((-53, y - 1.5, FLOOR0)).cut(wp().box(64, 5, 33, centered=False).translate((-50, y - 2.5, FLOOR0 + 3)))
            add('seal_motor%d' % (y > 0), cq_tris(boot.val()), 'Motor window boot (TPU)', 'seal', SEAL, 'Closes the gap round the motor can where it stands into the hull.', world=True)
        elif LEGS == 'wheels':
            for c, xa in W.LEAD_X.items():
                yg = y - (1.3 if y > YC else -1.3)                                         # in the wall's thickness
                g_ = wp().box(8.6, 2.6, 6.6).translate((xa, yg, TUB_TOP - 3.3)).cut(wp().box(4, 4, 4).translate((xa, yg, TUB_TOP - 3.3)))
                add('seal_lead%s%d' % (c, y > YC), cq_tris(g_.val()), 'Lead grommet (TPU)', 'seal', SEAL, 'The motor\'s leads come in here, over the pack.', world=True)
        else:
            ring = cq.Workplane('XZ').circle(L2.MOTOR['gb_d'] / 2 + 4).circle(L2.MOTOR['gb_d'] / 2).extrude(-1.2).translate((L2.SPROCKET[0], y + (0 if y > 0 else -1.2) - 0.4 * (1 if y > 0 else -1), L2.SPROCKET[1]))
            add('seal_motor%d' % (y > 0), cq_tris(ring.val()), 'Gearbox O-ring (TPU)', 'seal', SEAL, 'Seals the gearbox where it passes through the hull wall.', world=True)
    if CAGE: hood = wp().box(26, 40, 14).edges('|X and >Z').fillet(6).translate((-120, YC, PZ + 7)).cut(wp().box(30, 34, 10).translate((-122, YC, PZ + 4)))
    else:    hood = wp().box(40, 18, 10).edges('|X and >Z').fillet(4).translate((-118, YC - 52, PZ + 5)).cut(wp().box(44, 12, 6).translate((-120, YC - 52, PZ + 3)))   # beside the arm's turntable, under its sweep (top Z 114)
    add('intake', cq_tris(hood.val()), 'Air intake hood + foam filter', 'seal', SEAL,
        'The Pi\'s cooler still needs air: it comes in high (dust stays low), through foam, and leaves through the aft louvres.')
    for k, x, y in (('grommet0', 60, YC - 34), ('grommet1', 60, YC + 40)):
        add(k, cq_tris(wp().circle(5).circle(2.5).extrude(3).translate((x, y, TDECK)).val()), 'Cable grommet', 'seal', SEAL, 'Ribbon and servo leads up to the head.')
    for i, (x, y) in enumerate(((-55, -25), (-55, 20), (25, -25), (25, 20))):
        add('iso%d' % i, cq_tris(wp().circle(4).extrude(5).translate((x + 2, y, TUN_Z + WALL)).val()), 'TPU isolator', 'tpu', TPU, 'The Pi floats on 4 of these: falls reach it softened.')
    for k in ('pack_L', 'pack_R'):
        b = M[k]['t'].reshape(-1, 3); lo, hi = b.min(0), b.max(0)
        add(k + '_clamp', cq_tris(box_at(lo[0] + 20, hi[0] - 20, lo[1] - 0.5, hi[1] + 0.5, hi[2], hi[2] + 3, 1)), 'Pack clamp (TPU-faced bar)', 'tpu', TPU,
            'Holds the pack down in the bay: packs are a third of the mass.', world=True)
    ex, ey, ez, enote = (-95, YC - 95, FENDER + 2.4, 'On the right fender, inside the cage line.') if LEGS != 'wheels' else \
        (78, YC - 50, TDECK, 'On the right side lid, beside the head and outside the cradle\'s sweep: the fender it sat on is gone.')
    add('estop', np.vstack([cq_tris(wp().circle(11).extrude(8).translate((ex, ey, ez)).val()),
                            cq_tris(wp().circle(13).extrude(6).translate((ex, ey, ez + 8)).edges('>Z').fillet(3).val())]),
        'E-stop', 'elec', (0.78, 0.13, 0.13), enote, world=True)
    if CAGE:
        P = hoop_pts(O, HOOP_XR if REAR_HOOP else HOOP_XF, RAKE if REAR_HOOP else 0.0); top = P[np.abs(P[:, 1] - YC) < 70]
        add('antenna', tube_tris(top, 2.2), 'WiFi antenna (inside the %s hoop)' % ('rear' if REAR_HOOP else 'front'), 'elec', (0.1, 0.1, 0.1), '')
    else:
        add('antenna', cyl_tris((-138, YC + 22, PZ - 6), (-100, YC + 22, PZ - 6), 2.2, 16), 'WiFi antenna (inside the tail hump: printed, radio-clear)', 'elec', (0.1, 0.1, 0.1), '')
    return Wtop

# ---------------------------------------------------------------- mass
DENS = {'hull': 1.2e-3 * 0.9, 'cage': 1.2e-3 * 0.45, 'tpu': 1.21e-3 * 0.6, 'seal': 1.21e-3 * 0.8, 'legs': 1.24e-3 * 0.35}   # thin walls print solid
LUMP = {'claw0': 0.4, 'claw1': 0.4, 'hoop_f_pad': 0.42 * 1.21e-3 / DENS['tpu'], 'hoop_r_pad': 0.42 * 1.21e-3 / DENS['tpu']}
FIXED = {'pack_L': 300, 'pack_R': 300, 'esc_L': 55, 'esc_R': 55, 'ubec': 30, 'arm_ubec': 40, 'pca': 12, 'ina219': 3, 'wifi': 10, 'alarm': 8,
         'pi_switch': 6, 'estop': 20, 'antenna': 8, 'light0': 5, 'light1': 5}
def centroid(t):
    t = np.asarray(t).reshape(-1, 3, 3); v = np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])) / 6
    if abs(v.sum()) < 1e-6: return t.reshape(-1, 3).mean(0), 0.0
    return (v[:, None] * t.sum(1) / 4).sum(0) / v.sum(), abs(v.sum())

def mass_items(M, motor=None, head=210, pi=95, wiring=60):
    motor = MOTOR_G if motor is None else motor
    items = []
    for k, v in M.items():
        if v.get('ghost'): continue
        c, vol = centroid(v['t'])
        if k in FIXED: items.append((k, FIXED[k], c))
        elif k.startswith('motor_'): items.append((k, motor, c))
        elif k.startswith('track_'): items.append((k, vol * 1.21e-3 * 0.9, c))
        elif k.startswith('tire_'): items.append((k, vol * 1.21e-3 * 0.8, c))
        elif LEGS == 'wheels' and k.startswith(('pod_', 'rim_')): items.append((k, vol * 1.24e-3 * 0.9, c))   # thin walls: solid
        elif k in ('base', 'drum', 'cradle', 'ball'): pass
        elif k in ('pi', 'hat', 'hailo'): pass
        elif v['grp'] in DENS: items.append((k, vol * DENS[v['grp']] * LUMP.get(k, 1.0), c))
    hb = np.vstack([M[k]['t'].reshape(-1, 3) for k in ('base', 'ball')]); items.append(('head', head, (Hm.HX + BODY_DX, YC, (hb[:, 2].min() + hb[:, 2].max()) / 2)))
    ps = np.vstack([M[k]['t'].reshape(-1, 3) for k in ('pi', 'hat')]); items.append(('pi stack', pi, (ps.min(0) + ps.max(0)) / 2))
    items.append(('wiring', wiring, (-20 + BODY_DX, YC, 40)))
    return items

def cog(items):
    m = np.array([g for _, g, _ in items]); c = np.array([p for _, _, p in items], float)
    return (m[:, None] * c).sum(0) / m.sum(), float(m.sum())

# ---------------------------------------------------------------- analyses
def feet(M, side=''):
    """points of the parts it stands on: the tracks, or the tyres; side 'L' or 'R'"""
    return np.vstack([M[k]['t'].reshape(-1, 3) for k in M if k.startswith(('track_', 'tire_')) and k.endswith(side) and not M[k].get('ghost')])

def ground(M):
    return float(feet(M)[:, 2].min())

def corners(M):
    """the tracks' (tyres') bottom outer edges: their distance from the centre line"""
    return float(np.abs(feet(M)[:, 1] - YC).max())

def outline(M, items):
    """the outline for the current centre of mass; and whether the face from the track edge to the skirt's bottom edge
    leans out past the centre of mass (it must, or the robot could rest on its side on it)"""
    c, _ = cog(items); hw = corners(M); O = Outline(hw, c[2])
    yb, zb = O.at(SKIRT_Z0), SKIRT_Z0; u = (-hw, c[2] - G0); v = (yb - hw, zb - G0)
    O.skirt_ok = u[0] * v[0] + u[1] * v[1] < 0
    return O, c

def rest_states(M, items, keys=None):
    """stable rests of the robot's convex hull: faces whose foot from the centre of mass lies inside them"""
    from scipy.spatial import ConvexHull
    keys = keys or [k for k in M if not M[k].get('ghost')]
    P = np.vstack([M[k]['t'].reshape(-1, 3) for k in keys]); P = np.unique(np.round(P, 2), axis=0)
    H = ConvexHull(P); eq = H.equations; c, _ = cog(items)
    groups = {}
    for i, e in enumerate(eq):
        groups.setdefault(tuple(np.round(np.r_[e[:3] * 200, e[3]]).astype(int)), []).append(i)
    out = []
    for g, idx in groups.items():
        n = eq[idx[0], :3]; d = eq[idx[0], 3]; foot = c - (n @ c + d) * n
        inside = False
        for i in idx:
            A, B, Cc = P[H.simplices[i]]; v0, v1, v2 = Cc - A, B - A, foot - A
            d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1; den = d00 * d11 - d01 * d01
            if abs(den) < 1e-9: continue
            u = (d11 * d20 - d01 * d21) / den; v = (d00 * d21 - d01 * d20) / den
            if u >= -1e-6 and v >= -1e-6 and u + v <= 1 + 1e-6: inside = True; break
        if inside:
            area = sum(0.5 * np.linalg.norm(np.cross(*(P[H.simplices[i]][1:] - P[H.simplices[i]][0]))) for i in idx)
            edges = {}
            for i in idx:
                tri = H.simplices[i]
                for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                    key = (min(a, b), max(a, b)); edges[key] = edges.get(key, 0) + 1
            dmin = 1e9
            for (a, b), cnt in edges.items():
                if cnt > 1: continue
                A, B = P[a], P[b]; t = np.clip((foot - A) @ (B - A) / max((B - A) @ (B - A), 1e-9), 0, 1)
                dmin = min(dmin, np.linalg.norm(A + t * (B - A) - foot))
            hgt = float(-(n @ c + d)); tilt = float(np.degrees(np.arctan2(dmin, hgt)))
            if tilt >= MIN_TILT:
                out.append(dict(name=rest_name(n), normal=np.round(n, 2).tolist(), height=hgt, area=float(area), tilt=tilt))
    return sorted(out, key=lambda r: r['height'])
MIN_TILT = 1.5          # deg: a rest it leaves with less tilt than this is a knife-edge, not a place it stays

def rest_name(n):
    ax = [('upright on its wheels' if LEGS == 'wheels' else 'upright on its tracks', (0, 0, -1)), ('upside down', (0, 0, 1)), ('on its left side', (0, 1, 0)), ('on its right side', (0, -1, 0)),
          ('on its nose', (1, 0, 0)), ('on its tail', (-1, 0, 0))]
    best = max(ax, key=lambda a: np.dot(n, a[1])); ang = np.degrees(np.arccos(np.clip(np.dot(n, best[1]), -1, 1)))
    return best[0] if ang < 12 else best[0] + ', propped %.0f deg' % ang

FRAGILE = ('ball', 'cradle', 'drum', 'base', 'antenna', 'light0', 'light1', 'estop', 'pi', 'hat', 'hailo')
def first_contact(M, n=4000):
    """for falls in n directions (Fibonacci sphere): which part is the robot's extreme point, the first to touch"""
    from scipy.spatial import ConvexHull
    keys = [k for k in M if not M[k].get('ghost')]
    pts, owner = [], []
    for i, k in enumerate(keys):
        p = np.unique(np.round(M[k]['t'].reshape(-1, 3), 1), axis=0); pts.append(p); owner.append(np.full(len(p), i))
    P = np.vstack(pts); O = np.concatenate(owner)
    hv = ConvexHull(P).vertices; P, O = P[hv], O[hv]
    g = np.arange(n) + 0.5; phi = np.arccos(1 - 2 * g / n); th = np.pi * (1 + 5 ** 0.5) * g
    D = np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]
    hit = O[np.argmax(D @ P.T, axis=1)]
    cnt = {}
    for h in hit: cnt[keys[h]] = cnt.get(keys[h], 0) + 1
    by = {}
    for k, v in cnt.items():
        cat = category(k, M[k]); by[cat] = by.get(cat, 0) + v
    frag = {M[k]['label']: round(100 * v / n, 1) for k, v in cnt.items() if k in FRAGILE}
    return dict(by={k: round(100 * v / n, 1) for k, v in sorted(by.items(), key=lambda t: -t[1])}, fragile=frag)

def category(k, v):
    if k in ('ball', 'cradle', 'drum', 'base'): return 'the head'
    if k in FRAGILE: return 'antenna, lights, e-stop'
    if k.startswith(('track_', 'pod_', 'of_', 'cog', 'rollers_')) or v['grp'] == 'legs': return 'wheels and pods' if LEGS == 'wheels' else 'tracks and legs'
    if v['grp'] == 'tpu': return 'TPU bumpers'
    if v['grp'] == 'cage': return 'roll hoops'
    if k.startswith('skirt'): return 'skirts'
    if k.startswith('claw'): return 'claws'
    return 'body shell'

def climb(M, items):
    """tip angles on a slope: where the centre of mass passes the end of the tracks' flat contact ('flat'), and with the
    robot rocking onto the tracks' curved ends, over its side-view outline ('rock')"""
    from scipy.spatial import ConvexHull
    c, m = cog(items)
    tr = feet(M)
    g0 = ground(M); flat = tr[tr[:, 2] < g0 + 0.6]; x0, x1 = flat[:, 0].min(), flat[:, 0].max()
    if LEGS == 'wheels': x0, x1 = W.AXLES['R'], W.AXLES['F']           # on a slope a wheel touches it under its axle
    h = c[2] - g0; yo = (tr[:, 1].max(), tr[:, 1].min())
    keys = [k for k in M if not M[k].get('ghost')]
    P = np.vstack([M[k]['t'].reshape(-1, 3)[:, [0, 2]] for k in keys]); P = P[ConvexHull(P).vertices]
    def rock(sgn):
        for a in np.arange(0, 90.1, 0.25):
            r = np.radians(a) * sgn; Rm = np.array([[np.cos(r), np.sin(r)], [-np.sin(r), np.cos(r)]])
            Q = (P - [c[0], c[2]]) @ Rm.T; low = Q[Q[:, 1] < Q[:, 1].min() + 0.3]
            if (sgn < 0 and low[:, 0].max() < 0) or (sgn > 0 and low[:, 0].min() > 0): return float(a)
        return 90.0
    return dict(cog=[float(c[0]), float(c[1]), float(h)], mass=m, flat=[float(x0), float(x1)],
                up_flat=float(np.degrees(np.arctan2(c[0] - x0, h))), down_flat=float(np.degrees(np.arctan2(x1 - c[0], h))),
                side=float(np.degrees(np.arctan2(min(yo[0] - c[1], c[1] - yo[1]), h))), up_rock=rock(-1), down_rock=rock(1))

def ray_up(T_, x, y):
    """lowest Z where a vertical line at (x, y) meets the triangles T_ (n, 3, 3), or None"""
    a, b, c = T_[:, 0], T_[:, 1], T_[:, 2]
    v0, v1 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2]; v2 = np.array([x, y]) - a[:, :2]
    den = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]; ok = np.abs(den) > 1e-12
    u = np.where(ok, (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / np.where(ok, den, 1), -1)
    v = np.where(ok, (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / np.where(ok, den, 1), -1)
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1)
    if not hit.any(): return None
    z = a[hit, 2] + u[hit] * (b[hit, 2] - a[hit, 2]) + v[hit] * (c[hit, 2] - a[hit, 2])
    return float(z.min())

def belly_profile(M, xs=None):
    """clearance under the body (not the legs) along X: on the centre line, and the lowest point between the tracks"""
    xs = np.arange(-170, 191, 2) if xs is None else xs
    T_ = np.vstack([M[k]['t'] for k in M if not M[k].get('ghost') and M[k]['grp'] != 'legs'])
    yin = (feet(M, 'R')[:, 1].max(), feet(M, 'L')[:, 1].min())
    ys = np.arange(yin[0] + 1, yin[1] - 1, 4.0); out = []; g0 = ground(M)
    for x in xs:
        sel = T_[(T_[:, :, 0].min(1) <= x) & (T_[:, :, 0].max(1) >= x)]
        cen = ray_up(sel, x, YC); low = [z for z in (ray_up(sel, x, y) for y in ys) if z is not None]
        out.append((float(x), None if cen is None else cen - g0, min(low) - g0 if low else None))
    return out

# ---------------------------------------------------------------- the whole robot, sized to its own centre of mass
def assemble():
    M = build(); it = mass_items(M); O, c = outline(M, it)
    for i in range(3):                                                  # the shell moves the centre of mass a little: settle it
        add_shell(M, O); it = mass_items(M); O, c = outline(M, it)
    add_shell(M, O); it = mass_items(M)
    return M, it, O

def before():
    """the control: the tail-arms body (hull.py's parts under the tail-arms carapace), weighed the same way"""
    MB = TA.body(); items = []
    for k, v in MB.items():
        c, vol = centroid(v['t'])
        if k == 'batt':
            t = v['t'].reshape(-1, 3); lo, hi = t.min(0), t.max(0)
            for y in (lo[1] + 22.85, hi[1] - 22.85): items.append(('pack', 300, ((lo[0] + hi[0]) / 2, y, (lo[2] + hi[2]) / 2)))
        elif k in FIXED: items.append((k, FIXED[k], c))
        elif k in ('esc_L', 'esc_R'): items.append((k, 55, c))
        elif k == 'arm_ubec': items.append((k, 40, c))
        elif k.startswith('motor_'): items.append((k, 184, c))
        elif k.startswith('track_'): items.append((k, vol * 1.21e-3 * 0.9, c))
        elif k in ('base', 'drum', 'cradle', 'ball', 'pi', 'hat', 'hailo', 'yaw_servo'): pass
        elif v['grp'] in DENS: items.append((k, vol * DENS[v['grp']] * LUMP.get(k, 1.0), c))
    hb = np.vstack([MB[k]['t'].reshape(-1, 3) for k in ('base', 'ball')]); items.append(('head', 210, (Hm.HX, YC, (hb[:, 2].min() + hb[:, 2].max()) / 2)))
    ps = np.vstack([MB[k]['t'].reshape(-1, 3) for k in ('pi', 'hat')]); items.append(('pi stack', 95, (ps.min(0) + ps.max(0)) / 2))
    items.append(('wiring', 60, (-20, YC, 40)))
    for v in MB.values(): v.setdefault('ghost', False)
    return MB, items

def ends(M):
    """approach and departure angles: the steepest slope the robot meets before the body touches, from the ends of the
    tracks' flat contact"""
    tr = feet(M)
    g0 = ground(M); flat = tr[tr[:, 2] < g0 + 0.6]; x0, x1 = flat[:, 0].min(), flat[:, 0].max()
    P = np.vstack([M[k]['t'].reshape(-1, 3) for k in M if not M[k].get('ghost') and M[k]['grp'] != 'legs'])
    if LEGS == 'wheels':                                                # a ramp tangent to the end wheel, under every body point past it
        def steepest(xa, P_, sgn):
            for a in np.arange(0, 90.01, 0.25):
                r = np.radians(a); n = np.array([-sgn * np.sin(r), np.cos(r)])           # the ramp's upward normal (X, Z)
                if (P_[:, [0, 2]] @ n < n @ [xa, W.Z_A] - W.R_T - 1e-6).any(): return float(a)
            return 90.0
        return steepest(W.AXLES['F'], P[P[:, 0] > W.AXLES['F']], 1), steepest(W.AXLES['R'], P[P[:, 0] < W.AXLES['R']], -1)
    f = P[P[:, 0] > x1]; b = P[P[:, 0] < x0]
    ap = np.degrees(np.arctan2(f[:, 2] - g0, f[:, 0] - x1)).min(); de = np.degrees(np.arctan2(b[:, 2] - g0, x0 - b[:, 0])).min()
    return float(ap), float(de)

def checks(M):
    g = lambda *ks: np.vstack([M[k]['t'] for k in ks])
    legs = [k for k in M if M[k]['grp'] == 'legs']
    HX = Hm.HX + BODY_DX
    sweep = [T(g('cradle', 'ball') - [HX, YC, 0], Rz(a), (HX, YC, 0)) for a in range(0, 360, 30)]     # one copy per angle: summed
    around = g(*[k for k in ('carapace', 'tdeck', 'hoop_f', 'hoop_f_pad', 'brow', 'brow_pad', 'claw0', 'claw1', 'fender0', 'fender1', 'bed', 'grommet0', 'grommet1') if k in M])
    power = ['ubec', 'arm_ubec', 'pca', 'ina219', 'wifi', 'alarm', 'pi_switch', 'esc_L', 'esc_R', 'pack_L', 'pack_R'] + (['motor_L', 'motor_R'] if LEGS == 'v2' else [])
    def pairs(keys, shift={}):
        t = {k: M[k]['t'] + shift.get(k, [0, 0, 0]) for k in keys}
        return float(sum(C.overlap_mm3(t[a], t[b]) for i, a in enumerate(keys) for b in keys[i + 1:]))
    lift = [g('pack_L', 'pack_R') + [0, 0, dz] for dz in range(2, 62, 4)]
    rows = [
        ('Tub vs legs', M['tub']['t'], g(*legs), 'the pods on their pads, the motors in their windows'),
        ('Legs 3 mm inboard (control)', g(*[k for k in legs if k.endswith('_L')]) - [0, 3.0, 0], M['tub']['t'], 'must read > 0'),
        ('Packs, ESCs, UBECs, power parts vs each other', pairs(power), None, ''),
        (('Arm UBEC 12 mm forward (control)', pairs(power, {'arm_ubec': [12.0, 0, 0]}), None, 'must read > 0: it runs into the ESC') if LEGS == 'v1' else
         ('PCA9685 8 mm lower (control)', pairs(power, {'pca': [0, 0, -8.0]}), None, 'must read > 0: it sits 2.5 over the motors')),
        ('All of those vs tub, carapace', g(*power), g('tub', 'carapace'), 'packs on edge in the bays, the rest on the tunnel roof'),
        ('Packs 3 mm lower (control)', g('pack_L', 'pack_R') - [0, 0, 3.0], M['tub']['t'], 'must read > 0: they stand on the bay floor'),
        ('Pi + HAT + Hailo vs tub, PCA, carapace, bed', g('pi', 'hat', 'hailo'), g('tub', 'pca', 'carapace', 'bed'), 'on isolators over the tunnel roof'),
        ('Pi 8 mm lower (control)', g('pi', 'hat', 'hailo') - [0, 0, 8.0], M['tub']['t'], 'must read > 0'),
        ('Head base vs tub, turret deck', M['base']['t'], g('tub', 'tdeck'), 'on the raised nose floor'),
        ('Head base 3 mm lower (control)', M['base']['t'] - [0, 0, 3.0], M['tub']['t'], 'must read > 0'),
        ('Head, 12 pan angles, vs everything round it', sweep, around, 'carapace, front hoop, brow bar, claws, fenders, bed'),
        (('Head 15 mm higher (control)', [t + [0, 0, 15.0] for t in sweep], around, 'must read > 0: the brow bar is that close over it') if LEGS == 'v1' else
         ('Head 15 mm lower (control)', [t - [0, 0, 15.0] for t in sweep], around, 'must read > 0: the turret deck is under it')),
        ('Skirts + fenders vs legs', g('skirt0', 'skirt1', 'fender0', 'fender1'), g(*legs), 'outside the tracks and the outer frames'),
        (('Skirts 10 mm inboard (control)', g('skirt0') - [0, 10.0, 0], g(*legs), 'must read > 0: 7 to 15 mm from the outer frame') if LEGS == 'v1' else
         ('Skirts 15 mm inboard (control)', g('skirt0') - [0, 15.0, 0], g(*legs), 'must read > 0: 12 to 20 mm outside the track')),
        ('Fenders, hoops, brow, carapace, bed vs legs', g('fender0', 'fender1', 'hoop_f', 'hoop_r', 'brow', 'carapace', 'bed'), g(*legs), ''),
        ('Fenders 4 mm lower (control)', g('fender0', 'fender1') - [0, 0, 4.0], g(*legs), 'must read > 0: just over the legs'),
        ('Packs lifted out (every 4 mm to 60) vs the turret deck ring', lift, g('tdeck', 'base'), 'with the carapace and the side lids off'),
        ('The same lift vs the side lids (control)', lift, g('tdeck_lids'), 'must read > 0: the lids do cover them'),
    ]
    if LEGS == 'v2':
        body = g('tub', 'carapace', 'skirt0', 'skirt1', 'fender0', 'fender1')
        bump = g('wheels_L', 'wheels_R', 'arms_L', 'arms_R')
        rows += [('Motors 3 mm lower (control)', g('motor_L', 'motor_R') - [0, 0, 3.0], M['tub']['t'], 'must read > 0: 1.5 over the motor bay floor'),
                 ('Road wheels and arms at full bump (12 up) vs the hull', bump + [0, 0, L2.TRAVEL[0]], body, ''),
                 ('Road wheels 60 up (control)', bump + [0, 0, 60.0], body, 'must read > 0: the fender is over them')]
    out = []
    for what, a, b, why in rows:
        if b is None: v = a
        elif isinstance(a, list): v = sum(C.overlap_mm3(t, b) for t in a)
        else: v = C.overlap_mm3(a, b)
        out.append(dict(what=what, mm3=float(v), why=why)); print('%-55s %9.0f mm3' % (what, v))
    return out

# ---------------------------------------------------------------- pictures
def scene(M, skip=()):
    return [(v['t'], v['rgb'], 0.5 if v['grp'] in ('head', 'tpu') else 0.3) for k, v in M.items()
            if not v.get('ghost') and k not in skip and (v['grp'] != 'elec' or k in ('antenna', 'estop', 'light0', 'light1'))]

def renders(M):
    P = scene(M); names = []
    for fn, cam, foc, lab in (('rugged%s_front.png' % SFX, (820, -760, 430), (10, YC, 90), 'Front 3/4'),
                              ('rugged%s_rear.png' % SFX, (-820, -700, 520), (-10, YC, 100), 'Rear 3/4'),
                              ('rugged%s_side.png' % SFX, (20, -1350, 110), (10, YC, 95), 'Side')):
        IR.render(P, cam, foc, os.path.join(OUT, fn), size=(1300, 860)); names.append((fn, lab))
    IR.render(P, (1400, YC, 95), (0, YC, 95), os.path.join(OUT, 'rugged%s_head_on.png' % SFX), size=(1300, 860)); names.append(('rugged%s_head_on.png' % SFX, 'Head-on: skirts and hoops on one outline'))
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(os.path.join(OUT, n)) for n, _ in names]; w, h = ims[0].size
    sh = Image.new('RGB', (w * 2, h * 2), 'white'); d = ImageDraw.Draw(sh)
    try: f = ImageFont.truetype('arialbd.ttf', 34)
    except Exception: f = ImageFont.load_default()
    for i, (im, (_, lab)) in enumerate(zip(ims, names)):
        x, y = (i % 2) * w, (i // 2) * h; sh.paste(im, (x, y)); d.text((x + 24, y + 18), lab, fill=(30, 33, 30), font=f)
    sh.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, 'rugged%s_sheet.png' % SFX)); print('wrote rugged%s_sheet.png' % SFX)

def headon(M):
    """the head-on outline (every point projected along X), relative to the centre line and the ground"""
    from scipy.spatial import ConvexHull
    P = np.vstack([M[k]['t'].reshape(-1, 3) for k in M if not M[k].get('ghost')])[:, [1, 2]] - [YC, ground(M)]
    h = P[ConvexHull(P).vertices]; return np.vstack([h, h[:1]])

def figures(M, it, O, before_pts, before_cog, bel, belB, before_label='before (tail-arms body)'):
    """the head-on outline that explains the self-righting, and the belly clearance, before and after"""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    c, _ = cog(it); g0 = ground(M)
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw=dict(width_ratios=[1, 1.25]))
    ax = axs[0]
    bp = np.asarray(before_pts); ax.plot(bp[:, 0], bp[:, 1], color='#9AA3AE', lw=1.6, label=before_label)
    h = headon(M); ax.plot(h[:, 0], h[:, 1], color='#C0682B', lw=2.4, label='this robot')
    ax.plot([0], [c[2] - g0], 'o', color='#C0682B', ms=7); ax.plot([0], [before_cog], 'o', color='#9AA3AE', ms=6)
    th = np.linspace(0, 2 * np.pi, 200); hw = corners(M); dc = np.hypot(hw, c[2] - g0)
    ax.plot(dc * np.cos(th), c[2] - g0 + dc * np.sin(th), ':', color='#555', lw=1, label='distance to the track edge')
    ax.axhline(0, color='#333', lw=0.8); ax.set_aspect('equal'); ax.set_xlim(-185, 185); ax.set_ylim(-20, 260)
    ax.set_title('Head-on outline, and the centre of mass (dot)', fontsize=10.5, loc='left'); ax.legend(fontsize=8, loc='center'); ax.grid(alpha=0.25)
    ax.text(-180, 250, 'The outline stays outside the dotted circle and grows\ntowards the top, so it rolls back to the tracks.', fontsize=8.5, va='top')
    ax = axs[1]
    for b, col, lab in ((belB, '#9AA3AE', 'before'), (bel, '#C0682B', 'this robot')):
        x = [p[0] for p in b if p[1] is not None]; y = [p[1] for p in b if p[1] is not None]
        ax.plot(x, y, color=col, lw=2.2 if col != '#9AA3AE' else 1.6, label=lab + ': centre line')
        x2 = [p[0] for p in b if p[2] is not None]; y2 = [p[2] for p in b if p[2] is not None]
        ax.plot(x2, y2, '--', color=col, lw=1.2, label=lab + ': lowest point between the tracks')
    ax.set_xlim(-170, 200); ax.set_ylim(0, 90); ax.set_xlabel('X (mm, forward right)'); ax.set_ylabel('clearance over the ground (mm)')
    ax.set_title('Belly clearance along the robot', fontsize=10.5, loc='left'); ax.legend(fontsize=8, loc='upper left'); ax.grid(alpha=0.25)
    fig.tight_layout(); p = os.path.join(OUT, 'rugged%s_fig.png' % SFX); fig.savefig(p, dpi=110); plt.close(fig); print('wrote', p)

# ---------------------------------------------------------------- page
def page(M, D):
    import base64
    tohex = lambda rgb: int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)
    D['m'] = {}
    for k, v in M.items():
        if v.get('ghost'): continue
        Tk = C.decimate(v['t'], C.faces_for(k)); V, F = C.quant(Tk)
        D['m'][k] = {'v': C.b64(V), 'f': C.b64(F), 'i32': F.dtype == np.uint32, 'c': tohex(v['rgb']), 'grp': v['grp'], 'label': v['label'], 'note': v.get('note', '')}
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')]); D['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist(); D['yc'] = YC
    D['fig'] = base64.b64encode(TA._small(os.path.join(OUT, 'rugged%s_fig.png' % SFX), 1300)).decode()
    if LEGS == 'v2': D['side'] = base64.b64encode(TA._small(os.path.join(OUT, 'legs_v2_side.png'), 1300)).decode()
    tpl = 'rugged_template.html' if LEGS == 'v1' else 'legs_%s_template.html' % LEGS
    html = open(os.path.join(HERE, tpl), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D, default=float) + ';')
    p = os.path.join(OUT, 'rugged.html' if LEGS == 'v1' else 'legs_%s.html' % LEGS); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))

if __name__ == '__main__':
    t0 = time.time()
    M, it, O = assemble(); c, m = cog(it); g0 = ground(M)
    arm = it + [('arm', 300, (AX + BODY_DX, YC, PZ + 60))]
    bel = belly_profile(M)
    between = lambda b, i: min(p[i] for p in b if p[i] is not None and -103 <= p[0] <= 123)
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')])
    D = dict(rests=rest_states(M, it), contact=first_contact(M), climb=climb(M, it), climb_arm=climb(M, arm), ends=ends(M),
             outline=dict(r0=O.r0, top=O.top - g0, width=2 * O.at(O.cz), skirt_ok=bool(O.skirt_ok)), mass=m,
             belly=dict(centre=between(bel, 1), lowest=between(bel, 2)), belly_profile=bel,
             size=dict(L=float(np.ptp(A[:, 0])), W=float(np.ptp(A[:, 1])), H=float(A[:, 2].max() - g0)),
             headon=headon(M).tolist(), cog_og=float(c[2] - g0), legs=LEGS)
    if LEGS == 'v1':                                                    # the control: the tail-arms body
        MB, itB = before(); belB = belly_profile(MB); AB = np.vstack([v['t'].reshape(-1, 3) for v in MB.values() if not v.get('ghost')])
        B = dict(rests=rest_states(MB, itB), contact=first_contact(MB), climb=climb(MB, itB), ends=ends(MB), mass=cog(itB)[1],
                 belly=dict(centre=between(belB, 1), lowest=between(belB, 2)), belly_profile=belB,
                 size=dict(L=float(np.ptp(AB[:, 0])), W=float(np.ptp(AB[:, 1])), H=float(AB[:, 2].max() - ground(MB))),
                 headon=headon(MB).tolist(), cog_og=float(cog(itB)[0][2] - ground(MB)))
        label = 'before (tail-arms body)'
    else:                                                               # the control: the rugged body on the v1 legs
        B = json.load(open(os.path.join(OUT, 'rugged.json'))); label = 'rugged body on the v1 legs'
        D['legs_v2'] = L2.numbers({k: M[k] for k in M}, round(L2.loop_length(L2.circles()) / L2.PITCH)); D['shop'] = L2.SHOP
    for k in ('rests', 'contact', 'climb', 'ends', 'mass', 'belly', 'size') + (('climb_arm',) if LEGS != 'v1' else ()):
        D[k + '_before'] = B[k]
    D['size'].update(L0=B['size']['L'], W0=B['size']['W'], H0=B['size']['H'])
    for k in ('rests', 'rests_before'): print(k, [(r['name'], round(r['tilt'], 1)) for r in D[k]])
    print({k: D[k] for k in ('contact', 'ends', 'ends_before', 'outline', 'belly', 'belly_before', 'size', 'mass', 'mass_before')})
    print('climb', {k: round(v, 1) for k, v in D['climb'].items() if isinstance(v, float)}, 'before', {k: round(v, 1) for k, v in D['climb_before'].items() if isinstance(v, float)},
          'arm', round(D['climb_arm']['up_flat'], 1))
    D['checks'] = checks(M)
    json.dump(D, open(os.path.join(OUT, 'rugged%s.json' % SFX), 'w'), indent=1, default=float)
    figures(M, it, O, B['headon'], B['cog_og'], bel, B['belly_profile'], label)
    if '--no-render' not in sys.argv: renders(M)
    tpl = 'rugged_template.html' if LEGS == 'v1' else 'legs_%s_template.html' % LEGS
    if os.path.exists(os.path.join(HERE, tpl)): page(M, D)
    print('done %.0f s' % (time.time() - t0))
