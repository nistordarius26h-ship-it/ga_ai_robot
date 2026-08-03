import os
import re
import time
import serial
import requests
import threading
from flask import Flask, render_template_string
from flask_socketio import SocketIO

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "your_bot_token" #get at @BotFather
TELEGRAM_CHAT_ID   = "your_user_id" #get at @userinfobot by gmedia

# Open UART serial connection to ESP32
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def send_telegram_message(text):
    """Sends a text notification directly to your Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[Telegram Error] {e}")

def notify_tunnel_urls_async():
    """Background thread that waits for Cloudflare URLs on boot and sends them to Telegram."""
    control_url = None
    video_url = None

    # Check log files every second for up to 30 seconds
    for _ in range(30):
        if not control_url and os.path.exists("/tmp/control_tunnel.log"):
            with open("/tmp/control_tunnel.log", "r") as f:
                match = re.search(r'https://[a-zA-Z0-9-]*\.trycloudflare\.com', f.read())
                if match:
                    control_url = match.group(0)

        if not video_url and os.path.exists("/tmp/video_tunnel.log"):
            with open("/tmp/video_tunnel.log", "r") as f:
                match = re.search(r'https://[a-zA-Z0-9-]*\.trycloudflare\.com', f.read())
                if match:
                    video_url = match.group(0)

        if control_url and video_url:
            break

        time.sleep(1)

    if control_url:
        msg = f"🚀 *ROBOT ONLINE & READY!*\n\n📱 *Dashboard:* {control_url}\n\n📹 *Camera WHEP:* `{video_url}/cam/whep`"
        send_telegram_message(msg)
    else:
        send_telegram_message("⚠️ Robot booted, but Cloudflare tunnels failed to assign a public URL.")

def get_video_stream_url():
    log_path = "/tmp/video_tunnel.log"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            content = f.read()
            match = re.search(r'https://[a-zA-Z0-9-]*\.trycloudflare\.com', content)
            if match:
                return f"{match.group(0)}/cam/whep"
    return ""

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>4G FPV Robot Control</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/nipplejs/0.10.1/nipplejs.min.js"></script>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
            font-family: monospace;
        }

        video {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
            z-index: 1;
        }

        #hud {
            position: absolute;
            top: 15px;
            left: 15px;
            z-index: 10;
            background: rgba(0, 0, 0, 0.7);
            color: #00ffcc;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid rgba(0, 255, 204, 0.3);
            font-size: 13px;
            line-height: 1.6;
        }
        .hud-val { color: #fff; font-weight: bold; }
        .alert { color: #ff3333; font-weight: bold; animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0; } }

        #joystick-zone {
            position: absolute;
            bottom: 40px;
            right: 40px;
            width: 160px;
            height: 160px;
            z-index: 10;
        }
    </style>
</head>
<body>
    <video id="video" autoplay playsinline muted></video>

    <div id="hud">
        ⚡ BATT: <span id="batt" class="hud-val">--</span> V<br>
        🎙️ NOISE: <span id="mic" class="hud-val">--</span> dB<br>
        📏 DIST: <span id="dist" class="hud-val">--</span> cm<br>
        💧 WATER: <span id="water" class="hud-val">--</span><br>
        🌡️ TEMP: <span id="temp" class="hud-val">--</span> °C<br>
        💨 HUMID: <span id="humid" class="hud-val">--</span> %
    </div>

    <div id="joystick-zone"></div>

    <script>
        const videoEl = document.getElementById('video');

        async function startWebRTC() {
            try {
                const res = await fetch('/get_stream_url');
                const data = await res.json();
                const whepUrl = data.url;

                if (!whepUrl) {
                    setTimeout(startWebRTC, 2000);
                    return;
                }

                const pc = new RTCPeerConnection({
                    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
                });

                pc.addTransceiver('video', { direction: 'recvonly' });
                pc.ontrack = (e) => { videoEl.srcObject = e.streams[0]; };

                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);

                const response = await fetch(whepUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/sdp' },
                    body: offer.sdp
                });

                if (response.ok) {
                    const answerSdp = await response.text();
                    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
                }
            } catch (err) {
                console.error(err);
            }
        }

        startWebRTC();

        const socket = io();
        socket.on('telemetry', (d) => {
            document.getElementById('batt').innerText = d.batt;
            document.getElementById('mic').innerText = d.mic;
            document.getElementById('dist').innerText = d.dist;

            const waterEl = document.getElementById('water');
            if (d.water === "DETECTED") {
                waterEl.innerText = "ALARM!";
                waterEl.className = "alert";
            } else {
                waterEl.innerText = "CLEAR";
                waterEl.className = "hud-val";
            }

            document.getElementById('temp').innerText = d.temp;
            document.getElementById('humid').innerText = d.humid;
        });

        const manager = nipplejs.create({
            zone: document.getElementById('joystick-zone'),
            mode: 'static',
            position: { right: '80px', bottom: '80px' },
            color: 'cyan'
        });

        let lastSend = 0;
        manager.on('move', (evt, data) => {
            const now = Date.now();
            if (now - lastSend > 40) {
                socket.emit('control', { angle: Math.round(data.angle.degree), speed: Math.min(Math.round(data.distance), 100) });
                lastSend = now;
            }
        });

        manager.on('end', () => { socket.emit('control', { angle: 0, speed: 0 }); });
    </script>
</body>
</html>
"""

def read_serial_telemetry():
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("TELEMETRY:"):
                    parts = line.replace("TELEMETRY:", "").split(",")
                    if len(parts) == 6:
                        batt, mic, temp, humid, dist, water = parts
                        socketio.emit('telemetry', {
                            'batt': round(float(batt), 2) if batt != 'nan' else '--',
                            'mic': round(float(mic), 1) if mic != 'nan' else '--',
                            'temp': round(float(temp), 1) if temp != 'nan' else '--',
                            'humid': round(float(humid), 1) if humid != 'nan' else '--',
                            'dist': round(float(dist), 1) if dist != 'nan' else '--',
                            'water': "DETECTED" if water == "1" else "CLEAR"
                        })
        except Exception:
            pass

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/get_stream_url')
def get_stream_url():
    return {'url': get_video_stream_url()}

@socketio.on('control')
def handle_control(data):
    ser.write(f"CMD:{data['angle']},{data['speed']}\n".encode('utf-8'))

if __name__ == '__main__':
    # Start Telegram URL notifier background thread
    threading.Thread(target=notify_tunnel_urls_async, daemon=True).start()

    # Start UART telemetry reader thread
    threading.Thread(target=read_serial_telemetry, daemon=True).start()

    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
