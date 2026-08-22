#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_textures.py — подготовка иконок и store-картинок для модов FS19.

FS19 ждёт .dds:
    иконка мода    icon_*.dds    256x256
    картинка в магазин store_*.dds 1024x1024 (или 512x512)

Скрипт берёт PNG рядом и пересохраняет в DDS нужного размера.

    python3 tools/make_textures.py
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Нужен Pillow:  pip install pillow")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (путь к png, размер)
TARGETS = [
    ("FS19_FarmHelper/icon_FarmHelper.png",    256),
    ("FS19_AlphaMoped/icon_alphaMoped.png",    256),
    ("FS19_AlphaMoped/store_alphaMoped.png",   512),
]


def convert(rel_png, size):
    src = os.path.join(ROOT, rel_png)
    if not os.path.exists(src):
        print("пропуск (нет файла):", rel_png)
        return

    dst = os.path.splitext(src)[0] + ".dds"
    img = Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS)
    img.save(dst)
    print("ok  %s -> %s  (%dx%d)" % (rel_png, os.path.basename(dst), size, size))


if __name__ == "__main__":
    for rel, size in TARGETS:
        convert(rel, size)
    print("\nПримечание: Pillow пишет несжатый RGBA DDS — игра его читает.")
    print("Для магазина каноничнее BC3/DXT5: texconv -f BC3_UNORM <файл>.png")
