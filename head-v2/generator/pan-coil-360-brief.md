# Pan coil — 360° continuous pan, ribbon captured in the base

**Written 2026-09-19**, from a design session with Zach. This is the item the
variant B handoff left open as §0.3: *"a ribbon coil captured in the trunk
base, so pan can go 360° continuously instead of ±90°."*

This is a **chassis-v2 working brief**, like `../body-revision-brief.md` and
`ball-head-validation-handoff.md` — **not a phase**. If it becomes a phase it
needs a spec first (CLAUDE.md loop). Test results drain to `docs/bench/` the
moment they are observed.

**Lane note:** a parallel session owns the variant B head
(`generators/tree_parts_b.py` and its checks). Nothing in this brief touches
those files. Where this design wants something from the head, it is written
here as a *request*, not applied.

---

## 1. The problem

Variant B's ribbon leaves the nest's underside about **9 mm forward of the pan
axis**, so panning drags it. Pan is limited to ±90° and the README has carried
*"routing it down the pan axis is unsolved"* since the first write-up. This is
that problem solved properly, and it buys 360° while it is at it.

A slip ring is not the answer: the camera link is a CSI differential pair and
will not survive sliding contacts. The ribbon has to stay continuous, which
means a coil with end stops, not unlimited rotation.

## 2. Decisions — Zach's, 2026-09-19

Taken in session, in this order. Reversals are marked where they happened.

| Decision | Choice | Note |
|---|---|---|
| Travel wanted | **360° usable**, mechanism built for ±270° (540°) | the margin lives in the mechanism, where it is nearly free |
| Coil type | rolling loop in a flat can, **inner drum rotates**, outer well fixed to the body | matches `pan_coil.py`; keeps the deck hole round, not an annular slot |
| Where the ribbon leaves the can | **out the side (−Y), from the bottom of the can** — not the front, not wrapped round | Zach, 2026-09-19. `EXIT_DEG`, one number. −Y over +Y because the servo tower sits on +Y. Travel does not depend on it — only on `L`, `ri`, `ro` — so it is free to move. Clear of the wall the ribbon turns aft freely: a bend in its own plane, not a crease |
| How the servo gets in | **side window**, sliding along its own long axis | Zach, 2026-09-19. See §4 |
| Which member rotates | drum, hanging from the head | |
| Pan drive | **180° MG90D + 2:1 printed step-up**, servo **off-axis** | ⟲ reverses the earlier "fixed servo island in the middle" — see the drive note below |
| Position feedback | none needed; the servo is absolute | ⟲ reverses "software limit + home switch", which is moot once the drive is positional again |
| Where the 90° twist lives | ⚠ **in the trunk, above the deck** — *chosen, then found not to fit* | it rotates with the head, so it is set once at assembly and never cycles. **The trunk is ~14 mm, not the ~40 needed** — see §5.0. Decision left standing; it was right on its merits and wrong on the measurement |
| Drum location / thrust | **a real bearing** | concentricity is what stops the coil rubbing; PETG-on-PETG drag matters far more at 540° than at ±90° |
| Assembly | **lid over the top, drum drops through** | like the T1 coil rig |
| What crosses the joint | camera FPC **plus the three tilt servo leads**, taped alongside and rolling together | same trick variant B uses in the head track |

### The drive decision, and why it moved

Three routes were costed. The servo is **absolute over its travel**, which is
what the eventual YOLO→servo bridge will need — you cannot tell a
continuous-rotation servo to look 30° left.

| Route | Travel | Position | Cost |
|---|---|---|---|
| Continuous-rotation servo, on-axis | unlimited | **none** — dead reckoning | same PCA9685 channel; drift eventually tears the ribbon |
| 28BYJ-48 stepper + ULN2003 | unlimited | by step count | Zach owns one and rejected it: new driver, 4 GPIO, and too slow (~90°/s) |
| **180° MG90D + 2:1 step-up** ✅ | 360° | absolute | a printed gear pair, servo leaves the middle, ~1° of backlash |

4:1 (for 720°) was considered and dropped: it throws the servo ~35 mm off-axis
and multiplies mesh backlash to roughly 2°.

### ⚠ The 270° question, left standing deliberately

