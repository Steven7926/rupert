from __future__ import annotations

import json
from functools import cache
from typing import Any

from rupert.paths import shared_dir


@cache
def data(name: str) -> Any:
    with open(shared_dir() / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


@cache
def prompt(name: str) -> str:
    return (shared_dir() / "prompts" / f"{name}.txt").read_text(encoding="utf-8").rstrip("\n")


def fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key.upper() + "}}", value)
    return template
