from __future__ import annotations

import contextlib
import random
import sys
import time
from typing import Any

from PySide6.QtCore import QObject, QPropertyAnimation, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QApplication

from rupert.config import load_config, save_awake_pet
from rupert.desktop.hotkeys import WinHotkey, X11Hotkey
from rupert.desktop.trackers import WinTracker, X11Tracker
from rupert.paths import IS_WIN, SOCKET_NAME
from rupert.pets import DEFAULT_PET, all_pets
from rupert.ui.bubble import Bubble
from rupert.ui.chat import ChatMixin
from rupert.ui.menu import MenuMixin
from rupert.ui.pet_actions import PetActionsMixin
from rupert.ui.pet_view import PetView
from rupert.ui.placement import PlacementMixin
from rupert.ui.provider_actions import ProviderActionsMixin
from rupert.ui.wandering import WanderMixin

FOLLOW_MS = 50
ANIMATE_MS = 100


class Controller(QObject, PlacementMixin, WanderMixin, ChatMixin, MenuMixin, PetActionsMixin,
                 ProviderActionsMixin):
    replied = Signal(str, bool)
    hotkey = Signal()
    pet_made = Signal(str, object)
    info = Signal(str)

    def __init__(self, app: QApplication, pet_id: str):
        super().__init__()
        self.pets: dict[str, dict[str, Any]] = all_pets()
        self.pet_id = pet_id if pet_id in self.pets else DEFAULT_PET

        self.history: list[dict[str, Any]] = []
        self.last_reply: str | None = None
        self.busy = False
        self.closed_at = 0.0

        self.last: tuple[Any, Any] | None = None
        self.last_args: tuple[Any, Any, Any] | None = None
        self.no_window_since: float | None = None
        self.anim: QPropertyAnimation | None = None
        self.glide = load_config()["glide"]
        self.hidden = False
        self.vanish_timer: QTimer | None = None
        self.spot = 1.0
        self.track = 1.0
        self.track_edges: tuple[float, float] | None = None

        self.target = 1.0
        self.speed = 30.0
        self.next_walk = time.time() + random.uniform(20, 60)
        self.settle_until = 0.0
        self.grab = 0.0
        self.laps_left = 0

        self.view = PetView(self, self.pet)
        self.bubble = Bubble(self)
        self.replied.connect(self.on_reply)
        self.pet_made.connect(self.on_pet_made)
        self.info.connect(self.say)
        self.bubble.input.returnPressed.connect(self.submit)
        self.bubble.clip.clicked.connect(self.copy_command)

        avail = QGuiApplication.primaryScreen().availableGeometry()
        self.view.move(avail.right() - 200, avail.bottom() - 100)
        self.view.show()

        self.tracker = self._start_tracker()
        self._start_server()
        self.hotkey_note = self._start_hotkey(app)
        self._follow_system_theme()

        self.t_follow = QTimer(self, timeout=self.follow)
        self.t_follow.start(FOLLOW_MS)
        self.t_anim = QTimer(self, timeout=self.animate)
        self.t_anim.start(ANIMATE_MS)

    @property
    def pet(self) -> dict[str, Any]:
        return self.pets.get(self.pet_id) or self.pets[DEFAULT_PET]

    def refresh_pets(self) -> None:
        self.pets = all_pets()

    def switch_to(self, pet_id: str) -> None:
        self.refresh_pets()
        if pet_id not in self.pets:
            return
        self.pet_id = pet_id
        save_awake_pet(pet_id)
        self.view.pet = self.pet
        self.last = None
        self.follow()
        self.view.update()
        self.clear_chat()
        self.bubble.input.setPlaceholderText(self.ask_prompt())


    def _own_window_ids(self) -> set[int]:
        return {int(self.view.winId()), int(self.bubble.winId())}

    def _start_tracker(self):
        try:
            if IS_WIN:
                return WinTracker(self._own_window_ids)
            if QGuiApplication.platformName() == "xcb":
                return X11Tracker(self._own_window_ids)
        except Exception as e:  # noqa: BLE001
            print("window tracking off:", e, file=sys.stderr)
        return None

    def _start_server(self) -> None:
        QLocalServer.removeServer(SOCKET_NAME)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_command)
        self.server.listen(SOCKET_NAME)

    def _on_command(self) -> None:
        sock = self.server.nextPendingConnection()

        def read() -> None:
            for line in bytes(sock.readAll()).decode(errors="ignore").splitlines():
                if line == "quit":
                    QApplication.quit()
                elif line.startswith("dog "):
                    self.switch_to(line[4:].strip())

        sock.readyRead.connect(read)
        if sock.bytesAvailable():
            read()

    def _start_hotkey(self, app: QApplication) -> str:
        self.hotkey.connect(self.hotkey_pressed)
        try:
            if IS_WIN:
                self.win_hotkey = WinHotkey(self.hotkey.emit)
                app.installNativeEventFilter(self.win_hotkey)
            elif QGuiApplication.platformName() == "xcb":
                X11Hotkey(self.hotkey.emit).start()
            else:
                return "no global hotkey on Wayland"
        except Exception as e:  # noqa: BLE001
            print("hotkey off:", e, file=sys.stderr)
            return str(e)
        return ""

    def _follow_system_theme(self) -> None:
        with contextlib.suppress(AttributeError):
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                lambda *_: self.bubble.isVisible() and self.bubble.apply_theme(self.theme_name()))
