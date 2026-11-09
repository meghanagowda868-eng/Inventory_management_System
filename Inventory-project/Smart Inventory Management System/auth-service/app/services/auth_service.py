"""
Auth Service — business logic layer.
Orchestrates UserRepository + TokenService.
"""
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    ChangePasswordRequest,
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from app.services.token_service import TokenService
from app.utils.exceptions import (
    InactiveUserException,
    InsufficientPermissionsException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.utils.password import hash_password, verify_password


class AuthService:
    """Core authentication business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_service = TokenService()

    # ── Register ──────────────────────────────────────────────────────────

    def register(self, data: RegisterRequest) -> UserResponse:
        if self.user_repo.exists_by_email(data.email):
            raise UserAlreadyExistsException()

        hashed = hash_password(data.password)
        user = self.user_repo.create(
            name=data.name,
            email=data.email,
            password_hash=hashed,
            role=data.role,
        )
        return UserResponse.model_validate(user)

    # ── Login ─────────────────────────────────────────────────────────────

    def login(self, data: LoginRequest) -> LoginResponse:
        user = self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsException()
        if not user.is_active:
            raise InactiveUserException()

        access_token, expires_in = TokenService.create_access_token(user)
        refresh_token = TokenService.create_refresh_token(self.db, user)

        return LoginResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            ),
        )

    # ── Refresh ───────────────────────────────────────────────────────────

    def refresh_access_token(self, raw_refresh_token: str) -> dict:
        """Verify refresh token, return new access token."""
        db_token = TokenService.verify_refresh_token(self.db, raw_refresh_token)
        user = self.user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsException("User not found or inactive")

        access_token, expires_in = TokenService.create_access_token(user)
        return {"access_token": access_token, "token_type": "bearer", "expires_in": expires_in}

    # ── Logout ────────────────────────────────────────────────────────────

    def logout(self, raw_refresh_token: str) -> None:
        """Revoke the provided refresh token."""
        TokenService.revoke_refresh_token(self.db, raw_refresh_token)

    # ── Profile ───────────────────────────────────────────────────────────

    def get_profile(self, user: User) -> UserResponse:
        return UserResponse.model_validate(user)

    def update_profile(self, user: User, data: UpdateProfileRequest) -> UserResponse:
        if data.email and data.email != user.email:
            if self.user_repo.exists_by_email(data.email):
                raise UserAlreadyExistsException("Email already in use")

        updates = {}
        if data.name:
            updates["name"] = data.name.strip()
        if data.email:
            updates["email"] = data.email.lower().strip()

        updated_user = self.user_repo.update(user, **updates)
        return UserResponse.model_validate(updated_user)

    # ── Change Password ───────────────────────────────────────────────────

    def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsException("Current password is incorrect")

        new_hash = hash_password(data.new_password)
        self.user_repo.update(user, password_hash=new_hash)
        # Revoke all refresh tokens on password change (security best practice)
        TokenService.revoke_all_user_tokens(self.db, user.id)

    def list_users(self) -> list[UserResponse]:
        users = self.user_repo.list_all()
        return [UserResponse.model_validate(user) for user in users]

    def update_user_role(
        self,
        user_id: int,
        data: UpdateUserRoleRequest,
        actor_id: int,
    ) -> UserResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        if user_id == actor_id and data.role != UserRole.ADMIN:
            raise InsufficientPermissionsException("You cannot remove your own admin role")

        updated_user = self.user_repo.update(user, role=data.role)
        return UserResponse.model_validate(updated_user)

    def admin_create_user(self, data: AdminCreateUserRequest) -> UserResponse:
        if self.user_repo.exists_by_email(data.email):
            raise UserAlreadyExistsException()
        user = self.user_repo.create(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
        )
        return UserResponse.model_validate(user)

    def admin_update_user(
        self,
        user_id: int,
        data: AdminUpdateUserRequest,
        actor_id: int,
    ) -> UserResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        if user_id == actor_id and (
            (data.role is not None and data.role != UserRole.ADMIN)
            or data.is_active is False
        ):
            raise InsufficientPermissionsException("You cannot remove your own admin access")
        if data.email and data.email.lower().strip() != user.email:
            if self.user_repo.exists_by_email(data.email):
                raise UserAlreadyExistsException("Email already in use")
        updates = data.model_dump(exclude_none=True)
        if "name" in updates:
            updates["name"] = updates["name"].strip()
        if "email" in updates:
            updates["email"] = updates["email"].lower().strip()
        updated_user = self.user_repo.update(user, **updates)
        if "is_active" in updates and not updates["is_active"]:
            TokenService.revoke_all_user_tokens(self.db, user.id)
        return UserResponse.model_validate(updated_user)

    def admin_delete_user(self, user_id: int) -> UserResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        TokenService.revoke_all_user_tokens(self.db, user.id)
        response = UserResponse.model_validate(user)
        self.user_repo.delete(user)
        return response