`HARDWARE.md:30` records these servos as **270°**. The Amazon listing title
says **180 Degree, PWM500-2500**. The camera-verified calibration in
`movement/config.py` (`PAN_RIGHT_US` 500 ≈ 81° right, `PAN_LEFT_US` 2250 ≈ 90°
left) measures about **171°** over that window, which is 180°-shaped.

Zach's position, 2026-09-19: *"the 180 deg servos would just go to 270, saw it
with our own eyes and tested it a lot"* — recorded as a bench **observation**,
not a camera measurement, and the two grades are kept apart on purpose
(`docs/lessons/`). **`HARDWARE.md` is deliberately not corrected** — Zach's
call.

**The design does not depend on it.** Sized against 180° → 360° at the drum.
If the servos really deliver 270°, the same 2:1 gives **540°**, which is
exactly what the coil is already built for. The headroom is free and nothing
has to change to claim it.

## 3. The mechanism

    fixed    well, a cup sunk in the stump          <- outer half of the loop
    rotates  drum, hangs from the head              <- inner half of the loop
    fixed    lid, caps the can after threading
    rotates  barrel up through the deck into the trunk, carrying the twist

The ribbon leaves the drum's inner anchor, wraps the drum, reverses through a
**U**, wraps back the other way along the well's inner face, and leaves
through a slot in the well wall **on the −Y side, near the bottom of the can**
(`EXIT_DEG`). Turning the drum rolls the U around the annulus, transferring
ribbon from one layer to the other. Nothing slides against anything — it
rolls.

Where the fixed end leaves does not affect travel at all, so the exit is free
to go wherever the packaging wants it. Out of the wall it is still standing on
edge, and it can turn aft from there without a crease, because that is a bend
in its own plane (rule 2).

**Why the coil is below the deck.** Inside the can the ribbon's width stands
vertical, parallel to the pan axis; a ribbon cannot travel along its own
width, so it can only leave the can sideways with its width still vertical —
which is exactly what a fore-aft trough in the body wants. Stacking the can
above the deck would need the ribbon to turn downward out of it, which costs a
crease. (Rules 1 and 2,
`docs/lessons/2026-09-18-flat-cable-and-driver-access.md`.)

### The governing equation

With `ri` the inner layer's centreline radius and `ro` the outer's, and `L` the
ribbon length inside the can:

    travel (radians) = L × (1/ri + 1/ro)

One end of travel is all the ribbon wrapped on the drum, the other is all of it
on the wall. **Travel scales as `1/ri`** — a smaller drum buys turns per
millimetre of ribbon, which is the whole reason the servo left the middle.

## 4. Numbers

Ribbon first, because everything scales off it:

| | Value | Grade |
|---|---|---|
| Width | 16.0 mm | **measured** 2026-09-18 |
| Thickness | 0.2 mm | **assumed** — Zach: "about two sheets of paper". `RIBBON_T` in the generators is 0.3. **Get calipers on this**; it sets the bend radius directly |
| Length | 914 mm (3 ft) | Zach, 2026-09-19 |
| Minimum bend radius | 2.0 mm (10 × thickness) | rule, not measurement |

Geometry, for **540° of mechanism**:

| | Value | Basis |
|---|---|---|
| Drum outer R | 12.0 mm | barrel bore Ø18 for the twist + 3.0 wall |
| Annulus gap | 6.0 mm | gives a 2.65 mm U radius against a 2.0 minimum |
| Well inner R | 18.0 mm | |
| **Can outside Ø** | **40 mm** | 2 mm wall |
| **Can depth below deck** | **22 mm** | 18 chamber (ribbon 16 + 2) + 2 floor + 2 lid |
| **Ribbon inside the can** | **70 mm** | leaves 844 mm for the head, the twist and the run to the Pi |
| Travel that buys | **552°** of mechanism | software limited to 360 |
| Wraps on the drum at the stop | 0.90 turns | radial stack 0.18 mm — negligible |
| U bend radius | 2.65 mm | ✓ 13 × thickness, over the 2.0 minimum |
| **Stump depth below deck** | **33.5 mm** | can 22 + servo clearance + gear plane 6 + floor |
| Gears | 20 / 40 teeth, module 1.03 | 2:1; centres **31 mm**, set by the servo clearing the can |

Envelope **87 × 63 × 74 mm**. Built and checked: `generators/pan_coil_b.py` →
`pan-coil-b/`. All eight parts watertight, manifold, one body.

