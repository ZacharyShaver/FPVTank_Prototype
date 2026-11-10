"""Print noise on the peg joints (2026-11-09). Zach, after the box plates: "the pla inside of the connection holes and stubs can warp
or have defects rendering it impossible to assemble", and, from the ST5 history behind gauges/noisy.py: "designing with noise in
mind ... simulating these objects and attempting to assemble them might help". This is that screen in its cheapest form: geometry
and dice, no physics. Each trial prints a box and a floor slightly wrong, then looks for the best way to seat one in the other.

    python twin/print_noise.py          # the tables, and the controls

What it varies, each feature on its own: every peg's and every hole's centre (sd s, each axis) and diameter (sd s).
What it leaves out: warp, a leaning peg, blobs at the seam, and a scale error (box and floor come off one printer, so that cancels).
Those only make it worse, so the table is the kind side of the truth.

How it reads a trial: zero is the fit he picked on the bench, a 5 mm peg in a 5.1 hole, "slightly tight with a little snap". The
box may shift and turn to find its best seat. The number is how much the worst peg is squeezed past that fit, on the radius.
His bench gives the scale on the loose side only: 0.05 looser (5.2) "works", 0.10 looser (5.3) "will fall out". * No row was
tighter than 5.1, so how much squeeze a hand can press is a guess: 0.05, one row step.

* = guessed. Nothing here is measured on his printer yet: s is the knob, and one caliper reading places his printer in the table.
"""
import numpy as np
from scipy.optimize import minimize

ROW = 7.5
JOINTS = dict(                      # peg centres, from part_boxes.py (ESC_PEGS, PACK_PEGS, PI_PEGS, BOARD_PEGS, a spacer's two)
    one=[(0.0, 0.0)],
    spacer=[(0.0, -ROW), (0.0, ROW)],
    board=[(x, y) for x in (-15.0, 15.0) for y in (-ROW, ROW)],
    esc=[(x, y) for x in (-15.0, 0.0, 15.0) for y in (-ROW, ROW)],
    pi=[(x, y) for x in (-45.0, -15.0, 15.0, 30.0) for y in (-22.5, 22.5)],
    pack=[(x, y) for x in (-60.0, -30.0, 0.0, 30.0, 60.0) for y in (-ROW, ROW)])
NAMES = dict(one='one peg', spacer='spacer, 2', board='PCA / ESP32, 4', esc='ESC, 6', pi='Pi sleeve, 8', pack='pack, 10')
PRESS = 0.05                        # * mm on the radius a hand can still press: one row step of his patch
LOCATE, BACKUP = 0.20, 0.50         # room on the radius against the bench fit: spring_stack.py's 4.6 and 4.0 pegs, in the same 5.1 holes. 0.15 and 0.30 (4.7, 4.4) read 60 % for the ESC box at s 0.10; these read 94 %
SIGMAS = (0.02, 0.05, 0.10, 0.15)
TRIALS = 300


def seat(P, H):
    """the least-squares shift and turn of P onto H: where the search starts"""
    pc, hc = P.mean(0), H.mean(0)
    A, B = P - pc, H - hc
    t = np.arctan2(np.sum(A[:, 0] * B[:, 1] - A[:, 1] * B[:, 0]), np.sum(A * B))
    return pc, hc, t


def worst_squeeze(P, H, c):
    """the least the worst peg can be squeezed, over every shift and turn of the box. c: each peg's own room on the radius"""
    if len(P) == 1:
        return float(-c[0])
    pc, hc, t0 = seat(P, H)
    reach = max(float(np.linalg.norm(P - pc, axis=1).max()), 1.0)       # the turn is searched as mm at the farthest peg

    def worst(v):
        t = t0 + v[2] / reach
        R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
        return float(np.max(np.linalg.norm((P - pc) @ R.T + hc + v[:2] - H, axis=1) - c))
    simplex = np.vstack([np.zeros(3), 0.05 * np.eye(3)])               # start from the least-squares seat, in 0.05 mm steps
    return float(minimize(worst, np.zeros(3), method='Nelder-Mead', options=dict(initial_simplex=simplex, xatol=1e-4, fatol=1e-5, maxiter=800)).fun)


