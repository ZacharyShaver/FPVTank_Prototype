"""The knob log (2026-10-27): every knob, one at a time, around T3, read on all five gauges, so what each knob does to
each number is on record. Zach: "log how ... the height of the body and the width of the wheels actually translate
to the numbers on the hill climbing and all that".

    SCORPION_SEARCH=search_hills python gauges/knobs.py sweep   -> gauges/out/knobs/knobs_raw.jsonl, knobs_sweep.json
    SCORPION_SEARCH=search_hills python gauges/knobs.py rebrace -> knobs_brace.jsonl (braced over five tail angles)
    SCORPION_SEARCH=search_hills python gauges/knobs.py sweep67 -> knobs_g67.jsonl (G6 crest and G7 push for every design)
    SCORPION_SEARCH=search_hills python gauges/knobs.py rule    -> knobs_brace_rule.jsonl (a brace-angle rule against the best)
    SCORPION_SEARCH=search_hills python gauges/knobs.py speed   -> speed.json (the hills at other driving speeds)
    SCORPION_SEARCH=search_hills python gauges/knobs.py crest20 -> knobs_g67.jsonl's crest at the gauge's 20 tries
    SCORPION_SEARCH=search_hills python gauges/knobs.py grip    -> grip_hills.json (T3's hills by tread grip, x0.65 and x1)
    SCORPION_SEARCH=search_hills python gauges/knobs.py side    -> gauges/out/knobs/side.json (a side slope, exploratory)
    SCORPION_SEARCH=search_hills python gauges/knobs.py freeze  -> freeze.json (the settled knobs held at T3's: does a search lose anything?)
    python gauges/knobs.py cohere                               # the one-body check and its controls (2026-10-28)

T3 is the shape study's best (1.00 / 150 mm / 381 mm; hills 35 / 40 stowed, 45 / 45 braced). Each knob takes 7
values across its range, the rest at T3's, 3 seeds each; T3 itself takes 8 seeds, the noise a knob's effect is read
against. Each design gets the lean screen without its cut (G1 from 60 falls, G2's ladder at x0.65 and x1.5, G3 at the
band) and both hills at x2.5 in 6 tries, tail stowed and braced (the better of -30 and -15 degrees, held).

Two knobs are new: the tyres' width (TW, 46 mm in every design so far) and the tail mount's height (pinned at T5's
since the shape study). Ride height (clr) raises the body, its insides and the tail mount together; the wheels stay.
Two switches ride along: the tail off, and a middle axle.
"""
import os, sys, json, math, time
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config, stamp
import gauges as GG, robots as RB, search as S, hills as H

OUT = os.path.join(config.GAUGES_OUT, 'knobs')
T3 = dict(R=44.908, xw=14.684, gap=62.052, clr=51.943, dxp=23.189, dzp=0.56, six=0.0, shell=1.0, xc=27.025, af=166.408,
          ar=156.628, b=120.606, zc=159.624, cu=71.913, cd=71.847, p=3.26, qu=2.256, qd=2.565, limb=1.0, L=279.186, tq=3.306,
          th_push=-46.177, th_stow=111.658, mz=0.431, track=113.977, msize=1.0, gear=2.091, TW=46.0, mount_z=149.6, foot_r=12.0,
          tyre_mu=1.0, bumper=0.0, L2=0.0, rear_up=0.0)
MOUNT = (-154.83, 0.0)                    # the tail mount's x and y (T5's, pinned); its z is mount_z
# (group, knob, low, high, what it is). The ranges are the searches' own; TW and mount_z are new.
KNOBS = [('wheels', 'R', 35.0, 95.0, "the wheels' radius, mm"),
         ('wheels', 'gap', 15.0, 150.0, 'the gap between front and rear tyres, mm (sets the wheelbase with R)'),
         ('wheels', 'xw', -80.0, 80.0, "the wheelbase's centre, mm ahead of the body's"),
         ('wheels', 'track', 110.0, 180.0, "the wheels' centre planes from the centre line, mm (the robot's width)"),
         ('wheels', 'TW', 25.0, 80.0, "the tyres' width, mm (new)"),
         ('body', 'clr', 15.0, 90.0, "ride height: the body's belly above the ground, mm (body, insides and tail mount)"),
         ('body', 'zc', 30.0, 220.0, "the skin's middle height, mm"),
         ('body', 'cu', 40.0, 250.0, "the skin's height above its middle, mm"),
         ('body', 'cd', 20.0, 150.0, "the skin's depth below its middle, mm"),
         ('body', 'af', 120.0, 260.0, "the skin's reach forward, mm"),
         ('body', 'ar', 120.0, 260.0, "the skin's reach back, mm"),
         ('body', 'b', 100.0, 200.0, "the skin's half-width, mm"),
         ('body', 'xc', -40.0, 60.0, "the skin's centre, mm ahead"),
         ('body', 'p', 1.6, 5.0, "the skin's squareness seen from above (2 round, 5 boxy)"),
         ('body', 'qu', 1.0, 4.0, "the skin's top squareness (1 pointed, 4 flat)"),
         ('body', 'qd', 1.0, 4.0, "the skin's bottom squareness"),
         ('insides', 'dxp', -80.0, 80.0, 'the battery packs moved forward, mm'),
         ('insides', 'dzp', -8.0, 15.0, 'the battery packs moved up, mm'),
         ('drive', 'gear', 0.4, 2.5, 'the gearing, times the stock 30:1 (slower and stronger up)'),
         ('drive', 'msize', 0.5, 2.0, "the motors' size, times the stock 37 mm"),
         ('tail', 'L', 80.0, 350.0, "the tail's length, mm"),
         ('tail', 'tq', 0.3, 4.0, "the tail servo's stall torque, N m"),
         ('tail', 'th_push', -90.0, -10.0, "the tail's pitch when it pushes on a step, degrees (below level)"),
         ('tail', 'th_stow', 20.0, 160.0, "the tail's stowed pitch, degrees (90 up, 180 forward over the body)"),
         ('tail', 'mount_z', 90.0, 210.0, "the tail mount's height, mm (new)"),
         ('tail', 'foot_r', 6.0, 40.0, "the tail foot's radius, mm (12 so far; a pad or skid when big; new)"),
         ('tail', 'L2', 0.0, 250.0, "a second link on an elbow servo, mm (under 40: one link; 2026-10-30)"),
         ('tail', 'rear_up', 0.0, 1.0, "the tail-first climb reflex: the tail sets its foot on the step and lifts the rear (above half; 2026-10-30)"),
         ('wheels', 'tyre_mu', 0.5, 1.8, "the tread's grip, times the stock tyre's (0.9 at x1; new)"),
         ('body', 'bumper', 0.0, 150.0, "a flat push face at the very front: its top, mm (60 tall, 75 g; under 40: none; new)")]
SWITCHES = [('tail off', dict(limb=0.0)), ('six wheels', dict(six=1.0))]
N_VAL, SEEDS, T3_SEEDS = 7, 3, 8
# Front flippers (2026-10-28, robots.add_flippers): off unless q['flip'] > 0.5; kept apart from KNOBS so the runs
# before them rebuild as they ran. The defaults are a starting guess, not a tested design.
FLIP0 = dict(flip=0.0, f_nose=0.0, f_tail=0.0, FL=150.0, ftq=2.0, f_stow=30.0, f_up=60.0, f_press=-45.0, fz=0.5)
FLIP_KNOBS = [('flipper', 'FL', 60.0, 300.0, "the flipper's length, pivot to tip, mm"),
              ('flipper', 'ftq', 0.3, 4.0, "each flipper servo's stall torque, N m"),
              ('flipper', 'f_stow', 0.0, 180.0, "the flippers' stowed angle, degrees (0 ahead, 90 up, 180 back over the top)"),
              ('flipper', 'f_up', 20.0, 110.0, 'the angle they lift to over a step, degrees'),
              ('flipper', 'f_press', -90.0, -10.0, 'the angle they press down to, degrees (below level)'),
              ('flipper', 'fz', 0.0, 1.0, "the centre-line flipper's pivot height, belly (0) to the top of the nose (1)")]
BRACE = (-30.0, -15.0)
# The head as its own module (2026-11-07, search.HEAD_OUT): on only for a design with head_f, kept apart from KNOBS so the
# runs before rebuild as they ran. It sits on the body's top, its base wholly over the body fore and aft.
HEAD_KNOBS = [('head', 'head_f', 0.0, 1.0, "the head's place along the body's top: 0 at the back, 1 at the front")]


