import re

from rupert import shared
from rupert.pets import BREEDS, BUILTIN, DREAMS, PERSONALITIES


def test_every_breed_color_has_every_region_its_template_uses():
    for breed in BREEDS:
        regions = {region for region, _tone, _k in breed["tones"].values()}
        for color in breed["colors"]:
            missing = regions - set(color)
            assert not missing, f"{breed['id']}/{color['id']} has no color for {missing}"


def test_breed_frames_only_use_known_letters():
    for breed in BREEDS:
        known = set(breed["fixed"]) | set(breed["tones"]) | {"."}
        for name, rows in breed["frames"].items():
            used = set("".join(rows))
            assert used <= known, f"{breed['id']}/{name} uses {used - known}"


def test_personalities_are_complete():
    for p in PERSONALITIES:
        assert p["for"] in ("any", "dog", "cat")
        assert set(p["dream"]) == {"dog", "cat"} and all(d in DREAMS for d in p["dream"].values())
        assert all(len(f.split()) <= 2 for f in p["flavor"]), p["id"]
        assert p["text"] and p["thinking"] and p["saved"]


def test_breed_defaults_are_real_personalities():
    ids = {p["id"] for p in PERSONALITIES}
    for b in BREEDS:
        assert b["default"] in ids
        assert b["animal"] in ("dog", "cat")


def test_hats_use_symbols_so_they_never_clash_with_pet_palettes():
    for hat in shared.data("hats")["hats"]:
        assert not any(ch.isalnum() for ch in hat["palette"]), hat["id"]
        assert set("".join(hat["rows"])) <= set(hat["palette"]) | {"."}


def test_key_prefixes_point_at_real_providers():
    data = shared.data("providers")
    ids = {p["id"] for p in data["providers"]}
    assert all(pid in ids for _prefix, pid in data["key_prefixes"])


def test_built_in_pets_have_what_the_apps_need():
    for p in BUILTIN:
        for key in ("id", "name", "description", "personality", "flavor", "dream", "dream_color",
                    "thinking", "saved", "sprite"):
            assert key in p, (p.get("id"), key)


def test_prompt_templates_have_their_placeholders():
    assert {"NAME", "DESCRIPTION", "PERSONALITY", "OS_NOTE", "CAVEMAN_RULES", "FLAVOR_1", "FLAVOR_2"} <= set(
        re.findall(r"\{\{(\w+)\}\}", shared.prompt("pet")))
    assert set(re.findall(r"\{\{(\w+)\}\}", shared.prompt("draw_pet"))) == {"NAME", "EXAMPLE"}


def test_every_personality_has_an_energy():
    assert all(0 <= p["zoomies"] <= 1 for p in PERSONALITIES)