⚠ **Two mesh warts, not geometry faults.** `well.obj` decimates to 105,600
faces against a 48,000 target with **12 self-intersecting faces**, and
`bay.obj` to 57,200 against 26,000 with **20** — both are large thin shells and
the decimator stalls on them. Both counts rose with the merge work, as the
parts gained features. Fine as viewer geometry; both would need attention
before either was a print file. Same class as the note in §8.

### How the servo is held

It is **not** a press fit in a hole. It drops into a tower in the stump and
lands on a shelf, then takes two screws through its own tabs:

| | |
|---|---|
| Body | X 24.9–37.1, Y −5.9–16.9, Z −25.0 to −2.5 — **long axis along Y** |
| Shaft | on the axis at X 31, pointing **down**, 4 mm into the input gear |
| Tab shelf | Z −18.5 (`TAB_FROM_TOP` 6.5 below the shaft face) |
| Screws | **2 × M2 × 6** at X 31, Y −8.25 and 19.25 (`TAB_PITCH` 27.5), Ø1.7 pilots 6 deep |

The servo is turned 90° on purpose. `TAB_SPAN` is 32.5 mm along the body's
long axis, and with that axis along X the far tab tip landed at X 20.25 —
0.25 mm outside a cup of radius 20. Turned, it clears by 4.9 mm.

**It goes in through a window in the side** (Zach, 2026-09-19), not down from
above. It slides along its own long axis, −Y, through the tower's +Y end wall;
the tabs run along the shelf like rails and the far one bottoming out is the
depth stop. Taking out the short end wall leaves both long walls whole, and
those are what react the gear torque — a window in the outboard face would
have cost the stiffer side.

That removes the assembly constraint entirely. Both M2 sit at r > 31, outside
the deck plate, so a driver reaches them from above **with the well already in
place**, and the servo can come out again without disturbing the coil.

⚠ **The body window alone is not enough.** The insertion sweep found the
**output shaft** ploughing through the shell's +Y wall 22 mm into the slide,
4 mm below the pocket floor — clear when seated, blocked on the way in. It has
a slot of its own now. Nothing in the pairwise check could have seen that:
seated, the number is zero.

What the off-axis servo bought, against the centred layout it replaced:

| | servo centred | servo off-axis |
|---|---|---|
| Drum outer R | 21.5 mm (MG90D corner + clearance) | 12.0 mm |
| Can outside Ø | 60 mm | **40 mm** |
| Ribbon for 540° | 115 mm | **70 mm** |

## 5. ⚠ Open, and blocking any geometry

### 5.0 The twist run does not fit — found 2026-09-19 by sectioning the model

Measured out of `tree_parts_b.py`, not estimated:

| | Z above deck |
|---|---|
| Top of the drum's flange — where the bore starts | 0 |
| Ball underside — `H` 52.0 minus `R_BALL` 30.7 | **21.3** |
| **Vertical run available for the twist** | **21.3 mm** |
| Needed for a 16 mm ribbon to twist 90° (rule 3) | **~40 mm** |
| Short by | **18.7 mm** |

⚠ **Corrected 2026-09-19, same day, by building the model.** This first read
**14 mm**, measured from the top of the *bearing* at Z 7. That was wrong: the
bore runs continuously from the flange through the hub and the trunk, so the
ribbon can start twisting at Z 0, not Z 7. The deficit is **18.7 mm, not 26**
— which changes what "raise the head" costs.

So the decision in §2 — twist in the trunk — is **not buildable at variant
B's current head height**. The decision is left standing rather than quietly
swapped, because the reasoning behind it is still correct: a twist that
rotates *with* the head is set once at assembly and never cycles, which is
the kind rule 4 prefers. Only the space was wrong.

Three ways out, all of them the head session's call:

1. **Raise the head ~19 mm.** Changes `H`, the nest, and the whole envelope.
2. **Continue the twist up inside the nest's own volume.** There may be
   20–30 mm of usable height in there; nobody has looked.
3. **Deliver the ribbon already on edge from the head**, so no twist exists
   anywhere. Was listed as the cleanest option in §6; this finding makes it
   close to necessary rather than merely nicest.

**Nothing below this line should be built until one of the three is picked.**

### 5.1 The gear plane cannot be the coil plane

