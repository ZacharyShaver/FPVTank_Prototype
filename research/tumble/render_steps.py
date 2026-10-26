"""EXPLORATORY (2026-10-25): the Trainer and the step layout driving down the same step in MuJoCo, side by side, with the
step-down test's success rates in the frame (the test is built3.py; the rates are its built.json).

    python research/tumble/render_steps.py    -> research/figures/step_down.mp4, research/figures/step_down.png (poster frame)

The physics is built3's exactly: the two built designs from their own meshes (B3.design of chassis-v2's pickles), chassis3's
step and hard floor (C3.xml, C3.CONTACT), the drive law and the success test ('upright' after the run, C3.Sim.drive). This
script re-runs that law (drive_rec) only to record every step for the camera, and checks each run lands on C3.Sim.drive's own
outcome and final pose. Three things only change the picture: colours and a floor texture, a stripe on each tyre so the
spin shows, and the step drawn narrower than it collides (the 4 m wide collision slab is hidden, so the camera sits
outside it). It also re-runs built3's own seeds for the chosen cell and checks they give built.json's counts.

The run is picked from built.json: the step height where the two designs' success rates differ most, and at that height
the cell (speed, forwards or reverse) where they differ most. Both designs start from the same seed: same yaw, same speed,
same distance of the leading end short of the edge, as built3's job draws them (one run per seed here). Seed 0 first; if it
doesn't show the step layout down and the Trainer not, the first seed that does. Shown in slow motion (the factor is on the strip), the camera fixed
and the same for both. A run that drives on past the frame (the step layout does, upright) is drawn until its origin passes
X_STOP; the outcome on its badge is still built3's test at the run's end. The poster is the last frame.
"""
import os, sys, json, pickle, subprocess, time
sys.dont_write_bytecode = True
import numpy as np
import mujoco
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import built3 as B3, chassis3 as C3
from PIL import Image, ImageDraw, ImageFont

TRAINER, STEPS = 'Trainer (built)', 'Step layout (built)'
BUILT_JSON = os.path.join(ROOT, 'results', 'chassis3', 'built.json')
OUT_MP4 = os.path.join(ROOT, 'figures', 'step_down.mp4'); OUT_PNG = os.path.join(ROOT, 'figures', 'step_down.png')
PW, PH, FPS = 720, 420, 30                      # one panel (wide: the drop and the landing are 1.9 m of floor, 0.7 m tall), the video's frame rate
TOP, BOT = 40, 92                               # the label strip above the panels, the footer strip below
LEAD_IN, HOLD = 0.5, 1.4                        # s the first frame and the last frame stay up
MIN_S, MAX_S = 4.5, 8.0                         # the video's length, s: the slow-motion factor is the smallest whole number that reaches MIN_S
X_STOP = 0.9                                    # m: a run that drives on is frozen where it reaches the frame's edge (its origin passes this X)
SEED_MAX = 300
STEP_HALF_Y = 0.25                              # m: the drawn step's half width (the collision slab is 4 m wide)
CAM_D, CAM_EL, VIEW_H, LOOK = 5.0, -7.0, 1.15, (0.35, 0.0, 0.35)   # a telephoto camera outside the (narrowed) step, the same for both
FOVY = float(np.degrees(2 * np.arctan(VIEW_H / 2 / CAM_D)))        # so 1.15 m of height, 2 m of width, at the lookat plane


# ---- the numbers on the frame: built.json --------------------------------------------------------------------------------
def tally(cells, keep=lambda h, v, b: True):
    """(upright, runs) over the cells passing `keep`; cell keys are 'h|v|reverse'"""
    up = n = 0
    for k, c in cells.items():
        h, v, b = k.split('|')
        if keep(int(h), float(v), int(b)):
            up += c.get('upright', 0); n += sum(c.values())
    return up, n


