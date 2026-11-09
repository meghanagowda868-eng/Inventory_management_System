"""Analytics endpoints for inventory intelligence dashboard."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_token_data
from app.schemas.stock_movement import (
    InventoryDashboardSummary,
    MovementSummaryItem,
    RiskSnapshotResponse,
    StockMovementResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/inventory", tags=["Analytics"])


@router.get(
    "/analytics/dashboard",
    response_model=InventoryDashboardSummary,
    summary="Inventory system dashboard summary",
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    return AnalyticsService(db).get_dashboard_summary()


@router.get(
    "/analytics/recent-movements",
    response_model=list[StockMovementResponse],
    summary="Recent stock movements",
)
def get_recent_movements(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    return AnalyticsService(db).get_recent_movements(limit=limit)


@router.get(
    "/analytics/movements",
    response_model=list[MovementSummaryItem],
    summary="Stock movement summary grouped by day",
)
def get_movement_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    return AnalyticsService(db).get_movement_summary(days=days)


@router.get(
    "/analytics/risk",
    response_model=RiskSnapshotResponse,
    summary="Risk snapshot for low-stock and high-risk inventory items",
)
def get_risk_snapshot(
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    return AnalyticsService(db).get_risk_snapshot()
