"""
AutoBlog AI — Main Application Entry Point
FastAPI server dengan auth middleware, static files, dan API routers.
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os

from config import settings
from database import init_db
from routers import settings_router, history_router, generate_router, auth_router, schedule_router
from services.db_service import get_setting

# Paths yang TIDAK memerlukan auth
PUBLIC_PATHS = {
    "/api/login",
    "/api/login/setup",
    "/api/login/status",
    "/api/logout",
    "/api/auth/google",
    "/api/auth/callback",
}
PUBLIC_PREFIXES = ("/static/",)


import asyncio
from services.scheduler_service import process_pending_schedule_queue


async def schedule_worker():
    """Background worker untuk memproses antrean jadwal artikel."""
    print("⏳ Scheduler worker aktif (setiap 60 detik).")
    while True:
        try:
            await process_pending_schedule_queue()
        except Exception as e:
            print(f"❌ Error dalam schedule worker: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: inisialisasi database saat startup."""
    await init_db()
    # Mulai background scheduler worker
    worker_task = asyncio.create_task(schedule_worker())
    print(f"🚀 AutoBlog AI berjalan di http://{settings.HOST}:{settings.PORT}")
    yield
    # Batalkan task saat shutdown
    worker_task.cancel()
    print("👋 AutoBlog AI berhenti.")


# Inisialisasi FastAPI
app = FastAPI(
    title="AutoBlog AI",
    description="Aplikasi auto-posting ke Google Blogger menggunakan Gemini AI",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware: cek session cookie untuk semua request (kecuali public paths)."""
    path = request.url.path

    # Skip untuk public paths
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)

    # Skip jika login key belum di-setup (first-time user)
    stored_hash = await get_setting("login_key_hash")
    if not stored_hash:
        # Belum ada login key → izinkan akses (frontend akan menampilkan setup)
        return await call_next(request)

    # Cek session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": {"status": "error", "message": "Unauthorized. Silakan login.", "error_code": "UNAUTHORIZED"}},
            )
        # Untuk halaman utama, tetap serve tapi frontend akan handle login UI
        return await call_next(request)

    # Verifikasi session token
    stored_token = await get_setting("session_token")
    if session_token != stored_token:
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": {"status": "error", "message": "Session tidak valid. Silakan login ulang.", "error_code": "INVALID_SESSION"}},
            )

    return await call_next(request)


# Mount static files
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Include API routers
app.include_router(settings_router, prefix="/api", tags=["Settings"])
app.include_router(history_router, prefix="/api", tags=["History"])
app.include_router(generate_router, prefix="/api", tags=["Generate"])
app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(schedule_router, prefix="/api", tags=["Schedule"])


@app.get("/", include_in_schema=False)
async def index():
    """Halaman utama — serve file HTML langsung."""
    html_path = os.path.join(settings.TEMPLATES_DIR, "index.html")
    return FileResponse(html_path, media_type="text/html")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
