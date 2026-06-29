"""
AutoBlog AI — AI Service (Multi-Provider)
Mendukung: Google Gemini, DeepSeek, OpenAI (GPT).
Menjalankan Multi-Agent Chain of Prompts (SEO Strategist -> Content Writer -> Web Publisher).
"""

import re
import httpx
import asyncio
from google import genai
from google.genai import types
from typing import Dict

# ============================================
# Daftar Provider yang didukung
# ============================================
PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "models": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Cepat)"},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Terbaru)"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (Detail)"},
        ],
        "default_model": "gemini-2.0-flash",
        "key_placeholder": "AIzaSy...",
        "key_url": "https://aistudio.google.com/apikey",
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V4 Pro (Chat)"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner (R2)"},
        ],
        "default_model": "deepseek-chat",
        "key_placeholder": "sk-...",
        "key_url": "https://platform.deepseek.com/api_keys",
        "base_url": "https://api.deepseek.com",
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o (Balanced)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Cepat)"},
            {"id": "o3-mini", "name": "o3-mini (Reasoning)"},
        ],
        "default_model": "gpt-4o",
        "key_placeholder": "sk-proj-...",
        "key_url": "https://platform.openai.com/api-keys",
        "base_url": "https://api.openai.com",
    },
    "sumopod": {
        "name": "SumoPod AI",
        "models": [
            {"id": "gpt-5.4", "name": "gpt-5.4 (Recomended)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (SumoPod)"},
            {"id": "gpt-4o", "name": "GPT-4o (SumoPod)"},
        ],
        "default_model": "gpt-5.4",
        "key_placeholder": "sk-...",
        "key_url": "https://ai.sumopod.com",
        "base_url": "https://ai.sumopod.com",
    },
    "bynara": {
        "name": "Bynara Router",
        "models": [
            {"id": "mimo-v2.5-pro-free", "name": "Mimo v2.5 Pro Free (Reasoning)"},
            {"id": "mimo-v2.5-free", "name": "Mimo v2.5 Free (Reasoning)"},
            {"id": "mistral-large", "name": "Mistral Large (Cepat & Akurat)"},
            {"id": "mistral-medium-3-5", "name": "Mistral Medium 3.5 (Cepat)"},
        ],
        "default_model": "mimo-v2.5-pro-free",
        "key_placeholder": "sk-nry-...",
        "key_url": "https://router.bynara.id",
        "base_url": "https://router.bynara.id/v1",
    },
    "dahono": {
        "name": "Dahono Labs",
        "models": [
            {"id": "dahono/deepseek-v4-flash", "name": "DeepSeek V4 Flash (Free)"},
            {"id": "dahono/deepseek-v3.2", "name": "DeepSeek V3.2 (Free)"},
            {"id": "dahono/ai-chat", "name": "Dahono AI Chat (Free)"},
            {"id": "dahono/deepseek-v4-pro", "name": "DeepSeek V4 Pro (Paid)"},
        ],
        "default_model": "dahono/deepseek-v4-flash",
        "key_placeholder": "dahono-...",
        "key_url": "https://labs.dahono.com/gateway/docs",
        "base_url": "https://gateway.dahono.com/v1",
    },
    "custom": {
        "name": "Custom (OpenAI Compatible)",
        "models": [],
        "default_model": "",
        "key_placeholder": "sk-...",
        "key_url": "#",
        "base_url": "",
    },
}

