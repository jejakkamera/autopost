"""
AutoBlog AI — Pydantic Models
Request/Response schemas untuk validasi data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# Settings Models (Multi-Provider)
# ============================================

class SettingsRequest(BaseModel):
    """Schema untuk menyimpan pengaturan."""
    ai_provider: Optional[str] = Field(None, description="Provider AI: gemini/deepseek/openai/sumopod/custom")
    ai_model: Optional[str] = Field(None, description="Model AI spesifik")
    gemini_api_key: Optional[str] = Field(None, description="API Key Google Gemini")
    deepseek_api_key: Optional[str] = Field(None, description="API Key DeepSeek")
    openai_api_key: Optional[str] = Field(None, description="API Key OpenAI")
    sumopod_api_key: Optional[str] = Field(None, description="API Key SumoPod AI")
    bynara_api_key: Optional[str] = Field(None, description="API Key Bynara Router")
    dahono_api_key: Optional[str] = Field(None, description="API Key Dahono Labs")
    custom_api_key: Optional[str] = Field(None, description="API Key Custom Provider")
    custom_base_url: Optional[str] = Field(None, description="Base URL Custom Provider")
    custom_model: Optional[str] = Field(None, description="Model Name Custom Provider")
    blog_id: Optional[str] = Field(None, description="ID Blog Blogspot")
    default_status: Optional[str] = Field(None, description="Status default: draft/live")
    # Image Settings
    image_api_enabled: Optional[bool] = Field(None, description="Enable image generation")
    image_api_key: Optional[str] = Field(None, description="API Key Image Generator")
    image_base_url: Optional[str] = Field(None, description="Base URL Image Generator")
    image_model: Optional[str] = Field(None, description="Model Name Image Generator")
    image_prompt_template: Optional[str] = Field(None, description="Prompt Template for Image Generator")


class SettingsResponse(BaseModel):
    """Schema response pengaturan (API keys di-mask)."""
    ai_provider: str = "gemini"
    ai_model: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    sumopod_api_key: str = ""
    bynara_api_key: str = ""
    dahono_api_key: str = ""
    custom_api_key: str = ""
    custom_base_url: str = ""
    custom_model: str = ""
    blog_id: str = ""
    default_status: str = "draft"
    # Image Settings
    image_api_enabled: bool = False
    image_api_key: str = ""
    image_base_url: str = "https://api.premzone.co"
    image_model: str = "cx/gpt-5.5"
    image_prompt_template: str = "A flat style vector illustration of [TOPIK], modern design, vibrant colors, clean background"





# ============================================
# Generate Models
# ============================================

class GenerateRequest(BaseModel):
    """Schema untuk request generate artikel."""
    topic: str = Field(..., min_length=3, description="Topik/keyword artikel")
    status: str = Field("draft", description="Mode publikasi: draft/live")
    search_grounding: Optional[bool] = Field(False, description="Cari data terbaru via Google Search (Gemini)")
    dual_language: Optional[bool] = Field(False, description="Aktifkan dual bahasa (terjemahkan ke Inggris)")


class GenerateResponse(BaseModel):
    """Schema response generate artikel."""
    status: str
    title: Optional[str] = None
    post_id: Optional[str] = None
    article_url: Optional[str] = None
    html_preview: Optional[str] = None
    message: Optional[str] = None
    error_code: Optional[str] = None


# ============================================
# History Models
# ============================================

class HistoryItem(BaseModel):
    """Schema untuk satu item riwayat."""
    id: int
    topic: str
    title: Optional[str] = None
    status: str
    post_id: Optional[str] = None
    article_url: Optional[str] = None
    publish_mode: str = "draft"
    error_message: Optional[str] = None
    generation_log: Optional[str] = None
    created_at: str


class HistoryResponse(BaseModel):
    """Schema response riwayat dengan pagination."""
    total: int
    page: int
    data: List[HistoryItem]


# ============================================
# Auth Models
# ============================================

class AuthStatusResponse(BaseModel):
    """Schema response status koneksi Google."""
    connected: bool
    message: str = ""


class BlogVerifyRequest(BaseModel):
    """Schema request verifikasi Blog ID."""
    blog_id: str = Field(..., min_length=1, description="Blog ID untuk diverifikasi")


class BlogVerifyResponse(BaseModel):
    """Schema response verifikasi Blog ID."""
    status: str
    blog_name: Optional[str] = None
    blog_url: Optional[str] = None
    total_posts: Optional[int] = None
    message: str = ""


# ============================================
# Login Auth Models
# ============================================

class LoginRequest(BaseModel):
    """Schema request login."""
    key: str = Field(..., min_length=1, description="Login key")


class LoginSetupRequest(BaseModel):
    """Schema request setup login key pertama kali."""
    key: str = Field(..., min_length=4, description="Login key (minimal 4 karakter)")


class LoginStatusResponse(BaseModel):
    """Schema response status login."""
    authenticated: bool
    setup_required: bool
    message: str = ""


# ============================================
# Providers Info Model
# ============================================

class ProviderModel(BaseModel):
    id: str
    name: str


class ProviderInfo(BaseModel):
    name: str
    models: List[ProviderModel]
    default_model: str
    key_placeholder: str
    key_url: str


# ============================================
# Generic Response
# ============================================

class MessageResponse(BaseModel):
    """Schema response generik."""
    status: str
    message: str


# ============================================
# AI Connection Test Models
# ============================================

class AITestRequest(BaseModel):
    """Schema request tes koneksi AI."""
    provider: str
    api_key: str
    model: Optional[str] = None
    custom_base_url: Optional[str] = None


class AITestResponse(BaseModel):
    """Schema response tes koneksi AI."""
    status: str
    message: str


# ============================================
# Schedule Batch Models
# ============================================

class ScheduleBatchRequest(BaseModel):
    """Schema request batch scheduling."""
    topics: List[str] = Field(..., min_length=1, description="Daftar topik artikel")
    start_date: str = Field(..., description="Tanggal mulai (format: YYYY-MM-DD)")
    interval_days: int = Field(2, ge=1, description="Interval hari antar topik")
    search_grounding: Optional[bool] = Field(False, description="Cari data terbaru via Google Search (Gemini)")
    dual_language: Optional[bool] = Field(False, description="Aktifkan dual bahasa (terjemahkan ke Inggris)")



class ScheduleItemResult(BaseModel):
    """Schema hasil penjadwalan per-item."""
    topic: str
    language: str
    title: Optional[str] = None
    scheduled_at: Optional[str] = None
    post_id: Optional[str] = None
    article_url: Optional[str] = None
    labels: Optional[List[str]] = None
    status: str = "PENDING"
    error: Optional[str] = None


class ScheduleBatchResponse(BaseModel):
    """Schema response batch scheduling."""
    status: str
    message: str
    total_scheduled: int = 0
    total_failed: int = 0
    schedule: List[ScheduleItemResult] = []


