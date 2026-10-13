import pytest

from rupert.sprites import full_px, normalize_sprite, ramp

PAL = {"a": "#112233", "b": "#ffeedd"}


def block(w, h, ch="a"):
    return [ch * w] * h


def test_crops_to_the_pixels_and_drops_empty_rows():
    pet = normalize_sprite({"palette": PAL, "asleep": ["", "....", ".." + "a" * 30] + block(30, 3)})
    assert pet["h"] == 4 and pet["w"] == 32
    assert all(len(r) == 32 for r in pet["sleep"][0])


def test_bad_characters_become_transparent():
    pet = normalize_sprite({"palette": PAL, "asleep": block(20, 4) + ["a" * 10 + "?" * 10]})
    assert "?" not in "".join(pet["sleep"][0])


def test_broken_frames_fall_back_to_asleep():
    pet = normalize_sprite({"palette": PAL, "asleep": block(20, 4), "awake": ["a"]})
    assert pet["awake"] == [pet["sleep"][0]]


def test_walk_frames_are_aligned_as_a_block():
    walk = ["....aaaa", "aaaaaaaa", "a......a"]
    pet = normalize_sprite({"palette": PAL, "asleep": block(20, 4), "walk1": walk * 4})
    assert len(pet["walk"]) == 2
    rows = [r for r in pet["walk"][0] if r.strip(".")]
    assert rows[0].endswith("aaaa") and rows[1].endswith("aaaaaaaa")


@pytest.mark.parametrize("raw", [{}, {"palette": PAL}, {"palette": PAL, "asleep": ["ab"]},
                                 {"palette": {"a": "red"}, "asleep": block(20, 4)}])
def test_rejects_unusable_sprites(raw):
    with pytest.raises(ValueError):
        normalize_sprite(raw)


def test_halo_is_light_for_dark_pets_and_dark_for_light_ones():
    assert normalize_sprite({"palette": PAL, "asleep": block(20, 4, "a")})["halo"][0] == 255
    assert normalize_sprite({"palette": PAL, "asleep": block(20, 4, "b")})["halo"][0] == 0


def test_full_px_aims_for_about_80_points_and_respects_scale():
    assert full_px({"w": 40}) == 2.0
    assert full_px({"w": 10}) == 3.0
    assert full_px({"w": 40, "scale": 0.5}) == 1.0


@pytest.mark.parametrize("args, expected", [
    (("#1f1b1c", "hi", 1.0), "#43424d"),
    (("#f6f2ea", "out", 1.0), "#675c62"),
    (("#3c2a22", "base", 1.3), "#776a64"),
    (("#808080", "base", 1.0), "#808080"),
    (("#808080", "flat", 0.5), "#404040"),
])
def test_ramp_matches_the_mac_app(args, expected):
    assert ramp(*args) == expected
