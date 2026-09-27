"""Look through the head's camera and steer it with the mouse, like mouse-look in a game.

    python sim/mujoco/mouse_look.py

The mouse sets where the servos are told to point; the servos get there at MG90D speed, so a fast
flick lags and catches up the way the real head will. The corner shows the head from outside.

  click        start steering (captures the cursor)
  mouse        look around
  Esc          free the cursor (Esc again quits)
  R            back to straight ahead
  + / -        mouse sensitivity
  Tab          hide / show the outside view
  Q            quit

    python sim/mujoco/mouse_look.py --selftest   # scripted mouse, saves out/mouse_look_test.png, exits
"""
import os, sys, time
import numpy as np
import glfw
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
XML = os.path.join(HERE, 'out', 'head.xml')
SENS = 0.15                                  # degrees of head turn per pixel of mouse movement


class MouseLook:
    def __init__(self, selftest=False):
        if not os.path.exists(XML):
            sys.exit('no %s -- run sim/mujoco/build_head.py first' % XML)
        self.m = mujoco.MjModel.from_xml_path(XML); self.d = mujoco.MjData(self.m)
        m = self.m
        self.a_pan, self.a_tilt = m.actuator('pan_servo').id, m.actuator('tilt_servo').id
        self.q_pan, self.q_tilt = m.joint('pan').qposadr[0], m.joint('tilt').qposadr[0]
        self.pan_lim = m.actuator_ctrlrange[self.a_pan]; self.tilt_lim = m.actuator_ctrlrange[self.a_tilt]
        self.pan = self.tilt = 0.0
        self.sens, self.inset, self.captured, self.last = SENS, True, False, None

        glfw.init()
        if selftest:
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.win = glfw.create_window(1280, 800, 'Head camera - mouse look (Esc frees the cursor, Q quits)', None, None)
        glfw.make_context_current(self.win); glfw.swap_interval(1)
        if not selftest:
            glfw.set_mouse_button_callback(self.win, self.on_click)
            glfw.set_cursor_pos_callback(self.win, self.on_mouse)
            glfw.set_key_callback(self.win, self.on_key)

        self.scene = mujoco.MjvScene(m, maxgeom=10000)
        self.ctx = mujoco.MjrContext(m, mujoco.mjtFontScale.mjFONTSCALE_150)
        self.opt = mujoco.MjvOption(); self.pert = mujoco.MjvPerturb()
        self.eye = mujoco.MjvCamera(); self.eye.type = mujoco.mjtCamera.mjCAMERA_FIXED
        self.eye.fixedcamid = m.camera('head_cam').id
        self.outside = mujoco.MjvCamera(); self.outside.lookat[:] = (0.0, 0.0, 0.03)
        self.outside.distance, self.outside.azimuth, self.outside.elevation = 0.30, 25, -25   # from behind

    # ---- input
    def capture(self, on):
        self.captured = on; self.last = None
        glfw.set_input_mode(self.win, glfw.CURSOR, glfw.CURSOR_DISABLED if on else glfw.CURSOR_NORMAL)
        if on and glfw.raw_mouse_motion_supported():
            glfw.set_input_mode(self.win, glfw.RAW_MOUSE_MOTION, glfw.TRUE)

    def move(self, dx, dy):
        """mouse right = look right (pan is + anticlockwise from above); mouse up = look up"""
        self.pan = float(np.clip(self.pan - dx * self.sens, *self.pan_lim))
        self.tilt = float(np.clip(self.tilt - dy * self.sens, *self.tilt_lim))

    def on_mouse(self, win, x, y):
        if self.captured and self.last is not None:
            self.move(x - self.last[0], y - self.last[1])
        self.last = (x, y)

    def on_click(self, win, button, action, mods):
        if action == glfw.PRESS and not self.captured:
            self.capture(True)

    def on_key(self, win, key, sc, action, mods):
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:                   # like a game: first Esc lets go of the cursor
            if self.captured:
                self.capture(False)
            else:
                glfw.set_window_should_close(win, True)
        elif key == glfw.KEY_Q:
            glfw.set_window_should_close(win, True)
        elif key == glfw.KEY_R:
            self.pan = self.tilt = 0.0
        elif key == glfw.KEY_TAB:
            self.inset = not self.inset
        elif key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
            self.sens *= 1.25
        elif key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
            self.sens /= 1.25

    # ---- sim and drawing
    def advance(self, secs):
        self.d.ctrl[self.a_pan], self.d.ctrl[self.a_tilt] = self.pan, self.tilt
        end = self.d.time + secs
        while self.d.time < end:
            mujoco.mj_step(self.m, self.d)

    def draw(self):
        w, h = glfw.get_framebuffer_size(self.win)
        full = mujoco.MjrRect(0, 0, w, h)
        mujoco.mjv_updateScene(self.m, self.d, self.opt, self.pert, self.eye, mujoco.mjtCatBit.mjCAT_ALL, self.scene)
        mujoco.mjr_render(full, self.scene, self.ctx)
        # crosshair: where the lens points, open in the middle so the target isn't hidden
        cx, cy, g, l = w // 2, h // 2, 8, 12
        for r in (mujoco.MjrRect(cx - g - l, cy - 1, l, 2), mujoco.MjrRect(cx + g, cy - 1, l, 2),
                  mujoco.MjrRect(cx - 1, cy - g - l, 2, l), mujoco.MjrRect(cx - 1, cy + g, 2, l)):
            mujoco.mjr_rectangle(r, 1, 1, 1, 0.8)
        if self.inset:
            iw, ih = w // 4, h // 4
            box = mujoco.MjrRect(w - iw - 10, 10, iw, ih)
            mujoco.mjr_rectangle(mujoco.MjrRect(box.left - 2, box.bottom - 2, iw + 4, ih + 4), 1, 1, 1, 0.6)
            self.outside.azimuth = np.degrees(self.d.qpos[self.q_pan]) + 25      # stay behind the head as it pans
            mujoco.mjv_updateScene(self.m, self.d, self.opt, self.pert, self.outside, mujoco.mjtCatBit.mjCAT_ALL, self.scene)
            mujoco.mjr_render(box, self.scene, self.ctx)
        pan_now, tilt_now = np.degrees(self.d.qpos[self.q_pan]), np.degrees(self.d.qpos[self.q_tilt])
        stop = lambda v, lim: '  AT STOP' if min(abs(v - lim[0]), abs(v - lim[1])) < 0.5 else ''
        mujoco.mjr_overlay(mujoco.mjtFont.mjFONT_NORMAL, mujoco.mjtGridPos.mjGRID_TOPLEFT, full,
                           'pan\ntilt\nsensitivity\ncursor',
                           'told %+6.1f   is %+6.1f%s\ntold %+6.1f   is %+6.1f%s\n%.2f deg/px  (+/-)\n%s'
                           % (self.pan, pan_now, stop(self.pan, self.pan_lim), self.tilt, tilt_now,
                              stop(self.tilt, self.tilt_lim), self.sens,
                              'steering (Esc frees it)' if self.captured else 'free: click the window to steer'), self.ctx)
        return w, h

    def run(self):
        wall = time.perf_counter()
        while not glfw.window_should_close(self.win):
            now = time.perf_counter()
            self.advance(min(now - wall, 0.05))          # real time; never try to catch up more than 50 ms
            wall = now
            self.draw()
            glfw.swap_buffers(self.win); glfw.poll_events()
        glfw.terminate()

    def selftest(self):
        """scripted mouse: 400 px right and 200 px up, then read where the head went"""
        from PIL import Image
        self.move(400, -200)
        self.advance(0.8)
        w, h = self.draw()
        rgb = np.zeros((h, w, 3), np.uint8); mujoco.mjr_readPixels(rgb, None, mujoco.MjrRect(0, 0, w, h), self.ctx)
        Image.fromarray(np.flipud(rgb)).save(os.path.join(HERE, 'out', 'mouse_look_test.png'))
        pan_now, tilt_now = np.degrees(self.d.qpos[self.q_pan]), np.degrees(self.d.qpos[self.q_tilt])
        print('mouse 400 px right, 200 px up -> told pan %+.1f tilt %+.1f, head at pan %+.1f tilt %+.1f'
              % (self.pan, self.tilt, pan_now, tilt_now))
        ok = pan_now < -50 and tilt_now > 25          # right = pan negative (clockwise from above); up = tilt up
        print('directions', 'OK' if ok else 'WRONG')
        glfw.terminate()
        return ok


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(0 if MouseLook(selftest=True).selftest() else 1)
    MouseLook().run()
