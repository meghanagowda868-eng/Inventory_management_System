from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.promotion import CampaignCreateRequest, OfferCreateRequest
from app.schemas.seasonal import SeasonalEventCreateRequest


def test_seasonal_event_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        SeasonalEventCreateRequest(
            name="Invalid season",
            start_date="2026-10-20",
            end_date="2026-10-01",
        )


def test_percentage_offer_rejects_values_over_100():
    with pytest.raises(ValidationError):
        OfferCreateRequest(
            name="Invalid discount",
            discount_type="percentage",
            discount_value=101,
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(days=1),
        )


def test_campaign_requires_end_after_start():
    start = datetime.utcnow()
    with pytest.raises(ValidationError):
        CampaignCreateRequest(
            name="Invalid campaign",
            starts_at=start,
            ends_at=start,
        )
