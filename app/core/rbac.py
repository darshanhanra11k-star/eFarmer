from enum import StrEnum


class Role(StrEnum):
    FARMER = "FARMER"
    OFFICER = "OFFICER"


class Permission(StrEnum):
    FARMER_READ = "farmer:read"
    FARMER_WRITE = "farmer:write"
    QUEUE_READ = "queue:read"
    QUEUE_JOIN = "queue:join"
    QUEUE_MANAGE = "queue:manage"
    PROCUREMENT_READ = "procurement:read"
    PROCUREMENT_CREATE = "procurement:create"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.FARMER: frozenset(
        {
            Permission.FARMER_READ,
            Permission.FARMER_WRITE,
            Permission.QUEUE_READ,
            Permission.QUEUE_JOIN,
            Permission.PROCUREMENT_READ,
        }
    ),
    Role.OFFICER: frozenset(
        {
            Permission.FARMER_READ,
            Permission.FARMER_WRITE,
            Permission.QUEUE_READ,
            Permission.QUEUE_MANAGE,
            Permission.PROCUREMENT_READ,
            Permission.PROCUREMENT_CREATE,
        }
    ),
}


def get_role_permissions(role: Role | None) -> frozenset[Permission]:
    if role is None:
        return frozenset()
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: Role | None, permission: Permission) -> bool:
    if role is None:
        return False
    return permission in get_role_permissions(role)
