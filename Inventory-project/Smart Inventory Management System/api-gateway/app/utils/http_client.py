"""
Async HTTP client for proxying requests to downstream services.
Uses httpx with connection pooling.
"""
import httpx
from app.config import get_settings

settings = get_settings()

# Shared async client (reuse connections across requests)
_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=settings.request_timeout)
    return _client


async def close_http_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def proxy_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict,
    params: dict | None = None,
    body: bytes | None = None,
) -> httpx.Response:
    """
    Forward a request to a downstream service.
    Strips hop-by-hop headers before forwarding.
    """
    # Remove headers that should not be forwarded
    forward_headers = {
        k: v for k, v in headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }

    return await client.request(
        method=method,
        url=url,
        headers=forward_headers,
        params=params,
        content=body,
    )
