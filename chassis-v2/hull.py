"""Scorpion hull redesign (brainstorm, 2026-10-04): a new body built round the v1 legs, which bolt on
unmodified, and round everything the robot carries. Supersedes concept.py (which kept Zach's TEST-PRINT-2
body and added covers; he said the body was free to change).

    python chassis-v2/hull.py               # about 2 minutes

Writes chassis-v2/out/: hull.html (the "Scorpion Hull Redesign" page), hull_parts.step (every new part as a
named exact solid, his coordinates, for Fusion), hull_checks.json, hull_sheet.png.

Frame: his Fusion frame, X forward, Y left, Z up, mm. The legs are placed by their screw holes (concept.py)
and then turned 1.82 deg nose-up about the pod's centre, so the tracks run level under a level hull.
Everything else is a concept: numbers marked as guesses on the page.
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import concept as C                       # the legs, the meshes, the checks, the page packing
from concept import cq, load_stl, cq_tris, cyl_tris, box_tris, rbox, T, Rz, YR, YL, YC, FF, OUT

# ---------------------------------------------------------------- fixed by the legs
LEVEL = np.radians(1.82); LEVEL_C = (15.93, 32.4)      # the outer frame's 1.83 deg, taken out at the pods
def level(P):
    P = np.asarray(P, float).copy(); x = P[..., 0] - LEVEL_C[0]; z = P[..., 2] - LEVEL_C[1]
    P[..., 0] = LEVEL_C[0] + x * np.cos(LEVEL) - z * np.sin(LEVEL); P[..., 2] = LEVEL_C[1] + x * np.sin(LEVEL) + z * np.cos(LEVEL)
    return P
POD_HOLES = [(x, z) for x in (-41.56, 9.99, 61.54) for z in (11.4, 53.4)]   # his body's side holes = the pods' inserts

# ---------------------------------------------------------------- the redesign's numbers (guesses unless noted)
WALL = 2.6                                # tub walls and floor
FLOOR0 = 7.4; FLOOR = FLOOR0 + WALL       # floor top 10.0 (ground clearance 26 under it)
TUB_TOP = 57.4                            # the pods' mounting faces are 50 tall (fixed)
TUB_X0 = -136.0                           # rear wall (battery door in it)
HX, HY = 100.0, YC                        # head pan axis, on the hull's centre line now
NOSE_R = 31.0 + 0.6 + WALL                # the tub's nose hugs the well (r 31)
Z0H = FLOOR + 39.4                        # 49.4: the coil base stands on the floor
TDECK = Z0H + 6.6                         # 56.0: turret deck, flush with the well's top
BATT_DX, BATT_DZ = -46.5, 0.2             # packs 46.5 aft of where he drew them: X -99..42, on the floor
TRAY_Z0, TRAY_Z1 = 37.5, 40.0
FENDER = 62.0                             # pods top out at 59.4, tracks at 54.3 (levelled)
DECK = 87.0                               # carapace deck: ESCs (18 tall) fit in the sponsons over the fenders
CAR_X1 = 50.0                             # carapace front face: the cradle's 43.7 sweep needs X <= 56
SPL, SPR = 125.0, -117.5                  # sponson outer faces
SH_X0 = -104.0                            # sponsons end behind the tracks (-102.6)
HATCH = (-98.0, -48.0, 41.0, 55.5)        # X0, Y0, X1, Y1 of the lid over the brain bay
RAIL_X0, RAIL_X1 = -92.0, 34.0
TAIL_CLEVIS = True                        # off when the arm-tail's turntable takes its place
TAIL_PTS = [(-118, DECK + 6), (-134, DECK + 32), (-136, DECK + 64), (-122, DECK + 92), (-97, DECK + 106), (-72, DECK + 102)]

def wp(): return cq.Workplane('XY')
def plan_tub(off=0.0):
    """the tub's plan: the hull of a box (rear wall to X 100, full width) and the circle round the well"""
    from scipy.spatial import ConvexHull
    th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    pts = np.vstack([[[TUB_X0 + off, YR + off], [100, YR + off], [100, YL - off], [TUB_X0 + off, YL - off]],
                     np.c_[HX + (NOSE_R - off) * np.cos(th), HY + (NOSE_R - off) * np.sin(th)]])
    H = pts[ConvexHull(pts).vertices]
    return [tuple(p) for p in H]

