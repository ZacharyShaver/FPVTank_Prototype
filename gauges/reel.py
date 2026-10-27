"""A short reel of the gauges' runs (2026-10-27): chapters of side-by-side tries, each one try of a gauge as the gauge
runs it (gauges.Sim, hills.hill_try, climb_try, turn, falls; film.py's colours and cameras). Zach: "a nice
compilation of some of the simulation runs ... an accurate picture of these but is consumable easily".

    SCORPION_SEARCH=search_hills python gauges/reel.py   -> gauges/out/film/reel.mp4

A hill is the floor with gravity tipped. Each frame is drawn in a copy of the model whose floor is tilted by the
slope, with the robot's logged pose turned the same way, so the hill looks like a hill; the physics is untouched. Each chapter's header gives the gauge's reading (20 tries, or the knob sweep's screen). A panel is one try, at a
slope or step where its gauge's verdict is clear; its label says what that try did. (A first cut showed ride height
90 mm braced making 40° up in its one try, where the screen reads 35°: that row moved to 45°.)
"""
import os, sys, math, re, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import film as F, gauges as G, hills as H, knobs as K

PW, PH, HEAD, CW = F.PW, F.PH, 58, 3 * F.PW
CH = HEAD + 2 * PH
FPS = F.FPS


def u_of(sim):
    return min(H.V_HILL / (sim.w0 * sim.sp['R'] * 1e-3), 1.0)


def spec(ch):
    return K.make(dict(K.T3, **ch))


def hill(ch, deg, down, th=None, mu=H.GRIP, seed=1):
    """one hill try (the better direction of the two, as the gauge takes it), then a second more"""
    sp = spec(ch); best = None
    for back in (False, True):
        sim = F.Rec(sp, mu); rng = np.random.default_rng([seed, deg, int(back)])
        out = H.hill_try(sim, deg, down, back, rng, th); t_out = sim.d.time
        u = (-1.0 if back else 1.0) * u_of(sim)
        for _ in range(int(1000 / G.TICK)):
            sim.drive(u, u)
        best = (sim, out, t_out, back)
        if out == 'ok':
            break
    return best


def side(ch, deg, yaw_t=None, th=None, mu=H.GRIP, seed=1):
    sp = spec(ch); sim = F.Rec(sp, mu); rng = np.random.default_rng([seed, deg, 7])
    out = H.side_try(sim, deg, rng, yaw_t, th); t_out = sim.d.time
    u = u_of(sim)
    for _ in range(int(1000 / G.TICK)):
        sim.drive(u, u)
    return sim, out, t_out


def frames_tilted(sim, log, axis, deg, cams, label, t_end):
    """film.frames, drawn in a copy of the model with the floor tilted by deg (about Y: a hill, +X uphill; about X: a
    side slope, +Y uphill) and each logged pose turned with it"""
    import mujoco
    a = math.radians(deg); c, s_ = math.cos(a), math.sin(a)
    Rm, qr = ((np.array([[c, 0, -s_], [0, 1, 0], [s_, 0, c]]), (math.cos(a / 2), 0.0, -math.sin(a / 2), 0.0)) if axis == 'y' else
              (np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]]), (math.cos(a / 2), math.sin(a / 2), 0.0, 0.0)))
    xml = F.visual_xml(sim.sp, 1.0)
    if axis == 'y':                                                       # a hill seen from the side: a 1.2 m wide slab, so its edge is the slope
        p = Rm @ np.array([0.0, 0.0, -0.02])
        slab = '<geom type="box" material="floor" size="8 0.6 0.02" pos="%.5f %.5f %.5f" quat="%.6f %.6f %.6f %.6f"/>' % (*p, *qr)
        xml = re.sub(r'<geom type="plane"[^>]*/>', slab, xml, count=1)
    else:
        xml = xml.replace('<geom type="plane" material="floor"', '<geom type="plane" material="floor" quat="%.6f %.6f %.6f %.6f"' % qr, 1)
    xml = xml.replace('<visual>', '<visual><headlight ambient=".45 .45 .45" diffuse=".45 .45 .45"/>', 1).replace('reflectance=".05"', 'reflectance="0"')
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m); rid = m.body('robot').id
    r = mujoco.Renderer(m, PH, PW); out = []; ts = np.array([t for t, _ in log]); t0 = ts[0]; q4 = np.zeros(4)
    for t in np.arange(t0, t_end + 1e-9, 1.0 / FPS):
        i = min(int(np.searchsorted(ts, t)), len(log) - 1); q = log[i][1].copy()
        q[0:3] = Rm @ q[0:3]; mujoco.mju_mulQuat(q4, np.array(qr), q[3:7]); q[3:7] = q4
        d.qpos[:] = q; mujoco.mj_forward(m, d)
        cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE; cam.lookat[:] = d.xpos[rid]
        cam.distance, cam.azimuth, cam.elevation = cams['dist'], cams['az'], cams['el']
        r.update_scene(d, cam); out.append((r.render().copy(), label(t - t0)))
    r.close()
    return out


