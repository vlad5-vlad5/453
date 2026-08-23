#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_alpha_donor.py — разведка перед пересадкой модели.

Ищет на компьютере архив мода с готовой моделью Альфы
(по умолчанию FS22_AlphaClassic.zip) и печатает всё, что нужно знать,
чтобы встроить его модель в наш FS19_AlphaMoped:

  * список файлов внутри архива (i3d, shapes, текстуры, xml);
  * версию формата i3d и заголовок бинарника .i3d.shapes
    (это решает, «переварит» ли модель движок FS19);
  * полное дерево узлов с индексными путями;
  * какие узлы похожи на колёса / фару / руль;
  * ключевые куски vehicle-xml донора (колёса, i3dMappings).

НИЧЕГО НЕ МЕНЯЕТ. Только читает и печатает.

Запуск в консоли Blender (Window → Toggle System Console, вкладка Scripting):

    import urllib.request
    exec(urllib.request.urlopen(
      "https://raw.githubusercontent.com/vlad5-vlad5/453/<SHA>/tools/"
      "dump_alpha_donor.py").read().decode("utf-8"))

Если архив лежит в необычном месте — укажите его явно:

    import os; os.environ["ALPHA_SRC"] = r"C:\\Users\\solda\\Downloads\\FS22_AlphaClassic.zip"
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


# ------------------------------------------------------------------ поиск zip

# как может называться архив с моделью
NAME_HINTS = ("alphaclassic", "alpha_classic", "alphaclassic110",
              "fs22_alpha", "alpha110", "alpha")


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


def find_zip():
    explicit = os.environ.get("ALPHA_SRC", "").strip().strip('"')
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        out("!! ALPHA_SRC указан, но файла нет:", explicit)

    hits = []
    for d in search_dirs():
        try:
            names = os.listdir(d)
        except Exception:
            continue
        for n in names:
            low = n.lower()
            if not low.endswith(".zip"):
                continue
            if any(h in low.replace(" ", "") for h in NAME_HINTS):
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    hits.append(p)

    if not hits:
        return None
    # самый свежий и самый «похожий по имени»
    hits.sort(key=lambda p: ("alphaclassic" not in os.path.basename(p).lower(),
                             -os.path.getmtime(p)))
    if len(hits) > 1:
        out("Нашёл несколько подходящих архивов:")
        for h in hits:
            out("   ", h)
    return hits[0]


# ------------------------------------------------------------------ дерево i3d

SCENE_NODES = {"TransformGroup", "Shape", "Camera", "Light", "Audio",
               "NurbsCurve", "Skinned", "Mesh"}

INTERESTING = ("dynamic", "static", "kinematic", "compound", "compoundChild",
               "collisionMask", "visibility", "nonRenderable")

WHEELISH = ("wheel", "rad", "koleso", "tire", "reifen", "felge", "rim",
            "kolo", "wiel")
LIGHTISH = ("light", "lamp", "far", "svet", "headl", "blink", "turn", "brake")
STEERISH = ("steer", "handle", "bar", "lenk", "rul", "fork", "vilka")


def dump_tree(i3d_bytes, label):
    out("")
    out("=" * 72)
    out("ДЕРЕВО УЗЛОВ:", label)
    out("=" * 72)

    try:
        root = ET.fromstring(i3d_bytes)
    except Exception as exc:
        out("!! не разобрался в i3d:", exc)
        return {}

    out("версия формата i3d: %s   (FS19 пишет 1.6)" % root.get("version"))

    files = root.find("Files")
    if files is not None:
        out("")
        out("ВНЕШНИЕ ФАЙЛЫ (текстуры и т.п.):")
        for f in files:
            out("   id=%-4s %s" % (f.get("fileId"), f.get("filename")))

    scene = root.find("Scene")
    if scene is None:
        out("!! нет секции <Scene>")
        return {}

    index = {}
    guesses = {"колёса": [], "свет": [], "руль/вилка": []}

    def walk(elem, prefix, depth):
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

            name = child.get("name", "?")
            attrs = " ".join("%s=%s" % (k, child.get(k))
                             for k in INTERESTING if child.get(k) is not None)
            out("  %-14s %s%-15s %-28s %s"
                % (cur, "  " * depth, child.tag, name, attrs))

            index[name] = cur
            low = name.lower()
            if any(h in low for h in WHEELISH):
                guesses["колёса"].append((name, cur))
            if any(h in low for h in LIGHTISH):
                guesses["свет"].append((name, cur))
            if any(h in low for h in STEERISH):
                guesses["руль/вилка"].append((name, cur))

            walk(child, cur, depth + 1)
            idx += 1

    out("")
    out("  %-14s %-15s %-28s %s" % ("ПУТЬ", "ТИП", "ИМЯ", "ФИЗИКА"))
    walk(scene, None, 0)

    out("")
    out("ПОХОЖЕ НА:")
    for k, v in guesses.items():
        if v:
            out("  %s:" % k)
            for name, path in v[:24]:
                out("      %-30s %s" % (name, path))
        else:
            out("  %s: не нашёл по имени" % k)

    return index