def tub():
    o = wp().polyline(plan_tub()).close().extrude(TUB_TOP - FLOOR0).translate((0, 0, FLOOR0))
    o = o.edges('|Z and <X').fillet(10)
    i = wp().polyline(plan_tub(WALL)).close().extrude(TUB_TOP - FLOOR + 1).translate((0, 0, FLOOR))
    o = o.cut(i.edges('|Z and <X').fillet(7.4))
    for side, y in (('L', YL), ('R', YR)):                        # the pods' 6 screws, in the levelled pattern
        for x, z in POD_HOLES:
            px, _, pz = level(np.array([x, 0, z]))
            o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(1.7).extrude(20, both=True).translate((px, y, pz)))
        o = o.cut(wp().box(66, 12, 41, centered=False).translate((-51, y - 6, 3.0)))   # motor window (the can stands 2 mm in)
    o = o.cut(wp().box(8, 101, 27.5, centered=False).translate((TUB_X0 - 1, -47, FLOOR)))   # battery door
    o = o.union(wp().box(141, 3, 10, centered=False).translate((-99, 1.85, FLOOR)))           # spine: the packs' rail
    for y0, y1 in ((YR + WALL, YR + WALL + 3), (YL - WALL - 3, YL - WALL)):                  # tray ledges
        o = o.union(wp().box(141, y1 - y0, 2, centered=False).translate((-99, y0, TRAY_Z0 - 2)))
    o = o.union(wp().box(33.4, YL - YR - 2 * WALL, 2.5, centered=False).translate((TUB_X0 + WALL, YR + WALL, TRAY_Z0)))  # power-bay shelf
    for y0, y1 in ((YR + WALL, YR + WALL + 3), (YL - WALL - 3, YL - WALL)):                  # turret-deck ledges
        o = o.union(wp().box(52, y1 - y0, 2, centered=False).translate((CAR_X1, y0, TDECK - 4.4)))
    for x, y in ((46, HY - 30), (46, HY + 30), (110, HY - 30), (110, HY + 30)):            # inserts for the base's feet
        o = o.union(wp().circle(3.5).extrude(4).translate((x, y, FLOOR)))
    return o.val()

def tray():
    t = wp().box(141, YL - YR - 2 * WALL - 0.6, TRAY_Z1 - TRAY_Z0, centered=False).translate((-99, YR + WALL + 0.3, TRAY_Z0))
    t = t.cut(wp().box(50, 24, 10).translate((-30, 30, TRAY_Z0)))       # wiring slot, Pi to power bay
    t = t.cut(wp().box(20, 30, 10).translate((32, -30, TRAY_Z0)))       # ribbon and servo leads up from the head
    return t.val()

def turret_deck():
    d = wp().polyline(plan_tub(WALL + 0.3)).close().extrude(2.4).translate((0, 0, TDECK - 2.4))
    d = d.intersect(wp().box(200, 300, 20, centered=False).translate((CAR_X1, -150, TDECK - 10)))
    return d.cut(wp().circle(32.4).extrude(10).translate((HX, HY, TDECK - 5))).val()

def fenders():
    out = []
    for y0, y1, sk in ((YL, SPL, SPL - 2.4), (SPR, YR, SPR)):
        f = wp().box(124 - CAR_X1, y1 - y0, 2.4, centered=False).translate((CAR_X1, y0, FENDER))
        f = f.union(wp().box(124 - CAR_X1, 2.4, 12, centered=False).translate((CAR_X1, sk, FENDER - 9.6)))   # skirt
        f = f.union(wp().box(2.4, y1 - y0, 8, centered=False).translate((121.6, y0, FENDER - 5.6)))       # front lip
        out.append(f.edges('|Y and >X').fillet(1.0).val())
    return out

