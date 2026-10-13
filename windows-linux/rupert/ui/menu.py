from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QMenu

from rupert.behavior import ACTIVITY_MODES, activity_mode
from rupert.config import load_config, save_config, update_config
from rupert.desktop.hotkeys import HOTKEY_LABEL
from rupert.hats import HATS, hat_for
from rupert.pets import BUILTIN_IDS
from rupert.prompts import command_part
from rupert.providers import LOCAL_SERVERS, PROVIDERS, current_provider

if TYPE_CHECKING:
    from rupert.ui.controller import Controller

APPEARANCES = (("auto", "Auto (match system)"), ("light", "Light"), ("dark", "Dark"))


def _checkable(menu: QMenu, label: str, checked: bool, slot: Callable[[], object]) -> None:
    action = menu.addAction(label, lambda *_: slot())
    action.setCheckable(True)
    action.setChecked(checked)


class MenuMixin:
    def show_menu(self: Controller, pos: QPoint) -> None:
        self.refresh_pets()
        name = self.pet["name"]
        cfg = load_config()
        m = QMenu()

        talk = m.addAction(f"Talk to {name}\t{HOTKEY_LABEL}", self.hotkey_pressed)
        if self.hotkey_note:
            talk.setText(f"Talk to {name}  ({self.hotkey_note})")
        m.addSeparator()
        copy = m.addAction("Copy command", self.copy_command)
        copy.setEnabled(bool(self.last_reply and command_part(self.last_reply)))
        m.addAction("Clear chat", self.clear_chat)
        m.addSeparator()

        pets = m.addMenu("Pets")
        for pid, pet in self.pets.items():
            _checkable(pets, pet["name"], pid == self.pet_id, lambda pid=pid: self.switch_to(pid))
        pets.addSeparator()
        pets.addAction("Add new pet…", lambda: self.new_pet())
        if self.pet_id not in BUILTIN_IDS:
            pets.addAction(f"Edit {name}…", lambda: self.new_pet(edit_id=self.pet_id))
            pets.addAction(f"Remove {name}", self.remove_pet)
        m.addSeparator()

        p = current_provider(cfg)
        ai = m.addMenu(f"AI provider · {p['label']}")
        for pid, preset in PROVIDERS.items():
            _checkable(ai, preset["label"], pid == p["id"], lambda pid=pid: self.choose_provider(pid))
        ai.addSeparator()
        ai.addAction(f"Model: {p['model'] or '(none)'}…", lambda: self.choose_model(False))
        ai.addAction(f"Photo model: {p['vision'] or '(none)'}…", lambda: self.choose_model(True))
        if p["needs_key"] or p["id"] == "custom":
            ai.addAction("Set API key…", self.ask_for_key)
        if p["id"] in LOCAL_SERVERS:
            ai.addAction(f"Server URL: {p['base'] or '(none)'}…", self.ask_for_url)

        hats = m.addMenu("Accessories").addMenu("Hat")
        current_hat = hat_for(self.pet_id, cfg)
        for hid, label in [("", "No hat")] + [(k, v["name"]) for k, v in HATS.items()]:
            _checkable(hats, label, current_hat == hid, lambda hid=hid: self.set_hat(hid))

        activity = m.addMenu("Activity")
        current = activity_mode(cfg)
        for key, label in ACTIVITY_MODES:
            _checkable(activity, label, current == key, lambda key=key: self.set_activity(key))
        activity.addSeparator()
        _checkable(activity, "Glide between windows", self.glide, self.toggle_glide)

        look = m.addMenu("Appearance")
        for key, label in APPEARANCES:
            _checkable(look, label, cfg.get("appearance", "auto") == key, lambda key=key: self.set_appearance(key))
        m.addSeparator()
        m.addAction(f"Quit {name}", QApplication.quit)
        m.exec(pos)

    def set_hat(self: Controller, hat_id: str) -> None:
        cfg = load_config()
        cfg.setdefault("hats", {})[self.pet_id] = hat_id
        save_config(cfg)
        self.refresh_pets()
        self.view.pet = self.pet
        self.last = None
        self.follow()
        self.cheer(1.5)
        self.view.update()

    def set_activity(self: Controller, mode: str) -> None:
        update_config(activity=mode)
        self.next_walk = time.time() + 3
        if mode == "stay" and self.spot < 1.0 and not self.view.compact and self.last:
            self.target, self.speed, self.laps_left = 1.0, 36, 0
            self.view.facing, self.view.mode = 1, "walk"
            self.replace()

    def toggle_glide(self: Controller) -> None:
        self.glide = not self.glide
        update_config(glide=self.glide)
        if not self.glide and self.anim:
            self.anim.stop()
            self.replace()

    def set_appearance(self: Controller, pref: str) -> None:
        update_config(appearance=pref)
        self.bubble.apply_theme(self.theme_name())
        self.position_bubble()
