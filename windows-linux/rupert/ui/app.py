from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from rupert.cli import send
from rupert.ui.controller import Controller


def run_gui(pet_id: str) -> None:
    app = QApplication(sys.argv[:1])
    if send("ping"):
        send(f"dog {pet_id}")
        return
    app.setQuitOnLastWindowClosed(False)
    controller = Controller(app, pet_id)  # noqa: F841
    app.exec()
