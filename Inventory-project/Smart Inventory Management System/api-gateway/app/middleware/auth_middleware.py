"""
JWT validation middleware for API Gateway.
Validates the access token before forwarding to downstream services.
Public paths (login, register, health) are whitelisted.
"""
import logging

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger("api_gateway.auth")
settings = get_settings()

# Paths that do NOT require JWT
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/health",
    "/api/v1/inventory/health",
    "/api/v1/ai/health",
}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Validate JWT on every request except whitelisted public paths.
    Injects X-User-ID, X-User-Email, X-User-Role headers for downstream services.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Allow CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow public paths through
        if (
            path in PUBLIC_PATHS
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi")
            or path.startswith("/api/v1/inventory/uploads/")
        ):
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                raise JWTError("Not an access token")
        except JWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired access token"},
            )

        # Inject user context headers for downstream services
        request.state.user_id = payload.get("sub")
        request.state.user_email = payload.get("email")
        request.state.user_role = payload.get("role")

        response = await call_next(request)
        return response
