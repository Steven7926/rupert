from __future__ import annotations

import datetime
import random
import re
from typing import Any

from rupert import shared

_ACTIVITY = shared.data("activity")
ACTIVITY_MODES: list[tuple[str, str]] = [(m["id"], m["label"]) for m in _ACTIVITY["modes"]]
DAY_SCHEDULE: list[dict[str, Any]] = _ACTIVITY["schedule"]
DEFAULT_SPEED = 30.0


def activity_mode(cfg: dict[str, Any]) -> str:
    mode = cfg.get("activity") or ("normal" if cfg.get("wander", True) else "stay")
    return mode if mode in dict(ACTIVITY_MODES) else "normal"


def walk_plan(mode: str, hour: int | None = None) -> tuple[float | None, float]:
    if mode == "stay":
        return None, DEFAULT_SPEED
    if mode == "normal":
        return random.uniform(60, 240), DEFAULT_SPEED
    hour = datetime.datetime.now().hour if hour is None else hour
    h = hour if hour >= 6 else hour + 24
    for slot in DAY_SCHEDULE:
        if slot["start"] <= h < slot["end"]:
            gap = random.uniform(*slot["gap"]) if slot["gap"] else None
            return gap, float(slot["speed"])
    return random.uniform(60, 240), DEFAULT_SPEED


ZOOMIES: dict[str, Any] = _ACTIVITY["zoomies"]
ZOOMIES_SPEED = float(ZOOMIES["speed"])


def zoomies_chance(mode: str, walk_speed: float, energy: float) -> float:
    if mode == "stay":
        return 0.0
    slot = ZOOMIES["fast_slot"] if mode == "time" and walk_speed >= 40 else (
        ZOOMIES["slow_slot"] if mode == "time" else 1.0)
    return max(0.0, min(0.9, energy * slot))


def zoomies_target(spot: float, direction: int) -> float:
    for d in (direction, -direction):
        length = random.choice(ZOOMIES["run_lengths"])
        target = max(0.0, min(1.0, spot + d * length))
        if abs(target - spot) >= 0.12:
            return target
    return 0.0 if spot > 0.5 else 1.0


def zoomies_laps() -> int:
    low, high = ZOOMIES["laps"]
    return random.randint(low, high)


_GLYPHS = shared.data("glyphs")
HEART: list[str] = _GLYPHS["heart"]
BANG: list[str] = _GLYPHS["bang"]
HEART_COLOR: str = _GLYPHS["heart_color"]
BANG_COLOR: str = _GLYPHS["bang_color"]
DUST_COLOR: str = _GLYPHS["dust_color"]

DESTRUCTIVE = re.compile(
    r"\brm\s+(-\w*[rf]\w*\s+)+|\bmkfs|\bdd\s+if=|\bformat\s+[a-z]:|--force\b|\bpush\s+(-f|--force)|"
    r"reset\s+--hard|\bdrop\s+(table|database)\b|\btruncate\s+table|\bsystem\s+prune|\bkill\s+-9|"
    r"\bshutdown\b|\bRemove-Item\b.*-Recurse|\bdel\s+/[sq]|\bchmod\s+-R\s+777|>\s*/dev/sd", re.I)
THANKS = re.compile(r"\b(thanks|thank\s*you|thx|ty|good\s*(boy|girl|dog|pup)|love\s*(you|u)|cute)\b", re.I)


def is_destructive(cmd: str | None) -> bool:
    return bool(cmd and DESTRUCTIVE.search(cmd))


def is_thanks(text: str) -> bool:
    return bool(THANKS.search(text))
