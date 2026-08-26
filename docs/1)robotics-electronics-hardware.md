# Robotics & Electronics: Sensors, Modules, and Boards

Full hardware list — what each part does and how it connects.

## Compute & control

| Component | Role |
|---|---|
| ESP32 WROOM DevKit | Real-time motor control and sensor safety loop. Dual-core, LEDC PWM, enough GPIO/ADC for the sensor set. See [`3)esp32-firmware.md`](./3%29esp32-firmware.md). |
| Raspberry Pi 4 (4GB) | Runs the Flask control server, MediaMTX, Cloudflare tunnels, Telegram integration. Needs full Linux for `cloudflared` and MediaMTX, and enough headroom for video. See [`4)raspberry-pi-setup.md`](./4%29raspberry-pi-setup.md). |

## Drivetrain

| Component | Role |
|---|---|
| 4× 6.5" hoverboard hub motors | One per wheel. No separate gearbox/chain. |
| 4× DC 6–60V 400W hall-sensor BLDC controller | One per motor. Hall feedback gives real rotor position, better low-speed torque than sensorless. |
| PCA9685 16-channel PWM driver (I2C 0x40) | Sits between the ESP32 and the four BLDC controllers. Outputs PWM speed + digital direction per motor (8 channels: PWM+DIR × 4), 1 kHz. Keeps motor timing off the ESP32's own GPIO/PWM budget. |

## Power

| Component | Role |
|---|---|
| 2× 36V 4.4Ah battery packs | Drivetrain supply, sized for four 400W-class controllers under load. |
| 36V → 5V 10A buck converter | Logic rail for Pi, ESP32, sensors. |

## Sensors

| Sensor | Purpose | Notes |
|---|---|---|
| Ultrasonic distance sensor | Collision braking below threshold distance. | |
| DHT11 (temp/humidity) | Environmental monitoring, shown on dashboard. | |
| Water/rain sensor | Water contact detection. | |
| Battery voltage sensor | Pack voltage readout. | 100kΩ/6.8kΩ resistor divider, keeps worst-case 36V pack voltage under the ESP32's 3.3V ADC limit. |
| INMP441 I2S microphone | Sound/gesture triggering (clap detection). | Currently disabled in firmware (`MIC_ENABLED 0`); telemetry sends a placeholder dB value until re-enabled. |
| Light sensor (analog + digital out) | Ambient light level. | Can gate the IR illuminator or log alongside temp/humidity. |
| MPU6050 (6-axis IMU) | Accelerometer + gyro, orientation/tilt. | I2C address 0x68. |
| QMC5883L (3-axis magnetometer) | Compass heading. | I2C address 0x0D. Keep away from motor wiring — sensitive to nearby current and magnets. |
| 160° FOV night-vision camera | Video for FPV + AI tracking. | Feeds MediaMTX on the Pi. |

## Actuation / feedback

| Component | Role |
|---|---|
| 3-pin transistor active buzzer | Audible status/alert, digital HIGH/LOW drive. |
| Status LED | Visual state indicator. |

## Networking

| Component | Role |
|---|---|
| ZTE MF833N USB 4G modem | Pi's internet uplink in the field, independent of local Wi-Fi. See [`5)cloudflare-telegram-remote-access.md`](./5%29cloudflare-telegram-remote-access.md). |

## System diagram

```
Sensors ───────►┌──────────────────────────┐
(ultrasonic,    │         ESP32            │◄──I2C──► PCA9685 ──► 4× BLDC controllers ──► 4× hub motors
 temp/humidity, │  (real-time control &    │
 water, mic,    │   safety loop)           │
 light, MPU6050,└───────────┬──────────────┘
 QMC5883L,                  │ UART (telemetry / commands)
 voltage)                   ▼
                ┌──────────────────────────┐
Camera (160°,  ►│      Raspberry Pi 4      │
 night vision)  │  Flask + SocketIO,       │
                │  MediaMTX, cloudflared   │
                └───────────┬──────────────┘
                             │ Cloudflare Tunnel (WebRTC + control)
                             ▼
        ZTE MF833N 4G ── Internet ── Browser / Telegram
                             │
                             ▼ (video feed)
              Offboard GPU workstation — YOLO11 + ByteTrack

Power: 2× 36V 4.4Ah packs ──► BLDC controllers (direct)
                          └──► 36V→5V 10A converter ──► Pi 4, sensors, logic
```

ESP32 owns real-time/safety-critical control, the Pi owns networking/media, the offboard workstation owns AI. Each board does one job.

See also: [`2)electrical-engineering-pcb.md`](./2%29electrical-engineering-pcb.md), [`3)esp32-firmware.md`](./3%29esp32-firmware.md), [`6)ai-tracking-computer-vision.md`](./6%29ai-tracking-computer-vision.md).
