# GA AI Robot — Globally Accessible Autonomous Robot

![Python](https://img.shields.io/badge/Python-3.11-blue)
![C++](https://img.shields.io/badge/C%2B%2B-ESP32-blue)
![Linux](https://img.shields.io/badge/Platform-Raspberry%20Pi-green)
![AI](https://img.shields.io/badge/AI-Object%20Tracking-orange)
![License](https://img.shields.io/badge/License-MIT-red)

<img width="900" alt="gaairobotrenderss" src="https://github.com/user-attachments/assets/26aaba77-5643-4f9d-8797-212f19054a5e" />

## Overview

Four-wheeled differential-drive robot, controllable from anywhere over 4G. An ESP32 handles motor control and safety-critical sensors in a tight real-time loop; a Raspberry Pi 4 handles video streaming, the web dashboard, and remote connectivity; an offboard GPU workstation runs YOLO11 + ByteTrack for person detection and tracking.

This is a personal build, not a certified product. Wiring and code here should be checked against your own hardware before reuse.

## Features

- Remote control over 4G LTE, no local Wi-Fi dependency
- Low-latency video via WebRTC (MediaMTX)
- Real-time object detection and target-following (YOLO11 + ByteTrack, offboard)
- Ultrasonic collision braking
- Battery voltage, temperature/humidity, and water sensing
- Telegram boot notification with current tunnel URLs
- Automated boot via systemd + Cloudflare Tunnel

## System architecture

```
Sensors/motors → ESP32 (real-time control, safety loop)
              → UART → Raspberry Pi 4 (dashboard, video, tunnels, Telegram)
                     → Cloudflare Tunnel → Internet → browser / Telegram
                     → video feed → offboard GPU workstation (YOLO11 + ByteTrack)
```

See [`docs/`](./docs) for the full breakdown.

## Technologies

- C++ (ESP32 firmware, Arduino framework)
- Python (Flask, Flask-SocketIO, PyTorch)
- MediaMTX (WebRTC/WHEP video)
- Ultralytics YOLO11x + ByteTrack
- Cloudflare Tunnel
- systemd

## Requirements

**Software**
- Python 3.11+
- Arduino IDE or PlatformIO
- Raspberry Pi OS (32/64-bit)
- PyTorch (CUDA, ROCm, or CPU)
- MediaMTX
- cloudflared

**Network**
- 4G LTE modem with active data plan

AI tracking was developed and tested on an AMD Radeon RX 7800 XT. ROCm/HIP setup takes more steps than CUDA; falls back to CPU if no GPU is available.

## Hardware

**Compute**
- ESP32 WROOM DevKit — motor control, sensor safety loop
- Raspberry Pi 4 (4GB) — dashboard, video, tunnels, Telegram

**Drivetrain**
- 4× 6.5" hoverboard hub motors
- 4× DC 6–60V 400W hall-sensor BLDC motor controllers
- PCA9685 16-channel PWM driver (I2C 0x40) — PWM + direction per motor, 1 kHz

**Power**
- 2× 36V 4.4Ah battery packs
- 36V → 5V 10A buck converter (Pi, ESP32, sensor rail)

**Sensors**
- Ultrasonic distance sensor
- DHT11 temperature/humidity
- Water/rain sensor
- Battery voltage sensor (100kΩ/6.8kΩ divider)
- INMP441 I2S microphone (currently disabled in firmware, placeholder value in telemetry)
- Light sensor (analog + digital)
- MPU6050 6-axis accel/gyro (I2C)
- QMC5883L 3-axis magnetometer (I2C)
- 160° FOV night-vision camera

**Actuation / feedback**
- 3-pin transistor active buzzer
- Status LED

**Connectivity**
- ZTE MF833N USB 4G/LTE modem

**Chassis**
- Custom Fusion 360 design, see [`docs/7)3d-modeling-rendering.md`](./docs/7%293d-modeling-rendering.md)

## Project structure

```
esp32-firmware/   C++ firmware, motor + sensor control
raspberry-pi/     Control app, boot script, MediaMTX config
ai-tracking/      Offboard YOLO11 + ByteTrack pipeline
docs/             Component and subsystem documentation
media/            Renders, photos, clips
```

## Future work

- Onboard (edge) inference to remove the offboard GPU dependency
- SLAM-based navigation
- Mobile app for control/monitoring
- Custom PCB (currently point-to-point wiring)

## License

MIT

## Author

Nistor Darius — Embedded systems, robotics, AI
