"""Pan coil for variant B: a rolling loop in a flat can, sunk in the stump, 360 deg of pan.

The item tree-parts-b/HANDOFF.md left open as section 0.3. Sized from the brief in
../pan-coil-360-brief.md, which carries the reasoning; this file carries the geometry.

Differences from variant C's pan_coil.py, and why:

  * the pan servo is OFF-AXIS, driving a 2:1 step-up. That is what lets the drum shrink
    from r 21.5 to r 12 -- travel goes as 1/r_inner, so a small drum buys turns per mm of
    ribbon. Can outside diameter drops 60 -> 40 and the coil spends 70 mm instead of 115.
  * the servo therefore sits BESIDE the can at deck level, not inside it, and only the
    gear plane is below the can floor. Stump depth 31 mm, not the 47 a servo-under-the-can
    bay would have cost.
  * the ribbon rises ON AXIS above the drum's flange: below the flange the barrel is solid
    down to the gear, above it the hub is a bore. A FIXED lid cannot be crossed by a ribbon
    at a rotating radius, so the drum's own flange is the chamber's top cover -- the same
    conclusion pan_coil.py reached with its thrust flange.

  travel (rad) = L * (1/ri + 1/ro)     L = ribbon length inside the can

Frame: mm, Z 0 at the deck top, pan axis at the origin, X forward. Matches tree_parts_b.

    python pan_coil_b.py [part ...]
"""
import os, json, base64
import numpy as np
from skimage import measure
import tree_parts as A
from tree_parts import (smin, box, rbox, _cyl, cyl_z, U, ring_z, sample, project,
                        decimate, report, quiet)

OUT = os.path.join(A.D, '..', 'pan-coil-b')

# ------------------------------------------------------------------ the ribbon
RIBBON_W = 16.0                    # MEASURED 2026-09-18
RIBBON_T = 0.2                     # Zach, "two sheets of paper" -- ASSUMED, wants calipers
DRAW_T = 0.6                       # the coil is DRAWN this thick so it renders; it is 0.2
MIN_BEND_R = 10 * RIBBON_T         # 2.0

# ------------------------------------------------------------------ the can
DRUM_R = 12.0                      # coil face: bore 18 for the twist + 3 wall, once the
                                   # ribbon rises on axis rather than through the barrel
GAP = 6.0
WELL_IR = DRUM_R + GAP             # 18.0  -> cavity 36
WELL_OR = WELL_IR + 2.0            # 20.0  -> can 40
CLR = 0.25
RI = DRUM_R + RIBBON_T / 2 + CLR   # 12.35  inner layer centreline
RO = WELL_IR - RIBBON_T / 2 - CLR  # 17.65  outer layer centreline
U_R = (RO - RI) / 2                # 2.65   -- against MIN_BEND_R 2.0
L_CAN = 70.0                       # ribbon inside the can
TRAVEL = L_CAN * (1 / RI + 1 / RO) # rad -- 540 deg of mechanism, software limited to 360

CH_Z0, CH_Z1 = -20.0, -2.0         # chamber
BAND_Z0, BAND_Z1 = -19.0, -3.0     # where the 16 mm ribbon sits

# ---- the tilt servo's wires: their own lane under the ribbon (round 2, 2026-10-02) ----------
# Taped to the ribbon, the servo lead spoilt its fold (Zach). The wires (three Dupont jumpers, see
# tree_parts_b.WIRE_*) come down the drum's bore beside the ribbon, down a hole in the drum's core, and
# roll in a lane of their own below the ribbon, under a fixed shelf the ribbon now sits on. The lane
# has its own wall at r 21, past the ribbon's 18: a 9 mm gap, so the moving U is ~3.6 mm radius, not
# ~2 (Zach OK'd). The floor drops 4.3; the bay's roof under the can was 7.6 thick, so the gears, the
# servo and the floor plate stay where they are. They leave through a boss at -135 deg, clear of the
# ribbon's slot at -90.
WIRE_L = 74.0                      # wire length to leave in the lane: the same 540 deg of travel as the
                                   # ribbon, TRAVEL / (1/12.85 + 1/20.25)
SHELF_T = 0.8
LANE_H = 3.5                       # a ~2.8 bundle of three ~1.3 jumper wires
LANE_Z1 = CH_Z0 - SHELF_T          # -20.8: the shelf's underside
LANE_Z0 = LANE_Z1 - LANE_H         # -24.3: the lane's floor
LANE_ZC = (LANE_Z0 + LANE_Z1) / 2
LANE_R = 21.0                      # the lane's outer wall
LANE_WALL = 2.0
SHELF_R0 = DRUM_R + 0.6            # the shelf stops 0.6 off the turning drum
DRUM_LIFT = 0.4                    # the drum's bottom face stands this far off the lane's floor
FLOOR_Z = LANE_Z0 - 2.0            # -26.3 (was -22.0)
WIRE_R = 2.5                       # holes: a bare Dupont pin beside two wires (as in the cradle)
WIRE_EXIT_DEG = -145.0            # the boss's near corner stays 3 mm off the ribbon's slot (|X| 8.8)

