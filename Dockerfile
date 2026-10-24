FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей (ffmpeg критически важен для конвертации звука и SoundCloud)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода и ресурсов
COPY alembic.ini .
COPY alembic ./alembic
COPY src ./src
COPY frontend ./frontend
COPY pic ./pic
COPY musicbot.db .

# Создание каталогов для медиафайлов
RUN mkdir -p media/audio media/covers media/temp pic

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000 10000

CMD ["python", "-m", "src.main"]
