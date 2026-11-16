r"""
A navigation that fails to start leaves no observer behind.

`Page.navigate` (additions/juggler/protocol/PageHandler.js) registers a
`juggler-navigation-started-browser` observer to learn the navigation id, then
parses the URL and starts the load. It used to remove the observer only after
a load that started, so a URL the browser rejects left one registered for the
life of the browser, called on every later navigation start.

The guard counts that topic's observers through Marionette's chrome context
before and after goto() calls with a URL no browser parses, and checks that a
valid goto() still loads.

    python browser/tests/playwright/patches/navigate-observer-leak.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import Marionette, free_port, hidden_display, marionette_args, marionette_env, resolve_binary  # noqa: E402

TOPIC = "juggler-navigation-started-browser"
OBSERVERS = f'return Array.from(Services.obs.enumerateObservers("{TOPIC}")).length;'
REJECTED = 5


def main() -> int:
    from camoufox.sync_api import Camoufox
    from playwright.sync_api import Error

    port = free_port()
    failures = []
    with hidden_display(), Camoufox(
            headless=False, executable_path=str(resolve_binary()), args=marionette_args(), env=marionette_env(),
            firefox_user_prefs={"marionette.port": port}, i_know_what_im_doing=True) as browser:
        page = browser.new_page()
        m = Marionette(port)
        try:
            before = m.js(OBSERVERS)
            rejected = 0
            for _ in range(REJECTED):
                try:
                    page.goto("://not-a-url")
                except Error:
                    rejected += 1
            after = m.js(OBSERVERS)
            print(f"  observers on {TOPIC}: {before} before, {after} after {rejected} rejected goto() calls")
            if rejected != REJECTED:
                failures.append(f"only {rejected} of {REJECTED} goto() calls were rejected, so the check proves nothing")
            if after != before:
                failures.append(f"{after - before} navigation observers left behind by {rejected} rejected goto() calls")
            page.goto("data:text/html,<title>ok</title>")
            if page.title() != "ok":
                failures.append("a valid goto() no longer loads the page")
            if m.js(OBSERVERS) != before:
                failures.append("a valid goto() changed the observer count")
        finally:
            m.close()
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print("PASS: a navigation that fails to start leaves no observer behind")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
