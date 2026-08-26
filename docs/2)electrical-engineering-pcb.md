# Electrical Engineering & PCB Design

## Power and wiring

| Stage | Component | Notes |
|---|---|---|
| Main pack | 2× 36V 4.4Ah battery packs | Power the four BLDC controllers directly |
| Motor driver | PCA9685 (I2C 0x40) | Commands from ESP32 over I2C (SDA 21/SCL 22); outputs PWM + DIR per motor, 1 kHz |
| Drivetrain | 4× BLDC controller (hall sensor) → 4× hoverboard hub motor | Each controller takes hall feedback from its motor and PWM/DIR from the PCA9685 |
| Logic supply | 36V → 5V 10A buck converter | Feeds Pi, ESP32, sensor rail |

**Hall-sensor vs. sensorless:** hall feedback gives the controller real rotor position instead of inferring it from back-EMF. Matters most at low speed / starting from a stop under load, where sensorless controllers tend to need a kick-start ramp.

**Voltage sensing on 36V:** divider ratio (100kΩ/6.8kΩ here) has to be sized for a 36V pack specifically — reusing values from a smaller pack (e.g. 3S LiPo) will overshoot the ESP32's 3.3V ADC limit.

## PCB — not built yet

Current wiring is point-to-point/perfboard. Custom PCB design was done on a separate project, [`esp32jamm`](https://github.com/nistordarius26h-ship-it/esp32jamm) (ESP32 wireless sniffing platform) — same workflow would carry over here.

### Workflow from `esp32jamm`

1. Schematic + layout in EasyEDA — component library ties directly into JLCPCB's catalog, so footprints/sourcing stay consistent through to the fab file.
2. Layout rules used: power traces wider than signal traces, decoupling caps close to IC power pins, RF antenna footprints at the board edge with ground clearance per datasheet, silkscreen labels on every connector/test point.
3. Gerber export: `Gerber_TopLayer.GTL`, `Gerber_BottomLayer.GBL`, soldermask (`.GTS`/`.GBS`), silkscreen (`.GTO`), outline (`.GKO`), drill files (`.DRL`).
4. Fab: JLCPCB, Gerber `.zip` upload, checked in their viewer before ordering.
5. Assembly: hand-soldered, continuity-checked every power net before first power-up.

### What a future board would consolidate

ESP32, PCA9685, sensor breakouts (ultrasonic, temp/humidity, water, mic, light, MPU6050, QMC5883L, voltage sensor), buzzer/LED — one low-current logic board. The four BLDC controllers and the 36V→5V converter stay as separate high-current modules, kept physically apart from the logic board for noise isolation.

### Reference

- [`nistordarius26h-ship-it/esp32jamm`](https://github.com/nistordarius26h-ship-it/esp32jamm)