def claws():
    """Bumpers that guard the ball and carry the lights and a ToF window each: a body and an inward pincer."""
    out = []
    def lump(L, W, H, deg, c, r):
        return wp().box(L, W, H).edges().fillet(r).rotate((0, 0, 0), (0, 0, 1), deg).translate(c)
    for s in (1, -1):
        arm = lump(40, 18, 20, -8 * s, (126, HY + s * 50, 33), 5.5)            # from the nose cheek, forward
        palm = lump(16, 26, 20, -8 * s, (148, HY + s * 47, 33), 5.5)           # the hand the jaws grow from
        outer = lump(30, 8, 14, -38 * s, (163, HY + s * 47, 33), 3.5)          # long outer jaw, hooks inward
        inner = lump(16, 7, 12, 22 * s, (158, HY + s * 33, 33), 3.0)           # short inner jaw: the light sits between
        out.append(arm.union(palm).union(outer).union(inner).val())
    return out

def carapace():
    o = wp().box(CAR_X1 - TUB_X0, YL - YR, DECK - TUB_TOP, centered=False).translate((TUB_X0, YR, TUB_TOP))
    for y0, y1 in ((YL, SPL), (SPR, YR)):
        o = o.union(wp().box(CAR_X1 - SH_X0, y1 - y0, DECK - FENDER, centered=False).translate((SH_X0, y0, FENDER)))
    o = o.edges('|X and >Z and (>Y or <Y)').chamfer(7).edges('|Z and <X').fillet(8)
    o = o.cut(wp().box(CAR_X1 - TUB_X0 - 2 * 2.4, YL - YR - 4.8, DECK - TUB_TOP, centered=False).translate((TUB_X0 + 2.4, YR + 2.4, TUB_TOP - 2.4)))
    for y0, y1, out_edge in ((YL, SPL - 2.4, '>Y'), (SPR + 2.4, YR, '<Y')):        # chamfer the outboard edge only:
        o = o.cut(wp().box(CAR_X1 - SH_X0 - 4.8, y1 - y0, DECK - FENDER - 4.8, centered=False).translate((SH_X0 + 2.4, y0, FENDER + 2.4))
                  .edges('|X and >Z and %s' % out_edge).chamfer(5))                 # the ESC needs the full 19.8 inboard
    for yo in (SPL, SPR):                                               # louvres, ESC LED windows
        for i in range(8):
            o = o.cut(wp().box(5, 8, 11).translate((-92 + 15 * i, yo, FENDER + 13)))
        o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(2.5).extrude(10, both=True).translate((-4, yo, FENDER + 16)))
    x0, y0, x1, y1 = HATCH
    o = o.cut(wp().box(x1 - x0 - 6, y1 - y0 - 6, 6, centered=False).translate((x0 + 3, y0 + 3, DECK - 4)))   # brain bay opening
    for x in (-80, -45, -10, 25):                                       # segment grooves across the sponson tops
        for yy0, yy1 in ((YL - 2, SPL - 10), (SPR + 10, YR + 2)):
            o = o.cut(wp().box(2, yy1 - yy0, 2, centered=False).translate((x, yy0, DECK - 1)))
    for y, wd in ((-44, 16), (-24, 16), (28, 10), (42, 10)):           # charge + balance ports, back panel
        o = o.cut(wp().box(6, wd, 8, centered=False).translate((TUB_X0 - 1, y, 62)))
    for y in (-8, 6):                                                   # ESC LED light pipes, back panel
        o = o.cut(wp().workplane().transformed(rotate=(0, 90, 0)).circle(2).extrude(8).translate((TUB_X0 - 1, y, 76)))
    for y in ((YC - 19.5, YC + 15.5) if TAIL_CLEVIS else ()):          # tail clevis: cheeks outside the 30-wide root
        o = o.union(wp().box(18, 4, 6, centered=False).translate((-127, y, DECK)))
        o = o.union(cq.Workplane('XZ').circle(9).extrude(-4).translate((-118, y, DECK + 6)))
    return o.val()

