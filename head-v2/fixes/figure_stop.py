"""Old pin vs pin-with-stop, seated in the test block, cut through the pin's axis."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from slices import slice2d
from probe import load_stl
from snap import SOCKET_DEPTH, NOSE_R

GREY, BLUE = np.array([0.72, 0.72, 0.74]), np.array([0.2, 0.4, 0.9])
blk = load_stl(config.out('_fig_block.stl'))
pins = [('First pin: after the click it can still slide 0.75 mm deeper', load_stl(config.out('_fig_pin_old.stl'))),
        ('Pin with stop: the round nose reaches the end of the hole', load_stl(config.out('_fig_pin_new.stl')))]
fig, axs = plt.subplots(1, 2, figsize=(15, 7.2))
for ax, (title, T) in zip(axs, pins):
    lo, hi = (-5.5, -4.0), (5.5, 15.5)
    mb, u, v, _ = slice2d(blk, 2, 0.0, lo, hi, 0.02)
    mp, _, _, _ = slice2d(T, 2, 0.0, lo, hi, 0.02)
    img = np.ones(mb.shape + (3,)); img[mb] = GREY; img[mp] = BLUE
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(u[0], u[-1], v[0], v[-1]), interpolation='nearest')
    ax.axhline(0, color='k', lw=0.8, ls=':')
    ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.4); ax.tick_params(labelsize=8)
    ax.set_title(title, fontsize=11, weight='bold', loc='left')
    ax.set_xlabel('mm', fontsize=8); ax.set_ylabel('depth into the part, mm (seam face = dotted line)', fontsize=8)
    tip = T.reshape(-1, 3)[:, 1].max()
    cone_at_tip = SOCKET_DEPTH - (NOSE_R if 'stop' in title else 2.05)
    gap = cone_at_tip - tip
    ax.annotate('gap to the end of the hole: %.2f mm' % gap, xy=(1.6, tip), xytext=(2.3, 14.6), fontsize=9,
                color='k', arrowprops=dict(arrowstyle='->'))
    ax.text(-5.3, -3.6, 'grey = test block (same hole as the ball)    blue = pin', fontsize=8)
fig.text(0.01, 0.01, 'Both drawn seated. First pin: its tip stops 0.85 mm short of the end of the hole, so after the click a push '
         'slides it about 0.75 mm further. With the stop: 0.05 mm, and a harder push only squeezes the split ends, which spring it back.',
         fontsize=9)
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.savefig(config.out('pin_stop.png'), dpi=80)
print('ok')
