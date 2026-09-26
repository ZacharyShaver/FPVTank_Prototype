"""One sheet: each fix as a slice through the part. grey = your part, RED = removed, GREEN = added."""
import os, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from slices import slice2d
from probe import load_stl, DL
from build import OUT, RX, RZ, ROD_R, Y_HEAD, Y_OUT, PILOT_Y, HOLDER_CLEAR_R
from kit import B, A, XC, X0, X1, SW, SNIP_X, SNIP_Z, FRONT_TRIM
H = B.H
P0, P1 = load_stl(os.path.join(DL, 'BODY_NUMBA1 (1) (1).stl')), load_stl(os.path.join(OUT, 'BODY_NUMBA1_fixed.stl'))
M0, M1 = load_stl(os.path.join(DL, 'ball_minus_revised.stl')), load_stl(os.path.join(OUT, 'ball_minus_revised_fixed.stl'))
GREY, RED, GREEN = np.array([0.72, 0.72, 0.74]), np.array([0.86, 0.16, 0.16]), np.array([0.13, 0.62, 0.25])

def diff_panel(ax, pairs, axis, val, lo, hi, h=0.04):
    img = None
    for T0, T1 in pairs:
        m0, u, v, (a, b) = slice2d(T0, axis, val, lo, hi, h)
        m1, _, _, _ = slice2d(T1, axis, val, lo, hi, h)
        if img is None: img = np.ones(m0.shape + (3,))
        img[m0 & m1] = GREY; img[m0 & ~m1] = RED; img[m1 & ~m0] = GREEN
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(u[0], u[-1], v[0], v[-1]), interpolation='nearest')
    ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.4)
    ax.set_xlabel('XYZ'[a] + {'X': '  (toward the lens ->)', 'Y': '  (toward the post ->)', 'Z': '  (up)'}['XYZ'[a]], fontsize=8)
    ax.set_ylabel('XYZ'[b] + {'X': '', 'Y': '  (toward the post)', 'Z': '  (up)'}['XYZ'[b]], fontsize=8)
    ax.tick_params(labelsize=7)

fig, axs = plt.subplots(2, 3, figsize=(21, 13.5))
# 1. rail notch -- looking at the rail face-on (plane X 15)
ax = axs[0, 0]
diff_panel(ax, [(P0, P1)], 0, 15.0, (-2, 30), (26, 76))
ax.add_patch(Circle((0, H), 26.7 / 2, fill=False, ec='darkorange', lw=1.6, ls='--'))
ax.text(1, 76.6, '1. Rail notch for the camera\'s round IR-CUT block', fontsize=11, weight='bold')
ax.text(-1.5, 38.5, 'orange = the IR-CUT block\n(26.7 across)', color='darkorange', fontsize=8)
ax.text(12.6, 55.5, 'red: 0.5 mm arc\ncut from the rail', color=RED, fontsize=8)
# 2. servo slot -- plane X -5, through the servo
ax = axs[0, 1]
diff_panel(ax, [(P0, P1)], 0, -5.0, (-3, 41.5), (23, 62.5), h=0.02)
top = 21.2357
ax.add_patch(Rectangle((top - 23.5, H - SW / 2), 23.5, SW, fill=False, ec='royalblue', lw=1.4))
ax.text(-2.5, 62.9, '2. Servo slot 12.20 -> 12.50 mm', fontsize=11, weight='bold')
ax.text(0.5, 51.6, 'blue = the servo (12.2 thick),\ntop face on your plate at Y 21.24', color='royalblue', fontsize=8)
ax.text(0.5, 44.0, 'red strips = 0.15 mm shaved off each plate\n(a 12.2 servo in a 12.2 slot will not slide 21 mm)', color=RED, fontsize=8)
# 3. front seam screw -- plane Y 4.9, through the light sensor
ax = axs[0, 2]
diff_panel(ax, [(P0, P1)], 1, 4.9, (-2, 44), (32, 82))
bx0 = 10.5
ax.add_patch(Rectangle((bx0, H - 1.6 - 18), 2.0, 36.0, fill=False, ec='darkorange', lw=1.2))
ax.add_patch(Rectangle((bx0 + 2, H - 13.35), 8.6, 26.7, fill=False, ec='darkorange', lw=1.2))
ax.add_patch(Rectangle((bx0 + 2, H + 16.6 - 3.5), 4.0, 7.0, fill=False, ec='darkorange', lw=1.2))
ax.add_patch(Circle((RX, RZ), B.M3_CLEAR, fill=False, ec='k', lw=0.8))
ax.text(0, 82.6, '3. New front seam screw (M3), top-front', fontsize=11, weight='bold')
ax.text(23.0, 62.0, 'green = new post\nthat clamps the\ntwo halves', color=GREEN, fontsize=8)
ax.text(0.5, 71.3, 'light\nsensor', color='darkorange', fontsize=8)
ax.text(0.5, 45.5, 'board', color='darkorange', fontsize=8)
ax.text(14.0, 47.0, 'IR-CUT\nblock', color='darkorange', fontsize=8)
# 4. the screw itself -- plane X 21 through both halves
ax = axs[1, 0]
diff_panel(ax, [(P0, P1), (M0, M1)], 0, RX, (-16, 58), (16, 80), h=0.03)
L = 20.0
ax.add_patch(Rectangle((Y_HEAD - 2.0, RZ - 2.75), 2.0, 5.5, fill=False, ec='k', lw=1.0))
ax.add_patch(Rectangle((Y_HEAD, RZ - 1.5), L, 3.0, fill=False, ec='k', lw=1.0, ls='--'))
ax.axvline(0, color='k', lw=0.6, ls=':')
ax.text(-15.5, 80.6, '4. That screw, cut along its length', fontsize=11, weight='bold')
ax.text(-15, 74.7, 'ball_minus\n(head sits here)', fontsize=8)
ax.text(1.0, 74.7, 'ball_plus\n(threads bite here)', fontsize=8)
ax.text(-15, 60.0, 'dashed = M3 x 20, driven from the -Y side;\nhead seat Y %.1f, thread hole to Y +%.1f' % (Y_HEAD, PILOT_Y), fontsize=8)
# 5. the servo tabs -- plane Y 16.2 (tab level), what YOU trim
ax = axs[1, 1]
diff_panel(ax, [(P1, P1)], 1, 16.2, (-27, 38), (14, 66))
ty = [XC - A.TAB_SPAN / 2, XC + A.TAB_SPAN / 2]; zl, zh = H - SW / 2, H + SW / 2
ax.add_patch(Rectangle((ty[0], zl), ty[1] - ty[0], SW, fill=False, ec='royalblue', lw=1.0, ls='--'))
xe = ty[0]
poly = [(xe, zl + SNIP_Z), (xe + SNIP_X, zl), (ty[1] - FRONT_TRIM, zl), (ty[1] - FRONT_TRIM, zh), (xe + SNIP_X, zh), (xe, zh - SNIP_Z)]
ax.add_patch(Polygon(poly, closed=True, fill=False, ec='royalblue', lw=1.6))
for zc in (zl, zh):
    s = 1 if zc == zl else -1
    ax.add_patch(Polygon([(xe, zc), (xe + SNIP_X, zc), (xe, zc + s * SNIP_Z)], closed=True, fc=(0.86, 0.16, 0.16, 0.5), ec=RED))