# ------------------------------------------------------------- above the deck
# FLANGE_R was 19.6 and ploughed 270 mm3 through the deck ring, which starts at 19.0.
# Zach saw the servo clash by eye; the check written afterwards found this one too.
FLANGE_R = 17.7                    # the drum's own top cover, 0.3 inside the cup wall
DECK_IR = 19.0                     # deck plate inner radius, 1.3 clear of the flange
DECK_Z0, DECK_Z1 = -2.4, -0.4      # 0.4 of axial air under the rotating hub
BORE_R = 9.0                       # 18 bore: the twist run, rule 3
HUB_R = 22.5                       # 6809 bearing ID
BRG_OR = 29.0                      # 6809 45 x 58 x 7
# The bearing had NO SHOULDER. Its outer race now rests on the deck ring's top face and the
# mating disc's underside bears down on the inner race, so the load path is
#   drum -> disc -> inner race -> balls -> outer race -> well ledge.
# Before this the inner race had nothing under it at r 22.5..26 and would have dropped 0.4 mm
# onto the FIXED deck ring -- a rotating race grinding on a stationary part.
BRG_Z0 = DECK_Z1                   # -0.4
BRG_Z1 = BRG_Z0 + 7.0              # 6.6
BOSS_R = 31.0
# ---- bearing fits and the inner-race relief (2026-09-27, before set 2 printed) --------------
# Both fits were drawn at exactly the 6809's size. The 6704 tilt seats' precedent (tree_parts.py
# BRG_OD 27.1 for 27.0, HUB_R 9.95 for 20.0): seat +0.1 on the diameter, hub -0.1.
SEAT_BORE_R = BRG_OR + 0.05        # 29.05
HUB_FIT_R = HUB_R - 0.05           # 22.45
# The deck ring's top face ran solid from r 19 to 31, under BOTH races: the inner race turns with
# the drum and was pressed onto a fixed face by the drum's own weight. Relieved 0.4 deep out to
# r 26.0 -- between the inner race's shoulder (d1 ~49.6) and the outer's (D1 ~53.5) -- so only
# the outer race lands on the ledge.
RELIEF_R0, RELIEF_R1, RELIEF_D = WELL_OR + 0.5, 26.0, 0.4

# ---- the merge interface with tree_parts_b -------------------------------------------
# The nest (variant B's fork) presents a FLAT underside at BASE_Z with a Ø51 base disc, and
# it used to land on `roots` and a pan horn. In the merged part `roots` is gone: the drum
# carries a matching disc and the nest bolts straight to it. Taken from tree_parts.py, not
# retyped -- these numbers move if that file moves.
BASE_Z, MATE_R = A.BASE_Z, A.PED_R           # 10.5 nest underside, 25.5 its base radius
MATE_SCREW_R, MATE_SCREWS = 20.0, [0.0, 120.0, 240.0]
M3_PILOT = 1.25
BALL_UNDER = 21.3                  # tree_parts_b: H 52.0 - R_BALL 30.7

TWIST_NEED = 40.0                  # ~40 mm of run per 90 deg for a 16 mm ribbon
TWIST_HAVE = BALL_UNDER            # from the flange top (Z 0) to the ball's underside

# ------------------------------------------------------------------ the drive
# ---- second support, because one bearing is not enough --------------------------------
# 159.6 g rotating with its CG 46.1 mm above the deck (measured off the variant B meshes,
# plus servo/camera/bearings). Static tipping is only 4.6 N.mm, so strength is not the
# question -- ANGULAR COMPLIANCE is. A single 6809 resists tilt over its 7 mm width, so
# 0.10 mm of printed seat slop becomes 1.64 deg and 2.27 mm of sway at the top of the ball.
# Running the barrel in a journal 24 mm lower takes the same slop to 0.48 deg and 0.66 mm.
BARREL_R = 5.0
JOURNAL_R = BARREL_R + 0.25        # 5.25 bore around the 10 mm barrel
JOURNAL_Z0 = -30.9                 # 0.5 above the output gear (G_Z1 -31.4); 6.6 of journal since the lane
N_OUT, N_IN = 20, 40               # 2:1 step-up
CENTRE = 31.0                      # set by the servo clearing the can, not by the gears
R_OUT_G = CENTRE * N_OUT / (N_OUT + N_IN)   # 10.33
R_IN_G = CENTRE - R_OUT_G                   # 20.67
TOOTH = 1.0
# The pair was drawn at exactly CENTRE = R_OUT_G + R_IN_G: teeth touching both flanks at every
# angle, 0.0 deg of free play, and printed parts come out fat. All the gap goes on the small gear
# so a printed set-1 input gear still meshes. 0.3 -> 1.9 deg of drum play as drawn (0.1 -> 0,
# 0.2 -> 1.2), expected to print tighter. Measured by pan_coil_b_check.gear_play().
GEAR_GAP = 0.3

# The servo lies with its LONG axis along Y. The tabs stick out at the ends of that axis
# (TAB_SPAN is measured along it), and with the body along X the far tab tip landed at
# X 20.25 -- 0.25 mm outside the cup. Turned 90 deg it clears by 4.9.
# The pan servo is Zach's MG90S model (2026-09-28, "been using this it matches well"; the file is
# head-v2/generator/pan-coil-b/MG90S.3MF), not the datasheet numbers in tree_parts.
SW, SL, S2S = 12.2, 23.0, 6.1                                   # case width, length, shaft-end -> shaft axis
TAB_SPAN, TAB_FROM_TOP, TAB_PITCH = 33.0, 1.9, 26.86            # tab face nearest the shaft, from the case face
TAB_T = 3.0                                                     # MEASURED by Zach 2026-09-18 (his model: 2.5)
FIT, M2_PILOT, M2_CLEAR, M2_HEAD = A.FIT, A.M2_PILOT, A.M2_CLEAR, A.M2_HEAD
HORN_L, HORN_W, HORN_C, HORN_D = A.HORN_L, A.HORN_W, A.HORN_C, A.HORN_D   # GENERIC -- see below
HORN_ROOF = 1.5                    # material between the screw head and the horn
# Zach, 2026-09-27: "servo does not fit in there". The datasheet box used its LENGTH (22.8) as its
# height and had nothing past the case face. His MG90S has a 15 x 12.2 block 6.0 tall on the shaft end
# of the case face and the shaft 10.0 past the face, so the gear plane sits 0.5 under the block: the
# drum's barrel and the gear bay grew 5.6 (set 3). The gears themselves keep their shape.
SV_CASE = 22.4                     # case, face -> far end
SV_HUMP_L, SV_HUMP_H = 15.0, 6.0   # the block on the case face, from the shaft end, full width
SV_SHAFT_R, SV_SHAFT = 2.325, 10.0 # output shaft, case face -> tip
SV_Z1 = DECK_Z0 - 0.1              # body top, tucked under the deck plate
SV_Z0 = SV_Z1 - SV_CASE            # -24.9: the case face, pointing DOWN
SV_X0, SV_X1 = CENTRE - SW / 2, CENTRE + SW / 2                 # 24.9 .. 37.1
SV_Y0, SV_Y1 = -S2S, SL - S2S                                   # -5.9 .. 16.9
SV_YC = (SV_Y0 + SV_Y1) / 2                                     # 5.5, the tab centre
TAB_Z0 = SV_Z0 + TAB_FROM_TOP      # -23.0, the shelf the tabs land on
# The +Y tab had nothing under it: the servo slides in through that end, so its M2 pilot was cut in
# air (found 2026-09-29, in set 2 as well). A separate tab block slides in through the window after the
# servo, on two rails in grooves in the pocket's side walls, and stops under the tab; the tab's own
# M2 x 6 then drives down through the tab into it. Rails at the bottom, so it prints flat.
TB_Y0 = SV_Y1 + 0.3                # 17.2: 0.3 off the case end
TB_Y1 = SV_YC + TAB_SPAN / 2 + 2.0 # 23.9: just inside the tower's end
TB_H, TB_RAIL_H, TB_RAIL = 5.0, 4.0, 1.5   # block height under the tab; rails: height, reach into each wall
TB_SLIDE = 0.15                    # per side, in the channel and in the grooves (the slide rule)
G_Z1 = SV_Z0 - SV_HUMP_H - 0.5                                  # -31.4: 0.5 under the block
G_Z0 = G_Z1 - 6.0                                               # -37.5
BAY_Z0 = G_Z0 - 2.0                                             # -33.5

