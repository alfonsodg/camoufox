"""Browser pool — manages reusable Camoufox instances."""

import asyncio
import logging
import os

from camoufox.async_api import AsyncCamoufox

log = logging.getLogger("solver.pool")

POOL_SIZE = int(os.getenv("POOL_SIZE", "2"))
MAX_USES = int(os.getenv("MAX_USES_PER_INSTANCE", "50"))


class BrowserInstance:
    def __init__(self):
        self.browser = None
        self.camoufox = None
        self.uses = 0
        self.lock = asyncio.Lock()

    async def start(self):
        self.camoufox = AsyncCamoufox(headless=True)
        self.browser = await self.camoufox.__aenter__()
        self.uses = 0
        log.info("Browser instance started")

    async def stop(self):
        if self.camoufox:
            try:
                await self.camoufox.__aexit__(None, None, None)
            except Exception:
                pass
        self.browser = None
        self.camoufox = None

    async def new_context(self):
        self.uses += 1
        return await self.browser.new_context()

    @property
    def needs_recycle(self):
        return self.uses >= MAX_USES

    @property
    def is_available(self):
        return not self.lock.locked()


class BrowserPool:
    def __init__(self):
        self.size = POOL_SIZE
        self.instances: list[BrowserInstance] = []
        self.total_solves = 0
        self._queue: asyncio.Queue[BrowserInstance] = asyncio.Queue()

    async def start(self):
        for _ in range(self.size):
            inst = BrowserInstance()
            await inst.start()
            self.instances.append(inst)
            await self._queue.put(inst)

    async def stop(self):
        for inst in self.instances:
            await inst.stop()
        self.instances.clear()

    @property
    def available(self):
        return self._queue.qsize()

    @property
    def busy(self):
        return self.size - self.available

    async def acquire(self, timeout: int = 30) -> BrowserInstance:
        inst = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        if inst.needs_recycle:
            log.info("Recycling instance after %d uses", inst.uses)
            await inst.stop()
            await inst.start()
        return inst

    async def release(self, inst: BrowserInstance):
        self.total_solves += 1
        await self._queue.put(inst)
