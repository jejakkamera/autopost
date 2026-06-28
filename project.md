# Product Requirements Document (PRD)
**Nama Proyek:** AutoBlog AI (Blogger Auto-Posting Web App)  
**Dokumen Versi:** 1.1  
**Tanggal Dibuat:** 28 Juni 2026  
**Status:** ✅ Siap Implementasi  

---

## 1. Ringkasan Eksekutif (Executive Summary)

AutoBlog AI adalah aplikasi berbasis web antarmuka ringan (*lightweight*) yang dirancang untuk mengotomatiskan pembuatan dan publikasi konten ke Google Blogger (Blogspot). Dengan memasukkan ide topik sederhana, aplikasi ini memanfaatkan AI (Google Gemini, DeepSeek, atau OpenAI) untuk menyusun artikel berformat HTML SEO-friendly, lalu mempublikasikannya menggunakan Blogger API. Aplikasi ini berjalan secara lokal di perangkat pengguna untuk menjamin keamanan Kredensial API dan dilengkapi dengan sistem login key mandiri.

---

## 2. Latar Belakang & Tujuan

*   **Masalah:** Membuat draf artikel blog membutuhkan waktu riset, penulisan, dan pemformatan HTML yang memakan waktu (rata-rata 1-2 jam per artikel).
*   **Solusi:** Memanfaatkan AI untuk menghemat 90% waktu pengerjaan teknis, menyisakan waktu bagi pengguna murni untuk kurasi dan menentukan ide konten.
*   **Tujuan Utama:** Menciptakan sistem auto-posting yang stabil, anti-ribet, dan menghasilkan *output* tulisan yang tidak terlihat seperti *spam* (terstruktur dengan *Heading*, *List*, dan Paragraf yang baik).

---

## 3. Metrik Kesuksesan (Success Metrics)

| Metrik | Target | Cara Ukur |
| :--- | :--- | :--- |
| Kecepatan Generasi | < 15 detik per artikel (Gemini/OpenAI) | Timestamp di log backend |
| Success Rate Publikasi | > 95% tanpa error | Rasio status `SUKSES` vs `GAGAL` di tabel history |
| Kualitas HTML Output | 100% valid HTML | Tidak ada broken tag di artikel yang dipublikasikan |
| Uptime Lokal | 99% saat dijalankan | Tidak ada crash saat operasi normal |

---

## 4. User Stories

| ID | Sebagai... | Saya ingin... | Agar saya bisa... |
| :--- | :--- | :--- | :--- |
| US-01 | Blogger | Memasukkan topik dan langsung generate artikel | Menghemat waktu menulis konten |
| US-02 | Blogger | Memilih apakah artikel langsung LIVE atau DRAFT | Mengontrol kapan artikel dipublikasikan |
| US-03 | Blogger | Melihat riwayat artikel yang sudah dibuat | Melacak semua konten yang pernah di-generate |
| US-04 | Blogger | Menyimpan API Key dan Blog ID di pengaturan | Tidak perlu input kredensial berulang kali |
| US-05 | Blogger | Melihat preview HTML sebelum posting | Memastikan kualitas artikel sebelum publish |
| US-06 | Blogger | Mendapat notifikasi jika terjadi error | Mengetahui masalah dan cara mengatasinya |
| US-07 | Blogger | Menggunakan AI selain Gemini (misal DeepSeek, GPT) | Memiliki opsi kualitas dan gaya tulisan yang berbeda |
| US-08 | Blogger | Memverifikasi apakah Blog ID valid secara langsung | Mengetahui apakah blog terhubung sebelum posting |
| US-09 | Blogger | Memasukkan password key saat membuka aplikasi | Menjaga keamanan konfigurasi API key lokal saya |

---

## 5. Kebutuhan Fitur (Features Requirements)

