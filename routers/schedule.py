"""
AutoBlog AI — Schedule Batch Router
Endpoint untuk mengelola antrean penjadwalan penerbitan batch artikel.
"""

from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, HTTPException

from models import ScheduleBatchRequest, ScheduleBatchResponse, ScheduleItemResult
from services.db_service import (
    get_setting, add_to_schedule_queue, get_all_schedule_queue, delete_schedule_item
)
from services.blogger_service import check_auth_status

router = APIRouter()

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


@router.post("/schedule-batch", response_model=ScheduleBatchResponse)
async def schedule_batch(request: ScheduleBatchRequest):
    """
    Masukkan batch topik artikel ke dalam antrean database lokal.
    Akan diproses otomatis oleh background worker saat waktu rilis tercapai.
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

    # ── Validasi Blog ID & OAuth (Fail Fast) ──
    blog_id = await get_setting("blog_id")
    if not blog_id:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "⚠️ Blog ID belum diisi di Pengaturan.",
                "error_code": "MISSING_BLOG_ID",
            },
        )

    auth_status = await check_auth_status()
    if not auth_status["connected"]:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "message": "⚠️ Akun Google belum terhubung. Silakan hubungkan di Pengaturan.",
                "error_code": "AUTH_REQUIRED",
            },
        )

    # ── Masukkan ke Antrean ──
    schedule_results = []
    total_queued = 0

    for idx, topic in enumerate(topics):
        release_date = start_date + timedelta(days=idx * request.interval_days)
        
        # 1. Antrean Indonesia (09:00 WIB)
        iso_id = release_date.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=WIB).isoformat()
        await add_to_schedule_queue(
            topic=topic,
            scheduled_at=iso_id,
            language="Indonesia",
            search_grounding=request.search_grounding,
            publish_mode=request.status or "draft",
        )
        schedule_results.append(ScheduleItemResult(
            topic=topic,
            language="Indonesia",
            scheduled_at=iso_id,
            status="PENDING",
        ))
        total_queued += 1

        # 2. Antrean English (15:00 WIB - jika dual bahasa aktif)
        if request.dual_language:
            iso_en = release_date.replace(hour=15, minute=0, second=0, microsecond=0, tzinfo=WIB).isoformat()
            await add_to_schedule_queue(
                topic=topic,
                scheduled_at=iso_en,
                language="English",
                search_grounding=request.search_grounding,
                publish_mode=request.status or "draft",
            )
            schedule_results.append(ScheduleItemResult(
                topic=topic,
                language="English",
                scheduled_at=iso_en,
                status="PENDING",
            ))
            total_queued += 1

    return ScheduleBatchResponse(
        status="success",
        message=f"Berhasil mengantrekan {total_queued} jadwal penerbitan artikel.",
        total_scheduled=total_queued,
        total_failed=0,
        schedule=schedule_results,
    )


@router.get("/schedule-queue")
async def get_queue():
    """Mengambil semua daftar antrean jadwal postingan."""
    queue = await get_all_schedule_queue()
    return {"status": "success", "data": queue}


@router.delete("/schedule-queue/{item_id}")
async def cancel_schedule_item(item_id: int):
    """Membatalkan / menghapus antrean jadwal postingan."""
    await delete_schedule_item(item_id)
    return {"status": "success", "message": f"Berhasil membatalkan antrean ID #{item_id}."}
