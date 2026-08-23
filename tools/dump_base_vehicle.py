#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_base_vehicle.py — достаёт из установленной FS19 РАБОЧИЙ пример машины
и печатает ключевые секции: камеры, дифференциалы, трансмиссию, колесо.

Это первоисточник: так пишет сама GIANTS. Дальше остаётся просто повторить.
"""

import os
import re
import glob

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


def find_game_data():
    candidates = []
    for drive in ("C:", "D:", "E:"):
        candidates += [
            drive + r"\Program Files (x86)\Steam\steamapps\common\Farming Simulator 19\data",
            drive + r"\SteamLibrary\steamapps\common\Farming Simulator 19\data",
            drive + r"\Program Files (x86)\Farming Simulator 19\data",
            drive + r"\Games\Farming Simulator 19\data",
        ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    # запасной вариант — поиск
    for drive in ("C:\\", "D:\\"):
        hits = glob.glob(drive + "**/Farming Simulator 19/data", recursive=True)
        if hits:
            return hits[0]
    return None


# машины базовой игры: у них есть камеры, мотор, дифференциалы
PREFERRED = [
    "vehicles/lizard/pickup2014/pickup2014.xml",
    "vehicles/lizard/pickupTruck/pickupTruck.xml",
    "vehicles/lizard/carS/carS.xml",
    "vehicles/lizard/truckS/truckS.xml",
]

SECTIONS = [
    (r"<cameras>.*?</cameras>",                             "КАМЕРЫ"),
    (r"<differentialConfigurations>.*?</differentialConfigurations>",
     "ДИФФЕРЕНЦИАЛЫ"),
    (r"<transmission[^>]*/>|<transmission.*?</transmission>", "ТРАНСМИССИЯ"),
    (r"<motor [^>]*/>",                                     "МОТОР"),
    (r"<wheels\b[^>]*>",                                    "ТЕГ <wheels>"),
    (r"<wheel\b.*?</wheel>",                                "ОДНО КОЛЕСО"),
    (r"<enterable>.*?<cameras>",                            "НАЧАЛО <enterable>"),
]


def dump(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    out("=" * 68)
    out("ЭТАЛОН:", os.path.basename(path))
    out("=" * 68)

    for pattern, title in SECTIONS:
        m = re.search(pattern, text, re.S)
        out("")
        out("--- %s ---" % title)
        if not m:
            out("(не найдено)")
            continue
        block = m.group(0)
        lines = [l.rstrip() for l in block.splitlines()]
        if len(lines) > 18:
            lines = lines[:18] + ["   ... (обрезано)"]
        for l in lines:
            out(l.strip()[:100])


def deliver():
    text = "\n".join(_LINES)
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
        tb = bpy.data.texts.get("ALPHA_BASE") or bpy.data.texts.new("ALPHA_BASE")
        tb.clear()
        tb.write(text)
    except Exception:
        pass
    for d in (os.path.join(os.path.expanduser("~"), "Desktop"),
              os.path.expanduser("~")):
        if os.path.isdir(d):
            p = os.path.join(d, "alpha_base.txt")
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(text)
                print("")
                print("*  Сохранено:", p)
                try:
                    os.startfile(p)
                except Exception:
                    pass
                break
            except Exception:
                continue
    print("*  Также в буфере обмена и в текстовом блоке ALPHA_BASE")


if __name__ == "__main__":
    data = find_game_data()
    if not data:
        out("Папка data игры не найдена.")
    else:
        out("data игры:", data)
        found = None
        for rel in PREFERRED:
            p = os.path.join(data, rel.replace("/", os.sep))
            if os.path.isfile(p):
                found = p
                break
        if not found:
            hits = glob.glob(os.path.join(data, "vehicles", "**", "*.xml"),
                             recursive=True)
            for h in hits:
                try:
                    with open(h, encoding="utf-8", errors="replace") as f:
                        t = f.read()
                    if "<cameras>" in t and "<differentialConfigurations>" in t:
                        found = h
                        break
                except Exception:
                    continue
        if not found:
            out("Подходящий XML не найден.")
        else:
            dump(found)
    deliver()
