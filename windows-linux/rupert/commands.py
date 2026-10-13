from __future__ import annotations

import contextlib
import os
from collections.abc import Iterable
from pathlib import Path

RESERVED = {"pet"}

RUN = ('@setlocal & set "PYTHONPATH=%LOCALAPPDATA%\\Rupert" & '
       '"%LOCALAPPDATA%\\Rupert\\venv\\Scripts\\python.exe" -m rupert')


def windows_bin() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Rupert" / "bin"


def is_command_name(pet_id: str) -> bool:
    return pet_id.isascii() and pet_id.isalnum() and pet_id.lower() == pet_id and pet_id not in RESERVED


def sync_shims(pet_ids: Iterable[str], bin_dir: Path | None = None) -> None:
    bin_dir = bin_dir or windows_bin()
    if not bin_dir.is_dir():
        return
    wanted = {"pet": f"{RUN} %*"}
    wanted.update({pid: f"{RUN} {pid} %*" for pid in pet_ids if is_command_name(pid)})
    for shim in bin_dir.glob("*.cmd"):
        if shim.stem.lower() not in wanted:
            with contextlib.suppress(OSError):
                if "-m rupert" in shim.read_text(encoding="ascii", errors="ignore"):
                    shim.unlink()
    for name, line in wanted.items():
        shim = bin_dir / f"{name}.cmd"
        with contextlib.suppress(OSError):
            if not shim.is_file() or shim.read_text(encoding="ascii", errors="ignore").strip() != line:
                with open(shim, "w", encoding="ascii", newline="") as f:
                    f.write(line + "\r\n")