# ---- how it goes together (2026-09-27) --------------------------------------------------
# Zach asked how the drum's gear gets in, and it couldn't: moulded on the drum it was 22.6
# across and had to pass the 10.5 journal and the bay's 17.2 top hole, and the bay was a
# closed box the 43.3 input gear couldn't enter either. Every seated check read zero. Now:
#   * the small gear is its own part, pushed up onto a D-shaped seat on the barrel's end from
#     below and held by one M3 x 8 button head screw up the axis;
#   * the bay's floor is a separate plate on 4 x M2 x 6, so both gears go in from below;
#   * the well and the bay print as ONE part, `base` -- nowhere on the well could hold a screw.
# Order: servo in through the side window; 6809 onto the drum from below; drum into the base
# from above; input gear + horn up onto the servo shaft, horn screw; small gear up onto the
# seat, M3; floor on.
SEAT_R = 4.0                       # barrel steps down 5 -> 4 below the journal: the step is the gear's stop
SEAT_FLAT = 3.2                    # the D's flat, from the axis: it carries the torque
SLIDE = 0.15                       # per side, the gear onto the seat (the slide rule, not the horn rule)
WEB_Z1 = G_Z0 + 1.5                # -30.0: the gear's bottom 1.5 mm is a web the screw head pulls on
SEAT_Z0 = WEB_Z1 + 0.3             # -29.7: the seat stops short of the web so the screw clamps the step
M3_CLEAR, M3_BUTTON_R, M3_BUTTON_H = 1.7, 2.85, 1.65
SCREW_L = 8.0
SPLIT_Z = BAY_Z0 + 1.5             # -32.0: floor plate below, bay above
FLOOR_HOLE_R = 3.5                 # under each axis: the gear screw's head turns in one, a driver reaches
                                   # the horn screw through the other
SCREW_BOSS_R, SCREW_BOSS_H = 3.0, 5.0   # M2 bosses in the bay's four inside corners, clear of both
                                   # gears. NOT `BOSS_R`: that is the well's r 31, and reusing the
                                   # name silently deleted the bearing seat (2026-09-27)

# rolling-loop layout, angles CCW about +Z, 0 = +X
# Zach, 2026-09-19: the ribbon is to leave the bottom of the can at the SIDE, not off the
# front or wrapped round. -90 is the -Y side, picked over +Y because the servo tower sits
# there. Flip this one number to move it to the other side; nothing else needs touching --
# travel does not depend on where the fixed anchor is, only on L, ri and ro. Once out of
# the wall the ribbon can turn aft freely: that is a bend in its own plane, not a crease.
EXIT_DEG = -90.0
A_FIX = np.radians(EXIT_DEG)       # fixed anchor / wall exit


def at_exit(p):
    """Evaluate a shape drawn pointing at 180 deg as if it pointed at EXIT_DEG."""
    a = np.pi - A_FIX
    ca, sa = np.cos(a), np.sin(a)
    return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2])


def arc_band(p, R, a0, a1, half_t, z0, z1):
    """A thin arc of radius R spanning [a0, a1] (a1 > a0, span < 2pi), as a band in Z."""
    x, y = p[0], p[1]
    r = np.hypot(x, y)
    d = np.mod(np.arctan2(y, x) - a0, 2 * np.pi)
    inside = d <= (a1 - a0)
    e0 = np.hypot(x - R * np.cos(a0), y - R * np.sin(a0))
    e1 = np.hypot(x - R * np.cos(a1), y - R * np.sin(a1))
    d2 = np.where(inside, np.abs(r - R), np.minimum(e0, e1))
    return _cyl(d2 - half_t, np.abs(p[2] - (z0 + z1) / 2) - (z1 - z0) / 2)


def loop_angles(pan_deg=0.0):
    """Drum anchor, U, at a pan angle. Length is conserved: L = ro(tU-tf) + ri(tU-ta)."""
    tU_mid = A_FIX + L_CAN / (2 * RO)
    ta_mid = tU_mid - L_CAN / (2 * RI)
    ta = ta_mid + np.radians(pan_deg)
    tU = (L_CAN + RO * A_FIX + RI * ta) / (RO + RI)
    return ta, tU


