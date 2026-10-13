from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QTimer
from PySide6.QtGui import QGuiApplication

from rupert.paths import IS_WIN
from rupert.sprites import full_px

if TYPE_CHECKING:
    from rupert.ui.controller import Controller

NOSE_INSET = 14
GLIDE_MS = 220
NO_WINDOW_GRACE = 0.15
MINIMIZE_MS = 350


class PlacementMixin:
    def to_logical(self: Controller, x: float, y: float) -> tuple[float, float]:
        for s in QGuiApplication.screens():
            g, dpr = s.geometry(), s.devicePixelRatio()
            if (g.x() <= x < g.x() + g.width() * dpr) and (g.y() <= y < g.y() + g.height() * dpr):
                return g.x() + (x - g.x()) / dpr, g.y() + (y - g.y()) / dpr
        dpr = QGuiApplication.primaryScreen().devicePixelRatio()
        return x / dpr, y / dpr

    def follow(self: Controller) -> None:
        if not self.tracker:
            return
        hit = self.tracker.active()
        if hit == "keep":
            return
        if not hit:
            self.park_if_no_window()
            return
        self.no_window_since = None
        handle, (left, top, right, bottom) = hit
        probe_x, probe_y = self.to_logical((left + right) / 2, top + 8)
        L, T = self.to_logical(left, top)
        R, B = self.to_logical(right, bottom)
        if any(math.isnan(v) for v in (L, T, R, B)):
            return
        self.place(handle, (round(L), round(T), round(R), round(B)), QPoint(int(probe_x), int(probe_y)))

    def park_if_no_window(self: Controller) -> None:
        now = time.time()
        if self.no_window_since is None:
            self.no_window_since = now
            return
        if now - self.no_window_since < NO_WINDOW_GRACE:
            return
        d = self.view.geometry()
        screen = QGuiApplication.screenAt(d.center()) or QGuiApplication.primaryScreen()
        a = screen.availableGeometry()
        floor = (a.left(), a.bottom() + 1, a.right() + 1, a.bottom() + 2)
        if self.last != ("floor", floor):
            self.place("floor", floor, a.center())

    def place(self: Controller, handle: Any, rect: tuple[int, int, int, int], probe: QPoint,
              force: bool = False) -> None:
        self.last_args = (handle, rect, probe)
        if (handle, rect) == self.last and not force:
            return
        if self.glide and handle == "floor" and self.last is not None and self.last[0] != "floor":
            self.vanish(MINIMIZE_MS)
        glide = self.glide and not self.hidden and self.last is not None and self.last[0] != handle
        self.last = (handle, rect)
        L, T, R, B = rect
        screen = QGuiApplication.screenAt(probe) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        room = T - avail.top()
        sw, sh, top_px = self.pet["w"], self.pet["h"], full_px(self.pet)

        if room >= sh * 2 + 2:
            px = max(2.0, min(top_px, math.floor((room - 2) / sh * 2) / 2))
            bottom = T + 1
            left, right = L + NOSE_INSET, R - sw * px - NOSE_INSET
            self.track = max(1.0, right - left)
            self.track_edges = (left, right)
            sx = left + self.spot * (right - left)
        else:
            px = max(1.5, min(3.0, math.floor(26 / sh * 2) / 2))
            bottom = T + 29
            sx = R - (150 if IS_WIN else 110) - sw * px - 22
        body = sh * px
        compact = px < top_px or (bottom - body - avail.top()) < 26
        self.view.compact = compact
        w, h = (sw * px + 26, body + 2) if compact else (sw * px + 10, body + 30)
        trail = self.view.trail()
        w += trail
        x = max(L - 4 - trail, sx - 4 - trail if self.view.facing > 0 else sx - (w - 4 - trail - sw * px))
        geo = QRect(int(x), int(bottom - h), int(w), int(h))

        self.view.px = px
        if glide:
            if self.anim:
                self.anim.stop()
            self.anim = QPropertyAnimation(self.view, b"geometry", self)
            self.anim.setDuration(GLIDE_MS)
            self.anim.setEasingCurve(QEasingCurve.InOutQuad)
            self.anim.setEndValue(geo)
            self.anim.valueChanged.connect(lambda _: self.position_bubble())
            self.anim.start()
        elif self.anim and self.anim.state() == QPropertyAnimation.Running:
            self.anim.setEndValue(geo)
        else:
            self.view.setGeometry(geo)
        self.view.update()
        self.position_bubble()

    def vanish(self: Controller, ms: int) -> None:
        if self.vanish_timer is None:
            self.vanish_timer = QTimer(self)
            self.vanish_timer.setSingleShot(True)
            self.vanish_timer.timeout.connect(self.reappear)
        self.hidden = True
        if self.anim:
            self.anim.stop()
        if self.bubble.isVisible():
            self.close_bubble()
        self.view.setWindowOpacity(0.0)
        self.vanish_timer.start(ms)

    def reappear(self: Controller) -> None:
        self.hidden = False
        self.view.setWindowOpacity(1.0)

    def position_bubble(self: Controller) -> None:
        if not self.bubble.isVisible():
            return
        d, bub, px = self.view.geometry(), self.bubble, self.view.px
        sprite_w = self.pet["w"] * px
        left = d.x() + self.view.sprite_x()
        head_x = left + (0.8 if self.view.facing > 0 else 0.2) * sprite_w
        head_top = d.y() + d.height() - self.pet["h"] * px
        screen = QGuiApplication.screenAt(d.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        down = head_top - 2 - bub.height() >= avail.top()
        x = min(max(head_x - bub.WIDTH + 40, avail.left() + 4), avail.right() - bub.WIDTH - 4)
        bub.set_tail(down, head_x - x)
        y = head_top - 2 - bub.height() if down else d.y() + d.height() + 2
        bub.move(int(x), int(y))