def make(q, strict=False, real=False, why=None, cap=None):
    """the spec of a design given as T3's knobs with changes; None when it can't be built. strict (2026-10-28): None
    too when a part isn't fixed to the body (problems()); searches from then on sample strict, the runs before don't,
    so they rebuild as they ran. real (2026-10-31, strict as well): the body weighs as its one-piece print, the
    motors' pods are in the sims, the motors clear the parts inside and the flippers mount on the body (_real,
    real_problems). why: a list the refusals are added to. cap (2026-11-07, mm): a real build is refused when its body's
    print (the hull and the motor pods; not the head, tail or claws) is longer, wider or taller than cap (cap_problems)"""
    strict = strict or real
    sp = _make(q)
    if sp is None:
        return None
    if strict:
        sp = _cohere(q, sp)
        if sp.get('limb'):
            sp = dict(sp, solid_tail=True)                                # the body and tyres stop the tail (robots.xml)
    if q.get('flip', 0.0) > 0.5:                                          # after the tyres' width: the pair sits outside them
        f = dict(FLIP0, **{k: q[k] for k in FLIP0 if k in q})
        sp = RB.add_flippers(sp, f['FL'], f['ftq'], f['f_stow'], f['f_up'], f['f_press'], nose=f['f_nose'] > 0.5, fz=f['fz'], with_tail=f['f_tail'] > 0.5)
    if real and sp is not None:
        sp = _real(q, sp)
    if sp is not None and _head_out(q):
        sp = _place_head(q, sp)
        if sp is None and why is not None:
            why.append('head: no body under it')
    if strict and sp is not None:
        p = problems(q, sp) + (real_problems(q, sp) if real else []) + (head_problems(sp) if sp.get('head') else []) \
            + (cap_problems(q, sp, cap) if real and cap else [])
        if why is not None:
            why += p
        if p:
            return None
    if real and sp is not None:                                          # (add_flippers can refuse: None)
        sp = _real_shape(sp)
    return sp


def _make(q):
    q = dict(q); wb = 2 * q['R'] + q['gap'] if q['six'] <= 0.5 else 2 * (2 * q['R'] + q['gap'])
    q['xf'], q['xr'] = q['xw'] + wb / 2, q['xw'] - wb / 2
    S.LIMB_BASE = (MOUNT[0], MOUNT[1], q['mount_z'] + q['clr'] - T3['clr'])   # the mount rides with the body
    S.TRACK_R = q.get('track_r')                                         # front and rear tracks apart (Zach, 2026-10-28: "two knobs for wheel width")
    S.HEAD_OUT = _head_out(q)                                            # the head out of the body (2026-11-07)
    sp = S.build(np.array([q[k] for k in S.KEYS]))
    if sp is None:
        return None
    if q.get('L2', 0.0) >= 40.0 and sp.get('limb'):                     # a second link on an elbow (2026-10-30; under 40: one link)
        lm = sp['limb']; nl = RB.add_limb(dict(sp, limb=None), lm['L'], lm['tq'], lm['th_push'], lm['th_stow'], lm['mz'], base=lm['base'], L2=q['L2'])['limb']
        sp = RB.dims(dict(sp, limb=dict(lm, **{k: nl[k] for k in ('L2', 'tq2', 'm_link2', 'm_elbow')})))
    if q.get('rear_up', 0.0) > 0.5 and sp.get('limb'):                   # the tail-first climb reflex (gauges.RearUp, 2026-10-30)
        sp = dict(sp, limb=dict(sp['limb'], rear_up=True))
    if q['foot_r'] != 12.0 and sp.get('limb'):                           # a bigger foot weighs more, as a shell: 15 g at 12 mm
        sp = dict(sp, limb=dict(sp['limb'], foot_r=q['foot_r'], m_foot=15.0 * (q['foot_r'] / 12.0) ** 2))
    if q['tyre_mu'] != 1.0:
        sp = dict(sp, tyre_mu=q['tyre_mu'])
    if q['bumper'] > 40.0:                                                # a 3 mm plate and its struts, flush with the front-most point
        P = np.vstack(sp['hulls']); x0 = float(P[:, 0].max()); z1 = q['bumper']; z0 = max(30.0, z1 - 60.0)
        plate = np.array([[x, y, z] for x in (x0 - 3.0, x0 + 0.5) for y in (-100.0, 100.0) for z in (z0, z1)])
        sp = H.add_mass(dict(sp, hulls=list(sp['hulls']) + [plate]), 75.0, (x0, 0.0, (z0 + z1) / 2), sp['name'])
    return RB.dims(dict(sp, TW=q['TW'])) if (q['TW'], q['foot_r']) != (46.0, 12.0) else sp


# ---------- one body (2026-10-28) ----------
# Zach, on the capability page's shapes: "a lot of floating parts. Make a check to ensure everythings connected when
# sampling these and they actually fit as a cohesive body. some of the shapes are impossible to make due to that".
# A design's parts are mass items and hulls; nothing tied them together. Each part that must be fixed to the body:
MOTOR_HALF = (18.5, 40.7, 18.5)           # mm: chassis3's motor box, at (axle x, its side's |y| - 31, R)
PACK_HALF = (70.5, 13.0, 22.8)            # mm: chassis3's battery pack box
# The rule: a part touches the body or stands off it on at most a 10 mm bracket*. A motor reaches 5 mm* into the body
# (the Trainer's own layout: 10); the tail's turntable, about 40 mm across*, has its centre within 30 mm (limb_mount
# puts it 20 out; T3's is 26); the push plate within 10; a pack inside the tub within 2 (the wall).
MOTOR_IN, TAIL_OUT, PLATE_OUT, PACK_OUT = 5.0, 30.0, 10.0, 2.0
# Zach: "many times the tail moves through the body which is not possible". The turntable sits on the body's surface:
# its centre at least 15 mm* out (a buried one can't turn; limb_mount puts it 20 out), and the stowed tail clears the
# body and the tyres. Strict builds also let the body and tyres stop the tail in the sims (robots.xml, solid_tail).
TAIL_IN = 15.0
# Zach: "There should be size limits on the wheels to a realistic proportion for a motor that can move this thing". The
# sim's motors give their stall torque for as long as asked; a real one runs at about a third of it* without cooking.
# So each wheel's motor, at a third of its stall torque, must hold the robot still on a 30-degree slope*: bigger wheels
# need more torque for the same push (torque = force x radius), so this caps the wheel's size by the motor and gearing.
RATED, HOLD_DEG = 1.0 / 3.0, 30.0


def drive_need(sp):
    """(N m a wheel the robot needs on a HOLD_DEG slope, N m its motor gives at RATED of stall)"""
    need = sp['mass'] * 9.81e-3 * math.sin(math.radians(HOLD_DEG)) * sp['R'] * 1e-3 / len(sp['wheels'])
    return need, sp['motor']['stall'] * RATED


def problems(q, sp):
    """the parts not fixed to the body, as 'part: how far off', and a drive too weak for its wheels"""
    out = []
    for k, v in cohesion(q, sp).items():
        if k.startswith('motor') and v < MOTOR_IN:
            out.append(f'{k}: {"reaches " + format(v, ".0f") + " mm in" if v >= 0 else format(-v, ".0f") + " mm from the body"}')
        elif k == 'tail mount' and v < TAIL_IN:
            out.append(f'tail mount: ' + (f'buried {-v:.0f} mm in the body' if v < 0 else f'{v:.0f} mm out, too close to the body to turn'))
        elif (k == 'tail mount' and v > TAIL_OUT) or (k == 'push plate' and v > PLATE_OUT) or (k.startswith('pack') and v > PACK_OUT):
            out.append(f'{k}: {v:.0f} mm {"outside" if k.startswith("pack") else "from"} the body')
    lm = sp.get('limb')
    if lm:                                                                # the stowed tail, past its turntable, clear of body and tyres
        P = RB.limb_points(lm, 0.0, lm['th_stow'], k=24); P = P[np.linalg.norm(P - np.asarray(lm['base']), axis=1) > 20.0]
        if (RB.hull_dist(sp['hulls'][0], P) < RB.LINK_R - 1.0).any():
            out.append('tail: stowed through the body')
        for x, y in sp['wheels']:
            if np.any((np.hypot(P[:, 0] - x, P[:, 2] - sp['R']) < sp['R'] + RB.LINK_R) & (np.abs(P[:, 1] - y) < sp['TW'] / 2 + RB.LINK_R)):
                out.append('tail: stowed through a tyre'); break
    need, have = drive_need(sp)
    if need > have:
        out.append(f'drive: each wheel needs {need:.2f} N m on a {HOLD_DEG:.0f}° slope, its motor gives {have:.2f} at a third of stall')
    return out


def _add_body(M, c, I, m, cm, Im):
    """M, c, I with a body of mass m at cm, inertia Im about it, added (m < 0 with -Im takes one away)"""
    M2 = M + m; c2 = (M * c + m * cm) / M2; d0, d1 = c - c2, cm - c2
    return M2, c2, I + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + Im + m * (d1 @ d1 * np.eye(3) - np.outer(d1, d1))


