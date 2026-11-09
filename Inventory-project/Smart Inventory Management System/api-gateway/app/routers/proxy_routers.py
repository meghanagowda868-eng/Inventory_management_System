"""
API Gateway — proxy routers for all downstream services.
Adding a new service = add one new router file + register in main.py.
"""
import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.config import get_settings
from app.utils.http_client import get_http_client, proxy_request

logger = logging.getLogger("api_gateway")
settings = get_settings()

# ── Router factory ────────────────────────────────────────────────────────────

def _make_proxy_router(prefix: str, service_url: str, tag: str) -> APIRouter:
    """
    Create a catch-all proxy router for a downstream service.
    All methods and paths are forwarded transparently.
    """
    router = APIRouter(prefix=prefix, tags=[tag])
    downstream_prefix = prefix.removeprefix("/api/v1")

    @router.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def proxy(path: str, request: Request):
        downstream_path = f"{downstream_prefix}/{path}" if path else downstream_prefix
        target_url = f"{service_url}{downstream_path}"
        logger.debug("Proxying %s → %s", request.url.path, target_url)

        body = await request.body()
        headers = dict(request.headers)

        client = await get_http_client()
        try:
            upstream = await proxy_request(
                client=client,
                method=request.method,
                url=target_url,
                headers=headers,
                params=dict(request.query_params),
                body=body or None,
            )
        except httpx.ConnectError:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"detail": f"Service unavailable: {tag}"},
            )
        except httpx.TimeoutException:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=504,
                content={"detail": f"Service timeout: {tag}"},
            )

        # Return response to client with hop-by-hop / transfer headers stripped
        excluded_headers = {"content-length", "content-encoding", "transfer-encoding", "connection"}
        res_headers = {
            k: v for k, v in upstream.headers.items()
            if k.lower() not in excluded_headers
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=res_headers,
            media_type=upstream.headers.get("content-type", "application/json"),
        )

    return router


# ── Service routers ───────────────────────────────────────────────────────────

auth_router = _make_proxy_router(
    prefix="/api/v1/auth",
    service_url=settings.auth_service_url,
    tag="Auth Service",
)

inventory_router = _make_proxy_router(
    prefix="/api/v1/inventory",
    service_url=settings.inventory_service_url,
    tag="Inventory Service",
)

ai_router = _make_proxy_router(
    prefix="/api/v1/ai",
    service_url=settings.ai_service_url,
    tag="AI Service",
)

# ── Future services — add here without touching other code ────────────────────
# supplier_router = _make_proxy_router(...)
# sales_router = _make_proxy_router(...)
