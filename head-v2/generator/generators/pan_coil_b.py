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

# ---- set 7 (2026-10-04): the shelf drops in ----------------------------------------------------
# Zach: Orca's supports in the wire lane, under the shelf, can't be got out (8 mm deep in the 3.5 mm lane,
# all round), and he wants no supports there at all. A 30 deg slope can't carry the shelf: across the lane's
# 8.4 it would have to drop 14.5, and the lane is 3.5 tall with the ribbon's floor on top of it. So the shelf
# and the ribbon cup's wall leave the base as one part, `shelf_ring`, printed shelf face down, which drops in
# from above onto a ledge on the lane wall. The deck ring's hole widens to let it through, which also takes
# the deck ring out from under the drum's hub: the hub sat flush on it at r 19.5-20.4 (found 2026-10-04). A
# skirt carries the deck ring now, with a cone 30 deg off vertical under its outer part (Zach's limit), and the
# ribbon leaves through a slit in both. A rib on the ledge keys a notch in the ring's shelf, so the ribbon's
# drag can't turn the ring, and lines the ring's own ribbon notch up with the slit.
INSERT = True
RING_OR = LANE_R + 1.5             # 22.5: the shelf's outer edge, on a 1.5 ledge of the lane wall
RING_SLIDE = 0.15                  # per side, down the skirt (the slide rule)
SKIRT_IR = RING_OR + RING_SLIDE    # 22.65: also the deck ring's new hole (the hub is 22.45)
SKIRT_T = 1.8                      # its outer face 0.45 off the servo pocket's wall (X 24.65)
RING_IR = WELL_IR + 0.3            # 18.3, was 18.0: the drum's flange (17.7) keeps 0.45 with the ring a full
                                   # 0.15 off centre
RING_T = 2.0
CONE_OUT_DEG = 30.0                # the deck ring's underside outside the skirt, off vertical
WINDOW_W = RIBBON_W + 1.6          # 17.6, the old slot's width: the ring's ribbon notch
# The first set 7 slices (Orca, his settings) still put supports under a 17.6 window's roof, in the wires' exit
# hole, and then under the cone's free edge over a 17.6 channel for a tab on the ring. Past the ring's notch the
# ribbon only runs straight out, on edge, so it leaves by a slit, with a roof leaning 30 deg off vertical (Zach's
# limit), and the exit hole has a pointed top. Under the bearing's inner race the slit runs open to the top,
# where the deck ring is relieved anyway. The key is a rib on the ledge instead of a tab, so the skirt stays whole.
SLIT_W = 2.0                       # its roof rises 1.73, inside the deck ring
KEY_DEG = -60.0                    # clear of the slit (-90), the exit hole (-145) and the servo's tower (+X)
KEY_W, KEY_D, KEY_H = 2.4, 1.2, 2.5   # the rib: across, in from the skirt, up from the ledge
KEY_SLIDE = 0.15                   # per side, the ring's notch round the rib

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
# Set 6 (2026-10-03): the horn pocket above was a placeholder from generic numbers, and with the gear on
# the shaft Zach's screw couldn't reach. No horn model of his could be found, so the spline now presses
# straight into the gear, the way post v3 takes the tilt servo's: post v3's bore (his own faceted 4.5,
# flats at 2.22), a 1.5 lip under the spline tip, and the screw through the lip from below. The servo's
# own horn screw is sized for a horn's thin floor, which the lip stands in for. The lip sits at his
# MG90S model's tip (10.0 past the case face); if the real spline is 9.0 (his caliper on the tilt servo),
# the screw pulls the gear 1.0 up, which the bay has room for (0.8 under its roof, 0.5 off the boss).
SPL_BORE_R = 2.22                  # post3.BORE_R: the press fit he has printed
SPL_LIP = 1.5                      # post3: LIP1 - LIP0
SPL_HOLE_R, SPL_CB_R = 1.35, 2.6   # post3: clears M2 and M2.5; head counterbore 5.2
SPL_LEAD = 0.4                     # post3: lead-in chamfer on the bore's mouth
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
# Set 8 (2026-10-09): the seat kept snapping off when Zach tightened the screw (his photo: the broken seat still
# on the screw inside the gear). The M3 x 8 had 4.2 of its 6.2 mm of thread in the seat, below the step, so
# tightening pulled the seat down off the barrel while the gear pushed up on the step: tension across the
# layers (the drum prints upside down, layers across the barrel) at a sharp corner. Now the seat has a clear
# hole and a longer screw threads only into the barrel above the step, so tightening squeezes the step and the
# seat carries only the turning load. Superseded: SCREW_L 8.0, the pilot from the seat's end.
SCREW_THRU = True
SCREW_L = 12.0                     # his M3 x 12 button heads (2026-09-27 list; set 7 used the x 8)
# Set 8, Zach: "a square going in so it grips better". The D's flat stood only 0.8 in from the round, and with
# the 0.15 slide the gear could turn 7.5 deg on it, end to end, before the flat bit (2.2 for this square at
# 0.05, 4.4 at 0.10, 6.6 at 0.15; drum_set8.py measures it). A square with rounded corners: its
# corners reach r 4.62, inside the barrel's 5, so the step stays all round and the seat still passes down
# through the journal (5.25). The wall round the screw's clear hole is 1.8 (the D's was 1.5 at the flat). Two
# small gears to try, as the +Y sleeve had: SQ_FIT per side. Superseded: the D (SEAT_R, SEAT_FLAT, SLIDE).
SEAT_SQUARE = True
SQ_H, SQ_RC = 3.5, 0.8             # half across the flats (7.0 square), corner radius
SQ_FITS = (0.05, 0.10)             # per side: snug (the screw draws it on), and looser if that won't go on
SQ_FIT = SQ_FITS[0]

