#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alpha_from_donor.py — собирает FS19_AlphaMoped вокруг ГОТОВОЙ модели Альфы.

Берёт мод FS22_AlphaClassic.zip (модель сделана автором МихаТМ) и превращает
его в мод для Farming Simulator 19:

  1. переписывает геометрию .i3d.shapes из формата версии 7 (FS22)
     в версию 5, которую понимает движок FS19;
  2. вклеивает колёса из отдельного wheels.i3d прямо в основную модель,
     чтобы не зависеть от формата описания колёс FS22;
  3. чинит ссылки на файлы игры, которых в FS19 нет;
  4. пишет alphaMoped.xml в синтаксисе FS19 — с нашими отлаженными
     настройками физики, но на узлы донорской модели;
  5. пакует zip и кладёт его в папку модов игры.

Ничего не «переизобретает»: пути узлов берутся из i3dMappings самого донора.

Запуск в консоли Blender или любым Python 3.8+:

    import urllib.request
    exec(urllib.request.urlopen(".../tools/alpha_from_donor.py").read().decode("utf-8"))

Переменные окружения (все необязательные):
    ALPHA_SRC   — путь к FS22_AlphaClassic.zip
    ALPHA_OUT   — куда положить готовый zip (по умолчанию папка модов)
    ALPHA_STOP  — "shapes": остановиться после конвертации геометрии
