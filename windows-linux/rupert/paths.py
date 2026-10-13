from __future__ import annotations

import os
import sys
from pathlib import Path

IS_WIN = sys.platform.startswith("win")
HOME = Path.home()

CONFIG_PATH = HOME / ".rupert_config.json"
PETS_PATH = HOME / ".rupert_pets.json"
PREFS_PATH = HOME / ".rupert.json"
LEGACY_KEY_PATH = HOME / ".rupert_key"

SOCKET_NAME = "rupert-dog-" + (os.environ.get("USER") or os.environ.get("USERNAME") or "me")

PACKAGE_DIR = Path(__file__).resolve().parent


def shared_dir() -> Path:
    candidates = [os.environ.get("RUPERT_SHARED"), PACKAGE_DIR.parent / "shared",
                  PACKAGE_DIR.parent.parent / "shared"]
    for c in candidates:
        if c and (Path(c) / "pets.json").is_file():
            return Path(c)
    raise FileNotFoundError("Rupert's shared data folder is missing. Reinstall, or set RUPERT_SHARED.")