Found while sizing, and it is the biggest unsolved thing here. The barrel is
Ø24 because the twist bore is Ø18, so the **output gear cannot be smaller than
about Ø26 pitch**, which puts the input gear at Ø52 and the servo axis **~39 mm
from the pan axis**. At the coil's own Z the annulus already occupies R 0–20,
so the gear pair cannot live there. Three candidate arrangements, none chosen:

| Arrangement | Cost |
|---|---|
| **Gear bay above the deck** — barrel carries the output gear just above the deck, servo stands beside the trunk | turret base grows to ~Ø100; gears visible; shallowest stump |
| **Gear bay below the can floor** — barrel extends down, servo lies beside it under the can | stump goes to ~47 mm below the deck, near the full body height of the current 50 mm body |
| **GT2 belt instead of gears** — 38T on the barrel, 76T on the servo | thin (a 6–9 mm bay fits between lid and deck), near-zero backlash, free choice of centre distance — but it is a small purchase, and Zach asked for no new hardware |

**The escape route, chased 2026-09-19, and how far it got.** The ribbon does
not have to run up the middle of the barrel: everything above the drum's inner
anchor rotates with the head, so it can run anywhere in the rotating frame,
including beside a much thinner barrel. That works — the barrel drops to ~Ø10
and the output gear to ~Ø14 — but it does **not** free a plane above the deck,
for a reason worth writing down:

- The ribbon leaves the coil at R 12 and has to rise past the top of the
  chamber. A **fixed** lid cannot be crossed by a ribbon at a rotating radius,
  so **the drum's own flange has to be the chamber's top cover** — which is
  exactly what `pan_coil.py` did with its Ø72 thrust flange, and the reason is
  now on record rather than inherited.
- Above that flange the ribbon sits at R ~15 and sweeps R 6–24, which is where
  a small output gear would have to be. They collide.

### ⚠ Resolved 2026-09-19 by modelling it — the depth problem was self-inflicted

`generators/pan_coil_b.py` builds the thing, and the 47 mm above is **wrong**.
It assumed the servo hangs under the can with its gear. It does not have to:

- Make the gears big enough that the **centre distance clears the can** — 31 mm,
  set by the servo's nearest corner clearing R 20, *not* by the gear ratio — and
  the servo sits **beside** the can at deck level, Z 0 to −22.5.
- Only the **gear plane** then goes below the can floor, and that is 6 mm.

**Stump depth 31 mm, not 47.** Gears 20/40 teeth, module 1.03, servo body at
X 25.1–47.9. Everything else in §4 stands. The three-arrangement table above is
kept because the reasoning is still the reasoning; it is the *conclusion* that
moved.

### 5.2 Measurements needed

1. **The stump** — usable outside diameter, and how far below the deck top the
   can may sink. The Ø40 × 22 above is what the coil wants, not what fits.
2. ~~**Trunk height above the deck**~~ — **answered from the model, 2026-09-19:
   ~14 mm against ~40 needed. See §5.0.** Not a measurement to take; a
   conflict to resolve.
3. **Where the Pi's CSI connector sits** relative to the pan axis, and the run
   length to reach it. Budget is 914 mm total, 70 spent in the can.
4. **Is the 3 ft ribbon one continuous camera→Pi run**, or is there a joiner at
   the base? FPC cannot be cut, so this decides whether the can's length budget
   is shared with the head's.
5. **Ribbon thickness with calipers.** 0.2 vs 0.3 changes the annulus gap from
   5 to 6.5 mm and the can Ø from 38 to 41.
6. **Which bearing.** Candidates: 6809 (45 × 58 × 7) on a stepped barrel
   journal above the coil chamber, or a larger thin-section ring sitting on the
   deck around the well boss. The second is further from the axis, which is
   what actually kills wobble.

### 5.3 Four clashes, found 2026-09-19 — and the check that exists now

Zach looked at the first build in the viewer and said the servo *"doesn't screw
into anything"* and *"it looks like it intercepts the other thing"*. Both were
right, and **no check could see either, because there was no check**. This is
the third time on this project that eyes on a render have caught what the
geometry pipeline could not.

A pairwise interference check now exists — `generators/pan_coil_b_check.py`,
one volume in mm³ per pair, rotating parts swept over the pan range. What it
found on the first build:

