"""Print-health scan: where is this model too thin to survive?

Everything here prints in PETG at 0.2 mm layers through a 0.4 nozzle. Two perimeters is 0.8 mm;
below that a wall is a single extrusion with nothing behind it, and it is also where the mesher
starts producing self-intersections. This finds those places before the printer does.

Local thickness is approximated as twice the largest distance-to-surface in a small neighbourhood,
which is the standard trick and good enough to rank.

    python tree_parts_b_health.py
"""
import numpy as np
from scipy import ndimage
import tree_parts_b as B

STEP = 0.30
THIN = 0.80                       # two perimeters at a 0.4 nozzle
VERY_THIN = 0.50                  # one extrusion: this will not survive handling

print('%-12s %9s %11s %11s' % ('part', 'min wall', '< %.1f mm' % THIN, '< %.1f mm' % VERY_THIN))
for name, (fn, lo, hi, step, target, _) in B.PARTS.items():
    xs = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
    P = np.meshgrid(*xs, indexing='ij')
    solid = fn(P, True) < 0
    dist = ndimage.distance_transform_edt(solid) * STEP
    thick = 2.0 * ndimage.maximum_filter(dist, size=5)      # local thickness
    t = thick[solid]
    v_thin = float((t < THIN).sum()) * STEP ** 3
    v_vthin = float((t < VERY_THIN).sum()) * STEP ** 3
    flag = ''
    if v_vthin > 20:
        flag = '  <-- FRAGILE'
    elif v_thin > 150:
        flag = '  <-- thin'
    print('%-12s %7.2f mm %8.0f mm3 %8.0f mm3%s' % (name, t.min(), v_thin, v_vthin, flag))

# ------------------------------------------------------------------ coincident faces
# Two features OF THE SAME PART that stop on the same plane leave a zero-thickness step. It has
# bitten twice: ball_minus stalled at 44k faces and fork at 132k, both from a cut ending flush
# with the face it passed through. Faces of DIFFERENT parts meeting is just contact, and fine --
# the post's flange is supposed to land on the collar's recess floor -- so the part tag matters.
print()
print('--- features of one part landing on the same Y plane ---')
PLANES = [
  ('ball',  'servo case base',      B.SERVO_Y0),
  ('ball',  'servo case top',       B.SERVO_Y1),
  ('ball',  'tab recess inboard',   B.TAB_Y),
  ('ball',  'tab recess outboard',  B.TAB_Y + B.TAB_T),
  ('ball',  'stub bore start',      B.SERVO_Y1 - 0.6),
  ('ball',  'flat face +Y',         B.FLAT),
  ('ball',  'face plate inner +Y',  B.FLAT - B.FACE_T),
  ('ball',  'hub stub start',       B.FLAT - 2.0),
  ('ball',  'hub stub end',         B.BRG_P_Y1 - 0.2),
  ('ball',  'flat face -Y',         -B.FLAT),
  ('ball',  'face plate inner -Y',  -B.FLAT + B.FACE_T),
  ('ball',  'socket hub end',       -19.0),   # still a literal in the generator
  ('ball',  'axle socket bore end', B.AXLE_BORE_Y),
  ('ball',  'seam pilot end',       B.SEAM_PILOT_Y),
  ('fork',  'collar inboard',       B.POD_Y0),
  ('fork',  'hub bore start',       B.POD_Y0 - 1),
  ('fork',  'bearing seat in +Y',   B.BRG_P_Y0),
  ('fork',  'bearing seat out +Y',  B.BRG_P_Y1),
  ('fork',  'pass bore in +Y',      B.BRG_P_Y1 - 0.1),
  ('fork',  'flange recess +Y',     B.POD_P_Y1 - B.FLANGE_REC),
  ('fork',  'collar outer +Y',      B.POD_P_Y1),
  ('fork',  'bearing seat in -Y',   B.BRG_M_Y0),
  ('fork',  'bearing seat out -Y',  B.BRG_M_Y1),
  ('fork',  'pass bore in -Y',      B.BRG_M_Y1 + 0.1),
  ('fork',  'collar outer -Y',      B.POD_M_Y1),
  ('post',  'inboard face',         B.POST_IN),
  ('post',  'horn pocket floor',    B.POST_IN + B.HORN_D_B),
  ('post',  'retaining ring in',    B.BRG_P_Y1 - 0.1),
  ('post',  'flange face',          B.POD_P_Y1 - B.FLANGE_REC),
  ('post',  'outboard end',         B.POD_P_Y1 - B.FLANGE_REC + 0.2),
  ('axle',  'inboard end',          B.AXLE_Y1),
  ('axle',  'outboard end',         B.AXLE_Y0),
  ('cap',   'retaining ring in',    B.BRG_M_Y1 + 0.1),
  ('cap',   'inner face',           B.POD_M_Y1 + B.FLANGE_REC),
]
hits = 0
for i in range(len(PLANES)):
    for j in range(i + 1, len(PLANES)):
        pa, na, va = PLANES[i]
        pb, nb, vb = PLANES[j]
        if pa == pb and abs(va - vb) < 1e-6:
            print('  %-5s  Y %7.2f   %-22s == %s' % (pa, va, na, nb))
            hits += 1
print('  none' if not hits else '  %d coincidence(s) -- make one of each pair overrun the other' % hits)
