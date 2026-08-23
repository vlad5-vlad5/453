#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Самопроверка i3d_shapes.py: шифр и структуры, без реальных файлов игры."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i3d_shapes as m  # noqa: E402


def check_cipher():
    random.seed(3)
    for n in (1, 4, 7, 63, 64, 65, 200, 4096):
        data = bytes(random.getrandbits(8) for _ in range(n))
        for block in (0, 1, 5):
            a, x = m.Cipher_reference(0x2D).process(data, block)
            b, y = m.FastCipher(0x2D).process(data, block)
            assert a == b and x == y and len(b) == n, (n, block)
    print("шифр: быстрый вариант совпадает с эталонным")


def make_part(name, ident, nv):
    random.seed(nv)
    p = m.Part(1, name, ident)
    p.bounding = (0.0, 0.0, 0.0, 1.0)
    p.positions = [(random.random(), random.random(), random.random())
                   for _ in range(nv)]
    p.normals = [(0.0, 1.0, 0.0)] * nv
    p.tangents = [(1.0, 0.0, 0.0, 1.0)] * nv
    p.uvs[0] = [(random.random(), random.random()) for _ in range(nv)]
    p.triangles = [(i % nv, (i + 1) % nv, (i + 2) % nv) for i in range(1000)]
    p.subsets = [{"firstVertex": 0, "numVertices": nv, "firstIndex": 0,
                  "numIndices": 3000, "uvDensity": [1.0]}]
    p.attachments = [(0, None, b"xy")]
    p.parsed = True
    return p


def check_roundtrip():
    for nv in (500, 70000):          # 16-битные и 32-битные индексы
        orig = m.ShapesFile(7, 0x2D, [make_part("a", 1, nv),
                                      make_part("b", 2, nv)])
        again = m.ShapesFile.load(orig.save(), strict=True)
        v5 = m.ShapesFile.load(again.save(version=5), strict=True)

        assert v5.version == 5
        assert v5.parts[0].triangles == orig.parts[0].triangles
        assert len(v5.parts[0].positions) == nv
        assert all(abs(x - y) < 1e-6
                   for A, B in zip(orig.parts[0].uvs[0], v5.parts[0].uvs[0])
                   for x, y in zip(A, B)), "перепутан порядок U и V в версии 5"
        assert v5.parts[0].subsets[0]["uvDensity"] == []
        assert v5.parts[1].attachments[0][2] == b"xy"
        print("меш %d вершин: версия 7 -> версия 5 без потерь" % nv)


if __name__ == "__main__":
    check_cipher()
    check_roundtrip()
    print("SELF-TEST PASSED")
