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
    from mathutils import Vector
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


def tube(name, parent, p0, p1, radius, mat=None, verts=14):
    """Труба, соединяющая две точки. Углы считаются сами."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    length = d.length
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=length, location=(a + b) / 2.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    if mat is not None:
        obj.data.materials.append(mat)
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


def wheel_mesh(name, parent, loc, radius, width, mat_tire, mat_rim, spokes=12):
    """Покрышка + обод + ступица + спицы одним объектом.

    Поворот ОБЯЗАТЕЛЬНО запекается в сетку: игра каждый кадр выставляет
    поворот driveNode для вращения колеса и стирает поворот объекта.
    """
    tyre_minor = width * 0.62
    bpy.ops.mesh.primitive_torus_add(location=loc,
                                     major_radius=radius - tyre_minor,
                                     minor_radius=tyre_minor,
                                     major_segments=36, minor_segments=12)
    tire = bpy.context.active_object
    tire.name = name
    tire.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    tire.data.materials.append(mat_tire)
    smooth(tire)

    parts = []

    # обод — тонкое кольцо, а не диск
    bpy.ops.mesh.primitive_torus_add(location=loc,
                                     major_radius=radius - tyre_minor * 2.1,
                                     minor_radius=width * 0.16,
                                     major_segments=28, minor_segments=8)
    rim = bpy.context.active_object
    rim.name = name + "_rim"
    rim.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    rim.data.materials.append(mat_rim)
    smooth(rim)
    parts.append(rim)

    parts.append(cylinder(name + "_hub", None, loc, radius * 0.14, width * 1.2,
                          axis="X", verts=16, mat=mat_rim))

    r_out = radius - tyre_minor * 2.1
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        p0 = (loc[0], loc[1] + math.cos(a) * radius * 0.12,
              loc[2] + math.sin(a) * radius * 0.12)
        p1 = (loc[0], loc[1] + math.cos(a) * r_out,
              loc[2] + math.sin(a) * r_out)
        parts.append(tube(name + "_sp%d" % i, None, p0, p1,
                          radius * 0.014, mat_rim, verts=6))

    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    tire.select_set(True)
    bpy.context.view_layer.objects.active = tire
    bpy.ops.object.join()

    tire.name = name
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

    def Y(v):
        """v > 0 — в сторону переда мопеда."""
        return FWD * v

    def L(z):
        return z - WHEEL_R

    # опорные точки рамы (мировые координаты, z от земли)
    HEAD_TOP  = (0, Y(0.44), 0.95)
    HEAD_BOT  = (0, Y(0.50), 0.70)
    AX_F      = (0, Y(0.61), WHEEL_R)
    ENG_BOT   = (0, Y(0.05), 0.30)
    REAR_TOP  = (0, Y(-0.30), 0.72)
    SWING     = (0, Y(-0.28), 0.38)
    AX_R      = (0, Y(-0.61), WHEEL_R)

    # ---- рама трубами -----------------------------------------------------
    tube("frameMesh",  lean, HEAD_TOP, REAR_TOP, 0.022, m_black)   # верхняя
    tube("frameDown",  lean, HEAD_BOT, ENG_BOT,  0.022, m_black)   # подседельная
    tube("frameCradle", lean, ENG_BOT, SWING,    0.020, m_black)   # низ
    tube("frameStay",  lean, REAR_TOP, SWING,    0.018, m_black)   # подкос
    tube("headTube",   lean, HEAD_TOP, HEAD_BOT, 0.032, m_chrome)  # рулевая колонка
    for x in (-0.055, 0.055):
        tube("swingarm%s" % ("L" if x < 0 else "R"), lean,
             (x, SWING[1], SWING[2]), (x, AX_R[1], AX_R[2]), 0.016, m_black)
    tube("shock", lean, (0.045, Y(-0.32), 0.68), (0.045, Y(-0.52), 0.40),
         0.016, m_chrome)

    # ---- бак, седло -------------------------------------------------------
    box("tankMesh", lean, (0, Y(0.26), 0.83), (0.20, 0.40, 0.17),
        rot=(math.radians(-6 * FWD), 0, 0), mat=m_paint,
        bev=0.045, taper=(0.35, 0.7))
    box("seatMesh", lean, (0, Y(-0.10), 0.80), (0.21, 0.46, 0.065),
        mat=m_black, bev=0.028, taper=(0.85, 0.9))

    # ---- двигатель --------------------------------------------------------
    box("engineMesh", lean, (0, Y(0.06), 0.42), (0.20, 0.24, 0.22),
        mat=m_engine, bev=0.018)
    for i in range(5):
        box("engineFin%d" % i, lean, (0, Y(0.13), 0.50 + i * 0.030),
            (0.17, 0.13, 0.008), rot=(math.radians(22 * FWD), 0, 0),
            mat=m_engine, bev=0.002)
    cylinder("engineHead", lean, (0, Y(0.17), 0.60), 0.060, 0.13,
             axis="Y", rot_extra=(math.radians(22 * FWD), 0, 0),
             verts=16, mat=m_engine)
    cylinder("crankCase", lean, (0, Y(0.02), 0.36), 0.095, 0.19,
             axis="X", verts=18, mat=m_engine)

    # ---- выпуск -----------------------------------------------------------
    tube("exhaustPipe", lean, (0.05, Y(0.14), 0.40), (0.10, Y(-0.16), 0.31),
         0.017, m_chrome)
    cone("exhaustMesh", lean, (0.105, Y(-0.42), 0.32), 0.036, 0.030, 0.52,
         axis="Y", mat=m_chrome)

    # ---- задняя часть -----------------------------------------------------
    box("rearRackMesh", lean, (0, Y(-0.56), 0.86), (0.24, 0.22, 0.028),
        mat=m_black, bev=0.010)
    arc_shell("fenderRearMesh", lean, (0, AX_R[1], 0),
              radius=WHEEL_R + 0.035, width=0.115, thickness=0.010,
              a_start=math.radians(40), a_end=math.radians(155), mat=m_paint)
    cylinder("chainSprocket", lean, (-0.070, AX_R[1], 0.0), 0.095, 0.009,
             axis="X", verts=18, mat=m_chrome)
    box("chainGuard", lean, (-0.080, Y(-0.34), 0.30), (0.010, 0.36, 0.07),
        mat=m_black, bev=0.008)
    tube("kickstand", lean, (-0.095, Y(0.00), 0.28), (-0.15, Y(-0.06), 0.02),
         0.011, m_black)

    # ---- служебные точки и фонари ----------------------------------------
    empty("engineNode", lean, (0, Y(0.06), 0.42), size=0.05)
    empty("exhaustEffectNode", lean, (0.105, Y(-0.68), 0.32),
          rot=(0, 0, math.radians(180 if FWD > 0 else 0)), size=0.05)
    cylinder("brakeLightNode", lean, (0, Y(-0.64), 0.86), 0.040, 0.045,
             axis="Y", verts=14, mat=m_red)
    cylinder("turnLightRearLeft", lean, (-0.125, Y(-0.62), 0.85), 0.024, 0.045,
             axis="Y", verts=10, mat=m_amber)
    cylinder("turnLightRearRight", lean, (0.125, Y(-0.62), 0.85), 0.024, 0.045,
             axis="Y", verts=10, mat=m_amber)

    # ---- передок ----------------------------------------------------------
    steer = empty("handlebarNode", lean, (0, Y(0.47), 0.83), size=0.15)

    for x in (-0.070, 0.070):
        tube("forkMesh" if x < 0 else "forkMeshR", steer,
             (x, HEAD_BOT[1], HEAD_BOT[2]), (x, AX_F[1], AX_F[2]),
             0.018, m_chrome)
    tube("triple", steer, (-0.085, Y(0.47), 0.86), (0.085, Y(0.47), 0.86),
         0.016, m_chrome)

    cylinder("handlebarMesh", steer, (0, Y(0.44), 1.00), 0.012, 0.56,
             axis="X", verts=12, mat=m_black)
    for x in (-0.25, 0.25):
        cylinder("grip%s" % ("L" if x < 0 else "R"), steer,
                 (x, Y(0.44), 1.00), 0.017, 0.10, axis="X",
                 verts=10, mat=m_black)
        tube("mirrorStem%s" % ("L" if x < 0 else "R"), steer,
             (x, Y(0.44), 1.01), (x * 1.15, Y(0.42), 1.16), 0.006, m_chrome)
        cylinder("mirror%s" % ("L" if x < 0 else "R"), steer,
                 (x * 1.15, Y(0.42), 1.17), 0.038, 0.010, axis="Y",
                 verts=14, mat=m_black)

    arc_shell("fenderFrontMesh", steer, (0, AX_F[1], 0),
              radius=WHEEL_R + 0.032, width=0.105, thickness=0.009,
              a_start=math.radians(35), a_end=math.radians(125), mat=m_paint)

    cylinder("headlightCase", steer, (0, Y(0.53), 0.90), 0.075, 0.09,
             axis="Y", verts=20, mat=m_chrome)
    cylinder("headlightGlass", steer, (0, Y(0.575), 0.90), 0.068, 0.018,
             axis="Y", verts=20, mat=m_glass)
    empty("headlightLow",  steer, (0, Y(0.59), 0.90), size=0.05)
    empty("headlightHigh", steer, (0, Y(0.59), 0.90), size=0.05)
    cylinder("turnLightFrontLeft", steer, (-0.155, Y(0.50), 0.88), 0.023, 0.045,
             axis="Y", verts=10, mat=m_amber)
    cylinder("turnLightFrontRight", steer, (0.155, Y(0.50), 0.88), 0.023, 0.045,
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
