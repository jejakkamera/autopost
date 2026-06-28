"""
AutoBlog AI — Database Service
CRUD operations untuk tabel settings, history, dan oauth_tokens.
"""

from database import get_db
from typing import Optional, Dict, List


# ============================================
# Settings CRUD
# ============================================

async def get_all_settings() -> Dict[str, str]:
    """Mengambil semua settings dari database."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        await db.close()


async def get_setting(key: str) -> Optional[str]:
    """Mengambil satu setting berdasarkan key."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    finally:
        await db.close()


async def save_setting(key: str, value: str):
    """Menyimpan atau update satu setting."""
    db = await get_db()
    try:
        await db.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value))
        await db.commit()
    finally:
        await db.close()


async def save_multiple_settings(data: Dict[str, str]):
    """Menyimpan beberapa settings sekaligus."""
    db = await get_db()
    try:
        for key, value in data.items():
            if value is not None:
                await db.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                """, (key, value))
        await db.commit()
    finally:
        await db.close()


# ============================================
# History CRUD
# ============================================

async def add_history(
    topic: str,
    title: Optional[str] = None,
    status: str = "PENDING",
    post_id: Optional[str] = None,
    article_url: Optional[str] = None,
    publish_mode: str = "draft",
    error_message: Optional[str] = None,
    generation_log: Optional[str] = None,
) -> int:
    """Menambahkan entry baru ke tabel history. Return ID."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            INSERT INTO history (topic, title, status, post_id, article_url, publish_mode, error_message, generation_log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (topic, title, status, post_id, article_url, publish_mode, error_message, generation_log))
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_history(
    history_id: int,
    title: Optional[str] = None,
    status: Optional[str] = None,
    post_id: Optional[str] = None,
    article_url: Optional[str] = None,
    error_message: Optional[str] = None,
    generation_log: Optional[str] = None,
):
    """Update entry history berdasarkan ID."""
    db = await get_db()
    try:
        updates = []
        values = []

        if title is not None:
            updates.append("title = ?")
            values.append(title)
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if post_id is not None:
            updates.append("post_id = ?")
            values.append(post_id)
        if article_url is not None:
            updates.append("article_url = ?")
            values.append(article_url)
        if error_message is not None:
            updates.append("error_message = ?")
            values.append(error_message)
        if generation_log is not None:
            updates.append("generation_log = ?")
            values.append(generation_log)

        if updates:
            values.append(history_id)
            query = f"UPDATE history SET {', '.join(updates)} WHERE id = ?"
            await db.execute(query, values)
            await db.commit()
    finally:
        await db.close()


async def get_history(page: int = 1, limit: int = 20) -> Dict:
    """Mengambil riwayat dengan pagination."""
    db = await get_db()
    try:
        # Total count
        cursor = await db.execute("SELECT COUNT(*) FROM history")
        row = await cursor.fetchone()
        total = row[0]

        # Data dengan pagination
        offset = (page - 1) * limit
        cursor = await db.execute("""
            SELECT id, topic, title, status, post_id, article_url,
                   publish_mode, error_message, generation_log, created_at
            FROM history
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "topic": row[1],
                "title": row[2],
                "status": row[3],
                "post_id": row[4],
                "article_url": row[5],
                "publish_mode": row[6],
                "error_message": row[7],
                "generation_log": row[8],
                "created_at": row[9],
            })

        return {"total": total, "page": page, "data": data}
    finally:
        await db.close()


async def delete_history_item(history_id: int):
    """Menghapus item history berdasarkan ID."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM history WHERE id = ?", (history_id,))
        await db.commit()
    finally:
        await db.close()


# ============================================
# OAuth Tokens CRUD
# ============================================