def ribbon(p, features=True, pan_deg=0.0):
    ta, tU = loop_angles(pan_deg)
    h = DRAW_T / 2
    outer = arc_band(p, RO, A_FIX, tU, h, BAND_Z0, BAND_Z1)
    inner = arc_band(p, RI, ta, tU, h, BAND_Z0, BAND_Z1)
    cx, cy = (RO + RI) / 2 * np.cos(tU), (RO + RI) / 2 * np.sin(tU)
    d2 = np.abs(np.hypot(p[0] - cx, p[1] - cy) - U_R) - h
    turn = _cyl(d2, np.abs(p[2] - (BAND_Z0 + BAND_Z1) / 2) - (BAND_Z1 - BAND_Z0) / 2)
    tail = box(at_exit(p), (-WELL_OR - 12, -h, BAND_Z0), (-RO, h, BAND_Z1))   # out the side
    return U(outer, inner, turn, tail)


def gear(p, R, n, x0, z0, z1, phase=0.0):
    a = np.arctan2(p[1], p[0] - x0) * n + phase
    rr = R + TOOTH * np.cos(a)
    return _cyl(np.hypot(p[0] - x0, p[1]) - rr, np.abs(p[2] - (z0 + z1) / 2) - (z1 - z0) / 2)


def at_angle(p, deg):
    """Evaluate a shape drawn pointing along +X as if it pointed at deg."""
    a = -np.radians(deg); ca, sa = np.cos(a), np.sin(a)
    return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2])


def _pol(r, deg, z):
    return (r * np.cos(np.radians(deg)), r * np.sin(np.radians(deg)), z)


# The wires' holes, as centrelines (smoothed the way the cradle's are, tree_parts_b._centripetal).
# Drum: from the bore's floor at -X (the ribbon's slot is at +X), spiralling down and out (CW from above)
# and leaving the face at the lane's height, already heading along it. It stays inside r 8.5 until the
# lane so the face the ribbon wraps keeps 1 mm of wall. Base: from the lane out through the boss, heading
# the way the lane's outer wrap runs (CCW), clear of the ribbon's exit at -90.
DRUM_WIRE_PTS = [_pol(6.5, 185, 0.0), _pol(6.6, 184, -3.0), _pol(7.0, 178, -9.0), _pol(7.5, 171, -15.0),
                 _pol(8.0, 164, -19.0), _pol(9.4, 157, LANE_ZC + 0.6), _pol(11.4, 151, LANE_ZC),
                 _pol(14.0, 147, LANE_ZC)]
# Starts at r 20.5, not inside the lane: a 5 mm hole is taller than the 3.5 lane, and further in its top
# would shave the shelf to a skin under the ribbon. At r >= 18 the wall and the boss stand over it.
BASE_WIRE_PTS = [_pol(20.5, WIRE_EXIT_DEG - 6, LANE_ZC), _pol(21.8, WIRE_EXIT_DEG - 2, LANE_ZC),
                 _pol(23.5, WIRE_EXIT_DEG + 2, LANE_ZC), _pol(27.5, WIRE_EXIT_DEG + 7, LANE_ZC)]


def _centripetal(P, per=6):
    P = np.asarray(P, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Q) - 2):
        q = Q[i - 1:i + 3]; t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1) ** 0.5)]
        for u in np.linspace(t[1], t[2], per, endpoint=False):
            A_ = [((t[j + 1] - u) * q[j] + (u - t[j]) * q[j + 1]) / (t[j + 1] - t[j]) for j in range(3)]
            B_ = [((t[j + 2] - u) * A_[j] + (u - t[j]) * A_[j + 1]) / (t[j + 2] - t[j]) for j in range(2)]
            out.append(((t[2] - u) * B_[0] + (u - t[1]) * B_[1]) / (t[2] - t[1]))
    out.append(P[-1]); return np.array(out)


DRUM_WIRE = _centripetal(DRUM_WIRE_PTS)
BASE_WIRE = _centripetal(BASE_WIRE_PTS)


def wire_hole(p, line, r=WIRE_R):
    """A round hole of radius r along a centreline (capsule chain); far points skip the work."""
    X, Y, Z = (np.asarray(a, float) for a in p)
    d = np.full(np.broadcast(X, Y, Z).shape, 1e3)
    lo, hi = line.min(0) - r - 1, line.max(0) + r + 1
    m = (X >= lo[0]) & (X <= hi[0]) & (Y >= lo[1]) & (Y <= hi[1]) & (Z >= lo[2]) & (Z <= hi[2])
    if not m.any():
        return d
    q = np.stack([np.broadcast_to(X, d.shape)[m], np.broadcast_to(Y, d.shape)[m], np.broadcast_to(Z, d.shape)[m]], 1)
    best = np.full(len(q), 1e3)
    for a, b in zip(line[:-1], line[1:]):
        ab = b - a; t = np.clip(((q - a) @ ab) / (ab @ ab), 0, 1)
        best = np.minimum(best, np.linalg.norm(q - (a + t[:, None] * ab), axis=1))
    d[m] = best - r
    return d


