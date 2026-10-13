from __future__ import annotations

import datetime
import json
import re
from collections.abc import Sequence

from rupert import shared
from rupert.paths import IS_WIN

CAVEMAN_RULES = shared.prompt("caveman")
OS_NOTE = ("The user is on Windows; prefer PowerShell commands." if IS_WIN
           else "The user is on Linux; prefer bash commands.")


def pet_prompt(name: str, description: str, personality: str, flavor: Sequence[str]) -> str:
    flavor = list(flavor) + ["hmm.", "ok."]
    return shared.fill(shared.prompt("pet"), name=name, description=description, personality=personality,
                       os_note=OS_NOTE, caveman_rules=CAVEMAN_RULES, flavor_1=flavor[0], flavor_2=flavor[1])


def draw_pet_prompt(name: str, example_sprite: dict) -> str:
    example = json.dumps({"palette": example_sprite["palette"], "asleep": example_sprite["asleep"]})
    return shared.fill(shared.prompt("draw_pet"), name=name, example=example)


def time_note() -> str:
    now = datetime.datetime.now()
    clock = now.strftime("%I:%M %p").lstrip("0")
    return (f"\nIt is {clock} on {now:%A} for the user. If it's very late at night, your extra line "
            f"may tell them to go to bed; early morning, you can be sleepy.")


def tighten(raw: str) -> str:
    raw = re.sub(r"<think>.*?(</think>|$)", "", raw, flags=re.S)
    lines = [line.strip() for line in raw.replace("`", "").splitlines() if line.strip()]
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    return lines[0] + "\n" + " ".join(lines[1].split()[:2])


def command_part(reply: str) -> str | None:
    lines = reply.splitlines()
    if not lines:
        return None
    cmd = lines[0].split(" — ")[0].strip()
    return None if not cmd or cmd.endswith("?") else cmd
