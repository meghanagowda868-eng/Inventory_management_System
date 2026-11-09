"""
FastAPI dependency injection for auth validation.
Used by routers to get the currently authenticated user.
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenService
from app.utils.exceptions import (
    InactiveUserException,
    InsufficientPermissionsException,
    UserNotFoundException,
)

_bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode JWT from Authorization header.
    Returns the authenticated User ORM object.
    """
    payload = TokenService.decode_access_token(credentials.credentials)
    user_id: int = int(payload["sub"])

    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise UserNotFoundException()
    if not user.is_active:
        raise InactiveUserException()
    return user


def require_role(*roles: UserRole):
    """
    Dependency factory that enforces role-based access.
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))
    """
    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise InsufficientPermissionsException(
                f"Required roles: {[r.value for r in roles]}"
            )
        return current_user
    return _check_role