# ============================================
# Post-Processing
# ============================================
def _strip_markdown_wrapper(text: str) -> str:
    """Hapus ```html ... ``` wrapper dan teks pengantar/penutup jika ada."""
    text_clean = text.strip()
    
    # Cari pola ```html ... ``` atau ``` ... ``` secara non-greedy
    match = re.search(r'```(?:html)?\s*(.*?)\s*```', text_clean, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # Jika tidak ada block ```, bersihkan wrapper di awal/akhir secara standar
    text_clean = re.sub(r'^```html\s*\n?', '', text_clean)
    text_clean = re.sub(r'\n?```\s*$', '', text_clean)
    text_clean = re.sub(r'^```\s*\n?', '', text_clean)
    text_clean = re.sub(r'\n?```\s*$', '', text_clean)
    return text_clean.strip()


def _extract_title(html: str, default_title: str) -> str:
    """Ekstraksi judul dari tag <h1> pertama, atau fallback ke <h2>, atau default."""
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()

    match_h2 = re.search(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)
    if match_h2:
        title = re.sub(r'<[^>]+>', '', match_h2.group(1))
        return title.strip()

    return default_title


def _remove_h1(html: str) -> str:
    """Hapus tag <h1> karena Blogger otomatis menampilkan judul post."""
    return re.sub(r'<h1[^>]*>.*?</h1>\s*', '', html, count=1, flags=re.IGNORECASE | re.DOTALL)


def _validate_html(html: str) -> bool:
    """Validasi dasar: cek apakah output mengandung tag esensial."""
    has_h2 = bool(re.search(r'<h2', html, re.IGNORECASE))
    has_p = bool(re.search(r'<p', html, re.IGNORECASE))
    return has_h2 and has_p


def _post_process(raw_html: str, default_title: str, provider_name: str = None, model_name: str = None) -> Dict:
    """Post-process HTML dari AI: strip wrapper, extract title, remove h1, append AI watermark."""
    html = _strip_markdown_wrapper(raw_html)
    title = _extract_title(html, default_title)
    body_html = _remove_h1(html)
    is_valid = _validate_html(body_html)

    # Tambahkan tanda/signature AI pembuat di akhir artikel
    if provider_name and model_name:
        watermark = f"""
        <p style="font-size: 0.85em; color: #7f8c8d; font-style: italic; margin-top: 32px; border-top: 1px solid #e0e0e0; padding-top: 12px;">
            Artikel ini ditulis oleh kecerdasan buatan (AI) menggunakan model <strong>{model_name}</strong> via <strong>{provider_name}</strong>.
        </p>
        """
        body_html = body_html.rstrip() + watermark

    return {"title": title, "html_content": body_html, "is_valid": is_valid}


# ============================================
# API Call Handlers (Google GenAI & OpenAI SDK)
# ============================================

async def _call_gemini(
    api_key: str, system_prompt: str, user_prompt: str, model: str, search_grounding: bool = False
) -> str:
    """Panggil Gemini API menggunakan google-genai SDK terbaru dengan dukungan grounding search."""
    client = genai.Client(api_key=api_key)
    
    tools = None
    if search_grounding:
        tools = [{"google_search": {}}]

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=8192,
            tools=tools,
        ),
    )
    return response.text


async def _call_openai_compatible(
    api_key: str, system_prompt: str, user_prompt: str, model: str, base_url: str
) -> str:
    """Panggil OpenAI-compatible API (OpenAI, DeepSeek, SumoPod, Custom) secara streaming untuk menghindari Cloudflare Timeout."""
    base_url = base_url.rstrip("/")
    if base_url.endswith("/v1"):
        url = f"{base_url}/chat/completions"
    else:
        url = f"{base_url}/v1/chat/completions"
    api_key_clean = api_key.strip()
    if api_key_clean.lower().startswith("bearer "):
        api_key_clean = api_key_clean[7:].strip()

    headers = {
        "Authorization": f"Bearer {api_key_clean}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 8192,
        "stream": True,  # Mengaktifkan streaming
    }

    content_chunks = []
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code == 429:
                    raise Exception("QUOTA_EXCEEDED: Limit API provider tercapai. Coba lagi nanti.")
                elif response.status_code == 401:
                    raise Exception("INVALID_KEY: API Key tidak valid. Periksa di menu Pengaturan.")
                elif response.status_code != 200:
                    error_body = await response.aread()
                    error_msg = error_body.decode("utf-8", errors="ignore")[:200]
                    if error_msg.strip().startswith("<!DOCTYPE") or "cloudflare" in error_msg.lower():
                        error_msg = "Cloudflare Timeout / Block (Kemungkinan penulisan nama Model salah, server lambat/down, atau limit IP terpicu)"
                    raise Exception(f"API_ERROR: {error_msg}")

                import json
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    content_chunks.append(content)
                        except Exception:
                            pass
        except httpx.HTTPError as he:
            raise Exception(f"HTTP_CONNECTION_ERROR: Gagal terhubung ke API provider ({he})")

    return "".join(content_chunks)


