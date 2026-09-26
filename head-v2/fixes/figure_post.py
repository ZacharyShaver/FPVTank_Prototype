"""Cut along the tilt axis: cradle collar, bearing, post, ball hub, servo. Your post (pressed on) vs v3 (screw tight)."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from slices import slice2d
from probe import load_stl
from kit import B
from post3 import FACE, LIP0, LIP1, TOP

H = B.H
GREY, LIGHT, BLUE = np.array([0.55, 0.55, 0.58]), np.array([0.80, 0.80, 0.83]), np.array([0.2, 0.4, 0.9])
BP = load_stl(config.out('BODY_NUMBA1_snap.stl'))
POSTS = [('Your post, pressed on: it pushes the ball 0.6 mm away', load_stl(config.zach('post')), -0.60, 27.5),
         ('New post, centre screw tight: the ball sits centred', load_stl(config.out('ball_servo_post_v3.stl')), 0.0, FACE)]
lo, hi, h = (16.0, 30.0), (38.0, 74.0), 0.03
ys = np.arange(lo[0], hi[0], h); zs = np.arange(lo[1], hi[1], h)
Y, Z = np.meshgrid(ys, zs, indexing='ij')
fork = B.fork((np.zeros_like(Y), Y, Z)) < 0

fig, axs = plt.subplots(1, 2, figsize=(16, 8.4))
for ax, (title, T, off, face) in zip(axs, POSTS):
    img = np.ones(Y.shape + (3,))
    img[fork] = GREY
    mb, _, _, _ = slice2d(BP - [0, -off, 0], 0, 0.0, lo, hi, h)      # the ball, shifted along the axis
    img[mb] = LIGHT
    mp, _, _, _ = slice2d(T, 0, 0.0, lo, hi, h)
    img[mp] = BLUE
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(lo[0], hi[0] - h, lo[1], hi[1] - h), interpolation='nearest')
    for zc in (H + 10.0, H - 13.5):                                     # the 6704 bearing (ring), cut
        ax.add_patch(Rectangle((B.BRG_P_Y0, zc), B.BRG_W, 3.5, fc=(0.3, 0.3, 0.3), ec='k', lw=0.6, hatch='///'))
    top = TOP + off                                                     # the servo moves with the ball
    ax.add_patch(Rectangle((lo[0], H - 6.1), top - lo[0], 12.2, fc=(0.95, 0.6, 0.2, 0.35), ec=(0.8, 0.4, 0.0), lw=1.0))
    ax.add_patch(Rectangle((top, H - 3.45), B.BOSS_H, 6.9, fc=(0.95, 0.6, 0.2, 0.7), ec=(0.8, 0.4, 0.0), lw=1.0))
    ax.add_patch(Rectangle((top + B.BOSS_H, H - 2.4), B.SPLINE_PROUD, 4.8, fc=(0.6, 0.3, 0.0), ec='k', lw=0.8))
    tip = top + B.SPLINE_STACK
    engaged = tip - face
    ax.annotate('', xy=(face, H + 3.2), xytext=(tip, H + 3.2), arrowprops=dict(arrowstyle='<->', color='k'))
    ax.text((face + tip) / 2, H + 3.7, '%.1f mm of spline\ninside the post' % engaged, ha='center', fontsize=10, weight='bold')
    ax.annotate('', xy=(top + B.BOSS_H, H - 4.2), xytext=(face, H - 4.2), arrowprops=dict(arrowstyle='<->', color=(0.8, 0.4, 0.0)))
    ax.annotate("gap from the post's end to\nthe servo's black head: %.1f mm" % (face - top - B.BOSS_H),
                xy=((top + B.BOSS_H + face) / 2, H - 4.2), xytext=(16.4, 33.0), fontsize=9, color=(0.7, 0.3, 0.0),
                arrowprops=dict(arrowstyle='->', color=(0.7, 0.3, 0.0)))
    ax.set_title(title, fontsize=11, weight='bold', loc='left')
    ax.set_xlabel('Y along the tilt axis (toward the post ->)', fontsize=8); ax.set_ylabel('Z', fontsize=8)
    ax.set_aspect('equal'); ax.tick_params(labelsize=7)
fig.text(0.01, 0.012, "dark grey = cradle collar    hatched = 6704 bearing    light grey = ball    blue = post    "
         "orange = servo case and its black head, brown = the metal spline.\n"
         "Right: the servo's centre screw goes down the middle of the post into the spline and pulls its tip onto the stop plate.", fontsize=9)
plt.tight_layout(rect=(0, 0.06, 1, 1))
plt.savefig(config.out('post_reach.png'), dpi=80)
print('ok')
