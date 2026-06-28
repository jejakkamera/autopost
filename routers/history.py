"""
AutoBlog AI — History Router
Endpoint untuk mengambil riwayat pembuatan artikel.
"""

from fastapi import APIRouter, Query
from models import HistoryResponse, MessageResponse
from services.db_service import get_history, delete_history_item

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
async def list_history(
    page: int = Query(1, ge=1, description="Nomor halaman"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah data per halaman"),
):
    """Mengambil riwayat pembuatan artikel dengan pagination."""
    result = await get_history(page=page, limit=limit)
    return HistoryResponse(**result)


@router.delete("/history/{history_id}", response_model=MessageResponse)
async def delete_item(history_id: int):
    """Menghapus riwayat pembuatan artikel berdasarkan ID."""
    await delete_history_item(history_id)
    return MessageResponse(
        status="success",
        message="Riwayat artikel berhasil dihapus."
    )
