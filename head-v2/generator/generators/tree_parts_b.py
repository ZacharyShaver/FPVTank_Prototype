"""Variant B: the tilt servo lives INSIDE the ball, and the mount is ONE grown nest.

The servo's case rotates with the ball; its shaft splines onto a horn carried by a fixed
post that reaches in from the +Y side. Because the servo left the arms, there are no arms:
the trunk rises out of the pan pedestal and flares straight into a cupped nest whose two
side walls close over into the bearing collars. Trunk, nest and both collars are one
continuous organic body -- not a stem with pods and a hoop bolted to it.

The nest's mouth is a 180 deg window, rolled down 35 deg, so the ball can look from
35 deg below the horizon to 145 deg up. Everything else -- the whole back and underside --
is shell, and the gap the shell holds behind the ball is the rolling-loop track the camera
ribbon runs in. The three servo leads are taped alongside the ribbon and roll with it, so
there is no second channel and no fold anywhere in the run.

    A (servo in the arm)   107 x 79 x 58, fork + 2 caps + shroud
    B (servo in the ball)   68 x 72 x 83, ONE nest + 2 flush flange plates

The mouth is cut wider than the travel (MOUTH_DOWN/MOUTH_UP): at the end of its swing the lens
looks along the rim, so the rim has to sit outside the field of view, not merely outside the
bezel. tree_parts_b_check.py tests those two things separately.

Concept geometry for comparison: viewer meshes + Fusion OBJs, not a print set.
Reuses the SDF kit and mesh pipeline from tree_parts.py.

    python tree_parts_b.py
"""
import os, json, base64
import numpy as np
from skimage import measure
import tree_parts as A
from tree_parts import (smin, box, rbox, _cyl, cyl_x, cyl_y, cyl_z, U, ring_z, teardrop2d,
                        sample, project, unfold, decimate, report, quiet, mesh_set)

OUT = os.path.join(A.D, '..', 'tree-parts-b')

# ------------------------------------------------------------------ parameters
H = 52.0                       # tilt axis above deck: set by the bottom of the ribbon track,
                               # which has to stay above the fork's floor at full up-tilt
R_IN, R_BALL = 29.5, 30.7      # set by the servo's far corner (in-plane radius 18) at Y 23
FLAT = 24.5                    # ball truncation / hub faces
BOARD_X0, BOARD_X1 = 8.0, 10.0 # board moved forward to clear the servo behind it.
                               # 2.0 thick, MEASURED by Zach 2026-09-19 (was 1.6, assumed)
# MEASURED by Zach 2026-09-19: "the lens comes 21 mm off the board, -2 for the board itself".
# So 19.0 from the board's FRONT face, putting the lens tip at X 29.0. The model had the lens
# end stopping at BEZEL_X0 = 26.0 -- a 16.4 mm stand-off -- so the camera reaches 3.0 mm further
# forward than anything here assumed. Used by tree_parts_b_check.py's camera_solid.
CAM_STANDOFF = 19.0            # board front face -> lens tip              MEASURED
BOARD_Y = 18.0                 # board half-width along the tilt axis -- ASSUMED, measure
HOLDER_R, HOLDER_X1 = 10.5, 18.6
# The camera END is 14-15 mm across (Zach, 2026-09-18) -- the lens bore was cut for 12.4 and is
# far too small. Take the 15 and give it 0.5 all round. The bezel keeps its old 2.3 mm of wall.
CAM_END_W = 15.0                           # width at the camera's lens end   MEASURED-ish
# Zach, 2026-09-19: "just make a hole on the end, don't try to make a tunnel to fit the camera.
# too much stuff to measure on the front, it's not worth making a perfect form casing for it,
# just a hole in the ball."
# So the raised bezel tube is GONE. It was a Ø16.0 bore through a collar standing 1.9 mm proud
# of the sphere, and the moment the measured lens stand-off went in (19.0, so the lens tip sits
# at X 29.0 instead of the 26.0 the tube assumed) the corners of a 15 mm square housing fouled
# its wall by 94 mm3. The front is now the plain sphere with one oversize bore through it.
# LENS_R clears the corners of a 15 mm SQUARE housing -- half-diagonal 10.61 -- by 0.9, so the
# front fits whatever the camera turns out to be without anyone measuring it. That is the point:
# CAM_END_W is no longer load-bearing anywhere.
LENS_R = 11.5                              # a plain Ø23.0 hole, nothing else
LENS_TIP_X = BOARD_X1 + CAM_STANDOFF       # = 29.0, and 0.5 mm clear of the shell's inner face
BALL_CLEAR = 1.5
# Axial gap between the ball's flat face and the nest, set BY MEASUREMENT not by arithmetic: the
# carve is a SMOOTH max (k=1.5) so it rounds back, and the ball's own blends used to stand proud
# of FLAT (fixed at the end of ball_body). Do not "simplify" this to the gap you want -- re-measure
# with the signed sweep in cradle-audit.md section 1, which must stay POSITIVE everywhere.
BALL_CLEAR_Y = 0.60
# What the ball sweeps at the front as it tilts, which is what the nest's lips have to stand off.
# With the bezel gone it is just the sphere: this was hypot(BEZEL_X1, BEZEL_R) + 0.8 = 34.99, so
# the mouth was flaring 3.5 mm wider than the ball ever needed.
FRONT_SWEEP = R_BALL + 0.8

SW, SL, S2S, FIT = A.SERVO_W, A.SERVO_L, A.SHAFT_TO_END, A.FIT
# The servo sits 5.0 mm DEEPER than it did. That is not a preference: the measured boss-and-spline
# stack is 9 mm, not the 6 mm the datasheet implied, and the horn's hub adds 3 more on top. With the
# case top at 23.0 the horn's disc landed at Y 31..33 -- past the post's own outboard face at 32.2 --
# which left a 1.4 mm post and a pocket that breached the flange. Dropping the case 5.0 puts the
# disc back at 26..28 and gives the post 6.4 mm of shaft through the bearing. The case base now
# crosses the seam into the -Y half, so that half carries a real pocket, not just a pad.
SERVO_Y0, SERVO_Y1 = -5.5, 18.0            # case bottom (past the seam) .. case top (shaft face)
TAB_T = 3.0                                # servo tab thickness -- MEASURED by Zach 2026-09-18
TAB_Y = SERVO_Y1 - A.TAB_FROM_TOP          # underside of the tabs, inside the ball
ZC = H + (SL / 2 - S2S)

# The tilt servo had NOTHING fastening it (Zach spotted it, 2026-09-19). The tab recess that was
# supposed to stop it lifting toward the post removed 0.00 mm3 of a 1452 mm3 box -- it was cut
# entirely inside the ball's cavity, so it was never a feature at all. The servo was located in X
# and Z by its pocket, sat on the -Y pad, and had nothing above it: it could float 4 mm toward the
# post, taking the load on the horn instead of the mount.
# Two bosses now rise to the underside of the servo's own mounting tabs and take an M2 up through
# each tab hole -- the same way the PAN servo is held in roots(). The tab is clamped between the
# screw head below and the boss face above.
TAB_BOSS_R = 3.0                           # boss around a 1.7 mm pilot: 2.15 mm of wall
TAB_BOSS_Y0 = TAB_Y + TAB_T                # = 14.5, the face the tab lands on
TAB_BOSS_DEPTH = 5.4                       # thread depth, 2.7x the M2 diameter
TAB_BOSS_BLEND = 2.8                       # fillet at the root -- see ball_body()
TAB_Z = [ZC - A.TAB_PITCH / 2, ZC + A.TAB_PITCH / 2]   # = 43.75 and 71.25, both at X 0

