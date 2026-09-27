"""The head tracks a butterfly by looking for it in its own camera image, the way the real robot will
with YOLO.

    python sim/mujoco/butterfly.py

Every camera frame (30 a second) it renders what the head camera sees, finds the butterfly's pixels,
and works out how far off centre it is. After the camera delay it turns the servos to put it back in the
middle. The detector is perfect for now: MuJoCo tells it exactly which pixels are butterfly. It can
only see what's in frame, though, so it loses the butterfly if it flies out of view too fast. When it
does, the head sweeps to find it again.

  Space (or T) lock on / let go (let go: the mouse steers, as in mouse_look.py)
  [ / ]        camera delay down / up, 50 ms at a time
  B            butterfly speed: calm / normal / wild
  R            straight ahead; click, Esc, Q, Tab, +/- as in mouse_look.py

    python sim/mujoco/butterfly.py --selftest   # 30 s runs at several delays, tracking off as the control
"""
import os, sys
from collections import deque
import numpy as np
import glfw
import mujoco
from mouse_look import MouseLook

FPS = 30                                     # camera frames a second
DET_W, DET_H = 320, 240                      # the size of the image the detector looks at
SPEEDS = (('calm', 0.5), ('normal', 1.0), ('wild', 2.2))
ON_TARGET = 5.0                              # deg: "on target" when the lens points within this of it
BOB, FLAP = 0.012, 0.9                       # wingbeat: 1.2 cm up and down, wings +-0.9 rad, 5 a second
LOST_AFTER = 0.7                             # s without a sighting before the head starts sweeping


