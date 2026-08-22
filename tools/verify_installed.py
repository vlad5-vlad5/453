#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_installed.py — смотрит, ЧТО реально лежит в папке модов игры
и что из этого читает Farming Simulator.

Проверяет все возможные папки mods (обычные Документы и OneDrive),
находит и zip, и распакованную папку, показывает время изменения и
ключевые строки из alphaMoped.xml, который читает игра.
"""

import os
import time
import zipfile

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


def mods_dirs():
    home = os.path.expanduser("~")
    bases = [home]
    try:
        for e in os.listdir(home):
            if e.lower().startswith("onedrive"):
                bases.append(os.path.join(home, e))
    except Exception:
        pass

    found = []
    for b in bases:
        for d in ("Documents", "Документы", ""):
            p = os.path.join(b, d, "My Games", "FarmingSimulator2019", "mods")
            p = os.path.normpath(p)
            if os.path.isdir(p) and p not in found:
                found.append(p)
    return found


MARKERS = [
    ("<differentials>",                 "дифференциалы"),
    ("<physics repr=",                  "колёса: новый синтаксис"),
    ("<forwardGear",                    "передачи"),
    ('id="cameraOutside"',              "маппинг cameraOutside"),
]


def show_xml(label, text):
    out("    %s" % label)
    for needle, name in MARKERS:
        out("       [%s] %s" % ("+" if needle in text else "!", name))
    for line in text.splitlines():
        if 'id="camera' in line:
            out("       " + line.strip())


def main():
    dirs = mods_dirs()
    if not dirs:
        out("Папок mods не найдено вообще.")
        return

    out("=" * 68)
    out("НАЙДЕНО ПАПОК MODS:", len(dirs))
    out("=" * 68)

    for d in dirs:
        out("")
        out("ПАПКА:", d)

        zip_path = os.path.join(d, "FS19_AlphaMoped.zip")
        dir_path = os.path.join(d, "FS19_AlphaMoped")

        if not os.path.exists(zip_path) and not os.path.isdir(dir_path):
            out("  (мода тут нет)")
            continue

        if os.path.isdir(dir_path):
            out("  !! ЕСТЬ РАСПАКОВАННАЯ ПАПКА FS19_AlphaMoped")
            out("     изменена:", time.strftime(
                "%d.%m %H:%M", time.localtime(os.path.getmtime(dir_path))))
            out("     ВНИМАНИЕ: если рядом есть и zip, игра может читать папку!")
            x = os.path.join(dir_path, "alphaMoped.xml")
            if os.path.isfile(x):
                with open(x, encoding="utf-8", errors="replace") as f:
                    show_xml("alphaMoped.xml из ПАПКИ:", f.read())

        if os.path.exists(zip_path):
            out("  ZIP: FS19_AlphaMoped.zip  (%d КБ, изменён %s)" % (
                os.path.getsize(zip_path) // 1024,
                time.strftime("%d.%m %H:%M",
                              time.localtime(os.path.getmtime(zip_path)))))
            try:
                with zipfile.ZipFile(zip_path) as z:
                    data = z.read("alphaMoped.xml").decode("utf-8", "replace")
                show_xml("alphaMoped.xml из ZIP:", data)
            except Exception as exc:
                out("     не смог прочитать zip:", exc)


def deliver():
    text = "\n".join(_LINES)
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
        tb = bpy.data.texts.get("ALPHA_VERIFY") or bpy.data.texts.new("ALPHA_VERIFY")
        tb.clear()
        tb.write(text)
        print("")
        print("*  Отчёт также в буфере обмена и в текстовом блоке ALPHA_VERIFY")
    except Exception:
        pass


if __name__ == "__main__":
    main()
    deliver()
