"""
Hermes Agent — Self-hosted admin server.

Responsibilities:
  - Admin UI / setup wizard at /setup (Starlette + Jinja2, cookie-auth guarded)
  - Management API at /api/* (config, status, logs, gateway, pairing)
  - Reverse proxy at / and /* → native Hermes dashboard (hermes_cli/web_server, on 127.0.0.1:9119)
  - Managed subprocesses: `hermes gateway` (agent) and `hermes dashboard` (native UI)
  - Cookie-based session auth at /login (HMAC-signed, 7-day expiry, httponly)

Auth model: Cookie auth instead of Basic Auth because the Hermes React SPA's
plain fetch() calls do not reliably include basic-auth creds across browsers.
Cookies auto-include on every same-origin request, so both the setup UI and the
proxied dashboard work with a single login. The cookie signing secret is
regenerated on every process start, so any ADMIN_PASSWORD change on Railway
(which triggers a redeploy) invalidates all existing sessions.

First-visit behavior: if no provider+model config exists, GET / redirects to /setup.
Once configured, / proxies to the Hermes dashboard. A small "← Setup" widget is
injected into every proxied HTML response so users can always return to the wizard.
"""

import asyncio
import hashlib as _hashlib
import hmac as _hmac
import json
import os
import re
import secrets
import signal
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote as _url_quote, urlparse as _urlparse

import httpx
import websockets
import websockets.exceptions
import yaml
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

HERMES_HOME = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
ENV_FILE = Path(HERMES_HOME) / ".env"
PAIRING_DIR = Path(HERMES_HOME) / "pairing"
PAIRING_TTL = 3600

# Native Hermes dashboard — runs on loopback, fronted by our reverse proxy.
HERMES_DASHBOARD_HOST = "127.0.0.1"
HERMES_DASHBOARD_PORT = int(os.environ.get("HERMES_DASHBOARD_PORT", "9119"))
HERMES_DASHBOARD_URL = f"http://{HERMES_DASHBOARD_HOST}:{HERMES_DASHBOARD_PORT}"

# Hop-by-hop headers to strip when proxying (httpx sets host, recomputes transfer-encoding).
HOP_BY_HOP = {"host", "transfer-encoding"}

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    print(f"[server] Admin credentials — username: {ADMIN_USERNAME}  password: {ADMIN_PASSWORD}", flush=True)
else:
    print(f"[server] Admin username: {ADMIN_USERNAME}", flush=True)

# ── Env var registry ──────────────────────────────────────────────────────────
ENV_VARS = [
    ("LLM_MODEL",               "Model",                    "model",     False),
    ("OPENROUTER_API_KEY",       "OpenRouter",               "provider",  True),
    ("DEEPSEEK_API_KEY",         "DeepSeek",                 "provider",  True),
    ("DASHSCOPE_API_KEY",        "Qwen Cloud (DashScope)",   "provider",  True),
    ("GLM_API_KEY",              "GLM / Z.AI",               "provider",  True),
    ("KIMI_API_KEY",             "Kimi",                     "provider",  True),
    ("MINIMAX_API_KEY",          "MiniMax",                  "provider",  True),
    ("HF_TOKEN",                 "Hugging Face",             "provider",  True),
    ("NVIDIA_API_KEY",           "NVIDIA NIM",               "provider",  True),
    ("ARCEEAI_API_KEY",          "Arcee AI",                 "provider",  True),
    ("STEPFUN_API_KEY",          "Step Plan",                "provider",  True),
    ("AI_GATEWAY_API_KEY",       "Vercel AI Gateway",        "provider",  True),
    ("GEMINI_API_KEY",           "Google AI Studio",         "provider",  True),
    ("NOVITA_API_KEY",           "NovitaAI",                 "provider",  True),
    ("FIREWORKS_API_KEY",        "Fireworks AI",             "provider",  True),
    ("ANTHROPIC_API_KEY",        "Anthropic (Claude)",       "provider",  True),
    ("XAI_API_KEY",              "xAI",                      "provider",  True),
    ("AWS_ACCESS_KEY_ID",        "AWS Access Key ID",        "bedrock",   True),
    ("AWS_SECRET_ACCESS_KEY",    "AWS Secret Access Key",    "bedrock",   True),
    ("AWS_DEFAULT_REGION",       "AWS Region",               "bedrock",   False),
    ("COPILOT_GITHUB_TOKEN",     "GitHub Copilot",           "provider",  True),
    ("GMI_API_KEY",              "GMI Cloud",                "provider",  True),
    ("OPENCODE_ZEN_API_KEY",     "OpenCode Zen",             "provider",  True),
    ("OPENCODE_GO_API_KEY",      "OpenCode Go",              "provider",  True),
    ("KILOCODE_API_KEY",         "Kilo Code",                "provider",  True),
    ("OLLAMA_API_KEY",           "Ollama Cloud",             "provider",  True),
    ("AZURE_FOUNDRY_API_KEY",    "Azure Foundry key",        "provider",  True),
    ("AZURE_FOUNDRY_BASE_URL",   "Azure Foundry URL",        "azure",     False),
    ("CUSTOM_PROVIDER_API_KEY",  "Custom Provider key",      "provider",  True),
    ("CUSTOM_PROVIDER_BASE_URL", "Custom Provider base URL", "custom",    False),
    ("CUSTOM_PROVIDER_NAME",     "Custom Provider name",     "custom",    False),
    ("PARALLEL_API_KEY",         "Parallel (search)",        "tool",      True),
    ("FIRECRAWL_API_KEY",        "Firecrawl (scrape)",       "tool",      True),
    ("TAVILY_API_KEY",           "Tavily (search)",          "tool",      True),
    ("FAL_KEY",                  "FAL (image gen)",          "tool",      True),
    ("BROWSERBASE_API_KEY",      "Browserbase key",          "tool",      True),
    ("BROWSERBASE_PROJECT_ID",   "Browserbase project",      "tool",      False),
    ("GITHUB_TOKEN",             "GitHub token",             "tool",      True),
    ("VOICE_TOOLS_OPENAI_KEY",   "OpenAI (voice/TTS)",       "tool",      True),
    ("HONCHO_API_KEY",           "Honcho (memory)",          "tool",      True),
    ("TELEGRAM_BOT_TOKEN",       "Bot Token",                "telegram",  True),
    ("TELEGRAM_ALLOWED_USERS",   "Allowed User IDs",         "telegram",  False),
    ("DISCORD_BOT_TOKEN",        "Bot Token",                "discord",   True),
    ("DISCORD_ALLOWED_USERS",    "Allowed User IDs",         "discord",   False),
    ("SLACK_BOT_TOKEN",          "Bot Token (xoxb-...)",     "slack",     True),
    ("SLACK_APP_TOKEN",          "App Token (xapp-...)",     "slack",     True),
    ("WHATSAPP_ENABLED",         "Enable WhatsApp",          "whatsapp",  False),
    ("EMAIL_ADDRESS",            "Email Address",            "email",     False),
    ("EMAIL_PASSWORD",           "Email Password",           "email",     True),
    ("EMAIL_IMAP_HOST",          "IMAP Host",                "email",     False),
    ("EMAIL_SMTP_HOST",          "SMTP Host",                "email",     False),
    ("MATTERMOST_URL",           "Server URL",               "mattermost",False),
    ("MATTERMOST_TOKEN",         "Bot Token",                "mattermost",True),
    ("MATRIX_HOMESERVER",        "Homeserver URL",           "matrix",    False),
    ("MATRIX_ACCESS_TOKEN",      "Access Token",             "matrix",    True),
    ("MATRIX_USER_ID",           "User ID",                  "matrix",    False),
    ("GATEWAY_ALLOW_ALL_USERS",  "Allow all users",          "gateway",   False),
    ("ADMIN_USERNAME",           "Admin username",           "admin",     False),
    ("ADMIN_PASSWORD",           "Admin password",           "admin",     True),
]