def pick_cell(res):
    """the step height where the two designs' success rates differ most, then the (speed, reverse) cell there where the
    counts differ most (forwards on a tie)"""
    cT, cS = res[TRAINER]['cells'], res[STEPS]['cells']
    heights = sorted({int(k.split('|')[0]) for k in cT})
    gap = {h: abs(tally(cS, lambda a, v, b: a == h)[0] / tally(cS, lambda a, v, b: a == h)[1]
                  - tally(cT, lambda a, v, b: a == h)[0] / tally(cT, lambda a, v, b: a == h)[1]) for h in heights}
    h = max(heights, key=lambda h: gap[h])
    cells = [(h, float(k.split('|')[1]), int(k.split('|')[2])) for k in cT if int(k.split('|')[0]) == h]
    key = lambda c: f'{c[0]}|{c[1]}|{c[2]}'
    best = max(cells, key=lambda c: (abs(cS[key(c)].get('upright', 0) - cT[key(c)].get('upright', 0)), -c[2]))
    return h, (best[0], best[1], bool(best[2])), gap


# ---- the designs and runs -------------------------------------------------------------------------------------------------
def designs(res):
    """built3's designs from chassis-v2's pickles; if a design's mass differs from built.json's, rebuild the pickle from the
    current chassis-v2 once (B3.cache), and say so"""
    out = {}
    for name, w in B3.VARIANTS.items():
        path = os.path.join(B3.CHASSIS, 'out', f'_built_{w}.pkl')
        D = B3.design(pickle.load(open(path, 'rb'))) if os.path.exists(path) else None
        if D is None or abs(D['mass'] - res[name]['mass']) > 0.01:
            print(f'{name}: pickle missing or its mass differs from built.json; rebuilding with built3.cache')
            D = B3.design(B3.cache(w))
        assert abs(D['mass'] - res[name]['mass']) < 0.01 and abs(D['length'] - res[name]['length']) < 0.01, f'{name} is not the design in built.json'
        out[name] = D
    return out


def start(D, cell, seed):
    """built3.job's start for one run: yaw, the leading end short of the edge, speed (same draws, same order, so the
    same yaw, offset and speed factor for both designs)"""
    h, v, back = cell; rng = np.random.default_rng(seed)
    yaw = np.radians(rng.uniform(-15, 15)) + (np.pi if back else 0.0)
    x0 = -C3.lead(D, back) * 1e-3 - rng.uniform(0.05, 0.15)
    return dict(x0=x0, z0=h * 1e-3 + 0.0005, yaw=yaw, v=v * rng.uniform(0.9, 1.1), back=back, fall=0.4 * h * 1e-3)


def drive_rec(sim, s, record=True, t_max=5.0, hold=1.0):
    """C3.Sim.drive's loop, line for line, keeping the pose after every physics step. Returns outcome, poses, the step
    index of the landing (None if it never lands)"""
    mj, m, d = sim.mj, sim.m, sim.d; R = sim.D['R'] * 1e-3; back = s['back']
    mj.mj_resetData(m, d); q = np.array([np.cos(s['yaw'] / 2), 0, 0, np.sin(s['yaw'] / 2)])
    d.qpos[:3] = (s['x0'], 0, s['z0']); d.qpos[3:7] = q; d.qvel[0] = s['v']
    sgn = -1.0 if back else 1.0; d.qvel[sim.jw] = sgn * s['v'] / R; mj.mj_forward(m, d)
    u0 = sgn * min(s['v'] / (sim.w0 * R), 1.0); zc0 = d.xipos[sim.rid][2]; landed = False; t_land = None; still = 0
    per = int(round(C3.TICK * 1e-3 / m.opt.timestep)); poses = [d.qpos.copy()]; n_land = None
    for k in range(int(t_max * 1000 / C3.TICK)):
        t = k * C3.TICK / 1000
        if landed and t - t_land > hold:
            u = None
        else:
            u = u0 + C3.W3.KV * (u0 * sim.w0 - d.qvel[sim.jw].mean()) / sim.w0
        d.qfrc_applied[:] = 0.0
        if u is not None:
            d.qfrc_applied[sim.jw] = sim.stall * (np.clip(u, -1, 1) - d.qvel[sim.jw] / sim.w0)
        for _ in range(per):
            mj.mj_step(m, d)
            if record: poses.append(d.qpos.copy())
        zc = d.xipos[sim.rid][2]
        if not landed and zc0 - zc > s['fall'] and d.ncon > 0:
            landed, t_land = True, t; n_land = (k + 1) * per
        if landed and k % 4 == 0:
            if np.abs(d.qvel[:6]).max() < 0.02:
                still += 1
                if still >= 6: break
            else:
                still = 0
    outcome = C3.T.classify(d.xmat[sim.rid].reshape(3, 3)) if landed else 'stuck'
    return outcome, poses, n_land


