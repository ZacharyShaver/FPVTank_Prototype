# Variant B handoff — 2026-09-19, end of session

Ball head where the tilt servo lives **inside the ball** and the mount is **one grown nest**.
Concept/test-fit geometry, not a validated design. Read this before touching
`../generators/tree_parts_b.py`.

State in one line: **the model is self-consistent and all four checks are green, but nothing
has been printed and the camera is still measured by guess.**

---

## 0. The next session

Zach's brief, in his order:

1. **Get it print ready.** Nothing in `print/` is current — the whole directory is renamed
   `.STALE-DO-NOT-PRINT` and it is gitignored now. A real print set is
   `python tree_parts_b.py` (~25 min, no `--no-print`), then `print_post.py b`, then
   `mesh_qa_b.py`. Do not cut one until §3 is closed.
2. ~~**Look for further problems in the cradle**~~ — **DONE 2026-09-19, see
   [`cradle-audit.md`](cradle-audit.md). Seven findings; three fixed, four open.**
   Fixed: the **90° flange screw opened into the bearing bore on both collars** (the triad is
   now `SCREW_A = [30, 150, 270]`); the ball's `smin` blends stood **1.17 mm proud of its own
   FLAT**, so the ball and the nest were **actually interfering by 0.52 mm** and the 0.4 mm
   interference grid could not see it (truncation re-imposed after the blends — gap is now
   +0.602 mm, overlap 0.00 mm³); and the **tilt servo had nothing holding it at all**, its
   "tab recess" having removed 0.00 mm³ — two bosses and two M2s now, Zach's design.
   Still open: a 0.95 mm web at all three flange screws, the trough grazing three faces, a
   coincident plane at |Y| 34, and **nothing locating the ball along Y** — 1.2 mm of float,
   wanting a shoulder on the hub against the 6704's inner race. The C-frame and the neck —
   what I expected to be wrong — are both fine.
3. **A ribbon coil captured in the trunk base**, so pan can go 360° continuously instead of
   ±90°. Zach will spec this next session; nothing is designed for it yet. What it will run
   into: the trunk is grown out of the pan pedestal (`trunk()`, `PED_R`, `BASE_Z`), and the
   ribbon currently leaves the nest's underside about **9 mm forward of the pan axis**, so
   panning drags it. "Routing it down the pan axis is unsolved" has been an open item since the
   first write-up — this is that problem being solved properly. Prior art in the repo:
   `pan_coil.py` / `pan_coil_check.py` from variant C.

---

## 1. What is on disk

| | State |
|---|---|
| `fusion/*.obj`, `viewer_parts_b.js`, `mesh_report.txt` | **CURRENT.** All 7 watertight, manifold, bodies=1, self-int=0, each hitting its face target |
| `step/post,axle,cap_minus` | **CURRENT and exact** — 0.00 mm³ disagreement. Import as solids |
| `step/ball_plus,ball_minus` | ⚠ **13.7 % / 9.5 % short. Not the part.** See `step/README.md`. `ball_plus` worsened on 2026-09-19: the analytic rebuild does not model the two new tab bosses |
| `fusion-convert/` | **SUPERSEDED**, kept as a record of what was tried |
| `test-parts/bearing_dummy.stl` | Printable stand-in for the 6704 while the real ones are in transit |
| `print/*` | **ALL stale, all renamed, and gitignored** |
| Viewer artifact | Current. Merge into it, never overwrite — it carries A and C too |

### Verify before trusting any of it

```bash
cd ../../generators
python tree_parts_b_check.py    # 32 rows: interference, view cone, camera
python tree_parts_b_driver.py   # can a driver reach each screw, at its step
python tree_parts_b_insert.py   # can each part physically reach its seat
python tree_parts_b_health.py   # thin walls, and same-part coincident planes
```

All four were green at the end of this session: **32 rows zero · 0 problems · 0 problems · none**.
Row count went 38 → 32 on 2026-09-19: the seven `bezel clear @ tilt` rows went with the bezel
(they sampled a part that no longer exists, and `ball @ tilt … vs nest` already covers the
front at all eight angles), and one `view cone vs the ball hole` row was added.

Cheap rebuild, no print STLs: `python tree_parts_b.py --no-print` (~6 min), then
`viewer_bundle_b.py`, `mesh_qa_b.py`, `fusion_convert.py`, `tree_parts_b_step.py`.

---

## 2. What changed this session

- **The servo dropped 5 mm.** The measured boss-and-spline stack is 9 mm, not the 6 the
  datasheet implied, and the horn's hub adds 3 more. The old geometry left a 1.4 mm post whose
  pocket breached the flange. The case base now crosses the seam, so the −Y half carries a real
  pocket and the pad became the floor the servo lands on.