| pair | was | now |
|---|---|---|
| `servo` vs `well` | **140 mm³** — the deck plate ran through the servo's top | 0 |
| `gear_in` vs `bay` | **892 mm³** — the input gear's *tip* radius, not its pitch radius, is what has to clear | 0 |
| `drum` vs `well` | **270 mm³** — `FLANGE_R` 19.6 ploughing through a deck ring starting at 19.0 | 0 |
| `drum` vs `bay` | 1 mm³ | 0 |

**The servo had nothing fastening it — exactly the variant B fault Zach found
on 2026-09-19**, where a tab recess removed 0.00 mm³ of a 1452 mm³ box. Twice
in one day, and both times the missing thing was a *fastening*, not a shape.
Worth treating as a standing question: *what holds this part, and can a driver
reach it?*

The check carries a negative control (`--broken`) that puts the servo back
where the fault was: `servo vs well` reads **426.82** and `servo vs bay`
**1020.30**. Sideways alone was not enough — it hits the bay first and leaves
the well row reading zero, which is the row that needed proving. Every zero
above is a zero that has been made to move.

**A pairwise check is still not enough, and the side window proved it.** With
the servo seated, every pair reads zero — and it could not have been fitted.
The insertion sweep, added after, slides it the whole 40 mm and found the
output shaft cutting the shell's +Y wall 22 mm in. *Where a part ends up is a
different question from whether it can get there*, which is the same thing
variant B's `_insert.py` was written for. Both questions have a check now.

### 5.4 Accepted risks

- **No mechanical hard stop.** With an absolute servo the software limit is the
  real limit, so this is much safer than it was when the drive was
  continuous-rotation — but a wrong `config.py` number still over-winds the
  coil, and the ribbon is the one part in this build that cannot be reprinted.
  A lug on the drum and one on the well is nearly free. **Zach's call;
  currently declined.**
- **Backlash ~1°** at the output from a printed 2:1 pair. Fine by eye,
  noticeable in a tracking loop later.

## 6. The merge interface — prepared 2026-09-19

Zach's ask: get this ready to become **one part** with the ball-in-a-nest.
Nothing in `tree_parts_b.py` has been touched; this is the coil side made to
fit, plus what the nest has to change.

**On the five `fork vs …` rows reading zero:** those are bounding-box proofs — the nest holds nothing below Z 10.5 and the tallest fixed part tops out at 6.6, so no overlap is possible. A true statement, but not a hard-won one; do not read them as having exercised anything subtle.

**The frames already agree** — both are mm, Z 0 at the deck top, X forward,
pan axis at the origin. Confirmed by importing `tree_parts_b` into the check
rather than by reading numbers across.

### 6.1 What the drum now presents

The stand-in trunk is **gone**. Above the bearing the drum ends in a disc the
size of the nest's own base, and the nest bolts straight down onto it.

| Feature | Value | Comes from |
|---|---|---|
| Mating face | flat, **Z 10.5** | `A.BASE_Z` — the nest's existing underside plane |
| Mating disc | **Ø51** | `A.PED_R` 25.5 — the nest's existing base disc |
| Ribbon bore | **Ø18 on the axis**, chamber up through the face | rule 3, the twist |
| Fixing | **3 × M3 pilots, r 20, at 0/120/240°**, 7 deep | clear of the bore by 8 mm, of the rim by 5.5 |
| Clearance to the fixed boss | **3.5 mm radial** | disc R 25.5 inside the boss bore R 29 — they never meet at any Z. The nest’s underside also clears the boss top by 3.9 mm |

### 6.2 What the nest has to change — the head session's lane

1. **Delete the pan horn pocket.** `horn_pocket_z` in the nest's underside is
   exactly where the ribbon bore has to go. There is no pan horn any more: the
   nest is bolted to the drum, and the drum is geared.
2. **Delete the Ø5.6 centre hole** that runs up to `BASE_Z + 14` — same space.
3. **Add 3 × M3 clearance + counterbore** at r 20, 0/120/240°, through the
   base disc. They are driven from above, before the ball goes in — worth
   checking against the assembly order, because a captured horn is exactly how
   variant B lost its driver paths before.
4. **Re-route the trough to the axis.** It currently leaves the underside at
   **X ≈ 9** (`TROUGH_PATH` ends at `(9.0, BASE_Z − 1.5)`). That 9 mm offset
   is the original problem — it is what drags the ribbon when the head pans.
   It has to arrive at the Ø18 bore on the axis instead.
