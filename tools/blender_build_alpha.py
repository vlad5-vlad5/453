#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_build_alpha.py
======================

Процедурно строит low-poly модель мопеда «Альфа 110» в Blender с иерархией
узлов, которая один-в-один соответствует i3dMappings в FS19_AlphaMoped/alphaMoped.xml.

Запуск:

    # из GUI Blender: Scripting -> Open -> Run Script
    # или из консоли:
    blender --background --python tools/blender_build_alpha.py

После выполнения:
    1. File -> Export -> GIANTS I3D  (нужен GIANTS I3D Exporter для Blender)
    2. Сохранить как FS19_AlphaMoped/alphaMoped.i3d
    3. Открыть i3d в GIANTS Editor и СВЕРИТЬ индексы узлов с блоком
       <i3dMappings> в alphaMoped.xml (скрипт печатает ожидаемые пути в конце).

Система координат:
    Blender: Z вверх. Перёд мопеда направлен по оси Y на величину FWD.
    Экспортёр GIANTS переводит это в свою систему сам.
    Если в игре мопед едет задом наперёд — поменяйте FWD на противоположный знак
    и переэкспортируйте.
"""

import math

try:
    import bpy
    from mathutils import Vector  # noqa: F401
except ImportError:  # запуск вне Blender — только для проверки синтаксиса
    bpy = None


# ----------------------------------------------------------------------------
# Параметры мопеда (метры, реальные пропорции Альфа 110)
# ----------------------------------------------------------------------------

FWD = -1.0          # направление "вперёд" по оси Y

WHEELBASE   = 1.22  # колёсная база
WHEEL_R     = 0.335 # радиус колеса (17" + покрышка)
WHEEL_W     = 0.075 # ширина колеса
STAB_OFFSET = 0.22  # смещение НЕВИДИМЫХ физических колёс от осевой линии.
                    # Колея 44 см вместо 11 см: мопед перестаёт опрокидываться.
                    # На вид не влияет — меши колёс всё равно строятся по центру,
                    # они дети repr-узлов и компенсируют это смещение локально.

AXLE_F = FWD * (WHEELBASE / 2.0)
AXLE_R = -FWD * (WHEELBASE / 2.0)

SEAT_H = 0.77       # высота седла


# ----------------------------------------------------------------------------
# Утилиты
# ----------------------------------------------------------------------------

def clear_scene():
    # остановить возможное проигрывание анимации
    if bpy.context.screen is not None and bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_cancel(restore_frame=False)

    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def make_material(name, rgba, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        # в Blender 4.x/5.x материал уже создаётся с нодами;
        # use_nodes объявлен устаревшим и удаляется в 6.0
        if bpy.app.version < (4, 0, 0):
            mat.use_nodes = True
        if mat.node_tree is None:
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:  # на случай другой локализации/версии
            for n in mat.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    bsdf = n
                    break
        if bsdf is not None:
            for socket, value in (("Base Color", rgba),
                                  ("Metallic", metallic),
                                  ("Roughness", roughness)):
                if socket in bsdf.inputs:
                    bsdf.inputs[socket].default_value = value
        # viewport-цвет, чтобы модель была наглядной в Solid-режиме
        mat.diffuse_color = rgba
    return mat


def attach(obj, parent):
    """Родительство с сохранением мировой позиции."""
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def empty(name, parent, loc=(0, 0, 0), rot=(0, 0, 0), size=0.08):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = loc
    obj.rotation_euler = rot
    bpy.context.collection.objects.link(obj)
    return attach(obj, parent)


def box(name, parent, loc, size, rot=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0], size[1], size[2])
    obj.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat is not None:
        obj.data.materials.append(mat)
    return attach(obj, parent)


def cylinder(name, parent, loc, radius, depth, axis="X", rot_extra=(0, 0, 0),
             verts=16, mat=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    base = {"X": (0, math.radians(90), 0),
            "Y": (math.radians(90), 0, 0),
            "Z": (0, 0, 0)}[axis]
    obj.rotation_euler = (base[0] + rot_extra[0],
                          base[1] + rot_extra[1],
                          base[2] + rot_extra[2])
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if mat is not None:
        obj.data.materials.append(mat)
    return attach(obj, parent)


def camera(name, parent, loc, size=0.12):
    """Настоящая камера. FS19 ругается 'Must be a camera type!' на Empty."""
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 24.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = 2000.0
    obj = bpy.data.objects.new(name, cam_data)
    obj.location = loc
    # камера Blender смотрит вдоль -Z, разворачиваем её "вперёд" по мопеду
    obj.rotation_euler = (math.radians(90.0 * FWD), 0.0, 0.0)
    bpy.context.collection.objects.link(obj)
    return attach(obj, parent)


def box_origin_zero(name, parent, center, size, mat=None):
    """Коробка с геометрией в center, но с origin объекта в (0,0,0).

    Нужно для корневого узла техники: FS отсчитывает позицию компонента
    от origin, он обязан лежать в нуле."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    # запекаем и смещение, и масштаб в саму сетку
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if mat is not None:
        obj.data.materials.append(mat)
    return attach(obj, parent)