# ---- set 9 (2026-10-10): a 688 on the barrel instead of the journal ----------------------------------------------
# Zach at the bench (FPVTank_Control docs/bench/2026-10-10-v2-head-first-power.md): the pan servo can't turn the drum;
# there is more drag when the head leans, and the drum is "not bearing smooth" with the 6809ZZ in. Leaning, the barrel
# bears on the journal's PLA, 0.25 a side. He has many 688s (8 x 16 x 5, his numbers), so the journal becomes a 688's
# seat. The drum goes in from above THROUGH the bearing, so everything under the drum's face has to pass the 688's
# 8 mm bore: the barrel narrows to it, and the square seat shrinks to 6.0 across (corners r 3.91). The 688 drops in
# from above before the drum, onto a lip under its outer race only; its top is the lane's floor. The drum's underside
# stands DRUM_LIFT (0.4) over it, so the 688 only steadies the barrel and the 6809 still carries the drum.
# Superseded: the journal (JOURNAL_R, JOURNAL_Z0, the sleeve) and the 7.0 square (SQ_H 3.5).
BARREL_688 = True
B688_ID, B688_OD, B688_W = 8.0, 16.0, 5.0
NECK_R = B688_ID / 2 - 0.05        # 3.95: the barrel in the 688, HUB_FIT_R's -0.05
B688_SEAT_R = B688_OD / 2 + 0.05   # 8.05: the seat, SEAT_BORE_R's +0.05
B688_Z1 = LANE_Z0                  # -24.3: flush with the lane's floor
B688_Z0 = B688_Z1 - B688_W         # -29.3
B688_LIP_R, B688_LIP_T = 7.1, 1.0  # the lip reaches in under the outer race only (a 688's outer race starts ~r 7.0)
B688_WALL_R = 10.0                 # the housing's outside; its bottom (-30.3) is 1.1 over the gear plane
if BARREL_688:
    SQ_H = 3.0                     # 6.0 across: corners r 3.91 pass the 688's r 4.0
    # Zach, set 9 printed (2026-10-10): the 0.05 gear was so tight on the 6.0 square that pulling it off ripped the
    # square off the drum; the 0.10 one is "not that bad". 0.10 is the fit now. Superseded: SQ_FITS[0] as the default.
    SQ_FIT = SQ_FITS[1]
    # 2026-10-11: the 0.10 "went on fine, still super tight but it did come off".

# ---- set 10 (2026-10-11): the wires straight down the pan axis --------------------------------------------------
# Zach at the bench: set 9's pan moved only over 500..800 us meshed, and the bare servo turned its full 180 deg, so the
# drag is the head's. He found the jumper wires squashed in the lane once everything is screwed down, and asked why they
# leave the drum sideways at all: move the axis screw out to a few screws round a plate the gear bolts to, and run the
# wires down the middle. Set 8 rejected the axis route only because the gear's screw sat on the axis; set 9 rejected a
# 6704 only because its 20 mm barrel ran into set 8's off-axis wire hole. With the wires on the axis both reasons go.
# The 688's 8 mm bore was the bottleneck: hollow, its barrel leaves no wall for screws. Now:
#   * a 6704 (20 x 27 x 4; Zach has ~6) in the base where the 688 was, its top still level with the lane's floor, on a lip
#     under its outer ring only;
#   * the drum's barrel is 19.9 across, hollow: AX_WIRE_R straight down the axis from the cone's point, through the
#     barrel, the small gear and the floor plate's existing hole. The wires twist round the axis instead of rolling;
#   * the small gear bolts to the barrel's end on three M3 x 16 round the hole (Zach's plate; he has plenty, and few M2
#     left). The gear carries a solid hub
#     on top, 22.4 across, that meets the barrel's end face to face 0.4 under the 6704's inner ring, so the drum can't
#     lift out; the barrel ends there. The heads sit under the gear and turn in a wider hole in the floor plate.
# The lane, its shelf ring and the exit hole stay as they are, empty: the printed shelf ring still fits.
# Same day, never printed: the first draft had a 1.1 collar round the barrel's end and the heads sunk into the gear's
# underside, 0.9 of wall between each pocket and the wire hole or the teeth. Zach, in the view: "the connection for the
# gear looks extremely flimsy". Now every hole has ~1.4 of wall (M3) for the gear's full 8.7.
# Superseded: the 688 (BARREL_688), the square stub and the M3 on the axis (SEAT_SQUARE, SCREW_THRU), set 8's straight
# hole and groove (STRAIGHT_WIRE).
HOLLOW_AXIS = True
B6704_ID, B6704_OD, B6704_W = 20.0, 27.0, 4.0
AX_NECK_R = B6704_ID / 2 - 0.05    # 9.95: the barrel in the 6704, the stub's light slip (tree_parts_b.STUB_R)
B6704_SEAT_R = B6704_OD / 2 + 0.05 # 13.55: the tilt seats' 27.1 (tree_parts.BRG_OD)
B6704_Z1 = LANE_Z0                 # -24.3: flush with the lane's floor, as the 688 was
B6704_Z0 = B6704_Z1 - B6704_W      # -28.3
B6704_RINGS = (10.0, 11.3, 12.3, 13.5)   # inner ring r 10.0..11.3, outer 12.3..13.5 (ball_minus_cup.py, typical 6704)
B6704_LIP_R = 12.4                 # the lip reaches in under the outer ring only
B6704_WALL_R = B6704_SEAT_R + 2.0  # 15.55: the housing's outside
B6704_LIP_Z0 = G_Z1 + 1.8          # -29.6: down to the gear cavity's roof, so no sliver of the bay hangs under it
AX_WIRE_R = 2.75                   # 5.5 across: one jumper plug (2.5 square) with two 1.2 silicone wires beside it
AX_WIRE_Z1 = -12.0                 # the hole's top, in the cone's air: a r 3 hole meets the cone at Z -12.9
AX_SCREW_R = 5.9                   # the screws' circle: ~1.45 of wall each side, to the wire hole and the teeth's roots (r 9.03)
AX_SCREW_DEG = (90.0, 210.0, 330.0)
AX_SCREW_L = 16.0                  # M3 x 16 (Zach: "quite a few"): 8.7 through the gear, 7.3 into the barrel
AX_CLEAR_R, AX_PILOT_R = M3_CLEAR, M3_PILOT   # 1.7 clear through the gear; 1.25 pilot in the barrel
AX_HEAD_R, AX_HEAD_H = M3_BUTTON_R, M3_BUTTON_H   # button heads, as his other M3s: under the gear, not sunk into it
AX_HUB_R = 11.2                    # under the inner ring (r 10.0..11.3), clear of the outer (12.3)
AX_LIFT = 0.4                      # the hub's top under the 6704's inner ring: the drum's lift before it stops
AX_JOINT_Z = B6704_Z0 - AX_LIFT    # -28.7: the hub's top and the barrel's end, face to face
AX_FLOOR_HOLE_R = AX_SCREW_R + AX_HEAD_R + 0.6   # 8.5: the floor plate's middle hole, the heads turning in it
if HOLLOW_AXIS:
    BARREL_688 = False             # superseded by the 6704; the flag is what the checks and views key on

