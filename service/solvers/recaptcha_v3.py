"""reCAPTCHA v3 solver — uses real Camoufox browser for high-score tokens."""

import logging

log = logging.getLogger("solver.recaptcha")


async def solve_recaptcha_v3(pool, req) -> dict:
    inst = await pool.acquire(timeout=req.timeout)
    try:
        context = await inst.new_context()
        page = await context.new_page()
        try:
            await page.goto(req.url, wait_until="networkidle", timeout=req.timeout * 1000)

            sitekey = req.sitekey
            if not sitekey:
                sitekey = await page.evaluate("""
                    () => {
                        const s = document.querySelector('script[src*="recaptcha"][src*="render="]');
                        if (s) { const m = s.src.match(/render=([^&]+)/); if (m) return m[1]; }
                        const el = document.querySelector('[data-sitekey]');
                        return el ? el.getAttribute('data-sitekey') : null;
                    }
                """)
                if not sitekey:
                    raise ValueError("Could not detect reCAPTCHA sitekey")

            # reCAPTCHA v3 with render=SITEKEY loads grecaptcha differently.
            # We need to wait for it and handle both API styles.
            token = await page.evaluate(
                """
                async ({sitekey, action, timeout}) => {
                    const deadline = Date.now() + timeout;

                    // Wait for grecaptcha to be available
                    while (Date.now() < deadline) {
                        if (typeof grecaptcha !== 'undefined' && grecaptcha.execute) break;
                        // Also check grecaptcha.enterprise
                        if (typeof grecaptcha !== 'undefined' && grecaptcha.enterprise?.execute) break;
                        await new Promise(r => setTimeout(r, 300));
                    }

                    if (typeof grecaptcha === 'undefined') {
                        throw new Error('grecaptcha not loaded');
                    }

                    // Try enterprise API first, then standard
                    const executor = grecaptcha.enterprise?.execute || grecaptcha.execute;
                    if (!executor) throw new Error('No execute function found');

                    return await new Promise((resolve, reject) => {
                        const ready = grecaptcha.enterprise?.ready || grecaptcha.ready;
                        if (ready) {
                            ready(() => {
                                executor(sitekey, {action})
                                    .then(resolve)
                                    .catch(reject);
                            });
                        } else {
                            executor(sitekey, {action})
                                .then(resolve)
                                .catch(reject);
                        }
                    });
                }
                """,
                {"sitekey": sitekey, "action": req.action, "timeout": req.timeout * 1000},
            )

            if not token:
                raise ValueError("Empty token returned")

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
