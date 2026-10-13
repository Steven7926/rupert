from __future__ import annotations

from functools import cache
from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap

from rupert import shared

WINDOW_FLAGS = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint

THEMES: dict[str, dict[str, str]] = shared.data("themes")["themes"]


@cache
def mono_font() -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSize(10)
    return f


def color(value: Any, alpha: float = 1.0) -> QColor:
    c = QColor(value) if isinstance(value, str) else QColor(*value)
    if alpha < 1.0:
        c.setAlphaF(max(0.0, alpha))
    return c


def draw_glyph(p: QPainter, glyph: list[str], x: float, y: float, size: float, c: QColor) -> None:
    for gy, row in enumerate(glyph):
        for gx, ch in enumerate(row):
            if ch == "K":
                p.fillRect(QRectF(x + gx * size, y + gy * size, size, size), c)


def sprite_pixmap(pet: dict[str, Any], frame: str, px: float) -> QPixmap:
    if frame == "walk" and pet["walk"]:
        rows = pet["walk"][0]
    else:
        rows = pet["sleep" if frame == "sleep" else "awake"][0]
    pm = QPixmap(int(pet["w"] * px), int(len(rows) * px))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    for y, line in enumerate(rows):
        for x, ch in enumerate(line):
            if ch in pet["palette"]:
                p.fillRect(QRectF(x * px, y * px, px, px), color(pet["palette"][ch]))
    p.end()
    return pm
