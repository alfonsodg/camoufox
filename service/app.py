"""Camoufox Solver Service — HTTP API for captcha/anti-bot bypass."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from service.pool import BrowserPool
from service.solvers.recaptcha_v3 import solve_recaptcha_v3
from service.solvers.cloudflare import solve_cloudflare_waf, solve_turnstile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("solver")

pool: BrowserPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = BrowserPool()
    await pool.start()
    log.info("Solver service ready, pool size: %d", pool.size)
    yield
    await pool.stop()


app = FastAPI(title="Camoufox Solver", version="0.1.0", lifespan=lifespan)


class SolveRequest(BaseModel):
    type: str = Field(..., description="Challenge type: recaptcha_v3, turnstile, cloudflare_waf")
    url: str = Field(..., description="Target page URL")
    sitekey: str | None = Field(None, description="Captcha sitekey (for recaptcha/turnstile)")
    action: str = Field("verify", description="reCAPTCHA action name")
    timeout: int = Field(30, description="Max solve time in seconds")


class SolveResponse(BaseModel):
    success: bool
    token: str | None = None
    cookies: dict | None = None
    user_agent: str | None = None
    solve_time_ms: int = 0
    error: str | None = None


SOLVERS = {
    "recaptcha_v3": solve_recaptcha_v3,
    "turnstile": solve_turnstile,
    "cloudflare_waf": solve_cloudflare_waf,
}


@app.post("/solve", response_model=SolveResponse)
async def solve(req: SolveRequest):
    if req.type not in SOLVERS:
        raise HTTPException(400, f"Unknown type: {req.type}. Supported: {list(SOLVERS)}")
    if pool is None:
        raise HTTPException(503, "Service not ready")

    start = time.monotonic()
    try:
        result = await SOLVERS[req.type](pool, req)
        elapsed = int((time.monotonic() - start) * 1000)
        return SolveResponse(success=True, solve_time_ms=elapsed, **result)
    except asyncio.TimeoutError:
        return SolveResponse(success=False, error="Timeout", solve_time_ms=req.timeout * 1000)
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        log.exception("Solve failed: %s", e)
        return SolveResponse(success=False, error=str(e), solve_time_ms=elapsed)


@app.get("/health")
async def health():
    if pool is None:
        return {"status": "starting"}
    return {
        "status": "ok",
        "pool_size": pool.size,
        "available": pool.available,
        "busy": pool.busy,
        "total_solves": pool.total_solves,
    }
