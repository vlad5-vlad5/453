#!/usr/bin/env python3
"""
Генератор списка треков music_website/tracks/tracks.json.
Сканирует папки tracks/chanson, disco, deephouse, ruspop, other, подтягивает обложки
и метаданные из tracks/metadata.json.
"""

import json
import re
import wave
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TRACKS_DIR = BASE_DIR / "tracks"
METADATA_FILE = TRACKS_DIR / "metadata.json"
INDEX_FILE = TRACKS_DIR / "tracks.json"

GENRES = ("chanson", "disco", "deephouse", "ruspop", "other")
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".webm"}
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif")


def load_metadata() -> dict:
    if not METADATA_FILE.exists():
        return {}
    try:
        return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def clean_display_text(text: str) -> str:
    # Убираем технические теги вроде [sunodownloaderpro] из отображаемого названия
    cleaned = re.sub(r"\[[^\]]*\]", "", text)
    cleaned = re.sub(r"[_]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_name(stem: str) -> tuple[str, str]:
    cleaned_stem = clean_display_text(stem) or stem
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
            key=lambda p: p.name.lower(),
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
                }
            )
    return tracks


def write_index() -> list[dict]:
    tracks = scan_tracks()
    INDEX_FILE.write_text(
        json.dumps({"tracks": tracks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return tracks


if __name__ == "__main__":
    result = write_index()
    print(f"Обновлён tracks.json: треков — {len(result)}")
