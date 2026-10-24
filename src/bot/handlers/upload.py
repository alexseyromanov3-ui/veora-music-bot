import io
from aiogram import Bot, F, Router
from aiogram.types import Message
from src.bot.handlers.common import get_player_keyboard
from src.config import settings
from src.database.session import AsyncSessionLocal
from src.services.track_service import track_service

router = Router(name="upload_router")

SUPPORTED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/x-mp3",
    "audio/ogg",
    "audio/flac",
    "audio/x-m4a",
    "audio/mp4",
    "audio/wav",
}


def format_duration(seconds: int) -> str:
    """Форматирует секунды в mm:ss."""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


@router.message(F.audio)
async def handle_audio_message(message: Message, bot: Bot) -> None:
    """Обработчик аудиофайлов, отправленных стандартным способом (F.audio)."""
    audio = message.audio
    if not audio:
        return

    # Проверка размера
    if audio.file_size and audio.file_size > settings.MAX_FILE_SIZE:
        max_mb = settings.MAX_FILE_SIZE // (1024 * 1024)
        await message.reply(
            f"⚠️ Файл слишком большой ({audio.file_size / (1024*1024):.1f} МБ).\n"
            f"Telegram Bot API ограничивает загрузку файлов размером до {max_mb} МБ."
        )
        return

    status_msg = await message.reply("⏳ Загружаю и обрабатываю трек...")

    try:
        # Скачиваем файл в буфер памяти для анализа тегов
        buffer = io.BytesIO()
        await bot.download(audio, destination=buffer)
        file_bytes = buffer.getvalue()

        # Сохраняем копию в приватный канал-хранилище (Telegram Unlimited Storage)
        channel_file_id = audio.file_id
        channel_file_unique_id = audio.file_unique_id
        if settings.STORAGE_CHANNEL_ID:
            try:
                caption = f"🎵 {audio.performer or 'Unknown'} — {audio.title or 'Track'}\n👤 Загрузил: @{message.from_user.username or message.from_user.id}"
                channel_msg = await bot.send_audio(
                    chat_id=settings.STORAGE_CHANNEL_ID,
                    audio=audio.file_id,
                    caption=caption,
                )
                if channel_msg.audio:
                    channel_file_id = channel_msg.audio.file_id
                    channel_file_unique_id = channel_msg.audio.file_unique_id
            except Exception:
                pass

        filename = audio.file_name or f"{audio.performer or 'Unknown'} - {audio.title or 'Track'}.mp3"

        async with AsyncSessionLocal() as session:
            # Убеждаемся, что пользователь зарегистрирован
            await track_service.get_or_create_user(
                session=session,
                user_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                username=message.from_user.username,
            )

            track, is_new = await track_service.process_and_save_audio(
                session=session,
                file_bytes=file_bytes,
                filename=filename,
                uploader_id=message.from_user.id,
                telegram_file_id=channel_file_id,
                telegram_file_unique_id=channel_file_unique_id,
            )

        duration_str = format_duration(track.duration)
        if is_new:
            reply_text = (
                f"✅ **Трек успешно добавлен в медиатеку!**\n\n"
                f"🎵 **{track.artist}** — **{track.title}**\n"
                f"⏱ Длительность: {duration_str}\n"
                f"💾 Размер: {track.file_size / (1024*1024):.2f} МБ\n"
                + (f"💿 Альбом: {track.album}\n" if track.album else "")
            )
        else:
            reply_text = (
                f"ℹ️ **Трек уже сохранен на сервере!**\n\n"
                f"🎵 **{track.artist}** — **{track.title}** добавлен в твою медиатеку."
            )

        await status_msg.edit_text(reply_text, reply_markup=get_player_keyboard(), parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при обработке трека: {str(e)}")


@router.message(F.document)
async def handle_document_audio_message(message: Message, bot: Bot) -> None:
    """Обработчик аудиофайлов, отправленных как документы (F.document)."""
    doc = message.document
    if not doc:
        return

    # Проверяем MIME-тип или расширение файла
    is_audio = False
    if doc.mime_type and doc.mime_type.lower() in SUPPORTED_MIME_TYPES:
        is_audio = True
    elif doc.file_name and doc.file_name.lower().endswith((".mp3", ".flac", ".ogg", ".m4a", ".wav")):
        is_audio = True

    if not is_audio:
        return  # Не аудиофайл — игнорируем или передаем дальше

    if doc.file_size and doc.file_size > settings.MAX_FILE_SIZE:
        max_mb = settings.MAX_FILE_SIZE // (1024 * 1024)
        await message.reply(
            f"⚠️ Файл слишком большой. Максимальный размер: {max_mb} МБ."
        )
        return

    status_msg = await message.reply("⏳ Загружаю и анализирую аудиофайл...")

    try:
        buffer = io.BytesIO()
        await bot.download(doc, destination=buffer)
        file_bytes = buffer.getvalue()

        # Сохраняем копию в приватный канал-хранилище
        channel_file_id = doc.file_id
        channel_file_unique_id = doc.file_unique_id
        if settings.STORAGE_CHANNEL_ID:
            try:
                caption = f"🎵 {doc.file_name or 'Audio'}\n👤 Загрузил: @{message.from_user.username or message.from_user.id}"
                channel_msg = await bot.send_document(
                    chat_id=settings.STORAGE_CHANNEL_ID,
                    document=doc.file_id,
                    caption=caption,
                )
                if channel_msg.document:
                    channel_file_id = channel_msg.document.file_id
                    channel_file_unique_id = channel_msg.document.file_unique_id
            except Exception:
                pass

        async with AsyncSessionLocal() as session:
            await track_service.get_or_create_user(
                session=session,
                user_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                username=message.from_user.username,
            )

            track, is_new = await track_service.process_and_save_audio(
                session=session,
                file_bytes=file_bytes,
                filename=doc.file_name or "track.mp3",
                uploader_id=message.from_user.id,
                telegram_file_id=channel_file_id,
                telegram_file_unique_id=channel_file_unique_id,
            )

        duration_str = format_duration(track.duration)
        status_prefix = "✅ **Трек добавлен!**" if is_new else "ℹ️ **Трек уже в библиотеке!**"
        reply_text = (
            f"{status_prefix}\n\n"
            f"🎵 **{track.artist}** — **{track.title}**\n"
            f"⏱ Длительность: {duration_str}\n"
        )
        await status_msg.edit_text(reply_text, reply_markup=get_player_keyboard(), parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка обработки: {str(e)}")