POST_R, POST_BORE = 7.7, 8.0               # fixed drive post, and the ball's stub bore around it.
                                           # Both grew: the post head has to hold a horn pocket, and
                                           # everything it carries must still pass through the stub.
# MEASURED by Zach 2026-09-18, and it replaced a datasheet inference that was 3 mm short.
BOSS_H = 5.0                               # case top -> top of the black boss          MEASURED
SPLINE_PROUD = 4.0                         # how far the metal spline stands off the boss  MEASURED
SPLINE_STACK = BOSS_H + SPLINE_PROUD       # case top -> spline tip  = 9.0, not the 6.0 assumed
HORN_D_B = 2.0                             # horn ARM/disc thickness                    MEASURED
HORN_HUB_H = 5.0                           # horn thickness at the centre screw          MEASURED
HORN_HUB_D = 7.0                           # diameter of that raised hub                 MEASURED
# The hub stands proud on the side FACING THE SERVO (Zach, 2026-09-18), so it swallows the boss and
# the post only ever meets the flat disc -- no stepped pocket needed, just a 2.0 mm one. The hub's
# splined bore is 5.0 deep over a 4.0 spline, so it bottoms on the boss top and the disc rides the
# last 2.0 of it: case top + BOSS_H + HORN_HUB_H - HORN_D_B.
HORN_SEAT = BOSS_H + HORN_HUB_H - HORN_D_B # case top -> underside of the horn disc = 8.0
POST_IN = SERVO_Y1 + HORN_SEAT             # post's inboard face sits on the horn
HORN_L_B = 13.5                            # the horn is TRIMMED to this -- a 34 mm double-arm horn
                                           # cannot pass through a bore the hub can also live in
HUB_R = 9.95                               # ball's hollow stub: rides in the 6704 (OD 19.9 in a
                                           # 20.0 bore -- a light slip, NOT the 20.0 it was)
BRG_OD, BRG_W = A.BRG_OD, A.BRG_W
# The bearing has to be able to REACH its seat. Both collars used to step down to a bore smaller
# than the bearing on BOTH sides of the seat, so the seat was a sealed pocket -- the bearing could
# only ever have got there by being printed in place. The outboard bore is opened to BRG_PASS so it
# goes in from the cap face, and the post and the cap each grow a ring that traps it once it is in.
BRG_PASS = BRG_OD / 2 + 0.15               # outboard bore: the bearing slides through this
BRG_RING_R0, BRG_RING_R1 = 12.2, BRG_OD / 2 - 0.1   # the retaining ring: OUTER RACE ONLY.
                                           # 6704's inner race turns with the ball, so a solid
                                           # boss across the face would rub on it.
POD_Y0 = FLAT + 1.5                        # collar inboard face
BRG_P_Y0, BRG_P_Y1 = POD_Y0 + 0.5, POD_Y0 + 0.5 + BRG_W        # +Y bearing seat
POD_P_Y1 = BRG_P_Y1 + 3.5                                       # +Y outboard face  (= 34.0)
BRG_M_Y0, BRG_M_Y1 = -(POD_Y0 + 0.5), -(POD_Y0 + 0.5 + BRG_W)  # -Y bearing seat
POD_M_Y1 = -POD_P_Y1                                            # -Y outboard face

# ---- the ball's travel, and the nest mouth that has to let it happen
TILT_DOWN, TILT_UP = -35.0, 145.0          # 180 deg of travel, rolled down 35 deg at the bottom
                                           # (angles from +X = straight ahead, toward +Z = up)
# The mouth is cut wider than the travel: at the end of its swing the lens is looking along the
# rim, so the rim has to be outside the field of view, not just outside the bezel.
# The top margin went 5.0 -> 7.5 on 2026-09-19. Two changes pushed the same way: the view cone
# is now launched from the measured LENS TIP at X 29.0 instead of the front of the old bezel at
# 32.6, so it is 3.6 mm further back and wider by the time it reaches the rim; and FRONT_SWEEP
# dropped 34.99 -> 31.5 with the bezel, pulling the lips in. Together they clipped the cone by
# 0.15 mm at full up-tilt. The bottom margin is untouched -- tilt -35 never came close.
MOUTH_DOWN, MOUTH_UP = TILT_DOWN - 8.0, TILT_UP + 7.5

# ---- the rolling loop behind the ball. The U rides at HALF the tilt angle, so 180 deg of
# tilt walks it 90 deg around the back. TRACK_ANG is measured from straight back, + upward.
TRACK_GAP = 8.0                            # ribbon U-turn diameter (radius 4.0 vs the 3.0 minimum)
SHROUD_R0 = R_BALL + TRACK_GAP             # outer face of the gap
# At tilt 0 the loop is seated 2 deg BELOW straight back (a ribbon-length choice at assembly),
# which balances the margin at the two ends: the U then runs -74.5 .. +15.5.
TRACK_ANG_HI = 19.0                        # U at full DOWN-tilt (+ a margin); pulled in far enough
                                           # to leave a wall between the track and the mouth's top lip
TRACK_ANG_LO = -76.0                       # U at full UP-tilt   (+ a margin)
TRACK_MID = (TRACK_ANG_HI + TRACK_ANG_LO) / 2
TRACK_HALF = (TRACK_ANG_HI - TRACK_ANG_LO) / 2

# ---- the ribbon itself. The three servo leads ride beside it in the same slot.
RIBBON_W, RIBBON_T = A.RIBBON_W, A.RIBBON_T
BAND = RIBBON_W / 2 + 3.2                  # half-width of the track and every slot it runs through
TROUGH_W, TROUGH_T, TROUGH_Y = RIBBON_W + 6.0, 3.0, 0.0

# ---- the nest shell
# ---- stiffening the ball. Every internal rib used to meet the shell tangentially, as a butt
# joint with no fillet; BLEND rounds those junctions instead, which is both stronger and what the
# rest of this model already does everywhere else (smin is how the nest is grown).
BLEND = 1.6                                # fillet radius where internal ribs meet the shell
REAR_FILL = 1.2                            # extra wall at the back of the ball, where nothing lives
REAR_X0, REAR_FADE = 13.0, 9.0             # full thickness by X -22, none by X -13
FACE_T = 2.2                               # the two seam face plates, up from 1.6

NEST_T = 3.2                               # wall at the rim
RIM_FLARE = 20.0                           # the lips flare out to clear the bezel; the body between
                                           # them hugs the ball, which is what makes it a nest and
                                           # not a shroud standing off all the way round
