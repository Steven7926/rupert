from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from rupert import shared
from rupert.config import load_config, save_config

_DATA = shared.data("providers")
PROVIDERS: dict[str, dict[str, Any]] = {p["id"]: p for p in _DATA["providers"]}
KEY_PREFIXES: list[tuple[str, str]] = [tuple(x) for x in _DATA["key_prefixes"]]
SKIP_MODELS: list[str] = _DATA["skip_models"]
FAST_HINTS: list[str] = _DATA["fast_hints"]
LOCAL_SERVERS = ("custom", "ollama", "lmstudio")

Provider = dict[str, Any]


class ProviderError(Exception):

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def current_provider(cfg: dict[str, Any] | None = None) -> Provider:
    cfg = cfg or load_config()
    pid = cfg["provider"]
    preset = PROVIDERS[pid]
    env_key = os.environ.get(preset["env"], "").strip() if preset.get("env") else ""
    model = cfg["models"].get(pid) or preset.get("model", "")
    return dict(id=pid, label=preset["label"], api=preset["api"],
                key=env_key or cfg["keys"].get(pid, ""),
                base=(cfg["base_urls"].get(pid) or preset["base"]).rstrip("/"),
                needs_key=preset.get("needs_key", True), model=model,
                vision=cfg["vision_models"].get(pid) or preset.get("vision") or model)


def provider_ready(p: Provider) -> bool:
    return bool(p["base"] and p["model"] and (p["key"] or not p["needs_key"]))


def provider_for_key(key: str, current: str) -> str:
    return next((pid for prefix, pid in KEY_PREFIXES if key.startswith(prefix)), current)


def looks_like_key(text: str) -> bool:
    return len(text) >= 20 and " " not in text


def _request(p: Provider, method: str, path: str, payload: Any = None, timeout: float = 30) -> Any:
    headers = {"content-type": "application/json", "user-agent": "rupert-desktop-pet"}
    if p["api"] == "anthropic":
        headers.update({"x-api-key": p["key"], "anthropic-version": "2023-06-01"})
    elif p["key"]:
        headers["authorization"] = "Bearer " + p["key"]
    if p["id"] == "openrouter":
        headers["x-title"] = "Rupert desktop pet"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(p["base"] + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="ignore")
        raise ProviderError(e.code, _error_message(raw) or raw[:200] or str(e)) from None
    except urllib.error.URLError as e:
        raise ProviderError(0, f"can't reach {p['label']} ({e.reason})") from None


def _error_message(raw: str) -> str | None:
    try:
        err = json.loads(raw)
    except ValueError:
        return None
    err = err[0] if isinstance(err, list) and err else err
    if not isinstance(err, dict):
        return None
    inner = err.get("error")
    return inner.get("message") if isinstance(inner, dict) else inner


def chat(p: Provider, system: str | None, messages: list[dict[str, Any]], max_tokens: int,
         model: str | None = None, image_b64: str | None = None, timeout: float = 30) -> str:
    model = model or p["model"]
    msgs = [dict(m) for m in messages]
    if p["api"] == "anthropic":
        if image_b64:
            msgs[-1]["content"] = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": msgs[-1]["content"]}]
        payload: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": msgs}
        if system:
            payload["system"] = system
        data = _request(p, "POST", "/messages", payload, timeout)
        return "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text")

    if image_b64:
        msgs[-1]["content"] = [
            {"type": "text", "text": msgs[-1]["content"]},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}}]
    payload = {"model": model, "max_tokens": max_tokens,
               "messages": ([{"role": "system", "content": system}] if system else []) + msgs}
    try:
        data = _request(p, "POST", "/chat/completions", payload, timeout)
    except ProviderError as e:
        if e.code != 400 or "max_completion_tokens" not in str(e):
            raise
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        data = _request(p, "POST", "/chat/completions", payload, timeout)
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content


def parse_model_list(data: Any) -> list[str]:
    items = data.get("data", data.get("models", [])) if isinstance(data, dict) else data
    ids = set()
    for m in items or []:
        mid = (m.get("id") or m.get("name")) if isinstance(m, dict) else m
        if isinstance(mid, str):
            mid = mid.removeprefix("models/")
            if not any(word in mid.lower() for word in SKIP_MODELS):
                ids.add(mid)
    return sorted(ids)


def list_models(p: Provider, timeout: float = 10) -> list[str]:
    return parse_model_list(_request(p, "GET", "/models", timeout=timeout))


def pick_fast_model(ids: list[str]) -> str:
    for hint in FAST_HINTS:
        hits = sorted(i for i in ids if hint in i.lower())
        if hits:
            return hits[-1]
    return ids[0] if ids else ""


def friendly_error(e: Exception) -> str:
    if isinstance(e, ProviderError):
        if e.code in (401, 403):
            return "bad key. right-click → AI provider → Set API key."
        if e.code == 404:
            return "model not found. right-click → AI provider → Model."
        if e.code == 0:
            return f"grr. {e}"
        return f"grr. {str(e)[:120]}"
    return f"grr. {e}"


def connect(cfg: dict[str, Any]) -> str:
    ids = list_models(current_provider(cfg))
    if ids:
        pid = cfg["provider"]
        if cfg["models"].get(pid) not in ids and PROVIDERS[pid].get("model") not in ids:
            cfg["models"][pid] = pick_fast_model(ids)
        save_config(cfg)
    p = current_provider(cfg)
    return f"connected: {p['label'].rstrip('…')} · {p['model'] or 'pick a model'}"
