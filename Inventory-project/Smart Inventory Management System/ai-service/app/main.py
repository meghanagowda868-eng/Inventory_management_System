"""AI Service — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.ml.demand_model import get_demand_model
from app.routers.ai_router import router as ai_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_service")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm ML model on startup so first request is fast."""
    logger.info("Pre-warming demand prediction model...")
    get_demand_model()
    logger.info("AI Service ready.")
    yield
    logger.info("AI Service shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI microservice for inventory insights, demand prediction, and NL queries.",
        lifespan=lifespan,
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

    app.include_router(ai_router)

    @app.get("/", tags=["Root"])
    def root():
        return {"service": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
