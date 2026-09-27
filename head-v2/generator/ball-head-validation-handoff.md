# Ball head (v2 pan/tilt) — validation handoff

**Written 2026-09-17** at the end of the design session that produced the
ball-head concept. For the next session, whose job is to **validate that
design with test prints and bench tests** — above all the tilt drive: the
MG90D in its side pod turning the ball.

This is a chassis-v2 working brief, like `../body-revision-brief.md` — **not
a phase**. If this becomes a phase it needs a spec first (CLAUDE.md loop),
and test results drain to `docs/bench/` the moment they are observed.

> **First thing to confirm with Zach:** he described this session's focus as
> *"the servo inside the ball"*. In the concept the tilt servo sits in a
> **side pod** next to the ball, not inside it. Ask whether he means that
> pod-drives-ball joint (what this brief assumes) or wants to explore moving
> the servo into the ball itself — that would be a different design.

---

## Where things stand

| Item | State |
|---|---|
| Ball-head concept | Designed, rendered, **nothing printed** except the coil rig |
| Test print T1 (ribbon coil rig) | **Printing as of 2026-09-17**, results pending — ask Zach |
| Interactive 3D viewer | https://claude.ai/artifact/FsoKzonbvW3HrXWhw3G8iH (private to Zach; pan/tilt sliders, cutaway, see-through pods) |
| Zach's own head CAD | TEST-PRINT-2 (z_mount + split yoke + shroud) — reviewed, superseded in direction by the ball concept, but his parts are the base he may adapt |
| Robot | Unrelated to this work. Phase 4c Task 18 is still owed on the robot itself — **don't disturb its wiring** (see Bench rules) |

## How we got here (short)

