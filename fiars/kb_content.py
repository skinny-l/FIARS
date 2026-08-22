"""
kb_content.py — load externalized knowledge-base content.

KB article/entry text is sourced from vendor troubleshooting
documentation and is intentionally NOT tracked in this repository (see
kb_content/README.md at the project root). Each scripts/load_*.py loader
reads its payload from a local JSON file under kb_content/ instead of
hardcoding it, so the loading mechanism stays public while the actual
vendor-sourced content stays local to each installation.
"""
from __future__ import annotations

import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KB_DIR = os.path.join(_ROOT, "kb_content")


def load(name: str):
    """Load kb_content/<name>.json and return its parsed contents.

    Raises FileNotFoundError with setup guidance if the file isn't present
    locally — this is expected on a fresh clone since kb_content/ is
    gitignored.
    """
    path = os.path.join(_KB_DIR, f"{name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"KB content file not found: {path}\n"
            "This loader reads its content from a local, untracked file "
            "under kb_content/ — see kb_content/README.md for setup."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)
