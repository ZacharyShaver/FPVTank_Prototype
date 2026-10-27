"""Film a design on the gauges: falls that land off its wheels and the tail righting it, and a step climb. The physics
is the gauges' exactly (gauges.Sim, falls, right, climb_try's push); only colours, a floor texture and lights are added.

    python gauges/film.py [T5] [--step 100]   -> gauges/out/film/<name>_falls.mp4/.gif, <name>_climb.mp4/.gif

The design comes from the current search's finals (tools/config.py GAUGES_CURRENT; T12 was the tail search's).
"""
import os, sys, math, pickle, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
sys.path.insert(0, config.TUMBLE)
import gauges as G, robots as RB

OUT = os.path.join(config.GAUGES_OUT, 'film')
PW, PH, FPS = 400, 300, 30


def visual_xml(sp, mu, step=None):
    """robots.xml with colours, a floor texture, a sky and lights; nothing that touches the physics"""
    x = RB.xml(sp, mu, step)
    x = x.replace('<mujoco>', f'<mujoco><visual><global offwidth="{3 * PW}" offheight="{2 * PH}"/><quality shadowsize="2048"/></visual>', 1)
    x = x.replace('<asset>', '<asset><texture name="chk" type="2d" builtin="checker" rgb1=".78 .79 .76" rgb2=".72 .73 .70" width="256" height="256"/>'
                  '<material name="floor" texture="chk" texrepeat="16 16" reflectance=".05"/>'
                  '<texture name="sky" type="skybox" builtin="gradient" rgb1=".96 .96 .94" rgb2=".82 .83 .80" width="64" height="64"/>', 1)
    x = x.replace('<worldbody>', '<worldbody><light pos=".5 -.8 2" dir="-.2 .4 -1" diffuse=".85 .85 .8" castshadow="true"/>'
                  '<light pos="-1 .6 1.5" dir=".5 -.3 -1" diffuse=".35 .35 .35" castshadow="false"/>', 1)
    x = x.replace('<geom type="plane"', '<geom type="plane" material="floor"', 1)
    x = x.replace('<geom type="box"', '<geom type="box" rgba=".55 .6 .7 1"').replace('<geom type="capsule" fromto="0.0', '<geom type="capsule" rgba=".55 .6 .7 1" fromto="0.0')
    x = x.replace('<geom type="mesh"', '<geom type="mesh" rgba=".83 .55 .2 .95"' if any(n.startswith('skin') for n in sp['notes']) else '<geom type="mesh" rgba=".62 .66 .7 1"')
    x = x.replace('<geom type="cylinder"', '<geom type="cylinder" rgba=".13 .13 .14 1"')
    x = x.replace('contype="2" conaffinity="0"', 'contype="2" conaffinity="0" rgba=".07 .55 .43 1"')
    return x


class Rec(G.Sim):
    """gauges.Sim on the visual model, keeping the pose at every tick"""
    def __init__(self, sp, mu=1.0, step=None):
        super().__init__(sp, mu, step)
        import mujoco
        self.m = mujoco.MjModel.from_xml_string(visual_xml(sp, mu, step)); self.d = mujoco.MjData(self.m)
        self.jw = np.array([self.m.joint(f'j{i}').dofadr[0] for i in range(len(sp['wheels']))]); self.rid = self.m.body('robot').id
        if self.limb:
            self.lq = [self.m.joint(n).qposadr[0] for n in ('ly', 'lp')]
        self.log = []

    def drive(self, uL, uR):
        super().drive(uL, uR); self.log.append((self.d.time, self.d.qpos.copy()))


def fall(sim, rng):
    """gauges.falls' one fall, ticked at 5 ms so it can be filmed, then the tail's righting: the passive rest and the end"""
    d = sim.d; q = rng.normal(size=4); q /= np.linalg.norm(q)
    sim.place(q, G.DROP_MM * 1e-3); d.qvel[3:6] = rng.uniform(-1, 1, 3) * G.SPIN; sim.log = [(d.time, d.qpos.copy())]
    still = 0
    for k in range(int(8000 / G.TICK)):
        sim.drive(None, None)
        if k % 10 == 9:
            still = still + 1 if np.abs(d.qvel[:6]).max() < 0.02 else 0
            if still >= 6: break
    rest = G.classify(sim.rot()); t_rest = d.time
    if sim.limb and rest != 'upright':
        G.right(sim)
    return rest, G.classify(sim.rot()), t_rest, d.time


def frames(sim, log, cams, label, t_end):
    """the logged poses at FPS, each rendered from a camera following the robot"""
    import mujoco
    r = mujoco.Renderer(sim.m, PH, PW); out = []; ts = np.array([t for t, _ in log]); t0 = ts[0]
    for t in np.arange(t0, t_end + 1e-9, 1.0 / FPS):
        i = min(int(np.searchsorted(ts, t)), len(log) - 1); sim.d.qpos[:] = log[i][1]; mujoco.mj_forward(sim.m, sim.d)
        cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        p = sim.d.xpos[sim.rid]; cam.lookat[:] = (p[0] + cams.get('dx', 0.0), p[1], max(0.08, p[2] * 0.6)); cam.distance = cams['dist']
        cam.azimuth, cam.elevation = cams['az'], cams['el']
        r.update_scene(sim.d, cam); out.append((r.render().copy(), label(t - t0)))
    r.close()
    return out