5. **`roots` is deleted.** Its three jobs move: the pan servo goes to the
   coil's tower, the slide land is replaced by the bearing plus a lower
   journal (§6.4), and its 4 deck screws have to move (§6.3).

### 6.3 ⚠ The deck screws are under the bearing

`roots` puts 4 × M3 at **r 30** on the 45° diagonals. The bearing seat is the
ring **r 29–31**, and the deck plate covers r 19–31 — so every one of those
four holes runs straight through the seat. They must move.

Where they go is not decidable yet: outside r 31 on the +X side lands on the
gear bay, which is legitimate (it is stump material) but needs a boss and a
driver path, and the stump's real outline is still unmeasured (§5.2). Flagged,
not guessed.

### 6.4 Stability — why one bearing is not enough

Measured off the variant B meshes rather than estimated: **159.6 g rotating**,
CG at **X −2.9, Z +46.1**. Static tipping moment is **4.6 N·mm**, so strength
is not the question. Angular compliance is.

| Support | 0.05 mm slop | 0.10 mm slop |
|---|---|---|
| 6809 alone (7 mm wide) | 0.82° → **1.14 mm** sway at the ball top | 1.64° → **2.27 mm** |
| 6809 + lower journal, 26 mm apart | 0.24° → **0.33 mm** | 0.48° → **0.66 mm** |

A single deep-groove bearing resists tilt only across its own width, so
printed seat slop is multiplied by the 79 mm from the bearing to the top of
the ball. **The barrel now runs in a journal in the well's underside** — a
sleeve it was already passing through, tightened to Ø10.5 around the Ø10
barrel. That is a 3.4× improvement for one extra millimetre of wall.

Drag cost is negligible: the journal carries only the radial reaction, and
even the old full-face land would have been ~110 g·cm against 4400 g·cm
available at the drum after the 2:1.

**This makes the journal fit a T2 coupon item**, not a number to assume — it
is now load-bearing for how steady the head looks.

### 6.5 How the gear grips the servo — Zach's method, 2026-09-19

*"Using it in Autodesk to cut out the hole for it to go in."* He keeps a model
of the horn he owns and subtracts it as a cutting body, **with no size change
at all**, then leaves **1–2 mm** of material for the screw head to bear on.
In practice that prints as a tight fit.

**This supersedes the `+0.2 mm all round` in `ball-head-validation-handoff.md`
§T2** — that was advice, this is a bench result, and the two grades are not
equal. Recorded, not averaged.

What the generator fixes is the **position**; the pocket shape is a placeholder
cut from the repo's generic `HORN_*` (34.4 × 6.2, disc 8.4, depth 2.7, flagged
MEASURE). Re-cut it in Fusion with the real horn model.

| | |
|---|---|
| Cut axis | X 31, Y 0, along Z — the pan servo's shaft |
| Pocket | from the gear's top face **Z −25.8**, down by the horn's thickness |
| Roof | **1.5 mm** of material under the pocket |
| Screw | M2 clearance up from the gear's underside, counterbored for the head |
| Screw length | roof 1.5 + horn 2.7 + shaft depth — **~7.7 mm** if the shaft takes 3.5 |

**Why this joint matters more than the others.** A 34.4 mm horn fits *entirely
inside* the 41.3 mm gear, so the plastic grips the arm tips at **r 17.2**
instead of the shaft spline at ~1.25 — about **14× the leverage**, so the same
pocket slop makes 14× less angle at the output. Whatever is left is then
doubled by the 2:1 step-up. It is the one place in the drive where tightness
is worth paying for.

**Stock screws are likely too short.** The 1–2 mm of roof has to be spanned
before the screw reaches the shaft at all. Measure the usable thread depth —
run a stock screw into a bare servo and mark where it stops — then add the
roof. Longer than that is wasted and worse: the screw bottoms in the blind
hole and goes tight while the part is still loose, which feels tightened and
is not.

**Assembly note:** the horn's clocking on the shaft sets where the drum's zero
ends up. Fit it with the servo at mid-travel and the coil at mid-travel, or
360° of pan ends up lopsided about centre.

### 6.6 Two faults the merge work turned up

- **The bearing had no shoulder.** Its inner race had nothing under it at
  r 22.5–26 and would have dropped 0.4 mm onto the *fixed* deck ring — a
  rotating race grinding on a stationary part. The mating disc's underside is
  the shoulder now, and the load path is drum → disc → inner race → balls →
  outer race → well ledge.
