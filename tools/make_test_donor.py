#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_test_donor.py — собирает игрушечный мод-донор, чтобы прогонять
alpha_from_donor.py без настоящего 16-мегабайтного архива.

Делает два варианта:
    FS22_AlphaClassic.zip — как настоящий донор: геометрия версии 7,
                            колёса отдельным файлом wheels/wheels.i3d;
    FS19_AlphaClassic.zip — как уже сконвертированный: версия 5, без wheels/.

Запуск:  python make_test_donor.py <куда положить>
"""

import os
import random
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i3d_shapes as codec  # noqa: E402


def part(name, ident, nv=40):
    random.seed(ident)
    p = codec.Part(1, name, ident)
    p.bounding = (0.0, 0.0, 0.0, 1.0)
    p.positions = [(random.random(), random.random(), random.random())
                   for _ in range(nv)]
    p.normals = [(0.0, 1.0, 0.0)] * nv
    p.uvs[0] = [(0.1, 0.2)] * nv
    p.triangles = [(i % nv, (i + 1) % nv, (i + 2) % nv) for i in range(20)]
    p.subsets = [{"firstVertex": 0, "numVertices": nv, "firstIndex": 0,
                  "numIndices": 60, "uvDensity": [1.0]}]
    p.parsed = True
    return p


MAIN_I3D = """<?xml version="1.0" encoding="iso-8859-1"?>
<i3D name="AlphaClassic" version="1.6">
  <Files>
    <File fileId="4" filename="$data/shaders/vehicleShader.xml"/>
    <File fileId="11" filename="$data/shaders/glowShader.xml"/>
    <File fileId="27" filename="$data/shared/assets/lights/lizard/rearLight22_normal.png"/>
    <File fileId="2" filename="textures/frameAlpha_normal.dds"/>
  </Files>
  <Materials>
    <Material name="frame" materialId="5"><Normalmap fileId="2"/></Material>
    <Material name="glow" materialId="6" customShaderId="11"/>
  </Materials>
  <Shapes externalShapesFile="AlphaClassic.i3d.shapes"/>
  <Scene>
    <Shape name="alphaClassic_component1" shapeId="1" dynamic="true" compound="true" nonRenderable="true" materialIds="5">
      <TransformGroup name="frontSuspensionRot">
        <Shape name="vilka1" shapeId="1" materialIds="5">
          <TransformGroup name="wheelsFront"><TransformGroup name="wheel"/></TransformGroup>
        </Shape>
      </TransformGroup>
      <TransformGroup name="frame">
        <TransformGroup name="wheelsBack">
          <TransformGroup name="wheel"><TransformGroup name="wheelPhysics"/></TransformGroup>
          <TransformGroup name="wheelSupport1"/>
          <TransformGroup name="wheelSupport2"/>
        </TransformGroup>
        <TransformGroup name="visual">
          <Shape name="frameAlpha" shapeId="1" materialIds="5"/>
          <Shape name="motor" shapeId="2" materialIds="5"/>
        </TransformGroup>
        <TransformGroup name="lights">
          <TransformGroup name="defaultLights">
            <Light name="frontLightLow" type="spot"/>
            <Light name="frontLightHigh" type="spot"/>
          </TransformGroup>
          <Shape name="brakeLight_vis" shapeId="3" materialIds="6"/>
        </TransformGroup>
        <TransformGroup name="characterNode"><TransformGroup name="Player"/></TransformGroup>
        <TransformGroup name="cameras">
          <TransformGroup name="outdoorCameraTarget"><Camera name="outdoorCamera1" fov="60"/></TransformGroup>
          <Camera name="indoorCamera1" fov="70"/>
        </TransformGroup>
        <TransformGroup name="exitPoint"/>
      </TransformGroup>
    </Shape>
  </Scene>
