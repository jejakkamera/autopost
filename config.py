"""
AutoBlog AI — Konfigurasi Aplikasi
Memuat environment variables dan menyediakan konfigurasi global.
"""

import os
from dotenv import load_dotenv

# Load .env file jika ada
load_dotenv()

# Abaikan pemeriksaan ketat perubahan scope OAuth Google
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


class Settings:
    """Konfigurasi aplikasi dari environment variables."""

    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Google Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Blogger
    BLOG_ID: str = os.getenv("BLOG_ID", "")

    # OAuth2
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"
    OAUTH_SCOPES: list = [
        "https://www.googleapis.com/auth/blogger",
    ]

    # Database
    DATABASE_PATH: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "database.db"
    )

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    CREDENTIALS_DIR: str = os.path.join(BASE_DIR, "credentials")
    TEMPLATES_DIR: str = os.path.join(BASE_DIR, "templates")
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")


settings = Settings()