def well(p, features=True):
    # Hard union, not smin. These four rings genuinely overlap, and blending them left a
    # sub-resolution film between the cup and the bearing seat: 45 bodies and a decimator
    # stalled at 304k faces against a 16k target, with the solid itself fine. Same class of
    # fault as ../../lessons/2026-09-19-coincident-faces-and-insertion.md -- read the face
    # count, not just watertight/manifold.
    # The cup wall stops 0.4 BELOW the hub, not level with it. Taken to Z 0 it shared
    # Z -0.4..0 with the rotating hub's r 22.5 -- 60 mm3, and a rubbing face even at zero.
    wall = ring_z(p, WELL_IR, WELL_OR, LANE_Z1, DECK_Z1 - 0.4, 0.6)
    # the wires' lane below the ribbon: its own wall, the floor under it, the shelf over it, and the boss
    # their exit runs through. The lane itself is cut out of all of it.
    lane_wall = ring_z(p, LANE_R, LANE_R + LANE_WALL, FLOOR_Z, CH_Z0, 0.6)
    shelf = ring_z(p, SHELF_R0, LANE_R + LANE_WALL, LANE_Z1, CH_Z0, 0.3)
    floor = ring_z(p, JOURNAL_R, LANE_R + LANE_WALL, FLOOR_Z, LANE_Z0, 0.6)
    sleeve = ring_z(p, JOURNAL_R, JOURNAL_R + 2.75, JOURNAL_Z0, LANE_Z0, 0.4)
    boss = rbox(at_angle(p, WIRE_EXIT_DEG), (WELL_IR + 1.0, -6.5, FLOOR_Z), (LANE_R + 5.0, 6.5, -18.5), 1.5)
    deck = ring_z(p, DECK_IR, BOSS_R, DECK_Z0, DECK_Z1, 0.6)
    seat = ring_z(p, SEAT_BORE_R, BOSS_R, DECK_Z0, BRG_Z1, 0.6)
    s = U(wall, lane_wall, shelf, floor, deck, seat, sleeve, boss)
    s = np.maximum(s, -ring_z(p, DRUM_R - 1.0, LANE_R, LANE_Z0, LANE_Z1, 0.0))
    relief = ring_z(p, RELIEF_R0, RELIEF_R1, DECK_Z1 - RELIEF_D, DECK_Z1 + 1.0, 0.0)
    s = np.maximum(s, -relief)
    if features:
        slot = box(at_exit(p), (-WELL_OR - 2, -(RIBBON_W + 1.6) / 2, BAND_Z0 - 0.4),
                   (-WELL_IR + 1, (RIBBON_W + 1.6) / 2, BAND_Z1 + 0.4))
        s = np.maximum(s, -U(slot, wire_hole(p, BASE_WIRE)))
    return s


ANCHOR_Z1 = 2.0


def drum(p, features=True):
    face = cyl_z(p, 0, 0, DRUM_R, LANE_Z0 + DRUM_LIFT, 0.0)   # down past the shelf: the lane's inner wall
    flange = cyl_z(p, 0, 0, FLANGE_R, CH_Z1, 0.0)
    hub = cyl_z(p, 0, 0, HUB_FIT_R, BRG_Z0, BRG_Z1)
    # The stand-in trunk is GONE. Above the bearing the drum ends in a disc the size of the
    # nest's own base, and the nest bolts to it -- that is the merge. Its underside doubles
    # as the bearing's inner-race shoulder.
    mate = cyl_z(p, 0, 0, MATE_R, BRG_Z1, BASE_Z)
    # The gear used to be moulded on here, and it could not pass the journal (see SEAT_R).
    # The barrel now ends in a D-shaped seat the separate gear_out pushes onto from below.
    barrel = cyl_z(p, 0, 0, BARREL_R, G_Z1, LANE_Z0 + DRUM_LIFT)
    seat = np.maximum(cyl_z(p, 0, 0, SEAT_R, SEAT_Z0, G_Z1 + 0.5), p[0] - SEAT_FLAT)
    # HARD union between the three stacks, not smin. Blending the flange into the hub bulged
    # the surface to r 19.84 -- past its named 17.7 -- and 133 mm3 of it ended up inside the
    # cup wall. A bearing shoulder wants a step, not a fillet, and the same blend at the
    # barrel's root was swelling it into the journal bore. Named radius != real radius
    # wherever a smooth min is involved; cradle-audit.md section 1 made the same mistake.
    # hub + mate HARD too (2026-09-27): smin 1.5 left a fillet r 22.5..23.45, Z 5.6..6.55 all the way
    # round the corner the 6809's bore edge seats in -- 30 mm3 against the bearing, found the first
    # time the bearing was checked against the drum. A 6809's bore chamfer is only ~0.3-0.6.
    s = U(smin(face, flange, 1.0), hub, mate, barrel, seat)
    if features:
        bore = cyl_z(p, 0, 0, BORE_R, CH_Z1 - 0.5, BASE_Z + 1)
        # Top at 2.0, was 0.5: the tilt servo's connector (14 x 8, Zach 2026-09-27) jammed turning
        # from the bore into this slot at 3.0 thick. 2.0 passes 3.5 (head-v2/checks/plug_passage.py).
        anchor = box(p, (DRUM_R - 5.5, -(RIBBON_W + 1.0) / 2, BAND_Z0),
                     (DRUM_R + 1, (RIBBON_W + 1.0) / 2, ANCHOR_Z1))
        # the gear screw's pilot, 1 mm past the tip of an M3 x 8
        pilot = cyl_z(p, 0, 0, M3_PILOT, SEAT_Z0 - 1, G_Z0 + SCREW_L + 1)
        cuts = [bore, anchor, pilot, wire_hole(p, DRUM_WIRE)]
        for a in np.radians(MATE_SCREWS):
            cuts.append(cyl_z(p, MATE_SCREW_R * np.cos(a), MATE_SCREW_R * np.sin(a), M3_PILOT,
                              BASE_Z - 7.0, BASE_Z + 1))
        s = np.maximum(s, -U(*cuts))
    return s


