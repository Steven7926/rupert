import pytest

from rupert.prompts import command_part, pet_prompt, tighten


@pytest.mark.parametrize("raw, expected", [
    ("gg", "gg"),
    ("```\ngg\n```", "gg"),
    ("gg\nhmph. so lazy today", "gg\nhmph. so"),
    ("<think>the user wants vim</think>\ngg", "gg"),
    ("<think>never finished", ""),
    ("", ""),
])
def test_tighten(raw, expected):
    assert tighten(raw) == expected


@pytest.mark.parametrize("reply, expected", [
    ("git reset --soft HEAD~1\nzzz.", "git reset --soft HEAD~1"),
    ("rm -rf dir — no undo.", "rm -rf dir"),
    ("Mac or Linux?", None),
    ("", None),
])
def test_command_part(reply, expected):
    assert command_part(reply) == expected


def test_pet_prompt_includes_who_it_is_and_the_rules():
    p = pet_prompt("Mo", "a little corgi", "Zoomy.", ["zoom!!", "wheee!"])
    assert p.startswith("You are Mo, a little corgi")
    assert "Fewest tokens possible" in p and "zoom!!" in p and "Mo: gg" in p
    assert "{{" not in p
