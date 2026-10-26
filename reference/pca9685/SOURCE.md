# PCA9685 16-channel servo driver: source

Copied 2026-10-04 from Zach's download
`Downloads/pca9685-16-channel-12-bit-servo-driver-generic-adafruit-1.snapshot.3/`.

- `PCA9685 16-Channel Servo Driver - Adafruit.FCStd`: the FreeCAD file Zach pointed at.
- `PCA9685 16-Channel Servo Driver - Adafruit.step`: the same board as STEP; 62.23 × 25.65 × 12.36 with
  headers (board at Z 0, pins to -2.9, headers to 9.46). The chassis concept uses this one.
- `PCA9685 16-Channel Servo Driver - Generic.step`: the generic clone, 70.23 long with its side pins.
  HARDWARE.md says the robot's board is a generic Adafruit-layout clone; the two share the outline.

**Not tracked (2026-10-26):** the download's licence wasn't recorded (the `.snapshot.3` folder name looks like a
GrabCAD download), so the three model files are kept locally and gitignored, not redistributed. The chassis
generators load the Adafruit STEP from here, so a fresh clone needs a PCA9685 model with the same outline saved
under that name.
