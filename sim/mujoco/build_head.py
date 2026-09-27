"""The v2 pan/tilt head as a MuJoCo model: sim/mujoco/out/head.xml plus its meshes.

Three moving pieces, all in the head's frame (X toward the lens, Y along the tilt axis, Z up, mm):
  base  (fixed)  the well, the gear bay, the pan servo, the 6809 bearing
  pan   (Z axis) the drum, the cradle bolted on it, the post; the input gear is tied to it 2:1
  tilt  (Y axis, through X 0 Z 52) both ball halves, the tilt servo, the camera

Reads the current exports, so run these first (they write the files below):
    python head-v2/fixes/build_all.py                                   # ball halves, post
    python head-v2/generator/generators/tree_parts_b.py fork            # the cradle
    python head-v2/generator/generators/pan_coil_b.py                   # drum, well, bay, gear, servo
Then:
    python sim/mujoco/build_head.py        # writes out/head.xml, prints the mass table and a servo test
    python sim/mujoco/view_head.py         # opens it: sliders move the servos, Ctrl+drag shoves the head

Nothing collides (every geom has contype 0): the joints hold the parts together, and MuJoCo would
collide the cradle as its convex hull, which swallows the ball. Joint limits stand in for the stops.
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import contextlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
MESHES = os.path.join(OUT, 'meshes')
GEN = os.path.join(config.REPO, 'head-v2', 'generator')
H = 52.0                                     # tilt axis height (B.H)

# ---- masses, grams. ALL GUESSES until Zach reads the slicer: set the filament to PETG-GF, slice each
# part, and put its grams here. Printed parts are guessed as volume x 1.35 g/cm3 (PETG-GF, a guess)
# x 0.8 (walls and infill, a guess). Hardware is datasheet weight.
PETG_GF, FILL = 1.35, 0.8
SLICER = {                                   # grams from the slicer, when he has them; None = use the guess
    'ball_plus': None, 'ball_minus': None, 'post': None, 'cradle': None, 'drum': None, 'input_gear': None,
}
HARDWARE = {                                 # grams
    'tilt_servo': 13.4,                      # MG90D datasheet
    'camera': 6.0,                           # OV5647 IR-CUT module with its motorised filter: a guess
    'tilt_bearings': 11.0,                   # 2 x 6704 at ~5.5 g (catalogue), on the cradle side
    'drum_bearing_inner': 15.0,              # the 6809's inner race and half its balls, on the drum
    'cradle_screws': 3.0,                    # 3 x M3 x 12
}

# ---- the servo, MG90D datasheet at 4.8 V: stall 2.0 kg.cm, 0.10 s per 60 deg, no load.
STALL = 2.0 * 9.81 / 100                     # N.m
SPEED = np.radians(60) / 0.10                # rad/s
DEADBAND = 5.0                               # deg of error at which the servo is pushing flat out (a guess)
ROTOR = 1e-4                                 # kg.m2, the motor's inertia seen at the horn (a guess)
PAN_RATIO = 2.0                              # 2:1 step-up: the drum turns twice the servo

# (name, source, piece, colour). Mass comes from SLICER or the guess.
PARTS = [
    ('well', os.path.join(GEN, 'pan-coil-b', 'fusion', 'well.obj'), 'base', (163, 168, 162)),
    ('gear_bay', os.path.join(GEN, 'pan-coil-b', 'fusion', 'bay.obj'), 'base', (180, 184, 178)),
    ('gear_floor', os.path.join(GEN, 'pan-coil-b', 'fusion', 'floor.obj'), 'base', (180, 184, 178)),   # set 2
    ('pan_servo', os.path.join(GEN, 'pan-coil-b', 'fusion', 'servo.obj'), 'base', (40, 70, 140)),
    ('bearing_6809', os.path.join(GEN, 'pan-coil-b', 'fusion', 'bearing.obj'), 'base', (150, 150, 160)),
    ('input_gear', os.path.join(GEN, 'pan-coil-b', 'fusion', 'gear_in.obj'), 'gear', (79, 174, 158)),
    ('drum', os.path.join(GEN, 'pan-coil-b', 'fusion', 'drum.obj'), 'pan', (62, 156, 143)),
    ('small_gear', os.path.join(GEN, 'pan-coil-b', 'fusion', 'gear_out.obj'), 'pan', (79, 174, 158)),  # off the drum, set 2
    ('cradle', os.path.join(GEN, 'tree-parts-b', 'fusion', 'fork.obj'), 'pan', (216, 195, 154)),
    ('post', config.out('ball_servo_post_v3.stl'), 'pan', (200, 120, 60)),
    ('ball_plus', config.out('BODY_NUMBA1_camposts.stl'), 'tilt', (235, 235, 230)),
    ('ball_minus', config.out('ball_minus_revised_snap.stl'), 'tilt', (205, 205, 200)),
    ('camera', os.path.join(config.CAMERA, 'camera_dummy.stl'), 'tilt', (30, 110, 60)),
]
CAMERA_DX = 2.5                              # the board sits 2.5 forward of the dummy's frame (check_campost)
TILT_SERVO_BOX = ((-16.9, -2.26, H - 6.1), (5.9, 21.24, H + 6.1))   # kit.servo(): turned, top at Y 21.24
TARGET = (0.35, 0.2, 0.15)                   # m: the red ball's starting place
BEARING_Y = 29.0                             # 6704 seats, |Y| (the cradle's collars, roughly)


@contextlib.contextmanager
def quiet():
    """pymeshlab prints plugin warnings on stderr at load; hide them"""
    fd = os.dup(2); nul = os.open(os.devnull, os.O_WRONLY); os.dup2(nul, 2)
    try:
        yield
    finally:
        os.dup2(fd, 2); os.close(nul); os.close(fd)


with quiet():
    import pymeshlab as ml


def mesh(name, src, dx=0.0):
    """copy one part into out/meshes as a binary STL, in mm; returns (volume mm3, bbox min, bbox max)"""
    if not os.path.exists(src):
        sys.exit('missing %s -- run the steps in this file\'s docstring first' % src)
    with quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(src)
        ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
        if dx:
            ms.compute_matrix_from_translation(axisx=dx)
        ms.save_current_mesh(os.path.join(MESHES, name + '.stl'), binary=True, save_face_color=False)
        g = ms.get_geometric_measures(); b = ms.current_mesh().bounding_box()
    return g['mesh_volume'], b.min(), b.max()


def grams(name, vol):
    if name in SLICER and SLICER[name] is not None:
        return SLICER[name], 'slicer'
    return vol / 1000 * PETG_GF * FILL, 'guess'


def rgba(c, a=1.0):
    return '%.3f %.3f %.3f %.2f' % (c[0] / 255, c[1] / 255, c[2] / 255, a)


def build():
    os.makedirs(MESHES, exist_ok=True)
    info, geoms = {}, {'base': [], 'pan': [], 'tilt': [], 'gear': []}
    for name, src, piece, col in PARTS:
        vol, lo, hi = mesh(name, src, CAMERA_DX if name == 'camera' else 0.0)
        if piece == 'base':
            g, how = 0.0, 'fixed'
        elif name == 'camera':
            g, how = HARDWARE['camera'], 'guess'
        else:
            g, how = grams(name, vol)
        info[name] = dict(vol=vol, lo=lo, hi=hi, g=g, how=how, piece=piece)
        mass = '' if piece == 'base' else ' mass="%.6f"' % (g / 1000)
        geoms[piece].append('<geom name="%s" type="mesh" mesh="%s" rgba="%s"%s/>' % (name, name, rgba(col), mass))

    lo, hi = np.array(TILT_SERVO_BOX) / 1000
    geoms['tilt'].append('<geom name="tilt_servo" type="box" pos="%s" size="%s" rgba="0.16 0.27 0.55 1" mass="%.6f"/>'
                         % (' '.join('%.5f' % v for v in (lo + hi) / 2), ' '.join('%.5f' % v for v in (hi - lo) / 2),
                            HARDWARE['tilt_servo'] / 1000))
    for s in (-1, 1):
        geoms['pan'].append('<geom type="cylinder" fromto="0 %.4f %.4f 0 %.4f %.4f" size="0.0135" rgba="0.6 0.6 0.65 0.5" '
                            'mass="%.6f"/>' % (s * (BEARING_Y - 2) / 1000, H / 1000, s * (BEARING_Y + 2) / 1000, H / 1000,
                                               HARDWARE['tilt_bearings'] / 2000))
    geoms['pan'].append('<geom type="cylinder" fromto="0 0 0.0000 0 0 0.0066" size="0.0258" rgba="0.6 0.6 0.65 0.3" '
                        'mass="%.6f"/>' % (HARDWARE['drum_bearing_inner'] / 1000))
    geoms['pan'].append('<geom type="sphere" pos="0 0 0.016" size="0.003" rgba="0.3 0.3 0.3 1" mass="%.6f"/>'
                        % (HARDWARE['cradle_screws'] / 1000))

    gear = info['input_gear']; gx, gy = (gear['lo'][:2] + gear['hi'][:2]) / 2       # the gear's axis: its centre
    lens_tip = info['camera']['hi'][0]

    # the servo in MuJoCo terms. The motor's own drag (damping = stall / no-load speed) sets its top speed; kp
    # makes it push flat out once it is DEADBAND off target; forcerange is the stall torque. Sliders are in
    # degrees: gear = 180/pi makes the actuator's "length" degrees, so kp and the force limit are per degree.
    DEG = 180 / np.pi
    def servo(torque, speed, deadband):
        damping = torque / speed
        kp = torque / np.radians(deadband)
        return damping, kp / DEG ** 2, torque / DEG
    t_damp, t_kp, t_f = servo(STALL, SPEED, DEADBAND)          # both servos are MG90Ds

    POSTS = '\n    '.join('<geom type="cylinder" pos="%.2f %.2f 0.9" size="0.06 0.93" rgba="%s 1"/>'
                           % (7 * np.cos(a), 7 * np.sin(a), c) for a, c in zip(np.radians(np.arange(0, 360, 45)),
                           ('0.55 0.4 0.3', '0.3 0.5 0.35') * 4))
    def bird(name, pos):
        return (f'''<body name="{name}" mocap="true" pos="{pos}">
      <geom name="{name}_body" type="ellipsoid" size="0.09 0.03 0.028" material="bird"/>
      <geom name="{name}_head" type="sphere" pos="0.085 0 0.012" size="0.022" material="bird"/>
      <geom name="{name}_tail" type="ellipsoid" pos="-0.1 0 0" size="0.05 0.03 0.004" material="bird"/>
    </body>
    <body name="{name}_wing_l" mocap="true" pos="{pos}">
      <geom name="{name}_wl" type="ellipsoid" pos="0 0.085 0" size="0.05 0.08 0.004" material="bird"/>
    </body>
    <body name="{name}_wing_r" mocap="true" pos="{pos}">
      <geom name="{name}_wr" type="ellipsoid" pos="0 -0.085 0" size="0.05 0.08 0.004" material="bird"/>
    </body>''')
    BIRDS = '\n    '.join(bird(n, p) for n, p in (('bird', '3 0 1'), ('bird2', '0 0 -5'), ('bird3', '0 0 -5')))
    xml = f'''<mujoco model="head_v2">
  <!-- Built by sim/mujoco/build_head.py. Don't edit: change the script and rebuild. -->
  <compiler angle="degree" meshdir="meshes"/>
  <option timestep="0.0005" integrator="implicitfast"/>
  <statistic extent="1" center="0 0 0.1"/>   <!-- pinned: the big floor would push the near clip out to 8 cm -->
  <visual><global offwidth="1280" offheight="960"/><map znear="0.005" zfar="60"/><quality shadowsize="4096"/></visual>
  <default>
    <geom contype="0" conaffinity="0"/>
    <mesh scale="0.001 0.001 0.001" inertia="exact"/>
  </default>
  <asset>
{chr(10).join('    <mesh name="%s" file="%s.stl"/>' % (n, n) for n, *_ in PARTS)}
    <texture name="grid" type="2d" builtin="checker" rgb1="0.22 0.24 0.27" rgb2="0.27 0.29 0.32" width="300" height="300"/>
    <material name="grid" texture="grid" texrepeat="40 40"/>
    <material name="wing" rgba="0.95 0.5 0.05 1" emission="0.5"/>
    <material name="bird" rgba="0.12 0.12 0.15 1" emission="0.05"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.55 0.68 0.85" rgb2="0.12 0.14 0.18" width="512" height="512"/>
  </asset>
  <worldbody>
    <light pos="0.15 -0.2 0.4" dir="-0.4 0.5 -1" diffuse="0.8 0.8 0.8"/>
    <light pos="-0.2 0.2 0.3" dir="0.5 -0.5 -1" diffuse="0.35 0.35 0.35" castshadow="false"/>
    <geom name="floor" type="plane" pos="0 0 -0.034" size="12 12 0.01" material="grid"/>
    <!-- something to look at. The red target is a mocap body: move it (double-click it, then Ctrl+right-drag)
         or set it from a script (data.mocap_pos); it's the "point here" goal for learning later -->
    <body name="target" mocap="true" pos="{TARGET[0]} {TARGET[1]} {TARGET[2]}">
      <geom type="sphere" size="0.02" rgba="0.9 0.15 0.1 1"/>
    </body>
    <!-- a butterfly for the head to chase (sim/mujoco/butterfly.py flies it): three mocap bodies, so the
         wings can flap. About 9 cm across, like a real one -->
    <body name="butterfly" mocap="true" pos="0.35 -0.1 0.15">
      <geom name="bf_body" type="capsule" fromto="-0.012 0 0 0.012 0 0" size="0.003" rgba="0.08 0.06 0.05 1"/>
    </body>
    <body name="wing_l" mocap="true" pos="0.35 -0.1 0.15">
      <geom name="bf_wing_l" type="ellipsoid" pos="0 0.023 0" size="0.02 0.022 0.0008" material="wing"/>
    </body>
    <body name="wing_r" mocap="true" pos="0.35 -0.1 0.15">
      <geom name="bf_wing_r" type="ellipsoid" pos="0 -0.023 0" size="0.02 0.022 0.0008" material="wing"/>
    </body>
    <!-- birds for the head to track (sim/mujoco/bird.py flies them, flight.py): pigeon-sized, 33 cm across.
         bird is the one bird.py follows; bird2 and bird3 are extras, parked underground until flown -->
    {BIRDS}
    <!-- posts round the yard, 7 m out, so there's something to see behind the bird -->
    {POSTS}
    <geom type="box" pos="0.55 -0.25 0.02" size="0.05 0.05 0.054" rgba="0.95 0.75 0.2 1"/>
    <geom type="box" pos="0.45 0.35 0.04" size="0.04 0.08 0.074" rgba="0.25 0.5 0.9 1"/>
    <geom type="cylinder" pos="-0.4 0.3 0.06" size="0.04 0.094" rgba="0.3 0.75 0.4 1"/>
    <body name="base">
      {chr(10).join('      ' + g for g in geoms['base']).strip()}
      <body name="input_gear">
        <joint name="pan_input" type="hinge" axis="0 0 1" pos="{gx / 1000:.5f} {gy / 1000:.5f} 0" range="-92 92"
               damping="{t_damp:.6f}" armature="{ROTOR:.6f}"/>
        {chr(10).join('        ' + g for g in geoms['gear']).strip()}
      </body>
      <body name="pan">
        <joint name="pan" type="hinge" axis="0 0 1" range="-182 182" damping="0.0005"/>
        {chr(10).join('        ' + g for g in geoms['pan']).strip()}
        <body name="tilt">
          <!-- + tilt = lens up (the axis points -Y), same as kit.rotated_y and the generator's TILT_DOWN/UP -->
          <joint name="tilt" type="hinge" axis="0 -1 0" pos="0 0 {H / 1000:.4f}" range="-35 145"
                 damping="{t_damp:.6f}" armature="{ROTOR:.6f}"/>
          {chr(10).join('          ' + g for g in geoms['tilt']).strip()}
          <camera name="head_cam" pos="{lens_tip / 1000:.4f} 0 {H / 1000:.4f}" xyaxes="0 -1 0 0 0 1" fovy="100"/>
          <site name="lens" pos="{lens_tip / 1000:.4f} 0 {H / 1000:.4f}" size="0.002" rgba="1 0.2 0.2 1"/>
        </body>
      </body>
    </body>
  </worldbody>
  <equality>
    <!-- the gear pair: the drum turns twice the input gear, the other way round -->
    <joint joint1="pan" joint2="pan_input" polycoef="0 {-PAN_RATIO} 0 0 0"/>
  </equality>
  <actuator>
    <!-- MG90D, datasheet at 4.8 V. Sliders in degrees: tilt as the ball sees it; pan as the HEAD sees it -->
    <position name="tilt_servo" joint="tilt" gear="{DEG:.6f}" kp="{t_kp:.8f}" ctrlrange="-35 145"
              forcelimited="true" forcerange="{-t_f:.8f} {t_f:.8f}"/>
    <!-- the pan servo turns the input gear; gear = -2 x 180/pi reads its angle as the drum's, in degrees -->
    <position name="pan_servo" joint="pan_input" gear="{-DEG * PAN_RATIO:.6f}" kp="{t_kp / PAN_RATIO ** 2:.8f}" ctrlrange="-180 180"
              forcelimited="true" forcerange="{-t_f / PAN_RATIO:.8f} {t_f / PAN_RATIO:.8f}"/>
  </actuator>
  <sensor>
    <jointpos name="tilt_deg" joint="tilt"/>
    <jointpos name="pan_deg" joint="pan"/>
    <actuatorfrc name="tilt_torque" actuator="tilt_servo"/>
    <actuatorfrc name="pan_torque" actuator="pan_servo"/>
  </sensor>
</mujoco>
'''
    path = os.path.join(OUT, 'head.xml')
    with open(path, 'w') as f:
        f.write(xml)
    return path, info


def step_test(m, d, act, joint, target, hold=None, secs=0.6):
    """command one servo from where it is to `target` (deg); returns (secs to within 2 deg, overshoot deg,
    error at the end deg). `hold` sets the other servo's slider."""
    import mujoco
    a, j = m.actuator(act).id, m.joint(joint).qposadr[0]
    if hold:
        d.ctrl[m.actuator(hold[0]).id] = hold[1]
    d.ctrl[a] = target
    start, reach, peak = np.degrees(d.qpos[j]), None, 0.0
    sign = 1 if target >= start else -1
    for i in range(int(secs / m.opt.timestep)):
        mujoco.mj_step(m, d)
        q = np.degrees(d.qpos[j])
        peak = max(peak, sign * (q - target))
        if reach is None and abs(q - target) < 2:
            reach = (i + 1) * m.opt.timestep
    return reach, peak, np.degrees(d.qpos[j]) - target


