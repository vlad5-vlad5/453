#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
list_alpha_zips.py — показывает ВСЕ архивы Альфы, какие есть на диске,
и чем они друг от друга отличаются.

Понадобился, когда рядом оказались FS22_AlphaClassic.zip и
FS19_AlphaClassic.zip: надо понять, откуда взялся второй и что внутри.

Только читает.
"""

import os
import re
import zipfile

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


def _bases():
    home = os.path.expanduser("~")
    for env in ("USERPROFILE", "HOME"):
        v = os.environ.get(env)
        if v and os.path.isdir(v):
            home = v
            break
    bases = [home]
    try:
        for e in os.listdir(home):
            if e.lower().startswith("onedrive"):
                bases.append(os.path.join(home, e))
    except Exception:
        pass
    return bases


def search_dirs():
    dirs = []

    def add(p):
        p = os.path.normpath(p)
        if os.path.isdir(p) and p not in dirs:
            dirs.append(p)

    for b in _bases():
        for d in ("Downloads", "Загрузки", "Desktop", "Рабочий стол",
                  "Documents", "Документы", ""):
            add(os.path.join(b, d))
            add(os.path.join(b, d, "My Games", "FarmingSimulator2019", "mods"))
            add(os.path.join(b, d, "My Games", "FarmingSimulator2022", "mods"))
    return dirs


def shapes_version(head):
    b1, b2, b3, b4 = head[0], head[1], head[2], head[3]
    if b1 >= 4:
        return b1, b3
    if b4 in (2, 3):
        return b4, b2
    return None, None


def describe(path):
    out("")
    out("=" * 72)
    out(path)
    out("   размер %.1f МБ, изменён %s"
        % (os.path.getsize(path) / 1048576.0,
           __import__("time").strftime("%Y-%m-%d %H:%M",
                                       __import__("time").localtime(
                                           os.path.getmtime(path)))))
    out("=" * 72)

    try:
        z = zipfile.ZipFile(path)
    except Exception as exc:
        out("   не открывается:", exc)
        return

    with z:
        names = z.namelist()
        out("   файлов: %d" % len(names))
        for n in sorted(names):
            if n.endswith("/"):
                continue
            out("      %9d  %s" % (z.getinfo(n).file_size, n))

        for n in names:
            if n.lower().endswith(".i3d.shapes"):
                v, seed = shapes_version(z.read(n)[:4])
                mark = "подходит FS19" if v == 5 else (
                    "формат FS22, FS19 не примет" if v == 7 else "?")
                out("   геометрия %-28s версия %s (%s)"
                    % (os.path.basename(n), v, mark))

        for n in names:
            if n.lower().endswith("moddesc.xml"):
                t = z.read(n).decode("utf-8", "replace")
                m = re.search(r'descVersion="(\d+)"', t)
                a = re.search(r"<author>(.*?)</author>", t, re.S)
                out("   modDesc: descVersion=%s, автор=%s"
                    % (m.group(1) if m else "?",
                       (a.group(1).strip()[:60] if a else "?")))
                for line in t.splitlines():
                    ls = line.strip()
                    if ls.startswith("<type ") or ls.startswith("<storeItem"):
                        out("      " + ls[:160])

        for n in names:
            low = n.lower()
            if low.endswith(".xml") and "moddesc" not in low:
                t = z.read(n).decode("utf-8", "replace")
                if "<vehicle" in t:
                    m = re.search(r'<vehicle[^>]*type="([^"]+)"', t)
                    f = re.search(r"<filename>(.*?)</filename>", t)
                    out("   конфиг %s: type=%s, модель=%s"
                        % (n, m.group(1) if m else "?",
                           f.group(1) if f else "?"))


def _desktop_dirs():
    dirs = []
    for b in _bases():
        for name in ("Desktop", "Рабочий стол", ""):
            p = os.path.join(b, name)
            if os.path.isdir(p) and p not in dirs:
                dirs.append(p)
    return dirs


def deliver(filename="alpha_zips.txt", textblock="ALPHA_ZIPS"):
    text = "\n".join(_LINES)
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
        tb = bpy.data.texts.get(textblock) or bpy.data.texts.new(textblock)
        tb.clear()
        tb.write(text)
    except Exception:
        pass
    for d in _desktop_dirs():
        try:
            with open(os.path.join(d, filename), "w", encoding="utf-8") as f:
                f.write(text)
            print("\n*  отчёт: %s" % os.path.join(d, filename))
            break
        except Exception:
            continue
    print("*  он же в буфере обмена и в тексте '%s'" % textblock)


if __name__ == "__main__":
    found = []
    for d in search_dirs():
        try:
            names = os.listdir(d)
        except Exception:
            continue
        for n in names:
            if n.lower().endswith(".zip") and "alpha" in n.lower():
                p = os.path.join(d, n)
                if p not in found:
                    found.append(p)

    out("НАЙДЕНО АРХИВОВ С ИМЕНЕМ ALPHA: %d" % len(found))
    for p in found:
        out("   " + p)

    for p in found:
        try:
            describe(p)
        except Exception as exc:
            out("!! %s: %s" % (p, exc))

    deliver()
