import json

from rupert import config
from rupert.config import load_config, update_config


def test_glide_is_on_by_default():
    assert load_config()["glide"] is True


def test_glide_can_be_turned_off_and_stays_off():
    update_config(glide=False)
    assert load_config()["glide"] is False
    update_config(activity="normal")
    assert load_config()["glide"] is False
    assert json.loads(config.CONFIG_PATH.read_text())["glide"] is False


def test_bad_glide_value_falls_back_to_default():
    config.CONFIG_PATH.write_text(json.dumps({"glide": "nope"}))
    assert load_config()["glide"] is True
