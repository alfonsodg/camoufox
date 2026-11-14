"""The workflows reference every third-party action by commit, never by tag.

A tag moves; a commit does not. release.yml has always pinned this way, and
tests.yml runs pull-request code, so it matters at least as much there.
"""

from __future__ import annotations

import re

import pytest
import yaml

from ci._util import REPO_ROOT

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _steps(path):
    for job in yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"].values():
        yield from job.get("steps", [])


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_external_action_is_pinned_by_commit(path):
    unpinned = [
        s["uses"] for s in _steps(path)
        if "uses" in s and not s["uses"].startswith("./")
        and not FULL_SHA.match(s["uses"].partition("@")[2])
    ]
    assert not unpinned, f"{path.name} references actions by tag: {sorted(set(unpinned))}"


def test_a_checkout_in_tests_yml_does_not_persist_credentials():
    """No job in tests.yml pushes, so none needs the token left in .git/config."""
    path = REPO_ROOT / ".github" / "workflows" / "tests.yml"
    offenders = [
        s for s in _steps(path)
        if s.get("uses", "").startswith("actions/checkout@")
        and s.get("with", {}).get("persist-credentials") is not False
    ]
    assert not offenders, f"{len(offenders)} checkout(s) keep the token"


def test_run_scripts_in_tests_yml_do_not_interpolate_inputs():
    """An input spliced into a script is shell syntax; through env it is data."""
    path = REPO_ROOT / ".github" / "workflows" / "tests.yml"
    offenders = [s["run"] for s in _steps(path) if re.search(r"\$\{\{\s*inputs\.", s.get("run", ""))]
    assert not offenders, offenders
