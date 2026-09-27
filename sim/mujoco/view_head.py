"""Open the head in MuJoCo's viewer. Builds out/head.xml first if it isn't there.

In the window:
  right-hand panel, Control   the two servo sliders, in degrees (tilt -35..145, pan -180..180)
  double-click a part         selects it
  Ctrl + right-drag           shoves the selected part (the servo pushes back)
  Ctrl + left-drag            twists it
  left-drag / right-drag      orbit / pan the view; scroll zooms
  Tab / Shift+Tab             hide / show the side panels
  Space                       pause
  Camera dropdown (left panel, Rendering) -> head_cam   look through the head's camera
"""
import os, sys, subprocess
import mujoco
import mujoco.viewer

HERE = os.path.dirname(os.path.abspath(__file__))
XML = os.path.join(HERE, 'out', 'head.xml')

if __name__ == '__main__':
    if not os.path.exists(XML) or '--build' in sys.argv:
        subprocess.run([sys.executable, os.path.join(HERE, 'build_head.py')], check=True)
    m = mujoco.MjModel.from_xml_path(XML)
    mujoco.viewer.launch(m, mujoco.MjData(m))