class Butterfly(MouseLook):
    BODIES = ('butterfly', 'wing_l', 'wing_r')            # the target's mocap bodies: body, left wing, right wing
    GEOMS = ('bf_body', 'bf_wing_l', 'bf_wing_r')        # the pixels the detector counts as the target
    ON_TARGET = ON_TARGET
    DET_W, DET_H = DET_W, DET_H                        # the detector's image size

    def __init__(self, selftest=False, seed=1):
        super().__init__(selftest)
        m = self.m
        self.bf = [m.body(n).mocapid[0] for n in self.BODIES]
        self.bf_geoms = {m.geom(n).id for n in self.GEOMS}
        self.cam_id = m.camera('head_cam').id
        f = (self.DET_H / 2) / np.tan(np.radians(m.cam_fovy[self.cam_id]) / 2)
        self.focal = f
        self.cap_scene = mujoco.MjvScene(m, maxgeom=10000)
        rng = np.random.default_rng(seed)
        self.phase = rng.uniform(0, 2 * np.pi, 8)
        self.tracking, self.delay, self.speed_i = True, 0.10, 1
        self.frames = deque()                    # (time taken, pixel centre or None, camera pos, camera axes)
        self.next_frame, self.last_seen, self.sweep_dir = 0.0, 0.0, 1.0
        self.box = None                          # the latest detection, for drawing
        self.stats = dict(n=0, on=0, seen=0, err=0.0)
        self.clock = 0.0                         # the butterfly's own time, so B changes speed smoothly
        if not selftest:
            glfw.set_key_callback(self.win, self.on_key2)

    # ---- the butterfly: a smooth wander round the head, plus the bob of its wingbeat
    def fly(self, dt):
        self.clock += dt * SPEEDS[self.speed_i][1]
        T, p, t = self.clock, self.phase, self.d.time
        theta = 0.9 * np.sin(0.31 * T + p[0]) + 0.6 * np.sin(0.73 * T + p[1]) + 0.3 * np.sin(1.7 * T + p[2])
        r = 0.33 + 0.10 * np.sin(0.5 * T + p[3]) + 0.04 * np.sin(2.3 * T + p[4])
        z = 0.13 + 0.08 * np.sin(0.6 * T + p[5]) + 0.04 * np.sin(1.9 * T + p[6]) + BOB * np.sin(2 * np.pi * 5 * t)
        pos = np.array([r * np.cos(theta), r * np.sin(theta), z])
        prev = self.d.mocap_pos[self.bf[0]].copy()
        v = pos - prev
        yaw = np.arctan2(v[1], v[0]) if np.hypot(v[0], v[1]) > 1e-7 else 0.0
        flap = 0.25 + FLAP * np.sin(2 * np.pi * 5 * t)
        q_yaw = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)])
        for mid, roll in zip(self.bf, (0.0, flap, -flap)):
            q = np.zeros(4)
            mujoco.mju_mulQuat(q, q_yaw, np.array([np.cos(roll / 2), np.sin(roll / 2), 0, 0]))
            self.d.mocap_pos[mid] = pos; self.d.mocap_quat[mid] = q

    # ---- the camera and the detector
    def grab_frame(self):
        m, d, ctx = self.m, self.d, self.ctx
        mujoco.mj_forward(m, d)
        mujoco.mjv_updateScene(m, d, self.opt, self.pert, self.eye, mujoco.mjtCatBit.mjCAT_ALL, self.cap_scene)
        self.cap_scene.flags[mujoco.mjtRndFlag.mjRND_SEGMENT] = True
        self.cap_scene.flags[mujoco.mjtRndFlag.mjRND_IDCOLOR] = True
        rect = mujoco.MjrRect(0, 0, self.DET_W, self.DET_H)
        mujoco.mjr_setBuffer(mujoco.mjtFramebuffer.mjFB_OFFSCREEN, ctx)
        mujoco.mjr_render(rect, self.cap_scene, ctx)
        rgb = np.empty((self.DET_H, self.DET_W, 3), np.uint8)
        mujoco.mjr_readPixels(rgb, None, rect, ctx)
        mujoco.mjr_setBuffer(mujoco.mjtFramebuffer.mjFB_WINDOW, ctx)
        seg = np.flipud(rgb).astype(np.uint32)
        seg = seg[..., 0] + seg[..., 1] * 256 + seg[..., 2] * 65536          # segment id per pixel, 0 = sky
        lut = np.zeros(self.cap_scene.ngeom + 1, bool)
        for g in self.cap_scene.geoms[:self.cap_scene.ngeom]:
            if g.segid >= 0 and g.objtype == mujoco.mjtObj.mjOBJ_GEOM and g.objid in self.bf_geoms:
                lut[g.segid + 1] = True
        ys, xs = np.nonzero(lut[np.minimum(seg, self.cap_scene.ngeom)])
        found = None
        if len(xs) >= 3:
            found = (xs.mean(), ys.mean(), xs.min(), xs.max(), ys.min(), ys.max())
        self.frames.append((d.time, found, d.cam_xpos[self.cam_id].copy(), d.cam_xmat[self.cam_id].reshape(3, 3).copy()))

    def steer(self):
        """use every frame that has come out of the camera delay"""
        while self.frames and self.frames[0][0] + self.delay <= self.d.time:
            t, found, _, axes = self.frames.popleft()
            self.box = found
            if found is None:
                continue
            self.last_seen = self.d.time
            if not self.tracking:
                continue
            u, v = found[0] - self.DET_W / 2, found[1] - self.DET_H / 2
            ray = axes @ np.array([u / self.focal, -v / self.focal, -1.0])   # camera looks down its -Z
            pan = np.degrees(np.arctan2(ray[1], ray[0]))
            tilt = np.degrees(np.arctan2(ray[2], np.hypot(ray[0], ray[1])))
            # the coil stops at +-180: pick the way round nearest where the head already is
            options = [pan + k for k in (-360, 0, 360) if self.pan_lim[0] <= pan + k <= self.pan_lim[1]]
            self.pan = float(min(options, key=lambda a: abs(a - self.pan)))
            self.tilt = float(np.clip(tilt, *self.tilt_lim))
        if self.tracking and self.d.time - self.last_seen > LOST_AFTER:   # lost: sweep for it
            self.tilt = 15.0
            self.pan += self.sweep_dir * 90.0 * self.m.opt.timestep     # 90 deg/s
            if abs(self.pan) > 120:
                self.sweep_dir = -np.sign(self.pan)

    def truth(self):
        """how far off the lens really points, deg (from the model, not the camera)"""
        c = self.d.cam_xpos[self.cam_id]; axis = -self.d.cam_xmat[self.cam_id].reshape(3, 3)[:, 2]
        to = self.d.mocap_pos[self.bf[0]] - c
        return np.degrees(np.arccos(np.clip(axis @ to / np.linalg.norm(to), -1, 1)))

    def advance(self, secs):
        end = self.d.time + secs
        while self.d.time < end:
            self.fly(self.m.opt.timestep)
            if self.d.time >= self.next_frame:
                self.grab_frame(); self.next_frame += 1.0 / FPS
                e = self.truth()
                self.stats['n'] += 1; self.stats['err'] += e
                self.stats['on'] += e < self.ON_TARGET; self.stats['seen'] += self.frames[-1][1] is not None
            self.steer()
            self.d.ctrl[self.a_pan], self.d.ctrl[self.a_tilt] = self.pan, self.tilt
            mujoco.mj_step(self.m, self.d)

    # ---- input and drawing
    def on_key2(self, win, key, sc, action, mods):
        if action == glfw.PRESS:
            if key in (glfw.KEY_SPACE, glfw.KEY_T):
                self.tracking = not self.tracking
                if not self.tracking:            # letting go hands the head straight to the mouse
                    self.capture(True)
            elif key == glfw.KEY_LEFT_BRACKET:
                self.delay = max(0.0, self.delay - 0.05)
            elif key == glfw.KEY_RIGHT_BRACKET:
                self.delay = min(1.0, self.delay + 0.05)
            elif key == glfw.KEY_B:
                self.speed_i = (self.speed_i + 1) % len(SPEEDS)
            elif key == glfw.KEY_R:
                self.stats = dict(n=0, on=0, seen=0, err=0.0)
        self.on_key(win, key, sc, action, mods)

    def on_mouse(self, win, x, y):
        if self.tracking:
            self.last = (x, y)                   # the tracker has the servos; keep the mouse from jumping later
            return
        super().on_mouse(win, x, y)

    def draw(self):
        w, h = super().draw()
        self.draw_box(w, h)
        self.draw_panel(w, h)
        return w, h

    def draw_box(self, w, h):
        if self.box is not None:                 # what the detector saw, delay included
            s = h / self.DET_H
            x0, x1 = w / 2 + (self.box[2] - self.DET_W / 2) * s - 4, w / 2 + (self.box[3] - self.DET_W / 2) * s + 4
            y0, y1 = h / 2 - (self.box[5] - self.DET_H / 2) * s - 4, h / 2 - (self.box[4] - self.DET_H / 2) * s + 4
            x0, x1, y0, y1 = map(int, (x0, x1, y0, y1))
            for r in ((x0, y0, x1 - x0, 2), (x0, y1, x1 - x0, 2), (x0, y0, 2, y1 - y0), (x1, y0, 2, y1 - y0 + 2)):
                mujoco.mjr_rectangle(mujoco.MjrRect(*r), 0.2, 1, 0.3, 0.9)

    def draw_panel(self, w, h):
        st = self.stats; n = max(st['n'], 1)
        lost = self.tracking and self.d.time - self.last_seen > LOST_AFTER
        mujoco.mjr_overlay(mujoco.mjtFont.mjFONT_NORMAL, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT,
                           mujoco.MjrRect(0, 0, w, h),
                           'lock-on (Space)\ncamera delay ([ ])\nbutterfly (B)\noff target now\non target\nin frame',
                           '%s\n%.0f ms\n%s\n%.1f deg\n%.0f%%  (within %.0f deg; R resets)\n%.0f%%'
                           % ('LOST - sweeping' if lost else ('LOCKED ON' if self.tracking else 'off - mouse steers'),
                              self.delay * 1000, SPEEDS[self.speed_i][0], self.truth(),
                              100 * st['on'] / n, self.ON_TARGET, 100 * st['seen'] / n), self.ctx)