# ---- set 11 (2026-10-12): the shelf ring back in the base ---------------------------------------------------------
# Set 10 assembled, Zach had the pan's full sweep ("We fixed it!"), then: the drop-in shelf ring "has a chance of falling
# out of its lock if its gone upside down" (the base goes upside down for the small gear and the floor plate, and only a
# 2.5 rib held the ring), and it "doesnt need to be an extra piece if the wire just runs through the bottom now"; close
# the wires' old exit hole on the outside. Set 7 made the ring separate only because the lane under the shelf needed
# supports that couldn't be got out. With the wires down the axis the lane is empty, so it fills solid up to the
# ribbon's floor and nothing overhangs. The ring's cup wall stands on the fill as part of the base, its ribbon notch and
# the slit unchanged. The rib, the boss and the exit hole go. The 6704 still drops in from above, so the fill leaves a
# hole it passes, PASS_R, down to its seat: 1.75 round the drum's face where the ring's shelf left 0.6. The ribbon's
# bottom edge stands 1.0 over the floor, and its inner wrap rides on the drum. Superseded: the separate `shelf_ring`
# (INSERT's ring, KEY_*), the boss and BASE_WIRE's hole.
SHELF_MERGED = True
PASS_R = B6704_OD / 2 + 0.25       # 13.75: the 6704 (r 13.5) drops through, 0.25 a side
RING_PART = INSERT and not SHELF_MERGED   # set 7..10: the shelf ring is its own print


def rsquare(p, h, rc):
    """Rounded square about the Z axis, sides along X and Y, h half across the flats: a 2D distance."""
    qx, qy = np.abs(p[0]) - (h - rc), np.abs(p[1]) - (h - rc)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rc
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
DRUM_WIRE_PTS_SET5 = [_pol(6.5, 185, 0.0), _pol(6.6, 184, -3.0), _pol(7.0, 178, -9.0), _pol(7.5, 171, -15.0),
                      _pol(8.0, 164, -19.0), _pol(9.4, 157, LANE_ZC + 0.6), _pol(11.4, 151, LANE_ZC),
                      _pol(14.0, 147, LANE_ZC)]          # superseded by set 6 (below): its mouth was in the floor
# Set 6 (2026-10-03): the bore's flat floor printed as an 18 mm ceiling over tree supports (the drum prints
# top face down) and Zach couldn't get them out. The floor is now a cone 30 deg off vertical (his number),
# which prints with nothing under it, and its point is the hole's mouth: wherever the wires drop, they
# slide to it. The hole starts in the cone's air above the point, bends out under the ribbon's band and
# leaves the face where set 5's did. It keeps 0.8 of floor under it to r 5.5 (the barrel is below r 5),
# then breaks cleanly through the drum's underside on its way into the lane, as set 5's did from r 9.
CONE = True
CONE_DEG = 30.0                    # off vertical: Zach, "no greater than 30deg"
BORE_Z0 = CH_Z1 - 0.5              # -2.5: where the bore's straight wall ends
CONE_APEX_Z = BORE_Z0 - BORE_R / np.tan(np.radians(CONE_DEG))   # -18.09
DRUM_WIRE_PTS = [(0.0, 0.0, -13.0), _pol(0.8, 160, -17.0), _pol(3.0, 158, -19.6), _pol(5.5, 156, -20.6),
                 _pol(9.0, 154, LANE_ZC + 0.55), _pol(11.4, 151, LANE_ZC), _pol(14.0, 147, LANE_ZC)]
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

# Set 5 (2026-10-02): the cradle's wire hole (round 1, printed) lets the wires out IN FRONT of the ribbon,
# where it bends down into the bore, and this hole starts BEHIND it. The 18 bore leaves the 16 ribbon only
# ~0.7 at each edge, so the wires can't get round. A drum hole can't start outside the bore instead: the
# bore floor's edge (r 9, Z -2.5) and the chamber's top (r 12, Z -2) are 3.0 apart, under a 5 mm hole.
# So: a notch in the bore wall on -Y, under the cradle's groove (open to Y -11, X -6.9..1.4), where the
# wires pass the ribbon's -Y edge; and a funnel on this hole's mouth. Threading is done by eye, not blind.
# The cradle's 22 groove lets the 16 ribbon sit up to 3 off centre. At r 12.3 (the first cut) a ribbon 3
# toward -Y left a 1.4 bundle; from r 13.5 out, the printed cradle's mouth is the tightest place for every
# ribbon position (checks/wire_route.py row 7).
NOTCH_R = 14.0                     # the hub is solid to r 22.45; the drum screws' pilots start at r 18.75
NOTCH_A0, NOTCH_A1 = -150.0, -72.0 # X -12.1 .. +4.3 at r 14: in front of the ribbon to well behind it
NOTCH_Z0 = 6.0                     # the floor at the outer wall. It falls NOTCH_FLOOR_DEG inward to Z -1.1
NOTCH_FLOOR_DEG = 60.0             # at the bore, so it prints without support upside down (the drum prints
                                   # top face down) and leads the wires back into the bore. Set 5 had 55, 35
                                   # off vertical; set 6 takes Zach's 30 limit, which also lands the floor's
                                   # foot (Z -2.66 at r 9) on the cone's rim (-2.5), so the two run together
FUNNEL_R = 3.5                     # 7 across at the bore floor, down to the 5 mm hole 2 mm lower
FUNNEL_D = 2.0                     # set 6: the cone is the funnel, so this one is only cut when CONE is off
NOTCH = True
SPLINE_GEAR = True                 # set 6: the input gear takes the spline straight in (SPL_*)
# Set 9 (2026-10-10): Zach at the bench, the input gear "slips, on the connection i can see the inner screw moving
# without the movement of the outer gear", and it rubs the wall above it, worse as its screw tightens. Both are set
# 6's press bore: PLA can't hold a metal spline, and the screw set the gear's height. The note above expected the
# real 9.0 spline to let the screw pull the gear 1.0 up with room for it, but the block was 0.5 over the gear's top
# face, so the screw clamped the gear against the servo. Now the servo's own double-arm horn (Arm02 in
# ../pan-coil-b/horn/MG90_Arm.step, a measured MG90S horn; Zach's caliper matched its length, arm, hub and height)
# sits in a pocket of its own outline (his zero-offset rule), so the horn carries the torque, and the horn, seated
# on the spline, sets the gear's height. The spline stops on the horn's web, 1.4 above its flat face (measured on
# the model), so the flat face sits SPLINE_REAL - SV_HUMP_H + 1.4 = 4.4 under the block. The gear's top face drops
# to HUMP_AIR under the block; one M2 x 6 comes up through the gear's floor, the horn's web and into the spline.
# The exact pocket is cut in OCC on the print mesh (fixes/gear_horn_set9.py); the one here is the horn's outline
# drawn as a disc and a bar, for the checks and the views. Superseded: SPLINE_GEAR's press bore (set 6).
HORN_GEAR = True
SPLINE_REAL = 9.0                  # Zach's caliper, case face -> spline tip (the tilt servo, same model)
HORN_WEB = 1.45                    # Arm02: its flat face -> the web's top, where the spline tip stops (the STEP: a
                                   # 2.25 counterbore to 0.95, the web 0.95..1.45, the spline socket above)