def _wheels_in(q, sp, c):
    """_cohere's first step: each loose wheel in to the widest |y| where its motor reaches MOTOR_IN into the body (by
    bisection, its tyres at least 80 mm apart), its motor's mass moved with it. (spec, cohesion)"""
    body, R = sp['hulls'][0], sp['R']; wheels = list(sp['wheels']); M, cm, I = sp['M'], sp['com'], sp['I']
    m_mot = 205.0 * q['msize'] + 34.6; moved = []                         # search.build's motor
    depth = lambda x, sg, a: -float(RB.hull_dist(body, _grid((x, sg * (a - 31.0), R), MOTOR_HALF)).min())
    for i, (x, y) in enumerate(wheels):
        if c[f'motor {i}'] >= MOTOR_IN:
            continue
        sg, lo, hi = np.sign(y), sp['TW'] / 2 + 40.0, abs(y)
        if depth(x, sg, lo) < MOTOR_IN:
            continue                                                      # no width reaches: the body grows to it
        for _ in range(12):
            mid = 0.5 * (lo + hi); lo, hi = (mid, hi) if depth(x, sg, mid) >= MOTOR_IN else (lo, mid)
        wheels[i] = (x, sg * lo); moved.append(abs(y) - lo)
        for p, s in (((x, sg * (abs(y) - 31.0), R), -1.0), ((x, sg * (lo - 31.0), R), 1.0)):
            M, cm, I = _add_body(M, cm, I, s * m_mot, np.asarray(p, float), np.zeros((3, 3)))
    if not moved:
        return sp, c
    sp = RB.dims(dict(sp, wheels=wheels, M=M, com=cm, I=I, notes=list(sp['notes']) + [f'{len(moved)} wheel(s) in to the body, up to {max(moved):.0f} mm']))
    return sp, cohesion(q, sp)


def _mount_on_surface(sp):
    """the tail's turntable moved onto the body's rear surface: at its height (kept 15 mm inside the body's height
    range at the rear), 20 mm behind the surface along the centre line, then back until it is 20 mm clear of the body
    (a slanted rear). Unchanged when no height meets the body (problems() then refuses it)."""
    lm = sp['limb']; B = np.asarray(lm['base'], float); body = sp['hulls'][0]
    lo = float(body[:, 2].min()); hi = float(body[body[:, 0] < body[:, 0].min() + 40][:, 2].max())
    z = float(np.clip(B[2], lo + 15.0, hi - 15.0)) if hi - lo > 30.0 else 0.5 * (lo + hi); xs = RB.rear_surface([body], z)
    if xs is None:
        return sp
    nb = np.array([xs - 20.0, 0.0, z])
    for _ in range(6):
        d = float(RB.hull_dist(body, [nb])[0])
        if d >= 19.5:
            break
        nb[0] -= 20.0 - d + 0.5
    note = f"tail mount moved {np.linalg.norm(nb - B):.0f} mm, onto the body's rear"
    return RB.dims(dict(sp, limb=dict(lm, base=nb.tolist()), notes=list(sp['notes']) + [note]))


def _cohere(q, sp):
    """the strict body (2026-10-28). Zach: "it kinda needs to morph towards the wheel base when the shapes are further
    out and not connected", and of the push plate, "merge in something like the front plate in a smooth way to the
    shape of it". The body's hull grows to take in each part problems() finds off it: a motor (its box, out to 2 mm
    short of its tyre), a pack outside the tub, a tail turntable too far out (a 40 mm block round its centre). The
    push plate always joins the body's hull, which fairs it in. Parts already on the body leave it as it is, so T3
    and the Trainer's layout don't change. The added hull weighs as the skin does (1.5 mm PLA, search.shell_mass).
    First, without a skin (Zach: "wheels must attach to the body, you can put them on different widths? that may fix
    some"): a loose wheel comes in toward the tub, each axle on its own width, to the widest place its motor reaches
    MOTOR_IN into it (the track knob is then the widest the wheels may sit). Only a wheel no width can attach (ahead
    of, behind or under the tub) grows the body. A skin wraps its motors, so its wheels never move."""
    c = cohesion(q, sp); body = sp['hulls'][0]; add = []
    if q['shell'] <= 0.5 and any(c[f'motor {i}'] < MOTOR_IN for i in range(len(sp['wheels']))):
        sp, c = _wheels_in(q, sp, c)
    for i, (x, y) in enumerate(sp['wheels']):
        if c[f'motor {i}'] < MOTOR_IN:
            sg = np.sign(y); y0, y1 = abs(y) - 31.0 - MOTOR_HALF[1], abs(y) - sp['TW'] / 2 - 2.0
            add.append(np.array([[x + a, sg * b, sp['R'] + e] for a in (-MOTOR_HALF[0], MOTOR_HALF[0]) for b in (y0, y1) for e in (-MOTOR_HALF[2], MOTOR_HALF[2])]))
    if q['shell'] <= 0.5:
        import chassis3 as C3
        b = C3.base(); dz = q['clr'] - b['clr0']
        for n, _, p in b['items']:
            if n in ('pack_L', 'pack_R') and c[n.replace('_', ' ')] > PACK_OUT:
                add.append(_grid(np.asarray(p, float) + [q['dxp'], 0.0, dz + q['dzp']], PACK_HALF, (2, 2, 2)))
    if sp.get('limb') and not TAIL_IN <= c['tail mount'] <= TAIL_OUT:  # buried or off it: the turntable to the rear surface
        sp = _mount_on_surface(sp); c = cohesion(q, sp)
    hulls = list(sp['hulls']); plate = q['bumper'] > 40.0
    if plate:
        add.append(hulls.pop())                                           # the plate, the last hull (make)
    if not add:
        return sp
    new = RB.hull(np.vstack([body] + add))
    M, cm, I = sp['M'], sp['com'], sp['I']
    for Q, s in ((body, -1.0), (new, 1.0)):                               # the skin's change: the old surface out, the new in
        m, cq, Iq = S.shell_mass(Q); M, cm, I = _add_body(M, cm, I, s * m, cq, s * Iq)
    notes = list(sp['notes']) + [f'body grown to {len(add) - plate} part(s) off it' if len(add) > plate else ''] + (['push plate faired into the body'] if plate else [])
    return RB.dims(dict(sp, hulls=[new] + hulls[1:], M=M, com=cm, I=I, plate_merged=plate, grown=len(add) - plate, notes=[n for n in notes if n]))


def _grid(c, h, n=(5, 9, 5)):
    ax = [np.linspace(ci - hi, ci + hi, k) for ci, hi, k in zip(c, h, n)]
    return np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)


def cohesion(q, sp):
    """how each part meets the body (hulls[0], the skin or the Trainer's tub), mm: a motor's depth into it (negative:
    a gap), the tail's turntable centre's distance outside it, the push plate's gap to it, a pack's worst corner
    outside it (no skin; a skin wraps the packs by construction)"""
    import chassis3 as C3
    body = sp['hulls'][0]; out = {}
    for i, (x, y) in enumerate(sp['wheels']):
        out[f'motor {i}'] = -float(RB.hull_dist(body, _grid((x, np.sign(y) * (abs(y) - 31.0), sp['R']), MOTOR_HALF)).min())
    if sp.get('limb'):
        out['tail mount'] = float(RB.hull_dist(body, [sp['limb']['base']])[0])
    if q['bumper'] > 40.0 and not sp.get('plate_merged'):
        P = sp['hulls'][-1]; lo, hi = P.min(0), P.max(0)
        out['push plate'] = float(RB.hull_dist(body, _grid((lo + hi) / 2, (hi - lo) / 2, (2, 9, 9))).min())
    if q['shell'] <= 0.5:
        b = C3.base(); dz = q['clr'] - b['clr0']
        for n, m, c in b['items']:
            if n in ('pack_L', 'pack_R'):
                c = np.asarray(c, float) + [q['dxp'], 0.0, dz + q['dzp']]
                out[n.replace('_', ' ')] = float(RB.hull_dist(body, _grid(c, PACK_HALF, (2, 2, 2))).max())
    return out


# ---------- a real build (2026-10-31) ----------
# Zach, when the search's winners grown as one piece (unibody.design_knobs) lost 20-120 mm of step: "an unrealistic
# robot in simulation can tell us things about design, it can give us general ideas of how knobs effect the design. it
# cannot give us a workable design ... the system works if the tests can be trusted". The strict build still passed
# what the one-piece print can't have:
#   weight: the body weighs as its print, unibody's 6 mm shell (two 1.6 mm walls, 15 % infill)*, pods to the motors,
#     the tail's boss and TPU bumpers*: fitted to 36 one-piece shapes drawn from the wide and low runs' designs (mean
#     error 3.9 %, worst 14 %; the shell alone, by theory, 4.49e-3 g a mm2). The search had counted a 1.5 mm skin or the
#     Trainer's 415 g tub and carapace: 0.8-1.2 kg light, and its winners' servos were too weak for the real weight.
#   pods: each motor's pod past the body's width is in the sims (the strict build had motors as mass only).
#   (Wheel wells, tried the same day and dropped: the hull lies within 10 mm of the print's outer surface, and the
#     print's wheel rooms hold only the tyres, so the hull meets a step as the print would; cut back as boxes round the
#     tyres, it took skin the print keeps. The step readings that seemed to tell wells apart were seed noise: T3 at the
#     one piece's weight reads 50, 90 or 150 mm from one set of tries to the next.)
#   motor fit: the picked gearmotor (JGB37-520, unibody.MOT), placed as the one piece holds it, clear of every part
#     inside (the packs, ESCs, UBECs ...).
#   mounts: a flipper's servo on the body, its pivot within MOUNT_OUT* of it (as the tail's turntable, TAIL_OUT).
PRINT_G_MM2, PRINT_G0 = 4.617e-3, 180.4                     # g a mm2 of the body's hull, g
BUMP_G_MM2, BUMP_G_POD, BUMP_G0 = 1.034e-3, 0.295, 38.0     # the bumpers: g a mm2, g a mm of pod past the hull's width, g
WELL_GAP, MOUNT_OUT = 5.0, 30.0                             # mm a pod stops short of its tyre (unibody.WHEEL_GAP); a flipper pivot off the body


