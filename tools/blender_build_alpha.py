#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_build_alpha.py
======================

Строит модель мопеда «Альфа 110» в Blender с иерархией узлов под
FS19_AlphaMoped/alphaMoped.xml.

Запуск:
    Scripting -> Open -> Run Script
или целиком через tools/alpha_all_in_one.py (сборка + экспорт + установка).

Геометрия скруглённая: фаски, сглаженные нормали, гнутые крылья, спицы.
Имена и иерархия узлов менять нельзя — на них ссылается XML.
"""

import math

try:
    import bpy
    import bmesh
except ImportError:            # запуск вне Blender — только проверка синтаксиса
    bpy = None
    bmesh = None


# ----------------------------------------------------------------------------
# Параметры (метры, пропорции реальной Альфа 110)
# ----------------------------------------------------------------------------

FWD = -1.0          # направление "вперёд" по оси Y в Blender

WHEELBASE   = 1.22
WHEEL_R     = 0.335
WHEEL_W     = 0.075
STAB_OFFSET = 0.22  # разнос НЕВИДИМЫХ колёс-стабилизаторов от осевой линии.
                    # Видимые колёса стоят по центру отдельными узлами,
                    # поэтому на внешний вид это не влияет.

AXLE_F = FWD * (WHEELBASE / 2.0)
AXLE_R = -FWD * (WHEELBASE / 2.0)

SEAT_H = 0.77


# ----------------------------------------------------------------------------
# Утилиты
# ----------------------------------------------------------------------------

def clear_scene():
    if bpy.context.screen is not None and bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_cancel(restore_frame=False)
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects,
                  bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def make_material(name, rgba, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        if bpy.app.version < (4, 0, 0) or mat.node_tree is None:
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            for n in mat.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    bsdf = n
                    break
        if bsdf is not None:
            for socket, value in (("Base Color", rgba), ("Metallic", metallic),
                                  ("Roughness", roughness)):
                if socket in bsdf.inputs:
                    bsdf.inputs[socket].default_value = value
        mat.diffuse_color = rgba
    return mat


def attach(obj, parent):
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def smooth(obj):
    """Сглаженные нормали — убирает 'гранёный' вид у круглых деталей."""
    try:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()
    except Exception:
        for poly in obj.data.polygons:
            poly.use_smooth = True


def bevel(obj, width=0.008, segments=2):
    """Фаска по рёбрам: коробка перестаёт выглядеть коробкой."""
    try:
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = width
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(50)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as exc:
        print("[alpha] фаска не применилась:", exc)
    return obj


def empty(name, parent, loc=(0, 0, 0), rot=(0, 0, 0), size=0.08):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = loc
    obj.rotation_euler = rot
    bpy.context.collection.objects.link(obj)
    return attach(obj, parent)


def camera(name, parent, loc):
    cam = bpy.data.cameras.new(name)
    cam.lens = 24.0
    cam.clip_start = 0.05
    cam.clip_end = 2000.0
    obj = bpy.data.objects.new(name, cam)
    obj.location = loc
    obj.rotation_euler = (math.radians(90.0 * FWD), 0.0, 0.0)
    bpy.context.collection.objects.link(obj)
    return attach(obj, parent)


def box(name, parent, loc, size, rot=(0, 0, 0), mat=None, bev=0.008, taper=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if taper:  # сузить верх/перед: (масштаб_верха_X, масштаб_верха_Z)
        me = obj.data
        zs = [v.co.z for v in me.vertices]
        zmax = max(zs)
        for v in me.vertices:
            if abs(v.co.z - zmax) < 1e-6:
                v.co.x *= taper[0]
                v.co.y *= taper[1]

    if mat is not None:
        obj.data.materials.append(mat)
    if bev:
        bevel(obj, bev)
    return attach(obj, parent)


def cylinder(name, parent, loc, radius, depth, axis="X", rot_extra=(0, 0, 0),
             verts=24, mat=None, smooth_it=True, bev=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    base = {"X": (0, math.radians(90), 0),
            "Y": (math.radians(90), 0, 0),
            "Z": (0, 0, 0)}[axis]
    obj.rotation_euler = tuple(base[i] + rot_extra[i] for i in range(3))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if mat is not None:
        obj.data.materials.append(mat)
    if bev:
        bevel(obj, bev)
    if smooth_it:
        smooth(obj)
    return attach(obj, parent)


def cone(name, parent, loc, r1, r2, depth, axis="Y", verts=20, mat=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    base = {"X": (0, math.radians(90), 0),
            "Y": (math.radians(90), 0, 0),
            "Z": (0, 0, 0)}[axis]
    obj.rotation_euler = base
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if mat is not None:
        obj.data.materials.append(mat)
    smooth(obj)
    return attach(obj, parent)


def arc_shell(name, parent, center, radius, width, thickness,
              a_start, a_end, segments=14, mat=None):
    """Гнутая пластина — крыло над колесом. Дуга в плоскости YZ."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()

    ring = []
    for i in range(segments + 1):
        a = a_start + (a_end - a_start) * i / segments
        for r in (radius, radius + thickness):
            y = math.cos(a) * r
            z = math.sin(a) * r
            ring.append([bm.verts.new((-width / 2, y, z)),
                         bm.verts.new((width / 2, y, z))])

    for i in range(segments):
        i0, i1 = i * 2, (i + 1) * 2
        bm.faces.new((ring[i0][0], ring[i1][0], ring[i1][1], ring[i0][1]))
        bm.faces.new((ring[i0 + 1][1], ring[i1 + 1][1],
                      ring[i1 + 1][0], ring[i0 + 1][0]))
        bm.faces.new((ring[i0][0], ring[i0 + 1][0],
                      ring[i1 + 1][0], ring[i1][0]))
        bm.faces.new((ring[i0][1], ring[i1][1],
                      ring[i1 + 1][1], ring[i0 + 1][1]))

    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    obj = bpy.data.objects.new(name, me)
    obj.location = center
    bpy.context.collection.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    smooth(obj)
    return attach(obj, parent)


