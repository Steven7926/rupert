from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

from rupert.behavior import is_destructive, is_thanks
from rupert.config import load_config, save_key
from rupert.prompts import command_part, tighten, time_note
from rupert.providers import (
    Provider,
    chat,
    current_provider,
    friendly_error,
    looks_like_key,
    provider_for_key,
    provider_ready,
)
from rupert.ui.common import THEMES

if TYPE_CHECKING:
    from rupert.ui.controller import Controller

HISTORY_TURNS = 6
NO_ANSWER = "grr. no answer."


class ChatMixin:

    def toggle(self: Controller) -> None:
        if time.time() - self.closed_at < 0.3:
            return
        if self.bubble.isVisible():
            self.close_bubble()
            return
        self.view.awake = True
        if self.view.mode in ("walk", "run"):
            self.view.mode, self.laps_left = "sleep", 0
        self.bubble.apply_theme(self.theme_name())
        self.bubble.input.setPlaceholderText(self.ask_prompt())
        self.bubble.relayout()
        self.bubble.show()
        self.position_bubble()
        self.bubble.raise_()
        self.bubble.activateWindow()
        self.bubble.input.setFocus()

    def toggle_open(self: Controller) -> None:
        if not self.bubble.isVisible():
            self.closed_at = 0
            self.toggle()

    def close_bubble(self: Controller) -> None:
        if self.bubble.isVisible():
            self.closed_at = time.time()
        self.bubble.hide()
        self.view.awake = False
        self.view.update()

    def close_if_inactive(self: Controller) -> None:
        if self.bubble.isVisible() and not self.bubble.isActiveWindow():
            self.close_bubble()

    def hotkey_pressed(self: Controller) -> None:
        if self.bubble.isVisible():
            self.close_bubble()
        else:
            self.closed_at = 0
            self.toggle()

    def say(self: Controller, text: str) -> None:
        self.toggle_open()
        self.bubble.set_answer(text)
        self.bubble.input.setPlaceholderText(self.ask_prompt())
        self.position_bubble()

    def ask_prompt(self: Controller) -> str:
        p = current_provider()
        if provider_ready(p):
            return f"ask {self.pet_id}…"
        if p["needs_key"] and not p["key"]:
            return "paste an API key ⏎ (any provider)" if p["id"] == "anthropic" else f"paste {p['label']} key ⏎"
        return "right-click → AI provider to set up"

    def theme_name(self: Controller) -> str:
        pref = load_config().get("appearance", "auto")
        if pref in THEMES:
            return pref
        try:
            return "dark" if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"
        except AttributeError:
            return "dark" if QGuiApplication.palette().window().color().lightness() < 128 else "light"


    def submit(self: Controller) -> None:
        text = self.bubble.input.text().strip()
        if not text or self.busy:
            return
        self.bubble.input.clear()
        prov = current_provider()
        if not provider_ready(prov):
            if prov["needs_key"] and not prov["key"] and looks_like_key(text):
                save_key(provider_for_key(text, prov["id"]), text)
                self.bubble.set_answer(self.pet["key_saved"])
                self.connect_async()
            else:
                self.bubble.set_answer("not set up yet. right-click → AI provider.")
            self.bubble.input.setPlaceholderText(self.ask_prompt())
            self.position_bubble()
            return
        if is_thanks(text):
            self.cheer(2.5)
        self.busy = True
        self.bubble.input.setPlaceholderText(text)
        self.bubble.set_answer(self.pet["thinking"])
        self.position_bubble()
        self.history = (self.history + [{"role": "user", "content": text}])[-HISTORY_TURNS:]
        system = self.pet["prompt"] + time_note()
        threading.Thread(target=self._ask, args=(prov, system, list(self.history)), daemon=True).start()

    def _ask(self: Controller, prov: Provider, system: str, history: list[dict[str, Any]]) -> None:
        budget = 60 if prov["api"] == "anthropic" else 400
        try:
            reply = tighten(chat(prov, system, history, budget)) or NO_ANSWER
            ok = reply != NO_ANSWER
        except Exception as e:  # noqa: BLE001
            reply, ok = friendly_error(e), False
        self.replied.emit(reply, ok)

    def on_reply(self: Controller, reply: str, ok: bool) -> None:
        self.busy = False
        if ok:
            self.history.append({"role": "assistant", "content": reply})
            self.last_reply = reply
        elif self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        cmd = command_part(reply) if ok else None
        if is_destructive(cmd):
            self.view.nervous_until = time.time() + 2.5
        self.bubble.show_copied(False)
        self.bubble.clip.setVisible(cmd is not None)
        self.bubble.set_answer(reply, cmd)
        self.bubble.input.setPlaceholderText(self.ask_prompt())
        self.position_bubble()

    def clear_chat(self: Controller) -> None:
        self.history.clear()
        self.last_reply = None
        self.bubble.clip.hide()
        self.bubble.set_answer("")
        self.position_bubble()

    def copy_command(self: Controller) -> None:
        cmd = command_part(self.last_reply or "")
        if not cmd:
            return
        QGuiApplication.clipboard().setText(cmd)
        self.bubble.show_copied(True)
        self.cheer()
        QTimer.singleShot(1200, lambda: self.bubble.show_copied(False))


    def petted(self: Controller) -> None:
        if self.view.mode in ("walk", "run", "carry"):
            return
        self.view.happy_until = time.time() + 2.5
        self.next_walk = max(self.next_walk, time.time() + 30)

    def cheer(self: Controller, seconds: float = 1.8) -> None:
        self.view.happy_until = time.time() + seconds
