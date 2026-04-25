#!/bin/bash
# Quick test: solve reCAPTCHA v3 for SEACE directly
cd "$(dirname "$0")/.."

timeout 60 python3 << 'PYEOF'
import asyncio, time
from playwright.async_api import async_playwright

async def main():
    start = time.monotonic()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        print("1. Loading SEACE...")
        await page.goto("https://prod2.seace.gob.pe/seacebus-uiwd-pub/buscadorPublico/buscadorPublico.xhtml",
                        wait_until="networkidle", timeout=30000)
        
        print("2. Waiting for grecaptcha...")
        for i in range(15):
            if await page.evaluate("typeof grecaptcha?.execute === 'function'"): break
            await asyncio.sleep(1)
        
        print("3. Executing grecaptcha...")
        token = await page.evaluate("""
            () => new Promise(r => grecaptcha.ready(() =>
                grecaptcha.execute('6Lfhnb0pAAAAAB3RxPrOlihIByQUBjpZCAjX-cY2', {action:'search'}).then(r)))
        """)
        
        cookies = {c["name"]: c["value"] for c in await context.cookies()}
        elapsed = int((time.monotonic() - start) * 1000)
        
        print(f"\n✅ Token: {token[:60]}... ({len(token)} chars)")
        print(f"⏱  Time: {elapsed}ms")
        print(f"🍪 Cookies: {list(cookies.keys())}")
        
        # Now use the token to search SEACE
        print("\n4. Searching SEACE with token...")
        await page.click("text=Buscador de Procedimientos de Selección")
        await asyncio.sleep(1)
        
        await page.evaluate("""(token) => {
            document.querySelector('#tbBuscador\\\\:idFormBuscarProceso\\\\:tokenBusProSel').value = token;
            document.querySelector('#tbBuscador\\\\:idFormBuscarProceso\\\\:anioConvocatoria_input').value = '2025';
            const s = document.querySelector('#tbBuscador\\\\:idFormBuscarProceso\\\\:dfechaInicio_input');
            const e = document.querySelector('#tbBuscador\\\\:idFormBuscarProceso\\\\:dfechaFin_input');
            if (s) s.value = '24/04/2025';
            if (e) e.value = '24/04/2025';
        }""", token)
        
        # Click the hidden real search button
        await page.evaluate("""() => {
            const btn = document.querySelector('#tbBuscador\\\\:idFormBuscarProceso\\\\:btnBuscarSel');
            if (btn) { btn.style.display = 'block'; btn.click(); }
        }""")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(3)
        
        total = await page.evaluate("""() => {
            const p = document.querySelector('#tbBuscador\\\\:idFormBuscarProceso\\\\:dtProcesos_paginator_bottom .ui-paginator-current');
            return p ? p.textContent.trim() : 'not found';
        }""")
        print(f"   Results: {total}")
        
        rows = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('#tbBuscador\\\\:idFormBuscarProceso\\\\:dtProcesos_data tr[data-ri]'))
                .slice(0,5).map(tr => {
                    const c = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim());
                    return c.length >= 7 ? c[0]+'. '+c[1].substring(0,35)+' | '+c[6].substring(0,50) : '';
                });
        }""")
        for r in rows:
            print(f"   {r}")
        
        await browser.close()

asyncio.run(main())
PYEOF