def set_rigid_body(obj, body_type="dynamic", compound=False, collision=True,
                   solver_iterations=10):
    """Проставляет атрибуты физики экспортёра GIANTS I3D.

    Без этого экспортёр пишет rigid_body_type='none', модель уезжает в игру
    без физического тела, и FS не может ни поставить технику, ни убрать её
    («сначала уберите купленную технику»)."""
    attrs = getattr(obj, "i3d_attributes", None)
    if attrs is None:
        print("[alpha] ВНИМАНИЕ: аддон GIANTS I3D не найден, физика не задана")
        return False
    try:
        attrs.rigid_body_type = body_type
        attrs.collision = collision
        if body_type not in ("static", "compoundChild"):
            attrs.compound = compound
        attrs.solver_iteration_count = solver_iterations
        return True
    except Exception as exc:
        print("[alpha] не удалось задать физику для %s: %s" % (obj.name, exc))
        return False


def wheel_mesh(name, parent, loc, radius, width, mat_tire, mat_rim):
    """Покрышка + диск как один объект."""
    tire = cylinder(name, None, loc, radius, width, axis="X", verts=20, mat=mat_tire)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius * 0.55,
                                        depth=width * 1.05, location=loc)
    rim = bpy.context.active_object
    rim.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    rim.data.materials.append(mat_rim)

    bpy.ops.object.select_all(action="DESELECT")
    rim.select_set(True)
    tire.select_set(True)
    bpy.context.view_layer.objects.active = tire
    bpy.ops.object.join()

    tire.name = name
    return attach(tire, parent)


# ----------------------------------------------------------------------------
# Сборка
# ----------------------------------------------------------------------------

