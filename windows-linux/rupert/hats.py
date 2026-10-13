from __future__ import annotations

from typing import Any

from rupert import shared
from rupert.sprites import Frame, rgb

HATS: dict[str, dict[str, Any]] = {h["id"]: h for h in shared.data("hats")["hats"]}


def head_anchor(frame: Frame) -> tuple[int, float]:
    width = max(len(r) for r in frame)
    cut = int(width * 0.55)
    for y, row in enumerate(frame):
        xs = [x for x, c in enumerate(row) if c != "." and x >= cut]
        if xs:
            return y, (min(xs) + max(xs)) / 2
    return 0, width * 0.8


def apply_hat(frames: list[Frame], hat: dict[str, Any]) -> list[Frame]:
    rows = hat["rows"]
    hh, hw = len(rows), max(len(r) for r in rows)
    anchors = [head_anchor(f) for f in frames]
    pad = max(0, max(hh - 1 - y for y, _ in anchors))
    out = []
    for f, (y, cx) in zip(frames, anchors):
        width = max(len(r) for r in f)
        g = [list("." * width) for _ in range(pad)] + [list(r.ljust(width, ".")) for r in f]
        top = y + pad - (hh - 1)
        left = int(round(cx - (hw - 1) / 2))
        for dy, hat_row in enumerate(rows):
            for dx, ch in enumerate(hat_row):
                x, yy = left + dx, top + dy
                if ch != "." and 0 <= x < width and 0 <= yy < len(g):
                    g[yy][x] = ch
        out.append(["".join(r) for r in g])
    return out


def hat_for(pet_id: str, cfg: dict[str, Any]) -> str:
    hat = cfg.get("hats", {}).get(pet_id, "")
    return hat if hat in HATS else ""


def wear_hat(pet: dict[str, Any], hat_id: str) -> dict[str, Any]:
    if not hat_id:
        return pet
    hat = HATS[hat_id]
    dressed = apply_hat(pet["sleep"] + pet["awake"] + pet["walk"], hat)
    n1, n2 = len(pet["sleep"]), len(pet["sleep"]) + len(pet["awake"])
    return dict(pet, palette=dict(pet["palette"], **{k: rgb(v) for k, v in hat["palette"].items()}),
                sleep=dressed[:n1], awake=dressed[n1:n2], walk=dressed[n2:],
                h=len(dressed[0]), hat=hat_id)
