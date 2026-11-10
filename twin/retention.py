"""Do the parts stay put? (2026-11-07) The brain box dropped and tumbled in MuJoCo, every loose part a free body at its
real mass and clearance, read for how far each part moves in the box. Zach: "it has to be able to be dropped and
rolled around without parts falling out of place ... you can test this in mujoco".

    python twin/retention.py            # every variant, both heights -> twin/out/retention.json and a table

The box is the Trainer tub's insides as print 1 has them (trainer_tub.parts(): his packs, his ESCs at caliper size, the
Pi stack, the PCA9685), without the head's nose. Boxes stand in for the print's walls, the tunnel ridge and the stops.
The rest of the robot (motors, wheels, pods, the tub itself) rides as one mass on the box: REST_G*. The box hits the
ground with no tyres, which is harsher than the robot.
Variants:
  print1   as printed: an open top, nothing holds anything (the control)
  lid      print 1 with a lid screwed on, nothing else
  held     the candidate: bays walled to the lid, a stop at both ends of each pack and ESC, the Pi and the PCA on
           standoffs (fixed to the box), and TPU pads under the lid pressing the packs and ESCs down
  fitted   held, with the ESC bay narrowed to his 24 mm ESC (print 1's is 26.5, built for the sim's 18 mm one*)
  pibox    fitted, but the Pi stack and the PCA held by a friction fit, no standoffs (Zach, 2026-11-07: "a friction
           fit box with the lid for the pi"): each loose in a pocket POCKET_MM* bigger all round, on TPU pads (the Pi's
           isolators), the lid pressing down through TPU pads on top. The PCA moved back 2.6 mm for a wall to the Pi
  frames   the modular floor (grid_eval.py, 2026-11-08): each part in its own low frame (FRAMES*, 0.25 clearance) pegged to the
           floor, the frame taken as rigid, no bay walls, and a lid pressing every part down through TPU pads
  frames_open  the same with no lid: what pegs and frames do alone (the control, and what a snap would have to replace)
  frames_short frames with the ESC's walls at ESC_SHORT (Zach, after the test print: "a bit shorter height on the box"). A press fit's
           grip isn't modelled, so the ESC keeps its clearance: that's the harsher case
A part is out of place when it ends more than OUT_MM* from where it started, in the box's frame.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import numpy as np
import mujoco as mj
import config

OUT = config.TWIN_OUT
Z0 = 7.4                                    # the model's floor underside; the print's z 0
REST_G = 3100.0                             # g: the robot less the loose parts* (about 3.9 kg in all)
MASS = dict(pack_L=300.0, pack_R=300.0, esc_L=55.0, esc_R=55.0, pi_stack=95.0, pca=12.0)   # g (rugged.mass_items, the sim's)
OUT_MM = 3.0                                # mm: out of place
WALL, FLOOR, TOP = 2.6, 2.6, 50.0           # mm, print 1: wall, floor top, wall top
X0, X1 = -142.0, 102.6                      # the box's ends: print 1's back; the front just past the packs (no nose)
Y_R, Y_L = -59.4 - WALL, 66.9 + WALL        # outer walls: 0.5 mm off the packs' outer faces
DIV_L, DIV_R = 39.4, -31.9                  # the bays' inner sides (print 1: the tunnel ridge, 1.0 off the packs)
RIDGE = 23.2                                # the tunnel ridge's top: the Pi and PCA's shelf
LID_Z = 56.5                                # the lid's underside: over the Pi stack (55.3)
FRICTION = 0.5                              # PLA on PLA and plastic*
TRIALS, SPIN = 40, 6.0                      # drops a variant and height; spin up to rad/s
POCKET_MM = 0.3                             # a friction-fit pocket's clearance round the board, each side*
FRAMES = dict(pack_L=23.0, pack_R=23.0, esc_L=17.0, esc_R=17.0, pi_stack=15.0, pca=8.0)   # mm: a frame's wall height, about half the part*
FRAME_FIT, FRAME_WALL = 0.25, 1.2           # mm*
ESC_SHORT = 12.0                            # mm*: frame v2's walls
TPU_REF = 'solref="0.012 1" solimp="0.6 0.95 0.004"'   # the TPU pads: softer than a printed wall*
HEIGHTS = (0.3, 1.0)                        # m: the drop, from the box's lowest point


def parts():
    import trainer_tub as TT
    return {k: (x0, x1, y0, y1, z0 - Z0, z1 - Z0) for k, (x0, x1, y0, y1, z0, z1) in TT.parts().items()}


def box(name, x0, x1, y0, y1, z0, z1, **kw):
    a = ' '.join(f'{k}="{v}"' for k, v in kw.items())
    return (f'<geom name="{name}" type="box" pos="{(x0 + x1) / 2e3:.5f} {(y0 + y1) / 2e3:.5f} {(z0 + z1) / 2e3:.5f}" '
            f'size="{(x1 - x0) / 2e3:.5f} {(y1 - y0) / 2e3:.5f} {(z1 - z0) / 2e3:.5f}" {a}/>')


def xml(variant):
    P = parts(); g = []
    if variant in ('pibox', 'frames', 'frames_open', 'frames_short'):     # room for a wall between the PCA and the Pi, and
        x0, x1, y0, y1, z0, z1 = P['pca']; P['pca'] = (x0 - 2.6, x1 - 2.6, y0, y1, z0, z1)   # between the Pi and the right
        x0, x1, y0, y1, z0, z1 = P['pi_stack']; P['pi_stack'] = (x0, x1, y0 + 0.9, y1 + 0.9, z0, z1)   # pack (1.3 mm in print 1)
    g.append(box('floor', X0, X1, Y_R, Y_L, 0, FLOOR, mass=REST_G / 1e3))
    for nm, a in (('back', (X0, X0 + WALL, Y_R, Y_L)), ('front', (X1 - WALL, X1, Y_R, Y_L)),
                  ('right', (X0, X1, Y_R, Y_R + WALL)), ('left', (X0, X1, Y_L - WALL, Y_L))):
        g.append(box(nm, *a, 0, TOP, mass=0.001))
    held = variant in ('held', 'fitted', 'pibox')
    framed = variant in ('frames', 'frames_open', 'frames_short')
    wall_h = dict(FRAMES, esc_L=ESC_SHORT, esc_R=ESC_SHORT) if variant == 'frames_short' else FRAMES
    if variant in ('fitted', 'pibox'):                                   # the ESC bay narrowed to his 24 mm ESC, 0.5 mm
        for k, s in (('esc_L', 1), ('esc_R', -1)):
            x0, x1, y0, y1, z0, z1 = P[k]; yi = y0 - 0.5 if s > 0 else y1 + 0.5
            g.append(box('escwall_' + k, -88.5, -42.5, *((yi - 2.0, yi) if s > 0 else (yi, yi + 2.0)), FLOOR, LID_Z, mass=0.001))
    div_top = LID_Z if held else RIDGE                                    # print 1: the ridge walls the bays' bottom only
    g.append(box('ridge', X0 + WALL, 100.0, DIV_R, DIV_L, FLOOR, RIDGE, mass=0.001))
    if held:                                                              # the bays walled to the lid, 2 mm walls
        g.append(box('div_L', -90.0, X1 - WALL, DIV_L - 2.0, DIV_L, RIDGE, div_top, mass=0.001))
        yR = (-32.6, -31.0) if variant == 'pibox' else (DIV_R, DIV_R + 2.0)   # pibox: a 1.6 mm wall, the Pi's pocket side too
        g.append(box('div_R', -90.0, X1 - WALL, *yR, RIDGE, div_top, mass=0.001))
    for s, y0, y1 in (('L', Y_L - WALL - 2.0, Y_L - WALL), ('R', Y_R + WALL, Y_R + WALL + 2.0)):   # print 1's stops, 20 tall
        for x in (-42.5, -89.5):
            if not framed:
                g.append(box(f'stop{s}{x:.0f}', x, x + 1.5, y0, y1, FLOOR, FLOOR + 20.0, mass=0.001))
    if framed:                                                            # a low wall round each part, standing where the part stands
        c, t = FRAME_FIT, FRAME_WALL
        for k, wh in wall_h.items():
            x0, x1, y0, y1, z0, z1 = P[k]; zb, zt = z0 - 0.2, z0 + wh
            for nm, a in (('w0', (x0 - c - t, x0 - c, y0 - c - t, y1 + c + t)), ('w1', (x1 + c, x1 + c + t, y0 - c - t, y1 + c + t)),
                          ('w2', (x0 - c, x1 + c, y0 - c - t, y0 - c)), ('w3', (x0 - c, x1 + c, y1 + c, y1 + c + t))):
                g.append(box(f'frame_{k}_{nm}', *a, zb, zt, mass=0.001))
    if held:                                                              # the ESC's aft stop wall, the pack's front: 0.5 mm
        for s, (y0, y1) in (('L', (DIV_L, Y_L - WALL)), ('R', (Y_R + WALL, DIV_R))):
            g.append(box(f'escback{s}', -90.5, -88.5, y0, y1, FLOOR, 40.0, mass=0.001))
    if variant in ('lid', 'held'):
        g.append(box('lid', X0, X1, Y_R, Y_L, LID_Z, LID_Z + 2.4, mass=0.06))
    pads = ''
    if variant in ('frames', 'frames_short'):                             # TPU pads from the lid down onto every part
        for k in FRAMES:
            x0, x1, y0, y1, z0, z1 = P[k]; ins = 10 if k.startswith('pack') else 3 if k.startswith('esc') else 6
            pads += box('pad_' + k, x0 + ins, x1 - ins, y0 + 3, y1 - 3, z1, LID_Z, mass=0.001, solref='0.012 1', solimp='0.6 0.95 0.004')
            if k in ('pi_stack', 'pca') and z0 - RIDGE > 0.2:
                pads += box('under_' + k, x0 + 4, x1 - 4, y0 + 4, y1 - 4, RIDGE, z0, mass=0.001, solref='0.012 1', solimp='0.6 0.95 0.004')
    if held:                                                              # TPU pads from the lid down onto the packs and ESCs
        for k in ('pack_L', 'pack_R', 'esc_L', 'esc_R'):
            x0, x1, y0, y1, z0, z1 = P[k]
            pads += box('pad_' + k, x0 + 10, x1 - 10, y0 + 3, y1 - 3, z1, LID_Z, mass=0.001, solref='0.012 1', solimp='0.6 0.95 0.004')
    if variant == 'pibox':                                                # pockets, TPU pads under and over the boards
        c = POCKET_MM
        for k in ('pi_stack', 'pca'):
            x0, x1, y0, y1, z0, z1 = P[k]; zt = min(z1, z0 + 15.0)
            for nm, a in (('w0', (x0 - c - 2.0, x0 - c, y0 - c - 2.0, y1 + c + 2.0)), ('w1', (x1 + c, x1 + c + 2.0, y0 - c - 2.0, y1 + c + 2.0)),
                          ('w2', (x0 - c, x1 + c, y0 - c - 2.0, y0 - c)), ('w3', (x0 - c, x1 + c, y1 + c, y1 + c + 2.0))):
                if not (k == 'pca' and nm == 'w1') and not (k == 'pi_stack' and nm == 'w2'):   # shared: the Pi's wall, div_R
                    g.append(box(f'pocket_{k}_{nm}', *a, RIDGE, zt, mass=0.001))
            if z0 - RIDGE > 0.2:
                pads += box('under_' + k, x0 + 4, x1 - 4, y0 + 4, y1 - 4, RIDGE, z0, mass=0.001, solref='0.012 1', solimp='0.6 0.95 0.004')
            pads += box('pad_' + k, x0 + 6, x1 - 6, y0 + 6, y1 - 6, z1, LID_Z, mass=0.001, solref='0.012 1', solimp='0.6 0.95 0.004')
    loose = [k for k in P if not (held and variant != 'pibox' and k in ('pi_stack', 'pca'))]
    fixed = ''.join(box('fix_' + k, *P[k], mass=MASS[k] / 1e3, contype=0, conaffinity=0) for k in P if k not in loose)
    bodies = ''
    for k in loose:
        x0, x1, y0, y1, z0, z1 = P[k]; c = np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]) / 1e3
        h = np.array([x1 - x0, y1 - y0, z1 - z0]) / 2e3 - 0.0001          # 0.1 mm under size: no start in contact
        bodies += (f'<body name="{k}" pos="{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}"><freejoint/>'
                   f'<geom type="box" size="{h[0]:.5f} {h[1]:.5f} {h[2]:.5f}" mass="{MASS[k] / 1e3:.4f}"/></body>')
    return f'''<mujoco><option timestep="0.0002" gravity="0 0 -9.81"/>
<default><geom friction="{FRICTION} 0.005 0.0001" solref="0.004 1" condim="3"/></default>
<worldbody><geom name="ground" type="plane" size="5 5 0.1" friction="1 0.005 0.0001"/>
<body name="box" pos="0 0 0"><freejoint/>{''.join(g)}{pads}{fixed}</body>{bodies}</worldbody></mujoco>'''


def _rot(q):
    R = np.zeros(9); mj.mju_quat2Mat(R, q); return R.reshape(3, 3)


def _quat(rng):
    q = rng.normal(size=4); return q / np.linalg.norm(q)


def trial(m, d, loose, h, rng, T=1.2):
    """one drop: the box at a random orientation, its lowest point h above the ground, a random spin; each loose part's
    largest and final move in the box's frame (mm), the most it turned (deg), and the peak force on the lid and pads (N)"""
    mj.mj_resetData(m, d); q = _quat(rng); R = _rot(q)
    bid = {k: mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, k) for k in loose}; b0 = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, 'box')
    corners = []                                                          # the box's own geoms, turned: its lowest point
    for i in range(m.ngeom):
        if m.geom_bodyid[i] == b0:
            s = m.geom_size[i]; c = m.geom_pos[i]
            corners += [R @ (c + np.array([a, b, e]) * s) for a in (-1, 1) for b in (-1, 1) for e in (-1, 1)]
    pb = np.array([0.0, 0.0, h - min(p[2] for p in corners)])
    w = rng.uniform(-SPIN, SPIN, 3); wl = R.T @ w                          # a free joint's spin is in its body's frame
    d.qpos[0:3] = pb; d.qpos[3:7] = q; d.qvel[3:6] = wl
    for k, i in bid.items():                                              # each part where it sits in the box, moving with it
        j = m.jnt_qposadr[m.body_jntadr[i]]; v = m.jnt_dofadr[m.body_jntadr[i]]; c = m.qpos0[j:j + 3]
        d.qpos[j:j + 3] = pb + R @ c; d.qpos[j + 3:j + 7] = q
        d.qvel[v:v + 3] = np.cross(w, R @ c); d.qvel[v + 3:v + 6] = wl
    mj.mj_forward(m, d)
    rel0 = {}
    R0 = d.xmat[b0].reshape(3, 3)
    for k, i in bid.items():
        rel0[k] = (R0.T @ (d.xpos[i] - d.xpos[b0]), R0.T @ d.xmat[i].reshape(3, 3))
    mx = {k: 0.0 for k in loose}; rot = {k: 0.0 for k in loose}; peak = 0.0
    lidg = {mj.mj_name2id(m, mj.mjtObj.mjOBJ_GEOM, n) for n in ('lid', 'pad_pack_L', 'pad_pack_R', 'pad_esc_L', 'pad_esc_R')} - {-1}
    f6 = np.zeros(6)
    groups = {}                                                           # the frame variants: the peak on each part's frame and pad
    for i in range(m.ngeom):
        n = m.geom(i).name
        if n.startswith('frame_'):
            groups[i] = ('frame', n.split('_w')[0][6:])
        elif n.startswith('pad_'):
            groups[i] = ('pad', n[4:])
    pk = {}
    for step in range(int(T / m.opt.timestep)):
        mj.mj_step(m, d)
        if step % 10:
            continue
        R = d.xmat[b0].reshape(3, 3)
        for k, i in bid.items():
            p = R.T @ (d.xpos[i] - d.xpos[b0]); mx[k] = max(mx[k], 1e3 * np.linalg.norm(p - rel0[k][0]))
            Rr = R.T @ d.xmat[i].reshape(3, 3) @ rel0[k][1].T
            rot[k] = max(rot[k], np.degrees(np.arccos(np.clip((np.trace(Rr) - 1) / 2, -1, 1))))
        if lidg:
            tot = 0.0
            for j in range(d.ncon):
                c = d.contact[j]
                if c.geom1 in lidg or c.geom2 in lidg:
                    mj.mj_contactForce(m, d, j, f6); tot += abs(f6[0])
            peak = max(peak, tot)
        if groups:
            now = {}
            for j in range(d.ncon):
                c = d.contact[j]
                g_ = groups.get(c.geom1) or groups.get(c.geom2)
                if g_:
                    mj.mj_contactForce(m, d, j, f6); now[g_] = now.get(g_, 0.0) + abs(f6[0])
            for a, v in now.items():
                pk[a] = max(pk.get(a, 0.0), v)
    R = d.xmat[b0].reshape(3, 3)
    fin = {k: 1e3 * float(np.linalg.norm(R.T @ (d.xpos[i] - d.xpos[b0]) - rel0[k][0])) for k, i in bid.items()}
    return dict(max=mx, final=fin, rot=rot, lid_peak=peak, pk=pk)


