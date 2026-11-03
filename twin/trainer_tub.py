"""The Trainer's tub (2026-11-03): the sim's own housing for the inside parts, printed as drawn, so the real parts show
where the sim is wrong. Every search design carries the Trainer's parts where this tub holds them (gauges/search.py
components()); the tub itself had never been printed.

    python twin/trainer_tub.py      # twin/out/print/trainer_tub.stl, picture twin/out/trainer_tub.png, checks, mesh report

The tub is chassis-v2/rugged.py's tub() with the wheels (SCORPION_LEGS=wheels, as trainer.py builds it), unchanged
except for two loose 52 x 3 x 2 ledges for the turret deck that float 4 mm over its top edge: they belong to the deck,
so they're left off. Inside it:
- the pack bays along both walls (26.5 wide), with 20 mm stops at each pack's and ESC's aft end;
- the tunnel down the middle of the belly, its roof the Pi's and PCA's shelf (the Pi on 5 mm TPU isolators*);
- the power bay at the back, the head base's four feet in the nose;
- the wheel pods' pads (four M3 inserts each).
The checks place Zach's parts where the sim does, his ESC at his caliper size (the sim's is 46 x 18 x 34*).
"""
import os, sys
os.environ['SCORPION_LEGS'] = 'wheels'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
sys.path[:0] = [os.path.join(config.REPO, 'chassis-v2'), config.TUMBLE, config.GAUGES, HERE]
import numpy as np
import cadquery as cq
import rugged as R
from boxes import box, render                      # superseded boxes.py's helpers

OUT = config.TWIN_OUT
PRINT = os.path.join(OUT, 'print')
ESC = (45.0, 24.0, 34.0)                           # Zach's caliper 2026-10-11 (L, tall, W), stood on edge: X, Y, Z
TO_BODY = np.array([-R.BODY_DX, R.YC, 0.0])        # the sim's parts (search frame) -> the tub's frame


def tub():
    """the tub as one solid; the floating deck ledges left off"""
    t = R.tub(); S = sorted(t.Solids(), key=lambda s: -s.Volume())
    return S[0], [s.Volume() for s in S[1:]]


def parts():
    """Zach's parts where the sim puts them, as boxes in the tub's frame: {name: (x0, x1, y0, y1, z0, z1)}"""
    import pose3 as P3
    c = P3.C()['pts']
    def bb(*ks):
        P = np.vstack([np.asarray(c[k], float) for k in ks]) + TO_BODY; lo, hi = P.min(0), P.max(0)
        return (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
    out = {k: bb(k) for k in ('pack_L', 'pack_R', 'pca')}
    out['pi_stack'] = bb('pi', 'hat', 'hailo')
    for s in ('L', 'R'):                               # his ESC: against its aft stop and the outer wall, on the bay floor
        x0, _, y0, y1, z0, _ = bb('esc_' + s)
        y = (y1 - ESC[1], y1) if s == 'L' else (y0, y0 + ESC[1])
        out['esc_' + s] = (x0, x0 + ESC[0], y[0], y[1], z0, z0 + ESC[2])
    return out


def checks(T, P):
    """each part touches nothing (zero); the controls must read > 0: moved toward what holds it, by more than the gap"""
    side = lambda k: 1 if k.endswith('_L') else -1
    rows = []
    for k, b in P.items():
        rows.append((f'{k} where the sim puts it', b, (0, 0, 0), '== 0'))
    for k in ('pack_L', 'pack_R'):
        rows.append((f'control: {k} 1.0 toward its wall', P[k], (0, side(k) * 1.0, 0), '> 0'))
    for k in ('esc_L', 'esc_R'):
        rows.append((f'control: {k} 4.0 inboard, into the tunnel', P[k], (0, -side(k) * 4.0, 0), '> 0'))
        rows.append((f'control: {k} 1.0 aft, into its stop', P[k], (-1.0, 0, 0), '> 0'))
    rows.append(('control: pi_stack 6 lower (no isolators)', P['pi_stack'], (0, 0, -6.0), '> 0'))
    rows.append(('control: pca 1.5 lower, into the roof', P['pca'], (0, 0, -1.5), '> 0'))
    ok = True
    for what, b, sh, want in rows:
        v = T.intersect(box(*b).translate(sh).val()).Volume()
        good = v < 1e-6 if want == '== 0' else v > 1e-3; ok &= good
        print(f'{"ok  " if good else "FAIL"} {what:44s} {v:9.3f} mm3 (want {want})')
    return ok


def gaps(T, P):
    """room round each part, for the README: to the tub along +-Y and over the tub's top"""
    for k, (x0, x1, y0, y1, z0, z1) in P.items():
        free = []
        for d, sg in (('Y-', -1), ('Y+', 1)):
            g = 0.0
            while g < 30 and T.intersect(box(x0, x1, y0, y1, z0 + 0.5, z1).translate((0, sg * (g + 0.25), 0)).val()).Volume() < 1e-6:
                g += 0.25
            free.append(f'{d} {g:.2f}' if g < 30 else f'{d} 30+')
        print(f'     {k:9s} room: {", ".join(free)}; top {z1:.1f} vs the tub top {R.TUB_TOP:.1f}')


def picture(T, P, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(16, 6.5), dpi=130, facecolor='#fcfcfb')
    items = [(T, (0.62, 0.70, 0.78), 1.0)] + [(box(*b).val(), (0.92, 0.41, 0.20), 0.55) for b in P.values()]
    render(axs[0], items, az=-55, el=32); render(axs[1], [items[0]], az=-55, el=60)
    bb = T.BoundingBox()
    axs[0].set_title("The Trainer's tub with your parts where the sim puts them (orange; your ESC at its real 45 x 24 x 34)",
                     fontsize=11, color='#0b0b0b', loc='left')
    axs[1].set_title(f'Empty, from higher: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm; nose (head) to the right',
                     fontsize=11, color='#0b0b0b', loc='left')
    fig.tight_layout(); fig.savefig(path, facecolor=fig.get_facecolor()); plt.close(fig)


def main():
    from cadquery import exporters
    import export
    os.makedirs(PRINT, exist_ok=True)
    T, dropped = tub(); P = parts()
    print(f'tub {T.BoundingBox().xlen:.1f} x {T.BoundingBox().ylen:.1f} x {T.BoundingBox().zlen:.1f}; left off: {len(dropped)} loose ledges {np.round(dropped, 0)} mm3')
    ok = checks(T, P); gaps(T, P)
    p = os.path.join(PRINT, 'trainer_tub.stl')
    bb = T.BoundingBox()
    exporters.export(cq.Workplane().add(T.translate(cq.Vector(0, 0, -bb.zmin))), p, tolerance=0.02, angularTolerance=0.1)
    good, msg = export.health(p); ok &= good
    print(f'{"ok  " if good else "FAIL"} mesh {os.path.basename(p)}: {msg}')
    picture(T, P, os.path.join(OUT, 'trainer_tub.png'))
    print('all checks pass' if ok else 'CHECKS FAILED')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
