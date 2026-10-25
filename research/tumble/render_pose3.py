"""The drop-pose lab's poses on one sheet: the Trainer with guard arm E held in each pose (the real arm meshes), and
where 2000 simulated drops of each came to rest.

    python research/tumble/render_pose3.py  -> research/figures/pose3_poses.png
"""
import os, sys, json
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import pose3 as P3

D = json.load(open(os.path.join(ROOT, 'results', 'pose3', 'search.json')))
B, F = D['baselines'], D['finalists']
ROWS = [('No arm (base only)', None, B['no arm (base only)']['counts']), ('Guard (stowed arch)', B['guard (stowed arch)']['q'], B['guard (stowed arch)']['counts']),
        ('Straight up', B['straight up']['q'], B['straight up']['counts']), ('Best: folded back over the tail, forearm up', F[0]['q'], F[0]['robot_counts_2000']),
        ('Runner-up: reaching out to the left', F[1]['q'], F[1]['robot_counts_2000'])]
CAT = [('upright', ('upright',), '#13824f'), ('upside down', ('inverted',), '#b9661a'), ('on a side', ('left side', 'right side'), '#2765c2'),
       ('on an end', ('nose up', 'nose down'), '#8a6fb0')]


def body_tris():
    c = P3.C(); out = []
    for k, p in c['pts'].items():
        if len(p) < 4: continue
        try:
            h = ConvexHull(p); out.append((k, p[h.simplices]))
        except Exception:
            pass
    return out


def draw(ax, q, BT):
    L = np.array([0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
    def add(tri, rgb, a=1.0):
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        s = 0.5 + 0.5 * np.abs(n @ L); ax.add_collection3d(Poly3DCollection(tri, facecolors=np.clip(np.array(rgb)[None] * s[:, None], 0, 1), edgecolor='none', alpha=a))
    for k, tri in BT:
        if k.startswith('armbase_'): continue
        add(tri, (0.17, 0.18, 0.2) if k.startswith('tire_') else (0.62, 0.64, 0.66) if not k.startswith(('ball', 'base', 'drum', 'cradle')) else (0.78, 0.45, 0.22), 0.9)
    if q is not None:
        GA = P3.C()['GA']; t = GA.arm_tris(q) - [0, P3.C()['yc'], 0]; add(t.reshape(-1, 3, 3), (0.08, 0.55, 0.32))
        tb = GA.base_tris(q[0]) - [0, P3.C()['yc'], 0]; add(tb.reshape(-1, 3, 3), (0.08, 0.45, 0.28))
    ax.set_xlim(-230, 230); ax.set_ylim(-230, 230); ax.set_zlim(-25, 420); ax.set_box_aspect((460, 460, 445), zoom=1.75); ax.view_init(20, -55); ax.axis('off')


if __name__ == '__main__':
    BT = body_tris(); n = len(ROWS)
    fig = plt.figure(figsize=(13, 2.7 * n)); gs = fig.add_gridspec(n, 2, width_ratios=[1, 1.6], wspace=0.05, hspace=0.12)
    for i, (title, q, cnt) in enumerate(ROWS):
        draw(fig.add_subplot(gs[i, 0], projection='3d'), q, BT)
        ax = fig.add_subplot(gs[i, 1]); tot = sum(cnt.values()); x0 = 0.0
        for lab, ks, col in CAT:
            v = sum(cnt[k] for k in ks) / tot
            ax.barh(0, v, left=x0, color=col, height=0.5)
            if v > 0.06: ax.text(x0 + v / 2, 0, f'{lab}\n{v:.0%}', ha='center', va='center', color='white', fontsize=9.5, weight='bold')
            x0 += v
        ax.set_xlim(0, 1); ax.set_ylim(-0.6, 1.15); ax.axis('off')
        ax.text(0, 0.95, title, fontsize=12, weight='bold', va='center')
        ax.text(0, 0.62, f"upright {cnt['upright'] / tot:.3f}  ({tot} drops)" + ('' if q is None else f"   arm yaw {q[0]:.0f}, shoulder {q[1]:.0f}, elbow {q[2]:.0f}, wrist {q[3]:.0f} deg"),
                fontsize=9.5, ha='left', va='center', color='#444')
    fig.suptitle('Trainer + guard arm E: where it lands, by the pose the arm holds through the fall (simulated)', fontsize=13, y=0.93)
    out = os.path.join(ROOT, 'figures', 'pose3_poses.png'); fig.savefig(out, dpi=105, bbox_inches='tight', facecolor='white'); print(out)