def outcome_plain(D, h, s):
    """built3's own test (C3.Sim.drive) on the plain model: the outcome, and the final pose"""
    sim = C3.Sim(D, step=h); r = sim.drive(s['x0'], s['z0'], s['yaw'], s['v'], s['back'], fall=s['fall'])
    return r, sim.d.qpos.copy()


# ---- the picture ------------------------------------------------------------------------------------------------------------
def visual_xml(D, h_mm):
    """C3.xml's model with a picture added (colours, textures, lights, a stripe on each tyre, the step drawn narrower than
    it collides). Nothing added collides or weighs anything."""
    import re
    x = C3.xml(D, h_mm); h = h_mm * 1e-3; R = D['R'] * 1e-3; tw = C3.TW * 1e-3
    x = x.replace('<mujoco>', f'<mujoco><visual><global offwidth="{PW}" offheight="{PH}" fovy="{FOVY}"/><quality shadowsize="4096"/>'
                  '<headlight ambient=".42 .42 .42" diffuse=".35 .35 .35" specular="0 0 0"/><map znear="0.05" zfar="30"/></visual>', 1)
    x = x.replace('<asset>', '<asset><texture name="sky" type="skybox" builtin="gradient" rgb1=".93 .95 .98" rgb2=".72 .78 .86" width="64" height="64"/>'
                  '<texture name="tile" type="2d" builtin="checker" rgb1=".80 .78 .74" rgb2=".70 .68 .64" width="512" height="512"/>'
                  '<material name="floor" texture="tile" texuniform="true" texrepeat="5 5" reflectance="0"/>', 1)      # 5 5 gives 200 mm squares (measured top-down)
    x = x.replace('<geom type="plane" size="6 6 0.1"', '<geom type="plane" material="floor" size="6 6 0.1"', 1)
    x = re.sub(r'<geom type="box" size="2 2 [\d.]+"', lambda m: m.group(0).replace('<geom ', '<geom group="4" '), x, count=1)       # the collision slab, not drawn
    marks = ''.join(f'<geom type="box" size="1.6 0.0012 0.0016" pos="-1.6 -{STEP_HALF_Y:.3f} {z * 1e-3:.4f}" rgba=".9 .9 .88 1" contype="0" conaffinity="0" mass="0"/>'
                    for z in range(100, h_mm, 100))                                                                  # a mark on the step's face every 100 mm
    x = x.replace('<worldbody>', '<worldbody><light directional="true" pos="-0.4 -3 3" dir="0.25 0.5 -1" diffuse=".72 .72 .7" castshadow="true"/>'
                  f'<geom type="box" size="1.6 {STEP_HALF_Y} {h / 2:.4f}" pos="-1.6 0 {h / 2:.4f}" rgba=".47 .49 .54 1" contype="0" conaffinity="0" mass="0"/>' + marks, 1)
    x = x.replace('<geom type="mesh" mesh="body"', '<geom type="mesh" mesh="body" rgba=".32 .52 .80 1"', 1)
    x = re.sub(r'<geom type="mesh" mesh="x(\d+)"', r'<geom type="mesh" mesh="x\1" rgba=".93 .55 .16 1"', x)
    stripe = f'<geom type="box" size="{0.8 * R:.4f} {tw / 2 + 0.0008:.4f} {0.09 * R:.4f}" rgba="1 .86 .2 1" contype="0" conaffinity="0" mass="0"/>'
    x = re.sub(r'(<geom type="cylinder" size="[\d. ]+" euler="90 0 0" friction="[\d. ]+")/>', r'\1 rgba=".13 .13 .14 1"/>' + stripe, x)
    return x