def hatch():
    x0, y0, x1, y1 = HATCH
    h = wp().box(x1 - x0, y1 - y0, 2.4, centered=False).translate((x0, y0, DECK)).edges('|Z').fillet(6)
    for i in range(9):
        h = h.cut(wp().box(4, 44, 6).translate((-50 + 9 * i, PI_C[1], DECK)))   # vents over the Pi
    return h.val()

def rail():
    prof = [(-8, 0), (8, 0), (8, 3), (10.6, 5.6), (8, 8.2), (8, 9.5), (-8, 9.5), (-8, 8.2), (-10.6, 5.6), (-8, 3)]
    r = cq.Workplane('YZ').polyline(prof).close().extrude(RAIL_X1 - RAIL_X0).translate((RAIL_X0, YC, DECK + 2.4))
    for i in range(int((RAIL_X1 - RAIL_X0 - 6) / 10)):
        r = r.cut(wp().box(5.35, 30, 3, centered=False).translate((RAIL_X0 + 4 + 10 * i, YC - 15, DECK + 8.9)))
    return r.val()

def tail():
    segs = []
    for i in range(len(TAIL_PTS) - 1):
        (x0, z0), (x1, z1) = TAIL_PTS[i], TAIL_PTS[i + 1]
        L = np.hypot(x1 - x0, z1 - z0) + 8; ang = np.degrees(np.arctan2(z1 - z0, x1 - x0)); W = 30 - 3.2 * i; H = 26 - 2.6 * i
        s = wp().box(L, W, H).edges().fillet(min(W, H) * 0.42).rotate((0, 0, 0), (0, 1, 0), -ang).translate(((x0 + x1) / 2, YC, (z0 + z1) / 2))
        segs.append(s.val())
    pins = [cq.Workplane('XZ').circle(4).extrude(-(34 - 3 * i)).translate((x, YC - (34 - 3 * i) / 2, z)).val() for i, (x, z) in enumerate(TAIL_PTS[:-1])]
    x0, z0 = TAIL_PTS[-1]
    sting = [wp().sphere(13).translate((x0, YC, z0)).val(), cq.Solid.makeCone(7, 0.8, 26, cq.Vector(x0 + 8, YC, z0 - 3), cq.Vector(0.93, 0, -0.36))]
    return segs, pins, sting

COMP = {  # key: (label, centre, size, note)   * = guess
    'esc_L': ('ESC, left (INJORA brushed)', (-18, YL + 24.5, FENDER + 2.4 + 9.0), (34, 46, 18), 'In the sponson right over its motor: 60 mm of motor lead. LED shows through the side window. Size* 46 x 34 x 18.'),
    'esc_R': ('ESC, right (INJORA brushed)', (-18, YR - 24.5, FENDER + 2.4 + 9.0), (34, 46, 18), 'Mirror of the left. Size* 46 x 34 x 18.'),
    'ubec': ('UBEC 5 V / 5 A (Pi only)', (-108, -27, 66), (45, 26, 12), 'Power bay. Size* 45 x 26 x 12.'),
    'ina219': ('INA219 pack monitor', (-110, 30, 62), (26, 21, 4), 'Jumper it off 0x40 (the PCA9685 has it).'),
    'alarm': ('LiPo alarm (balance lead)', (-129, 10, 72), (8, 40, 14), 'Buzzer and LEDs at the back panel.'),
    'pi_switch': ('Pi power switch', (-129, -40, 72), (8, 20, 13), 'Inline on the UBEC input.'),
    'wifi': ('USB WiFi + RP-SMA', (-112, 44, 77), (40, 18, 10), 'Its antenna is in the tail.'),
}
PI_C = (-15.0, -3.0); PCA_C = (-8.9, 42.8, 42.95)

