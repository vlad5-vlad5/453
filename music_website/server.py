#!/usr/bin/env python3
"""
Локальный сервер для сайта «Моя Новая Музыка» (music_website).
- Автоматически сканирует папки tracks/chanson, disco, deephouse, other
- Отдаёт /api/tracks с метаданными и обложками и синхронизирует tracks/tracks.json
- Поддерживает загрузку треков (POST /api/upload) и обложек (POST /api/cover) прямо в tracks/
- Поддерживает HTTP Range-запросы для плавной перемотки аудио
"""

import base64
import json
import mimetypes
import os
import re
import time
import urllib.parse
import uuid
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TRACKS_DIR = BASE_DIR / "tracks"
METADATA_FILE = TRACKS_DIR / "metadata.json"
INDEX_FILE = TRACKS_DIR / "tracks.json"
SOCIAL_FILE = TRACKS_DIR / "social.json"

GENRES = ("chanson", "disco", "deephouse", "other")
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".webm"}
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 МБ


def load_metadata() -> dict:
    if not METADATA_FILE.exists():
        return {}
    try:
        return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_metadata(data: dict) -> None:
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_tracks_index() -> None:
    tracks = scan_tracks()
    INDEX_FILE.write_text(
        json.dumps({"tracks": tracks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_social() -> dict:
    if not SOCIAL_FILE.exists():
        return {"likes": {}, "comments": {}}
    try:
        data = json.loads(SOCIAL_FILE.read_text(encoding="utf-8"))
        return {
            "likes": data.get("likes", {}) if isinstance(data.get("likes"), dict) else {},
            "comments": data.get("comments", {}) if isinstance(data.get("comments"), dict) else {},
        }
    except Exception:
        return {"likes": {}, "comments": {}}


def save_social(data: dict) -> None:
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    SOCIAL_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sanitize_filename(name: str, fallback: str = "track") -> str:
    name = os.path.basename(name or "").strip()
    stem, ext = os.path.splitext(name)
    # Оставляем буквы (включая кириллицу), цифры, пробелы, дефисы, подчёркивания
    stem = re.sub(r"[^\w\s\-().]+", "", stem, flags=re.UNICODE).strip()
    stem = re.sub(r"\s+", "-", stem)
    if not stem:
        stem = fallback
    ext = re.sub(r"[^a-zA-Z0-9.]", "", ext).lower()
    return f"{stem}{ext}"


def format_duration(seconds: float) -> str:
    if seconds < 0:
        return "--:--"
    total = int(round(seconds))
    mins, secs = divmod(total, 60)
    return f"{mins}:{secs:02d}"


def probe_wav_duration(path: Path) -> str | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return format_duration(frames / rate)
    except Exception:
        pass
    return None


def parse_name(stem: str) -> tuple[str, str]:
    """Разбирает 'Artist - Title' и убирает теги вроде [sunodownloaderpro]."""
    cleaned_stem = re.sub(r"\[[^\]]*\]", "", stem)
    cleaned_stem = re.sub(r"[_]+", " ", cleaned_stem)
    cleaned_stem = re.sub(r"\s+", " ", cleaned_stem).strip() or stem
    if " - " in cleaned_stem:
        artist, title = cleaned_stem.split(" - ", 1)
        return artist.strip() or "Неизвестный исполнитель", title.strip() or cleaned_stem
    title = cleaned_stem[:1].upper() + cleaned_stem[1:] if cleaned_stem else stem
    return "Моя коллекция", title


def find_matching_cover(audio_path: Path) -> str | None:
    for ext in IMAGE_EXTS:
        candidate = audio_path.with_suffix(ext)
        if candidate.exists():
            return candidate.relative_to(BASE_DIR).as_posix()
    return None


def scan_tracks() -> list[dict]:
    meta = load_metadata()
    tracks = []

    for genre in GENRES:
        folder = TRACKS_DIR / genre
        folder.mkdir(parents=True, exist_ok=True)
        files = sorted(
            (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for audio_path in files:
            rel_path = audio_path.relative_to(BASE_DIR).as_posix()
            entry = meta.get(rel_path, {})
            inferred_artist, inferred_title = parse_name(audio_path.stem)

            cover = entry.get("cover")
            if cover and not (BASE_DIR / cover).exists():
                cover = None
            if not cover:
                cover = find_matching_cover(audio_path)

            duration = entry.get("duration") or probe_wav_duration(audio_path)

            tracks.append(
                {
                    "id": rel_path,
                    "title": entry.get("title") or inferred_title,
                    "artist": entry.get("artist") or inferred_artist,
                    "genre": genre,
                    "src": rel_path,
                    "cover": cover,
                    "duration": duration or "--:--",
                    "size": audio_path.stat().st_size,
                }
            )
    return tracks


def unique_path(folder: Path, filename: str) -> Path:
    target = folder / filename
    if not target.exists():
        return target
    stem, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = folder / f"{stem}-{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def decode_data_url_or_b64(value: str) -> bytes:
    if "," in value and value.startswith("data:"):
        value = value.split(",", 1)[1]
    return base64.b64decode(value)


class MusicRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        # Компактные логи сервера
        print(f"[server] {self.address_string()} - {format % args}", flush=True)

    def send_json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            self.send_json(413, {"error": "Файл слишком большой или пустой запрос."})
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_json(400, {"error": "Некорректный JSON."})
            return None

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/tracks":
            tracks = scan_tracks()
            self.send_json(200, {"tracks": tracks, "serverMode": True})
            return
        if parsed.path == "/api/social":
            self.send_json(200, load_social())
            return

        # Обработка HTTP Range для плавной перемотки аудио
        range_header = self.headers.get("Range")
        if range_header and not parsed.path.startswith("/api/"):
            fs_path = Path(self.translate_path(self.path))
            if fs_path.is_file():
                self.serve_range_file(fs_path, range_header)
                return

        super().do_GET()

    def serve_range_file(self, fs_path: Path, range_header: str) -> None:
        file_size = fs_path.stat().st_size
        match = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match:
            super().do_GET()
            return

        start_s, end_s = match.groups()
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
        if start >= file_size:
            self.send_error(416, "Requested Range Not Satisfiable")
            return
        end = min(end, file_size - 1)
        length = end - start + 1

        ctype, _ = mimetypes.guess_type(str(fs_path))
        self.send_response(206)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()

        with open(fs_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/upload":
            self.handle_upload()
            return
        if parsed.path == "/api/cover":
            self.handle_cover_update()
            return
        if parsed.path == "/api/like":
            self.handle_like()
            return
        if parsed.path == "/api/comments":
            self.handle_add_comment()
            return
        if parsed.path == "/api/comments/delete":
            self.handle_delete_comment()
            return
        if parsed.path == "/api/delete-track":
            self.handle_delete_track()
            return
        self.send_json(404, {"error": "Маршрут не найден."})

    def handle_like(self) -> None:
        data = self.read_json_body()
        if data is None:
            return
        track_id = str(data.get("trackId", "")).strip()
        delta = 1 if int(data.get("delta", 0)) >= 0 else -1
        if not track_id:
            self.send_json(400, {"error": "Не указан трек."})
            return
        social = load_social()
        current = int(social["likes"].get(track_id, 0))
        new_val = max(0, current + delta)
        social["likes"][track_id] = new_val
        save_social(social)
        self.send_json(200, {"trackId": track_id, "likes": new_val})

    def handle_add_comment(self) -> None:
        data = self.read_json_body()
        if data is None:
            return
        track_id = str(data.get("trackId", "")).strip()
        author = str(data.get("author", "")).strip()[:40] or "Гость"
        text = str(data.get("text", "")).strip()[:500]
        client_id = str(data.get("clientId", "")).strip()[:64]
        if not track_id or not text:
            self.send_json(400, {"error": "Введите текст комментария."})
            return
        comment = {
            "id": uuid.uuid4().hex[:12],
            "author": author,
            "text": text,
            "createdAt": int(time.time() * 1000),
            "clientId": client_id,
        }
        social = load_social()
        social["comments"].setdefault(track_id, []).insert(0, comment)
        save_social(social)
        self.send_json(201, {"comment": comment})

    def handle_delete_comment(self) -> None:
        data = self.read_json_body()
        if data is None:
            return
        track_id = str(data.get("trackId", "")).strip()
        comment_id = str(data.get("commentId", "")).strip()
        client_id = str(data.get("clientId", "")).strip()
        if not track_id or not comment_id:
            self.send_json(400, {"error": "Недостаточно данных."})
            return
        social = load_social()
        items = social["comments"].get(track_id, [])
        social["comments"][track_id] = [
            c for c in items if not (c.get("id") == comment_id and (not c.get("clientId") or c.get("clientId") == client_id))
        ]
        save_social(social)
        self.send_json(200, {"ok": True})

    def handle_delete_track(self) -> None:
        """Удаляет файл трека (и парную обложку) с диска и обновляет tracks.json."""
        data = self.read_json_body()
        if data is None:
            return

        track_id = str(data.get("trackId", "")).strip()
        if not track_id:
            self.send_json(400, {"error": "Не указан трек."})
            return

        # Разрешаем только пути внутри music_website/tracks/<жанр>/<файл>
        try:
            rel = urllib.parse.unquote(track_id).replace("\\", "/")
            if rel.startswith("music_website/"):
                rel = rel[len("music_website/"):]
            candidate = (BASE_DIR / rel).resolve()
            tracks_root = TRACKS_DIR.resolve()
            if tracks_root not in candidate.parents and candidate != tracks_root:
                self.send_json(403, {"error": "Путь вне папки треков."})
                return
            if candidate.suffix.lower() not in AUDIO_EXTS:
                self.send_json(400, {"error": "Это не аудиофайл."})
                return
            if not candidate.is_file():
                self.send_json(404, {"error": "Файл не найден — возможно, уже удалён."})
                return
        except Exception:
            self.send_json(400, {"error": "Некорректный путь трека."})
            return

        try:
            candidate.unlink()
        except Exception as exc:  # noqa: BLE001
            self.send_json(500, {"error": f"Не удалось удалить файл: {exc}"})
            return

        # Обложка с тем же именем (cover.jpg / <stem>.jpg)
        stem = candidate.stem
        for img in IMAGE_EXTS:
            for name in (f"{stem}{img}", f"cover{img}"):
                cover_path = candidate.parent / name
                if cover_path.is_file():
                    try:
                        cover_path.unlink()
                    except Exception:
                        pass

        # Чистим метаданные и пересобираем индекс
        meta = load_metadata()
        removed_keys = [k for k in meta if k == rel or k.endswith("/" + candidate.name)]
        for key in removed_keys:
            meta.pop(key, None)
        if removed_keys:
            save_metadata(meta)

        try:
            sync_tracks_index()
        except Exception:
            pass

        self.send_json(200, {"ok": True, "deleted": rel})

    def handle_upload(self) -> None:
        data = self.read_json_body()
        if data is None:
            return

        genre = data.get("genre", "")
        if genre not in GENRES:
            self.send_json(400, {"error": "Неверный жанр."})
            return

        filename = sanitize_filename(data.get("filename", ""), fallback="track")
        ext = Path(filename).suffix.lower()
        if ext not in AUDIO_EXTS:
            self.send_json(400, {"error": f"Неподдерживаемый формат аудио: {ext or 'без расширения'}"})
            return

        audio_b64 = data.get("audioBase64")
        if not audio_b64:
            self.send_json(400, {"error": "Отсутствуют данные аудиофайла."})
            return

        try:
            audio_bytes = decode_data_url_or_b64(audio_b64)
        except Exception:
            self.send_json(400, {"error": "Ошибка декодирования аудио."})
            return

        folder = TRACKS_DIR / genre
        folder.mkdir(parents=True, exist_ok=True)
        audio_path = unique_path(folder, filename)
        audio_path.write_bytes(audio_bytes)
        rel_audio = audio_path.relative_to(BASE_DIR).as_posix()

        cover_rel = None
        cover_b64 = data.get("coverBase64")
        cover_filename = data.get("coverFilename")
        if cover_b64 and cover_filename:
            c_ext = Path(sanitize_filename(cover_filename, "cover")).suffix.lower()
            if c_ext in IMAGE_EXTS:
                try:
                    cover_bytes = decode_data_url_or_b64(cover_b64)
                    cover_path = audio_path.with_suffix(c_ext)
                    cover_path.write_bytes(cover_bytes)
                    cover_rel = cover_path.relative_to(BASE_DIR).as_posix()
                except Exception:
                    pass

        title = (data.get("title") or "").strip()
        artist = (data.get("artist") or "").strip()
        inferred_artist, inferred_title = parse_name(audio_path.stem)

        meta = load_metadata()
        meta[rel_audio] = {
            "title": title or inferred_title,
            "artist": artist or inferred_artist,
            **({"cover": cover_rel} if cover_rel else {}),
        }
        save_metadata(meta)
        sync_tracks_index()

        self.send_json(
            201,
            {
                "track": {
                    "id": rel_audio,
                    "title": meta[rel_audio]["title"],
                    "artist": meta[rel_audio]["artist"],
                    "genre": genre,
                    "src": rel_audio,
                    "cover": cover_rel,
                    "duration": probe_wav_duration(audio_path) or "--:--",
                }
            },
        )

    def handle_cover_update(self) -> None:
        data = self.read_json_body()
        if data is None:
            return

        track_id = data.get("trackId", "")
        cover_b64 = data.get("coverBase64", "")
        cover_filename = data.get("coverFilename", "cover.png")

        target_audio = (BASE_DIR / track_id).resolve()
        try:
            target_audio.relative_to(TRACKS_DIR.resolve())
        except ValueError:
            self.send_json(400, {"error": "Недопустимый путь трека."})
            return

        if not target_audio.is_file():
            self.send_json(404, {"error": "Трек не найден на диске."})
            return

        c_ext = Path(sanitize_filename(cover_filename, "cover.png")).suffix.lower()
        if c_ext not in IMAGE_EXTS:
            self.send_json(400, {"error": "Поддерживаются JPG, PNG, WEBP, SVG, GIF."})
            return

        try:
            cover_bytes = decode_data_url_or_b64(cover_b64)
        except Exception:
            self.send_json(400, {"error": "Ошибка декодирования изображения."})
            return

        cover_path = target_audio.with_suffix(c_ext)
        cover_path.write_bytes(cover_bytes)
        rel_cover = cover_path.relative_to(BASE_DIR).as_posix()

        meta = load_metadata()
        entry = meta.get(track_id, {})
        entry["cover"] = rel_cover
        meta[track_id] = entry
        save_metadata(meta)
        sync_tracks_index()

        self.send_json(200, {"cover": rel_cover})


def main():
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", port), MusicRequestHandler)
    print(f"Сервер «Моя Новая Музыка» запущен на http://0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
