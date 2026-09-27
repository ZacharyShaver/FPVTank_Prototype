"""Pan-axis ribbon take-up: a rolling loop in a flat can, sunk into the tank body.

Why a can and not a twist: measured from "tank body section.stl" there are only 28 mm
from the deck to the cable-trough floor and 18 of those are servo. A 90 deg twist of a
16 mm ribbon wants ~40 mm of straight run. So the pan rotation is taken up by a coil.

Why the coil is BELOW the deck: inside the coil the ribbon's width stands vertical
(parallel to the pan axis). A ribbon cannot travel along its own width, so it can only
leave the can sideways, width still vertical -- which is exactly what a fore-aft trough
in the body wants. Stacking the can on top of the deck would need the ribbon to turn
downward out of it, which it cannot do without a crease.

Which member rotates: the INNER drum. That keeps the fixed outer wall as plain body
material and means the deck only needs a round hole, not an annular slot.

    fixed   body well, inner face r 30.0, Z 0 .. -18       <- outer half of the loop
    rotates drum, outer face r 21.5, hangs from the head   <- inner half of the loop
    fixed   servo island in the middle, the old pocket

Frame: the head frame -- mm, Z 0 at the deck top, pan axis at the origin, X forward.
To place in the body model of 2026-09-18, translate to (96.16, -196.46, 57.40); the
servo's long axis lies along that model's X with the shaft end toward -X.

    python pan_coil.py [part ...]
"""
import os, json, base64
import numpy as np
from skimage import measure
import tree_parts as A
from tree_parts import (smin, box, rbox, _cyl, cyl_x, cyl_y, cyl_z, U, ring_z,
                        sample, project, decimate, report, quiet)

OUT = os.path.join(A.D, '..', 'pan-coil')

# ------------------------------------------------------------------ the ribbon
RIBBON_W, RIBBON_T = 16.0, 0.3     # MEASURED 2026-09-18 (width) / assumed (thickness)
CH_W = RIBBON_T + 2.2              # 2.5  channel thickness
CH_H = RIBBON_W + 0.8              # 16.8 channel height = the ribbon's width
MIN_BEND_R = 10 * RIBBON_T         # 3.0

# ------------------------------------------- measured from "tank body section.stl"
POCKET_L, POCKET_W, POCKET_D = 23.0, 12.2, 18.0   # servo pocket, open at the deck
SHAFT_OFF = 5.6                    # shaft sits this far toward -X of the pocket centre
NOTCH_L, NOTCH_W = 2.0, 8.0        # servo lead notch, +X end of the pocket
PK_X0, PK_X1 = -(POCKET_L / 2 + SHAFT_OFF), POCKET_L / 2 - SHAFT_OFF    # -17.1 .. 5.9
CORNER_R = np.hypot(PK_X0, POCKET_W / 2)          # 18.16: the servo's far corner

# ------------------------------------------------------------------ the can
DRUM_IR = 19.5                     # clears the servo corner by 1.34
DRUM_T = 2.0
DRUM_OR = DRUM_IR + DRUM_T         # 21.5
GAP = 8.5                          # rolling-loop gap, drum face to well face
WELL_IR = DRUM_OR + GAP            # 30.0  -> cavity Ø 60
WELL_T = 2.0
WELL_OR = WELL_IR + WELL_T         # 32.0  -> body boss Ø 64
# the two ribbon layers lie ON those faces, so the loop runs on these radii, not the walls
RUN_CLR = 0.25                     # running clearance between ribbon and wall
R_OUT = WELL_IR - RIBBON_T / 2 - RUN_CLR   # 29.60
R_IN = DRUM_OR + RIBBON_T / 2 + RUN_CLR    # 21.90
U_R = (R_OUT - R_IN) / 2           # 4.10 = 14x the ribbon thickness
CAN_Z0, CAN_Z1 = -POCKET_D, 0.0    # reuses the existing pocket depth exactly
BAND_Z0, BAND_Z1 = CAN_Z0 + 1.0, CAN_Z1 - 1.0     # where the 16 mm ribbon sits

# rolling-loop layout, angles CCW about +Z, 0 = +X
A_OUT = 180.0                      # fixed anchor / exit, straight back
A_IN0 = A_OUT + 20.0               # drum anchor at pan 0
U0 = A_OUT + 110.0                 # the U at pan 0
DU_DPAN = R_IN / (R_OUT + R_IN)    # 0.4204: how fast the U follows pan, from dL/dpan = 0
PAN = 90.0                         # +- pan range

