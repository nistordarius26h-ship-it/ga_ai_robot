# Robotics & Electronics: Sensors, Modules, and Boards

The full hardware bill of materials for this build — what each part does, why it's there, and how it connects into the system.

## Compute & control

| Component | Role |
|---|---|
| **ESP32 WROOM DevKit** | Real-time motor control and sensor safety layer. Chosen for dual-core performance, PWM (LEDC) peripherals, plenty of GPIO/ADC pins, and a native Arduino/C++ toolchain — see [`esp32-firmware.md`](./esp32-firmware.md). |
| **Raspberry Pi 4 (4GB RAM)** | Edge compute: runs the Flask control server, MediaMTX video server, Cloudflare tunnels, and Telegram integration. Chosen over the ESP32 for this role because it needs real Linux (for MediaMTX, systemd, and `cloudflared`) and enough RAM/CPU headroom for video handling — see [`raspberry-pi-setup.md`](./raspberry-pi-setup.md). |

## Drivetrain

| Component | Role |
|---|---|
| **4× 6.5" hoverboard hub motors** | Drive motors — one per wheel. Hub motors mean no separate gearbox/chain, which simplifies the mechanical build and keeps unsprung weight predictable, at the cost of the motor itself sitting directly in the wheel (more exposed to terrain/impacts than a chassis-mounted motor would be). |
| **4× DC 6-60V 400W BLDC brushless motor controller (hall-sensor based)** | One controller per hub motor. Hall-sensor feedback gives the controller true commutation timing (vs. sensorless BLDC control), which means better low-speed torque and smoother starts — important for a loaded robot starting from a stop on uneven ground, versus the jerkier startup you get from sensorless ESCs. |

> **Note on the firmware in this repo:** the ESP32 firmware currently published in `esp32-firmware/32controlcode.ino` drives a simpler two-channel H-bridge (BTS7960-style) differential-drive setup — it predates/doesn't yet reflect the 4-motor hub-motor + hall-sensor-controller configuration described here. If you're working from this repo, treat the firmware doc as documentation of an earlier drivetrain revision, and the four-BLDC-controller setup as the current physical build that the firmware still needs to be updated to match (each hall-sensor BLDC controller typically takes a PWM throttle input plus a direction/brake logic pin — the ESP32 has enough PWM-capable GPIO to drive all four independently).

## Power

| Component | Role |
|---|---|
| **2× 36V 4.4Ah battery packs** | Main power source for the drivetrain — sized for the combined draw of four 400W-class BLDC controllers under load. |
| **36V → 5V 10A buck converter** | Steps the battery voltage down to a clean 5V rail for the Raspberry Pi and low-voltage sensors/logic. A 10A rating gives real headroom above the Pi 4's own draw for the camera, sensors, and any USB peripherals sharing that rail. |

## Sensors

| Sensor | Purpose | Notes |
|---|---|---|
| **Ultrasonic distance sensor** | Collision avoidance — forces a motor stop below a distance threshold. | Same role as documented in [`esp32-firmware.md`](./esp32-firmware.md). |
| **Temperature & humidity sensor** | Ambient environmental monitoring, reported on the live dashboard. | |
| **Water/rain sensor** | Safety cutoff — stops the robot if water is detected. | |
| **Battery voltage sensor** | Reports real pack voltage so you know when to recharge. | With a 36V pack, the sense circuit needs a resistor divider (or a dedicated voltage-sensor board) sized to bring worst-case pack voltage safely under the ESP32 ADC's 3.3V input range — this ratio is different from what a smaller LiPo pack would need, so double-check the divider math for the 36V rail specifically. |
| **Microphone sensor** | Sound/gesture triggering (e.g. clap detection) via envelope sampling. | |
| **Light sensor** | Ambient light level sensing — useful for auto-triggering the night-vision camera's IR illuminator or logging environmental conditions alongside temp/humidity. | |
| **MPU6500 (6-axis IMU)** | Accelerometer + gyroscope — gives the robot orientation, tilt, and motion-dynamics data (useful for detecting the suspension working, a tip-over event, or rough terrain). | Typically I²C. |
| **HMC5883L (3-axis magnetometer)** | Digital compass — heading/orientation relative to magnetic north. | Commonly paired with an IMU like the MPU6500 to get a full 9-DOF orientation estimate (accel + gyro + compass) — useful groundwork for future SLAM/autonomous-navigation work. Keep it mounted away from motor wiring and the BLDC controllers, since magnetometers are sensitive to nearby current-carrying conductors and motor magnets throwing off the heading reading. |
| **160° FOV camera with night vision** | Video feed for FPV control and the AI tracking pipeline, with the wide field of view helping compensate for a fixed (non-gimbaled) camera mount, and IR night-vision extending usable operating hours. | Feeds into MediaMTX on the Pi — see [`raspberry-pi-setup.md`](./raspberry-pi-setup.md). |

## Actuation / feedback

| Component | Role |
|---|---|
| **Beeper (buzzer)** | Audible status/alert indicator. |
| **Status LED** | Visual state indicator. |

## Networking / connectivity

| Component | Role |
|---|---|
| **ZTE MF833N USB 4G modem** | Provides the Pi's internet uplink in the field, independent of local Wi-Fi — this is what makes the robot reachable globally over Cloudflare Tunnel. See [`cloudflare-telegram-remote-access.md`](./cloudflare-telegram-remote-access.md). |

## How it all fits together

```
Sensors ───────►┌──────────────────────────┐
(ultrasonic,    │         ESP32            │◄──── 4× hall-sensor BLDC controllers ──► 4× hoverboard hub motors
 temp/humidity, │  (real-time control &    │
 water, mic,    │   safety loop)           │
 light, MPU6500,└───────────┬──────────────┘
 HMC5883L,                  │ UART (telemetry / commands)
 voltage)                   ▼
                ┌──────────────────────────┐
Camera (160°,  ►│      Raspberry Pi 4      │
 night vision)  │  Flask + SocketIO,       │
                │  MediaMTX, cloudflared   │
                └───────────┬──────────────┘
                             │ Cloudflare Tunnel (WebRTC + control)
                             ▼
        ZTE MF833N 4G ── Internet ── Browser / Telegram (anywhere)
                             │
                             ▼ (video feed)
              Offboard GPU workstation — YOLO11 + ByteTrack tracking

Power: 2× 36V 4.4Ah packs ──► BLDC controllers (direct)
                          └──► 36V→5V 10A converter ──► Pi 4, sensors, logic
```

This split — ESP32 for hard real-time/safety-critical control, Pi for networking/media, offboard GPU for AI — keeps each piece doing what it's actually good at instead of overloading a single board with everything.

See also: [`electrical-engineering-pcb.md`](./electrical-engineering-pcb.md) for wiring/power details, [`esp32-firmware.md`](./esp32-firmware.md) for the control logic, and [`ai-tracking-computer-vision.md`](./ai-tracking-computer-vision.md) for the vision pipeline.
