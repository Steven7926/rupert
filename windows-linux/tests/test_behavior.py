import pytest

from rupert.behavior import activity_mode, is_destructive, is_thanks, walk_plan


def test_activity_mode_understands_older_configs():
    assert activity_mode({"activity": "time"}) == "time"
    assert activity_mode({"wander": False}) == "stay"
    assert activity_mode({"activity": "bogus"}) == "normal"


@pytest.mark.parametrize("hour, asleep", [(2, True), (23, True), (7, False), (15, False)])
def test_lively_by_time_of_day_sleeps_at_night(hour, asleep):
    gap, speed = walk_plan("time", hour)
    assert (gap is None) == asleep and speed > 0


def test_stay_never_walks():
    assert walk_plan("stay")[0] is None


@pytest.mark.parametrize("cmd", ["rm -rf build", "git push --force", "git reset --hard", "DROP TABLE users"])
def test_destructive_commands_make_him_nervous(cmd):
    assert is_destructive(cmd)


def test_harmless_things_dont():
    assert not is_destructive("ls -la") and not is_destructive(None)
    assert is_thanks("thanks!") and is_thanks("good boy") and not is_thanks("git log")


def test_zoomies_never_happen_in_stay_mode():
    from rupert.behavior import zoomies_chance
    assert zoomies_chance("stay", 45, 1.0) == 0


def test_zoomies_are_likelier_in_lively_hours_and_for_zoomy_pets():
    from rupert.behavior import zoomies_chance
    assert zoomies_chance("time", 45, 0.4) > zoomies_chance("time", 26, 0.4)
    assert zoomies_chance("normal", 30, 0.7) > zoomies_chance("normal", 30, 0.05)
    assert zoomies_chance("time", 45, 1.0) <= 0.9


def test_zoomies_run_a_few_laps():
    from rupert.behavior import zoomies_laps
    assert all(3 <= zoomies_laps() <= 5 for _ in range(50))


def test_zoomies_runs_vary_in_length_and_stay_on_the_window():
    from rupert.behavior import zoomies_target
    lengths = set()
    for _ in range(300):
        t = zoomies_target(0.1, 1)
        assert 0 <= t <= 1 and t > 0.1
        lengths.add(round(t - 0.1, 2))
    assert len(lengths) >= 3


def test_zoomies_turn_around_at_an_edge():
    from rupert.behavior import zoomies_target
    assert all(zoomies_target(1.0, 1) < 1.0 for _ in range(50))
