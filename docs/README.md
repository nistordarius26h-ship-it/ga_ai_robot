# Documentation

| Doc | Covers |
|---|---|
| [`esp32-firmware.md`](./esp32-firmware.md) | C++ firmware architecture: motor control, sensor sampling, serial protocol |
| [`electrical-engineering-pcb.md`](./electrical-engineering-pcb.md) | Wiring, power distribution, motor driver sizing, and PCB design workflow |
| [`robotics-electronics-hardware.md`](./robotics-electronics-hardware.md) | Sensor/module breakdown — what each part does and why it was chosen |
| [`3d-modeling-rendering.md`](./3d-modeling-rendering.md) | Fusion 360 chassis modeling and rendering workflow |
| [`raspberry-pi-setup.md`](./raspberry-pi-setup.md) | Installing, configuring, and running the Pi as the robot's edge controller |
| [`cloudflare-telegram-remote-access.md`](./cloudflare-telegram-remote-access.md) | Cloudflare Tunnel + Telegram bot setup for global control and video access |
| [`ai-tracking-computer-vision.md`](./ai-tracking-computer-vision.md) | YOLO11 + ByteTrack + OpenCV pipeline used for autonomous target following |

## Suggested reading order

1. Start with **robotics-electronics-hardware.md** for the parts list and what each component does.
2. **electrical-engineering-pcb.md** for how it's all wired and powered.
3. **esp32-firmware.md** for the low-level control logic.
4. **raspberry-pi-setup.md** and **cloudflare-telegram-remote-access.md** for the edge compute and remote-access layer.
5. **ai-tracking-computer-vision.md** for the vision/tracking pipeline.
6. **3d-modeling-rendering.md** for the mechanical design.

Back to [main README](../README.md).
