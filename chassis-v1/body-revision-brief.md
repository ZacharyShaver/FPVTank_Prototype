# Body revision brief — findings from the 2026-08-03 assembly

Requirements captured at the bench by Zach while assembling the robot, for
the next revision of the body model. This is the working checklist for the
Fusion session, not a design spec — some items need measuring first.

Baseline part: `body-rover-v13`, 207.1 × 50.0 × 110.0 mm
(`parts/body-rover-v13.stl`). Related: `used-parts.md`,
`docs/lessons/2026-08-03-drivetrain-bringup.md` in FPVTank_Control.

## 1. Defects in the current print — reprint required

**Right rear deformation.** Present on the printed part.

> Worth deciding which kind of problem this is before modelling anything:
> a *print* defect (warping, bed adhesion, cooling) is fixed by reprinting
> as-is, while a *model* defect needs geometry work. If the STL measures
> correct in Fusion, don't change the model — change the print settings.

**Bottom holes do not fully extend through.** The holes on the underside
stop at the first body — a boolean that didn't cut through the full stack,
which is the classic multi-body symptom. Fix by ensuring the cut extends
"All" / "Through All" rather than a fixed depth, then verify by sectioning
the model before export.

This part needs reprinting regardless.

## 2. Heat-set inserts — wheel section to body

Add bosses for **heat-set threaded inserts** at the bottom **front and
rear** connections between the wheel section and the body.

Things to fix before modelling:

- **Which insert?** Buy them first and measure. M3 brass inserts are the
  usual choice, but the required hole diameter varies by insert (commonly
  ~4.0–4.2 mm for M3) — model to the insert you actually own.
- **Boss wall thickness.** The insert is installed hot and displaces
  plastic; a thin boss splits. Aim for ≥2 mm of material around the hole.
- **A lead-in chamfer** at the mouth helps the insert start square. They
  go in crooked easily.

> Rationale worth recording: this is the same failure class as the pinion
> grub screw. Threads cut directly into printed plastic strip after a few
> cycles, and the drivetrain is a part you will be taking on and off
> repeatedly while prototyping.

## 3. Screwdriver access holes

Add clearance holes running **from the top, under the wheel cover,
straight down to the bottom screws**, so a driver can pass through without
disassembly.

- Hole must be **coaxial with the screw axis** — an offset of even a few
  millimetres makes it useless.
- Size for the **driver shaft**, not the screw head, and add clearance —
  measure the actual driver.
- Check the path is clear the whole way down in section view; this is
  exactly the cut that silently stops at the first body (see item 1).

> This is the same principle as the ESC LED visibility problem: a
> maintenance action you cannot perform without disassembly is one you will
> avoid doing, and prototypes get taken apart constantly.

## 4. Top part needs securing

The top currently has no fastening method. Options, roughly in order of
prototype-friendliness:

| Option | Notes |
|---|---|
| Screws into heat-set inserts | Consistent with item 2; strongest; needs boss space |
| Captive nuts in slots | No inserts needed; nuts can fall out during assembly |
| Snap fit | No hardware, but printed snaps fatigue — poor for a part opened often |
| Magnets | Fast access, no tools; weak against vibration |

Given how often this gets opened during bring-up, favour something
**tool-free or single-tool** and rated for many cycles.

## 5. 🦂 Tail section — the v2 defining feature

Extend the **centre portion** of the body to carry a mount for the tail.
This is what gives Scorpion its name.

The tail must house:

- **Raspberry Pi 5** — model available at
  `reference/raspberry-pi-5/` in this repo (the STEP is in `reference/downloads/raspberry-pi-5/`)
  (including the **active cooler** variant; design around that one, it is
  taller)
- **PCA9685** — a native Fusion file exists:
  `Downloads/pca9685-...-model_files/PCA9685.f3d`
- **Power feed from the drive batteries**
- **Cable routing** for all of it

### ⚠ Power — decided 2026-08-03, see HARDWARE.md

**Plan: a dedicated 5 V / 5 A UBEC off one drive pack, feeding the Pi
only.** The servos stay on the left ESC's existing 2 A BEC. Full wiring,
budget and the three hardware-killing gotchas are in `HARDWARE.md` →
*Planned: onboard Pi power via UBEC*. Summary of what affects the tail:

- The Pi cannot share a rail with the servos — servo current spikes dip
  the rail and brown out a Pi 5, which then gets debugged as a software
  crash. Two separate regulators, so **two devices to find room for**.
- **Pick the actual UBEC before dimensioning the tail.** Its footprint and
  heat dissipation set the enclosure volume, and a switching regulator in
  a sealed printed box needs airflow or it derates.
- Budget space for a **LiPo low-voltage alarm** on the balance lead — a
  UBEC has no cutoff, and this project has already lost two packs to
  over-discharge.
- The Pi boots whenever the pack is connected (the ESC switch is
  signal-level and won't gate the UBEC), so **an inline switch wants a
  reachable spot** in the tail.

**Still open:** whether to feed from one pack and accept that the Pi dies
with it, or diode-OR both. One pack is simpler and fine for a prototype
provided the failure mode is understood — the Pi dropping mid-drive
leaves the PCA9685 free-running its last command.

### Design-in from the lessons doc

Two things that saved real time this session and would be lost by burying
the electronics (see FPVTank_Control's `docs/lessons/2026-08-03-drivetrain-bringup.md`):

- **ESC arm LEDs must stay visible.** Solid vs blinking is the only honest
  arming indicator — the beeps are inaudible at the bench. Light pipes or
  cutouts.
- **Connectors must be reachable without disassembly.** Plug drift has
  cost this project three sessions; it is only cheap to recover from when
  you can get at the headers.

Also worth designing in: **access to the OE gate wiring and the killswitch
path**, since those are the safety-critical connections.

## Suggested order

1. Measure everything physical first — inserts, driver shaft, chosen power
   converter. Modelling against guessed dimensions is rework.
2. Fix the defects (items 1–2) and reprint, since that part blocks
   reassembly.
3. Access holes and top fastening (items 3–4) — same print.
4. Tail (item 5) last: it is the largest change, and it depends on the
   power decision above.