| ID Fitur | Kategori | Nama Fitur | Deskripsi Fungsionalitas | Prioritas |
| :--- | :--- | :--- | :--- | :--- |
| **F-01** | Input | Form Topik | Textarea untuk memasukkan ide topik/keyword. | P1 (Wajib) |
| **F-02** | Input | Mode Publikasi | Dropdown/Toggle untuk memilih hasil diposting sebagai `DRAFT` atau `LIVE`. | P1 (Wajib) |
| **F-03** | Core | AI Text Generator | Integrasi API Gemini (Client SDK), DeepSeek, dan OpenAI untuk merombak teks ke artikel lengkap berformat HTML. | P1 (Wajib) |
| **F-04** | Core | Blogger Publisher | Integrasi OAuth2 & Blogger API v3 untuk push artikel HTML ke Blogspot. | P1 (Wajib) |
| **F-05** | UI/UX | Loading State | Animasi/Indikator visual saat sistem sedang menghubungi AI dan Blogspot. | P1 (Wajib) |
| **F-06** | Data | Riwayat (History) | Tabel berisi Tanggal, Topik, Status (Sukses/Gagal), dan Link ke artikel. | P2 (Penting) |
| **F-07** | Config | Pengaturan API | Halaman/Modal untuk input dan simpan Blog ID, AI Provider Keys (Gemini, DeepSeek, OpenAI), dan model ke SQLite lokal. | P1 (Wajib) |
| **F-08** | UI/UX | Preview HTML | Panel preview untuk melihat hasil generate artikel sebelum/sesudah posting. | P2 (Penting) |
| **F-09** | Auth | OAuth2 Flow | Tombol "Connect to Google" untuk memulai alur otorisasi Blogger API. | P1 (Wajib) |
| **F-10** | Core | Blog ID Verification | Tombol "Cek" terpisah untuk memvalidasi keberadaan Blog ID secara real-time. | P1 (Wajib) |
| **F-11** | Security | Simple Auth | Halaman login key mandiri (hashed, session cookies) untuk proteksi akses localhost. | P1 (Wajib) |
| **F-12** | Core | Bulk Generate | Kemampuan memasukkan beberapa topik sekaligus (satu per baris) untuk batch processing. | P3 (Nice-to-have) |

---

## 6. Spesifikasi Teknis (Tech Stack)

### 6.1 Arsitektur Sistem
Sistem menggunakan pendekatan **Monolitik Sederhana** — Frontend & Backend berjalan dalam satu *environment* lokal.

```
┌─────────────────────────────────────────────────────┐
│                   LOCALHOST                          │
│                                                     │
│  ┌──────────────┐       ┌────────────────────────┐  │
│  │   Frontend    │       │       Backend          │  │
│  │  (HTML/JS)    │◄─────►│      (FastAPI)         │  │
│  │  Port: 8000   │ fetch │      Port: 8000        │  │
│  └──────────────┘       │                        │  │
│                          │  ┌──────────────────┐  │  │
│                          │  │    SQLite DB      │  │  │
│                          │  │  (database.db)    │  │  │
│                          │  └──────────────────┘  │  │
│                          └───────────┬────────────┘  │
│                                      │               │
└──────────────────────────────────────┼───────────────┘
                                       │ HTTPS
                          ┌────────────▼────────────┐
                          │    External Services     │
                          │  ┌────────────────────┐  │
                          │  │  Google Gemini API  │  │
                          │  └────────────────────┘  │
                          │  ┌────────────────────┐  │
                          │  │  Blogger API v3    │  │
                          │  └────────────────────┘  │
                          └─────────────────────────┘
```

### 6.2 Technology Stack

| Layer | Teknologi | Versi/Detail |
| :--- | :--- | :--- |
| **Runtime** | Python | 3.10+ |
| **Backend Framework** | FastAPI | Latest (dengan `uvicorn` sebagai ASGI server) |
| **Frontend** | HTML5 + Vanilla JS | ES6+ (`fetch` API, `async/await`) |
| **Styling** | Tailwind CSS | Via CDN (v3.x) |
| **Database** | SQLite | Built-in Python `aiosqlite` untuk async |
| **AI Service** | `google-generativeai` | Gemini 2.0 Flash atau model terbaru |
| **Google Auth** | `google-auth-oauthlib` | Untuk OAuth2 flow |
| **Blogger API** | `google-api-python-client` | Blogger API v3 |
| **Template** | Jinja2 | Untuk serve HTML dari FastAPI |

