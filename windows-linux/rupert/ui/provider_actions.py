from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit

from rupert.config import load_config, save_config, save_key, update_config
from rupert.providers import connect, current_provider, friendly_error, list_models

if TYPE_CHECKING:
    from rupert.ui.controller import Controller


class ProviderActionsMixin:
    def connect_async(self: Controller) -> None:
        self.say(f"…connecting to {current_provider()['label']}…")

        def work() -> None:
            cfg = load_config()
            try:
                self.info.emit(connect(cfg))
            except Exception as e:  # noqa: BLE001
                self.info.emit(friendly_error(e))

        threading.Thread(target=work, daemon=True).start()

    def choose_provider(self: Controller, pid: str) -> None:
        p = current_provider(update_config(provider=pid))
        if pid == "custom" and not p["base"] and not self.ask_for_url():
            return
        if p["needs_key"] and not p["key"] and not self.ask_for_key():
            self.say(f"{p['label']} needs a key. paste it here ⏎")
            return
        self.connect_async()

    def ask_for_key(self: Controller) -> bool:
        p = current_provider()
        key, ok = QInputDialog.getText(None, "API key", f"{p['label']} API key:", QLineEdit.Password)
        key = key.strip()
        if not ok or not key:
            return False
        save_key(p["id"], key)
        self.connect_async()
        return True

    def ask_for_url(self: Controller) -> bool:
        cfg = load_config()
        p = current_provider(cfg)
        url, ok = QInputDialog.getText(None, "Server URL", "OpenAI-compatible base URL (ends in /v1):",
                                       QLineEdit.Normal, p["base"] or "http://localhost:8000/v1")
        url = url.strip().rstrip("/")
        if not ok or not url:
            return False
        cfg["base_urls"][p["id"]] = url
        save_config(cfg)
        self.connect_async()
        return True

    def choose_model(self: Controller, vision: bool) -> None:
        cfg = load_config()
        p = current_provider(cfg)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ids = list_models(p)
        except Exception:  # noqa: BLE001
            ids = []
        finally:
            QApplication.restoreOverrideCursor()
        current = p["vision"] if vision else p["model"]
        if current and current not in ids:
            ids.insert(0, current)
        label = ("Model for reading pet photos (must accept images):" if vision
                 else "Model for answers (small and fast is best):")
        pick, ok = QInputDialog.getItem(None, "Choose model", label, ids or [current or ""],
                                        ids.index(current) if current in ids else 0, True)
        pick = pick.strip()
        if not ok or not pick:
            return
        cfg["vision_models" if vision else "models"][p["id"]] = pick
        save_config(cfg)
        self.say(f"{'photo model' if vision else 'model'}: {pick}")