HORN_H = 3.7                       # Arm02: flat face -> the hub's top
HORN_ARM_T = 1.65                  # Arm02: the arms' thickness
HORN_LEN, HORN_HUB_D = 31.35, 6.9  # Arm02: tip to tip; the hub's outside
HORN_FACE_Z = SV_Z0 - SPLINE_REAL - HORN_WEB          # -35.3: the horn's flat face, down
HUMP_AIR = 1.0                     # the gear's top face under the servo's block (set 6 had 0.5, and no stop)
GIN_Z1 = SV_Z0 - SV_HUMP_H - HUMP_AIR                  # -31.9: the input gear's top face
HORN_SDF_POCKET = True             # off only while fixes/gear_horn_set9.py samples the blank for its exact cut
# Set 9 as first printed (2026-10-10), Zach: the horn's own screw (the 3 mm head x 5 one in his horn kit) can't reach
# through the gear's floor, and the zero-offset pocket was so tight the horn flew out and hit him in the eye. So the
# floor is open under the horn's centre, and the stock screw goes up through it, seats on the horn's web as the horn
# was made for, and gets 4.5 mm into the spline; the horn carries the gear in its pocket, and the floor plate sits 0.5
# under the gear. The pocket gets HORN_FIT a side, two gears to try. Superseded: the M2 x 6 from under a 1.5 floor
# (M2_SCREW_L 6.0), and zero offset on this horn.
HORN_FITS = (0.10, 0.15)           # per side, the pocket's outline grown in plan; the floor stays at the horn's face
HORN_FIT = HORN_FITS[0]            # Zach, 2026-10-11: 0.10 "fits well enough with still being a bit tight which is
                                   # good"; 0.15 is too loose. 0.10 it is.
HORN_SCREW_L = 5.0                 # the horn kit's machine screw, under the head (his listing: 3 mm head, 5 long)
HORN_CB_R, HORN_CB_H = 2.25, 0.95  # Arm02's own counterbore for that head (the STEP)
GEAR_HOLE_R = 2.5                  # through the gear's floor, round the horn's counterbore: head and driver pass
# The wires' way through, for drawing only: the widest path checks/wire_route.py row 7's flood fill finds
# with the ribbon centred. From the cradle's hole (Z 13), past the ribbon's -Y edge inside the cradle's
# groove, down the notch behind the ribbon, into the funnel.
HANDOVER_PTS_SET5 = [(-2.0, -7.0, 13.0), (-2.4, -9.4, 11.4), (-3.6, -9.4, 8.8), (-4.2, -7.8, 6.8), (-4.2, -5.6, 4.6),
                     (-4.2, -3.4, 2.4), (-5.2, -1.4, 0.4), (-6.2, -0.4, -2.0), (-6.6, -0.2, -4.8)]
# Set 6: the same way down to the notch's foot, then down the cone toward its point; the hole (DRUM_WIRE)
# carries on from (0, 0, -13). Ends short of that point so a drawing can join the two without a repeat.
HANDOVER_PTS = HANDOVER_PTS_SET5[:6] + [(-4.0, -2.6, -3.0), (-3.2, -1.8, -8.5), (-1.6, -0.8, -11.8)]

# Set 8 (2026-10-09): Zach, "threading the wires through it is a massive pain", stuck at the cone. Set 6's hole
# starts at the cone's point and bends from straight down to sideways (~90 deg) out of sight, and stiff copper
# can't take the bend. Now a straight vertical hole starts where the wires already come down (under the handover's
# drop, behind the ribbon) and leaves through the drum's underside, where an open groove takes them out into the
# lane. Push straight through, bend them into the groove by hand, drop the drum in. Both print without support
# (the drum prints upside down: the hole stands vertical, the groove opens upward). Superseded: DRUM_WIRE (set 6).
STRAIGHT_WIRE = True
DROP_R, DROP_DEG = 8.0, -127.0     # the hole's axis, X -4.8 Y -6.4: 1.0 off the handover's drop at Z 4.6, behind
                                   # the ribbon (X 0 below Z 7); its wall 0.5 off the barrel, 1.5 inside the face
DROP_XY = _pol(DROP_R, DROP_DEG, 0.0)[:2]
DROP_Z1 = 1.0                      # its top: past the cone and the notch floor, into the bore's air
GROOVE_Z1 = LANE_Z1 - 0.2          # -21.0, the groove's roof: inside the lane's height, under the shelf
# Out from the hole and round CW, so the wire leaves the face already turning the way its inner wrap runs (set 6's
# hole did too). Past r 12 it is in the lane's air: the cut overruns the face.
GROOVE_PTS = [_pol(DROP_R, DROP_DEG, 0.0), _pol(9.6, -133, 0.0), _pol(11.0, -140, 0.0), _pol(12.4, -147, 0.0),
              _pol(14.0, -153, 0.0)]
GROOVE_LINE2 = _centripetal(GROOVE_PTS)
# The wires' centrelines, for the checks and drawings: down the hole's axis, then along the groove at the lane's
# height. The groove's floor is the base's lane floor, 0.4 under the drum.
DROP_LINE = np.array([(DROP_XY[0], DROP_XY[1], z) for z in np.arange(-5.0, LANE_ZC - 0.01, -0.5)])
GROOVE_LINE = GROOVE_LINE2 + np.array([0.0, 0.0, LANE_ZC])


def straight_wire(p):
    """Set 8's way through the drum: the vertical hole, and the groove open on the drum's underside. Both run 0.9
    past the underside (Z -23.9) into the lane's air."""
    hole = cyl_z(p, DROP_XY[0], DROP_XY[1], WIRE_R, LANE_Z0 - 0.5, DROP_Z1)
    flat = (p[0], p[1], np.zeros(np.broadcast(*p).shape))
    groove = np.maximum(wire_hole(flat, GROOVE_LINE2), np.maximum((LANE_Z0 - 0.5) - p[2], p[2] - GROOVE_Z1))
    return np.minimum(hole, groove)