def report(path, info):
    import mujoco
    m = mujoco.MjModel.from_xml_path(path); d = mujoco.MjData(m)
    print('head.xml: %d bodies, %d meshes, %d joints' % (m.nbody, m.nmesh, m.njnt))
    print('\nMASS (g)  "guess" = volume x %.2f g/cm3 x %.1f fill; replace with slicer grams in SLICER' % (PETG_GF, FILL))
    for n, i in info.items():
        if i['piece'] != 'base':
            print('  %-12s %-5s %6.1f  %s  (%.1f cm3)' % (n, i['piece'], i['g'], i['how'], i['vol'] / 1000))
    for n, g in HARDWARE.items():
        if n != 'camera':
            print('  %-12s       %6.1f  hardware' % (n, g))
    tilt, pan = m.body('tilt').id, m.body('pan').id
    mujoco.mj_forward(m, d)
    mt = m.body_subtreemass[tilt]; cg = d.subtree_com[tilt] * 1000
    off = np.hypot(cg[0], cg[2] - H)
    print('\nTILT PIECE  %.1f g, balance point X %+.1f Z %+.1f from the tilt axis (%.1f mm off it)'
          % (mt * 1000, cg[0], cg[2] - H, off))
    worst = mt * 9.81 * off / 1000
    print('  gravity pulls with up to %.4f N.m = %.0f%% of the MG90D stall torque (%.3f N.m)'
          % (worst, 100 * worst / STALL, STALL))
    print('PAN PIECE   %.1f g turning, tilt piece included' % (m.body_subtreemass[pan] * 1000))

    print('\nSERVO TEST  (datasheet speed: 60 deg in 0.10 s at the servo)')
    rows = [('tilt  0 -> +60', 'tilt_servo', 'tilt', 60.0, None),
            ('tilt +60 -> -35', 'tilt_servo', 'tilt', -35.0, None),
            ('pan   0 -> +180', 'pan_servo', 'pan', 180.0, ('tilt_servo', 0.0)),
            ('pan +180 -> -180', 'pan_servo', 'pan', -180.0, ('tilt_servo', 0.0))]
    mujoco.mj_resetData(m, d)
    for label, act, joint, target, hold in rows:
        if label.startswith('pan   0'):
            mujoco.mj_resetData(m, d)
        reach, over, err = step_test(m, d, act, joint, target, hold)
        print('  %-17s within 2 deg after %s, overshoot %.1f deg, off by %+.2f deg at rest'
              % (label, '%.3f s' % reach if reach else 'NEVER', over, err))
    gear = np.degrees(d.qpos[m.joint('pan_input').qposadr[0]]); panq = np.degrees(d.qpos[m.joint('pan').qposadr[0]])
    print('  gear pair: head at %+.1f deg, input gear at %+.1f deg (should be -1/2 of it)' % (panq, gear))
    return m


def picture(m):
    """two views into out/: the head from the front-left, and what the head's camera sees"""
    import mujoco
    from PIL import Image
    d = mujoco.MjData(m)
    # aim the head at the red target, so the camera view shows it centred
    t = np.array(TARGET) - (0, 0, H / 1000)
    pan, tilt = np.arctan2(t[1], t[0]), np.arctan2(t[2], np.hypot(t[0], t[1]))
    d.qpos[m.joint('tilt').qposadr[0]] = tilt; d.qpos[m.joint('pan').qposadr[0]] = pan
    d.qpos[m.joint('pan_input').qposadr[0]] = -pan / PAN_RATIO
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 720, 960)
    cam = mujoco.MjvCamera(); cam.lookat[:] = (0.02, 0, 0.03); cam.distance = 0.30; cam.azimuth = 205; cam.elevation = -20
    r.update_scene(d, cam); a = r.render()
    r.update_scene(d, 'head_cam'); b = r.render()
    Image.fromarray(np.hstack([a, b])).save(os.path.join(OUT, 'head.png'))
    r.close()


if __name__ == '__main__':
    path, info = build()
    m = report(path, info)
    picture(m)
    print('\nwrote', path, 'and out/head.png')