"""

import os
import re
import shutil
import struct
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

REPO = "vlad5-vlad5/453"
SHA = "04ccc51046355b164c48be53d90d19107c0083c6"
CODEC_URL = ("https://raw.githubusercontent.com/%s/%s/tools/i3d_shapes.py"
             % (REPO, SHA))

MOD = "FS19_AlphaMoped"

_LINES = []


def out(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    _LINES.append(text)


# ----------------------------------------------------------------- кодек

def load_codec():
    """Модуль i3d_shapes: рядом на диске или из GitHub."""
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
    if here and os.path.isfile(os.path.join(here, "i3d_shapes.py")):
        sys.path.insert(0, here)
        import i3d_shapes
        out("кодек: локальный файл", os.path.join(here, "i3d_shapes.py"))
        return i3d_shapes

    out("кодек: качаю", CODEC_URL)
    src = urllib.request.urlopen(CODEC_URL, timeout=60).read().decode("utf-8")
    ns = {"__name__": "i3d_shapes"}
    exec(compile(src, "i3d_shapes.py", "exec"), ns)
    mod = type(sys)("i3d_shapes")
    mod.__dict__.update(ns)
    sys.modules["i3d_shapes"] = mod
    return mod


# ----------------------------------------------------------------- пути

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


def game_dir():
    for drive in ("C:", "D:", "E:", "F:"):
        for tail in (r"\Program Files (x86)\Steam\steamapps\common\Farming Simulator 19",
                     r"\Steam\steamapps\common\Farming Simulator 19",
                     r"\SteamLibrary\steamapps\common\Farming Simulator 19",
                     r"\Games\Farming Simulator 19",
                     r"\Program Files (x86)\Farming Simulator 2019",
                     r"\Program Files\Farming Simulator 2019"):
            if os.path.isdir(os.path.join(drive + tail, "data")):
                return drive + tail
    return None


def find_donor():
    p = os.environ.get("ALPHA_SRC", "").strip().strip('"')
    if p and os.path.isfile(p):
        return p

    hits = []
    for b in _bases():
        for d in ("Downloads", "Загрузки", "Desktop", "Рабочий стол",
                  "Documents", "Документы", ""):
            for extra in ("", os.path.join("My Games", "FarmingSimulator2019", "mods")):
                folder = os.path.join(b, d, extra)
                if not os.path.isdir(folder):
                    continue
                try:
                    names = os.listdir(folder)
                except Exception:
                    continue
                for n in names:
                    if "alphaclassic" in n.lower() and n.lower().endswith(".zip"):
                        full = os.path.join(folder, n)
                        if full not in hits:
                            hits.append(full)

    if not hits:
        return None
    # исходник — тот, что от FS22; остальные могли быть собраны нами же
    hits.sort(key=lambda f: (0 if "fs22" in os.path.basename(f).lower() else 1,
                             os.path.basename(f).lower()))
    if len(hits) > 1:
        out("подходящих архивов несколько, беру первый:")
        for h in hits:
            out("   " + h)
    return hits[0]


# ----------------------------------------------------------------- геометрия

def locate_donor_files(work):
    """Находит внутри распакованного донора модель, геометрию, колёса и конфиг."""
    main_i3d = wheels_i3d = vehicle_xml = None
    best = -1

    for root_dir, _, files in os.walk(work):
        for name in files:
            full = os.path.join(root_dir, name)
            low = name.lower()
            rel_depth = os.path.relpath(full, work).count(os.sep)

            if low.endswith(".i3d"):
                if rel_depth == 0:
                    size = os.path.getsize(full)
                    if size > best:
                        best, main_i3d = size, full
                elif "wheel" in low or "wheel" in root_dir.lower():
                    wheels_i3d = full
            elif low.endswith(".xml") and "moddesc" not in low:
                try:
                    head = open(full, encoding="utf-8", errors="replace").read(4000)
                except Exception:
                    continue
                if "<vehicle" in head:
                    vehicle_xml = full

    return main_i3d, wheels_i3d, vehicle_xml


def convert_shapes(codec, work, main_i3d, wheels_i3d):
    """Версия 7 -> версия 5, колёса вклеиваются в основную модель.

    Возвращает: (сдвиг id для колёсных мешей, карта имя->id колёсных мешей)."""

    main_path = main_i3d + ".shapes"
    wheel_path = (wheels_i3d + ".shapes") if wheels_i3d else None

    out("")
    out("=" * 72)
    out("ГЕОМЕТРИЯ")
    out("=" * 72)

    if not os.path.isfile(main_path):
        out("!! рядом с моделью нет файла геометрии %s" % main_path)
        out("   значит, геометрия лежит прямо внутри .i3d — конвертировать нечего")
        return {}

    main = codec.ShapesFile.load(open(main_path, "rb").read())
    out("основная модель: версия %d, сущностей %d" % (main.version, len(main.parts)))
    bad = [p for p in main.parts if not p.parsed and p.etype == 1]
    if bad:
        out("!! не разобралось мешей: %d" % len(bad))
        for p in bad[:5]:
            out("   %s: %s" % (p.name, getattr(p, "error", "")))
    out(main.summary()[:4000])

    wheels = None
    if wheel_path and os.path.isfile(wheel_path):
        wheels = codec.ShapesFile.load(open(wheel_path, "rb").read())
        out("")
        out("колёса: версия %d, сущностей %d"
            % (wheels.version, len(wheels.parts)))
        out(wheels.summary())
    else:
        out("")
        out("отдельного файла колёс нет — значит, колёса уже внутри модели")

    if main.version == 5 and wheels is None:
        out("")
        out("геометрия уже версии 5 и колёса на месте: перекодировать нечего")
        return {}

    # переносим колёсные меши в основной файл с новыми номерами
    used = set(p.id for p in main.parts)
    shift = max(used) if used else 0
    wheel_ids = {}
    for p in (wheels.parts if wheels is not None else []):
        new_id = shift + p.id
        while new_id in used:
            new_id += 1
        used.add(new_id)
        p.id = new_id
        wheel_ids[p.name] = new_id
        main.parts.append(p)

    data = main.save(version=5)
    open(main_path, "wb").write(data)
    out("")
    out("записано %s: версия 5, сущностей %d, %.1f МБ"
        % (os.path.basename(main_path), len(main.parts), len(data) / 1048576.0))

    # проверяем, что записанное читается обратно
    check = codec.ShapesFile.load(open(main_path, "rb").read(), strict=True)
    assert check.version == 5 and len(check.parts) == len(main.parts)
    out("перечитано без ошибок — формат корректный")

    if wheel_path:
        try:
            os.remove(wheel_path)
        except Exception:
            pass

    return wheel_ids


# ----------------------------------------------------------------- i3d

def indexed_children(elem):
    NODES = ("TransformGroup", "Shape", "Camera", "Light", "Audio",
             "NurbsCurve", "Skinned", "Mesh")
    return [c for c in elem if c.tag in NODES]


def build_paths(scene):
    """имя узла -> путь вида 0>1|2 (первое вхождение) и путь -> элемент."""
    by_name, by_path, parent = {}, {}, {}

    def walk(elem, prefix):
        for i, child in enumerate(indexed_children(elem)):
            if prefix is None:
                cur = "%d>" % i
            elif prefix.endswith(">"):
                cur = "%s%d" % (prefix, i)
            else:
                cur = "%s|%d" % (prefix, i)
            name = child.get("name")
            if name and name not in by_name:
                by_name[name] = cur
            by_path[cur] = child
            parent[child] = elem
            walk(child, cur)

    walk(scene, None)
    return by_name, by_path


def fix_file_references(root, game, missing_report):
    """Ссылки на файлы FS22, которых в FS19 нет.

    Шейдер, которого нет, подменять нельзя — у чужого шейдера другие
    параметры. Поэтому недостающий шейдер просто отцепляем: материал
    рисуется стандартным. Недостающую текстуру тоже убираем — деталь
    станет одноцветной, но это лучше розового пятна и лучше ошибки.
    """
    files = root.find("Files")
    if files is None or not game:
        return 0

    def exists(fn):
        if not fn.startswith("$data/"):
            return True
        return os.path.isfile(os.path.join(game, fn.replace("$data/", "data/")
                                           .replace("/", os.sep)))

    missing_shaders, missing_textures, drop = set(), set(), []
    for f in files:
        fn = f.get("filename", "")
        if exists(fn):
            continue
        fid = f.get("fileId")
        if "/shaders/" in fn.lower() or fn.lower().endswith("shader.xml"):
            missing_shaders.add(fid)
        else:
            missing_textures.add(fid)
        drop.append(f)
        missing_report.append(fn)

    if not drop:
        return 0

    materials = root.find("Materials")
    for mat in (materials if materials is not None else []):
        if mat.get("customShaderId") in missing_shaders:
            mat.attrib.pop("customShaderId", None)
            for sub in list(mat):
                if sub.tag.startswith("Custom"):
                    mat.remove(sub)
        for sub in list(mat):
            if sub.get("fileId") in missing_textures:
                mat.remove(sub)
            elif sub.get("fileId") in missing_shaders:
                mat.remove(sub)

    for f in drop:
        files.remove(f)

    return len(drop)


def merge_wheels(main_root, wheel_root, wheel_shape_ids):
    """Копирует материалы/файлы колёс в основной i3d и возвращает
    заготовки узлов колёсных мешей (обод + покрышка)."""

    # --- файлы
    mfiles = main_root.find("Files")
    if mfiles is None:
        mfiles = ET.SubElement(main_root, "Files")
    used_file_ids = set(int(f.get("fileId")) for f in mfiles if f.get("fileId"))
    next_file = (max(used_file_ids) + 1) if used_file_ids else 1

    by_name = {}
    for f in mfiles:
        by_name[f.get("filename")] = f.get("fileId")

    file_map = {}
    wfiles = wheel_root.find("Files")
    for f in (wfiles if wfiles is not None else []):
        fn = f.get("filename", "")
        # пути в wheels.i3d относительные: ../textures/... -> textures/...
        fn = fn.replace("../", "")
        old = f.get("fileId")
        if fn in by_name:
            file_map[old] = by_name[fn]
            continue
        new = str(next_file)
        next_file += 1
        el = ET.SubElement(mfiles, "File")
        el.set("fileId", new)
        el.set("filename", fn)
        by_name[fn] = new
        file_map[old] = new

    # --- материалы
    mmat = main_root.find("Materials")
    if mmat is None:
        mmat = ET.SubElement(main_root, "Materials")
    used_mat = set(int(m.get("materialId")) for m in mmat if m.get("materialId"))
    next_mat = (max(used_mat) + 1) if used_mat else 1

    mat_map = {}
    wmat = wheel_root.find("Materials")
    for m in (wmat if wmat is not None else []):
        old = m.get("materialId")
        new = str(next_mat)
        next_mat += 1
        copy = ET.fromstring(ET.tostring(m))
        copy.set("materialId", new)
        for sub in copy.iter():
            fid = sub.get("fileId")
            if fid and fid in file_map:
                sub.set("fileId", file_map[fid])
        mmat.append(copy)
        mat_map[old] = new

    # --- узлы колёс из сцены wheels.i3d
    wscene = wheel_root.find("Scene")
    nodes = {}

    def walk(elem):
        for child in indexed_children(elem):
            if child.get("name"):
                nodes[child.get("name")] = child
            walk(child)

    walk(wscene)
    return nodes, mat_map


def make_wheel_node(src, name, wheel_shape_ids, mat_map):
    """Копия Shape-узла колеса с новыми номерами меша и материала."""
    el = ET.fromstring(ET.tostring(src))
    el.set("name", name)
    el.attrib.pop("translation", None)
    el.attrib.pop("rotation", None)
    sid = el.get("shapeId")
    if sid is not None:
        by_id = wheel_shape_ids.get(src.get("name"))
        if by_id is not None:
            el.set("shapeId", str(by_id))
    mid = el.get("materialIds")
    if mid:
        el.set("materialIds", " ".join(mat_map.get(x, x) for x in mid.split()))
    return el


# ----------------------------------------------------------------- сборка мода

def dds_kind(path):
    """Грубо определяет формат DDS: FS19 не умеет BC7 из FS22."""
    try:
        with open(path, "rb") as f:
            head = f.read(128)
    except Exception:
        return "?"
    if head[:4] != b"DDS ":
        return "не DDS"
    fourcc = head[84:88]
    if fourcc == b"DX10":
        try:
            with open(path, "rb") as f:
                f.seek(128)
                dxgi = struct.unpack("<I", f.read(4))[0]
            names = {77: "BC3/DXT5", 80: "BC4", 83: "BC5",
                     98: "BC7 (FS19 НЕ ПОДДЕРЖИВАЕТ)", 99: "BC7 sRGB (FS19 НЕ ПОДДЕРЖИВАЕТ)"}
            return names.get(dxgi, "DX10 формат %d" % dxgi)
        except Exception:
            return "DX10"
    try:
        return fourcc.decode("ascii")
    except Exception:
        return "нестандартный"


def fetch(path_in_repo):
    url = "https://raw.githubusercontent.com/%s/%s/%s" % (REPO, SHA, path_in_repo)
    return urllib.request.urlopen(url, timeout=60).read()


MODDESC = """<?xml version="1.0" encoding="utf-8" standalone="no" ?>
<modDesc descVersion="53">
    <author>MihaTM (model) / conversion for FS19</author>
    <version>2.0.0.0</version>

    <title>
        <ru>Мопед Альфа 110</ru>
        <en>Alpha 110 Moped</en>
    </title>

    <description>
        <ru><![CDATA[Классический мопед «Альфа» 110 кубов.

Модель из мода Alpha Classic 110 (автор МихаТМ), перенесена в FS19.

Скорость: 75 км/ч
Мощность: 7 л.с.
Бак: 4 л]]></ru>
        <en><![CDATA[Classic Alpha 110cc moped.]]></en>
    </description>

    <iconFilename>icon_alphaMoped.dds</iconFilename>
    <multiplayer supported="true"/>
    <l10n filenamePrefix="translations/translation"/>

    <!--
        Специализации перечислены явно: в FS19 у <type> нет атрибута parent=,
        наследование типов появилось только в FS22.
    -->
    <vehicleTypes>
        <type name="alphaMoped" className="Vehicle" filename="$dataS/scripts/vehicles/Vehicle.lua">
            <specialization name="baseMaterial"/>
            <specialization name="tipOccluder"/>
            <specialization name="foliageBending"/>
            <specialization name="washable"/>
            <specialization name="wearable"/>
            <specialization name="dynamicallyLoadedParts"/>
            <specialization name="animatedVehicle"/>
            <specialization name="dashboard"/>
            <specialization name="cylindered"/>
            <specialization name="mountable"/>
            <specialization name="ikChains"/>
            <specialization name="wheels"/>
            <specialization name="speedRotatingParts"/>
            <specialization name="enterable"/>
            <specialization name="fillUnit"/>
            <specialization name="motorized"/>
            <specialization name="drivable"/>
            <specialization name="lights"/>
            <specialization name="honk"/>
        </type>
    </vehicleTypes>

    <storeItems>
        <storeItem xmlFilename="alphaMoped.xml"/>
    </storeItems>