def _hole_xy(z):
    """The drum hole's centreline (x, y) at height z, along its top run (it drifts as it goes down)."""
    top = DRUM_WIRE[DRUM_WIRE[:, 2] > -12.0][::-1]
    return np.interp(z, top[:, 2], top[:, 0]), np.interp(z, top[:, 2], top[:, 1])


def _mouth():
    """Where the drum's wire hole crosses the bore's floor."""
    return _hole_xy(CH_Z1 - 0.5)


def wire_notch(p):
    """The notch in the bore wall: an annular sector from r 8 (overruns the bore) to NOTCH_R, open at the
    top face, over a floor sloping NOTCH_FLOOR_DEG down toward the bore."""
    a0, a1 = np.radians(NOTCH_A0), np.radians(NOTCH_A1)
    r = np.hypot(p[0], p[1])
    wedge = np.maximum(p[0] * np.sin(a0) - p[1] * np.cos(a0), -p[0] * np.sin(a1) + p[1] * np.cos(a1))
    radial = np.maximum((BORE_R - 1.0) - r, r - NOTCH_R)
    t = np.radians(NOTCH_FLOOR_DEG)
    floor = ((NOTCH_Z0 - np.tan(t) * (NOTCH_R - r)) - p[2]) * np.cos(t)
    return np.maximum(np.maximum(radial, wedge), np.maximum(floor, p[2] - (BASE_Z + 1.0)))


def wire_funnel(p):
    """A cone round the drum hole's own centreline: FUNNEL_R at the bore floor, WIRE_R FUNNEL_D below. It
    carries on narrowing for 0.6 more, inside the hole, so it leaves no ledge where it meets it, and runs
    straight up 1 mm into the bore's air (a cut overruns the face it passes through)."""
    z0 = CH_Z1 - 0.5
    cx, cy = _hole_xy(p[2])
    slope = (FUNNEL_R - WIRE_R) / FUNNEL_D
    rz = np.minimum(FUNNEL_R, WIRE_R + slope * (p[2] - (z0 - FUNNEL_D)))
    d = (np.hypot(p[0] - cx, p[1] - cy) - rz) * np.cos(np.arctan(slope))
    return np.maximum(d, np.maximum((z0 - FUNNEL_D - 0.6) - p[2], p[2] - (z0 + 1.0)))


def bore_cone(p):
    """The bore's floor since set 6: a cone CONE_DEG off vertical from the bore's wall at BORE_Z0 down to a
    point on the axis. Runs 0.5 up into the straight bore, so the two cuts overlap."""
    a = np.radians(CONE_DEG)
    return np.maximum(np.hypot(p[0], p[1]) * np.cos(a) - (p[2] - CONE_APEX_Z) * np.sin(a), p[2] - (BORE_Z0 + 0.5))


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
    return (_well_set7 if INSERT else _well_set5)(p, features)


def _well_set7(p, features=True):
    """Set 7's well (INSERT): no shelf and no cup wall, which are `shelf_ring` now; the lane wall's ledge the ring
    sits on, with the rib that keys it; a skirt and a 30 deg cone under the deck ring; the ribbon's slit through
    both. Set 11 (SHELF_MERGED): the lane filled and the ring's cup wall built on, so no ring, rib, boss or exit hole."""
    ro = SKIRT_IR + SKIRT_T
    lane_wall = ring_z(p, LANE_R, ro, FLOOR_Z, LANE_Z1 + 0.5, 0.3)   # its top inside SKIRT_IR is the ledge
    if HOLLOW_AXIS:   # set 10: the 6704's seat, open at the top, a lip under its outer ring
        floor = ring_z(p, B6704_SEAT_R, ro, FLOOR_Z, LANE_Z0, 0.6)
        sleeve = U(ring_z(p, B6704_SEAT_R, B6704_WALL_R, B6704_LIP_Z0, LANE_Z0, 0.4),
                   ring_z(p, B6704_LIP_R, B6704_WALL_R, B6704_LIP_Z0, B6704_Z0, 0.2))
    elif BARREL_688:   # set 9: the 688's seat, open at the top, a lip under its outer race
        floor = ring_z(p, B688_SEAT_R, ro, FLOOR_Z, LANE_Z0, 0.6)
        z0 = B688_Z0 - B688_LIP_T
        sleeve = U(ring_z(p, B688_SEAT_R, B688_WALL_R, z0, LANE_Z0, 0.4), ring_z(p, B688_LIP_R, B688_WALL_R, z0, B688_Z0, 0.2))
    else:
        floor = ring_z(p, JOURNAL_R, ro, FLOOR_Z, LANE_Z0, 0.6)
        sleeve = ring_z(p, JOURNAL_R, JOURNAL_R + 2.75, JOURNAL_Z0, LANE_Z0, 0.4)
    # the boss 3 taller than set 5's (to Z -15.5): the exit hole's pointed top reaches -17.55, and broke out of
    # the old top at -18.5 leaving a 0.1 fin (checks/wire_route.py row 6). Set 11: gone with the hole.
    boss = rbox(at_angle(p, WIRE_EXIT_DEG), (WELL_IR + 1.0, -6.5, FLOOR_Z), (LANE_R + 5.0, 6.5, -15.5), 1.5)
    if SHELF_MERGED:
        boss = np.full(np.broadcast(*p).shape, 1e3)
    skirt = ring_z(p, SKIRT_IR, ro, LANE_Z1, DECK_Z1, 0.0)
    deck = ring_z(p, SKIRT_IR, BOSS_R, DECK_Z0, DECK_Z1, 0.6)
    seat = ring_z(p, SEAT_BORE_R, BOSS_R, DECK_Z0, BRG_Z1, 0.6)
    # Under the deck ring, from the skirt out to its rim: a cone CONE_OUT_DEG off vertical. Where the servo's
    # tower stands it isn't needed (the tower carries the deck there) and would fill the servo's pocket, so it
    # stops 1 mm inside the tower's outline. (2 mm left a loose speck at the tower's rounded top corner; 1 mm leaves
    # a few support lines there, outside, where they come off.)
    a = np.radians(CONE_OUT_DEG)
    r = np.hypot(p[0], p[1])
    cone = np.maximum(((DECK_Z0 - (BOSS_R - r) / np.tan(a)) - p[2]) * np.sin(a), r - BOSS_R)
    cone = np.maximum(cone, np.maximum((ro - 0.5) - r, p[2] - (DECK_Z0 + 0.5)))
    tower = box(p, (SV_X0 - 2.5, SV_YC - TAB_SPAN / 2 - 1.5, -60.0), (60.0, SV_YC + TAB_SPAN / 2 + 1.5, 60.0))
    cone = np.maximum(cone, -tower)
    s = U(lane_wall, floor, deck, seat, sleeve, boss, skirt, cone)
    room = cyl_z(p, 0, 0, SKIRT_IR, LANE_Z1, BRG_Z1 + 1.0)           # where the ring goes in and sits
    lane = ring_z(p, DRUM_R - 1.0, LANE_R, LANE_Z0, LANE_Z1 + 0.5, 0.0)
    relief = ring_z(p, SKIRT_IR - 0.5, RELIEF_R1, DECK_Z1 - RELIEF_D, DECK_Z1 + 1.0, 0.0)
    s = np.maximum(s, -U(room, lane, relief))
    if SHELF_MERGED:   # set 11: the lane filled to the ribbon's floor, out into the skirt; the cup wall on it
        fill = ring_z(p, PASS_R, SKIRT_IR + 0.2, LANE_Z0 - 0.2, CH_Z0, 0.0)
        cup = ring_z(p, RING_IR, RING_IR + RING_T, CH_Z0 - 0.4, DECK_Z1 - 0.4, 0.4)   # as the ring's: 0.4 under the hub
        s = U(s, fill, cup)
    else:
        rib = box(at_angle(p, KEY_DEG), (SKIRT_IR - KEY_D, -KEY_W / 2, LANE_Z1 - 0.5), (SKIRT_IR + 0.5, KEY_W / 2, LANE_Z1 + KEY_H))
        s = U(s, rib)
    if features:
        # The ribbon's way out at EXIT_DEG: a slit from inside the ring's room out through the skirt and the cone.
        # Its roof leans CONE_OUT_DEG off vertical; inside RELIEF_R1 it runs open through the top instead.
        q = at_exit(p)
        a = np.radians(CONE_OUT_DEG)
        roof = np.abs(q[1]) * np.cos(a) + (q[2] - (BAND_Z1 + 0.4)) * np.sin(a) - (SLIT_W / 2) * np.cos(a)
        roof = np.where(-q[0] < RELIEF_R1 + 0.1, q[2] - (BRG_Z1 + 1.0), roof)
        slit = np.maximum(np.maximum(-(BOSS_R + 3.0) - q[0], q[0] + (SKIRT_IR - 0.5)),
                          np.maximum(np.maximum(np.abs(q[1]) - SLIT_W / 2, roof), (LANE_Z1 + 0.3) - q[2]))
        if SHELF_MERGED:   # set 11: no exit hole; the ring's ribbon notch through the cup wall, open at the top
            notch = box(at_exit(p), (-(RING_IR + RING_T + 1.0), -WINDOW_W / 2, BAND_Z0 - 0.4),
                        (-(RING_IR - 1.0), WINDOW_W / 2, DECK_Z1 + 1.0))
            s = np.maximum(s, -U(slit, notch))
        else:
            s = np.maximum(s, -U(slit, teardrop_hole(p, BASE_WIRE)))
    return s


