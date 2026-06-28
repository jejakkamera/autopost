"""
AutoBlog AI — Auth Router
OAuth2 endpoints, login auth, dan blog verification.
"""

import hashlib
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from models import (
    AuthStatusResponse, MessageResponse, BlogVerifyRequest, BlogVerifyResponse,
    LoginRequest, LoginSetupRequest, LoginStatusResponse,
)
from services.blogger_service import (
    get_auth_url, exchange_code, check_auth_status, disconnect, verify_blog,
)
from services.db_service import get_setting, save_setting
from config import settings

router = APIRouter()

# ============================================
# Login Key Auth
# ============================================
AUTH_SALT = "autoblog_ai_session_salt_2026"


def _hash_key(key: str) -> str:
    """Hash login key dengan salt."""
    return hashlib.sha256(f"{AUTH_SALT}_{key}".encode()).hexdigest()


def _generate_token(key: str) -> str:
    """Generate session token dari login key."""
    return hashlib.sha256(f"session_{key}_{AUTH_SALT}".encode()).hexdigest()


@router.get("/login/status", response_model=LoginStatusResponse)
async def login_status(request: Request):
    """Cek status login user."""
    stored_hash = await get_setting("login_key_hash")
    setup_required = not stored_hash

    # Cek cookie session
    session_token = request.cookies.get("session_token")
    if not session_token or not stored_hash:
        return LoginStatusResponse(
            authenticated=False,
            setup_required=setup_required,
            message="Setup login key." if setup_required else "Silakan login.",
        )

    # Verifikasi token
    stored_token = await get_setting("session_token")
    if session_token == stored_token:
        return LoginStatusResponse(
            authenticated=True,
            setup_required=False,
            message="Authenticated.",
        )

    return LoginStatusResponse(
        authenticated=False,
        setup_required=False,
        message="Session tidak valid. Silakan login ulang.",
    )


@router.post("/login/setup", response_model=MessageResponse)
async def setup_login(request: LoginSetupRequest):
    """Setup login key pertama kali (hanya jika belum ada key)."""
    existing = await get_setting("login_key_hash")
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Login key sudah dikonfigurasi."},
        )

    if len(request.key) < 4:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Login key minimal 4 karakter."},
        )

    key_hash = _hash_key(request.key)
    await save_setting("login_key_hash", key_hash)

    # Auto-login setelah setup
    token = _generate_token(request.key)
    await save_setting("session_token", token)

    response = JSONResponse(content={
        "status": "success",
        "message": "Login key berhasil dibuat! Anda otomatis login.",
    })
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 hari
    )
    return response


@router.post("/login")
async def login(request: LoginRequest):
    """Login dengan key."""
    stored_hash = await get_setting("login_key_hash")
    if not stored_hash:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Login key belum dikonfigurasi."},
        )

    # Verifikasi key
    key_hash = _hash_key(request.key)
    if key_hash != stored_hash:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Login key salah."},
        )

    # Buat session token
    token = _generate_token(request.key)
    await save_setting("session_token", token)

    response = JSONResponse(content={
        "status": "success",
        "message": "Login berhasil!",
    })
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 hari
    )
    return response


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """Logout — hapus session."""
    await save_setting("session_token", "")

    response = JSONResponse(content={
        "status": "success",
        "message": "Logout berhasil.",
    })
    response.delete_cookie("session_token")
    return response


# ============================================
# Google OAuth2
# ============================================

@router.get("/auth/google")
async def start_oauth():
    """Mulai alur OAuth2 — redirect ke Google consent screen."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "⚠️ OAuth Client ID/Secret belum dikonfigurasi. Periksa file .env.",
                "error_code": "MISSING_OAUTH_CONFIG",
            },
        )

    auth_url = await get_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/auth/callback")
async def oauth_callback(code: str = Query(...), error: str = Query(None)):
    """Handle callback dari Google setelah user memberikan consent."""
    if error:
        return RedirectResponse(url="/?auth=denied")

    try:
        await exchange_code(code)
        return RedirectResponse(url="/?auth=success")
    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        return RedirectResponse(url="/?auth=error")


@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status():
    """Cek apakah user sudah terkoneksi ke Google."""
    result = await check_auth_status()
    return AuthStatusResponse(**result)


@router.post("/auth/disconnect", response_model=MessageResponse)
async def disconnect_google():
    """Hapus token OAuth (disconnect dari Google)."""
    result = await disconnect()
    return MessageResponse(**result)


# ============================================
# Blog Verification
# ============================================

@router.post("/blog/verify", response_model=BlogVerifyResponse)
async def verify_blog_endpoint(request: BlogVerifyRequest):
    """Verifikasi Blog ID — cek apakah blog ada dan bisa diakses."""
    try:
        result = await verify_blog(request.blog_id)
        return BlogVerifyResponse(**result)
    except Exception as e:
        error_msg = str(e)
        clean_msg = error_msg.split(": ", 1)[-1] if ": " in error_msg else error_msg
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": clean_msg,
            },
        )