def build():
    t0 = time.time(); M = {}
    def add(k, tris, label, group, color, note='', ex=(0, 0, 0), ghost=False):
        M[k] = dict(t=np.asarray(tris, float), label=label, group=group, color=color, note=note, ex=ex, ghost=ghost)
    S = {}                                    # exact solids for the STEP
    def addS(k, solid, *a, **kw):
        S[k] = solid; add(k, cq_tris(solid), *a, **kw)
    L = C.legs()
    LEG = 'Yours, unmodified (v1 leg parts)'
    for s_, dy in (('L', 70), ('R', -70)):
        nm = 'left' if s_ == 'L' else 'right'
        for k, lab, col, note, f in (('pod_', 'Track pod, ' + nm, 0x2B2F33, LEG + '. Bolts on with its 6 v1 screws; the hull carries the hole pattern turned 1.82 deg so the tracks run level.', 1.0),
                                     ('of_', 'Outer frame, ' + nm, 0x34393E, LEG + '.', 1.4), ('track_', 'TPU track, ' + nm, 0x1E2124, 'Luengoa flex track (CC BY-NC), drawn tight round sprockets and rollers.', 1.2),
                                     ('cog_rear_', 'Rear drive sprocket, ' + nm, 0xE8A33A, LEG + '.', 1.2), ('cog_front_', 'Front idler sprocket, ' + nm, 0xE8A33A, LEG + '.', 1.2),
                                     ('rollers_', 'Road and return rollers, ' + nm, 0xE8A33A, LEG + '.', 1.3), ('crown_', '4:1 crown gear, ' + nm, 0xC9CDD2, '', 1.1),
                                     ('motor_', 'Drive motor, ' + nm + ' (INJORA 540 55T)', 0x8A8F96, 'In the pod as v1; stands 2 mm into the hull through a window. Can 36 x 52*.', 1.0),
                                     ('pinion_', '4:1 pinion, ' + nm, 0xC9CDD2, '', 1.0)):
            add(k + s_, level(L[k + s_]), lab, 'legs', col, note, (0, dy * f, 0))
    addS('tub', tub(), 'Tub (new): the hull\'s lower half', 'hull', 0x7C8C7A,
         'Floor, walls and nose in one print (272 x 132 x 50). Flat pads take the pods\' 12 screws; the nose hugs the head\'s well; a spine guides the packs out the back door.')
    addS('tray', tray(), 'Brain tray (new)', 'hull', 0x6F86A3, 'Drops onto ledges over the packs. Pi + Hailo and the PCA9685 ride on it; lifts out as one.', (0, 0, 40))
    addS('tdeck', turret_deck(), 'Turret deck (new)', 'hull', 0x6E7E6C, 'Low deck round the well, flush with its top, inside the tub\'s rim.', (0, 0, 60))
    for i, f in enumerate(fenders()):
        addS('fender%d' % i, f, 'Front fender (new)', 'hull', 0x6E7E6C, 'Over the front half of the track, 2.6 over the pod, 7.7 over the track.', (0, 40 * (1 if i == 0 else -1), 40))
    for i, c in enumerate(claws()):
        addS('claw%d' % i, c, 'Claw (new)', 'hull', 0x55606B, 'Bumper and pincer: the jaws reach 40 mm past the ball, so a wall meets them first. A light / IR pod sits between the jaws.', (40, 0, 0))
    addS('carapace', carapace(), 'Carapace (new)', 'hull', 0x7C8C7A,
         'Raised hull behind the head: sponsons over the tracks hold the ESCs over their motors, the centre is the brain bay, the back is the power bay with the ports. Screws to the tub.', (0, 0, 100))
    addS('hatch', hatch(), 'Brain hatch (new)', 'hull', 0x6E7E6C, 'Lifts off (magnets) to reach the Pi without touching anything else. Vents over the Pi.', (0, 0, 135))
    for i, s in enumerate(cq_ls for cq_ls in (wp().workplane().transformed(rotate=(0, 90, 0)).circle(6).extrude(6).translate((154, HY + sg * 42, 33)).val() for sg in (1, -1))):
        add('light%d' % i, cq_tris(s), 'Light / IR pod', 'elec', 0xF2F2E6, '', (40, 0, 0))
    segs, pins, sting = tail()
    for i, s in enumerate(segs):
        addS('tail%d' % i, s, 'Tail segment %d (new)' % (i + 1), 'tail', 0x7C8C7A, 'Hollow; the antenna lead runs inside. Pinned joints, so it folds flat.', (-40, 0, 120))
    add('tailpins', np.vstack([cq_tris(p) for p in pins]), 'Tail joint pins', 'tail', 0x3A3F44, '', (-40, 0, 120))
    add('stinger', np.vstack([cq_tris(s) for s in sting]), 'Stinger: antenna radome', 'tail', 0xD9622B, 'Printed plastic passes WiFi: the antenna sits 100 mm over the deck.', (-40, 0, 120))
    (xa, za), (xb, zb) = TAIL_PTS[-3], TAIL_PTS[-1]
    add('antenna', cyl_tris((xa, YC, za), (xb, YC, zb), 4.0), 'WiFi antenna', 'elec', 0x222222, '', (-40, 0, 120))
    add('estop', np.vstack([cq_tris(wp().circle(11).extrude(10).translate((-120, YR + 18, DECK)).val()),
                            cq_tris(wp().circle(14).extrude(7).translate((-120, YR + 18, DECK + 10)).edges('>Z').fillet(3).val())]),
        'E-stop (cuts both ESC feeds)', 'elec', 0xC62828, 'On the rear deck; the Pi stays up.', (0, 0, 100))
    for k, (lab, c, sz, note) in COMP.items():
        add(k, cq_tris(rbox(c, sz)), lab, 'elec', 0x2F5FB0 if k.startswith('esc') else 0x3C9A4C, note, (0, 0, 100) if k.startswith('esc') else (-60, 0, 60))
    bl, br = load_stl(FF + 'LeftBattery.stl'), load_stl(FF + 'RightBattery.stl')
    add('batt', np.vstack([bl, br]) + [BATT_DX, 0, BATT_DZ], '2 x Zeee 2S 5200 LiPo', 'elec', 0xE0B040,
        'Your model\'s boxes, 46.5 aft of where you drew them, on the floor either side of the spine. They slide out the back door.', (-175, 0, 0))
    C.PI_C, C.PCA_C = PI_C, PCA_C
    PP = C.pi_parts()
    add('pi', PP['pi'], 'Raspberry Pi 5 + active cooler', 'elec', 0x3C9A4C, 'Your model, USB/Ethernet aft. Its front edge is 15 mm from the head base: a short ribbon.', (0, 0, 70))
    add('hat', PP['hat'], 'M.2 HAT+', 'elec', 0x2E7D32, 'Over the cooler on 16 mm* standoffs.', (0, 0, 80))
    add('hailo', PP['hailo'], 'Hailo-8L (M.2 2242)', 'elec', 0x111111, '', (0, 0, 80))
    add('pca', PP['pca'], 'PCA9685 (Adafruit model)', 'elec', 0x1F4FA0, 'Beside the Pi: short I2C, short leads to the head and the ESCs.', (0, 0, 70))
    G = C.G
    base = np.vstack([C.tri_obj(os.path.join(G, n + '.obj')) for n in ('well', 'bay', 'floor', 'gear_in', 'servo')])
    turn = np.vstack([C.tri_obj(os.path.join(G, n + '.obj')) for n in ('drum', 'gear_out', 'bearing')])
    add('base', T(base, Rz(180), (HX, HY, Z0H)), 'Pan coil base (turned 180)', 'head', 0x7A90AC, 'Stands on the floor, 4 feet into inserts; the gear bay points aft, over nothing.', (0, 0, 90))
    add('drum', T(turn, None, (HX, HY, Z0H)), 'Drum + bearing', 'head', 0xC9763A, '', (0, 0, 120))
    add('cradle', T(C.tri_obj(C.FORK), None, (HX, HY, Z0H)), 'Cradle', 'head', 0xD49A4A, '', (0, 0, 135))
    add('ball', T(np.vstack([load_stl(p) for p in C.BALL]), None, (HX, HY, Z0H)), 'Ball (your rev 2)', 'head', 0x4F7FBF, '', (0, 0, 135))
    add('res_sweep', cyl_tris((HX, HY, Z0H + 10.5), (HX, HY, Z0H + 72.5), 43.7, 64), 'Kept clear: the head\'s 360 sweep (r 43.7)', 'reserved', 0xF0B27A, '', (0, 0, 135), ghost=True)
    add('old_body', load_stl(FF + 'Tank_body.stl'), 'Your TEST-PRINT-2 body, for comparison', 'orig', 0x9AA3AE, '', ghost=True)
    print('built %d meshes in %.0f s' % (len(M), time.time() - t0))
    return M, S

