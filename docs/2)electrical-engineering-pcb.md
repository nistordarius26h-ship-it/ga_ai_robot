# Electrical Engineering & PCB Design

## Power & wiring for this robot

| Stage | Component | Notes |
|---|---|---|
| Main pack | 2× 36V 4.4Ah battery packs | Power the four hall-sensor BLDC motor controllers directly |
| Drivetrain | 4× DC 6-60V 400W BLDC controller (hall sensor) → 4× 6.5" hoverboard hub motor | Each controller takes hall-sensor feedback from its motor for accurate commutation, and a PWM throttle / direction input from the ESP32 |
| Logic supply | 36V → 5V 10A buck converter | Regulates the pack voltage down for the Raspberry Pi, ESP32, and sensor rail |

**Why hall-sensor BLDC controllers over sensorless ESCs:** hall sensors give the controller real, immediate rotor-position feedback instead of inferring it from back-EMF, which matters most exactly where a robot needs it — starting from a dead stop under load and running at low speed on uneven terrain. Sensorless controllers tend to stumble or need a "kick-start" ramp in that regime; hall-sensor controllers don't.

**Voltage sensing on a 36V pack:** the battery voltage sensor needs a resistor divider (or dedicated sensor board) sized specifically for a 36V rail — bringing worst-case pack voltage safely under the ESP32's 3.3V ADC limit. This is a different divider ratio than you'd use on a smaller pack (e.g. a 3S LiPo), so it's worth double-checking/re-deriving the resistor values for this specific pack voltage rather than reusing values from a different project.

**General decoupling practice:** every sensor module's supply pins should get a local decoupling capacitor near the module itself (not just at the regulator output), to suppress switching noise from the BLDC controllers coupling into the sensitive sensor rails — this matters more here than on a smaller build, since four independent motor controllers switching simultaneously is a noisier electrical environment than a single H-bridge.

## PCB design — not yet done for this robot

There's no custom PCB in this project yet — the wiring here is point-to-point/breadboard-and-perfboard style. Custom PCB design and fabrication is a skill I learned and applied on a separate project, **[`esp32jamm`](https://github.com/nistordarius26h-ship-it/esp32jamm)** (an ESP32-based wireless sniffing platform), and that's the workflow I'd bring over here if/when this robot gets a dedicated board.

### The workflow I learned on `esp32jamm`

1. **Schematic capture & layout — EasyEDA.** EasyEDA's browser-based editor for schematic entry and PCB layout. A good entry point for custom boards because its component library ties directly into JLCPCB's parts catalog, so footprints and sourcing stay consistent from schematic straight through to the fab file.
2. **Design considerations I picked up:**
   - Power traces routed wider than signal traces to handle current without excessive voltage drop/heating.
   - Decoupling capacitors placed as close as possible to each IC's power pins.
   - External antenna connector footprints placed at the board edge, with ground pour clearance around them per the module's RF datasheet section.
   - Silkscreen labels on every connector and test point — pays off hugely during assembly and debugging.
3. **Gerber export.** EasyEDA exports the standard Gerber/Excellon set: `Gerber_TopLayer.GTL`, `Gerber_BottomLayer.GBL`, solder mask layers (`.GTS`/`.GBS`), silkscreen (`.GTO`), board outline (`.GKO`), and drill files (`.DRL`).
4. **Fabrication — JLCPCB.** Uploaded the exported Gerber `.zip` directly to JLCPCB for manufacturing, using their online Gerber viewer as a final visual sanity check before ordering (catches silkscreen collisions, missing outline layers, etc. before paying for a board).
5. **Assembly.** Hand-soldered the components onto the fabricated board, checking continuity on every power net with a multimeter before first power-up — a five-minute check that's far cheaper than a shorted board.

### What a future PCB for this robot would consolidate

If this robot gets a dedicated board, the obvious candidates to bring onto one PCB (rather than loose modules and jumper wires) are: the ESP32 itself, the sensor breakouts (ultrasonic, temp/humidity, water, mic, light, MPU6500, HMC5883L, voltage sensor), and the buzzer/LED — leaving the four BLDC controllers and the 36V→5V converter as separate high-current modules connected by wire, since keeping high-current switching hardware physically separate from the low-current sensor/logic board is generally good practice for noise isolation.

### Reference

- PCB design/fabrication example: [`nistordarius26h-ship-it/esp32jamm`](https://github.com/nistordarius26h-ship-it/esp32jamm)
