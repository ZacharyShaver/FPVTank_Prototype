# Used parts — current state and edit history

**What this is:** the STLs actually used in *this* build, checked into the
repo so their current state is versioned and their edits are traceable.
`stl-parts.md` is the full visual catalogue of everything in the source
folder, used or not; this file is the shorter question of "what is on the
robot, and how far has it drifted from the download?"

Files live in [`parts/`](parts/). Source of record remains:

```
reference/fpv-rover-v2/        (in this repo since 2026-09-27)
```

## ⚠ Baseline, not current

Every file copied in on 2026-08-03 was dated **2026-01-18** — i.e. these
are the **original downloads**, not Zach's edited versions. The body and
top-parts edits exist in Blender and had not been exported back to that
folder at the time of the copy.

So `parts/` is the **as-downloaded baseline**. That is deliberate and
useful: when an edited export lands here, the git history shows exactly
what changed and when. But do not treat the current contents as "what is
printed on the robot" until the edited exports replace them.

## Status legend

- ✅ **used** — on the robot
- ✏️ **used, edited** — modified from the download; see change log
- 🔜 **used, edit planned**
- ❌ **not used in this build** — not copied into `parts/`
- ❓ **unconfirmed** — copied in, but nobody has confirmed it is installed

## Parts

| Part | Status | Notes |
| --- | --- | --- |
| `body-rover-v13` | ✏️ used, edited | Main tub. Two holes being removed (in progress 2026-08-03). |
| `top-parts-v15` | ✏️ used, edited | Vented top deck + brackets. Edited; details TBC. |
| `motor-mount-v13` | 🔜 edit planned | Motor flange + gearbox bracket. |
| `inner-frame-left-high-v10` | ✅ used | **The tall variant is the one in this build.** |
| `inner-frame-right-high-v10` | ✅ used | Tall variant. |
| `inner-frame-left-v15` | ❌ not used | Standard-height frame — superseded by the high variant. |
| `inner-frame-right-v15` | ❌ not used | Standard-height frame. |
| `camera-mount-main-v11` | ❌ not used | This build uses its own pan/tilt turret, not the stock cradle. |
| `camera-mount-left-v11` | ❌ not used | |
| `camera-mount-right-v11` | ❌ not used | |
| `esc-mount-left-v12` | ❌ not used | ESCs are mounted differently in this build. |
| `esc-mount-right-v12` | ❌ not used | |
| `front-cover-v13` | 🔜 edit planned | Body front end cap. |
| `rear-cover-v12` | 🔜 edit planned | Body rear end cap (vented). |
| `outer-frame-v13` | ❓ unconfirmed | Outer track-side plate, carries the axles. |
| `front-main-cog-v13` | ✅ used | 12-tooth front idler sprocket. |
| `rear-main-cog-v13` | ✅ used | 12-tooth rear drive sprocket (keyed). |
| `small-cog-v2` | ✅ used | Flanged roller ring. |
| `big-bevel-gear-41-v13` | ✅ **fitted 2026-08-03** | 40T crown, **4:1 — the correct set.** Source: `alternitive wheel mounts/`. |
| `small-bevel-gear-41-v11` | ✅ **fitted 2026-08-03** | ~10T pinion, 4:1. Only 16.2 mm across vs the 20T's 24.8 mm — a smaller, more fragile bore, so check the grub screw periodically. |
| `big-bevel-gear-21-v11` | ❌ replaced 2026-08-03 | 40T crown, 2:1. Fitted by mistake from the start. Kept for history. |
| `small-bevel-gear-21-v11` | ❌ replaced 2026-08-03 | 20T pinion, 2:1. **This is the part that was slipping** — see below. |
| `track-v13` | ✅ kept | Standard printed track link — part of the design, **not what is currently fitted.** |
| `big_track_v11` | ✅ kept | Wide/deep printed shoe variant. |
| `rubbertrack-v12` | ✅ kept | Chevron tread pad, flexible filament. |
| `FLEX_TRACK_2mm_ANGLED_32track15.1mm_32N_153mm_v2_Tessellation.4_1` | ✅ **installed** | **The track actually on the robot.** One-piece flexible continuous TPU track — *not* the printed link-by-link tracks above. By **Luengoa**, [Thingiverse thing:7127065](https://www.thingiverse.com/thing:7127065). Author's claim: more durable than the originals, quieter, and easier to refit if thrown. In [`parts/third-party/luengoa-flex-track/`](parts/third-party/luengoa-flex-track/) with its README and LICENSE. **CC BY-NC** — see licensing note below. |
| `led-mount-v12` | ❓ unconfirmed | Headlight disc trunnion. |
| `tow-bar-plug-v12` | ❓ unconfirmed | Blanking plug for the tow-bar socket. |

## ⚖️ Licensing — the fitted track is CC BY-NC

The installed TPU track is licensed **Creative Commons
Attribution–NonCommercial** by its author (Luengoa). This repo is
private, so simply keeping a copy here is fine, but the NC term is worth
knowing early given this build is a prototype for something else:

- **Non-commercial only.** If anything downstream of this project is ever
  sold or used commercially, that track cannot ship with it.
- **Attribution required** wherever it is shared or published.
- The `LICENSE.txt` and `README.txt` are kept alongside the STL
  deliberately — do not separate them from the model.

If a commercial path is ever on the table, the options are: design an
original track, find a permissively licensed one, or ask Luengoa for
permission. Cheapest to resolve now, most expensive to discover late.

### Open questions

1. `outer-frame-v13`, `led-mount-v12`, `tow-bar-plug-v12` — still
   unconfirmed; a yes/no pass turns them into ✅ or ❌.
2. The printed link tracks (`track-v13`, `big_track_v11`,
   `rubbertrack-v12`) are kept for history but are **not fitted** — worth
   confirming they are fully superseded rather than a fallback.
3. **Where is the edited `top-parts` file?** An updated version with the
   edits exists, but not in the source folder (everything there is dated
   2026-01-18). Its export should replace the baseline in `parts/`.
4. Same for the body once the hole removal is exported.

## ✅ Bevel set corrected — 2:1 → 4:1, fitted 2026-08-03

The robot had been running the **2:1** pair since the start; this build is
meant to use the **4:1** pair. Swapped and confirmed the same day.

**Result: noticeably smoother, and the crown no longer rubs the motor
mount.**

The reason is the bevel geometry, not clearance luck. **The 4:1 crown
sits at an angle, rising away from the mount, and `motor-mount-v13` has a
matching angled face for it.** A bevel pair's pitch cone angles are set
by its ratio, so a 4:1 pinion meets its crown at a genuinely different
shaft angle than a 2:1 pinion does. The 2:1 set was therefore meeting a
mount built for a different cone geometry — which is why the crown fouled
it. The mount was right all along; the gears were wrong.

This also answers the open question about the missing "alternative wheel
mount": there isn't one to find. `motor-mount-v13` *is* the 4:1 mount.

Worth recording the prediction that was wrong: the 4:1 crown is **thicker**
(9.4 mm vs 6.5 mm), so it looked like it might rub *worse*. Thickness was
never the variable — the mounting angle was.

Consequences:

- **All four min-moving pulses were measured through the old 2:1 ratio
  and are invalid.** More reduction means less throttle to move, so every
  number should come out lower. `DRIVE_CALIBRATION_COMPLETE` stays
  `False` until the re-survey. Use `tests/hw/esc_sweep.py`.
- **The smaller pinion is more fragile, not less.** Its bore and
  grub-screw boss have less material than the 20T that already failed by
  slipping. Check it periodically, and print replacements with extra
  perimeters and a solid hub.

## Change log

Newest first. One row per exported change to a used part.

| Date | Part | Version | Change | Why |
| --- | --- | --- | --- | --- |
| 2026-08-03 | `body-rover-v13` | v13 → v14 (in progress) | Removing two holes; **plus the full revision list in [`body-revision-brief.md`](body-revision-brief.md)** — right-rear deformation, bottom holes not cutting through, heat-set inserts, screwdriver access, top fastening, tail mount | Assembly findings; **this part needs reprinting** |
| _export pending_ | `top-parts-v15` | — | Edited — updated version exists, not yet located/exported here | |
| _planned_ | `motor-mount-v13` | — | Edit planned | |
| _planned_ | `front-cover-v13` | — | Edit planned | |
| _planned_ | `rear-cover-v12` | — | Edit planned | |

## Notes that affect future prints

- **The 20T bevel pinion must have its grub screw fitted.** On 2026-08-02
  the drivetrain fully decoupled mid-session: the motor spun audibly while
  the wheel free-wheeled with no magnetic cogging felt by hand. The
  printed bore had been carrying full motor torque on a friction fit
  alone. Fitting the grub screw onto the shaft flat fixed it. See
  `../bench/2026-08-02-right-wheel-reprint-calibration.md`.
- **A printed pinion on a friction fit is the weak link of this design.**
  For the v2 chassis, a metal pinion with a grub-screwed hub onto a
  flatted shaft is the durable answer.
- **The right wheel was reprinted** before the 2026-08-02 session; the
  warped original had made that side's drive calibration impossible.

## Related

- `stl-parts.md` — full visual catalogue with renders and bounding boxes
- `../../HARDWARE.md` — electronics, parts list, GPIO map
- `render_stl_views.py` — regenerates the render strips after an edit
