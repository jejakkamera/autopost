# AutoBlog AI — Blogger Auto-Posting dengan AI 🚀

Aplikasi web berbasis **FastAPI (Python)** dan **Tailwind CSS** untuk mempublikasikan artikel berkualitas tinggi secara otomatis ke **Google Blogger (Blogspot)** menggunakan kekuatan AI Multi-Agent.

---

## ✨ Fitur Utama

### 1. 🤖 Multi-Agent Content Pipeline
Pembuatan artikel dilakukan melalui rantai instruksi (chain-of-agents) teratur:
*   **SEO Strategist Agent**: Menganalisis topik dan menghasilkan kerangka artikel (H2/H3) terstruktur.
*   **Content Writer Agent**: Menulis artikel yang panjang, mendalam, dan memiliki sentuhan manusiawi (*human-like content*).
*   **Web Publisher Agent**: Memformat teks menjadi dokumen HTML murni yang rapi dan siap saji (menggunakan tag `<p>`, `<h2>`, `<h3>`, `<ul>`, `<li>`, `<strong>`).
*   **Art Director Agent**: Mengekstrak deskripsi visual singkat (10-15 kata bahasa Inggris) untuk pembuat gambar agar prompt bersih dari kode HTML/iframe.

### 2. 🖼️ Pembuat Gambar Otomatis & Hosting
*   Membuat ilustrasi gambar berkualitas tinggi berdasarkan topik artikel menggunakan DALL-E 3 (via Premzone API) dengan sistem **3x Retry otomatis** jika terjadi kendala jaringan.
*   Otomatis mengunggah gambar ke cloud hosting **Catbox.moe** untuk mendapatkan tautan publik permanen yang disematkan langsung di dalam artikel Blogger.

### 3. 🌐 Cari Info Terbaru (Google Search Grounding)
*   Menggunakan kapabilitas penelusuran langsung Google Search (via Gemini API) untuk mencari fakta terbaru di internet agar konten artikel tetap akurat, faktual, dan bebas dari halusinasi.

### 4. 🌍 Dual Bahasa (Terjemah ke Inggris)
*   Otomatis menerjemahkan judul dan konten artikel dari Bahasa Indonesia ke Bahasa Inggris menggunakan AI Translator Agent untuk jangkauan audiens internasional.

### 5. 📅 Jadwal Batch (Auto-Posting Terjadwal)
*   Menjadwalkan penerbitan banyak artikel sekaligus dengan pengaturan waktu otomatis:
    *   **Versi Indonesia**: Dirilis pada jam **09:00 WIB** pagi.
    *   **Versi Inggris**: Dirilis pada jam **15:00 WIB** sore di hari yang sama.
    *   Topik berikutnya dirilis secara bertahap sesuai interval hari yang Anda tentukan.
*   Mendukung pengisian topik secara dinamis (tambah/hapus baris) atau **unggah berkas Excel/CSV** (menggunakan SheetJS). Anda juga dapat mengunduh file template Excel langsung dari aplikasi.

### 6. 🔐 Keamanan & Riwayat Posting
*   Pengamanan halaman menggunakan sistem **Login Key** terenkripsi.
*   Halaman **Riwayat** terintegrasi dengan database SQLite untuk memantau status publikasi, menyalin tautan artikel sukses, membaca detail error jika gagal, dan melihat log prompt AI di setiap langkah.

---

## 🛠️ Persyaratan Sistem
*   **Python**: v3.10 atau lebih baru.
*   **Google Cloud Console Project**: dengan API Blogger v3 diaktifkan dan kredensial OAuth 2.0.
*   **Akses internet** untuk API AI dan Blogger.

---

## 🚀 Panduan Instalasi & Menjalankan Lokal

### 1. Klon Repositori
```bash
git clone https://github.com/jejakkamera/autopost.git
cd autopost
```

### 2. Buat Virtual Environment & Pasang Dependensi
```bash
python -m venv venv
source venv/bin/activate  # Untuk macOS/Linux
# venv\Scripts\activate   # Untuk Windows

pip install -r requirements.txt
```

### 3. Konfigurasi Environment File
Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Isi konfigurasi host dan port default:
```env
HOST=127.0.0.1
PORT=8000
```

### 4. Siapkan Google Client Secrets JSON
Unduh berkas kredensial OAuth 2.0 dari Google Cloud Console Anda, ubah namanya menjadi `client_secret.json`, lalu letakkan di root direktori project ini.

### 5. Jalankan Aplikasi
```bash
python main.py
```
Aplikasi akan aktif di **http://127.0.0.1:8000**.

---

## 🏗️ Struktur Proyek
```
autopost/
├── main.py                 # Entry point aplikasi FastAPI
├── config.py               # Pengaturan konfigurasi aplikasi
├── database.py             # Inisialisasi DB SQLite (aiosqlite)
├── models.py               # Pydantic Request/Response models
├── client_secret.json      # File rahasia Google OAuth Anda (diabaikan oleh git)
├── routers/                # Modul Endpoint API FastAPI
│   ├── auth.py             # Penanganan autentikasi Google OAuth & login key
│   ├── generate.py         # Orkestrasi pembuatan satu artikel
│   ├── history.py          # CRUD riwayat postingan
│   ├── schedule.py         # Orkestrasi penjadwalan batch postingan
│   └── settings.py         # Pengaturan API provider & blogger
├── services/               # Logika Bisnis & Integrasi API
│   ├── ai_service.py       # Chain-of-Prompts & integrasi model AI
│   ├── blogger_service.py  # Operasi ke Google Blogger API
│   ├── db_service.py       # Operasi database SQLite
│   └── image_service.py    # Pembuatan gambar & upload Catbox
├── static/                 # Aset Frontend statis
│   ├── css/
│   └── js/
└── templates/
    └── index.html          # File HTML halaman utama
```

---

## 🛡️ Lisensi
Didistribusikan secara bebas untuk keperluan pengembangan pribadi. Jaga kerahasiaan file `.env` dan `client_secret.json` Anda. Jangan mengunggahnya ke repositori publik!
