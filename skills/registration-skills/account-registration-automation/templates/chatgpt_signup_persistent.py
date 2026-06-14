#!/usr/bin/env python3
"""
ChatGPT fresh account registration via CloakBrowser launch_persistent_context.
Keeps browser open after registration for follow-up tasks via cmd-file injection.

Usage:
  CLOAKBROWSER_BINARY_PATH="$HOME/.cloakbrowser/chromium-146.0.7680.177.5/chrome" \
    # OLD: /home/hermes/.venv/bin/python3 chatgpt_signup_persistent.py

Status written to:  /tmp/chatgpt_status.txt
Next cmd injected:  /tmp/chatgpt_next_cmd.py  (agent writes here; script picks up and exec's)
"""
import time, os, re, json, subprocess, sys, traceback
from cloakbrowser import launch_persistent_context

PROFILE_DIR = "/tmp/chatgpt_profile"
EMAIL = os.environ.get("REGISTRATION_EMAIL", "user@example.com")
PASS = os.environ.get("REGISTRATION_EMAIL_PASSWORD", "")
STATUS_FILE = "/tmp/chatgpt_status.txt"
CMD_FILE    = "/tmp/chatgpt_next_cmd.py"

def write_status(msg):
    with open(STATUS_FILE, "w") as f:
        f.write(msg + "\n")
    print(f"[STATUS] {msg}", flush=True)

def fetch_letters():
    key = os.environ.get("NOTLETTERS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("NOTLETTERS_API_KEY is not set. Add it in Hermes dashboard or ~/.hermes/.env.")
    if not PASS:
        raise RuntimeError("REGISTRATION_EMAIL_PASSWORD is not set.")
    auth = "Authorization: Bearer " + key
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "https://api.notletters.com/v1/letters",
         "-H", auth,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"email": EMAIL, "password": PASS})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("letters", [])

def wait_for_otp(sender_kw="openai", timeout=120, interval=5):
    seen = {l["id"] for l in fetch_letters()}
    write_status(f"WAITING_OTP: polling (timeout={timeout}s)...")
    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        for l in fetch_letters():
            if l["id"] in seen:
                continue
            seen.add(l["id"])
            if sender_kw.lower() not in l.get("sender", "").lower():
                continue
            text = l["letter"].get("text", "") + " " + l["letter"].get("html", "")
            codes = re.findall(r'\b\d{6,8}\b', text)
            if codes:
                write_status(f"OTP_FOUND: {codes[0]}")
                return codes[0]
    return None

# ── Launch ──────────────────────────────────────────────────────────────────
write_status("INIT: launching CloakBrowser...")
ctx = launch_persistent_context(
    PROFILE_DIR,
    headless=True,
    humanize=True,
    locale="en-US",
    timezone="America/Chicago",
    args=["--fingerprint=47382", "--fingerprint-platform=windows"],
)
page = ctx.new_page()

try:
    # 1. Navigate to chatgpt.com
    write_status("NAV: chatgpt.com")
    page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
    time.sleep(3)

    # 2. Click Sign up
    page.locator("button:has-text('Sign up')").first.click()
    write_status("CLICK: Sign up")
    time.sleep(2)

    # 3. Email
    page.wait_for_selector("input[name='email']", timeout=10000)
    email_el = page.locator("input[name='email']")
    email_el.fill(EMAIL)
    time.sleep(0.5)
    email_el.press("Enter")  # NEVER click Continue — catches Google OAuth
    write_status("FILL: email submitted")
    time.sleep(2)

    # 4. OTP
    page.wait_for_selector(
        "input[name='code'], input[autocomplete='one-time-code'], input[placeholder='Code']",
        timeout=20000
    )
    write_status("OTP: input field visible, fetching code...")
    otp = wait_for_otp(sender_kw="openai", timeout=120)
    if not otp:
        write_status("ERROR: OTP not received")
        sys.exit(1)
    page.locator(
        "input[name='code'], input[autocomplete='one-time-code'], input[placeholder='Code']"
    ).first.fill(otp)
    page.locator(
        "input[name='code'], input[autocomplete='one-time-code'], input[placeholder='Code']"
    ).first.press("Enter")
    write_status(f"OTP: entered {otp}")
    time.sleep(3)

    # 5. Name + age (page: "How old are you?")
    try:
        page.wait_for_selector("input[name='name']", timeout=8000)
        page.locator("input[name='name']").first.fill("Alex Johnson")
        time.sleep(0.3)
        # DOB: try year field first
        for sel, val in [("input[name='year']", "1998"),
                         ("input[name='month']", "6"),
                         ("input[name='day']", "15")]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=1000):
                    el.fill(val)
                    time.sleep(0.2)
            except:
                pass
        page.locator("button:has-text('Finish creating account'), button:has-text('Continue')").first.click()
        time.sleep(3)
        write_status(f"ABOUT: name+age submitted, url={page.url}")
    except Exception as e:
        write_status(f"ABOUT: step skipped ({e})")

    # 6. Verify
    try:
        page.wait_for_url("*chatgpt.com*", timeout=15000)
    except:
        pass
    write_status(f"RESULT: url={page.url} title={page.title()}")
    if "chatgpt.com" in page.url and "/auth" not in page.url:
        write_status("SUCCESS: registered and on chatgpt.com!")

except Exception as e:
    write_status(f"EXCEPTION: {e}\n{traceback.format_exc()}")

# ── Keep browser alive for follow-up commands ────────────────────────────────
write_status("IDLE: waiting for commands at /tmp/chatgpt_next_cmd.py")
while True:
    if os.path.exists(CMD_FILE):
        code = open(CMD_FILE).read()
        os.remove(CMD_FILE)
        write_status(f"EXEC: {code[:60].strip()}...")
        try:
            exec(code, {"page": page, "ctx": ctx, "time": time,
                        "write_status": write_status, "fetch_letters": fetch_letters,
                        "wait_for_otp": wait_for_otp})
            write_status("CMD_DONE")
        except Exception as e:
            write_status(f"CMD_ERROR: {e}\n{traceback.format_exc()}")
    time.sleep(2)
