"""
AutoBlog AI — Image Generation Service
Menggunakan OpenAI-compatible Images API (misal Premzone).
"""

import httpx
from typing import Optional


async def generate_image(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
) -> str:
    """
    Generate gambar dari prompt menggunakan OpenAI-compatible Image API.

    Returns:
        Base64 string of the generated image.
    """
    # Pastikan v1 suffix ada jika tidak dideklarasikan
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        url = f"{base_url}/v1/images/generations"
    else:
        url = f"{base_url}/images/generations"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "medium",
    }

    # Premzone image generation takes 15-240s, so we set a generous timeout
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 429:
            raise Exception("IMAGE_QUOTA: Limit API generator gambar tercapai.")
        elif response.status_code == 401:
            raise Exception("IMAGE_AUTH: API Key generator gambar tidak valid.")
        elif response.status_code != 200:
            error_msg = response.text[:200]
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
            except Exception:
                pass
            raise Exception(f"IMAGE_ERROR: {error_msg}")

        data = response.json()
        
        # Ambil b64
        try:
            b64_json = data["data"][0].get("b64_json")
            if not b64_json:
                # Cek jika URL yang direturn, tapi spek user minta b64
                url_img = data["data"][0].get("url")
                if url_img:
                    # Ambil image bytes dan convert ke base64
                    img_resp = await client.get(url_img)
                    import base64
                    b64_json = base64.b64encode(img_resp.content).decode("utf-8")
                else:
                    raise Exception("Format response API gambar tidak valid (missing b64_json/url).")
            return b64_json
        except (KeyError, IndexError) as e:
            raise Exception(f"IMAGE_ERROR: Gagal memproses response API gambar — {str(e)}")


async def upload_to_catbox(b64_image: str) -> str:
    """Upload base64 image to Catbox.moe and return the permanent public URL."""
    try:
        import base64
        img_bytes = base64.b64decode(b64_image)
        url = "https://catbox.moe/user/api.php"

        files = {
            "fileToUpload": ("image.png", img_bytes, "image/png")
        }
        data = {
            "reqtype": "fileupload"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, data=data, files=files)
            if response.status_code == 200:
                img_url = response.text.strip()
                if img_url.startswith("https://files.catbox.moe/"):
                    return img_url
            raise Exception(f"Catbox upload failed: {response.text}")
    except Exception as e:
        raise Exception(f"IMAGE_UPLOAD_ERROR: Gagal mengunggah gambar ke cloud — {str(e)}")

