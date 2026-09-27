"""The head tracks a bird, smoothly, by predicting where it's going.

    python sim/mujoco/train_bird.py     # once: trains out/bird_predictor.npz (~1 min)
    python sim/mujoco/bird.py

Like butterfly.py, it finds the bird in its own camera image, 30 frames a second, after a camera delay.
The detector is made YOLO-like: its centre jitters by a pixel and it misses 5% of frames. What changes
is what it does with a sighting. Three modes (M switches):

  hold     today's tracker: jump the servos to the last sighting. Always behind, and jumpy.
  line     draw a straight line through the recent sightings and follow it forward in time.
  learned  the trained network predicts the next 0.5 s of the bird's path; the head follows that path.

In line and learned, the servos get a target that moves continuously, not once per frame, and each new
prediction blends in over 50 ms. That's what makes it smooth. The prediction is what puts it on the bird.
The dots in the view are the predicted path.

  M            mode: hold / line / learned
  Space (or T) lock on / let go (let go: the mouse steers)
  [ / ]        camera delay down / up, 50 ms at a time
  B            bird speed: calm / normal / wild (wild is faster than anything it was trained on)
  R            straight ahead, and reset the score; click, Esc, Q, Tab, +/- as in mouse_look.py

    python sim/mujoco/bird.py --selftest   # 60 s per mode at 100 and 200 ms delay, tracking off as control
"""
import os, sys
from collections import deque
import numpy as np
import glfw
import mujoco
import flight as F
from butterfly import Butterfly, SPEEDS, LOST_AFTER

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = os.path.join(HERE, 'out', 'bird_predictor.npz')
MODES = ('hold', 'line', 'learned')
LINE_K = 7                                   # the look-back train_bird.py found best for "line"
LEAD = 0.01                                  # s: aim this far ahead again, for the servo's own lag
BLEND = 0.05                                 # s: a new prediction fades in over this long
JITTER_PX, MISS = 2.0, 0.05                  # the YOLO-like detector: centre jitter (px at 640x480), misses
FLY_EVERY = 0.002                            # s: the flight model steps every 2 ms


