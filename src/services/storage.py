import os
import aiofiles
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from src.config import settings


class StorageService:
    """Сервис управления локальными медиафайлами и генерации Range-стриминга."""

    def __init__(
        self,
        audio_dir: Path = settings.AUDIO_DIR,
        covers_dir: Path = settings.COVERS_DIR,
    ):
        self.audio_dir = audio_dir
        self.covers_dir = covers_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.covers_dir.mkdir(parents=True, exist_ok=True)

    def get_audio_path(self, file_hash: str) -> Path:
        """Возвращает путь к аудиофайлу по его SHA-256 хешу."""
        return self.audio_dir / f"{file_hash}.mp3"

    def get_cover_path(self, file_hash: str) -> Path:
        """Возвращает путь к обложке по хешу."""
        return self.covers_dir / f"{file_hash}.jpg"

    def audio_exists(self, file_hash: str) -> bool:
        """Проверяет наличие файла в хранилище."""
        return self.get_audio_path(file_hash).exists()

    async def save_audio(self, file_hash: str, file_bytes: bytes) -> Path:
        """Сохраняет аудиофайл на диск."""
        path = self.get_audio_path(file_hash)
        async with aiofiles.open(path, "wb") as f:
            await f.write(file_bytes)
        return path

    async def save_cover(self, file_hash: str, cover_bytes: bytes) -> Path:
        """Сохраняет обложку на диск."""
        path = self.get_cover_path(file_hash)
        async with aiofiles.open(path, "wb") as f:
            await f.write(cover_bytes)
        return path

    @staticmethod
    def parse_range_header(
        range_header: Optional[str], file_size: int
    ) -> Optional[Tuple[int, int]]:
        """
        Парсит HTTP заголовок Range (например: 'bytes=0-1024', 'bytes=1024-').
        Возвращает (start, end).
        """
        if not range_header or not range_header.startswith("bytes="):
            return None

        range_val = range_header.replace("bytes=", "").strip()
        parts = range_val.split("-")
        if len(parts) != 2:
            return None

        start_str, end_str = parts[0].strip(), parts[1].strip()

        try:
            if start_str and end_str:
                start = int(start_str)
                end = int(end_str)
            elif start_str and not end_str:
                start = int(start_str)
                end = file_size - 1
            elif not start_str and end_str:
                # Последние N байт
                length = int(end_str)
                start = max(0, file_size - length)
                end = file_size - 1
            else:
                return None
        except ValueError:
            return None

        if start >= file_size or end >= file_size or start > end:
            return None

        return start, end

    @staticmethod
    async def file_chunk_generator(
        file_path: Path, start: int, end: int, chunk_size: int = 65536
    ) -> AsyncGenerator[bytes, None]:
        """Асинхронный генератор чанков файла в заданном диапазоне байт."""
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(start)
            bytes_left = end - start + 1
            while bytes_left > 0:
                current_chunk = min(chunk_size, bytes_left)
                data = await f.read(current_chunk)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    def create_streaming_response(
        self,
        file_path: Path,
        range_header: Optional[str] = None,
        mime_type: str = "audio/mpeg",
        as_attachment: bool = False,
        filename: Optional[str] = None,
    ) -> StreamingResponse:
        """
        Создает StreamingResponse с честной поддержкой HTTP 206 Partial Content.
        Критически важно для перемотки и потокового воспроизведения в Safari/iOS и Chrome WebView.
        """
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Аудиофайл не найден"
            )

        file_size = file_path.stat().st_size
        range_bounds = self.parse_range_header(range_header, file_size)

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": mime_type,
        }

        if as_attachment:
            safe_name = filename or file_path.name
            headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'

        if range_bounds:
            start, end = range_bounds
            content_length = end - start + 1
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(content_length)

            return StreamingResponse(
                self.file_chunk_generator(file_path, start, end),
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                headers=headers,
            )
        else:
            headers["Content-Length"] = str(file_size)
            return StreamingResponse(
                self.file_chunk_generator(file_path, 0, file_size - 1),
                status_code=status.HTTP_200_OK,
                headers=headers,
            )

    async def create_telegram_proxy_streaming_response(
        self,
        telegram_file_id: str,
        bot_token: str = settings.BOT_TOKEN,
        range_header: Optional[str] = None,
        mime_type: str = "audio/mpeg",
        as_attachment: bool = False,
        filename: Optional[str] = None,
    ) -> StreamingResponse:
        """
        Проксирует аудиопоток напрямую из серверов Telegram (api.telegram.org)
        с честной поддержкой Range (206) и буферизацией без сохранения файла на диск!
        """
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={telegram_file_id}"
        client = httpx.AsyncClient(timeout=30.0)
        try:
            resp = await client.get(get_file_url)
            if resp.status_code != 200 or not resp.json().get("ok"):
                await client.aclose()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Аудиофайл не найден на серверах Telegram",
                )
            file_path = resp.json()["result"]["file_path"]
        except HTTPException:
            raise
        except Exception as e:
            await client.aclose()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ошибка связи с Telegram: {str(e)}",
            )

        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

        tg_headers = {}
        if range_header:
            tg_headers["Range"] = range_header

        req = client.build_request("GET", download_url, headers=tg_headers)
        tg_resp = await client.send(req, stream=True)

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": mime_type,
        }
        if "content-range" in tg_resp.headers:
            resp_headers["Content-Range"] = tg_resp.headers["content-range"]
        if "content-length" in tg_resp.headers:
            resp_headers["Content-Length"] = tg_resp.headers["content-length"]
        if as_attachment:
            safe_name = filename or "track.mp3"
            resp_headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'

        async def tg_chunk_generator():
            try:
                async for chunk in tg_resp.aiter_bytes(chunk_size=65536):
                    yield chunk
            finally:
                await tg_resp.aclose()
                await client.aclose()

        return StreamingResponse(
            tg_chunk_generator(),
            status_code=tg_resp.status_code,
            headers=resp_headers,
        )


storage_service = StorageService()
