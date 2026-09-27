# Cradle audit — 2026-09-19

The structural/geometry audit of `fork` (the nest) that `HANDOFF.md` §0.2 asked for:
*"the part that has had the least scrutiny… it is organic, it has never had a structural
audit, and almost all that has been checked on it is clearance."*

**Five findings. Two of them block a print.** Nothing here is fixed — this is the review.

All four existing checks were re-run first and were green, unchanged from the end of the
previous session: **38 rows zero · 0 problems · 0 problems · none**. Every finding below
sits in a blind spot of those four.

---

## 1. ⚠ The ball has 0.10 mm of running clearance to the nest, not 1.11 mm

`HANDOFF.md` §5 records *"the fillets bulge them to 24.89, leaving 1.11 mm to the collar."*
That 1.11 is measured to `POD_Y0` = 26.00, the **named** collar inboard face. But
`fork()` calls `collar(m, POD_Y0 - 1.0, POD_P_Y1)` — the collar body starts at **25.00**,
and the `smin(…, 7.0)` blend into the cradle bulges inboard of even that.

Swept over the whole facing annulus (1320 rays, r 4→20.5, every 5°):

| | gap |
|---|---|
| minimum | **0.103 mm** at r 15.5–16.0, θ 235–265° (the lower-rear quadrant) |
| median | 0.580 mm |
| maximum | 2.078 mm (in the mouth, where only the collar is present) |
| rays under 0.30 mm | **143 of 1320 (11 %)** |

The ball rotates 180° against this. 0.10 mm is inside the print tolerance of the process,
so on the bench the two will touch. The ball is also not located axially by anything except
these two gaps — the hub is a slip fit in the 6704 bore — so it floats ~0.2 mm and rubs on
whichever side it lands.

**Why no check saw it.** `tree_parts_b_check.py` scores *overlap volume*. It reads 0.00 mm³
whether the gap is 5 mm or 0.05 mm. Its eight `ball @ tilt … vs nest` rows are all true, and
all uninformative about fit.

**Negative control.** The same probe reads 2.078 mm where the design does have room (the
mouth) and 0.103 mm where it does not — it discriminates, it is not reading a constant.

---

> **CORRECTED AND FIXED, later the same day. §1 above understates the fault, and the
> measurement behind it was wrong.** The sweep dropped every ray where the nest's material
> started *before* the ball's ended (`if fs < be: continue`), so interference could not appear
> — it could only ever report a positive gap. Re-measured signed, the two parts were **actually
> touching**: 1.71 mm³ of real overlap, worst −0.52 mm at r 10.5. See §6.

## 2. ⚠ The 90° flange screw opens into the bearing bore — on both collars

> **FIXED the same day.** The triad was rotated to `SCREW_A = [30, 150, 270]` and named,
> instead of being written out as a literal in four places (`fork` ×2, `post`, `cap_minus`)
> plus two more copies in `tree_parts_b_driver.py` and `tree_parts_b_step.py`, which now
> derive it. Overlap 7.65 → **0.00 mm³**; confined connectivity inside the collar shows
> no screw sharing the bore's void on either side; all four checks green. The finding
> below is left as it was written — the geometry it describes is what shipped up to this
> commit. Nothing else in this document is fixed.


`SCREW_R = 15.5` carries the comment *"flange screws, clear of the 6704 OD."* It is clear of
the **OD circle** (r 13.55). It is not clear of the **teardrop roof**: `td_y` truncates at
`r × 1.15`, so the bore's ceiling reaches **15.58 mm** (seat) and **15.76 mm** (pass bore)
straight up the Z axis — above the 90° pilot's inner edge at 14.65.

| bore | roof | overlap with the 90° pilot |
|---|---|---|
| bearing seat r 13.55 | 15.58 | **4.83 mm³** |
| pass bore r 13.70 | 15.76 | **2.82 mm³** |
| hub bore r 10.40 | 11.96 | 0.00 — clear |
| post bore r 8.00 | 9.20 | 0.00 — clear |

Identical on the −Y collar (same two bores, same screw ring).

Of the screw's 6.2 mm of engagement in the collar, **5.7 mm is in a hole that is open into
the bearing pocket**; only the last 0.5 mm, in the hub-bore region, is full thread. These
three screws are what react the *entire* tilt-servo torque through the post.

**Negative control.** Walk `SCREW_R` and watch the overlap move —
14.5 → 8.73 mm³ · 15.0 → 7.81 · **15.5 → 4.83 (as built)** · 16.0 → 1.68 · 16.5 → 0.00 ·
17.0 → 0.00. And on the real part, a connected-component label of the void puts the screw
hole and the bearing bore in **one component**.

