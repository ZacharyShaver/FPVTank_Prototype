# Shopping list: the one-piece body's drive (2026-10-30)

Zach picked the JGB37-520 (2026-10-30: "put JGB37-520"), the cheaper of chassis-v2's two 37 mm gearmotors (the other
was the Pololu 37D 30:1, $61 each). Buy one first and caliper it: the pod's bore, lip holes and hub are sized to
datasheet numbers*. Numbers marked * are from sellers' listings, which disagree with each other.

| Item | Qty | On hand | Why |
|---|---|---|---|
| JGB37-520 gearmotor, **12 V, 333 rpm (~30:1), with Hall encoder**, 6 mm D shaft | 1 now; then one a wheel + 1 spare (5 for 4 wheels, 7 for 6) | no | On the 2S packs (7.4 V) it runs about 200 rpm*, the Trainer's plan. Caliper: gearbox length, the face's holes (count, circle, depth), shaft length and flat. |
| TPU 95A filament, 1 kg | 1 | yes (Inland TPU, 95A; Zach, 2026-11-08) | Tyres (~100 g* each) and bumpers (~400 g* on a body). |
| M3 x 8 button screws | 6 a motor | yes | Gearbox face to the pod's 5 mm lip: 3 mm into the gearbox at most (Pololu's warning for its 37D; check the JGB's hole depth). |
| M3 heat-set inserts, M3 x 5 set screws | 1 a wheel each | ask | The hub onto the shaft's flat. |
| 18 AWG silicone wire, 2 mm bullet connectors (or solder splices) | a few | ask | Each side's motors in parallel onto that side's ESC. |
| 6-pin JST-PH lead (usually in the box) | 1 a motor | - | Motor +/-, encoder 5 V, GND, A, B. The encoder wants 3.3-5 V, not the motor's supply*. |
| ~~Raspberry Pi Pico (optional)~~ | - | not needed | **Resolved** (Zach, 2026-11-08): his ESP32-WROOM-32 counts the encoders instead. |

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
  they're only for the Pi to read wheel speed. His ESP32 counts them (below); the Pi's own pins in Python may struggle at
  the ~2 kHz a channel* a motor-shaft encoder gives at full speed.
- **Later, if per-wheel control is wanted:** a dual H-bridge driver per pair of motors (e.g. a Cytron MDD10A, 2 x 10 A)
  replaces the ESCs. That's a wiring and Control change, not a body change.

## Driving four motors with two ESCs (2026-11-07)

