# Hermes Agent — Self-Hosted Admin Server

Reimplementation of the [hermes-agent-template](https://github.com/praveen-ks-2001/hermes-agent-template) with full code ownership and security hardening.

## What This Is

A Dockerized admin server that wraps [Hermes Agent](https://github.com/NousResearch/hermes-agent) (by Nous Research) with:

- **Web-based admin dashboard** — configure providers, channels, tools, and manage the gateway
- **Gateway management** — start, stop, restart the Hermes gateway from the browser
- **Live logs** — streaming gateway log viewer
- **User pairing** — approve or deny users who message your bot
- **Cookie-based auth** — HMAC-signed sessions
- **Security hardening** — non-root container, rate limiting, secret masking, input validation

## Quick Start (Local)

```bash
docker build -t hermes-agent .
docker run --rm -it \
  -p 8080:8080 \
  -e PORT=8080 \
  -e ADMIN_PASSWORD=changeme \
  -v hermes-data:/data \
  hermes-agent
```

Open `http://localhost:8080` and log in with `admin` / `changeme`.

## Deploy to Railway

1. Click **Deploy** (Railway button coming soon)
2. Set `ADMIN_PASSWORD`
3. Attach a volume mounted at `/data`
4. Open your app URL

## Architecture

```
Railway Container
├── Python Admin Server (Starlette + Uvicorn)
│   ├── /            → Admin dashboard (cookie auth)
│   ├── /health      → Health check (no auth)
│   └── /api/*       → Config, status, logs, gateway, pairing
└── hermes gateway   → Managed as async subprocess
```

## Credits

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com/)
- Original template by [praveen-ks-2001](https://github.com/praveen-ks-2001/hermes-agent-template)

## License

MIT