SECRET_KEYS  = {k for k, _, _, s in ENV_VARS if s}
PROVIDER_KEYS = [k for k, _, c, _ in ENV_VARS if c == "provider"]
CHANNEL_MAP  = {
    "Telegram":    "TELEGRAM_BOT_TOKEN",
    "Discord":     "DISCORD_BOT_TOKEN",
    "Slack":       "SLACK_BOT_TOKEN",
    "WhatsApp":    "WHATSAPP_ENABLED",
    "Email":       "EMAIL_ADDRESS",
    "Mattermost":  "MATTERMOST_TOKEN",
    "Matrix":      "MATRIX_ACCESS_TOKEN",
}


# ── .env helpers ──────────────────────────────────────────────────────────────
def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        out[k.strip()] = v
    return out


def write_config_yaml(data: dict[str, str]) -> None:
    """Write config.yaml — deep-merge template defaults with any existing user/cron-managed sections.

    Preserves unknown top-level keys (e.g. mcp_servers) so user-managed config
    survives across container restarts.
    """
    model = data.get("LLM_MODEL", "")
    config_path = Path(HERMES_HOME) / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        try:
            with config_path.open() as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                existing = loaded
        except (yaml.YAMLError, OSError):
            existing = {}

    merged = dict(existing)

    # Deployment-managed keys (always authoritative — reflect runtime env).
    merged_model = dict(merged.get("model") if isinstance(merged.get("model"), dict) else {})
    merged_model["default"] = model
    if any(data.get(k) for k in PROVIDER_KEYS):
        merged_model["provider"] = "auto"
    merged["model"] = merged_model

    merged_terminal = dict(merged.get("terminal") if isinstance(merged.get("terminal"), dict) else {})
    merged_terminal["backend"] = "local"
    merged_terminal["timeout"] = 60
    merged_terminal["cwd"] = "/tmp"
    merged["terminal"] = merged_terminal

    merged_agent = dict(merged.get("agent") if isinstance(merged.get("agent"), dict) else {})
    merged_agent.setdefault("max_iterations", 50)
    merged["agent"] = merged_agent

    merged["data_dir"] = HERMES_HOME

    custom_base_url = data.get("CUSTOM_PROVIDER_BASE_URL", "").strip()
    if custom_base_url:
        raw_name = data.get("CUSTOM_PROVIDER_NAME", "").strip() or custom_base_url
        sanitized_name = re.sub(r"[^a-z0-9-]", "-", raw_name.lower()).strip("-") or "custom"
        merged["custom_providers"] = [{
            "name": sanitized_name,
            "base_url": custom_base_url,
            "key_env": "CUSTOM_PROVIDER_API_KEY",
        }]
    else:
        merged.pop("custom_providers", None)

    with config_path.open("w") as f:
        yaml.safe_dump(merged, f, sort_keys=False, default_flow_style=False)


def write_env(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cat_order = ["model", "provider", "bedrock", "azure", "custom", "tool",
                 "telegram", "discord", "slack", "whatsapp",
                 "email", "mattermost", "matrix", "gateway", "admin"]
    cat_labels = {
        "model": "Model", "provider": "Providers",
        "bedrock": "AWS Bedrock", "azure": "Azure Foundry",
        "custom": "Custom Endpoint", "tool": "Tools",
        "telegram": "Telegram", "discord": "Discord", "slack": "Slack",
        "whatsapp": "WhatsApp", "email": "Email",
        "mattermost": "Mattermost", "matrix": "Matrix", "gateway": "Gateway",
        "admin": "Admin",
    }
    key_cat = {k: c for k, _, c, _ in ENV_VARS}
    grouped: dict[str, list[str]] = {c: [] for c in cat_order}
    grouped["other"] = []

    for k, v in data.items():
        if not v:
            continue
        cat = key_cat.get(k, "other")
        grouped.setdefault(cat, []).append(f"{k}={v}")

    lines: list[str] = []
    for cat in cat_order:
        entries = sorted(grouped.get(cat, []))
        if entries:
            lines.append(f"# {cat_labels.get(cat, cat)}")
            lines.extend(entries)
            lines.append("")
    if grouped["other"]:
        lines.append("# Other")
        lines.extend(sorted(grouped["other"]))
        lines.append("")

    path.write_text("\n".join(lines))


# ── Config helpers ───────────────────────────────────────────────────────────
def is_config_complete(data: dict[str, str] | None = None) -> bool:
    """Single source of truth for 'ready to run the gateway'."""
    if data is None:
        data = read_env(ENV_FILE)
    has_model = bool(data.get("LLM_MODEL"))
    has_provider = any(data.get(k) for k in PROVIDER_KEYS) or _has_xai_oauth_tokens()
    return has_model and has_provider


def mask(data: dict[str, str]) -> dict[str, str]:
    return {
        k: (v[:8] + "***" if len(v) > 8 else "***") if k in SECRET_KEYS and v else v
        for k, v in data.items()
    }


def unmask(new: dict[str, str], existing: dict[str, str]) -> dict[str, str]:
    return {
        k: (existing.get(k, "") if k in SECRET_KEYS and v.endswith("***") else v)
        for k, v in new.items()
    }


# ── Auth (cookie-based) ─────────────────────────────────────────────────────
COOKIE_NAME = "hermes_auth"
COOKIE_MAX_AGE = 7 * 86400  # 7 days
COOKIE_SECRET = secrets.token_bytes(32)

# Public paths — no auth required.
PUBLIC_PATHS = {"/health", "/login", "/logout"}


def _make_auth_token() -> str:
    expires = str(int(time.time()) + COOKIE_MAX_AGE)
    sig = _hmac.new(COOKIE_SECRET, expires.encode(), _hashlib.sha256).hexdigest()
    return f"{expires}.{sig}"


def _verify_auth_token(token: str) -> bool:
    try:
        expires_s, sig = token.rsplit(".", 1)
        if int(expires_s) < time.time():
            return False
        expected = _hmac.new(COOKIE_SECRET, expires_s.encode(), _hashlib.sha256).hexdigest()
        return _hmac.compare_digest(sig, expected)
    except Exception:
        return False


def _is_authenticated(request: Request) -> bool:
    return _verify_auth_token(request.cookies.get(COOKIE_NAME, ""))


def _safe_return_to(value: str) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    p = _urlparse(value)
    if p.scheme or p.netloc:
        return "/"
    return value


def guard(request: Request) -> Response | None:
    if _is_authenticated(request):
        return None
    accept = request.headers.get("accept", "").lower()
    wants_html = "text/html" in accept
    if wants_html:
        rt = request.url.path
        if request.url.query:
            rt = f"{rt}?{request.url.query}"
        return RedirectResponse(f"/login?returnTo={_url_quote(rt)}", status_code=302)
    return JSONResponse({"error": "Unauthorized"}, status_code=401)


LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes Agent — Sign in</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0f14;color:#c9d1d9;font-family:'IBM Plex Sans',sans-serif;
  min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#14181f;border:1px solid #252d3d;border-radius:12px;padding:36px 32px;width:100%;max-width:380px;
  box-shadow:0 20px 40px rgba(0,0,0,0.4)}
