from __future__ import annotations

import contextlib
import json
import re
from typing import Any

from rupert import shared
from rupert.commands import RESERVED, sync_shims
from rupert.config import load_config
from rupert.hats import hat_for, wear_hat
from rupert.paths import IS_WIN, PETS_PATH
from rupert.prompts import draw_pet_prompt, pet_prompt
from rupert.providers import Provider, chat
from rupert.sprites import HEX, normalize_sprite, ramp, rgb

Pet = dict[str, Any]

DREAMS: dict[str, list[str]] = shared.data("glyphs")["dreams"]
BUILTIN: list[dict[str, Any]] = shared.data("pets")["pets"]
BUILTIN_IDS = [p["id"] for p in BUILTIN]
DEFAULT_PET = BUILTIN_IDS[0]
BREEDS: list[dict[str, Any]] = shared.data("breeds")["breeds"]
PERSONALITIES: list[dict[str, Any]] = shared.data("breeds")["personalities"]


DEFAULT_ENERGY = 0.2


def build_pet(name: str, sprite: dict[str, Any], dream: str, dream_color: str, thinking: str,
              key_saved: str, prompt: str, scale: float = 1.0, energy: float = DEFAULT_ENERGY) -> Pet:
    pet = normalize_sprite(sprite)
    pet.update(name=name, dream=DREAMS.get(dream, DREAMS["z"]), dream_color=rgb(dream_color),
               thinking=thinking, key_saved=key_saved, prompt=prompt, scale=scale, energy=energy)
    return pet


def _builtin(p: dict[str, Any]) -> Pet:
    return build_pet(p["name"], p["sprite"], p["dream"], p["dream_color"], p["thinking"], p["saved"],
                     pet_prompt(p["name"], p["description"], p["personality"], p["flavor"]),
                     energy=p.get("zoomies", DEFAULT_ENERGY))


BUILTIN_PETS: dict[str, Pet] = {p["id"]: _builtin(p) for p in BUILTIN}


def breed_template(breed_id: str | None) -> dict[str, Any]:
    return next((b for b in BREEDS if b["id"] == breed_id), BREEDS[0])


def breed_color(template: dict[str, Any], color_id: str | None) -> dict[str, Any]:
    return next((c for c in template["colors"] if c["id"] == color_id), template["colors"][0])


def personality(pid: str | None) -> dict[str, Any] | None:
    return next((p for p in PERSONALITIES if p["id"] == pid), None)


def personalities_for(animal: str) -> list[dict[str, Any]]:
    return [p for p in PERSONALITIES if not animal or p["for"] in ("any", animal)]


def paint_breed(breed_id: str | None, color_id: str | None) -> dict[str, Any]:
    t = breed_template(breed_id)
    col = breed_color(t, color_id)
    palette = dict(t["fixed"])
    for letter, (region, tone, k) in t["tones"].items():
        palette[letter] = ramp(col[region], tone, k)
    return dict(t["frames"], palette=palette)


def make_pet(saved: Pet) -> Pet:
    name = saved["name"]
    scale = 1.0
    if saved.get("kind") == "breed":
        t = breed_template(saved["breed"])
        sprite = paint_breed(t["id"], saved.get("color"))
        description = f"a little {t['noun']} ({breed_color(t, saved.get('color'))['name'].lower()})"
        animal = t["animal"]
        preset = personality(saved.get("personality")) or personality(t["default"])
        scale = t.get("size", 1.0)
    else:
        sprite, description = saved["sprite"], saved["description"]
        animal = "cat" if re.search(r"\b(cat|kitten|kitty)\b", description, re.I) else "dog"
        preset = personality(saved.get("preset"))
    if preset:
        return build_pet(name, sprite, preset["dream"][animal], preset["dream_color"], preset["thinking"],
                         preset["saved"], pet_prompt(name, description, preset["text"], preset["flavor"]),
                         scale, preset.get("zoomies", DEFAULT_ENERGY))
    return build_pet(name, sprite, saved["dream"], saved["dream_color"], "…hmm…", "key saved. ask.",
                     pet_prompt(name, description, saved["personality"], saved["flavor"]))


def pet_flavor(saved: Pet) -> str:
    preset = personality(saved.get("personality") if saved.get("kind") == "breed" else saved.get("preset"))
    return (preset or saved)["flavor"][-1]


def load_pets() -> dict[str, Pet]:
    try:
        with open(PETS_PATH, encoding="utf-8") as f:
            return json.load(f).get("pets", {})
    except (OSError, ValueError):
        return {}


def _write_pets(pets: dict[str, Pet]) -> None:
    with open(PETS_PATH, "w", encoding="utf-8") as f:
        json.dump({"pets": pets}, f, indent=1)
    if IS_WIN:
        sync_shims([*BUILTIN_IDS, *pets])


def save_pet(pet_id: str, pet: Pet) -> None:
    pets = load_pets()
    pets[pet_id] = pet
    _write_pets(pets)


def delete_pet(pet_id: str) -> None:
    pets = load_pets()
    if pets.pop(pet_id, None) is not None:
        _write_pets(pets)


def pet_id_for(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", name.lower()) or "pet"
    taken = set(BUILTIN_IDS) | set(load_pets()) | RESERVED
    pid, n = base, 2
    while pid in taken:
        pid, n = f"{base}{n}", n + 1
    return pid


def all_pets() -> dict[str, Pet]:
    pets = dict(BUILTIN_PETS)
    for pid, saved in load_pets().items():
        with contextlib.suppress(KeyError, ValueError, TypeError):
            pets[pid] = make_pet(saved)
    cfg = load_config()
    return {pid: wear_hat(p, hat_for(pid, cfg)) for pid, p in pets.items()}


def parse_json_reply(text: str) -> dict[str, Any]:
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON in reply")
    return json.loads(text[a:b + 1])


def clean_photo_pet(data: dict[str, Any], name: str) -> Pet:
    sprite = data.get("sprite") or {}
    normalize_sprite(sprite)
    flavor = [" ".join(str(f).split()[:2]) for f in (data.get("flavor") or []) if str(f).strip()]
    dream_color = data.get("dream_color")
    return dict(name=name, sprite=sprite,
                description=str(data.get("description") or "a pet")[:80],
                personality=str(data.get("personality") or "Friendly and curious.")[:240],
                flavor=(flavor + ["hmm.", "ok.", "yay."])[:3],
                dream=data.get("dream") if data.get("dream") in DREAMS else "z",
                dream_color=dream_color if isinstance(dream_color, str) and HEX.match(dream_color) else "#c8a070")


def draw_from_photo(p: Provider, jpeg_b64: str, name: str) -> Pet:
    example = next(b for b in BUILTIN if b["id"] == "stewart")["sprite"]
    budget = 6000 if p["api"] == "anthropic" else 10000
    text = chat(p, None, [{"role": "user", "content": draw_pet_prompt(name, example)}],
                budget, model=p["vision"], image_b64=jpeg_b64, timeout=180)
    result = parse_json_reply(text)
    if "error" in result:
        raise ValueError(result["error"])
    return clean_photo_pet(result, name)