</modDesc>
"""


VEHICLE = """<?xml version="1.0" encoding="utf-8" standalone="no" ?>
<!--
    Мопед Альфа 110 для Farming Simulator 19.

    Модель взята из мода Alpha Classic 110 для FS22 (автор МихаТМ);
    геометрия переписана из формата версии 7 в версию 5,
    колёса вклеены в основную модель, конфиг переписан под FS19.

    Пути узлов подставлены напрямую (0>1|0 и т.п.) — так надёжнее имён,
    потому что в модели есть одноимённые узлы (wheel, visual, lights).
-->
<vehicle type="alphaMoped">

    <annotation>Alpha Classic 110</annotation>

    <storeData>
        <name>
            <ru>Альфа 110</ru>
            <en>Alpha 110</en>
        </name>
        <specs>
            <power>7</power>
            <maxSpeed>75</maxSpeed>
        </specs>
        <functions>
            <function>$l10n_function_alphaMoped</function>
        </functions>
        <image>store_alphaMoped.dds</image>
        <price>1900</price>
        <lifetime>300</lifetime>
        <rotation>0</rotation>
        <brand>LIZARD</brand>
        <category>cars</category>
        <shopTranslationOffset>0 0 0</shopTranslationOffset>
        <shopRotationOffset>0 0 0</shopRotationOffset>
        <vertexBufferMemoryUsage>0</vertexBufferMemoryUsage>
        <indexBufferMemoryUsage>0</indexBufferMemoryUsage>
        <textureMemoryUsage>0</textureMemoryUsage>
        <instanceVertexBufferMemoryUsage>0</instanceVertexBufferMemoryUsage>
        <instanceIndexBufferMemoryUsage>0</instanceIndexBufferMemoryUsage>
    </storeData>

    <base>
        <typeDesc>$l10n_typeDesc_alphaMoped</typeDesc>
        <filename>alphaMoped.i3d</filename>
        <size width="0.7" length="1.9" lengthOffset="0"/>
        <components>
            <component centerOfMass="0 0.10 -0.05"
                       solverIterationCount="20" mass="115"/>
        </components>
        <schemaOverlay name="DEFAULT"/>
    </base>

    <wheels>
        <wheelConfigurations>
            <wheelConfiguration name="$l10n_configuration_valueDefault" price="0">
                <wheels autoRotateBackSpeed="2.3">

                    <!-- 1: переднее видимое, рулевое. Меш висит на {WHEEL0} -->
                    <wheel isLeft="true" hasTireTracks="true" hasParticles="true" tireTrackAtlasIndex="0">
                        <physics rotSpeed="1" restLoad="0.5"
                                 repr="{VILKA}" driveNode="{WHEEL0}"
                                 useReprDirection="true"
                                 radius="0.29" width="0.09" mass="0.2"
                                 forcePointRatio="0.5" initialCompression="20"
                                 suspTravel="0.15" spring="0.5" damper="0.7"
                                 frictionScale="5" transRatio="1"/>
                    </wheel>

                    <!-- 2: заднее видимое, ведущее -->
                    <wheel isLeft="false" hasTireTracks="true" hasParticles="true" tireTrackAtlasIndex="0">
                        <physics rotSpeed="1" restLoad="0.5"
                                 repr="{WHEEL1}"
                                 radius="0.29" width="0.09" mass="0.2"
                                 forcePointRatio="1" initialCompression="20"
                                 suspTravel="0.15" spring="0.5" damper="0.7"
                                 frictionScale="5" transRatio="1"/>
                    </wheel>

                    <!-- 3-5: невидимые колёса-стабилизаторы (как у донора) -->
                    <wheel hasTireTracks="false" hasParticles="false">
                        <physics radius="0.29" width="0.14" mass="0.01"
                                 restLoad="0.4" repr="{WPHYS}"
                                 forcePointRatio="0.5" initialCompression="20"
                                 suspTravel="0.15" spring="0.5" damper="0.7"
                                 transRatio="1"/>
                    </wheel>
                    <wheel hasTireTracks="false" hasParticles="false">
                        <physics radius="0.29" width="0.1" mass="0.01"
                                 restLoad="0.4" repr="{WSUP1}"
                                 forcePointRatio="0.5" initialCompression="20"
                                 suspTravel="0.15" spring="0.5" damper="0.7"
                                 transRatio="1"/>
                    </wheel>
                    <wheel hasTireTracks="false" hasParticles="false">
                        <physics radius="0.29" width="0.1" mass="0.01"
                                 restLoad="0.4" repr="{WSUP2}"
                                 forcePointRatio="0.5" initialCompression="20"
                                 suspTravel="0.15" spring="0.5" damper="0.7"
                                 transRatio="1"/>
                    </wheel>
                </wheels>
            </wheelConfiguration>
        </wheelConfigurations>

        <!-- Рулевая геометрия: FS19 читает её только из этой обёртки
             и только на уровне <wheels>. Индексы колёс с единицы. -->
        <ackermannSteeringConfigurations>
            <ackermannSteering rotSpeed="30" rotMax="32"
                               rotCenterWheel1="2" rotCenterWheel2="3"
                               rotCenterWheel3="4" rotCenterWheel4="5"/>
        </ackermannSteeringConfigurations>
    </wheels>

    <motorized>
        <motorConfigurations>
            <motorConfiguration name="Super CUB 110" hp="7" price="0">
                <!-- Кривая момента обязательна: без неё VehicleMotor.lua(128)
                     падает на nil и техника не создаётся. -->
                <motor torqueScale="4.5" minRpm="1300" maxRpm="8500"
                       maxForwardSpeed="75" maxBackwardSpeed="6"
                       accelerationLimit="10" brakeForce="1.4"
                       lowBrakeForceScale="0.08" lowBrakeForceSpeedLimit="0.6"
                       ptoMotorRpmRatio="1">
                    <torque normRpm="0.15" torque="0.45"/>
                    <torque normRpm="0.40" torque="0.80"/>
                    <torque normRpm="0.65" torque="1.00"/>
                    <torque normRpm="0.85" torque="0.95"/>
                    <torque normRpm="1.00" torque="0.70"/>
                </motor>
                <transmission name="4-speed"
                              minForwardGearRatio="8"  maxForwardGearRatio="130"
                              minBackwardGearRatio="60" maxBackwardGearRatio="130"/>
            </motorConfiguration>
        </motorConfigurations>

        <!-- Дифференциалы FS19 читает только из этой обёртки -->
        <differentialConfigurations>
            <differentialConfiguration>
                <differentials>
                    <differential torqueRatio="1" maxSpeedRatio="5.5"
                                  wheelIndex1="2" wheelIndex2="3"/>
                </differentials>
            </differentialConfiguration>
        </differentialConfigurations>

        <consumerConfigurations>
            <consumerConfiguration>
                <consumer fillUnitIndex="1" fillType="DIESEL" capacity="4"
                          usage="0.35" refillLitersPerSecond="1"/>
            </consumerConfiguration>
        </consumerConfigurations>

        <sounds>
            <motorStart template="carMotorStart" linkNode="{MOTOR}" volumeScale="0.7"/>
            <motorStop  template="carMotorStop"  linkNode="{MOTOR}" volumeScale="0.7"/>
            <motor      template="carMotorSmall" linkNode="{MOTOR}"
                        volumeScale="0.8" pitchScale="1.35"/>
        </sounds>
    </motorized>

    <fillUnit>
        <fillUnitConfigurations>
            <fillUnitConfiguration>
                <fillUnits>
                    <fillUnit unit="$l10n_unit_literShort" fillTypes="DIESEL"
                              capacity="4" showOnHud="true"/>
                </fillUnits>
            </fillUnitConfiguration>
        </fillUnitConfigurations>
    </fillUnit>

    <enterable isTabbable="true">
        <enterReferenceNode node="{CHARNODE}" upperHeight="1.6" lowerHeight="0.05"/>
        <exitPoint node="{EXIT}"/>

        <cameras>
            <camera node="{CAMOUT}" rotatable="true" rotateNode="{CAMTARGET}"
                    limit="true" useWorldXZRotation="true"
                    rotMinX="-1.0" rotMaxX="0.4"
                    transMin="2.0" transMax="10.0"
                    translation="0 0 4.0" rotation="-8 180 0"/>
            <camera node="{CAMIN}" rotatable="true" limit="true"
                    isInside="true" rotMinX="-1.1" rotMaxX="0.4"
                    transMin="0" transMax="0"/>
        </cameras>

        <characterNode node="{PLAYER}" cameraMinDistance="0.35"
                       characterIndex="1" useAnimation="false"/>
    </enterable>

    <drivable>
        <cruiseControl minSpeed="3" maxSpeed="75"/>
    </drivable>

    <lights>
        <states>
            <state1 lightTypes="0"/>
            <state2 lightTypes="0 1"/>
        </states>
        <realLights>
            <low>
                <light node="{LIGHTLOW}" type="0"/>
            </low>
            <high>
                <light node="{LIGHTHIGH}" type="1"/>
            </high>
        </realLights>
        <brakeLights>
            <brakeLight node="{BRAKELIGHT}"/>
        </brakeLights>
    </lights>

    <honk>
        <sound template="carHorn" linkNode="{ROOT}" volumeScale="0.6"/>
    </honk>

    <washable>
        <dirtNode node="{FRAME}"/>
        <dirtNode node="{MOTOR}"/>
    </washable>

    <wearable>
        <wearNode node="{FRAME}"/>
    </wearable>

