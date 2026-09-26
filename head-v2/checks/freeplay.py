"""How far does a clicked pin slide inside ONE socket? Push the pin along its axis by d and measure its
overlap with the test block. Overlap > 0 = something is touching (the barb's back on the neck edge when
pulled back, the tip on the end cone when pushed in). A run of zeros = free play.
Negative control: the first pins (no stop), which Zach found sliding 0.75 mm on the test block."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import *
from snap import socket, pin, BARBS, SOCKET_DEPTH
from record import record
plate = bx((-7, 0, -7), (7, 2.0, 7))
post = cyl('y', (0.0, 0.0), 4.0, 0, SOCKET_DEPTH + 1.5)
block = cut(fuse(plate, post), socket((0.0, 0.0), +1))
def curve(p):
    ds = np.round(np.arange(-0.20, 1.21, 0.05), 3)
    return ds, np.array([overlap(moved(p, 0, d, 0), block) for d in ds])
if __name__ == '__main__':
    for nm, br in BARBS.items():
        for nose in (False, True):
            p, lh = pin(br, nose)
            ds, ov = curve(p)
            free = ds[ov < 1e-4]
            land_back = 8.0 + (br - 2.2)
            print('%-6s %-9s length %.1f   free play %-22s  both ends click while it sits within +-%.2f'
                  % (nm, 'WITH stop' if nose else 'first pin', 2 * lh,
                     ('%.2f..%.2f (%.2f mm)' % (free.min(), free.max(), free.max() - free.min())) if len(free) else 'none',
                     land_back - 8.25))
            if nm == 'medium':
                print('        ' + ' '.join('%+.2f:%.2f' % (d, o) for d, o in zip(ds, ov)))
                record('free_play_%s' % ('stop' if nose else 'first'),
                       float(free.max() - free.min()) if len(free) else None)
