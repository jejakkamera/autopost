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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.post(url, data=data, files=files, headers=headers)
            response_text = response.text.strip()
            if response.status_code == 200:
                if response_text.startswith("https://files.catbox.moe/"):
                    return response_text
            
            if "Invalid uploader" in response_text:
                raise Exception(
                    "Catbox memblokir IP server Anda (Invalid uploader). "
                    "Ini sering terjadi pada server VPS/hosting. Silakan masuk ke Pengaturan, "
                    "ubah 'Penyedia Upload Gambar' ke 'ImgBB', dan masukkan API Key ImgBB gratis Anda."
                )
            raise Exception(f"Catbox upload failed: {response_text}")
    except Exception as e:
        if "Catbox memblokir IP server Anda" in str(e):
            raise Exception(f"IMAGE_UPLOAD_ERROR: {str(e)}")
        raise Exception(f"IMAGE_UPLOAD_ERROR: Gagal mengunggah gambar ke cloud — {str(e)}")


async def upload_to_imgbb(b64_image: str, api_key: str) -> str:
    """Upload base64 image to ImgBB and return the public URL."""
    if not api_key:
        raise Exception("API Key ImgBB belum dikonfigurasi. Silakan isi di Pengaturan.")
    try:
        url = "https://api.imgbb.com/1/upload"
        data = {
            "key": api_key,
            "image": b64_image
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, data=data, headers=headers)
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("success") and "data" in resp_json:
                    return resp_json["data"]["url"]
            raise Exception(f"ImgBB upload failed: {response.text}")
    except Exception as e:
        raise Exception(f"IMAGE_UPLOAD_ERROR: Gagal mengunggah gambar ke ImgBB — {str(e)}")


async def upload_image(b64_image: str, uploader: str = "catbox", imgbb_api_key: str = "") -> str:
    """Upload base64 image using the specified uploader ('catbox' or 'imgbb')."""
    if uploader.lower() == "imgbb":
        return await upload_to_imgbb(b64_image, imgbb_api_key)
    else:
        return await upload_to_catbox(b64_image)

