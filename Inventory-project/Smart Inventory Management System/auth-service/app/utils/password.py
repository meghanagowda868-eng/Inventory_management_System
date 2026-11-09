"""
Password hashing utilities using bcrypt directly.
Bypasses passlib which is incompatible with bcrypt >= 4.1.
"""
import bcrypt


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of the given password."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False
