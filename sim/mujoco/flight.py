"""A bird flying round the robot, and what the head camera sees of it. Used twice: to make training data
(thousands of birds at once, no rendering) and to fly the one bird in the MuJoCo scene.

The flight is smooth but unpredictable: speed, turn rate and climb each drift at random (an
Ornstein-Uhlenbeck process: a random walk that is pulled back toward a typical value), and the bird
steers back when it strays outside 1.5-5 m from the robot or 0.5-2.5 m up. It flaps for a while, then
glides. Units: m, s, radians inside; degrees for the angles the camera sees.
"""
import numpy as np

PIVOT = np.array([0.0, 0.0, 0.052])         # the head's pivot: the tilt axis over the pan axis
FLOOR = -0.034
R_MIN, R_MAX = 1.5, 5.0                     # how far from the robot it stays, m
Z_MIN, Z_MAX = 0.5, 2.5                     # how high, m above the floor
V0, V_SD, V_TC = 4.0, 1.2, 2.0              # speed: typical 4 m/s (a pigeon cruising), wanders +-1.2
W_SD, W_TC = 1.2, 1.5                       # turn rate, rad/s: typical turns of ~3 m radius
G_SD, G_TC = 0.25, 1.5                      # climb angle, rad
FLAP_HZ, BOB = 7.0, 0.012                   # wingbeat, and how much the body bobs with it (m)

FPS = 30                                    # camera frames a second
N_HIST = 12                                 # sightings the predictor looks back over (0.4 s)
HORIZONS = np.arange(11) * 0.05             # it predicts 0, 50, ... 500 ms after the newest frame


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class Flight:
    """n birds at once. step(dt) moves them; pos() is where the body is, bob included."""

    def __init__(self, n, rng):
        self.rng, self.n = rng, n
        r, th = rng.uniform(2.0, 4.0, n), rng.uniform(-np.pi, np.pi, n)
        self.p = np.stack([r * np.cos(th), r * np.sin(th), FLOOR + rng.uniform(0.8, 2.0, n)], 1)
        self.psi = th + np.pi / 2 * rng.choice([-1, 1], n) + rng.normal(0, 0.3, n)
        self.v = np.clip(rng.normal(V0, V_SD, n), 1.5, 8.0)
        self.w = rng.normal(0, W_SD, n)
        self.g = rng.normal(0, G_SD, n)
        self.t = 0.0
        self.flapping = np.ones(n, bool)
        self.switch = rng.uniform(0.5, 2.0, n)   # time left in this flap or glide

    def _ou(self, x, mean, sd, tc, dt):
        return x + (mean - x) / tc * dt + sd * np.sqrt(2 * dt / tc) * self.rng.normal(size=self.n)

    def step(self, dt):
        self.v = np.clip(self._ou(self.v, V0, V_SD, V_TC, dt), 1.5, 8.0)
        self.w = self._ou(self.w, 0.0, W_SD, W_TC, dt)
        self.g = self._ou(self.g, 0.0, G_SD, G_TC, dt)
        x, y, z = self.p.T
        r, out = np.hypot(x, y), np.arctan2(y, x)
        # steer home: turn toward the inside of the ring when too far, outward when too close
        far, near = np.clip((r - R_MAX) / 0.5, 0, 1), np.clip((R_MIN - r) / 0.5, 0, 1)   # firm: 2.5 let them reach 9.5 m
        home = 4.0 * far * wrap(out + np.pi - self.psi) + 4.0 * near * wrap(out - self.psi)
        h = z - FLOOR
        climb = 3.0 * np.clip((Z_MIN - h) / 0.4, 0, 1) - 3.0 * np.clip((h - Z_MAX) / 0.4, 0, 1)   # firm: it swooped into the floor at 0.8
        self.psi = wrap(self.psi + (self.w + home) * dt)
        g = np.clip(self.g + climb, -0.6, 0.6)
        self.p = self.p + dt * self.v[:, None] * np.stack([np.cos(g) * np.cos(self.psi),
                                                           np.cos(g) * np.sin(self.psi), np.sin(g)], 1)
        self.switch -= dt
        flip = self.switch <= 0
        self.flapping[flip] = ~self.flapping[flip]
        self.switch[flip] = np.where(self.flapping[flip], self.rng.uniform(0.8, 2.5, flip.sum()),
                                     self.rng.uniform(0.3, 1.2, flip.sum()))
        self.t += dt

    def pos(self):
        bob = np.where(self.flapping, BOB * np.sin(2 * np.pi * FLAP_HZ * self.t), 0.0)
        return self.p + np.stack([0 * bob, 0 * bob, bob], 1)

    def heading(self):
        return self.psi


def direction(p):
    """(az, el) in degrees of points p (..., 3) seen from the head's pivot"""
    d = p - PIVOT
    return np.degrees(np.arctan2(d[..., 1], d[..., 0])), np.degrees(np.arctan2(d[..., 2], np.hypot(d[..., 0], d[..., 1])))


