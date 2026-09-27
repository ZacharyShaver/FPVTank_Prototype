# A cut must overrun the face it passes through — and a part must be able to reach its seat

**2026-09-19.** Two faults, each hit twice in one day, on the variant B head
(`head-v2/generator/generators/tree_parts_b.py`).

---

## 1. Coincident faces

**The rule: in this SDF model, a cut must always overrun the face it passes
through. It must never stop flush with it.**

Twice in one session, a cut was given an end plane exactly equal to the end
plane of the thing it cut through. Both times the solid was fine — `scipy.ndimage.label`
confirmed a single connected component — and both times the *mesh* was wrong:

| | symptom |
|---|---|
| `ball_minus`: axle socket bore ended at Y −19.0, exactly the socket hub's end face | bodies=2, self-int=6, decimator stalled at **44k faces against a 20k target** |
| `fork`: bearing pass-bore started at Y 30.5, exactly where the bearing seat ended | bodies=1 but self-int=28, decimator stalled at **132k against 60k** |

Marching cubes renders two coplanar surfaces as a zero-thickness skin. It is
watertight and manifold, so those flags do not catch it. The tell is the **face
count**: a part that blew past its decimation target did not decimate, because
the mesher choked on something degenerate.

Both times the face count was printed in the build output and went unread.
`mesh_qa_b.py` now flags it: `<-- DECIMATOR STALLED: n faces against a t target`.

The fix in both cases was one number — overrun by 0.1 mm into a region that is
void anyway, so nothing else changes.

**Do not reach for `scipy.ndimage.label` first.** It answers "is the solid
connected", which was *yes* both times. It is the right tool for the loose-rib
trap (a rib whose corners stop short of the shell) and the wrong one here.

`tree_parts_b_health.py` now lists every Y plane the model uses, tagged by part,
and flags two features of the **same part** landing on one plane. Faces of
*different* parts meeting is just contact and is fine — the post's flange is
supposed to land on the collar's recess floor.

---

## 2. Nothing tested whether a part can get to its seat

Three faults in one day shared a root cause: every check asked *where parts end
up*, none asked *how they get there*.

- the axle sat 1.95 mm inside the camera board
- the −Y pad ran the full width of the ball, straight through that board
- **both bearing seats stepped down to a smaller bore on both sides** — sealed
  pockets. The bearing could only ever have arrived by being printed in place,
  and the README confidently said to press it in from outside

The third was found by Zach looking at the viewer, not by any check. So was the
first.

`tree_parts_b_insert.py` now slides each inserted part back out along its
assembly path and reports the first thing it hits, on the principle that **a
part that cannot come out cannot go in**. Negative control against the pre-fix
geometry: both collars blocked within 0.5 mm; after, clear over 9 mm.

There are now three checks answering three different questions, and all three
are needed:

| script | question |
|---|---|
| `tree_parts_b_check.py` | do parts overlap where they end up? |
| `tree_parts_b_driver.py` | can a screwdriver reach each screw, at its step? |
| `tree_parts_b_insert.py` | can each part physically reach its seat? |

---

## 3. The habit worth keeping

Every new check row got a **negative control** — run it against the geometry
from before the fix and confirm it reports the fault. The camera-vs-axle row
scores 39.74 mm³ against the old axle and 0.00 against the new one; the
insertion rows block at 0.0–0.5 mm on the old collars.

A row that has only ever returned zero has not been shown to be capable of
returning anything else. Three rows were added this day that read zero while
the geometry was wrong.
