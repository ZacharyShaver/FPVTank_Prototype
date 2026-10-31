# The sim passed robots that can't be built

2026-10-31, the capability searches (`gauges/capability.py`) and the one-piece grower (`gauges/unibody.py`).

**What happened.** The search's winners were grown into one printable piece (`unibody.design_knobs`): the body
round its parts, a pod to each motor, the tail's boss. On the full gauges every one read less step: T3 150 to 30 mm,
the low step-and-turn winner 175 to 100. The search had weighed the body as a 1.5 mm skin, or as the Trainer's 415 g
tub; the printed shell weighs 0.8-1.2 kg more, and the low winner's servos had been picked just strong enough for the
lighter robot (19 % more servo torque read 175 mm again). The strict build also passed the picked gearmotor running
7-12 mm into the battery packs and ESCs (T3 too), and flippers pivoting 60-100 mm off the body.

**Then the gauge itself.** Checking the one piece against a cheaper realistic build found that T3, at the one piece's
weight, reads 50, 90 or 150 mm on the step from one set of random tries to the next. The ladder (the tallest rung
where 18 of 20 tries pass, every lower rung too, worst of three floors) flips on a single unlucky rung for any design
near its limit. Readings taken once, a few tens of mm apart, said nothing; a theory built on them (the skin over T3's
wheels as a ramp) was wrong and was taken back. The grower also dropped a given two-link tail's elbow, rear-up and foot
when it re-attached the tail, so the low winners' one pieces were gauged with a shorter, plainer tail (fixed).

**Why it slipped.** The strict build (2026-10-28) checked that parts touch the body, not that the body as printed
could hold them, weigh what it weighs, or leave room for the motor beside the packs. And no one had read the same
design twice with different seeds: the step gauge's repeatability was never tested.

**How to apply.** Before trusting a search's winner, build it the expensive, realistic way and read the gauges again.
Before comparing two readings, know the gauge's spread on one design: read it with two or more seed sets, and treat a
difference inside that spread as nothing. The search now has a real build (`knobs.make(real=True)`, run
`capability_real`): the printed weight (fitted to 36 grown shapes, 3.9 % mean error; within 0.5 % of the grown one
piece on the four winners), the motors' pods, the motor's fit beside the parts and flipper mounts, each with a control
(`python gauges/knobs.py real`). Zach: "an unrealistic robot in simulation can tell us things about design ... it
cannot give us a workable design ... the system works if the tests can be trusted". Related:
`2026-10-31-a-new-part-must-reach-every-measure.md`, `2026-10-28-parts-are-not-a-body.md`.