def bay(p, features=True):
    """Gear plane below the can, plus the tower the servo drops into. The servo is NOT a
    press fit in a hole: it lands on a shelf at TAB_Z0 and takes two M2 through its tabs.
    Zach found it unfastened by eye, the same way he found variant B's tilt servo."""
    # Tip radius, not pitch radius, is what has to clear: the cavity was cut to R_IN_G + 1,
    # which IS the tooth tip, so the teeth shaved 122 mm3 off the wall. Give them 2.5.
    tip = R_IN_G + TOOTH
    gx1 = CENTRE + tip + 3.5
    shell = rbox(p, (-BARREL_R - 9, -tip - 4, BAY_Z0), (gx1, tip + 4, FLOOR_Z), 3.0)
    tower = rbox(p, (SV_X0 - 3.5, SV_YC - TAB_SPAN / 2 - 2.5, G_Z1 + 1.8),
                 (SV_X1 + 3.5, SV_YC + TAB_SPAN / 2 + 2.5, DECK_Z0), 3.0)
    s = smin(shell, tower, 2.0)
    # Rounding 1.0, not 2.5: a fat corner radius pinches back in over the gear's top face
    # and that alone read 28 mm3 against the teeth.
    # Open underneath since 2026-09-27: the cavity runs out through the bottom and the floor is
    # the separate `floor` plate below SPLIT_Z, so both gears go in from below.
    cav = rbox(p, (-BARREL_R - 7, -tip - 1.5, BAY_Z0 - 2.0), (gx1 - 2.0, tip + 1.5, G_Z1 + 1.8), 1.0)
    s = np.maximum(np.maximum(s, -cav), SPLIT_Z - p[2])
    s = U(s, *[cyl_z(p, x, y, SCREW_BOSS_R, SPLIT_Z, SPLIT_Z + SCREW_BOSS_H) for x, y in floor_screws()])
    s = np.maximum(s, -U(*[cyl_z(p, x, y, M2_PILOT, SPLIT_Z - 1, SPLIT_Z + SCREW_BOSS_H + 0.5)
                           for x, y in floor_screws()]))
    if not features:
        return s
    # Zach, 2026-09-19: a window in the side so the servo slips in rather than dropping from
    # above. It goes in along its OWN long axis (-Y), which takes out only the short +Y end
    # wall -- the two long X walls, which react the gear torque, stay whole. The far tab
    # meeting the end of the tab slot is the depth stop. Both M2 sit at r > 31, outside the
    # deck plate, so a driver still reaches them from above once the well is in.
    win_y = SV_YC + TAB_SPAN / 2 + 4.0                 # out through the +Y wall
    pocket = box(p, (SV_X0 - FIT, SV_Y0 - FIT, SV_Z0), (SV_X1 + FIT, win_y, 1.0))
    # DOUBLES AS THE DRIVER PATH for the horn screw, which is driven from below up into
    # the servo shaft. It runs r 3.5 from under the bay's floor all the way to the servo,
    # so rule 6 is satisfied by accident, not by design -- shorten it and the screw
    # becomes unreachable with nothing to show it. Checked: 0 mm3 of bay on that axis.
    shaftway = cyl_z(p, CENTRE, 0, 3.75, BAY_Z0 - 1, SV_Z0 + 0.1)
    # The drum's barrel runs up through the shell's top slab on its way to the can.
    barrelway = cyl_z(p, 0, 0, JOURNAL_R + 3.35, G_Z1, FLOOR_Z + 1)
    tabs = box(p, (SV_X0 - FIT, SV_YC - TAB_SPAN / 2 - FIT, TAB_Z0), (SV_X1 + FIT, win_y, 1.0))
    # The body window is not enough on its own: sliding in, the OUTPUT SHAFT sweeps through
    # the shell's +Y wall between the gear cavity and the outside, 4 mm below the pocket
    # floor. Found by the insertion sweep, not by the pair check -- seated, it is clear.
    # The MG90S's block and shaft reach 6.0 and 10.0 below the case face, through the slab over the gear
    # cavity that the old 4 mm stub cleared. Both get a channel out through the window (2026-09-28).
    humpway = box(p, (SV_X0 - FIT, SV_Y0 - FIT, SV_Z0 - SV_HUMP_H - 0.3), (SV_X1 + FIT, win_y, SV_Z0 + 0.1))
    shaftslot = box(p, (CENTRE - 3.75, 0.0, SV_Z0 - SV_SHAFT - 0.5), (CENTRE + 3.75, win_y + 2, SV_Z0 + 0.4))
    # The tab block's grooves: blind at the -Y end (its stop), out through the window.
    grooves = box(p, (SV_X0 - FIT - TB_RAIL - TB_SLIDE, TB_Y0 - TB_SLIDE, TAB_Z0 - TB_H - TB_SLIDE),
                  (SV_X1 + FIT + TB_RAIL + TB_SLIDE, win_y + 1, TAB_Z0 - TB_H + TB_RAIL_H + TB_SLIDE))
    cuts = [pocket, tabs, shaftway, barrelway, humpway, shaftslot, grooves]
    for ty in (SV_YC - TAB_PITCH / 2, SV_YC + TAB_PITCH / 2):
        cuts.append(cyl_z(p, CENTRE, ty, M2_PILOT, TAB_Z0 - 6.0, TAB_Z0 + 0.2))
    return np.maximum(s, -U(*cuts))


def tab_block(p, features=True):
    """Slides in under the servo's +Y tab after the servo; the tab's M2 x 6 screws into it."""
    x0, x1 = SV_X0 - FIT + TB_SLIDE, SV_X1 + FIT - TB_SLIDE
    z0 = TAB_Z0 - TB_H
    body = box(p, (x0, TB_Y0, z0), (x1, TB_Y1, TAB_Z0))
    rails = box(p, (x0 - TB_RAIL, TB_Y0, z0), (x1 + TB_RAIL, TB_Y1, z0 + TB_RAIL_H))
    s = U(body, rails)
    if not features:
        return s
    return np.maximum(s, -cyl_z(p, CENTRE, SV_YC + TAB_PITCH / 2, M2_PILOT, z0 + 0.5, TAB_Z0 + 1))


def floor_screws():
    """The four M2s, one in each inside corner of the gear cavity, 1.8 in from both walls."""
    tip = R_IN_G + TOOTH
    x0, x1, y1 = -BARREL_R - 7 + 1.8, CENTRE + tip + 3.5 - 2.0 - 1.8, tip + 1.5 - 1.8
    return [(x0, -y1), (x0, y1), (x1, -y1), (x1, y1)]


def floor(p, features=True):
    """The bay's old floor, now a plate on four M2 x 6. Holes under both axes."""
    tip = R_IN_G + TOOTH
    shell = rbox(p, (-BARREL_R - 9, -tip - 4, BAY_Z0), (CENTRE + tip + 3.5, tip + 4, FLOOR_Z), 3.0)
    s = np.maximum(shell, p[2] - SPLIT_Z)
    if not features:
        return s
    cuts = [cyl_z(p, x, y, M2_CLEAR, BAY_Z0 - 1, SPLIT_Z + 1) for x, y in floor_screws()]
    cuts += [cyl_z(p, x, 0, FLOOR_HOLE_R, BAY_Z0 - 1, SPLIT_Z + 1) for x in (0.0, CENTRE)]
    return np.maximum(s, -U(*cuts))