def stamp(img, lines):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(img); dr = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype('segoeui.ttf', 15)
    except OSError:
        f = ImageFont.load_default()
    y = 6
    for s in lines:
        dr.text((9, y + 1), s, fill=(255, 255, 255), font=f); dr.text((8, y), s, fill=(25, 28, 32), font=f); y += 19
    return np.asarray(im)


def write(path, panels, cols):
    """panels: lists of (image, text lines), tiled cols wide; shorter ones hold their last frame; mp4 and a gif"""
    n = max(len(p) for p in panels); rows = math.ceil(len(panels) / cols); W, H = cols * PW, rows * PH
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-an', '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', path + '.mp4'], stdin=subprocess.PIPE)
    for k in range(n + FPS):                                              # a second of the end held
        canvas = np.full((H, W, 3), 245, np.uint8)
        for j, p in enumerate(panels):
            img, txt = p[min(k, len(p) - 1)]; r_, c_ = divmod(j, cols)
            canvas[r_ * PH:(r_ + 1) * PH, c_ * PW:(c_ + 1) * PW] = stamp(img, txt)
        ff.stdin.write(canvas.tobytes())
    ff.stdin.close(); ff.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path + '.mp4', '-vf', f'fps=12,scale={min(W, 900)}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse',
                    path + '.gif'], check=True)
    return path + '.mp4', path + '.gif'


def main():
    name = next((a for a in sys.argv[1:] if not a.startswith('--') and not a.isdigit()), 'T12')
    step = int(sys.argv[sys.argv.index('--step') + 1]) if '--step' in sys.argv else None
    src = config.GAUGES_CURRENT                                            # the current search's finalists (tools/config.py)
    specs = {sp['name']: sp for sp in pickle.load(open(os.path.join(src, 'finals_specs.pkl'), 'rb'))}
    sp = specs[name]; os.makedirs(OUT, exist_ok=True); fn = name.replace(', ', '_').replace(' ', '_')
    # falls: the gauge's own random starts at x1, keeping the first six that land off the wheels
    sim = Rec(sp, 1.0); rng = np.random.default_rng(31); panels, tried, kept = [], 0, 0
    while kept < 6 and tried < 80:
        tried += 1; rest, end, t_rest, t_end = fall(sim, rng)
        if rest == 'upright':
            continue
        kept += 1; log = list(sim.log)
        lab = (lambda r, e, tr, te, k_: (lambda t: [f'fall {k_}: landed {r}' if t >= tr - log[0][0] else f'fall {k_}',
               ('tail righting...' if t < te - log[0][0] else (f'on its wheels at {te - log[0][0]:.1f} s' if e == 'upright' else f'still {e} after 10 s')) if t >= tr - log[0][0] else '']))(rest, end, t_rest, t_end, kept)
        panels.append(frames(sim, log, dict(dist=1.5, az=135.0, el=-22.0), lab, t_end))
        print(f'fall {kept} (try {tried}): landed {rest}, ended {end}, righting {t_end - t_rest:.1f} s', flush=True)
    print(write(os.path.join(OUT, f'{fn}_falls'), panels, 3))
    # the climb: the best height its finals passed, at x1, forwards, the push as climb_try does it
    import json
    fin = {f['name']: f for f in json.load(open(os.path.join(src, 'finals.json')))['finals']}
    h = step or fin[name]['worst']['climb']
    sim = Rec(sp, 1.0, step=h); ok = G.climb_try(sim, h, False, np.random.default_rng(5)); log = list(sim.log)
    print(f'climb {h} mm: {"on top" if ok else "failed"} in {log[-1][0]:.2f} s')
    t_end = log[-1][0] + 0.8
    for _ in range(int(0.8 * 1000 / G.TICK)):                             # let it roll on a moment after the gauge's success line
        sim.drive(0.5 / (sim.w0 * sp['R'] * 1e-3), 0.5 / (sim.w0 * sp['R'] * 1e-3)); log.append((sim.d.time, sim.d.qpos.copy()))
    lab = lambda t: [f'{name}: a {h} mm step', 'on top' if (ok and t > log[-1][0] - 0.8 - log[0][0]) else ('climbing...' if ok else 'failed')]
    side = frames(sim, log, dict(dist=1.4, az=90.0, el=-8.0, dx=0.0), lab, t_end)
    three = frames(sim, log, dict(dist=1.6, az=135.0, el=-20.0), lambda t: [], t_end)
    print(write(os.path.join(OUT, f'{fn}_climb'), [side, three], 2))


if __name__ == '__main__':
    main()
