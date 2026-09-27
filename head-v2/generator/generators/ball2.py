import os, sys
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, 'ball.py'), encoding='utf-8-sig').read().split("P_ = 10.0")[0])

def sph(cx, cy, cz, r, th0=0.0, th1=np.pi, nlat=40, nlon=72):
    th = np.linspace(th0, th1, nlat + 1); ph = np.linspace(0, 2 * np.pi, nlon + 1)
    P = lambda i, j: [cx + r * np.sin(th[i]) * np.cos(ph[j]), cy + r * np.cos(th[i]), cz + r * np.sin(th[i]) * np.sin(ph[j])]
    t = []
    for i in range(nlat):
        for j in range(nlon):
            a, b, c, d = P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)
            t += [[a, b, c], [a, c, d]]
    T = np.array(t, float)
    keep = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) > 1e-9
    return orient(T[keep], np.array([cx, cy, cz]))
def project(pt, yaw, pitch, size, center, ext):
    Rm = rot(yaw, pitch); Pp = (np.array(pt) - center) @ Rm.T; sc = size / (2 * ext)
    return size / 2 + Pp[0] * sc, size / 2 - Pp[2] * sc

# ---- measured camera (Zach 2026-09-17) ----
BOARD, PITCH, HOLE, HOLDER_H, PCB_T = 36.0, 28.0, 2.0, 9.0, 1.6
XB = 8.5                                    # board back face: moved forward so the ribbon's axle run fits behind it
corner = np.sqrt((XB + PCB_T) ** 2 + 2 * (BOARD / 2) ** 2)
R_IN = corner + 1.0                         # 1 mm clearance to the board corners
WALL = 1.2
R = R_IN + WALL
P_, TT = 10.0, 14.5
H = TT + R + 2.0
FRONT = 40.0
GAP = 3.0
POD = 22.0                                  # 4 mm 6704 bearing + 16 mm ribbon coil + walls/clearance
SP0, SP1 = R + GAP, R + GAP + POD           # servo pod Y range
BP0, BP1 = -(R + GAP), -(R + GAP + POD)     # bearing pod: matched to the servo pod for symmetry
C0 = BP0 - 5.0                              # coil chamber starts after the bearing (ribbon spans C0-16..C0)
PED_Y = -13.0                               # ribbon drop through the pedestal, beside the pan servo
col = dict(deck=(185, 183, 175), struct=(90, 190, 160), ball=(170, 150, 225), seam=(90, 80, 120), lens=(55, 55, 65),
           bezel=(120, 110, 150), bearing=(230, 175, 70), ribbon=(235, 130, 60), ir=(215, 80, 80), servo=(95, 140, 210),
           pcb=(70, 120, 90), ldr=(215, 175, 120), horn=(225, 225, 215))

def base_static(with_servo_pod=True):
    s = []
    for b in [box(-60, -20, -55, 55, -3, 0), box(-20, -9, -55, -9, -3, 0), box(9, 12, -55, -9, -3, 0), box(-9, 9, -55, -14.5, -3, 0),
              box(-20, 12, 9, 55, -3, 0), box(12, FRONT, -55, 55, -3, 0)]:
        s.append((b, col['deck']))
    s += [(box(-16.9, 5.9, -6.1, 6.1, P_ - 24.3, P_ - 1.8), col['servo']), (cyl(0, 0, 0, 18, 'z', 0, P_), col['struct']),
          (cyl(0, 0, 0, 17, 'z', P_, P_ + 0.5), col['bearing']), (cyl(0, 0, 0, 20, 'z', P_ + 0.5, TT), col['struct']),
          (box(-11, 11, BP1, SP1, P_ + 0.5, TT), col['struct'])]
    if with_servo_pod:
        s += [(box(-10, 10, SP0, SP1, TT, H), col['struct']), (cyl(0, 0, H, 20, 'y', SP0, SP1), col['struct'])]
    s += [(box(-10, 10, BP1, BP0, TT, H), col['struct']), (cyl(0, 0, H, 20, 'y', BP1, BP0), col['struct']),
          (cyl(0, 0, H, 13.5, 'y', BP0 - 4.0, BP0 + 0.3), col['bearing'])]
    s += ribbon_pod_parts()
    for sgn in (-1, 1):
        s += [(box(FRONT - 8, FRONT, sgn * 42 - 6, sgn * 42 + 6, 0, 10), col['deck']), (cyl(0, sgn * 42, 5, 4.5, 'x', FRONT, FRONT + 1), col['ir'])]
    return s

