from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.config import settings
from src.api.routes import (
    auth_router,
    history_router,
    library_router,
    playlists_router,
    search_router,
    social_router,
    tracks_router,
)


def create_app() -> FastAPI:
    """Инициализация и сборка приложения FastAPI."""
    app = FastAPI(
        title="Telegram Music Player API",
        version="1.0.0",
        description="RESTful API и Range-стриминг аудио для Telegram Mini App",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    # CORS настройка (критически важна для работы внутри Telegram WebView)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "Content-Range",
            "Accept-Ranges",
            "Content-Length",
            "Content-Disposition",
        ],
    )

    @app.middleware("http")
    async def add_no_cache_header(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/webapp") or request.url.path.startswith("/pic"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Подключение роутов
    app.include_router(auth_router, prefix="/api")
    app.include_router(tracks_router, prefix="/api")
    app.include_router(library_router, prefix="/api")
    app.include_router(playlists_router, prefix="/api")
    app.include_router(history_router, prefix="/api")
    app.include_router(social_router, prefix="/api")
    app.include_router(search_router, prefix="/api")

    # Статические файлы для Mini App
    frontend_dir = Path("./frontend")
    if frontend_dir.exists():
        app.mount("/webapp", StaticFiles(directory=str(frontend_dir), html=True), name="webapp")

    pic_dir = Path("./pic")
    if pic_dir.exists():
        app.mount("/pic", StaticFiles(directory=str(pic_dir)), name="pic")

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "app": "Telegram Music Player"}

    return app


app = create_app()
