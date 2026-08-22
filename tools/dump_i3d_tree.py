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


def one_line_summary(path):
    """Короткий итог — его можно просто перепечатать руками."""
    try:
        root = ET.parse(path).getroot()
        scene = root.find("Scene")
    except Exception as exc:
        return "PARSE-ERROR %s" % exc

    cams, first, phys = [], None, "-"

    def walk(elem, prefix):
        nonlocal first, phys
        idx = 0
        for child in elem:
            if child.tag not in SCENE_NODES:
                continue
            cur = ("%d>" % idx) if prefix is None else (
                "%s%d" % (prefix, idx) if prefix.endswith(">")
                else "%s|%d" % (prefix, idx))
            if first is None:
                first = "%s=%s" % (cur, child.get("name"))
                flags = [k for k in ("dynamic", "static", "compound")
                         if child.get(k) in ("true", "1")]
                phys = "+".join(flags) if flags else "НЕТ"
            if child.tag == "Camera":
                cams.append(cur)
            walk(child, cur)
            idx += 1

    walk(scene, None)
    return "ROOT[%s] PHYS[%s] CAM[%s]" % (first, phys,
                                          ",".join(cams) if cams else "НЕТ")


def deliver(path):
    text = "\n".join(_LINES)

    # 1) буфер обмена
    try:
        import bpy
        bpy.context.window_manager.clipboard = text
    except Exception:
        pass

    # 2) файл на Рабочем столе + открыть в Блокноте
    saved = None
    for d in (os.path.join(os.path.expanduser("~"), "Desktop"),
              os.path.join(os.path.expanduser("~"), "Рабочий стол"),
              os.path.expanduser("~")):
        if os.path.isdir(d):
            saved = os.path.join(d, "alpha_report.txt")
            try:
                with open(saved, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                saved = None
                continue
            break

    print("")
    print("*" * 70)
    print("*  ГЛАВНОЕ (можно просто перепечатать эту строку):")
    print("*  " + one_line_summary(path))
    print("*" * 70)
    if saved:
        print("*  Полный отчёт сохранён: %s" % saved)
        try:
            os.startfile(saved)          # откроется в Блокноте
            print("*  Файл открыт — там Ctrl+A, затем Ctrl+C.")
        except Exception:
            print("*  Откройте его вручную и скопируйте.")
        print("*" * 70)


if __name__ == "__main__":
    p = find_i3d()
    if not p:
        out("Не нашёл .i3d")
    else:
        dump(p)
        check_installed()
    if p:
        deliver(p)
