# ESP32 Firmware (C++)

`esp32-firmware/32controlcode.ino`

The ESP32 is the robot's **real-time sensor and safety layer**, sitting between the sensors and the Raspberry Pi. It runs a tight, deterministic loop independent of whatever is happening on the network link above it — if the 4G connection drops or the Pi hangs, the ESP32 keeps working (braking on obstacles, flagging water contact, streaming telemetry).

## Toolchain

- Arduino IDE or PlatformIO
- Board package: **ESP32 by Espressif Systems**
- Library dependencies: `DHT` (Adafruit, for temp/humidity), `Wire` (built-in, for the I²C IMU and magnetometer)

## What this firmware does

1. Continuously polls the ultrasonic sensor and raises an obstacle-braking flag below a distance threshold
2. Continuously reads the water sensor and flags water contact
3. Samples the microphone to estimate a rough dB level (peak-to-peak envelope over a 25 ms window)
4. On a 1-second interval: reads temperature/humidity, battery voltage, light level (analog + digital), compass heading, and pitch/roll from the IMU
5. Streams a single CSV telemetry line to the Raspberry Pi over UART every second
6. Receives and parses throttle/steering commands from the Pi over the same UART link

## Sensors wired to the ESP32

| Sensor | Interface | GPIO / Address |
|---|---|---|
| Ultrasonic distance sensor | Digital TRIG/ECHO | TRIG `18`, ECHO `19` |
| Temperature & humidity (DHT11) | Single-wire digital | `4` |
| Water/rain sensor | Digital input | `26` |
| Battery voltage sensor | Analog (ADC1) | `35` |
| Microphone sensor | Analog (ADC1), envelope-sampled | `32` |
| Light sensor (analog + digital output) | Analog (ADC) + digital | Analog `34`, digital `13` |
| 6-axis IMU (accelerometer) | I²C | Address `0x68` — MPU6050-register-compatible (same register map as the MPU6500/MPU9250 family) |
| Magnetometer/compass | I²C | Address `0x0D` — **QMC5883L**, driven with raw register writes in this firmware |
| Beeper (buzzer) | PWM (LEDC tone) | `25`, 1500 Hz |
| Status LED | Digital output | `2` |
| I²C bus (shared by the IMU and compass) | — | SDA `21`, SCL `22` |
| UART2 to Raspberry Pi | Serial | RX `16`, TX `17`, 115200 baud |

## Motor / drivetrain control — not yet implemented

This firmware does **not** currently drive any motor controller. The UART command parser (`parsecommand()`) receives `CMD:<throttle>,<steering>` from the Pi and stores the values in `current_throttle` / `current_steering`, but nothing in the current code writes those values out to any GPIO — no motor pins, PWM channels, or direction lines are defined. This is intentional groundwork: the throttle/steering values are already being received and parsed, ready to be wired into whichever motor controller you settle on, without needing to touch the UART protocol or the Pi-side code again once you do.

## UART protocol (Pi ↔ ESP32)

**Pi → ESP32 (command):**
```
CMD:<throttle>,<steering>\n
```
Parsed and stored in `current_throttle` / `current_steering` — currently unused beyond that until motor control logic is added.

**ESP32 → Pi (telemetry, once per second):**
```
TELEMETRY:<battery_v>,<mic_db>,<temp_c>,<humidity_pct>,<distance_cm>,<water_0_or_1>,<light_analog>,<light_digital>,<heading_deg>,<pitch_deg>,<roll_deg>\n
```
The Pi's Flask app parses this line and re-emits it to the browser dashboard over Socket.IO in real time. Any future firmware changes that add or reorder fields need the parser in `robot_app.py` updated to match, or the line will silently misparse.

## Sensor details worth knowing

- **Obstacle braking:** the ultrasonic sensor is polled every loop iteration (not on a timer), so the brake flag responds as fast as the 30 ms `pulseIn` timeout allows. Below 10 cm, `brakeactive` is set; it clears once the reading rises back above that threshold.
- **Battery voltage:** `(rawadc / 4095.0) * 3.3 * 5.0` — this assumes a voltage-sensor module/divider with a 5:1 scaling ratio ahead of the ADC pin. If you swap in a different voltage sensor, this multiplier needs to be recalculated to match its actual divider ratio.
- **Compass heading:** computed from raw QMC5883L X/Y magnetometer axes via `atan2`, normalized to 0–360°. This is an uncompensated heading (no tilt compensation from the accelerometer), so it's most accurate when the robot is roughly level.
- **Pitch/roll:** computed from the accelerometer axes alone (no gyroscope fusion), which is simple and drift-free at rest but will read incorrectly during active acceleration (e.g. hard braking or a bump) since it can't distinguish gravity from linear acceleration. Fine for general tilt/orientation monitoring; not a substitute for a real complementary/Kalman filter if precise dynamic orientation is ever needed.
- **Microphone sampling:** blocks for a fixed 25 ms window each loop iteration to capture a peak-to-peak envelope, converted to an approximate dB value.

## Extending the firmware

- **Adding motor control:** once a controller is chosen, this is where PWM/direction (or serial/CAN, depending on the controller type) pins get defined and driven from `current_throttle`/`current_steering` inside `loop()`.
- **Adding more telemetry fields:** read the sensor, append a value to the `TELEMETRY:` print block, and update the corresponding parser in `robot_app.py`.
- Keep any new blocking logic (like `pulseIn` or the mic sampling window) time-bounded — the loop needs to stay fast enough that the UART RX buffer doesn't overflow and telemetry stays close to its 1-second cadence.
