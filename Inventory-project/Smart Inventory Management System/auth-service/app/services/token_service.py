"""
JWT + Refresh Token service for Auth Service.
Handles creation, verification, and revocation of tokens.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.token import RefreshToken
from app.models.user import User
from app.utils.exceptions import InvalidTokenException, TokenExpiredException

settings = get_settings()


class TokenService:
    """Manages JWT access tokens and refresh token lifecycle."""

    # ── JWT Access Tokens ─────────────────────────────────────────────────

    @staticmethod
    def create_access_token(user: User) -> tuple[str, int]:
        """
        Create a signed JWT access token.
        Returns (token_string, expires_in_seconds).
        """
        expire_minutes = settings.jwt_access_token_expire_minutes
        expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expire_minutes)

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "exp": expire,
            "iat": datetime.now(tz=timezone.utc),
            "type": "access",
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return token, expire_minutes * 60

    @staticmethod
    def decode_access_token(token: str) -> dict:
        """
        Decode and validate a JWT access token.
        Raises InvalidTokenException or TokenExpiredException on failure.
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                raise InvalidTokenException("Not an access token")
            return payload
        except JWTError as exc:
            if "expired" in str(exc).lower():
                raise TokenExpiredException()
            raise InvalidTokenException() from exc

    # ── Refresh Tokens ────────────────────────────────────────────────────

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """SHA-256 hash a raw token for secure storage."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def create_refresh_token(cls, db: Session, user: User) -> str:
        """
        Generate a secure random refresh token, store its hash in DB.
        Returns the raw token (sent to client once).
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = cls._hash_token(raw_token)
        expire_days = settings.jwt_refresh_token_expire_days
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=expire_days)

        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(db_token)
        db.commit()
        return raw_token

    @classmethod
    def verify_refresh_token(cls, db: Session, raw_token: str) -> Optional[RefreshToken]:
        """
        Verify a refresh token by hash lookup.
        Returns the RefreshToken record or raises InvalidTokenException.
        """
        token_hash = cls._hash_token(raw_token)
        db_token = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
            .first()
        )
        if not db_token:
            raise InvalidTokenException("Refresh token not found or already revoked")

        if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(tz=timezone.utc):
            db_token.is_revoked = True
            db.commit()
            raise TokenExpiredException("Refresh token has expired")

        return db_token

    @classmethod
    def revoke_refresh_token(cls, db: Session, raw_token: str) -> None:
        """Revoke a specific refresh token (logout)."""
        token_hash = cls._hash_token(raw_token)
        db_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )
        if db_token:
            db_token.is_revoked = True
            db.commit()

    @classmethod
    def revoke_all_user_tokens(cls, db: Session, user_id: int) -> None:
        """Revoke all refresh tokens for a user (force logout all devices)."""
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,  # noqa: E712
        ).update({"is_revoked": True})
        db.commit()