### 6.3 Dependensi Python (`requirements.txt`)

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
aiosqlite>=0.19.0
google-generativeai>=0.5.0
google-api-python-client>=2.90.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.0
jinja2>=3.1.0
python-dotenv>=1.0.0
```

---

## 7. Struktur Direktori Proyek

```
autopost/
├── project.md                  # Dokumen PRD ini
├── requirements.txt            # Dependensi Python
├── .env.example                # Template environment variables
├── .gitignore                  # Git ignore rules
├── main.py                     # Entry point FastAPI app
├── config.py                   # Konfigurasi aplikasi & environment
├── database.py                 # Inisialisasi & koneksi SQLite
├── models.py                   # Pydantic models (request/response schemas)
├── routers/
│   ├── __init__.py
│   ├── settings.py             # Endpoint: GET/POST /api/settings
│   ├── generate.py             # Endpoint: POST /api/generate
│   └── history.py              # Endpoint: GET /api/history
├── services/
│   ├── __init__.py
│   ├── gemini_service.py       # Logika komunikasi dengan Gemini API
│   ├── blogger_service.py      # Logika OAuth2 & publish ke Blogger
│   └── db_service.py           # CRUD operations ke SQLite
├── static/
│   ├── css/
│   │   └── style.css           # Custom CSS tambahan
│   ├── js/
│   │   └── app.js              # Logika frontend JavaScript
│   └── img/                    # Asset gambar (logo, icons)
├── templates/
│   └── index.html              # Halaman utama (Single Page)
└── credentials/
    └── .gitkeep                # Folder untuk OAuth client_secret.json
```

---

## 8. Skema Database SQLite

### 8.1 Tabel `settings`

Menyimpan konfigurasi API yang diperlukan aplikasi.

```sql
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,          -- Nama setting (e.g., 'gemini_api_key', 'blog_id')
    value TEXT NOT NULL,               -- Nilai setting
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data yang disimpan:**
| key | Deskripsi |
| :--- | :--- |
| `gemini_api_key` | API Key Google Gemini |
| `blog_id` | ID Blog Blogspot target |
| `default_status` | Status default posting: `draft` / `live` |

### 8.2 Tabel `history`

Menyimpan riwayat semua artikel yang pernah di-generate.

```sql
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,                -- Topik/keyword yang diinput user
    title TEXT,                         -- Judul artikel yang dihasilkan AI
    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | SUKSES | GAGAL
    post_id TEXT,                       -- ID post di Blogger (jika sukses)
    article_url TEXT,                   -- URL artikel di Blogspot (jika sukses)
    publish_mode TEXT DEFAULT 'draft',  -- draft | live
    error_message TEXT,                 -- Pesan error (jika gagal)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 8.3 Tabel `oauth_tokens`

Menyimpan token OAuth2 untuk Blogger API agar tidak perlu login berulang.

```sql
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri TEXT,
    client_id TEXT,
    client_secret TEXT,
    expiry TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 9. Desain API Backend (Internal Endpoints)

FastAPI menyediakan endpoint RESTful berikut:

### 9.1 Settings Endpoints

#### `GET /api/settings`
- **Fungsi:** Mengambil semua konfigurasi yang tersimpan.
- **Response:**
```json
{
    "gemini_api_key": "AIza...(masked)",
    "blog_id": "1234567890",
    "default_status": "draft"
}
```

#### `POST /api/settings`
- **Fungsi:** Menyimpan/Update konfigurasi ke SQLite.
- **Payload:**
```json
{
    "gemini_api_key": "AIzaSy...",
    "blog_id": "1234567890",
    "default_status": "draft"
}
```
- **Response:** `{ "status": "success", "message": "Pengaturan berhasil disimpan." }`

### 9.2 Generate Endpoint

#### `POST /api/generate`
- **Fungsi:** Proses inti — kirim topik ke Gemini → terima HTML → kirim ke Blogger API.
- **Payload:**
```json
{
    "topic": "Manfaat AI untuk Pendidikan",
    "status": "draft"
}
```
- **Response (Sukses):**
```json
{
    "status": "success",
    "title": "Manfaat AI untuk Pendidikan: Revolusi Pembelajaran Modern",
    "post_id": "12345678901234",
    "article_url": "https://myblog.blogspot.com/2026/06/manfaat-ai-pendidikan.html",
    "html_preview": "<h2>Pendahuluan</h2><p>Kecerdasan buatan...</p>"
}
```
- **Response (Gagal):**
```json
{
    "status": "error",
    "message": "Gemini API: Quota exceeded. Silakan coba lagi nanti.",
    "error_code": "QUOTA_EXCEEDED"
}
```