def trial(xy, s, room, rng):
    N = np.asarray(xy, float)
    P = N + rng.normal(0, s, N.shape)
    H = N + rng.normal(0, s, N.shape)
    c = room + (rng.normal(0, s, len(N)) - rng.normal(0, s, len(N))) / 2      # hole grew, less peg grew, on the radius
    return worst_squeeze(P, H, c)


def two_locate(xy):
    """spring_stack.py's joint: the two pegs on one diagonal locate, the rest stand clear"""
    r = np.full(len(xy), BACKUP)
    r[0] = r[-1] = LOCATE
    return r


def share(xy, room, s, limit=0.0, trials=TRIALS, seed=1):
    """the share of prints that go together. room: a number, or a function of the pegs giving each its own"""
    rng = np.random.default_rng(seed)
    r = room(xy) if callable(room) else room
    return float(np.mean([trial(xy, s, r, rng) <= limit for _ in range(trials)]))


def run(room=0.0, seed=1):
    out = {}
    for k, xy in JOINTS.items():
        r = room(xy) if callable(room) else room
        for s in SIGMAS:
            rng = np.random.default_rng(seed)
            out[k, s] = np.array([trial(xy, s, r, rng) for _ in range(TRIALS)])
    return out


def controls():
    rng = np.random.default_rng(0)
    ok = True
    z = max(abs(trial(xy, 0.0, 0.0, rng)) for xy in JOINTS.values())
    print('  %-58s %s  %.4f' % ('no noise: every joint reads the bench fit, 0', 'ok ' if z < 1e-3 else 'BAD', z)); ok &= z < 1e-3
    N = np.asarray(JOINTS['pack'], float); P = N.copy(); P[0, 0] += 0.4
    v = worst_squeeze(P, N, np.zeros(len(N)))
    print('  %-58s %s  %.3f' % ('control: one pack peg 0.4 out of place reads as a squeeze', 'ok ' if v > 0.1 else 'BAD', v)); ok &= v > 0.1
    t = np.radians(3.0); R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    v = worst_squeeze(N @ R.T + (0.7, -0.3), N, np.zeros(len(N)))
    print('  %-58s %s  %.4f' % ('a box only shifted and turned finds its seat again, 0', 'ok ' if abs(v) < 2e-3 else 'BAD', v)); ok &= abs(v) < 2e-3
    return ok


def table(R, limit, title):
    print(title)
    print('  %-16s' % 'joint' + ''.join('  s %.2f      ' % s for s in SIGMAS))
    for k in JOINTS:
        print('  %-16s' % NAMES[k] + ''.join('  %3.0f %% %5.2f ' % (100 * np.mean(R[k, s] <= limit), np.percentile(R[k, s], 90)) for s in SIGMAS))


if __name__ == '__main__':
    print('Controls:'); good = controls()
    print('\nEach cell: the share of prints that go together, then the worst peg\'s squeeze in the unlucky 1 in 10 (mm on the radius).')
    print('s = how far off each printed feature is, 1 sd, in mm. Not measured on his printer yet.\n')
    table(run(0.0), PRESS, 'Now: 5.1 holes, the pegs hold by friction. Goes together = no peg squeezed over %.2f (* guessed)' % PRESS)
    print()
    table(run(0.15), 0.0, 'Loose pegs: 5.4 holes, the pegs only locate and something else holds. Goes together = nothing squeezed at all')
    print()
    table(run(two_locate), 0.0, 'Drawn in spring_stack.py: two 4.6 pegs locate, the rest are 4.0 and stand clear, in 5.1 holes. Goes together = nothing squeezed at all')
    print('\ncontrols', 'ok' if good else 'BAD')
