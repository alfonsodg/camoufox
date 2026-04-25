"""Cloudflare Turnstile and WAF solvers."""

import asyncio
import logging

log = logging.getLogger("solver.cloudflare")


async def solve_turnstile(pool, req) -> dict:
    """Solve Cloudflare Turnstile challenge."""
    inst = await pool.acquire(timeout=req.timeout)
    try:
        context = await inst.new_context()
        page = await context.new_page()
        try:
            await page.goto(req.url, wait_until="networkidle", timeout=req.timeout * 1000)

            # Wait for Turnstile to auto-solve (Camoufox passes fingerprint checks)
            token = await page.evaluate(
                """
                async (timeout) => {
                    const deadline = Date.now() + timeout;
                    while (Date.now() < deadline) {
                        const input = document.querySelector('[name="cf-turnstile-response"]') ||
                                      document.querySelector('input[name="cf_turnstile_response"]');
                        if (input && input.value) return input.value;
                        await new Promise(r => setTimeout(r, 500));
                    }
                    return null;
                }
                """,
                req.timeout * 1000,
            )

            cookies = await context.cookies()
            ua = await page.evaluate("navigator.userAgent")

            if not token:
                raise ValueError("Turnstile did not solve within timeout")

            log.info("Turnstile solved: token=%s...", token[:30])
            return {
                "token": token,
                "cookies": {c["name"]: c["value"] for c in cookies},
                "user_agent": ua,
            }
        finally:
            await context.close()
    finally:
        await pool.release(inst)


async def solve_cloudflare_waf(pool, req) -> dict:
    """Solve Cloudflare WAF/5s challenge — wait for redirect and return cookies."""
    inst = await pool.acquire(timeout=req.timeout)
    try:
        context = await inst.new_context()
        page = await context.new_page()
        try:
            await page.goto(req.url, timeout=req.timeout * 1000)

            # Wait for Cloudflare challenge to pass (title changes from "Just a moment...")
            await page.wait_for_function(
                "document.title !== 'Just a moment...'",
                timeout=req.timeout * 1000,
            )
            await page.wait_for_load_state("networkidle")

            cookies = await context.cookies()
            ua = await page.evaluate("navigator.userAgent")
            final_url = page.url

            log.info("Cloudflare WAF solved: %s -> %s", req.url, final_url)
            return {
                "cookies": {c["name"]: c["value"] for c in cookies},
                "user_agent": ua,
            }
        finally:
            await context.close()
    finally:
        await pool.release(inst)
