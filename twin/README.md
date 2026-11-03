# The real twin

Printed parts that test the sim's numbers against the real robot, so the sim can be realigned from what they show
(2026-11-03: a week of finding sim-vs-reality gaps before more search work). `tools/config.py` has the paths
(`TWIN`, `TWIN_OUT`); `twin/out/` is untracked.

## The Trainer's tub (`trainer_tub.py`), print 1

This is the sim's own housing for the inside parts, printed as drawn. Every search design carries the Trainer's parts
where this tub holds them. It's chassis-v2/rugged.py's `tub()` with wheels, as trainer.py builds it, and had never been
printed. The only change: two loose turret-deck ledges that float above the tub's top are left off.

```
python twin/trainer_tub.py      # twin/out/print/trainer_tub.stl, picture twin/out/trainer_tub.png, checks
```

- **Size:** 276 x 140 x 50 mm, floor down.
- **Print:** 10h23m and 236 g of PLA, with Zach's normal settings. Supports go in the belly tunnel and the aft ramp.
- **Checks:** Zach's parts placed where the sim puts them touch nothing. Each check has a control that reads nonzero.
  His ESC is placed at his caliper size, 45 x 24 x 34. It fits the 26.5 bay with 3 mm to spare, so the sim's 18 mm
  guess didn't matter here.

**Room round each part, from the sim:**

| Part | Room |
|---|---|
| Packs | 0.5 mm to the wall and 1.0 mm to the tunnel: 1.5 mm of play in all |
| ESCs | 0.5 mm to the wall, 3.0 mm to the tunnel |
| ESC length | 0.5 mm between its two stops (his 45 mm ESC); the sim's own 46 mm ESC overlaps the forward stop by 0.5 |
| Pi stack | stands 5.3 mm over the tub's top (the carapace covers it in the sim) |
| Pi and PCA | sit loose on the tunnel roof: the tub has no mounts for them; the Pi's 5 mm TPU isolators\* aren't printed |

**To record when the parts go in:**
- does each part go in, and how tight;
- where the leads go;
- whether the T-plugs reach between each pack and its ESC (they sit end to end, with only a 1.5 mm stop between);
- what has no room.

## Insides boxes (`boxes.py`): superseded before printing

Superseded 2026-11-03 before printing: Zach chose the Trainer's own tub (above), the sim's housing, over free-standing
boxes. The STLs moved to `twin/out/boxes-superseded/`.

These are the boxes the inside parts sit in, v0, printed to shake out sizing. The parts are laid out as the sim lays
them, adding the walls, clearances and lead room the sim leaves out. There are two kinds:
- **Brain box, 173 x 62 x 32:** the Pi 5 stack with its USB end aft and the end open, and the PCA9685 forward of it.
  - The Pi stands on four rings at its mounting holes; the HAT kit's screw heads drop into them.
  - A window in one long wall leaves the USB-C and HDMI side clear.
- **Side box, 221 x 31 x 48, two of them:** the ESC aft, a 25 mm lead bay for the T-plugs, then the pack, both on edge.
  - The search moves the packs. Here the ESC moves with its pack, which ends the packs-into-ESCs clash.

```
python twin/boxes.py      # STLs + plate to twin/out/boxes-superseded/, picture twin/out/boxes.png, checks
```

The boxes have open tops and flat bottoms, and no mounting yet: that waits for the fit check and the screws on hand.
Every cutout runs out through the top edge, so no supports are needed. Plate: 221 x 140; 4h14m and 166 g of PLA with
Zach's normal settings.

The guessed numbers are in `GUESSES` in `boxes.py`:
- the clearance (0.5 a side);
- the Pi rings (4 tall, 6.5 hole);
- the SD card's overhang;
- the Pi-to-PCA gap (6);
- the room for the PCA's end headers (12);
- the lead bay (25);
- the PCA's size;
- the HAT's 16 mm standoffs.

**Not in yet:**
- **Parts not bought:** the Pi regulator, the arm UBEC, the INA219, the WiFi dongle, the alarm and the switches. They
  get their own small box once bought.
- **The third pack:** the power plan in HARDWARE.md feeds the Pi from its own pack C, but the sim carries only two packs.

## Fit cups (`fit_cups.py`): superseded before printing

Superseded 2026-11-03 before printing: Zach wanted the boxes the parts sit in inside the robot (above), not a test cup per
part. Kept as a per-part size check.

One open cup per inside part Zach owns, at the size the sim gives it (`gauges/body.parts()`, the Trainer's parts that
every search design carries). The motors and the head are left out: the head's parts are already real.

```
python twin/fit_cups.py      # cups + plate STLs to twin/out/fit-cups-superseded/, picture twin/out/fit_cups.png, checks
```

- **Cup:** the sim's box plus 0.3 a side, a 3 mm rim, and four corner posts as tall as the sim says the part is. The sides
  are open above the rim, so leads come out anywhere.
- **Floor:** runs 22 mm past the box, with a raised ring every 5 mm (double at 10 and 20) counted from the sim's box
  face. A plug or lead's protrusion reads straight off the rings.
- **Each label** is the size the cup was built to, engraved on the floor.

| Cup | Size built (X x Y x Z, mm) | Where the number comes from |
|---|---|---|
| Pack | 141 x 26 x 45.7, on edge | Zach's model's box (`LeftBattery.stl`) |
| ESC | 45 x 24 x 34, on edge | Zach's caliper (2026-10-11). **The sim still has 46 x 18 x 34** |
| Pi 5 stack | 89.1 x 57.2 x 27.2 | Pi 5 + cooler (his model), M.2 HAT+ on 16 mm\* standoffs, Hailo-8L |
| PCA9685 | 62.2 x 25.7 x 12.4 | Adafruit's size\*; his is a generic clone |

\* = a guess. The 0.3 mm clearance is a pick, not a tested rule.

**What to record for each part:**
- does it drop in, go in tight, or not go in (and which way it's too big);
- how far it stands over the posts;
- how far its plugs and leads stick out, read off the rings.

That's the gap list the sim gets realigned from.

**Not printed** (not bought yet): the Pi's regulator, the arm UBEC, the INA219, the WiFi dongle, the LiPo alarm and
the switches.

**Known layout gaps** (from the sim, not this print): the sim packs the parts 0.3–1.3 mm apart with no room for walls
or leads. Those gaps are PCA to Pi 0.3 mm, ESC to pack 1.0 mm, Pi to the right pack 1.3 mm. Separately, the search's
pack shift drives the packs into the ESCs.

**Plate:** `plate_fit_cups.stl`, 282 x 179 mm, laid out by hand because Orca's arrange left two cups off. Sliced with
Zach's normal settings, not draft (the fit is the point): 2h51m, 102 g, PLA, no supports.