</i3D>
"""

WHEELS_I3D = """<?xml version="1.0" encoding="iso-8859-1"?>
<i3D name="wheels" version="1.6">
  <Files>
    <File fileId="4" filename="$data/shaders/vehicleShader.xml"/>
    <File fileId="9" filename="../textures/tireL358_normal.dds"/>
  </Files>
  <Materials><Material name="tyre" materialId="7"><Normalmap fileId="9"/></Material></Materials>
  <Shapes externalShapesFile="wheels.i3d.shapes"/>
  <Scene>
    <TransformGroup name="wheels">
      <TransformGroup name="front"><Shape name="wheelDriveF1" shapeId="1" materialIds="7" translation="0 1 0"/></TransformGroup>
      <TransformGroup name="back"><Shape name="wheelDriveB1" shapeId="2" materialIds="7"/></TransformGroup>
      <TransformGroup name="tyre"><Shape name="tireL358" shapeId="3" materialIds="7"/></TransformGroup>
    </TransformGroup>
  </Scene>
</i3D>
"""

VEHICLE = """<?xml version="1.0" encoding="utf-8"?>
<vehicle type="carFillable">
<i3dMappings>
<i3dMapping id="alphaClassic_component1" node="0>"/>
<i3dMapping id="vilka1" node="0>0|0"/>
<i3dMapping id="wheel_0" node="0>0|0|0|0"/>
<i3dMapping id="frame" node="0>1"/>
<i3dMapping id="wheel_1" node="0>1|0|0"/>
<i3dMapping id="wheelPhysics" node="0>1|0|0|0"/>
<i3dMapping id="wheelSupport1" node="0>1|0|1"/>
<i3dMapping id="wheelSupport2" node="0>1|0|2"/>
<i3dMapping id="frameAlpha" node="0>1|1|0"/>
<i3dMapping id="motor" node="0>1|1|1"/>
<i3dMapping id="frontLightLow" node="0>1|2|0|0"/>
<i3dMapping id="frontLightHigh" node="0>1|2|0|1"/>
<i3dMapping id="brakeLight_vis" node="0>1|2|1"/>
<i3dMapping id="characterNode" node="0>1|3"/>
<i3dMapping id="Player" node="0>1|3|0"/>
<i3dMapping id="outdoorCameraTarget" node="0>1|4|0"/>
<i3dMapping id="outdoorCamera1" node="0>1|4|0|0"/>
<i3dMapping id="indoorCamera1" node="0>1|4|1"/>
<i3dMapping id="exitPoint" node="0>1|5"/>
</i3dMappings>
</vehicle>
"""


def dds(fmt):
    if fmt == "bc7":
        return b"DDS " + bytes(80) + b"DX10" + bytes(40) + struct.pack("<I", 98)
    return b"DDS " + bytes(80) + b"DXT5" + bytes(40)


def build(target_dir):
    os.makedirs(target_dir, exist_ok=True)

    main_parts = [part("frameAlpha", 1), part("motor", 2), part("fara", 3)]
    wheel_parts = [part("wheelDriveF1", 1), part("wheelDriveB1", 2),
                   part("tireL358", 3)]

    # --- как настоящий донор FS22
    fs22 = os.path.join(target_dir, "FS22_AlphaClassic.zip")
    with zipfile.ZipFile(fs22, "w") as z:
        z.writestr("AlphaClassic.i3d", MAIN_I3D)
        z.writestr("AlphaClassic.i3d.shapes",
                   codec.ShapesFile(7, 0x2D, main_parts).save())
        z.writestr("AlphaClassic.xml", VEHICLE)
        z.writestr("modDesc.xml", '<modDesc descVersion="79"/>')
        z.writestr("wheels/wheels.i3d", WHEELS_I3D)
        z.writestr("wheels/wheels.i3d.shapes",
                   codec.ShapesFile(7, 0x2D, wheel_parts).save())
        z.writestr("textures/frameAlpha_normal.dds", dds("dxt5"))
        z.writestr("textures/bc7.dds", dds("bc7"))

    # --- как уже сконвертированный мод: версия 5, колёса внутри
    fs19 = os.path.join(target_dir, "FS19_AlphaClassic.zip")
    with zipfile.ZipFile(fs19, "w") as z:
        z.writestr("AlphaClassic.i3d", MAIN_I3D)
        z.writestr("AlphaClassic.i3d.shapes",
                   codec.ShapesFile(5, 0x2D, main_parts + wheel_parts).save())
        z.writestr("AlphaClassic.xml", VEHICLE)
        z.writestr("modDesc.xml", '<modDesc descVersion="53"/>')
        z.writestr("textures/frameAlpha_normal.dds", dds("dxt5"))

    print(fs22)
    print(fs19)
    return fs22, fs19


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else ".")
