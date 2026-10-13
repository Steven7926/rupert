from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from rupert.behavior import BANG, BANG_COLOR, DUST_COLOR, HEART, HEART_COLOR
from rupert.sprites import full_px
from rupert.ui.common import WINDOW_FLAGS, color, draw_glyph

if TYPE_CHECKING:
    from rupert.ui.controller import Controller

RUB_CHANGES, RUB_WINDOW = 3, 1.5
DRAG_THRESHOLD = 4
DUST_ROOM = 22


class PetView(QWidget):
    def __init__(self, ctl: Controller, pet: dict[str, Any]):
        super().__init__(None, WINDOW_FLAGS | Qt.WindowDoesNotAcceptFocus)
        self.ctl = ctl
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.pet = pet
        self.awake = False
        self.tick = 0
        self.px = full_px(pet)
        self.compact = False
        self.mode = "sleep"
        self.facing = 1
        self.happy_until = 0.0
        self.nervous_until = 0.0
        self._rubs: list[float] = []
        self._hover_x: float | None = None
        self._hover_dir = 0
        self._press_x: float | None = None
        self._moved = self._dragging = False
        self.setMouseTracking(True)
        self.resize(int(pet["w"] * self.px + 10), int(pet["h"] * self.px + 30))


    @property
    def paused(self) -> bool:
        return self.compact and self.mode in ("walk", "run")

    @property
    def shown(self) -> str:
        return "settle" if self.paused else self.mode

    def _frame(self) -> tuple[list[str], float, float]:
        b, px, t = self.pet, self.px, self.tick
        now = time.time()
        happy, nervous = now < self.happy_until, now < self.nervous_until
        if self.shown == "carry":
            return b["awake"][(t // 2) % len(b["awake"])], 2 * px, 0
        if self.shown == "run":
            frames = b["walk"] or b["awake"][:1]
            return frames[t % len(frames)], px if t % 2 else 0, 0
        if nervous and self.shown != "walk":
            return b["awake"][0], 0, px * 0.5 if t % 2 else -px * 0.5
        if happy and self.shown != "walk":
            return b["awake"][t % len(b["awake"])], px if t % 4 == 0 else 0, px if (t // 2) % 2 else -px
        if self.awake or self.shown == "settle":
            return b["awake"][(t // 2) % len(b["awake"])], 0, 0
        if self.shown == "walk" and b["walk"]:
            return b["walk"][(t // 2) % len(b["walk"])], 0, 0
        if self.shown == "walk":
            return b["awake"][0], px if (t // 2) % 2 else 0, 0
        return b["sleep"][(t // 12) % len(b["sleep"])], 0, 0

    def paintEvent(self, _event) -> None:
        b, px = self.pet, self.px
        sprite, hop, wiggle = self._frame()
        if self.facing < 0:
            sprite = [r[::-1] for r in sprite]
        ox = self.sprite_x() + wiggle
        top = self.height() - len(sprite) * px - hop
        pal = b["palette"]
        p = QPainter(self)
        if self.shown == "run":
            self._paint_dust(p, ox)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        halo = color(b["halo"])
        for y, line in enumerate(sprite):
            for x, ch in enumerate(line):
                if ch in pal:
                    p.fillRect(QRectF(ox - 1 + x * px, top - 1 + y * px, px + 2, px + 2), halo)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        for y, line in enumerate(sprite):
            for x, ch in enumerate(line):
                if ch in pal:
                    p.fillRect(QRectF(ox + x * px, top + y * px, px, px), color(pal[ch]))
        now = time.time()
        if now < self.happy_until:
            self._paint_hearts(p, ox, top)
        elif now < self.nervous_until:
            self._paint_bang(p, ox, top)
        elif not self.awake and self.shown == "sleep":
            self._paint_dreams(p, top)

    def trail(self) -> float:
        return DUST_ROOM if self.shown == "run" else 0

    def sprite_x(self) -> float:
        if self.facing > 0:
            return 4 + self.trail()
        return self.width() - 4 - self.trail() - self.pet["w"] * self.px

    def _paint_dust(self, p: QPainter, ox: float) -> None:
        rear = ox if self.facing > 0 else ox + self.pet["w"] * self.px
        for i in range(3):
            t = ((self.tick + i * 3) % 9) / 9
            s = self.px * (1.5 + t * 1.5)
            x = rear - 3 - t * 16 - s if self.facing > 0 else rear + 3 + t * 16
            y = self.height() - s - t * 6
            p.fillRect(QRectF(x, y, s, s), color(DUST_COLOR, 0.8 * (1 - t)))

    def _head_x(self, ox: float) -> float:
        return ox + (0.75 if self.facing > 0 else 0.25) * self.pet["w"] * self.px

    def _paint_dreams(self, p: QPainter, top: float) -> None:
        b, px, glyph = self.pet, self.px, self.pet["dream"]
        for i in range(3):
            t = ((self.tick + i * 14) % 42) / 42
            s = 1.5 if self.compact else (2 if t < 0.5 else 2.5)
            x = 4 + b["w"] * px + 2 + t * 12 if self.compact else 4 + 0.75 * b["w"] * px + t * 16
            if self.facing < 0:
                x = self.width() - x - len(glyph[0]) * s
            y = (self.height() - len(glyph) * s - 1) * (1 - t) if self.compact else top - 10 - t * 16
            draw_glyph(p, glyph, x, y, s, color(b["dream_color"], 1 - t))

    def _paint_hearts(self, p: QPainter, ox: float, top: float) -> None:
        head = self._head_x(ox)
        for i in range(3):
            t = ((self.tick * 2 + i * 9) % 27) / 27
            s = 1.0 if self.compact else 1.5
            x = head + (i - 1) * 9 + t * 4 * (1 if i % 2 else -1)
            y = (self.height() - 8 * s) * (1 - t) if self.compact else top - 6 - t * 20
            draw_glyph(p, HEART, x, y, s, color(HEART_COLOR, 1 - t * t))

    def _paint_bang(self, p: QPainter, ox: float, top: float) -> None:
        s = 1.5 if self.compact else 2.0
        y = (1 if self.compact else top - 16) - (2 if (self.tick // 2) % 2 else 0)
        draw_glyph(p, BANG, self._head_x(ox) - s, y, s, color(BANG_COLOR))


    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._press_x = e.globalPosition().x()
            self._dragging = self._moved = False
        elif e.button() == Qt.RightButton:
            self.ctl.show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e) -> None:
        x = e.globalPosition().x()
        if not e.buttons():
            self._feel_rub(x)
            return
        if not (e.buttons() & Qt.LeftButton) or self._press_x is None:
            return
        if not self._moved and abs(x - self._press_x) > DRAG_THRESHOLD:
            self._moved = True
            self._dragging = self.ctl.drag_start(self._press_x)
        if self._dragging:
            self.ctl.drag_to(x)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() != Qt.LeftButton:
            return
        if self._dragging:
            self.ctl.drag_end()
        elif not self._moved:
            self.ctl.toggle()
        self._dragging, self._press_x = False, None

    def leaveEvent(self, e) -> None:
        self._hover_x, self._hover_dir = None, 0
        super().leaveEvent(e)

    def _feel_rub(self, x: float) -> None:
        if self._hover_x is not None and abs(x - self._hover_x) >= 3:
            direction = 1 if x > self._hover_x else -1
            if self._hover_dir and direction != self._hover_dir:
                now = time.time()
                self._rubs = [t for t in self._rubs if now - t < RUB_WINDOW] + [now]
                if len(self._rubs) >= RUB_CHANGES:
                    self.ctl.petted()
            self._hover_dir = direction
        if self._hover_x is None or abs(x - self._hover_x) >= 3:
            self._hover_x = x