NEST_HALF_Y = 28.5                         # out to where the collars take over
# The mouth runs the WHOLE width. Letting it close into a ring near the sides was the first
# attempt, and it made the thing read as three hoops round the ball instead of one cup.
COLLAR_R = 20.5
FLANGE_R, FLANGE_REC = 17.5, 1.8           # the two side plates sit flush in a recess
SCREW_R = 15.5                             # flange screws, clear of the 6704 OD *circle*
# ...but NOT of the bore's teardrop ROOF, which is what 90 deg used to sit on. td_y truncates
# at r*1.15, so the seat's ceiling reaches 15.58 and the pass bore's 15.76 -- both above the
# pilot's inner edge at SCREW_R - M2_PILOT = 14.65. The hole opened straight into the bearing
# pocket and 5.7 of the screw's 6.2 mm of engagement had no thread on its lower side, on BOTH
# collars, while these three screws react the whole tilt torque through the post. The roof only
# exists above z = r/sqrt(2), so rotating the triad 60 deg clears it: 7.65 mm3 of breach -> 0.00.
# Named, not a literal: it hid because it was typed out in SIX places -- four here
# (fork x2, post, cap_minus) and once each in _driver.py and _step.py, which now derive it.
# See ../tree-parts-b/cradle-audit.md section 2.
SCREW_A = [30, 150, 270]                   # flange screw angles, deg from +X toward +Z

CAP_T = A.CAP_T
BASE_Z, PED_R, ROOT_TOP = A.BASE_Z, A.PED_R, A.ROOT_TOP
AXLE_R = 9.95                              # same fit as the hub, at the other end of the axis
# The axle used to reach in to Y -14.0, which put its full R 9.95 body directly behind the camera
# board over Y -18..-14 -- the board's whole -Y end backed onto it. Flatting it stopped the axle
# eating INTO the board but left it filling the space behind. It now stops short of the board
# entirely. Socket engagement drops from 10.5 mm to 6.0 mm, which is still plenty for a plain
# idler that is trapped by cap_minus and carries no drive load.
AXLE_Y0, AXLE_Y1 = POD_M_Y1 + FLANGE_REC + 0.2, -18.5
SLOT_W, SLOT_T = A.SLOT_W, A.SLOT_T
M2_PILOT, M2_CLEAR, M2_HEAD, M3_CLEAR = A.M2_PILOT, A.M2_CLEAR, A.M2_HEAD, A.M3_CLEAR
# The seam is M3 now, not M2. Not a preference: an M2 long enough to cross the ball does not exist
# in Zach's box, and M3 x 30 does. Radii, and the rod grown to carry them -- at 2.8 an M3 clearance
# hole left 1.1 mm of wall.
M3_PILOT, M3_HEAD = 1.25, 3.0
# Named, because both of these were loose numbers sitting inside expressions and they have to stay
# off each other's planes: two cuts in the same part ending flush leaves a zero-thickness step.
SEAM_PILOT_Y = -18.5                       # how deep the seam screws' pilot holes run
AXLE_BORE_Y = -18.0                        # where the axle's socket bore stops
SEAM_R = 4.0                               # was 2.8, sized for M2
HORN_L, HORN_W, HORN_C, HORN_D = A.HORN_L, A.HORN_W, A.HORN_C, A.HORN_D
# (x, z-H). The rear pair moved from +-8.0 to +-9.0 when the rods grew for M3: at r 4.0 the lower
# one's top edge landed exactly on the ribbon exit slot's bottom edge, and a tangency like that is
# what put a zero-thickness skin on ball_minus once already. 9.0 leaves 1.0 mm of daylight.
# They are also clear of Z +-14, which is where the camera board's screws used to be.
SEAM_RODS = [(-23.0, 9.0), (-23.0, -9.0), (17.0, -20.0)]

# ---- the trunk: one swept form from the pan pedestal up into the underside of the nest
TRUNK_P = np.array([[0, 0, BASE_Z + 1.0], [0, 0, BASE_Z + 14.0],
                    [-8.0, 0, H - 30.0], [-7.0, 0, H - 19.0]])

def ball_dist(p):
    return np.sqrt(p[0] ** 2 + p[1] ** 2 + (p[2] - H) ** 2)

def bezier(P, n=40):
    P = np.asarray(P, float); t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]

def smax(a, b, k):
    return -smin(-a, -b, k)

def sstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def _rear_angle(p):
    """Radius from the tilt axis, and the angle measured from straight back, positive upward."""
    x, z = -p[0], p[2] - H
    return np.hypot(x, z), np.degrees(np.arctan2(z, x))

# ---- where the ribbon leaves the track and runs down inside the trunk. It leaves along the
# tangent (forward and slightly down) and keeps curving the same way, so there is no fold and
# no reversal anywhere: one drawn-out arc from the shroud to the floor.
_ta = np.radians(180.0 + abs(TRACK_ANG_LO))          # polar angle of the track's lower end
_TX, _TZ = (SHROUD_R0 + 1.2) * np.cos(_ta), H + (SHROUD_R0 + 1.2) * np.sin(_ta)
_TD = (np.sin(np.radians(abs(TRACK_ANG_LO))), -np.cos(np.radians(abs(TRACK_ANG_LO))))
# The cradle sits on the 360-degree pan coil's drum (pan-coil-360-brief.md section 6), not on a
# pan-servo pedestal. 2026-09-27, Zach. False rebuilds the superseded pedestal version: a pan-horn
# pocket and a 5.6 shaft hole in the underside, and the groove landing 9 mm forward of the axis.
PAN_COIL = True
TROUGH_PATH_PEDESTAL = [(_TX, _TZ), (_TX + 8.0 * _TD[0], _TZ + 8.0 * _TD[1]),
                        (5.0, BASE_Z + 0.6), (9.0, BASE_Z - 1.5)]
# On the coil the groove turns straight down ON the axis, into the drum's 18 bore. The ribbon keeps
# lying across Y (width along Y), which is what the drum wants: it drops down the bore and makes ONE
# soft 45-degree fold at the drum's side slot, set once at assembly -- no twist (decision 2026-09-27).
# The turn is a bend about Y and it FINISHES inside the drum's bore (Z 5), which makes its tightest
# radius 6.3 -- ending at the underside instead gave 2.4, too tight if the ribbon calipers at 0.3
# (minimum 10 x thickness). Below the cradle the path stays within X 0..-2.4, where the 18 bore's
# chord is still 17.2 for the 16 ribbon. The cut below BASE_Z only removes air.
TROUGH_PATH_COIL = [(_TX, _TZ), (_TX + 2.5 * _TD[0], _TZ + 2.5 * _TD[1]),
                    (0.0, BASE_Z + 1.5), (0.0, BASE_Z - 5.5)]
TROUGH_PATH = TROUGH_PATH_COIL if PAN_COIL else TROUGH_PATH_PEDESTAL
# The coil drum's three M3 pilots (pan_coil_b.MATE_SCREW_R / MATE_SCREWS, 7 deep). The cradle is
# 15-16 mm thick over them and open above (probed 2026-09-27), so each takes a clearance hole
# through the bottom 5.5 mm and a head recess opening into the bowl, driven from above BEFORE the
# ball goes in. M3 x 12: 5.5 through, ~6.5 into the drum.
MATE_SCREW_R, MATE_SCREWS = 20.0, [0.0, 120.0, 240.0]
MATE_CLAMP = 5.5                                   # cradle material under each screw head
MATE_HEAD_R = 3.2                                  # 6.4 recess for a 5.5 M3 socket head
# The tilt servo's plug has to come down the same way as the ribbon, and it could not (Zach,
# 2026-09-27): the groove was 3.0 thick with a 6.3 bend, and it met the bowl through a 1.5 slit.
# A rigid plug can't turn that bend at any slot thickness. So the cradle's groove is now CHUTE_T
# (Zach's 4, his wire bundle is 3) and a straight chute runs beside it, from the bowl's floor behind
# the ball straight into the drum's bore. The plug drops down the chute with the ball out; the ribbon
# still follows the groove's curve, whose inner wall -- the one it bends round -- the chute leaves
# alone. 50 deg from vertical and exiting at X -1.5 is the angle that leaves no loose sliver between
# the two cuts (40-46 left fins held only at the sides). TROUGH_T stays: it also sizes the ball's
# ribbon slot. Checked by head-v2/checks/plug_passage.py (a plug slid and turned through the cut).
CHUTE_T = 4.0
CHUTE_ANG, CHUTE_X = 50.0, -1.5                    # deg from vertical (heading +X going down); X at BASE_Z
CHUTE_Z0, CHUTE_Z1 = 4.0, 22.0                     # overruns the drum's bore below and the bowl above