- **A blend bulged past its named radius, again.** The smooth min tying the
  drum's flange to its hub reached **r 19.84** against a named 17.7, putting
  133 mm³ inside the cup wall. The three stacks are hard-unioned now — a
  bearing shoulder wants a step, not a fillet. Same mistake
  `cradle-audit.md` §1 records, in a different part.

## 7. Requests to the head session (not applied)

- The ribbon currently leaves the nest's underside **9 mm forward of the pan
  axis**. For this coil it wants to arrive at the trunk bore, on the axis or in
  a known channel — whichever §5.1 settles.
- **⚠ The twist has nowhere to go — this is the one that matters.** See §5.0:
  ~14 mm of run exists between the bearing and the ball's underside, against
  ~40 needed. Either the head rises ~26 mm, or the twist continues inside the
  nest, or the head's track delivers the ribbon **already on edge** and the
  twist stops existing. The third is cleanest and costs the head session the
  least if the track's orientation is still soft.

## 8. Test ladder

**T1 already exists and its result is unknown.** `coil-test/` (cup, spool, lid,
knob) was printing on 2026-09-17 and the ball-head handoff still says *"results
pending — ask Zach"*. It is the same mechanism on a different axis, so **find
out before printing anything new here.** Its pass criteria — smooth over full
range, coil stays centred after 50 cycles, no whitening at the slits after
~300, one turn vs two — transfer directly.

| Rung | Question | Rig |
|---|---|---|
| **P1** | Does a rolling loop survive 540° rather than ±120°? | Re-run the T1 rig to its real limits, counting cycles. Use the spare Arducam ribbon — paper does not behave like FPC |
| **P2** | Does a printed 2:1 pair have acceptable backlash? | Gear pair on a plate, long pointer on the output, servo holding; measure tip travel by hand |
| **P3** | Does the twist work in the trunk height available? | A plain Ø18 bore of the measured length, ribbon threaded, camera still images through it |
| **P4** | Full can: coil + drum + bearing + gear + servo | Sweep to both stops, images at −180/0/+180, inspect the coil through a cut or clear lid |

Record every observed fact in a dated `docs/bench/` log **when it is observed**,
with print settings. Keep measurements and comfort judgements apart.

## 9. Files

- **`generators/pan_coil_b.py`** — the geometry. Parameters at the top; the
  travel equation and the layout reasoning are in the module docstring. Run it
  from inside `generators/`; ~8 min for all eight parts.
- **`generators/pan_coil_b_check.py`** — the interference check. Run it before
  believing any build: `python pan_coil_b_check.py` (expect 0 clashes) and
  `python pan_coil_b_check.py --broken` (expect 2, or the check has gone
  vacuous). ~3 min each.
- **`pan-coil-b/`** — `fusion/*.obj`, `viewer_pan_coil_b.js`, `mesh_report.txt`.
- **Viewer** — https://claude.ai/artifact/94q1eeyW7FKFkLAPTugMSt, tab **D · pan
  coil**. Pan slider runs ±270°, and the loop rolls as it turns. The orange
  ghost above the trunk is the missing twist run from §5.0. **Merge onto the
  live version, never overwrite it** — it carries A, B and C too.

One thing the build taught, already commented in the generator: the `well` is a
large 2 mm shell that marching cubes gives ~300k faces. A 16k decimation target
broke it — the decimator would not collapse that far, returned its last failed
attempt undecimated, and the *report* then read 46 bodies while the raw mesh was
one clean watertight component. Same class as
`docs/lessons/2026-09-19-coincident-faces-and-insertion.md`: **read the face
count against the target, not just the flags.**

## 10. Prior art in the repo

- **`generators/pan_coil.py` + `pan_coil_check.py`** (variant C) — this exact
  mechanism, built for ±90°. Read the module docstring first: it explains why a
  can and not a twist, why the coil is below the deck, and which member
  rotates. Outputs in `pan-coil/`.
- **`coil-test/`** — the T1 rig STLs, printable.
- **`docs/lessons/2026-09-18-flat-cable-and-driver-access.md`** — the six flat
  cable and driver rules. Rules 1–4 govern everything here.
- **`tree-parts-b/HANDOFF.md` §0.3** — where this item came from.
- **`ball-head-validation-handoff.md`** — the camera measurements and the
  ribbon path through the head.