# ------------------------------------------------------------------ vehicle xml

XML_KEYS = ("<wheels", "<wheel ", "<physics ", "<i3dMappings", "<i3dMapping ",
            "<motor", "<transmission", "<camera", "<enterable",
            "<ackermannSteering", "<differential", "<lights", "<size")


def dump_vehicle_xml(text, label):
    out("")
    out("=" * 72)
    out("VEHICLE XML ДОНОРА:", label)
    out("=" * 72)

    for raw in text.splitlines():
        line = raw.strip()
        if any(line.startswith(k.strip()) or k in line for k in XML_KEYS):
            out("   " + line[:200])


# ------------------------------------------------------------------ основное

def main():
    zpath = find_zip()
    if not zpath:
        out("!! Архив с моделью не найден.")
        out("   Скачайте FS22_AlphaClassic.zip и положите в Загрузки,")
        out("   либо укажите путь:")
        out('   os.environ["ALPHA_SRC"] = r"C:\\путь\\FS22_AlphaClassic.zip"')
        return

    out("=" * 72)
    out("АРХИВ:", zpath)
    out("размер: %.1f МБ" % (os.path.getsize(zpath) / 1048576.0))
    out("=" * 72)

    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()

        out("")
        out("СОДЕРЖИМОЕ (%d файлов):" % len(names))
        for n in sorted(names):
            try:
                size = z.getinfo(n).file_size
            except Exception:
                size = 0
            out("   %9d  %s" % (size, n))

        # --- бинарник геометрии: главный вопрос совместимости
        shapes = [n for n in names if n.lower().endswith(".i3d.shapes")]
        out("")
        out("=" * 72)
        out("ГЕОМЕТРИЯ (.i3d.shapes) — от неё зависит, заведётся ли в FS19")
        out("=" * 72)
        if not shapes:
            out("   отдельного .i3d.shapes нет — геометрия внутри самого i3d.")
        for s in shapes:
            head = z.read(s)[:16]
            out("   %s" % s)
            out("      первые байты: %s" % " ".join("%02X" % b for b in head))
            try:
                out("      как текст:    %r" % head.decode("latin-1"))
            except Exception:
                pass

        # --- i3d
        i3ds = [n for n in names if n.lower().endswith(".i3d")]
        for n in i3ds:
            dump_tree(z.read(n), n)

        # --- vehicle xml
        xmls = [n for n in names
                if n.lower().endswith(".xml") and "moddesc" not in n.lower()]
        for n in xmls:
            try:
                t = z.read(n).decode("utf-8", "replace")
            except Exception:
                continue
            if "<vehicle" in t:
                dump_vehicle_xml(t, n)

        # --- modDesc: версия дескриптора и заявленные специализации
        for n in names:
            if n.lower().endswith("moddesc.xml"):
                t = z.read(n).decode("utf-8", "replace")
                out("")
                out("=" * 72)
                out("MODDESC:", n)
                out("=" * 72)
                m = re.search(r'descVersion="(\d+)"', t)
                out("   descVersion =", m.group(1) if m else "?")
                for line in t.splitlines():
                    ls = line.strip()
                    if ls.startswith("<type ") or ls.startswith("<specialization"):
                        out("   " + ls[:200])


# ------------------------------------------------------------------ доставка

def _desktop_dirs():
    dirs = []
    for b in _bases():
        for name in ("Desktop", "Рабочий стол", ""):
            p = os.path.join(b, name)
            if os.path.isdir(p) and p not in dirs:
                dirs.append(p)
    return dirs


def deliver(filename="alpha_donor.txt", textblock="ALPHA_DONOR"):
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
        print("*  СПОСОБ 1: вкладка Scripting → выпадающий список текстов →")
        print("*  '%s' → Ctrl+A, Ctrl+C." % textblock)
    if saved:
        print("*  СПОСОБ 2: файл — %s" % saved)
        print("*  %s" % ("он открылся сам." if opened else "откройте двойным щелчком."))
    print("*  СПОСОБ 3: текст уже в буфере обмена, просто Ctrl+V.")
    print("*" * 72)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        out("!! СБОЙ: %s" % exc)
        out(traceback.format_exc())
    deliver()
