"""Audit (2026-10-14): time-step convergence, the settle rule, and a knock after settling (E1 mass low, fixed starts).
See AUDIT.md.    python research/tumble/audit/audit_conv.py"""
import os, sys, numpy as np, mujoco
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import audit_sim as A, tumble as T, scale_model as S

def run(args):
    name, high, att, timestep, solref, settle_steps, kick, n = args
    m, d, Ps, com = A.model(name, high, timestep=timestep, solref=solref)
    roll, pitch = S.ATTITUDES[att]; rng = np.random.default_rng(7); cnt = {}
    chk = int(round(0.02 / timestep))                      # check every 20 ms, as predict does
    for _ in range(n):
        r = np.radians(roll + rng.normal(0, 7.5)); pt = np.radians(pitch + rng.normal(0, 7.5)); yw = rng.uniform(0, 2 * np.pi)
        q0 = np.zeros(4); mujoco.mju_euler2Quat(q0, np.array([r, pt, 0.0]), 'xyz'); q = np.zeros(4)
        mujoco.mju_mulQuat(q, np.array([np.cos(yw / 2), 0, 0, np.sin(yw / 2)]), q0)
        R9 = np.zeros(9); mujoco.mju_quat2Mat(R9, q); R = R9.reshape(3, 3)
        mujoco.mj_resetData(m, d); d.qpos[:3] = (0, 0, 0.06 - (Ps @ R.T)[:, 2].min()); d.qpos[3:7] = q
        still = 0
        for _ in range(240 * 4):
            mujoco.mj_step(m, d, nstep=chk)
            if np.abs(d.qvel).max() < 0.01:
                still += 1
                if still >= settle_steps: break
            else: still = 0
        if kick:                                           # a small knock: does it stay?
            d.qvel[3:6] += rng.normal(0, kick, 3); still = 0
            for _ in range(240 * 4):
                mujoco.mj_step(m, d, nstep=chk)
                if np.abs(d.qvel).max() < 0.01:
                    still += 1
                    if still >= settle_steps: break
                else: still = 0
        c = T.classify(d.xmat[1].reshape(3, 3)); cnt[c] = cnt.get(c, 0) + 1
    return args[:7], {k: v / n for k, v in sorted(cnt.items())}

if __name__ == '__main__':
    base = ('E1_tub', False)
    jobs = []
    for att in ('nose down', 'left side down'):
        for ts in (0.001, 0.0005, 0.00025):
            jobs.append(base + (att, ts, None, 6, 0.0, 200))
        jobs.append(base + (att, 0.0005, None, 25, 0.0, 200))      # 0.5 s still
        jobs.append(base + (att, 0.0005, None, 6, 0.3, 200))       # then a 0.3 rad/s knock
    with Pool(10) as p:
        for k, v in p.map(run, jobs):
            print(f'{k[2]:<16} dt {k[3]:<8} settle {k[5]*20:>3} ms  kick {k[6]}:  ' + ', '.join(f'{c} {x:.2f}' for c, x in v.items()))
