"""Purchase Order management router for Inventory Service."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_token_data, require_role, TokenData
from app.schemas.purchase_order import (
    PurchaseOrderCreateRequest,
    PurchaseOrderResponse,
    ReceiveOrderRequest,
)
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter(prefix="/inventory/purchase-orders", tags=["Purchase Orders"])


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[PurchaseOrderResponse], summary="List purchase orders")
def list_purchase_orders(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (ORDERED, RECEIVED, etc.)"),
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """List all purchase orders."""
    return PurchaseOrderService(db).list_orders(status=status_filter)


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED, summary="Create purchase order")
def create_purchase_order(
    data: PurchaseOrderCreateRequest,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Create a new purchase order."""
    try:
        return PurchaseOrderService(db).create_order(data=data, created_by=token.user_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/{order_id}", response_model=PurchaseOrderResponse, summary="Get purchase order by ID")
def get_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Fetch purchase order with line items."""
    try:
        return PurchaseOrderService(db).get_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{order_id}/approve", response_model=PurchaseOrderResponse, summary="Approve purchase order")
def approve_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Approve a draft/pending purchase order."""
    try:
        return PurchaseOrderService(db).approve_order(order_id, approved_by=token.user_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/{order_id}/order", response_model=PurchaseOrderResponse, summary="Mark purchase order as ordered")
def mark_purchase_order_ordered(
    order_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Place purchase order with supplier."""
    try:
        return PurchaseOrderService(db).mark_ordered(order_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/{order_id}/receive", response_model=PurchaseOrderResponse, summary="Receive stock for purchase order")
def receive_purchase_order(
    order_id: int,
    data: Optional[ReceiveOrderRequest] = None,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """
    Receive stock from purchase order. Supports partial receipts.
    Automatically increments product and warehouse stock and creates stock movements.
    """
    try:
        return PurchaseOrderService(db).receive_order(order_id, received_by=token.user_id, data=data)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/{order_id}/cancel", response_model=PurchaseOrderResponse, summary="Cancel purchase order")
def cancel_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Cancel a purchase order."""
    try:
        return PurchaseOrderService(db).cancel_order(order_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