def _uni():
    """unibody, for its motor and pod geometry (imported late; it sets SCORPION_SEARCH when unset, put back here)"""
    had = 'SCORPION_SEARCH' in os.environ
    import unibody as U
    if not had:
        os.environ.pop('SCORPION_SEARCH', None)
    return U


def _bosses(sp):
    """each wheel's motor as the one piece holds it (unibody._boss): [(x, side, boss)]"""
    U = _uni(); R, TW = sp['R'], sp['TW']; dish = R - U.RIM_IN - U.WHEEL_GAP >= U.POD_R + 2.0
    return [(x, np.sign(y), U._boss(x, abs(y), R, TW, dish)) for x, y in sp['wheels']]


def _counted_body(q, sp):
    """the body's mass as the search counted it, (g, centre, inertia): the skin (search.shell_mass of the hull), or the
    Trainer's printed structure (chassis3's STRUCT items) with _cohere's added skin; the push plate's 75 g on either"""
    import chassis3 as C3
    body = np.asarray(sp['hulls'][0], float)
    if q['shell'] > 0.5:
        M, c, I = S.shell_mass(body)
    else:
        p = dict(zip(S.KEYS, sp['x'])); D = C3.design({k: p[k] for k in C3.KEYS})
        M, c, I = RB.inertia([it for it in D['items'] if it[0].startswith(S.STRUCT)], D['box'])
        if sp.get('grown') or sp.get('plate_merged'):                  # _cohere's skin on the grown hull, less the tub's
            for Q, s in ((body, 1.0), (np.asarray(D['pts'], float), -1.0)):
                m, cq, Iq = S.shell_mass(Q); M, c, I = _add_body(M, c, I, s * m, cq, s * Iq)
    if q['bumper'] > 40.0:                                              # the plate (_make), now part of the print
        z1 = q['bumper']; M, c, I = _add_body(M, c, I, 75.0, np.array([body[:, 0].max(), 0.0, (max(30.0, z1 - 60.0) + z1) / 2]), np.zeros((3, 3)))
    return M, c, I


def print_mass(q, sp):
    """the body's printed mass with its bumpers, spread as the hull's skin: (g, centre, inertia)"""
    from scipy.spatial import ConvexHull
    body = np.asarray(sp['hulls'][0], float); A = ConvexHull(body).area; hy = float(body[:, 1].max())
    pods = sum(2 * max(0.0, b['y1'] - hy) for _, s, b in _bosses(sp) if s > 0)
    g = PRINT_G_MM2 * A + PRINT_G0 + BUMP_G_MM2 * A + BUMP_G_POD * pods + BUMP_G0
    m, c, I = S.shell_mass(body)
    return g, c, I * (g / m)


def _real(q, sp):
    """the spec with its body's counted mass swapped for its print's"""
    m0, c0, I0 = _counted_body(q, sp); m1, c1, I1 = print_mass(q, sp)
    M, c, I = _add_body(sp['M'], sp['com'], sp['I'], -m0, c0, -I0); M, c, I = _add_body(M, c, I, m1, c1, I1)
    return RB.dims(dict(sp, M=M, com=c, I=I, print_g=m1, notes=list(sp['notes']) + [f'printed body {m1:.0f} g (counted {m0:.0f})']))


def real_problems(q, sp):
    """what a real build can't have: a motor through a part inside ('motor: N mm into pack_L'), a flipper's pivot off
    the body"""
    U = _uni(); out = []; body = np.asarray(sp['hulls'][0], float)
    C, _, _, clr0 = U.B.parts(); dz = q['clr'] - clr0; a = np.linspace(0, 2 * np.pi, 16, endpoint=False); worst = {}
    parts = {k: RB.hull(np.asarray(P, float) + ([q['dxp'], 0.0, dz + q['dzp']] if k.startswith('pack') else [0.0, 0.0, dz]))
             for k, P in C.items() if not (_head_out(q) and k in S.HEAD)}   # the head on top: head_problems
    for x, s, b in _bosses(sp):
        ys = s * np.linspace(b['face'] - U.MOT_L, b['face'], 6); R = sp['R']
        Mp = np.vstack([np.c_[x + U.MOTOR_R * np.cos(a), np.full(16, yy), R + U.MOTOR_R * np.sin(a)] for yy in ys])
        for k, Q in parts.items():                                      # the motor's surface in the part, or the part in the motor
            r = np.hypot(Q[:, 0] - x, Q[:, 2] - R); inside = (np.abs(Q[:, 1] - ys.mean()) < U.MOT_L / 2)
            d = min(float(RB.hull_dist(Q, Mp).min()), float((r[inside] - U.MOTOR_R).min()) if inside.any() else 1e9)
            if d < 0.0:
                worst[k] = min(worst.get(k, 0.0), d)
    out += [f'motor: {-d:.0f} mm into {k}' for k, d in sorted(worst.items(), key=lambda t: t[1])]
    fl = sp.get('flip')
    if fl:
        d = max(float(RB.hull_dist(body, [p])[0]) for p in fl['pivots'])
        if d > MOUNT_OUT:
            out.append(f'flipper: {d:.0f} mm off the body')
    return out


# ---------- the head as its own module (2026-11-07) ----------
# Zach: "I dont think we should include the pan tilt in this box. Theres a good chance that is going to be blocked in
# some way for most bodies. We would want the flexibility to be able to move that somewhere else." The body (skin or
# Trainer hull) leaves the head out (search.HEAD_OUT); the head's base sits flat on the body's top, on the highest point
# under its footprint, the pan axis on the centre line at head_f of the way from the back to the front (the base wholly
# over the body fore and aft). Its 210 g moves with it. In the sims it is two hulls, base and drum, cradle and ball, part
# of the body (it lands in falls and stops the tail), last in the hull list (head_n of them). Not modelled: a dome or
# guard over it, and the cradle's 44 mm pan sweep against a body that rises past the base's footprint.
HEAD_SEAT_IN = 5.0                                          # mm: the base's footprint pulled in, so it sits on the body, not its edge


def _head_out(q):
    return 'head_f' in q


def _top_z(body, xy):
    """the convex hull's top surface over each (x, y): nan outside its outline"""
    from scipy.spatial import ConvexHull
    E = ConvexHull(body).equations; up, dn, side = E[:, 2] > 1e-9, E[:, 2] < -1e-9, np.abs(E[:, 2]) <= 1e-9
    xy = np.asarray(xy, float); z = np.full(len(xy), np.nan)
    top = (-(xy @ E[up, :2].T + E[up, 3]) / E[up, 2]).min(1)
    low = (-(xy @ E[dn, :2].T + E[dn, 3]) / E[dn, 2]).max(1) if dn.any() else np.full(len(xy), -np.inf)
    ok = top >= low
    if side.any():
        ok &= ((xy @ E[side, :2].T + E[side, 3]) <= 1e-6).all(1)
    z[ok] = top[ok]
    return z


def _place_head(q, sp):
    """the spec with the head seated on the body's top at head_f (see above); refused (None) when no body is under it"""
    import chassis3 as C3
    C = S.components(); b = C3.base(); dz = q['clr'] - b['clr0']
    H = {k: np.asarray(C[k], float) + [0.0, 0.0, dz] for k in S.HEAD}
    D = H['drum']; pan0 = 0.5 * (D.min(0) + D.max(0)); z_b0 = float(H['base'][:, 2].min())
    foot = H['base'][:, :2] - pan0[:2]; f_lo, f_hi = float(foot[:, 0].min()), float(foot[:, 0].max())
    body = np.asarray(sp['hulls'][0], float); x0, x1 = float(body[:, 0].min()), float(body[:, 0].max())
    lo, hi = x0 - f_lo, x1 - f_hi
    xp = lo + q['head_f'] * (hi - lo) if hi > lo else 0.5 * (x0 + x1 - f_lo - f_hi)
    F = foot[np.unique(np.round(foot / 4.0), axis=0, return_index=True)[1]]        # a 4 mm sample of the footprint
    c = F.mean(0); F = c + (F - c) * np.maximum(0.0, 1.0 - HEAD_SEAT_IN / np.maximum(np.linalg.norm(F - c, axis=1), 1e-9))[:, None]
    zt = _top_z(body, F + [xp, 0.0])
    if np.isnan(zt).all():
        return None
    d = np.array([xp - pan0[0], -pan0[1], float(np.nanmax(zt)) - z_b0])
    heads = [RB.hull(np.vstack([H['base'], H['drum']]) + d), RB.hull(np.vstack([H['cradle'], H['ball']]) + d)]
    m, p0 = next((m, np.asarray(p, float) + [0.0, 0.0, dz]) for n, m, p in b['items'] if n == 'head')
    M, cm, I = _add_body(sp['M'], sp['com'], sp['I'], -m, p0, np.zeros((3, 3)))
    M, cm, I = _add_body(M, cm, I, m, p0 + d, np.zeros((3, 3)))
    note = f'head on top at x {xp:.0f} (f {q["head_f"]:.2f}), seat z {d[2] + z_b0:.0f}'
    return RB.dims(dict(sp, hulls=list(sp['hulls']) + heads, head_n=2, head=dict(pan=[float(xp), 0.0, float(d[2] + z_b0)], f=float(q['head_f'])),
                        M=M, com=cm, I=I, notes=list(sp['notes']) + [note]))