**The cheap fix is to rotate the triad**, not to grow it: at 30/150/270° no screw sits where
the roof is, because the roof only exists above `zr = r/√2` = 9.69. Growing `SCREW_R` to 17.0
also works but drags `FLANGE_R` and `COLLAR_R` with it — which is the same change §3's
M3 question is already circling. `post()` and `cap_minus()` share the angle list and would
move with it, and the driver check would need re-running.

---

## 3. The other two flange screws leave a 0.95 mm web

At 210° and 330° the roof does not apply, so the circle governs and the wall is exact
arithmetic: `SCREW_R − M2_PILOT − r_bore`.

- to the pass bore (r 13.70): **0.95 mm**
- to the bearing seat (r 13.55): **1.10 mm**

Two extrusions at a 0.4 nozzle. Not a fault, but it is the wall that stops all three screws
breaking into the bore, and the comment at `SCREW_R` implies roughly twice the margin that
is actually there. `tree_parts_b_health.py`'s threshold is 0.80 mm, so it passes by 0.15.

---

## 4. The ribbon trough grazes three faces instead of overrunning them

Every one of the fork's 24 mm³ of sub-0.8 mm material is the trough, and in all three places
the cut runs *tangent* to a face rather than crossing it:

| where | volume | what it is |
|---|---|---|
| Z 10.6–10.9, X −6.4…−4.3 | 15.0 mm³ | the trough's floor lies along the deck plane `BASE_Z`, leaving a 0.6 mm tongue at the mouth of the ribbon slot |
| Z 14.8, X −9.7, Y −10.3…10.4 | 1.9 mm³ | a 20 mm-wide skin where the trough passes just inside the trunk's back |
| Z 22.3–25.3, X −15.7…−8.2 | 3.4 mm³ | the web between the trough and the ball's clearance sweep |

