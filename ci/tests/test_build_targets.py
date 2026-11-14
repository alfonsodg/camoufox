"""One table of supported build targets and one upstream.sh reader for the build scripts."""

import os
import subprocess
import sys

import pytest

from ci._util import BROWSER_ROOT, read_upstream_sh

sys.path.insert(0, str(BROWSER_ROOT))
sys.path.insert(0, str(BROWSER_ROOT / "scripts"))
import _mixin  # noqa: E402
import multibuild  # noqa: E402
import pgo  # noqa: E402
import remote_settings  # noqa: E402
from _targets import SUPPORTED  # noqa: E402


def test_windows_arm64_is_refused_with_a_message_not_a_key_error():
    with pytest.raises(ValueError, match=r"Unsupported build target windows,arm64; supported: .*linux,x86_64"):
        _mixin.get_moz_target("windows", "arm64")
    with pytest.raises(ValueError, match="Unsupported build target windows,arm64"):
        pgo.fetch("windows", "arm64", read_upstream_sh()["version"])


@pytest.mark.parametrize("pair, triple", [
    (("linux", "x86_64"), "x86_64-pc-linux-gnu"),
    (("linux", "arm64"), "aarch64-unknown-linux-gnu"),
    (("windows", "x86_64"), "x86_64-pc-windows-msvc"),
    (("windows", "i686"), "i686-pc-windows-msvc"),
    (("macos", "x86_64"), "x86_64-apple-darwin"),
    (("macos", "arm64"), "aarch64-apple-darwin"),
])
def test_every_supported_pair_keeps_its_target_triple(pair, triple):
    assert _mixin.get_moz_target(*pair) == triple


def test_multibuild_builds_exactly_the_supported_pairs(tmp_path, monkeypatch, capsys):
    built = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(multibuild, "run_build", lambda target, arch: built.append((target, arch)))
    monkeypatch.setattr(multibuild, "setup_linux_sysroots", lambda: None)
    monkeypatch.setattr(sys, "argv", ["multibuild.py", "--target", "linux", "windows",
                                      "--arch", "x86_64", "arm64", "i686"])
    multibuild.main()
    assert set(built) == {pair for pair in SUPPORTED if pair[0] != "macos"}
    assert "Skipping windows arm64" in capsys.readouterr().out


def test_patch_py_refuses_windows_arm64_by_name(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(BROWSER_ROOT / "scripts" / "patch.py"), "1.0", "1"],
        cwd=tmp_path, env={**os.environ, "BUILD_TARGET": "windows,arm64"},
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode != 0
    assert "Unsupported build target windows,arm64" in proc.stderr
    assert "KeyError" not in proc.stderr


def test_the_pgo_pin_script_reads_upstream_sh_through_the_shared_parser():
    version = read_upstream_sh()["version"]
    assert remote_settings.firefox_version() == version
    assert pgo.upstream_version() == version
