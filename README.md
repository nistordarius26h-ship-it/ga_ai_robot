# GA AI Robot — Globally Accessible Autonomous Robot

Four-wheel differential-drive robot built around an ESP32 real-time controller, Raspberry Pi 4 edge computer, 4G/LTE remote access, WebRTC FPV video, environmental/inertial sensing, and offboard YOLO11 + ByteTrack perception.

> This is a personal engineering project, not a certified product. High-current battery wiring, motor-controller interfaces, safety circuits, and any copied wiring should be verified against the exact hardware before use.

## Architecture

```text
Sensors / safety / drivetrain
          │
          ▼
        ESP32
  real-time control loop
          │ UART 115200
          ▼
    Raspberry Pi 4
  Flask + Socket.IO
  MediaMTX / WHEP
  Cloudflare tunnels
  Telegram notification
          │
          ├──────── Internet / 4G ─────── Browser / phone
          │
          └──────── video stream ─────── Offboard GPU
                                         YOLO11 + ByteTrack
```

## Current hardware

### Compute
- ESP32 WROOM DevKit — motor/sensor controller and local failsafes
- Raspberry Pi 4, 4 GB — dashboard, UART bridge, video, Cloudflare, Telegram
- Offboard GPU workstation for YOLO11 + ByteTrack

### Drivetrain
- 4 × 6.5-inch hoverboard BLDC hub motors
- 4 × 6–60 V / 400 W hall-sensor BLDC controllers
- PCA9685 at I2C address `0x40`, 1 kHz
- Per controller currently used: `P/PWM`, `DIR`, `GND`
- Controllers also expose terminals including `5V`, `0-5V`, `BRAKE`, `STOP` and additional terminals marked `G`, `S`, `V/U`, `P`, `G`. Their exact electrical function/polarity must be verified against the controller documentation before connecting them to the custom PCB.

### Power
- 2 × 36 V, 4.4 Ah battery packs
- 36 V → 5 V / 10 A buck converter for Raspberry Pi / control electronics
- High-current traction distribution remains OFF the sensor/control PCB

An early prototype used an undersized common battery feeder before the four controller branches. Because the common section carried the combined controller current, it overheated and melted. The traction wiring was rebuilt using larger-gauge conductors. The custom PCB is intentionally limited to low-current control/sensor electronics; traction current must remain on properly sized external wiring and protection.

### Sensors
- Ultrasonic distance sensor, forward collision braking
- DHT11 temperature / humidity
- Water / rain sensor
- Battery-voltage divider
- Light sensor, analog + digital
- MPU6050 accelerometer / gyroscope
- QMC5883L magnetometer
- INMP441 I2S microphone (hardware provision retained; firmware can keep it disabled until needed)
- Wide-angle night-vision Raspberry Pi camera

### Current ESP32 connections

| Function | ESP32 |
|---|---:|
| Status LED | GPIO 2 |
| DHT11 | GPIO 4 |
| Light digital | GPIO 13 |
| INMP441 BCLK | GPIO 14 |
| Pi UART RX | GPIO 16 |
| Pi UART TX | GPIO 17 |
| Ultrasonic TRIG | GPIO 18 |
| Ultrasonic ECHO | GPIO 19 |
| I2C SDA | GPIO 21 |
| I2C SCL | GPIO 22 |
| PCA9685 OE | GPIO 23 |
| Buzzer | GPIO 25 |
| Water sensor | GPIO 26 |
| INMP441 WS | GPIO 27 |
| INMP441 SD | GPIO 32 |
| Light analog | GPIO 34 |
| Battery ADC | GPIO 35 |

## Motor-control channel map

| PCA9685 channel | Function |
|---:|---|
| 0 | Front-left P/PWM |
| 1 | Front-left DIR |
| 2 | Rear-left P/PWM |
| 3 | Rear-left DIR |
| 4 | Front-right P/PWM |
| 5 | Front-right DIR |
| 6 | Rear-right P/PWM |
| 7 | Rear-right DIR |
| 8–15 | Reserved / future expansion |