async def _call_llm(
    provider: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str,
    base_url: str = None,
    search_grounding: bool = False,
) -> str:
    """Router pemanggilan LLM berdasarkan provider yang dipilih dengan dukungan grounding."""
    if provider == "gemini":
        return await _call_gemini(api_key, system_prompt, user_prompt, model, search_grounding)
    elif provider in ("deepseek", "openai", "sumopod", "bynara", "dahono", "custom"):
        return await _call_openai_compatible(api_key, system_prompt, user_prompt, model, base_url)
    else:
        raise Exception(f"INVALID_PROVIDER: Provider '{provider}' tidak didukung.")


# ============================================
# Main Entry Point: Chain of Prompts (Multi-Agent)
# ============================================

async def generate_article(
    provider: str,
    api_key: str,
    topic: str,
    model: str = None,
    custom_base_url: str = None,
    search_grounding: bool = False,
) -> Dict:
    """
    Generate artikel HTML melalui proses Chain of Prompts (Multi-Agent).

    Langkah 1: SEO Strategist -> Membuat kerangka artikel.
    Langkah 2: Content Writer  -> Menulis artikel blog berdasarkan kerangka.
    Langkah 3: Web Publisher   -> Mengonversi artikel menjadi format HTML bersih.
    """
    if provider not in PROVIDERS:
        raise Exception(f"INVALID_PROVIDER: Provider '{provider}' tidak didukung.")

    if not model and provider != "custom":
        model = PROVIDERS[provider]["default_model"]

    # Set base URL
    base_url = None
    if provider in ("deepseek", "openai", "sumopod", "bynara", "dahono"):
        base_url = PROVIDERS[provider]["base_url"]
    elif provider == "custom":
        if not custom_base_url:
            raise Exception("API_ERROR: Custom Base URL tidak boleh kosong.")
        base_url = custom_base_url.rstrip("/")

    steps = []
    try:
        # ── Langkah 1: Role = SEO Strategist ──
        system_1 = "Kamu adalah SEO Strategist."
        prompt_1 = f"Buat kerangka artikel H2 dan H3 dari topik {topic}. Batasi maksimal 4 tag H2 saja, masing-masing dengan maksimal 2 tag H3. Jangan beri basa-basi, hanya output daftar."
        try:
            outline = await _call_llm(provider, api_key, system_1, prompt_1, model, base_url, search_grounding)
            steps.append({
                "step": "1. SEO Strategist",
                "prompt": f"System Instruction: {system_1}\nUser Prompt: {prompt_1}",
                "response": outline,
                "status": "SUKSES"
            })
        except Exception as e1:
            steps.append({
                "step": "1. SEO Strategist",
                "prompt": f"System Instruction: {system_1}\nUser Prompt: {prompt_1}",
                "response": str(e1) or type(e1).__name__,
                "status": "GAGAL"
            })
            raise e1

        # Berikan jeda waktu untuk menghindari rate limit / deteksi bot dari Cloudflare
        await asyncio.sleep(3)

        # ── Langkah 2: Role = Content Writer ──
        system_2 = "Kamu adalah Content Writer."
        prompt_2 = f"Tulis artikel blog berkualitas tinggi dan terfokus berdasarkan kerangka ini: {outline}. Tulis secara padat dan humanis (hindari basa-basi berlebih). Jangan gunakan HTML dulu, KECUALI jika perlu menyematkan peta lokasi, gunakan penanda khusus format: [MAPS: Nama Lokasi atau Alamat Lengkap]."
        try:
            raw_article = await _call_llm(provider, api_key, system_2, prompt_2, model, base_url, search_grounding)
            steps.append({
                "step": "2. Content Writer",
                "prompt": f"System Instruction: {system_2}\nUser Prompt: {prompt_2}",
                "response": raw_article,
                "status": "SUKSES"
            })
        except Exception as e2:
            steps.append({
                "step": "2. Content Writer",
                "prompt": f"System Instruction: {system_2}\nUser Prompt: {prompt_2}",
                "response": str(e2) or type(e2).__name__,
                "status": "GAGAL"
            })
            raise e2

        # Berikan jeda waktu sebelum memformat ke HTML
        await asyncio.sleep(3)

        # ── Langkah 3: Role = Web Publisher ──
        system_3 = "Kamu adalah Web Publisher."
        prompt_3 = f"Ubah artikel berikut menjadi murni HTML. Gunakan tag HTML standar untuk postingan blog seperti <h2>, <h3>, <h4>, <p>, <strong>, <b>, <em>, <i>, <u>, <ul>, <ol>, <li>, <a> (untuk link / tautan rujukan / referral), <img> (gambar), <iframe> (untuk video YouTube atau peta Google Maps), <blockquote> (kutipan), <br> (baris baru), serta <table>, <thead>, <tbody>, <tr>, <th>, <td> (untuk tabel perbandingan/data). JIKA menemukan penanda peta seperti [MAPS: Nama Lokasi], ubahlah penanda tersebut menjadi tag <iframe> Google Maps dengan format: <iframe src=\"https://maps.google.com/maps?q=Nama+Lokasi+Disini&output=embed\" width=\"100%\" height=\"450\" style=\"border:0;\" allowfullscreen=\"\" loading=\"lazy\"></iframe>. JANGAN sertakan markdown ```html, dan jangan sertakan <html>, <head>, atau <body>. Teks: {raw_article}"
        try:
            final_html = await _call_llm(provider, api_key, system_3, prompt_3, model, base_url, False)
            steps.append({
                "step": "3. Web Publisher",
                "prompt": f"System Instruction: {system_3}\nUser Prompt: {prompt_3}",
                "response": final_html,
                "status": "SUKSES"
            })
        except Exception as e3:
            steps.append({
                "step": "3. Web Publisher",
                "prompt": f"System Instruction: {system_3}\nUser Prompt: {prompt_3}",
                "response": str(e3) or type(e3).__name__,
                "status": "GAGAL"
            })
            raise e3

        # Post-processing dan validasi HTML
        provider_name = PROVIDERS.get(provider, {}).get("name", provider)
        processed = _post_process(final_html, topic, provider_name, model)
        return {
            "title": processed["title"],
            "html_content": processed["html_content"],
            "is_valid": processed["is_valid"],
            "steps": steps
        }

    except Exception as e:
        error_msg = str(e) or type(e).__name__
        raised_exc = None
        if "quota" in error_msg.lower() or "429" in error_msg:
            raised_exc = Exception("QUOTA_EXCEEDED: Limit AI provider tercapai. Silakan coba beberapa saat lagi.")
        elif "api key" in error_msg.lower() or "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower():
            raised_exc = Exception("INVALID_KEY: API Key tidak valid. Periksa di menu Pengaturan.")
        else:
            raised_exc = Exception(f"AI_GENERATOR_ERROR: Gagal memproses Chain of Prompts — {error_msg}")
        
        raised_exc.steps = steps
        raise raised_exc


