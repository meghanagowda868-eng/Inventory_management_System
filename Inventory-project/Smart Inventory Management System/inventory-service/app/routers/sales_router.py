"""FastAPI router for sales orders, POS checkout, order tracking, and refunds."""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import TokenData, require_role, get_token_data
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderRefundRequest,
    SalesOrderResponse,
    SalesSummaryResponse,
)
from app.services.sales_service import SalesService

router = APIRouter(prefix="/sales", tags=["Sales Management"])


@router.post("", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    payload: SalesOrderCreate,
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Process a checkout sale transaction, deduct stock in real time, and log stock ledger."""
    service = SalesService(db)
    try:
        return service.create_sales_order(payload, created_by=token.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[SalesOrderResponse])
def list_sales_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: COMPLETED, REFUNDED, CANCELLED"),
    search: Optional[str] = Query(None, description="Search by order number or customer name"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_token_data),
):
    """List recent sales orders with pagination and filtering."""
    service = SalesService(db)
    orders, _ = service.list_sales_orders(
        page=page,
        limit=limit,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )
    return orders


@router.get("/summary", response_model=SalesSummaryResponse)
def get_sales_summary(
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_token_data),
):
    """Get high-level summary KPIs for sales transactions."""
    service = SalesService(db)
    return service.get_sales_summary()


@router.get("/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_token_data),
):
    """Get complete sales order details and line items."""
    service = SalesService(db)
    try:
        return service.get_sales_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{order_id}/refund", response_model=SalesOrderResponse)
def refund_sales_order(
    order_id: int,
    payload: SalesOrderRefundRequest,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Refund or cancel a sales order and return stock back into inventory (Manager/Admin only)."""
    service = SalesService(db)
    try:
        return service.refund_sales_order(order_id, user_id=token.user_id, reason=payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