def base(p, features=True):
    """The printed fixed part: the well and the bay fused. Each keeps its own cuts, so the
    servo pocket does not bite the well's bearing seat."""
    return U(well(p, features), bay(p, features))


def gear_out(p, features=True):
    """The drum's gear, off the drum since 2026-09-27. D bore onto the barrel's seat from
    below, a web at the bottom for the M3 head to pull up on."""
    s = gear(p, R_OUT_G - GEAR_GAP, N_OUT, 0.0, G_Z0, G_Z1)
    s = np.maximum(s, np.maximum(G_Z0 - p[2], p[2] - G_Z1))
    if not features:
        return s
    d = np.maximum(cyl_z(p, 0, 0, SEAT_R + SLIDE, WEB_Z1, G_Z1 + 1), p[0] - SEAT_FLAT - SLIDE)
    hole = cyl_z(p, 0, 0, M3_CLEAR, G_Z0 - 1, WEB_Z1 + 0.1)
    return np.maximum(s, -U(d, hole))


def screw_out(p, features=True):
    """The M3 x 8 button head holding gear_out, as hardware for the checks."""
    head = cyl_z(p, 0, 0, M3_BUTTON_R, G_Z0 - M3_BUTTON_H, G_Z0)
    # Shank drawn at the pilot's radius: the thread cutting into the drum is meant, and at 1.5
    # it reads 16 mm3 against the drum in every check.
    shank = cyl_z(p, 0, 0, M3_PILOT, G_Z0, G_Z0 + SCREW_L)
    return U(head, shank)


def servo(p, features=True):
    body = rbox(p, (SV_X0, SV_Y0, SV_Z0), (SV_X1, SV_Y1, SV_Z1), 1.0)
    tabs = rbox(p, (SV_X0, SV_YC - TAB_SPAN / 2, TAB_Z0), (SV_X1, SV_YC + TAB_SPAN / 2, TAB_Z0 + TAB_T), 0.8)
    hump = box(p, (SV_X0, SV_Y0, SV_Z0 - SV_HUMP_H), (SV_X1, SV_Y0 + SV_HUMP_L, SV_Z0 + 0.5))
    shaft = cyl_z(p, CENTRE, 0, SV_SHAFT_R, SV_Z0 - SV_SHAFT, SV_Z0 - SV_HUMP_H + 0.1)
    return U(body, tabs, hump, shaft)


def horn_at(p, x0, z0, z1):
    """A stock double-arm horn: centre disc plus the arm bar, as a cutting body."""
    q = (p[0] - x0, p[1], p[2])
    return U(cyl_z(q, 0, 0, HORN_C / 2, z0, z1),
             rbox(q, (-HORN_L / 2, -HORN_W / 2, z0), (HORN_L / 2, HORN_W / 2, z1), 1.0))


def gear_in(p, features=True):
    # The hub used to run 2 mm ABOVE the gear and straight into the servo's case. It hangs
    # below instead; the shaft still gets 3.5 mm of engagement.
    g = gear(p, R_IN_G, N_IN, CENTRE, G_Z0, G_Z1, phase=np.pi)
    hub = cyl_z(p, CENTRE, 0, 5.0, G_Z0, G_Z1)     # flush both ends: hanging 1.5 below put
                                                   # it through the bay's floor, 28 mm3 of it
    s = smin(g, hub, 0.8)
    # Trim both faces flat: the smooth min bulged ~0.2 below G_Z0 round the hub, so the gear sat on
    # a ring and its face floated 0.05-0.3 mm off the bed (2026-09-27, print check).
    s = np.maximum(s, np.maximum(G_Z0 - p[2], p[2] - G_Z1))
    if not features:
        return s
    # ZERO offset on the horn pocket -- Zach's method, 2026-09-19: subtract the horn's own
    # model in Fusion with no size change and the print comes out a tight fit. That beats the
    # "+0.2 mm all round" in ball-head-validation-handoff.md, which was advice, not a result.
    # HORN_* here are the repo's GENERIC numbers and are only a placeholder: re-cut this
    # pocket in Fusion with the real horn model. What this file fixes is the POSITION.
    #
    # It matters more on this gear than anywhere else: a 34.4 mm horn fits inside a 41.3 mm
    # gear, so the plastic grips the arm tips at r 17.2 instead of the shaft spline at ~1.25
    # -- 14x the leverage, so the same pocket slop makes 14x less angle at the head. And the
    # 2:1 step-up doubles whatever is left, which is why this joint is the one to get right.
    horn = horn_at(p, CENTRE, G_Z1 - HORN_D, G_Z1 + 0.5)
    shank = cyl_z(p, CENTRE, 0, M2_CLEAR, G_Z0 - 1, G_Z1 - HORN_D + 0.1)
    cbore = cyl_z(p, CENTRE, 0, M2_HEAD, G_Z0 - 1, G_Z1 - HORN_D - HORN_ROOF)
    return np.maximum(s, -U(horn, shank, cbore))


def bearing(p, features=True):
    return ring_z(p, HUB_R, BRG_OR, BRG_Z0, BRG_Z1, 0.4)


def twist_short(p, features=True):
    """The run the twist actually needs, drawn from where it has to stop. The ghost is the
    finding: TWIST_HAVE of bore exists, TWIST_NEED is wanted."""
    return ring_z(p, BORE_R - 0.9, BORE_R, TWIST_HAVE, TWIST_NEED, 0.3)


