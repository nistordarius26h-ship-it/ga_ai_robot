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

ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[Telegram Error] {e}")

def notify_tunnel_urls_async():
    control_url, video_url = None, None
    for _ in range(30):
        if not control_url and os.path.exists("/tmp/control_tunnel.log"):
            with open("/tmp/control_tunnel.log", "r") as f:
                match = re.search(r'https://[a-zA-Z0-9-]*\.trycloudflare\.com', f.read())
                if match: control_url = match.group(0)

        if not video_url and os.path.exists("/tmp/video_tunnel.log"):
            with open("/tmp/video_tunnel.log", "r") as f:
                match = re.search(r'https://[a-zA-Z0-9-]*\.trycloudflare\.com', f.read())
                if match: video_url = match.group(0)

        if control_url and video_url: break
        time.sleep(1)

    if control_url:
        msg = f"🚀 *ROBOT ONLINE & READY!*\n\n📱 *Dashboard:* {control_url}\n\n📹 *Camera WHEP:* `{video_url}/cam/whep`"
        send_telegram_message(msg)

def get_video_stream_url():
    log_path = "/tmp/video_tunnel.log"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            match = re.search(r'https://[a-zA-Z0-9-]*\.trycloudflare\.com', f.read())
            if match: return f"{match.group(0)}/cam/whep"
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
            margin: 0; padding: 0; width: 100%; height: 100%;
            overflow: hidden; background: #000; font-family: monospace;
        }
        video {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            object-fit: contain; z-index: 1;
        }

        #hud {
            position: absolute; top: 15px; left: 15px; z-index: 10;
            background: rgba(0, 0, 0, 0.75); color: #00ffcc;
            padding: 12px 16px; border-radius: 8px;
            border: 1px solid rgba(0, 255, 204, 0.3);
            font-size: 13px; line-height: 1.6;
        }
        .hud-val { color: #fff; font-weight: bold; }
        .alert { color: #ff3333; font-weight: bold; animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0; } }

        #top-right-instruments {
            position: absolute; top: 15px; right: 15px; z-index: 10;
            display: flex; gap: 12px; align-items: center;
        }

        .widget-box {
            background: rgba(0, 0, 0, 0.85); border: 1.5px solid rgba(0, 255, 204, 0.5);
            border-radius: 50%; width: 95px; height: 95px;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            position: relative; overflow: hidden; box-shadow: 0 0 10px rgba(0,0,0,0.9);
        }

        /* Compass Widget */
        #compass-dial {
            position: absolute; width: 100%; height: 100%;
            border-radius: 50%; transition: transform 0.2s ease-out;
        }
        .compass-mark {
            position: absolute; width: 100%; text-align: center;
            font-size: 11px; font-weight: bold; color: #ff3300; top: 3px;
        }
        #compass-readout {
            z-index: 2; font-size: 11px; font-weight: bold; color: #fff; text-align: center;
            text-shadow: 1px 1px 2px #000;
        }

        /* Tilt / Horizon Animated Widget */
        #horizon-disc {
            position: absolute; width: 100%; height: 100%; border-radius: 50%;
            overflow: hidden; z-index: 1;
        }
        #horizon-sky {
            position: absolute; width: 200%; height: 100%; top: -50%; left: -50%; background: #0066cc;
        }
        #horizon-ground {
            position: absolute; width: 200%; height: 100%; top: 50%; left: -50%; background: #663300;
        }
        #horizon-pitch-roll {
            position: absolute; width: 100%; height: 100%;
            transition: transform 0.1s ease-out;
        }
        #horizon-line {
            position: absolute; width: 200%; height: 2px; background: #00ffcc; top: 50%; left: -50%;
        }
        .horizon-crosshair {
            position: absolute; z-index: 4; width: 20px; height: 20px;
            border: 2px solid #ffcc00; border-radius: 50%;
        }
        #tilt-readout {
            position: absolute; bottom: 6px; z-index: 5; font-size: 9px;
            font-weight: bold; color: #fff; text-shadow: 1px 1px 2px #000;
        }

        /* Joysticks */
        #left-joystick-zone {
            position: absolute; bottom: 40px; left: 40px;
            width: 150px; height: 150px; z-index: 10;
        }
        #right-joystick-zone {
            position: absolute; bottom: 40px; right: 40px;
            width: 150px; height: 150px; z-index: 10;
        }
    </style>