def trunk(p):
    raw = bezier(TRUNK_P, 400)
    seg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(raw, axis=0), axis=1))]
    t = np.linspace(0, 1, 56)
    pts = np.stack([np.interp(t * seg[-1], seg, raw[:, k]) for k in range(3)], 1)
    d = None
    for c, ri, ey in zip(pts, 11.5 + 6.5 * t ** 1.5, 1.0 + 0.45 * t ** 1.5):
        di = np.sqrt((p[0] - c[0]) ** 2 + ((p[1] - c[1]) / ey) ** 2 + (p[2] - c[2]) ** 2) - ri
        d = di if d is None else smin(d, di, 1.2)
    return d

def tube(p, ctrl, r, xs=1.0):
    d = None
    for c in bezier(ctrl):
        di = np.sqrt(((p[0] - c[0]) / xs) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) - r
        d = di if d is None else np.minimum(d, di)
    return d

def trough(p, half_w, perp_r):
    d2 = None
    for cx, cz in bezier(TROUGH_PATH, 44):
        di = np.hypot(p[0] - cx, p[2] - cz) - perp_r
        d2 = di if d2 is None else np.minimum(d2, di)
    return _cyl(d2, np.abs(p[1] - TROUGH_Y) - half_w)

def chute(p, half_w=TROUGH_W / 2, t=CHUTE_T):
    """The servo plug's straight way down through the cradle (see CHUTE_T)."""
    s, c = np.sin(np.radians(CHUTE_ANG)), -np.cos(np.radians(CHUTE_ANG))
    ax, az = CHUTE_X + s * (CHUTE_Z1 - BASE_Z) / c, CHUTE_Z1
    vx, vz = s * (CHUTE_Z0 - CHUTE_Z1) / c, CHUTE_Z0 - CHUTE_Z1
    k = np.clip(((p[0] - ax) * vx + (p[2] - az) * vz) / (vx * vx + vz * vz), 0.0, 1.0)
    return _cyl(np.hypot(p[0] - ax - k * vx, p[2] - az - k * vz) - t / 2, np.abs(p[1] - TROUGH_Y) - half_w)

# ---- the tilt servo's own wire route, round 1 (2026-10-02). Taping the servo lead to the ribbon spoilt
# the ribbon's fold (Zach). The servo's lead and plug now stay coiled inside the ball; his thin jumper
# wires plug into it and run alone: through the middle of a fixed hollow STUB that replaces the -Y axle
# (on the tilt axis they twist, they don't bend), down a hole inside the cradle's -Y wall, and into the
# plug chute's mouth above the drum's bore. The stub also replaces the axle that never fitted: Zach's
# ball socket is r 10.04 and the axle r 9.95. The stub doesn't turn; the ball turns on it.
WIRE_ROUTE = True
WIRE_R = 2.5                       # 5 mm hole: three ~1.3 jumper wires plus one bare Dupont crimp (~1.8)
WIRE_WALL = 1.6                    # the conduit's wall: the -Y wall is only ~5.8 thick across its slope,
                                   # so a ridge grows on its OUTSIDE where the hole would break through
STUB_R = 9.8                       # in Zach's socket, r 10.04 (measured on his rev 2 ball_minus): 0.24 running gap
STUB_Y1 = -19.0                    # the socket ends at Y -18.6
STUB_RING_R = 13.4                 # fills the empty 6704 seat (r 13.55): 0.15, his slide fit
STUB_RING_Y1 = BRG_M_Y0 - 0.1      # 0.1 short of the seat's shoulder: no shared face
# Hand-placed along the wall's measured middle (X -5 keeps 1.6 mm off the cap's bottom M2 pilot), pushed
# 1.2 outward where the conduit carries the outer wall, and passing the 240 deg drum screw BELOW its
# head recess (Z 16). Ends in the chute's mouth (air), level over the drum's bore lip, then straight down.
WIRE_PTS = [(0.0, -17.0, H), (0.0, -23.5, H), (-0.6, -27.4, H - 1.2), (-2.0, -29.9, H - 4.8),
            (-3.8, -30.2, H - 9.0), (-5.0, -29.7, 38.5), (-5.0, -29.0, 35.0), (-5.0, -29.0, 31.0),
            (-5.0, -27.8, 28.0), (-5.0, -25.0, 25.0), (-4.8, -22.6, 21.5), (-3.8, -21.0, 17.8),
            (-3.4, -19.6, 15.6), (-3.0, -16.4, 14.3), (-2.5, -12.6, 14.0), (-2.1, -9.6, 13.6),
            (-2.0, -7.0, 13.0), (-1.8, -5.2, 10.8), (-1.5, -4.6, 7.5)]

def _centripetal(P, per=6):
    """Centripetal Catmull-Rom through P: smooth, and no overshoot where points bunch."""
    P = np.asarray(P, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Q) - 2):
        q = Q[i - 1:i + 3]; t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1) ** 0.5)]
        for u in np.linspace(t[1], t[2], per, endpoint=False):
            A = [((t[j + 1] - u) * q[j] + (u - t[j]) * q[j + 1]) / (t[j + 1] - t[j]) for j in range(3)]
            Bb = [((t[j + 2] - u) * A[j] + (u - t[j]) * A[j + 1]) / (t[j + 2] - t[j]) for j in range(2)]
            out.append(((t[2] - u) * Bb[0] + (u - t[1]) * Bb[1]) / (t[2] - t[1]))
    out.append(P[-1]); return np.array(out)

WIRE_LINE = _centripetal(WIRE_PTS)

def wire_tube(p, r=WIRE_R, line=None):
    """A round hole of radius r along WIRE_LINE (capsule chain). Points far from it skip the work."""
    line = WIRE_LINE if line is None else line
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

def stub(p, features=True):
    """The fixed hollow stub: the cap's flange, a ring filling the empty bearing seat, and the tube the ball
    turns on. Three M2 x 6 through the cap's old holes hold it, and they also set its turn, so its wire
    channel lines up with the cradle's hole."""
    face = POD_M_Y1
    flange = _cyl(np.hypot(p[0], p[2] - H) - (FLANGE_R - 0.6),
                  np.abs(p[1] - (face + FLANGE_REC / 2)) - (FLANGE_REC / 2 - 0.6)) - 0.6
    ring = cyl_y(p, 0, H, STUB_RING_R, face + FLANGE_REC - 0.6, STUB_RING_Y1)
    tube = cyl_y(p, 0, H, STUB_R, STUB_RING_Y1 - 0.5, STUB_Y1)
    s = U(flange, ring, tube)
    if not features:
        return s
    holes = [cyl_y(p, SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_CLEAR, face - 1, face + FLANGE_REC + 1)
             for a in np.radians(SCREW_A)]
    return np.maximum(s, -U(wire_tube(p), *holes))