1. **Reviewed Zach's TEST-PRINT-2 head** (files in `test-print-2/`). The
   z_mount is the pan stage holding the tilt servo; the yoke carries a
   camera shroud 25–40 mm *ahead* of the tilt axis. Findings, measured
   from the STLs:
   - A keyhole slot cut "through all" splits the z_mount's +X wall its
     full length (turns the box into an open channel — torsionally weak).
   - Top/bottom z_mount seam is a flat butt joint with nothing locating it;
     the two 688 bearing seats are therefore not guaranteed coaxial.
   - Printed female splines (~4.55 mm, 3.7–4 mm engagement) on both pan and
     tilt — slop risk. Recommended capturing a stock horn instead.
   - 0.5–0.7 mm floor behind the front 688 seat; everything drawn at zero
     clearance (bearing bores 16.00, servo pocket 22.9 × 12.3 mm).
   - **Tilt-down collision:** shroud bottom already ~10 mm below the pan
     spline face at level; would hit a tab-mounted pan deck by ~3°.
     Zach wants 10–20° below level. Render: `test-print-2/review_tilt_down_collision.png`.
   - **CG ~25 mm ahead of the tilt axis**, ~78 g·cm at level (≈4 % of MG90D
     stall — not a strength problem; means the head drops *face-down* when
     limp, the opposite of today's head).
   - Shroud posts on a **28.8 mm** pattern; the real board is **28.0 mm**.
   - The split left/right yoke (Zach's revision) was a good change.
2. **Moved the camera onto the tilt axis** (block concept,
   `concept/block_concept_superseded.png`) → load ~3 g·cm, constant swing
   radius, no tilt-down collision at any angle.
3. **Ball version** chosen by Zach: ball centred on the tilt axis, split
   left/right, pedestal, head moved toward the deck front.
4. **Measured the camera** and resized to it.
5. **Ribbon routing**: out the hollow idler axle into a clock-spring coil in
   the pod. Zach: "pretty clever". The coil is the one novel mechanism, so
   it got the first test print.

## Decisions (Zach's, this session)

- IR pods move **off the head** to the tank front as fixed "headlights"
  ("the tank can turn if it needs light"; they made the face bulky/heavy).
- Camera ribbon exits the head at the bottom and drops into a slot in the
  tank.
- Head mounted higher/further forward for down-angle — "looks more
  functional".
- Ball tilt head, split L/R, both pods matched in size (symmetry).
- Ribbon through the hollow axle + clock-spring coil.
- Material: PETG.

## Measured camera — Arducam UC-439 Rev.D (OV5647, day/night)

From Zach with calipers, 2026-09-17, plus photos:

| Feature | Value | Source |
|---|---|---|
| Board | 36 × 36 mm | measured |
| Mounting holes | Ø2 mm, 26 mm apart inside edges → **28.0 mm centre pitch**, centred on the board | measured |
| IR-cut holder height above board | 9 mm (board thickness already subtracted) | measured — "IR things", read as the holder |
| Board thickness | 1.6 mm | **assumed** |
| Light sensor (LDR) | on bent leads, sticks up past the **top edge**, faces forward | photo |
| Ribbon connector | 15-pin FPC on the **bottom edge**, cable exits downward | photo |
| IR-cut solenoid | 2-pin JST, loose red/black wires loop past the left edge | photo |
| IR pod power | large GND/3V3 pads either side (pods screw on and draw power there) | photo |
| Header | GND, IR, VSYNC, STROBE, FREX, 3V3 | photo |
| Lens / FOV | **not measured — deferred by Zach** | — |

## The concept, by the numbers

All in `concept/`; regenerate with `generators/` (see below). Estimates are
flagged.

| | Value | Basis |
|---|---|---|
| Ball OD | 59.2 mm (inner R 28.4, 1.2 mm wall) | board corners + 1 mm clearance |
| Board position | back face 8.5 mm **ahead** of the tilt axis | makes room for the ribbon run behind it |
| Tilt axis above deck | 46.1 mm | pedestal 10 + turntable 4.5 + ball R + 2 mm |
| Pods | Ø40 × 22 mm, both sides | 4 mm 6704 + 16 mm coil + walls; servo corner reaches 18 mm from axis |
| Width across pods | ~109 mm | the real cost of the coil |
| Tilt servo | MG90D in the +Y pod, stock horn into the ball hub | body dims 22.8 × 12.2 × 22.5 are **datasheet, not measured** |
| Idler | 6704 thin bearing (20 × 27 × 4), hollow hub, ribbon passes through | |
| Ribbon coil | 2 loose turns, r 10.5 → 17.5 mm around a Ø20 spool | |
| Pan | MG90D in a Ø36 pedestal, horn captured in the turntable, slide ring carries head weight | |
| Deck front | 40 mm ahead of pan axis | |
| Tilt load at level | ~7 g·cm | **estimate** |
| Down-view before deck enters frame | ~35° was computed for the *earlier* 55 mm ball with an **assumed 41° VFOV** — **stale**, recompute once the lens is known | estimate |
| Hard stop | needed ~60° down (lens clears turntable by <1 mm at 90°) | not yet designed |

Ribbon path: down off the board's bottom edge → creased back under the
board → up behind it to axis height → flat along the axis out through the
hub and 6704 → 2-turn coil in the −Y pod → down the pod stem → across the
turntable → down the pedestal beside the pan servo → deck slot → slack loop
under the deck (pan still swings it; needs slack).

## Test ladder

Cheapest and most uncertain first. Each rung isolates one question so a
failure points at one cause — the drivetrain saga here was solved by
isolating, and mechanical faults on this robot have repeatedly mimicked
software bugs (`docs/lessons/2026-08-03-drivetrain-bringup.md`).

### T1 — Ribbon coil rig ⏳ printing

Files: `coil-test/` (cup, spool, lid, knob; preview PNG). All in print
orientation, supports not needed. Parts are multiple overlapping closed
shells per STL — the slicer should union them; check the slice preview.

Geometry: chamber ID 37.6 mm, 21 mm deep; spool Ø20 with a 17.4 mm × 1 mm
anchor slit; 1.8 mm exit slit through the wall at 180°; rim ticks at
−60/0/+60; 0.15–0.3 mm fits (scale 1–2 % or sand if tight).

Assembly: ribbon sideways through the spool slit → spool on floor pin → two
loose turns → out the wall slit → lid (ring down) over the square neck →
knob on neck, relaxed ribbon = pointer at 0.

**Use the spare Arducam 30 cm ribbon** (they came as a 2-pack) — paper does
not behave like FPC.

| Check | Pass |
|---|---|
| ±60° by hand, full range | turns smoothly, no jam at either end |
| Coil position after 50 cycles | stays centred in the chamber, edges not rubbing floor/lid |
| After ~300 cycles | no whitening/cracks at the spool slit or wall slit; ribbon edges unscuffed |
| One turn vs two | if 1 turn is equally smooth, pods can shrink (−width) |
| Signal (optional, stronger) | camera still images through the cycled ribbon (`rpicam-still`, see CLAUDE.md commands) |

Fail modes to name if seen: binding (coil too tight / chamber too small),
axial walking (needs a guide flange), crease fatigue at the slit (needs a
radius on the slit edge).

### T2 — Fit coupons (flat, fast)

Before any big part. Print small plates with graded features and keep the
winners as the modelling truth ("measure, don't derive"):

- **6704 seat:** bores 26.8 / 27.0 / 27.2 mm × 4 mm deep; **hub journal**
  19.8 / 19.9 / 20.0 mm. Record press vs slip for each.
- **Camera posts:** 28.0 mm pitch, holes for M2 at 1.6 / 1.7 / 1.8 mm
  (thread-forming) — fit the actual UC-439 and a real M2 screw.
- **Horn capture:** a pocket sized to the **horn Zach actually owns** —
  measure it first, +0.2 mm all round, plus the two small screw holes.
- **Square/servo pod pocket** for the MG90D: measure the servo, then
  +0.2 mm per side.

### T3 — Tilt drive: servo pod turning a hub (the core of this session)

Question: does a stock horn captured in a printed hub give a slop-free,
wobble-free tilt joint, supported on the other side by a 6704?

Rig: one pod with the MG90D + a short hub disc with a captured horn and a
long pointer (≥60 mm, so backlash shows as millimetres), the opposite
support a 6704 in a second pod, a bar joining the two pods at the real
spacing. No ball yet — a dummy mass on the hub at the real CG offset
(~30 g).

| Check | How | Pass (initial targets, revise with Zach) |
|---|---|---|
| Backlash | servo holding position, rock pointer by hand, measure tip travel | < 1 mm at 60 mm radius (< ~1°) |
| Wobble / axial play | push the hub along the axis | no visible play; bearing seat not rocking |
| Coaxiality | spin unpowered by hand | no tight spot over the range |
| Hold at level with dummy mass | servo powered at centre | no creep, no audible hunting |
| Hard stop | drive gently toward the stop | stop takes it, servo not stalled into it |

Servo drive for T3 **must not use the robot's channels** — see Bench rules.

### T4 — One ball half-shell + real camera

Print the −Y (idler-side) half with its two posts. Fit the UC-439 and check:
corner clearance to the shell; LDR sits behind its window; FPC can make the
bottom-edge crease and rise behind the board without sharp stress; IR-cut
wires have room; seam face flat. **Decide the half-to-half joining method**
here (open question).

### T5 — Full tilt stage

Both halves, both pods, coil, bearing, servo. Sweep ±60° with the servo;
take images at −60, 0, +60 (camera must stay live through the coil); check
the coil through a see-through or cut lid; confirm hard stops.

### T6 — Pan stage and whole head

Pedestal, slide ring, captured pan horn, deck mock-up with ribbon slot.
Pan ±90° with the ribbon slack loop under the deck. Only then consider
mounting on the robot.

## Recording results

- Every observed fact → a dated bench log in `docs/bench/`
  (`YYYY-MM-DD-ball-head-T<n>-<slug>.md`) **when it is observed**. Include
  print settings (material, layer height, walls, scale) — fit results are
  meaningless without them.
- Separate **measurements** from Zach's **comfort judgements** ("feels
  tight") — both grades are useful, don't build a geometry change on the
  second alone.
- A design mistake worth remembering → `docs/lessons/`.
- If a rung fails, record it as failed with the reason; don't quietly
  revise the concept numbers above — write the change underneath with a
  date.

## Bench rules that apply here

From CLAUDE.md, and they exist because sessions went wrong:

- **Do not unplug or re-seat the robot's servo plugs** (PCA9685 ch 4 tilt /
  ch 5 pan) for head testing. Plug drift has cost three sessions, and Phase
  4c's Task 18 still needs the robot as-is. Drive T3/T5 servos from a
  **spare MG90D (4-pack) on the spare PCA9685 (2-pack) or a plain servo
  tester**. If the robot's own board is used anyway, the OE gate, one step
  per invocation and verify-by-motion rules all apply.
- **One hardware step per invocation**, result verified before the next;
  never `&&`-chain robot commands.
- **Bench tools default gentle**: a first write after limp slams at full
  servo speed — soft-engage, slow slews, especially near a hard stop.
- **Announce each step; Zach owns the physical kill;** hands off while
  anything is commanded.
- Servo rail power: the robot's servos share the left ESC's 5 V / 2 A BEC.
  A bench rig on its own supply avoids that coupling entirely.

## Open questions

1. "Servo inside the ball" — pod-drives-ball (assumed) or servo relocated
   into the ball?
2. Ball half-to-half joining: screws into heat-set inserts, pins + screws,
   or a twist/bayonet ring on the seam?
3. Hard-stop design and angle (~60° down proposed; up-limit?).
4. Lens FOV (deferred) — drives the down-view number and the bezel size.
5. Is ~109 mm width acceptable? If T1 shows one coil turn works, pods can
   shrink; alternative is a ≥40 mm straight axle run instead of a coil.
6. Actual deck/turret height and front-edge position on the v2 chassis.
7. Which servo horn and screws are on hand (measure before T2).
8. Slide-ring material for the pan (PTFE washer, printed PETG on PETG, or
   a thin bearing).

## Files

```
head-v2/
  ball-head-validation-handoff.md   this file
  test-print-2/                     Zach's CAD exports (shared assembly coordinates, mm)
    z_mount_bottom.stl, z_mount_top.stl       pan stage
    y_tilt_mount_left.stl, _right.stl         split yoke (current)
    y_tilt_mount_onepiece_superseded.stl      earlier one-piece yoke
    y_tilt_face.stl                           camera shroud
    review_assembled.png, review_tilt_down_collision.png
  concept/                          ball concept, one shared frame, mm, Z up
    ball_concept_fixed.stl    deck, pedestal, pan servo, slide ring, IR headlights
    ball_concept_pan.stl      turntable, pods, 6704, ribbon coil + route
    ball_concept_tilt.stl     ball, board, holder, lens, posts, hub, horn
    ball_head_render_sheet.png, block_concept_superseded.png
  coil-test/                        T1 rig STLs (print orientation) + preview
  generators/                       the throwaway scripts that made all of the above
```

**Generators are scratch-quality**, not product code: they chain by
`exec`-ing slices of each other (`render_stl.py` → `render2.py` →
`concept.py` → `ball.py` → `ball2.py` → `export3d.py`; `coil_test.py`
stands alone apart from the renderer). Parameters live at the top of
`ball2.py` (board size, pitch, pod depth, pedestal, etc.) and
`coil_test.py`. Run from inside `generators/`; they write outputs next to
themselves. `ball_head_3d.html` + the `ball_parts.js` that `export3d.py`
writes are the interactive viewer. Rendering needs only numpy + Pillow.
They are concept geometry — **Zach models the real parts in Autodesk**;
use these for dimensions and as reference bodies, not as print files
(except `coil-test/`, which is printable).

## Working with Zach (for this work)

- Brief. One step per message at the bench, paced to how fast he can
  observe.
- He models in Autodesk himself; the useful output is **numbers and
  rationale**, rendered pictures, and printable test rigs — not a finished
  CAD file.
- "Ish" numbers delegate the exact value — measure and decide.
- He likes seeing geometry: renders and the interactive viewer landed well.
