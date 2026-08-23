#!/usr/bin/env bash
# Сборка модов в ZIP, готовые для папки mods FS19.
#
#   ./build.sh                  -> собрать все моды в build/
#   ./build.sh FS19_AlphaMoped  -> собрать только один
#   ./build.sh install          -> собрать все и скопировать в папку модов игры
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/build"

ALL_MODS=(FS19_FarmHelper FS19_AlphaMoped)

DO_INSTALL=0
MODS=()

for arg in "$@"; do
    if [ "$arg" = "install" ]; then
        DO_INSTALL=1
    else
        MODS+=("$arg")
    fi
done

if [ ${#MODS[@]} -eq 0 ]; then
    MODS=("${ALL_MODS[@]}")
fi

mkdir -p "$OUT"

check_xml() {
    if command -v xmllint >/dev/null 2>&1; then
        xmllint --noout "$1"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import sys,xml.dom.minidom;xml.dom.minidom.parse(sys.argv[1])" "$1"
    fi
}

build_mod() {
    local name="$1"
    local src="$ROOT/$name"

    if [ ! -d "$src" ]; then
        echo "!! нет папки мода: $name" >&2
        return 1
    fi

    echo "=============================================="
    echo "  $name"
    echo "=============================================="

    # XML
    while IFS= read -r -d '' f; do
        check_xml "$f"
        echo "  xml ok  ${f#$src/}"
    done < <(find "$src" -name '*.xml' -print0)

    # Lua (если есть luac)
    local luac=""
    command -v luac5.1 >/dev/null 2>&1 && luac=luac5.1
    [ -z "$luac" ] && command -v luac >/dev/null 2>&1 && luac=luac
    if [ -n "$luac" ]; then
        while IFS= read -r -d '' f; do
            "$luac" -p "$f"
            echo "  lua ok  ${f#$src/}"
        done < <(find "$src" -name '*.lua' -print0)
    fi

    # предупреждение про отсутствующие i3d (только локальные, не из $data игры)
    while IFS= read -r i3d; do
        if [ ! -f "$src/$i3d" ]; then
            echo "  !! ВНИМАНИЕ: $i3d отсутствует — мод не загрузится в игре."
            echo "     Соберите модель: см. tools/blender_build_alpha.py и README."
        fi
    done < <(grep -hoE '(<filename>|filename=")[^<"$]*\.i3d' "$src"/*.xml 2>/dev/null \
             | sed -E 's/^(<filename>|filename=")//' | sort -u)

    rm -f "$OUT/$name.zip"
    ( cd "$src" && zip -r -q "$OUT/$name.zip" . -x '*.DS_Store' -x '__MACOSX/*' -x '*.blend1' )
    echo "  -> build/$name.zip  ($(du -h "$OUT/$name.zip" | cut -f1))"
}

for m in "${MODS[@]}"; do
    build_mod "$m"
done

if [ "$DO_INSTALL" = "1" ]; then
    CANDIDATES=(
        "$HOME/Documents/My Games/FarmingSimulator2019/mods"
        "$HOME/OneDrive/Documents/My Games/FarmingSimulator2019/mods"
        "/mnt/c/Users/$USER/Documents/My Games/FarmingSimulator2019/mods"
    )
    for dir in "${CANDIDATES[@]}"; do
        if [ -d "$dir" ]; then
            for m in "${MODS[@]}"; do
                cp "$OUT/$m.zip" "$dir/"
            done
            echo "==> Установлено в: $dir"
            exit 0
        fi
    done
    echo "Папка модов FS19 не найдена, скопируйте zip вручную." >&2
fi