def build():
    clear_scene()

    m_paint  = make_material("alpha_paint",  (0.42, 0.03, 0.05, 1.0), 0.35, 0.25)
    m_black  = make_material("alpha_black",  (0.03, 0.03, 0.03, 1.0), 0.0,  0.7)
    m_chrome = make_material("alpha_chrome", (0.75, 0.76, 0.78, 1.0), 1.0,  0.15)
    m_engine = make_material("alpha_engine", (0.35, 0.36, 0.37, 1.0), 0.8,  0.45)
    m_glass  = make_material("alpha_glass",  (0.95, 0.93, 0.80, 1.0), 0.0,  0.05)
    m_amber  = make_material("alpha_amber",  (0.90, 0.45, 0.05, 1.0), 0.0,  0.3)
    m_red    = make_material("alpha_red",    (0.80, 0.05, 0.05, 1.0), 0.0,  0.3)

    # === корень (component1) ==============================================
    # Корень обязан быть МЕШЕМ: экспортёр разрешает физику только на мешах.
    # Это невидимая коллизионная коробка корпуса — на ней держится вся техника.
    m_col = make_material("alpha_collision", (0.1, 0.6, 0.1, 1.0), 0.0, 1.0)
    root = box_origin_zero("alphaMoped", None,
                           center=(0, 0, 0.50), size=(0.34, 1.30, 0.46),
                           mat=m_col)
    # НЕ используем hide_render: visibility="false" наследуется всеми детьми
    # и мопед пропадает целиком. Правильный способ — non_renderable у самого меша
    # (так же сделано в пресете аддона Physics-VehicleCompound).
    try:
        root.data.i3d_attributes.non_renderable = True
        root.data.i3d_attributes.casts_shadows = False
        root.data.i3d_attributes.receive_shadows = False
    except Exception as exc:
        print("[alpha] не удалось задать non_renderable:", exc)
    set_rigid_body(root, "dynamic", compound=True, collision=True,
                   solver_iterations=10)

    # === 0: bodyLean — всё, что кренится в поворотах =======================
    lean = empty("bodyLean", root, (0, 0, WHEEL_R), size=0.25)

    def L(z):
        """локальная высота относительно bodyLean"""
        return z - WHEEL_R

    #  0 рама
    box("frameMesh", lean, (0, FWD * 0.02, 0.56), (0.11, 0.95, 0.30), mat=m_paint)
    #  1 бак
    box("tankMesh", lean, (0, FWD * 0.26, 0.79), (0.27, 0.50, 0.23),
        rot=(math.radians(-4 * FWD), 0, 0), mat=m_paint)
    #  2 седло
    box("seatMesh", lean, (0, -FWD * 0.20, SEAT_H + 0.03), (0.26, 0.60, 0.09), mat=m_black)
    #  3 двигатель
    box("engineMesh", lean, (0, FWD * 0.02, 0.42), (0.30, 0.34, 0.30), mat=m_engine)
    #  4 глушитель (справа вдоль корпуса)
    cylinder("exhaustMesh", lean, (0.13, -FWD * 0.22, 0.31), 0.045, 0.90,
             axis="Y", mat=m_chrome)
    #  5 задний багажник
    box("rearRackMesh", lean, (0, -FWD * 0.64, SEAT_H + 0.09), (0.28, 0.26, 0.04),
        mat=m_black)
    #  6 заднее крыло
    box("fenderRearMesh", lean, (0, -FWD * 0.60, 0.63), (0.13, 0.46, 0.05), mat=m_paint)
    #  7 звезда цепи (крутится от скорости)
    cylinder("chainSprocket", lean, (-0.07, AXLE_R, 0.0), 0.10, 0.012,
             axis="X", verts=12, mat=m_chrome)
    #  8 точка звука двигателя
    empty("engineNode", lean, (0, FWD * 0.02, 0.42), size=0.05)
    #  9 точка выхлопа
    empty("exhaustEffectNode", lean, (0.15, -FWD * 0.68, 0.33),
          rot=(0, 0, math.radians(180 if FWD > 0 else 0)), size=0.05)
    # 10 стоп-сигнал
    box("brakeLightNode", lean, (0, -FWD * 0.72, 0.83), (0.10, 0.04, 0.06), mat=m_red)
    # 11/12 задние поворотники
    box("turnLightRearLeft",  lean, (-0.14, -FWD * 0.70, 0.83), (0.04, 0.04, 0.05), mat=m_amber)
    box("turnLightRearRight", lean, ( 0.14, -FWD * 0.70, 0.83), (0.04, 0.04, 0.05), mat=m_amber)

    # 13 handlebarNode — узел рулёжки (визуальный поворот руля)
    steer = empty("handlebarNode", lean, (0, FWD * 0.52, 0.78),
                  rot=(math.radians(24 * FWD), 0, 0), size=0.15)

    #  0 вилка
    box("forkMesh", steer, (0, FWD * 0.60, 0.62), (0.16, 0.07, 0.60),
        rot=(math.radians(24 * FWD), 0, 0), mat=m_chrome)
    #  1 руль
    cylinder("handlebarMesh", steer, (0, FWD * 0.50, 1.03), 0.014, 0.62,
             axis="X", verts=10, mat=m_black)
    #  2 переднее крыло
    box("fenderFrontMesh", steer, (0, AXLE_F, 0.62), (0.12, 0.34, 0.05), mat=m_paint)
    #  3 стекло фары
    cylinder("headlightGlass", steer, (0, FWD * 0.62, 0.88), 0.075, 0.05,
             axis="Y", verts=14, mat=m_glass)
    #  4/5 источники света (ближний / дальний)
    empty("headlightLow",  steer, (0, FWD * 0.64, 0.88), size=0.05)
    empty("headlightHigh", steer, (0, FWD * 0.64, 0.88), size=0.05)
    #  6/7 передние поворотники
    box("turnLightFrontLeft",  steer, (-0.16, FWD * 0.58, 0.86), (0.04, 0.04, 0.05), mat=m_amber)
    box("turnLightFrontRight", steer, ( 0.16, FWD * 0.58, 0.86), (0.04, 0.04, 0.05), mat=m_amber)

    # === 1: колёса ==========================================================
    # Схема как у мотоцикла MX: два ВИДИМЫХ колеса строго по центру
    # (на них висят меши) плюс четыре НЕВИДИМЫХ стабилизатора по бокам.
    # Меш на центральном узле не уезжает в сторону при повороте руля.
    wheels = empty("wheels", root, (0, 0, 0), size=0.2)

    # 1-2: передние боковые стабилизаторы (рулевые, невидимые)
    empty("wheelFrontLeft",  wheels, (-STAB_OFFSET, AXLE_F, WHEEL_R), size=0.1)
    empty("wheelFrontRight", wheels, ( STAB_OFFSET, AXLE_F, WHEEL_R), size=0.1)

    # 3: переднее центральное — видимое, рулевое
    wfm = empty("wheelFrontMid", wheels, (0, AXLE_F, WHEEL_R), size=0.1)
    wheel_mesh("wheelFrontMesh", wfm, (0, AXLE_F, WHEEL_R),
               WHEEL_R, WHEEL_W, m_black, m_chrome)

    # 4-5: задние боковые стабилизаторы (невидимые)
    empty("wheelRearLeft",  wheels, (-STAB_OFFSET, AXLE_R, WHEEL_R), size=0.1)
    empty("wheelRearRight", wheels, ( STAB_OFFSET, AXLE_R, WHEEL_R), size=0.1)

    # 6: заднее центральное — видимое, ведущее
    wrm = empty("wheelRearMid", wheels, (0, AXLE_R, WHEEL_R), size=0.1)
    wheel_mesh("wheelRearMesh", wrm, (0, AXLE_R, WHEEL_R),
               WHEEL_R, WHEEL_W + 0.01, m_black, m_chrome)

    # === 2: игрок и камеры ==================================================
    player = empty("player", root, (0, 0, 0), size=0.2)

    empty("enterNode", player, (0.42, -FWD * 0.10, 0.55), size=0.12)
    empty("exitNode",  player, (0.62, -FWD * 0.10, 0.10), size=0.12)
    # посадка водителя: чуть выше седла, лицом вперёд
    empty("playerSeatNode", player, (0, -FWD * 0.16, SEAT_H + 0.08),
          rot=(0, 0, math.radians(0 if FWD < 0 else 180)), size=0.12)
    # камера от третьего лица: сама камера — ребёнок группы вращения,
    # как в рабочих модах (rotateNode="cameraTarget")
    cam_target = empty("cameraTarget", player,
                       (0, -FWD * 0.10, SEAT_H + 0.30), size=0.12)
    camera("cameraOutside", cam_target,
           (0, -FWD * 0.10, SEAT_H + 0.30))
    # камера с седла
    camera("cameraInside", player, (0, -FWD * 0.02, SEAT_H + 0.42))

    return root


EXPECTED_MAPPINGS = """
ВНИМАНИЕ: экспортёр GIANTS сортирует детей узла ПО АЛФАВИТУ, поэтому
реальные индексные пути НЕ совпадают с порядком создания объектов здесь.
Не выписывайте их руками — install_alpha_mod.py читает готовый .i3d и
пересчитывает <i3dMappings> автоматически.

Посмотреть реальное дерево: tools/dump_i3d_tree.py
"""


def main():
    if bpy is None:
        print("Этот скрипт нужно запускать внутри Blender.")
        return
    build()
    print(EXPECTED_MAPPINGS)
    print("Модель собрана.")
    print("Корень alphaMoped: Rigid Body = Dynamic + Compound (иначе техника")
    print("не ставится и не убирается в магазине).")
    print("Камеры cameraOutside/cameraInside созданы как настоящие Camera.")
    print("")
    print("ЭКСПОРТ: File -> Export -> I3D")
    print("  Export Scope  = Everything")
    print("  Keep Collections = ВЫКЛЮЧИТЬ (иначе корнем техники станет Collection")
    print("                     и физика мопеда будет проигнорирована)")


if __name__ == "__main__":
    main()