- **Three faults Zach found by eye, none of which any check could see.** The axle sat 1.95 mm
  inside the camera board. The −Y pad ran the full width of the ball and straight through that
  board. Both bearing seats were **sealed pockets** — stepped down to a smaller bore on *both*
  sides, so no bearing could ever have reached them, while the README said to press them in.
- **Stiffening.** Worst attachment went from 647 mm³ of rail on 28 mm² of contact to 101 mm²;
  the pad 32 → 116; hub stub 97 → 263; socket hub 181 → 522. Internal ribs are filleted into
  the shell instead of butted, the rear wall is 2.4 mm where nothing lives, and the seam face
  plates went 1.6 → 2.2. About +20 % material.
- **Seam went M2 × 25 → M3 × 30**, because no M2 that long exists in Zach's box.
- **Three new checks** (`_insert`, `_health`, `ball_structure`) and a decimation-stall gate in
  `mesh_qa_b.py`.
- **The tilt servo is fastened now**, and was not before: two bosses to the tabs' underside,
  an M2 up through each, driven from the seam face before the halves close (Zach's design, the
  same way the pan servo is held in `roots`). The recess that was supposed to capture it removed
  0.00 mm³. README BOM and assembly updated -- its step 4d also still said M2 × 25 for a seam
  that went M3 × 30 in c36022c.
- **The ball is truncated again after its blends.** Eight `smin()` calls had pushed its face up
  to 1.17 mm past FLAT. That, not the collar, was the clearance fault.
- **The cradle audit §0.2 asked for, and the one fix that came out of it.** Five findings in
  [`cradle-audit.md`](cradle-audit.md); the flange-screw triad moved to `SCREW_A = [30, 150, 270]`
  and is now **named in one place** — it hid because it was typed out in six (`fork` ×2, `post`,
  `cap_minus`, `_driver`, `_step`). The last two now derive it rather than repeat it, which is the
  same drift `e79f5e6` already had to correct once.

---

## 3. Open, and blocking a print

**Three of the five are closed as of 2026-09-19. Two are left, and only one of those bites.**

| Symbol | Value | Status |
|---|---|---|
| `BOARD_X0/X1` | 8.0 / **10.0** | **MEASURED** — board is 2.0 thick (was 1.6, assumed) |
| `CAM_STANDOFF` | **19.0** | **MEASURED** — "21 mm off the board, −2 for the board itself". Lens tip at X 29.0 |
| `CAM_END_W` | 15.0 | still "14-15ish", but **no longer load-bearing**: the front is one Ø23.0 hole, sized to clear the corners of a 15 mm *square* housing by 0.9 mm |
| `BOARD_Y` | 18.0 | **ASSUMED half-width. The rails grip this, and it is now the one that bites.** |
| `RIBBON_W` | 16.0 | ASSUMED. Sets the rear slot, `BAND`, `TROUGH_W` |

Still wanted: **the board outline (length × width)** and the ribbon width. The axle's flat
clears the board by only **0.5 mm in Y**, so if `BOARD_Y` grows that is the first thing that
breaks — and `BOARD_Y` reaches `ball_plus`, `ball_minus` and nothing else (measured by
perturbation, not by reading the source).

**The bezel is gone.** Zach, 2026-09-19: *"just make a hole on the end, don't try to make a
tunnel to fit the camera. too much stuff to measure on the front."* It was a Ø16.0 bore down a
collar standing 1.9 mm proud of the sphere, and the moment the measured 19.0 stand-off went in,
the corners of the lens housing fouled its wall by 94 mm³. The front is now the plain sphere
with one oversize bore. Knock-ons, all of them improvements: `FRONT_SWEEP` replaces
`BEZEL_SWEEP` at 31.5 instead of 34.99, so the nest's lips stand off 3.5 mm less; the view cone
is launched from the **measured lens tip** instead of the front of a bezel that no longer
exists; `MOUTH_UP` went +5.0 → +7.5 because those two together clipped the cone by 0.15 mm at
full up-tilt; and there is a **new row** testing the cone against the ball's own hole, which
nothing asked while the aperture was a bore down a tube.

**Two decisions Zach has not made yet:**

