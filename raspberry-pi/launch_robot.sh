#!/bin/bash
set -Eeuo pipefail

ROBOT_HOME="${ROBOT_HOME:-/home/raspforex}"
MEDIAMTX_BIN="${MEDIAMTX_BIN:-$ROBOT_HOME/mediamtx}"
MEDIAMTX_CONFIG="${MEDIAMTX_CONFIG:-$ROBOT_HOME/mediamtx.yml}"
ROBOT_APP="${ROBOT_APP:-$ROBOT_HOME/robot_app.py}"

VIDEO_LOG=/tmp/video_tunnel.log
CONTROL_LOG=/tmp/control_tunnel.log
MEDIAMTX_LOG=/tmp/mediamtx.log

MEDIAMTX_PID=""
VIDEO_TUNNEL_PID=""
CONTROL_TUNNEL_PID=""

cleanup() {
    echo "Stopping robot services..."
    [[ -n "$CONTROL_TUNNEL_PID" ]] && kill "$CONTROL_TUNNEL_PID" 2>/dev/null || true
    [[ -n "$VIDEO_TUNNEL_PID" ]] && kill "$VIDEO_TUNNEL_PID" 2>/dev/null || true
    [[ -n "$MEDIAMTX_PID" ]] && kill "$MEDIAMTX_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait_for_internet() {
    echo "Waiting for real Internet connectivity (important for LTE dongle boot)..."
    until curl -fsS --max-time 5 https://www.cloudflare.com/cdn-cgi/trace >/dev/null 2>&1; do
        echo "Internet not ready yet; retrying in 3 s..."
        sleep 3
    done
    echo "Internet is reachable."
}

wait_for_port() {
    local port="$1"
    local attempts="${2:-30}"
    for ((i=1; i<=attempts; i++)); do
        if python3 - "$port" <<'PY' >/dev/null 2>&1
import socket, sys
s = socket.socket()
s.settimeout(0.2)
try:
    s.connect(("127.0.0.1", int(sys.argv[1])))
finally:
    s.close()
PY
        then
            return 0
        fi
        sleep 1
    done
    return 1
}

rm -f "$VIDEO_LOG" "$CONTROL_LOG" "$MEDIAMTX_LOG"
wait_for_internet

echo "1. Starting MediaMTX..."
"$MEDIAMTX_BIN" "$MEDIAMTX_CONFIG" > "$MEDIAMTX_LOG" 2>&1 &
MEDIAMTX_PID=$!

if ! wait_for_port 8889 30; then
    echo "ERROR: MediaMTX did not open port 8889."
    tail -n 100 "$MEDIAMTX_LOG" || true
    exit 1
fi

echo "2. Starting Video Tunnel (Port 8889)..."
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8889 > "$VIDEO_LOG" 2>&1 &
VIDEO_TUNNEL_PID=$!

echo "3. Starting Control Tunnel (Port 5000)..."
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:5000 > "$CONTROL_LOG" 2>&1 &
CONTROL_TUNNEL_PID=$!

echo "4. Starting Control Server & Telegram Notifier..."
exec python3 "$ROBOT_APP"
