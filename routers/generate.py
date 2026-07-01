"""
AutoBlog AI — Generate Router
Endpoint inti: orkestrasi AI → post-process → Blogger publish → simpan history.
Mendukung multi-provider: Gemini, DeepSeek, OpenAI.
"""

import json
from fastapi import APIRouter, HTTPException
from models import GenerateRequest, GenerateResponse
from services.db_service import get_setting, add_history, update_history
from services.ai_service import generate_article, translate_article_to_english, generate_tags, generate_image_prompt, PROVIDERS
from services.blogger_service import publish_to_blogger, check_auth_status
from services.image_service import generate_image, upload_image
from services.webhook_service import send_make_webhook

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_and_publish(request: GenerateRequest):
    """
    Proses inti:
    1. Validasi konfigurasi (provider + API key + Blog ID + OAuth)
    2. Generate artikel via AI provider yang dipilih
    3. Generate gambar jika diaktifkan (via Premzone)
    4. Publish ke Blogger API
    5. Simpan ke history
    """
    topic = request.topic.strip()
    is_draft = request.status.lower() == "draft"

    # ── Ambil konfigurasi provider ──
    ai_provider = await get_setting("ai_provider") or "gemini"
    ai_model = await get_setting("ai_model") or ""

    if ai_provider not in PROVIDERS:
        ai_provider = "gemini"

    # ── Ambil API key sesuai provider ──
    api_key_field = f"{ai_provider}_api_key"
    api_key = await get_setting(api_key_field)
    provider_name = PROVIDERS[ai_provider]["name"]

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": f"⚠️ API Key {provider_name} belum dikonfigurasi. Silakan isi di menu Pengaturan.",
                "error_code": "MISSING_API_KEY",
            },
        )

    # Ambil custom settings jika custom provider
    custom_base_url = None
    if ai_provider == "custom":
        custom_base_url = await get_setting("custom_base_url")
        ai_model = await get_setting("custom_model") or ""

    # Ambil konfigurasi gambar
    image_api_enabled = (await get_setting("image_api_enabled") or "false").lower() == "true"
    image_api_key = await get_setting("image_api_key")
    image_base_url = await get_setting("image_base_url") or "https://api.premzone.co"
    image_model = await get_setting("image_model") or "cx/gpt-5.5"
    image_prompt_template = await get_setting("image_prompt_template") or "A flat style vector illustration of [TOPIK], modern design, vibrant colors, clean background"
    image_uploader = await get_setting("image_uploader") or "catbox"
    imgbb_api_key = await get_setting("imgbb_api_key") or ""

    if image_api_enabled and not image_api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "⚠️ API Key Generator Gambar diaktifkan tetapi belum diisi. Silakan isi di menu Pengaturan Gambar.",
                "error_code": "MISSING_IMAGE_KEY",
            },
        )

    # ── Validasi Blog ID ──
    blog_id = await get_setting("blog_id")
    if not blog_id:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "⚠️ Blog ID belum diisi. Silakan isi di menu Pengaturan.",
                "error_code": "MISSING_BLOG_ID",
            },
        )

    # ── Cek OAuth status ──
    auth_status = await check_auth_status()
    if not auth_status["connected"]:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "message": "⚠️ Akun Google belum terhubung. Silakan klik 'Connect to Google' di Pengaturan.",
                "error_code": "AUTH_REQUIRED",
            },
        )

    # ── Buat entry history (PENDING) ──
    history_id = await add_history(
        topic=topic,
        status="PENDING",
        publish_mode="draft" if is_draft else "live",
    )

    if request.dual_language:
        history_id_en = await add_history(
            topic=topic + " (English)",
            status="PENDING",
            publish_mode="draft" if is_draft else "live",
        )

    try:
        # ── Step 1: Generate artikel via AI ──
        article = await generate_article(
            provider=ai_provider,
            api_key=api_key,
            topic=topic,
            model=ai_model or None,
            custom_base_url=custom_base_url,
            search_grounding=request.search_grounding or False,
        )
        title = article["title"]
        html_content = article["html_content"]
        steps = article["steps"]

        # ── Step 2: Klasifikasi Label/Tags ──
        try:
            tags = await generate_tags(
                provider=ai_provider,
                api_key=api_key,
                topic=topic,
                model=ai_model or None,
                custom_base_url=custom_base_url,
            )
            steps.append({
                "step": "Classify Tags",
                "prompt": f"Classify topic: {topic}",
                "response": f"Tags: {json.dumps(tags)}",
                "status": "SUKSES"
            })
        except Exception as tag_err:
            print(f"⚠️ Tag classification failed: {tag_err}")
            tags = {"tag_id": "Umum", "tag_en": "General"}
            steps.append({
                "step": "Classify Tags",
                "prompt": f"Classify topic: {topic}",
                "response": f"Failed, fallback to default. Error: {tag_err}",
                "status": "GAGAL"
            })

        # ── Step 3: Generate Gambar jika diaktifkan ──
        if image_api_enabled:
            # Ambil deskripsi visual singkat terlebih dahulu agar prompt gambar bersih
            try:
                visual_desc = await generate_image_prompt(
                    provider=ai_provider,
                    api_key=api_key,
                    topic=topic,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                )
            except Exception as e_vis:
                print(f"⚠️ Failed to generate visual desc: {e_vis}")
                visual_desc = " ".join(topic.split()[:5])

            prompt = image_prompt_template.replace("[TOPIK]", visual_desc)
            
            # Coba generate gambar maksimal 3 kali jika terjadi error
            b64_image = None
            last_img_err = None
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"🖼️ Attempt {attempt} to generate image for prompt: '{prompt}'")
                    b64_image = await generate_image(
                        api_key=image_api_key,
                        base_url=image_base_url,
                        model=image_model,
                        prompt=prompt,
                    )
                    break
                except Exception as img_err:
                    last_img_err = img_err
                    print(f"⚠️ Attempt {attempt} failed: {img_err}")
                    if attempt < max_attempts:
                        import asyncio
                        await asyncio.sleep(1.5)

            try:
                if not b64_image:
                    raise last_img_err or Exception("Image generation returned empty.")

                img_url = None
                last_upload_err = None
                for upload_attempt in range(1, 4):
                    try:
                        print(f"☁️ Attempt {upload_attempt} to upload image via {image_uploader}...")
                        img_url = await upload_image(
                            b64_image=b64_image,
                            uploader=image_uploader,
                            imgbb_api_key=imgbb_api_key
                        )
                        break
                    except Exception as upload_err:
                        last_upload_err = upload_err
                        print(f"⚠️ Upload Attempt {upload_attempt} failed: {upload_err}")
                        if upload_attempt < 3:
                            import asyncio
                            await asyncio.sleep(1.5)

                if not img_url:
                    raise last_upload_err or Exception("Image upload failed after 3 attempts.")
                
                # Prepend img tag ke html_content menggunakan link publik
                image_html = f"""
                <div style="text-align: center; margin-bottom: 24px; width: 100%;">
                    <img src="{img_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);" />
                </div>
                """
                html_content = image_html + html_content
                
                steps.append({
                    "step": "4. Image Generator",
                    "prompt": f"Base URL: {image_base_url}\nModel: {image_model}\nVisual Desc: {visual_desc}\nPrompt: {prompt}\nUploader: {image_uploader}",
                    "response": f"Image URL: {img_url}",
                    "status": "SUKSES"
                })
            except Exception as final_img_err:
                print(f"⚠️ Image generation/upload failed: {final_img_err}")
                steps.append({
                    "step": "4. Image Generator",
                    "prompt": f"Base URL: {image_base_url}\nModel: {image_model}\nVisual Desc: {visual_desc}\nPrompt: {prompt}\nUploader: {image_uploader}",
                    "response": f"Error: {str(final_img_err)}",
                    "status": "GAGAL"
                })

        # ── Step 4: Terjemahkan ke Bahasa Inggris (jika dual bahasa aktif) ──
        if request.dual_language:
            steps_en = list(steps)
            try:
                translation = await translate_article_to_english(
                    provider=ai_provider,
                    api_key=api_key,
                    title=title,
                    html_content=html_content,
                    model=ai_model or None,
                    custom_base_url=custom_base_url,
                )
                title_en = translation["title"]
                html_content_en = translation["html_content"]

                steps.append({
                    "step": "5. Translator Agent (ID -> EN)",
                    "prompt": f"Translate title and HTML content to English.",
                    "response": f"Translated title: {title_en}",
                    "status": "SUKSES"
                })
                steps_en.append({
                    "step": "5. Translator Agent (ID -> EN)",
                    "prompt": f"Translate title and HTML content to English.",
                    "response": f"Translated title: {title_en}",
                    "status": "SUKSES"
                })
            except Exception as trans_err:
                steps.append({
                    "step": "5. Translator Agent (ID -> EN)",
                    "prompt": f"Translate title and HTML content to English.",
                    "response": f"Error: {str(trans_err)}",
                    "status": "GAGAL"
                })
                raise trans_err

        # ── Step 5: Publish Indonesia ke Blogger ──
        try:
            result_id = await publish_to_blogger(
                blog_id=blog_id,
                title=title,
                html_content=html_content,
                is_draft=is_draft,
                labels=["Indonesia", tags["tag_id"]]
            )
            steps.append({
                "step": "6. Blogger Publisher (Indonesia)",
                "prompt": f"Publish Mode: {'Draft' if is_draft else 'Live'}\nBlog ID: {blog_id}\nLabels: Indonesia, {tags['tag_id']}",
                "response": f"Post ID: {result_id['post_id']}\nURL: {result_id['article_url']}",
                "status": "SUKSES"
            })
        except Exception as blog_err:
            steps.append({
                "step": "6. Blogger Publisher (Indonesia)",
                "prompt": f"Publish Mode: {'Draft' if is_draft else 'Live'}\nBlog ID: {blog_id}\nLabels: Indonesia, {tags['tag_id']}",
                "response": f"Error: {str(blog_err)}",
                "status": "GAGAL"
            })
            raise blog_err

        # Update Indonesia History (SUKSES)
        await update_history(
            history_id=history_id,
            title=title,
            status="SUKSES",
            post_id=result_id["post_id"],
            article_url=result_id["article_url"],
            generation_log=json.dumps(steps),
        )

        # ── Webhook: Kirim ke Make.com (Indonesia) ──
        webhook_enabled = (await get_setting("webhook_enabled") or "false").lower() == "true"
        webhook_url = await get_setting("webhook_url") or ""
        if webhook_enabled and webhook_url:
            try:
                wh_result = await send_make_webhook(
                    webhook_url=webhook_url,
                    title=title,
                    article_url=result_id["article_url"],
                    topic=topic,
                    labels=["Indonesia", tags["tag_id"]],
                    language="Indonesia",
                )
                steps.append({
                    "step": "7. Webhook Make.com (Indonesia)",
                    "prompt": f"URL: {webhook_url[:40]}...",
                    "response": wh_result["message"],
                    "status": "SUKSES" if wh_result["success"] else "GAGAL"
                })
            except Exception as wh_err:
                print(f"⚠️ Webhook error (non-blocking): {wh_err}")
                steps.append({
                    "step": "7. Webhook Make.com (Indonesia)",
                    "prompt": f"URL: {webhook_url[:40]}...",
                    "response": f"Error: {str(wh_err)}",
                    "status": "GAGAL"
                })

        # ── Step 6: Publish Inggris ke Blogger (jika dual bahasa aktif) ──
        if request.dual_language:
            try:
                result_en = await publish_to_blogger(
                    blog_id=blog_id,
                    title=title_en,
                    html_content=html_content_en,
                    is_draft=is_draft,
                    labels=["English", tags["tag_en"]]
                )
                steps_en.append({
                    "step": "6. Blogger Publisher (English)",
                    "prompt": f"Publish Mode: {'Draft' if is_draft else 'Live'}\nBlog ID: {blog_id}\nLabels: English, {tags['tag_en']}",
                    "response": f"Post ID: {result_en['post_id']}\nURL: {result_en['article_url']}",
                    "status": "SUKSES"
                })
            except Exception as blog_err_en:
                steps_en.append({
                    "step": "6. Blogger Publisher (English)",
                    "prompt": f"Publish Mode: {'Draft' if is_draft else 'Live'}\nBlog ID: {blog_id}\nLabels: English, {tags['tag_en']}",
                    "response": f"Error: {str(blog_err_en)}",
                    "status": "GAGAL"
                })
                await update_history(
                    history_id=history_id_en,
                    title=title_en,
                    status="GAGAL",
                    error_message=str(blog_err_en),
                    generation_log=json.dumps(steps_en),
                )
                raise blog_err_en

            # Update English History (SUKSES)
            await update_history(
                history_id=history_id_en,
                title=title_en,
                status="SUKSES",
                post_id=result_en["post_id"],
                article_url=result_en["article_url"],
                generation_log=json.dumps(steps_en),
            )

            # ── Webhook: Kirim ke Make.com (English) ──
            if webhook_enabled and webhook_url:
                try:
                    wh_result_en = await send_make_webhook(
                        webhook_url=webhook_url,
                        title=title_en,
                        article_url=result_en["article_url"],
                        topic=topic,
                        labels=["English", tags["tag_en"]],
                        language="English",
                    )
                    steps_en.append({
                        "step": "7. Webhook Make.com (English)",
                        "prompt": f"URL: {webhook_url[:40]}...",
                        "response": wh_result_en["message"],
                        "status": "SUKSES" if wh_result_en["success"] else "GAGAL"
                    })
                except Exception as wh_err_en:
                    print(f"⚠️ Webhook EN error (non-blocking): {wh_err_en}")

        return GenerateResponse(
            status="success",
            title=title if not request.dual_language else f"{title} & {title_en}",
            post_id=result_id["post_id"],
            article_url=result_id["article_url"],
            html_preview=html_content[:2000],
        )

    except Exception as e:
        error_msg = str(e)
        steps = getattr(e, "steps", [])

        # Update history (GAGAL)
        await update_history(
            history_id=history_id,
            status="GAGAL",
            error_message=error_msg,
            generation_log=json.dumps(steps) if steps else None,
        )

        if request.dual_language and 'history_id_en' in locals():
            await update_history(
                history_id=history_id_en,
                status="GAGAL",
                error_message=error_msg,
                generation_log=json.dumps(steps) if steps else None,
            )

        # Tentukan error code
        error_code = "UNKNOWN_ERROR"
        if "QUOTA_EXCEEDED" in error_msg:
            error_code = "QUOTA_EXCEEDED"
        elif "INVALID_KEY" in error_msg:
            error_code = "INVALID_KEY"
        elif "AUTH_REQUIRED" in error_msg:
            error_code = "AUTH_REQUIRED"
        elif "BLOGGER_" in error_msg or "BLOG_" in error_msg:
            error_code = error_msg.split(":")[0]

        clean_msg = error_msg.split(": ", 1)[-1] if ": " in error_msg else error_msg

        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"❌ {clean_msg}",
                "error_code": error_code,
            },
        )