def teardrop_hole(p, line, r=WIRE_R):
    """wire_hole for a level centreline, with a pointed top CONE_OUT_DEG off vertical, so it prints without
    support. Its point stands 2r over the centre."""
    d3 = wire_hole(p, line, r)                                    # round, by the capsule chain
    z0 = line[:, 2].mean()
    w = p[2] - z0
    dxy = np.sqrt(np.maximum((d3 + r) ** 2 - w ** 2, 0))           # horizontal distance to the line
    a = np.radians(CONE_OUT_DEG)
    point = np.maximum(-w, dxy * np.cos(a) + w * np.sin(a) - r)
    return np.minimum(d3, np.where(d3 < 1e2, point, 1e3))


def shelf_ring(p, features=True):
    """Set 7: the shelf (the ribbon's floor and the wire lane's ceiling) and the ribbon cup's wall, as one part
    that drops in from above onto the lane wall's ledge. It prints shelf face down and overhangs nowhere. A
    notch in the shelf's rim fits the rib on the ledge."""
    shelf = ring_z(p, SHELF_R0, RING_OR, LANE_Z1, CH_Z0, 0.2)
    cup = ring_z(p, RING_IR, RING_IR + RING_T, CH_Z0 - 0.4, DECK_Z1 - 0.4, 0.4)   # top 0.4 under the hub, as before
    # the notch the ledge's rib keys into
    key = box(at_angle(p, KEY_DEG), (SKIRT_IR - KEY_D - KEY_SLIDE, -KEY_W / 2 - KEY_SLIDE, LANE_Z1 - 1.0),
              (RING_OR + 1.0, KEY_W / 2 + KEY_SLIDE, CH_Z0 + 1.0))
    s = np.maximum(U(shelf, cup), -key)
    if not features:
        return s
    # the ribbon's way out through the cup wall: the old slot, open at the top so nothing bridges
    notch = box(at_exit(p), (-(RING_IR + RING_T + 1.0), -WINDOW_W / 2, BAND_Z0 - 0.4),
                (-(RING_IR - 1.0), WINDOW_W / 2, DECK_Z1 + 1.0))
    # The wires' exit hole starts under the shelf (set 5's shelf was cut there too). It is kept out of the cup
    # wall, the ribbon's, from the wall's foot up; under the foot the shelf is cut, and the wall bridges the notch.
    r = np.hypot(p[0], p[1])
    wall = np.maximum(np.abs(r - (RING_IR + RING_T / 2)) - (RING_T / 2 + 0.3), (CH_Z0 - 0.4) - p[2])
    mouth = np.maximum(teardrop_hole(p, BASE_WIRE), -wall)
    return np.maximum(s, -U(notch, mouth))


def fixed(p, features=True):
    """Everything fixed round the coil, as assembled: the printed base, plus set 7's ring."""
    return U(base(p, features), shelf_ring(p, features)) if RING_PART else base(p, features)