WORD = {'ok': 'made it 2.5 m', 'tipped': 'tipped over', 'slid': 'slid', 'stalled': 'stalled'}


def p_hill(title, ch, deg, down, th=None, mu=H.GRIP):
    sim, out, t_out, back = hill(ch, deg, down, th, mu)
    t0 = sim.log[0][0]; way = f"{deg}° {'down' if down else 'up'}" + (', in reverse' if back else '')
    lab = lambda t: [title, way if t < t_out - t0 else f'{way}: {WORD[out]}']
    return frames_tilted(sim, sim.log, 'y', deg, dict(dist=1.25, az=90.0, el=-8.0), lab, sim.log[-1][0]), out


def p_side(title, ch, deg, yaw_t=None, th=None, mu=H.GRIP):
    sim, out, t_out = side(ch, deg, yaw_t, th, mu)
    t0 = sim.log[0][0]; way = f'{deg}° side slope'
    lab = lambda t: [title, way if t < t_out - t0 else f'{way}: {WORD[out]}']
    return frames_tilted(sim, sim.log, 'x', deg, dict(dist=1.2, az=0.0, el=-6.0), lab, sim.log[-1][0]), out


def p_step(title, ch, h, mu=0.65, seed=5):
    sp = spec(ch); sim = F.Rec(sp, mu, step=h); ok = G.climb_try(sim, h, False, np.random.default_rng(seed)); t_out = sim.d.time
    u = u_of(sim)
    for _ in range(int(800 / G.TICK)):
        sim.drive(u, u)
    t0 = sim.log[0][0]
    lab = lambda t: [title, f'{h} mm step' if t < t_out - t0 else f"{h} mm step: {'on top' if ok else 'failed'}"]
    return F.frames(sim, sim.log, dict(dist=1.4, az=90.0, el=-8.0), lab, sim.log[-1][0]), 'ok' if ok else 'failed'


def p_turn(title, ch, mu=1.0):
    sp = spec(ch); sim = F.Rec(sp, mu); dia, t = G.turn(sim, 1)
    lab = lambda t_: [title, f'turn in place: {dia:.0f} mm circle' if dia else 'turn in place: never got round']
    return F.frames(sim, sim.log, dict(dist=1.1, az=90.0, el=-80.0), lab, sim.log[-1][0]), f'{dia:.0f} mm'


def p_fall(title, ch, seed=31):
    sp = spec(ch); sim = F.Rec(sp, 1.0); rng = np.random.default_rng(seed)
    for _ in range(80):
        rest, end, t_rest, t_end = F.fall(sim, rng)
        if rest != 'upright':
            break
    t0 = sim.log[0][0]
    lab = lambda t: [title, 'dropped from 300 mm' if t < t_rest - t0 else (f'landed {rest}: tail righting' if t < t_end - t0 else f'landed {rest}, righted at {t_end - t0:.1f} s' if end == 'upright' else f'still {end}')]
    return F.frames(sim, sim.log, dict(dist=1.5, az=135.0, el=-22.0), lab, t_end + 0.5), end


def header(img, title, sub):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(img); dr = ImageDraw.Draw(im)
    try:
        f1, f2 = ImageFont.truetype('segoeuib.ttf', 21), ImageFont.truetype('segoeui.ttf', 15)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    dr.rectangle([0, 0, CW, HEAD - 1], fill=(28, 32, 38)); dr.text((14, 6), title, fill=(255, 255, 255), font=f1)
    dr.text((14, 33), sub, fill=(200, 206, 214), font=f2)
    return np.asarray(im)


def chapter(ff, title, sub, panels):
    n = len(panels); cols = 3 if n > 4 else (2 if n in (2, 4) else n); rows = math.ceil(n / cols)
    x0 = (CW - cols * PW) // 2; y0 = HEAD + (2 * PH - rows * PH) // 2
    m = max(len(p) for p in panels)
    for k in range(m + int(1.5 * FPS)):
        canvas = np.full((CH, CW, 3), 245, np.uint8)
        for j, p in enumerate(panels):
            img, txt = p[min(k, len(p) - 1)]; r_, c_ = divmod(j, cols)
            canvas[y0 + r_ * PH:y0 + (r_ + 1) * PH, x0 + c_ * PW:x0 + (c_ + 1) * PW] = F.stamp(img, txt)
        ff.stdin.write(header(canvas, title, sub).tobytes())


