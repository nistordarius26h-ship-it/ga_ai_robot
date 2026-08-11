# Cloudflare Tunnel & Telegram Bot: Global Remote Access

This is the layer that makes the robot reachable **from anywhere in the world over 4G**, without port forwarding, a static IP, or a VPN — and that notifies you automatically the moment it's ready to control.

## Why Cloudflare Tunnel instead of port forwarding

The robot is behind a 4G cellular connection, which almost always sits behind carrier-grade NAT — there's no public IP to forward a port to, even if you wanted to. **Cloudflare Tunnel** (`cloudflared`) solves this by having the Pi open an *outbound* connection to Cloudflare's edge, which then exposes that local service through a public URL. No inbound firewall rules, no router configuration, works identically on any network the 4G modem connects to.

## Quick Tunnels vs. named tunnels

This project uses **Cloudflare Quick Tunnels** — the simplest mode, requiring no Cloudflare account or DNS setup:

```bash
cloudflared tunnel --url http://localhost:8889
```

This prints (and, in this setup, logs to a file) a random `https://<random-words>.trycloudflare.com` URL that proxies straight to `localhost:8889` on the Pi. Two independent quick tunnels are started per boot — one for video (port `8889`, MediaMTX), one for the control dashboard (port `5000`, Flask).

**Trade-off:** quick tunnel URLs are randomly generated and change every restart — which is exactly why the Telegram notifier step below exists, so you always know the current URL without SSH-ing in.

**If you want a stable, permanent URL instead:** create a named tunnel tied to a domain you control in Cloudflare Zero Trust (`cloudflared tunnel create <name>`, `cloudflared tunnel route dns <name> <hostname>`, then run with `cloudflared tunnel run <name>` against a config file mapping hostnames to local ports). This is more setup but avoids the "check Telegram for the URL" step entirely — worth doing if this becomes a permanent build rather than a field-test one.

## Installing cloudflared on the Pi

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared.deb
cloudflared --version
```
(Use the `arm` build instead of `arm64` if running 32-bit Raspberry Pi OS.)

## How the tunnels are launched here

From `launch_robot.sh`:

```bash
echo "2. Starting Video Tunnel (Port 8889)..."
cloudflared tunnel --url http://localhost:8889 > /tmp/video_tunnel.log 2>&1 &
sleep 2

echo "3. Starting Control Tunnel (Port 5000)..."
cloudflared tunnel --url http://localhost:5000 > /tmp/control_tunnel.log 2>&1 &
sleep 2
```

Both are launched in the background (`&`) with their stdout/stderr redirected to log files — those log files are the only place the assigned public URLs actually appear, which is what the Telegram notifier parses.

## Telegram bot setup

### 1. Create the bot

1. Message **[@BotFather](https://t.me/BotFather)** on Telegram.
2. Send `/newbot`, follow the prompts (choose a name and a unique username ending in `bot`).
3. BotFather replies with an **API token** — this is `TELEGRAM_BOT_TOKEN` in `robot_app.py`.

### 2. Get your chat ID

1. Message **[@userinfobot](https://t.me/userinfobot)** — it replies with your numeric Telegram user ID.
2. This becomes `TELEGRAM_CHAT_ID` in `robot_app.py`.
3. **Important:** send `/start` to your new bot at least once from that account first — Telegram bots can't message a user who has never initiated a conversation with them.

### 3. Configure the app

```python
TELEGRAM_BOT_TOKEN = "123456789:AAExampleTokenFromBotFather"
TELEGRAM_CHAT_ID   = "987654321"
```

## How the notification flow works

`notify_tunnel_urls_async()` in `robot_app.py` runs as a background thread started at app launch:

1. Polls `/tmp/control_tunnel.log` and `/tmp/video_tunnel.log` once per second, for up to 30 seconds.
2. Extracts the `https://*.trycloudflare.com` URL from each log with a regex as soon as `cloudflared` writes it out.
3. Once both URLs are found (or the 30-second window expires), sends a single Telegram message via the Bot API:

```python
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=5)
```

The message includes the dashboard link and the direct WHEP video URL:

```
🚀 ROBOT ONLINE & READY!
📱 Dashboard: https://xxxx.trycloudflare.com
📹 Camera WHEP: https://yyyy.trycloudflare.com/cam/whep
```

If no control URL is found within the 30-second window, a fallback warning message is sent instead — so you always get *some* signal on boot, even in a failure case (e.g. no internet yet, `cloudflared` crashed).

## Security notes

- Quick Tunnel URLs are unguessable but **not authenticated** — anyone with the link can open the dashboard and drive the robot. For a field-test/hobby project this is an accepted trade-off in exchange for zero-config setup; for anything more permanent, put the Flask app behind [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) (which layers login-based auth in front of a named tunnel) or add your own auth to the Flask routes.
- Never commit your real `TELEGRAM_BOT_TOKEN` to a public repo — keep the placeholder in version control and load real credentials from an environment variable or a gitignored config file in practice.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| No URL ever appears in the log file | `cloudflared` not installed correctly, or no internet on the Pi at boot |
| Telegram message never arrives | Bot token/chat ID wrong, or you never sent `/start` to the bot |
| Dashboard loads but video doesn't | Video tunnel URL and control tunnel URL got mixed up, or MediaMTX wasn't ready before the tunnel came up |
