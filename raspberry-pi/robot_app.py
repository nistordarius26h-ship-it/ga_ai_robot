import os
import re
import time
import serial
import requests
import threading
from flask import Flask, render_template_string, make_response
from flask_socketio import SocketIO

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "your_bot_token" #get at @BotFather
TELEGRAM_CHAT_ID = "your_user_id" #get at @userinfobot by gmedia

ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured; skipping message")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        response = requests.post(url, json=payload, timeout=8)
        response.raise_for_status()
    except Exception as e:
        print(f"[Telegram Error] {e}")

def notify_tunnel_urls_async():
    control_url, video_url = None, None
    for _ in range(180):  # Retry up to 3 minutes for LTE dongle boot timing
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

    if control_url and video_url:
        msg = f"ROBOT ONLINE\n\nDashboard: {control_url}\n\nCamera WHEP: {video_url}/cam/whep"
        send_telegram_message(msg)
    else:
        missing = []
        if not control_url: missing.append("control tunnel")
        if not video_url: missing.append("video tunnel")
        send_telegram_message("Robot booted, but timeout waiting for: " + ", ".join(missing))

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
        .hud-label { color: #7fd8c8; }
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

        /* Speed Mode Switch Button */
        #speed-btn {
            background: rgba(0, 0, 0, 0.85);
            border: 1.5px solid #00ffcc;
            color: #00ffcc;
            font-family: monospace;
            font-size: 12px;
            font-weight: bold;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(0,0,0,0.9);
            transition: background 0.2s, color 0.2s;
        }
        #speed-btn:active {
            background: #00ffcc;
            color: #000;
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

        /* --- Linear slider controls --- */
        #steering-track {
            position: absolute; bottom: 20px; left: 20px;
            width: 240px; height: 50px; z-index: 10;
            background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(0, 255, 204, 0.4);
            border-radius: 4px;
        }
        #steering-center-mark {
            position: absolute; left: 50%; top: 0; width: 1px; height: 100%;
            background: rgba(0, 255, 204, 0.4);
        }
        #steering-thumb {
            position: absolute; top: 3px; left: 50%; width: 44px; height: 44px;
            margin-left: -22px;
            background: rgba(0, 255, 204, 0.85); border-radius: 3px;
        }

        #throttle-track {
            position: absolute; 
            bottom: 20px;
            right: 20px;
            width: 50px; 
            height: 50vh;
            max-height: 260px;
            z-index: 10;
            background: rgba(0, 0, 0, 0.6); 
            border: 1px solid rgba(0, 255, 204, 0.4);
            border-radius: 4px;
        }
        #throttle-center-mark {
            position: absolute; top: 50%; left: 0; height: 1px; width: 100%;
            background: rgba(0, 255, 204, 0.4);
        }
        #throttle-thumb {
            position: absolute; left: 3px; top: 50%; width: 44px; height: 44px;
            margin-top: -22px;
            background: rgba(0, 255, 204, 0.85); border-radius: 3px;
        }

        .slider-label {
            position: absolute; color: rgba(0, 255, 204, 0.6); font-size: 10px;
            letter-spacing: 1px;
        }

        @media (orientation: landscape) and (max-height: 500px) {
            .widget-box { width: 75px; height: 75px; }
            #throttle-track { max-height: 180px; }
        }
    </style>
