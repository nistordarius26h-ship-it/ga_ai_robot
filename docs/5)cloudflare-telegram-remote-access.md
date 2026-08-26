# Cloudflare Tunnel & Telegram Bot: Remote Access

Makes the robot reachable over 4G with no port forwarding, static IP, or VPN, and notifies you the moment it's ready.

## Why Cloudflare Tunnel

The robot sits behind carrier-grade NAT on 4G — no public IP to forward a port to. `cloudflared` opens an outbound connection from the Pi to Cloudflare's edge, which exposes that local service through a public URL. No inbound firewall rules, no router config.

## Quick tunnels vs. named tunnels

This project uses Cloudflare Quick Tunnels — no account or DNS setup needed:

```bash
cloudflared tunnel --url http://localhost:8889
```

Prints (and here, logs to file) a `https://<random-words>.trycloudflare.com` URL proxying to `localhost:8889`. Two quick tunnels start per boot: video (`8889`, MediaMTX) and control (`5000`, Flask).

Quick tunnel URLs are random and change every restart, which is why the Telegram notifier exists.

For a stable URL: create a named tunnel against a domain in Cloudflare Zero Trust (`cloudflared tunnel create <name>`, `cloudflared tunnel route dns <name> <hostname>`, run with `cloudflared tunnel run <name>` against a config mapping hostnames to local ports). More setup, but removes the "check Telegram for the URL" step — worth it for a permanent build.

## Installing cloudflared on the Pi

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared.deb
cloudflared --version
```
Use the `arm` build instead of `arm64` on 32-bit Raspberry Pi OS.

## Launch (from `launch_robot.sh`)

```bash
echo "2. Starting Video Tunnel (Port 8889)..."
cloudflared tunnel --url http://localhost:8889 > /tmp/video_tunnel.log 2>&1 &
sleep 2

echo "3. Starting Control Tunnel (Port 5000)..."
cloudflared tunnel --url http://localhost:5000 > /tmp/control_tunnel.log 2>&1 &
sleep 2
```

Both run in the background with stdout/stderr to log files — those logs are where the Telegram notifier reads the assigned URLs from.

## Telegram bot setup

**1. Create the bot**
1. Message [@BotFather](https://t.me/BotFather).
2. `/newbot`, choose a name and a username ending in `bot`.
3. BotFather returns an API token → `TELEGRAM_BOT_TOKEN` in `robot_app.py`.

**2. Get your chat ID**
1. Message [@userinfobot](https://t.me/userinfobot) → returns your numeric Telegram user ID → `TELEGRAM_CHAT_ID`.
2. Send `/start` to your new bot at least once first — bots can't message a user who hasn't started a conversation with them.

**3. Configure**
```python
TELEGRAM_BOT_TOKEN = "123456789:AAExampleTokenFromBotFather"
TELEGRAM_CHAT_ID   = "987654321"
```

## Notification flow

`notify_tunnel_urls_async()` in `robot_app.py`, background thread at app launch:

1. Polls `/tmp/control_tunnel.log` and `/tmp/video_tunnel.log` once/sec for up to 30s.
2. Extracts the `https://*.trycloudflare.com` URL from each log by regex as soon as `cloudflared` writes it.
3. Once both are found (or the 30s window expires), sends one Telegram message:

```python
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=5)
```

Message includes both links:
```
ROBOT ONLINE
Dashboard: https://xxxx.trycloudflare.com
Camera WHEP: https://yyyy.trycloudflare.com/cam/whep
```

If no control URL is found in the 30s window, a fallback warning is sent instead — always some signal on boot, even on failure (no internet yet, `cloudflared` crashed).

## Security notes

- Quick Tunnel URLs are unguessable but not authenticated — anyone with the link can drive the robot. Acceptable for a hobby/field-test build; for anything more permanent, put Flask behind [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) on a named tunnel, or add auth to the Flask routes directly.
- Don't commit the real `TELEGRAM_BOT_TOKEN` to a public repo — keep the placeholder in version control, load real credentials from an env var or gitignored config in practice.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| No URL ever appears in the log | `cloudflared` not installed correctly, or no internet on the Pi at boot |
| Telegram message never arrives | Wrong bot token/chat ID, or never sent `/start` to the bot |
| Dashboard loads but video doesn't | Video/control tunnel URLs mixed up, or MediaMTX wasn't ready before the tunnel came up |
