# Raspberry Pi: Installation, Configuration & Operation

`raspberry-pi/` — the Pi 4 is the edge controller: serves the web UI, relays motor commands to the ESP32, streams video over WebRTC, and runs the Cloudflare tunnels and Telegram notifications.

## 1. OS install

1. Flash Raspberry Pi OS (32- or 64-bit) with Raspberry Pi Imager.
2. Enable SSH and Wi-Fi in the Imager's advanced options if you need headless access before the 4G modem is wired in.
3. First boot, then:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ```

## 2. Enable UART (ESP32 link)

Pi talks to the ESP32 over `/dev/serial0`. Requires disabling the serial console and enabling the hardware UART:

```bash
sudo raspi-config
# Interface Options → Serial Port
#   "Would you like a login shell accessible over serial?" → No
#   "Would you like the serial port hardware enabled?" → Yes
sudo reboot
```

Confirm `/dev/serial0` exists after reboot. Wire ESP32 `Serial2` TX/RX (GPIO 17/16) to the Pi's UART RX/TX, cross-connected (Pi RX ↔ ESP32 TX, Pi TX ↔ ESP32 RX), shared ground.

## 3. Python environment

```bash
sudo apt install -y python3-pip python3-venv
python3 -m venv ~/robot-env
source ~/robot-env/bin/activate
pip install flask flask-socketio pyserial requests
```

`robot_app.py` depends on `flask`, `flask-socketio`, `pyserial` (`import serial`), `requests` (Telegram API).

## 4. MediaMTX

Takes the Pi's camera feed and exposes it over WebRTC (WHEP).

1. Download the MediaMTX build matching your Pi OS arch (ARM64/ARMv7), place the binary at `/home/<user>/mediamtx`.
2. `mediamtx.yml` sets up the WHEP endpoint and camera input. Check: WHEP server on port `8889` (this is the port `launch_robot.sh` tunnels), camera source path pointed at the right input (`ffmpeg`/`rpicam`/USB depending on the module).
3. Run `./mediamtx` locally first, confirm a WHEP stream pulls at `http://<pi-ip>:8889/<path>/whep` on the local network before wiring in the tunnels.

## 5. Control app — `robot_app.py`

Flask + Flask-SocketIO app:

- Serves a single-page dashboard (embedded as `HTML_PAGE`) with on-screen joysticks (nipplejs) and a live telemetry HUD.
- Opens UART to the ESP32: `serial.Serial('/dev/serial0', baudrate=115200, timeout=1)` — baud rate must match `Serial2.begin(115200, ...)` in the firmware.
- Two background threads:
  - `read_serial_telemetry()` — parses `TELEMETRY:` lines, re-emits over Socket.IO.
  - `notify_tunnel_urls_async()` — polls the Cloudflare tunnel logs for up to 30s after boot, sends URLs to Telegram (see [`5)cloudflare-telegram-remote-access.md`](./5%29cloudflare-telegram-remote-access.md)).
- Handles the `control` Socket.IO event, forwards it to the ESP32 as `CMD:<angle>,<speed>\n`.
- Serves `/get_stream_url` for the frontend to fetch the current WHEP URL (quick-tunnel URL changes on every restart).

Set before running:
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"   # from @BotFather
TELEGRAM_CHAT_ID   = "your_user_id"     # from @userinfobot
```

## 6. Boot orchestration — `launch_robot.sh`

Single entry point, run by systemd:

1. Kills leftover `cloudflared`/`robot_app.py`/`mediamtx` processes, clears old tunnel logs.
2. Starts MediaMTX.
3. Starts a Cloudflare quick tunnel for video (`8889`) → `/tmp/video_tunnel.log`.
4. Starts a second quick tunnel for control (`5000`) → `/tmp/control_tunnel.log`.
5. Runs `robot_app.py` in the foreground so systemd tracks it as the main process.

`sleep 2` between steps gives each process time to bind its port before the next starts.

## 7. systemd service — `robot.service`

```ini
[Unit]
Description=4G FPV Robot Control and Cloudflare Tunnels
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=raspforex
WorkingDirectory=/home/raspforex
ExecStart=/bin/bash /home/raspforex/launch_robot.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Install:
```bash
sudo cp robot.service /etc/systemd/system/robot.service
sudo systemctl daemon-reload
sudo systemctl enable robot.service
sudo systemctl start robot.service
```

Update `User=`, `WorkingDirectory=`, and the paths inside `launch_robot.sh` to match your Pi username instead of `raspforex`.

```bash
sudo systemctl status robot.service      # check running
sudo journalctl -u robot.service -f      # tail logs
sudo systemctl restart robot.service     # restart after a code change
```

## 8. 4G connectivity

Once the USB modem shows up as a network interface (most run in RNDIS/ECM mode — check `ip a`), `network-online.target` covers it, same as Wi-Fi or Ethernet.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `robot_app.py` can't open `/dev/serial0` | UART not enabled, or serial console still holding the port |
| No telemetry on dashboard | Baud mismatch, or TX/RX swapped between Pi and ESP32 |
| No Telegram message on boot | Wrong bot token/chat ID, or no internet yet when the 30s window expired |
| Video doesn't load | MediaMTX not running, wrong WHEP path, or video tunnel not up before `/get_stream_url` was polled |
