#!/usr/bin/env python3
"""
SheerID student form fill — verified working pattern.
Uses exact DOM IDs. For OpenAI Codex Student offer (program 69b1aafc617d5165c65f8173).
Key fixes over naive approach:
  - Year must use type() not fill() — React clips fill() to 1 char
  - Month is a combobox dropdown, not a <select>
  - School is disabled until Country is selected
  - get_by_label("School"/"Month") causes strict mode violation (2 elements)
"""
import time


def fill_sheerid_form(page, first_name, last_name, dob_month, dob_day, dob_year, email):
    """
    Fill the SheerID student verification form.
    dob_month: full name e.g. "February"
    dob_day, dob_year: strings e.g. "20", "2003"
    """
    # 1. Country
    page.locator("#sid-country").click()
    page.locator("#sid-country").type("United States", delay=80)
    time.sleep(2)
    page.locator("[role='option']:has-text('United States')").first.click()
    time.sleep(1.5)

    # 2. School — wait for enabled (depends on Country)
    page.wait_for_function(
        "() => !document.getElementById('sid-college-name')?.disabled",
        timeout=10000
    )
    page.locator("#sid-college-name").click()
    time.sleep(0.5)
    page.locator("#sid-college-name").type("Tarrant County", delay=85)
    time.sleep(3)
    # Select first autocomplete option = Tarrant County College District, Fort Worth TX
    page.locator("[role='option']").first.click()
    time.sleep(1)

    # 3. Names
    page.locator("#sid-first-name").fill(first_name)
    time.sleep(0.2)
    page.locator("#sid-last-name").fill(last_name)
    time.sleep(0.2)

    # 4. Month — combobox, NOT a <select>
    page.locator("#sid-birthdate__month").click()
    page.wait_for_selector("#sid-birthdate__month-menu [role='option']", timeout=5000)
    found_month = False
    for opt in page.locator("#sid-birthdate__month-menu [role='option']").all():
        if dob_month in opt.text_content():
            opt.click()
            found_month = True
            break
    if not found_month:
        # Fallback: click second option (February = index 1)
        opts = page.locator("#sid-birthdate__month-menu [role='option']").all()
        month_names = ["January","February","March","April","May","June",
                       "July","August","September","October","November","December"]
        idx = month_names.index(dob_month) if dob_month in month_names else 1
        if idx < len(opts):
            opts[idx].click()
    time.sleep(0.4)

    # 5. Day
    page.locator("#sid-birthdate-day").fill(dob_day)
    time.sleep(0.2)

    # 6. Year — CRITICAL: fill() clips to 1 char due to React. Use type() instead.
    page.locator("#sid-birthdate-year").click()
    page.locator("#sid-birthdate-year").press("Control+a")
    page.locator("#sid-birthdate-year").type(dob_year, delay=50)
    time.sleep(0.2)

    # 7. Email
    page.locator("#sid-email").fill(email)
    time.sleep(0.3)

    # 8. Submit — wait for enabled
    page.wait_for_function(
        "() => !document.getElementById('sid-submit-wrapper__collect-info')?.disabled",
        timeout=5000
    )
    page.locator("#sid-submit-wrapper__collect-info").click()
    time.sleep(5)


# Example usage:
# fill_sheerid_form(page, "Snizhana", "Dzyuba", "February", "20", "2003", "user@example.com")