def font(size, bold=False):
    for f in (('arialbd.ttf' if bold else 'arial.ttf'), ('calibrib.ttf' if bold else 'calibri.ttf')):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', f), size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def say(r):
    return {'upright': 'down, on its wheels', 'inverted': 'down, upside down', 'stuck': 'never got down'}.get(r, 'down, ended ' + r)


def main():
    t0 = time.time()
    J = json.load(open(BUILT_JSON)); res = J['results']
    # the rates on the frame
    rate = {n: tally(res[n]['cells']) for n in (TRAINER, STEPS)}
    pct = {n: rate[n][0] / rate[n][1] for n in rate}
    for n in rate:
        assert abs(pct[n] - res[n]['down']) < 1e-9, 'tally disagrees with built.json'
    h, cell, gap = pick_cell(res)
    rh = {n: tally(res[n]['cells'], lambda a, v, b: a == h) for n in rate}
    print('built.json overall: ' + ', '.join(f'{n} {pct[n]:.1%} ({rate[n][0]}/{rate[n][1]})' for n in rate))
    print('success-rate gap by step height (mm): ' + ', '.join(f'{k} {v:.3f}' for k, v in gap.items()) + f'  -> {h} mm')
    key = f'{cell[0]}|{cell[1]}|{int(cell[2])}'
    print(f'cell with the widest count gap at {h} mm: {cell[1]} m/s, {"reverse" if cell[2] else "forwards"}  '
          f'(Trainer {res[TRAINER]["cells"][key].get("upright", 0)}/20, step layout {res[STEPS]["cells"][key].get("upright", 0)}/20)')
    des = designs(res)

    # reproduce built.json's own runs for this cell (built3's seeds): the designs here are the ones the table measured
    ci = C3.CELLS.index(cell); B3._init(des)
    for n in (TRAINER, STEPS):
        _, got = B3.job((n, cell, 400 + ci))
        assert got == res[n]['cells'][key], f'{n}: built3.job gives {got}, built.json has {res[n]["cells"][key]}'
    print(f'built3.job reproduces built.json for this cell: Trainer {got_up(res[TRAINER], key)}/20, step layout {got_up(res[STEPS], key)}/20 upright: OK')

    # the seed: 0 first, else the first where the step layout gets down and the Trainer doesn't
    def trial(seed):
        return {n: outcome_plain(des[n], h, start(des[n], cell, seed)) for n in des}
    seed0 = trial(0); pick = 0; why = 'seed 0'
    print('seed 0: ' + ', '.join(f'{n} {seed0[n][0]}' for n in seed0))
    shows = lambda t: t[STEPS][0] == 'upright' and t[TRAINER][0] != 'upright'
    if not shows(seed0):
        for pick in range(1, SEED_MAX):
            if shows(trial(pick)): break
        else:
            raise SystemExit(f'BLOCKED: no seed up to {SEED_MAX} shows the step layout down and the Trainer not')
        why = f'seed {pick}: the first where the step layout lands on its wheels and the Trainer does not'
    print(f'seed {pick} chosen ({why})')

    # record both runs on the picture model, and check they are C3.Sim.drive's runs
    run = {}
    for n in (TRAINER, STEPS):
        D = des[n]; s = start(D, cell, pick); m = mujoco.MjModel.from_xml_string(visual_xml(D, h)); sim = C3.Sim(D, step=h)
        sim.m, sim.d = m, mujoco.MjData(m)
        r, poses, n_land = drive_rec(sim, s)
        r0, q0 = outcome_plain(D, h, s)
        assert r == r0, f'{n}: recorded run {r} differs from C3.Sim.drive {r0}'
        err = float(np.abs(poses[-1] - q0).max()); assert err < 1e-9, f'{n}: final pose differs from C3.Sim.drive by {err}'
        run[n] = dict(D=D, s=s, m=m, poses=np.array(poses), outcome=r, n_land=n_land, dt=m.opt.timestep)
        print(f'{n}: {r} ({len(poses) * m.opt.timestep:.2f} s simulated, landed at {n_land * m.opt.timestep:.2f} s, start x {s["x0"]:.3f} m, '
              f'speed {s["v"]:.3f} m/s, yaw {np.degrees(s["yaw"]):.1f} deg); same as C3.Sim.drive, final pose within {err:.1e}')
    render(run, h, cell, pick, seed0, rate, pct, rh, J['runs_per_cell'])
    print(f'{time.time() - t0:.0f} s')


