#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_alpha_compat.py — проверка совместимости донорской модели с FS19.

Отвечает на три вопроса, без которых пересадку начинать нельзя:

  1. Одинаковый ли формат у бинарника геометрии .i3d.shapes
     у донора (FS22) и у заведомо рабочих модов FS19?
     Сравниваем заголовки байт в байт.

  2. Как выглядит FS19-овский файл описания колеса?
     Берём живой пример из FS19_Zil_pack (weels/WheelsFront.xml)
     и рядом печатаем донорский wheels/wheels.xml (FS22).

  3. Есть ли в установленной игре те общие текстуры $data/...,
     на которые ссылается донорский i3d.

НИЧЕГО НЕ МЕНЯЕТ. Только читает и печатает.
"""

import os
import re
import zipfile

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


# ------------------------------------------------------------------ пути

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


def mods_dir():
    for b in _bases():
        for d in ("Documents", "Документы", ""):
            p = os.path.normpath(os.path.join(b, d, "My Games",
                                              "FarmingSimulator2019", "mods"))
            if os.path.isdir(p):
                return p
    return None


def game_data_dirs():
    """Где лежит папка data установленной игры."""
    cands = []
    for drive in ("C:", "D:", "E:", "F:"):
        for tail in (r"\Program Files (x86)\Steam\steamapps\common\Farming Simulator 19",
                     r"\Steam\steamapps\common\Farming Simulator 19",
                     r"\SteamLibrary\steamapps\common\Farming Simulator 19",
                     r"\Games\Farming Simulator 19",
                     r"\Program Files (x86)\Farming Simulator 2019",
                     r"\Program Files\Farming Simulator 2019"):
            p = drive + tail
            if os.path.isdir(os.path.join(p, "data")):
                cands.append(p)
    return cands


# ------------------------------------------------------------------ 1. shapes

def shapes_header(data):
    head = data[:24]
    return " ".join("%02X" % b for b in head)


def collect_shapes_from_zip(path, limit=2):
    res = []
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.lower().endswith(".i3d.shapes"):
                    res.append((n, z.read(n)[:24]))
                    if len(res) >= limit:
                        break
    except Exception as exc:
        out("   !! %s: %s" % (os.path.basename(path), exc))
    return res


def i3d_versions_from_zip(path):
    vers = []
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.lower().endswith(".i3d"):
                    head = z.read(n)[:400].decode("utf-8", "replace")
                    m = re.search(r'version="([\d.]+)"', head)
                    vers.append((n, m.group(1) if m else "?"))
    except Exception:
        pass
    return vers


def step1(mods, donor):
    out("")
    out("=" * 72)
    out("1. ФОРМАТ ГЕОМЕТРИИ: донор против рабочих модов FS19")
    out("=" * 72)

    out("")
    out("ДОНОР (FS22):")
    for n, head in collect_shapes_from_zip(donor, limit=4):
        out("   %-34s %s" % (os.path.basename(n), shapes_header(head)))
    for n, v in i3d_versions_from_zip(donor):
        out("   i3d %-30s version=%s" % (os.path.basename(n), v))

    out("")
    out("РАБОЧИЕ МОДЫ FS19 (эталон):")
    if not mods:
        out("   папку mods не нашёл")
        return

    shown = 0
    for name in sorted(os.listdir(mods)):
        if not name.lower().endswith(".zip"):
            continue
        if "alphaclassic" in name.lower():
            continue
        p = os.path.join(mods, name)
        got = collect_shapes_from_zip(p, limit=1)
        if not got:
            continue
        n, head = got[0]
        ver = ""
        vs = i3d_versions_from_zip(p)
        if vs:
            ver = "  i3d=%s" % vs[0][1]
        out("   %-26s %s%s" % (name[:26], shapes_header(head), ver))
        shown += 1
        if shown >= 12:
            break

    out("")
    out("   ЧИТАЕМ ТАК: первые 4 байта — версия формата.")
    out("   Совпадает с эталонами → модель заведётся в FS19.")


# ------------------------------------------------------------------ 2. колёса

def print_file_from_zip(path, inner, label, maxlen=6000):
    out("")
    out("=" * 72)
    out(label)
    out("=" * 72)
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if n.lower().replace("\\", "/").endswith(inner.lower())]
            if not names:
                out("   нет файла %s внутри %s" % (inner, os.path.basename(path)))
                return
            t = z.read(names[0]).decode("utf-8", "replace")
    except Exception as exc:
        out("   !! %s" % exc)
        return

    if len(t) > maxlen:
        t = t[:maxlen] + "\n... (обрезано)"
    for line in t.splitlines():
        if line.strip():
            out("   " + line.rstrip()[:200])


def step2(mods, donor):
    print_file_from_zip(donor, "wheels/wheels.xml",
                        "2а. КОЛЕСО ДОНОРА (формат FS22)")

    if not mods:
        return
    for name in sorted(os.listdir(mods)):
        low = name.lower()
        if low.endswith(".zip") and "zil" in low:
            p = os.path.join(mods, name)
            try:
                with zipfile.ZipFile(p) as z:
                    inner = [n for n in z.namelist()
                             if n.lower().endswith(".xml")
                             and ("weel" in n.lower() or "wheel" in n.lower())]
            except Exception:
                inner = []
            if inner:
                print_file_from_zip(p, inner[0],
                                    "2б. КОЛЕСО РАБОЧЕГО МОДА FS19 (%s :: %s)"
                                    % (name, inner[0]))
            break


# ------------------------------------------------------------------ 3. текстуры

def step3(donor):
    out("")
    out("=" * 72)
    out("3. ОБЩИЕ ФАЙЛЫ ИГРЫ, НА КОТОРЫЕ ССЫЛАЕТСЯ ДОНОР")
    out("=" * 72)

    refs = set()
    try:
        with zipfile.ZipFile(donor) as z:
            for n in z.namelist():
                if n.lower().endswith(".i3d"):
                    t = z.read(n).decode("utf-8", "replace")
                    for m in re.finditer(r'filename="(\$data/[^"]+)"', t):
                        refs.add(m.group(1))
    except Exception as exc:
        out("   !! %s" % exc)
        return

    games = game_data_dirs()
    if not games:
        out("   папку с установленной игрой не нашёл —")
        out("   проверить наличие файлов не могу, список просто для сведения:")
        for r in sorted(refs):
            out("      %s" % r)
        return

    game = games[0]
    out("   игра:", game)
    out("")
    missing = 0
    for r in sorted(refs):
        rel = r.replace("$data/", "data/").replace("/", os.sep)
        full = os.path.join(game, rel)
        ok = os.path.isfile(full)
        if not ok:
            missing += 1
        out("   [%s] %s" % ("+" if ok else "НЕТ", r))
    out("")
    out("   отсутствует файлов: %d из %d" % (missing, len(refs)))
    out("   (отсутствующие = розовые пятна на модели, чинится заменой пути)")


# ------------------------------------------------------------------ доставка

def _desktop_dirs():
    dirs = []
    for b in _bases():
        for name in ("Desktop", "Рабочий стол", ""):
            p = os.path.join(b, name)
            if os.path.isdir(p) and p not in dirs:
                dirs.append(p)
    return dirs


def deliver(filename="alpha_compat.txt", textblock="ALPHA_COMPAT"):
    text = "\n".join(_LINES)
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
    except Exception:
        pass
    shown = False
    try:
        import bpy
        tb = bpy.data.texts.get(textblock) or bpy.data.texts.new(textblock)
        tb.clear()
        tb.write(text)
        shown = True
    except Exception:
        pass
    saved = None
    for d in _desktop_dirs():
        cand = os.path.join(d, filename)
        try:
            with open(cand, "w", encoding="utf-8") as f:
                f.write(text)
            saved = cand
            break
        except Exception:
            continue
    opened = False
    if saved:
        try:
            os.startfile(saved)
            opened = True
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["notepad.exe", saved])
                opened = True
            except Exception:
                pass
    print("")
    print("*" * 72)
    if shown:
        print("*  СПОСОБ 1: вкладка Scripting → список текстов → '%s'" % textblock)
    if saved:
        print("*  СПОСОБ 2: файл — %s %s"
              % (saved, "(открылся сам)" if opened else ""))
    print("*  СПОСОБ 3: текст уже в буфере обмена, Ctrl+V.")
    print("*" * 72)


def find_donor():
    explicit = os.environ.get("ALPHA_SRC", "").strip().strip('"')
    if explicit and os.path.isfile(explicit):
        return explicit
    for b in _bases():
        for d in ("Downloads", "Загрузки", "Desktop", "Рабочий стол",
                  "Documents", "Документы", ""):
            for extra in ("", os.path.join("My Games", "FarmingSimulator2019", "mods")):
                p = os.path.join(b, d, extra)
                if not os.path.isdir(p):
                    continue
                for n in os.listdir(p):
                    if "alphaclassic" in n.lower() and n.lower().endswith(".zip"):
                        return os.path.join(p, n)
    return None


if __name__ == "__main__":
    try:
        donor = find_donor()
        mods = mods_dir()
        out("донор:", donor)
        out("mods :", mods)
        if donor:
            step1(mods, donor)
            step2(mods, donor)
            step3(donor)
        else:
            out("!! FS22_AlphaClassic.zip не найден")
    except Exception as exc:
        import traceback
        out("!! СБОЙ: %s" % exc)
        out(traceback.format_exc())
    deliver()