def wheel_mesh(name, parent, loc, radius, width, mat_tire, mat_rim, spokes=10):
    """Покрышка + обод + ступица + спицы, слитые в один объект.

    ВАЖНО: поворот обязательно запекается в саму сетку (transform_apply).
    Игра каждый кадр выставляет поворот driveNode, чтобы колесо крутилось,
    и стирает любой поворот, оставшийся на объекте — колесо ляжет плашмя.
    """
    parts = []

    bpy.ops.mesh.primitive_torus_add(location=loc,
                                     major_radius=radius - width * 0.55,
                                     minor_radius=width * 0.62,
                                     major_segments=32, minor_segments=12)
    tire = bpy.context.active_object
    tire.name = name
    tire.rotation_euler = (0, math.radians(90), 0)      # ось вращения -> X
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    tire.data.materials.append(mat_tire)
    smooth(tire)

    parts.append(cylinder(name + "_rim", None, loc, radius * 0.42, width * 0.85,
                          axis="X", verts=24, mat=mat_rim))
    parts.append(cylinder(name + "_hub", None, loc, radius * 0.13, width * 1.15,
                          axis="X", verts=14, mat=mat_rim))

    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        r_mid = radius * 0.28
        p = (loc[0], loc[1] + math.cos(a) * r_mid, loc[2] + math.sin(a) * r_mid)
        parts.append(cylinder(name + "_sp%d" % i, None, p,
                              radius * 0.022, radius * 0.60,
                              axis="Z", rot_extra=(a, 0, 0), verts=6,
                              mat=mat_rim))

    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    tire.select_set(True)
    bpy.context.view_layer.objects.active = tire
    bpy.ops.object.join()

    tire.name = name
    # финальная страховка: на объекте не должно остаться поворота
    tire.rotation_euler = (0, 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return attach(tire, parent)


def box_origin_zero(name, parent, center, size, mat=None):
    """Коробка с геометрией в center, но origin объекта в (0,0,0).
    Нужно корневому узлу: FS отсчитывает позицию компонента от origin."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if mat is not None:
        obj.data.materials.append(mat)
    return attach(obj, parent)


def set_rigid_body(obj, body_type="dynamic", compound=False, collision=True,
                   solver_iterations=10):
    """Физика для экспортёра GIANTS. Без неё техника не ставится в магазине."""
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


# ----------------------------------------------------------------------------
# Сборка
# ----------------------------------------------------------------------------

def build():
    clear_scene()

    m_paint  = make_material("alpha_paint",  (0.42, 0.03, 0.05, 1.0), 0.4, 0.18)
    m_black  = make_material("alpha_black",  (0.035, 0.035, 0.04, 1.0), 0.0, 0.65)
    m_chrome = make_material("alpha_chrome", (0.78, 0.79, 0.82, 1.0), 1.0, 0.12)
    m_engine = make_material("alpha_engine", (0.36, 0.37, 0.39, 1.0), 0.85, 0.4)
    m_glass  = make_material("alpha_glass",  (0.96, 0.94, 0.80, 1.0), 0.0, 0.05)
    m_amber  = make_material("alpha_amber",  (0.90, 0.45, 0.05, 1.0), 0.0, 0.3)
    m_red    = make_material("alpha_red",    (0.80, 0.05, 0.05, 1.0), 0.0, 0.3)
    m_col    = make_material("alpha_collision", (0.1, 0.6, 0.1, 1.0), 0.0, 1.0)

    # === корень (component1): невидимая коллизия ============================
    root = box_origin_zero("alphaMoped", None,
                           center=(0, 0, 0.50), size=(0.34, 1.30, 0.46),
                           mat=m_col)
    # НЕ hide_render: visibility="false" наследуется детьми и прячет весь мопед
    try:
        root.data.i3d_attributes.non_renderable = True
        root.data.i3d_attributes.casts_shadows = False
        root.data.i3d_attributes.receive_shadows = False
    except Exception as exc:
        print("[alpha] не удалось задать non_renderable:", exc)
    set_rigid_body(root, "dynamic", compound=True, collision=True,
                   solver_iterations=20)

    # === 0: bodyLean — всё, что кренится ====================================
    lean = empty("bodyLean", root, (0, 0, WHEEL_R), size=0.25)

    #  рама: две трубы вместо коробки
    cylinder("frameMesh", lean, (0, FWD * 0.10, 0.66), 0.028, 0.62,
             axis="Y", rot_extra=(math.radians(-18 * FWD), 0, 0), mat=m_black)
    cylinder("frameDown", lean, (0, FWD * 0.22, 0.40), 0.026, 0.55,
             axis="Y", rot_extra=(math.radians(34 * FWD), 0, 0), mat=m_black)
    cylinder("frameRear", lean, (0, -FWD * 0.30, 0.55), 0.024, 0.52,
             axis="Y", rot_extra=(math.radians(-24 * FWD), 0, 0), mat=m_black)

    #  бак — скруглённый и сужается кверху
    box("tankMesh", lean, (0, FWD * 0.26, 0.80), (0.26, 0.48, 0.22),
        rot=(math.radians(-5 * FWD), 0, 0), mat=m_paint,
        bev=0.035, taper=(0.45, 0.75))

    #  седло
    box("seatMesh", lean, (0, -FWD * 0.20, SEAT_H + 0.03), (0.25, 0.58, 0.085),
        mat=m_black, bev=0.03, taper=(0.8, 0.85))

    #  двигатель: блок + рёбра охлаждения + цилиндр
    eng = box("engineMesh", lean, (0, FWD * 0.02, 0.40), (0.26, 0.30, 0.26),
              mat=m_engine, bev=0.02)
    for i in range(5):
        box("engineFin%d" % i, lean,
            (0, FWD * 0.10, 0.46 + i * 0.035), (0.22, 0.16, 0.010),
            rot=(math.radians(20 * FWD), 0, 0), mat=m_engine, bev=0.003)
    cylinder("engineHead", lean, (0, FWD * 0.14, 0.58), 0.075, 0.16,
             axis="Y", rot_extra=(math.radians(24 * FWD), 0, 0),
             verts=16, mat=m_engine)

    #  глушитель: труба + конический баллон
    cylinder("exhaustPipe", lean, (0.10, FWD * 0.05, 0.30), 0.020, 0.45,
             axis="Y", verts=14, mat=m_chrome)
    cone("exhaustMesh", lean, (0.13, -FWD * 0.40, 0.32), 0.050, 0.038, 0.52,
         axis="Y", mat=m_chrome)

    #  багажник, крыло, звезда
    box("rearRackMesh", lean, (0, -FWD * 0.64, SEAT_H + 0.09), (0.26, 0.24, 0.035),
        mat=m_black, bev=0.012)
    arc_shell("fenderRearMesh", lean, (0, AXLE_R, 0),
              radius=WHEEL_R + 0.045, width=0.13, thickness=0.012,
              a_start=math.radians(35), a_end=math.radians(150),
              mat=m_paint)
    cylinder("chainSprocket", lean, (-0.075, AXLE_R, 0.0), 0.105, 0.010,
             axis="X", verts=18, mat=m_chrome)
    box("chainGuard", lean, (-0.085, -FWD * 0.30, 0.22), (0.012, 0.42, 0.09),
        mat=m_black, bev=0.01)
    cylinder("kickstand", lean, (-0.12, FWD * 0.02, 0.12), 0.012, 0.24,
             axis="Z", rot_extra=(0, math.radians(20), 0), verts=8, mat=m_black)

    #  служебные точки
    empty("engineNode", lean, (0, FWD * 0.02, 0.42), size=0.05)
    empty("exhaustEffectNode", lean, (0.15, -FWD * 0.66, 0.33),
          rot=(0, 0, math.radians(180 if FWD > 0 else 0)), size=0.05)

    #  фонари
    cylinder("brakeLightNode", lean, (0, -FWD * 0.72, 0.84), 0.045, 0.05,
             axis="Y", verts=14, mat=m_red)
    cylinder("turnLightRearLeft", lean, (-0.14, -FWD * 0.70, 0.83), 0.028, 0.05,
             axis="Y", verts=10, mat=m_amber)
    cylinder("turnLightRearRight", lean, (0.14, -FWD * 0.70, 0.83), 0.028, 0.05,
             axis="Y", verts=10, mat=m_amber)

    # --- рулёжка -----------------------------------------------------------
    steer = empty("handlebarNode", lean, (0, FWD * 0.52, 0.78),
                  rot=(math.radians(24 * FWD), 0, 0), size=0.15)

    #  перья вилки — две трубы
    for side, xoff in (("L", -0.085), ("R", 0.085)):
        cylinder("forkMesh" if side == "L" else "forkMesh" + side, steer,
                 (xoff, FWD * 0.60, 0.62), 0.019, 0.60,
                 axis="Z", rot_extra=(math.radians(24 * FWD), 0, 0),
                 verts=12, mat=m_chrome)

    #  руль: перекладина + две ручки
    cylinder("handlebarMesh", steer, (0, FWD * 0.50, 1.04), 0.013, 0.60,
             axis="X", verts=12, mat=m_black)
    for xoff in (-0.27, 0.27):
        cylinder("grip%s" % ("L" if xoff < 0 else "R"), steer,
                 (xoff, FWD * 0.50, 1.04), 0.019, 0.11,
                 axis="X", verts=10, mat=m_black)
    #  зеркала
    for xoff in (-0.24, 0.24):
        cylinder("mirrorStem%s" % ("L" if xoff < 0 else "R"), steer,
                 (xoff, FWD * 0.50, 1.13), 0.007, 0.17, axis="Z",
                 verts=8, mat=m_chrome)
        cylinder("mirror%s" % ("L" if xoff < 0 else "R"), steer,
                 (xoff, FWD * 0.50, 1.22), 0.042, 0.012, axis="Y",
                 verts=14, mat=m_black)

    #  переднее крыло — гнутое
    arc_shell("fenderFrontMesh", steer, (0, AXLE_F, 0),
              radius=WHEEL_R + 0.040, width=0.12, thickness=0.010,
              a_start=math.radians(30), a_end=math.radians(120),
              mat=m_paint)

    #  фара: корпус + стекло
    cylinder("headlightCase", steer, (0, FWD * 0.585, 0.90), 0.082, 0.10,
             axis="Y", verts=20, mat=m_chrome)
    cylinder("headlightGlass", steer, (0, FWD * 0.635, 0.90), 0.074, 0.02,
             axis="Y", verts=20, mat=m_glass)
    empty("headlightLow",  steer, (0, FWD * 0.65, 0.90), size=0.05)
    empty("headlightHigh", steer, (0, FWD * 0.65, 0.90), size=0.05)
    cylinder("turnLightFrontLeft", steer, (-0.17, FWD * 0.56, 0.88), 0.026, 0.05,
             axis="Y", verts=10, mat=m_amber)
    cylinder("turnLightFrontRight", steer, (0.17, FWD * 0.56, 0.88), 0.026, 0.05,
             axis="Y", verts=10, mat=m_amber)

    # === 1: колёса ==========================================================
    # Видимые колёса — отдельные ЦЕНТРАЛЬНЫЕ узлы (как FMR/RMR у мода MX),
    # иначе меш на боковом узле уезжает дугой при повороте руля.
    wheels = empty("wheels", root, (0, 0, 0), size=0.2)

    empty("wheelFrontLeft",  wheels, (-STAB_OFFSET, AXLE_F, WHEEL_R), size=0.1)
    empty("wheelFrontRight", wheels, ( STAB_OFFSET, AXLE_F, WHEEL_R), size=0.1)

    wfm = empty("wheelFrontMid", wheels, (0, AXLE_F, WHEEL_R), size=0.1)
    wheel_mesh("wheelFrontMesh", wfm, (0, AXLE_F, WHEEL_R),
               WHEEL_R, WHEEL_W, m_black, m_chrome)

    empty("wheelRearLeft",  wheels, (-STAB_OFFSET, AXLE_R, WHEEL_R), size=0.1)
    empty("wheelRearRight", wheels, ( STAB_OFFSET, AXLE_R, WHEEL_R), size=0.1)

    wrm = empty("wheelRearMid", wheels, (0, AXLE_R, WHEEL_R), size=0.1)
    wheel_mesh("wheelRearMesh", wrm, (0, AXLE_R, WHEEL_R),
               WHEEL_R, WHEEL_W + 0.012, m_black, m_chrome)

    # === 2: игрок и камеры ==================================================
    player = empty("player", root, (0, 0, 0), size=0.2)
    empty("enterNode", player, (0.42, -FWD * 0.10, 0.55), size=0.12)
    empty("exitNode",  player, (0.62, -FWD * 0.10, 0.10), size=0.12)
    empty("playerSeatNode", player, (0, -FWD * 0.16, SEAT_H + 0.08),
          rot=(0, 0, math.radians(0 if FWD < 0 else 180)), size=0.12)

    cam_target = empty("cameraTarget", player,
                       (0, -FWD * 0.10, SEAT_H + 0.30), size=0.12)
    camera("cameraOutside", cam_target, (0, -FWD * 0.10, SEAT_H + 0.30))
    camera("cameraInside", player, (0, -FWD * 0.02, SEAT_H + 0.42))

    return root


EXPECTED_MAPPINGS = """
ВНИМАНИЕ: экспортёр GIANTS сортирует детей узла ПО АЛФАВИТУ, поэтому
реальные индексные пути не совпадают с порядком создания объектов здесь.
Не выписывайте их руками — install_alpha_mod.py читает готовый .i3d и
подставляет пути автоматически.

Посмотреть реальное дерево: tools/dump_i3d_tree.py
"""


def main():
    if bpy is None:
        print("Этот скрипт нужно запускать внутри Blender.")
        return
    build()
    print(EXPECTED_MAPPINGS)
    print("Модель собрана: скруглённые формы, гнутые крылья, спицы, зеркала.")
    print("Корень alphaMoped: Rigid Body = Dynamic + Compound, non_renderable.")
    print("Видимые колёса — центральные узлы wheelFrontMid / wheelRearMid.")
    print("")
    print("ЭКСПОРТ: File -> Export -> I3D, Everything, Keep Collections ВЫКЛ")


if __name__ == "__main__":
    main()
