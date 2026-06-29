"""
AutoBlog AI — Scheduler Service
Mengelola background worker untuk memproses antrean artikel terjadwal.
"""

import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict

from services.db_service import (
    get_setting, get_pending_schedule_items, update_schedule_item, add_history
)
from services.ai_service import (
    generate_article, translate_article_to_english,
    generate_tags, generate_image_prompt, PROVIDERS
)
from services.blogger_service import publish_to_blogger
from services.image_service import generate_image, upload_to_catbox

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


async def process_pending_schedule_queue():
    """
    Mengecek antrean jadwalan di database SQLite dan memproses item
    yang waktu rilisnya sudah terlewati (scheduled_at <= waktu sekarang).
    """
    items = await get_pending_schedule_items()
    if not items:
        return

    now_wib = datetime.now(WIB)
    due_items = []

    for item in items:
        try:
            # Parse datetime dengan timezone-aware
            scheduled_dt = datetime.fromisoformat(item["scheduled_at"])
            if scheduled_dt <= now_wib:
                due_items.append(item)
        except Exception as dt_err:
            print(f"⚠️ Scheduler: Gagal membaca tanggal {item['scheduled_at']}: {dt_err}")
            await update_schedule_item(
                item["id"],
                status="GAGAL",
                error_message=f"Format tanggal salah: {dt_err}"
            )

    if not due_items:
        return

    print(f"⏳ Scheduler: Memproses {len(due_items)} postingan terjadwal...")

    # Load konfigurasi umum sekali saja
    ai_provider = await get_setting("ai_provider") or "gemini"
    ai_model = await get_setting("ai_model") or ""
    if ai_provider not in PROVIDERS:
        ai_provider = "gemini"

    api_key_field = f"{ai_provider}_api_key"
    api_key = await get_setting(api_key_field)
    if not api_key:
        print("❌ Scheduler: API Key AI belum dikonfigurasi.")
        return

    custom_base_url = None
    if ai_provider == "custom":
        custom_base_url = await get_setting("custom_base_url")
        ai_model = await get_setting("custom_model") or ""

    blog_id = await get_setting("blog_id")
    if not blog_id:
        print("❌ Scheduler: Blog ID belum dikonfigurasi.")
        return

    image_api_enabled = (await get_setting("image_api_enabled") or "false").lower() == "true"
    image_api_key = await get_setting("image_api_key")
    image_base_url = await get_setting("image_base_url") or "https://api.premzone.co"
    image_model = await get_setting("image_model") or "cx/gpt-5.5"
    image_prompt_template = await get_setting("image_prompt_template") or "A flat style vector illustration of [TOPIK], modern design, vibrant colors, clean background"

    is_draft = (await get_setting("default_status") or "draft").lower() == "draft"

    for item in due_items:
        item_id = item["id"]
        topic = item["topic"]
        language = item["language"]
        search_grounding = item["search_grounding"]

        print(f"🚀 Scheduler: Mulai memproses ID #{item_id} | Bahasa: {language} | Topik: \"{topic}\"")
        await update_schedule_item(item_id, status="GENERATING")

        title = None
        html_content = None
        steps = []

        try:
            if language == "Indonesia":
                # 1. Generate Artikel Indonesia
                article = await generate_article(
                    provider=ai_provider,
                    api_key=api_key,
                    topic=topic,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                    search_grounding=search_grounding,
                )
                title = article["title"]
                html_content = article["html_content"]
                steps = article.get("steps", [])
            else:
                # 2. Generate Artikel Indonesia + Terjemahkan ke Inggris
                article = await generate_article(
                    provider=ai_provider,
                    api_key=api_key,
                    topic=topic,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                    search_grounding=search_grounding,
                )
                title_id = article["title"]
                html_id = article["html_content"]
                steps = article.get("steps", [])

                try:
                    translation = await translate_article_to_english(
                        provider=ai_provider,
                        api_key=api_key,
                        title=title_id,
                        html_content=html_id,
                        model=ai_model or None,
                        custom_base_url=custom_base_url,
                    )
                    title = translation["title"]
                    html_content = translation["html_content"]
                    steps.append({
                        "step": "5. Translator Agent (ID -> EN)",
                        "prompt": "Translate title and HTML content to English.",
                        "response": f"Translated title: {title}",
                        "status": "SUKSES"
                    })
                except Exception as trans_err:
                    steps.append({
                        "step": "5. Translator Agent (ID -> EN)",
                        "prompt": "Translate title and HTML content to English.",
                        "response": f"Error: {str(trans_err)}",
                        "status": "GAGAL"
                    })
                    raise trans_err

            # 3. Klasifikasi Tag/Label
            try:
                tags = await generate_tags(
                    provider=ai_provider,
                    api_key=api_key,
                    topic=topic,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                )
                tag_label = tags["tag_id"] if language == "Indonesia" else tags["tag_en"]
                steps.append({
                    "step": "Classify Tags",
                    "prompt": f"Classify topic: {topic}",
                    "response": f"Tags: {json.dumps(tags)}",
                    "status": "SUKSES"
                })
            except Exception as tag_err:
                tag_label = "Umum" if language == "Indonesia" else "General"
                steps.append({
                    "step": "Classify Tags",
                    "prompt": f"Classify topic: {topic}",
                    "response": f"Failed, fallback to default. Error: {tag_err}",
                    "status": "GAGAL"
                })

            labels = [language, tag_label]

            # 4. Generate Gambar (opsional)
            if image_api_enabled and image_api_key:
                try:
                    visual_desc = await generate_image_prompt(
                        provider=ai_provider,
                        api_key=api_key,
                        topic=topic,
                        model=ai_model or None,
                        custom_base_url=custom_base_url,
                    )
                except Exception as vis_err:
                    print(f"   ⚠️ Scheduler: Failed to generate visual desc: {vis_err}")
                    visual_desc = " ".join(topic.split()[:5])

                img_prompt = image_prompt_template.replace("[TOPIK]", visual_desc)
                b64_image = None
                last_img_err = None
                for attempt in range(1, 4):
                    try:
                        print(f"   🖼️ Scheduler: Attempt {attempt} to generate image for prompt: '{img_prompt}'")
                        b64_image = await generate_image(
                            api_key=image_api_key,
                            base_url=image_base_url,
                            model=image_model,
                            prompt=img_prompt,
                        )
                        break
                    except Exception as img_err:
                        last_img_err = img_err
                        print(f"   ⚠️ Scheduler Image Attempt {attempt} failed: {img_err}")
                        if attempt < 3:
                            await asyncio.sleep(1.5)

                try:
                    if not b64_image:
                        raise last_img_err or Exception("Image generation returned empty.")
                    img_url = await upload_to_catbox(b64_image)
                    image_html = f"""
                    <div style="text-align: center; margin-bottom: 24px; width: 100%;">
                        <img src="{img_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);" />
                    </div>
                    """
                    html_content = image_html + html_content
                    steps.append({
                        "step": "4. Image Generator",
                        "prompt": f"Base URL: {image_base_url}\nModel: {image_model}\nVisual Desc: {visual_desc}\nPrompt: {img_prompt}",
                        "response": f"Image URL: {img_url}",
                        "status": "SUKSES"
                    })
                except Exception as final_img_err:
                    print(f"   ⚠️ Scheduler Image generation/upload failed: {final_img_err}")
                    steps.append({
                        "step": "4. Image Generator",
                        "prompt": f"Base URL: {image_base_url}\nModel: {image_model}\nVisual Desc: {visual_desc}\nPrompt: {img_prompt}",
                        "response": f"Error: {str(final_img_err)}",
                        "status": "GAGAL"
                    })

            # 5. Publikasikan ke Blogger
            result = await publish_to_blogger(
                blog_id=blog_id,
                title=title,
                html_content=html_content,
                is_draft=is_draft,
                labels=labels,
            )
            steps.append({
                "step": f"6. Blogger Publisher ({language})",
                "prompt": f"Publish Mode: {'Draft' if is_draft else 'Live'}\nBlog ID: {blog_id}\nLabels: {', '.join(labels)}",
                "response": f"Post ID: {result['post_id']}\nURL: {result['article_url']}",
                "status": "SUKSES"
            })

            # 6. Simpan ke Riwayat (History)
            await add_history(
                topic=topic + (" (English)" if language == "English" else ""),
                title=title,
                status="SUKSES",
                post_id=result["post_id"],
                article_url=result["article_url"],
                publish_mode="draft" if is_draft else "live",
                generation_log=json.dumps(steps) if steps else None,
            )

            # 7. Update status antrean
            await update_schedule_item(
                item_id=item_id,
                status="SUKSES",
                title=title,
                post_id=result["post_id"],
                article_url=result["article_url"],
            )
            print(f"   ✅ Scheduler: ID #{item_id} sukses dipublikasikan!")

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Scheduler: ID #{item_id} gagal: {error_msg}")
            
            # Simpan status gagal ke Riwayat
            await add_history(
                topic=topic + (" (English)" if language == "English" else ""),
                title=title or "Gagal Terjadwal",
                status="GAGAL",
                publish_mode="draft" if is_draft else "live",
                error_message=error_msg,
                generation_log=json.dumps(steps) if steps else None,
            )

            # Update status antrean
            await update_schedule_item(
                item_id=item_id,
                status="GAGAL",
                error_message=error_msg,
            )

        # Jeda 2 detik antar pemrosesan untuk menjaga rate limit
        await asyncio.sleep(2)
