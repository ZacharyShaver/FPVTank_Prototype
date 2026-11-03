# A contact parameter is not a physical number

2026-11-03, a code and math review (`docs/audit/2026-11-03-code-and-math-review.md`), `gauges/robots.py`,
`gauges/drops.py` and `gauges/course.py`.

**What happened.** Two MuJoCo contact settings did something other than what their comments said.
- The tyres' spring (`tyre_k`, "N/mm") and the TPU bumpers' went into MuJoCo's direct `solref` as written. MuJoCo
  reads those values per unit mass: a contact sinks the same depth under any load. So a 30 N/mm tyre landed like a
  30 × m spring, m being the mass on it: about 15 N/mm on a 2 kg robot's tyre. The bumpers came out stiffer than
  labelled. The test: a ball of 0.5 kg and one of 2 kg each stayed on the "30 N/mm" contact 18.2 ms. A spring holds
  them 12.8 and 25.7 ms.
- The tyres have contact priority, so their own friction wins on every surface. The obstacle course gave its rocks
  and ridge G8's ×2.5 grip, but only on the terrain's side, so the tyres met them at ×1 (0.9, not 2.25). The course
  wasn't built from the gauges' terrain after all.

**Why it slipped.** Each setting was checked by its outcome ("30 N/mm makes it 7 times the weight"; the course's
controls stop the box), never against the physics it claimed. A spring has one clean test: its contact time against
π√(m/k) at two masses. A friction has another: read `d.contact[i].friction` for the pair.

**How to apply.** When a sim parameter carries a physical unit or names a property ("N/mm", "x2.5 grip"), test it
against that physics directly, with a second mass or the other geom of the pair as the control: `robots.py spring`,
and `course.py grip`. Do this before a real measurement is plugged in. This week's tyre caliper
numbers would have gone in wrong. Related: `2026-10-02-an-sdf-value-is-a-bound.md`.