</head>
<body>
    <video id="video" autoplay playsinline muted></video>

    <!-- Top Left HUD -->
    <div id="hud">
        <span class="hud-label">BATT</span> <span id="batt" class="hud-val">--</span> V<br>
        <span class="hud-label">MIC</span>  <span id="mic" class="hud-val">--</span> dB<br>
        <span class="hud-label">DIST</span> <span id="dist" class="hud-val">--</span> cm<br>
        <span class="hud-label">WATER</span> <span id="water" class="hud-val">--</span><br>
        <span class="hud-label">TEMP</span> <span id="temp" class="hud-val">--</span> C<br>
        <span class="hud-label">HUMID</span> <span id="humid" class="hud-val">--</span> %<br>
        <span class="hud-label">LIGHT</span> <span id="light-mode" class="hud-val">--</span>
    </div>

    <!-- Top Right Visual Instruments -->
    <div id="top-right-instruments">
        <button id="speed-btn" onclick="toggleSpeedMode()">SPD: HIGH (100%)</button>

        <div class="widget-box">
            <div class="horizon-crosshair"></div>
            <div id="horizon-disc">
                <div id="horizon-pitch-roll">
                    <div id="horizon-sky"></div>
                    <div id="horizon-ground"></div>
                    <div id="horizon-line"></div>
                </div>
            </div>
            <div id="tilt-readout"><span id="pitch-val">0</span>DEG / <span id="roll-val">0</span>DEG</div>
        </div>

        <div class="widget-box">
            <div id="compass-dial">
                <div class="compass-mark">N</div>
            </div>
            <div id="compass-readout">
                <span id="heading-deg">--</span>DEG<br>
                <span id="heading-card" style="color:#00ffcc;">--</span>
            </div>
        </div>
    </div>

    <!-- Linear slider controls -->
    <div id="steering-track">
        <div class="slider-label" style="top:-16px; left:0;">STEER L</div>
        <div class="slider-label" style="top:-16px; right:0;">STEER R</div>
        <div id="steering-center-mark"></div>
        <div id="steering-thumb"></div>
    </div>

    <div id="throttle-track">
        <div class="slider-label" style="top:-16px; left:0;">FWD</div>
        <div class="slider-label" style="bottom:-16px; left:0;">REV</div>
        <div id="throttle-center-mark"></div>
        <div id="throttle-thumb"></div>
    </div>
    <div id="debug-control" style="position:fixed; bottom:10px; left:50%; transform:translateX(-50%); color:#0f0; background:rgba(0,0,0,0.6); padding:4px 10px; font-family:monospace; font-size:13px; z-index:9999;">sent: throttle=0 steering=0</div>
    <div id="conn-status" style="position:fixed; top:60px; left:50%; transform:translateX(-50%); color:#0f0; background:rgba(0,0,0,0.6); padding:4px 10px; font-family:monospace; font-size:13px; z-index:9999;">connecting...</div>

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

        let disconnectCount = 0;
        socket.on('connect', () => {
            const el = document.getElementById('conn-status');
            if (el) el.innerText = `connected (reconnects: ${disconnectCount})`;
        });
        socket.on('disconnect', (reason) => {
            disconnectCount++;
            const el = document.getElementById('conn-status');
            if (el) el.innerText = `DISCONNECTED (${reason}) -- reconnects so far: ${disconnectCount}`;
        });

        socket.on('telemetry', (d) => {
            document.getElementById('batt').innerText = d.batt;
            document.getElementById('mic').innerText = d.mic;
            document.getElementById('dist').innerText = d.dist;

            const waterEl = document.getElementById('water');
            if (d.water === "DETECTED") {
                waterEl.innerText = "ALARM"; waterEl.className = "alert";
            } else {
                waterEl.innerText = "CLEAR"; waterEl.className = "hud-val";
            }

            document.getElementById('temp').innerText = d.temp;
            document.getElementById('humid').innerText = d.humid;

            document.getElementById('light-mode').innerText = d.is_day ? "DAY" : "NIGHT";

            if (d.heading !== '--') {
                const headingVal = floatVal(d.heading);
                document.getElementById('heading-deg').innerText = Math.round(headingVal);
                document.getElementById('heading-card').innerText = getCardinalDirection(headingVal);
                document.getElementById('compass-dial').style.transform = `rotate(${-headingVal}deg)`;
            }

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

        let rawThrottle = 0;
        let rawSteering = 0;
        let speedMultiplier = 1.0; // Default HIGH (100%)
        let lastSendTime = 0;

        function toggleSpeedMode() {
            const btn = document.getElementById('speed-btn');
            if (speedMultiplier === 1.0) {
                speedMultiplier = 0.25;
                btn.innerText = "SPD: LOW (25%)";
            } else if (speedMultiplier === 0.25) {
                speedMultiplier = 0.50;
                btn.innerText = "SPD: MED (50%)";
            } else {
                speedMultiplier = 1.0;
                btn.innerText = "SPD: HIGH (100%)";
            }
            sendControl();
        }

        function sendControl() {
            const now = Date.now();
            if (now - lastSendTime > 40) {
                // Scale BOTH throttle and steering with the selected mode.
                // speedLimit is sent separately so the ESP32 can treat
                // +/-25 as full steering lock in LOW and +/-50 as full
                // lock in MED while still keeping every wheel under the cap.
                const cappedThrottle = Math.round(rawThrottle * speedMultiplier);
                const cappedSteering = Math.round(rawSteering * speedMultiplier);
                const speedLimit = Math.round(speedMultiplier * 100);
                
                socket.emit('control', { throttle: cappedThrottle, steering: cappedSteering, speed_limit: speedLimit });
                lastSendTime = now;
                const dbgEl = document.getElementById('debug-control');
                if (dbgEl) dbgEl.innerText = `sent: throttle=${cappedThrottle} steering=${cappedSteering} limit=${speedLimit}`;
            }
        }

        setInterval(sendControl, 100);

        function setupSlider(trackId, thumbId, axis, invert, onChange) {
            const track = document.getElementById(trackId);
            const thumb = document.getElementById(thumbId);
            let activeTouchId = null;
            let mouseDragging = false;

            function trackSize() {
                return axis === 'x' ? track.clientWidth : track.clientHeight;
            }
            function thumbSize() {
                return axis === 'x' ? thumb.offsetWidth : thumb.offsetHeight;
            }

            function setThumbPosition(fraction) {
                const usablePx = (trackSize() - thumbSize()) / 2;
                const offsetPx = fraction * usablePx;
                if (axis === 'x') {
                    thumb.style.left = `calc(50% + ${offsetPx}px)`;
                    thumb.style.marginLeft = `${-thumbSize()/2}px`;
                } else {
                    thumb.style.top = `calc(50% + ${offsetPx}px)`;
                    thumb.style.marginTop = `${-thumbSize()/2}px`;
                }
            }

            function valueFromEvent(clientX, clientY) {
                const rect = track.getBoundingClientRect();
                let fraction;
                if (axis === 'x') {
                    const centerPx = rect.left + rect.width / 2;
                    const usablePx = (rect.width - thumbSize()) / 2;
                    fraction = (clientX - centerPx) / usablePx;
                } else {
                    const centerPx = rect.top + rect.height / 2;
                    const usablePx = (rect.height - thumbSize()) / 2;
                    fraction = (clientY - centerPx) / usablePx;
                }
                fraction = Math.max(-1, Math.min(1, fraction));
                if (invert) fraction = -fraction;
                return fraction;
            }

            function handleMove(clientX, clientY) {
                const fraction = valueFromEvent(clientX, clientY);
                setThumbPosition(invert ? -fraction : fraction);
                const value = Math.max(-100, Math.min(100, Math.round(fraction * 100)));
                onChange(value);
                sendControl();
            }

            function handleEnd() {
                activeTouchId = null;
                mouseDragging = false;
                setThumbPosition(0);
                onChange(0);
                sendControl();
            }

            track.addEventListener('touchstart', (e) => {
                const touch = e.changedTouches[0];
                activeTouchId = touch.identifier;
                handleMove(touch.clientX, touch.clientY);
                e.preventDefault();
            }, {passive: false});

            track.addEventListener('touchmove', (e) => {
                if (activeTouchId === null) return;
                for (let i = 0; i < e.touches.length; i++) {
                    if (e.touches[i].identifier === activeTouchId) {
                        handleMove(e.touches[i].clientX, e.touches[i].clientY);
                        break;
                    }
                }
                e.preventDefault();
            }, {passive: false});

            function touchEndHandler(e) {
                for (let i = 0; i < e.changedTouches.length; i++) {
                    if (e.changedTouches[i].identifier === activeTouchId) {
                        handleEnd();
                        break;
                    }
                }
            }
            track.addEventListener('touchend', touchEndHandler);
            track.addEventListener('touchcancel', touchEndHandler);

            track.addEventListener('mousedown', (e) => { mouseDragging = true; handleMove(e.clientX, e.clientY); });
            window.addEventListener('mousemove', (e) => { if (mouseDragging) handleMove(e.clientX, e.clientY); });
            window.addEventListener('mouseup', () => { if (mouseDragging) handleEnd(); });
        }

        setupSlider('steering-track', 'steering-thumb', 'x', false, (val) => { rawSteering = val; });
        setupSlider('throttle-track', 'throttle-thumb', 'y', true, (val) => { rawThrottle = val; });
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
        except Exception as e:
            print(f"[telemetry error] {e} | raw line: {line if 'line' in dir() else '(no line read)'}")

@app.route('/')
def index():
    resp = make_response(render_template_string(HTML_PAGE))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/get_stream_url')
def get_stream_url():
    return {'url': get_video_stream_url()}

last_throttle = 0
last_steering = 0
last_speed_limit = 100
control_lock = threading.Lock()

def serial_heartbeat_loop():
    while True:
        with control_lock:
            t, s, limit = last_throttle, last_steering, last_speed_limit
        try:
            ser.write(f"CMD:{t},{s},{limit}\n".encode('utf-8'))
        except Exception as e:
            print(f"[heartbeat] serial write error: {e}")
        time.sleep(0.1)

@socketio.on('control')
def handle_control(data):
    global last_throttle, last_steering
    try:
        throttle = int(data.get('throttle', 0))
        steering = int(data.get('steering', 0))
    except (TypeError, ValueError):
        print(f"[control] invalid payload: {data}")
        return

    throttle = max(-100, min(100, throttle))
    steering = max(-100, min(100, steering))

    with control_lock:
        last_throttle = throttle
        last_steering = steering
    print(f"[control] browser sent: throttle={throttle} steering={steering}")

@socketio.on('disconnect')
def handle_disconnect():
    global last_throttle, last_steering
    print("[control] client disconnected -- zeroing throttle/steering")
    with control_lock:
        last_throttle = 0
        last_steering = 0

if __name__ == '__main__':
    threading.Thread(target=notify_tunnel_urls_async, daemon=True).start()
    threading.Thread(target=read_serial_telemetry, daemon=True).start()
    threading.Thread(target=serial_heartbeat_loop, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