def checks(M):
    g = lambda *ks: np.vstack([M[k]['t'] for k in ks])
    legs = [k for k in M if M[k]['group'] == 'legs']
    legsL = [k for k in legs if k.endswith('_L')]; legsR = [k for k in legs if k.endswith('_R')]
    sweep = [T(g('cradle', 'ball') - [HX, HY, 0], Rz(a), (HX, HY, 0)) for a in range(0, 360, 30)]
    around = g('carapace', 'fender0', 'fender1', 'claw0', 'claw1', 'hatch', 'tdeck', 'light0', 'light1')
    drawer = M['batt']['t'] - [170.0, 0, 0]
    power = ['ubec', 'ina219', 'alarm', 'pi_switch', 'wifi']
    rows = [
        ('Left leg vs tub', g(*legsL), M['tub']['t'], 'pods flat on the pads; motors through their windows'),
        ('Right leg vs tub', g(*legsR), M['tub']['t'], ''),
        ('Left leg 3 mm inboard (control)', g(*legsL) - [0, 3.0, 0], M['tub']['t'], 'must read > 0'),
        ('Legs vs fenders + carapace + claws', g(*legs), g('fender0', 'fender1', 'carapace', 'claw0', 'claw1'), ''),
        ('Carapace 6 mm lower vs legs (control)', M['carapace']['t'] - [0, 0, 6.0], g(*legs), 'must read > 0'),
        ('Head base vs tub, tray, turret deck', M['base']['t'], g('tub', 'tray', 'tdeck'), 'stands on the floor'),
        ('Head base 3 mm lower (control)', M['base']['t'] - [0, 0, 3.0], M['tub']['t'], 'must read > 0'),
        ('Head base vs packs', M['base']['t'], M['batt']['t'], ''),
        ('Head, 12 pan angles, vs everything round it', sweep, around, 'each angle checked on its own'),
        ('Head, 12 pan angles, 20 mm lower (control)', [t - [0, 0, 20.0] for t in sweep], around, 'must read > 0'),
        ('Packs vs tub, tray, legs', M['batt']['t'], g('tub', 'tray', *legs), ''),
        ('Packs slid out the back vs tub, carapace', drawer, g('tub', 'carapace'), 'the battery drawer works'),
        ('Packs slid out, 3 mm higher (control)', drawer + [0, 0, 3.0], g('tub', 'carapace'), 'must read > 0'),
        ('Pi + HAT + PCA vs tub, tray, carapace, hatch', g('pi', 'hat', 'hailo', 'pca'), g('tub', 'tray', 'carapace', 'hatch'), ''),
        ('Pi raised 20 mm (control)', g('pi', 'hat', 'hailo') + [0, 0, 20.0], g('carapace', 'hatch'), 'must read > 0: 15.9 of air over the stack'),
        ('ESCs vs carapace', g('esc_L', 'esc_R'), M['carapace']['t'], 'in the sponsons'),
        ('ESCs 3 mm higher (control)', g('esc_L', 'esc_R') + [0, 0, 3.0], M['carapace']['t'], 'must read > 0'),
        ('Power bay parts vs tub + carapace', g(*power), g('tub', 'carapace'), ''),
        ('Claws vs ball + tracks', g('claw0', 'claw1'), g('ball', 'track_L', 'track_R'), ''),
        ('Tail vs hatch + carapace', g('tail0', 'tail1', 'tail2', 'tail3', 'tail4', 'stinger'), g('hatch', 'carapace'), ''),
    ]
    out = []
    for what, A, B, why in rows:
        v = sum(C.overlap_mm3(t, B) for t in A) if isinstance(A, list) else C.overlap_mm3(A, B)   # copies one by one: the voxel parity cancels where stacked copies overlap
        out.append(dict(what=what, mm3=v, why=why)); print('%-52s %9.0f mm3' % (what, v))
    return out

