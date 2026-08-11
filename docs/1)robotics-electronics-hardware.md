# Robotics & Electronics: Sensors, Modules, and Boards

A breakdown of every physical component in the build, what it does, why it was chosen, and how it fits into the system.

## Compute & control

| Component | Role |
|---|---|
| **ESP32 WROOM DevKit** | Real-time motor control and sensor safety layer. Chosen for dual-core performance, PWM (LEDC) peripherals, plenty of GPIO/ADC pins, and a native Arduino/C++ toolchain — see [`esp32-firmware.md`](./esp32-firmware.md). |
| **Raspberry Pi 4** | Edge compute: runs the Flask control server, MediaMTX video server, Cloudflare tunnels, and Telegram integration. Chosen over the ESP32 for this role because it needs real Linux (for MediaMTX, systemd, and Cloudflare's `cloudflared` binary) and more processing headroom for video handling — see [`raspberry-pi-setup.md`](./raspberry-pi-setup.md). |

## Drivetrain

| Component | Role |
|---|---|
| **JGB37-500 12V DC gear motor + encoder** (×2) | Drive motors. The built-in gearbox trades top speed for torque, which matters for climbing over uneven/rugged terrain rather than racing on flat ground. |
| **BTS7960 43A H-bridge motor driver** | Drives each motor from the LiPo pack under ESP32 PWM/direction control. See [`electrical-engineering-pcb.md`](./electrical-engineering-pcb.md) for the sizing rationale versus a smaller driver like the L298N. |

## Power

| Component | Role |
|---|---|
| **3S LiPo 11.1V 5000mAh** | Main pack, sized for the motor current draw and to give reasonable field runtime. |
| **2× LM2596 3A buck regulator** | Step the LiPo voltage down to 5V for the Pi and sensor rails — kept as two independent regulators to isolate the Pi's supply from motor-driver switching noise. |
| **Solar panel(s)** | Extends field deployment time without needing to swap/recharge the LiPo mid-mission. |

## Sensors

| Sensor | Purpose | Wired to |
|---|---|---|
| **Ultrasonic distance sensor (HC-SR04-style)** | Collision avoidance — forces a hard motor stop below a configurable distance threshold. | ESP32 (TRIG/ECHO) |
| **DHT11** | Ambient temperature & humidity monitoring, reported on the live dashboard. | ESP32 (single data pin) |
| **Rain/water sensor** | Safety cutoff — stops the robot immediately if water is detected on the sensor pads. | ESP32 (digital) |
| **Battery voltage sensor (resistor divider)** | Lets the firmware/dashboard report real pack voltage so you know when to recharge/swap the LiPo. | ESP32 (ADC) |
| **Microphone module (electret + amp)** | Sound/gesture triggering — e.g. clap detection, via peak-to-peak envelope sampling and a rough dB estimate. | ESP32 (ADC) |
| **Camera module** | Video feed for FPV control and the AI tracking pipeline. | Raspberry Pi |

## Actuation / feedback

| Component | Role |
|---|---|
| **Buzzer** | Audible status/alert indicator, driven via LEDC tone output on the ESP32. |
| **Status LED** | Visual state indicator. |
| **Active mechanical suspension** | Improves stability and traction across rugged, uneven terrain — modeled with real joints in Fusion 360 to verify range of motion before build; see [`3d-modeling-rendering.md`](./3d-modeling-rendering.md). |

## Networking / connectivity

| Component | Role |
|---|---|
| **4G LTE USB modem** | Provides the Pi's internet uplink in the field, independent of local Wi-Fi. |

## How it all fits together

```
                ┌──────────────────────────┐
Sensors ───────►│         ESP32            │◄──── Motor driver (BTS7960) ──► JGB37-500 motors ×2
(ultrasonic,    │  (real-time control &    │
 DHT11, water,  │   safety loop)           │
 mic, voltage)  └───────────┬──────────────┘
                             │ UART 115200 (TELEMETRY: / CMD:)
                             ▼
                ┌──────────────────────────┐
Camera ────────►│      Raspberry Pi 4      │
                │  Flask + SocketIO,       │
                │  MediaMTX, cloudflared   │
                └───────────┬──────────────┘
                             │ Cloudflare Tunnel (WebRTC + control)
                             ▼
                    4G LTE ── Internet ── Browser / Telegram (anywhere)
                             │
                             ▼ (video feed)
              Offboard GPU workstation — YOLO11 + ByteTrack tracking
```

This split — ESP32 for hard real-time/safety-critical control, Pi for networking/media, offboard GPU for AI — keeps each piece doing what it's actually good at instead of overloading a single board with everything.

See also: [`electrical-engineering-pcb.md`](./electrical-engineering-pcb.md) for wiring/power details, [`esp32-firmware.md`](./esp32-firmware.md) for the control logic, and [`ai-tracking-computer-vision.md`](./ai-tracking-computer-vision.md) for the vision pipeline.
