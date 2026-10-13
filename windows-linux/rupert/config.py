from __future__ import annotations

import contextlib
import json
import os
from typing import Any

from rupert import shared
from rupert.paths import CONFIG_PATH, LEGACY_KEY_PATH, PREFS_PATH

DEFAULTS: dict[str, Any] = {
    "provider": "anthropic",
    "models": {},
    "vision_models": {},
    "keys": {},
    "base_urls": {},
    "appearance": "auto",
    "wander": True,
    "activity": "",
    "hats": {},
    "glide": True,
}


def load_config() -> dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        for k in cfg:
            if k in saved and isinstance(saved[k], type(cfg[k])):
                cfg[k] = saved[k]
    except (OSError, ValueError):
        pass
    if cfg["provider"] not in {p["id"] for p in shared.data("providers")["providers"]}:
        cfg["provider"] = "anthropic"
    if "anthropic" not in cfg["keys"]:
        try:
            old = LEGACY_KEY_PATH.read_text().strip()
            if old:
                cfg["keys"]["anthropic"] = old
        except OSError:
            pass
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1)
    with contextlib.suppress(OSError):
        os.chmod(CONFIG_PATH, 0o600)


def update_config(**changes: Any) -> dict[str, Any]:
    cfg = load_config()
    cfg.update(changes)
    save_config(cfg)
    return cfg


def save_key(provider_id: str, key: str) -> dict[str, Any]:
    cfg = load_config()
    cfg["provider"] = provider_id
    cfg["keys"][provider_id] = key
    save_config(cfg)
    return cfg


def load_awake_pet(known: set[str], default: str) -> str:
    try:
        with open(PREFS_PATH, encoding="utf-8") as f:
            pet = json.load(f).get("dog", default)
        return pet if pet in known else default
    except (OSError, ValueError):
        return default


def save_awake_pet(pet_id: str) -> None:
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump({"dog": pet_id}, f)
    except OSError:
        pass
