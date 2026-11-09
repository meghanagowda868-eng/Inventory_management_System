"""Pydantic schemas for system notifications and alerts."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: Optional[int] = Field(None, description="Target user ID, or None for broadcast")
    title: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1)
    category: str = Field("SYSTEM", description="LOW_STOCK, REORDER, PURCHASE_ORDER, SALE, PROMOTION, SYSTEM")
    severity: str = Field("INFO", description="INFO, WARNING, CRITICAL, SUCCESS")
    link_url: Optional[str] = Field(None, max_length=255)


class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    title: str
    message: str
    category: str
    severity: str
    is_read: bool
    link_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationSummaryResponse(BaseModel):
    unread_count: int
    critical_count: int
    recent_notifications: List[NotificationResponse] = []