The firmware uses mode-aware differential steering. LOW, MED and HIGH cap both throttle and steering at 25%, 50% and 100%. Full steering within each mode is normalized to full lock, so the inner side reaches zero while the outer side stays within that mode's ceiling (25/0, 50/0 or 100/0 at full command). Steering uses the same slew-rate logic as throttle. At zero throttle, steering commands a turn-in-place within the active mode limit.

## Embedded safety

Current firmware includes:
- 1 s serial-command watchdog
- Raspberry Pi 100 ms command heartbeat
- PCA9685 `OE` hardware output disable
- I2C health checking and recovery
- neutral-before-rearm after a bus fault / boot
- ultrasonic forward braking below the configured threshold
- fast throttle deceleration compared with acceleration
- steering ramping instead of instantaneous steering steps

The robot already has a physical E-stop independent of Linux, Cloudflare and the browser; PCB v1 keeps that E-stop external and adds a separate physical ARM switch input.

## Raspberry Pi control stack

- Python 3
- Flask + Flask-SocketIO
- `/dev/serial0` at 115200 baud
- MediaMTX on port 8889
- WebRTC / WHEP camera path `/cam/whep`
- Cloudflare Quick Tunnel for dashboard port 5000
- Cloudflare Quick Tunnel for MediaMTX port 8889
- Telegram notification of the dynamically assigned URLs
- systemd boot service

The boot launcher waits for real Internet connectivity before creating the Cloudflare tunnels. This is important with the LTE dongle because cellular registration can take longer than Wi-Fi and `network-online.target` alone does not guarantee usable Internet access.

## 4G / WebRTC note

Cloudflare handles HTTP/WHEP signaling, but WebRTC media still depends on ICE connectivity. Cellular carriers commonly place clients behind CGNAT. STUN-only WebRTC can therefore load the dashboard/signaling successfully while failing to establish the media path.

For reliable 4G video, configure a TURN/TURNS relay in `raspberry-pi/mediamtx.yml` on the deployed Pi. Do not commit real TURN credentials.

## Planned custom control/sensor PCB

PCB v1 is one simple low-voltage **carrier/backplane** board. It keeps the existing working modules removable and replaces loose jumper wiring with robust connectors. Planned PCB features:

- ESP32 DevKit socket/header
- PCA9685 module/header
- direct PCA `P`/`DIR` motor-controller signals through 100-ohm series resistors
- four controller connectors/pads for `P`, `DIR`, `GND`, plus reserved `S/BRAKE/STOP` positions
- Raspberry Pi UART connector
- physical ARM switch on GPIO33
- existing physical E-stop remains separate from the PCB
- simple 100 kΩ / 6.8 kΩ battery-voltage divider to GPIO35
- one active ultrasonic sensor on GPIO18/GPIO19 with a 10 kΩ / 20 kΩ ECHO divider
- optional physical connectors for US2–US8, with TRIG/ECHO routed only to an unconnected expansion header
- DHT, water, light, MPU6050, INMP441 and remote QMC5883L connectors
- PCA CH8–CH15 expansion header/pads
- keyed/locking connectors or through-hole solder pads with mechanical strain relief for remote sensor cables

The high-current 36 V battery and motor-controller power paths remain external.

## Navigation expansion

For future localization / SLAM, the preferred progression is:
1. Use each controller's `S` speed-pulse output for wheel RPM/odometry.
2. Expand obstacle coverage to as many as eight sequentially-polled ultrasonic sensors.
3. Fuse wheel odometry + IMU, and optionally GNSS outdoors.
4. Add more autonomous behaviors only after the low-level speed/odometry data is calibrated.

## AI tracking

The object-detection/tracking implementation is maintained separately in:

`ai_multiobject_python_tracker`

The robot integration uses YOLO11 + ByteTrack for detection/tracking and person-following experiments. Heavy inference currently runs offboard.

## Repository structure

```text
esp32-firmware/   ESP32 firmware
raspberry-pi/     dashboard, serial bridge, MediaMTX, tunnels, systemd
docs/             subsystem documentation
media/            CAD exports, renders, photos and clips
ai-tracking.md    link/summary for the external tracking project
```

## License

See [`LICENSE`](./LICENSE). The current repository license is portfolio/viewing-only; it is **not MIT**.

## Author

Nistor Darius — embedded systems, robotics, AI, mechanical/electrical integration
