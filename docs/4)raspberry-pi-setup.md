# Raspberry Pi: Installation, Configuration & Operation

`raspberry-pi/` — the Raspberry Pi 4 is the robot's **edge controller**: it serves the web control UI, relays motor commands to the ESP32, streams video via WebRTC, and orchestrates the Cloudflare tunnels and Telegram notifications that make the robot reachable from anywhere.

## 1. OS installation

1. Flash **Raspberry Pi OS (32- or 64-bit)** to a microSD card using Raspberry Pi Imager.
2. In the Imager's advanced options (or via `raspi-config` after first boot), enable SSH and configure Wi-Fi if you'll need headless access before the 4G modem is wired in.
3. First boot, then update the system:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ```

## 2. Enable the UART (ESP32 link)

The Pi talks to the ESP32 over serial (`/dev/serial0`), which requires disabling the Pi's serial console and enabling the hardware UART:

```bash
sudo raspi-config
# Interface Options → Serial Port
#   "Would you like a login shell accessible over serial?" → No
#   "Would you like the serial port hardware enabled?" → Yes
sudo reboot
```

Confirm `/dev/serial0` exists after reboot and wire the ESP32's `Serial2` TX/RX (GPIO 17/16) to the Pi's UART RX/TX (cross-connected — Pi RX to ESP32 TX, Pi TX to ESP32 RX) with a shared ground.

## 3. Python environment

```bash
sudo apt install -y python3-pip python3-venv
python3 -m venv ~/robot-env
source ~/robot-env/bin/activate
pip install flask flask-socketio pyserial requests
```

`robot_app.py` depends on: `flask`, `flask-socketio`, `pyserial` (imported as `serial`), and `requests` (for the Telegram API calls).

## 4. MediaMTX (WebRTC video server)

MediaMTX is the media server that takes the Pi's camera feed and exposes it over **WebRTC (WHEP)** for low-latency browser playback.

1. Download the appropriate MediaMTX release (ARM64/ARMv7 build matching your Pi OS) and place the binary at `/home/<user>/mediamtx`.
2. The included `mediamtx.yml` configures WebRTC (WHEP endpoint), camera input, and ports. Key settings to check for this setup:
   - WebRTC/WHEP server enabled on port `8889` (this is the port `launch_robot.sh` tunnels for the video feed).
   - A camera source path configured to read from the Pi's camera (via `ffmpeg`/`rpicam`/USB source, depending on which camera module is attached).
3. Test it locally first: run `./mediamtx` and confirm you can pull a WHEP stream at `http://<pi-ip>:8889/<path>/whep` from the local network before wiring in the tunnels.

## 5. The control app — `robot_app.py`

A Flask + Flask-SocketIO app that:

- Serves a single-page HTML dashboard (embedded in the script as `HTML_PAGE`) with an on-screen joysticks (nipplejs) and a live telemetry HUD.
- Opens the UART link to the ESP32 (`serial.Serial('/dev/serial0', baudrate=115200, timeout=1)`) — **the baud rate here must match `Serial2.begin(115200, ...)` in the ESP32 firmware.**
- Runs two background threads:
  - `read_serial_telemetry()` — parses `TELEMETRY:` lines from the ESP32 and re-emits them to connected browsers over Socket.IO.
  - `notify_tunnel_urls_async()` — polls the Cloudflare tunnel log files for up to 30 seconds after boot and sends the resulting public URLs to Telegram (see [`cloudflare-telegram-remote-access.md`](./cloudflare-telegram-remote-access.md)).
- Handles the `control` Socket.IO event from the browser joystick and forwards it to the ESP32 as `CMD:<angle>,<speed>\n`.
- Serves `/get_stream_url`, which the frontend polls to discover the current WebRTC WHEP URL (since the Cloudflare quick-tunnel URL changes on every restart).

Before running, edit the two placeholder constants at the top of the file:
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"   # from @BotFather
TELEGRAM_CHAT_ID   = "your_user_id"     # from @userinfobot
```

## 6. Boot orchestration — `launch_robot.sh`

This script is the single entry point that brings the whole stack up in order, and is what systemd actually runs:

1. Kills any leftover `cloudflared`, `robot_app.py`, or `mediamtx` processes and clears old tunnel logs — makes restarts idempotent.
2. Starts MediaMTX.
3. Starts a Cloudflare quick tunnel for the video port (`8889`), logging to `/tmp/video_tunnel.log`.
4. Starts a second Cloudflare quick tunnel for the control port (`5000`), logging to `/tmp/control_tunnel.log`.
5. Runs `robot_app.py` in the foreground (so systemd tracks it as the main process for restart/monitoring purposes).

The `sleep 2` calls between steps are a simple/pragmatic way to give each process time to bind its port before the next one starts — not perfectly robust, but effective in practice for this on-boot use case.

## 7. Running it as a service — `robot.service`

A systemd unit that runs `launch_robot.sh` automatically after networking is up, and restarts it if it ever crashes:

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

Installation:

```bash
sudo cp robot.service /etc/systemd/system/robot.service
sudo systemctl daemon-reload
sudo systemctl enable robot.service
sudo systemctl start robot.service
```

Update `User=` and `WorkingDirectory=` (and the paths inside `launch_robot.sh`) to match your actual Pi username instead of `raspforex`.

Useful commands while developing:

```bash
sudo systemctl status robot.service      # check it's running
sudo journalctl -u robot.service -f      # tail live logs
sudo systemctl restart robot.service     # restart after a code change
```

## 8. 4G connectivity

The 4G USB modem provides the Pi's uplink in the field. Once it's recognized by the Pi as a network interface (most USB modems in "RNDIS"/"ECM" mode just appear as a standard Ethernet-like interface — check with `ip a` after plugging in), `network-online.target` covers it and the systemd service above will wait for it before launching, same as it would for Wi-Fi or Ethernet.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `robot_app.py` can't open `/dev/serial0` | UART not enabled in `raspi-config`, or another process (serial console) is still holding the port |
| No telemetry on the dashboard | Baud rate mismatch, or TX/RX wires swapped between Pi and ESP32 |
| No Telegram message on boot | Wrong bot token/chat ID, or the Pi had no internet yet when the 30s polling window expired |
| Video doesn't load in browser | MediaMTX not running, wrong WHEP path, or the video Cloudflare tunnel didn't come up before `/get_stream_url` was first polled |
