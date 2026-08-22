#!/usr/bin/env bash
# Сборка мода в ZIP, готовый для папки mods FS19.
#
#   ./build.sh            -> build/FS19_FarmHelper.zip
#   ./build.sh install    -> дополнительно копирует zip в папку модов игры
#
set -euo pipefail

MOD_NAME="FS19_FarmHelper"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/$MOD_NAME"
OUT="$ROOT/build"

if [ ! -d "$SRC" ]; then
    echo "Не найдена папка мода: $SRC" >&2
    exit 1
fi

# 1. Проверка синтаксиса Lua (если установлен luac/lua)
if command -v luac5.1 >/dev/null 2>&1; then
    LUAC=luac5.1
elif command -v luac >/dev/null 2>&1; then
    LUAC=luac
else
    LUAC=""
fi

if [ -n "$LUAC" ]; then
    echo "==> Проверка синтаксиса Lua ($LUAC)"
    find "$SRC" -name '*.lua' -print0 | while IFS= read -r -d '' f; do
        "$LUAC" -p "$f"
        echo "    ok  ${f#$ROOT/}"
    done
else
    echo "==> luac не найден, пропускаю проверку Lua"
fi

# 2. Проверка XML
if command -v xmllint >/dev/null 2>&1; then
    echo "==> Проверка XML"
    find "$SRC" -name '*.xml' -print0 | while IFS= read -r -d '' f; do
        xmllint --noout "$f"
        echo "    ok  ${f#$ROOT/}"
    done
fi

# 3. Упаковка
mkdir -p "$OUT"
rm -f "$OUT/$MOD_NAME.zip"

echo "==> Упаковка $MOD_NAME.zip"
( cd "$SRC" && zip -r -q "$OUT/$MOD_NAME.zip" . -x '*.DS_Store' -x '__MACOSX/*' )

echo "==> Готово: $OUT/$MOD_NAME.zip"
unzip -l "$OUT/$MOD_NAME.zip" | tail -n +4 | head -n -2

# 4. Опциональная установка в папку модов (Windows / Git Bash / WSL)
if [ "${1:-}" = "install" ]; then
    CANDIDATES=(
        "$HOME/Documents/My Games/FarmingSimulator2019/mods"
        "$HOME/OneDrive/Documents/My Games/FarmingSimulator2019/mods"
        "/mnt/c/Users/$USER/Documents/My Games/FarmingSimulator2019/mods"
    )
    for dir in "${CANDIDATES[@]}"; do
        if [ -d "$dir" ]; then
            cp "$OUT/$MOD_NAME.zip" "$dir/"
            echo "==> Установлен в: $dir"
            exit 0
        fi
    done
    echo "Папка модов FS19 не найдена, скопируйте zip вручную." >&2
fi