def collar(p, y0, y1, r=COLLAR_R, rnd=3.0):
    """Plain rounded disc, not a pointed pod: it is a swelling of the nest wall, not a box."""
    d2 = np.hypot(p[0], p[2] - H) - (r - rnd)
    return _cyl(d2, np.abs(p[1] - (y0 + y1) / 2) - (abs(y1 - y0) / 2 - rnd)) - rnd

def sector(p, lo, hi):
    """Negative inside the angular mouth lo..hi, degrees from +X (the lens) toward +Z (up).
    Past 180 deg the wedge is the UNION of the two half-planes, not their intersection -- getting
    that wrong silently shrinks the mouth instead of widening it."""
    x, z = p[0], p[2] - H
    a, b = np.radians(lo), np.radians(hi)
    d_lo = x * np.sin(a) - z * np.cos(a)
    d_hi = z * np.cos(b) - x * np.sin(b)
    return np.maximum(d_lo, d_hi) if hi - lo <= 180.0 else np.minimum(d_lo, d_hi)

def rim_w(p):
    """1 just inside either lip of the mouth, 0 deeper into the shell: the bezel only sweeps
    past the shell at the two ends of the mouth, so only the two lips need to stand off."""
    th = np.degrees(np.arctan2(p[2] - H, p[0]))
    wrap = lambda a: (a + 180.0) % 360.0 - 180.0
    dt = wrap(th - MOUTH_UP)                   # degrees into the shell past the top lip (<0 = in the mouth)
    db = wrap(MOUTH_DOWN - th)                 # ... past the bottom lip
    return np.maximum(sstep((RIM_FLARE - dt) / 11.0), sstep((RIM_FLARE - db) / 11.0))

def nest_rin(p):
    """Inner face of the nest: it hugs the ball, flares at the two lips where the bezel sweeps
    past, swells across the back into the spine the rolling loop rolls in, and draws back in
    towards the hubs once it is past the ball's flats."""
    x, y, z = p[0], p[1], p[2] - H
    _, ang = _rear_angle(p)
    hug = R_BALL + 1.5
    wb = sstep((16.5 - np.abs(y)) / 8.5) * rim_w(p)                       # lens-bezel lips
    wy = sstep((BAND + 6.5 - np.abs(y)) / 7.0)                            # ribbon band
    wa = sstep((TRACK_HALF + 7.0 - np.abs(ang - TRACK_MID)) / 11.0)       # ... over the track arc
    rin = smax(hug + wb * (FRONT_SWEEP + 0.9 - hug),
               hug + wy * wa * (SHROUD_R0 - hug), 1.5)
    wc = sstep((np.abs(y) - (FLAT - 3.5)) / 7.0)      # past the ball's flat there is only the hub
    return rin * (1 - wc) + (COLLAR_R - NEST_T) * wc

def cradle(p):
    """The nest: one shell, mouth 180 deg wide and rolled down 35 deg, closing over into a
    full ring by the time it reaches the collars."""
    x, y, z = p[0], p[1], p[2] - H
    r = np.maximum(np.hypot(x, z), 1e-6)
    rin = nest_rin(p)
    t = NEST_T + 3.2 * sstep((-z / r + 0.15) / 0.9)     # thickens underneath, into the trunk
    shell = np.maximum(r - (rin + t), rin - r)
    shell = smax(shell, -sector(p, MOUTH_DOWN, MOUTH_UP), 1.6)   # rounded lip along the whole mouth
    return np.maximum(shell, np.abs(y) - NEST_HALF_Y)

def track(p):
    """The gap the ribbon rolls in: ball surface out to the shroud, over the swept arc."""
    r, ang = _rear_angle(p)
    arc = (np.abs(ang - TRACK_MID) - TRACK_HALF) * np.radians(1.0) * np.maximum(r, 1.0)
    band = np.maximum(np.abs(r - (R_BALL + TRACK_GAP / 2)) - (TRACK_GAP / 2 - 0.4), arc)
    return _cyl(band, np.abs(p[1]) - BAND)

def td_y(p, x, z, r, y0, y1, cap=1.15):
    """Bore along Y with a 45 deg roof, truncated so the peak does not eat the collar wall.
    The full circle is still cut, so the bearing or axle still locates; only the crown above it
    is opened up, and that is what lets a horizontal bore print without support."""
    zr = p[2] - z
    d2 = np.maximum(teardrop2d(p[0] - x, zr, r), zr - r * cap)
    return _cyl(d2, np.abs(p[1] - (y0 + y1) / 2) - abs(y1 - y0) / 2)

def horn_pocket_y(p, y0, y1, length=None):
    L = HORN_L if length is None else length
    return U(cyl_y(p, 0, H, HORN_C / 2, y0, y1),
             rbox(p, (-HORN_W / 2, y0, H - L / 2), (HORN_W / 2, y1, H + L / 2), 1.0))

# ------------------------------------------------------------------ parts
def roots(p, features=True):
    return A.roots(p, features)