def head_hulls(sp):
    return sp['hulls'][len(sp['hulls']) - sp.get('head_n', 0):] if sp.get('head_n') else []


def head_problems(sp):
    """the head in the way of the tail or a flipper: the stowed tail through it, the tail's turntable (40 mm across) on
    it, a flipper's sweep through it"""
    out = []; Hs = head_hulls(sp); lm = sp.get('limb'); fl = sp.get('flip')
    if lm:
        P = RB.limb_points(lm, 0.0, lm['th_stow'], k=24); P = P[np.linalg.norm(P - np.asarray(lm['base']), axis=1) > 20.0]
        if any((RB.hull_dist(Hh, P) < RB.LINK_R - 1.0).any() for Hh in Hs):
            out.append('tail: stowed through the head')
        if min(float(RB.hull_dist(Hh, [lm['base']])[0]) for Hh in Hs) < 20.0:
            out.append("tail mount: in the head's way")
    if fl and RB._sweep_hits(Hs, fl):
        out.append('flipper: sweeps through the head')
    return out


def body_print_size(sp):
    """the body's print, (length, width, height) mm: the hull and its motor pods (_real_shape); not the head, the tail
    or the claws"""
    sh = _real_shape(dict(sp, hulls=sp['hulls'][:len(sp['hulls']) - sp.get('head_n', 0)]))
    P = np.vstack([sh['hulls'][0]] + sh['hulls'][1:1 + sh['pods']])
    return tuple(float(v) for v in P.max(0) - P.min(0))


def cap_problems(q, sp, cap):
    """the body's print over the cap on any side (Zach, 2026-11-07: 250 mm for the body and wheels, not the claws and
    tail: long prints in tougher materials are the risk). The Trainer's own body is its 276 mm tub and claws: over"""
    if q['shell'] <= 0.5:
        return [f"size: the Trainer's own body (tub 276 mm), over the {cap:.0f} mm cap"]
    L, W, H = body_print_size(sp)
    return [f'size: body {L:.0f} x {W:.0f} x {H:.0f} mm, over the {cap:.0f} mm cap'] if max(L, W, H) > cap else []


def _real_shape(sp):
    """the sims' body: the hull as it is (the print's outer surface; wells were tried and dropped, see above), with each
    motor's pod past the body's width, TUBE_R round its axle out to WELL_GAP short of its tyre"""
    U = _uni(); P = np.asarray(sp['hulls'][0], float); R, TW = sp['R'], sp['TW']; hy = float(P[:, 1].max())
    a = np.linspace(0, 2 * np.pi, 12, endpoint=False); pods = []
    for x, s, b in _bosses(sp):
        y1 = b['y'] - TW / 2 - WELL_GAP
        if y1 > hy - 5.0:
            pods.append(np.vstack([np.c_[x + U.T.TUBE_R * np.cos(a), np.full(12, s * yy), R + U.T.TUBE_R * np.sin(a)] for yy in (hy - 5.0, y1)]))
    return dict(sp, hulls=[P] + pods + list(sp['hulls'][1:]), pods=len(pods))


def screen(a):
    tag, ch, seed = a
    sp = make(dict(T3, **ch))
    if sp is None:
        return tag, ch, seed, None
    s = S.screen_lean(sp, seed, cut=False); s.update(S.statics(sp))
    G = S.com_all(sp); s.update(tip_static=H.tip_static(sp), com_x=float(G[0]), com_z=float(G[2]),
                                **{k: sp[k] for k in ('mass', 'length', 'width', 'height', 'belly')})
    for down, g in ((False, 'up'), (True, 'down')):
        s['h_' + g] = H.ladder(sp, H.GRIP, down, H.N_SCREEN, seed)[0]
        s['hb_' + g] = max(H.ladder(sp, H.GRIP, down, H.N_SCREEN, seed, th)[0] for th in BRACE) if sp.get('limb') else None
    return tag, ch, seed, s


def jobs():
    J = [('T3', {}, 85000 + i) for i in range(T3_SEEDS)]
    for _, k, lo, hi, _ in KNOBS:
        for v in np.linspace(lo, hi, N_VAL):
            J += [(k, {k: float(v)}, 85000 + i) for i in range(SEEDS)]
    for nm, ch in SWITCHES:
        J += [(nm, ch, 85000 + i) for i in range(SEEDS)]
    return J


G_KEYS = ('up', 'climb', 'turn', 'h_up', 'h_down', 'hb_up', 'hb_down', 'crest', 'push')


def summarise(rows):
    """per knob and value: the gauges' means over the seeds, the screen's statics, and T3's noise (sd over its seeds)"""
    by = {}
    for r in rows:
        k = r['tag']; v = r['ch'].get(k) if k in r['ch'] else None
        by.setdefault(k, {}).setdefault(v, []).append(r['s'])
    mean = lambda ss, g: (None if not ss or any(q.get(g) is None for q in ss) else float(np.mean([q[g] for q in ss])))
    res = {}
    for k, vs in by.items():
        res[k] = []
        for v, ss in sorted(vs.items(), key=lambda t: -1e9 if t[0] is None else t[0]):
            ok = [q for q in ss if q is not None]
            res[k].append(dict(v=v, built=len(ok), of=len(ss), **{g: mean(ok, g) for g in G_KEYS + ('tip_static', 'com_x', 'com_z', 'mass', 'length', 'width', 'height', 'belly')}))
    t3 = [r['s'] for r in rows if r['tag'] == 'T3']
    noise = {g: float(np.std([q[g] for q in t3])) for g in G_KEYS if g not in ('crest', 'push')   # read once, copied to every seed
             and all(q.get(g) is not None for q in t3)}
    return res, noise


def sweep():
    os.makedirs(OUT, exist_ok=True); J = jobs(); raw = os.path.join(OUT, 'knobs_raw.jsonl'); t0 = time.time()
    done = set(); stamp.check(raw)                                        # only rows made by this code
    if os.path.exists(raw):                                               # resume after a stop
        done = {(r['tag'], json.dumps(r['ch'], sort_keys=True), r['seed']) for r in map(json.loads, open(raw))}
    J = [j for j in J if (j[0], json.dumps(j[1], sort_keys=True), j[2]) not in done]
    print(f'{len(J)} screens to run ({len(done)} done)', flush=True)
    with Pool(GG.WORKERS) as pool, open(raw, 'a') as f:
        for i, (tag, ch, seed, s) in enumerate(pool.imap_unordered(screen, J, chunksize=1)):
            f.write(json.dumps(dict(tag=tag, ch=ch, seed=seed, s=s), default=float) + '\n'); f.flush()
            if i % 30 == 0:
                print(f'{i + 1}/{len(J)}, {time.time() - t0:.0f} s', flush=True)
    write()


BRACE_ALL = (-75.0, -60.0, -45.0, -30.0, -15.0)


def brace_job(a):
    tag, ch = a; sp = make(dict(T3, **ch)); out = {}
    for down, g in ((False, 'up'), (True, 'down')):
        r = {th: H.ladder(sp, H.GRIP, down, H.N_SCREEN, 85000, th)[0] for th in BRACE_ALL}
        out['hb_' + g] = max(r.values()); out['hb_' + g + '_th'] = max(r, key=lambda t: (r[t], t)); out['hb_' + g + '_all'] = r
    return tag, ch, out


def rebrace():
    """the braced hills again, over BRACE_ALL, one seed (T3's hills don't move over 8 seeds). The sweep's -30 and -15
    left the foot in the air once the body or the mount rose or the tail got short. -> knobs_brace.jsonl"""
    rows = [json.loads(l) for l in open(os.path.join(OUT, 'knobs_raw.jsonl'))]
    bf = os.path.join(OUT, 'knobs_brace.jsonl'); stamp.check(bf)
    done = {(b['tag'], json.dumps(b['ch'], sort_keys=True)) for b in map(json.loads, open(bf))} if os.path.exists(bf) else set()
    J = [(r['tag'], r['ch']) for r in rows if r['seed'] == 85000 and r['s'] is not None and r['s'].get('hb_up') is not None
         and (r['tag'], json.dumps(r['ch'], sort_keys=True)) not in done]                # only designs not braced yet
    t0 = time.time()
    with Pool(GG.WORKERS) as pool, open(bf, 'a') as f:
        for i, (tag, ch, out) in enumerate(pool.imap_unordered(brace_job, J, chunksize=1)):
            f.write(json.dumps(dict(tag=tag, ch=ch, **out), default=float) + '\n'); f.flush()
    print(f'{len(J)} designs braced again, {time.time() - t0:.0f} s'); write()