ax.add_patch(Rectangle((ty[1] - FRONT_TRIM, zl), FRONT_TRIM, SW, fc=(0.86, 0.16, 0.16, 0.5), ec=RED))
ax.add_patch(Rectangle((10.5, 32.4), 2.0, 36.0, fill=False, ec='darkorange', lw=1.2))
ax.text(-26.5, 66.6, '5. Two snips on the servo\'s tabs (you do these)', fontsize=11, weight='bold')
ax.text(-26.5, 38.2, 'rear tab: snip both outer\ncorners %.1f x %.1f mm --\nthey hit the seam posts' % (SNIP_X, SNIP_Z), color=RED, fontsize=8)
ax.text(-9.0, 61.6, 'front tab: %.1f mm off the end --\nit touches the camera board' % FRONT_TRIM, color=RED, fontsize=8)
ax.text(8.0, 40.5, 'board', color='darkorange', fontsize=8)
# 6. overview: 3D view into the fixed ball_plus with every fix face coloured
from zr import zrender
def fix_faces(T):
    c = T.mean(1); x, y, z = c[:, 0], c[:, 1], c[:, 2]
    rho_l = np.hypot(y, z - H); rho_s = np.hypot(x - RX, z - RZ)
    m = ((np.abs(rho_l - HOLDER_CLEAR_R) < 0.03) & (x > 13.4) & (x < 16.6))
    m |= ((np.abs(z - 45.74) < 0.01) | (np.abs(z - 58.24) < 0.01)) & (x > -22.4) & (x < 10.9)
    m |= (rho_s < ROD_R + 0.03) & (np.abs(y) < 16)
    return m
F = fix_faces(P1)
im = zrender([(P1[~F], (200, 200, 205)), (P1[F], (220, 90, 40))], 0, 0, 640, '', center=(0, 12, 52), ext=33)
ax = axs[1, 2]; ax.imshow(im); ax.set_axis_off()
ax.set_title('6. Your ball_plus from the seam side, fixes in orange', fontsize=11, weight='bold', loc='left')
fig.text(0.01, 0.005, 'grey = your part, unchanged    RED = material removed    GREEN = material added    '
         'blue = servo    orange = camera (board on the front of your wall)', fontsize=10)
plt.tight_layout(rect=(0, 0.015, 1, 1)); plt.savefig(os.path.join(OUT, 'fixes_sheet.png'), dpi=72)
print('ok')