def fork(p, features=True):
    """The nest. Trunk, cup and both collars are one grown body."""
    m = (p[0], np.abs(p[1]), p[2])
    s = smin(cyl_z(p, 0, 0, PED_R, BASE_Z, BASE_Z + 6.0), trunk(p), 6.0)
    s = smin(s, cradle(p), 7.0)
    s = smin(s, collar(m, POD_Y0 - 1.0, POD_P_Y1), 7.0)
    if WIRE_ROUTE and PAN_COIL:                         # the conduit: only below the collar's seat
        s = smin(s, wire_tube(p, WIRE_R + WIRE_WALL, WIRE_LINE[WIRE_LINE[:, 2] < 40.0]), 1.5)
    s = np.maximum(s, BASE_Z - p[2])
    s = np.maximum(s, np.abs(p[1]) - POD_P_Y1)          # flat outer faces for the two flange plates
    bezel_sweep = smax(cyl_y(p, 0, H, FRONT_SWEEP, -11.0, 11.0),
                       sector(p, TILT_DOWN - 16.0, TILT_UP + 16.0), 2.5)
    # The ball's running clearance, and the clip is RADIUS-DEPENDENT because it has to be.
    # At +0.5 flat the nest's nearest material sat at Y 25.000 against the ball's fillet bulge at
    # 24.898 -- a 0.103 mm gap between two SEPARATELY PRINTED parts, finer than the process holds,
    # so they would have touched. But opening it uniformly is wrong the other way: the ball's face
    # is FLAT at 24.5 over most of its radius and only bulges out at r 18.5 where the flat fillets
    # into the sphere, so a uniform clip carves away material the ball can never reach -- it
    # undercut the 6704's inboard shoulder from 1.5 mm to 0.7 and took fork's sub-0.8 volume from
    # 24 to 243 mm3. So: 0.6 mm inside r 12, opening to BALL_CLEAR_Y by r 16, where the bulge is.
    # Nothing locates the ball along Y except these two faces, so every extra mm is a mm of
    # rattle; the proper fix is a shoulder on the hub bearing against the 6704's inner race.
    # See ../tree-parts-b/cradle-audit.md section 1.
    swept = np.maximum(np.minimum(np.minimum(ball_dist(p) - (R_BALL + BALL_CLEAR), bezel_sweep),
                                  cyl_y(p, 0, H, HUB_R + 1.5, -FLAT - 11, FLAT + 11)),
                       np.abs(p[1]) - (FLAT + BALL_CLEAR_Y))
    s = smax(s, -swept, 1.5)
    if not features:
        return s
    plus = p[1] > 0
    # +Y collar: 6704 seat, bore for the fixed post, flange recess and screws
    arm = U(td_y(p, 0, H, BRG_OD / 2, BRG_P_Y0, BRG_P_Y1),
            td_y(p, 0, H, HUB_R + 0.45, POD_Y0 - 1, BRG_P_Y0),
            # starts 0.1 INSIDE the seat, not flush with it. Butted flush, the seat's r 13.55 and
            # this bore's r 13.70 share an end plane and leave a zero-thickness annular step --
            # the same coincident-surface fault that stalled ball_minus at 44k faces.
            td_y(p, 0, H, BRG_PASS, BRG_P_Y1 - 0.1, POD_P_Y1 - FLANGE_REC + 0.1),   # bearing's way in
            td_y(p, 0, H, POST_R + 0.3, BRG_P_Y1, POD_P_Y1 + 1),
            cyl_y(p, 0, H, FLANGE_R + 0.25, POD_P_Y1 - FLANGE_REC, POD_P_Y1 + 1))
    for a in np.radians(SCREW_A):
        arm = np.minimum(arm, cyl_y(p, SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_PILOT,
                                    POD_P_Y1 - 9, POD_P_Y1 + 1))
    # -Y collar: bearing seat, axle bore, flange recess and screws
    coll = U(td_y(p, 0, H, AXLE_R + 0.45, BRG_M_Y1, -POD_Y0 + 1.5),
             td_y(p, 0, H, BRG_OD / 2, BRG_M_Y1, BRG_M_Y0),
             td_y(p, 0, H, BRG_PASS, POD_M_Y1 + FLANGE_REC - 0.1, BRG_M_Y1 + 0.1),  # bearing's way in
             td_y(p, 0, H, AXLE_R + 0.45, POD_M_Y1 - 1, BRG_M_Y1),
             cyl_y(p, 0, H, FLANGE_R + 0.25, POD_M_Y1 - 1, POD_M_Y1 + FLANGE_REC))
    for a in np.radians(SCREW_A):
        coll = np.minimum(coll, cyl_y(p, SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_PILOT,
                                      POD_M_Y1 - 1, POD_M_Y1 + 9))
    cuts = [np.where(plus, arm, coll),
            trough(p, TROUGH_W / 2, (CHUTE_T if PAN_COIL else TROUGH_T) / 2),
            track(p)]
    if PAN_COIL:
        cuts.append(chute(p))
        if WIRE_ROUTE:
            cuts.append(wire_tube(p))
        for a in np.radians(MATE_SCREWS):
            x, y = MATE_SCREW_R * np.cos(a), MATE_SCREW_R * np.sin(a)
            cuts += [cyl_z(p, x, y, M3_CLEAR, BASE_Z - 1, BASE_Z + MATE_CLAMP + 0.1),
                     cyl_z(p, x, y, MATE_HEAD_R, BASE_Z + MATE_CLAMP, H)]       # overruns the bowl
    else:                                                                       # SUPERSEDED 2026-09-27
        cuts += [U(cyl_z(p, 0, 0, HORN_C / 2, BASE_Z - 1, BASE_Z + HORN_D),
                   rbox(p, (-HORN_L / 2, -HORN_W / 2, BASE_Z - 1), (HORN_L / 2, HORN_W / 2, BASE_Z + HORN_D), 1.0)),
                 cyl_z(p, 0, 0, 2.8, BASE_Z - 1, BASE_Z + 14)]
    return np.maximum(s, -U(*cuts))

def rin(p):
    """Inner radius of the ball, which is NOT constant any more.

    The shell is 1.2 mm -- three perimeters at a 0.4 nozzle, and the reason the whole thing reads
    as flimsy. It cannot thicken where the camera board and the servo live, but the rear of the
    ball (-X) holds nothing except the ribbon's exit slot, and that is a cut made afterwards. So
    the back gets REAR_FILL mm of extra wall, faded in so there is no step for a crack to start at.
    """
    return R_IN - REAR_FILL * sstep((-REAR_X0 - p[0]) / REAR_FADE)

def ball_body(p):
    d = ball_dist(p)
    ri = rin(p)
    s = np.maximum(np.maximum(d - R_BALL, ri - d), np.abs(p[1]) - FLAT)
    for sgn in (1.0, -1.0):                 # the two edge rails the board slides into
        y0, y1 = sgn * (BOARD_Y - 3.0), sgn * (BOARD_Y + 2.0)
        # run the rail past the board's own edge: rounded off at +-19 its corners stopped a
        # few tenths short of the shell and the whole rail printed as a loose second body
        # +-26.0, not +-21.5: at 21.5 the rail stopped just short of the sphere and met it almost
        # tangentially, so a 647 mm3 rib hung on 28 mm2 of contact. Run long and let the sphere cut
        # it -- the ends then land on the shell across an arc instead of a sliver.
        rail = rbox(p, (BOARD_X0 - 1.5, min(y0, y1), H - 26.0),
                    (BOARD_X1 + 1.5, max(y0, y1), H + 26.0), 1.0)
        s = smin(s, np.maximum(rail, d - ri - 0.6), BLEND)
    for rx, rz in SEAM_RODS:
        s = smin(s, np.maximum(cyl_y(p, rx, H + rz, SEAM_R, -FLAT, FLAT), d - ri - 0.6), BLEND)
    # FACE_T, up from 1.6. These two discs are the load path: the whole weight and tilt torque of
    # the ball passes stub -> face plate -> shell on the +Y side. A 1.6 mm disc carrying an 850 mm3
    # stub was the thinnest thing in the assembly that actually gets worked.
    face_r = np.sqrt(R_BALL ** 2 - FLAT ** 2)
    s = smin(s, np.maximum(cyl_y(p, 0, H, face_r, FLAT - FACE_T, FLAT), -p[1]), BLEND)      # +Y face plate
    s = smin(s, np.maximum(cyl_y(p, 0, H, face_r, -FLAT, -FLAT + FACE_T), p[1]), BLEND)     # -Y face plate
    # the hubs are filleted into those plates rather than butted onto them
    s = smin(s, np.maximum(cyl_y(p, 0, H, HUB_R, FLAT - 2.0, BRG_P_Y1 - 0.2), -p[1]), BLEND)  # +Y hollow stub
    s = smin(s, np.maximum(cyl_y(p, 0, H, 13.0, -FLAT, -19.0), p[1]), BLEND)                  # -Y socket hub
    # -Y half: the pad that closes on the servo's base. Nothing screws the servo down -- the
    # tab recess stops it moving +Y, the pocket's flat sides take the torque, and this takes the
    # rest. It also leaves every driver path in the +Y half clear. It sits directly UNDER the case
    # base now (the servo dropped past the seam), so it is a floor the servo lands on, not a lip.
    # It stops at the camera board's face, NOT at +24. It used to run the full width of the ball
    # and pass straight through the board -- the bar Zach could see crossing the middle. It still
    # reaches -24 because that is how it stays attached: the (-23, +8) seam rod is what carries it
    # back to the shell. Its job only needs it out to the servo's X +-6.1 anyway.
    # -29.5, not -24: at -24 it stopped in mid air and the (-23, +8) seam rod was the only thing
    # holding it -- 711 mm3 of plate on 32 mm2 of contact. It now runs out to the shell and the
    # sphere trims it, so it is carried by the wall it is part of.
    pad = rbox(p, (-29.5, SERVO_Y0 - 3.0, ZC - 4.0), (BOARD_X0 - 0.1, SERVO_Y0, ZC + 4.0), 1.0)
    s = smin(s, np.maximum(np.maximum(pad, d - ri - 0.6), p[1]), BLEND)
    # +Y half: the two bosses the servo's tabs screw up into. Clipped to the cavity like the rails
    # and rods so they grow OUT of the shell rather than butting onto it -- the near one runs up
    # into the +Y face plate, the far one into the sphere.
    # A bigger fillet than BLEND: these are pillars standing off the shell, so almost all of
    # their contact IS the fillet. At BLEND they scored 4.5 and 4.2 mm of volume per mm2 of
    # contact against ball_structure.py's 4.0 threshold; TAB_BOSS_BLEND brings both under it.
    for tz in TAB_Z:
        boss = cyl_y(p, 0.0, tz, TAB_BOSS_R, TAB_BOSS_Y0, FLAT)
        s = smin(s, np.maximum(np.maximum(boss, d - ri - 0.6), -p[1]), TAB_BOSS_BLEND)
    # Re-impose the flat AFTER the blends. Every smin above is a smooth min, and a smooth min
    # bulges outward wherever two surfaces meet near-tangentially -- so the ball was standing
    # 25.67 proud at r 10.5 (the hub stub's root) and 25.41 at r 16.5 (the face plate's rim)
    # against a FLAT of 24.5 that the whole rest of the model reasons about. That is what drove
    # the nest's running clearance NEGATIVE: 1.71 mm3 of real interference that the 0.4 mm
    # interference grid could not see. Everywhere except the hub itself, which has to pass
    # through the collar, the face is the flat again. This is the SAME plane ball_body already
    # truncates on, not a second one. (2026-09-19)
    return np.maximum(s, np.minimum(np.abs(p[1]) - FLAT,
                                    np.hypot(p[0], p[2] - H) - (HUB_R + 0.25)))

