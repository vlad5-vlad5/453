#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alpha_all_in_one.py
===================

Один запуск — весь цикл:

    1. строит модель мопеда заново;
    2. САМ экспортирует её в .i3d с правильными настройками
       (Everything + Keep Collections выключено + без бинаризации);
    3. собирает мод и ставит его в папку модов игры.

Запускать в консоли Blender:

    exec(__import__("urllib.request").request.urlopen(
        "https://raw.githubusercontent.com/vlad5-vlad5/453/"
        "arena/01a02958-453/tools/alpha_all_in_one.py").read().decode("utf-8"))

Ручной экспорт больше не нужен — именно на нём чаще всего и терялись
камеры и физика, потому что модель пересобиралась уже ПОСЛЕ экспорта.
"""

import os
import sys
import tempfile
import urllib.request

BASE = ("https://raw.githubusercontent.com/vlad5-vlad5/453/"
        "arena/01a02958-453/tools/")

try:
    import bpy
except ImportError:
    print("Этот скрипт нужно запускать внутри Blender.")
    sys.exit(1)


def banner(text):
    print("")
    print("=" * 64)
    print("  " + text)
    print("=" * 64)


def fetch(name):
    url = BASE + name
    req = urllib.request.Request(url, headers={"User-Agent": "alpha-aio"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


# ---------------------------------------------------------------- 1. модель

banner("ШАГ 1/3  Сборка модели")
exec(compile(fetch("blender_build_alpha.py"), "blender_build_alpha.py", "exec"),
     {"__name__": "__main__"})


# ---------------------------------------------------------------- 2. экспорт

banner("ШАГ 2/3  Экспорт в .i3d")

if bpy.data.filepath:
    out_dir = os.path.dirname(bpy.data.filepath)
else:
    out_dir = tempfile.mkdtemp(prefix="alpha_i3d_")
    print("  .blend не сохранён, экспортирую во временную папку")

i3d_path = os.path.join(out_dir, "alphaMoped.i3d")

# снимаем выделение, чтобы 'ALL' точно взял всю сцену
bpy.ops.object.select_all(action="DESELECT")

result = bpy.ops.export_scene.i3d(
    filepath=i3d_path,
    selection="ALL",                        # Export Scope = Everything
    keep_collections_as_transformgroups=False,  # без обёртки Collection
    binarize_i3d=False,
    apply_modifiers=True,
    apply_unit_scale=True,
    copy_files=False,
    verbose_output=True,
)

print("  результат экспорта:", result)

if not os.path.isfile(i3d_path):
    print("")
    print("!! Экспорт не создал файл:", i3d_path)
    print("!! Сделайте экспорт вручную: File -> Export -> I3D")
    print("     Export Scope = Everything, Keep Collections = выключено")
    sys.exit(1)

size_kb = os.path.getsize(i3d_path) // 1024
print("  готово: %s (%d КБ)" % (i3d_path, size_kb))

# быстрая самопроверка содержимого
with open(i3d_path, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

checks = [
    ("<Camera",      "камеры"),
    ("rigidBodyType", "физическое тело"),
    ('name="alphaMoped"', "корневой узел"),
]
ok = True
for needle, label in checks:
    if needle in text:
        print("  [+] %s — есть" % label)
    else:
        print("  [!] %s — ОТСУТСТВУЕТ" % label)
        ok = False

if not ok:
    print("")
    print("  Чего-то не хватает. Мод всё равно соберётся, но в игре будут ошибки.")


# ---------------------------------------------------------------- 3. установка

banner("ШАГ 3/3  Сборка и установка мода")

os.environ["ALPHA_I3D"] = i3d_path
exec(compile(fetch("install_alpha_mod.py"), "install_alpha_mod.py", "exec"),
     {"__name__": "__main__"})

banner("ГОТОВО")