xh = XB + PCB_T                               # board front face
ldr_y, ldr_z = 2.7, BOARD / 2 + 2.5           # sensor pokes just past the top edge
ldr_win_x = np.sqrt(R ** 2 - ldr_y ** 2 - ldr_z ** 2)
lens_x = np.sqrt(R ** 2 - 9 ** 2)
post_back = -np.sqrt(R_IN ** 2 - 2 * (PITCH / 2) ** 2) + 0.5

def strip_surface(pts, y0, y1):
    """Ribbon as a surface: a polyline in the XZ plane swept across Y (ribbon width along Y)."""
    t = []
    for a, b in zip(pts[:-1], pts[1:]):
        p0, p1 = [a[0], y0, a[1]], [b[0], y0, b[1]]
        p2, p3 = [b[0], y1, b[1]], [a[0], y1, a[1]]
        t += [[p0, p1, p2], [p0, p2, p3], [p0, p2, p1], [p0, p3, p2]]
    return np.array(t, float)

def ribbon_pod_parts():
    s = []
    ya, yb = C0 - 16.0, C0
    s.append((box(-0.15, 0.15, ya, yb, H - 10.5, H), col['ribbon']))                     # drops from the axle to the spool
    ts = np.linspace(0, 4 * np.pi, 160); rs = 10.5 + (17.5 - 10.5) * ts / ts[-1]           # clock-spring coil: 2 loose turns
    s.append((strip_surface([(r * np.sin(a), H - r * np.cos(a)) for a, r in zip(ts, rs)], ya, yb), col['ribbon']))
    s.append((box(-0.15, 0.15, ya, yb, TT + 0.3, H - 17.5), col['ribbon']))              # down inside the stem
    s.append((box(-8, 8, PED_Y, yb, TT, TT + 0.3), col['ribbon']))                        # across the turntable to the centre
    s.append((box(-8, 8, PED_Y - 0.3, PED_Y, -22, TT + 0.3), col['ribbon']))              # down the pedestal, through the deck slot
    return s

def camera_parts(half):   # half: 'all' or 'minusY' (cutaway keeps the -Y shell)
    t = []
    t += [(box(XB, xh, -BOARD / 2, BOARD / 2, H - BOARD / 2, H + BOARD / 2), col['pcb']),
          (cyl(0, 0, H, 10.5, 'x', xh, xh + HOLDER_H), col['lens']),
          (cyl(0, 0, H, 6, 'x', xh + HOLDER_H, lens_x - 0.5), col['lens']),
          (cyl(0, ldr_y, H + ldr_z, 2.4, 'x', xh + 1, xh + 5), col['ldr']),
          (box(xh + 0.3, xh + 0.6, -8, 8, H - BOARD / 2 - 3.0, H - BOARD / 2), col['ribbon']),   # FPC leaves the bottom edge, heading down
          (box(-8.3, xh + 0.6, -8, 8, H - BOARD / 2 - 3.3, H - BOARD / 2 - 3.0), col['ribbon']), # creased back under the board
          (box(-8.3, -8.0, -8, 8, H - BOARD / 2 - 3.3, H), col['ribbon']),                      # up behind the board to the axis
          (box(-8.0, 8.0, C0 + 0.5, 8, H - 0.15, H + 0.15), col['ribbon'])]                     # folded flat along the axis, out through the hub
    for py in (-PITCH / 2, PITCH / 2):
        if half == 'minusY' and py > 0: continue
        for pz in (-PITCH / 2, PITCH / 2):
            t.append((cyl(0, py, H + pz, 2.6, 'x', post_back, XB), col['ball']))
    t += [(cyl(0, 0, H, 10, 'y', C0 - 17.0, -R + 1.0), col['struct'])]                         # hollow hub -> 6704, then the coil spool
    if half == 'all':
        t += [(sph(0, 0, H, R), col['ball']), (cyl(0, 0, H, R + 0.15, 'y', -0.4, 0.4), col['seam']),
              (cyl(0, 0, H, 9, 'x', lens_x - 1.5, lens_x + 1.2), col['bezel']), (cyl(0, 0, H, 6, 'x', lens_x + 1.2, lens_x + 3.0), col['lens']),
              (cyl(0, ldr_y, H + ldr_z, 3.0, 'x', ldr_win_x - 0.6, ldr_win_x + 0.4), col['seam']),
              (cyl(0, 0, H, 8, 'y', R - 1.0, R + GAP), col['horn'])]
    else:
        t += [(sph(0, 0, H, R, np.pi / 2, np.pi), col['ball'])]
    return t

