"""Schemas for subcategory management."""
from datetime import datetime

from pydantic import BaseModel, Field


class SubcategoryCreateRequest(BaseModel):
    category_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=2, max_length=120)
    description: str | None = Field(None, max_length=500)


class SubcategoryUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=500)


class SubcategoryResponse(BaseModel):
    id: int
    category_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
