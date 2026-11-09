"""Inventory Service — FastAPI application entry point."""
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.routers.analytics_router import router as analytics_router
from app.routers.catalog_router import router as catalog_router
from app.routers.product_router import router as product_router
from app.routers.purchase_order_router import router as purchase_order_router
from app.routers.reorder_router import router as reorder_router
from app.routers.seasonal_router import router as seasonal_router
from app.routers.supplier_router import router as supplier_router
from app.routers.sales_router import router as sales_router
from app.routers.notification_router import router as notification_router
from app.routers.report_router import router as report_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

settings = get_settings()
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Product inventory management microservice with sales checkout, reorder workflows, alerts, and analytics.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
    app.include_router(catalog_router)
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(reorder_router)
    app.include_router(supplier_router)
    app.include_router(purchase_order_router)
    app.include_router(seasonal_router)
    app.include_router(notification_router)
    app.include_router(report_router)
    app.include_router(analytics_router)

    @app.get("/", tags=["Root"])
    def root():
        return {"service": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
