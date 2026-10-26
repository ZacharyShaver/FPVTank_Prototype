"""EXPLORATORY (2026-10-25): the built step layout (chassis-v2, SCORPION_WHEELS=step) down steps, from its own meshes, against
the built four-wheel Trainer and chassis3's stand-in for the same layout. chassis3's step model, hard floor; the pods
(drop plates included) are their own convex geoms, so they can't bridge into a skid plate under the body.

    python research/tumble/built3.py   -> research/results/chassis3/built.json, chassis-v2/out/trainerstep_steps.png
"""
import os, sys, json, pickle, subprocess, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
CHASSIS = os.path.abspath(os.path.join(ROOT, '..', 'chassis-v2'))
sys.path.insert(0, HERE)
import chassis3 as C3

VARIANTS = {'Trainer (built)': '4', 'Step layout (built)': 'step'}


def cache(wheels):
    """the variant's parts, masses and wheel numbers, from a child (rugged fixes its legs at import)"""
    path = os.path.join(CHASSIS, 'out', f'_built_{wheels}.pkl')
    code = ("import sys, pickle; sys.path.insert(0, r'%s'); import rugged as R; R.CAGE = False; import wheels as W; "
            "M, it, O = R.assemble(); "
            "pickle.dump(dict(parts={k: dict(t=v['t'], grp=v.get('grp')) for k, v in M.items() if not v.get('ghost')}, items=it, "
            "ground=R.ground(M), yc=float(W.YC), R=W.R_T, axles=W.AXLES, y_w=(W.Y_IN + W.Y_OUT) / 2), open(r'%s', 'wb'))") % (CHASSIS, path)
    subprocess.run([sys.executable, '-c', code], env=dict(os.environ, SCORPION_LEGS='wheels', SCORPION_WHEELS=wheels), check=True, cwd=CHASSIS,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pickle.load(open(path, 'rb'))


def design(B):
    """a chassis3 design dict from built meshes: the body's hull without the wheel modules, each pod its own geom"""
    g0, yc = B['ground'], B['yc']; to = lambda t: t.reshape(-1, 3) - [0, yc, g0]
    mods = ('tire_', 'rim_', 'pod_', 'motor_')
    body = np.vstack([to(v['t']) for k, v in B['parts'].items() if not k.startswith(mods)]); body = body[ConvexHull(body).vertices]
    pods = [to(v['t']) for k, v in B['parts'].items() if k.startswith('pod_')]; pods = [p[ConvexHull(p).vertices] for p in pods]
    items = [(n, m, np.asarray(p, float) - [0, yc, g0]) for n, m, p in B['items'] if not n.startswith(('tire_', 'rim_'))]
    m_w = np.mean([m for n, m, _ in B['items'] if n.startswith(('tire_', 'rim_'))]) * 2
    R = B['R']; I_w = (m_w / 2 * (0.91 * R) ** 2 + m_w / 2 * (0.55 * R) ** 2) * 1e-9
    axles = {c + s: (x, sg * B['y_w']) for c, x in B['axles'].items() for s, sg in (('L', 1), ('R', -1))}
    box = {k: np.ptp(to(v['t']), 0) / 2 for k, v in B['parts'].items()}
    return dict(pts=body, extra=pods, items=items, box=box, R=R, m_w=m_w, I_w=I_w, axles=axles, ok=True, notes=[],
                length=float(np.ptp(np.vstack([body] + pods)[:, 0])), height=float(body[:, 2].max()), mass=float(sum(m for _, m, _ in B['items'])),
                belly=float(body[:, 2].min()), pod_low=float(min(p[:, 2].min() for p in pods)))


def job(a):
    name, cell, seed = a
    D = DES[name]; sim = C3.Sim(D, step=cell[0]); rng = np.random.default_rng(seed); c = {}
    for _ in range(20):
        yaw = np.radians(rng.uniform(-15, 15)) + (np.pi if cell[2] else 0.0)
        x0 = -C3.lead(D, cell[2]) * 1e-3 - rng.uniform(0.05, 0.15)
        r = sim.drive(x0, cell[0] * 1e-3 + 0.0005, yaw, cell[1] * rng.uniform(0.9, 1.1), cell[2], fall=0.4 * cell[0] * 1e-3)
        c[r] = c.get(r, 0) + 1
    return a, c


def _init(des):
    global DES
    DES = des


if __name__ == '__main__':
    t0 = time.time()
    des = {name: design(cache(w)) for name, w in VARIANTS.items()}
    des['Step layout (chassis3 stand-in)'] = C3.design(dict(R=46.0, xf=53.0, xr=-77.0, clr=54.0, dxp=0.0, dzp=0.0))
    for n, D in des.items():
        print(f"{n:34s} mass {D['mass']:.0f} g, length {D['length']:.0f}, belly {D.get('belly', D['pts'][:, 2].min()):.1f} mm, pods' lowest {D.get('pod_low', float('nan')):.1f} mm, axles {D['axles']}")
    jobs = [(n, c, 400 + i) for n in des for i, c in enumerate(C3.CELLS)]
    with Pool(30, initializer=_init, initargs=(des,)) as pool:
        R = pool.map(job, jobs, chunksize=1)
    out = {}
    for (n, c, _), r in R:
        out.setdefault(n, {})['|'.join(map(str, (c[0], c[1], int(c[2]))))] = r
    res = {n: dict(down=float(np.mean([v.get('upright', 0) / sum(v.values()) for v in cells.values()])),
                   stuck=float(np.mean([v.get('stuck', 0) / sum(v.values()) for v in cells.values()])), cells=cells,
                   mass=des[n]['mass'], length=des[n]['length']) for n, cells in out.items()}
    json.dump(dict(wall_s=round(time.time() - t0), runs_per_cell=20, contact=C3.CONTACT, results=res), open(os.path.join(ROOT, 'results', 'chassis3', 'built.json'), 'w'), indent=1)
    for n, r in res.items():
        print(f"{n:34s} down a step {r['down']:.3f}  stuck {r['stuck']:.3f}")
    # the page's figure: the built Trainer against the built step layout
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    HS, VS = (100, 200, 300, 400), (0.3, 0.6, 1.0, 1.4)
    fig, axs = plt.subplots(2, 2, figsize=(11, 8)); fig.subplots_adjust(hspace=0.35, wspace=0.2)
    for i, n in enumerate(('Trainer (built)', 'Step layout (built)')):
        for j, back in enumerate((False, True)):
            ax = axs[i, j]; A = np.array([[res[n]['cells'][f'{h}|{v}|{int(back)}'].get('upright', 0) / 20 for v in VS] for h in HS])
            ax.imshow(A, origin='lower', cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
            for a in range(len(HS)):
                for b in range(len(VS)):
                    ax.text(b, a, f'{A[a, b]:.0%}', ha='center', va='center', fontsize=10)
            ax.set_xticks(range(4)); ax.set_xticklabels(VS); ax.set_yticks(range(4)); ax.set_yticklabels(HS)
            ax.set_title(f"{n.split(' (')[0]}, {'in reverse' if back else 'forwards'}: down {res[n]['down']:.0%} overall" if j == 0 else f"{'in reverse' if back else 'forwards'}", loc='left', fontsize=11)
            ax.set_xlabel('speed at the edge (m/s)'); ax.set_ylabel('step down (mm)')
    fig.suptitle('Down a step and onto its wheels (simulated, 20 runs a cell, hard floor)', fontsize=12)
    out_png = os.path.join(CHASSIS, 'out', 'trainerstep_steps.png'); fig.savefig(out_png, dpi=100, bbox_inches='tight', facecolor='white'); print(out_png)
    print(f'{time.time() - t0:.0f} s')
