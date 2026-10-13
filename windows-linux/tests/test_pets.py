import json

import pytest

from rupert import pets
from rupert.hats import HATS, head_anchor, wear_hat
from rupert.pets import (
    BREEDS,
    BUILTIN_IDS,
    PERSONALITIES,
    all_pets,
    clean_photo_pet,
    delete_pet,
    make_pet,
    parse_json_reply,
    personalities_for,
    pet_flavor,
    pet_id_for,
    save_pet,
)


@pytest.mark.parametrize("breed", BREEDS, ids=lambda b: b["id"])
def test_every_breed_and_color_makes_a_pet_that_can_walk(breed):
    for color in breed["colors"]:
        pet = make_pet({"name": "Mo", "kind": "breed", "breed": breed["id"], "color": color["id"]})
        assert len(pet["sleep"]) == 2 and len(pet["awake"]) == 2 and len(pet["walk"]) == 2
        assert pet["w"] <= 48 and pet["h"] <= 20
        assert "Mo" in pet["prompt"] and breed["noun"] in pet["prompt"]


def test_personality_shapes_the_prompt_and_dreams():
    cat = make_pet({"name": "Mo", "kind": "breed", "breed": "cat", "color": "black", "personality": "hungry"})
    dog = make_pet({"name": "Mo", "kind": "breed", "breed": "corgi", "color": "red", "personality": "hungry"})
    assert "snacks" in cat["prompt"]
    assert cat["dream"] == pets.DREAMS["fish"] and dog["dream"] == pets.DREAMS["bone"]


def test_small_breeds_are_drawn_smaller():
    chi = make_pet({"name": "Mo", "kind": "breed", "breed": "chihuahua", "color": "fawn"})
    lab = make_pet({"name": "Mo", "kind": "breed", "breed": "hound", "color": "yellow"})
    assert chi["scale"] < lab["scale"] == 1.0


def test_personalities_for_cats_leave_out_dog_only_ones():
    cat_ids = {p["id"] for p in personalities_for("cat")}
    assert "golden" not in cat_ids and "aloof" in cat_ids
    assert len(personalities_for("")) == len(PERSONALITIES)


def test_photo_pet_round_trip_with_a_preset():
    stewart = next(p for p in pets.BUILTIN if p["id"] == "stewart")
    reply = json.dumps({"description": "a fluffy cat", "personality": "Naps.", "flavor": ["mrow", "purr purr purr"],
                        "dream": "fish", "dream_color": "#123456", "sprite": stewart["sprite"]})
    saved = clean_photo_pet(parse_json_reply("Sure! " + reply + " done"), "Mo")
    assert saved["flavor"] == ["mrow", "purr purr", "hmm."]
    assert "Naps." in make_pet(saved)["prompt"]
    saved["preset"] = "gremlin"
    assert "chaotic" in make_pet(saved)["prompt"]
    assert pet_flavor(saved) == "mlem."


def test_saved_pets_get_unique_ids_and_show_up(isolated_home):
    assert pet_id_for("Rupert") == "rupert2"
    save_pet("biscuit", {"name": "Biscuit", "kind": "breed", "breed": "doodle", "color": "apricot"})
    assert pet_id_for("Biscuit!") == "biscuit2"
    assert list(all_pets())[:len(BUILTIN_IDS)] == BUILTIN_IDS and "biscuit" in all_pets()
    delete_pet("biscuit")
    assert "biscuit" not in all_pets()


def test_broken_saved_pets_are_skipped(isolated_home):
    save_pet("old", {"name": "Old", "sprite": {"palette": {}}})
    assert "old" not in all_pets()


def test_hats_sit_on_the_head_and_keep_frames_aligned():
    pet = pets.BUILTIN_PETS["rupert"]
    dressed = wear_hat(pet, "party")
    assert dressed["h"] > pet["h"]
    frames = dressed["sleep"] + dressed["awake"] + dressed["walk"]
    assert len({len(f) for f in frames}) == 1
    assert any(ch in "".join(dressed["sleep"][0]) for ch in HATS["party"]["palette"])
    assert head_anchor(["....", "..aa", "aaaa"])[0] == 1


def test_energy_comes_from_the_personality():
    zoomy = make_pet({"name": "Mo", "kind": "breed", "breed": "corgi", "color": "red", "personality": "zoomy"})
    sleepy = make_pet({"name": "Mo", "kind": "breed", "breed": "corgi", "color": "red", "personality": "sleepy"})
    assert zoomy["energy"] > sleepy["energy"]
    assert pets.BUILTIN_PETS["stewart"]["energy"] > pets.BUILTIN_PETS["rupert"]["energy"]