# drum body above the deck: thrust flange, then the twist barrel
FLANGE_R, FLANGE_Z = 36.0, 3.0     # lands on the deck outside the well wall
BARREL_R, BARREL_Z = 30.0, 20.0    # carries the twist channel and the horn
BOSS_R = 26.5                      # the anchor boss, into the gap but clear of the outer ribbon
BOSS_CR = 23.9                     # the channel's centreline radius through the boss
SERVO_PROUD = 4.5                  # servo body standing above the deck
HORN_L, HORN_W, HORN_C, HORN_D = A.HORN_L, A.HORN_W, A.HORN_C, A.HORN_D
M2_PILOT, M2_CLEAR, M2_HEAD, M3_CLEAR = A.M2_PILOT, A.M2_CLEAR, A.M2_HEAD, A.M3_CLEAR
FORK_SCREWS = [(0.0, 26.0), (120.0, 26.0), (240.0, 26.0)]     # (deg, r) up into the fork

# where the stem's trough meets the barrel: the channel hands the ribbon over here
STEM_A, STEM_R = 340.0, 26.5

def polar(r, deg, z):
    a = np.radians(deg)
    return np.array([r * np.cos(a), r * np.sin(a), z])

# ------------------------------------------------------------------ swept channel
def bez3(P, n):
    P = np.asarray(P, float); t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1]
            + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]), t[:, 0]

def frames(pts, w0, w1):
    """Travel/width/thickness at each sample; width swings from w0 to w1 along the run."""
    T = np.gradient(pts, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1)[:, None], 1e-9)
    t = np.linspace(0, 1, len(pts))[:, None]
    Wr = (1 - t) * np.asarray(w0, float) + t * np.asarray(w1, float)
    W = Wr - (Wr * T).sum(1)[:, None] * T
    W /= np.maximum(np.linalg.norm(W, axis=1)[:, None], 1e-9)
    return T, W, np.cross(T, W)

def sweep(p, pts, T, W, Uu, half_h, half_w):
    """Chain of oriented boxes along the path: the ribbon channel."""
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1).mean()
    d = None
    for c, tt, ww, uu in zip(pts, T, W, Uu):
        dx = p[0] - c[0]; dy = p[1] - c[1]; dz = p[2] - c[2]
        a = np.abs(dx * tt[0] + dy * tt[1] + dz * tt[2]) - seg * 0.75
        b = np.abs(dx * ww[0] + dy * ww[1] + dz * ww[2]) - half_h
        e = np.abs(dx * uu[0] + dy * uu[1] + dz * uu[2]) - half_w
        di = np.maximum(np.maximum(a, b), e)
        d = di if d is None else np.minimum(d, di)
    return d

# the rotating side: drum anchor -> up and around -> hands off to the stem, vertical
_TWIST_P = [polar(BOSS_CR, A_IN0, (BAND_Z0 + BAND_Z1) / 2),
            polar(BOSS_CR, A_IN0 + 45, (BAND_Z0 + BAND_Z1) / 2 + 3.0),
            polar(BARREL_R - 2.0, STEM_A - 30, 8.0),
            polar(STEM_R, STEM_A, BARREL_Z + 0.5)]
_TWIST, _ = bez3(_TWIST_P, 70)
_TW_T, _TW_W, _TW_U = frames(_TWIST, (0, 0, 1), (0, 1, 0))
TWIST_LEN = float(np.linalg.norm(np.diff(_TWIST, axis=0), axis=1).sum())

_MOUTH = 20        # samples still inside the can, where the slot runs clean through in Z

def twist_channel(p, grow=0.0):
    """Inside the can the ribbon has no roof -- the can floor and the drum flange are its
    roof and floor -- so the boss is slotted right through there. Above the deck the
    channel closes into a real bore."""
    return np.minimum(
        sweep(p, _TWIST[:_MOUTH], _TW_T[:_MOUTH], _TW_W[:_MOUTH], _TW_U[:_MOUTH],
              12.0, CH_W / 2 + grow),
        sweep(p, _TWIST[_MOUTH - 4:], _TW_T[_MOUTH - 4:], _TW_W[_MOUTH - 4:], _TW_U[_MOUTH - 4:],
              CH_H / 2 + grow, CH_W / 2 + grow))