This is §4's own rule — *a cut must overrun the face it passes through* — in a third place.
The slot is **not** blocked (see finding 5's green below); the consequence is feather edges
that will print as stringing and snap off in handling.

---

## 5. The clip at |Y| = 34 is coincident with the collar's own end face

`fork()` ends with `np.maximum(s, np.abs(p[1]) - POD_P_Y1)`, commented *"flat outer faces for
the two flange plates."* But `collar(…, POD_P_Y1)` already ends flat at exactly 34.000.
Measured, the clip removes:

| probe | body ends at | clip removes |
|---|---|---|
| x 0, z−H 0 | 33.998 | **0.000 mm** |
| x 0, z−H +10 | 33.998 | **0.000 mm** |
| x 10, z−H 0 | 33.998 | **0.000 mm** |
| x 0, z−H −10 | 34.050 | 0.050 mm |

Two surfaces of one part on one plane — the exact fault `tree_parts_b_health.py` exists to
catch. It misses it because its `PLANES` list carries `('fork', 'collar outer +Y', POD_P_Y1)`
**once**; the clip is not a second entry, so there is no pair to compare. Latent, not biting:
`fork.obj` hits its 60 000-face target, watertight, manifold, bodies 1, self-int 0.

---

## Green, and worth recording

- **No sealed voids anywhere in the fork.** One void component; 0.0 mm³ enclosed. Given that
  both bearing seats *were* sealed pockets a session ago, this was worth testing rather than
  assuming.
- **The ribbon channel is open end to end.** The `track` and `trough` regions hold 9050 and
  1415 mm³ of void, 100 % of it reaching open air, 0.0 mm³ still solid, and the slot stays
  22.0 mm wide (ribbon 16.0) along the whole path from the loop to below the deck.
- **The neck is not the weak point.** Sections every 1 mm from the deck up: 850–2200 mm² of
  area, and the trough costs at most 22 % of it, at the base.
- **The collar-to-shell handover is not starved** — 648 mm² of section at the Y 25 plane.
  The C-frame was the thing I expected to find wrong, and it is fine.

## Blind spots these findings expose in the four checks

1. `_check.py` measures interference, never **clearance** — a 0.00 mm³ row and a 0.10 mm gap
   are the same row.
2. Nothing tests a **screw pilot against a bore of the same part**.
3. `_health.py`'s `PLANES` list is hand-maintained, so a plane nobody listed cannot collide
   with anything.
4. `ball_structure.py` still only covers the ball halves.

---

## 6. ⚠ The ball's own blends stand 1.17 mm proud of its flat — and that is what the clearance
## fault actually was

Found while fixing §1, and it supersedes §1's diagnosis.

`ball_body()` truncates the ball at `|Y| = FLAT = 24.5`, and then applies eight `smin()` blends
on top of it — rails, seam rods, face plates, hubs, the pad. **A smooth min bulges outward**
wherever two surfaces meet near-tangentially, so the finished ball stands well past the flat
that the rest of the model reasons about:

| r from the tilt axis | ball reaches \|Y\| | over FLAT | what is there |
|---|---|---|---|
| 10.5 | **25.672** | +1.172 | the hub stub's root fillet |
| 11.5 | 25.254 | +0.754 | " |
| 16.5–17.5 | 25.414 | +0.914 | the face plate's rim |
| 18.5 | 25.238 | +0.738 | the flat-to-sphere fillet |

The handoff recorded this bulge as **24.89**. §1 of this document repeated it as the ball's
limit. It is **25.67**. The nest was carved to 25.0, so the two parts interfered.

**Why nothing caught it.** `tree_parts_b_check.py` votes on a **0.4 mm grid** and only counts a
voxel when both solids are more than 0.05 mm inside. The overlap is a shell ~0.5 mm thick and
~0.6 mm wide, wrapped round a 40° arc — 1.71 mm³ that falls between voxel centres. All eight
`ball @ tilt … vs nest` rows read 0.00 mm³ while the parts were touching. This is the lesson in
`../../lessons/2026-09-19-surface-sampling-is-a-vacuous-check.md` in a new costume: the row was
not wrong, it was **under-resolved**, and a coarse zero looks exactly like a real one.

**Fixed** by re-imposing the truncation *after* the blends, everywhere except the hub itself,
which has to pass through the collar — the same plane `ball_body` already truncates on, so no
second face is introduced. The nest's clip then went back to a plain `FLAT + BALL_CLEAR_Y`.

| | before | after |
|---|---|---|
| signed gap, min | **−0.524 mm** | **+0.602 mm** |
| rays interfering | 31 of 2719 | **0** |
| boolean overlap | 1.71 mm³ | **0.00 mm³** |
| fork material under 0.8 mm | 24 mm³ | 24 mm³ |

Cost: the hub stubs lose their *external* root fillet, which is what was bulging. The socket
hub's contact drops 522 → 344 mm² and its volume-per-contact goes 2.3 → 3.5 mm, still inside
`ball_structure.py`'s 4.0. The internal blends are untouched.

Still open, and the reason the gap is only 0.6: **nothing locates the ball along Y** except
these two faces, so the clearance is also the rattle — 1.2 mm of total float. The proper fix is
a shoulder on the hub bearing against the 6704's inner race, which is what a bearing is for.

---

## 7. The tilt servo had nothing holding it

Zach spotted this by eye: *"doesn't seem like there's a place for screws to go in?"*

There was not. The README said the servo was **captured** — *"the tabs drop into a `TAB_T = 3.0`
recess that stops it moving +Y"*. Measured, that recess removed **0.00 mm³ of a 1452 mm³ box**:
it was cut entirely inside the ball's cavity and never touched solid material. So the servo was
located in X and Z by its pocket, rested on the −Y pad, and had **nothing above it at all** — it
could float ~4 mm toward the post and take the load through the horn instead of the mount.

**Fixed to Zach's suggestion** — two bosses rising to the tabs' underside, each taking an M2 up
through the servo's own tab hole, driven from the seam face before the halves close. Exactly how
the pan servo is held in `roots()`. Both reachable (`tree_parts_b_driver.py`), 5.4 mm of thread
each, and `ball_structure.py` now tracks them: 4.6 and 4.2 mm of volume per mm² of contact,
just over its 4.0 flag and in the same band as the rail (7.7) and pad (6.8) already accepted.

One detail worth keeping: the near boss's pilot sits at r 7.4–9.1 from the tilt axis and the
post bore is r 8.0, so the bore would have opened the pilot down one side — **the exact fault
§2 is about**. `POST_BORE` now starts at 20.5 instead of 17.4; the old start was pure overrun
into empty cavity.

---

Probes used for this audit were scratch, not committed. Say the word and they become
`cradle_structure.py` alongside the other four.

---

## What was fixed, and what was not

| # | | status |
|---|---|---|
| 1 | ball-to-nest clearance — actually −0.52 mm, interfering | **fixed** — see §6. Not the way §1 proposed: the fault was on the ball, not the collar |
| 2 | 90° screw into the bearing bore | **fixed** — `SCREW_A = [30, 150, 270]` |
| 3 | 0.95 mm web at the other two screws | **open** — unchanged by the rotation; all three sit at 0.95 now |
| 4 | trough grazing three faces, 24 mm³ | **open** |
| 5 | coincident clip at \|Y\| 34 | **open** |
| 6 | the ball's blends stand 1.17 mm proud of FLAT | **fixed** — truncation re-imposed after the blends |
| 7 | the tilt servo had no fastening, and its "capture" was inert | **fixed** — two tab bosses + M2, Zach's design |

Finding 3 is worth reading next to finding 2: rotating the triad removed the breach but did
not widen the web, so **all three screws now sit on the same 0.95 mm**. Growing `SCREW_R`
past 17.0 fixes 2 and 3 together and is the same change §3's M3/flange question is circling —
that is the one to make if the flanges grow anyway.
