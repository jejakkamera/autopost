"""
AutoBlog AI — Routers Package
Export semua router untuk digunakan di main.py.
"""

from routers.settings import router as settings_router
from routers.history import router as history_router
from routers.generate import router as generate_router
from routers.auth import router as auth_router
from routers.schedule import router as schedule_router

__all__ = ["settings_router", "history_router", "generate_router", "auth_router", "schedule_router"]

