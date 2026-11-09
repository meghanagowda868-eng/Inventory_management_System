"""
Product Router — inventory CRUD + stock management endpoints.
"""
import logging
from pathlib import Path
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import TokenData, get_token_data, require_role
from app.schemas.product import (
    MessageResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductOptionResponse,
    ProductResponse,
    ProductUpdateRequest,
    StockAdjustRequest,
    StockAdjustResponse,
)
from app.services.product_service import ProductService

logger = logging.getLogger("inventory_service")
router = APIRouter(prefix="/inventory", tags=["Inventory"])
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "inventory-service"}


@router.post("/uploads/image", status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    image: UploadFile = File(...),
    token: TokenData = Depends(require_role("admin", "manager")),
):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP, or GIF image")
    suffix = Path(image.filename or "image").suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / filename).write_bytes(await image.read())
    return {"image_url": f"/api/v1/inventory/uploads/{filename}"}


@router.get("/uploads/{filename}")
def get_product_image(filename: str):
    image_path = (UPLOADS_DIR / Path(filename).name).resolve()
    if not image_path.is_file() or image_path.parent != UPLOADS_DIR.resolve():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


# ── List Products ─────────────────────────────────────────────────────────────

@router.get("/products", response_model=ProductListResponse, summary="List products")
def list_products(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Search in name, SKU, category"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    category_id: Optional[int] = Query(default=None, gt=0, description="Filter by category ID"),
    subcategory_id: Optional[int] = Query(default=None, gt=0, description="Filter by subcategory ID"),
    stock_status: Optional[str] = Query(
        default=None,
        description="Filter by: available | low_stock | out_of_stock",
    ),
    token: TokenData = Depends(get_token_data),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    return service.list_products(
        page, page_size, search, category, category_id, subcategory_id, stock_status
    )


@router.get("/products/counts", summary="Get product counts by category and subcategory")
def product_counts(
    token: TokenData = Depends(get_token_data),
    db: Session = Depends(get_db),
):
    return ProductService(db).catalog_counts()


@router.get(
    "/products/options",
    response_model=list[ProductOptionResponse],
    summary="List active product options for inventory workflows",
)
def list_product_options(
    token: TokenData = Depends(get_token_data),
    db: Session = Depends(get_db),
):
    return ProductService(db).list_product_options()


# ── Low Stock Alert ───────────────────────────────────────────────────────────

@router.get(
    "/products/low-stock",
    response_model=list[ProductResponse],
    summary="Get all low stock products",
)
def list_low_stock(
    token: TokenData = Depends(get_token_data),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    return service.list_low_stock()


# ── Create Product ────────────────────────────────────────────────────────────

@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
def create_product(
    data: ProductCreateRequest,
    token: TokenData = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    product = service.create_product(data)
    logger.info("Product created: %s by %s", product.sku, token.email)
    return product


# ── Get Product ───────────────────────────────────────────────────────────────

@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
def get_product(
    product_id: int,
    token: TokenData = Depends(get_token_data),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    return service.get_product(product_id)


# ── Update Product ────────────────────────────────────────────────────────────

@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
)
def update_product(
    product_id: int,
    data: ProductUpdateRequest,
    token: TokenData = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    product = service.update_product(product_id, data)
    logger.info("Product updated: id=%s by %s", product_id, token.email)
    return product


# ── Stock Adjustment ──────────────────────────────────────────────────────────

@router.patch(
    "/products/{product_id}/stock",
    response_model=StockAdjustResponse,
    summary="Adjust product stock (increase or decrease)",
)
def adjust_stock(
    product_id: int,
    data: StockAdjustRequest,
    token: TokenData = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    result = service.adjust_stock(product_id, data)
    logger.info(
        "Stock adjusted: id=%s delta=%s by %s", product_id, data.delta, token.email
    )
    return result


# ── Delete Product ────────────────────────────────────────────────────────────

@router.delete(
    "/products/{product_id}",
    response_model=MessageResponse,
    summary="Soft delete product (admin only)",
)
def delete_product(
    product_id: int,
    token: TokenData = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    result = service.delete_product(product_id)
    logger.info("Product deleted: id=%s by %s", product_id, token.email)
    return result
