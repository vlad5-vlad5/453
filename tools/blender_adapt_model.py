#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_adapt_model.py
======================

Превращает ЛЮБУЮ скачанную модель мотоцикла/мопеда в мод для FS19:
подгоняет масштаб и ориентацию, строит служебные узлы (физика, колёса,
камеры, точки посадки) и раскладывает всё по иерархии, которую ждёт
alphaMoped.xml.

КАК ПОЛЬЗОВАТЬСЯ
----------------
1. Скачайте модель со Sketchfab (форматы .glb / .fbx / .obj / .blend).
2. Blender -> File -> New -> General  (пустая сцена)
3. Blender -> File -> Import -> выберите скачанный файл
4. Запустите этот скрипт (вкладка Scripting -> Run Script)
5. Дальше — обычная установка мода, но в БЕЗОПАСНОМ режиме:
       import os; os.environ["ALPHA_SAFE"] = "1"
       exec(...install_alpha_mod.py...)

   Безопасный режим нужен потому, что у чужой модели нет наших узлов
   для фар, поворотников и выхлопа — эти секции просто отключаются.

ЕСЛИ КОЛЁСА ОПРЕДЕЛИЛИСЬ НЕВЕРНО
--------------------------------
Задайте их имена вручную ДО запуска:

    import os
    os.environ["ALPHA_FRONT_WHEEL"] = "Wheel_F"
    os.environ["ALPHA_REAR_WHEEL"]  = "Wheel_R"

ЕСЛИ МОПЕД СМОТРИТ НЕ ТУДА

    os.environ["ALPHA_FLIP"] = "1"
