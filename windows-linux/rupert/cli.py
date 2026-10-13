from __future__ import annotations

import os
import subprocess
import sys
import time

from rupert.commands import sync_shims
from rupert.config import load_awake_pet, save_awake_pet
from rupert.paths import IS_WIN, PACKAGE_DIR, SOCKET_NAME
from rupert.pets import DEFAULT_PET, all_pets


def send(msg: str) -> bool:
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtNetwork import QLocalSocket
    _ = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    s = QLocalSocket()
    s.connectToServer(SOCKET_NAME)
    if not s.waitForConnected(500):
        return False
    s.write((msg + "\n").encode())
    s.flush()
    s.waitForBytesWritten(500)
    s.disconnectFromServer()
    return True


def spawn(pet_id: str) -> None:
    py = sys.executable
    args = ["-m", "rupert", "--run", pet_id]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PACKAGE_DIR.parent), env.get("PYTHONPATH")]))
    if IS_WIN:
        pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
        if os.path.exists(pyw):
            py = pyw
        detached, new_group = 0x00000008, 0x00000200
        subprocess.Popen([py, *args], creationflags=detached | new_group, close_fds=True, env=env)
    else:
        if env.get("XDG_SESSION_TYPE") == "wayland" and env.get("DISPLAY"):
            env.setdefault("QT_QPA_PLATFORM", "xcb")
        subprocess.Popen([py, *args], start_new_session=True, env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(pet_id: str, action: str) -> None:
    name = all_pets()[pet_id]["name"]
    if action == "off":
        print(f"{name} sleeps. bye." if send("quit") else f"{name} already off.")
    elif action in ("on", ""):
        save_awake_pet(pet_id)
        if send(f"dog {pet_id}"):
            print(f"{name} here.")
        else:
            spawn(pet_id)
            print(f"{name} waking up…")
    elif action == "restart":
        send("quit")
        time.sleep(0.6)
        save_awake_pet(pet_id)
        spawn(pet_id)
        print(f"{name} restarted.")
    else:
        print(f"usage: {pet_id} [on|off|restart]")


def main(argv: list[str] | None = None) -> None:
    args = [a.lower() for a in (sys.argv[1:] if argv is None else argv)]
    pets = all_pets()
    if args[:1] == ["--is-pet"]:
        sys.exit(0 if len(args) == 2 and args[1] in pets else 1)
    if args[:1] == ["--sync-commands"]:
        sync_shims(pets)
        return
    if args[:1] == ["--run"]:
        from rupert.ui.app import run_gui
        pet_id = args[1] if len(args) > 1 and args[1] in pets else load_awake_pet(set(pets), DEFAULT_PET)
        run_gui(pet_id)
        return
    if args and args[0] not in pets and args[0] not in ("on", "off", "restart"):
        print(f"no pet named {args[0]}. pets: {', '.join(sorted(pets))}")
        return
    pet_id = args[0] if args and args[0] in pets else load_awake_pet(set(pets), DEFAULT_PET)
    run(pet_id, args[1] if len(args) > 1 else "on")
