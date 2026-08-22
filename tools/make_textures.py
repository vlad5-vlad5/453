#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_textures.py — подготовка иконок и store-картинок для модов FS19.

FS19 хочет сжатые DDS:
    иконка мода          icon_*.dds    256x256  DXT5
    картинка в магазине  store_*.dds   512x512  DXT5

Несжатый (raw) DDS игра тоже читает, но пишет в log.txt:
    Warning (performance): Texture ... raw format.
и держит текстуру в памяти в 4 раза больше. Поэтому жмём в DXT5.

Нужен ImageMagick (`convert`) — он умеет писать сжатые DDS,
в отличие от Pillow.

    python3 tools/make_textures.py
"""

import os
import shutil
import subprocess
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (png относительно корня репозитория, сторона в пикселях)
TARGETS = [
    ("FS19_FarmHelper/icon_FarmHelper.png",   256),
    ("FS19_AlphaMoped/icon_alphaMoped.png",   256),
    ("FS19_AlphaMoped/store_alphaMoped.png",  512),
]


def find_magick():
    for exe in ("magick", "convert"):
        path = shutil.which(exe)
        if path:
            return path
    return None


def describe(dds_path):
    with open(dds_path, "rb") as f:
        head = f.read(128)
    if len(head) < 88 or head[:4] != b"DDS ":
        return "не похоже на DDS"
    h = struct.unpack("<7I", head[4:32])
    fourcc = head[84:88].decode("ascii", "replace").strip("\x00") or "raw"
    size_kb = os.path.getsize(dds_path) // 1024
    return "%dx%d %s %d KB" % (h[3], h[2], fourcc, size_kb)


def convert(magick, rel_png, size):
    src = os.path.join(ROOT, rel_png)
    if not os.path.exists(src):
        print("пропуск (нет файла):", rel_png)
        return

    dst = os.path.splitext(src)[0] + ".dds"

    cmd = [magick]
    if os.path.basename(magick).startswith("magick"):
        cmd.append("convert")
    cmd += [
        src,
        "-resize", "%dx%d!" % (size, size),
        "-alpha", "set",                      # без альфы ImageMagick уйдёт в DXT1
        "-define", "dds:compression=dxt5",
        "-define", "dds:mipmaps=0",
        dst,
    ]

    subprocess.run(cmd, check=True)
    print("ok  %-38s -> %s" % (rel_png, describe(dst)))


if __name__ == "__main__":
    magick = find_magick()
    if magick is None:
        print("Не найден ImageMagick.")
        print("  Windows: winget install ImageMagick.ImageMagick")
        print("  Linux:   sudo apt install imagemagick")
        print("Альтернатива от Microsoft: texconv -f BC3_UNORM <файл>.png")
        sys.exit(1)

    for rel, size in TARGETS:
        convert(magick, rel, size)
