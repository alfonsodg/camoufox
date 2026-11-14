"""An enforced run id and loud Playwright pin resolution (#27)."""

from __future__ import annotations

import urllib.error

import pytest

from ci import results, summarize, versions


# -- run_id is compared, not just recorded -----------------------------------


def _record(directory, run_id):
    record = results.GateResult(gate="pythonlib")
    record.run_id = run_id
    record.finish(results.PASS).save(directory)


def _summarize(tmp_path):
    return summarize.main(["--results-dir", str(tmp_path), "--require", "pythonlib"])


def test_evidence_from_another_run_does_not_satisfy_a_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "200")
    _record(tmp_path, "100")
    assert _summarize(tmp_path) == 1


def test_evidence_from_this_run_counts_across_attempts(tmp_path, monkeypatch):
    """A re-run keeps the first attempt's passing artifacts, under the same run id."""
    monkeypatch.delenv("HARNESS_RUN_ID", raising=False)
    monkeypatch.setenv("GITHUB_RUN_ID", "200")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    _record(tmp_path, results.run_id())
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    assert _summarize(tmp_path) == 0


def test_a_local_run_has_no_run_id_to_compare(tmp_path, monkeypatch):
    """Locally each gate is its own process, so there is nothing to compare against."""
    for name in ("HARNESS_RUN_ID", "GITHUB_RUN_ID"):
        monkeypatch.delenv(name, raising=False)
    _record(tmp_path, "local-elsewhere-1")
    assert _summarize(tmp_path) == 0


# -- tags that cannot be resolved are named ---------------------------------


def test_a_tag_whose_pin_cannot_be_read_is_named(monkeypatch, capsys):
    monkeypatch.setattr(versions, "released_tags", lambda: ["v1.62.0", "v1.61.0"])

    def fetch(url, **kw):
        if "v1.61.0" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return {"browsers": [{"name": "firefox", "browserVersion": "153.0"}]}

    monkeypatch.setattr(versions, "http_json", fetch)
    assert versions.pins() == [("v1.62.0", "153.0")]
    assert "v1.61.0" in capsys.readouterr().err


def test_ci_does_not_fall_back_to_the_built_in_table(monkeypatch):
    monkeypatch.setenv("CI", "true")

    def unreachable():
        raise urllib.error.URLError("rate limited")

    monkeypatch.setattr(versions, "released_tags", unreachable)
    with pytest.raises(SystemExit):
        versions.pins()


def test_a_local_run_falls_back_with_a_warning(monkeypatch, capsys):
    monkeypatch.delenv("CI", raising=False)

    def unreachable():
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(versions, "released_tags", unreachable)
    assert versions.pins() == list(versions.FALLBACK_PINS)
    assert "built-in table" in capsys.readouterr().err
