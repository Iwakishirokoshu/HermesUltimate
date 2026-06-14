#!/usr/bin/env python3
"""
ChatGPT login + SheerID student verification template.
Usage: CLOAKBROWSER_BINARY_PATH=~/.cloakbrowser/chromium-146.0.7680.177.5/chrome python3 this.py
"""
import json, re, subprocess, time, os
from cloakbrowser import launch_persistent_context

EMAIL = os.environ.get("REGISTRATION_EMAIL", "user@example.com")
EMAIL_PASS = os.environ.get("REGISTRATION_EMAIL_PASSWORD", "")
PROFILE_DIR = "/tmp/chatgpt_profile"
DOCS_DIR    = os.path.expanduser("~/myfiles")  # directory with SheerID document images

NL_KEY = os.environ.get("NOTLETTERS_API_KEY", "").strip()
if not NL_KEY:
    raise SystemExit("NOTLETTERS_API_KEY is not set. Add it in Hermes dashboard or ~/.hermes/.env.")
if not EMAIL_PASS:
    raise SystemExit("REGISTRATION_EMAIL_PASSWORD is not set.")
NL_AUTH = "Authorization: Bearer " + NL_KEY


def nl_letters():
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://api.notletters.com/v1/letters",
         "-H", NL_AUTH, "-H", "Content-Type: application/json",
         "-d", json.dumps({"email": EMAIL, "password": EMAIL_PASS})],
        capture_output=True, text=True)
    return json.loads(r.stdout).get("data", {}).get("letters", [])


def wait_otp(sender_kw="openai", max_age=300, retries=15, delay=5):
    for _ in range(retries):
        for l in nl_letters():
            if time.time() - l["date"] < max_age and sender_kw in l["sender"].lower():
                codes = re.findall(r'\b\d{6,8}\b', l["letter"].get("text", ""))
                if codes:
                    return codes[0]
        time.sleep(delay)
    return None


def wait_sheerid_link(max_age=600, retries=12, delay=15):
    for _ in range(retries):
        for l in nl_letters():
            if time.time() - l["date"] < max_age:
                html = l["letter"].get("html", "") + l["letter"].get("text", "")
                links = re.findall(r'https?://[^\s"<>]+sheerid[^\s"<>]+', html)
                if links:
                    return links[0]
        time.sleep(delay)
    return None


def ss(page, name):
    page.screenshot(path=f"/tmp/{name}.png")


def main():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    jpgs = sorted([os.path.join(DOCS_DIR, f) for f in os.listdir(DOCS_DIR) if f.lower().endswith(".jpg")])

    ctx = launch_persistent_context(
        PROFILE_DIR, headless=True,
        args=["--fingerprint=54321", "--fingerprint-platform=windows"],
        locale="en-US", timezone="America/Chicago",
        viewport={"width": 1366, "height": 768},
    )
    page = ctx.new_page()

    # ── Step 1: Login ─────────────────────────────────────────────────────────
    page.goto("https://auth.openai.com/log-in?screen_hint=login", wait_until="domcontentloaded")
    time.sleep(2)
    if "session has ended" in page.content().lower():
        page.locator("a:has-text('Log in')").click(); time.sleep(2)

    page.wait_for_selector("input[name='email']", timeout=10000)
    email_el = page.locator("input[name='email']")
    email_el.fill(EMAIL); time.sleep(0.5)
    # IMPORTANT: press Enter, not click Continue — avoids Google OAuth button
    email_el.press("Enter"); time.sleep(2)
    ss(page, "01_after_email")

    page.wait_for_selector("input[name='code'], input[placeholder='Code']", timeout=15000)
    code = wait_otp("openai")
    assert code, "No OTP received"
    page.locator("input[name='code'], input[placeholder='Code']").first.fill(code)
    page.locator("button:has-text('Continue')").first.click()
    page.wait_for_url("**/chatgpt.com/**", timeout=15000)
    time.sleep(2)

    # ── Step 2: SheerID form ──────────────────────────────────────────────────
    page.goto("https://chatgpt.com/codex/offers/students", wait_until="domcontentloaded")
    time.sleep(4)
    page.wait_for_selector("button[aria-label='Open menu']", timeout=20000)

    # Country → United States
    page.locator("button[aria-label='Open menu']").first.click(); time.sleep(0.5)
    page.locator("[role='option']:has-text('United States')").first.click(); time.sleep(0.8)

    # School
    page.get_by_label("School").type("Tarrant County", delay=80); time.sleep(1.5)
    page.locator("[role='option']:has-text('Tarrant County College District')").first.click(); time.sleep(0.5)

    # Names
    page.get_by_label("First name").fill("Snizhana")
    page.get_by_label("Last name").fill("Dzyuba")

    # DOB
    page.locator("button[aria-label='Open menu']").nth(1).click(); time.sleep(0.4)
    page.locator("[role='option']:has-text('February')").first.click(); time.sleep(0.3)
    page.get_by_placeholder("Day").fill("20")
    page.get_by_placeholder("Year").fill("2003")

    # Email
    page.get_by_label("Email address").fill(EMAIL)
    ss(page, "02_form_filled")

    page.locator("button:has-text('Verify my student status')").click()
    time.sleep(5); ss(page, "03_after_submit")

    # ── Step 3: Doc upload ────────────────────────────────────────────────────
    doc_link = wait_sheerid_link()
    if doc_link:
        page.goto(doc_link, wait_until="domcontentloaded"); time.sleep(3)

    file_inputs = page.locator("input[type='file']").all()
    for idx, fi in enumerate(file_inputs):
        if idx < len(jpgs):
            fi.set_input_files(jpgs[idx]); time.sleep(1)
    time.sleep(2); ss(page, "04_after_upload")

    page.locator("button:has-text('Submit'), button[type='submit']").first.click()
    time.sleep(5); ss(page, "05_submitted")

    # ── Step 4: Poll status ───────────────────────────────────────────────────
    for chk in range(5):
        time.sleep(300)
        page.reload(); time.sleep(2)
        content = page.content().lower()
        hits = [w for w in ["approved", "congratulations", "rejected", "pending"] if w in content]
        ss(page, f"poll_{chk+1}")
        print(f"[poll {chk+1}] hits={hits}")
        if any(w in hits for w in ["approved", "congratulations"]):
            print("APPROVED!"); break
        elif "rejected" in hits:
            print("Rejected."); break

    ctx.close()


if __name__ == "__main__":
    main()
