"""
AutoBlog AI — Database Initialization
Mengelola koneksi SQLite dan inisialisasi tabel.
"""

import aiosqlite
from config import settings

DATABASE_PATH = settings.DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    """Membuat koneksi database baru."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Inisialisasi database — membuat tabel jika belum ada."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Tabel settings: menyimpan konfigurasi API
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabel history: menyimpan riwayat artikel
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                title TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                post_id TEXT,
                article_url TEXT,
                publish_mode TEXT DEFAULT 'draft',
                error_message TEXT,
                generation_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Safe migration: tambahkan kolom generation_log jika belum ada
        try:
            await db.execute("ALTER TABLE history ADD COLUMN generation_log TEXT")
        except Exception:
            pass  # Kolom sudah ada

        # Tabel oauth_tokens: menyimpan token OAuth2
        await db.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                token_uri TEXT,
                client_id TEXT,
                client_secret TEXT,
                expiry TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabel scheduler_queue: menyimpan antrean jadwal postingan
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                language TEXT NOT NULL,
                search_grounding INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'PENDING',
                title TEXT,
                post_id TEXT,
                article_url TEXT,
                error_message TEXT,
                publish_mode TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Safe migration: tambahkan kolom publish_mode ke scheduler_queue jika belum ada
        try:
            await db.execute("ALTER TABLE scheduler_queue ADD COLUMN publish_mode TEXT DEFAULT 'draft'")
        except Exception:
            pass  # Kolom sudah ada

        await db.commit()
        print("✅ Database initialized successfully.")
