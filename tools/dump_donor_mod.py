#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_donor_mod.py — берёт РАБОЧИЙ мод техники из папки mods и печатает,
как в нём устроены камеры, дифференциалы, трансмиссия и колёса.

Идея простая: эти моды в игре работают, значит их синтаксис заведомо верный.
Копируем структуру у них, а не выдумываем.
"""

import os
import re
import zipfile

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


def mods_dir():
    home = os.path.expanduser("~")
    bases = [home]
    try:
        for e in os.listdir(home):
            if e.lower().startswith("onedrive"):
                bases.append(os.path.join(home, e))
    except Exception:
        pass
    for b in bases:
        for d in ("Documents", "Документы", ""):
            p = os.path.normpath(os.path.join(b, d, "My Games",
                                              "FarmingSimulator2019", "mods"))
            if os.path.isdir(p):
                return p
    return None


NEEDED = ("<cameras>", "<differentialConfigurations>", "<motorized>", "<wheels")

# небольшие машины ближе к мопеду, чем комбайны
PREFER = ("gaz", "uaz", "zil", "car", "moto", "paz", "niva", "moskvich", "lada")


def candidates(mods):
    """[(человекочитаемый источник, текст xml, приоритет)]"""
    found = []

    for name in sorted(os.listdir(mods)):
        path = os.path.join(mods, name)

        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(path) as z:
                    for inner in z.namelist():
                        if not inner.lower().endswith(".xml"):
                            continue
                        if inner.count("/") > 1:
                            continue
                        try:
                            t = z.read(inner).decode("utf-8", "replace")
                        except Exception:
                            continue
                        if all(k in t for k in NEEDED):
                            pri = 0 if any(w in name.lower() for w in PREFER) else 1
                            found.append(("%s :: %s" % (name, inner), t, pri))
            except Exception:
                continue

        elif os.path.isdir(path):
            try:
                for inner in os.listdir(path):
                    if not inner.lower().endswith(".xml"):
                        continue
                    try:
                        with open(os.path.join(path, inner), encoding="utf-8",
                                  errors="replace") as f:
                            t = f.read()
                    except Exception:
                        continue
                    if all(k in t for k in NEEDED):
                        pri = 0 if any(w in name.lower() for w in PREFER) else 1
                        found.append(("%s\\%s" % (name, inner), t, pri))
            except Exception:
                continue

    found.sort(key=lambda x: (x[2], len(x[1])))
    return found


SECTIONS = [
    (r"<enterable[^>]*>",                                    "тег <enterable>"),
    (r"<cameras>.*?</cameras>",                              "КАМЕРЫ"),
    (r"<differentialConfigurations>.*?</differentialConfigurations>",
     "ДИФФЕРЕНЦИАЛЫ"),
    (r"<transmission[^>]*/>|<transmission.*?</transmission>", "ТРАНСМИССИЯ"),
    (r"<motor [^>]*/>",                                      "МОТОР"),
    (r"<wheels\b[^>]*>",                                     "тег <wheels>"),
    (r"<wheel\b[^>]*>.*?</wheel>|<wheel\b[^>]*/>",           "ОДНО КОЛЕСО"),
    (r"<components>.*?</components>",                        "КОМПОНЕНТЫ"),
]


def dump(label, text, limit=16):
    out("=" * 68)
    out("ЭТАЛОН:", label)
    out("=" * 68)
    for pattern, title in SECTIONS:
        m = re.search(pattern, text, re.S)
        out("")
        out("--- %s ---" % title)
        if not m:
            out("(нет)")
            continue
        lines = [l.strip() for l in m.group(0).splitlines() if l.strip()]
        if len(lines) > limit:
            lines = lines[:limit] + ["... (обрезано)"]
        for l in lines:
            out(l[:110])


def deliver():
    text = "\n".join(_LINES)
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
        tb = bpy.data.texts.get("ALPHA_DONOR") or bpy.data.texts.new("ALPHA_DONOR")
        tb.clear()
        tb.write(text)
    except Exception:
        pass
    for d in (os.path.join(os.path.expanduser("~"), "Desktop"),
              os.path.expanduser("~")):
        if os.path.isdir(d):
            p = os.path.join(d, "alpha_donor.txt")
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
    print("*  Также в буфере обмена и в блоке ALPHA_DONOR")


if __name__ == "__main__":
    m = mods_dir()
    if not m:
        out("Папка mods не найдена")
    else:
        out("mods:", m)
        cands = candidates(m)
        out("подходящих моддерских машин:", len(cands))
        if not cands:
            out("Не нашёл мод с камерами и дифференциалами.")
        else:
            out("(беру самый компактный XML из списка)")
            dump(cands[0][0], cands[0][1])
            if len(cands) > 1:
                out("")
                out("Другие кандидаты:")
                for label, _, _ in cands[1:6]:
                    out("   " + label)
    deliver()
