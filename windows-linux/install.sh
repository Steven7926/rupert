#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

DIR="$HOME/.local/share/rupert"
mkdir -p "$DIR"
rm -rf "$DIR/rupert" "$DIR/shared"
cp -R "$HERE/rupert" "$DIR/rupert"
cp -R "$HERE/../shared" "$DIR/shared"
rm -f "$DIR/rupert.py"

if [ ! -x "$DIR/venv/bin/python" ]; then
  echo "Setting up Python environment (one time, ~1 min)…"
  python3 -m venv "$DIR/venv"
fi
"$DIR/venv/bin/python" -m pip install -q --upgrade pip
"$DIR/venv/bin/python" -m pip install -q "PySide6>=6.4" python-xlib

{ printf "_RUPERT_DIR='%s'\n" "$DIR"; cat "$HERE/shell/rupert.sh"; } > "$HOME/.rupert.sh"

for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [ -f "$rc" ] || continue
  grep -q 'source ~/.rupert.sh' "$rc" || \
    printf '\n# rupert-commands\n[ -f ~/.rupert.sh ] && source ~/.rupert.sh\n' >> "$rc"
done

echo "Installed. Open a new terminal (or run: source ~/.rupert.sh), then: rupert on"