def ball_cuts(p):
    cuts = [cyl_x(p, 0, H, LENS_R, 0.0, 44.0),
            cyl_x(p, 2.7, H + 20.5, 3.0, 14.0, 44.0),
            # the case pocket runs through BOTH halves -- the base is 5.5 mm past the seam. It stops
            # exactly at SERVO_Y0 so the -Y pad below it survives as the floor the servo lands on.
            box(p, (-SW / 2 - FIT, SERVO_Y0, H - S2S - FIT), (SW / 2 + FIT, SERVO_Y1 + FIT, H + SL - S2S + FIT)),
            # The tab recess used to be here, described as "what stops the servo walking out
            # toward the post". Measured, it removed 0.00 mm3 of a 1452 mm3 box: it was cut
            # entirely inside the cavity and never touched solid material. Deleted rather than
            # left in, because an inert cut that reads as a feature is worse than no cut. The
            # tabs are now clamped to TAB_BOSS_* instead. (2026-09-19)
            # POST_BORE starts at 20.5, not SERVO_Y1 - 0.6 = 17.4. The old start was pure overrun
            # into empty cavity, but the near tab boss now lives there: its pilot sits at r 7.4
            # to 9.1 and the bore is r 8.0, so the bore would have opened the pilot down one side
            # -- the exact fault just fixed on the collar. 20.5 still overruns the face plate's
            # inner face at 22.3 by 1.8 mm, and the servo's own boss (r 3.45) is nowhere near it.
            cyl_y(p, 0, H, POST_BORE, 20.5, FLAT + 10.5),
            # A PLAIN round socket. It used to carry a flat roof matching the axle's, and either
            # orientation of that flat leaves a thin wedge inside the bore that meshes badly --
            # ball_minus came back bodies=2, self-int=6, and the decimator gave up at 44k faces.
            # The key is not needed: the axle now stops at Y -18.5, short of the board's -18.0, so
            # it cannot reach the board whatever angle it sits at. The axle keeps its flat purely
            # as margin, because BOARD_Y is still a guess and may grow.
            # It ends at -18.0, NOT -19.0: the socket hub's own end face is at -19.0, and a cut that
            # stops exactly flush with the face it passes through is coincident-surface CSG. That
            # is what put a zero-thickness skin on ball_minus -- bodies=2, self-int, decimator
            # stalled at 44k. Everything past -19.0 is cavity, so the overshoot removes nothing.
            cyl_y(p, 0, H, AXLE_R + 0.1, -FLAT - 1, AXLE_BORE_Y),
            # ribbon (and the servo leads taped to it) leave through the back, already in the loop plane
            box(p, (-R_BALL - 2, -BAND, H - TROUGH_T - 1.0), (-R_IN + 4, BAND, H - 1.0))]
    for sgn in (1.0, -1.0):                 # the groove: the board's last 2.6 mm of edge sits here
        # 3.2, not 2.6: the rail starts at BOARD_Y - 3.0, so a slot starting at 2.6 left 0.4 mm of
        # rail sitting inboard of its own opening -- squarely in the path of the board it holds.
        y0, y1 = sgn * (BOARD_Y - 3.2), sgn * (BOARD_Y + 0.3)
        cuts.append(box(p, (BOARD_X0 - 0.15, min(y0, y1), H - 19.5),
                        (BOARD_X1 + 0.15, max(y0, y1), H + 19.5)))
    for tz in TAB_Z:                        # M2 pilots for the servo's own tab holes
        cuts.append(cyl_y(p, 0.0, tz, M2_PILOT, TAB_BOSS_Y0 - 0.6, TAB_BOSS_Y0 + TAB_BOSS_DEPTH))
    for rx, rz in SEAM_RODS:
        y_out = np.sqrt(max(R_BALL ** 2 - rx ** 2 - rz ** 2, 1.0))
        cuts.append(np.where(p[1] > 0,
                             U(cyl_y(p, rx, H + rz, M3_CLEAR, -1, FLAT), cyl_y(p, rx, H + rz, M3_HEAD, y_out - 2.2, FLAT)),
                             cyl_y(p, rx, H + rz, M3_PILOT, SEAM_PILOT_Y, 1)))
    return U(*cuts)

def ball_plus(p, features=True):
    s = np.maximum(ball_body(p), -p[1])
    return np.maximum(s, -ball_cuts(p)) if features else s

def ball_minus(p, features=True):
    s = np.maximum(ball_body(p), p[1])
    return np.maximum(s, -ball_cuts(p)) if features else s

