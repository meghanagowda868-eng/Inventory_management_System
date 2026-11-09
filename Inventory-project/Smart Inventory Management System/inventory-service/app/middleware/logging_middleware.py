"""Request logging middleware for Inventory Service."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("inventory_service")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        logger.info("→ [%s] %s %s", request_id, request.method, request.url.path)
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        logger.info(
            "← [%s] %s %s | %d | %.1fms",
            request_id, request.method, request.url.path, response.status_code, ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
