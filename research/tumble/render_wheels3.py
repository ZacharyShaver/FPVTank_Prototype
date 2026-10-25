"""The wheels-in-flight study on one sheet: the Trainer off a step, forwards and in reverse (side-view filmstrips),
upright odds over step height x speed both ways, and the tuned in-flight controller against holding the throttle.

    python research/tumble/render_wheels3.py [--map]   # --map reruns the height x speed map (~3 min, 30 cores)
      -> research/results/wheels3/ledge_map.json, research/figures/wheels3_ledges.png
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, 'results', 'wheels3')
HS = [100, 150, 200, 300, 400, 500, 600]; VS = [0.2, 0.4, 0.7, 1.0, 1.4, 1.8]


def cell(a):
    import wheels3 as W3
    h, v, back = a
    c = W3.ledge_trials((h, v, None, 40, 3, W3.MOTOR, back))
    return a, c['upright'] / sum(c.values()), c.get('stuck', 0) / sum(c.values())


def film(h, v, back):
    import wheels3 as W3
    sim = W3.Sim(ledge=h); u0 = min(v / (W3.MOTOR['w0'] * 0.055), 1.0) * (-1 if back else 1); z = h * 1e-3 - sim.E[:, 2].min() + 0.0005
    yaw = np.pi if back else 0.0; q = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]); rec = []
    cls, _ = W3.run(sim, q, (-0.35, 0, z), np.array([v, 0, 0]), (0, 0, 0), lambda e, r: u0, drive=u0, hold=1.0, rec=rec, fall=h)
    return (cls if sim.landed else 'stuck'), rec, sim


if __name__ == '__main__':
    path = os.path.join(OUT, 'ledge_map.json')
    if '--map' in sys.argv or not os.path.exists(path):
        jobs = [(h, v, b) for h in HS for v in VS for b in (False, True)]
        with Pool(30) as pool:
            R = pool.map(cell, jobs, chunksize=1)
        json.dump(dict(hs=HS, vs=VS, n=40, cells=[dict(h=h, v=v, back=b, p=p, stuck=st) for (h, v, b), p, st in R]), open(path, 'w'))
    MAP = json.load(open(path))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull
    from scipy.spatial.transform import Rotation as Rot
    import pose3 as P3
    c = P3.C(); body = np.vstack([c['body']] + [c['pts'][k] for k in c['tyres']]) * 1e-3
    fig = plt.figure(figsize=(14, 13)); gs = fig.add_gridspec(4, 2, height_ratios=[0.8, 0.8, 0.8, 1.25], hspace=0.3, wspace=0.12)
    for row, (hh, vv, back) in enumerate(((300, 0.7, False), (300, 1.4, False), (300, 0.2, True))):
        ax = fig.add_subplot(gs[row, :]); cls, rec, sim = film(hh, vv, back)
        ts = [t for t, *_ in rec]; picks = np.linspace(0, len(rec) - 1, 10).astype(int)                 # the whole run, to rest
        for j, k in enumerate(picks):
            t, qp, u, _ = rec[k]; R = Rot.from_quat(np.r_[qp[4:7], qp[3]]).as_matrix(); P = body @ R.T + qp[:3]
            pr = P[:, [0, 2]]; h = ConvexHull(pr); v = pr[h.vertices]; a = 0.25 + 0.75 * j / (len(picks) - 1)
            ax.fill(*v.T, color='#2765c2' if not back else '#13824f', alpha=0.10 + 0.25 * a, lw=0); ax.plot(*np.vstack([v, v[:1]]).T, color='#1c2124', lw=0.6, alpha=a)
        ax.fill([-1.2, 0, 0, -1.2], [0, 0, hh / 1000, hh / 1000], color='#8d959c', alpha=0.5, lw=0); ax.axhline(0, color='#555', lw=1)
        ax.set_aspect('equal'); ax.set_xlim(-0.75, 1.35); ax.set_ylim(-0.05, 0.62); ax.axis('off')
        ax.set_title(f"{'Forwards' if not back else 'In reverse'} off a {hh // 10} cm step at {vv} m/s, throttle held: {'lands upside down' if cls == 'inverted' else 'lands on its wheels' if cls == 'upright' else 'hangs on the edge, belly down' if cls == 'stuck' else 'lands ' + cls}"
                     f"  (snapshots every {(picks[1] - picks[0]) * 10} ms)", fontsize=12, loc='left')
    for k, back in enumerate((False, True)):
        ax = fig.add_subplot(gs[3, k]); A = np.full((len(MAP['hs']), len(MAP['vs'])), np.nan); S_ = np.zeros_like(A)
        for e in MAP['cells']:
            if e['back'] == back: A[MAP['hs'].index(e['h']), MAP['vs'].index(e['v'])] = e['p']; S_[MAP['hs'].index(e['h']), MAP['vs'].index(e['v'])] = e.get('stuck', 0)
        im = ax.imshow(A, origin='lower', cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
        for i in range(A.shape[0]):
            for j in range(A.shape[1]):
                ax.text(j, i, f'{A[i, j]:.0%}' + (f'\n{S_[i, j]:.0%} stuck' if S_[i, j] > 0.01 else ''), ha='center', va='center', fontsize=8.5, color='#111')
        ax.set_xticks(range(len(MAP['vs']))); ax.set_xticklabels([f'{v}' for v in MAP['vs']]); ax.set_yticks(range(len(MAP['hs']))); ax.set_yticklabels(MAP['hs'])
        ax.set_xlabel('speed at the edge (m/s)'); ax.set_ylabel('step height (mm)')
        ax.set_title(f"{'Forwards' if not back else 'In reverse'}: gets down and lands on its wheels ({MAP['n']} runs a cell)", fontsize=12, loc='left')
    fig.suptitle('Trainer off a step: where it lands, by direction, height and speed (simulated)', fontsize=13, y=0.97)
    out = os.path.join(ROOT, 'figures', 'wheels3_ledges.png'); fig.savefig(out, dpi=105, bbox_inches='tight', facecolor='white'); print(out)
