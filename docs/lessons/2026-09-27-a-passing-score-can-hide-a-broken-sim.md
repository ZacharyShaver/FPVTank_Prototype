# 2026-09-27: A passing score can hide a broken simulation

From the first MuJoCo session (`sim/mujoco/`). The bird tracker's self-test passed on its first run:
learned beat hold, on target and on smoothness, and tracking-off failed as the control should. Two of
its numbers were still wrong, and both errors were in the simulation, not the tracker.

## What gave it away

The trained tracker was on target 79% of the time, yet its mean miss was 13°. Most frames were close,
so a minority had to be off by a lot. "In frame" was only 85%.

## What was actually wrong

Every unseen frame was sorted by cause: lost and sweeping, out of view, or in view but not detected.
Then each large miss was grouped into episodes, with what the bird and the head were doing at the time.
- **The flight model let birds sink through the floor.** 95% of the training birds dipped under
  0.25 m, and some went 1.4 m underground. The floor hid them. The "stay above 0.5 m" steering was too
  gentle, and the distance limit let birds wander to 9.5 m.
- **A phantom sighting.** Before its first move, the bird sat at its placeholder spot, straight ahead.
  The first frame "saw" it there, so the head started the wrong way. It also defeated the fix meant
  to score from the first sighting: that sighting was the phantom.

With both fixed, mean miss fell from 13° to 4.9°. Every remaining miss over 20° was one real thing:
the pan's ±180° stop, when the bird circles behind the head.

## Do

- A passing comparison doesn't prove the numbers. When an average and a typical case disagree, find
  the minority behind the gap before trusting either.
- Sort the failures by cause, then look at the worst episodes one by one. The cause is often in the
  test rig, not the thing under test.
- Check a simulated world's own limits directly (lowest bird, furthest bird) with a before/after, just
  as a fit check needs its negative control.
