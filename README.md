# Globally Accessible Autonomous Robot with AI Tracking & Environmental Sensing
![Python](https://img.shields.io/badge/Python-3.11-blue)
![C++](https://img.shields.io/badge/C%2B%2B-ESP32-blue)
![Linux](https://img.shields.io/badge/Platform-Raspberry%20Pi-green)
![AI](https://img.shields.io/badge/AI-Object%20Tracking-orange)
![License](https://img.shields.io/badge/License-MIT-red)

## Overview

This project presents a **remotely operable autonomous robot**, controllable from anywhere in the world over a 4G cellular connection.

The robot integrates the AI Multi-Object Tracker developed in my previous project, adapting it into an autonomous person-following system capable of real-time object detection and tracking. By combining this computer vision pipeline with onboard robotics hardware, the platform can detect, track, and follow designated targets while remaining under remote supervision.

The platform combines low-level embedded motor control, onboard edge computing, real-time video streaming, offboard AI object tracking, and solar-based power into a single distributed system — enabling autonomous navigation and cargo transport across rugged, uneven terrain without dependence on local Wi-Fi.

> **Disclaimer**
>
> This project is a personal engineering/research build. It is not a commercial or certified product, and hardware/wiring shared here should be adapted and tested carefully before reuse.

---

## Features

- Global remote access via 4G LTE
- Low-latency FPV video streaming (WebRTC)
- Real-time AI object detection & autonomous target-following
- Active mechanical suspension for terrain stability
- Ultrasonic collision avoidance
- Microphone-based sound/gesture triggering (e.g. clap detection)
- Battery voltage monitoring with automated alerts
- Temperature, humidity, and rain/water sensing
- Solar-powered for extended field deployment
- Automated boot orchestration and secure remote tunneling

---

## System Architecture

- Environment / Terrain
- ESP32 (motor control, safety sensors)
- Raspberry Pi (edge compute, streaming, orchestration)
- 4G LTE Modem (remote connectivity)
- Offboard AI Workstation (GPU-accelerated tracking)
- Remote Operator (anywhere in the world)

---

## Technologies

- C++ (ESP32 firmware)
- Python (Flask, SocketIO, AI tracking)
- Linux (Raspberry Pi)
- MediaMTX (WebRTC streaming)
- Ultralytics YOLO11x
- ByteTrack
- Cloudflare Tunnel
- systemd

---

## Requirements

### Software

- Python 3.11+
- C++ toolchain for ESP32
- Raspberry Pi OS (32 / 64-bit)
- PlatformIO or Arduino IDE
- PyTorch (CUDA, ROCm, or CPU)
- MediaMTX
- Cloudflare Tunnel

### Network

- 4G LTE modem with active data connection
- Internet connectivity for remote operation

> **Development Note**
>
> The AI tracking pipeline was developed and tested on an **AMD Radeon RX 7800 XT**. Configuring GPU acceleration with ROCm/HIP required additional setup compared to NVIDIA CUDA. If GPU acceleration is unavailable, the AI software automatically falls back to CPU execution.

---

## Hardware

- ESP32 WROOM DevKit
- Raspberry Pi 4
- 4G LTE USB modem
- Ultrasonic distance sensors
- Microphone module
- Battery voltage sensor
- Temperature & humidity sensor
- Rain/water sensor
- Solar panel(s)
- Camera module
- Custom chassis
- JGB37-500 12V motor and encoder
- 2X 3A LM2596 voltage regulator
- BTS7960 43A controller module
- 3S LiPo 11.1V 5000mAh battery

---

## Project Structure

```
esp32-firmware/     # C++ firmware for motor/sensor control
raspberry-pi/        # Control app, boot script, streaming config
ai-tracking/         # Offboard YOLO11x + ByteTrack pipeline
docs/                # Architecture diagrams and notes
media/               # Photos, demo clips
```

---

## Future Work

- Onboard (edge) AI inference to remove dependency on an offboard workstation
- Improved terrain-adaptive suspension tuning
- SLAM-based autonomous navigation
- Extended solar/battery capacity for multi-day deployment
- Mobile app for remote control and monitoring

---

## License

MIT License

---

## Author

Nistor Darius

Embedded Systems • Robotics • AI