def run(variant):
    m = mj.MjModel.from_xml_string(xml(variant)); d = mj.MjData(m)
    loose = [m.body(i).name for i in range(m.nbody) if m.body(i).name not in ('world', 'box', '')]
    out = {}
    for h in HEIGHTS:
        rng = np.random.default_rng([11, int(h * 100)]); T = [trial(m, d, loose, h, rng) for _ in range(TRIALS)]
        out[str(h)] = dict(
            out_of_place={k: sum(t['final'][k] > OUT_MM for t in T) for k in loose},
            final_p90={k: float(np.percentile([t['final'][k] for t in T], 90)) for k in loose},
            max_p90={k: float(np.percentile([t['max'][k] for t in T], 90)) for k in loose},
            rot_p90={k: float(np.percentile([t['rot'][k] for t in T], 90)) for k in loose},
            lid_peak_p90=float(np.percentile([t['lid_peak'] for t in T], 90)), trials=TRIALS)
        keys = {a for t in T for a in t['pk']}
        if keys:
            out[str(h)]['peak_p90'] = {'%s %s' % a: float(np.percentile([t['pk'].get(a, 0.0) for t in T], 90)) for a in sorted(keys)}
    return variant, out


if __name__ == '__main__':
    from multiprocessing import Pool
    V = sys.argv[1:] or ['print1', 'lid', 'held', 'fitted']
    with Pool(len(V)) as p:
        R = dict(p.map(run, V))
    os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, 'retention.json')
    json.dump({**(json.load(open(path)) if os.path.exists(path) else {}), **R}, open(path, 'w'), indent=1)   # keep the other variants' runs
    for v, r in R.items():
        for h, s in r.items():
            print(f"{v:6s} {h} m: out of place (of {s['trials']}) " + ', '.join(f"{k} {n}" for k, n in s['out_of_place'].items())
                  + f" | moved, 90th pct: " + ', '.join(f"{k} {x:.1f}" for k, x in s['final_p90'].items())
                  + (f" | lid peak {s['lid_peak_p90']:.0f} N" if s['lid_peak_p90'] else '')
                  + (' | peak, 90th pct: ' + ', '.join(f"{k} {x:.0f} N" for k, x in s['peak_p90'].items()) if s.get('peak_p90') else ''))