def write():
    """knobs_sweep.json from the raw screens, the braced hills from knobs_brace.jsonl where it exists (the sweep's own,
    over -30 and -15, kept as hb_*_2)"""
    rows = [json.loads(l) for l in open(os.path.join(OUT, 'knobs_raw.jsonl'))]; bf = os.path.join(OUT, 'knobs_brace.jsonl')
    if os.path.exists(bf):
        B = {(b['tag'], json.dumps(b['ch'], sort_keys=True)): b for b in map(json.loads, open(bf))}
        for r in rows:
            b = B.get((r['tag'], json.dumps(r['ch'], sort_keys=True)))
            if b and r['s'] is not None:
                for g in ('up', 'down'):
                    r['s']['hb_' + g + '_2'] = r['s']['hb_' + g]; r['s']['hb_' + g] = b['hb_' + g]; r['s']['hb_' + g + '_th'] = b['hb_' + g + '_th']
    gf = os.path.join(OUT, 'knobs_g67.jsonl')
    if os.path.exists(gf):                                                # crest and push: one seed, given to every seed's row
        Q = {(q['tag'], json.dumps(q['ch'], sort_keys=True)): q for q in map(json.loads, open(gf))}
        for r in rows:
            q = Q.get((r['tag'], json.dumps(r['ch'], sort_keys=True)))
            if q and r['s'] is not None:
                r['s'].update(crest=q['crest'], push=q['push'])
    res, noise = summarise(rows)
    t3 = res['T3'][0]
    json.dump(dict(base=T3, brace=BRACE_ALL if os.path.exists(bf) else BRACE, knobs=[dict(group=g, key=k, lo=lo, hi=hi, what=w) for g, k, lo, hi, w in KNOBS],
                   switches=[n for n, _ in SWITCHES], noise=noise, results=res), open(os.path.join(OUT, 'knobs_sweep.json'), 'w'), indent=1, default=float)
    print(f"T3: {t3}\nnoise (sd over {T3_SEEDS} seeds): {noise}")
    for _, k, *_ in KNOBS:
        print(f'{k:8s} ' + '  '.join(f"{r['v']:.3g}: {r['up'] if r['up'] is None else round(r['up'], 2)}/{r['climb'] and round(r['climb'])}/{r['turn'] and round(r['turn'])} "
                                    f"h {r['h_up'] and round(r['h_up'])}/{r['h_down'] and round(r['h_down'])} b {r['hb_up'] and round(r['hb_up'])}/{r['hb_down'] and round(r['hb_down'])}"
                                    for r in res[k]), flush=True)
    for nm, _ in SWITCHES:
        r = res[nm][0]; print(f"{nm}: {r['up']:.2f}/{r['climb']:.0f}/{r['turn']:.0f} h {r['h_up']}/{r['h_down']} b {r['hb_up']}/{r['hb_down']}")


SIDE_POSES = ((None, None), (90.0, -30.0), (90.0, -45.0))               # stowed; the tail out down the slope, braced


def side_job(a):
    name, ch, mu, pose, top_kg = a
    sp = make(dict(T3, **ch))
    if top_kg:
        sp = H.add_mass(sp, 1000.0 * top_kg, (float(sp['com'][0]), 0.0, float(sp['hulls'][0][:, 2].max()) - 20.0), name)
    top, seen = H.side_ladder(sp, mu, 10, 61, *pose)
    return a, top, seen.get(top + 5), H.side_static(sp), float(S.com_all(sp)[2]), sp['width']


def side():
    """a side slope (exploratory): T3 and its width and height knobs, tail stowed and out as an outrigger, at x2.5 and
    x1. The control: 1 kg on top must read lower wherever tipping binds. -> out/knobs/side.json"""
    specs = [('T3', {}, 0), ('track 110', dict(track=110.0), 0), ('track 145', dict(track=145.0), 0), ('track 180', dict(track=180.0), 0),
             ('tyres 25 wide', dict(TW=25.0), 0), ('tyres 80 wide', dict(TW=80.0), 0), ('ride height 15', dict(clr=15.0), 0),
             ('ride height 90', dict(clr=90.0), 0), ('T3, 1 kg on top', {}, 1)]
    J = [(n, ch, mu, pose, kg) for n, ch, kg in specs for mu in (H.GRIP, 1.0) for pose in SIDE_POSES]
    t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(side_job, J, chunksize=1)
    out = []
    for (n, ch, mu, pose, kg), top, why, st, cz, w in R:
        out.append(dict(name=n, mu=mu, tail='stowed' if pose[0] is None else f'yaw {pose[0]:.0f}, pitch {pose[1]:.0f}', side=top, why=why,
                        static=st, com_z=cz, width=w))
        print(f"{n:18s} x{mu:<4} tail {out[-1]['tail']:20s} side {top:3d} (next: {why})  static {st:.1f}  CoM z {cz:.1f}  width {w:.0f}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), rows=out), open(os.path.join(OUT, 'side.json'), 'w'), indent=1, default=str)
    print(f'{len(J)} ladders, {time.time() - t0:.0f} s')


def g67_job(a):
    import crest as CR, push as PU
    tag, ch = a; sp = make(dict(T3, **ch))
    if sp is None:
        return tag, ch, None
    c, cs = CR.ladder(sp, CR.GRIP, H.N_SCREEN, 85000)
    P = {mu: PU.ladder(sp, mu, H.N_SCREEN, 85000) for mu in GG.BAND}; w = min(P, key=lambda mu: P[mu][0])
    return tag, ch, dict(crest=c, crest_why=cs.get(c + 5), push=P[w][0], push_mu=w, push_by_mu={str(mu): v[0] for mu, v in P.items()},
                         push_why=P[w][1].get(PU.nxt(P[w][0])))


def sweep67():
    """G6 crest and G7 push for every design of the sweep, one seed, 6 tries (the screen's): crest at x2.5, push the
    worst over the band. -> knobs_g67.jsonl, then knobs_sweep.json"""
    gf = os.path.join(OUT, 'knobs_g67.jsonl'); stamp.check(gf)
    done = {(q['tag'], json.dumps(q['ch'], sort_keys=True)) for q in map(json.loads, open(gf))} if os.path.exists(gf) else set()
    J = [(t, c) for t, c, sd in jobs() if sd == 85000 and (t, json.dumps(c, sort_keys=True)) not in done]; t0 = time.time()
    print(f'{len(J)} designs for crest and push', flush=True)
    with Pool(GG.WORKERS) as pool, open(gf, 'a') as f:
        for i, (tag, ch, out) in enumerate(pool.imap_unordered(g67_job, J, chunksize=1)):
            if out is not None:
                f.write(json.dumps(dict(tag=tag, ch=ch, **out), default=float) + '\n'); f.flush()
            if i % 30 == 0:
                print(f'{i + 1}/{len(J)}, {time.time() - t0:.0f} s', flush=True)
    write()


def rule_angle(sp):
    """the brace angle that puts the foot just on the ground, degrees (pitch below level), within the servo's range"""
    lm = sp['limb']; r = lm.get('foot_r', RB.FOOT_R)
    return max(-75.0, min(-5.0, math.degrees(math.asin(max(-1.0, min(1.0, (r - lm['base'][2]) / lm['L']))))))


def rule_job(a):
    tag, ch = a; sp = make(dict(T3, **ch)); th = rule_angle(sp)
    return tag, ch, dict(th=th, **{'hr_' + g: H.ladder(sp, H.GRIP, d, H.N_SCREEN, 85000, th)[0] for d, g in ((False, 'up'), (True, 'down'))})


def brace_rule():
    """K3: does a rule (the foot just on the ground) pick as well as the best of five held angles? Every braced
    design at its rule angle, one seed. -> knobs_brace_rule.jsonl"""
    B = list(map(json.loads, open(os.path.join(OUT, 'knobs_brace.jsonl')))); t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(rule_job, [(b['tag'], b['ch']) for b in B], chunksize=1)
    by = {(t, json.dumps(c, sort_keys=True)): o for t, c, o in R}; tally = {}
    with open(os.path.join(OUT, 'knobs_brace_rule.jsonl'), 'w') as f:
        for b in B:
            o = by[(b['tag'], json.dumps(b['ch'], sort_keys=True))]
            f.write(json.dumps(dict(tag=b['tag'], ch=b['ch'], best_up=b['hb_up'], best_down=b['hb_down'], **o)) + '\n')
            for g in ('up', 'down'):
                dd = o['hr_' + g] - b['hb_' + g]; tally[(g, dd)] = tally.get((g, dd), 0) + 1
    print(f'{len(B)} designs, {time.time() - t0:.0f} s; rule minus best (degrees: count):', {f'{g} {d:+d}': n for (g, d), n in sorted(tally.items())})


SPEEDS = (0.15, 0.25, 0.5, 0.8)


def speed_job(a):
    name, ch, v, down, th, mu = a; sp = make(dict(T3, **ch))
    H.V_HILL, H.T_HILL = v, max(8.0, H.HILL_MM * 1e-3 / v + H.RAMP + 2.0)   # the 2.5 m at v, with room (8 s timed out every try under 0.5)
    if th == 'rule':
        th = rule_angle(sp)
    return a, H.ladder(sp, mu, down, 20, 61, th)


def speed():
    """K6: the hills at other driving speeds (H.V_HILL, 0.5 m/s in the gauge), T3 and two knob extremes, stowed and
    braced at the rule angle, 20 tries, at x2.5 and x1. -> speed.json"""
    designs = [('T3', {}), ('ride height 90', dict(clr=90.0)), ('tyre gap 150', dict(gap=150.0))]
    J = [(n, ch, v, down, th, mu) for n, ch in designs for v in SPEEDS for down in (False, True) for th in (None, 'rule') for mu in (H.GRIP, 1.0)]
    t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(speed_job, J, chunksize=1)
    out = [dict(name=n, v=v, down=down, tail='stowed' if th is None else 'braced', mu=mu, top=top, why=seen.get(top + 5))
           for (n, ch, v, down, th, mu), (top, seen) in R]
    for n, _ in designs:
        for mu in (H.GRIP, 1.0):
            line = []
            for v in SPEEDS:
                g = {(r['down'], r['tail']): r['top'] for r in out if r['name'] == n and r['v'] == v and r['mu'] == mu}
                line.append(f"{v}: {g[(False, 'stowed')]}/{g[(True, 'stowed')]} b {g[(False, 'braced')]}/{g[(True, 'braced')]}")
            print(f'{n:15s} x{mu}: ' + '  '.join(line), flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), rows=out), open(os.path.join(OUT, 'speed.json'), 'w'), indent=1, default=str)


