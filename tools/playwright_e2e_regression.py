import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

# Config
BASE_URL = os.environ.get("LORE_WEB_PROBE_BASE_URL", "http://127.0.0.1:5000")
EVIDENCE = []
FAILURES = []


def log_evidence(check, status, details, screenshot=None):
    EVIDENCE.append(
        {
            "check": check,
            "status": status,
            "details": details,
            "screenshot": screenshot,
        }
    )
    if status == "FAIL":
        FAILURES.append(check)


def capture_console_and_network(page):
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(f"Console error: {msg.text}")

    def on_request_failed(request):
        errors.append(f"Network failed: {request.url}")

    page.on("console", on_console)
    page.on("requestfailed", on_request_failed)
    return errors


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        errors = capture_console_and_network(page)

        # (a) Sessions provider filter controls
        page.goto(f"{BASE_URL}/sessions", wait_until="networkidle")
        try:
            select = page.locator('select[name="tool"]')
            apply_btn = page.get_by_role("button", name=re.compile("apply", re.I))
            expect(select).to_be_visible()
            expect(apply_btn).to_be_visible()
            # Change provider to gemini-cli
            select.select_option("gemini-cli")
            expect(select).to_have_value("gemini-cli")
            apply_btn.click()
            page.wait_for_url(re.compile(r"tool=gemini-cli"))
            # Assert select remains selected
            expect(select).to_have_value("gemini-cli")
            log_evidence(
                "(a) Sessions provider filter controls",
                "PASS",
                {
                    "url": page.url,
                    "heading": page.locator("h1, h2").first.text_content(),
                    "select_value": select.input_value(),
                    "console_errors": list(errors),
                },
            )
        except Exception as e:
            screenshot = "sessions-filter-fail.png"
            page.screenshot(path=screenshot)
            log_evidence(
                "(a) Sessions provider filter controls",
                "FAIL",
                {
                    "url": page.url,
                    "error": str(e),
                    "console_errors": list(errors),
                },
                screenshot=screenshot,
            )

        # (b) Dashboard links
        try:
            page.goto(f"{BASE_URL}/sessions", wait_until="networkidle")
            page.get_by_role("link", name=re.compile("Export Index", re.I)).click()
            expect(page).to_have_url(re.compile(r"/sessions"))
            # Click a session open link (first session in list)
            session_link = page.locator('a[href*="/sessions/"]').first
            session_link.click()
            expect(page).to_have_url(re.compile(r"/sessions/"))
            heading = page.locator("h1, h2").first.text_content()
            log_evidence(
                "(b) Dashboard links",
                "PASS",
                {"url": page.url, "heading": heading, "console_errors": list(errors)},
            )
        except Exception as e:
            screenshot = "dashboard-links-fail.png"
            page.screenshot(path=screenshot)
            log_evidence(
                "(b) Dashboard links",
                "FAIL",
                {"url": page.url, "error": str(e), "console_errors": list(errors)},
                screenshot=screenshot,
            )

        # (c) Sidebar links
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            page.get_by_role("link", name=re.compile("Rules", re.I)).click()
            expect(page).to_have_url(re.compile(r"/rules"))
            heading_rules = page.locator("h1, h2").first.text_content()
            page.get_by_role("link", name=re.compile("Threads", re.I)).click()
            expect(page).to_have_url(re.compile(r"/threads"))
            heading_threads = page.locator("h1, h2").first.text_content()
            log_evidence(
                "(c) Sidebar links",
                "PASS",
                {
                    "rules_url": page.url,
                    "rules_heading": heading_rules,
                    "threads_heading": heading_threads,
                    "console_errors": list(errors),
                },
            )
        except Exception as e:
            screenshot = "sidebar-links-fail.png"
            page.screenshot(path=screenshot)
            log_evidence(
                "(c) Sidebar links",
                "FAIL",
                {"url": page.url, "error": str(e), "console_errors": list(errors)},
                screenshot=screenshot,
            )

        # (d) Topbar search modal
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            search_btn = page.get_by_role("button", name=re.compile("search", re.I))
            search_btn.click()
            modal = page.locator("[role=dialog], .modal, .search-modal")
            expect(modal).to_be_visible()
            # Close modal (Escape)
            page.keyboard.press("Escape")
            expect(modal).not_to_be_visible()
            log_evidence(
                "(d) Topbar search modal",
                "PASS",
                {"modal_visible": False, "console_errors": list(errors)},
            )
        except Exception as e:
            screenshot = "search-modal-fail.png"
            page.screenshot(path=screenshot)
            log_evidence(
                "(d) Topbar search modal",
                "FAIL",
                {"error": str(e), "console_errors": list(errors)},
                screenshot=screenshot,
            )

        # (e) Theme and density toggles
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            # Density toggle
            density_btn = page.get_by_role("button", name=re.compile("Comfortable|Density", re.I))
            density_btn.click()
            # Theme toggle
            theme_btn = page.get_by_role("button", name=re.compile("◐|Theme", re.I))
            theme_btn.click()
            # Check DOM class and localStorage
            html_class = page.evaluate("document.documentElement.className")
            theme = page.evaluate("window.localStorage.getItem('theme')")
            log_evidence(
                "(e) Theme and density toggles",
                "PASS",
                {
                    "html_class": html_class,
                    "theme": theme,
                    "console_errors": list(errors),
                },
            )
        except Exception as e:
            screenshot = "theme-density-fail.png"
            page.screenshot(path=screenshot)
            log_evidence(
                "(e) Theme and density toggles",
                "FAIL",
                {"error": str(e), "console_errors": list(errors)},
                screenshot=screenshot,
            )

        browser.close()

    # Print matrix
    print("\nE2E Regression Matrix:")
    for ev in EVIDENCE:
        print(f"{ev['check']}: {ev['status']}")
        for k, v in ev["details"].items():
            print(f"  {k}: {v}")
        if ev["screenshot"]:
            print(f"  Screenshot: {ev['screenshot']}")
        print()
    if FAILURES:
        print("FAILURES:", FAILURES)
        sys.exit(1)
    else:
        print("All checks passed.")


if __name__ == "__main__":
    run()
