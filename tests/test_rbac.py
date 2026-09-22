from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.exceptions import PermissionDeniedError
from app.core.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
    get_role_permissions,
    has_permission,
)
from app.core.security import create_access_token
from app.dependencies.auth import AuthenticatedUser
from app.dependencies.rbac import (
    require_permission,
    require_permissions,
    require_role,
    require_roles,
)
from app.main import app

TEST_JWT_SECRET = "super_secret_test_key_that_is_at_least_32_characters_long"


@pytest.fixture(autouse=True)
def _configure_test_jwt(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_defined_roles_exist() -> None:
    assert Role.FARMER.value == "FARMER"
    assert Role.OFFICER.value == "OFFICER"
    assert set(Role) == {Role.FARMER, Role.OFFICER}


def test_removed_roles_do_not_exist() -> None:
    assert not hasattr(Role, "SAHAYAK")
    assert not hasattr(Role, "ARHTIYA")
    assert not hasattr(Role, "OPERATOR")
    assert not hasattr(Role, "ADMIN")

    with pytest.raises(ValueError):
        Role("SAHAYAK")

    with pytest.raises(ValueError):
        Role("ARHTIYA")

    with pytest.raises(ValueError):
        Role("OPERATOR")

    with pytest.raises(ValueError):
        Role("ADMIN")

    with pytest.raises(ValueError):
        Role("farmer")

    with pytest.raises(ValueError):
        Role("officer")


def test_every_role_has_deterministic_policy() -> None:
    for role in Role:
        perms = get_role_permissions(role)
        assert isinstance(perms, frozenset)
        assert len(perms) > 0
        assert perms == ROLE_PERMISSIONS[role]


def test_role_permissions_exact_mappings() -> None:
    assert ROLE_PERMISSIONS[Role.FARMER] == frozenset(
        {
            Permission.FARMER_READ,
            Permission.FARMER_WRITE,
            Permission.QUEUE_READ,
            Permission.QUEUE_JOIN,
            Permission.PROCUREMENT_READ,
        }
    )
    assert len(ROLE_PERMISSIONS[Role.FARMER]) == 5

    assert ROLE_PERMISSIONS[Role.OFFICER] == frozenset(
        {
            Permission.FARMER_READ,
            Permission.FARMER_WRITE,
            Permission.QUEUE_READ,
            Permission.QUEUE_MANAGE,
            Permission.PROCUREMENT_READ,
            Permission.PROCUREMENT_CREATE,
        }
    )
    assert len(ROLE_PERMISSIONS[Role.OFFICER]) == 6


def test_unknown_role_policy_behavior() -> None:
    assert get_role_permissions(None) == frozenset()
    assert has_permission(None, Permission.FARMER_READ) is False


def test_role_has_permission_checks() -> None:
    assert has_permission(Role.FARMER, Permission.FARMER_READ) is True
    assert has_permission(Role.FARMER, Permission.FARMER_WRITE) is True
    assert has_permission(Role.FARMER, Permission.QUEUE_READ) is True
    assert has_permission(Role.FARMER, Permission.QUEUE_JOIN) is True
    assert has_permission(Role.FARMER, Permission.PROCUREMENT_READ) is True
    assert has_permission(Role.FARMER, Permission.QUEUE_MANAGE) is False
    assert has_permission(Role.FARMER, Permission.PROCUREMENT_CREATE) is False

    assert has_permission(Role.OFFICER, Permission.FARMER_READ) is True
    assert has_permission(Role.OFFICER, Permission.FARMER_WRITE) is True
    assert has_permission(Role.OFFICER, Permission.QUEUE_READ) is True
    assert has_permission(Role.OFFICER, Permission.QUEUE_MANAGE) is True
    assert has_permission(Role.OFFICER, Permission.PROCUREMENT_READ) is True
    assert has_permission(Role.OFFICER, Permission.PROCUREMENT_CREATE) is True
    assert has_permission(Role.OFFICER, Permission.QUEUE_JOIN) is False


def test_require_role_allowed_succeeds() -> None:
    user = AuthenticatedUser(subject="officer_1", role=Role.OFFICER)
    dep = require_role(Role.OFFICER)
    assert dep(user) is user


def test_require_role_disallowed_raises_permission_denied() -> None:
    user = AuthenticatedUser(subject="farmer_1", role=Role.FARMER)
    dep = require_role(Role.OFFICER)
    with pytest.raises(PermissionDeniedError):
        dep(user)


def test_require_role_multiple_roles_allowed() -> None:
    user_officer = AuthenticatedUser(subject="u1", role=Role.OFFICER)
    user_farmer = AuthenticatedUser(subject="u2", role=Role.FARMER)

    dep = require_role(Role.OFFICER, Role.FARMER)
    assert dep(user_officer) is user_officer
    assert dep(user_farmer) is user_farmer


def test_require_roles_alias() -> None:
    user = AuthenticatedUser(subject="u1", role=Role.OFFICER)
    dep = require_roles(Role.OFFICER)
    assert dep(user) is user


def test_require_role_no_role_on_user_raises_permission_denied() -> None:
    user = AuthenticatedUser(subject="user_1", role=None)
    dep = require_role(Role.FARMER)
    with pytest.raises(PermissionDeniedError):
        dep(user)


def test_require_role_empty_allowed_roles_raises_value_error() -> None:
    with pytest.raises(ValueError):
        require_role()


def test_require_permission_allowed_succeeds() -> None:
    user = AuthenticatedUser(subject="user_1", role=Role.FARMER)
    dep = require_permission(Permission.FARMER_READ)
    assert dep(user) is user


def test_require_permission_disallowed_raises_permission_denied() -> None:
    user = AuthenticatedUser(subject="user_1", role=Role.FARMER)
    dep = require_permission(Permission.QUEUE_MANAGE)
    with pytest.raises(PermissionDeniedError):
        dep(user)


def test_require_permissions_alias() -> None:
    user = AuthenticatedUser(subject="u1", role=Role.FARMER)
    dep = require_permissions(Permission.FARMER_READ)
    assert dep(user) is user


def test_require_permission_empty_permissions_raises_value_error() -> None:
    with pytest.raises(ValueError):
        require_permission()


def test_http_rbac_flow() -> None:
    test_router = APIRouter(prefix="/test-rbac")

    @test_router.get(
        "/farmer-only",
        dependencies=[Depends(require_role(Role.FARMER))],
    )
    def farmer_only() -> dict[str, str]:
        return {"status": "farmer_ok"}

    @test_router.get(
        "/officer-only",
        dependencies=[Depends(require_role(Role.OFFICER))],
    )
    def officer_only() -> dict[str, str]:
        return {"status": "officer_ok"}

    @test_router.get(
        "/queue-manage",
        dependencies=[Depends(require_permission(Permission.QUEUE_MANAGE))],
    )
    def queue_manage() -> dict[str, str]:
        return {"status": "queue_manage_ok"}

    @test_router.get(
        "/queue-join",
        dependencies=[Depends(require_permission(Permission.QUEUE_JOIN))],
    )
    def queue_join() -> dict[str, str]:
        return {"status": "queue_join_ok"}

    @test_router.get(
        "/procurement-create",
        dependencies=[Depends(require_permission(Permission.PROCUREMENT_CREATE))],
    )
    def procurement_create() -> dict[str, str]:
        return {"status": "procurement_create_ok"}

    @test_router.get(
        "/farmer-read",
        dependencies=[Depends(require_permission(Permission.FARMER_READ))],
    )
    def farmer_read() -> dict[str, str]:
        return {"status": "farmer_read_ok"}

    app.include_router(test_router)

    try:
        client = TestClient(app, raise_server_exceptions=False)

        farmer_token = create_access_token(subject="farmer_1", role=Role.FARMER)
        officer_token = create_access_token(
            subject="officer_1",
            role=Role.OFFICER,
        )
        no_role_token = create_access_token(subject="norole_1")

        res_no_auth = client.get("/test-rbac/farmer-only")
        assert res_no_auth.status_code == 401
        body_401 = res_no_auth.json()
        assert body_401["code"] == "unauthenticated"
        assert body_401["status_code"] == 401
        assert body_401["message"] == "Please sign in again."
        assert body_401["details"] == {}

        res_bad_auth = client.get(
            "/test-rbac/farmer-only",
            headers={"Authorization": "Bearer bad.token.here"},
        )
        assert res_bad_auth.status_code == 401
        assert res_bad_auth.json()["code"] == "unauthenticated"

        now = datetime.now(UTC)
        expired_payload = {
            "sub": "user_exp",
            "role": "FARMER",
            "iat": now - timedelta(minutes=60),
            "exp": now - timedelta(minutes=10),
        }
        expired_token = jwt.encode(
            expired_payload,
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        res_expired = client.get(
            "/test-rbac/farmer-only",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res_expired.status_code == 401
        assert res_expired.json()["code"] == "unauthenticated"

        res_farmer_on_farmer = client.get(
            "/test-rbac/farmer-only",
            headers={"Authorization": f"Bearer {farmer_token}"},
        )
        assert res_farmer_on_farmer.status_code == 200
        assert res_farmer_on_farmer.json() == {"status": "farmer_ok"}

        res_farmer_on_officer = client.get(
            "/test-rbac/officer-only",
            headers={"Authorization": f"Bearer {farmer_token}"},
        )
        assert res_farmer_on_officer.status_code == 403
        body_403 = res_farmer_on_officer.json()
        assert body_403["code"] == "permission_denied"
        assert body_403["status_code"] == 403
        assert body_403["message"] == "You do not have permission to do this."
        assert body_403["details"] == {}

        res_officer_on_officer = client.get(
            "/test-rbac/officer-only",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res_officer_on_officer.status_code == 200
        assert res_officer_on_officer.json() == {"status": "officer_ok"}

        res_officer_on_farmer = client.get(
            "/test-rbac/farmer-only",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res_officer_on_farmer.status_code == 403
        assert res_officer_on_farmer.json()["code"] == "permission_denied"

        res_farmer_on_queue_join = client.get(
            "/test-rbac/queue-join",
            headers={"Authorization": f"Bearer {farmer_token}"},
        )
        assert res_farmer_on_queue_join.status_code == 200

        res_officer_on_queue_join = client.get(
            "/test-rbac/queue-join",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res_officer_on_queue_join.status_code == 403
        assert res_officer_on_queue_join.json()["code"] == "permission_denied"

        res_officer_on_queue_manage = client.get(
            "/test-rbac/queue-manage",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res_officer_on_queue_manage.status_code == 200

        res_farmer_on_queue_manage = client.get(
            "/test-rbac/queue-manage",
            headers={"Authorization": f"Bearer {farmer_token}"},
        )
        assert res_farmer_on_queue_manage.status_code == 403
        assert res_farmer_on_queue_manage.json()["code"] == "permission_denied"

        res_officer_on_procurement_create = client.get(
            "/test-rbac/procurement-create",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res_officer_on_procurement_create.status_code == 200

        res_farmer_on_procurement_create = client.get(
            "/test-rbac/procurement-create",
            headers={"Authorization": f"Bearer {farmer_token}"},
        )
        assert res_farmer_on_procurement_create.status_code == 403
        assert res_farmer_on_procurement_create.json()["code"] == "permission_denied"

        for token in (farmer_token, officer_token):
            res_fr = client.get(
                "/test-rbac/farmer-read",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_fr.status_code == 200

        res_no_role = client.get(
            "/test-rbac/farmer-read",
            headers={"Authorization": f"Bearer {no_role_token}"},
        )
        assert res_no_role.status_code == 403
        assert res_no_role.json()["code"] == "permission_denied"

        for invalid_role_str in (
            "SAHAYAK",
            "ARHTIYA",
            "OPERATOR",
            "ADMIN",
            "SUPERADMIN",
        ):
            invalid_role_payload = {
                "sub": "invalid_role_user",
                "role": invalid_role_str,
                "iat": now,
                "exp": now + timedelta(minutes=30),
            }
            invalid_token = jwt.encode(
                invalid_role_payload,
                TEST_JWT_SECRET,
                algorithm="HS256",
            )
            res_invalid_role = client.get(
                "/test-rbac/farmer-only",
                headers={"Authorization": f"Bearer {invalid_token}"},
            )
            assert res_invalid_role.status_code == 403
            assert res_invalid_role.json()["code"] == "permission_denied"

        res_spoof = client.get(
            "/test-rbac/queue-manage?role=OFFICER",
            headers={
                "Authorization": f"Bearer {farmer_token}",
                "X-Role": "OFFICER",
            },
        )
        assert res_spoof.status_code == 403
        assert res_spoof.json()["code"] == "permission_denied"

    finally:
        app.routes[:] = [
            r
            for r in app.routes
            if not str(getattr(r, "path", "")).startswith("/test-rbac")
        ]
