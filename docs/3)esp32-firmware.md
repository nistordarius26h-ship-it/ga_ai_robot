# ESP32 Firmware (C++)

`esp32-firmware/32controlcode.ino`

Real-time motor control and safety layer between the sensors/motors and the Pi. Runs independently of the network link above it — if 4G drops or the Pi hangs, obstacle braking, water flagging, and telemetry keep running.

## Toolchain

- Arduino IDE or PlatformIO
- Board: ESP32 by Espressif Systems
- Libraries: `DHT` (Adafruit), `Wire` (built-in), `Adafruit_PWMServoDriver` (PCA9685), `driver/i2s.h` (built-in, INMP441 — currently compiled out)

## Loop summary

1. Every 60 ms: ping ultrasonic, set/clear obstacle-brake flag below 10 cm
2. Every loop: read `CMD:` strings off UART, drive all 4 motors via PCA9685 with ramped tank steering
3. Every 2 s: sample DHT11 into cache
4. Every 20 ms (20 Hz): read voltage, light, water, heading, pitch/roll, mic, send telemetry line
5. 5 s command failsafe — zero throttle/steering if nothing received in that window
6. Boot: full I2C scan + explicit PCA9685 presence check to `Serial`

## Motor control — PCA9685

ESP32 doesn't drive motors directly. It talks to a PCA9685 (I2C 0x40, 1 kHz), which drives the four BLDC controllers.

| Wheel | PWM channel | DIR channel |
|---|---|---|
| Front left | 0 | 1 |
| Rear left | 2 | 3 |
| Front right | 4 | 5 |
| Rear right | 6 | 7 |

- Speed mapped from 1–100% to a 12-bit PCA9685 value (200–4095) so motors always get enough duty cycle to start.
- Direction set by driving the DIR channel fully on/off (`4095`/`0` via `setPWM`), not a separate GPIO.
- Left-side motors (FL, RL) are physically mirrored — commanded speed sign is inverted in software for those two, confirmed by per-motor DIR testing.
- Tank steering: `left = throttle + steering`, `right = throttle − steering`. 15% deadzone on both inputs. Soft ramp (`RAMP_RATE_PERCENT_PER_SEC = 220`) instead of snapping to target speed.
- While driving, steering can only slow the inner wheels toward zero, not reverse them. Full pivot turns only at zero throttle.
- Ultrasonic trigger forces throttle to 0 (brake only, no reverse).

## Sensors

| Sensor | Interface | GPIO / Address |
|---|---|---|
| Ultrasonic | Digital TRIG/ECHO | TRIG 18, ECHO 19 |
| DHT11 | Single-wire digital | 4 |
| Water/rain | Digital input | 26 |
| Battery voltage | Analog (ADC1), 100kΩ/6.8kΩ divider | 35 |
| INMP441 mic | I2S digital, disabled (`MIC_ENABLED 0`) | WS 27, SD 32, SCK 14, I2S_NUM_0 |
| Light | Analog + digital | Analog 34, digital 13 |
| MPU6050 (accel/gyro) | I2C | 0x68 |
| QMC5883L (magnetometer) | I2C, raw register writes | 0x0D |
| PCA9685 (PWM driver) | I2C | 0x40 |
| Buzzer (3-pin transistor) | Digital output | 25 |
| Status LED | Digital output | 2 |
| I2C bus (IMU, compass, PCA9685) | — | SDA 21, SCL 22 |
| UART2 to Pi | Serial | RX 16, TX 17, 115200 baud |

## UART protocol

**Pi → ESP32:**
```
CMD:<throttle>,<steering>\n
```
Parsed into `current_throttle`/`current_steering`, timestamps the failsafe, fed to `driveTankSteering()` every loop.

**ESP32 → Pi (~20 Hz):**
```
TELEMETRY:<battery_v>,<mic_db>,<temp_c>,<humidity_pct>,<distance_cm>,<water_0_or_1>,<light_analog>,<light_digital>,<heading_deg>,<pitch_deg>,<roll_deg>\n
```
Same field order regardless of rate. Any field change requires updating the parser in `robot_app.py` to match.

## Notes

- Obstacle braking: non-blocking, 60 ms interval, 6 ms `pulseIn` timeout.
- Battery voltage: `(rawadc/4095.0) * 3.3 * ((100.0+6.8)/6.8)` — actual 100kΩ/6.8kΩ divider, ~15.7× multiplier.
- Heading and pitch/roll: low-pass filtered (`alpha = 0.15`) to smooth 20 Hz telemetry jitter.
- Mic: INMP441 I2S driver is written but disabled at compile time while isolating an earlier crash. Telemetry sends a flat 30.0 dB placeholder in the meantime.
- Buzzer: digital HIGH/LOW to a 3-pin transistor module, not PWM/tone.

## Extending

- Re-enable mic: set `MIC_ENABLED 1` once the earlier crash is confirmed fixed.
- New telemetry fields: read sensor, append to the `TELEMETRY:` print block, update the parser in `robot_app.py` to match.
- Keep new blocking calls time-bounded — the loop needs to hold ~20 Hz telemetry and not overflow the UART RX buffer.