def sizes(M):
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v['ghost']]); lo, hi = A.min(0), A.max(0)
    ground = np.vstack([M['track_L']['t'], M['track_R']['t']]).reshape(-1, 3)[:, 2].min()
    tail = np.vstack([M[k]['t'].reshape(-1, 3) for k in M if k.startswith('tail') or k == 'stinger'])
    vol_tub = (100 - TUB_X0) * (YL - YR) * (TUB_TOP - FLOOR0) + np.pi * NOSE_R ** 2 / 2 * (TUB_TOP - FLOOR0)
    vol_car = (CAR_X1 - TUB_X0) * (YL - YR) * (DECK - TUB_TOP) + 2 * (CAR_X1 - SH_X0) * 54 * (DECK - FENDER)
    return [('Length, claws to tail', '%.0f mm' % (hi[0] - lo[0])), ('Width over the sponsons', '%.0f mm' % (hi[1] - lo[1])),
            ('Height to the ball / stinger', '%.0f / %.0f mm' % (M['ball']['t'].reshape(-1, 3)[:, 2].max() - ground, tail[:, 2].max() - ground)),
            ('Turret deck / carapace deck', '%.0f / %.0f mm' % (TDECK - ground, DECK - ground)),
            ('Ground clearance', '%.0f mm' % (FLOOR0 - ground)), ('Track gauge', '188 mm (fixed by the legs)'),
            ('Room inside (tub + carapace)', '%.1f L (yours: 1.4)' % ((vol_tub + vol_car) / 1e6)),
            ('Lens height vs before', '%.0f mm (was %.0f)' % (Z0H + 52 - ground, 79.4 + 52 - ground))]

