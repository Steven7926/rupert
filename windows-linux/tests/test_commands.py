import pytest

from rupert import cli
from rupert.commands import is_command_name, sync_shims
from rupert.pets import pet_id_for, save_pet


def breed_pet(name):
    return {"name": name, "kind": "breed", "breed": "corgi", "color": "red", "personality": "zoomy"}


def test_is_pet_flag(monkeypatch):
    save_pet("biscuit", breed_pet("Biscuit"))
    for args, code in ((["--is-pet", "biscuit"], 0), (["--is-pet", "Biscuit"], 0), (["--is-pet", "rupert"], 0),
                       (["--is-pet", "nope"], 1), (["--is-pet"], 1)):
        with pytest.raises(SystemExit) as e:
            cli.main(args)
        assert e.value.code == code


def test_pet_id_never_takes_the_pet_command():
    assert pet_id_for("Pet") == "pet2"
    assert not is_command_name("pet")
    assert not is_command_name("café")
    assert is_command_name("mochi2")


def test_sync_shims(tmp_path):
    (tmp_path / "old.cmd").write_text("@x -m rupert old %*")
    (tmp_path / "other.cmd").write_text("@echo not ours")
    sync_shims(["rupert", "stewart", "biscuit", "pet"], tmp_path)
    names = sorted(p.stem for p in tmp_path.glob("*.cmd"))
    assert names == ["biscuit", "other", "pet", "rupert", "stewart"]
    body = (tmp_path / "biscuit.cmd").read_bytes()
    assert body.endswith(b"-m rupert biscuit %*\r\n")
    assert (tmp_path / "pet.cmd").read_bytes().endswith(b"-m rupert %*\r\n")


def test_sync_shims_skips_when_not_installed(tmp_path):
    sync_shims(["biscuit"], tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_saving_a_pet_on_windows_adds_its_command(tmp_path, monkeypatch):
    from rupert import commands, pets
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setattr(pets, "IS_WIN", True)
    monkeypatch.setattr(commands, "windows_bin", lambda: bin_dir)
    save_pet("biscuit", breed_pet("Biscuit"))
    assert (bin_dir / "biscuit.cmd").is_file()
    pets.delete_pet("biscuit")
    assert not (bin_dir / "biscuit.cmd").exists()
