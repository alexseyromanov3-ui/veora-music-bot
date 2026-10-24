import hashlib
import io
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import mutagen
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4


@dataclass
class ParsedAudioMetadata:
    """Извлеченные метаданные аудиофайла."""
    title: str
    artist: str
    album: Optional[str]
    duration: int  # в секундах
    bit_rate: Optional[int]  # в kbps
    file_size: int
    file_hash: str
    mime_type: str
    cover_bytes: Optional[bytes] = None
    cover_mime: Optional[str] = None


class AudioMetadataService:
    """Сервис для безопасного чтения, проверки и извлечения метаданных аудио."""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Вычисляет SHA-256 хеш файла по блокам."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def extract_metadata(
        file_path: Path, fallback_filename: Optional[str] = None
    ) -> ParsedAudioMetadata:
        """
        Извлекает ID3/Vorbis/MP4 теги, длительность, битрейт и обложку.
        Если теги отсутствуют или повреждены, используются безопасные значения по умолчанию.
        """
        file_size = file_path.stat().st_size
        file_hash = AudioMetadataService.calculate_sha256(file_path)

        # Определение базового названия из имени файла на случай отсутствия тегов
        base_name = fallback_filename or file_path.stem
        # Если имя вида "Artist - Title", пытаемся предварительно распарсить
        default_artist = "Unknown Artist"
        default_title = base_name
        if " - " in base_name:
            parts = base_name.split(" - ", 1)
            default_artist = parts[0].strip() or "Unknown Artist"
            default_title = parts[1].strip() or base_name

        try:
            audio_file = mutagen.File(str(file_path))
        except Exception:
            audio_file = None

        if audio_file is None:
            # Файл может быть не распознан mutagen, возвращаем базовые данные
            return ParsedAudioMetadata(
                title=default_title,
                artist=default_artist,
                album=None,
                duration=0,
                bit_rate=None,
                file_size=file_size,
                file_hash=file_hash,
                mime_type="audio/mpeg",
                cover_bytes=None,
            )

        duration = 0
        bit_rate = None
        mime_type = "audio/mpeg"

        if hasattr(audio_file, "info") and audio_file.info is not None:
            duration = int(round(getattr(audio_file.info, "length", 0)))
            if hasattr(audio_file.info, "bitrate") and audio_file.info.bitrate:
                bit_rate = int(audio_file.info.bitrate // 1000)

        title = default_title
        artist = default_artist
        album = None
        cover_bytes = None
        cover_mime = None

        # Обработка MP3 с ID3
        if isinstance(audio_file, MP3) or hasattr(audio_file, "tags"):
            tags = audio_file.tags
            if tags:
                # Извлечение названия
                for key in ["TIT2", "title", "\xa9nam"]:
                    if key in tags and tags[key]:
                        val = str(tags[key][0]).strip()
                        if val:
                            title = val
                            break

                # Извлечение исполнителя
                for key in ["TPE1", "artist", "\xa9ART"]:
                    if key in tags and tags[key]:
                        val = str(tags[key][0]).strip()
                        if val:
                            artist = val
                            break

                # Извлечение альбома
                for key in ["TALB", "album", "\xa9alb"]:
                    if key in tags and tags[key]:
                        val = str(tags[key][0]).strip()
                        if val:
                            album = val
                            break

                # Извлечение обложки (APIC в ID3)
                if isinstance(tags, ID3):
                    for tag in tags.values():
                        if isinstance(tag, APIC):
                            cover_bytes = tag.data
                            cover_mime = tag.mime or "image/jpeg"
                            break

        # Обработка FLAC
        elif isinstance(audio_file, FLAC):
            mime_type = "audio/flac"
            if audio_file.pictures:
                cover_bytes = audio_file.pictures[0].data
                cover_mime = audio_file.pictures[0].mime

        # Обработка M4A / MP4
        elif isinstance(audio_file, MP4):
            mime_type = "audio/mp4"
            if audio_file.tags and "covr" in audio_file.tags:
                covers = audio_file.tags["covr"]
                if covers:
                    cover_bytes = bytes(covers[0])
                    cover_mime = "image/jpeg"

        return ParsedAudioMetadata(
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            bit_rate=bit_rate,
            file_size=file_size,
            file_hash=file_hash,
            mime_type=mime_type,
            cover_bytes=cover_bytes,
            cover_mime=cover_mime,
        )
