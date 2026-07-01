"""
AutoBlog AI — Make.com Webhook Service
Mengirimkan notifikasi POST ke Make.com webhook setelah artikel berhasil dipublikasikan.
Non-blocking: kegagalan webhook tidak akan menggagalkan proses publish.
"""

import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional, List

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


async def send_make_webhook(
    webhook_url: str,
    title: str,
    article_url: str,
    topic: str,
    labels: Optional[List[str]] = None,
    language: str = "Indonesia",
) -> dict:
    """
    Mengirimkan data postingan baru ke Make.com webhook URL.

    Returns:
        dict: {"success": True/False, "message": "...", "status_code": int}
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return {"success": False, "message": "Webhook URL tidak valid.", "status_code": 0}

    payload = {
        "event": "new_post",
        "title": title,
        "url": article_url,
        "topic": topic,
        "labels": labels or [],
        "language": language,
        "published_at": datetime.now(WIB).isoformat(),
    }

    # Coba kirim maksimal 2 kali (1 retry)
    last_error = None
    for attempt in range(1, 3):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code in (200, 201, 202, 204):
                print(f"   📤 Webhook: Berhasil dikirim ke Make.com (status {response.status_code})")
                return {
                    "success": True,
                    "message": f"Webhook berhasil dikirim (HTTP {response.status_code}).",
                    "status_code": response.status_code,
                }
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"   ⚠️ Webhook Attempt {attempt}: {last_error}")

        except httpx.TimeoutException:
            last_error = "Request timeout (15 detik)"
            print(f"   ⚠️ Webhook Attempt {attempt}: Timeout")
        except Exception as e:
            last_error = str(e)
            print(f"   ⚠️ Webhook Attempt {attempt}: {last_error}")

    print(f"   ❌ Webhook: Gagal setelah 2 percobaan. Error terakhir: {last_error}")
    return {
        "success": False,
        "message": f"Webhook gagal: {last_error}",
        "status_code": 0,
    }


async def test_make_webhook(webhook_url: str) -> dict:
    """
    Mengirimkan payload dummy untuk menguji koneksi webhook Make.com.

    Returns:
        dict: {"success": True/False, "message": "..."}
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return {"success": False, "message": "Webhook URL tidak valid. Pastikan dimulai dengan https://"}

    payload = {
        "event": "test",
        "title": "🧪 Test Webhook dari AutoBlog AI",
        "url": "https://example.com/test-article",
        "topic": "Test Koneksi Webhook",
        "labels": ["Test", "AutoBlog AI"],
        "language": "Indonesia",
        "published_at": datetime.now(WIB).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code in (200, 201, 202, 204):
            return {
                "success": True,
                "message": f"Koneksi berhasil! Make.com merespon HTTP {response.status_code}. Cek Scenario Make.com Anda untuk melihat data yang diterima.",
            }
        else:
            return {
                "success": False,
                "message": f"Make.com merespon HTTP {response.status_code}. Pastikan Scenario Make.com sudah aktif dan webhook URL benar.",
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "Request timeout. Pastikan URL webhook valid dan Make.com dapat diakses.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal mengirim: {str(e)}",
        }
