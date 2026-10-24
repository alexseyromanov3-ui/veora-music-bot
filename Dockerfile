# Multi-stage production Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные зависимости
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Копируем код приложения
COPY alembic.ini .
COPY alembic ./alembic
COPY src ./src
COPY frontend ./frontend

# Создаем директории для хранения медиа
RUN mkdir -p media/audio media/covers media/temp

EXPOSE 8000

# Запуск миграций и основного процесса
CMD ["sh", "-c", "alembic upgrade head && python -m src.main"]