1. **Pegs vs backstops** for the camera board. He chose "locating pegs, no screws" — but pegs
   pointing along X cannot be assembled: the ball splits at Y 0 and the board's holes run along
   X, so a peg would have to enter its hole sideways as the halves close. The workable forms
   are pegs in the **+Y half only** (needs the board's hole pitch) or **backstops** behind the
   board (needs no hole pattern). Nothing is built yet; the rails still do the job.
2. **Ball halves: solids or meshes.** They stopped being CSG when they were stiffened. The
   trade is written up with the numbers in `step/README.md`.

**Hardware Zach has, against what the design wants:**

| | needs | has |
|---|---|---|
| M3 × 30 ball seam | 3 | 4 ✓ |
| M3 × 10 roots to deck | 4 | 4 ✓ |
| M2 × 6 pan servo tabs | 2 | "a couple" ✓ |
| M2 × 8 flanges (post ×3, cap ×3) | 6 | ✗ **unresolved** |
| M3 × 16 | 0 | 4, no home |

The flange holes are only 3.8 mm deep, so a 6 mm stem is fine. Growing the flange plates
R 17.5 → 18.8 would take M3 and leave 1.8 mm of collar — but his M3 × 16 are far too long and
would punch into the ball and hit the horn.

---

## 4. Two rules this model has earned

**A cut must overrun the face it passes through, never stop flush with it.** Hit twice in one
day — `ball_minus` stalled at 44k faces against a 20k target, `fork` at 132k against 60k. Both
times the solid was fine and the *mesh* was degenerate, so watertight/manifold/bodies did not
catch it. The face count did, and both times it was printed in the build output and went
unread. `mesh_qa_b.py` flags a stalled decimator now, and `tree_parts_b_health.py` lists
same-part coincident planes.

**Every zero gets a negative control before it is believed.** Three check rows were added this
session that read zero while the geometry was wrong. Break the part on purpose and watch the
number move: camera-vs-axle scores 39.74 mm³ against the old axle and 0.00 against the new one;
the insertion rows block within 0.5 mm on the old collars and run clear over 9 mm on the new.

Both are written up in `../../lessons/2026-09-19-coincident-faces-and-insertion.md` and
`../../lessons/2026-09-19-surface-sampling-is-a-vacuous-check.md`.

---

## 5. Geometry that is settled

180° of tilt, rolled down 35° (−35° to +145°). Three separate things have to hold and each has
its own check row: the ball clears at every angle; the **rim stays out of frame** (the
mouth is cut 8° wider at the bottom and 5° at the top than the travel, because at the ends of
the swing the lens looks along the rim); and the rolling loop has somewhere to go (track +19°
to −76°, U seated 2° below straight back at neutral).

Envelope **74.9 × 68.0 × 82.7 mm**. Tilt axis at X 0, **Z 52.0**. Ball flats at |Y| 24.5 —
note the fillets bulge them to 24.89, leaving 1.11 mm to the collar. ⚠ **Both numbers are wrong, and
the first correction was wrong too.** 1.11 measured to `POD_Y0` = 26.0, the *named* collar
face, while `collar()` is called with `POD_Y0 - 1.0`. The audit then put the gap at 0.103 mm —
but that sweep silently dropped interfering rays, and the bulge is not 24.89 either: the ball's
blends reached **25.672**, so the two parts were **touching** by 0.52 mm. Fixed by re-truncating
the ball after its blends; the gap is now **+0.602 mm** with 0.00 mm³ of overlap. All three
numbers left standing, because what was believed is the point — see
[`cradle-audit.md`](cradle-audit.md) §1 and §6.

Live parameters are at the top of `tree_parts_b.py` — read them there, not from here.

---

## 6. Files

**Generators** (`docs/chassis/head-v2/generators/`)

- `tree_parts_b.py` — the whole variant. Parameters at the top; `PARTS` at the bottom carries
  each part's print orientation (measured, not guessed: the nest wants deck-plate-down, 11.8 %
  support and 1606 mm² of bed contact, versus 1 mm² mouth-up).
- `tree_parts_b_check.py` · `_driver.py` · `_insert.py` · `_health.py` — the four checks. Note
  `_check` uses **+deg = lens up**; variant A's `tree_parts_check.py` uses the opposite sign and
  was deliberately left alone.
- `ball_structure.py` — how each internal feature attaches to the shell. **Only covers the ball
  halves; the cradle has never had this run on it** (see §0.2).
- `tree_parts_b_step.py` · `step_kit.py` · `step_mesh_prep.py` · `build_b.py` — the STEP route.
- `bearing_dummy.py` — the printable stand-in bearing.
- `print_post.py`, `mesh_qa_b.py`, `viewer_bundle_b.py`, `fusion_convert.py`.

Not this variant, from a parallel line: `tree_hood.py`, `tree_hood_check.py`, `pan_coil.py`,
`pan_coil_check.py` (variant C, the fixed hood). **`pan_coil*` is worth reading for §0.3.**

**Viewer:** https://claude.ai/artifact/94q1eeyW7FKFkLAPTugMSt — carries A, B and C. **Merge onto
the live version, never overwrite it**: read it first, apply only B's changes, republish.

**Also see:** `cradle-audit.md` (the 2026-09-19 audit of `fork`, and the blind spots it
found in the four checks), `README.md` (BOM, assembly order, fits to check, the Fusion route),
`step/README.md`, `../../lessons/2026-09-18-flat-cable-and-driver-access.md`.
