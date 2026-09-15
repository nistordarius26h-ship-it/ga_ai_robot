# Cloudflare Tunnel, Telegram & 4G Remote Access

The Raspberry Pi uses outbound Cloudflare tunnels so control works behind LTE carrier-grade NAT without conventional inbound port forwarding.

## Services

```text
localhost:5000 -> Cloudflare Quick Tunnel -> dashboard/control
localhost:8889 -> Cloudflare Quick Tunnel -> MediaMTX WHEP signaling
```

Quick Tunnel URLs change after restart. `robot_app.py` extracts the URLs from `/tmp/control_tunnel.log` and `/tmp/video_tunnel.log`, then sends them through Telegram.

## LTE boot race that was fixed

`network-online.target` is not enough to guarantee that a USB cellular modem has registered, received routing and DNS, and can reach the Internet. The launcher therefore performs a real HTTPS connectivity check before starting `cloudflared`.

The Telegram URL poll window is also 180 seconds instead of the original 30 seconds.

## Credentials

`robot_app.py` now reads:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

from the service environment. Put real values in `/etc/ga-ai-robot/robot.env`; never commit them.

If a token has ever been uploaded/shared in source code, regenerate it before deploying this version.

## Why the page can work while the camera fails

Cloudflare carries the HTTPS control page and WHEP signaling. WebRTC media uses ICE separately. A cellular carrier can place the robot behind CGNAT/symmetric NAT where STUN alone cannot create a usable direct media path.

The robust solution is a TURN relay. Add TURN/TURNS entries to the deployed Pi's MediaMTX configuration. A VPS running coturn or a reputable TURN provider are both valid approaches.

## Security

Quick Tunnel URLs are temporary but should not be treated as authentication. For a more permanent robot, move to a named tunnel and add access control before exposing the driving interface broadly.
