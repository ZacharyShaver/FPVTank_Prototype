"""A picture of the one-body rules (2026-10-28): three designs as the first capability run built them and as strict
builds them, in 3D: a bare-tub six-wheeler whose wheels floated (the body grown to them), T3 with a push plate that
hung in front of its nose (faired in), and the six-wheel hill champion, whose middle tyres sat inside its skin (wells cut).

    python gauges/cohere_sheet.py   -> gauges/out/cohere/cohere_sheet.png
"""
import os, sys, math
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import ConvexHull
import knobs as K, robots as RB

OUT = os.path.join(config.GAUGES_OUT, 'cohere')
SKIN, PLATE, TYRE, TAIL = (0.86, 0.62, 0.55), (0.55, 0.58, 0.62), (0.16, 0.17, 0.19), (0.45, 0.30, 0.15)


def wells(P, sp):
    V, T = RB.with_wells(P, sp, tol=0.3); return V[T]


def hull_tris(P):
    P = np.asarray(P, float); return P[ConvexHull(P).simplices]


def tyre_tris(x, y, R, TW, n=28):
    a = np.linspace(0, 2 * np.pi, n + 1); c = np.c_[x + R * np.cos(a), R + R * np.sin(a)]; out = []
    for i in range(n):
        for (y0, y1) in ((y - TW / 2, y + TW / 2),):
            p, q = c[i], c[i + 1]
            out.append([[p[0], y0, p[1]], [q[0], y0, q[1]], [q[0], y1, q[1]], [p[0], y1, p[1]]])
        for yy in (y - TW / 2, y + TW / 2):
            out.append([[x, yy, R], [p[0], yy, p[1]], [q[0], yy, q[1]]])
    return out


def draw(ax, sp, cut, title):
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    def add(T, col, alpha=1.0):
        T = [np.asarray(t, float) for t in T]; sh = []
        for t in T:
            n = np.cross(t[1] - t[0], t[2] - t[0]); nn = np.linalg.norm(n); sh.append(0.55 + 0.45 * abs(n @ light) / nn if nn > 0 else 0.8)
        pc = Poly3DCollection([t[:, [0, 1, 2]] for t in T], facecolors=[tuple(np.clip(np.array(col) * s, 0, 1)) for s in sh], edgecolors='none', alpha=alpha)
        ax.add_collection3d(pc)
    hs = sp['hulls']
    add(wells(hs[0], sp) if cut else hull_tris(hs[0]), SKIN)
    for h in hs[1:]:
        add(hull_tris(h), PLATE)
    for x, y in sp['wheels']:
        add(tyre_tris(x, y, sp['R'], sp['TW']), TYRE)
    lm = sp.get('limb')
    if lm:
        P = RB.limb_points(lm, 0.0, lm['th_stow']); ax.plot(P[:8, 0], P[:8, 1], P[:8, 2], color=TAIL, lw=3)
    E = np.vstack(list(sp['hulls']) + [np.c_[np.array(sp['wheels']), np.full(len(sp['wheels']), sp['R'])]]); lo, hi = E.min(0), E.max(0); c = (lo + hi) / 2; r = 0.55 * (hi - lo).max()
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(0, 2 * r)
    ax.view_init(elev=22, azim=-58); ax.set_box_aspect((1, 1, 1), zoom=1.3); ax.set_axis_off(); ax.set_title(title, fontsize=10, loc='left')


def main():
    os.makedirs(OUT, exist_ok=True)
    import capability as CA
    ok = CA.ranks(CA.load()); best = max(ok, key=lambda r: CA.score(r, 'h_up'))
    tub6 = max((r for r in ok if r['wheels'] == 6 and r['q']['shell'] < 0.5), key=lambda r: CA.score(r, 'up'))
    rows = [('Bare-tub six-wheeler (best upright, first run)', CA.q_of(tub6['z']), False),
            ('T3 with a push plate topping at 100 mm', dict(K.T3, bumper=100.0), False),
            ('Six-wheel hill champion (skin)', CA.q_of(best['z']), True)]
    fig = plt.figure(figsize=(10, 12)); fig.patch.set_facecolor('white')
    for i, (name, q, wl) in enumerate(rows):
        a, b = K.make(q), K.make(q, strict=True)
        pr = K.problems(q, a); pa = (pr[0] + (f' (+{len(pr) - 1} more)' if len(pr) > 1 else '')) if pr else 'every part on the body'
        draw(fig.add_subplot(3, 2, 2 * i + 1, projection='3d'), a, False, f'{name}\nfirst run: {pa}')
        nb = [n for n in b['notes'] if 'grown' in n or 'faired' in n]
        draw(fig.add_subplot(3, 2, 2 * i + 2, projection='3d'), b, True, f"strict: {'; '.join(nb) or 'body as it was'}\nwells cut; {b['mass'] - a['mass']:+.0f} g")
    fig.suptitle('One body: parts off the body grow it, the push plate is faired in, every tyre gets a 5 mm well', fontsize=12, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.97)); p = os.path.join(OUT, 'cohere_sheet.png'); plt.savefig(p, dpi=110); print(p)


def samples(n=14, seed=None):
    """T3 and n designs drawn at random (uniform) over the strict run's space, each built strict, wells cut; a refused
    one drawn as sampled, with why -> out/cohere/samples.png (the seed is printed, to draw the same again)"""
    os.environ['SCORPION_CAP'] = 'capability_strict'
    import capability as CA
    seed = int(np.random.SeedSequence().entropy % 100000) if seed is None else seed; print('seed', seed)
    Z = np.random.default_rng(seed).random((n, len(CA.KEYS)))
    rows = [('T3 (reference)', dict(K.T3))] + [(f'Sample {i + 1}', CA.q_of(z)) for i, z in enumerate(Z)]
    cols = 3; fig = plt.figure(figsize=(12, 4 * math.ceil(len(rows) / cols))); fig.patch.set_facecolor('white')
    for i, (name, q) in enumerate(rows):
        ax = fig.add_subplot(math.ceil(len(rows) / cols), cols, i + 1, projection='3d')
        sp = K.make(q, strict=True)
        if sp is None:
            a = K.make(q)
            if a is None:
                ax.set_axis_off(); ax.set_title(f'{name}: not buildable (tyres overlap)', fontsize=9, loc='left'); continue
            why = K.problems(q, K._cohere(q, a)) or ['not built']
            draw(ax, a, False, f'{name}: REFUSED\n{why[0][:46]}'); continue
        kind = f"{len(sp['wheels'])} wheels, {'skin' if q['shell'] > 0.5 else 'tub'}{', tail' if sp.get('limb') else ''}"
        fix = [('wheels in' if 'in to the body' in s else 'grown' if 'grown' in s else 'plate faired' if 'faired' in s else 'mount moved')
               for s in sp['notes'] if any(w in s for w in ('in to the body', 'grown', 'faired', 'tail mount moved'))]
        draw(ax, sp, True, f"{name}: {kind}\nR {sp['R']:.0f}, {sp['mass'] / 1000:.1f} kg{'; ' + ', '.join(fix) if fix else ''}")
    fig.suptitle(f'A random sample of the strict search space (seed {seed}): built as one body, wells cut', fontsize=13, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.98)); p = os.path.join(OUT, 'samples.png'); plt.savefig(p, dpi=90); print(p)


if __name__ == '__main__':
    samples(seed=int(sys.argv[2]) if len(sys.argv) > 2 else None) if 'samples' in sys.argv[1:] else main()