</vehicle>
"""


def build_vehicle_xml(paths):
    """Подставляет реальные пути узлов в шаблон конфига."""
    need = {
        "{ROOT}":       "alphaClassic_component1",
        "{VILKA}":      "vilka1",
        "{WHEEL0}":     "wheel_0",
        "{WHEEL1}":     "wheel_1",
        "{WPHYS}":      "wheelPhysics",
        "{WSUP1}":      "wheelSupport1",
        "{WSUP2}":      "wheelSupport2",
        "{MOTOR}":      "motor",
        "{FRAME}":      "frameAlpha",
        "{CHARNODE}":   "characterNode",
        "{PLAYER}":     "Player",
        "{EXIT}":       "exitPoint",
        "{CAMOUT}":     "outdoorCamera1",
        "{CAMTARGET}":  "outdoorCameraTarget",
        "{CAMIN}":      "indoorCamera1",
        "{LIGHTLOW}":   "frontLightLow",
        "{LIGHTHIGH}":  "frontLightHigh",
        "{BRAKELIGHT}": "brakeLight_vis",
    }

    text = VEHICLE
    missing = []
    for token, node_id in need.items():
        path = paths.get(node_id)
        if path is None:
            missing.append(node_id)
            path = paths.get("alphaClassic_component1", "0>")
        text = text.replace(token, path)

    if missing:
        out("!! не нашёл узлы: %s" % ", ".join(missing))
    return text


def collect_paths(donor_vehicle_xml, scene):
    """id -> путь. Сначала родные i3dMappings донора, затем обход дерева."""
    paths = {}
    try:
        root = ET.fromstring(donor_vehicle_xml)
        for m in root.iter("i3dMapping"):
            if m.get("id") and m.get("node"):
                paths[m.get("id")] = m.get("node")
    except Exception as exc:
        out("!! i3dMappings донора не разобрались:", exc)

    by_name, _ = build_paths(scene)
    for name, path in by_name.items():
        paths.setdefault(name, path)
    return paths


def main():
    codec = load_codec()

    donor = find_donor()
    mods = mods_dir()
    game = game_dir()

    out("=" * 72)
    out("СБОРКА МОДА ИЗ ГОТОВОЙ МОДЕЛИ")
    out("=" * 72)
    out("донор:", donor)
    out("моды :", mods)
    out("игра :", game)

    if not donor:
        out("!! FS22_AlphaClassic.zip не найден. Укажите путь:")
        out('   os.environ["ALPHA_SRC"] = r"C:\\путь\\FS22_AlphaClassic.zip"')
        return

    work = tempfile.mkdtemp(prefix="alpha_")
    with zipfile.ZipFile(donor) as z:
        z.extractall(work)

    main_i3d_path, wheels_i3d_path, donor_xml_path = locate_donor_files(work)
    out("модель :", main_i3d_path)
    out("колёса :", wheels_i3d_path or "(отдельного файла нет)")
    out("конфиг :", donor_xml_path)
    if not main_i3d_path:
        out("!! внутри архива нет .i3d — это не мод с моделью")
        return

    # 1. геометрия
    wheel_shape_ids = convert_shapes(codec, work, main_i3d_path, wheels_i3d_path)

    if os.environ.get("ALPHA_STOP") == "shapes":
        out("")
        out("остановка после геометрии (ALPHA_STOP=shapes)")
        out("рабочая папка:", work)
        return

    # 2. сцена
    out("")
    out("=" * 72)
    out("СЦЕНА")
    out("=" * 72)

    main_tree = ET.parse(main_i3d_path)
    main_root = main_tree.getroot()
    wheel_root = (ET.parse(wheels_i3d_path).getroot()
                  if wheels_i3d_path and os.path.isfile(wheels_i3d_path) else None)

    # 2а. чиним ссылки на файлы, которых в FS19 нет
    report = []
    n = fix_file_references(main_root, game, report)
    out("подменено ссылок на отсутствующие файлы игры: %d" % n)
    for line in report:
        out("   " + line)

    # 2б. переносим материалы колёс и вешаем меши на узлы колёс
    if wheel_root is not None and wheel_shape_ids:
        wnodes, mat_map = merge_wheels(main_root, wheel_root, wheel_shape_ids)
        out("перенесено материалов колёс: %d" % len(mat_map))
    else:
        wnodes, mat_map = {}, {}
        out("колёса переносить не нужно")

    scene = main_root.find("Scene")
    by_name, by_path = build_paths(scene)

    # передний диск + покрышка на wheel_0, задний — на wheel_1
    pairs = ([("wheel_0", "wheelDriveF1", "tireL358"),
              ("wheel_1", "wheelDriveB1", "tireL358")] if wnodes else [])
    for host_name, rim, tyre in pairs:
        host_path = None
        try:
            dv = open(donor_xml_path, encoding="utf-8", errors="replace").read()
            m = re.search(r'<i3dMapping id="%s" node="([^"]+)"' % host_name, dv)
            if m:
                host_path = m.group(1)
        except Exception:
            pass
        host = by_path.get(host_path) if host_path else None
        if host is None:
            host = by_path.get(by_name.get(host_name, ""), None)
        if host is None:
            out("!! узел %s не найден, колесо не привешено" % host_name)
            continue
        for src_name, label in ((rim, host_name + "_rim"),
                                (tyre, host_name + "_tyre")):
            src = wnodes.get(src_name)
            if src is None:
                out("!! в wheels.i3d нет %s" % src_name)
                continue
            host.append(make_wheel_node(src, label, wheel_shape_ids, mat_map))
        out("на %s (%s) повешены %s + %s" % (host_name, host_path, rim, tyre))

    # 2в. геометрия теперь одна и называется по-нашему
    shapes_el = main_root.find("Shapes")
    if shapes_el is not None:
        shapes_el.set("externalShapesFile", "alphaMoped.i3d.shapes")
    files_el = main_root.find("Files")
    if files_el is not None:
        for f in files_el:
            if (f.get("filename") or "").endswith("wheels.i3d"):
                f.set("filename", "alphaMoped.i3d")

    # 3. собираем мод
    out("")
    out("=" * 72)
    out("СБОРКА")
    out("=" * 72)

    stage = os.path.join(work, "_mod")
    os.makedirs(stage, exist_ok=True)

    main_tree.write(os.path.join(stage, "alphaMoped.i3d"),
                    encoding="utf-8", xml_declaration=True)
    src_shapes = main_i3d_path + ".shapes"
    if os.path.isfile(src_shapes):
        shutil.move(src_shapes, os.path.join(stage, "alphaMoped.i3d.shapes"))
    else:
        out("!! файла геометрии нет — модель без .shapes работать не будет")

    tex_src = os.path.join(os.path.dirname(main_i3d_path), "textures")
    if os.path.isdir(tex_src):
        shutil.copytree(tex_src, os.path.join(stage, "textures"))
        out("текстуры:")
        for n in sorted(os.listdir(tex_src)):
            out("   %-34s %s" % (n, dds_kind(os.path.join(tex_src, n))))

    donor_vehicle = (open(donor_xml_path, encoding="utf-8",
                          errors="replace").read() if donor_xml_path else "")
    paths = collect_paths(donor_vehicle, scene)

    with open(os.path.join(stage, "alphaMoped.xml"), "w", encoding="utf-8") as f:
        f.write(build_vehicle_xml(paths))
    with open(os.path.join(stage, "modDesc.xml"), "w", encoding="utf-8") as f:
        f.write(MODDESC)

    # иконка, картинка магазина и переводы — из нашего репозитория
    for rel in ("icon_alphaMoped.dds", "store_alphaMoped.dds",
                "translations/translation_ru.xml", "translations/translation_en.xml"):
        try:
            data = fetch("%s/%s" % (MOD, rel))
        except Exception as exc:
            out("!! не скачался %s: %s" % (rel, exc))
            continue
        dst = os.path.join(stage, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(data)

    # 4. пакуем
    target_dir = os.environ.get("ALPHA_OUT") or mods or os.path.expanduser("~")
    zip_path = os.path.join(target_dir, MOD + ".zip")

    tmp_zip = zip_path + ".new"
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root_dir, _, files in os.walk(stage):
            for name in files:
                full = os.path.join(root_dir, name)
                z.write(full, os.path.relpath(full, stage).replace(os.sep, "/"))

    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        os.rename(tmp_zip, zip_path)
    except Exception as exc:
        out("!! не смог заменить %s: %s" % (zip_path, exc))
        out("   готовый мод лежит здесь: %s" % tmp_zip)
        return

    folder = os.path.join(target_dir, MOD)
    if os.path.isdir(folder):
        out("")
        out("!! ВНИМАНИЕ: в папке модов есть распакованная папка %s —" % MOD)
        out("   игра читает её вместо zip. Уберите папку, иначе увидите старую версию.")

    out("")
    out("ГОТОВО: %s (%.1f МБ)" % (zip_path, os.path.getsize(zip_path) / 1048576.0))
    out("Запускайте игру и покупайте мопед в магазине, раздел «Машины».")


# ----------------------------------------------------------------- доставка

def _desktop_dirs():
    dirs = []
    for b in _bases():
        for name in ("Desktop", "Рабочий стол", ""):
            p = os.path.join(b, name)
            if os.path.isdir(p) and p not in dirs:
                dirs.append(p)
    return dirs


def deliver(filename="alpha_build.txt", textblock="ALPHA_BUILD"):
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
    print("*  он же в буфере обмена и в тексте '%s' внутри Blender" % textblock)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        out("!! СБОЙ: %s" % exc)
        out(traceback.format_exc())
    deliver()