def features(az, el, valid):
    """The predictor's input, from the last N_HIST sightings (oldest first): az, el in degrees (B, N),
    valid (B, N) False where the detector missed. Everything is relative to the newest good sighting,
    so the model learns motion, not place. Returns (x (B, 3N+1), ref_az (B,), ref_el (B,))."""
    B, N = az.shape
    last = N - 1 - np.argmax(valid[:, ::-1], axis=1)             # newest valid slot per row
    ref_az, ref_el = az[np.arange(B), last], el[np.arange(B), last]
    daz = np.degrees(wrap(np.radians(az - ref_az[:, None])))
    dee = el - ref_el[:, None]
    daz, dee = np.where(valid, daz, 0.0), np.where(valid, dee, 0.0)
    x = np.concatenate([daz / 10, dee / 10, valid.astype(float), (ref_el / 45)[:, None]], 1)
    return x.astype(np.float32), ref_az, ref_el


def make_data(n_birds, secs, rng, rate=120):
    """Flights seen by a 30 fps camera with jitter and missed frames. Returns the predictor's inputs,
    the true future (daz, del) at HORIZONS relative to the newest good sighting, and ref_el."""
    fl = Flight(n_birds, rng)
    dt, steps = 1.0 / rate, int(secs * rate)
    per_frame, per_h = rate // FPS, int(round(0.05 * rate))
    true_p, seen_p = np.empty((steps, n_birds, 3)), np.empty((steps, n_birds, 3))
    for i in range(steps):
        fl.step(dt)
        true_p[i], seen_p[i] = fl.p, fl.pos()                    # truth: the smooth path; seen: with bob
    t_az, t_el = direction(true_p)
    s_az, s_el = direction(seen_p)
    # the camera: every per_frame steps, with jitter (per bird, 0.2-1.2 deg) and misses (0-15%)
    frames = np.arange(0, steps, per_frame)
    noise = rng.uniform(0.2, 1.2, n_birds); miss = rng.uniform(0.0, 0.15, n_birds)
    f_el = s_el[frames] + rng.normal(size=(len(frames), n_birds)) * noise
    f_az = s_az[frames] + rng.normal(size=(len(frames), n_birds)) * noise / np.cos(np.radians(s_el[frames]))
    f_ok = rng.random((len(frames), n_birds)) > miss
    X, Y, E = [], [], []
    last_needed = (len(HORIZONS) - 1) * per_h
    for k in range(N_HIST - 1, len(frames)):
        i_now = frames[k]
        if i_now + last_needed >= steps:
            break
        ok = f_ok[k - N_HIST + 1:k + 1].T
        keep = ok.any(1)
        x, ref_az, ref_el = features(f_az[k - N_HIST + 1:k + 1].T, f_el[k - N_HIST + 1:k + 1].T, ok)
        fut = i_now + np.arange(len(HORIZONS)) * per_h
        yaz = np.degrees(wrap(np.radians(t_az[fut].T - ref_az[:, None])))
        yel = t_el[fut].T - ref_el[:, None]
        X.append(x[keep]); Y.append(np.concatenate([yaz, yel], 1)[keep] / 10); E.append(ref_el[keep])
    return np.concatenate(X), np.concatenate(Y).astype(np.float32), np.concatenate(E)


# ---- the two hand-made predictors the learned one has to beat
def predict_hold(x):
    """today's tracker: the bird stays where it was last seen"""
    return np.zeros((len(x), 2 * len(HORIZONS)), np.float32)


def predict_line(x, k=6):
    """constant velocity: fit a straight line through the last k good sightings and extend it"""
    N = N_HIST
    daz, dee, ok = x[:, :N] * 10, x[:, N:2 * N] * 10, x[:, 2 * N:3 * N] > 0.5
    t = (np.arange(N) - (N - 1)) / FPS
    w = ok & (np.arange(N) >= N - k)
    out = np.zeros((len(x), 2 * len(HORIZONS)), np.float32)
    for c, v in ((0, daz), (1, dee)):
        sw = w.sum(1); st = (w * t).sum(1); sv = (w * v).sum(1)
        stt = (w * t * t).sum(1); stv = (w * t * v).sum(1)
        den = sw * stt - st ** 2
        slope = np.where(den > 1e-12, (sw * stv - st * sv) / np.where(den > 1e-12, den, 1), 0.0)
        icpt = np.where(sw > 0, (sv - slope * st) / np.maximum(sw, 1), 0.0)
        out[:, c * len(HORIZONS):(c + 1) * len(HORIZONS)] = (icpt[:, None] + slope[:, None] * HORIZONS[None]) / 10
    return out


class Learned:
    """the trained network, run in plain numpy (no torch needed to use it, so it can go on the Pi)"""

    def __init__(self, path):
        z = np.load(path)
        self.W = [(z['W%d' % i], z['b%d' % i]) for i in range(len(z.files) // 2)]

    def __call__(self, x):
        h = x
        for i, (W, b) in enumerate(self.W):
            h = h @ W + b
            if i < len(self.W) - 1:
                h = np.maximum(h, 0)
        return h
