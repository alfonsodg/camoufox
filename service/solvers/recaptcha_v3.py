"""reCAPTCHA v3 solver — uses real Camoufox browser for high-score tokens."""

import asyncio
import logging

log = logging.getLogger("solver.recaptcha")


async def solve_recaptcha_v3(pool, req) -> dict:
    inst = await pool.acquire(timeout=req.timeout)
    try:
        context = await inst.new_context()
        page = await context.new_page()
        try:
            await page.goto(req.url, wait_until="networkidle", timeout=req.timeout * 1000)

            # Wait for reCAPTCHA script to load
            await page.wait_for_function(
                "typeof grecaptcha !== 'undefined' && typeof grecaptcha.execute === 'function'",
                timeout=10000,
            )

            sitekey = req.sitekey
            if not sitekey:
                # Auto-detect sitekey from page
                sitekey = await page.evaluate("""
                    () => {
                        const script = document.querySelector('script[src*="recaptcha"][src*="render="]');
                        if (script) {
                            const m = script.src.match(/render=([^&]+)/);
                            if (m) return m[1];
                        }
                        const el = document.querySelector('[data-sitekey]');
                        if (el) return el.getAttribute('data-sitekey');
                        return null;
                    }
                """)
                if not sitekey:
                    raise ValueError("Could not detect reCAPTCHA sitekey")

            # Execute reCAPTCHA v3 — this generates a high-score token
            token = await page.evaluate(
                """
                async ({sitekey, action}) => {
                    return await new Promise((resolve, reject) => {
                        grecaptcha.ready(() => {
                            grecaptcha.execute(sitekey, {action})
                                .then(resolve)
                                .catch(reject);
                        });
                    });
                }
                """,
                {"sitekey": sitekey, "action": req.action},
            )

            cookies = await context.cookies()
            ua = await page.evaluate("navigator.userAgent")

            log.info("reCAPTCHA v3 solved: token=%s... (%d chars)", token[:30], len(token))
            return {
                "token": token,
                "cookies": {c["name"]: c["value"] for c in cookies},
                "user_agent": ua,
            }
        finally:
            await context.close()
    finally:
        await pool.release(inst)
