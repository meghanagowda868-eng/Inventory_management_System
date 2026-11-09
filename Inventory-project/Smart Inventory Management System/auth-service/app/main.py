"""
Auth Service — FastAPI application entry point.
"""
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.session import SessionLocal
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.routers.auth_router import router as auth_router
from app.utils.password import hash_password

# ── Logging Configuration ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

settings = get_settings()


def ensure_bootstrap_accounts() -> None:
    accounts = (
        (
            "Admin",
            settings.bootstrap_admin_email,
            settings.bootstrap_admin_password,
            UserRole.ADMIN,
        ),
        (
            "Manager",
            settings.bootstrap_manager_email,
            settings.bootstrap_manager_password,
            UserRole.MANAGER,
        ),
    )
    with SessionLocal() as db:
        users = UserRepository(db)
        for name, email, password, role in accounts:
            if email is None and password is None:
                continue
            if not email or not password:
                raise RuntimeError(
                    f"Both bootstrap email and password must be configured for the {role.value} account"
                )
            if users.get_by_email(email) is None:
                users.create(
                    name=name,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    ensure_bootstrap_accounts()
    yield


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="JWT-based authentication microservice for Smart Inventory System.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom Middleware ─────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(auth_router)

    # ── Root endpoint ─────────────────────────────────────────────────────
    @app.get("/", tags=["Root"])
    def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
        }

    return app


app = create_app()
