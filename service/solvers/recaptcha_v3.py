"""reCAPTCHA v3 solver — uses Chromium (reCAPTCHA blocks Firefox/Camoufox patches)."""

import logging

from playwright.async_api import async_playwright

log = logging.getLogger("solver.recaptcha")

# Shared playwright instance for Chromium
_pw = None
_chromium = None


async def _get_chromium():
    global _pw, _chromium
    if _chromium is None:
        _pw = await async_playwright().start()
        _chromium = await _pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        log.info("Chromium launched for reCAPTCHA solving")
    return _chromium


async def solve_recaptcha_v3(pool, req) -> dict:
    """Solve reCAPTCHA v3 using Chromium (Camoufox's Firefox patches block grecaptcha)."""
    browser = await _get_chromium()    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    try:
        await page.goto(req.url, wait_until="networkidle", timeout=req.timeout * 1000)

        sitekey = req.sitekey
        if not sitekey:
            sitekey = await page.evaluate("""() => {
                const s = document.querySelector('script[src*="recaptcha"][src*="render="]');
                if (s) { const m = s.src.match(/render=([^&]+)/); if (m) return m[1]; }
                return null;
            }""")
            if not sitekey:
                raise ValueError("Could not detect reCAPTCHA sitekey")

        # Wait for grecaptcha.execute
        for _ in range(req.timeout):
            ready = await page.evaluate(
                "typeof grecaptcha !== 'undefined' && typeof grecaptcha.execute === 'function'"
            )
            if ready:
                break
            await page.wait_for_timeout(1000)
        else:
            raise ValueError("grecaptcha.execute not available")

        token = await page.evaluate(
            """({sitekey, action}) => new Promise((resolve, reject) =>
                grecaptcha.ready(() =>
                    grecaptcha.execute(sitekey, {action}).then(resolve).catch(reject)))""",
            {"sitekey": sitekey, "action": req.action},
        )

        cookies = await context.cookies()
        ua = await page.evaluate("navigator.userAgent")

        log.info("reCAPTCHA v3 solved: %d chars", len(token))
        return {
            "token": token,
            "cookies": {c["name"]: c["value"] for c in cookies},
            "user_agent": ua,
        }
    finally:
        await context.close()
