#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_i3d_tree.py — печатает дерево узлов экспортированного .i3d
и сверяет установленный мод.

Нужен, чтобы увидеть глазами, ГДЕ реально оказались камеры и какие
атрибуты физики стоят на корне.

Запуск в консоли Blender:

    exec(__import__("urllib.request").request.urlopen(
      "https://raw.githubusercontent.com/vlad5-vlad5/453/"
      "arena/01a02958-453/tools/dump_i3d_tree.py").read().decode("utf-8"))
"""

import os
import glob
import xml.etree.ElementTree as ET

_LINES = []


def out(*parts):
    """Печатает и одновременно копит текст для буфера обмена."""
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)

SCENE_NODES = {"TransformGroup", "Shape", "Camera", "Light", "Audio",
               "NurbsCurve", "Skinned", "Mesh"}

INTERESTING = ("dynamic", "static", "kinematic", "compound", "compoundChild",
               "collision", "visibility", "fov")


def find_i3d():
    p = os.environ.get("ALPHA_I3D")
    if p and os.path.isfile(p):
        return p
    try:
        import bpy
        if bpy.data.filepath:
            d = os.path.dirname(bpy.data.filepath)
            for name in ("alphaMoped.i3d", "Untitled1.i3d"):
                c = os.path.join(d, name)
                if os.path.isfile(c):
                    return c
            hits = glob.glob(os.path.join(d, "*.i3d"))
            if hits:
                return max(hits, key=os.path.getmtime)
    except Exception:
        pass
    return None


def dump(path):
    out("=" * 70)
    out("ДЕРЕВО:", path)
    out("=" * 70)

    root = ET.parse(path).getroot()
    scene = root.find("Scene")
    if scene is None:
        out("нет секции <Scene>")
        return

    def walk(elem, prefix):
        idx = 0
        for child in elem:
            if child.tag not in SCENE_NODES:
                continue
            if prefix is None:
                cur = "%d>" % idx
            elif prefix.endswith(">"):
                cur = "%s%d" % (prefix, idx)
            else:
                cur = "%s|%d" % (prefix, idx)

            attrs = " ".join("%s=%s" % (k, child.get(k))
                             for k in INTERESTING if child.get(k) is not None)
            out("  %-12s %-16s %-22s %s" % (cur, child.tag,
                                              child.get("name", "?"), attrs))
            walk(child, cur)
            idx += 1

    out("  %-12s %-16s %-22s %s" % ("ПУТЬ", "ТИП", "ИМЯ", "АТРИБУТЫ"))
    walk(scene, None)


def check_installed():
    home = os.path.expanduser("~")
    cands = []
    for base in (home,):
        try:
            entries = [base] + [os.path.join(base, e) for e in os.listdir(base)
                                if e.lower().startswith("onedrive")]
        except Exception:
            entries = [base]
        for b in entries:
            for d in ("Documents", "Документы"):
                cands.append(os.path.join(b, d, "My Games",
                                          "FarmingSimulator2019", "mods"))

    mods = next((c for c in cands if os.path.isdir(c)), None)
    if not mods:
        return

    xml_path = os.path.join(mods, "FS19_AlphaMoped", "alphaMoped.xml")
    if not os.path.isfile(xml_path):
        out("\n(распакованной папки мода в mods нет — игра читает zip)")
        return

    with open(xml_path, encoding="utf-8", errors="replace") as f:
        t = f.read()

    out("\n" + "=" * 70)
    out("УСТАНОВЛЕННЫЙ alphaMoped.xml")
    out("=" * 70)
    for needle, label in (("<differentials>", "дифференциалы"),
                          ("<physics repr=", "новый синтаксис колёс"),
                          ("<forwardGear", "передачи"),
                          ('type="alphaMoped"', "тип техники")):
        out("  [%s] %s" % ("+" if needle in t else "!", label))


def to_clipboard():
    text = "\n".join(_LINES)
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
        print("")
        print("*" * 70)
        print("*  ВЫВОД СКОПИРОВАН В БУФЕР ОБМЕНА (%d строк)." % len(_LINES))
        print("*  Просто нажмите Ctrl+V в чате.")
        print("*" * 70)
    except Exception as exc:
        print("не удалось скопировать в буфер:", exc)


if __name__ == "__main__":
    p = find_i3d()
    if not p:
        out("Не нашёл .i3d")
    else:
        dump(p)
        check_installed()
    to_clipboard()
