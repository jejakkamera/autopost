"""
AutoBlog AI — Blogger Service
OAuth2 flow dan publish artikel ke Google Blogger API v3.
"""

import json
from typing import Dict, Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config import settings
from services.db_service import save_oauth_token, get_oauth_token, delete_oauth_token, save_setting, get_setting

# Scopes yang dibutuhkan
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def _build_client_config() -> Dict:
    """Buat client config dari environment variables."""
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.OAUTH_REDIRECT_URI],
        }
    }


async def get_auth_url() -> str:
    """Generate URL untuk OAuth2 consent screen."""
    client_config = _build_client_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.OAUTH_REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Simpan code_verifier PKCE ke database untuk pertukaran kode nanti
    if hasattr(flow, "code_verifier") and flow.code_verifier:
        await save_setting("oauth_code_verifier", flow.code_verifier)
    return auth_url


async def exchange_code(code: str) -> Dict:
    """Tukar authorization code menjadi access token & refresh token."""
    try:
        client_config = _build_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=settings.OAUTH_REDIRECT_URI,
        )
        # Ambil code_verifier yang tersimpan
        code_verifier = await get_setting("oauth_code_verifier")
        if code_verifier:
            flow.code_verifier = code_verifier

        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Simpan token ke database
        expiry_str = credentials.expiry.isoformat() if credentials.expiry else None
        await save_oauth_token(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            expiry=expiry_str,
        )

        return {"status": "success", "message": "Berhasil terhubung ke Google."}

    except Exception as e:
        raise Exception(f"AUTH_ERROR: Gagal menukar kode otorisasi — {str(e)}")


async def get_credentials() -> Optional[Credentials]:
    """Ambil credentials dari database dan refresh jika expired."""
    token_data = await get_oauth_token()
    if not token_data:
        return None

    expiry = None
    if token_data.get("expiry"):
        try:
            expiry = datetime.fromisoformat(token_data["expiry"])
        except (ValueError, TypeError):
            expiry = None

    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", settings.GOOGLE_CLIENT_ID),
        client_secret=token_data.get("client_secret", settings.GOOGLE_CLIENT_SECRET),
        expiry=expiry,
    )

    # Auto-refresh jika expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            # Update token di database
            expiry_str = creds.expiry.isoformat() if creds.expiry else None
            await save_oauth_token(
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                token_uri=creds.token_uri,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                expiry=expiry_str,
            )
        except Exception:
            # Refresh gagal — hapus token, user perlu re-auth
            await delete_oauth_token()
            return None

    return creds


async def check_auth_status() -> Dict:
    """Cek apakah user sudah terkoneksi ke Google."""
    creds = await get_credentials()
    if creds and creds.valid:
        return {"connected": True, "message": "Terhubung ke Google."}
    return {"connected": False, "message": "Belum terhubung ke Google."}


async def publish_to_blogger(
    blog_id: str,
    title: str,
    html_content: str,
    is_draft: bool = True,
    labels: Optional[list] = None,
) -> Dict:
    """
    Publish artikel ke Google Blogger.

    Returns:
        Dict dengan keys: post_id, article_url
    """
    creds = await get_credentials()
    if not creds or not creds.valid:
        raise Exception("AUTH_REQUIRED: Akun Google belum terhubung. Silakan klik 'Connect to Google' di Pengaturan.")

    try:
        # Build Blogger API service
        service = build("blogger", "v3", credentials=creds)

        # Buat body post
        post_body = {
            "kind": "blogger#post",
            "blog": {"id": blog_id},
            "title": title,
            "content": html_content,
        }
        if labels:
            post_body["labels"] = labels

        # Insert post
        if is_draft:
            # Simpan sebagai draft
            result = service.posts().insert(
                blogId=blog_id,
                body=post_body,
                isDraft=True,
            ).execute()
        else:
            # Publish langsung (live)
            result = service.posts().insert(
                blogId=blog_id,
                body=post_body,
                isDraft=False,
            ).execute()

        return {
            "post_id": result.get("id", ""),
            "article_url": result.get("url", ""),
        }

    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "rateLimitExceeded" in error_msg:
            raise Exception("BLOGGER_QUOTA: Kuota Blogger API tercapai. Coba lagi nanti.")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            raise Exception("BLOGGER_FORBIDDEN: Tidak punya akses ke blog ini. Periksa Blog ID.")
        elif "404" in error_msg or "not found" in error_msg.lower():
            raise Exception("BLOGGER_NOT_FOUND: Blog tidak ditemukan. Periksa Blog ID.")
        else:
            raise Exception(f"BLOGGER_ERROR: Gagal mempublikasikan ke Blogger — {error_msg}")