def page(M, Cks):
    import base64
    D = {'m': {}, 'checks': Cks, 'sizes': sizes(M), 'yc': YC}
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v['ghost']]); D['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist()
    for k, v in M.items():
        Tk = C.decimate(v['t'], C.faces_for(k)); V, F = C.quant(Tk)
        D['m'][k] = {'v': C.b64(V), 'f': C.b64(F), 'i32': F.dtype == np.uint32, 'c': v['color'], 'grp': v['group'],
                     'label': v['label'], 'note': v['note'], 'ex': list(v['ex']), 'ghost': v['ghost']}
    html = open(os.path.join(HERE, 'hull_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D) + ';')
    p = os.path.join(OUT, 'hull.html'); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))

def step(S):
    a = cq.Assembly()
    for k, s in S.items(): a.add(cq.Shape(s.wrapped) if hasattr(s, 'wrapped') else s, name=k)
    p = os.path.join(OUT, 'hull_parts.step'); a.save(p); print('wrote', p)

if __name__ == '__main__':
    M, S = build()
    np.savez_compressed(os.path.join(OUT, '_hull_meshes.npz'), **{k: v['t'] for k, v in M.items()})
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != 't'} for k, v in M.items()}, open(os.path.join(OUT, '_hull_meta.json'), 'w'))
    Cks = checks(M); json.dump(Cks, open(os.path.join(OUT, 'hull_checks.json'), 'w'), indent=1)
    if os.path.exists(os.path.join(HERE, 'hull_template.html')): page(M, Cks)
    step(S)
