from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import get_settings
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _token(token_type: str) -> str:
    settings = get_settings()
    return jwt.encode(
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


def test_ai_endpoint_rejects_invalid_and_non_access_tokens(client):
    payload = {
        "product_id": 1,
        "product_name": "Test product",
        "category": "Test",
        "current_quantity": 5,
        "price": 1.0,
    }

    missing = client.post("/ai/predict-demand", json=payload)
    invalid = client.post(
        "/ai/predict-demand",
        json=payload,
        headers={"Authorization": "Bearer invalid"},
    )
    non_access = client.post(
        "/ai/predict-demand",
        json=payload,
        headers={"Authorization": f"Bearer {_token('refresh')}"},
    )

    assert missing.status_code == 403
    assert invalid.status_code == 401
    assert non_access.status_code == 401


def test_ai_endpoint_accepts_valid_employee_access_token(client):
    payload = {
        "product_id": 1,
        "product_name": "Test product",
        "category": "Test",
        "current_quantity": 5,
        "price": 1.0,
    }

    response = client.post(
        "/ai/predict-demand",
        json=payload,
        headers={"Authorization": f"Bearer {_token('access')}"},
    )

    assert response.status_code == 200
    assert response.json()["product_id"] == 1