# the fixed side: leaves the well tangentially, curves 90 deg in plane, runs aft
_EXIT_P = [polar(WELL_IR - 0.5, A_OUT, 0), np.array([-WELL_IR - 1.0, 13.0, 0.0]),
           np.array([-WELL_IR - 6.0, 15.0, 0.0]), np.array([-52.0, 15.0, 0.0])]
_EXIT, _ = bez3(_EXIT_P, 48)
_EXIT[:, 2] = (BAND_Z0 + BAND_Z1) / 2
_EX_T, _EX_W, _EX_U = frames(_EXIT, (0, 0, 1), (0, 0, 1))

def exit_channel(p, grow=0.0):
    return sweep(p, _EXIT, _EX_T, _EX_W, _EX_U, CH_H / 2 + grow, CH_W / 2 + grow)

# ------------------------------------------------------------------ parts
def servo_envelope(p, clr=0.6, z1=SERVO_PROUD):
    return box(p, (PK_X0 - clr, -POCKET_W / 2 - clr, CAN_Z0 - 1),
               (PK_X1 + clr, POCKET_W / 2 + clr, z1 + clr))

def drum(p, features=True):
    """Rotates with the head: inner half of the loop, the twist barrel, the horn coupling."""
    s = np.maximum(cyl_z(p, 0, 0, DRUM_OR, CAN_Z0 + 0.5, FLANGE_Z),
                   -cyl_z(p, 0, 0, DRUM_IR, CAN_Z0 - 1, FLANGE_Z + 1))
    # local thickening at the drum anchor so the channel mouth has walls.
    # Clipped to the annulus at both ends: inward it must not reach the fixed servo island,
    # outward it must stay clear of the ribbon lying on the well wall.
    c = polar(BOSS_CR, A_IN0, (BAND_Z0 + BAND_Z1) / 2)
    rr = np.hypot(p[0], p[1])
    bump = rbox(p, (c[0] - 7, c[1] - 7, BAND_Z0 - 1.0), (c[0] + 7, c[1] + 7, BAND_Z1 + 1.0), 1.5)
    bump = np.maximum(np.maximum(bump, rr - BOSS_R), DRUM_IR - rr)
    s = U(s, np.maximum(bump, (CAN_Z0 + 0.5) - p[2]))
    s = U(s, cyl_z(p, 0, 0, FLANGE_R, 0.0, FLANGE_Z))
    s = smin(s, cyl_z(p, 0, 0, BARREL_R, FLANGE_Z - 1.0, BARREL_Z), 3.0)
    s = np.maximum(s, -servo_envelope(p))                       # clear the proud servo
    if not features:
        return s
    cuts = [twist_channel(p),
            U(cyl_z(p, 0, 0, HORN_C / 2, SERVO_PROUD - 0.5, SERVO_PROUD + HORN_D),
              rbox(p, (-HORN_L / 2, -HORN_W / 2, SERVO_PROUD - 0.5),
                   (HORN_L / 2, HORN_W / 2, SERVO_PROUD + HORN_D), 1.0)),
            cyl_z(p, 0, 0, 3.2, SERVO_PROUD, BARREL_Z + 1)]     # driver access to the horn screw
    for deg, r in FORK_SCREWS:
        cuts.append(cyl_z(p, r * np.cos(np.radians(deg)), r * np.sin(np.radians(deg)),
                          M2_PILOT, BARREL_Z - 7, BARREL_Z + 1))
    return np.maximum(s, -U(*cuts))

def island(p, features=True):
    """Add-material for the body: the old servo pocket, left standing in the middle of the well."""
    s = np.maximum(box(p, (PK_X0 - 2.0, -POCKET_W / 2 - 2.0, CAN_Z0), (PK_X1 + 2.0, POCKET_W / 2 + 2.0, 0.0)),
                   np.hypot(p[0], p[1]) - (DRUM_IR - 0.6))
    if not features:
        return s
    cuts = [box(p, (PK_X0, -POCKET_W / 2, CAN_Z0 + 2.0), (PK_X1, POCKET_W / 2, 1.0)),
            box(p, (PK_X1, -NOTCH_W / 2, CAN_Z0 + 2.0), (PK_X1 + NOTCH_L, NOTCH_W / 2, 1.0))]
    return np.maximum(s, -U(*cuts))

