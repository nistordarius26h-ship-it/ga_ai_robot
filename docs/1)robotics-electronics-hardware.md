# Robotics & Electronics: Sensors, Modules and PCB v1

## Compute & control

| Component | Role |
|---|---|
| ESP32 WROOM DevKit | Real-time motor control, local safety, sensors and UART link to Raspberry Pi |
| Raspberry Pi 4 (4 GB) | Dashboard, MediaMTX, Cloudflare tunnels, Telegram and higher-level software |
| Offboard GPU workstation | YOLO11 + ByteTrack detection/tracking |

## Drivetrain

- 4 × 6.5-inch hoverboard BLDC hub motors
- 4 × 6–60 V / 400 W Hall-sensor BLDC controllers
- PCA9685 module, I2C address `0x40`, 1 kHz PWM

Current tested controller wiring is kept simple:

```text
P/PWM <- PCA9685 channel through 100-220 ohm series resistor
DIR   <- PCA9685 channel through 100-220 ohm series resistor
GND   <-> common logic/control ground
```

The controller also exposes `5V`, `0-5V`, `BRAKE`, `STOP`, `S` speed-pulse output and motor Hall connections. PCB v1 leaves `BRAKE` and `S` available as pads/connector pins for future measurement and use. The `0-5V` analog speed input is not used because the project already controls speed through `P` PWM.

## Power

- 2 × 36 V, 4.4 Ah battery packs
- external 36 V → 5 V / 10 A buck converter for Pi/logic power

An early prototype used a common feeder that was too thin for the combined current of four controllers. It overheated and melted. The traction harness was rebuilt with heavier wiring. Therefore the custom PCB is **not** a traction-power board.

Keep off the PCB:

- 36 V main feeder;
- controller power branches;
- motor phase wiring;
- high-current battery distribution.

The PCB handles low-current control/sensor wiring only.

## Grounding

ESP32 GND, PCA GND, Pi UART GND, sensor grounds, motor-controller **signal** grounds and buck-converter output ground share the same electrical reference. The metal chassis does not need to be used as ground.

## Current sensor set

| Sensor | Interface | Connection |
|---|---|---|
| Ultrasonic US1 | TRIG/ECHO | GPIO18 / GPIO19; ECHO through 10k/20k divider |
| DHT11 | digital | GPIO4 |
| Water/rain | digital | GPIO26 |
| Battery voltage | ADC | GPIO35 via 100 kΩ / 6.8 kΩ divider |
| INMP441 microphone | I2S | WS27 / SD32 / BCLK14; currently optional/disabled in firmware |
| Light sensor | analog + digital | GPIO34 / GPIO13 |
| MPU6050 | I2C | address `0x68` |
| QMC5883L | I2C | address `0x0D`, mounted remotely |
| Camera | Raspberry Pi camera interface | wide-angle/night-vision camera |

## QMC5883L placement

The compass should be mounted remotely because hub-motor magnets, high-current battery/phase wiring, motor controllers, the buck converter and nearby steel can distort heading. The main PCB therefore provides a 4-wire remote connector (`3V3/GND/SDA/SCL`) instead of placing the QMC directly beside the motor-control wiring.

## Speed-pulse expansion

Each controller has an `S` speed-pulse output. PCB v1 reserves `S_FL`, `S_FR`, `S_RL`, `S_RR` pads/connector pins, but they are not tied directly to ESP32 GPIO until their output voltage/waveform is measured.

## Ultrasonic expansion

US1 is active now. The PCB may physically provide connectors for US2-US8, but only their power rails are shared. Their TRIG/ECHO signals terminate on an unconnected expansion header/pads. They are **not** all tied to GPIO18/GPIO19.

This keeps PCB v1 simple and avoids ultrasonic cross-talk from firing multiple sensors simultaneously.

## Actuation / feedback

- active buzzer module signal on GPIO25
- physical E-stop remains external to the PCB
- physical ARM switch on GPIO33
- GPIO2 intentionally unused on PCB v1

## Single-PCB philosophy

The one custom PCB is a **carrier/backplane** for removable modules and robust connectors:

- ESP32 DevKit socket
- PCA9685 module
- Pi UART connector
- sensor connectors
- battery-voltage divider
- ARM switch input
- four motor-controller P/DIR/GND interfaces
- PCA CH8–CH15 expansion
- US2–US8 expansion pads/header
- mechanical strain-relief features or locking connectors for remote sensor cable
