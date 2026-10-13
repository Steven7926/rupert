from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from rupert.behavior import ZOOMIES_SPEED, activity_mode, walk_plan, zoomies_chance, zoomies_laps, zoomies_target
from rupert.config import load_config

if TYPE_CHECKING:
    from rupert.ui.controller import Controller

TICK = 0.1
SETTLE_SECONDS = 1.2
CATCH_BREATH = 3.0
STAY_AFTER_DRAG = 180
MIN_TRIP = 0.25


class WanderMixin:
    def animate(self: Controller) -> None:
        self.view.tick += 1
        self.wander()
        self.view.update()

    def wander(self: Controller) -> None:
        v, now = self.view, time.time()
        if v.mode in ("walk", "run"):
            if self.bubble.isVisible():
                v.mode, self.laps_left = "sleep", 0
                return
            if v.paused:
                return
            step = self.speed * TICK / max(1.0, self.track)
            self.spot += max(-step, min(step, self.target - self.spot))
            if abs(self.target - self.spot) < 1e-3:
                if v.mode == "run" and self.laps_left > 0:
                    self.laps_left -= 1
                    self._run_leg(-v.facing)
                else:
                    v.mode, self.settle_until = "settle", now + (CATCH_BREATH if v.mode == "run" else SETTLE_SECONDS)
            self.replace()
        elif v.mode == "settle" and now > self.settle_until:
            v.mode = "sleep"
            self.schedule_walk()
        elif (v.mode == "sleep" and now > self.next_walk and not self.bubble.isVisible()
              and not v.compact and self.last):
            mode = activity_mode(load_config())
            gap, self.speed = walk_plan(mode)
            if gap is None:
                self.next_walk = now + 300
                return
            if random.random() < zoomies_chance(mode, self.speed, self.pet.get("energy", 0.2)):
                self.start_zoomies()
                return
            options = [x / 20 for x in range(21) if abs(x / 20 - self.spot) >= MIN_TRIP]
            self.target = random.choice(options)
            v.facing = 1 if self.target > self.spot else -1
            v.mode = "walk"
            self.replace()

    def start_zoomies(self: Controller) -> None:
        self.speed, self.laps_left = ZOOMIES_SPEED, zoomies_laps() - 1
        self.view.mode = "run"
        self._run_leg(-1 if self.spot > 0.5 else 1)
        self.replace()

    def _run_leg(self: Controller, direction: int) -> None:
        self.target = zoomies_target(self.spot, direction)
        self.view.facing = 1 if self.target > self.spot else -1

    def schedule_walk(self: Controller, at_least: float = 0) -> None:
        gap, _ = walk_plan(activity_mode(load_config()))
        now = time.time()
        self.next_walk = max(self.next_walk, now + at_least, now + (gap if gap is not None else 300))

    def replace(self: Controller) -> None:
        if self.last_args:
            self.place(*self.last_args, force=True)


    def drag_start(self: Controller, x: float) -> bool:
        if not self.track_edges:
            return False
        v = self.view
        self.laps_left = 0
        self.grab = x - (v.x() + v.sprite_x())
        v.mode = "carry"
        return True

    def drag_to(self: Controller, x: float) -> None:
        left, right = self.track_edges
        self.spot = max(0.0, min(1.0, (x - self.grab - left) / max(1.0, right - left)))
        self.target = self.spot
        self.replace()

    def drag_end(self: Controller) -> None:
        self.view.mode = "settle"
        self.settle_until = time.time() + 1.0
        self.next_walk = time.time()
        self.schedule_walk(at_least=STAY_AFTER_DRAG)
