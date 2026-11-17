"""The browser renders at the identity's devicePixelRatio (#933)."""

import pytest

from camoufox import utils
from camoufox.fingerprints import Screen

from test_launch_environment import isolated_launch_dependencies  # noqa: F401

PREF = "layout.css.devPixelsPerPx"
WIN = {"navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0",
       "screen.width": 1382, "screen.height": 864, "window.outerWidth": 1280, "window.outerHeight": 900}


def prefs(dpr, **kwargs):
    return utils.launch_options(config={**WIN, "window.devicePixelRatio": dpr}, i_know_what_im_doing=True,
                                **{"headless": True, **kwargs})["firefox_user_prefs"]


def test_renders_at_the_claimed_scale(isolated_launch_dependencies):  # noqa: F811
    assert prefs(2.5)[PREF] == "2.5"
    assert prefs(1)[PREF] == "1"


def test_caller_pref_wins(isolated_launch_dependencies):  # noqa: F811
    assert prefs(2.5, firefox_user_prefs={PREF: "1.0"})[PREF] == "1.0"


def test_window_too_large_for_the_monitor_raises(monkeypatch, isolated_launch_dependencies):  # noqa: F811
    monkeypatch.setattr(utils, "OS_NAME", "lin")
    with pytest.raises(ValueError, match="needs 3200 pixels, but this monitor has 1920"):
        prefs(2.5, headless=False, screen=Screen(max_width=1920, max_height=1080))
    assert prefs(1.25, headless=False, screen=Screen(max_width=1920, max_height=1200))[PREF] == "1.25"


def test_a_non_step_scale_is_written_with_six_significant_digits(isolated_launch_dependencies):  # noqa: F811
    # typescript/tests/launch.test.ts asserts the same strings.
    assert prefs(1.0909090909)[PREF] == "1.09091"


def test_the_monitor_error_names_the_scale_with_six_significant_digits(monkeypatch, isolated_launch_dependencies):  # noqa: F811
    monkeypatch.setattr(utils, "OS_NAME", "lin")
    with pytest.raises(
        ValueError,
        match="window.outerWidth 1280 at display scale 1.09091 needs 1396.36 pixels, but this monitor has 1000",
    ):
        prefs(1.0909090909, headless=False, screen=Screen(max_width=1000, max_height=1080))
