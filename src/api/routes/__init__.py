from src.api.routes.auth import router as auth_router
from src.api.routes.tracks import router as tracks_router
from src.api.routes.library import router as library_router
from src.api.routes.playlists import router as playlists_router
from src.api.routes.history import router as history_router
from src.api.routes.search import router as search_router
from src.api.routes.social import router as social_router

__all__ = [
    "auth_router",
    "tracks_router",
    "library_router",
    "playlists_router",
    "history_router",
    "social_router",
    "search_router",
]
