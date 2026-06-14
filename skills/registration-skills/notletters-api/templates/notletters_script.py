#!/usr/bin/env python3
"""
NotLetters CLI
  python3 notletters.py balance
  python3 notletters.py letters "user@example.com:<mailbox-password>"
  python3 notletters.py codes   "user@example.com:<mailbox-password>"
  python3 notletters.py watch   "user@example.com:<mailbox-password>" [--interval=10]
"""

import json, os, re, sys, time, subprocess
from datetime import datetime

# API key is managed globally by Hermes env/dashboard.
API_KEY = os.environ.get("NOTLETTERS_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit(
        "NOTLETTERS_API_KEY is not set. Add it in Hermes dashboard or ~/.hermes/.env."
    )
API_BASE = "https://api.notletters.com"
# Строим через конкатенацию — не f-string, чтобы агент не замаскировал ключ
AUTH_HDR = ["Authorization: Bearer " + API_KEY]


def curl(method, endpoint, payload=None):
    args = ["curl", "-s", "-X", method.upper(),
            f"{API_BASE}/{endpoint}",
            "-H", AUTH_HDR[0],
            "-H", "Content-Type: application/json"]
    if payload:
        args += ["-d", json.dumps(payload)]
    r = subprocess.run(args, capture_output=True, text=True)
    return json.loads(r.stdout)


def get_balance():
    d = curl("GET", "v1/me").get("data", {})
    print(f"Аккаунт : {d.get('username','?')}")
    print(f"Баланс  : {d.get('balance','?')} руб")
    print(f"Лимит   : {d.get('rate_limit','?')} req/s")


def fetch_letters(email, password, search=""):
    payload = {"email": email, "password": password}
    if search:
        payload["filters"] = {"search": search}
    return curl("POST", "v1/letters", payload)


def find_codes(text, digits=None):
    """digits=6 для OTP, digits=None для любых 4-8 значных"""
    if digits:
        return re.findall(rf'\b\d{{{digits}}}\b', text)
    return re.findall(r'\b\d{4,8}\b', text)


def wait_for_code(email, password, sender_filter="openai", timeout_sec=120):
    """Ждёт письмо от sender_filter, возвращает первый 6-значный код."""
    for _ in range(timeout_sec // 5):
        data = fetch_letters(email, password)
        for l in data.get("data", {}).get("letters", []):
            ts = l.get("date", 0)
            sender = l.get("sender", "")
            if time.time() - ts < 300 and sender_filter in sender.lower():
                codes = find_codes(l["letter"].get("text", ""), digits=6)
                if codes:
                    return codes[0]
        time.sleep(5)
    return None


def print_letters(email, data, codes_only=False):
    if "error" in data:
        print(f"  Ошибка [{email}]: {data['error']}")
        return
    letters = data.get("data", {}).get("letters", [])
    if not letters:
        if not codes_only:
            print("  Писем нет.")
        return
    for l in letters:
        dt = datetime.fromtimestamp(l["date"]).strftime("%Y-%m-%d %H:%M:%S")
        text = l["letter"].get("text", "").strip()
        codes = find_codes(text)
        if codes_only:
            if codes:
                print(f"[{dt}] {email} | {l['subject']}")
                print(f"         КОД: {', '.join(codes)}")
        else:
            print(f"\n  Дата : {dt}")
            print(f"  От   : {l.get('sender_name','?')} <{l['sender']}>")
            print(f"  Тема : {l['subject']}")
            if codes:
                print(f"  КОД  : {', '.join(codes)}")
            print(f"  Текст: {text[:600]}")


def parse_creds(args):
    creds = []
    for a in args:
        if a.startswith("--"):
            continue
        if ":" in a:
            e, p = a.split(":", 1)
            creds.append((e, p))
        else:
            print(f"Неверный формат (нужно email:pass): {a}")
    return creds


def watch(creds, interval=10):
    print(f"Мониторинг {len(creds)} ящик(ов), каждые {interval}с. Ctrl+C — стоп.")
    seen = {c[0]: set() for c in creds}
    for email, password in creds:
        data = fetch_letters(email, password)
        for l in data.get("data", {}).get("letters", []):
            seen[email].add(l["id"])
    print("Инициализация завершена, слежу за новыми...")
    while True:
        time.sleep(interval)
        for email, password in creds:
            data = fetch_letters(email, password)
            for l in data.get("data", {}).get("letters", []):
                if l["id"] not in seen[email]:
                    seen[email].add(l["id"])
                    dt = datetime.fromtimestamp(l["date"]).strftime("%H:%M:%S")
                    text = l["letter"].get("text", "")
                    codes = find_codes(text)
                    code_str = f"  => КОД: {', '.join(codes)}" if codes else ""
                    print(f"[{dt}] НОВОЕ | {email} | {l['subject']}{code_str}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == "balance":
        get_balance()
    elif cmd in ("letters", "l"):
        creds = parse_creds(rest)
        for email, password in creds:
            print(f"\n{'='*60}\nЯЩИК: {email}\n{'='*60}")
            data = fetch_letters(email, password)
            print_letters(email, data, codes_only=False)
    elif cmd in ("codes", "c"):
        creds = parse_creds(rest)
        for email, password in creds:
            data = fetch_letters(email, password)
            print_letters(email, data, codes_only=True)
    elif cmd == "watch":
        interval = 10
        for a in rest:
            if a.startswith("--interval="):
                interval = int(a.split("=")[1])
        creds = parse_creds(rest)
        if not creds:
            print("Нужны creds: email:pass")
            sys.exit(1)
        try:
            watch(creds, interval)
        except KeyboardInterrupt:
            print("\nОстановлено.")
    else:
        print(f"Неизвестная команда: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