def _well_set5(p, features=True):
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
    barrel = cyl_z(p, 0, 0, AX_NECK_R if HOLLOW_AXIS else NECK_R if BARREL_688 else BARREL_R,
                   AX_JOINT_Z if HOLLOW_AXIS else G_Z1, LANE_Z0 + DRUM_LIFT)   # set 10: it ends on the gear's hub
    if HOLLOW_AXIS:   # set 10: the barrel's end face is the gear's plate; no stub
        seat = np.full(np.broadcast(*p).shape, 1e3)
    elif SEAT_SQUARE:
        seat = np.maximum(rsquare(p, SQ_H, SQ_RC), np.maximum(SEAT_Z0 - p[2], p[2] - (G_Z1 + 0.5)))
    else:
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
        # the gear screw's pilot, 1 mm past its tip. Set 8: only above the step; a clear hole through the seat
        if HOLLOW_AXIS:   # set 10: the wires' hole down the axis, and the three M2s' pilots, 1 mm past their tips
            tip = G_Z0 + AX_SCREW_L + 1.0
            cuts = [cyl_z(p, 0, 0, AX_WIRE_R, AX_JOINT_Z - 1.0, AX_WIRE_Z1), bore, anchor]
            cuts += [cyl_z(p, x, y, AX_PILOT_R, AX_JOINT_Z - 1.0, tip) for x, y in ax_screws()]
        elif SCREW_THRU:
            cuts = [cyl_z(p, 0, 0, M3_PILOT, G_Z1, G_Z0 + SCREW_L + 1), cyl_z(p, 0, 0, M3_CLEAR, SEAT_Z0 - 1, G_Z1 + 0.2)]
        else:
            cuts = [cyl_z(p, 0, 0, M3_PILOT, SEAT_Z0 - 1, G_Z0 + SCREW_L + 1)]
        if not HOLLOW_AXIS:
            cuts += [bore, anchor, straight_wire(p) if STRAIGHT_WIRE else wire_hole(p, DRUM_WIRE)]
        if CONE:
            cuts.append(bore_cone(p))
        if NOTCH:
            cuts += [wire_notch(p)] + ([] if CONE else [wire_funnel(p)])
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
    if INSERT:   # set 7: the tower reached in to X 21.4, into the shelf ring's room
        s = np.maximum(s, -cyl_z(p, 0, 0, SKIRT_IR, LANE_Z1, BRG_Z1 + 1.0))
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
    # The drum's barrel runs up through the shell's top slab on its way to the can. Set 10: as wide as the 6704's seat,
    # from the cavity's roof (the well's housing and lip stand in the hole).
    barrelway = (cyl_z(p, 0, 0, B6704_SEAT_R, B6704_LIP_Z0 - 0.1, FLOOR_Z + 1) if HOLLOW_AXIS
                 else cyl_z(p, 0, 0, JOURNAL_R + 3.35, G_Z1, FLOOR_Z + 1))
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
    cuts += [cyl_z(p, x, 0, AX_FLOOR_HOLE_R if HOLLOW_AXIS and x == 0.0 else FLOOR_HOLE_R, BAY_Z0 - 1, SPLIT_Z + 1)
             for x in (0.0, CENTRE)]   # set 10: the drum's is wider, for the gear's three screw heads to turn in
    return np.maximum(s, -U(*cuts))


def base(p, features=True):
    """The printed fixed part: the well and the bay fused. Each keeps its own cuts, so the
    servo pocket does not bite the well's bearing seat."""
    return U(well(p, features), bay(p, features))


def gear_out(p, features=True):
    """The drum's gear, off the drum since 2026-09-27. Square bore (set 8; a D before) onto the barrel's seat
    from below, a web at the bottom for the M3 head to pull up on."""
    s = gear(p, R_OUT_G - GEAR_GAP, N_OUT, 0.0, G_Z0, G_Z1)
    s = np.maximum(s, np.maximum(G_Z0 - p[2], p[2] - G_Z1))
    if HOLLOW_AXIS:   # set 10: a solid hub up to the barrel's end, AX_LIFT under the 6704's inner ring
        # its foot sinks 0.2 into the gear's top (0.3 over the input gear's top face, GIN_Z1), so it fuses
        s = U(s, cyl_z(p, 0, 0, AX_HUB_R, G_Z1 - 0.2, AX_JOINT_Z))
    if not features:
        return s
    if HOLLOW_AXIS:   # the wires' hole, and the three screws' clear holes, gear and hub; the heads stay under the gear
        cuts = [cyl_z(p, 0, 0, AX_WIRE_R, G_Z0 - 1, AX_JOINT_Z + 1)]
        cuts += [cyl_z(p, x, y, AX_CLEAR_R, G_Z0 - 1, AX_JOINT_Z + 1) for x, y in ax_screws()]
        return np.maximum(s, -U(*cuts))
    if SEAT_SQUARE:
        d = np.maximum(rsquare(p, SQ_H + SQ_FIT, SQ_RC + SQ_FIT), np.maximum(WEB_Z1 - p[2], p[2] - (G_Z1 + 1)))
    else:
        d = np.maximum(cyl_z(p, 0, 0, SEAT_R + SLIDE, WEB_Z1, G_Z1 + 1), p[0] - SEAT_FLAT - SLIDE)
    hole = cyl_z(p, 0, 0, M3_CLEAR, G_Z0 - 1, WEB_Z1 + 0.1)
    return np.maximum(s, -U(d, hole))


def screw_out(p, features=True):
    """The M3 button head holding gear_out (x 12 since set 8), as hardware for the checks. Set 10: the three M3 x 16."""
    if HOLLOW_AXIS:
        # shanks at the pilot's radius, as the M3's: the thread cutting into the barrel is meant
        return U(*[U(cyl_z(p, x, y, AX_HEAD_R, G_Z0 - AX_HEAD_H, G_Z0),
                     cyl_z(p, x, y, AX_PILOT_R, G_Z0, G_Z0 + AX_SCREW_L)) for x, y in ax_screws()])
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


def horn_sdf(p):
    """Set 9: the horn's outline, a hub disc and a bar along Y, from its flat face up (for checks and views only; the
    print's pocket is the exact Arm02 outline, cut in OCC). Its arms taper; the bar is drawn at their widest."""
    q = (p[0] - CENTRE, p[1], p[2])
    hub = cyl_z(q, 0, 0, HORN_HUB_D / 2, HORN_FACE_Z, HORN_FACE_Z + HORN_H)
    bar = rbox(q, (-2.3, -HORN_LEN / 2, HORN_FACE_Z), (2.3, HORN_LEN / 2, HORN_FACE_Z + HORN_ARM_T), 0.5)
    return U(hub, bar)


def horn(p, features=True):
    """Set 9: the servo's double-arm horn as seated on the spline (hardware, for the checks)."""
    return horn_sdf(p)


