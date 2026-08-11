# ESP32 Firmware (C++)

`esp32-firmware/32controlcode.ino`

The ESP32 is the robot's **real-time safety and motor-control layer**. It runs a tight, deterministic loop that handles motor driving, obstacle braking, water-intrusion cutoff, and telemetry — independent of whatever is happening on the Raspberry Pi or the network link above it. This separation matters: if the 4G link drops or the Pi hangs, the ESP32 still protects the hardware (braking on obstacles, cutting motors on water contact).

## Toolchain

- Arduino IDE or PlatformIO
- Board package: **ESP32 by Espressif Systems**
- Library dependency: `DHT sensor library` (Adafruit) for the DHT11 temperature/humidity sensor

## Responsibilities

1. Drive the two DC motors via PWM (LEDC peripheral) based on commands received over UART from the Pi
2. Continuously poll the ultrasonic sensor and force an emergency stop below a distance threshold
3. Continuously poll the water sensor and cut motors immediately on detection
4. Sample the electret microphone to estimate a rough dB level (used for clap/sound-trigger features)
5. Read battery voltage, temperature, and humidity on a 1-second interval
6. Push a compact CSV telemetry line back to the Pi over UART for the web dashboard

## Pin map

| Function | GPIO | Notes |
|---|---|---|
| Status LED | 2 | |
| Microphone (analog) | 32 | ADC1, envelope-sampled over a 25 ms window |
| DHT11 (temp/humidity) | 4 | |
| Buzzer | 25 | LEDC tone output, 1500 Hz |
| Water sensor (digital) | 26 | Active HIGH = water detected |
| Battery voltage sense | 35 | ADC1, resistor-divider scaled input |
| Ultrasonic TRIG | 18 | |
| Ultrasonic ECHO | 19 | |
| Motor A enable (PWM) | 14 | LEDC channel 0 |
| Motor A IN1 / IN2 | 12 / 13 | Direction pins, left side |
| Motor B IN3 / IN4 | 22 / 23 | Direction pins, right side |
| Motor B enable (PWM) | 27 | LEDC channel 1 |
| UART2 RX / TX (to Pi) | 16 / 17 | 115200 baud, `Serial2` |

PWM is configured at **1 kHz, 8-bit resolution** (0–255 duty range) via `ledcAttachChannel`.

## UART protocol (Pi ↔ ESP32)

A single UART2 link (115200 baud) carries commands down and telemetry up. Keeping this a simple line-based text protocol (rather than a binary one) made it trivial to debug with a serial monitor while wiring things up.

**Pi → ESP32 (motor command):**
```
CMD:<angle>,<speed>\n
```
- `angle` — direction in degrees (joystick angle from the web UI)
- `speed` — 0–100, mapped internally to a 0–255 PWM value

The firmware buckets the angle into four zones (forward, back, left, right) rather than doing full vector mixing — simple, predictable, and easy to tune per-motor.

**ESP32 → Pi (telemetry, once per second):**
```
TELEMETRY:<battery_v>,<mic_db>,<temp_c>,<humidity_pct>,<distance_cm>,<water_0_or_1>\n
```
The Pi's Flask app parses this line and re-emits it to the browser dashboard over Socket.IO in real time.

## Safety behavior

- **Obstacle braking:** the ultrasonic sensor is polled every loop iteration (not on a timer) so braking is as close to instant as the 30 ms `pulseIn` timeout allows. Below 10 cm, motors are forced to stop and further drive commands are ignored (`brakeactive` flag) until the obstacle clears.
- **Water cutoff:** identical pattern — any HIGH reading on the water sensor immediately stops both motors and blocks new commands until the sensor clears.
- Both safety conditions take priority over incoming UART commands, so a stuck or malicious command stream can't override them.

## Motor trim

Because the two DC gear-motors don't draw identically at the same PWM duty cycle, each side has an independent trim multiplier (`lefttrim`, `righttrim`) applied in `scalepwm()`, with a `minpwm` floor (60) to avoid stall-without-movement at low duty cycles. These values were tuned empirically by driving the robot straight and adjusting until it stopped curving to one side.

## Extending the firmware

- Add new sensors by declaring a pin, reading it in `loop()`, and appending a field to the `TELEMETRY:` line (update the Python parser in `robot_app.py` to match).
- New motor behaviors (e.g. true vector/differential mixing) belong in `drivevector()`.
- Keep any new blocking logic (like `pulseIn`) time-bounded — the loop must stay fast enough that the UART RX buffer doesn't overflow.
