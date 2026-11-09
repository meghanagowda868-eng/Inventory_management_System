from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.config import get_settings
from app.dependencies.auth import get_token_data


def _credentials(token_type: str) -> HTTPAuthorizationCredentials:
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "1",
            "email": "employee@example.com",
            "role": "employee",
            "type": token_type,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_inventory_accepts_access_token():
    token_data = get_token_data(_credentials("access"))

    assert token_data.user_id == 1
    assert token_data.role == "employee"


def test_inventory_rejects_non_access_token():
    with pytest.raises(HTTPException) as error:
        get_token_data(_credentials("refresh"))

    assert error.value.status_code == 401
