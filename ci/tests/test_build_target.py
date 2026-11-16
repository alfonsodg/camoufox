"""browser/scripts/patch.py takes its build target from BUILD_TARGET, defaulting to the documented Linux x86_64 build."""

from __future__ import annotations

import os
import subprocess
import sys

from ci._util import BROWSER_ROOT

SCRIPTS = BROWSER_ROOT / "scripts"


def _build_target(tmp_path, build_target):
    """extract_build_target() as patch.py sees it, with BUILD_TARGET set to `build_target` or unset."""
    env = {k: v for k, v in os.environ.items() if k != "BUILD_TARGET"}
    if build_target is not None:
        env["BUILD_TARGET"] = build_target
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['patch.py', '1.0', '1']; "
        "import patch; print(','.join(patch.extract_build_target()))"
    )
    return subprocess.run(
        [sys.executable, "-c", code, str(SCRIPTS)],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )


def test_an_unset_build_target_is_the_documented_linux_build(tmp_path):
    proc = _build_target(tmp_path, None)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "linux,x86_64"


def test_an_explicit_build_target_is_used(tmp_path):
    proc = _build_target(tmp_path, "macos,arm64")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "macos,arm64"
