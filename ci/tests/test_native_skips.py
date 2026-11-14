"""ci.run_native fails a skip that is not on its allowlist.

A prerequisite the runner image lacks (Xvfb) skipped its tests, and a skipped
test reads as green. Only the skips that are a measured outcome may stay.
"""

from __future__ import annotations

import json
from xml.sax.saxutils import quoteattr

import pytest

from ci import run_native
from ci._util import Result


def _run(tmp_path, monkeypatch, skips):
    """Run `--subset browser` against a stand-in pytest that skips with `skips`."""
    cases = "".join(
        f'<testcase classname="test_x" name="t{i}"><skipped message={quoteattr(reason)}/></testcase>'
        for i, reason in enumerate(skips)
    )
    monkeypatch.setattr(run_native, "WORK_DIR", tmp_path)

    def fake_pytest(**kw):
        kw["junit"].write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>")
        return Result(0, "", "")

    monkeypatch.setattr(run_native, "run_pytest", fake_pytest)
    binary = tmp_path / "camoufox-bin"
    binary.touch()
    code = run_native.main(
        ["--subset", "browser", "--binary", str(binary), "--results-dir", str(tmp_path / "out")]
    )
    saved = json.loads(next((tmp_path / "out").glob("*.json")).read_text())
    return code, saved


@pytest.mark.parametrize(
    "reason",
    [
        "Xvfb unavailable: Cannot find Xvfb",
        "Xvfb is not installed",
        "virtual display tests disabled for this run",
    ],
)
def test_a_skipped_prerequisite_fails_the_gate(tmp_path, monkeypatch, reason):
    code, saved = _run(tmp_path, monkeypatch, [reason])
    assert (code, saved["status"]) == (1, "fail")
    assert any(reason in note for note in saved["notes"])


@pytest.mark.parametrize(
    "reason",
    [
        "the browser was launched directly; there is no separate driver to kill",
        "no driver process in this build's tree",
        "fetch: growth stayed under the noise floor (0.1 MB at n=5, 0.2 MB at n=20)",
    ],
)
def test_the_measured_skips_still_skip(tmp_path, monkeypatch, reason):
    code, saved = _run(tmp_path, monkeypatch, [reason])
    assert (code, saved["status"]) == (0, "pass")
