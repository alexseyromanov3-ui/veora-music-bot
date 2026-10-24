import hashlib
import pytest
from pathlib import Path
from src.services.audio_metadata import AudioMetadataService


def test_calculate_sha256(tmp_path: Path) -> None:
    data = b"hello music world"
    test_file = tmp_path / "sample.txt"
    test_file.write_bytes(data)
    expected_hash = hashlib.sha256(data).hexdigest()
    file_hash = AudioMetadataService.calculate_sha256(test_file)
    assert len(file_hash) == 64
    assert file_hash == expected_hash


def test_extract_metadata_fallback_filename(tmp_path: Path) -> None:
    # Создаем файл без валидных ID3 тегов, проверяем умный fallback по имени файла
    dummy_file = tmp_path / "Queen - Bohemian Rhapsody.mp3"
    dummy_file.write_bytes(b"NOT_A_REAL_MP3_STREAM_1234567890")

    metadata = AudioMetadataService.extract_metadata(dummy_file)
    assert metadata.artist == "Queen"
    assert metadata.title == "Bohemian Rhapsody"
    assert metadata.file_size == len(b"NOT_A_REAL_MP3_STREAM_1234567890")
    assert metadata.file_hash is not None


def test_extract_metadata_simple_filename(tmp_path: Path) -> None:
    dummy_file = tmp_path / "track_without_artist.mp3"
    dummy_file.write_bytes(b"DUMMY_DATA")

    metadata = AudioMetadataService.extract_metadata(dummy_file)
    assert metadata.artist == "Unknown Artist"
    assert metadata.title == "track_without_artist"
