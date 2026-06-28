from fastapi import APIRouter
from models import SettingsRequest, SettingsResponse, MessageResponse, AITestRequest, AITestResponse
from services.db_service import get_all_settings, save_multiple_settings, get_setting
from services.ai_service import get_providers_info, _call_llm, PROVIDERS

router = APIRouter()


def mask_api_key(key: str) -> str:
    """Mask API key — hanya tampilkan 4 karakter terakhir."""
    if not key or len(key) <= 4:
        return key
    return "*" * (len(key) - 4) + key[-4:]


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Mengambil konfigurasi yang tersimpan (API keys di-mask)."""
    data = await get_all_settings()
    return SettingsResponse(
        ai_provider=data.get("ai_provider", "gemini"),
        ai_model=data.get("ai_model", ""),
        gemini_api_key=mask_api_key(data.get("gemini_api_key", "")),
        deepseek_api_key=mask_api_key(data.get("deepseek_api_key", "")),
        openai_api_key=mask_api_key(data.get("openai_api_key", "")),
        sumopod_api_key=mask_api_key(data.get("sumopod_api_key", "")),
        custom_api_key=mask_api_key(data.get("custom_api_key", "")),
        custom_base_url=data.get("custom_base_url", ""),
        custom_model=data.get("custom_model", ""),
        blog_id=data.get("blog_id", ""),
        default_status=data.get("default_status", "draft"),
        # Image Settings
        image_api_enabled=data.get("image_api_enabled", "false").lower() == "true",
        image_api_key=mask_api_key(data.get("image_api_key", "")),
        image_base_url=data.get("image_base_url", "https://api.premzone.co"),
        image_model=data.get("image_model", "cx/gpt-5.5"),
        image_prompt_template=data.get(
            "image_prompt_template",
            "A flat style vector illustration of [TOPIK], modern design, vibrant colors, clean background"
        ),
    )


@router.post("/settings", response_model=MessageResponse)
async def save_settings(request: SettingsRequest):
    """Menyimpan/update konfigurasi ke database."""
    settings_data = {}

    # Simpan semua field yang dikirim
    fields = {
        "ai_provider": request.ai_provider,
        "ai_model": request.ai_model,
        "gemini_api_key": request.gemini_api_key,
        "deepseek_api_key": request.deepseek_api_key,
        "openai_api_key": request.openai_api_key,
        "sumopod_api_key": request.sumopod_api_key,
        "custom_api_key": request.custom_api_key,
        "custom_base_url": request.custom_base_url,
        "custom_model": request.custom_model,
        "blog_id": request.blog_id,
        "default_status": request.default_status,
        # Image Settings
        "image_api_key": request.image_api_key,
        "image_base_url": request.image_base_url,
        "image_model": request.image_model,
        "image_prompt_template": request.image_prompt_template,
    }

    if request.image_api_enabled is not None:
        fields["image_api_enabled"] = "true" if request.image_api_enabled else "false"

    for key, value in fields.items():
        if value is not None:
            settings_data[key] = value

    if not settings_data:
        return MessageResponse(
            status="error",
            message="Tidak ada data yang dikirim."
        )

    await save_multiple_settings(settings_data)

    return MessageResponse(
        status="success",
        message="Pengaturan berhasil disimpan."
    )


@router.get("/providers")
async def get_providers():
    """Mengembalikan daftar AI provider dan model yang didukung."""
    return get_providers_info()


@router.post("/settings/test-ai", response_model=AITestResponse)
async def test_ai_connection(request: AITestRequest):
    """Menguji koneksi ke provider AI yang dipilih."""
    provider = request.provider
    api_key = request.api_key.strip()
    model = request.model
    custom_base_url = request.custom_base_url

    # Fallback ke key tersimpan jika key kosong atau masked
    if not api_key or api_key.startswith("*"):
        api_key_field = f"{provider}_api_key"
        saved_key = await get_setting(api_key_field)
        if saved_key:
            api_key = saved_key

    if not api_key:
        return AITestResponse(status="error", message="API Key tidak boleh kosong.")

    if provider not in PROVIDERS:
        return AITestResponse(status="error", message=f"Provider '{provider}' tidak didukung.")

    if not model and provider != "custom":
        model = PROVIDERS[provider]["default_model"]

    base_url = None
    if provider in ("deepseek", "openai", "sumopod"):
        base_url = PROVIDERS[provider]["base_url"]
    elif provider == "custom":
        if not custom_base_url:
            return AITestResponse(status="error", message="Custom Base URL tidak boleh kosong.")
        base_url = custom_base_url.rstrip("/")

    try:
        system_prompt = "You are a helpful assistant."
        user_prompt = "Say only 'Koneksi Berhasil!' if you can read this message."

        response = await _call_llm(
            provider=provider,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            base_url=base_url
        )

        clean_resp = response.strip()
        return AITestResponse(
            status="success",
            message=f"Koneksi Berhasil! AI merespon: \"{clean_resp[:100]}\""
        )
    except Exception as e:
        error_msg = str(e)
        clean_msg = error_msg.split(": ", 1)[-1] if ": " in error_msg else error_msg
        return AITestResponse(
            status="error",
            message=f"Koneksi Gagal: {clean_msg}"
        )

