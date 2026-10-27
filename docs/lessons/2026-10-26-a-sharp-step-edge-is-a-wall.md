# 2026-10-26: In MuJoCo, a sharp step edge is a wall to a cylinder tyre

From the first run of the step-up gauge (`gauges/`). The Trainer's 110 mm wheels stalled at a 10 mm step in
1 try of 5, and stopped dead at 30 mm. A wheel that size should roll up both.

## What was actually wrong

The tyre is a cylinder and the step a box. MuJoCo's contact between them starts out right, its normal along
the line from the edge to the axle, and then flickers to the box face's normal, (1, 0, 0). The tyre then
pushes on a vertical wall and spins in place. `gauges.edge_normal` measures it: the worst normal in the first
0.3 s of contact is 60–66° off radial on every design with the sharp edge, and under 1° with the edge rounded.

The fix rounds the step's top edge to 3 mm (a capsule along it, the face 3 mm behind). With it, the Trainer
climbs 10–30 mm in 20 of 20 tries. It stops at 40 mm for a real reason: the box's nose, 32 mm off the floor and
ahead of the wheels, meets the step first.

chassis3's steps have the sharp edge. Its climb numbers (the Trainer "climbs" 0.04) carry the fault. Its
step-down numbers may too, since the tyre rolls off that same edge; they haven't been rechecked.

## Do

- Look at the contact normals at the first odd stall, before tuning anything else. A tyre spinning while the
  body stands still is the sign.
- Check a contact in sim against the obvious real case: a wheel climbs a step well under its radius.
- Keep the old model as the control. With the sharp edge, `python gauges/gauges.py port` reproduces chassis3's
  stalls, and the edge check must read high on it.
