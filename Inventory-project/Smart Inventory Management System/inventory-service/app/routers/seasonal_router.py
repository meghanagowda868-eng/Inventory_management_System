"""Seasonal demand and festive promotion APIs."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_token_data, require_role
from app.schemas.seasonal import ProductFestiveForecastResponse, SeasonalForecastRequest
from app.schemas.promotion import (
    CampaignApplyDiscountRequest,
    CampaignCreateRequest,
    CampaignResponse,
    CampaignUpdateRequest,
    OfferCreateRequest,
    OfferResponse,
    OfferUpdateRequest,
    PricingResponse,
)
from app.schemas.seasonal import (
    SeasonalDemandResponse,
    SeasonalEventCreateRequest,
    SeasonalEventResponse,
)
from app.schemas.purchase_order import (
    PurchaseOrderCreateRequest,
    PurchaseOrderResponse,
    SupplierCreateRequest,
    SupplierResponse,
)
from app.schemas.festive_discount import (
    FestiveDiscountPerformanceCreateRequest,
    FestiveDiscountPerformanceResponse,
    FestiveDiscountRecommendationResponse,
    FestiveDiscountRequest,
    FestiveDiscountSimulationRequest,
    FestiveDiscountSimulationResponse,
)
from app.services.promotion_service import PromotionService
from app.services.purchase_order_service import PurchaseOrderService
from app.services.festive_discount_service import FestiveDiscountService
from app.services.seasonal_service import SeasonalService

router = APIRouter(prefix="/inventory", tags=["Seasonal Demand & Offers"])


def bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/seasonal-events", response_model=list[SeasonalEventResponse])
def list_seasonal_events(
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    return SeasonalService(db).list_events()


@router.post("/seasonal-events", response_model=SeasonalEventResponse, status_code=status.HTTP_201_CREATED)
def create_seasonal_event(
    data: SeasonalEventCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return SeasonalService(db).create_event(data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/seasonal-demand", response_model=SeasonalDemandResponse)
def seasonal_demand(
    event_id: int | None = Query(default=None, ge=1),
    festival: str | None = Query(default=None, min_length=2, max_length=120),
    year: int | None = Query(default=None, ge=2000, le=2100),
    product_id: int | None = Query(default=None, gt=0),
    category_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return SeasonalService(db).recommendations(
            event_id=event_id,
            festival=festival,
            year=year,
            product_id=product_id,
            category_id=category_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc



@router.post(
    "/seasonal-demand/forecast",
    response_model=ProductFestiveForecastResponse,
    summary="Forecast festive demand and stock readiness for one product",
)
def forecast_product_demand(
    data: SeasonalForecastRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return SeasonalService(db).forecast_product(
            product_id=data.product_id,
            festival=data.festival,
            year=data.year,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(db: Session = Depends(get_db), token=Depends(get_token_data)):
    return PromotionService(db).list_campaigns()


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: CampaignCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return PromotionService(db).create_campaign(data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post(
    "/campaigns/{campaign_id}/apply-discount",
    response_model=OfferResponse,
    summary="Apply the manager-confirmed campaign discount to selected electronics",
)
def apply_campaign_discount(
    campaign_id: int,
    data: CampaignApplyDiscountRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return PromotionService(db).apply_campaign_discount(campaign_id, data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post(
    "/festive-discounts/recommend",
    response_model=FestiveDiscountRecommendationResponse,
    summary="Recommend a bounded, explainable festive discount for one product",
)
def recommend_festive_discount(
    data: FestiveDiscountRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return FestiveDiscountService(db).recommend(data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.post(
    "/festive-discounts/simulate",
    response_model=FestiveDiscountSimulationResponse,
    summary="Simulate a manager-selected discount without applying it",
)
def simulate_festive_discount(
    data: FestiveDiscountSimulationRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return FestiveDiscountService(db).simulate(data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get(
    "/festive-discounts/performance",
    response_model=list[FestiveDiscountPerformanceResponse],
    summary="List recorded actual festive discount performance",
)
def list_festive_discount_performance(
    festival_event_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    return FestiveDiscountService(db).list_performance(festival_event_id)


@router.post(
    "/festive-discounts/performance",
    response_model=FestiveDiscountPerformanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record actual campaign sales results for future festive planning",
)
def record_festive_discount_performance(
    data: FestiveDiscountPerformanceCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return FestiveDiscountService(db).record_performance(data, recorded_by=token.user_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    data: CampaignUpdateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return PromotionService(db).update_campaign(campaign_id, data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        PromotionService(db).delete_campaign(campaign_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/offers", response_model=list[OfferResponse])
def list_offers(db: Session = Depends(get_db), token=Depends(get_token_data)):
    return PromotionService(db).list_offers()


@router.post("/offers", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    data: OfferCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return PromotionService(db).create_offer(data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.put("/offers/{offer_id}", response_model=OfferResponse)
def update_offer(
    offer_id: int,
    data: OfferUpdateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return PromotionService(db).update_offer(offer_id, data)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.patch("/offers/{offer_id}/disable", response_model=OfferResponse)
def disable_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return PromotionService(db).disable_offer(offer_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.delete("/offers/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        PromotionService(db).delete_offer(offer_id)
    except ValueError as exc:
        raise bad_request(exc) from exc


@router.get("/products/{product_id}/pricing", response_model=PricingResponse)
def product_pricing(
    product_id: int,
    purchase_amount: float | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    try:
        return PromotionService(db).pricing(product_id, purchase_amount)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
