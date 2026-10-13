# Contributing

Thanks for helping Rupert. A few notes so changes land smoothly.

## How it fits together

- `shared/` holds everything both apps read: pets, breeds, hats, providers, themes, the activity schedule and the prompts. Most changes to what Rupert *is* (a new breed, color, personality, hat or provider) are a change to one of these files, and both apps pick it up.
- `macos/` is the AppKit app. `build.sh` compiles everything in `Sources/` and copies `shared/` into the app bundle.
- `windows-linux/` is the PySide6 (Qt) app: the `rupert` package plus installers.

The two apps are written to behave the same. If you change behavior in one, please change the other too, or say in your PR that it's single-platform. The 16-bit color ramp is the one bit of math both apps implement; `tests/test_sprites.py` pins its numbers, and `rampColor()` in `macos/Sources/Pets/Breeds.swift` must produce the same ones.

## Running and testing

```sh
cd windows-linux
pip install "PySide6>=6.4" python-xlib pytest ruff
python -m rupert rupert on      # run from the checkout
pytest                          # pets, breeds, hats, prompts, providers, activity, shared data
ruff check .                    # lint (settings in pyproject.toml)

cd ../macos && ./build.sh && open Rupert.app
```

The tests check the shared data too: every breed color covers every region its template uses, every frame only uses letters that have a color, personalities are complete, and so on. Run them after editing anything in `shared/`.

## Code style

- Small files with one job each. In both apps the main controller is split by job (following windows, placement, wandering, chat, menu, pets, providers).
- Data in `shared/`, not in code.
- Python: type hints on public functions, docstrings that say why, ruff clean. No dependencies beyond PySide6 (and python-xlib on Linux).
- Swift: no dependencies beyond AppKit. Decode shared files with `Decodable` types where the shape is fixed.
- Answers must stay short. The caveman rules (`shared/prompts/caveman.txt`) and `tighten()` are the whole point.
- Never log or send API keys anywhere except the provider's own API.

## Good first contributions

- **More breeds, colors and personalities.** Add to `shared/breeds.json`. A new color is one line; a new personality is a sentence, three 2-word reactions, a "thinking" line and a dream. Check with `python tools/preview_pets.py --breeds` and `pytest`.
- **More hats.** Add to `shared/hats.json`, using symbols (not letters) for colors.
- **Provider presets.** Add an entry to `shared/providers.json`. Anything OpenAI-compatible only needs a base URL and an env var name.
- **Better photo drawings.** Improve `shared/prompts/draw_pet.txt` so photo pets come out cleaner.
- **More poses,** such as sitting or stretching.
- **Native Wayland window tracking** for GNOME and KDE.
- **Packaging** such as a signed `.app`, a Windows installer, or Homebrew and AUR packages.

Test on the platform you changed. For window following, check a normal window, a maximized one, minimizing, and switching apps.
