"""
Auth Router — all authentication endpoints.
Thin controller: validates input, calls AuthService, returns response.
"""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import (
    AccessTokenResponse,
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.utils.exceptions import InsufficientPermissionsException

logger = logging.getLogger("auth_service")
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Health Check ──────────────────────────────────────────────────────────────

@router.get("/health", response_model=dict, summary="Health Check")
def health_check():
    return {"status": "healthy", "service": "auth-service"}


# ── Register ──────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user account. Role defaults to 'employee'."""
    service = AuthService(db)
    user = service.register(data)
    logger.info("New user registered: %s", data.email)
    return user


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and receive JWT tokens",
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate with email/password. Returns access token + refresh token."""
    service = AuthService(db)
    result = service.login(data)
    logger.info("User logged in: %s", data.email)
    return result


# ── Refresh Token ─────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh access token",
)
def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token."""
    service = AuthService(db)
    return service.refresh_access_token(data.refresh_token)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke refresh token",
)
def logout(
    data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke the provided refresh token. User must be authenticated."""
    service = AuthService(db)
    service.logout(data.refresh_token)
    logger.info("User logged out: %s", current_user.email)
    return MessageResponse(message="Successfully logged out")


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_profile(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile",
)
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update name or email for the current user."""
    service = AuthService(db)
    return service.update_profile(current_user, data)


# ── Change Password ───────────────────────────────────────────────────────────

@router.put(
    "/change-password",
    response_model=MessageResponse,
    summary="Change user password",
)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change the authenticated user's password.
    Also revokes all refresh tokens for security.
    """
    service = AuthService(db)
    service.change_password(current_user, data)
    return MessageResponse(message="Password changed successfully. Please log in again.")


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users for admin role management",
)
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role.value != "admin":
        raise InsufficientPermissionsException("Only admins can list users")
    return AuthService(db).list_users()


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update a user's role",
)
def update_user_role(
    user_id: int,
    data: UpdateUserRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role.value != "admin":
        raise InsufficientPermissionsException("Only admins can update user roles")
    return AuthService(db).update_user_role(user_id, data, actor_id=current_user.id)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_as_admin(
    data: AdminCreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role.value != "admin":
        raise InsufficientPermissionsException("Only admins can create users")
    return AuthService(db).admin_create_user(data)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_as_admin(
    user_id: int,
    data: AdminUpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role.value != "admin":
        raise InsufficientPermissionsException("Only admins can update users")
    return AuthService(db).admin_update_user(user_id, data, actor_id=current_user.id)


@router.delete("/users/{user_id}/permanent", response_model=UserResponse)
def delete_user_as_admin(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role.value != "admin":
        raise InsufficientPermissionsException("Only admins can delete users")
    if user_id == current_user.id:
        raise InsufficientPermissionsException("You cannot delete your own account")
    return AuthService(db).admin_delete_user(user_id)
