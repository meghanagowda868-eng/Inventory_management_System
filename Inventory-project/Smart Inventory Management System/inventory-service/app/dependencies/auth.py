"""
JWT auth dependency for Inventory Service.
Validates tokens issued by Auth Service using the shared JWT secret.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.utils.exceptions import InsufficientPermissionsException

settings = get_settings()
_bearer_scheme = HTTPBearer()


class TokenData:
    def __init__(self, user_id: int, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role


def get_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> TokenData:
    """Decode and validate JWT. Return token payload as TokenData."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise ValueError("Token is not an access token")
        return TokenData(
            user_id=int(payload["sub"]),
            email=payload["email"],
            role=payload["role"],
        )
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(*roles: str):
    """Reusable dependency for backend authorization.

    Authentication is handled by get_token_data(); authorization is checked here.
    The JWT and DB remain the single source of truth for a user's role.
    """
    allowed_roles = {str(role).lower() for role in roles}

    def _check(token_data: TokenData = Depends(get_token_data)) -> TokenData:
        current_role = str(token_data.role).lower()
        if current_role not in allowed_roles:
            raise InsufficientPermissionsException(
                f"Required roles: {sorted(allowed_roles)}, your role: {current_role}"
            )
        return token_data

    return _check


def require_admin():
    return require_role("admin")


def require_manager():
    return require_role("manager")


def require_admin_or_manager():
    return require_role("admin", "manager")
