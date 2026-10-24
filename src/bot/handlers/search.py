import hashlib
import io
from typing import Dict, List
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from src.bot.handlers.common import get_player_keyboard
from src.database.session import AsyncSessionLocal
from src.services.soundcloud_service import soundcloud_service
from src.services.track_service import track_service

router = Router(name="search_router")

# Временный кэш результатов поиска в памяти бота: search_hash -> list of track dicts
_search_cache: Dict[str, List[dict]] = {}


def format_duration(seconds: int) -> str:
    """Форматирует секунды в mm:ss."""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


@router.message(Command(commands=["search", "sc", "find"]))
async def handle_search_command(message: Message, command: CommandObject, bot: Bot) -> None:
    """Команда /search <запрос> или /sc <запрос> — поиск музыки в SoundCloud."""
    query = (command.args or "").strip()
    if not query:
        await message.reply(
            "🔍 **Поиск музыки в SoundCloud**\n\n"
            "Напишите название трека или исполнителя после команды, например:\n"
            "• `/search Miyagi`\n"
            "• `/sc Phonk`\n"
            "• `/find Macan`\n\n"
            "Или просто отправьте название песни в чат!",
            parse_mode="Markdown",
        )
        return

    status_msg = await message.reply(f"⏳ Ищу **«{query}»** в SoundCloud...", parse_mode="Markdown")
    try:
        results = await soundcloud_service.search(query=query, limit=5)
        if not results:
            await status_msg.edit_text(
                f"😔 По запросу **«{query}»** ничего не найдено в SoundCloud.\n"
                "Попробуйте изменить запрос (например, указать только название или автора).",
                parse_mode="Markdown",
            )
            return

        # Сохраняем в кэш под коротким ключом
        cache_key = hashlib.md5(f"{message.from_user.id}:{query}".encode("utf-8")).hexdigest()[:8]
        _search_cache[cache_key] = results

        lines = [f"🎵 **Найдено в SoundCloud по запросу «{query}»:**\n"]
        buttons = []
        num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

        for idx, item in enumerate(results):
            num = num_emojis[idx] if idx < len(num_emojis) else f"{idx+1}."
            dur = format_duration(item["duration"])
            lines.append(f"{num} **{item['artist']}** — {item['title']} `({dur})`")

        # Кнопки для скачивания
        row1 = []
        row2 = []
        for idx in range(len(results)):
            cb_data = f"sc_dl:{cache_key}:{idx}"
            btn = InlineKeyboardButton(text=f"📥 {idx+1}", callback_data=cb_data)
            if len(row1) < 3:
                row1.append(btn)
            else:
                row2.append(btn)

        keyboard_rows = []
        if row1:
            keyboard_rows.append(row1)
        if row2:
            keyboard_rows.append(row2)

        # Кнопка открытия плеера
        player_btn = get_player_keyboard().inline_keyboard[0]
        keyboard_rows.append(player_btn)

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        await status_msg.edit_text("\n".join(lines), reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка поиска: {str(e)}")


@router.callback_query(F.data.startswith("sc_dl:"))
async def handle_sc_download_callback(call: CallbackQuery, bot: Bot) -> None:
    """Обработчик нажатия на кнопку скачивания трека из результатов поиска."""
    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Неверные данные запроса", show_alert=True)
        return

    _, cache_key, idx_str = parts
    try:
        idx = int(idx_str)
    except ValueError:
        await call.answer("Ошибка индекса трека", show_alert=True)
        return

    results = _search_cache.get(cache_key)
    if not results or idx >= len(results):
        await call.answer("Результаты поиска устарели. Повторите /search", show_alert=True)
        return

    item = results[idx]
    await call.answer("⏳ Загружаю трек из SoundCloud...", show_alert=False)

    status_msg = await call.message.reply(
        f"⏳ Скачиваю и конвертирую в MP3:\n**{item['artist']} — {item['title']}**...",
        parse_mode="Markdown",
    )

    try:
        async with AsyncSessionLocal() as session:
            await track_service.get_or_create_user(
                session=session,
                user_id=call.from_user.id,
                first_name=call.from_user.first_name,
                last_name=call.from_user.last_name,
                username=call.from_user.username,
            )

            track, is_new = await soundcloud_service.import_track(
                session=session,
                user_id=call.from_user.id,
                url=item["url"],
                bot=bot,
            )

        # Скачиваем аудиофайл для отправки в чат
        file_bytes, _ = await soundcloud_service._sync_download(item["url"])

        safe_name = f"{track.artist} - {track.title}.mp3"
        safe_filename = "".join(c for c in safe_name if c.isalnum() or c in (" ", "-", "_", ".")).strip() or "track.mp3"

        caption = (
            f"✅ **{track.artist} — {track.title}**\n\n"
            f"⏱ Длительность: {format_duration(track.duration)}\n"
            f"💾 Добавлен в вашу медиатеку VEORA Player!"
        )

        await bot.send_audio(
            chat_id=call.message.chat.id,
            audio=BufferedInputFile(file_bytes, filename=safe_filename),
            caption=caption,
            title=track.title,
            performer=track.artist,
            duration=track.duration,
            reply_markup=get_player_keyboard(),
            parse_mode="Markdown",
        )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка скачивания трека: {str(e)}")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_music_search(message: Message, bot: Bot) -> None:
    """Умный текстовый поиск: если пользователь просто прислал название трека в чат."""
    text = (message.text or "").strip()
    # Пропускаем слишком короткие или слишком длинные сообщения
    if len(text) < 3 or len(text) > 80:
        return

    # Запускаем поиск через существующую логику
    class FakeCommand:
        args = text

    await handle_search_command(message, FakeCommand(), bot)
