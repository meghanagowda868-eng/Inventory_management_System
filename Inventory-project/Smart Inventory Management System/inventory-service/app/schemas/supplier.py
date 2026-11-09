"""Validated supplier API contracts."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SupplierCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160, examples=["TechCorp Solutions"])
    contact_person: Optional[str] = Field(None, max_length=120, examples=["John Doe"])
    contact_name: Optional[str] = Field(None, max_length=120)
    email: Optional[str] = Field(None, max_length=180, examples=["contact@techcorp.com"])
    phone: Optional[str] = Field(None, max_length=50, examples=["+1-555-0199"])
    address: Optional[str] = Field(None, max_length=255, examples=["123 Logistics Blvd, Silicon Valley, CA"])
    status: Optional[str] = Field(default="ACTIVE", max_length=30)


class SupplierUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=160)
    contact_person: Optional[str] = Field(None, max_length=120)
    contact_name: Optional[str] = Field(None, max_length=120)
    email: Optional[str] = Field(None, max_length=180)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    contact_person: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str = "ACTIVE"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
