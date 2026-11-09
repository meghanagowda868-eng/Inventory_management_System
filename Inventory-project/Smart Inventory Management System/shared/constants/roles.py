from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


# Role hierarchy — higher index = more permissions
ROLE_HIERARCHY = [UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN]


def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """Check if user_role meets or exceeds required_role."""
    return ROLE_HIERARCHY.index(user_role) >= ROLE_HIERARCHY.index(required_role)