class Bird(Butterfly):
    BODIES = ('bird', 'bird_wing_l', 'bird_wing_r')
    GEOMS = ('bird_body', 'bird_head', 'bird_tail', 'bird_wl', 'bird_wr')
    ON_TARGET = 3.0                          # deg: the bird is ~6 deg across at 3 m
    DET_W, DET_H = 640, 480                  # YOLO's usual input. At 320x240 a pigeon 6 m out is ~3 px and
                                             # gets missed 1 frame in 5

    def __init__(self, selftest=False, seed=1, mode='learned'):
        if not os.path.exists(WEIGHTS):
            sys.exit('no %s -- run python sim/mujoco/train_bird.py first' % WEIGHTS)
        super().__init__(selftest, seed)
        self.flight = F.Flight(1, np.random.default_rng(seed))
        self.fly_acc = 0.0
        for n in ('butterfly', 'wing_l', 'wing_r'):          # this is the bird's show: park the butterfly
            self.d.mocap_pos[self.m.body(n).mocapid[0]] = (0, 0, -5)
        self.fly(FLY_EVERY)                      # put the bird on its path before the first frame: left at the
                                                 # model's placeholder spot, it was "seen" dead ahead at 0.1 s
        self.learned = F.Learned(WEIGHTS)
        self.mode = mode
        self.noise = np.random.default_rng(seed + 100)
        self.hist = deque([(0.0, 0.0, False)] * F.N_HIST, maxlen=F.N_HIST)
        self.traj = self.prev = None             # (capture time, ref az, ref el, daz(H), del(H)), deg
        self.blend_from = 0.0
        self.dof = [self.m.jnt_dofadr[self.m.joint(j).id] for j in ('pan', 'tilt')]
        self.stats.update(acc=0.0, acc_n=0)
        if not selftest:
            glfw.set_key_callback(self.win, self.on_key3)

    # ---- the bird
    def fly(self, dt):
        self.fly_acc += dt * SPEEDS[self.speed_i][1]
        if self.fly_acc < FLY_EVERY:
            return
        self.flight.step(self.fly_acc); self.fly_acc = 0.0
        pos, yaw, t = self.flight.pos()[0], self.flight.heading()[0], self.flight.t
        flap = 0.2 + 0.8 * np.sin(2 * np.pi * F.FLAP_HZ * t) if self.flight.flapping[0] else 0.08
        q_yaw = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)])
        for mid, roll in zip(self.bf, (0.0, flap, -flap)):
            q = np.zeros(4)
            mujoco.mju_mulQuat(q, q_yaw, np.array([np.cos(roll / 2), np.sin(roll / 2), 0, 0]))
            self.d.mocap_pos[mid] = pos; self.d.mocap_quat[mid] = q

    # ---- the detector, made a little like YOLO
    def grab_frame(self):
        super().grab_frame()
        t, found, pos, axes = self.frames[-1]
        if found is not None:
            if self.noise.random() < MISS:
                found = None
            else:
                jx, jy = self.noise.normal(0, JITTER_PX, 2)
                found = (found[0] + jx, found[1] + jy) + tuple(found[2:])
        self.frames[-1] = (t, found, pos, axes)

    # ---- prediction and steering
    def predict(self, t_cap):
        h = np.array([(a, e) for a, e, _ in self.hist]); ok = np.array([v for *_, v in self.hist])
        if not ok.any():
            return
        x, ra, re = F.features(h[None, :, 0], h[None, :, 1], ok[None])
        p = {'hold': F.predict_hold, 'line': lambda x: F.predict_line(x, LINE_K), 'learned': self.learned}[self.mode](x)[0] * 10
        H = len(F.HORIZONS)
        self.prev, self.blend_from = self.traj, self.d.time
        self.traj = (t_cap, ra[0], re[0], p[:H], p[H:])

    def aim(self, traj, now):
        t_cap, ra, re, daz, dee = traj
        tau = now + LEAD - t_cap
        if self.mode == 'hold':
            return ra, re
        return ra + np.interp(tau, F.HORIZONS, daz), re + np.interp(tau, F.HORIZONS, dee)

    def steer(self):
        d = self.d
        self.stats['acc'] += sum(np.degrees(d.qacc[i]) ** 2 for i in self.dof); self.stats['acc_n'] += 1
        while self.frames and self.frames[0][0] + self.delay <= d.time:
            t, found, _, axes = self.frames.popleft()
            self.box = found
            if found is not None:
                u, v = found[0] - self.DET_W / 2, found[1] - self.DET_H / 2
                ray = axes @ np.array([u / self.focal, -v / self.focal, -1.0])
                self.hist.append((np.degrees(np.arctan2(ray[1], ray[0])),
                                  np.degrees(np.arctan2(ray[2], np.hypot(ray[0], ray[1]))), True))
                self.last_seen = d.time
            else:
                self.hist.append((0.0, 0.0, False))
            self.predict(t)
        if not self.tracking:
            return
        if d.time - self.last_seen > LOST_AFTER:                       # lost: sweep, forget the old path
            self.traj = self.prev = None
            self.tilt = 20.0
            self.pan += self.sweep_dir * 90.0 * self.m.opt.timestep
            if abs(self.pan) > 150:
                self.sweep_dir = -np.sign(self.pan)
            return
        if self.traj is None:
            return
        az, el = self.aim(self.traj, d.time)
        if self.prev is not None and self.mode != 'hold':
            w = min(1.0, (d.time - self.blend_from) / BLEND)
            if w < 1.0:
                az0, el0 = self.aim(self.prev, d.time)
                az = az0 + w * ((az - az0 + 180) % 360 - 180); el = el0 + w * (el - el0)
        options = [az + k for k in (-360, 0, 360) if self.pan_lim[0] <= az + k <= self.pan_lim[1]]
        self.pan = float(min(options, key=lambda a: abs(a - self.pan)))
        self.tilt = float(np.clip(el, *self.tilt_lim))

    # ---- input and drawing
    def on_key3(self, win, key, sc, action, mods):
        if action == glfw.PRESS and key == glfw.KEY_M:
            self.mode = MODES[(MODES.index(self.mode) + 1) % len(MODES)]
            self.traj = self.prev = None
            self.stats = dict(n=0, on=0, seen=0, err=0.0, acc=0.0, acc_n=0)
        if action == glfw.PRESS and key == glfw.KEY_R:
            self.stats = dict(n=0, on=0, seen=0, err=0.0, acc=0.0, acc_n=0)
        self.on_key2(win, key, sc, action, mods)

    def jumpiness(self):
        """RMS angular acceleration of the head, deg/s^2: what makes the picture shake"""
        return np.sqrt(self.stats['acc'] / max(self.stats['acc_n'], 1))

    def draw_path(self, w, h):
        """the predicted path, projected into the view"""
        if self.traj is None or self.mode == 'hold':
            return
        t_cap, ra, re, daz, dee = self.traj
        c = self.d.cam_xmat[self.cam_id].reshape(3, 3)
        f = (h / 2) / np.tan(np.radians(self.m.cam_fovy[self.cam_id]) / 2)
        for i in range(len(F.HORIZONS)):
            a, e = np.radians(ra + daz[i]), np.radians(re + dee[i])
            v = c.T @ np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
            if v[2] >= -1e-3:
                continue
            x, y = w / 2 + f * v[0] / -v[2], h / 2 + f * v[1] / -v[2]
            s = 7 if i == 0 else 5
            mujoco.mjr_rectangle(mujoco.MjrRect(int(x) - s // 2, int(y) - s // 2, s, s), 0.2, 0.9, 0.8, 0.9)

    def draw(self):
        w, h = super(Butterfly, self).draw()           # MouseLook's view and top panel
        self.draw_box(w, h)
        self.draw_path(w, h)
        st = self.stats; n = max(st['n'], 1)
        lost = self.tracking and self.d.time - self.last_seen > LOST_AFTER
        mujoco.mjr_overlay(mujoco.mjtFont.mjFONT_NORMAL, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT,
                           mujoco.MjrRect(0, 0, w, h),
                           'mode (M)\nlock-on (Space)\ncamera delay ([ ])\nbird (B)\noff target now\non target\n'
                           'jumpiness\nin frame',
                           '%s\n%s\n%.0f ms\n%s\n%.1f deg\n%.0f%%  (within %.0f deg; R resets)\n%.0f deg/s2\n%.0f%%'
                           % (self.mode.upper(),
                              'LOST - sweeping' if lost else ('LOCKED ON' if self.tracking else 'off - mouse steers'),
                              self.delay * 1000, SPEEDS[self.speed_i][0], self.truth(),
                              100 * st['on'] / n, self.ON_TARGET, self.jumpiness(), 100 * st['seen'] / n), self.ctx)
        return w, h


def selftest(secs=60.0):
    """Same bird, same path, every run; scored from the first sighting on. Checks: tracking off (the control) is almost never on the bird;
    learned is on target more than hold, and smoother than hold, at both delays."""
    print('%.0f s each, the same flight; "on target" = lens within %.0f deg of the bird' % (secs, Bird.ON_TARGET))
    print('  %-26s %10s %10s %14s %9s' % ('', 'on target', 'mean miss', 'jumpiness', 'in frame'))
    ok, res = True, {}
    runs = [('tracking off (control)', 'learned', False, 0.10)]
    for dl in (0.10, 0.20):
        runs += [('%-7s %3d ms delay' % (mo, dl * 1000), mo, True, dl) for mo in MODES]
    for label, mode, track, dl in runs:
        b = Bird(selftest=True, mode=mode)
        b.tracking, b.delay = track, dl
        if track:                                  # score tracking, not the first search: start at first sighting
            while b.last_seen == 0 and b.d.time < 10:
                b.advance(1 / 30)
            b.stats = dict(n=0, on=0, seen=0, err=0.0, acc=0.0, acc_n=0)
        b.advance(secs)
        st = b.stats; n = st['n']
        res[(mode, track, dl)] = (st['on'] / n, b.jumpiness())
        print('  %-26s %9.0f%% %8.1f deg %9.0f deg/s2 %8.0f%%'
              % (label, 100 * st['on'] / n, st['err'] / n, b.jumpiness(), 100 * st['seen'] / n))
        b.ctx.free(); glfw.terminate()
    ok &= res[('learned', False, 0.10)][0] < 0.1
    for dl in (0.10, 0.20):
        ok &= res[('learned', True, dl)][0] > res[('hold', True, dl)][0]
        ok &= res[('learned', True, dl)][1] < res[('hold', True, dl)][1]
    print('checks', 'OK' if ok else 'FAILED')
    return ok


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(0 if selftest() else 1)
    Bird().run()
