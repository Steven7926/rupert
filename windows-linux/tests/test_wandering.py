from types import SimpleNamespace

from rupert.ui.wandering import WanderMixin


class View(SimpleNamespace):
    @property
    def paused(self):
        return self.compact and self.mode in ("walk", "run")


class Walker(WanderMixin):
    def __init__(self, mode="walk"):
        self.view = View(mode=mode, compact=False, facing=1)
        self.bubble = SimpleNamespace(isVisible=lambda: False)
        self.speed, self.track, self.spot, self.target = 30.0, 300.0, 0.2, 0.9
        self.laps_left = 2
        self.placed = 0

    def replace(self):
        self.placed += 1


def test_walk_keeps_going_across_window_switches():
    pet = Walker()
    pet.wander()
    before = pet.spot
    assert before > 0.2 and pet.view.mode == "walk"

    pet.view.compact = True
    for _ in range(5):
        pet.wander()
    assert pet.view.mode == "walk" and pet.spot == before and pet.target == 0.9

    pet.view.compact = False
    pet.wander()
    assert pet.view.mode == "walk" and pet.spot > before


def test_zoomies_keep_their_laps_while_squeezed():
    pet = Walker(mode="run")
    pet.view.compact = True
    pet.wander()
    assert pet.view.mode == "run" and pet.laps_left == 2


def test_opening_the_chat_still_stops_him():
    pet = Walker()
    pet.bubble = SimpleNamespace(isVisible=lambda: True)
    pet.wander()
    assert pet.view.mode == "sleep" and pet.laps_left == 0
