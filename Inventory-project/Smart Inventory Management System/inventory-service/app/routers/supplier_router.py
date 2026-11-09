"""Supplier management router for inventory service."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_token_data, require_role, TokenData
from app.schemas.supplier import (
    SupplierCreateRequest,
    SupplierResponse,
    SupplierUpdateRequest,
)
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter(prefix="/inventory/suppliers", tags=["Suppliers"])


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[SupplierResponse], summary="List suppliers")
def list_suppliers(
    include_inactive: bool = Query(default=False, description="Include deactivated suppliers"),
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """List suppliers in the system."""
    return PurchaseOrderService(db).list_suppliers(include_inactive=include_inactive)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED, summary="Create a new supplier")
def create_supplier(
    data: SupplierCreateRequest,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Create a new supplier profile."""
    try:
        return PurchaseOrderService(db).create_supplier(data)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/{supplier_id}", response_model=SupplierResponse, summary="Get supplier by ID")
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Fetch supplier profile by ID."""
    try:
        return PurchaseOrderService(db).get_supplier(supplier_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{supplier_id}", response_model=SupplierResponse, summary="Update supplier")
def update_supplier(
    supplier_id: int,
    data: SupplierUpdateRequest,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    """Update supplier profile."""
    try:
        return PurchaseOrderService(db).update_supplier(supplier_id, data)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.delete("/{supplier_id}", summary="Deactivate supplier")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    token: TokenData = Depends(require_role("admin")),
):
    """Deactivate supplier (soft delete). Admin only."""
    try:
        return PurchaseOrderService(db).delete_supplier(supplier_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
