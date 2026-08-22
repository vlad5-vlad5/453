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

    print("=" * 70)
    print("ЛОГ:", log)
    print("=" * 70)

    with open(log, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    # последний запуск игры
    start = 0
    for i, ln in enumerate(lines):
        if "Game version" in ln or "Application" in ln and "start" in ln.lower():
            start = i
    body = lines[start:]

    print("\n--- СТРОКИ ПРО МОПЕД ---")
    found = False
    for ln in body:
        low = ln.lower()
        if "alphamoped" in low or "alpha_moped" in low:
            print(ln)
            found = True
    if not found:
        print("(ни одного упоминания — мод вообще не загружался)")

    print("\n--- ОШИБКИ ПОСЛЕДНЕГО ЗАПУСКА ---")
    errs = [ln for ln in body if ln.strip().startswith(("Error", "  Error"))
            or "Error:" in ln]
    if errs:
        for ln in errs[-40:]:
            print(ln)
    else:
        print("(ошибок нет)")

    print("\n--- ПРЕДУПРЕЖДЕНИЯ (последние 20) ---")
    warns = [ln for ln in body if "Warning" in ln]
    for ln in warns[-20:]:
        print(ln)

    print("\n--- ХВОСТ ЛОГА (последние 25 строк) ---")
    for ln in lines[-25:]:
        print(ln)


if __name__ == "__main__":
    main()
