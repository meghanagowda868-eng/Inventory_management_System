import pytest

from app.dependencies.auth import TokenData, require_role
from app.utils.exceptions import InsufficientPermissionsException


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_promotion_manager_roles_are_authorized(role):
    check = require_role("admin", "manager")
    assert check(TokenData(user_id=1, email=f"{role}@example.com", role=role)).role == role


def test_employee_cannot_manage_promotions():
    check = require_role("admin", "manager")
    with pytest.raises(InsufficientPermissionsException):
        check(TokenData(user_id=2, email="employee@example.com", role="employee"))