def selftest():
    """30 s of flight per row, the same path every run. Checks: with tracking off (the control) the lens is
    almost never on the butterfly; with no delay it mostly is; and more delay only makes it worse.
    With no delay it still misses by 2-4 deg: the 5-a-second wingbeat bob (about +-2 deg, too fast for
    30 frames a second), the wings sitting above the body (0.7 deg), and a frame of lag (about 1 deg).
    Measured 2026-09-27 by switching the bob and flap off (BOB, FLAP = 0): 100% on target, 2.0 deg."""
    delays = (0.0, 0.10, 0.25, 0.50)
    print('30 s each, the same flight path every run; "on target" = lens within %.0f deg' % ON_TARGET)
    ok = True
    for sp in (1, 2):
        print('  --', SPEEDS[sp][0], 'butterfly')
        on = []
        for track, dl in [(False, 0.10)] + [(True, dl) for dl in delays]:
            b = Butterfly(selftest=True)
            b.speed_i, b.tracking, b.delay = sp, track, dl
            b.advance(30.0)
            st = b.stats; n = st['n']
            label = 'tracking off (control)' if not track else 'tracking, %3d ms delay' % (dl * 1000)
            print('  %-24s on target %3.0f%%   in frame %3.0f%%   mean miss %5.1f deg'
                  % (label, 100 * st['on'] / n, 100 * st['seen'] / n, st['err'] / n))
            if not track:
                ok &= st['on'] / n < 0.2
            else:
                on.append(st['on'] / n)
            b.ctx.free(); glfw.terminate()
        ok &= on[0] > 0.6 and all(a >= b for a, b in zip(on, on[1:]))
    print('checks', 'OK' if ok else 'FAILED')
    return ok


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(0 if selftest() else 1)
    Butterfly().run()
