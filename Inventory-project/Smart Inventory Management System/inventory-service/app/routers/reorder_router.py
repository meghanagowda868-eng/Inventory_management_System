"""Reorder Management Router — endpoints for stock replenishment workflow."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_token_data, require_role, TokenData
from app.schemas.purchase_order import PurchaseOrderResponse
from app.schemas.reorder import (
    ReorderDetectionItem,
    ReorderRequestCreate,
    ReorderRequestReject,
    ReorderRequestResponse,
    ReorderRequestUpdate,
    ReorderSummaryResponse,
    ReorderToPOCreateRequest,
)
from app.services.reorder_service import ReorderService

router = APIRouter(prefix="/inventory/reorders", tags=["Reorder Management"])


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Reorder Detection & Analytics ────────────────────────────────────────────

@router.get("/required", response_model=list[ReorderDetectionItem], summary="List products requiring reorder")
def list_required_reorders(
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Detect and return all products where current_stock <= reorder_point."""
    return ReorderService(db).list_reorder_recommendations()


@router.get("/summary", response_model=ReorderSummaryResponse, summary="Get summary metrics of reorders")
def get_reorder_summary(
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Return dashboard KPI counters for reorder recommendations, requests, and POs."""
    return ReorderService(db).get_summary()


# ── Reorder Requests CRUD ───────────────────────────────────────────────────

@router.get("", response_model=list[ReorderRequestResponse], summary="List reorder requests")
def list_reorder_requests(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (PENDING, APPROVED, etc.)"),
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """List reorder requests with optional status filtering."""
    return ReorderService(db).list_reorder_requests(status=status_filter)


@router.post("", response_model=ReorderRequestResponse, status_code=status.HTTP_201_CREATED, summary="Create a reorder request")
def create_reorder_request(
    data: ReorderRequestCreate,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Create a new reorder request. Prevents duplicate active requests for the same product."""
    try:
        return ReorderService(db).create_reorder_request(data=data, requested_by=token.user_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/{reorder_id}", response_model=ReorderRequestResponse, summary="Get reorder request by ID")
def get_reorder_request(
    reorder_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Fetch details of a single reorder request."""
    try:
        return ReorderService(db).get_reorder_request(reorder_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{reorder_id}", response_model=ReorderRequestResponse, summary="Update pending reorder request")
def update_reorder_request(
    reorder_id: int,
    data: ReorderRequestUpdate,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Update quantity, supplier, or reason on a pending reorder request."""
    try:
        return ReorderService(db).update_reorder_request(reorder_id, data)
    except ValueError as exc:
        raise _bad_request(exc) from exc


# ── Approval Workflow ────────────────────────────────────────────────────────

@router.post("/{reorder_id}/approve", response_model=ReorderRequestResponse, summary="Approve reorder request")
def approve_reorder_request(
    reorder_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Approve a pending reorder request. Only managers and admins can approve."""
    try:
        return ReorderService(db).approve_reorder_request(reorder_id, approved_by=token.user_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/{reorder_id}/reject", response_model=ReorderRequestResponse, summary="Reject reorder request")
def reject_reorder_request(
    reorder_id: int,
    data: ReorderRequestReject,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Reject a pending reorder request. Requires rejection reason."""
    try:
        return ReorderService(db).reject_reorder_request(
            reorder_id, rejection_reason=data.rejection_reason, rejected_by=token.user_id
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


# ── Purchase Order Conversion ────────────────────────────────────────────────

@router.post("/{reorder_id}/purchase-order", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED, summary="Convert approved reorder to PO")
def create_purchase_order_from_reorder(
    reorder_id: int,
    data: Optional[ReorderToPOCreateRequest] = None,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Convert an approved reorder request into a Purchase Order."""
    try:
        req_data = data or ReorderToPOCreateRequest()
        return ReorderService(db).create_purchase_order_from_reorder(
            reorder_id=reorder_id, data=req_data, created_by=token.user_id
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc
