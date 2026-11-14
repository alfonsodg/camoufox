"""browser/scripts/check-input-dispatch.py and fetch-fonts.py."""

import importlib.util
import json
import sys

import pytest

from ci._util import BROWSER_ROOT


def _load(filename):
    path = BROWSER_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_").removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dispatch(tmp_path, monkeypatch):
    """check-input-dispatch.py pointed at a tree holding only its chokepoint."""
    module = _load("check-input-dispatch.py")
    juggler = tmp_path / "additions" / "juggler"
    (juggler / "input").mkdir(parents=True)
    (tmp_path / module.CHOKEPOINT).write_text("jugglerSendMouseEvent(a);\n")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SCAN_ROOT", juggler)
    return module, juggler


@pytest.mark.parametrize("name", ["Leak.js", "Leak.mjs", "Leak.sys.mjs"])
def test_a_dispatch_outside_the_chokepoint_is_reported_in_any_module_flavour(dispatch, name, capsys):
    module, juggler = dispatch
    (juggler / name).write_text("const x = win.sendWheelEvent(1);\n")
    assert module.main() == 1
    assert f"additions/juggler/{name}:1" in capsys.readouterr().out


def test_a_clean_tree_passes_and_counts_the_module_files(dispatch, capsys):
    module, juggler = dispatch
    (juggler / "Fine.sys.mjs").write_text("export const x = 1;\n")
    assert module.main() == 0
    assert "2 files scanned" in capsys.readouterr().out


def test_the_shipped_juggler_goes_through_the_chokepoint():
    assert _load("check-input-dispatch.py").main() == 0


@pytest.fixture
def fonts(tmp_path, monkeypatch):
    module = _load("fetch-fonts.py")
    spec = tmp_path / "font-bundle.json"
    archive = tmp_path / "fonts-bundle-v2.tar.xz"
    archive.write_bytes(b"fonts")
    monkeypatch.setattr(module, "SPEC", str(spec))
    return module, spec, archive


def _write_spec(module, monkeypatch, archive):
    monkeypatch.setattr(sys, "argv", ["fetch-fonts.py", "--write-spec", str(archive), "--tag", "font-bundle-v2"])
    return module.main()


def test_write_spec_keeps_the_repo_the_spec_already_names(fonts, monkeypatch):
    module, spec, archive = fonts
    spec.write_text(json.dumps({"repo": "daijro/camoufox"}))
    assert _write_spec(module, monkeypatch, archive) == 0
    written = json.loads(spec.read_text())
    assert written["repo"] == "daijro/camoufox"
    assert written["url"] == "https://github.com/daijro/camoufox/releases/download/font-bundle-v2/fonts-bundle-v2.tar.xz"


@pytest.mark.parametrize("existing", [None, {"tag": "font-bundle-v1"}])
def test_write_spec_without_a_repo_in_the_spec_fails_instead_of_guessing_a_fork(fonts, monkeypatch, existing):
    module, spec, archive = fonts
    if existing is not None:
        spec.write_text(json.dumps(existing))
    with pytest.raises(SystemExit, match="repo"):
        _write_spec(module, monkeypatch, archive)
    assert "JWriter20" not in (spec.read_text() if spec.exists() else "")
