"""
User Repository — data access layer for User model.
All DB queries live here; services call this layer only.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        )

    def exists_by_email(self, email: str) -> bool:
        return (
            self.db.query(User.id)
            .filter(User.email == email.lower().strip())
            .first()
        ) is not None

    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.EMPLOYEE,
    ) -> User:
        user = User(
            name=name.strip(),
            email=email.lower().strip(),
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_all(self) -> list[User]:
        return self.db.query(User).order_by(User.id.asc()).all()

    def update(self, user: User, **kwargs) -> User:
        for field, value in kwargs.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user: User) -> User:
        user.is_active = False
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
