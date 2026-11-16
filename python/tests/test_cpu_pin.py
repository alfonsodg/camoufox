"""CPU pinning happens only when the caller asked for it, and a failed pin is reported.

pin_cpu_cores is off by default. The decision travels with the launch options
(launch_options marks them), so options passed back as from_options pin, or do
not, exactly as the options that built them said.
"""

import asyncio
from contextlib import contextmanager
from unittest import mock

import orjson
import pytest

from camoufox import async_api, cpu_affinity, sync_api, utils
from camoufox import fingerprints as fp

HOST_CORES = 15  # not in PLAUSIBLE_CORE_COUNTS: the snapped count is 14


@contextmanager
def _host():
    with mock.patch.object(utils, "get_screen_cons", lambda headless: None), (
        mock.patch.object(utils, "has_display", lambda env: False)
    ), mock.patch.object(utils, "installed_verstr", lambda: "150.0.2"), (
        mock.patch.object(utils, "launch_path", lambda **kwargs: "/nonexistent/camoufox")
    ):
        yield


@pytest.fixture
def host15(monkeypatch):
    monkeypatch.setattr(cpu_affinity, "supported", lambda: True)
    monkeypatch.setattr(cpu_affinity, "host_cores", lambda: list(range(HOST_CORES)))
    monkeypatch.setattr(fp, "host_cpu_count", lambda: HOST_CORES)


def _options(**kwargs):
    with _host():
        return utils.launch_options(os="linux", headless=True, i_know_what_im_doing=True, **kwargs)


def _reported(options):
    chunks = sorted((int(k.rsplit("_", 1)[1]), v) for k, v in options["env"].items() if k.startswith("CAMOU_CONFIG_"))
    return orjson.loads("".join(v for _, v in chunks))["navigator.hardwareConcurrency"]


def test_options_built_without_pinning_are_not_pinned(host15):
    options = _options()
    assert _reported(options) == 14
    assert utils.pinned_core_count(options) is None


def test_options_built_with_pinning_are_pinned_to_the_reported_count(host15):
    options = _options(pin_cpu_cores=True)
    assert utils.pinned_core_count(options) == _reported(options) < HOST_CORES


def test_sync_launch_without_pinning_leaves_affinity_alone(host15, monkeypatch):
    class Browser:
        pass

    launched = Browser()

    class Firefox:
        launch = staticmethod(lambda **kw: launched)

    class Playwright:
        firefox = Firefox()

    def forbidden(*args):
        raise AssertionError("affinity touched")

    monkeypatch.setattr(utils, "driver_pid", forbidden)
    monkeypatch.setattr(cpu_affinity, "pin", forbidden)
    monkeypatch.setattr(sync_api, "host_identity", lambda *a: None)
    monkeypatch.setattr(sync_api, "attach_context_defaults", lambda *a: None)
    monkeypatch.setattr(sync_api, "sync_attach_vd", lambda browser, vd: browser)
    assert sync_api._launch(Playwright(), None, True, _options(), False, None, {}) is launched


def test_async_launch_without_pinning_takes_no_lock(host15, monkeypatch):
    def forbidden(*args):
        raise AssertionError("pin lock or affinity touched")

    async def launched(*args):
        return "browser"

    monkeypatch.setattr(utils, "driver_pid", forbidden)
    monkeypatch.setattr(async_api, "_pin_lock", forbidden)
    monkeypatch.setattr(async_api, "_launch", launched)
    result = asyncio.run(async_api._new_browser(object(), None, True, _options(), False, None, {}))
    assert result == "browser"
