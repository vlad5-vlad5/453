#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i3d_shapes.py — чтение и запись бинарных файлов .i3d.shapes движка GIANTS.

Нужен, чтобы перенести готовую модель из мода Farming Simulator 22
(формат геометрии версии 7) в Farming Simulator 19 (версия 5).
Движок FS19 файл версии 7 просто не примет.

Это построчный перенос на Python библиотеки I3DShapesTool (C#, лицензия MIT)
Donkie: https://github.com/Donkie/I3DShapesTool
Таблица ключей шифра и порядок полей взяты оттуда же.

Модуль ничего не знает про Blender и не требует сторонних пакетов —
работает на любом Python 3.8+.

Использование:
    import i3d_shapes
    f = i3d_shapes.ShapesFile.load(open("model.i3d.shapes", "rb").read())
    print(f.version, len(f.parts))
    open("out.i3d.shapes", "wb").write(f.save(version=5))
"""

import base64
import struct
import zlib

# ----------------------------------------------------------------- шифр

# 256 ключей по 16 слов; пожато, чтобы не раздувать файл
_KEY_B64 = (
'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'
)

_KEY_TABLE = struct.unpack("<4096I", zlib.decompress(base64.b64decode(_KEY_B64)))

_MASK = 0xFFFFFFFF
CRYPT_BLOCK_SIZE = 64


def _rol(v, b):
    v &= _MASK
    return ((v << b) | (v >> (32 - b))) & _MASK


def _ror(v, b):
    v &= _MASK
    return ((v >> b) | (v << (32 - b))) & _MASK


def _shuffle1(k, a, b, c, d):
    k[c] ^= _rol((k[b] + k[a]) & _MASK, 7)
    k[d] ^= _rol((k[c] + k[a]) & _MASK, 9)
    k[b] ^= _rol((k[c] + k[d]) & _MASK, 13)
    k[a] ^= _ror((k[b] + k[d]) & _MASK, 14)


def _shuffle2(k, a, b, c, d):
    k[c] ^= _rol((k[b] + k[a]) & _MASK, 7)
    k[d] ^= _rol((k[b] + k[c]) & _MASK, 9)
    k[a] ^= _rol((k[c] + k[d]) & _MASK, 13)
    k[b] ^= _ror((k[d] + k[a]) & _MASK, 14)


class Cipher(object):
    """Поточный шифр GIANTS. Каждый вызов process() начинается с новой
    64-байтовой границы — именно так работает оригинал, и от этого
    зависит результат, поэтому размеры чтений повторяем один в один."""

    def __init__(self, seed):
        start = seed << 4
        self.key = list(_KEY_TABLE[start:start + 16])
        self.key[8] = 0
        self.key[9] = 0

    def process(self, data, block_index):
        pad = (-len(data)) % CRYPT_BLOCK_SIZE
        buf = bytearray(data) + bytes(pad)
        words = list(struct.unpack("<%dI" % (len(buf) // 4), bytes(buf)))

        key = list(self.key)
        key[8] = block_index & _MASK
        key[9] = (block_index >> 32) & _MASK
        counter = block_index

        for i in range(0, len(words), 16):
            tmp = list(key)
            for _ in range(10):
                _shuffle1(tmp, 0x0, 0xC, 0x4, 0x8)
                _shuffle1(tmp, 0x5, 0x1, 0x9, 0xD)
                _shuffle1(tmp, 0xA, 0x6, 0xE, 0x2)
                _shuffle1(tmp, 0xF, 0xB, 0x3, 0x7)
                _shuffle2(tmp, 0x3, 0x0, 0x1, 0x2)
                _shuffle2(tmp, 0x4, 0x5, 0x6, 0x7)
                _shuffle1(tmp, 0xA, 0x9, 0xB, 0x8)
                _shuffle2(tmp, 0xE, 0xF, 0xC, 0xD)
            for j in range(16):
                words[i + j] ^= (key[j] + tmp[j]) & _MASK
                words[i + j] &= _MASK

            counter += 1
            key[8] = counter & _MASK
            key[9] = (counter >> 32) & _MASK

        out = struct.pack("<%dI" % len(words), *words)
        return out[:len(data)], block_index + len(buf) // CRYPT_BLOCK_SIZE


# --- быстрый вариант того же самого ------------------------------------
# Раскручиваем перемешивание в явные выражения над локальными переменными:
# на модели в несколько мегабайт разница в скорости примерно десятикратная.

def _gen_round_source():
    lines = []

    def rol(expr, b):
        return "((({e}) << {b} | ({e}) >> {r}) & M)".format(e=expr, b=b, r=32 - b)

    def ror(expr, b):
        return "((({e}) >> {b} | ({e}) << {r}) & M)".format(e=expr, b=b, r=32 - b)

    def sh1(a, b_, c, d):
        lines.append("    t{c} ^= {x}".format(c=c, x=rol("t%d + t%d & M" % (b_, a), 7)))
        lines.append("    t{d} ^= {x}".format(d=d, x=rol("t%d + t%d & M" % (c, a), 9)))
        lines.append("    t{b} ^= {x}".format(b=b_, x=rol("t%d + t%d & M" % (c, d), 13)))
        lines.append("    t{a} ^= {x}".format(a=a, x=ror("t%d + t%d & M" % (b_, d), 14)))

    def sh2(a, b_, c, d):
        lines.append("    t{c} ^= {x}".format(c=c, x=rol("t%d + t%d & M" % (b_, a), 7)))
        lines.append("    t{d} ^= {x}".format(d=d, x=rol("t%d + t%d & M" % (b_, c), 9)))
        lines.append("    t{a} ^= {x}".format(a=a, x=rol("t%d + t%d & M" % (c, d), 13)))
        lines.append("    t{b} ^= {x}".format(b=b_, x=ror("t%d + t%d & M" % (d, a), 14)))

    for _ in range(10):
        sh1(0x0, 0xC, 0x4, 0x8)
        sh1(0x5, 0x1, 0x9, 0xD)
        sh1(0xA, 0x6, 0xE, 0x2)
        sh1(0xF, 0xB, 0x3, 0x7)
        sh2(0x3, 0x0, 0x1, 0x2)
        sh2(0x4, 0x5, 0x6, 0x7)
        sh1(0xA, 0x9, 0xB, 0x8)
        sh2(0xE, 0xF, 0xC, 0xD)

    args = ", ".join("k%d" % i for i in range(16))
    head = ["def _keystream(%s):" % args,
            "    M = 0xFFFFFFFF",
            "    " + "; ".join("t%d = k%d" % (i, i) for i in range(16))]
    tail = ["    return (" + ", ".join("k%d + t%d & M" % (i, i)
                                       for i in range(16)) + ")"]
    return "\n".join(head + lines + tail)


_ns = {}
exec(compile(_gen_round_source(), "<i3d_keystream>", "exec"), _ns)
_keystream = _ns["_keystream"]


class FastCipher(Cipher):
    def process(self, data, block_index):
        want = len(data)
        pad = (-want) % CRYPT_BLOCK_SIZE
        if pad:
            data = bytes(data) + bytes(pad)
        n = len(data) // 4
        words = list(struct.unpack("<%dI" % n, bytes(data)))

        key = self.key
        k = list(key)
        counter = block_index
        M = _MASK

        for i in range(0, n, 16):
            k[8] = counter & M
            k[9] = (counter >> 32) & M
            ks = _keystream(*k)
            for j in range(16):
                words[i + j] ^= ks[j]
            counter += 1

        out = struct.pack("<%dI" % n, *words)
        return out[:want], block_index + n // 16


# везде пользуемся быстрым вариантом; медленный оставлен как эталон для сверки
Cipher_reference = Cipher
Cipher = FastCipher


class CipherReader(object):
    """Читает зашифрованный поток. ВАЖНО: расшифровка зависит от того,
    какими порциями читают, поэтому размеры чтений повторяют оригинал."""

    def __init__(self, data, seed, offset=0):
        self.data = data
        self.pos = offset
        self.cipher = Cipher(seed)
        self.block = 0

    def read(self, n):
        chunk = self.data[self.pos:self.pos + n]
        if len(chunk) < n:
            raise EOFError("файл кончился раньше времени")
        self.pos += n
        plain, self.block = self.cipher.process(chunk, self.block)
        return plain

    def i32(self):
        return struct.unpack("<i", self.read(4))[0]


class CipherWriter(object):
    def __init__(self, seed):
        self.cipher = Cipher(seed)
        self.block = 0
        self.parts = []

    def write(self, data):
        enc, self.block = self.cipher.process(data, self.block)
        self.parts.append(enc)

    def i32(self, v):
        self.write(struct.pack("<i", v))

    def getvalue(self):
        return b"".join(self.parts)


# ----------------------------------------------------------------- буферы

class Buf(object):
    """Чтение уже расшифрованных данных одной сущности."""

    def __init__(self, data):
        self.d = data
        self.p = 0

    def raw(self, n):
        if self.p + n > len(self.d):
            raise EOFError("выход за границу данных сущности")
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def u32(self):
        return struct.unpack("<I", self.raw(4))[0]

    def i32(self):
        return struct.unpack("<i", self.raw(4))[0]

    def u16(self):
        return struct.unpack("<H", self.raw(2))[0]

    def u8(self):
        return struct.unpack("<B", self.raw(1))[0]

    def f32(self):
        return struct.unpack("<f", self.raw(4))[0]

    def vec3(self):
        return struct.unpack("<3f", self.raw(12))

    def vec4(self):
        return struct.unpack("<4f", self.raw(16))

    def align(self, n=4):
        mod = self.p % n
        if mod:
            self.raw(n - mod)

    def done(self):
        return self.p == len(self.d)


class OutBuf(object):
    def __init__(self):
        self.parts = []
        self.n = 0

    def raw(self, b):
        self.parts.append(b)
        self.n += len(b)

    def u32(self, v):
        self.raw(struct.pack("<I", v & 0xFFFFFFFF))

    def i32(self, v):
        self.raw(struct.pack("<i", v))

    def u16(self, v):
        self.raw(struct.pack("<H", v))

    def u8(self, v):
        self.raw(struct.pack("<B", v))

    def f32(self, v):
        self.raw(struct.pack("<f", v))

    def vec3(self, v):
        self.raw(struct.pack("<3f", *v))

    def vec4(self, v):
        self.raw(struct.pack("<4f", *v))

    def align(self, n=4):
        mod = self.n % n
        if mod:
            self.raw(bytes(n - mod))

    def getvalue(self):
        return b"".join(self.parts)


# ----------------------------------------------------------------- флаги

OPT_NORMALS = 0b0000000001
OPT_UV1     = 0b0000000010
OPT_UV2     = 0b0000000100
OPT_UV3     = 0b0000001000
OPT_UV4     = 0b0000010000
OPT_COLOR   = 0b0000100000
OPT_SKIN    = 0b0001000000
OPT_TANGENT = 0b0010000000
OPT_SINGLEW = 0b0100000000
OPT_GENERIC = 0b1000000000
OPT_ALL     = 0b1111111111

VERSION_WITH_TANGENTS = 5


class Part(object):
    """Одна сущность файла: имя, номер и содержимое."""

    def __init__(self, etype, name, ident, data=None):
        self.etype = etype          # 1 = меш, 2 = сплайн
        self.name = name
        self.id = ident
        self.raw_contents = data    # если тип не разобран — сырые байты

        self.bounding = (0.0, 0.0, 0.0, 0.0)
        self.subsets = []
        self.triangles = []
        self.positions = []
        self.normals = None
        self.tangents = None
        self.uvs = [None, None, None, None]
        self.colors = None
        self.blend_weights = None
        self.blend_indices = None
        self.generic = None
        self.attachments = []
        self.options_high = 0
        self.parsed = False

    # -------------------------------------------------------------- чтение

    @classmethod
    def read(cls, etype, data, version):
        b = Buf(data)
        name_len = b.i32()
        name = b.raw(name_len).decode("ascii", "replace")
        b.align(4)
        ident = b.u32()

        part = cls(etype, name, ident)
        if etype != 1:
            part.raw_contents = data[b.p:]
            return part

        part._read_shape(b, version)
        part.parsed = True
        return part

    def _read_shape(self, b, version):
        self.bounding = b.vec4()
        corner_count = b.u32()
        num_subsets = b.u32()
        vertex_count = b.u32()
        options = b.u32()
        self.options_high = options & ~OPT_ALL

        for _ in range(num_subsets):
            s = {"firstVertex": b.u32(), "numVertices": b.u32(),
                 "firstIndex": b.u32(), "numIndices": b.u32(),
                 "uvDensity": []}
            if version >= 6:
                for flag in (OPT_UV1, OPT_UV2, OPT_UV3, OPT_UV4):
                    if options & flag:
                        s["uvDensity"].append(b.f32())
            self.subsets.append(s)

        big = vertex_count > 65536
        for _ in range(corner_count // 3):
            if big:
                self.triangles.append((b.u32(), b.u32(), b.u32()))
            else:
                self.triangles.append((b.u16(), b.u16(), b.u16()))
        b.align(4)

        self.positions = [b.vec3() for _ in range(vertex_count)]

        if options & OPT_NORMALS:
            self.normals = [b.vec3() for _ in range(vertex_count)]

        if options & OPT_TANGENT:
            if version >= VERSION_WITH_TANGENTS:
                self.tangents = [b.vec4() for _ in range(vertex_count)]
            else:
                self.options_high |= OPT_TANGENT

        for i, flag in enumerate((OPT_UV1, OPT_UV2, OPT_UV3, OPT_UV4)):
            if options & flag:
                uvs = []
                for _ in range(vertex_count):
                    a, c = b.f32(), b.f32()
                    # в версиях 4 и 5 порядок перевёрнут: сначала V, потом U
                    uvs.append((c, a) if 4 <= version <= 5 else (a, c))
                self.uvs[i] = uvs

        if options & OPT_COLOR:
            self.colors = [b.vec4() for _ in range(vertex_count)]

        if options & OPT_SKIN:
            single = bool(options & OPT_SINGLEW)
            if not single:
                self.blend_weights = [[b.f32() for _ in range(4)]
                                      for _ in range(vertex_count)]
            cnt = 1 if single else 4
            self.blend_indices = [[b.u8() for _ in range(cnt)]
                                  for _ in range(vertex_count)]

        if options & OPT_GENERIC:
            self.generic = [b.f32() for _ in range(vertex_count)]

        num_att = b.u32()
        for _ in range(num_att):
            flags = b.u32()
            floats = [b.f32() for _ in range(3)] if flags & 4 else None
            nb = b.i32()
            self.attachments.append((flags, floats, b.raw(nb)))

        if not b.done():
            raise ValueError("остались непрочитанные байты (%d из %d)"
                             % (b.p, len(b.d)))

    # -------------------------------------------------------------- запись

    @property
    def options(self):
        o = 0
        if self.normals is not None:
            o |= OPT_NORMALS
        for i, flag in enumerate((OPT_UV1, OPT_UV2, OPT_UV3, OPT_UV4)):
            if self.uvs[i] is not None:
                o |= flag
        if self.colors is not None:
            o |= OPT_COLOR
        if self.blend_indices is not None:
            o |= OPT_SKIN
        if self.blend_indices is not None and self.blend_weights is None:
            o |= OPT_SINGLEW
        if self.generic is not None:
            o |= OPT_GENERIC
        if self.tangents is not None:
            o |= OPT_TANGENT
        return o | self.options_high

    def write(self, version):
        o = OutBuf()
        name = self.name.encode("ascii", "replace")
        o.i32(len(name))
        o.raw(name)
        o.align(4)
        o.u32(self.id)

        if not self.parsed:
            o.raw(self.raw_contents or b"")
            return o.getvalue()

        options = self.options
        vertex_count = len(self.positions)

        o.vec4(self.bounding)
        o.u32(len(self.triangles) * 3)
        o.u32(len(self.subsets))
        o.u32(vertex_count)
        o.u32(options)

        for s in self.subsets:
            o.u32(s["firstVertex"])
            o.u32(s["numVertices"])
            o.u32(s["firstIndex"])
            o.u32(s["numIndices"])
            if version >= 6:
                dens = s.get("uvDensity") or []
                need = sum(1 for f in (OPT_UV1, OPT_UV2, OPT_UV3, OPT_UV4)
                           if options & f)
                for i in range(need):
                    o.f32(dens[i] if i < len(dens) else 1.0)

        big = vertex_count > 65536
        for t in self.triangles:
            for idx in t:
                o.u32(idx) if big else o.u16(idx)
        o.align(4)

        for p in self.positions:
            o.vec3(p)

        if self.normals is not None:
            for n in self.normals:
                o.vec3(n)

        if self.tangents is not None:
            if version < VERSION_WITH_TANGENTS:
                raise ValueError("версия %d не умеет хранить тангенты" % version)
            for t in self.tangents:
                o.vec4(t)

        for i in range(4):
            if self.uvs[i] is None:
                continue
            for u, v in self.uvs[i]:
                if 4 <= version <= 5:
                    o.f32(v)
                    o.f32(u)
                else:
                    o.f32(u)
                    o.f32(v)

        if self.colors is not None:
            for c in self.colors:
                o.vec4(c)

        if self.blend_indices is not None:
            if self.blend_weights is not None:
                for w in self.blend_weights:
                    for x in w:
                        o.f32(x)
            for bi in self.blend_indices:
                for x in bi:
                    o.u8(x)

        if self.generic is not None:
            for g in self.generic:
                o.f32(g)

        o.u32(len(self.attachments))
        for flags, floats, data in self.attachments:
            o.u32(flags)
            if floats:
                for f in floats:
                    o.f32(f)
            o.i32(len(data))
            o.raw(data)

        return o.getvalue()


class ShapesFile(object):
    def __init__(self, version, seed, parts):
        self.version = version
        self.seed = seed
        self.parts = parts

    # -------------------------------------------------------------- загрузка

    @staticmethod
    def read_header(data):
        b1, b2, b3, b4 = data[0], data[1], data[2], data[3]
        if b1 >= 4:
            return b1, b3
        if b4 in (2, 3):
            return b4, b2
        raise ValueError("неизвестная версия файла геометрии")

    @classmethod
    def load(cls, data, strict=False):
        version, seed = cls.read_header(data)
        if version < 2 or version > 7:
            raise ValueError("версия %d не поддерживается" % version)

        r = CipherReader(data, seed, offset=4)
        count = r.i32()
        if count < 0 or count > 1000000:
            raise ValueError("расшифровка не удалась: сущностей %d" % count)

        parts = []
        for i in range(count):
            etype = r.i32()
            size = r.i32()
            raw = r.read(size)
            try:
                parts.append(Part.read(etype, raw, version))
            except Exception as exc:
                if strict:
                    raise
                p = Part(etype, "<не разобрано #%d>" % i, 0, raw)
                p.error = str(exc)
                parts.append(p)
        return cls(version, seed, parts)

    # -------------------------------------------------------------- запись

    def save(self, version=None, seed=None):
        version = self.version if version is None else version
        seed = self.seed if seed is None else seed

        out = bytearray()
        out.append(version)
        out.append(0)
        out.append(seed)
        out.append(0)

        w = CipherWriter(seed)
        w.i32(len(self.parts))
        for p in self.parts:
            body = p.write(version)
            w.i32(p.etype)
            w.i32(len(body))
            w.write(body)

        return bytes(out) + w.getvalue()

    def summary(self):
        lines = []
        for p in self.parts:
            if p.parsed:
                lines.append("  #%-4d %-28s вершин %-6d треуг. %-6d частей %d"
                             % (p.id, p.name[:28], len(p.positions),
                                len(p.triangles), len(p.subsets)))
            else:
                lines.append("  #%-4d %-28s тип %s, не разобрано %s"
                             % (p.id, p.name[:28], p.etype,
                                getattr(p, "error", "")))
        return "\n".join(lines)
