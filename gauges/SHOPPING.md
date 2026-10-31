# Shopping list: the one-piece body's drive (2026-10-30)

Zach picked the JGB37-520 (2026-10-30: "put JGB37-520"), the cheaper of chassis-v2's two 37 mm gearmotors (the other
was the Pololu 37D 30:1, $61 each). Buy one first and caliper it: the pod's bore, lip holes and hub are sized to
datasheet numbers*. Numbers marked * are from sellers' listings, which disagree with each other.

| Item | Qty | On hand | Why |
|---|---|---|---|
| JGB37-520 gearmotor, **12 V, 333 rpm (~30:1), with Hall encoder**, 6 mm D shaft | 1 now; then one a wheel + 1 spare (5 for 4 wheels, 7 for 6) | no | On the 2S packs (7.4 V) it runs about 200 rpm*, the Trainer's plan. Caliper: gearbox length, the face's holes (count, circle, depth), shaft length and flat. |
| TPU 95A filament, 1 kg | 1 | ask | Tyres (~100 g* each) and bumpers (~400 g* on a body). |
| M3 x 8 button screws | 6 a motor | yes | Gearbox face to the pod's 5 mm lip: 3 mm into the gearbox at most (Pololu's warning for its 37D; check the JGB's hole depth). |
| M3 heat-set inserts, M3 x 5 set screws | 1 a wheel each | ask | The hub onto the shaft's flat. |
| 18 AWG silicone wire, 2 mm bullet connectors (or solder splices) | a few | ask | Each side's motors in parallel onto that side's ESC. |
| 6-pin JST-PH lead (usually in the box) | 1 a motor | - | Motor +/-, encoder 5 V, GND, A, B. The encoder wants 3.3-5 V, not the motor's supply*. |
| Raspberry Pi Pico (optional) | 1 | ask | Counts the encoders for the Pi, if wheel speed is wanted. |

**Kept:** the two INJORA 35/45/55T ESCs, the four Zeee 2S packs, the PCA9685. **Freed:** the two INJORA 540 55T
motors (the tracked rover's).

## What happens to the ESCs

They stay (Zach, 2026-10-30: "Keep the ESCs"). Nothing has to change. Each side's 2-3 gearmotors are wired in parallel to that side's ESC, and the robot skid-steers
as the rover does now: the Control code (PCA9685 pulses to two ESCs) and the wiring stay as they are. The sims already
drive each side as one ("each side's speed held"), and the body's bay already holds two ESCs.

- **Current:** the ESC is built for a 540 crawler motor (chassis-v2 notes it as a clone of the Hobbywing 1060, a 60 A
  brushed ESC). Three small gearmotors stalling together draw a fraction of that (JGB37-520 listings give 1.2-2.4 A
  stall at 12 V for the slower ratios*; none gives the 333 rpm's).
- **Given up:** wheels on one side can't differ (no per-wheel traction control), and the ESC doesn't read the encoders;
  they're only for the Pi to read wheel speed. A Pico counts them easily; the Pi's own pins in Python may struggle at
  the ~2 kHz a channel* a motor-shaft encoder gives at full speed.
- **Later, if per-wheel control is wanted:** a dual H-bridge driver per pair of motors (e.g. a Cytron MDD10A, 2 x 10 A)
  replaces the ESCs. That's a wiring and Control change, not a body change.
