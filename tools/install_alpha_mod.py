#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_alpha_mod.py
====================

Собирает мод FS19_AlphaMoped целиком на компьютере пользователя и кладёт
готовый zip в папку модов Farming Simulator 19.

Запускается из консоли Blender (в Blender есть Python), либо любым Python 3.8+.

Что делает:
  1. находит экспортированный .i3d (самый свежий в Документах/на Рабочем столе);
  2. скачивает файлы мода из публичного репозитория GitHub;
  3. подставляет модель под именем alphaMoped.i3d;
  4. РАЗБИРАЕТ .i3d и переписывает <i3dMappings> в alphaMoped.xml
     под реальный порядок узлов — то, ради чего обычно лезут в GIANTS Editor;
  5. пакует FS19_AlphaMoped.zip;
  6. копирует его в папку модов игры.

Использование:
    python install_alpha_mod.py                  # найти i3d автоматически
    python install_alpha_mod.py C:\\path\\my.i3d   # указать i3d явно
"""

import os
import sys
import glob
import json
import shutil
import zipfile
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

REPO   = "vlad5-vlad5/453"
BRANCH = "arena/01a02958-453"
MOD    = "FS19_AlphaMoped"

# узлы сцены i3d, которые считаются за индекс
SCENE_NODES = {"TransformGroup", "Shape", "Camera", "Light", "Audio",
               "NurbsCurve", "Skinned", "Mesh"}


def log(msg):
    print("[alpha] %s" % msg)


# ---------------------------------------------------------------- поиск i3d

def _home_candidates():
    """Внутри Blender expanduser('~') может указывать не туда — собираем варианты."""
    homes = []
    for env in ("USERPROFILE", "HOME"):
        v = os.environ.get(env)
        if v:
            homes.append(v)
    hd, hp = os.environ.get("HOMEDRIVE"), os.environ.get("HOMEPATH")
    if hd and hp:
        homes.append(hd + hp)
    homes.append(os.path.expanduser("~"))

    out = []
    for h in homes:
        h = os.path.normpath(h)
        if os.path.isdir(h) and h not in out:
            out.append(h)
    return out


def _search_roots():
    roots = []

    def add(p):
        p = os.path.normpath(p)
        if os.path.isdir(p) and p not in roots:
            roots.append(p)

    # папка текущего .blend — самый надёжный ориентир
    try:
        import bpy
        if bpy.data.filepath:
            add(os.path.dirname(bpy.data.filepath))
    except Exception:
        pass

    doc_names = ["Documents", "Документы", "Desktop", "Рабочий стол", "Downloads",
                 "Загрузки"]

    for home in _home_candidates():
        add(home)
        for d in doc_names:
            add(os.path.join(home, d))
        # OneDrive может называться "OneDrive", "OneDrive - Personal" и т.п.
        try:
            for entry in os.listdir(home):
                if entry.lower().startswith("onedrive"):
                    od = os.path.join(home, entry)
                    add(od)
                    for d in doc_names:
                        add(os.path.join(od, d))
        except Exception:
            pass

    return roots


def find_i3d(explicit=None):
    # приоритет: аргумент -> переменная окружения -> автопоиск
    if not explicit:
        explicit = os.environ.get("ALPHA_I3D")

    if explicit:
        explicit = explicit.strip().strip('"')
        if not os.path.isfile(explicit):
            raise SystemExit("Файл не найден: %s" % explicit)
        log("использую указанный файл: %s" % explicit)
        return explicit

    # самый надёжный вариант: .i3d рядом с открытым .blend и с тем же именем
    try:
        import bpy
        if bpy.data.filepath:
            base = os.path.splitext(bpy.data.filepath)[0]
            for ext in (".i3d", ".i3d.txt"):
                guess = base + ext
                if os.path.isfile(guess):
                    log("нашёл модель рядом с .blend: %s" % guess)
                    return guess
    except Exception:
        pass

    roots = _search_roots()
    found = []
    for r in roots:
        for pattern in ("*.i3d", "*.i3d.txt",
                        os.path.join("*", "*.i3d"), os.path.join("*", "*.i3d.txt"),
                        os.path.join("*", "*", "*.i3d")):
            found += glob.glob(os.path.join(r, pattern))

    found = [f for f in set(found) if os.path.isfile(f)]

    if not found:
        msg = ["Не нашёл ни одного .i3d. Искал в:"]
        msg += ["   " + r for r in roots]
        msg.append("")
        msg.append("Укажите файл явно — выполните ДВЕ строки:")
        msg.append('   import os; os.environ["ALPHA_I3D"] = r"C:\\путь\\к\\файлу.i3d"')
        msg.append("   (затем снова строку с exec)")
        raise SystemExit("\n".join(msg))

    found.sort(key=os.path.getmtime, reverse=True)
    log("нашёл модель: %s" % found[0])
    if len(found) > 1:
        log("(всего найдено %d, взял самый свежий)" % len(found))
    return found[0]


# ------------------------------------------------------- скачивание из репо

def gh_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "alpha-installer"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def download_mod(dest):
    """Рекурсивно тянет папку мода из GitHub."""
    def walk(path):
        api = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (
            REPO, path, urllib.parse.quote(BRANCH, safe=""))
        for item in gh_json(api):
            rel = item["path"][len(MOD) + 1:]
            if item["type"] == "dir":
                os.makedirs(os.path.join(dest, rel), exist_ok=True)
                walk(item["path"])
            else:
                target = os.path.join(dest, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                req = urllib.request.Request(
                    item["download_url"], headers={"User-Agent": "alpha-installer"})
                with urllib.request.urlopen(req, timeout=60) as r, \
                        open(target, "wb") as f:
                    shutil.copyfileobj(r, f)
                log("  скачан %s" % rel)

    log("скачиваю файлы мода из GitHub...")
    walk(MOD)


# -------------------------------------------------- разбор i3d и маппинги

def build_node_index(i3d_path):
    """{имя узла: индексный путь вида '0>0|13|2'}"""
    tree = ET.parse(i3d_path)
    root = tree.getroot()

    scene = root.find("Scene")
    if scene is None:
        raise SystemExit("В i3d нет секции <Scene> — файл повреждён?")

    mapping = {}
    duplicates = set()

    def visit(elem, path):
        idx = 0
        for child in elem:
            if child.tag not in SCENE_NODES:
                continue
            name = child.get("name")
            if path is None:
                cur = "%d>" % idx
            elif path.endswith(">"):
                cur = "%s%d" % (path, idx)
            else:
                cur = "%s|%d" % (path, idx)

            if name:
                if name in mapping:
                    duplicates.add(name)
                else:
                    mapping[name] = cur
            visit(child, cur)
            idx += 1

    visit(scene, None)

    if duplicates:
        log("ВНИМАНИЕ: повторяющиеся имена узлов: %s" % ", ".join(sorted(duplicates)))

    return mapping


def fix_mappings(xml_path, node_index):
    """Переписывает блок <i3dMappings> под реальную структуру i3d."""
    with open(xml_path, "r", encoding="utf-8") as f:
        text = f.read()

    start = text.find("<i3dMappings>")
    end   = text.find("</i3dMappings>")
    if start == -1 or end == -1:
        raise SystemExit("В alphaMoped.xml не найден блок <i3dMappings>")

    block = text[start:end]

    ids = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("<i3dMapping ") and 'id="' in line:
            a = line.find('id="') + 4
            b = line.find('"', a)
            ids.append(line[a:b])

    missing = []
    width = (max(len(i) for i in ids) if ids else 20) + 2

    rows = []
    for node_id in ids:
        if node_id in node_index:
            quoted = '"%s"' % node_id
            rows.append('        <i3dMapping id=%-*s node="%s"/>'
                        % (width, quoted, node_index[node_id]))
        else:
            missing.append(node_id)
            rows.append('        <!-- НЕ НАЙДЕН В МОДЕЛИ: %s -->' % node_id)

    new_block = "<i3dMappings>\n" + "\n".join(rows) + "\n    "
    text = text[:start] + new_block + text[end:]

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(text)

    return missing


# ------------------------------------------------------------- папка модов

def find_mods_dir():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Documents", "My Games", "FarmingSimulator2019", "mods"),
        os.path.join(home, "OneDrive", "Documents", "My Games", "FarmingSimulator2019", "mods"),
        os.path.join(home, "OneDrive", "Документы", "My Games", "FarmingSimulator2019", "mods"),
        os.path.join(home, "Документы", "My Games", "FarmingSimulator2019", "mods"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


# ------------------------------------------------------------------- main

def main():
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    i3d = find_i3d(explicit)

    work = tempfile.mkdtemp(prefix="alphamod_")
    modx = os.path.join(work, MOD)
    os.makedirs(modx, exist_ok=True)

    download_mod(modx)

    # модель
    shutil.copy2(i3d, os.path.join(modx, "alphaMoped.i3d"))
    log("модель добавлена как alphaMoped.i3d")

    shapes = i3d + ".shapes"
    if os.path.isfile(shapes):
        shutil.copy2(shapes, os.path.join(modx, "alphaMoped.i3d.shapes"))
        log("добавлен alphaMoped.i3d.shapes")

    # маппинги
    log("разбираю структуру модели...")
    index = build_node_index(os.path.join(modx, "alphaMoped.i3d"))
    log("узлов в модели: %d" % len(index))

    # проверка физики: без rigidBodyType техника не ставится в магазине
    with open(os.path.join(modx, "alphaMoped.i3d"), "r",
              encoding="utf-8", errors="replace") as f:
        i3d_text = f.read()
    if "rigidBodyType" not in i3d_text:
        log("!" * 60)
        log("В МОДЕЛИ НЕТ ФИЗИЧЕСКОГО ТЕЛА (rigidBodyType отсутствует).")
        log("В игре будет: 'сначала уберите купленную технику'.")
        log("Перестройте модель свежим blender_build_alpha.py и переэкспортируйте.")
        log("!" * 60)
    else:
        log("физическое тело в модели найдено — ок")

    missing = fix_mappings(os.path.join(modx, "alphaMoped.xml"), index)
    if missing:
        log("НЕ НАЙДЕНЫ в модели (%d): %s" % (len(missing), ", ".join(missing)))
        log("Мод соберётся, но эти детали в игре работать не будут.")
    else:
        log("все узлы совпали — маппинги обновлены")

    # zip
    out_zip = os.path.join(os.path.expanduser("~"), "Desktop", "%s.zip" % MOD)
    if not os.path.isdir(os.path.dirname(out_zip)):
        out_zip = os.path.join(work, "%s.zip" % MOD)

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root_dir, _, files in os.walk(modx):
            for fn in files:
                full = os.path.join(root_dir, fn)
                z.write(full, os.path.relpath(full, modx))

    log("собран архив: %s (%.1f МБ)" % (out_zip, os.path.getsize(out_zip) / 1048576.0))

    # установка
    mods = find_mods_dir()
    if mods:
        shutil.copy2(out_zip, os.path.join(mods, "%s.zip" % MOD))
        log("УСТАНОВЛЕНО в: %s" % mods)
        log("Запускайте игру, мопед будет в магазине в разделе Автомобили.")
    else:
        log("Папку модов не нашёл. Скопируйте архив вручную в:")
        log(r"  Документы\My Games\FarmingSimulator2019\mods\ ")

    return out_zip


if __name__ == "__main__":
    main()