async def save_oauth_token(
    access_token: str,
    refresh_token: Optional[str] = None,
    token_uri: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    expiry: Optional[str] = None,
):
    """Menyimpan OAuth token (replace existing)."""
    db = await get_db()
    try:
        # Hapus token lama
        await db.execute("DELETE FROM oauth_tokens")
        # Simpan token baru
        await db.execute("""
            INSERT INTO oauth_tokens
                (access_token, refresh_token, token_uri, client_id, client_secret, expiry)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (access_token, refresh_token, token_uri, client_id, client_secret, expiry))
        await db.commit()
    finally:
        await db.close()


async def get_oauth_token() -> Optional[Dict]:
    """Mengambil OAuth token tersimpan."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT access_token, refresh_token, token_uri, client_id, client_secret, expiry
            FROM oauth_tokens
            ORDER BY id DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            return {
                "access_token": row[0],
                "refresh_token": row[1],
                "token_uri": row[2],
                "client_id": row[3],
                "client_secret": row[4],
                "expiry": row[5],
            }
        return None
    finally:
        await db.close()


async def delete_oauth_token():
    """Menghapus semua OAuth token (disconnect)."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM oauth_tokens")
        await db.commit()
    finally:
        await db.close()


# ============================================
# Scheduler Queue CRUD
# ============================================

async def add_to_schedule_queue(
    topic: str,
    scheduled_at: str,
    language: str,
    search_grounding: bool = False,
) -> int:
    """Menambahkan item penjadwalan baru ke antrean."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            INSERT INTO scheduler_queue (topic, scheduled_at, language, search_grounding, status)
            VALUES (?, ?, ?, ?, 'PENDING')
        """, (topic, scheduled_at, language, 1 if search_grounding else 0))
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_pending_schedule_items() -> List[Dict]:
    """Mengambil semua item PENDING yang scheduled_at <= waktu sekarang."""
    db = await get_db()
    try:
        # Gunakan string comparison karena ISO 8601 terurut secara alfabetis/leksikografis
        # Tapi untuk meminimalkan masalah zona waktu, kita akan filter menggunakan datetime lokal di Python,
        # jadi kita tarik semua PENDING dulu dan filter di level Python, atau gunakan string comparison.
        # Format ISO 8601: YYYY-MM-DDTHH:MM:SS+HH:MM.
        # Tarik semua PENDING dulu agar aman dengan manipulasi datetime di Python.
        cursor = await db.execute("""
            SELECT id, topic, scheduled_at, language, search_grounding, status
            FROM scheduler_queue
            WHERE status = 'PENDING'
            ORDER BY scheduled_at ASC
        """)
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "topic": row[1],
                "scheduled_at": row[2],
                "language": row[3],
                "search_grounding": bool(row[4]),
                "status": row[5],
            }
            for row in rows
        ]
    finally:
        await db.close()


async def update_schedule_item(
    item_id: int,
    status: str,
    title: Optional[str] = None,
    post_id: Optional[str] = None,
    article_url: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Mengupdate status dan data hasil pengerjaan item antrean."""
    db = await get_db()
    try:
        await db.execute("""
            UPDATE scheduler_queue
            SET status = ?, title = ?, post_id = ?, article_url = ?, error_message = ?
            WHERE id = ?
        """, (status, title, post_id, article_url, error_message, item_id))
        await db.commit()
    finally:
        await db.close()


async def get_all_schedule_queue() -> List[Dict]:
    """Mengambil semua daftar antrean untuk ditampilkan di UI."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT id, topic, scheduled_at, language, search_grounding, status, title, post_id, article_url, error_message, created_at
            FROM scheduler_queue
            ORDER BY scheduled_at ASC
        """)
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "topic": row[1],
                "scheduled_at": row[2],
                "language": row[3],
                "search_grounding": bool(row[4]),
                "status": row[5],
                "title": row[6],
                "post_id": row[7],
                "article_url": row[8],
                "error_message": row[9],
                "created_at": row[10],
            }
            for row in rows
        ]
    finally:
        await db.close()


async def delete_schedule_item(item_id: int):
    """Menghapus item dari antrean (membatalkan)."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM scheduler_queue WHERE id = ?", (item_id,))
        await db.commit()
    finally:
        await db.close()

