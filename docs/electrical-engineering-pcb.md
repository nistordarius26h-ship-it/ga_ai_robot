# Electrical Engineering & PCB Design

This covers the robot's power distribution, motor driving, and general wiring approach, plus the custom PCB workflow used across my projects (including this one).

## Power architecture

| Stage | Component | Notes |
|---|---|---|
| Main pack | 3S LiPo, 11.1V nominal, 5000 mAh | Powers the motors and, through regulation, everything else |
| Motor driver | BTS7960 43A H-bridge module | Drives the JGB37-500 12V gear motor directly from LiPo voltage |
| Logic supply | 2× LM2596 3A buck regulator | One rail regulated to 5V for the Raspberry Pi / sensors, ESP32 runs from its own onboard 3.3V regulator fed from a 5V rail |
| Solar input | Solar panel(s) | Trickle-charges/extends the LiPo for longer field deployments |

**Why BTS7960 over a smaller L298N-class driver:** the JGB37-500 draws well beyond what an L298N (2A) can sustain under load on uneven terrain. The BTS7960 is rated to 43A and uses MOSFETs rather than a linear bipolar bridge, so it runs cooler and wastes less power as heat — important on a battery-powered platform.

**Why two separate LM2596 regulators instead of one:** splitting the Raspberry Pi's supply from the sensor/peripheral supply keeps voltage sag from motor-driver switching noise off the Pi's rail, which is more sensitive to brownouts (an undervoltage Pi can silently corrupt the SD card).

## ESP32 wiring

The ESP32 sits between the sensors/motors and the Raspberry Pi. Full pin assignments are documented in [`esp32-firmware.md`](./esp32-firmware.md#pin-map); the electrical highlights:

- **Motor driver interface:** `ENA`/`ENB` (PWM, LEDC-driven) plus `IN1–IN4` direction pins straight into the BTS7960's logic inputs. The BTS7960's own high-current side is fed directly from the LiPo, isolated from the ESP32's 3.3V logic domain except through the driver's opto-isolated (or resistor-buffered, depending on the module revision) inputs.
- **Analog sensing:** battery voltage is read through a resistor divider into an ADC1 pin (GPIO35) — never feed LiPo voltage directly into an ESP32 ADC pin, the divider ratio must bring worst-case pack voltage (~12.6V full charge) safely under 3.3V.
- **Ultrasonic sensor:** standard TRIG/ECHO HC-SR04-style wiring. Note the ECHO line is a 5V logic signal on most HC-SR04 modules — if using a 5V-tolerant module without a divider, confirm your specific sensor variant is 3.3V-safe on ECHO or add a divider/level shifter to protect the ESP32 pin.
- **DHT11, water sensor, microphone, buzzer:** all straightforward digital/analog GPIO, no special conditioning beyond decoupling capacitors near each module's supply pins.

**General decoupling practice:** every sensor module supply pin gets a local decoupling capacitor near the module (not just at the regulator output) — this is standard practice to suppress switching noise from the motor driver from coupling into the sensor rails.

## Custom PCB design workflow

The custom PCB experience for this project's family of builds (this robot and the standalone [`esp32jamm`](https://github.com/nistordarius26h-ship-it/esp32jamm) wireless-sniffing platform) follows the same pipeline:

1. **Schematic capture & layout — EasyEDA.** EasyEDA's browser-based editor was used for schematic entry and PCB layout. It's a good entry point for custom boards because its component library is directly tied to JLCPCB's parts catalog, so part footprints and sourcing stay consistent from schematic to fabrication.
2. **Design considerations:**
   - Power traces (motor driver / battery routing) sized wider than signal traces to handle higher current without excessive voltage drop or heating.
   - Decoupling capacitors placed as close as possible to each IC's power pins.
   - External antenna connector footprints (on the RF-focused board) placed at the board edge with clear ground pour clearance per the module datasheet's RF section.
   - Silkscreen labels added for every connector and test point — this pays off enormously during assembly and debugging.
3. **Gerber export.** EasyEDA exports the standard Gerber/Excellon set: `Gerber_TopLayer.GTL`, `Gerber_BottomLayer.GBL`, solder mask layers (`.GTS`/`.GBS`), silkscreen (`.GTO`), board outline (`.GKO`), and drill files (`.DRL` for plated through-holes and vias).
4. **Fabrication — JLCPCB.** The exported Gerber .zip is uploaded directly to JLCPCB for manufacturing. JLCPCB's online Gerber viewer is also useful as a final visual sanity check before ordering (catches silkscreen collisions, missing outline layers, etc. before you pay for a board).
5. **Assembly.** Components hand-soldered onto the fabricated board; a multimeter continuity check on every power net before first power-up is non-negotiable — it catches shorts that are far cheaper to fix before power is ever applied.

### Suggested `pcb/` folder structure for this repo

If/when a dedicated board is designed for this robot (vs. the current point-to-point wiring), keep the same structure used in `esp32jamm`:

```
pcb/
  Gerber_TopLayer.GTL
  Gerber_BottomLayer.GBL
  Gerber_TopSolderMaskLayer.GTS
  Gerber_BottomSolderMaskLayer.GBS
  Gerber_TopSilkscreenLayer.GTO
  Gerber_BoardOutlineLayer.GKO
  Gerber_DocumentLayer.GDL
  Drill_PTH_Through.DRL
  Drill_PTH_Through_Via.DRL
  *.png          # rendered top/bottom board previews for the README
```

## Reference

- Custom PCB example (same design workflow): [`nistordarius26h-ship-it/esp32jamm`](https://github.com/nistordarius26h-ship-it/esp32jamm)