def post(p, features=True):
    """Fixed drive post: sits flush in the +Y collar, reaches through the bearing, and ends in a
    blind pocket that captures the (trimmed) servo horn. Nothing screws the horn down: the servo's
    own boss holds it on one side, the pocket floor on the other, and the spline carries the torque."""
    face = POD_P_Y1 - FLANGE_REC
    # the ring that traps the bearing: it fills the gap the bearing came in through and lands on
    # the OUTER race only. Without it the bearing can walk back out the way it went in.
    ring = np.maximum(cyl_y(p, 0, H, BRG_RING_R1, BRG_P_Y1 - 0.1, face + 0.1),
                      -(np.hypot(p[0], p[2] - H) - BRG_RING_R0))
    s = U(cyl_y(p, 0, H, POST_R, POST_IN, face + 0.2), ring,
          _cyl(np.hypot(p[0], p[2] - H) - (FLANGE_R - 0.6),
               np.abs(p[1] - (face + FLANGE_REC / 2)) - (FLANGE_REC / 2 - 0.6)) - 0.6)
    if not features:
        return s
    cuts = [horn_pocket_y(p, POST_IN - 0.1, POST_IN + HORN_D_B, HORN_L_B),
            # The hub faces the servo, so the post meets a flat 2.0 mm disc and the spline tip stops
            # 1.0 mm short of the pocket floor. This relief is insurance for that 1.0 mm, not a
            # feature: if the hub or the spline runs long, it has somewhere to go.
            cyl_y(p, 0, H, HORN_HUB_D / 2 + 0.2, POST_IN + HORN_D_B - 0.1, POST_IN + HORN_D_B + 1.5)]
    for a in np.radians(SCREW_A):
        cuts.append(cyl_y(p, SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_CLEAR, face - 1, POD_P_Y1 + 1))
    return np.maximum(s, -U(*cuts))

def axle(p, features=True):
    s = cyl_y(p, 0, H, AXLE_R, AXLE_Y0, AXLE_Y1)
    # ONE flat, turned 90 deg to face the camera. It was already the right feature and the right
    # size -- it was just pointing +Z instead of +X. Rotated, not duplicated: a second cut would
    # take two bites out of an idler that only has to carry the -Y end of the tilt axis.
    # Cut only INSIDE the ball, so the bearing journal stays fully round.
    s = np.maximum(s, -np.maximum((BOARD_X0 - 0.4) - p[0], (-FLAT - 0.1) - p[1]))
    if not features:
        return s
    slot = box(p, (-SLOT_W / 2, AXLE_Y0 + 1.5, H - SLOT_T / 2), (SLOT_W / 2, AXLE_Y1 + 5, H + SLOT_T / 2))
    return np.maximum(s, -slot)

def cap_minus(p, features=True):
    """Closes the -Y collar flush and stops the axle walking out."""
    face = POD_M_Y1
    # a flush plate, nothing more: its inner face lands 0.2 mm off the axle's end, so the axle
    # is trapped axially without the two ever being modelled into each other
    ring = np.maximum(cyl_y(p, 0, H, BRG_RING_R1, face + FLANGE_REC - 0.1, BRG_M_Y1 + 0.1),
                      -(np.hypot(p[0], p[2] - H) - BRG_RING_R0))
    s = U(_cyl(np.hypot(p[0], p[2] - H) - (FLANGE_R - 0.6),
               np.abs(p[1] - (face + FLANGE_REC / 2)) - (FLANGE_REC / 2 - 0.6)) - 0.6, ring)
    if not features:
        return s
    return np.maximum(s, -U(*[cyl_y(p, SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_CLEAR, face - 1, face + FLANGE_REC + 1)
                              for a in np.radians(SCREW_A)]))

def rx(sign):
    """Rotate about X by +-90 deg: sign=+1 maps +Y up, sign=-1 maps -Y up."""
    return lambda v: np.c_[v[:, 0], -sign * v[:, 2], sign * v[:, 1]]

def same(v):
    return v

# (fn, lo, hi, sample step, viewer faces, print orientation)
# The orientations were measured, not guessed -- overhang area and bed contact for every
# candidate. The nest wants its deck plate flat on the bed: 1606 mm2 of contact and the least
# overhang of anything tried. Standing it on a hub gave 85 mm2, mouth-up gave 1 mm2.
PARTS = {
    'roots':      (roots,      (-40, -40, -0.5), (40, 40, BASE_Z + 0.5), 0.30, 16000, same),
    'fork':       (fork,       (-46.0, POD_M_Y1 - 3, BASE_Z - 0.5), (34.0, POD_P_Y1 + 3, H + 30.0), 0.30, 60000, same),
    'ball_plus':  (ball_plus,  (-33, -0.5, H - 33), (35, FLAT + 11, H + 33), 0.26, 20000, rx(+1)),
    'ball_minus': (ball_minus, (-33, -FLAT - 1, H - 33), (35, 0.5, H + 33), 0.26, 20000, rx(-1)),
    'post':       (post,       (-20, 14, H - 20), (20, POD_P_Y1 + 3, H + 20), 0.18, 5000, rx(-1)),
    'axle':       (axle,       (-10.5, AXLE_Y0 - 1, H - 10.5), (10.5, AXLE_Y1 + 1, H + 10.5), 0.18, 4000, rx(+1)),
    'cap_minus':  (cap_minus,  (-20, POD_M_Y1 - 3, H - 20), (20, AXLE_Y0 + 1.5, H + 20), 0.18, 4000, rx(+1)),
    'stub':       (stub,       (-19, POD_M_Y1 - 1.5, H - 19), (19, STUB_Y1 + 1, H + 19), 0.15, 6000, rx(+1)),
}

if __name__ == '__main__':
    os.makedirs(os.path.join(OUT, 'fusion'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'print'), exist_ok=True)
    args = os.sys.argv[1:]
    no_print = '--no-print' in args
    names = [a for a in args if a in PARTS]
    lines, bundle = [], {}
    lo_all = np.array([1e9] * 3); hi_all = -lo_all
    for name, (fn, lo, hi, step, target, to_print) in PARTS.items():
        if names and name not in names:
            continue
        f = lambda P: fn(P, True)
        vol = sample(f, lo, hi, step)
        v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
        v_raw = v + np.array(lo)
        v = project(f, v_raw, step)
        with quiet():
            v = unfold(v, v_raw, faces)
            if not no_print:
                pms, _ = decimate(v, faces, 250000)        # print mesh: plenty for a slicer
                pv = to_print(pms.current_mesh().vertex_matrix())
                pv = pv - np.array([(pv[:, 0].min() + pv[:, 0].max()) / 2,
                                    (pv[:, 1].min() + pv[:, 1].max()) / 2, pv[:, 2].min()])
                pm = mesh_set(pv, pms.current_mesh().face_matrix())
                pok, pmsg = report(pm)
                pm.save_current_mesh(os.path.join(OUT, 'print', name + '.stl'), binary=True)
                lines.append(('print/' + name + '.stl').ljust(26) + pmsg + ('' if pok else '   <-- CHECK'))
                print(lines[-1], flush=True)
            ms, ok = decimate(v, faces, target)
            _, msg = report(ms)
            ms.save_current_mesh(os.path.join(OUT, 'fusion', name + '.obj'), save_vertex_normal=False)
            V = ms.current_mesh().vertex_matrix()
            bundle[name] = {'v': base64.b64encode(V.astype('<f4').tobytes()).decode(),
                            'f': base64.b64encode(ms.current_mesh().face_matrix().astype('<u4').tobytes()).decode()}
        lo_all = np.minimum(lo_all, V.min(0)); hi_all = np.maximum(hi_all, V.max(0))
        lines.append(('fusion/' + name + '.obj').ljust(26) + msg)
        print(lines[-1], flush=True)
    if not names:
        open(os.path.join(OUT, 'viewer_parts_b.js'), 'w').write('window.TREEB=' + json.dumps(bundle) + ';')
    env = 'ENVELOPE %s -> %s  size %s' % (lo_all.round(1), hi_all.round(1), (hi_all - lo_all).round(1))
    print(env)
    mode = 'a' if names else 'w'
    open(os.path.join(OUT, 'mesh_report.txt'), mode).write('\n'.join(lines) + '\n' + env + '\n')
