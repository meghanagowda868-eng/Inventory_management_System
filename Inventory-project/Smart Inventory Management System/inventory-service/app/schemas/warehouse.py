"""Schemas for warehouse management."""
from datetime import datetime

from pydantic import BaseModel, Field


class WarehouseCreateRequest(BaseModel):
    warehouse_code: str = Field(..., min_length=3, max_length=30)
    name: str = Field(..., min_length=3, max_length=200)
    location: str | None = Field(None, max_length=200)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    status: str = Field(default="ACTIVE", max_length=20)
    contact_name: str | None = Field(None, max_length=120)
    contact_phone: str | None = Field(None, max_length=50)


class WarehouseUpdateRequest(BaseModel):
    warehouse_code: str | None = Field(None, min_length=3, max_length=30)
    name: str | None = Field(None, min_length=3, max_length=200)
    location: str | None = Field(None, max_length=200)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=20)
    contact_name: str | None = Field(None, max_length=120)
    contact_phone: str | None = Field(None, max_length=50)


class WarehouseResponse(BaseModel):
    id: int
    warehouse_code: str
    name: str
    location: str | None
    city: str | None
    state: str | None
    status: str
    contact_name: str | None
    contact_phone: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