async def translate_article_to_english(
    provider: str,
    api_key: str,
    title: str,
    html_content: str,
    model: str = None,
    custom_base_url: str = None,
) -> Dict[str, str]:
    """Terjemahkan judul dan konten HTML dari Bahasa Indonesia ke Bahasa Inggris."""
    # Set default model
    if not model and provider != "custom":
        model = PROVIDERS[provider]["default_model"]

    base_url = None
    if provider in ("deepseek", "openai", "sumopod", "bynara", "dahono"):
        base_url = PROVIDERS[provider]["base_url"]
    elif provider == "custom":
        base_url = custom_base_url.rstrip("/")

    system_prompt = "Kamu adalah Translator profesional bahasa Indonesia ke bahasa Inggris."
    user_prompt = f"""Terjemahkan judul dan artikel HTML berikut dari Bahasa Indonesia ke Bahasa Inggris secara alami, profesional, dan pertahankan seluruh tag HTML (termasuk tag <iframe>, <a>, <img>, dll) dengan sempurna.

Judul Asli: {title}
Konten HTML Asli: {html_content}

Kembalikan hasil terjemahan dalam format JSON murni seperti ini (JANGAN gunakan markdown ```json, hanya JSON murni):
{{
  "title": "Terjemahan Judul Disini",
  "html_content": "Terjemahan Konten HTML Disini"
}}"""

    response_text = await _call_llm(provider, api_key, system_prompt, user_prompt, model, base_url, False)
    
    # Post-process JSON
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        import json
        data = json.loads(cleaned)
        translated_title = data.get("title", title)
        translated_html = data.get("html_content", html_content)
        
        provider_name = PROVIDERS.get(provider, {}).get("name", provider)
        if provider_name and model:
            watermark = f"""
            <p style="font-size: 0.85em; color: #7f8c8d; font-style: italic; margin-top: 32px; border-top: 1px solid #e0e0e0; padding-top: 12px;">
                This article was translated by Artificial Intelligence (AI) using <strong>{model}</strong> via <strong>{provider_name}</strong>.
            </p>
            """
            translated_html = translated_html.rstrip() + watermark
            
        return {
            "title": translated_title,
            "html_content": translated_html
        }
    except Exception:
        # Fallback jika parsing gagal
        print("⚠️ Gagal mem-parse JSON hasil terjemahan. Menggunakan fallback parsial.")
        raise Exception("Gagal mem-parse respon JSON dari Translator agent.")


