# Raspberry Pi: Installation, Configuration & Operation

The Raspberry Pi 4 is the edge computer: it serves the control UI, bridges commands/telemetry to the ESP32, runs MediaMTX, starts Cloudflare tunnels, and sends the current URLs through Telegram.

## UART

Enable the Raspberry Pi hardware UART and disable the serial login console. The application uses `/dev/serial0` at `115200` baud.

Physical connection:

```text
Pi TX  -> ESP32 RX / GPIO16
Pi RX  <- ESP32 TX / GPIO17
Pi GND <-> ESP32 GND
```

## Python environment

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv curl
python3 -m venv ~/robot-env
source ~/robot-env/bin/activate
pip install flask flask-socketio pyserial requests
```

## Secrets

Do not hard-code the Telegram token/chat ID in `robot_app.py`.

```bash
sudo mkdir -p /etc/ga-ai-robot
sudo cp robot.env.example /etc/ga-ai-robot/robot.env
sudo chmod 600 /etc/ga-ai-robot/robot.env
sudo nano /etc/ga-ai-robot/robot.env
```

`robot.service` loads this file with `EnvironmentFile=`.

## MediaMTX

Place the MediaMTX binary at `/home/raspforex/mediamtx` or override the path in the environment file.

The included configuration publishes the Raspberry Pi camera as `cam` and provides WHEP at:

```text
http://127.0.0.1:8889/cam/whep
```

Test this locally before debugging Cloudflare.

### 4G / TURN

A Cloudflare HTTP tunnel does not relay the WebRTC RTP/ICE media path. On LTE/CGNAT, add a TURN/TURNS server to the Pi's local `mediamtx.yml` copy. Keep the public GitHub copy credential-free.

## Boot launcher

`launch_robot.sh` now:
1. removes stale runtime logs;
2. waits until a real HTTPS Internet request works;
3. starts MediaMTX;
4. waits until port 8889 is actually listening;
5. starts the video and control Quick Tunnels;
6. starts `robot_app.py` in the foreground.

This removes the old fixed-delay race that was exposed when Wi-Fi was replaced by the slower-starting LTE dongle.

## systemd

```bash
sudo cp robot.service /etc/systemd/system/robot.service
sudo systemctl daemon-reload
sudo systemctl enable --now robot.service
```

Useful commands:

```bash
sudo systemctl status robot.service
sudo journalctl -u robot.service -f
sudo systemctl restart robot.service
```

## Control application

The current dashboard uses custom linear touch/mouse sliders. Speed mode scales both throttle and steering. The Pi also sends the active mode limit (25/50/100) so the ESP32 can normalize steering: ±25 is full lock in LOW, ±50 is full lock in MED, and ±100 is full lock in HIGH.

The Pi stores the latest valid command and sends it to the ESP32 every `100 ms`. If the browser disconnects, the stored command is zeroed. The ESP32 independently rejects stale command streams with its watchdog.
