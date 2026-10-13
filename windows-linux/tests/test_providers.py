import pytest

from rupert.config import load_config, save_config
from rupert.providers import (
    ProviderError,
    current_provider,
    friendly_error,
    parse_model_list,
    pick_fast_model,
    provider_for_key,
    provider_ready,
)


@pytest.mark.parametrize("key, expected", [
    ("sk-ant-api03-xyz", "anthropic"), ("sk-or-v1-abc", "openrouter"), ("gsk_abc", "groq"),
    ("AIzaSyAbc", "gemini"), ("sk-proj-abc", "openai"), ("nothing-known", "current"),
])
def test_provider_for_key(key, expected):
    assert provider_for_key(key, "current") == expected


def test_parse_model_list_handles_every_shape_and_skips_non_chat_models():
    assert parse_model_list({"data": [{"id": "gpt-x-mini"}, {"id": "text-embed-3"}]}) == ["gpt-x-mini"]
    assert parse_model_list({"models": [{"name": "models/gemini-flash"}]}) == ["gemini-flash"]
    assert parse_model_list(["llama3:8b", "llama3:8b"]) == ["llama3:8b"]


def test_pick_fast_model_prefers_small_ones():
    assert pick_fast_model(["claude-opus-9", "claude-haiku-4", "claude-haiku-5"]) == "claude-haiku-5"
    assert pick_fast_model(["big-model"]) == "big-model"
    assert pick_fast_model([]) == ""


def test_current_provider_reads_config_and_environment(monkeypatch):
    cfg = load_config()
    assert not provider_ready(current_provider(cfg))
    cfg["keys"]["anthropic"] = "sk-ant-saved"
    save_config(cfg)
    assert current_provider()["key"] == "sk-ant-saved"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    assert current_provider()["key"] == "sk-ant-env"
    cfg.update(provider="ollama")
    save_config(cfg)
    p = current_provider()
    assert p["base"] == "http://localhost:11434/v1" and not p["needs_key"]


def test_unknown_provider_in_config_falls_back(isolated_home):
    (isolated_home / "config.json").write_text('{"provider": "nope"}')
    assert load_config()["provider"] == "anthropic"


def test_friendly_errors():
    assert "bad key" in friendly_error(ProviderError(401, "x"))
    assert "model not found" in friendly_error(ProviderError(404, "x"))
    assert friendly_error(ValueError("boom")) == "grr. boom"