async def generate_tags(
    provider: str,
    api_key: str,
    topic: str,
    model: str = None,
    custom_base_url: str = None,
) -> Dict[str, str]:
    """Hasilkan kategori/label artikel yang sesuai berdasarkan topik."""
    if not model and provider != "custom":
        model = PROVIDERS[provider]["default_model"]

    base_url = None
    if provider in ("deepseek", "openai", "sumopod", "bynara", "dahono"):
        base_url = PROVIDERS[provider]["base_url"]
    elif provider == "custom":
        base_url = custom_base_url.rstrip("/")

    system_prompt = "Kamu adalah SEO Classifier."
    user_prompt = f"""Klasifikasikan topik artikel berikut ke dalam SATU kategori umum/label (maksimal 2 kata).
Berikan hasil dalam Bahasa Indonesia dan terjemahannya dalam Bahasa Inggris.

Topik: {topic}

Kembalikan hasil dalam format JSON murni seperti ini (JANGAN gunakan markdown ```json):
{{
  "tag_id": "Kategori Bahasa Indonesia",
  "tag_en": "Category in English"
}}"""

    response_text = await _call_llm(provider, api_key, system_prompt, user_prompt, model, base_url, False)
    
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        import json
        data = json.loads(cleaned)
        return {
            "tag_id": data.get("tag_id", "Lainnya").strip(),
            "tag_en": data.get("tag_en", "Others").strip()
        }
    except Exception:
        return {"tag_id": "Umum", "tag_en": "General"}


async def generate_image_prompt(
    provider: str,
    api_key: str,
    topic: str,
    model: str = None,
    custom_base_url: str = None,
) -> str:
    """Ekstrak/buat deskripsi ilustrasi visual singkat berbahasa Inggris dari topik artikel."""
    if not model and provider != "custom":
        model = PROVIDERS[provider]["default_model"]

    base_url = None
    if provider in ("deepseek", "openai", "sumopod", "bynara", "dahono"):
        base_url = PROVIDERS[provider]["base_url"]
    elif provider == "custom":
        base_url = custom_base_url.rstrip("/")

    system_prompt = "Kamu adalah Art Director profesional."
    user_prompt = f"""Buat 1 baris deskripsi visual singkat (maksimal 10-15 kata) dalam Bahasa Inggris yang sangat cocok dijadikan prompt ilustrasi gambar artikel untuk topik berikut.
Jangan sertakan instruksi penulisan, link, HTML, atau angka. Hanya deskripsi visual murni.

Topik: {topic}

Output hanya 1 baris deskripsi visual tersebut."""

    response_text = await _call_llm(provider, api_key, system_prompt, user_prompt, model, base_url, False)
    
    # Bersihkan response
    clean_prompt = response_text.strip().replace('"', '').replace("'", "")
    # Batasi panjang kata jika masih kepanjangan
    words = clean_prompt.split()
    if len(words) > 20:
        clean_prompt = " ".join(words[:20])
        
    return clean_prompt


def get_providers_info() -> Dict:
    """Mengembalikan informasi semua provider untuk frontend."""
    return {
        key: {
            "name": val["name"],
            "models": val["models"],
            "default_model": val["default_model"],
            "key_placeholder": val["key_placeholder"],
            "key_url": val["key_url"],
            "base_url": val.get("base_url", ""),
        }
        for key, val in PROVIDERS.items()
    }
