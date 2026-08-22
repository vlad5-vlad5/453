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


def deliver(filename="alpha_report.txt", textblock="ALPHA_TREE"):
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
if __name__ == "__main__":
    p = find_i3d()
    if not p:
        out("Не нашёл .i3d")
    else:
        dump(p)
        check_installed()
    if p:
        out("")
        out("ИТОГ: " + one_line_summary(p))
        deliver()
