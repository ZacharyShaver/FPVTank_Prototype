"""Rev 2 sheet: why the screws jammed, the pin, where the pins go, the plugged holes, the test piece."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle
from slices import slice2d
from probe import load_stl
from kit import B
from build_snap import REAR, FRONT, POST_R
from snap import PIN_R, BARBS, S_B, SLOT_W, SLOT_FROM, NOSE_R, S_NOSE
from zr import zrender
from PIL import Image
H = B.H
GREY, RED, GREEN, BLUE = (np.array([0.72, 0.72, 0.74]), np.array([0.86, 0.16, 0.16]),
                          np.array([0.13, 0.62, 0.25]), np.array([0.2, 0.4, 0.9]))
P0, P1 = load_stl(config.zach('ball_plus')), load_stl(config.out('BODY_NUMBA1_snap.stl'))
M0, M1 = load_stl(config.zach('ball_minus')), load_stl(config.out('ball_minus_revised_snap.stl'))
PIN = load_stl(config.out('snap_pin_stop_medium.stl'))


def diff_img(pairs, axis, val, lo, hi, h, extra=None):
    img = None
    for T0, T1 in pairs:
        m0, u, v, _ = slice2d(T0, axis, val, lo, hi, h)
        m1, _, _, _ = slice2d(T1, axis, val, lo, hi, h)
        if img is None:
            img = np.ones(m0.shape + (3,))
        img[m0 & m1] = GREY
        img[m0 & ~m1] = RED
        img[m1 & ~m0] = GREEN
    if extra is not None:
        for T, col in extra:
            m, _, _, _ = slice2d(T, axis, val, lo, hi, h)
            img[m] = col
    return img, u, v


def show(ax, img, u, v, xl, yl):
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(u[0], u[-1], v[0], v[-1]), interpolation='nearest')
    ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.4); ax.tick_params(labelsize=7)
    ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8)


fig, axs = plt.subplots(2, 3, figsize=(21, 13.5))

# 1. why the screws jam: the plane through the lower rear post's axis and the ball's centre
ax = axs[0, 0]
rho0 = np.hypot(REAR[0][0], REAR[0][1] - H)                     # 24.7 from the centre
rr, yy = np.meshgrid(np.linspace(14, 36, 900), np.linspace(-2, 26, 1100), indexing='ij')
d = np.hypot(rr, yy)
ball = (d <= B.R_BALL) & ((d >= B.R_IN - 1.2) | (np.abs(rr - rho0) <= POST_R)) & (yy >= 0)
recess = (np.abs(rr - rho0) <= 3.0) & (yy >= 16.03)
hole = np.abs(rr - rho0) <= 1.7
img = np.ones(rr.shape + (3,)); img[ball & ~recess & ~hole] = GREY
ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(14, 36, -2, 26), interpolation='nearest')
th = np.linspace(0, np.pi / 2, 300)
ax.plot(B.R_BALL * np.cos(th), B.R_BALL * np.sin(th), 'k', lw=0.8)
ax.plot((B.R_BALL + B.BALL_CLEAR) * np.cos(th), (B.R_BALL + B.BALL_CLEAR) * np.sin(th), color='darkorange', ls='--', lw=1.6)
hy, hh, hr = 16.03, 2.1, 2.75
ax.add_patch(Rectangle((rho0 - 1.5, -2), 3.0, hy + 2, fc=(0.35, 0.35, 0.4), ec='k', lw=0.6))
ax.add_patch(Rectangle((rho0 - hr, hy), 2 * hr, hh, fc=RED, ec='k', lw=0.6))
cx, cy = rho0 + hr, hy + hh
past_ball = np.hypot(cx, cy) - B.R_BALL
ax.annotate('screw head edge: %.1f mm past the ball,\n%.1f mm past where the nest starts' % (past_ball, past_ball - B.BALL_CLEAR),
            xy=(cx, cy), xytext=(15, 23.0), fontsize=8, color=RED, arrowprops=dict(arrowstyle='->', color=RED))
ax.text(29.8, 2.0, 'ball', fontsize=8)
ax.text(31.7, 6.8, 'nest\n(1.5 mm out)', color='darkorange', fontsize=8)
ax.text(15, -1.5, 'M3 pan head in the old pocket, lower rear post', fontsize=8)
ax.set_xlim(14, 36); ax.set_ylim(-2, 26); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
ax.set_xlabel("distance from the ball's centre, out through the post", fontsize=8)
ax.set_ylabel('Y (toward the post side)', fontsize=8)
ax.set_title('1. Why the screws jammed: the ball curves away under the head', fontsize=11, weight='bold', loc='left')

# 2. a pin, seated, cut through its middle (plane Z 43, the lower rear post)
ax = axs[0, 1]
x0, z0 = REAR[0]
bb = PIN.reshape(-1, 3); c = (bb.min(0) + bb.max(0)) / 2
Tpin = PIN - [c[0], c[1], 0] - [0, 0, 1.8] + [x0, 0, z0]       # print frame -> seated at the post
img, u, v = diff_img([(P0, P1), (M0, M1)], 2, z0, (x0 - 6.5, -15), (x0 + 6.5, 15), 0.02, extra=[(Tpin, BLUE)])
show(ax, img, u, v, 'X', 'Y  (seam at 0; ball_plus above, ball_minus below)')
ax.axhline(0, color='k', lw=0.6, ls=':')
ax.set_title('2. A pin seated across the seam (cut through the pin)', fontsize=11, weight='bold', loc='left')
ax.text(x0 + 3.2, 10.5, 'blue = pin\ngreen = old screw\nhole plugged\nred = socket cut', fontsize=8)
ax.text(x0 - 6.2, 8.9, 'barb springs\nout here', fontsize=8, color=BLUE)

# 3. where the three pins go: ball_plus seam face, seen from the seam
ax = axs[0, 2]
m, u, v, _ = slice2d(P1, 1, 0.3, (-32, 20), (32, 84), 0.05)
img = np.ones(m.shape + (3,)); img[m] = GREY
show(ax, img, u, v, 'X  (toward the lens ->)', 'Z  (up)')
for i, (x, z) in enumerate(REAR + [FRONT]):
    ax.add_patch(Circle((x, z), 6.0, fill=False, ec=BLUE, lw=1.6))
    ax.text(x + 6.5, z + 1.5, 'pin %d' % (i + 1), color=BLUE, fontsize=9, weight='bold')
ax.text(-30, 22, 'the lower two posts are yours (screws out, pins in);\n'
                 'the top one is new: above the servo box, behind the board', fontsize=8)
ax.set_title('3. Where the 3 pins go (seam face of ball_plus)', fontsize=11, weight='bold', loc='left')

# 4. the old holes, plugged: plane X -23 through both rear posts, both halves
ax = axs[1, 0]
img, u, v = diff_img([(P0, P1), (M0, M1)], 0, -23.0, (-21, 34), (21, 70), 0.03)
show(ax, img, u, v, 'Y  (seam at 0)', 'Z  (up)')
ax.axvline(0, color='k', lw=0.6, ls=':')
ax.set_title('4. Old screw holes plugged, sockets cut (both halves)', fontsize=11, weight='bold', loc='left')
ax.text(-20, 68.3, 'ball_minus', fontsize=8)
ax.text(1, 68.3, 'ball_plus', fontsize=8)
ax.text(-20, 35.5, 'green = plug (the head pocket is gone: nothing\n'
                   'can stand proud of the ball now)\nred = the socket, 12.5 deep each side', fontsize=8)

# 5. the pin as printed, and the test piece
ax = axs[1, 1]
im1 = zrender([(PIN, (80, 110, 220))], -35, 35, 460, 'pin, as printed: lying on its flat', ext=11)
TB = load_stl(config.out('snap_test_block.stl'))
im2 = zrender([(TB, (200, 200, 205))], -35, 25, 460, 'test block (print 2): socket opening on the bed', ext=11)
W = Image.new('RGB', (920, 460), 'white'); W.paste(im1, (0, 0)); W.paste(im2, (460, 0))
ax.imshow(W); ax.set_axis_off()
ax.set_title('5. Print these first: 2 test blocks + one pin of each size', fontsize=11, weight='bold', loc='left')

# 6. the pin's shape with sizes (the pin with the stop: a round nose at each end)
ax = axs[1, 2]
br = BARBS['medium']
land = S_B + (br - PIN_R)
lh = S_NOSE
prof = [(0, PIN_R), (S_B, PIN_R), (land, br), (land + 0.6, br), (land + 0.6 + (br - NOSE_R), NOSE_R), (lh, NOSE_R)]
outline = ([(-x, y) for x, y in prof[::-1]] + prof + [(x, -y) for x, y in prof[::-1]] + [(-x, -y) for x, y in prof])
ax.add_patch(Polygon(outline, closed=True, fc=(0.2, 0.4, 0.9, 0.25), ec=BLUE, lw=1.2))
ax.add_patch(Rectangle((SLOT_FROM, -SLOT_W / 2), lh + 0.2 - SLOT_FROM, SLOT_W, fc='white', ec=BLUE, lw=0.8))
ax.add_patch(Rectangle((-lh - 0.2, -SLOT_W / 2), lh + 0.2 - SLOT_FROM, SLOT_W, fc='white', ec=BLUE, lw=0.8))
ax.axvline(0, color='k', lw=0.6, ls=':')
ax.set_xlim(-11, 11); ax.set_ylim(-5, 5); ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.4); ax.tick_params(labelsize=7)
ax.text(-10.5, 3.9, 'length %.1f, body %.1f across, barbs %.2f / %.2f / %.2f (soft / medium / firm)'
        % (2 * lh, 2 * PIN_R, 2 * BARBS['soft'], 2 * BARBS['medium'], 2 * BARBS['firm']), fontsize=8)
ax.text(-10.5, -4.6, "the slot lets each end squeeze 0.25 mm through the socket's neck, then spring back", fontsize=8)
ax.set_title('6. The pin, from above (seam = dotted line)', fontsize=11, weight='bold', loc='left')

fig.text(0.01, 0.005, 'grey = your part, unchanged    RED = removed    GREEN = added    BLUE = snap pin', fontsize=10)
plt.tight_layout(rect=(0, 0.015, 1, 1))
plt.savefig(config.out('snap_sheet.png'), dpi=72)
print('ok')
