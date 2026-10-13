from __future__ import annotations

import math
import re
from typing import Any

MAX_W, MAX_H = 48, 20
MIN_INK = 60
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

RGB = tuple[int, int, int]
Frame = list[str]


def rgb(hex_color: str) -> RGB:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def luminance(c: tuple[float, ...]) -> float:
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


def _ink(frame: Frame) -> int:
    return sum(1 for row in frame for c in row if c != ".")


def normalize_sprite(raw: dict[str, Any]) -> dict[str, Any]:
    palette = {k: rgb(v) for k, v in (raw.get("palette") or {}).items()
               if isinstance(k, str) and len(k) == 1 and k != "." and isinstance(v, str) and HEX.match(v)}
    if len(palette) < 2:
        raise ValueError("sprite has no colors")

    def grid(rows: Any) -> Frame | None:
        if not isinstance(rows, list) or not rows:
            return None
        g = ["".join(c if c in palette else "." for c in str(r)[:MAX_W]) for r in rows[:MAX_H]]
        while g and not g[-1].strip("."):
            g.pop()
        while g and not g[0].strip("."):
            g.pop(0)
        return g or None

    asleep = grid(raw.get("asleep"))
    if not asleep:
        raise ValueError("sprite has no pixels")
    frames: dict[str, Frame] = {"asleep": asleep}
    for k in ("breathe", "awake", "awake2"):
        f = grid(raw.get(k))
        if f and _ink(f) >= _ink(asleep) * 0.6 and abs(len(f) - len(asleep)) <= 2:
            frames[k] = f
    frames.setdefault("breathe", asleep)
    frames.setdefault("awake", asleep)
    frames.setdefault("awake2", frames["awake"])
    walk = [f for f in (grid(raw.get(k)) for k in ("walk1", "walk2"))
            if f and _ink(f) >= _ink(asleep) * 0.4]
    if len(walk) == 1:
        walk.append(walk[0])
    for i, f in enumerate(walk):
        frames[f"walk{i + 1}"] = f

    height = max(len(f) for f in frames.values())
    width = max(len(r) for f in frames.values() for r in f)
    for k, f in frames.items():
        fw = max(len(r) for r in f)
        rows = [r.ljust(fw, ".").rjust(width, ".") if k.startswith("walk") else r.ljust(width, ".")
                for r in f]
        frames[k] = ["." * width] * (height - len(f)) + rows

    if _ink(frames["asleep"]) < MIN_INK:
        raise ValueError("sprite too small")
    cells = [(x, y) for f in frames.values() for y, r in enumerate(f) for x, c in enumerate(r) if c != "."]
    x0, x1 = min(x for x, _ in cells), max(x for x, _ in cells)
    y0, y1 = min(y for _, y in cells), max(y for _, y in cells)
    for k, f in frames.items():
        frames[k] = [r[x0:x1 + 1] for r in f[y0:y1 + 1]]

    filled = [palette[c] for r in frames["asleep"] for c in r if c != "."]
    dark = sum(luminance(c) for c in filled) / len(filled) < 0.45
    awake = [frames["awake"]] if frames["awake2"] == frames["awake"] else [frames["awake"], frames["awake2"]]
    return dict(palette=palette, sleep=[frames["asleep"], frames["breathe"]], awake=awake,
                walk=[frames[k] for k in ("walk1", "walk2") if k in frames],
                w=x1 - x0 + 1, h=y1 - y0 + 1,
                halo=(255, 255, 255, 90) if dark else (0, 0, 0, 72))


def full_px(pet: dict[str, Any]) -> float:
    return max(1.0, min(3.0, math.floor(80 * pet.get("scale", 1.0) / pet["w"] * 2) / 2))


def ramp(hex_color: str, tone: str, k: float = 1.0) -> str:
    c: tuple[float, ...] = rgb(hex_color)

    def mix(a: tuple[float, ...], b: tuple[float, ...], t: float) -> tuple[float, ...]:
        return tuple(x + (y - x) * t for x, y in zip(a, b))

    if k < 1:
        c = tuple(v * k for v in c)
    elif k > 1:
        c = mix(c, (255, 255, 255), k - 1)
    if tone == "hi":
        c = mix(c, (150, 156, 190), 0.30) if luminance(c) < 0.2 else mix(c, (255, 246, 228), 0.32)
    elif tone == "sh":
        c = (c[0] * 0.80, c[1] * 0.78, c[2] * 0.82)
    elif tone == "dp":
        c = (c[0] * 0.64, c[1] * 0.61, c[2] * 0.68)
    elif tone == "out":
        c = (c[0] * 0.42, c[1] * 0.38, c[2] * 0.42)
    return "#{:02x}{:02x}{:02x}".format(*tuple(max(0, min(255, int(v + 0.5))) for v in c))