size = 900
ci, ei = np.array([0.0, 0.0, 30.0]), 66.0
tiles = []
def callouts(im, pts, yaw, pitch, c, e):
    d = ImageDraw.Draw(im)
    for num, pt in pts:
        x, y = project(pt, yaw, pitch, size, c, e)
        d.line([(x, y), (x + 26, y - 26)], fill=(40, 40, 40), width=2)
        d.ellipse([x + 20, y - 46, x + 46, y - 20], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
        d.text((x + 29, y - 39), str(num), fill=(20, 20, 20))
full = base_static() + camera_parts('all')
im = zrender(full, 215, 22, size=size, label=f'Ball head at true size: ball {2*R:.1f} mm', center=ci, ext=ei)
callouts(im, [(1, (0, -10, H + R)), (2, (0, SP1, H + 12)), (6, (ldr_win_x, ldr_y, H + ldr_z + 3))], 215, 22, ci, ei); tiles.append(im)
cut = base_static(with_servo_pod=False) + camera_parts('minusY')
cc, ec = np.array([0.0, -5.0, H]), 40.0
im = zrender(cut, 140, 20, size=size, label='Cutaway from behind: +Y half-shell and servo pod removed', center=cc, ext=ec)
callouts(im, [(3, (XB, 12, H + 10)), (4, (post_back / 2, -PITCH / 2, H + PITCH / 2 + 2.6)), (5, (XB - 3.3, 4, H - 10)),
              (7, (XB - 7, -(R - 2), H + 0.3))], 140, 20, cc, ec); tiles.append(im)
im = zrender(full, 270, 0, size=size, label='front view', center=np.array([0, 0, 34.0]), ext=ei); tiles.append(im)
cs2, es2 = np.array([0.0, 0.0, H - 4]), 38.0
im = zrender(cut, 180, 0, size=size, label='Cutaway looking into the open half (camera faces LEFT)', center=cs2, ext=es2)
callouts(im, [(3, (XB, 0, H + 14)), (4, (post_back / 2, -PITCH / 2, H + PITCH / 2 + 2.6)), (5, (XB - 3.3, 0, H - 12)),
              (6, (xh + 3, ldr_y, H + ldr_z + 2.4)), (7, (XB - 7, 0, H + 0.3))], 180, 0, cs2, es2); tiles.append(im)
im = zrender(full, 0, 0, size=size, label='side view', center=np.array([6.0, 0, 36.0]), ext=ei); tiles.append(im)
lg = Image.new('RGB', (size, size), (246, 245, 241)); d = ImageDraw.Draw(lg)
lines = ['MEASURED: board 36 x 36 mm, holes 2 mm on 28 mm pitch, IR-cut holder 9 mm',
         f'Board corner radius from axis {corner:.1f} mm + 1 mm clearance -> inner R {R_IN:.1f}',
         f'Ball OD {2*R:.1f} mm ({WALL} mm wall), tilt axis {H:.1f} mm above deck',
         f'Overall width across pods ~{SP1 - BP1:.0f} mm', '',
         '1  Ball split L/R, seam groove on the face', '2  Servo pod (MG90D + stock horn)',
         '3  Board sits on the tilt axis, lens forward', '4  Posts on 28 mm pitch: two per half-shell',
         '5  FPC: down off the board, back under it, up to the axis', '6  Light-sensor window above the lens',
         '7  Out the hollow hub into a 2-turn clock-spring coil in the pod,', '    then down the stem, across the turntable, down the pedestal',
         '', 'Lens / FOV: not modelled yet (to do)']
for i, s_ in enumerate(lines): d.text((36, 50 + i * 42), s_, fill=(30, 30, 30))
tiles.append(lg)
sheet = Image.new('RGB', (size * 3, size * 2), 'white')
for i, t_ in enumerate(tiles): sheet.paste(t_, ((i % 3) * size, (i // 3) * size))
sheet.save(os.path.join(D, 'ball_head_true.png'))
print(f'R {R:.2f} OD {2*R:.2f} H {H:.2f} width {SP1-BP1:.1f} post_back {post_back:.2f} ldr window x {ldr_win_x:.1f}')
