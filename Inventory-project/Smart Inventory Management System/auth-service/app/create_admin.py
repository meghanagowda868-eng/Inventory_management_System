"""Create the first administrator from a trusted local environment."""
from getpass import getpass

from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.schemas.user import AdminCreateUserRequest
from app.services.auth_service import AuthService
from app.utils.exceptions import UserAlreadyExistsException


def main() -> int:
    with SessionLocal() as db:
        existing_admin = db.query(User.id).filter(User.role == UserRole.ADMIN).first()
        if existing_admin:
            print("An administrator already exists; bootstrap was not run.")
            return 1

        name = input("Administrator name: ").strip()
        email = input("Administrator email: ").strip()
        password = getpass("Administrator password: ")
        if password != getpass("Confirm password: "):
            print("Passwords do not match.")
            return 1

        try:
            data = AdminCreateUserRequest(
                name=name,
                email=email,
                password=password,
                role=UserRole.ADMIN,
            )
            user = AuthService(db).admin_create_user(data)
        except (ValueError, UserAlreadyExistsException) as exc:
            print(f"Administrator was not created: {exc}")
            return 1

    print(f"Created administrator account for {user.email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())