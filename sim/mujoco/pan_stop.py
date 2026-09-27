"""How much does the pan overshoot when it stops after a 90 deg move, and what fixes it?

    python sim/mujoco/pan_stop.py

2026-09-27: a jump command overshoots 7.9 deg. A smooth command (speed up and slow down gently)
cuts it to 0.6-1.4 deg; drag, a lighter cradle or a servo that brakes help less. The 2:1 step-up makes
the drum feel 4x heavier to the servo, which is why pan overshoots and tilt (about 1 deg) doesn't. Gear
play isn't modelled, so the real head will also rattle by about 1 deg at stops.
"""
import os
import mujoco, numpy as np
XML = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'head.xml')

def run(label, edit=None, profile=None, secs=0.8):
    m = mujoco.MjModel.from_xml_path(XML)
    if edit: edit(m)
    d = mujoco.MjData(m)
    a, j = m.actuator('pan_servo').id, m.joint('pan').qposadr[0]
    target, peak, settle, t = 90.0, 0.0, None, 0.0
    qs = []
    for i in range(int(secs / m.opt.timestep)):
        t = i * m.opt.timestep
        d.ctrl[a] = profile(t) if profile else target
        mujoco.mj_step(m, d)
        q = np.degrees(d.qpos[j]); qs.append(q)
        peak = max(peak, q - target)
    qs = np.array(qs); ts = np.arange(len(qs)) * m.opt.timestep
    outside = np.nonzero(np.abs(qs - target) > 1.0)[0]
    settle = ts[outside[-1]] if len(outside) else 0
    print('  %-44s overshoot %4.1f deg   settled (within 1 deg) at %.3f s' % (label, peak, settle))

def trapezoid(vmax, amax, dist=90.0):
    """a smooth command: speed up at amax, cruise at vmax, slow down at amax"""
    ta = vmax / amax
    if amax * ta * ta > dist: ta = np.sqrt(dist / amax); vmax = amax * ta
    tc = (dist - amax * ta * ta) / vmax
    def f(t):
        if t < ta: return 0.5 * amax * t * t
        if t < ta + tc: return 0.5 * amax * ta * ta + vmax * (t - ta)
        if t < 2 * ta + tc: tt = 2 * ta + tc - t; return dist - 0.5 * amax * tt * tt
        return dist
    return f

def pan_dof(m): return m.jnt_dofadr[m.joint('pan').id]
def friction(nm):
    def e(m): m.dof_frictionloss[pan_dof(m)] = nm
    return e
def lighter(frac):
    def e(m):
        b = m.body('pan').id; m.body_mass[b] *= frac; m.body_inertia[b] *= frac
    return e
def smart(kv):
    def e(m):
        a = m.actuator('pan_servo').id
        m.actuator_biasprm[a, 2] = -kv          # position actuator bias = -kp*q - kv*qdot
    return e

print('pan, 0 -> 90 deg at the head (the MG90D through the 2:1 step-up); no gear play modelled')
run('today: jump the command straight to 90')
run('smooth command (400 deg/s, 4000 deg/s^2)', profile=trapezoid(400, 4000))
run('smooth command (600 deg/s, 8000 deg/s^2)', profile=trapezoid(600, 8000))
run('drag on the drum, 0.005 N.m (a felt pad)', edit=friction(0.005))
run('drag on the drum, 0.015 N.m', edit=friction(0.015))
run('cradle + drum half the weight', edit=lighter(0.5))
m = mujoco.MjModel.from_xml_path(XML); a = m.actuator('pan_servo').id
kp = m.actuator_gainprm[a, 0]
for kv in (kp * 0.004, kp * 0.008):
    run('"smart" servo that brakes (D gain %.2g)' % kv, edit=smart(kv))
