# Auth Service tests
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_USER"] = "test-user"
os.environ["DB_PASSWORD"] = "test-password"
os.environ["JWT_SECRET_KEY"] = "test-signing-key-for-isolated-auth-tests"

from app.main import app, ensure_bootstrap_accounts, settings
from app.database.session import Base, get_db
from app.models.user import User, UserRole
from app.utils.password import hash_password, verify_password

# ── In-memory SQLite for testing ──────────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test_auth.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.SessionLocal", TestingSessionLocal):
        with (
            patch.object(settings, "bootstrap_admin_email", "admin@gmail.com"),
            patch.object(settings, "bootstrap_admin_password", "admin@123"),
            patch.object(settings, "bootstrap_manager_email", "manager@gmail.com"),
            patch.object(settings, "bootstrap_manager_password", "manager@123"),
        ):
            with TestClient(app) as c:
                yield c
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health_check(client):
    response = client.get("/auth/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_bootstrap_accounts_can_login(client):
    for email, password, role in (
        ("admin@gmail.com", "admin@123", "admin"),
        ("manager@gmail.com", "manager@123", "manager"),
    ):
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200
        assert response.json()["user"]["role"] == role


def test_bootstrap_does_not_overwrite_existing_password(client, db):
    admin = db.query(User).filter(User.email == "admin@gmail.com").first()
    admin.password_hash = hash_password("ChangedPass123!")
    db.commit()

    ensure_bootstrap_accounts()

    db.refresh(admin)
    assert verify_password("ChangedPass123!", admin.password_hash)
    response = client.post(
        "/auth/login",
        json={"email": admin.email, "password": "ChangedPass123!"},
    )
    assert response.status_code == 200


def test_register_success(client):
    response = client.post("/auth/register", json={
        "name": "Test Admin",
        "email": "admin@test.com",
        "password": "SecurePass123!",
        "role": "admin"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "employee"
    assert "password_hash" not in data


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "name": "Duplicate User",
        "email": "dup@test.com",
        "password": "SecurePass123!",
    })
    response = client.post("/auth/register", json={
        "name": "Duplicate User 2",
        "email": "dup@test.com",
        "password": "SecurePass123!",
    })
    assert response.status_code == 409


def test_login_success(client):
    response = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]


def test_login_wrong_password(client):
    response = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "WrongPass999!"
    })
    assert response.status_code == 401


def test_get_profile_authenticated(client):
    login = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "SecurePass123!"
    })
    token = login.json()["tokens"]["access_token"]

    response = client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


def test_get_profile_unauthenticated(client):
    response = client.get("/auth/profile")
    assert response.status_code in (401, 403)


def test_admin_can_list_users(client, db):
    client.post("/auth/register", json={
        "name": "Employee One",
        "email": "employee1@test.com",
        "password": "SecurePass123!",
        "role": "employee",
    })
    admin = db.query(User).filter(User.email == "admin@test.com").first()
    admin.role = UserRole.ADMIN
    db.commit()

    login = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "SecurePass123!",
    })
    token = login.json()["tokens"]["access_token"]

    response = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(user["email"] == "admin@test.com" for user in data)
    assert any(user["email"] == "employee1@test.com" for user in data)

    admin_id = admin.id
    role_response = client.put(
        f"/auth/users/{admin_id}/role",
        json={"role": "employee"},
        headers={"Authorization": f"Bearer {token}"},
    )
    deactivate_response = client.put(
        f"/auth/users/{admin_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert role_response.status_code == 403
    assert deactivate_response.status_code == 403

    employee = db.query(User).filter(User.email == "employee1@test.com").first()
    promote_response = client.put(
        f"/auth/users/{employee.id}/role",
        json={"role": "manager"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert promote_response.status_code == 200
    assert promote_response.json()["role"] == "manager"


def test_manager_cannot_list_users(client, db):
    client.post("/auth/register", json={
        "name": "Manager Role",
        "email": "manager2@test.com",
        "password": "SecurePass123!",
        "role": "manager",
    })
    manager = db.query(User).filter(User.email == "manager2@test.com").first()
    manager.role = UserRole.MANAGER
    db.commit()

    login = client.post("/auth/login", json={
        "email": "manager2@test.com",
        "password": "SecurePass123!",
    })
    token = login.json()["tokens"]["access_token"]

    response = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
