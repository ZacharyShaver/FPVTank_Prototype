"""Picture for the +Y sleeve hand-off (2026-10-03): out/print-rev2/plus_sleeve.png. Left, the section through the
tilt axis today; middle, the same with the hub as a sleeve; right, looking into the socket from +Y (Y 23.5):
the key's flat and the notch for the servo's gear bump. Real meshes, after fixes/plus_sleeve.py."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from vox import load_stl
from slices import slice2d

H = 52.0
O = os.path.join(config.OUT, 'plus-sleeve')
COL = {'ball': (0.29, 0.50, 0.76), 'cradle': (0.60, 0.64, 0.61), 'post': (0.85, 0.38, 0.17),
       'sleeve': (0.72, 0.20, 0.55), 'brg': (0.79, 0.64, 0.23)}


def obj(p):
    V, F = [], []
    for l in open(p):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('f '): F.append([int(x.split('/')[0]) - 1 for x in l.split()[1:4]])
    V = np.array(V); return V[np.array(F)]


def paint(ax, layers, lo, hi, axis, val, h=0.06):
    img = None
    for name, T in layers:
        m, u, v, _ = slice2d(T, axis, val, lo, hi, h)
        if img is None:
            img = np.ones(m.shape + (3,))
        img[m] = COL[name]
    ax.imshow(img.transpose(1, 0, 2), origin='lower', extent=(u[0], u[-1], v[0], v[-1]), interpolation='nearest')


if __name__ == '__main__':
    cradle = obj(os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'fusion', 'fork.obj'))
    post = load_stl(config.out('ball_servo_post_v3.stl'))
    now, new = load_stl(os.path.join(O, 'ball_plus_rev2.stl')), load_stl(os.path.join(O, 'ball_plus_sleeve.stl'))
    sl = load_stl(os.path.join(O, 'sleeve.stl'))
    brg = np.concatenate([load_stl(os.path.join(O, 'bearing_inner.stl')), load_stl(os.path.join(O, 'bearing_outer.stl'))])
    fig, axs = plt.subplots(1, 3, figsize=(18, 6.6), gridspec_kw={'width_ratios': [1, 1, 1.05]})
    lo, hi = (14.0, 30.0), (36.0, 74.0)
    paint(axs[0], [('cradle', cradle), ('post', post), ('brg', brg), ('ball', now)], lo, hi, 0, 0.0)
    axs[0].set_title('Today: the hub (blue, Y 24.5 -> 30.3) inside the collar.\nThe arm spreads ~5 mm to let it past',
                     fontsize=10)
    paint(axs[1], [('cradle', cradle), ('post', post), ('brg', brg), ('ball', new), ('sleeve', sl)], lo, hi, 0, 0.0)
    axs[1].set_title('Hub as a sleeve (pink), the 6704 pressed on up to its lip:\nin from outside after the ball, into a 1.5 mm socket in its face',
                     fontsize=10)
    for ax in axs[:2]:
        ax.axvline(24.5, color='k', lw=0.6, ls='--'); ax.text(24.3, 31, 'ball face\nY 24.5', ha='right', fontsize=8)
        ax.axvline(25.1, color='0.3', lw=0.6, ls=':'); ax.text(25.3, 31, 'collar\nY 25.1', ha='left', fontsize=8)
        ax.set_xlabel('Y (mm, + toward the post)'); ax.set_ylabel('Z (mm)')
    paint(axs[2], [('ball', new), ('sleeve', sl)], (-13.0, H - 13.0), (13.0, H + 13.0), 1, 23.5, h=0.04)
    axs[2].set_title('Into the socket from +Y, at Y 23.5: the flat (lens side, +X)\nkeys the sleeve so its notch meets the servo\'s gear bump',
                     fontsize=10)
    axs[2].annotate('key flat X 9.0', (9.0, H + 2.5), (3.0, H + 10.5), fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
    axs[2].annotate('notch r 8.9\n(gear bump)', (-8.6, H), (-12.5, H - 10.5), fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
    axs[2].set_xlabel('X (mm, + toward the lens)'); axs[2].set_ylabel('Z (mm)')
    fig.legend(handles=[Patch(color=COL[k], label=l) for k, l in (('ball', 'ball_plus'), ('sleeve', 'sleeve (new)'),
               ('cradle', 'cradle'), ('post', 'post v3'), ('brg', '6704'))], loc='lower center', ncol=5, fontsize=9)
    plt.tight_layout(rect=(0, 0.05, 1, 1))
    out = config.out('print-rev2', 'plus_sleeve.png')
    plt.savefig(out, dpi=85); print(out)