def crest20_job(a):
    import crest as CR
    tag, ch = a; sp = make(dict(T3, **ch)); c, cs = CR.ladder(sp, CR.GRIP, 20, 85000)
    return tag, ch, c, cs.get(c + 5)


def crest20():
    """G6 again at the gauge's 20 tries for every design: at 6, T3 (which tips about 1 try in 6 at 30 degrees) passed
    or failed by luck, and its push-angle neighbours read 40 against its 25. Rewrites knobs_g67.jsonl's crest (the
    6-try reading kept as crest_6), then knobs_sweep.json"""
    gf = os.path.join(OUT, 'knobs_g67.jsonl'); Q = [json.loads(l) for l in open(gf)]
    J = [(q['tag'], q['ch']) for q in Q if 'crest_6' not in q]; t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(crest20_job, J, chunksize=1)
    by = {(t, json.dumps(c, sort_keys=True)): (v, w) for t, c, v, w in R}
    with open(gf, 'w') as f:
        for q in Q:
            k = (q['tag'], json.dumps(q['ch'], sort_keys=True))
            if k in by:
                q['crest_6'], q['crest_why_6'] = q['crest'], q['crest_why']; q['crest'], q['crest_why'] = by[k]
            f.write(json.dumps(q, default=float) + '\n')
    print(f'{len(J)} designs, crest at 20 tries, {time.time() - t0:.0f} s'); write()


def grip_job(a):
    g, down, th, mu = a; sp = make(dict(T3, tyre_mu=g))
    return a, H.ladder(sp, mu, down, 20, 61, rule_angle(sp) if th else None)


def grip_hills():
    """K1: tread grip on the hills on ordinary ground (x1) and the band's slipperiest (x0.65), where the tyres bind;
    the sweep reads hills at x2.5, where they don't. T3, stowed and braced at the rule angle, 20 tries. -> grip_hills.json"""
    G_ = (0.5, 0.75, 1.0, 1.25, 1.5, 1.8); J = [(g, d, th, mu) for g in G_ for d in (False, True) for th in (False, True) for mu in (0.65, 1.0)]
    with Pool(GG.WORKERS) as pool:
        R = pool.map(grip_job, J, chunksize=1)
    out = [dict(grip=g, down=d, tail='braced' if th else 'stowed', mu=mu, top=top, why=seen.get(top + 5)) for (g, d, th, mu), (top, seen) in R]
    for mu in (0.65, 1.0):
        print(f'x{mu}: ' + '  '.join(f"grip {g}: " + '/'.join(str(next(r['top'] for r in out if r['grip'] == g and r['mu'] == mu and r['down'] == d and r['tail'] == t))
                                                       for t in ('stowed', 'braced') for d in (False, True)) for g in G_), flush=True)
    json.dump(dict(rows=out), open(os.path.join(OUT, 'grip_hills.json'), 'w'), indent=1, default=str)


# The knob review (2026-10-28, README "Which knobs matter"). Zach: "yes" to dropping the dead two and checking the
# settled ones. DEAD are held at T3's in every search from here; SETTLED only cost when moved off T3's value (af too,
# which the review's list missed: T3 sits 10 mm from its climb cliff); LEVERS trade one gauge for another.
DEAD = ('cu', 'qu')
SETTLED = ('track', 'TW', 'b', 'p', 'ar', 'xc', 'cd', 'qd', 'dzp', 'msize', 'foot_r', 'th_push', 'th_stow', 'af')
LEVERS = ('gap', 'xw', 'clr', 'zc', 'dxp', 'R', 'mount_z')
FREEZE_ARMS = (('free', ()), ('settled frozen', SETTLED), ('levers frozen', LEVERS))   # the last is the control
HELD = DEAD + ('tyre_mu', 'bumper')                       # never searched here: the tread is a property, the push face a switch


def freeze_job(a):
    arm, tag, q, seed = a
    sp = make(dict(T3, **q))
    if sp is None:
        return a, None
    s = S.screen_lean(sp, seed)
    return a, dict(up=s['up'], climb=s['climb'], turn=s['turn'])


def freeze(n_b=256, gens=6, pop=60, ws=(0.25, 1.0)):
    """does freezing the settled knobs at T3's cost a search anything? Three searches over the knob log's space (its
    switches off, HELD at T3's): every knob free; SETTLED held at T3's; LEVERS held at T3's (the control: it must lose
    some of the front). Each starts from the same n_b designs (an arm overwrites its held knobs with T3's) and
    refines by cross-entropy under each weighting in ws (climb - w * turn, upright at least S.UP_SCREEN), every arm on
    the same seeds. Read: the front (climb against turn) and its area. -> out/knobs/freeze.json
    From random designs, holding knobs at T3's is a head start (T3's values are near the best) and the control would
    pass for the wrong reason (a smoke run had both held arms beat the free one), so every arm starts at T3 and the
    designs within a quarter of each knob's range of it: the claim is about T3's neighbourhood, as the sweep was."""
    from scipy.stats import qmc
    K = [(k, lo, hi) for _, k, lo, hi, _ in KNOBS if k not in HELD]; keys = [k for k, _, _ in K]
    LO = np.array([lo for _, lo, _ in K]); HI = np.array([hi for _, _, hi in K]); span = HI - LO
    zT = np.array([T3[k] for k in keys])                                  # T3, then designs within a quarter of each range of it:
    U = qmc.Sobol(len(K), scramble=True, seed=41).random_base2(int(math.ceil(math.log2(n_b))))[:n_b - 1]   # the review's claim is
    Z0 = np.vstack([zT, np.clip(zT + (U - 0.5) * 0.5 * span, LO, HI)])                                    # about T3's neighbourhood
    def q_of(z, held):
        return {k: (T3[k] if k in held else float(v)) for k, v in zip(keys, z)}
    def score(r, w):
        return -1e9 if (r is None or r['up'] < S.UP_SCREEN or r['turn'] is None) else r['climb'] - w * r['turn']
    t0 = time.time(); rows = {arm: [] for arm, _ in FREEZE_ARMS}
    with Pool(GG.WORKERS) as pool:
        def run(J):
            out = pool.map(freeze_job, J, chunksize=1)
            for (arm, tag, q, seed), r in out:
                rows[arm].append(dict(tag=tag, q=q, seed=seed, **(r or dict(up=0.0, climb=0, turn=None))))
            return out
        run([(arm, 'B', q_of(z, held), 40000) for arm, held in FREEZE_ARMS for z in Z0])
        for arm, held in FREEZE_ARMS:
            ok = [r for r in rows[arm] if r['up'] >= S.UP_SCREEN and r['turn'] is not None]
            print(f"{arm:15s} B: {len(ok)} of {n_b} feasible, front {[(r['climb'], round(r['turn'])) for r in sorted(S.front(rows[arm]), key=lambda r: r['climb'])]}, {time.time() - t0:.0f} s", flush=True)
        rng = np.random.default_rng(43); free_ix = {arm: [i for i, k in enumerate(keys) if k not in held] for arm, held in FREEZE_ARMS}
        for j, w in enumerate(ws):                                        # one cross-entropy run per arm and weighting, as search.cem
            st = {}
            for arm, held in FREEZE_ARMS:
                el = sorted(rows[arm], key=lambda r: -score(r, w))[:8]; E = np.array([[r['q'][k] for k in keys] for r in el])
                st[arm] = [E.mean(0), np.maximum(E.std(0), 0.05 * span), el]
            for g in range(gens):
                J = []
                for arm, held in FREEZE_ARMS:
                    mu, sd, _ = st[arm]; Z = np.clip(mu + sd * rng.normal(size=(pop, len(keys))), LO, HI)
                    J += [(arm, f'C{w}', q_of(z, held), 50000 + 100 * j + g) for z in Z]
                new = run(J)
                for arm, held in FREEZE_ARMS:
                    got = [dict(q=q, **(r or dict(up=0.0, climb=0, turn=None))) for (a, _, q, _), r in new if a == arm]
                    mu, sd, el = st[arm]; el = sorted(el + got, key=lambda r: -score(r, w))[:8]
                    E = np.array([[r['q'][k] for k in keys] for r in el]); mu = 0.6 * E.mean(0) + 0.4 * mu
                    sd = np.maximum(0.6 * E.std(0) + 0.4 * sd * 0.8, 0.01 * span); st[arm] = [mu, sd, el]
                    b = el[0]
                    print(f"{arm:15s} w={w} gen {g}: best climb {b['climb']} turn {b['turn'] and round(b['turn'])} up {b['up']:.2f}; {time.time() - t0:.0f} s", flush=True)
    res = {}
    for arm, held in FREEZE_ARMS:
        F = sorted(S.front(rows[arm]), key=lambda r: r['climb'])
        area, prev = 0.0, 0                                               # the front's area against (0 mm climb, 900 mm turn)
        for r in F:
            area += (r['climb'] - prev) * max(0.0, 900.0 - min(o['turn'] for o in F if o['climb'] >= r['climb'])); prev = r['climb']
        res[arm] = dict(held=list(held), n=len(rows[arm]), front=[dict(climb=r['climb'], turn=r['turn'], up=r['up'], q=r['q']) for r in F], area=area)
        print(f"{arm:15s} front {[(r['climb'], round(r['turn'])) for r in F]}  area {area / 1e3:.1f} k", flush=True)
    a = {arm: res[arm]['area'] for arm in res}
    print(('PASS ' if a['levers frozen'] < 0.95 * a['free'] else 'FAIL ') + 'control: holding the levers loses at least 5% of the free front', flush=True)
    print(f"settled frozen: {a['settled frozen'] / a['free']:.3f} of the free front's area", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), n_b=n_b, gens=gens, pop=pop, ws=ws, keys=keys, arms=res), open(os.path.join(OUT, 'freeze.json'), 'w'), indent=1, default=float)


