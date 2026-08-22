#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_fs19_log.py — вытаскивает из log.txt игры всё, что относится к нашему моду.

Запуск из консоли Blender (одной строкой через exec) или обычным Python.

Печатает:
  * строки, где упоминается AlphaMoped / alphaMoped;
  * все Error / Warning из последнего запуска игры;
  * содержимое modDesc-ошибок, если они есть.
"""

import os
import glob

_LINES = []


def out(*parts):
    """Печатает и копит текст, чтобы потом отдать файлом и в буфер."""
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


def _desktop_dirs():
    home = os.path.expanduser("~")
    dirs = []
    bases = [home]
    try:
        for e in os.listdir(home):
            if e.lower().startswith("onedrive"):
                bases.append(os.path.join(home, e))
    except Exception:
        pass
    for b in bases:
        for name in ("Desktop", "Рабочий стол"):
            dirs.append(os.path.join(b, name))
    dirs.append(home)
    return [d for d in dirs if os.path.isdir(d)]


def deliver(filename="alpha_log.txt", textblock="ALPHA_LOG"):
    text = "\n".join(_LINES)

    # 1) буфер обмена Blender
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
    except Exception:
        pass

    # 2) текстовый блок внутри Blender — самый надёжный способ скопировать
    shown_in_blender = False
    try:
        import bpy
        tb = bpy.data.texts.get(textblock) or bpy.data.texts.new(textblock)
        tb.clear()
        tb.write(text)
        shown_in_blender = True
    except Exception:
        pass

    # 3) файл на диск
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

    # 4) попытки открыть его
    opened = False
    if saved:
        for opener in ("startfile", "notepad", "cmd"):
            try:
                if opener == "startfile":
                    os.startfile(saved)
                elif opener == "notepad":
                    import subprocess
                    subprocess.Popen(["notepad.exe", saved])
                else:
                    import subprocess
                    subprocess.Popen(["cmd", "/c", "start", "", saved], shell=False)
                opened = True
                break
            except Exception:
                continue

    print("")
    print("*" * 70)
    if shown_in_blender:
        print("*  СПОСОБ 1 (надёжный): в Blender вверху выберите вкладку Scripting,")
        print("*  в текстовом редакторе нажмите на выпадающий список файлов и")
        print("*  выберите '%s'. Затем Ctrl+A, Ctrl+C." % textblock)
    if saved:
        print("*  СПОСОБ 2: файл лежит здесь —")
        print("*     %s" % saved)
        print("*  %s" % ("он должен был открыться сам." if opened
                          else "откройте его двойным щелчком."))
    print("*  СПОСОБ 3: текст уже в буфере обмена — попробуйте просто Ctrl+V.")
    print("*" * 70)
def find_log():
    homes = []
    for env in ("USERPROFILE", "HOME"):
        v = os.environ.get(env)
        if v:
            homes.append(v)
    homes.append(os.path.expanduser("~"))

    subdirs = []
    for h in homes:
        if not os.path.isdir(h):
            continue
        bases = [h]
        try:
            for e in os.listdir(h):
                if e.lower().startswith("onedrive"):
                    bases.append(os.path.join(h, e))
        except Exception:
            pass
        for b in bases:
            for docs in ("Documents", "Документы", ""):
                subdirs.append(os.path.join(b, docs, "My Games",
                                            "FarmingSimulator2019", "log.txt"))

    for p in subdirs:
        if os.path.isfile(p):
            return p

    hits = []
    for h in homes:
        hits += glob.glob(os.path.join(h, "**", "FarmingSimulator2019", "log.txt"),
                          recursive=True)
    return hits[0] if hits else None


def main():
    log = find_log()
    if not log:
        print("log.txt не найден. Обычно он тут:")
        print(r"  Документы\My Games\FarmingSimulator2019\log.txt")
        return

    out("=" * 70)
    out("ЛОГ:", log)
    out("=" * 70)

    with open(log, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    # последний запуск игры
    start = 0
    for i, ln in enumerate(lines):
        if "Game version" in ln or "Application" in ln and "start" in ln.lower():
            start = i
    body = lines[start:]

    out("\n--- СТРОКИ ПРО МОПЕД ---")
    found = False
    for ln in body:
        low = ln.lower()
        if "alphamoped" in low or "alpha_moped" in low:
            out(ln)
            found = True
    if not found:
        out("(ни одного упоминания — мод вообще не загружался)")

    # чужие моды не нужны — оставляем только наши строки и общие сбои Lua
    def ours(ln):
        low = ln.lower()
        if "alphamoped" in low:
            return True
        return "running lua method" in low

    out("\n--- ОШИБКИ (только наши) ---")
    errs = [ln for ln in body if "Error" in ln and ours(ln)]
    if errs:
        for ln in errs[-20:]:
            out(ln)
    else:
        out("(ошибок по мопеду нет)")

    others = len([ln for ln in body if "Error" in ln and not ours(ln)])
    out("(ошибок от других модов: %d — не наши, пропущены)" % others)

    deliver()


if __name__ == "__main__":
    main()
