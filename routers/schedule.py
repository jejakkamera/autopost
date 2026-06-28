"""
AutoBlog AI — Schedule Batch Router
Endpoint untuk menjadwalkan penerbitan batch artikel dwi-bahasa ke Blogger.
"""

import json
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException

from models import ScheduleBatchRequest, ScheduleBatchResponse, ScheduleItemResult
from services.db_service import get_setting, add_history, update_history
from services.ai_service import (
    generate_article, translate_article_to_english,
    generate_tags, generate_image_prompt, PROVIDERS,
)
from services.blogger_service import schedule_post_to_blogger, check_auth_status
from services.image_service import generate_image, upload_to_catbox

router = APIRouter()

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


@router.post("/schedule-batch", response_model=ScheduleBatchResponse)
async def schedule_batch(request: ScheduleBatchRequest):
    """
    Jadwalkan batch artikel dwi-bahasa ke Blogger.

    Untuk setiap topik:
    1. Generate artikel Bahasa Indonesia via chain-of-prompts.
    2. Terjemahkan ke Bahasa Inggris.
    3. Klasifikasi label/tag.
    4. Generate gambar (opsional).
    5. Jadwalkan ke Blogger dengan waktu:
       - Indonesia: jam 09:00 WIB
       - English: jam 15:00 WIB
    6. Topik berikutnya = + interval_days.
    """
    # ── Validasi start_date ──
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "❌ Format tanggal tidak valid. Gunakan format YYYY-MM-DD.",
                "error_code": "INVALID_DATE",
            },
        )

    # Filter topik kosong
    topics = [t.strip() for t in request.topics if t.strip()]
    if not topics:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "❌ Daftar topik tidak boleh kosong.",
                "error_code": "EMPTY_TOPICS",
            },
        )

    # ── Ambil konfigurasi provider ──
    ai_provider = await get_setting("ai_provider") or "gemini"
    ai_model = await get_setting("ai_model") or ""
    if ai_provider not in PROVIDERS:
        ai_provider = "gemini"

    api_key_field = f"{ai_provider}_api_key"
    api_key = await get_setting(api_key_field)
    provider_name = PROVIDERS[ai_provider]["name"]

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": f"⚠️ API Key {provider_name} belum dikonfigurasi.",
                "error_code": "MISSING_API_KEY",
            },
        )

    custom_base_url = None
    if ai_provider == "custom":
        custom_base_url = await get_setting("custom_base_url")
        ai_model = await get_setting("custom_model") or ""

    # Konfigurasi gambar
    image_api_enabled = (await get_setting("image_api_enabled") or "false").lower() == "true"
    image_api_key = await get_setting("image_api_key")
    image_base_url = await get_setting("image_base_url") or "https://api.premzone.co"
    image_model = await get_setting("image_model") or "cx/gpt-5.5"
    image_prompt_template = await get_setting("image_prompt_template") or "A flat style vector illustration of [TOPIK], modern design, vibrant colors, clean background"

    # Blog ID
    blog_id = await get_setting("blog_id")
    if not blog_id:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "⚠️ Blog ID belum diisi.",
                "error_code": "MISSING_BLOG_ID",
            },
        )

    # OAuth
    auth_status = await check_auth_status()
    if not auth_status["connected"]:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "message": "⚠️ Akun Google belum terhubung.",
                "error_code": "AUTH_REQUIRED",
            },
        )

    # ── Proses setiap topik ──
    schedule_results = []
    total_scheduled = 0
    total_failed = 0

    for idx, topic in enumerate(topics):
        # Hitung tanggal rilis untuk topik ini
        release_date = start_date + timedelta(days=idx * request.interval_days)
        iso_id = release_date.replace(hour=9, minute=0, second=0, tzinfo=WIB).isoformat()
        iso_en = release_date.replace(hour=15, minute=0, second=0, tzinfo=WIB).isoformat()

        print(f"\n📅 Memproses topik {idx + 1}/{len(topics)}: \"{topic}\"")
        print(f"   🇮🇩 Indonesia → {iso_id}")
        print(f"   🇬🇧 English   → {iso_en}")

        # ── Generate artikel Indonesia ──
        try:
            article = await generate_article(
                provider=ai_provider,
                api_key=api_key,
                topic=topic,
                model=ai_model or None,
                custom_base_url=custom_base_url,
                search_grounding=request.search_grounding,
            )
            title_id = article["title"]
            html_id = article["html_content"]
            steps = article.get("steps", [])
        except Exception as e:
            error_msg = f"Gagal generate artikel: {str(e)}"
            print(f"   ❌ {error_msg}")
            schedule_results.append(ScheduleItemResult(
                topic=topic, language="Indonesia", status="GAGAL", error=error_msg,
            ))
            if request.dual_language:
                schedule_results.append(ScheduleItemResult(
                    topic=topic, language="English", status="GAGAL", error="Dilewati karena artikel ID gagal.",
                ))
                total_failed += 2
            else:
                total_failed += 1
            continue

        # ── Terjemahkan ke Inggris (jika dual bahasa aktif) ──
        title_en = None
        html_en = None
        if request.dual_language:
            try:
                translation = await translate_article_to_english(
                    provider=ai_provider,
                    api_key=api_key,
                    title=title_id,
                    html_content=html_id,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                )
                title_en = translation["title"]
                html_en = translation["html_content"]
            except Exception as e:
                error_msg = f"Gagal terjemahkan: {str(e)}"
                print(f"   ❌ Translation failed: {error_msg}")

        # ── Klasifikasi tag ──
        try:
            tags = await generate_tags(
                provider=ai_provider,
                api_key=api_key,
                topic=topic,
                model=ai_model or None,
                custom_base_url=custom_base_url,
            )
        except Exception:
            tags = {"tag_id": "Umum", "tag_en": "General"}

        # ── Generate gambar (opsional) ──
        if image_api_enabled and image_api_key:
            try:
                visual_desc = await generate_image_prompt(
                    provider=ai_provider,
                    api_key=api_key,
                    topic=topic,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                )
            except Exception:
                visual_desc = " ".join(topic.split()[:5])

            img_prompt = image_prompt_template.replace("[TOPIK]", visual_desc)
            b64_image = None
            for attempt in range(1, 4):
                try:
                    b64_image = await generate_image(
                        api_key=image_api_key,
                        base_url=image_base_url,
                        model=image_model,
                        prompt=img_prompt,
                    )
                    break
                except Exception as img_err:
                    print(f"   ⚠️ Image attempt {attempt}: {img_err}")
                    if attempt < 3:
                        await asyncio.sleep(1.5)

            if b64_image:
                try:
                    img_url = await upload_to_catbox(b64_image)
                    image_html = f"""
                    <div style="text-align: center; margin-bottom: 24px; width: 100%;">
                        <img src="{img_url}" alt="{title_id}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);" />
                    </div>
                    """
                    html_id = image_html + html_id
                    if html_en:
                        html_en = image_html + html_en
                    print(f"   🖼️ Gambar berhasil: {img_url}")
                except Exception as up_err:
                    print(f"   ⚠️ Upload gambar gagal: {up_err}")

        # ── Publish Indonesia (Scheduled) ──
        labels_id = ["Indonesia", tags["tag_id"]]
        try:
            result_id = await schedule_post_to_blogger(
                blog_id=blog_id,
                title=title_id,
                html_content=html_id,
                published_iso=iso_id,
                labels=labels_id,
            )

            # Simpan ke history
            history_id_id = await add_history(
                topic=topic,
                title=title_id,
                status="TERJADWAL",
                post_id=result_id["post_id"],
                article_url=result_id["article_url"],
                publish_mode="scheduled",
                generation_log=json.dumps(steps),
            )

            schedule_results.append(ScheduleItemResult(
                topic=topic,
                language="Indonesia",
                title=title_id,
                scheduled_at=iso_id,
                post_id=result_id["post_id"],
                article_url=result_id["article_url"],
                labels=labels_id,
                status="TERJADWAL",
            ))
            total_scheduled += 1
            print(f"   ✅ ID scheduled: {iso_id}")

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ ID schedule failed: {error_msg}")
            await add_history(
                topic=topic, title=title_id, status="GAGAL",
                publish_mode="scheduled", error_message=error_msg,
                generation_log=json.dumps(steps),
            )
            schedule_results.append(ScheduleItemResult(
                topic=topic, language="Indonesia", title=title_id,
                scheduled_at=iso_id, labels=labels_id,
                status="GAGAL", error=error_msg,
            ))
            total_failed += 1

        # ── Publish English (Scheduled - jika dual bahasa aktif) ──
        if request.dual_language:
            if title_en and html_en:
                labels_en = ["English", tags["tag_en"]]
                try:
                    result_en = await schedule_post_to_blogger(
                        blog_id=blog_id,
                        title=title_en,
                        html_content=html_en,
                        published_iso=iso_en,
                        labels=labels_en,
                    )

                    await add_history(
                        topic=topic + " (English)",
                        title=title_en,
                        status="TERJADWAL",
                        post_id=result_en["post_id"],
                        article_url=result_en["article_url"],
                        publish_mode="scheduled",
                    )

                    schedule_results.append(ScheduleItemResult(
                        topic=topic,
                        language="English",
                        title=title_en,
                        scheduled_at=iso_en,
                        post_id=result_en["post_id"],
                        article_url=result_en["article_url"],
                        labels=labels_en,
                        status="TERJADWAL",
                    ))
                    total_scheduled += 1
                    print(f"   ✅ EN scheduled: {iso_en}")

                except Exception as e:
                    error_msg = str(e)
                    print(f"   ❌ EN schedule failed: {error_msg}")
                    await add_history(
                        topic=topic + " (English)", title=title_en,
                        status="GAGAL", publish_mode="scheduled",
                        error_message=error_msg,
                    )
                    schedule_results.append(ScheduleItemResult(
                        topic=topic, language="English", title=title_en,
                        scheduled_at=iso_en, labels=labels_en,
                        status="GAGAL", error=error_msg,
                    ))
                    total_failed += 1
            else:
                schedule_results.append(ScheduleItemResult(
                    topic=topic, language="English",
                    status="GAGAL", error="Terjemahan gagal, post EN dilewati.",
                ))
                total_failed += 1

        # Jeda antar topik untuk menghindari rate-limit
        if idx < len(topics) - 1:
            await asyncio.sleep(2)

    # ── Response ──
    overall_status = "success" if total_failed == 0 else ("partial" if total_scheduled > 0 else "error")
    return ScheduleBatchResponse(
        status=overall_status,
        message=f"Berhasil menjadwalkan {total_scheduled} artikel, {total_failed} gagal.",
        total_scheduled=total_scheduled,
        total_failed=total_failed,
        schedule=schedule_results,
    )