### 9.3 History Endpoint

#### `GET /api/history`
- **Fungsi:** Mengambil data riwayat pembuatan artikel.
- **Query Params:** `?page=1&limit=20`
- **Response:**
```json
{
    "total": 42,
    "page": 1,
    "data": [
        {
            "id": 1,
            "topic": "Manfaat AI",
            "title": "Manfaat AI: Panduan Lengkap",
            "status": "SUKSES",
            "post_id": "12345",
            "article_url": "https://...",
            "publish_mode": "draft",
            "created_at": "2026-06-28T10:30:00"
        }
    ]
}
```

### 9.4 OAuth Endpoints

#### `GET /api/auth/google`
- **Fungsi:** Memulai alur OAuth2 — redirect user ke Google consent screen.

#### `GET /api/auth/callback`
- **Fungsi:** Menerima authorization code dari Google, menukarnya menjadi access token & refresh token, lalu menyimpannya ke SQLite.
- **Response:** Redirect ke halaman utama dengan status koneksi.

#### `GET /api/auth/status`
- **Fungsi:** Mengecek apakah user sudah terkoneksi ke Google (token valid).
- **Response:**
```json
{
    "connected": true,
    "email": "user@gmail.com"
}
```

#### `POST /api/auth/disconnect`
- **Fungsi:** Menghapus token OAuth dari database (logout dari Google).

---

## 10. Panduan Prompt Engineering (Instruksi AI)

Agar AI menghasilkan artikel yang rapi di Blogspot, Backend menyuntikkan *System Prompt* yang ketat sebelum mengirim topik dari pengguna.

### 10.1 System Prompt Baku

```
Kamu adalah seorang penulis blog profesional dan pakar SEO berbahasa Indonesia.
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
13. Sertakan kesimpulan di akhir artikel dengan tag <h2>Kesimpulan</h2>.
```

### 10.2 Format Pengiriman ke Gemini

```python
prompt = f"""
{SYSTEM_PROMPT}

TOPIK ARTIKEL: {user_topic}

Tulis artikelnya sekarang:
"""
```

### 10.3 Post-Processing HTML

Setelah menerima response dari Gemini, backend melakukan:
1. **Strip markdown wrapper** — Hapus ```html dan ``` jika ada.
2. **Ekstraksi judul** — Ambil teks dari tag `<h1>` pertama sebagai judul artikel.
3. **Hapus `<h1>`** — Karena Blogger otomatis menampilkan judul post, tag `<h1>` dihapus dari body.
4. **Validasi HTML** — Cek apakah output mengandung minimal tag `<h2>` dan `<p>`.

---

## 11. Alur Proses Utama (Main Flow)

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  USER     │    │   Frontend   │    │   Backend    │    │  External    │
│           │    │   (Browser)  │    │  (FastAPI)   │    │  Services    │
└─────┬─────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
      │                 │                    │                   │
      │  1. Input topik │                    │                   │
      │  + pilih mode   │                    │                   │
      ├────────────────►│                    │                   │
      │                 │                    │                   │
      │                 │  2. POST           │                   │
      │                 │  /api/generate     │                   │
      │                 ├───────────────────►│                   │
      │                 │                    │                   │
      │                 │                    │  3. Validasi      │
      │                 │                    │  (cek API key,    │
      │                 │                    │   cek OAuth)      │
      │                 │                    │                   │
      │                 │                    │  4. Kirim prompt  │
      │                 │                    │  ke Gemini API    │
      │                 │                    ├──────────────────►│
      │                 │                    │                   │
      │                 │                    │  5. Terima HTML   │
      │                 │                    │◄──────────────────┤
      │                 │                    │                   │
      │                 │                    │  6. Post-process  │
      │                 │                    │  HTML (strip,     │
      │                 │                    │  extract title)   │
      │                 │                    │                   │
      │                 │                    │  7. Publish ke    │
      │                 │                    │  Blogger API      │
      │                 │                    ├──────────────────►│
      │                 │                    │                   │
      │                 │                    │  8. Response      │
      │                 │                    │  (post_id, url)   │
      │                 │                    │◄──────────────────┤
      │                 │                    │                   │
      │                 │                    │  9. Simpan ke     │
      │                 │                    │  history (SQLite) │
      │                 │                    │                   │
      │                 │  10. Response JSON │                   │
      │                 │◄───────────────────┤                   │
      │                 │                    │                   │
      │  11. Tampilkan  │                    │                   │
      │  hasil + preview│                    │                   │
      │◄────────────────┤                    │                   │
      │                 │                    │                   │