def main():
    os.makedirs(F.OUT, exist_ok=True); path = os.path.join(F.OUT, 'reel.mp4'); log = []
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{CW}x{CH}', '-r', str(FPS), '-i', '-',
                           '-an', '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', path], stdin=subprocess.PIPE)
    for title, sub, specs in CHAPTERS:
        panels = []
        for fn, args in specs:
            fr, out = fn(*args); panels.append(fr); log.append((title, args[0], out))
            print(f'{title} | {args[0]}: {out}', flush=True)
        chapter(ff, title, sub, panels)
    ff.stdin.close(); ff.wait(); print(path)


B, B15 = -30.0, -15.0                     # the tail braced behind: T3's best angle up, and the raised and lowered bodies' best
CHAPTERS = [
    ('The five gauges, run on T3', 'One try each. T3 reads: upright 1.00, step 150 mm, turn 392 mm, hills 35° up / 40° down (45° / 45° with its tail braced).', [
        (p_fall, ('G1: a fall, the tail rights it', {})),
        (p_step, ('G2: step up, friction x0.65', {}, 140)),
        (p_turn, ('G3: turn-around space', {})),
        (p_hill, ('G4: up a hill, tail braced', {}, 45, False, B)),
        (p_hill, ('G5: down a hill, tail braced', {}, 45, True, B)),
        (p_side, ('New: across a slope', {}, 50)),
    ]),
    ('The tail braced on a hill', 'Gauge, 20 tries at friction x2.5: tail stowed 35° up / 40° down; braced behind, 45° / 45°. Same robot, same slopes.', [
        (p_hill, ('T3, tail stowed', {}, 40, False)),
        (p_hill, ('T3, tail braced at -30°', {}, 40, False, B)),
        (p_hill, ('T3, tail stowed', {}, 45, True)),
        (p_hill, ('T3, tail braced at -30°', {}, 45, True, B)),
    ]),
    ('Body height (ride height 15, 52 and 90 mm)', 'Step: 30, 150, 140 mm. Hills braced: 45°/50°, 45°/45°, 35°/40° (stowed 45°/45°, 35°/40°, 30°/35°). Bottom row: 45° up, braced.', [
        (p_step, ('ride height 15 mm', dict(clr=15.0), 100)),
        (p_step, ('T3, ride height 52 mm', {}, 100)),
        (p_step, ('ride height 90 mm', dict(clr=90.0), 100)),
        (p_hill, ('ride height 15 mm, braced', dict(clr=15.0), 45, False, B15)),
        (p_hill, ('T3, braced', {}, 45, False, B)),
        (p_hill, ('ride height 90 mm, braced', dict(clr=90.0), 45, False, B15)),
    ]),
    ('Wheelbase: hills bought with the step', 'Tyre gap 15, 62 (T3) and 150 mm. Step: 90, 150, 40 mm. Hills stowed: 25°/30°, 35°/40°, 50°/50°. Bottom row: 35° up, stowed.', [
        (p_step, ('tyre gap 15 mm', dict(gap=15.0), 80)),
        (p_step, ('T3, tyre gap 62 mm', {}, 80)),
        (p_step, ('tyre gap 150 mm', dict(gap=150.0), 80)),
        (p_hill, ('tyre gap 15 mm, stowed', dict(gap=15.0), 35, False)),
        (p_hill, ('T3, stowed', {}, 35, False)),
        (p_hill, ('tyre gap 150 mm, stowed', dict(gap=150.0), 35, False)),
    ]),
    ('Wheel width', 'Wider costs the turn (track 110: 393 mm, 180: 485; tyres 80 wide: 441) and moves no other gauge. Across a slope at x2.5 it buys 5° (55° to 60°); at x1 all slide at 40°.', [
        (p_turn, ('track 110 mm', dict(track=110.0))),
        (p_turn, ('track 180 mm', dict(track=180.0))),
        (p_turn, ('tyres 80 mm wide', dict(TW=80.0))),
        (p_side, ('track 110 mm', dict(track=110.0), 60)),
        (p_side, ('track 180 mm', dict(track=180.0), 60)),
        (p_side, ('ride height 90 mm', dict(clr=90.0), 55)),
    ]),
]


if __name__ == '__main__':
    main()
