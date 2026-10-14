"""Workstream E filming aid (2026-10-14): a tripod adapter for a bare iPhone 15, landscape, for slow-mo drop video.

A sleeve 24 mm wide slides onto the phone from the USB-C end and sits in the bottom half, clear of every button and
the camera. A ridge down the middle of the back plate squeezes the phone against the two front lips (the 72 mm back
plate bows to take it). Under the sleeve, a block with a printed 1/4"-20 female thread (the tripod standard) for
the mount's screw.

Prints lying on the sleeve's cross-section (the phone's long axis vertical), so every wall is in the layer plane
and nothing needs support. The thread then prints horizontal; the screw cleans up its top.

    python research/tumble/phone_mount.py   -> research/models/phone_mount_iphone15.stl, plus fit checks

Print frame: X = phone thickness (0 = its back face, + toward the screen), Y = phone width (0 = the edge that sits
on the mount, + up when filming), Z = along the phone (0..W, the sleeve).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
import cadquery as cq

# iPhone 15, bare (Apple's spec; Zach said bare phone, 2026-10-14)
PHONE_L, PHONE_W, PHONE_T = 147.6, 71.6, 7.80

W = 24.0                 # sleeve width along the phone
WALL = 3.0               # back plate and jaws
LIP_T, LIP = 2.5, 3.0    # front lip thickness, and how far it reaches over the screen
CLR_W = 0.2              # per side, across the phone's width
SLOT_T = 8.2             # phone 7.8 + 0.4 ...
RIDGE = 0.7              # ... less this ridge = 0.3 mm squeeze, taken by the back plate bowing
RIDGE_R = 3.0
LEAD = 0.8               # lead-in chamfer at both ends of the slot

# mount block and thread: 1/4"-20 UNC; Zach's caliper read the screw ~6 mm (crests of a 6.35 thread read low)
BASE_H, BASE_D = 10.0, 18.0
TPI_P = 25.4 / 20
D_MAJ = 6.35
CLR_TH = 0.2             # radial, printed-thread allowance
DEPTH = 10.0             # thread depth; 3 mm jaw above it is the roof under the phone
MOUTH = 0.6              # entry chamfer

SLOT_W = PHONE_W + 2 * CLR_W
XC = SLOT_T / 2          # screw under the phone's mid-plane
Y_BOT = -WALL - BASE_H   # mount face


def body():
    x0, x1 = -WALL, SLOT_T + LIP_T
    y0, y1 = -WALL, SLOT_W + WALL
    p = cq.Workplane('XY').box(x1 - x0, y1 - y0, W, centered=False).translate((x0, y0, 0))
    # phone slot, with the front open between the lips
    p = p.cut(cq.Workplane('XY').box(SLOT_T, SLOT_W, W + 2, centered=False).translate((0, 0, -1)))
    p = p.cut(cq.Workplane('XY').box(LIP_T + 1, SLOT_W - 2 * LIP, W + 2, centered=False)
              .translate((SLOT_T - 0.5, LIP, -1)))
    # ridge on the back plate's inner face
    ridge = cq.Workplane('XY').circle(RIDGE_R).extrude(W).translate((RIDGE - RIDGE_R, SLOT_W / 2, 0))
    p = p.union(ridge.intersect(cq.Workplane('XY').box(RIDGE + 1, 2 * RIDGE_R + 1, W, centered=False)
                                .translate((-1, SLOT_W / 2 - RIDGE_R - 0.5, 0))))
    # lead-in funnels at both ends
    for z0, sgn in ((0.0, 1), (W, -1)):
        e = LEAD + 0.5
        f = (cq.Workplane('XY').workplane(offset=z0 - sgn * 0.5)
             .center(SLOT_T / 2, SLOT_W / 2).rect(SLOT_T + 2 * e, SLOT_W + 2 * e)
             .workplane(offset=sgn * (LEAD + 0.5)).rect(SLOT_T, SLOT_W).loft())
        p = p.cut(f)
    # mount block
    p = p.union(cq.Workplane('XY').box(BASE_D, BASE_H + 0.5, W, centered=False)
                .translate((XC - BASE_D / 2, Y_BOT, 0)))
    return p


def thread_tool(clr=CLR_TH, overrun=1.5):
    """The hole: minor-diameter bore + swept 60 deg groove + entry chamfer, along +Z from z = 0 (the mount face)."""
    P = TPI_P; H = 0.8660254 * P
    r_min = D_MAJ / 2 - 5 * H / 8 + clr
    r_apex = D_MAJ / 2 + H / 8 + clr          # sharp-V apex; the groove reaches the major radius + clr
    r_base = r_apex - 0.9 * H                 # inside the bore, so turns never touch
    h = DEPTH + overrun
    bore = cq.Workplane('XY').circle(r_min).extrude(h).translate((0, 0, -overrun))
    helix = cq.Wire.makeHelix(P, h - 0.6, r_base, center=cq.Vector(0, 0, -overrun))
    half = 0.45 * P
    prof = cq.Wire.makePolygon([cq.Vector(r_base, 0, -overrun - half), cq.Vector(r_apex, 0, -overrun),
                                cq.Vector(r_base, 0, -overrun + half)], close=True)
    groove = cq.Solid.sweep(prof, [], helix, isFrenet=True)
    mouth = cq.Solid.makeCone(r_apex + MOUTH + overrun, r_apex - 0.2, MOUTH + overrun + 0.2,
                              pnt=cq.Vector(0, 0, -overrun))
    return bore.union(cq.Workplane().add(groove)).union(cq.Workplane().add(mouth))


def to_part(w):
    """Hole frame (+Z into the part, z 0 at the mount face) -> print frame."""
    return w.rotate((0, 0, 0), (1, 0, 0), -90).translate((XC, Y_BOT, W / 2))


def mount():
    return body().cut(to_part(thread_tool()))


def screw(shift=0.0, length=8.0):
    """Dummy 1/4"-20 external thread at full nominal size (basic profile, flat crest P/8), from the face inward."""
    P = TPI_P; H = 0.8660254 * P
    r_core = D_MAJ / 2 - 5 * H / 8 - 0.02
    r_crest = D_MAJ / 2
    w_crest = P / 8; w_root = 0.9 * P
    core = cq.Workplane('XY').circle(r_core).extrude(length)
    helix = cq.Wire.makeHelix(P, length - 1.0, r_core - 0.1, center=cq.Vector(0, 0, 0.3))
    prof = cq.Wire.makePolygon([cq.Vector(r_core - 0.1, 0, 0.3 - w_root / 2), cq.Vector(r_crest, 0, 0.3 - w_crest / 2),
                                cq.Vector(r_crest, 0, 0.3 + w_crest / 2), cq.Vector(r_core - 0.1, 0, 0.3 + w_root / 2)],
                               close=True)
    ridge = cq.Solid.sweep(prof, [], helix, isFrenet=True)
    s = core.union(cq.Workplane().add(ridge))
    return s.translate((0, 0, shift))