```

---

## 12. Desain Antarmuka (UI Layout)

### 12.1 Layout Utama — Single Page Application

Aplikasi menggunakan satu halaman HTML dengan navigasi tab/section:

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AutoBlog AI                    [⚙️ Pengaturan] [📡 Status] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── Tab: ✍️ Generate ──────────────────────────────────┐  │
│  │                                                        │  │
│  │  Topik Artikel:                                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ [Textarea - masukkan topik/keyword di sini]      │  │  │
│  │  │                                                  │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  Mode Publikasi: [▼ DRAFT / LIVE ]                     │  │
│  │                                                        │  │
│  │  [ 🚀 Generate & Publish ]                             │  │
│  │                                                        │  │
│  │  ┌─── Preview Hasil ──────────────────────────────┐    │  │
│  │  │  (Menampilkan HTML preview artikel setelah      │    │  │
│  │  │   generate berhasil)                            │    │  │
│  │  └────────────────────────────────────────────────┘    │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── Tab: 📋 Riwayat ──────────────────────────────────┐  │
│  │                                                        │  │
│  │  | # | Tanggal    | Topik          | Status | Link |   │  │
│  │  |---|------------|----------------|--------|------|   │  │
│  │  | 1 | 28/06/2026 | Manfaat AI     | ✅     | 🔗   |   │  │
│  │  | 2 | 28/06/2026 | Tips SEO       | ✅     | 🔗   |   │  │
│  │  | 3 | 27/06/2026 | React vs Vue   | ❌     | -    |   │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── Modal: ⚙️ Pengaturan ─────────────────────────────┐  │
│  │                                                        │  │
│  │  Gemini API Key:  [________________________]           │  │
│  │  Blog ID:         [________________________]           │  │
│  │  Google Account:  [🔗 Connect to Google]  ✅ Connected │  │
│  │                                                        │  │
│  │  [ 💾 Simpan Pengaturan ]                              │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  AutoBlog AI v1.0 — Berjalan di localhost:8000              │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 Prinsip Desain UI

*   **Dark Mode** sebagai default — nyaman untuk pengguna yang bekerja lama di depan layar.
*   **Glassmorphism** pada card/panel — memberikan kesan modern dan premium.
*   **Animasi Loading** — spinner + teks status bertahap ("Menghubungi AI...", "Mempublish ke Blogger...", "Selesai!").
*   **Responsive** — mendukung tampilan mobile meskipun penggunaan utama di desktop.
*   **Warna Tema:** Gradasi ungu-biru gelap (dark mode), aksen hijau untuk sukses, merah untuk error.

---

## 13. Penanganan Error (Edge Cases & Error Handling)

| Skenario | Tindakan Backend | Pesan ke User |
| :--- | :--- | :--- |
| API Key Gemini kosong | Tolak request, return 400 | "⚠️ API Key belum dikonfigurasi. Silakan isi di menu Pengaturan." |
| Blog ID kosong | Tolak request, return 400 | "⚠️ Blog ID belum diisi. Silakan isi di menu Pengaturan." |
| OAuth belum terhubung | Tolak request, return 401 | "⚠️ Akun Google belum terhubung. Silakan klik 'Connect to Google' di Pengaturan." |
| Token OAuth expired | Auto-refresh token. Jika gagal, return 401 | "🔄 Sesi Google kedaluwarsa. Silakan hubungkan ulang akun Google." |
| Koneksi internet terputus | Timeout 30 detik, simpan status GAGAL | "❌ Tidak dapat terhubung ke server. Periksa koneksi internet Anda." |
| Gemini API quota exceeded | Return 429, simpan status GAGAL | "⏳ Limit AI tercapai. Silakan coba beberapa saat lagi." |
| Gemini response tidak valid HTML | Log warning, tetap simpan, beri flag | "⚠️ Format artikel tidak sempurna. Silakan periksa di preview." |
| Blogger API error (umum) | Log error, simpan status GAGAL | "❌ Gagal mempublikasikan ke Blogger: [pesan error]" |
| Input topik kosong | Validasi di frontend & backend | "⚠️ Topik tidak boleh kosong." |

---

## 14. Keamanan (Security Considerations)

*   **Penyimpanan Kredensial:** Semua API key dan OAuth token disimpan di SQLite lokal (`database.db`). Tidak ada data yang dikirim ke server pihak ketiga selain Google.
*   **File `.gitignore`:** Wajib meng-exclude `database.db`, `.env`, dan folder `credentials/` agar tidak ter-commit ke repository.
*   **OAuth2 Best Practice:**
    *   Menggunakan `offline` access type untuk mendapatkan refresh token.
    *   Refresh token otomatis saat access token kedaluwarsa.
    *   Redirect URI: `http://localhost:8000/api/auth/callback`.
