"""
AutoBlog AI — Gemini Service
Komunikasi dengan Google Gemini API untuk generate artikel HTML.
"""

import re
from google import genai
from google.genai import types
from typing import Dict

# System prompt baku untuk menghasilkan artikel SEO-friendly
SYSTEM_PROMPT = """Kamu adalah seorang penulis blog profesional dan pakar SEO berbahasa Indonesia.
Tulis artikel mendalam dan informatif tentang topik yang diberikan.

ATURAN KETAT yang WAJIB diikuti:
1. Panjang artikel MINIMAL 800 kata, IDEAL 1000-1500 kata.
2. Format hasil akhir WAJIB MURNI dalam bentuk HTML, TANPA tag markdown ```html```.
3. Baris PERTAMA output HARUS berupa tag <h1> yang berisi judul artikel yang menarik dan SEO-friendly.
4. Gunakan tag <h2> untuk sub-judul pokok dan <h3> untuk sub-poin di dalamnya.
5. Gunakan tag <p> untuk paragraf. Buat paragraf pendek (2-4 kalimat) agar mudah dibaca.
6. Gunakan tag <ul> atau <ol> dengan <li> untuk daftar poin jika relevan.
7. Gunakan tag <strong> untuk menebalkan kata kunci (keyword) penting secara natural.
8. Gunakan tag <em> untuk penekanan ringan.
9. JANGAN tambahkan tag <html>, <head>, <body>, <meta>, atau <style>.
10. JANGAN gunakan CSS inline atau atribut style.
11. JANGAN sertakan gambar atau tag <img>.
12. Tulis dengan gaya bahasa yang natural, informatif, dan engaging — BUKAN seperti robot/spam.
13. Sertakan kesimpulan di akhir artikel dengan tag <h2>Kesimpulan</h2>."""


def _strip_markdown_wrapper(text: str) -> str:
    """Hapus ```html ... ``` wrapper jika ada."""
    # Hapus ```html di awal dan ``` di akhir
    text = re.sub(r'^```html\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text.strip())
    # Hapus ``` generic juga
    text = re.sub(r'^```\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text.strip())
    return text.strip()


def _extract_title(html: str) -> str:
    """Ekstraksi judul dari tag <h1> pertama."""
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if match:
        # Hapus tag HTML dalam judul
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()
    return "Artikel Tanpa Judul"


def _remove_h1(html: str) -> str:
    """Hapus tag <h1> karena Blogger otomatis menampilkan judul post."""
    return re.sub(r'<h1[^>]*>.*?</h1>\s*', '', html, count=1, flags=re.IGNORECASE | re.DOTALL)


def _validate_html(html: str) -> bool:
    """Validasi dasar: cek apakah output mengandung tag esensial."""
    has_h2 = bool(re.search(r'<h2', html, re.IGNORECASE))
    has_p = bool(re.search(r'<p', html, re.IGNORECASE))
    return has_h2 and has_p


async def generate_article(api_key: str, topic: str) -> Dict:
    """
    Generate artikel HTML dari topik menggunakan Gemini API.

    Returns:
        Dict dengan keys: title, html_content, is_valid
    """
    try:
        # Inisialisasi client dengan API key
        client = genai.Client(api_key=api_key)

        # Buat prompt lengkap
        prompt = f"""{SYSTEM_PROMPT}

TOPIK ARTIKEL: {topic}

Tulis artikelnya sekarang:"""

        # Generate konten menggunakan google-genai SDK baru
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=8192,
            ),
        )
        raw_html = response.text

        # Post-processing
        html = _strip_markdown_wrapper(raw_html)
        title = _extract_title(html)
        body_html = _remove_h1(html)
        is_valid = _validate_html(body_html)

        return {
            "title": title,
            "html_content": body_html,
            "is_valid": is_valid,
        }

    except Exception as e:
        error_msg = str(e)

        # Deteksi error spesifik
        if "quota" in error_msg.lower() or "429" in error_msg:
            raise Exception("QUOTA_EXCEEDED: Limit AI tercapai. Silakan coba beberapa saat lagi.")
        elif "api key" in error_msg.lower() or "invalid" in error_msg.lower():
            raise Exception("INVALID_KEY: API Key Gemini tidak valid. Periksa di menu Pengaturan.")
        else:
            raise Exception(f"GEMINI_ERROR: Gagal generate artikel — {error_msg}")
