"""The one reader of browser/upstream.sh, shared by the build scripts and ci/_util.py."""

from pathlib import Path
from typing import Dict, Optional

UPSTREAM_SH = Path(__file__).resolve().parent.parent / 'upstream.sh'


def read_upstream_sh(path: Optional[Path] = None) -> Dict[str, str]:
    """Parse upstream.sh into a dict. It is shell, but strictly key=value."""
    out: Dict[str, str] = {}
    for line in (path or UPSTREAM_SH).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, val = line.partition('=')
        out[key.strip()] = val.strip().strip('\'"')
    return out
