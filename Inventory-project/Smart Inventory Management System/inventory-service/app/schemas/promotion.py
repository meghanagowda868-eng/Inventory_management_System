"""Schemas for campaigns, offers, and promotional pricing."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = None
    banner_title: str | None = Field(None, max_length=200)
    starts_at: datetime
    ends_at: datetime
    is_enabled: bool = True
    festival_event_id: int | None = Field(None, gt=0)
    minimum_discount: float | None = Field(None, ge=0, le=100)
    maximum_discount: float | None = Field(None, ge=0, le=100)
    selected_discount: float | None = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        _validate_campaign_discount_range(self.minimum_discount, self.maximum_discount, self.selected_discount)
        return self


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: str | None
    banner_title: str | None
    starts_at: datetime
    ends_at: datetime
    is_enabled: bool
    status: str
    festival_event_id: int | None = None
    minimum_discount: float | None = None
    maximum_discount: float | None = None
    selected_discount: float | None = None


class CampaignUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=160)
    description: str | None = None
    banner_title: str | None = Field(None, max_length=200)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool | None = None
    festival_event_id: int | None = Field(None, gt=0)
    minimum_discount: float | None = Field(None, ge=0, le=100)
    maximum_discount: float | None = Field(None, ge=0, le=100)
    selected_discount: float | None = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        _validate_campaign_discount_range(self.minimum_discount, self.maximum_discount, self.selected_discount)
        return self


class CampaignApplyDiscountRequest(BaseModel):
    selected_discount: float = Field(..., ge=0, le=100)
    product_ids: list[int] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)
    subcategory_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_electronics_targets(self):
        if not (self.product_ids or self.category_ids or self.subcategory_ids):
            raise ValueError("Select at least one electronic product or category")
        if any(len(values) != len(set(values)) for values in (self.product_ids, self.category_ids, self.subcategory_ids)):
            raise ValueError("Discount targets cannot contain duplicates")
        return self


def _validate_campaign_discount_range(minimum: float | None, maximum: float | None, selected: float | None) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum_discount must not exceed maximum_discount")
    if selected is not None:
        if minimum is not None and selected < minimum:
            raise ValueError("selected_discount must be at least minimum_discount")
        if maximum is not None and selected > maximum:
            raise ValueError("selected_discount must not exceed maximum_discount")


class OfferCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = None
    campaign_id: int | None = Field(None, gt=0)
    discount_type: Literal["percentage", "fixed"]
    discount_value: float = Field(..., gt=0)
    starts_at: datetime
    ends_at: datetime
    minimum_purchase: float = Field(0, ge=0)
    maximum_discount: float | None = Field(None, gt=0)
    priority: int = Field(0, ge=0, le=10000)
    is_enabled: bool = True
    product_ids: list[int] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)
    subcategory_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_offer(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.discount_type == "percentage" and self.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError("product_ids contains duplicates")
        if len(set(self.category_ids)) != len(self.category_ids):
            raise ValueError("category_ids contains duplicates")
        if len(set(self.subcategory_ids)) != len(self.subcategory_ids):
            raise ValueError("subcategory_ids contains duplicates")
        return self


class OfferResponse(BaseModel):
    id: int
    name: str
    description: str | None
    campaign_id: int | None
    discount_type: str
    discount_value: float
    starts_at: datetime
    ends_at: datetime
    minimum_purchase: float
    maximum_discount: float | None
    priority: int
    is_enabled: bool
    status: str
    product_ids: list[int]
    category_ids: list[int]
    subcategory_ids: list[int]


class OfferUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=160)
    description: str | None = None
    campaign_id: int | None = Field(None, gt=0)
    discount_type: Literal["percentage", "fixed"] | None = None
    discount_value: float | None = Field(None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    minimum_purchase: float | None = Field(None, ge=0)
    maximum_discount: float | None = Field(None, gt=0)
    priority: int | None = Field(None, ge=0, le=10000)
    is_enabled: bool | None = None
    product_ids: list[int] | None = None
    category_ids: list[int] | None = None
    subcategory_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_offer(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.discount_type == "percentage" and self.discount_value is not None and self.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        return self


class PricingResponse(BaseModel):
    product_id: int
    product_name: str
    original_price: float
    offer_id: int | None
    offer_name: str | None
    discount_type: str | None
    discount_value: float | None
    discount_amount: float
    final_price: float
    offer_status: str | None
