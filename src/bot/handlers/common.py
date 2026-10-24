from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from src.config import settings
from src.database.session import AsyncSessionLocal
from src.services.friend_service import friend_service
from src.services.track_service import track_service

router = Router(name="common_router")


def get_player_keyboard(friend_id: int | None = None) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру с кнопкой запуска Telegram Mini App."""
    url = settings.WEBAPP_URL
    if friend_id:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}friend={friend_id}"
    button = InlineKeyboardButton(
        text="🎵 Открыть аудиоплеер",
        web_app=WebAppInfo(url=url),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


@router.message(CommandStart())
async def handle_start(message: Message, command: CommandObject) -> None:
    """Обработчик команды /start с поддержкой deep-link добавления в друзья."""
    user = message.from_user
    friend_connected = False
    friend_id_val = None
    target_friend = None

    if user:
        async with AsyncSessionLocal() as session:
            await track_service.get_or_create_user(
                session=session,
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
            )

            # Проверяем deep-link параметр
            if command.args and command.args.startswith("friend_"):
                try:
                    friend_id_val = int(command.args.replace("friend_", ""))
                    if friend_id_val != user.id:
                        friend_connected, target_friend, _ = await friend_service.connect_friends_flexible(
                            session=session, user_id=user.id, friend_id=friend_id_val
                        )
                except ValueError:
                    pass

    if friend_connected and target_friend:
        # Уведомляем пригласившего друга в ЛС бота
        try:
            if message.bot and target_friend.id:
                joined_name = user.first_name if user else "Друг"
                joined_handle = f" (@{user.username})" if user and user.username else ""
                await message.bot.send_message(
                    chat_id=target_friend.id,
                    text=(
                        f"🎉 **У вас новый друг в VEORA Music!**\n\n"
                        f"**{joined_name}**{joined_handle} перешел по вашей ссылке и присоединился к вам!\n"
                        f"Теперь ваши треки доступны друг другу во вкладке **«Друзья 👥»**."
                    ),
                    reply_markup=get_player_keyboard(friend_id=user.id if user else None),
                    parse_mode="Markdown",
                )
        except Exception:
            pass

        target_name = target_friend.first_name or "друг"
        target_handle = f" (@{target_friend.username})" if target_friend.username else ""
        text = (
            f"🎉 **Отлично, {user.first_name if user else 'друг'}!**\n\n"
            f"Вы успешно добавили **{target_name}**{target_handle} в друзья в VEORA Music!\n\n"
            "Теперь вы можете:\n"
            "• Слушать треки друга во вкладке **«Друзья 👥»**\n"
            "• Делиться новыми песнями — отправьте сюда аудиофайл, и друг сразу сможет его послушать!\n\n"
            "Нажмите кнопку ниже, чтобы запустить плеер 🎧"
        )
        reply_markup = get_player_keyboard(friend_id=target_friend.id)
    else:
        text = (
            f"👋 Привет, {user.first_name if user else 'друг'}!\n\n"
            "Я твой персональный **Telegram Music Player**.\n\n"
            "🎧 **Что я умею:**\n"
            "• Сохранять треки, которые ты мне отправляешь (MP3, M4A, FLAC).\n"
            "• Слушать музыку друзей и делиться своей во вкладке **«Друзья 👥»**\n"
            "• Открывать глобальную музыкальную **«Ленту 🌍»** сообщества\n"
            "• **Слушать офлайн**: сохраняй треки прямо в память устройства без расхода трафика!\n\n"
            "Отправь мне любой аудиофайл, чтобы начать формировать библиотеку."
        )
        reply_markup = get_player_keyboard()

    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Обработчик команды /help."""
    text = (
        "📖 **Инструкция пользователя:**\n\n"
        "1. **Загрузка музыки:** просто перешли или отправь аудиофайл боту (до 20 МБ).\n"
        "2. **Плеер:** нажми кнопку *'Открыть аудиоплеер'* ниже.\n"
        "3. **Офлайн-режим:** внутри плеера нажми иконку скачивания рядом с треком, и он сохранится в локальное хранилище браузера (IndexedDB).\n"
        "4. **Поиск:** в плеере доступен поиск по артисту, названию и альбому."
    )
    await message.answer(text, reply_markup=get_player_keyboard(), parse_mode="Markdown")
