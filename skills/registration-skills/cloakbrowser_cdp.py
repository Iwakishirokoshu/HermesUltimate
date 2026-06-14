#!/usr/bin/env python3
"""
CloakBrowser CDP daemon.
Запускает CloakBrowser с открытым CDP портом 9222.

Использование:
  # Без прокси, профиль по имени:
  DISPLAY=:1 python3 cloakbrowser_cdp.py acc_01

  # С residential прокси:
  PROXY=socks5://USER:PASS@HOST:PORT \
  DISPLAY=:1 python3 cloakbrowser_cdp.py acc_01

  # Через tmux (рекомендуется — не умрёт при обрыве SSH):
  tmux new -d -s cloak 'DISPLAY=:1 python3 cloakbrowser_cdp.py acc_01'

  # Путь к venv (если cloakbrowser не в системном python):
  VENV_PYTHON=/home/USER/venv/bin/python3 python3 cloakbrowser_cdp.py acc_01

Подключить агента:
  hermes config set browser.cdp_url http://127.0.0.1:9223   # через шим
  hermes config set browser.auto_local_for_private_urls false

Профили хранятся в ~/profiles/<name> (или PROFILES_DIR env) — никогда не удалять.
"""
import os, sys, re, signal, threading, uuid, glob

# ── Venv bootstrap ────────────────────────────────────────────────────────────
# Если VENV_PYTHON задан явно — используем его.
# Иначе пытаемся найти venv с cloakbrowser автоматически.
_VENV_PYTHON = os.environ.get("VENV_PYTHON", "")
if not _VENV_PYTHON:
    _candidates = (
        glob.glob(os.path.expanduser("~/venv/bin/python3")) +
        glob.glob(os.path.expanduser("~/.cloakbrowser/venv/bin/python3")) +
        glob.glob("/usr/local/lib/*/venv/bin/python3")
    )
    if _candidates:
        _VENV_PYTHON = _candidates[0]

if _VENV_PYTHON and sys.executable != _VENV_PYTHON and os.path.isfile(_VENV_PYTHON):
    os.execv(_VENV_PYTHON, [_VENV_PYTHON] + sys.argv)

# ── CloakBrowser binary ───────────────────────────────────────────────────────
os.environ.setdefault("DISPLAY", ":1")
if not os.environ.get("CLOAKBROWSER_BINARY_PATH"):
    _bins = sorted(glob.glob(os.path.expanduser("~/.cloakbrowser/chromium-*/chrome")))
    if _bins:
        os.environ["CLOAKBROWSER_BINARY_PATH"] = _bins[-1]
        print(f"[CDP] Auto-detected binary: {_bins[-1]}", flush=True)
    else:
        print("[CDP] WARNING: CLOAKBROWSER_BINARY_PATH not set and no binary found in ~/.cloakbrowser/", flush=True)

from cloakbrowser import launch_persistent_context

CDP_PORT     = int(os.environ.get("CDP_PORT", "9222"))
PROFILES_DIR = os.environ.get("PROFILES_DIR", os.path.expanduser("~/profiles"))

# Профиль: первый аргумент или случайный ID
profile_name = sys.argv[1] if len(sys.argv) > 1 else uuid.uuid4().hex[:8]
profile_path = os.path.join(PROFILES_DIR, profile_name)
os.makedirs(profile_path, exist_ok=True)

# Прокси из env (опционально)
proxy_url = os.environ.get("PROXY", "")
proxy = None
if proxy_url:
    m = re.match(r'(\w+)://([^:]+):([^@]+)@([^:]+):(\d+)', proxy_url)
    if m:
        proxy = {
            "server":   f"{m.group(1)}://{m.group(4)}:{m.group(5)}",
            "username": m.group(2),
            "password": m.group(3),
        }
        print(f"[CDP] Proxy: {m.group(4)}:{m.group(5)}", flush=True)
    else:
        print(f"[CDP] WARNING: cannot parse PROXY={proxy_url}", flush=True)
else:
    print("[CDP] No proxy", flush=True)

# Аргументы запуска — БЕЗ --no-sandbox
# Если запускается под root и падает — запускать через:
#   useradd -m chromeuser && sudo -u chromeuser DISPLAY=:1 python3 cloakbrowser_cdp.py
args = [
    "--ignore-certificate-errors",
    "--fingerprint-platform=windows",
    f"--remote-debugging-port={CDP_PORT}",
    "--remote-debugging-address=127.0.0.1",
    # "--disable-setuid-sandbox",  # крайний случай если без root совсем не запускается
]

# Если явно запускаем под root (HermesUnlock сервер) — добавляем no-sandbox
# Это менее плохо чем падение, но лучше создать chromeuser
if os.getuid() == 0:
    print("[CDP] WARNING: running as root — adding --no-sandbox. "
          "Better: useradd chromeuser && sudo -u chromeuser ...", flush=True)
    args.append("--no-sandbox")

print(f"[CDP] Profile: {profile_path}", flush=True)
print(f"[CDP] Starting on port {CDP_PORT}...", flush=True)

kwargs = dict(
    headless=False,
    humanize=True,
    human_preset="careful",
    locale="en-US",
    timezone="America/Chicago",
    args=args,
)
if proxy:
    kwargs["proxy"] = proxy

ctx = launch_persistent_context(profile_path, **kwargs)
page = ctx.new_page()
page.goto("about:blank")

print(f"\n[CDP] ✅ Ready on ws://127.0.0.1:{CDP_PORT}", flush=True)
print(f"[CDP] Connect via shim: hermes config set browser.cdp_url http://127.0.0.1:9223", flush=True)
print(f"[CDP] Press Ctrl+C to stop\n", flush=True)

# Нормальный daemon — не падает при обрыве SSH
stop = threading.Event()

def _shutdown(sig, frame):
    print(f"\n[CDP] Signal {sig}, shutting down...", flush=True)
    stop.set()

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

stop.wait()
ctx.close()
print("[CDP] Closed.", flush=True)