Zach: "our esc drives one motor at a time if im not mistaken and we only have two". An ESC has one output, but two
motors can share it in parallel: they get the same voltage, so a side's two wheels turn together, as skid steering wants.
The load is small. Listings give a 333 rpm JGB37-520 about 0.2 A free-running and up to about 2 A stalled, at 12 V
([Colgroad](https://colgroad.com/product/dc-gear-motor-333rpm-with-encoder-12v-jgb37-520/)). So a stalled pair draws
about 4 A, and less on 2S. The ESC was bought for an INJORA 540 55T crawler motor, which draws far more. INJORA publishes
no current rating for it.

| | A: two a side on each ESC (pick) | B: a driver channel a motor |
|---|---|---|
| What | Each side's two motors in parallel on that side's ESC | 2 x [Cytron MDD3A](https://robotshop.com/en/cytron-3a-4-16v-dual-channel-dc-motor-driver.html) (3 A a channel, 5 A peak, 4-16 V), one channel a motor, the ESCs retired |
| Control | As now: the Pi through the PCA9685 to two ESCs; the code doesn't change | The ESP32 drives the four channels; the Pi talks to the ESP32 |
| Encoders | The ESP32 reads all four (its pulse counter hardware does 8, [ESP32Encoder](https://www.github.com/madhephaestus/ESP32Encoder)) and the Pi holds each side's speed through its ESC, as the sims do ("each side's speed held") | The ESP32 reads them and holds each wheel's speed itself |
| Gives | Skid steering with each side's speed held: what the sims assume | Each wheel on its own: traction control, more than the sims model |
| Costs | $0 more (the wire and bullets below) | about $25 for two MDD3As, new firmware, more wiring |

**A it is** (Zach, 2026-11-07: "lets just do A for now"). His ESP32 is an ESP32-WROOM-32 dev board, an original ESP32,
so all four encoders get hardware counters. Move to B only if holding speed per side through an RC ESC turns out too
coarse at a crawl. Two things to
check on the motor when it comes: the encoder's supply (it must run at 3.3 V for the ESP32's pins, or needs level
shifting) and its pulses a turn.

His boards (2026-11-07: "an arduino, esp32, a pi4, and a pi mini"): the **ESP32** does the encoders: it's an original
ESP32, with 8 pulse counters for the 4 encoders, so no Pico. An Arduino Uno has only two interrupt pins, too few for four
encoders. The Pi 4 isn't needed in the robot. The "Pi mini" is a Pi Zero (Zach): not
needed either, since the ESP32 counts the encoders and the Pi 5's second camera port takes the tail camera later.

## Missing parts (2026-11-07)

**Updated 2026-11-08, Zach:** "lets stick with using one for the motors one for the pi". One pack runs both ESCs through the
Y-harness and the other runs the Pi through the regulator, so the robot comes off the wall. **Now** adds the regulator, the
alarm, the INA219 (review C6, Zach: "Buy it now"), the Y-harness, the 20 AWG wire and a stop button (review C2): about
**$180-270**, with the pinhole lens off the list (review C8). The selector waits. This supersedes the tethered call below.

**Updated 2026-11-07 (evening), Zach:** he has a T-plug; "battery unification is not really necessary yet"; he may have
TPU already; he can find cheaper straps; the ESP32 he has replaces the Pico. So the packs stay one per ESC (review C1:
two packs, the Pi tethered), and everything for the Pi's own pack waits: the selector, the Y-harness, the regulator, the
alarm, the INA219 and the Pi's inline switch. **Now:** the pinhole lens, the four more motors, 18 AWG wire and
bullets, the IMU, and M3 inserts for the lid if they're not on hand: about **$95-180** (2026-11-08; the standoffs and the
Pico are off the list). TPU is on the shelf (Zach, 2026-11-08: Inland TPU, 95A).

Everything the robot still needs that Zach doesn't own, from the power plan (FPVTank_Control `HARDWARE.md`, "Planned:
power layout", chosen 2026-10-11), the pinhole camera (`docs/decisions.md`, 2026-11-07) and the drive above. Links are
the ones already chosen in those notes; the rest are specs to shop by.

**Prices** (looked up 2026-11-07, USD, before shipping and tax; listings change, so check before buying). A range is the
spread between sellers found; the source is the cheapest sensible one.

| Item | Qty | For | Price each | Line | Notes |
|---|---|---|---|---|---|
| JGB37-520 gearmotor, 12 V 333 rpm, Hall encoder | 1, then 4 more | Drive | $10-22 ([AliExpress](https://www.aliexpress.us/item/3256807403055518.html) $11.59 with bracket and wheel; [OzRobotics](https://ozrobotics.com/shop/encoder-reduction-motor-jgb37-520b-12v-dc-deceleration-motor-12v-333rpm/) $22) | $42-88 for the 4 | One is coming (Zach, 2026-11-07: next weekend); caliper it before the pods are sized. Listings disagree on the encoder's pulses a turn (11 or 20). |
| ~~TPU 95A filament, 1 kg~~ | - | ~~Tyres, bumpers~~ | - | $0 | **Not needed** (Zach, 2026-11-08): he already has Inland TPU, which is 95A. |
| [Pololu D36V50F5](https://www.pololu.com/product/4091) fixed 5 V regulator | 1 | The Pi off its own pack | $39.95 (Pololu) | $39.95 | 25.4 x 25.4 x 9.5 mm. Fixed 5 V, so it can't be set to 6 V by mistake. Holds 5 V down to about 5.9 V in at 2.5 A (its dropout graph, read by eye). Meter it under load before the Pi goes on. |
| 1-8S LiPo checker with buzzer | 1 | The Pi pack's low-voltage alarm | $4-5.50 ([Race Day Quads](https://racedayquads.com/products/1-8s-lipo-battery-voltage-tester-low-voltage-buzzer-alarm) $3.99; [GetFPV](https://www.getfpv.com/batteries/battery-accessories/1-8s-lipo-battery-voltage-tester-low-voltage-buzzer-alarm.html) $5.49) | $4-5.50 | The regulator has no cutoff; set ~3.5 V a cell. |
| [Carling L16D1S001-AZZG9-1H2](https://www.datasheets.com/carling-technologies/l16d1s001-azzg9-1h2) rocker, ON-OFF-ON, 20 A at 12 V DC | 1 | The drive pack selector (A / off / B) | $10-23 for the L16D1S001 family ([Spemco](https://spemco.com/l16d1s001-carling-spdt-l-series-on-off-on-rocker-switch-no-lamps-20a-12v/) $10.25; [Del City](https://www.delcity.net/store/switches/rocker-switches/carling-rocker-switches/l-series-non-illuminated-spdt/) $22.56) | $10-23 | No listing found for the exact suffix (-AZZG9-1H2, the options); Spemco's is the same switch, 20 A 12 V, on-off-on. Its centre-off is the drive kill switch. |
| T-plug (Deans) Y-harness, 1 female to 2 male, 12 AWG | 1 (sold in 2s) | Both ESCs off one drive pack | $8.99 for 2 ([Gator-RC](https://gator-rc.com/t-plug-2-male-to-1-female-connector-adapter?amp=1)) | $8.99 | Plugged, not soldered. Check the gender: the pack's plug to two ESC plugs. |
| INA219 current/voltage board with address jumpers ([Adafruit 904](https://www.adafruit.com/product/904)) | 1 | The Pi watches its own pack and shuts down cleanly | $9.95 (Adafruit) | $9.95 | Buy now (review C6). Its default I2C address, 0x40, is the PCA9685's: solder A0 to move it to 0x41. Its power pin may read VIN on newer boards, which isn't the Vin+ pack terminal. |
| M12 pinhole lens, M12 x 0.5, 3.7 mm, **no IR-cut filter of its own** | 1 (2 to compare) | The pinhole camera in the nose, on his Arducam day-night board | $11.32 ([M12Lenses PT-3722](https://www.m12lenses.com/3-7mm-F2-2-Pinhole-Board-Lens-p/pt-3722.htm)) | $0 | **Not needed** (Zach, 2026-11-08): the Arducam goes on the tail, and the nose gets the IMX219 120-degree module he owns. Kept for the record: the board switches its own IR-cut filter, so skip listings with "IR cut" (the cheap $8 eBay ones have it); confirm the PT-3722 has none before ordering. On the OV5647 a 3.7 mm lens sees about 53° across; shorter is wider. |
| 18 AWG silicone wire, red and black, 5 m | 1 | Each side's motors in parallel | $9.49 (MMOBIEL, Walmart) | $9.49 | |
| 20 AWG silicone wire, red and black | ~1 m | Regulator to the Pi's 5 V pins | about $5-10 (stock patchy) | $5-10 | Thinner wire drops voltage near the Pi's brownout point. |
| 2 mm bullet connectors | 10 pairs | Motors to the ESC leads | $7.95 ([VETCO](https://vetco.net/products/vupn638_10_pair_gold_2mm_rc_bullet_connectors)) | $7.95 | |
| BNO085 IMU (Adafruit 4754) | 1 | The tail knows it's upside down (review C5) | $24.95 ([DigiKey/Mouser](https://www.electronicsdatasheets.com/manufacturers/adafruit/parts/4754)) | $24.95 | C5: yes (Zach, 2026-11-07). The sims' choice. Runs on its own serial wire (UART-RVC), off the PCA's I2C bus (Zach, 2026-11-08): Adafruit lists it as troublesome on I2C. |
| Latching stop button, normally closed, 16 mm | 1 | The kill, in the wire from GPIO 17 to the PCA's OE (review C2) | €24.23 ([EAO 51-256.026, Bürklin](https://www.buerklin.com/en/p/eao/emergency-stop/51-256-026/12G0467/)); A$57.56 ex GST ([TE, RS](https://au.rs-online.com/web/p/emergency-stop-push-buttons/2243486)) | about $25-40 | Carries only a signal, so a cheaper generic latching button will do if it's normally closed; those aren't priced. Plus a 1 kΩ resistor if none is on hand. |
| Small switch for the regulator's EN pin | 1 | Turning the Pi off without pulling a plug (review C3: yes) | not priced | - | From EN to ground, so it carries almost no current and needn't be rated for the Pi's 2.5 A (2026-11-08). Test it on the bench first. |
| ~~M2.5 brass standoff kit~~ | - | ~~Pi and PCA standoffs~~ | - | $0 | **Not needed** (2026-11-07): the Pi and PCA sit in a friction-fit box, as on his last robot. The HAT kit's screws stay in the Pi; the box's rings are bored for their heads (2026-11-08). |
| Heat-set inserts, M3 | 1 kit | The brain box lid's screws into the print | $25 for a 370-piece M2-M6 kit (VXB); M3-only packs not priced | up to $25 | Only if not on hand. The M2.5 size is off the list with the standoffs (2026-11-08). |
| Rubberized hook-and-loop straps, 20 x 200 mm | 5-pack | Pack hold-downs, if the battery door uses straps | $12.55 ([Apex RC via Toytooth](https://toytooth.com/products/apex-rc-products-5-pack-20mm-x-200mm-hd-rubberized-battery-straps-non-slip-3030)) | $12.55 | Only if not on hand. |
| ~~Raspberry Pi Pico 2 (optional)~~ | - | ~~Counting the encoders (review C11)~~ | - | $0 | **Resolved** (Zach, 2026-11-08): his ESP32-WROOM-32 does it. |
| USB WiFi dongle (optional) | 1 | Range | not priced in the US ([£13.90 at The Pi Hut](https://thepihut.com/products/dual-band-usb-wifi-adapter-for-raspberry-pi-5ghz-2-4ghz-mt7612u)) | - | Not needed so far (review C7): the Pi's own WiFi measured 41-188 Mbps in the open and 47-48 inside PLA (2026-11-08), against 6 needed. Retest with the packs on, at the far end of the driving area. If one is needed, pick an MT7612U: its driver has been in Linux since 4.19. |
| Servo BEC, 8 A class (later) | 1 | The tail's servos (review C4) | not priced | - | Buy with the tail's servos. The box keeps a 48 x 30 x 15\* slot for it at the back (the sims' size, a guess). |

**Totals, roughly (2026-11-08):**
- **Buying now, $180-270:** the four more motors, the 18 AWG wire and bullets, the IMU, M3 inserts if needed,
  the regulator, the alarm, the INA219, the Y-harness, the 20 AWG wire and the stop button. The EN switch isn't priced.
- **Waiting, $10-23:** the selector.
- **Straps, $12.55,** only if he doesn't find cheaper or have some.
- **About $200-305 in all,** before shipping. The review's calls (C1-C11) are in `docs/decisions.md`, 2026-11-07 (evening).

Already owned and staying: the four Zeee 2S 5200 packs (one drive, one for the Pi, two to swap in and charge), the two INJORA ESCs, the
PCA9685, the Pi 5 with M.2 HAT+ and Hailo-8L, the ESP32-WROOM-32, the IMX219 120-degree camera (the nose), the Arducam day-night board and its 30 cm ribbon (the tail), an HC-SR04, a T-plug,
Dupont leads and header extensions, Inland TPU 95A filament.