.brand{text-align:center;margin-bottom:28px}
.brand-logo{display:inline-flex;align-items:center;gap:10px;font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:18px;color:#6272ff}
.brand-logo span{color:#6b7688;font-weight:400}
.brand-sub{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6b7688;margin-top:8px;letter-spacing:1.5px;text-transform:uppercase}
label{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6b7688;
  letter-spacing:0.05em;text-transform:uppercase;margin-bottom:6px;margin-top:16px}
input{width:100%;background:#0d0f14;border:1px solid #252d3d;border-radius:6px;color:#c9d1d9;
  font-family:'IBM Plex Mono',monospace;font-size:13px;padding:9px 11px;outline:none;transition:border-color .15s}
input:focus{border-color:#6272ff}
button{width:100%;margin-top:24px;background:#6272ff;border:1px solid #6272ff;border-radius:6px;color:#fff;
  font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:500;padding:10px;cursor:pointer;
  transition:background .15s,border-color .15s}
button:hover{background:#7b8fff;border-color:#7b8fff}
.err{background:rgba(248,81,73,0.08);border:1px solid rgba(248,81,73,0.3);border-radius:6px;
  color:#f85149;font-family:'IBM Plex Mono',monospace;font-size:12px;padding:8px 12px;margin-bottom:14px;text-align:center}
.footnote{margin-top:18px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#6b7688;text-align:center;line-height:1.6}
</style></head>
<body>
<div class="card">
  <div class="brand">
    <div class="brand-logo">hermes<span>/admin</span></div>
    <div class="brand-sub">Sign in to continue</div>
  </div>
  __ERROR__
  <form method="POST" action="/login">
    <input type="hidden" name="returnTo" value="__RETURN_TO__">
    <label for="username">Username</label>
    <input id="username" name="username" type="text" autocomplete="username" autofocus required>
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Sign in</button>
  </form>
  <p class="footnote">Credentials are the <code>ADMIN_USERNAME</code> and <code>ADMIN_PASSWORD</code><br>environment variables.</p>
</div>
</body></html>"""


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


async def page_login(request: Request) -> Response:
    if _is_authenticated(request):
        return RedirectResponse(_safe_return_to(request.query_params.get("returnTo", "/")), status_code=302)
    rt = _safe_return_to(request.query_params.get("returnTo", "/"))
    error_html = ('<div class="err">Invalid username or password</div>'
                  if request.query_params.get("error") else "")
    html = (LOGIN_PAGE_HTML
            .replace("__ERROR__", error_html)
            .replace("__RETURN_TO__", _html_escape(rt)))
    return HTMLResponse(html)


async def login_post(request: Request) -> Response:
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    return_to = _safe_return_to(str(form.get("returnTo", "/")))

    valid_user = _hmac.compare_digest(username, ADMIN_USERNAME)
    valid_pw = _hmac.compare_digest(password, ADMIN_PASSWORD)
    if valid_user and valid_pw:
        resp = RedirectResponse(return_to, status_code=302)
        resp.set_cookie(
            COOKIE_NAME,
            _make_auth_token(),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return resp
    return RedirectResponse(f"/login?returnTo={_url_quote(return_to)}&error=1", status_code=302)


async def logout(request: Request) -> Response:
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


# ── Gateway manager ──────────────────────────────────────────────────────────
class Gateway:
    def __init__(self):
        self.proc: asyncio.subprocess.Process | None = None
        self.state = "stopped"
        self.logs: deque[str] = deque(maxlen=500)
        self.started_at: float | None = None
        self.restarts = 0

    async def start(self):
        if self.proc and self.proc.returncode is None:
            return
        self.state = "starting"
        try:
            env = {**os.environ, "HERMES_HOME": HERMES_HOME}
            env.update(read_env(ENV_FILE))
            model = env.get("LLM_MODEL", "")
            provider_key = next((env.get(k, "") for k in PROVIDER_KEYS if env.get(k)), "")
            print(f"[gateway] model={model or '⚠ NOT SET'} | "
                  f"provider_key={'set' if provider_key else '⚠ NOT SET'}", flush=True)
            write_config_yaml(read_env(ENV_FILE))
            self.proc = await asyncio.create_subprocess_exec(
                "hermes", "gateway", "run", "--replace",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            self.state = "running"
            self.started_at = time.time()
            asyncio.create_task(self._drain())
        except Exception as e:
            self.state = "error"
            self.logs.append(f"[error] Failed to start: {e}")

    async def stop(self):
        if not self.proc or self.proc.returncode is not None:
            self.state = "stopped"
            return
        self.state = "stopping"
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=10)
        except asyncio.TimeoutError:
            self.proc.kill()
            await self.proc.wait()
        self.state = "stopped"
        self.started_at = None

    async def restart(self):
        await self.stop()
        self.restarts += 1
        await self.start()

    async def _drain(self):
        assert self.proc and self.proc.stdout
        async for raw in self.proc.stdout:
            line = ANSI_ESCAPE.sub("", raw.decode(errors="replace").rstrip())
            self.logs.append(line)
        if self.state == "running":
            self.state = "error"
            self.logs.append(f"[error] Gateway exited (code {self.proc.returncode})")

    def status(self) -> dict:
        uptime = int(time.time() - self.started_at) if self.started_at and self.state == "running" else None
        return {
            "state":    self.state,
            "pid":      self.proc.pid if self.proc and self.proc.returncode is None else None,
            "uptime":   uptime,
            "restarts": self.restarts,
        }


gw = Gateway()
cfg_lock = asyncio.Lock()


# ── Dashboard manager ────────────────────────────────────────────────────────
class Dashboard:
    def __init__(self):
        self.proc: asyncio.subprocess.Process | None = None
        self.logs: deque[str] = deque(maxlen=300)
        self._drain_task: asyncio.Task | None = None

    async def start(self):
        if self.proc and self.proc.returncode is None:
            return
        try:
            self.proc = await asyncio.create_subprocess_exec(
                "hermes", "dashboard",
                "--host", HERMES_DASHBOARD_HOST,
                "--port", str(HERMES_DASHBOARD_PORT),
                "--no-open",
                "--skip-build",
                "--tui",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            print(f"[dashboard] spawned pid={self.proc.pid} → {HERMES_DASHBOARD_URL}", flush=True)
            self._drain_task = asyncio.create_task(self._drain())
        except Exception as e:
            print(f"[dashboard] FAILED to spawn: {e!r}", flush=True)

    async def _drain(self):
        assert self.proc and self.proc.stdout
        try:
            async for raw in self.proc.stdout:
                line = ANSI_ESCAPE.sub("", raw.decode(errors="replace").rstrip())
                self.logs.append(line)
                print(f"[dashboard] {line}", flush=True)
        except Exception as e:
            print(f"[dashboard] drain error: {e!r}", flush=True)
        finally:
            rc = self.proc.returncode if self.proc else None
            if rc is not None and rc != 0:
                print(f"[dashboard] EXITED with code {rc}", flush=True)
            elif rc == 0:
                print(f"[dashboard] exited cleanly (code 0)", flush=True)

    async def stop(self):
        if not self.proc or self.proc.returncode is not None:
            return
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.proc.kill()
            await self.proc.wait()


dash = Dashboard()

# Shared async HTTP client for reverse proxy.
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=False,
        )
    return _http_client


# ── xAI Grok SuperGrok OAuth (Device Code — RFC 8628) ───────────────────────
_XAI_CLIENT_ID   = "b1a00492-073a-47ea-816f-4c329264a828"
_XAI_SCOPE       = "openid profile email offline_access grok-cli:access api:access"
_XAI_DEVICE_URL  = "https://auth.x.ai/oauth2/device/code"
_XAI_TOKEN_URL   = "https://auth.x.ai/oauth2/token"
_XAI_GRANT_TYPE  = "urn:ietf:params:oauth:grant-type:device_code"

_xai_oauth_state: dict | None = None


def _has_xai_oauth_tokens() -> bool:
    auth_path = Path(HERMES_HOME) / "auth.json"
    if not auth_path.exists():
        return False
    try:
        data = json.loads(auth_path.read_text())
        tokens = data.get("providers", {}).get("xai-oauth", {}).get("tokens", {})
        return bool(isinstance(tokens, dict) and tokens.get("refresh_token"))
    except Exception:
        return False


def _save_xai_auth_json(tokens: dict) -> None:
    auth_path = Path(HERMES_HOME) / "auth.json"
    existing: dict = {}
    if auth_path.exists():
        try:
            existing = json.loads(auth_path.read_text())
        except Exception:
            pass
    if not isinstance(existing, dict):
        existing = {}

    providers = existing.setdefault("providers", {})
    providers["xai-oauth"] = {
        "tokens": tokens,
        "auth_mode": "oauth_device",
        "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "discovery": {
            "authorization_endpoint": "https://auth.x.ai/oauth2/authorize",
            "token_endpoint": _XAI_TOKEN_URL,
        },
        "redirect_uri": "",
    }
    existing["active_provider"] = "xai-oauth"
    existing["version"] = 2
    existing["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    auth_path.write_text(json.dumps(existing, indent=2) + "\n")
    try:
        auth_path.chmod(0o600)
    except Exception:
        pass


def _apply_xai_oauth_config(model: str) -> None:
    config_path = Path(HERMES_HOME) / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if config_path.exists():
        try:
            with config_path.open() as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            pass

    merged = dict(existing)
    merged_model = dict(merged.get("model") if isinstance(merged.get("model"), dict) else {})
    if model:
        merged_model["default"] = model
    merged_model["provider"] = "xai-oauth"
    merged["model"] = merged_model

    merged_terminal = dict(merged.get("terminal") if isinstance(merged.get("terminal"), dict) else {})
    merged_terminal.setdefault("backend", "local")
    merged_terminal.setdefault("timeout", 60)
    merged_terminal.setdefault("cwd", "/tmp")
    merged["terminal"] = merged_terminal

    merged_agent = dict(merged.get("agent") if isinstance(merged.get("agent"), dict) else {})
    merged_agent.setdefault("max_iterations", 50)
    merged["agent"] = merged_agent
    merged["data_dir"] = HERMES_HOME

    with config_path.open("w") as f:
        yaml.safe_dump(merged, f, sort_keys=False, default_flow_style=False)

    if model:
        existing_env = read_env(ENV_FILE)
        existing_env["LLM_MODEL"] = model
        existing_env["_MODEL_XAI_OAUTH"] = model
        write_env(ENV_FILE, existing_env)


async def _poll_xai_device_auth(state: dict) -> None:
    client = get_http_client()
    while time.time() < state["expires_at"]:
        await asyncio.sleep(state["interval"])
        try:
            resp = await client.post(
                _XAI_TOKEN_URL,
                data={
                    "grant_type": _XAI_GRANT_TYPE,
                    "device_code": state["device_code"],
                    "client_id": _XAI_CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=httpx.Timeout(15.0),
            )
        except Exception as e:
            print(f"[xai-oauth] poll error: {e!r}", flush=True)
            continue

        if resp.status_code == 200:
            try:
                tokens = resp.json()
            except Exception:
                state["status"] = "error"
                state["error"] = "Invalid token response from xAI"
                return
            _save_xai_auth_json(tokens)
            _apply_xai_oauth_config(state.get("model", ""))
            state["status"] = "authorized"
            print("[xai-oauth] authorized — restarting gateway", flush=True)
            asyncio.create_task(gw.restart())
            return

        try:
            err_data = resp.json()
        except Exception:
            err_data = {}
        error = err_data.get("error", "")

        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            state["interval"] = min(state["interval"] + 5, 30)
        else:
            state["status"] = "error"
            state["error"] = err_data.get("error_description", error) or error or "Unknown error"
            print(f"[xai-oauth] failed: {error}", flush=True)
            return

    state["status"] = "expired"
    print("[xai-oauth] device code expired", flush=True)


async def api_oauth_xai_delete(request: Request) -> Response:
    global _xai_oauth_state
    if err := guard(request):
        return err
    auth_path = Path(HERMES_HOME) / "auth.json"
    if auth_path.exists():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
            data.get("providers", {}).pop("xai-oauth", None)
            if data.get("active_provider") == "xai-oauth":
                data.pop("active_provider", None)
            auth_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
    env = read_env(ENV_FILE)
    env.pop("_MODEL_XAI_OAUTH", None)
    write_env(ENV_FILE, env)
    _xai_oauth_state = None
    return JSONResponse({"ok": True})


async def api_oauth_xai_start(request: Request) -> Response:
    global _xai_oauth_state
    if err := guard(request):
        return err

    try:
        body = await request.json()
    except Exception:
        body = {}
    model = str(body.get("model", "")).strip()

    client = get_http_client()
    try:
        resp = await client.post(
            _XAI_DEVICE_URL,
            data={"client_id": _XAI_CLIENT_ID, "scope": _XAI_SCOPE},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=httpx.Timeout(15.0),
        )
    except Exception as e:
        return JSONResponse({"error": f"Could not reach xAI: {e}"}, status_code=502)

    if resp.status_code != 200:
        return JSONResponse(
            {"error": f"xAI returned {resp.status_code}: {resp.text[:200]}"},
            status_code=502,
        )

    try:
        data = resp.json()
    except Exception:
        return JSONResponse({"error": "Invalid response from xAI"}, status_code=502)

    _xai_oauth_state = {
        "device_code": data["device_code"],
        "user_code": data["user_code"],
        "verification_uri": data.get("verification_uri_complete") or data["verification_uri"],
        "expires_at": time.time() + data.get("expires_in", 900),
        "interval": max(data.get("interval", 5), 5),
        "status": "pending",
        "model": model,
    }
    asyncio.create_task(_poll_xai_device_auth(_xai_oauth_state))

    return JSONResponse({
        "user_code": data["user_code"],
        "verification_uri": _xai_oauth_state["verification_uri"],
        "expires_in": data.get("expires_in", 900),
    })


async def api_oauth_xai_status(request: Request) -> Response:
    if err := guard(request):
        return err
    if _xai_oauth_state is None:
        if _has_xai_oauth_tokens():
            return JSONResponse({"status": "authorized"})
        return JSONResponse({"status": "none"})
    return JSONResponse({
        "status": _xai_oauth_state["status"],
        "error": _xai_oauth_state.get("error", ""),
    })


# ── Reverse proxy → Hermes dashboard ──────────────────────────────────────────
_WIDGET_LINK_STYLE = (
    "background:rgba(20,24,31,0.92);backdrop-filter:blur(8px);"
    "border:1px solid #252d3d;border-radius:6px;padding:6px 12px;"
    "color:#c9d1d9;text-decoration:none;display:inline-flex;"
    "align-items:center;gap:6px;"
)
BACK_TO_SETUP_WIDGET = (
    '<div id="hermes-back-widget" style="position:fixed;bottom:14px;right:14px;'
    'z-index:99999;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;'
    'font-size:11px;display:flex;gap:8px;">'
    f'<a href="/setup" style="{_WIDGET_LINK_STYLE}">← Setup</a>'
    f'<a href="/logout" style="{_WIDGET_LINK_STYLE}">Sign out</a>'
    '</div>'
)

DASHBOARD_UNAVAILABLE_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard starting…</title>
<style>body{background:#0d0f14;color:#c9d1d9;font-family:ui-monospace,Menlo,monospace;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{max-width:480px;padding:32px;border:1px solid #252d3d;border-radius:12px;
background:#14181f;text-align:center}
h1{font-size:16px;color:#d29922;margin:0 0 12px;font-weight:600}
p{font-size:13px;color:#6b7688;line-height:1.6;margin:0 0 16px}
a{color:#6272ff;text-decoration:none;border:1px solid #252d3d;border-radius:6px;
padding:7px 14px;font-size:12px;display:inline-block}
a:hover{border-color:#6272ff}</style></head>
<body><div class="card">
<h1>⚠ Hermes dashboard unavailable</h1>
<p>The native Hermes dashboard is not responding on port %d.<br>
It may still be starting up, or it may have crashed.</p>
<p>Try refreshing in a few seconds, or head back to setup.</p>
<a href="/setup">← Back to Setup</a>
</div>
<script>setTimeout(()=>location.reload(),4000);</script>
</body></html>""" % HERMES_DASHBOARD_PORT


async def _proxy_to_dashboard(request: Request) -> Response:
    """Forward an authenticated request to the Hermes dashboard subprocess."""
    client = get_http_client()
    target = f"{HERMES_DASHBOARD_URL}{request.url.path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    req_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP
    }
    body = await request.body()

    try:
        upstream = await client.request(
            request.method,
            target,
            headers=req_headers,
            content=body,
        )
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return HTMLResponse(DASHBOARD_UNAVAILABLE_HTML, status_code=503)
    except httpx.RequestError as e:
        print(f"[proxy] upstream error for {request.method} {request.url.path}: {e}", flush=True)
        return HTMLResponse(DASHBOARD_UNAVAILABLE_HTML, status_code=502)

    if upstream.status_code >= 400:
        body_snip = upstream.content[:200].decode("utf-8", errors="replace")
        print(
            f"[proxy] {request.method} {request.url.path} -> {upstream.status_code} "
            f"body={body_snip!r}",
            flush=True,
        )

    resp_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in HOP_BY_HOP
        and k.lower() not in ("content-encoding", "content-length")
    }

    content = upstream.content
    content_type = upstream.headers.get("content-type", "").lower()

    # Inject "← Setup" widget into HTML pages.
    if "text/html" in content_type and b"</body>" in content:
        try:
            text = content.decode("utf-8", errors="replace")
            text = text.replace("</body>", BACK_TO_SETUP_WIDGET + "</body>", 1)
            content = text.encode("utf-8")
        except Exception:
            pass

    return Response(
        content=content,
        status_code=upstream.status_code,
        headers=resp_headers,
    )


async def _proxy_ws(ws: WebSocket):
    """WebSocket proxy → Hermes dashboard.

    Connects to the upstream FIRST, and only accepts the client if the upstream
    is available. This prevents accepting a WebSocket only to immediately fail
    because the Hermes dashboard isn't ready yet.
    """
    target = f"ws://{HERMES_DASHBOARD_HOST}:{HERMES_DASHBOARD_PORT}{ws.url.path}"
    if ws.url.query:
        target = f"{target}?{ws.url.query}"

    # Try upstream connection first — fail fast if dashboard isn't ready.
    try:
        upstream_ws = await asyncio.wait_for(
            websockets.connect(target, close_timeout=10),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        print(f"[proxy-ws] upstream timeout for {ws.url.path}", flush=True)
        await ws.accept()
        await ws.send_json({"error": "Dashboard not ready yet", "type": "error"})
        await ws.close()
        return
    except Exception as e:
        print(f"[proxy-ws] upstream unavailable for {ws.url.path}: {e}", flush=True)
        await ws.accept()
        await ws.send_json({"error": "Dashboard unavailable", "type": "error"})
        await ws.close()
        return

    # Upstream is connected, now accept the client.
    await ws.accept()

    async def relay_upstream():
        try:
            async for msg in upstream_ws:
                if ws.client_state == WebSocketState.DISCONNECTED:
                    break
                if isinstance(msg, bytes):
                    await ws.send_bytes(msg)
                else:
                    await ws.send_text(msg)
        except Exception:
            pass

    relay_task = asyncio.create_task(relay_upstream())

    try:
        while True:
            msg = await ws.receive_text()
            if ws.client_state == WebSocketState.DISCONNECTED:
                break
            try:
                parsed = json.loads(msg)
                await upstream_ws.send(json.dumps(parsed))
            except json.JSONDecodeError:
                await upstream_ws.send(msg)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[proxy-ws] client send error: {e}", flush=True)
    finally:
        relay_task.cancel()
        try:
            await relay_task
        except asyncio.CancelledError:
            pass
        await upstream_ws.close()
    try:
        await ws.close()
    except Exception:
        pass


# ── Route handlers ────────────────────────────────────────────────────────────
async def page_index(request: Request):
    if err := guard(request):
        return err

    # If config is complete, proxy to the Hermes dashboard.
    data = read_env(ENV_FILE)
    if is_config_complete(data):
        return await _proxy_to_dashboard(request)

    return templates.TemplateResponse(request, "index.html")


async def route_health(request: Request):
    return JSONResponse({"status": "ok", "gateway": gw.state})


async def api_config_get(request: Request):
    if err := guard(request):
        return err
    async with cfg_lock:
        data = read_env(ENV_FILE)
    defs = [{"key": k, "label": l, "category": c, "secret": s} for k, l, c, s in ENV_VARS]
    return JSONResponse({"vars": mask(data), "defs": defs})


async def api_config_put(request: Request):
    if err := guard(request):
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    try:
        restart = body.pop("_restart", False)
        new_vars = body.get("vars", {})
        async with cfg_lock:
            existing = read_env(ENV_FILE)
            merged = unmask(new_vars, existing)
            for k, v in existing.items():
                if k not in merged:
                    merged[k] = v
            write_env(ENV_FILE, merged)
            write_config_yaml(merged)
        if restart:
            asyncio.create_task(gw.restart())
        return JSONResponse({"ok": True, "restarting": restart})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_status(request: Request):
    if err := guard(request):
        return err
    data = read_env(ENV_FILE)
    providers = {
        k.replace("_API_KEY","").replace("_TOKEN","").replace("HF_","HuggingFace ").replace("_"," ").title():
        {"configured": bool(data.get(k))}
        for k in PROVIDER_KEYS
    }
    channels = {
        name: {"configured": bool(v := data.get(key,"")) and v.lower() not in ("false","0","no")}
        for name, key in CHANNEL_MAP.items()
    }
    return JSONResponse({"gateway": gw.status(), "providers": providers, "channels": channels})


async def api_logs(request: Request):
    if err := guard(request):
        return err
    return JSONResponse({"lines": list(gw.logs)})


async def api_gw_start(request: Request):
    if err := guard(request):
        return err
    asyncio.create_task(gw.start())
    return JSONResponse({"ok": True})


async def api_gw_stop(request: Request):
    if err := guard(request):
        return err
    asyncio.create_task(gw.stop())
    return JSONResponse({"ok": True})


async def api_gw_restart(request: Request):
    if err := guard(request):
        return err
    asyncio.create_task(gw.restart())
    return JSONResponse({"ok": True})


async def api_config_reset(request: Request):
    if err := guard(request):
        return err
    asyncio.create_task(gw.stop())
    async with cfg_lock:
        if ENV_FILE.exists():
            ENV_FILE.unlink()
        write_config_yaml({})
    return JSONResponse({"ok": True})


# ── Pairing ───────────────────────────────────────────────────────────────────
def _pjson(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}


def _wjson(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _platforms(suffix: str) -> list[str]:
    if not PAIRING_DIR.exists():
        return []
    return [f.stem.rsplit(f"-{suffix}", 1)[0] for f in PAIRING_DIR.glob(f"*-{suffix}.json")]


async def api_pairing_pending(request: Request):
    if err := guard(request):
        return err
    now = time.time()
    out = []
    for p in _platforms("pending"):
        for code, info in _pjson(PAIRING_DIR / f"{p}-pending.json").items():
            if now - info.get("created_at", now) <= PAIRING_TTL:
                out.append({"platform": p, "code": code,
                            "user_id": info.get("user_id",""), "user_name": info.get("user_name",""),
                            "age_minutes": int((now - info.get("created_at", now)) / 60)})
    return JSONResponse({"pending": out})


async def api_pairing_approve(request: Request):
    if err := guard(request):
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    platform, code = body.get("platform",""), body.get("code","").upper().strip()
    if not platform or not code:
        return JSONResponse({"error": "platform and code required"}, status_code=400)
    pending_path = PAIRING_DIR / f"{platform}-pending.json"
    pending = _pjson(pending_path)
    if code not in pending:
        return JSONResponse({"error": "Code not found"}, status_code=404)
    entry = pending.pop(code)
    _wjson(pending_path, pending)
    approved = _pjson(PAIRING_DIR / f"{platform}-approved.json")
    approved[entry["user_id"]] = {"user_name": entry.get("user_name",""), "approved_at": time.time()}
    _wjson(PAIRING_DIR / f"{platform}-approved.json", approved)
    return JSONResponse({"ok": True})


async def api_pairing_deny(request: Request):
    if err := guard(request):
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    platform, code = body.get("platform",""), body.get("code","").upper().strip()
    p = PAIRING_DIR / f"{platform}-pending.json"
    pending = _pjson(p)
    if code in pending:
        del pending[code]
        _wjson(p, pending)
    return JSONResponse({"ok": True})


async def api_pairing_approved(request: Request):
    if err := guard(request):
        return err
    out = []
    for p in _platforms("approved"):
        for uid, info in _pjson(PAIRING_DIR / f"{p}-approved.json").items():
            out.append({"platform": p, "user_id": uid,
                        "user_name": info.get("user_name",""), "approved_at": info.get("approved_at",0)})
    return JSONResponse({"approved": out})


async def api_pairing_revoke(request: Request):
    if err := guard(request):
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    platform, uid = body.get("platform",""), body.get("user_id","")
    if not platform or uid:
        return JSONResponse({"error": "platform and user_id required"}, status_code=400)
    p = PAIRING_DIR / f"{platform}-approved.json"
    approved = _pjson(p)
    if uid in approved:
        del approved[uid]
        _wjson(p, approved)
    return JSONResponse({"ok": True})


# ── MCP Server management ────────────────────────────────────────────────────
def read_config_yaml() -> dict:
    """Read full config.yaml, return empty dict if missing or invalid."""
    config_path = Path(HERMES_HOME) / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open() as f:
            loaded = yaml.safe_load(f)
        return loaded if isinstance(loaded, dict) else {}
    except (yaml.YAMLError, OSError):
        return {}


async def api_mcp_get(request: Request):
    """GET /api/mcp — return list of configured MCP servers."""
    if err := guard(request):
        return err
    config = read_config_yaml()
    servers = config.get("mcp_servers", {})
    return JSONResponse({"servers": servers})


async def api_mcp_put(request: Request):
    """PUT /api/mcp — update MCP servers config (deep-merge)."""
    if err := guard(request):
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    try:
        async with cfg_lock:
            config = read_config_yaml()
            existing_mcp = config.get("mcp_servers", {})
            new_servers = body.get("servers", {})

            # Validate server entries
            for name, srv in new_servers.items():
                if not isinstance(srv, dict):
                    return JSONResponse(
                        {"error": f"MCP server '{name}' must be an object"},
                        status_code=400,
                    )

            # Deep-merge: update existing servers with new ones
            merged_mcp = dict(existing_mcp)
            for name, srv in new_servers.items():
                if srv is None:
                    merged_mcp.pop(name, None)  # Remove server
                else:
                    existing = merged_mcp.get(name, {})
                    merged = dict(existing)
                    merged.update(srv)
                    merged_mcp[name] = merged

            config["mcp_servers"] = merged_mcp

            # Write full config.yaml preserving all other keys
            config_path = Path(HERMES_HOME) / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open("w") as f:
                yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)

        return JSONResponse({"ok": True, "servers": merged_mcp})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_mcp_delete(request: Request):
    """DELETE /api/mcp — remove a specific MCP server."""
    if err := guard(request):
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    name = body.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "MCP server name required"}, status_code=400)

    async with cfg_lock:
        config = read_config_yaml()
        servers = config.get("mcp_servers", {})
        if name in servers:
            del servers[name]
        config["mcp_servers"] = servers
        config_path = Path(HERMES_HOME) / "config.yaml"
        with config_path.open("w") as f:
            yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)

    return JSONResponse({"ok": True})


async def api_mcp_restart(request: Request):
    """POST /api/mcp/restart — restart gateway to pick up MCP changes."""
    if err := guard(request):
        return err
    asyncio.create_task(gw.restart())
    return JSONResponse({"ok": True})


# ── Google Sheets API for PWA ───────────────────────────────────────────────
# Reads financial data from the user's personal finance sheet and returns
# structured JSON consumed by the PWA at /api/sheets.
# Uses the same GOOGLE_SHEETS_CREDENTIALS service account as the MCP server.

SHEET_ID = "1okMWpcUWUHiLQqIn06BnOFI4jBYf516PEj0GFugXxN0"


def _get_sheets_service():
    """Build a Google Sheets service client using stored credentials."""
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return None, "google-auth or google-api-python-client not installed"

    if not creds_json:
        # Fallback: file written by start.sh
        creds_file = "/data/.google-sheets-creds.json"
        if os.path.exists(creds_file):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    creds_file,
                    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
                )
                return build("sheets", "v4", credentials=creds), None
            except Exception as e:
                return None, str(e)
        return None, "GOOGLE_SHEETS_CREDENTIALS not set"
    try:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        return build("sheets", "v4", credentials=creds), None
    except Exception as e:
        return None, str(e)


def _safe_float(v):
    try:
        return float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0


async def api_sheets_finance(request: Request):
    """GET /api/sheets — return structured financial data from Google Sheets.

    This endpoint is meant to be consumed by the Personal Finance PWA.
    Returns the same JSON shape as the Apps Script Web App spec.
    """
    service, err = _get_sheets_service()
    if err:
        return JSONResponse({"error": err}, status_code=500)
    if service is None:
        return JSONResponse({"error": "Sheets service unavailable"}, status_code=500)

    try:
        # Discover all sheet names dynamically
        metadata = service.spreadsheets().get(spreadsheetId=SHEET_ID, fields="sheets.properties.title,sheets.properties.sheetId").execute()
        all_sheets = [s["properties"]["title"] for s in metadata.get("sheets", [])]
        print(f"[sheets] Available tabs: {all_sheets}", flush=True)

        # Map expected sheet names to actual names
        def find_sheet(name_hints):
            for hint in name_hints:
                for s in all_sheets:
                    if hint in s.lower():
                        return s
            return all_sheets[0] if all_sheets else None

        tablero_name = find_sheet(["tablero", "dashboard", "control"])
        presupuesto_name = find_sheet(["presupuesto", "presup", "budget"])
        inversiones_name = find_sheet(["inversiones", "inversion", "invers"])
        metas_name = find_sheet(["metas", "goals", "meta"])
        salud_name = find_sheet(["salud", "health", "sal"])
        subs_name = find_sheet(["suscripciones", "suscrip", "subscriptions"])
        registro_name = find_sheet(["registro", "gastos", "expenses", "registro"])

        if not tablero_name:
            return JSONResponse({"error": f"No sheets found in document. Available: {all_sheets}"}, status_code=500)

        sheets_api = service.spreadsheets().values()

        # Tab 1: Tablero (row 18 = current month)
        tablero = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{tablero_name}!A18:N18").execute()
        t = tablero.get("values", [[]])[0]
        # A=Mes, B=Ingreso, C=% Ahorro, D=Tope Gasto, E=Total Gastado
        # F=% Uso, G=Semáforo, H=Exigible Galicia, I=Exigible Macro
        # J=Exigible ICBC, K=Exigible ML, L=Total Exigible, M=Rescate FCI
        # N=Deuda Remanente
        ingreso = _safe_float(t[1]) if len(t) > 1 else 0
        tope_gasto = _safe_float(t[3]) if len(t) > 3 else 0
        total_gastado = _safe_float(t[4]) if len(t) > 4 else 0
        pct_uso = _safe_float(t[5]) if len(t) > 5 else 0
        semaforo = t[6] if len(t) > 6 else "🟢"
        galicia = _safe_float(t[7]) if len(t) > 7 else 0
        macro = _safe_float(t[8]) if len(t) > 8 else 0
        icbc = _safe_float(t[9]) if len(t) > 9 else 0
        ml = _safe_float(t[10]) if len(t) > 10 else 0
        total_exigible = _safe_float(t[11]) if len(t) > 11 else 0
        fci = _safe_float(t[12]) if len(t) > 12 else 0

        # Inversiones tab (last 2 rows for current month + projection)
        inv_result = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{inversiones_name or 'Inversiones'}!A:G").execute()
        inv_rows = inv_result.get("values", [])
        inv_header = inv_rows[0] if inv_rows else []
        inv_data = inv_rows[-1] if len(inv_rows) > 1 else []
        capital_actual = _safe_float(inv_data[2]) if len(inv_data) > 2 else fci
        rendimiento = _safe_float(inv_data[4]) if len(inv_data) > 4 else 0
        pct_rendimiento = _safe_float(inv_data[5]) if len(inv_data) > 5 else 0

        # Presupuesto tab (all rows, skip header if there's one)
        pres_result = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{presupuesto_name or 'Presupuesto'}!A:G").execute()
        pres_rows = pres_result.get("values", [])
        presupuesto = []
        for row in pres_rows[1:]:  # skip header
            if len(row) >= 3:
                cat = row[0]
                ppto = _safe_float(row[1]) if len(row) > 1 else 0
                gast = _safe_float(row[2]) if len(row) > 2 else 0
                rest = _safe_float(row[3]) if len(row) > 3 else 0
                pct = _safe_float(row[4]) if len(row) > 4 else 0
                sem = row[5] if len(row) > 5 else ("🔴" if pct > 100 else ("🟡" if pct > 50 else "🟢"))
                presupuesto.append({
                    "categoria": cat, "presupuesto": ppto,
                    "gastado": gast, "restante": rest,
                    "pct": round(pct, 1), "semaforo": sem
                })

        # Compute merged dashboard
        total_exigible_list = []
        if galicia:
            total_exigible_list.append({"banco": "Galicia", "exigible": galicia})
        if macro:
            total_exigible_list.append({"banco": "Macro", "exigible": macro})
        if icbc:
            total_exigible_list.append({"banco": "ICBC", "exigible": icbc})
        if ml:
            total_exigible_list.append({"banco": "MercadoLibre", "exigible": ml})

        # Find next due date (first exigible that's due soon)
        prox_vencimiento = None
        if total_exigible_list:
            # Simple heuristic: take the first one or the largest
            top = max(total_exigible_list, key=lambda x: x["exigible"])
            # Figure out the due date from the tcs endpoint (we'll compute)
            prox_vencimiento = {
                "concepto": "TCs por vencer",
                "monto": total_exigible,
                "entidades": [e["banco"] for e in total_exigible_list],
            }

        # Metas tab
        metas_result = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{metas_name or 'Metas'}!A:I").execute()
        metas_rows = metas_result.get("values", [])
        metas = []
        for row in metas_rows[1:]:
            if len(row) >= 1:
                nombre = row[0]
                objetivo = _safe_float(row[1]) if len(row) > 1 else 0
                ahorrado = _safe_float(row[2]) if len(row) > 2 else 0
                progreso = round((ahorrado / objetivo * 100)) if objetivo > 0 else 0
                m = {"nombre": nombre, "objetivo": objetivo, "ahorrado": ahorrado, "progreso": progreso}
                if len(row) > 7:
                    m["estado"] = row[7]
                metas.append(m)

        # Salud tab
        salud_result = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{salud_name or 'Salud'}!A:H").execute()
        salud_rows = salud_result.get("values", [])
        salud = []
        for row in salud_rows[1:]:
            if len(row) >= 1:
                s = {"profesional": row[0]}
                if len(row) > 1: s["motivo"] = row[1]
                if len(row) > 4: s["costo_est"] = _safe_float(row[4])
                if len(row) > 6: s["estado"] = row[6]
                salud.append(s)

        # Suscripciones tab
        subs_result = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{subs_name or 'Suscripciones'}!A:H").execute()
        subs_rows = subs_result.get("values", [])
        suscripciones = []
        for row in subs_rows[1:]:
            if len(row) >= 1:
                s = {"servicio": row[0]}
                if len(row) > 1: s["monto_mes"] = _safe_float(row[1])
                if len(row) > 3: s["monto_anio"] = _safe_float(row[3])
                if len(row) > 5: s["activo"] = row[5].lower() in ("true", "sí", "si", "1", "yes")
                suscripciones.append(s)

        # Expenses tab (last 50 for reference)
        exp_result = sheets_api.get(spreadsheetId=SHEET_ID, range=f"{registro_name or 'Registro'}!A2:J51").execute()
        exp_rows = exp_result.get("values", [])
        registro = []
        for row in exp_rows:
            if len(row) >= 4:
                registro.append({
                    "fecha": row[0], "comercio": row[2] if len(row) > 2 else "",
                    "categoria": row[3] if len(row) > 3 else "",
                    "monto": _safe_float(row[4]) if len(row) > 4 else 0,
                })

        # Build response matching the PWA spec
        result = {
            "dashboard": {
                "ingreso": ingreso,
                "tope_gasto": tope_gasto,
                "total_gastado": total_gastado,
                "pct_uso": round(pct_uso, 1),
                "semaforo": semaforo,
                "capital_fci": fci,
                "rendimiento_fci": rendimiento,
                "prox_vencimiento": prox_vencimiento,
            },
            "presupuesto": presupuesto,
            "tcs": total_exigible_list,
            "inversiones": [{
                "capital": capital_actual,
                "rendimiento": rendimiento,
                "pct_rendimiento": round(pct_rendimiento, 2),
            }],
            "metas": metas,
            "salud": salud,
            "suscripciones": suscripciones,
            "registro": registro,
        }

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Catch-all proxy for / (non-API paths) ────────────────────────────────────
async def catch_all_proxy(request: Request):
    """Serve the admin SPA for /setup/*, proxy everything else to dashboard."""
    if request.url.path.startswith("/setup"):
        if err := guard(request):
            return err
        return templates.TemplateResponse(request, "index.html")
    if err := guard(request):
        return err
    # Non-setup, non-API paths → proxy to Hermes dashboard
    return await _proxy_to_dashboard(request)


# ── App factory ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    """Lifespan handler: start dashboard on boot, shutdown on exit."""
    asyncio.create_task(dash.start())
    yield
    await dash.stop()
    if _http_client:
        await _http_client.aclose()


def create_app() -> Starlette:
    routes = [
        Route("/",                page_index),
        Route("/health",          route_health),
        Route("/login",           page_login,      methods=["GET"]),
        Route("/login",           login_post,      methods=["POST"]),
        Route("/logout",          logout),
        Route("/api/config",      api_config_get,  methods=["GET"]),
        Route("/api/config",      api_config_put,  methods=["PUT"]),
        Route("/api/status",      api_status,      methods=["GET"]),
        Route("/api/logs",        api_logs,        methods=["GET"]),
        Route("/api/gw/start",    api_gw_start,    methods=["POST"]),
        Route("/api/gw/stop",     api_gw_stop,     methods=["POST"]),
        Route("/api/gw/restart",  api_gw_restart,  methods=["POST"]),
        Route("/api/config/reset", api_config_reset, methods=["POST"]),
        Route("/api/pairing/pending",  api_pairing_pending,  methods=["GET"]),
        Route("/api/pairing/approve",  api_pairing_approve,  methods=["POST"]),
        Route("/api/pairing/deny",     api_pairing_deny,     methods=["POST"]),
        Route("/api/pairing/approved", api_pairing_approved, methods=["GET"]),
        Route("/api/pairing/revoke",   api_pairing_revoke,   methods=["POST"]),
        Route("/api/oauth/xai/start",  api_oauth_xai_start,  methods=["POST"]),
        Route("/api/oauth/xai/status", api_oauth_xai_status, methods=["GET"]),
        Route("/api/oauth/xai/delete", api_oauth_xai_delete, methods=["POST"]),
        # MCP server management
        Route("/api/mcp",       api_mcp_get,      methods=["GET"]),
        Route("/api/mcp",       api_mcp_put,      methods=["PUT"]),
        Route("/api/mcp",       api_mcp_delete,   methods=["DELETE"]),
        Route("/api/mcp/restart", api_mcp_restart, methods=["POST"]),
        # Google Sheets finance endpoint for PWA
        Route("/api/sheets", api_sheets_finance, methods=["GET"]),
        # WebSocket proxy endpoints
        WebSocketRoute("/api/pty",     _proxy_ws),
        WebSocketRoute("/api/ws",      _proxy_ws),
        WebSocketRoute("/api/events",  _proxy_ws),
        # Catch-all for SPA routes and dashboard proxy (all HTTP methods).
        # The Hermes dashboard SPA sends POST/PUT/DELETE to its API endpoints,
        # and these must be proxied through — not rejected with 405.
        Route("/{path:path}", catch_all_proxy, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]),
    ]
    return Starlette(
        routes=routes,
        lifespan=lifespan,
        middleware=[
            Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
        ],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