def well_cut(p, features=True):
    """CUT TOOL for the body: the can cavity plus the ribbon's way out. Subtract, then add the island."""
    s = cyl_z(p, 0, 0, WELL_IR, CAN_Z0, 0.5)
    if not features:
        return s
    return U(s, exit_channel(p), cyl_z(p, 0, 0, FLANGE_R + 0.4, -0.01, FLANGE_Z + 0.4))

# ------------------------------------------------------------------ the loop itself
def loop_points(pan_deg, n=160):
    """The ribbon's centreline inside the can at a given pan angle. Length is invariant."""
    u = U0 + DU_DPAN * pan_deg
    ai = A_IN0 + pan_deg
    ro, ri, rm = R_OUT, R_IN, (R_OUT + R_IN) / 2
    outer = np.radians(np.linspace(A_OUT, u, n // 2))
    inner = np.radians(np.linspace(u, ai, n // 2))
    phi = np.linspace(-np.pi / 2, np.pi / 2, 24)
    ua = np.radians(u)
    pts = [np.stack([ro * np.cos(outer), ro * np.sin(outer), np.zeros(n // 2)], 1)]
    # the U: a half circle of radius U_R about the mid-gap, swung round to sit at angle u
    cx, cy = rm * np.cos(ua), rm * np.sin(ua)
    tx, ty = -np.sin(ua), np.cos(ua)
    rx, ry = np.cos(ua), np.sin(ua)
    pts.append(np.stack([cx + U_R * (np.sin(phi) * tx + np.cos(phi) * rx),
                         cy + U_R * (np.sin(phi) * ty + np.cos(phi) * ry),
                         np.zeros(len(phi))], 1)[::-1])
    pts.append(np.stack([ri * np.cos(inner), ri * np.sin(inner), np.zeros(n // 2)], 1))
    return np.vstack(pts)

def loop_len(pan_deg):
    p = loop_points(pan_deg)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())

PARTS = {
    'drum':     (drum,     (-FLANGE_R - 2, -FLANGE_R - 2, CAN_Z0 - 1), (FLANGE_R + 2, FLANGE_R + 2, BARREL_Z + 2), 0.26, 26000),
    'island':   (island,   (PK_X0 - 3, -POCKET_W / 2 - 3, CAN_Z0 - 1), (PK_X1 + 3, POCKET_W / 2 + 3, 1.5), 0.22, 6000),
    'well_cut': (well_cut, (-58, -WELL_IR - 6, CAN_Z0 - 1), (FLANGE_R + 2, FLANGE_R + 2, FLANGE_Z + 1.5), 0.34, 14000),
}

if __name__ == '__main__':
    os.makedirs(os.path.join(OUT, 'fusion'), exist_ok=True)
    names = [a for a in os.sys.argv[1:] if a in PARTS]
    print(f'servo far corner  {CORNER_R:.2f} mm from the pan axis')
    print(f'drum  r {DRUM_IR}..{DRUM_OR}   gap {GAP}  (U radius {U_R:.2f} = {U_R / RIBBON_T:.0f}x thickness)')
    print(f'well  inner r {WELL_IR}  -> cavity Ø{2 * WELL_IR:.0f}, body boss Ø{2 * WELL_OR:.0f}')
    print(f'can   Z {CAN_Z0}..{CAN_Z1}   ribbon band Z {BAND_Z0}..{BAND_Z1}')
    print(f'U travel {DU_DPAN * PAN:+.1f} deg for {PAN:+.0f} deg of pan')
    for q in (-PAN, -45, 0, 45, PAN):
        print(f'  pan {q:+6.1f}  U at {U0 + DU_DPAN * q:7.1f} deg   loop length {loop_len(q):7.2f} mm')
    print(f'twist run {TWIST_LEN:.1f} mm for 90 deg = {TWIST_LEN / RIBBON_W:.1f}x the ribbon width')
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
        lines.append(f'fusion/{name}.obj'.ljust(24) + msg)
        print(lines[-1], flush=True)
    bundle['_loop'] = {str(q): loop_points(q).round(3).tolist() for q in (-90, -45, 0, 45, 90)}
    open(os.path.join(OUT, 'viewer_pan_coil.js'), 'w').write('window.PANCOIL=' + json.dumps(bundle) + ';')
    env = f'ENVELOPE {lo_all.round(1)} -> {hi_all.round(1)}  size {(hi_all - lo_all).round(1)}'
    print(env)
    open(os.path.join(OUT, 'mesh_report.txt'), 'w').write('\n'.join(lines) + '\n' + env + '\n')
