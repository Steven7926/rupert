#!/bin/bash
set -e
cd "$(dirname "$0")"

SOURCES=()
while IFS= read -r f; do SOURCES+=("$f"); done < <(find Sources -name '*.swift' | sort)
swiftc -O "${SOURCES[@]}" -o Rupert -framework Cocoa

APP=Rupert.app
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
mv Rupert "$APP/Contents/MacOS/Rupert"
cp -R ../shared "$APP/Contents/Resources/shared"
cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Rupert</string>
  <key>CFBundleExecutable</key><string>Rupert</string>
  <key>CFBundleIdentifier</key><string>local.rupert</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
EOF
codesign --force --sign - "$APP" >/dev/null 2>&1 || true

APP_PATH="$(pwd)/$APP"
{ printf "_RUPERT_APP='%s'\n" "$APP_PATH"; cat shell/rupert.zsh; } > ~/.rupert.zsh

if grep -q '^# rupert-command$' ~/.zshrc 2>/dev/null; then
  sed -i '' '/^# rupert-command$/,/^}$/d' ~/.zshrc
fi
if ! grep -q 'source ~/.rupert.zsh' ~/.zshrc 2>/dev/null; then
  printf '\n# rupert-commands\n[ -f ~/.rupert.zsh ] && source ~/.rupert.zsh\n' >> ~/.zshrc
fi

echo "Built $APP. Run: source ~/.zshrc, then: rupert on  (or: stewart on)"
