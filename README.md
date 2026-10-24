# Telegram Music Player & Bot

Полноценный музыкальный сервис внутри Telegram с поддержкой потокового воспроизведения (HTTP Range 206), **полноценного офлайн-режима** через IndexedDB, персональных плейлистов и истории прослушиваний.

---

## 🛠 Технологический стек

- **Backend**: Python 3.12+ (проверено на Python 3.14), `aiogram 3.x`, `FastAPI`, `SQLAlchemy 2.x`, `Alembic`, `Pydantic v2`, `mutagen`, `aiofiles`.
- **Database**: SQLite (локально) / PostgreSQL (production) с полной асинхронной поддержкой через SQLAlchemy + Greenlet + asyncpg.
- **Frontend**: Telegram Mini App SDK, HTML5 Audio, IndexedDB Storage, MediaSession API, CSS Glassmorphism.
- **Аудио-стриминг**: Честная поддержка HTTP Byte-Range Requests (`206 Partial Content`) для мгновенной перемотки на iOS/Android WebKit.
- **Офлайн-режим**: Сохранение аудио-блобов в IndexedDB и воспроизведение через `URL.createObjectURL` без подключения к интернету.

---

## ✨ Возможности сервиса

1. **Telegram-бот**:
   - Приём аудиофайлов и документов (MP3, M4A, FLAC).
   - Автоматическое извлечение тегов артиста, названия, альбома и встроенных обложек (`mutagen`).
   - Защита от дубликатов по SHA-256 хешу.
   - Постоянная кнопка запуска Mini App.
2. **Музыкальный аудиоплеер (Telegram Mini App)**:
   - Адаптивный плеер в темной теме Telegram (мини-панель + полноэкранный режим).
   - Управление очередью, случайный порядок (Shuffle), повтор трека / плейлиста.
   - Синхронизация с системным центром управления (MediaSession API — экран блокировки и шторка iOS/Android).
3. **Офлайн-режим (IndexedDB)**:
   - Скачивание треков и обложек в локальную память браузера.
   - Пакетное скачивание целых плейлистов в один клик.
   - Полное воспроизведение сохранённой медиатеки при отсутствии сети.
   - Отображение объёма занятой памяти и функция быстрой очистки кэша.
4. **Персональные плейлисты и история**:
   - Создание и редактирование плейлистов.
   - Добавление и удаление треков.
   - Раздел «Недавно прослушанные» (History).
   - Ручная коррекция метаданных треков (карандаш ✏️).

---

## 🚀 Быстрый старт (Локально)

### 1. Виртуальное окружение и зависимости
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройка переменных окружения
Скопируйте пример конфигурации:
```powershell
Copy-Item .env.example .env
```
Укажите ваш `BOT_TOKEN` и `WEBAPP_URL` в `.env`.

### 3. Применение миграций базы данных
```powershell
alembic upgrade head
```

### 4. Запуск сервиса (Бот + API)
```powershell
python -m src.main
```

---

## 🐳 Развёртывание через Docker Compose (Production)

Для запуска бота и PostgreSQL одной командой:
```bash
docker compose up -d --build
```
Подробное руководство по настройке Nginx, SSL и бэкапов доступно в [deployment_guide.md](file:///C:/Users/RAMKELAUNER/.gemini/antigravity/brain/6dac8fdd-b33c-408a-9a5a-4708783467da/deployment_guide.md).

---

## 🧪 Запуск автоматических тестов
Все ключевые модули покрыты тестами (`pytest`):
```powershell
pytest -v
```
Покрыто 17 тестов: база данных, авторизация initData HMAC-SHA256, Range-стриминг (206), метаданные, плейлисты, история, статика.