def got_up(r, key):
    return r['cells'][key].get('upright', 0)


def fit(draw, text, size, bold, width):
    """a font of at most `size` px that fits `text` into `width` px"""
    while True:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= width or size <= 10:
            return f
        size -= 1


def render(run, h, cell, pick, seed0, rate, pct, rh, runs_per_cell):
    names = (TRAINER, STEPS)
    rend = {n: mujoco.Renderer(run[n]['m'], PH, PW) for n in names}; dat = {n: mujoco.MjData(run[n]['m']) for n in names}
    cam = mujoco.MjvCamera(); cam.azimuth = 90; cam.elevation = CAM_EL; cam.distance = CAM_D; cam.lookat[:] = LOOK
    for n in names:                                                       # where each run stops being drawn: its end, or the frame's edge
        r = run[n]; x = r['poses'][:, 0]; r['n_show'] = int(np.argmax(x >= X_STOP)) if (x >= X_STOP).any() else len(x) - 1
        r['n_show'] = min(r['n_show'], len(x) - 1); r['t_show'] = r['n_show'] * r['dt']
    t_show = max(run[n]['t_show'] for n in names)
    slow = next((k for k in range(1, 40) if t_show * k + LEAD_IN + HOLD >= MIN_S), 1)
    while slow > 1 and t_show * slow + LEAD_IN + HOLD > MAX_S:
        slow -= 1
    n_lead, n_run, n_hold = int(round(LEAD_IN * FPS)), int(round(t_show * slow * FPS)), int(round(HOLD * FPS))
    W, H = 2 * PW, TOP + PH + BOT
    spd = 'real time' if slow == 1 else f'1/{slow} speed'
    v0, back = run[TRAINER]['s']['v'], cell[2]
    won = lambda n: run[n]['outcome'] == 'upright'
    L1 = (f'Step-down test (MuJoCo, hard floor): Trainer {pct[TRAINER]:.0%} vs step layout {pct[STEPS]:.0%} of runs end upright after the drop, '
          f'over {rate[TRAINER][1]} runs each ({len(C3.CELLS)} cells x {runs_per_cell}).')
    L2 = (f'At {h} mm steps: Trainer {rh[TRAINER][0] / rh[TRAINER][1]:.0%} vs step layout {rh[STEPS][0] / rh[STEPS][1]:.0%} ({rh[TRAINER][1]} runs each).   '
          f'Floor squares are 200 mm, marks on the step 100 mm.   Shown at {spd}.')
    how = f'{h} mm step, {cell[1]} m/s cell ({v0:.2f} m/s here), {"in reverse" if back else "forwards"}'
    if pick == 0:
        L3 = f'This run: {how}, seed 0.'
    else:
        same = len({seed0[n][0] for n in names}) == 1
        s0 = f'seed 0: both ended {seed0[names[0]][0]}' if same else f'seed 0: Trainer {seed0[TRAINER][0]}, step layout {seed0[STEPS][0]}'
        L3 = f"This run: {how}, seed {pick}, the first seed where the step layout lands on its wheels and the Trainer doesn't ({s0})."
    probe = ImageDraw.Draw(Image.new('RGB', (4, 4)))
    f1, f2, f3 = (fit(probe, t, sz, b, W - 28) for t, sz, b in ((L1, 21, True), (L2, 19, False), (L3, 19, False)))
    fs = min(f.size for f in (f2, f3)); f2, f3 = font(fs), font(fs)
    ft, fb = font(23, True), font(22, True)

    def panel(n, i):
        r = run[n]; k = min(max(i, 0), r['n_show']); d = dat[n]; d.qpos[:] = r['poses'][k]
        mujoco.mj_forward(r['m'], d); rend[n].update_scene(d, cam); return rend[n].render().copy(), k * r['dt']

    def compose(j):
        i = int(round((j - n_lead) / FPS / slow / run[TRAINER]['dt'])) if j >= n_lead else 0
        end = j >= n_lead + n_run; i = min(i, max(run[n]['n_show'] for n in names)); tclock = min(i * run[TRAINER]['dt'], t_show)
        im = Image.new('RGB', (W, H), (243, 243, 240)); dr = ImageDraw.Draw(im)
        for c, n in enumerate(names):
            img, _ = panel(n, i)
            im.paste(Image.fromarray(img), (c * PW, TOP))
            x0 = c * PW
            tag = f"{n}, {run[n]['D']['mass']:.0f} g"
            dr.text((x0 + 12, 8), tag, font=ft, fill=(25, 25, 28))
            tt = f't = {tclock:.2f} s'; dr.text((x0 + PW - 12 - dr.textlength(tt, font=ft), 8), tt, font=ft, fill=(90, 90, 95))
            if end:
                ok = won(n); msg = say(run[n]['outcome']).capitalize()
                bw = dr.textlength(msg, font=fb) + 28; bx = x0 + (PW - bw) / 2
                dr.rounded_rectangle((bx, TOP + 12, bx + bw, TOP + 12 + 38), 9, fill=(30, 140, 70) if ok else (190, 50, 45))
                dr.text((bx + 14, TOP + 17), msg, font=fb, fill=(255, 255, 255))
        dr.line((PW, 0, PW, TOP + PH), fill=(243, 243, 240), width=3)
        dr.line((0, TOP + PH, W, TOP + PH), fill=(190, 190, 185), width=1)
        y = TOP + PH + 8
        for t, f, col in ((L1, f1, (25, 25, 28)), (L2, f2, (55, 55, 60)), (L3, f3, (55, 55, 60))):
            dr.text((14, y), t, font=f, fill=col); y += int(f.size * 1.32)
        return im

    total = n_lead + n_run + n_hold
    os.makedirs(os.path.dirname(OUT_MP4), exist_ok=True)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-an',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT_MP4], stdin=subprocess.PIPE)
    last = None
    for j in range(total):
        im = compose(j); ff.stdin.write(np.asarray(im).tobytes()); last = im
    ff.stdin.close(); ff.wait()
    for r in rend.values(): r.close()
    last.save(OUT_PNG)                                                   # the poster: the last frame, both outcomes up
    print(f't_show {t_show:.2f} s simulated at {spd}: {total} frames, {total / FPS:.1f} s, {W}x{H}')
    print('wrote', OUT_MP4, f'({os.path.getsize(OUT_MP4) / 1e6:.2f} MB)'); print('wrote', OUT_PNG)
    print('rates on the frame:'); [print('  ' + t) for t in (L1, L2, L3)]


if __name__ == '__main__':
    main()
