#!/usr/bin/env python3

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "windows-linux"))

from rupert.pets import BREEDS, BUILTIN_PETS, make_pet  # noqa: E402

DARK, LIGHT = (52, 52, 60), (232, 230, 226)


def draw_frame(d: ImageDraw.ImageDraw, pet: dict, frame: list, left: int, bottom: int, size: int) -> None:
    top = bottom - len(frame) * size
    for y, line in enumerate(frame):
        for x, ch in enumerate(line):
            if ch in pet["palette"]:
                x0, y0 = left + x * size, top + y * size
                d.rectangle([x0, y0, x0 + size - 1, y0 + size - 1], fill=pet["palette"][ch])


def breeds_sheet() -> Image.Image:
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    size, cell_w, cell_h = 4, 230, 150
    columns = max(len(b["colors"]) for b in BREEDS)
    img = Image.new("RGB", (columns * cell_w + 16, len(BREEDS) * cell_h + 16), (30, 30, 34))
    d = ImageDraw.Draw(img)
    for row, breed in enumerate(BREEDS):
        for col, color in enumerate(breed["colors"]):
            pet = make_pet({"name": "x", "kind": "breed", "breed": breed["id"], "color": color["id"]})
            x, y = 8 + col * cell_w, 8 + row * cell_h
            light = (row + col) % 2 == 1
            d.rounded_rectangle([x + 4, y + 4, x + cell_w - 4, y + cell_h - 4], 10, fill=LIGHT if light else DARK)
            draw_frame(d, pet, (pet["walk"] or pet["awake"])[0], x + (cell_w - pet["w"] * size) // 2, y + 104, size)
            text_w = d.textlength(color["name"], font=font)
            d.text((x + (cell_w - text_w) / 2, y + 116), color["name"], font=font,
                   fill=(60, 60, 66) if light else (220, 220, 226))
    return img


def pets_sheet(pets: dict) -> Image.Image:
    size, columns = 8, 6
    cell_w = max(p["w"] for p in pets.values()) * size + 16
    cell_h = max(p["h"] for p in pets.values()) * size + 16
    img = Image.new("RGB", (columns * (cell_w + 8) + 8, len(pets) * (cell_h + 8) + 8), (30, 30, 34))
    d = ImageDraw.Draw(img)
    for row, pet in enumerate(pets.values()):
        for col, frame in enumerate((pet["sleep"] + pet["awake"] + pet["walk"])[:columns]):
            x, y = 8 + col * (cell_w + 8), 8 + row * (cell_h + 8)
            d.rectangle([x, y, x + cell_w, y + cell_h], fill=LIGHT if (row + col) % 2 else (46, 46, 52))
            draw_frame(d, pet, frame, x + 8, y + cell_h - 8, size)
    return img


def main() -> None:
    if sys.argv[1:] == ["--breeds"]:
        out, img = ROOT / "docs" / "breeds.png", breeds_sheet()
    else:
        pets = dict(BUILTIN_PETS)
        for path in sys.argv[1:]:
            with open(Path(path).expanduser(), encoding="utf-8") as f:
                for pid, saved in json.load(f).get("pets", {}).items():
                    try:
                        pets[pid] = make_pet(saved)
                    except (KeyError, ValueError, TypeError) as e:
                        print(f"skipping {pid}: {e}")
        out, img = ROOT / "docs" / "pets.png", pets_sheet(pets)
    img.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
