"""config.py — load config.json with safe local defaults."""
from __future__ import annotations

import json
import os

_DEFAULTS = {
    "db_path": "fiars.db",
    "backup_dir": "backups",
    "engineer_name": "",
    "host": "127.0.0.1",
    "port": 5000,
}


def load_config(path: str = "config.json") -> dict:
    cfg = dict(_DEFAULTS)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                cfg.update({k: v for k, v in json.load(f).items() if v not in (None, "")})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg
