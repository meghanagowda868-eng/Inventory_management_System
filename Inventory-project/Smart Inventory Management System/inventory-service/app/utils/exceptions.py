"""Custom exceptions for Inventory Service."""
from fastapi import HTTPException, status


class ProductNotFoundException(HTTPException):
    def __init__(self, product_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id={product_id} not found",
        )


class SKUAlreadyExistsException(HTTPException):
    def __init__(self, sku: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{sku}' already exists",
        )


class InsufficientStockException(HTTPException):
    def __init__(self, current: int, requested: int):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient stock: available={current}, requested decrease={requested}",
        )


class InsufficientPermissionsException(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
