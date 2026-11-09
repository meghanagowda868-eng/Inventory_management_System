"""API Gateway — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.auth_middleware import JWTAuthMiddleware
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.routers.proxy_routers import ai_router, auth_router, inventory_router
from app.utils.http_client import close_http_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_http_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        description=(
            "Central API Gateway for the Smart Inventory Management System.\n\n"
            "Routes all requests to Auth, Inventory, and AI services.\n"
            "Validates JWT before forwarding protected requests."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS (frontend → gateway) ─────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Middleware (order matters: outer → inner) ─────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(JWTAuthMiddleware)

    # ── Service proxy routers ─────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(inventory_router)
    app.include_router(ai_router)

    # ── Gateway info endpoint ─────────────────────────────────────────────
    @app.get("/", tags=["Gateway"])
    def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "services": {
                "auth": f"{settings.auth_service_url}/docs",
                "inventory": f"{settings.inventory_service_url}/docs",
                "ai": f"{settings.ai_service_url}/docs",
            },
            "api_prefix": "/api/v1",
        }

    @app.get("/health", tags=["Gateway"])
    def health():
        return {"status": "healthy", "service": "api-gateway"}

    return app


app = create_app()