COHERE = [   # (name, changes to T3, whole as it is, built strict)
    ('T3', {}, True, True), ("the Trainer's own layout (no skin, no tail)", dict(shell=0.0, limb=0.0, R=55.0, xw=-1.0, gap=74.0, track=131.0, clr=32.4, dxp=0.0, dzp=0.0), True, True),
    ('T3, tail mount 170 mm', dict(mount_z=170.0), True, True),
    ('control: no skin, wheels out at track 180', dict(shell=0.0, track=180.0), False, True),
    ('control: no skin, six wheels on a long wheelbase', dict(shell=0.0, six=1.0, gap=120.0), False, True),
    ('control: no skin, packs 80 mm forward', dict(shell=0.0, dxp=80.0), False, True),
    ('control: tail mount 210 mm, skin 120 tall', dict(mount_z=210.0, zc=60.0), False, True),
    ('control: push plate topping at 100 mm', dict(bumper=100.0), False, True),
    ('control: skin reaching 250 mm back, burying the tail mount', dict(ar=250.0), False, True),
    ('control: 190 mm wheels on half-size motors geared 0.4x', dict(R=95.0, msize=0.5, gear=0.4), False, False),
    ('control: tail stowed forward over the top, 170 degrees', dict(th_stow=170.0), False, False)]


def cohere():
    """the one-body check: T3, the Trainer's own layout and T3's 170 mm tail mount pass; each control has a part
    off the body (or a drive too weak for its wheels) and must fail. Then strict: the body grown to its parts must
    pass, except the weak drive and a tail stowed through the body, which growing can't fix; T3 strict must be T3 to
    the gram; and a tail swung through the body must pass through it loose and stop on it strict"""
    for name, ch, want, want_st in COHERE:
        q = dict(T3, **ch); sp = make(q); pr = problems(q, sp) if sp is not None else ['not built']
        print(('PASS ' if (not pr) == want else 'FAIL ') + f'{name}: ' + ('; '.join(pr) if pr else 'every part on the body'))
        st = make(q, strict=True)
        print(('PASS ' if (st is not None) == want_st else 'FAIL ') + '   strict: ' + ('refused: ' + '; '.join(problems(q, _cohere(q, sp))) if st is None else
              f"built, {st['mass'] - sp['mass']:+.0f} g, {'; '.join(n for n in st['notes'] if any(w in n for w in ('grown', 'faired', 'in to the body', 'tail mount moved'))) or 'unchanged'}"))
    a, b = make(T3), make(T3, strict=True)
    same = a['mass'] == b['mass'] and np.array_equal(a['hulls'][0], b['hulls'][0]) and np.array_equal(a['com'], b['com'])
    print(('PASS ' if same else 'FAIL ') + 'T3 strict is T3 (mass, hull and centre of mass identical)')
    reach = {}
    for nm, sp in (('loose', a), ('strict', b)):                           # the tail swung forward through the body, 1 s
        sim = GG.Sim(sp); sim.place(GG.yaw_quat(0.0), 0.0005); sim.limb_goal(0.0, math.radians(RB.LIMB_PITCH[1]))
        for _ in range(200):
            sim.drive(None, None)
        reach[nm] = math.degrees(sim.limb_pose()[1])
    ok = reach['loose'] > 170.0 and reach['strict'] < reach['loose'] - 20.0
    print(('PASS ' if ok else 'FAIL ') + f"T3's tail swung forward to 180 degrees: loose reaches {reach['loose']:.0f}, strict stops at {reach['strict']:.0f} (the body)")


TRAINER = dict(shell=0.0, limb=0.0, R=55.0, xw=-1.0, gap=74.0, track=131.0, clr=32.4, dxp=0.0, dzp=0.0)
REAL = [   # (name, changes to T3, the refusal it must give (None: none))
    ("the Trainer's own layout", TRAINER, None), ('T3, track 130 (its motors clear)', dict(track=130.0), None),
    ('T3, track 130, a nose flipper', dict(track=130.0, flip=1.0, f_nose=1.0), None),
    ("the Trainer's layout, a nose flipper", dict(TRAINER, flip=1.0, f_nose=1.0), None),
    ('control: T3 as it is (track 114): its motors in the ESCs and packs', {}, 'motor'),
    ('control: T3, track 120', dict(track=120.0), 'motor'),
    ('control: T3, track 130, a flipper pair outside the tyres', dict(track=130.0, flip=1.0, f_nose=0.0), 'flipper'),
    ("control: the Trainer's layout, a flipper pair", dict(TRAINER, flip=1.0, f_nose=0.0), 'flipper')]


def real():
    """the real build's checks (2026-10-31), each with its control: the motor fit and the flipper mounts refuse what
    they should and only that; the printed weight replaces the counted one (T3: about +1.2 kg, as its one piece weighs);
    a pod goes in where a motor's wheel stands off the body (the Trainer's layout) and not where the skin wraps the
    motors (T3). Exits 1 on a failure"""
    bad = 0
    for name, ch, want in REAL:
        q = dict(T3, **ch); why = []; sp = make(q, real=True, why=why)
        got = None if not why else why[0].split(':')[0]; ok = got == want; bad += not ok
        print(('PASS ' if ok else 'FAIL ') + f"{name}: {'; '.join(why) if why else 'built'}")
    a, b = make(dict(T3, track=130.0), strict=True), make(dict(T3, track=130.0), real=True)
    ok = 1000.0 < b['mass'] - a['mass'] < 1400.0; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f"T3 at track 130 weighs {a['mass']:.0f} g strict, {b['mass']:.0f} g real (its one piece: about +1.2 kg)")
    tr = make(dict(T3, **TRAINER), real=True); ok = tr['pods'] == 4 and b['pods'] == 0; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f"pods in the sims: the Trainer's layout {tr['pods']} (its wheels stand off the tub), T3 {b['pods']} (its skin wraps the motors)")
    sys.exit(1 if bad else 0)


def check():
    """T3 rebuilt from its knobs must match the shape study's T3 (its mass and centre of mass)"""
    import pickle
    sp = make(T3); ref = {s['name']: s for s in pickle.load(open(os.path.join(config.GAUGES_OUT, 'search_shape', 'finals_specs.pkl'), 'rb'))}['T3']
    print(f"T3 rebuilt: mass {sp['mass']:.1f} (ref {ref['mass']:.1f}), CoM {np.round(S.com_all(sp), 2)} (ref {np.round(S.com_all(ref), 2)}), "
          f"tail base {sp['limb']['base']} (ref {ref['limb']['base']})")
    for k, v in (('clr', 80.0), ('TW', 70.0), ('mount_z', 200.0), ('track', 170.0)):
        q = make(dict(T3, **{k: v})); print(f"{k}={v}: mass {q['mass']:.1f}, CoM z {S.com_all(q)[2]:.1f}, belly {q['belly']:.1f}, TW {q['TW']}, base {np.round(q['limb']['base'], 1)}, width {q['width']:.0f}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'sweep': sweep, 'check': check, 'side': side, 'rebrace': rebrace, 'write': write, 'sweep67': sweep67, 'rule': brace_rule, 'speed': speed, 'crest20': crest20, 'grip': grip_hills, 'freeze': freeze, 'cohere': cohere, 'real': real}.get(cmd, lambda: print(__doc__))()
