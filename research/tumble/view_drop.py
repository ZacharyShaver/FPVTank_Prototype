"""Watch simulated drops in MuJoCo's 3D viewer, from any start, in slow motion.

    python research/tumble/view_drop.py                       # E3, mass low, bounce, all six starts in turn
    python research/tumble/view_drop.py --body E1 --start "nose down" --contact stiff --slow 8

--body E1 | E2 | E3; --mass low | high; --contact dead (MuJoCo's default) | bounce (fitted at 6 cm) | stiff (a hard
floor: barely sinks in, rebounds ~0.3); --start one of the six (the model's names: "nose down" is the head end down)
or all; --height mm; --slow how many times slower than real time; --seed.

In the window: left-drag turns the view, right-drag moves it, scroll zooms. Double-click the body to select it, then
Ctrl + right-drag pushes it and Ctrl + left-drag twists it. Space pauses. Close the window to stop.
"""
import os, sys, time, argparse
import numpy as np
import mujoco
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import render_drops as RD, scale_model as S, tumble as T

BODY = {'E1': 'E1_tub', 'E2': 'E2_dome', 'E3': 'E3_tall'}
CONTACT = {'dead': None, 'bounce': '0.02 0.2', 'stiff': '0.002 0.35'}   # stiff: restitution 0.31, the slow-motion measurement


def model(body, high, contact):
    xml, Ps = RD.scene(BODY[body], high, None)
    sr = CONTACT[contact]
    if sr:
        xml = xml.replace('material="floor"', f'material="floor" solref="{sr}"').replace('rgba=".86 .74 .64 1"', f'rgba=".86 .74 .64 1" solref="{sr}"')
    m = mujoco.MjModel.from_xml_string(xml)
    return m, mujoco.MjData(m), Ps


def place(m, d, Ps, att, rng, height):
    q, R = RD.start(att, rng, Ps)
    mujoco.mj_resetData(m, d); d.qpos[:3] = (0, 0, height / 1000 - (Ps @ R.T)[:, 2].min()); d.qpos[3:7] = q
    mujoco.mj_forward(m, d)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--body', default='E3', choices=list(BODY)); ap.add_argument('--mass', default='low', choices=['low', 'high'])
    ap.add_argument('--contact', default='bounce', choices=list(CONTACT)); ap.add_argument('--start', default='all')
    ap.add_argument('--height', type=float, default=60.0); ap.add_argument('--slow', type=float, default=4.0)
    ap.add_argument('--seed', type=int, default=0); ap.add_argument('--dry', action='store_true', help='no window: print what each drop does')
    a = ap.parse_args()
    starts = list(S.ATTITUDES) if a.start == 'all' else [a.start]
    m, d, Ps = model(a.body, a.mass == 'high', a.contact); rng = np.random.default_rng(a.seed)
    if a.dry:
        for att in starts:
            place(m, d, Ps, att, rng, a.height); deep = 0.0
            for _ in range(int(2.0 / m.opt.timestep)):
                mujoco.mj_step(m, d); deep = min(deep, d.xpos[1][2] + (Ps @ d.xmat[1].reshape(3, 3).T)[:, 2].min())
            print(f'{att:<30} -> {T.classify(d.xmat[1].reshape(3, 3)):<11} (sank {-deep * 1000:.1f} mm into the floor)')
        sys.exit()
    import mujoco.viewer
    with mujoco.viewer.launch_passive(m, d) as v:
        v.cam.distance, v.cam.elevation, v.cam.azimuth = 0.35, -8, 90
        k = 0
        while v.is_running():
            att = starts[k % len(starts)]; k += 1
            with v.lock(): place(m, d, Ps, att, rng, a.height)
            print(f'drop {k}: {a.body}, mass {a.mass}, {a.contact} contact, start "{att}"', flush=True)
            t_end = time.time() + 2.2 * a.slow
            while v.is_running() and time.time() < t_end:
                t0 = time.time()
                with v.lock(): mujoco.mj_step(m, d, nstep=10)
                v.cam.lookat[:] = (d.qpos[0], d.qpos[1], 0.03); v.sync()
                time.sleep(max(0.0, 10 * m.opt.timestep * a.slow - (time.time() - t0)))
            print(f'   -> {T.classify(d.xmat[1].reshape(3, 3))}', flush=True)