*   **API Key Masking:** Endpoint `GET /api/settings` mengembalikan API key dalam bentuk masked (hanya tampilkan 4 karakter terakhir) untuk keamanan tampilan.
*   **CORS:** Tidak diperlukan karena frontend dan backend berjalan di origin yang sama (`localhost:8000`).

---

## 15. Non-Functional Requirements (NFR)

| Requirement | Detail |
| :--- | :--- |
| **Portabilitas** | Berjalan di Windows, Mac, Linux. Cukup `pip install -r requirements.txt` dan `python main.py` |
| **Performa** | Response endpoint < 15 detik (tergantung kecepatan Gemini API) |
| **Kompatibilitas Browser** | Chrome, Firefox, Edge (modern browsers) |
| **Ukuran Aplikasi** | < 50MB termasuk semua dependensi |
| **Database** | SQLite — zero-config, tidak perlu install database server |
| **Koneksi** | Membutuhkan internet untuk Gemini API dan Blogger API |

---

## 16. File Konfigurasi

### 16.1 `.env.example`

```env
# Google Gemini API Key (dari Google AI Studio)
GEMINI_API_KEY=your_gemini_api_key_here

# Blog ID Blogspot (dari URL dashboard Blogger)
BLOG_ID=your_blog_id_here

# OAuth2 Client (dari Google Cloud Console)
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here

# Server
HOST=127.0.0.1
PORT=8000
```

### 16.2 `.gitignore`

