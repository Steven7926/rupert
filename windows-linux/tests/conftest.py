import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    from rupert import config, pets
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(config, "PREFS_PATH", tmp_path / "prefs.json")
    monkeypatch.setattr(config, "LEGACY_KEY_PATH", tmp_path / "key")
    monkeypatch.setattr(pets, "PETS_PATH", tmp_path / "pets.json")
    for env in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    return tmp_path
