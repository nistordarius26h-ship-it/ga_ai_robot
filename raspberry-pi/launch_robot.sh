#!/bin/bash

echo "Cleaning up old processes and logs..."
pkill -9 -f cloudflared
pkill -9 -f robot_app.py
pkill -9 -f mediamtx
rm -f /tmp/control_tunnel.log /tmp/video_tunnel.log

echo "1. Starting MediaMTX..."
/home/raspforex/mediamtx > /tmp/mediamtx.log 2>&1 &
sleep 2

echo "2. Starting Video Tunnel (Port 8889)..."
cloudflared tunnel --url http://localhost:8889 > /tmp/video_tunnel.log 2>&1 &
sleep 2

echo "3. Starting Control Tunnel (Port 5000)..."
cloudflared tunnel --url http://localhost:5000 > /tmp/control_tunnel.log 2>&1 &
sleep 2

echo "4. Starting Control Server & Telegram Notifier..."
# Running python3 in foreground so systemd can track the main process
python3 /home/raspforex/robot_app.py