"""

import os
import math

try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None


WHEELBASE = 1.22      # целевая колёсная база, м
WHEEL_R   = 0.335
FWD       = -1.0      # перёд модели по оси Y
STAB      = 0.22      # разнос невидимых колёс-стабилизаторов


def log(*a):
    print("[adapt]", " ".join(str(x) for x in a))


# ---------------------------------------------------------------- анализ

def mesh_objects():
    return [o for o in bpy.context.scene.objects
            if o.type == "MESH" and len(o.data.vertices) > 0]


def world_bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx, (mn + mx) / 2.0, (mx - mn)


def looks_like_wheel(dim):
    """Колесо: круглое в профиль и узкое поперёк."""
    prof = sorted([dim.y, dim.z])
    if prof[1] < 1e-4:
        return False
    roundness = prof[0] / prof[1]                 # ~1 у круга
    narrow = dim.x < prof[1] * 0.75
    return roundness > 0.72 and narrow


def find_wheels(objs):
    named_f = os.environ.get("ALPHA_FRONT_WHEEL", "").strip()
    named_r = os.environ.get("ALPHA_REAR_WHEEL", "").strip()
    if named_f and named_r:
        f = bpy.data.objects.get(named_f)
        r = bpy.data.objects.get(named_r)
        if f and r:
            log("колёса заданы вручную:", f.name, "/", r.name)
            return f, r
        log("ВНИМАНИЕ: указанные имена колёс не найдены, ищу сам")

    cands = []
    for o in objs:
        _, _, c, d = world_bbox(o)
        if looks_like_wheel(d):
            cands.append((c.y, o, d))
    if len(cands) < 2:
        return None, None

    cands.sort(key=lambda t: t[0])
    return cands[0][1], cands[-1][1]      # крайние по оси Y


# ---------------------------------------------------------------- сборка

def empty(name, parent, loc=(0, 0, 0), rot=(0, 0, 0), size=0.1):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    o.empty_display_size = size
    o.location = loc
    o.rotation_euler = rot
    bpy.context.collection.objects.link(o)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def camera(name, parent, loc):
    cd = bpy.data.cameras.new(name)
    cd.lens, cd.clip_start, cd.clip_end = 24.0, 0.05, 2000.0
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    o.rotation_euler = (math.radians(90.0 * FWD), 0.0, 0.0)
    bpy.context.collection.objects.link(o)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def reparent(obj, parent):
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def main():
    if bpy is None:
        print("Запускать внутри Blender.")
        return

    objs = mesh_objects()
    if not objs:
        log("В сцене нет мешей. Сначала импортируйте модель:")
        log("File -> Import -> glTF / FBX / OBJ")
        return
    log("мешей в сцене:", len(objs))

    # --- 1. общий габарит и нормализация ----------------------------------
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        a, b, _, _ = world_bbox(o)
        mn = Vector((min(mn.x, a.x), min(mn.y, a.y), min(mn.z, a.z)))
        mx = Vector((max(mx.x, b.x), max(mx.y, b.y), max(mx.z, b.z)))
    size = mx - mn
    log("габарит модели: %.2f x %.2f x %.2f м" % (size.x, size.y, size.z))

    # если модель «длинная» по X — развернём на 90°, чтобы длина легла на Y
    root_helper = empty("__fit", None, (0, 0, 0), size=0.3)
    for o in objs:
        if o.parent is None:
            reparent(o, root_helper)

    if size.x > size.y * 1.4:
        root_helper.rotation_euler = (0, 0, math.radians(90))
        log("модель развёрнута: длина была по оси X")
        bpy.context.view_layer.update()

    if os.environ.get("ALPHA_FLIP"):
        root_helper.rotation_euler.z += math.pi
        log("применён разворот ALPHA_FLIP")
        bpy.context.view_layer.update()

    # --- 2. колёса ---------------------------------------------------------
    w1, w2 = find_wheels(objs)
    if w1 is None:
        log("!! Колёса не распознаны. Укажите вручную:")
        log('   os.environ["ALPHA_FRONT_WHEEL"] = "имя_объекта"')
        log('   os.environ["ALPHA_REAR_WHEEL"]  = "имя_объекта"')
        log("   Имена видны в Outliner справа сверху.")
        return

    _, _, c1, d1 = world_bbox(w1)
    _, _, c2, d2 = world_bbox(w2)
    base = abs(c2.y - c1.y)
    log("найдены колёса: %s и %s, база %.2f м" % (w1.name, w2.name, base))

    # --- 3. масштаб по колёсной базе --------------------------------------
    if base > 1e-4:
        k = WHEELBASE / base
        root_helper.scale = (k, k, k)
        bpy.context.view_layer.update()
        log("масштаб подогнан: x%.3f" % k)

    # пересчёт после масштабирования
    _, _, c1, d1 = world_bbox(w1)
    _, _, c2, d2 = world_bbox(w2)
    mn = Vector((1e9, 1e9, 1e9))
    for o in objs:
        a, _, _, _ = world_bbox(o)
        mn = Vector((min(mn.x, a.x), min(mn.y, a.y), min(mn.z, a.z)))

    # переднее — то, что в сторону FWD
    front, rear = (w1, w2) if (c1.y - c2.y) * FWD > 0 else (w2, w1)
    _, _, cf, _ = world_bbox(front)
    _, _, cr, _ = world_bbox(rear)

    # --- 4. поставить на землю и отцентровать -----------------------------
    mid_y = (cf.y + cr.y) / 2.0
    root_helper.location += Vector((-((cf.x + cr.x) / 2.0), -mid_y, -mn.z))
    bpy.context.view_layer.update()
    log("модель поставлена на землю и отцентрована")

    # --- 5. служебная иерархия --------------------------------------------
    AX_F = FWD * (WHEELBASE / 2.0)
    AX_R = -FWD * (WHEELBASE / 2.0)
    _, _, _, dfront = world_bbox(front)
    r_wheel = max(dfront.y, dfront.z) / 2.0 or WHEEL_R
    seat_h = 0.77

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.50))
    root = bpy.context.active_object
    root.name = "alphaMoped"
    root.scale = (0.34, 1.30, 0.46)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mat = bpy.data.materials.new("alpha_collision")
    root.data.materials.append(mat)
    try:
        root.data.i3d_attributes.non_renderable = True
        root.data.i3d_attributes.casts_shadows = False
        root.data.i3d_attributes.receive_shadows = False
        root.i3d_attributes.rigid_body_type = "dynamic"
        root.i3d_attributes.compound = True
        root.i3d_attributes.collision = True
        root.i3d_attributes.solver_iteration_count = 20
    except Exception as exc:
        log("ВНИМАНИЕ: аддон GIANTS I3D не найден, физика не задана:", exc)

    lean = empty("bodyLean", root, (0, 0, r_wheel), size=0.25)
    wheels = empty("wheels", root, (0, 0, 0), size=0.2)
    player = empty("player", root, (0, 0, 0), size=0.2)

    # колёса: невидимые стабилизаторы + видимые центральные
    empty("wheelFrontLeft",  wheels, (-STAB, AX_F, r_wheel), size=0.1)
    empty("wheelFrontRight", wheels, ( STAB, AX_F, r_wheel), size=0.1)
    wfm = empty("wheelFrontMid", wheels, (0, AX_F, r_wheel), size=0.1)
    empty("wheelRearLeft",   wheels, (-STAB, AX_R, r_wheel), size=0.1)
    empty("wheelRearRight",  wheels, ( STAB, AX_R, r_wheel), size=0.1)
    wrm = empty("wheelRearMid", wheels, (0, AX_R, r_wheel), size=0.1)

    empty("enterNode", player, (0.42, -FWD * 0.10, 0.55), size=0.12)
    empty("exitNode",  player, (0.62, -FWD * 0.10, 0.10), size=0.12)
    empty("playerSeatNode", player, (0, -FWD * 0.16, seat_h + 0.08), size=0.12)
    cam_t = empty("cameraTarget", player, (0, -FWD * 0.10, seat_h + 0.30), size=0.12)
    camera("cameraOutside", cam_t, (0, -FWD * 0.10, seat_h + 0.30))
    camera("cameraInside", player, (0, -FWD * 0.02, seat_h + 0.42))
    empty("handlebarNode", lean, (0, FWD * 0.47, 0.83), size=0.15)

    # --- 6. разложить меши -------------------------------------------------
    front.name = "wheelFrontMesh"
    rear.name = "wheelRearMesh"
    reparent(front, wfm)
    reparent(rear, wrm)

    for o in list(objs):
        if o in (front, rear):
            continue
        if o.parent is root_helper or o.parent is None:
            reparent(o, lean)

    # вспомогательный узел больше не нужен: применяем его трансформ детям
    bpy.ops.object.select_all(action="DESELECT")
    root_helper.select_set(True)
    bpy.context.view_layer.objects.active = root_helper

    log("")
    log("=" * 60)
    log("ГОТОВО. Структура собрана:")
    log("  alphaMoped (физика) -> bodyLean / wheels / player")
    log("  видимые колёса: wheelFrontMesh, wheelRearMesh")
    log("=" * 60)
    log("Дальше — установка В БЕЗОПАСНОМ РЕЖИМЕ (две строки):")
    log('  import os; os.environ["ALPHA_SAFE"] = "1"')
    log("  exec(... install_alpha_mod.py ...)")
    log("")
    log("Если мопед смотрит назад — задайте ALPHA_FLIP=1 и соберите заново.")


if __name__ == "__main__":
    main()
