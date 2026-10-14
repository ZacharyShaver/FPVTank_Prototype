"""See the scale-model drops: render simulated drops to video, and write MuJoCo scenes to explore by hand.

    python research/tumble/render_drops.py            -> research/figures/sim_drops.mp4 (dead vs bounce, side by side)
    python -m mujoco.viewer --mjcf=research/tumble/viz/E3_tall_low_bounce.xml          (interactive: drag to throw it)

The physics is predict()'s exactly (scale_model.py: the hull, the mass layout, timestep, friction, contact), plus
things that only change the picture: a floor texture, lights, and a blue patch under the base like the tape over the
pocket (no collision, no mass). Each clip is one drop from the same start, run twice: MuJoCo's default dead contact
(left) and the bounce the 6 cm drops fitted (right, damping ratio 0.2). Shown at 1/4 speed.
"""
import os, sys, json, subprocess
import numpy as np
import mujoco
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import scale_model as S, predict_drops as PD, tumble as T

W, H = 480, 360


def scene(name, high, dampratio=None):
    """predict()'s model, with visuals added"""
    info = json.load(open(os.path.join(ROOT, 'models', name + '.json')))
    M, com, I, P = S.mass_layout(info, PD.GRAMS[name], high)
    s = 1e-3; Isi = I * 1e-9; k = info['pockets'][0]
    verts = ' '.join('%.5f' % v for v in (P * s).ravel())
    full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    sr = '' if dampratio is None else f' solref="0.02 {dampratio:.4f}"'
    return f"""<mujoco model="{name} mass {'high' if high else 'low'}">
  <option timestep="0.0005"/>
  <visual><global offwidth="{W}" offheight="{H}"/><quality shadowsize="2048"/></visual>
  <asset>
    <mesh name="h" vertex="{verts}"/>
    <texture name="wood" type="2d" builtin="checker" rgb1=".42 .26 .16" rgb2=".38 .23 .14" width="256" height="256"/>
    <material name="floor" texture="wood" texrepeat="12 12" reflectance=".15"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1=".95 .95 .93" rgb2=".8 .8 .78" width="64" height="64"/>
  </asset>
  <worldbody>
    <light pos=".1 -.3 .6" dir="-.1 .4 -1" diffuse=".9 .9 .85" castshadow="true"/>
    <light pos="-.3 .2 .5" dir=".4 -.2 -1" diffuse=".35 .35 .35" castshadow="false"/>
    <geom type="plane" size="2 2 .1" friction="0.450 0.005 0.0005" material="floor"{sr}/>
    <body name="b" pos="0 0 .3"><freejoint/>
      <inertial pos="{com[0] * s:.5f} {com[1] * s:.5f} {com[2] * s:.5f}" mass="{M * 1e-3:.5f}" fullinertia="{full}"/>
      <geom type="mesh" mesh="h" friction="0.450 0.005 0.0005" rgba=".86 .74 .64 1"{sr}/>
      <geom type="box" size=".014 .014 .0002" pos="{k['x'] * s:.4f} 0 -.0003" rgba=".15 .45 .95 1" contype="0" conaffinity="0" mass="0"/>
    </body>
  </worldbody>
</mujoco>""", P * s


def start(att, rng, Ps):
    roll, pitch = S.ATTITUDES[att]
    r = np.radians(roll + rng.normal(0, 7.5)); pt = np.radians(pitch + rng.normal(0, 7.5)); yw = rng.uniform(0, 2 * np.pi)
    q0 = np.zeros(4); mujoco.mju_euler2Quat(q0, np.array([r, pt, 0.0]), 'xyz'); q = np.zeros(4)
    mujoco.mju_mulQuat(q, np.array([np.cos(yw / 2), 0, 0, np.sin(yw / 2)]), q0)
    R9 = np.zeros(9); mujoco.mju_quat2Mat(R9, q); return q, R9.reshape(3, 3)


def run(name, high, att, seed, dampratio, seconds=1.6, fps=120, drop_mm=60.0):
    xml, Ps = scene(name, high, dampratio)
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m); rnd = mujoco.Renderer(m, H, W)
    q, R = start(att, np.random.default_rng(seed), Ps)
    d.qpos[:3] = (0, 0, drop_mm * 1e-3 - (Ps @ R.T)[:, 2].min()); d.qpos[3:7] = q
    cam = mujoco.MjvCamera(); cam.distance = 0.32; cam.elevation = -6; cam.azimuth = 90
    frames = []; per = int(round(1 / fps / m.opt.timestep))
    for _ in range(int(seconds * fps)):
        cam.lookat[:] = (d.qpos[0], d.qpos[1], 0.035)
        rnd.update_scene(d, camera=cam); frames.append(rnd.render().copy())
        mujoco.mj_step(m, d, nstep=per)
    return frames, T.classify(d.xmat[1].reshape(3, 3))


if __name__ == '__main__':
    from PIL import Image, ImageDraw
    os.makedirs(os.path.join(HERE, 'viz'), exist_ok=True)
    for n in ('E1_tub', 'E3_tall'):
        for dr, tag in ((None, 'dead'), (0.2, 'bounce')):
            open(os.path.join(HERE, 'viz', f'{n}_low_{tag}.xml'), 'w').write(scene(n, False, dr)[0])
    clips = [('E3_tall', False, 'nose down', 3), ('E3_tall', False, 'left side down', 5), ('E1_tub', False, 'tail down', 2),
             ('E1_tub', False, 'upside down, 45 to the left', 4)]
    out = os.path.join(ROOT, 'figures', 'sim_drops.mp4')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{2 * W}x{H}', '-r', '30', '-i', '-',
                           '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '20', out], stdin=subprocess.PIPE)
    for name, high, att, seed in clips:
        (A, ra), (B, rb) = run(name, high, att, seed, None), run(name, high, att, seed, 0.2)
        label = f"{name.split('_')[0]}, weight low, start: {att} (model's names)"
        for i, (a, b) in enumerate(zip(A, B)):
            im = Image.fromarray(np.concatenate([a, b], 1)); d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 2 * W, 18), fill=(0, 0, 0)); d.text((6, 3), label + '   (1/4 speed)', fill=(255, 255, 255))
            d.text((6, H - 16), f'dead contact -> {ra}' if i > len(A) * 0.8 else 'dead contact (no bounce)', fill=(0, 0, 0))
            d.text((W + 6, H - 16), f'bounce -> {rb}' if i > len(B) * 0.8 else 'bounce (fitted at 6 cm)', fill=(0, 0, 0))
            ff.stdin.write(np.asarray(im).tobytes())
        print(f'{name} {att}: dead -> {ra}, bounce -> {rb}', flush=True)
    ff.stdin.close(); ff.wait(); print('wrote', out)