```
# Environment
.env
__pycache__/
*.pyc

# Database
database.db

# OAuth Credentials
credentials/
token.json

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

## 17. Panduan Setup (Getting Started)

### 17.1 Prasyarat
1. **Python 3.10+** terinstal di sistem.
2. **Google Cloud Project** dengan Blogger API enabled.
3. **OAuth2 Client ID** (tipe "Desktop App" atau "Web Application" dengan redirect URI `http://localhost:8000/api/auth/callback`).
4. **Gemini API Key** dari [Google AI Studio](https://aistudio.google.com/apikey).
5. **Blog ID** dari dashboard Blogger (terlihat di URL: `https://www.blogger.com/blog/posts/BLOG_ID`).

### 17.2 Langkah Instalasi

```bash
# 1. Masuk ke direktori proyek
cd /Applications/MAMP/htdocs/phyton/autopost

# 2. Buat virtual environment
python3 -m venv venv
source venv/bin/activate    # Mac/Linux
# venv\Scripts\activate     # Windows

# 3. Install dependensi
pip install -r requirements.txt

# 4. Copy dan isi konfigurasi
cp .env.example .env
# Edit .env dengan API key dan kredensial Anda

# 5. Letakkan file OAuth client_secret.json di folder credentials/
# Download dari Google Cloud Console → APIs & Services → Credentials

# 6. Jalankan aplikasi
python main.py
# atau: uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 7. Buka browser
# http://localhost:8000
```

---

## 18. Roadmap Implementasi (Milestones Eksekusi)

### Tahap 1: Setup Lingkungan & Fondasi (Hari ke-1)
- [ ] Membuat struktur direktori proyek sesuai Bagian 7.
- [ ] Membuat `requirements.txt`, `.env.example`, `.gitignore`.
- [ ] Setup FastAPI dasar (`main.py`) dengan static file serving dan Jinja2 template.
- [ ] Membuat `config.py` untuk load environment variables.
- [ ] Membuat `database.py` dengan inisialisasi tabel SQLite (settings, history, oauth_tokens).
- [ ] Membuat `models.py` dengan Pydantic schemas.

### Tahap 2: Backend API — Settings & History (Hari ke-2)
- [ ] Membuat `services/db_service.py` — CRUD operations.
- [ ] Membuat `routers/settings.py` — `GET/POST /api/settings`.
- [ ] Membuat `routers/history.py` — `GET /api/history`.
- [ ] Testing endpoint dengan browser/curl.

### Tahap 3: Integrasi Inti — Gemini AI & Blogger (Hari ke-3)
- [ ] Membuat `services/gemini_service.py` — komunikasi dengan Gemini API menggunakan system prompt.
- [ ] Membuat `services/blogger_service.py` — OAuth2 flow + publish ke Blogger.
- [ ] Membuat `routers/generate.py` — `POST /api/generate` (menyatukan Gemini + Blogger).
- [ ] Implementasi OAuth2 endpoints (`/api/auth/*`).
- [ ] Implementasi auto-refresh token.

### Tahap 4: Antarmuka Web / Frontend (Hari ke-4)
- [ ] Desain `templates/index.html` dengan Tailwind CSS (dark mode, glassmorphism).
- [ ] Membuat `static/js/app.js` — logika frontend (fetch API, tab navigation, modals).
- [ ] Membuat `static/css/style.css` — custom styles dan animasi.
- [ ] Implementasi form generate dengan loading animation.
- [ ] Implementasi tabel riwayat.
- [ ] Implementasi modal pengaturan.
- [ ] Implementasi HTML preview panel.

### Tahap 5: Testing & Polish (Hari ke-5)
- [ ] Uji coba end-to-end: input topik → generate → publish → cek di Blogger.
- [ ] Evaluasi dan perbaiki format HTML dari AI.
- [ ] Test semua error scenarios (API key kosong, token expired, dll).
- [ ] Polish UI: animasi, transisi, responsivitas.
- [ ] Dokumentasi final dan cleanup kode.

---

## 19. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
| :--- | :--- | :--- |
| Gemini API quota limit (gratis) | Tidak bisa generate artikel | Implementasi retry logic + notifikasi jelas ke user |
| OAuth token corruption | Tidak bisa publish ke Blogger | Tombol "Reconnect" di pengaturan + clear token |
| Format HTML dari AI tidak konsisten | Layout blog rusak | Post-processing + validasi HTML sebelum publish |
| SQLite concurrent write issue | Data corrupt | Gunakan `aiosqlite` dengan proper locking |
| Google API breaking changes | Fitur rusak | Pin versi library di requirements.txt |

---

## 20. Glossary

| Istilah | Definisi |
| :--- | :--- |
| **Blogger API v3** | REST API dari Google untuk mengelola blog di platform Blogspot |
| **OAuth2** | Protokol otorisasi untuk mengakses resource Google atas nama pengguna |
| **Gemini** | Model AI generatif dari Google (pengganti PaLM) |
| **FastAPI** | Framework web Python modern berbasis ASGI, mendukung async |
| **SQLite** | Database relasional ringan yang tersimpan dalam satu file |
| **ASGI** | Asynchronous Server Gateway Interface — standar Python untuk async web |
| **SEO** | Search Engine Optimization — optimasi konten untuk mesin pencari |

---

*Dokumen ini adalah panduan lengkap untuk implementasi AutoBlog AI. Semua spesifikasi di atas menjadi acuan utama selama pengembangan.*

mysecretadmin