def gear_in(p, features=True):
    # The hub used to run 2 mm ABOVE the gear and straight into the servo's case. It hangs
    # below instead; the shaft still gets 3.5 mm of engagement.
    z1 = GIN_Z1 if HORN_GEAR else G_Z1
    g = gear(p, R_IN_G, N_IN, CENTRE, G_Z0, z1, phase=np.pi)
    hub = cyl_z(p, CENTRE, 0, 5.0, G_Z0, z1)       # flush both ends: hanging 1.5 below put
                                                   # it through the bay's floor, 28 mm3 of it
    s = smin(g, hub, 0.8)
    # Trim both faces flat: the smooth min bulged ~0.2 below G_Z0 round the hub, so the gear sat on
    # a ring and its face floated 0.05-0.3 mm off the bed (2026-09-27, print check).
    s = np.maximum(s, np.maximum(G_Z0 - p[2], p[2] - z1))
    if not features:
        return s
    if HORN_GEAR:
        # Set 9: the horn's pocket from its flat face up through the top face (overrun 1), HORN_FIT a side, and the
        # floor open under the horn's counterbore for its own screw.
        q = (p[0] - CENTRE, p[1], p[2])
        cuts = [cyl_z(q, 0, 0, GEAR_HOLE_R, G_Z0 - 1, HORN_FACE_Z + 0.5)]
        if HORN_SDF_POCKET:
            cuts.append(np.maximum(horn_sdf((p[0], p[1], np.minimum(p[2], HORN_FACE_Z + 0.5))) - HORN_FIT,
                                   HORN_FACE_Z - p[2]))   # the outline, carried straight up
            cuts[-1] = np.maximum(cuts[-1], p[2] - (z1 + 1.0))
        return np.maximum(s, -U(*cuts))
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
    if not SPLINE_GEAR:
        horn = horn_at(p, CENTRE, G_Z1 - HORN_D, G_Z1 + 0.5)
        shank = cyl_z(p, CENTRE, 0, M2_CLEAR, G_Z0 - 1, G_Z1 - HORN_D + 0.1)
        cbore = cyl_z(p, CENTRE, 0, M2_HEAD, G_Z0 - 1, G_Z1 - HORN_D - HORN_ROOF)
        return np.maximum(s, -U(horn, shank, cbore))
    # Set 6: the spline straight in (SPL_* above). Bore from the top face down to the spline's tip, the lip
    # under it, the screw's clearance hole through the lip, the head's counterbore up from the bottom.
    tip = SV_Z0 - SV_SHAFT                                         # -34.9
    q = (p[0] - CENTRE, p[1], p[2])
    r = np.hypot(q[0], q[1])
    lead = np.maximum((r - (SPL_BORE_R + SPL_LEAD + (q[2] - G_Z1))) * np.cos(np.pi / 4), q[2] - (G_Z1 + 1))
    bore = cyl_z(q, 0, 0, SPL_BORE_R, tip, G_Z1 + 1)
    hole = cyl_z(q, 0, 0, SPL_HOLE_R, tip - SPL_LIP - 0.2, tip + 0.2)
    cbore = cyl_z(q, 0, 0, SPL_CB_R, G_Z0 - 1, tip - SPL_LIP)
    return np.maximum(s, -U(bore, lead, hole, cbore))


def bearing(p, features=True):
    return ring_z(p, HUB_R, BRG_OR, BRG_Z0, BRG_Z1, 0.4)


def bearing688(p, features=True):
    """Set 9: the 688 round the barrel, in the base's seat (hardware, for the checks and the views)."""
    return ring_z(p, B688_ID / 2, B688_OD / 2, B688_Z0, B688_Z1, 0.3)


def bearing6704(p, features=True):
    """Set 10: the 6704 round the hollow barrel, in the base's seat (hardware, for the checks and the views)."""
    return ring_z(p, B6704_ID / 2, B6704_OD / 2, B6704_Z0, B6704_Z1, 0.3)


def ax_screws():
    """Set 10: the three gear screws' axes (x, y), round the wire hole."""
    return [(AX_SCREW_R * np.cos(np.radians(a)), AX_SCREW_R * np.sin(np.radians(a))) for a in AX_SCREW_DEG]


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
    'bearing688': (bearing688, (-9, -9, B688_Z0 - 1), (9, 9, B688_Z1 + 1), 0.12, 5000),
    'horn':     (horn,     (CENTRE - 5, -HORN_LEN / 2 - 1, HORN_FACE_Z - 1), (CENTRE + 5, HORN_LEN / 2 + 1,
                            HORN_FACE_Z + HORN_H + 1), 0.15, 5000),
    # 2026-09-27: what prints is base (= well + bay), floor and gear_out; well and bay stay as
    # separate meshes for the viewer, the sim and the pair checks.
    'base':     (base,     (-33, -33, BAY_Z0 - 1),
                           (CENTRE + R_IN_G + 10, 33, BRG_Z1 + 1), 0.34, 60000),
    'floor':    (floor,    (-17, -R_IN_G - 7, BAY_Z0 - 1), (CENTRE + R_IN_G + 7, R_IN_G + 7, SPLIT_Z + 1),
                           0.25, 12000),
    'gear_out': (gear_out, (-R_OUT_G - 3, -R_OUT_G - 3, G_Z0 - 1),
                           (R_OUT_G + 3, R_OUT_G + 3, (B6704_Z0 if HOLLOW_AXIS else G_Z1) + 1), 0.20, 9000),
    'tab_block': (tab_block, (SV_X0 - 3, TB_Y0 - 1, TAB_Z0 - TB_H - 1), (SV_X1 + 3, TB_Y1 + 1, TAB_Z0 + 1), 0.15, 4000),
    'screw_out': ((screw_out, (-9, -9, G_Z0 - AX_HEAD_H - 1), (9, 9, G_Z0 + AX_SCREW_L + 1), 0.12, 3000)
                  if HOLLOW_AXIS else
                  (screw_out, (-4, -4, G_Z0 - M3_BUTTON_H - 1), (4, 4, G_Z0 + SCREW_L + 1), 0.20, 3000)),
    # set 10 (2026-10-11): the 6704 round the hollow barrel, in place of the 688
    'bearing6704': (bearing6704, (-15, -15, B6704_Z0 - 1), (15, 15, B6704_Z1 + 1), 0.15, 6000),
    # set 7 (2026-10-04): the shelf and the ribbon cup's wall, dropped into the base from above
    'shelf_ring': (shelf_ring, (-26, -26, LANE_Z1 - 1), (26, 26, DECK_Z1 + 1), 0.20, 24000),
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
