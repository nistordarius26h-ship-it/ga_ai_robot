# GA AI Robot update manifest — v3

This package is the latest replacement set based on the public GitHub project plus the newer local ESP32/Pi code supplied in chat and the final PCB-v1 decisions.

## Main software changes

- LTE tunnel discovery waits up to 180 seconds and uses the newer Pi control UI.
- Pi sends `CMD:<throttle>,<steering>,<speed_limit>` at a 100 ms heartbeat.
- LOW/MED/HIGH scale both throttle and steering to 25/50/100.
- Firmware normalizes full steering against the active speed limit so full lock still reaches inner=0 inside each mode.
- Steering uses the **same ramp function and same ramp rates as throttle**.
- Physical ARM switch added on GPIO33: 10 kΩ pull-up to 3.3 V, switch to GND.
- PCA OE on GPIO23 stays disabled unless communication/I2C/ARM conditions are safe.
- Battery ADC uses the simple 100 kΩ / 6.8 kΩ divider and software averaging/calibration.
- GPIO2 is intentionally unused on PCB v1.

## Final PCB-v1 decisions reflected in docs

- One simple carrier/backplane PCB using existing modules.
- No traction current through PCB.
- No ACS758/current sensor.
- No MOSFET accessory outputs.
- No SN74AHCT125 or ULN2003A.
- No extra clamp/Schottky network.
- No LiDAR or ToF.
- No ultrasonic mux/decoder on v1.
- US1 active on GPIO18/GPIO19; US2-US8 only reserved as future expansion.
- PCA P/DIR outputs go through 100-ohm series resistors.
- Existing physical E-stop stays external.
- QMC5883L is remote from motors/high-current wiring.
- Remote cables should use locking through-hole connectors or plated through-hole solder pads with mechanical strain relief.

## Modified files

- `.gitignore`
- `README.md`
- `esp32-firmware/gaaicode.ino`
- `raspberry-pi/robot_app.py`
- `raspberry-pi/launch_robot.sh`
- `raspberry-pi/mediamtx.yml`
- `raspberry-pi/robot.service`
- `docs/README.md`
- `docs/1)robotics-electronics-hardware.md`
- `docs/2)electrical-engineering-pcb.md`
- `docs/3)esp32-firmware.md`
- `docs/4)raspberry-pi-setup.md`
- `docs/5)cloudflare-telegram-remote-access.md`
- `docs/8)custom-pcb-expansion.md`

## New

- `raspberry-pi/robot.env.example`

## Verified but intentionally not changed in this update set

- `LICENSE`
- `ai-tracking.md`
- `docs/6)ai-tracking-computer-vision.md`
- `docs/7)3d-modeling-rendering.md`
