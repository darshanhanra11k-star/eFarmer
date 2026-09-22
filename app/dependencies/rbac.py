from collections.abc import Callable

from app.core.exceptions import PermissionDeniedError
from app.core.rbac import Permission, Role, get_role_permissions
from app.dependencies.auth import AuthenticatedUser, CurrentUserDep


def require_role(
    *allowed_roles: Role,
) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    if not allowed_roles:
        raise ValueError("At least one role must be specified")

    allowed_set = frozenset(allowed_roles)

    def dependency(user: CurrentUserDep) -> AuthenticatedUser:
        if user.role is None or user.role not in allowed_set:
            raise PermissionDeniedError()
        return user

    return dependency


def require_roles(
    *allowed_roles: Role,
) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    return require_role(*allowed_roles)


def require_permission(
    *required_permissions: Permission,
) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    if not required_permissions:
        raise ValueError("At least one permission must be specified")

    needed = frozenset(required_permissions)

    def dependency(user: CurrentUserDep) -> AuthenticatedUser:
        if user.role is None:
            raise PermissionDeniedError()

        user_permissions = get_role_permissions(user.role)
        if not needed.issubset(user_permissions):
            raise PermissionDeniedError()

        return user

    return dependency


def require_permissions(
    *required_permissions: Permission,
) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    return require_permission(*required_permissions)