def phone(squeeze_side=True):
    """Bare iPhone 15 as a rounded box, in the slot, pushed by the ridge against the lips."""
    x0 = RIDGE if squeeze_side else (SLOT_T - PHONE_T) / 2
    b = (cq.Workplane('XY').box(PHONE_T, PHONE_W, PHONE_L, centered=False)
         .edges('|Z').fillet(1.5)
         .translate((x0, CLR_W, W / 2 - 48.0)))       # sleeve centre 48 mm from the USB-C end
    return b


def vol(a, b):
    return a.intersect(b).val().Volume() if a.intersect(b).vals() else 0.0


if __name__ == '__main__':
    out = os.path.join(ROOT, 'models'); os.makedirs(out, exist_ok=True)
    m = mount()
    v = m.val()
    bb = v.BoundingBox()
    print(f'mount: valid {v.isValid()}, solids {len(m.solids().vals())}, volume {v.Volume() / 1000:.2f} cm3, '
          f'bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}')
    p = os.path.join(out, 'phone_mount_iphone15.stl')
    cq.exporters.export(m, p, tolerance=0.01, angularTolerance=0.1)
    print('wrote', p)

    # fit checks, each with its negative control. The dummy screw starts in phase with the groove (crest centre
    # on the groove centre at angle 0: groove at z = -1.5, crest at z = 0.3 + shift), as a real screw finds it.
    ph0 = (-1.5 - 0.3) % TPI_P
    sc = to_part(screw(shift=ph0))
    print(f'screw in thread: overlap {vol(m, sc):.3f} mm3 (want 0)')
    play = [d for d in [i * 0.02 for i in range(-15, 16)] if vol(m, to_part(screw(shift=ph0 + d))) < 1e-3]
    print(f'  axial play: {min(play):+.2f} .. {max(play):+.2f} mm' if play else '  axial play: none')
    print(f'  control, screw half a pitch off: {vol(m, to_part(screw(shift=ph0 + TPI_P / 2))):.3f} mm3 (want > 0)')
    print(f'  control, thread cut 0.1 undersize (no allowance): '
          f'{vol(body().cut(to_part(thread_tool(clr=-0.1))), sc):.3f} mm3 (want > 0)')
    ph = phone(squeeze_side=False)
    print(f'phone centred in slot, ridge cut away: overlap '
          f'{vol(m.cut(cq.Workplane("XY").box(RIDGE + 0.01, 2 * RIDGE_R + 1, W + 2, centered=False).translate((-0.005, SLOT_W / 2 - RIDGE_R - 0.5, -1))), ph):.3f} mm3 (want 0)')
    print(f'  phone vs full part (the ridge squeeze, want > 0): {vol(m, ph):.3f} mm3')
    for n, s in (('screw', sc), ('phone', ph)):
        cq.exporters.export(s, os.path.join(out, f'_fig_{n}.stl'), tolerance=0.02, angularTolerance=0.2)
