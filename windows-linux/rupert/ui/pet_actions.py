from __future__ import annotations

import base64
import threading
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QDialog

from rupert.pets import DEFAULT_PET, delete_pet, draw_from_photo, load_pets, pet_flavor, pet_id_for, save_pet
from rupert.providers import ProviderError, current_provider, friendly_error, provider_ready
from rupert.ui.pet_dialog import PetDialog

if TYPE_CHECKING:
    from rupert.ui.controller import Controller

PHOTO_MAX_SIDE = 768


def _jpeg_base64(path: str) -> str | None:
    img = QImage(path)
    if img.isNull():
        return None
    img = img.scaled(PHOTO_MAX_SIDE, PHOTO_MAX_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "JPEG", 85)
    return base64.b64encode(bytes(buf.data())).decode()


class PetActionsMixin:
    def new_pet(self: Controller, edit_id: str | None = None) -> None:
        existing = load_pets().get(edit_id) if edit_id else None
        dialog = PetDialog(existing)
        if dialog.exec() != QDialog.Accepted:
            return
        choice = dialog.result_pet()
        name, preset = choice["name"], choice["personality"]
        pid = edit_id or pet_id_for(name)
        self.toggle_open()
        if choice["from_breed"]:
            self.on_pet_made(pid, dict(name=name, kind="breed", breed=choice["breed"],
                                       color=choice["color"], personality=preset))
            return
        if not choice["photo"]:
            pet = dict(existing or {}, name=name, preset=preset)
            pet.pop("kind", None)
            self.on_pet_made(pid, pet)
            return
        prov = current_provider()
        if not provider_ready(prov):
            self.say("set up an AI provider first. right-click → AI provider.")
            return
        photo = _jpeg_base64(choice["photo"])
        if not photo:
            self.say("can't read that photo. try JPG or PNG.")
            return
        self.say(f"…drawing {name}… (takes ~30s)")

        def work() -> None:
            try:
                pet = draw_from_photo(prov, photo, name)
                if preset:
                    pet["preset"] = preset
                self.pet_made.emit(pid, pet)
            except Exception as e:  # noqa: BLE001
                hint = "" if isinstance(e, ProviderError) and e.code in (401, 403) \
                    else " (photo model must accept images)"
                self.pet_made.emit("", friendly_error(e) + hint)

        threading.Thread(target=work, daemon=True).start()

    def on_pet_made(self: Controller, pid: str, result: Any) -> None:
        if not pid:
            self.say(str(result))
            return
        save_pet(pid, result)
        self.switch_to(pid)
        self.say(f"{result['name']} here! {pet_flavor(result)}\nterminal: pet {pid} on")

    def remove_pet(self: Controller) -> None:
        delete_pet(self.pet_id)
        self.switch_to(DEFAULT_PET)