</head>
<body>
    <video id="video" autoplay playsinline muted></video>

    <!-- Top Left HUD -->
    <div id="hud">
        ⚡ BATT: <span id="batt" class="hud-val">--</span> V<br>
        🎙️ NOISE: <span id="mic" class="hud-val">--</span> dB<br>
        📏 DIST: <span id="dist" class="hud-val">--</span> cm<br>
        💧 WATER: <span id="water" class="hud-val">--</span><br>
        🌡️ TEMP: <span id="temp" class="hud-val">--</span> °C<br>
        💨 HUMID: <span id="humid" class="hud-val">--</span> %<br>
        💡 LIGHT: <span id="light-mode" class="hud-val">--</span>
    </div>

    <!-- Top Right Visual Instruments -->
    <div id="top-right-instruments">
        <!-- Animated Horizon Tilt Instrument -->
        <div class="widget-box">
            <div class="horizon-crosshair"></div>
            <div id="horizon-disc">
                <div id="horizon-pitch-roll">
                    <div id="horizon-sky"></div>
                    <div id="horizon-ground"></div>
                    <div id="horizon-line"></div>
                </div>
            </div>
            <div id="tilt-readout"><span id="pitch-val">0</span>° / <span id="roll-val">0</span>°</div>
        </div>

        <!-- Animated Compass Instrument -->
        <div class="widget-box">
            <div id="compass-dial">
                <div class="compass-mark">▲ N</div>
            </div>
            <div id="compass-readout">
                <span id="heading-deg">--</span>°<br>
                <span id="heading-card" style="color:#00ffcc;">--</span>
            </div>
        </div>
    </div>

    <!-- Dual Joystick Touch Zones -->
    <div id="left-joystick-zone"></div>
    <div id="right-joystick-zone"></div>

    <script>
        const videoEl = document.getElementById('video');

        async function startWebRTC() {
            try {
                const res = await fetch('/get_stream_url');
                const data = await res.json();
                if (!data.url) { setTimeout(startWebRTC, 2000); return; }

                const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
                pc.addTransceiver('video', { direction: 'recvonly' });
                pc.ontrack = (e) => { videoEl.srcObject = e.streams[0]; };

                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);

                const response = await fetch(data.url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/sdp' },
                    body: offer.sdp
                });

                if (response.ok) {
                    const answerSdp = await response.text();
                    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
                }
            } catch (err) { console.error(err); }
        }
        startWebRTC();

        function getCardinalDirection(deg) {
            const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
            return directions[Math.round(deg / 45) % 8];
        }

        const socket = io();
        socket.on('telemetry', (d) => {
            document.getElementById('batt').innerText = d.batt;
            document.getElementById('mic').innerText = d.mic;
            document.getElementById('dist').innerText = d.dist;

            const waterEl = document.getElementById('water');
            if (d.water === "DETECTED") {
                waterEl.innerText = "ALARM!"; waterEl.className = "alert";
            } else {
                waterEl.innerText = "CLEAR"; waterEl.className = "hud-val";
            }

            document.getElementById('temp').innerText = d.temp;
            document.getElementById('humid').innerText = d.humid;

            document.getElementById('light-mode').innerText = d.is_day ? "☀️ DAY" : "🌙 NIGHT";

            // Compass Instrument Update
            if (d.heading !== '--') {
                const headingVal = floatVal(d.heading);
                document.getElementById('heading-deg').innerText = Math.round(headingVal);
                document.getElementById('heading-card').innerText = getCardinalDirection(headingVal);
                document.getElementById('compass-dial').style.transform = `rotate(${-headingVal}deg)`;
            }

            // Tilt Instrument Horizon Animation
            if (d.pitch !== '--' && d.roll !== '--') {
                const pitch = floatVal(d.pitch);
                const roll = floatVal(d.roll);
                document.getElementById('pitch-val').innerText = Math.round(pitch);
                document.getElementById('roll-val').innerText = Math.round(roll);

                const horizonEl = document.getElementById('horizon-pitch-roll');
                horizonEl.style.transform = `translateY(${pitch * 0.9}px) rotate(${-roll}deg)`;
            }
        });

        function floatVal(val) { return parseFloat(val) || 0; }

        let currentThrottle = 0;
        let currentSteering = 0;
        let lastSendTime = 0;

        function sendControl() {
            const now = Date.now();
            if (now - lastSendTime > 40) {
                socket.emit('control', { throttle: currentThrottle, steering: currentSteering });
                lastSendTime = now;
            }
        }

        // Left Joystick (Steering)
        const leftManager = nipplejs.create({
            zone: document.getElementById('left-joystick-zone'),
            mode: 'static', position: { left: '75px', bottom: '75px' },
            color: 'cyan', lockX: true
        });

        leftManager.on('move', (evt, data) => {
            if (data.vector) { currentSteering = Math.round(data.vector.x * 100); sendControl(); }
        });
        leftManager.on('end', () => { currentSteering = 0; socket.emit('control', { throttle: currentThrottle, steering: 0 }); });

        // Right Joystick (Throttle)
        const rightManager = nipplejs.create({
            zone: document.getElementById('right-joystick-zone'),
            mode: 'static', position: { right: '75px', bottom: '75px' },
            color: 'lime', lockY: true
        });

        rightManager.on('move', (evt, data) => {
            if (data.vector) { currentThrottle = Math.round(data.vector.y * 100); sendControl(); }
        });
        rightManager.on('end', () => { currentThrottle = 0; socket.emit('control', { throttle: 0, steering: currentSteering }); });
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
                    if len(parts) == 11:
                        batt, mic, temp, humid, dist, water, light_adc, light_dig, heading, pitch, roll = parts
                        
                        is_day = (light_dig == "0") if light_dig != 'nan' else True

                        socketio.emit('telemetry', {
                            'batt': round(float(batt), 2) if batt != 'nan' else '--',
                            'mic': round(float(mic), 1) if mic != 'nan' else '--',
                            'temp': round(float(temp), 1) if temp != 'nan' else '--',
                            'humid': round(float(humid), 1) if humid != 'nan' else '--',
                            'dist': round(float(dist), 1) if dist != 'nan' else '--',
                            'water': "DETECTED" if water == "1" else "CLEAR",
                            'is_day': is_day,
                            'heading': round(float(heading), 1) if heading != 'nan' else '--',
                            'pitch': round(float(pitch), 1) if pitch != 'nan' else '--',
                            'roll': round(float(roll), 1) if roll != 'nan' else '--'
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
    ser.write(f"CMD:{data['throttle']},{data['steering']}\n".encode('utf-8'))

if __name__ == '__main__':
    threading.Thread(target=notify_tunnel_urls_async, daemon=True).start()
    threading.Thread(target=read_serial_telemetry, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
