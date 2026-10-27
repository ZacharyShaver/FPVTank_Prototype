# Dead on average is not dead at the front

2026-10-27, the gauge search (`gauges/search.py`).

**What happened.** The review of the drive search ranked its 27 knobs with a random forest's permutation importance
over every screened design. 14 knobs scored under 1 % on every gauge: the packs' place, the middle axle, the skin's
shape, the push angle, the tail's mount height and the motor's size. The review called them dead and proposed
freezing them. Before freezing, `frozen_check` redrew all 14 at random on four finalists, with tail length and torque
redrawn as the control. The claim failed: T10 went from 0.94 / 100 mm / 404 mm to 0.76 / 54 / 505, about as far as the
control moved it (0.55 / 75 / 420).

**Why.** Most screened designs are poor (B: 14 % clear the upright bar), and on a poor design nothing but the big knobs
matters. The importance is an average over the whole space, so it ranks what separates bad designs from middling
ones. Near the front, a tuned design depends on knobs that do nothing elsewhere: the push angle and the mount height
only count once a tail can lift the robot.

**What held up.** One knob at a time (`frozen_each`), three moved no gauge, or only for the worse: the middle axle,
the packs' height and the motor's size. Only those were frozen as dead. The skin's shape moves a skinned design's
climb, and is held at T5's by choice, not because it doesn't matter.

**Rule.** Check a claim that a knob does nothing where the decision will act, near the front, and redraw the knob
there, against a control knob that must move.
