"""Catalog and warehouse router for the Inventory Service."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_token_data, require_role
from app.schemas.category import CategoryCreateRequest, CategoryResponse, CategoryUpdateRequest
from app.schemas.subcategory import (
    SubcategoryCreateRequest,
    SubcategoryResponse,
    SubcategoryUpdateRequest,
)
from app.schemas.warehouse import WarehouseCreateRequest, WarehouseResponse, WarehouseUpdateRequest
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/inventory", tags=["Catalog & Warehouses"])


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    try:
        return CatalogService(db).list_categories()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return CatalogService(db).create_category(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return CatalogService(db).update_category(category_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        CatalogService(db).delete_category(category_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/subcategories", response_model=list[SubcategoryResponse])
def list_subcategories(
    category_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    token=Depends(get_token_data),
):
    try:
        return CatalogService(db).list_subcategories(category_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/subcategories", response_model=SubcategoryResponse, status_code=status.HTTP_201_CREATED)
def create_subcategory(
    data: SubcategoryCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return CatalogService(db).create_subcategory(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
def update_subcategory(
    subcategory_id: int,
    data: SubcategoryUpdateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return CatalogService(db).update_subcategory(subcategory_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/subcategories/{subcategory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subcategory(
    subcategory_id: int,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        CatalogService(db).delete_subcategory(subcategory_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(
    db: Session = Depends(get_db),
    token=Depends(require_role("admin", "manager")),
):
    try:
        return CatalogService(db).list_warehouses()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    data: WarehouseCreateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return CatalogService(db).create_warehouse(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdateRequest,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        return CatalogService(db).update_warehouse(warehouse_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    token=Depends(require_role("admin")),
):
    try:
        CatalogService(db).delete_warehouse(warehouse_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