PARTS = {
    # The well is a large 2 mm shell: marching cubes gives ~300k faces at this step and the
    # raw mesh is clean (1 component, watertight, manifold -- checked). A 16k target is what
    # broke it; the decimator would not collapse that far with preservetopology on, returned
    # its last failed attempt undecimated, and the REPORT then read 46 bodies. Read the face
    # count against the target, not just the flags.
    'well':     (well,     (-33, -33, JOURNAL_Z0 - 1), (33, 33, BRG_Z1 + 1), 0.34, 48000),
    'drum':     (drum,     (-28, -28, G_Z0 - 1), (28, 28, BASE_Z + 1), 0.30, 24000),
    'ribbon':   (ribbon,   (-WELL_OR - 13, -WELL_OR - 13, BAND_Z0 - 1),
                           (WELL_OR + 13, WELL_OR + 13, BAND_Z1 + 1), 0.22, 14000),
    'bay':      (bay,      (-17, -R_IN_G - 7, BAY_Z0 - 1),
                           (CENTRE + R_IN_G + 10, SV_YC + TAB_SPAN / 2 + 5, DECK_Z0 + 1), 0.34, 26000),
    'servo':    (servo,    (SV_X0 - 1.5, SV_YC - TAB_SPAN / 2 - 1.5, SV_Z0 - SV_SHAFT - 1),
                           (SV_X1 + 1.5, SV_YC + TAB_SPAN / 2 + 1.5, SV_Z1 + 1), 0.28, 7000),
    'gear_in':  (gear_in,  (CENTRE - R_IN_G - 3, -R_IN_G - 3, G_Z0 - 3),
                           (CENTRE + R_IN_G + 3, R_IN_G + 3, G_Z1 + 2), 0.28, 11500),
    'bearing':  (bearing,  (-30, -30, BRG_Z0 - 1), (30, 30, BRG_Z1 + 1), 0.26, 7000),
    # 2026-09-27: what prints is base (= well + bay), floor and gear_out; well and bay stay as
    # separate meshes for the viewer, the sim and the pair checks.
    'base':     (base,     (-33, -33, BAY_Z0 - 1),
                           (CENTRE + R_IN_G + 10, 33, BRG_Z1 + 1), 0.34, 60000),
    'floor':    (floor,    (-17, -R_IN_G - 7, BAY_Z0 - 1), (CENTRE + R_IN_G + 7, R_IN_G + 7, SPLIT_Z + 1),
                           0.25, 12000),
    'gear_out': (gear_out, (-R_OUT_G - 3, -R_OUT_G - 3, G_Z0 - 1), (R_OUT_G + 3, R_OUT_G + 3, G_Z1 + 1),
                           0.20, 9000),
    'tab_block': (tab_block, (SV_X0 - 3, TB_Y0 - 1, TAB_Z0 - TB_H - 1), (SV_X1 + 3, TB_Y1 + 1, TAB_Z0 + 1), 0.15, 4000),
    'screw_out': (screw_out, (-4, -4, G_Z0 - M3_BUTTON_H - 1), (4, 4, G_Z0 + SCREW_L + 1), 0.20, 3000),
    'twist_gap': (twist_short, (-11, -11, TWIST_HAVE - 1), (11, 11, TWIST_NEED + 1), 0.30, 5000),
}

if __name__ == '__main__':
    os.makedirs(os.path.join(OUT, 'fusion'), exist_ok=True)
    names = [a for a in os.sys.argv[1:] if a in PARTS]
    print(f'coil   ri {RI:.2f}  ro {RO:.2f}   U radius {U_R:.2f} = {U_R / RIBBON_T:.0f}x thickness'
          f'  (min {MIN_BEND_R:.1f})')
    print(f'travel {np.degrees(TRAVEL):.0f} deg of mechanism for {L_CAN:.0f} mm of ribbon in the can')
    print(f'can    cavity {2 * WELL_IR:.0f}  outside {2 * WELL_OR:.0f}  depth {-FLOOR_Z:.0f}'
          f'   stump depth {-BAY_Z0:.0f}')
    print(f'gears  {N_OUT}/{N_IN} = {N_IN / N_OUT:.0f}:1   module {2 * R_OUT_G / N_OUT:.2f}'
          f'   centres {CENTRE:.0f}   servo X {SV_X0:.1f}..{SV_X1:.1f}')
    print(f'wraps  {L_CAN / (2 * np.pi * RI):.2f} turns on the drum at the stop')
    print(f'TWIST  {TWIST_HAVE:.1f} mm of bore exists, {TWIST_NEED:.0f} wanted'
          f'  -> short by {TWIST_NEED - TWIST_HAVE:.1f}')
    lines, bundle = [], {}
    lo_all = np.array([1e9] * 3); hi_all = -lo_all
    for name, (fn, lo, hi, step, target) in PARTS.items():
        if names and name not in names:
            continue
        f = lambda P: fn(P, True)
        vol = sample(f, lo, hi, step)
        v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
        v = project(f, v + np.array(lo), step)
        with quiet():
            ms, ok = decimate(v, faces, target)
            _, msg = report(ms)
            ms.save_current_mesh(os.path.join(OUT, 'fusion', f'{name}.obj'), save_vertex_normal=False)
            V = ms.current_mesh().vertex_matrix()
            bundle[name] = {'v': base64.b64encode(V.astype('<f4').tobytes()).decode(),
                            'f': base64.b64encode(ms.current_mesh().face_matrix().astype('<u4').tobytes()).decode()}
        lo_all = np.minimum(lo_all, V.min(0)); hi_all = np.maximum(hi_all, V.max(0))
        lines.append(f'fusion/{name}.obj'.ljust(22) + msg)
        print(lines[-1], flush=True)
    bundle['_meta'] = {'travel_deg': round(float(np.degrees(TRAVEL)), 1), 'L_can': L_CAN,
                       'can_od': 2 * WELL_OR, 'stump_depth': -BAY_Z0,
                       'twist_have': TWIST_HAVE, 'twist_need': TWIST_NEED,
                       'ri': round(RI, 2), 'ro': round(RO, 2), 'u_r': round(U_R, 2)}
    open(os.path.join(OUT, 'viewer_pan_coil_b.js'), 'w').write('window.PANCOILB=' + json.dumps(bundle) + ';')
    env = f'ENVELOPE {lo_all.round(1)} -> {hi_all.round(1)}  size {(hi_all - lo_all).round(1)}'
    print(env)
    open(os.path.join(OUT, 'mesh_report.txt'), 'w').write('\n'.join(lines) + '\n' + env + '\n')