async def schedule_post_to_blogger(
    blog_id: str,
    title: str,
    html_content: str,
    published_iso: str,
    labels: Optional[list] = None,
) -> Dict:
    """
    Jadwalkan artikel ke Google Blogger dengan waktu rilis di masa depan.
    Blogger API otomatis menjadwalkan post jika field 'published' diset ke waktu masa depan
    dan post dikirim sebagai live (isDraft=False).

    Args:
        blog_id: ID blog target.
        title: Judul artikel.
        html_content: Konten HTML artikel.
        published_iso: Waktu rilis dalam format ISO 8601 (e.g., 2026-07-01T09:00:00+07:00).
        labels: Daftar label/kategori.

    Returns:
        Dict dengan keys: post_id, article_url
    """
    creds = await get_credentials()
    if not creds or not creds.valid:
        raise Exception("AUTH_REQUIRED: Akun Google belum terhubung.")

    try:
        service = build("blogger", "v3", credentials=creds)

        post_body = {
            "kind": "blogger#post",
            "blog": {"id": blog_id},
            "title": title,
            "content": html_content,
            "published": published_iso,
            "status": "LIVE",
        }
        if labels:
            post_body["labels"] = labels

        # Publish sebagai live — Blogger akan otomatis schedule karena tanggal di masa depan
        result = service.posts().insert(
            blogId=blog_id,
            body=post_body,
            isDraft=False,
        ).execute()

        return {
            "post_id": result.get("id", ""),
            "article_url": result.get("url", ""),
        }

    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "rateLimitExceeded" in error_msg:
            raise Exception("BLOGGER_QUOTA: Kuota Blogger API tercapai. Coba lagi nanti.")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            raise Exception("BLOGGER_FORBIDDEN: Tidak punya akses ke blog ini.")
        else:
            raise Exception(f"BLOGGER_SCHEDULE_ERROR: Gagal menjadwalkan ke Blogger — {error_msg}")


async def disconnect():
    """Hapus token OAuth (disconnect dari Google)."""
    await delete_oauth_token()
    return {"status": "success", "message": "Berhasil terputus dari Google."}


async def verify_blog(blog_id: str) -> Dict:
    """
    Verifikasi Blog ID — cek apakah blog ada dan bisa diakses.

    Returns:
        Dict dengan info blog (name, url, total_posts) atau error.
    """
    creds = await get_credentials()
    if not creds or not creds.valid:
        raise Exception("AUTH_REQUIRED: Hubungkan akun Google terlebih dahulu untuk memverifikasi Blog ID.")

    try:
        service = build("blogger", "v3", credentials=creds)
        blog = service.blogs().get(blogId=blog_id).execute()

        return {
            "status": "success",
            "blog_name": blog.get("name", "Unknown"),
            "blog_url": blog.get("url", ""),
            "total_posts": blog.get("posts", {}).get("totalItems", 0),
            "message": f"Blog \"{blog.get('name', '')}\" berhasil ditemukan!",
        }

    except Exception as e:
        error_msg = str(e)
        if "AUTH_REQUIRED" in error_msg:
            raise
        elif "404" in error_msg or "not found" in error_msg.lower():
            raise Exception("BLOG_NOT_FOUND: Blog tidak ditemukan. Periksa Blog ID Anda.")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            raise Exception("BLOG_FORBIDDEN: Tidak punya akses ke blog ini. Pastikan akun Google Anda adalah pemilik blog.")
        else:
            raise Exception(f"BLOG_ERROR: Gagal memverifikasi blog — {error_msg}")

