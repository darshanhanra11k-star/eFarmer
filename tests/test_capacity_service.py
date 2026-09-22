from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.capacity.engine import CapacityStatus
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.models.capacity import CapacityRecord
from app.models.centre import ProcurementCentre
from app.models.crop import Crop
from app.models.user import User
from app.repositories.capacity import CapacityRepository
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.services.capacity import CapacityService


class FakeSession:
    pass


def _make_auth_user(user_id: str, role: Role) -> AuthenticatedUser:
    return AuthenticatedUser(subject=user_id, role=role)


@pytest.fixture
def service_deps() -> tuple[
    CapacityRepository,
    CentreRepository,
    CropRepository,
    FarmerRepository,
    FakeSession,
]:
    fake_session = FakeSession()
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    cap_repo = CapacityRepository(fake_session)  # type: ignore[arg-type]
    return cap_repo, c_repo, cr_repo, f_repo, fake_session


@pytest.mark.asyncio
async def test_farmer_read_active_centre_capacity_success(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        CentreRepository,
        CropRepository,
        FarmerRepository,
        FakeSession,
    ],
) -> None:
    cap_repo, c_repo, cr_repo, f_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 11, 15)

    centre = ProcurementCentre(id=centre_id, name="Centre 1", active=True)
    crop = Crop(id=crop_id, code="WHEAT", name="Wheat", active=True)
    record = CapacityRecord(
        id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000.00"),
        allocated_quantity_kg=Decimal("300.00"),
        procured_quantity_kg=Decimal("100.00"),
        active=True,
    )

    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(cap_repo, "get_capacity_record", AsyncMock(return_value=record))

    service = CapacityService(
        capacity_repo=cap_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        farmer_repo=f_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(uuid4()), Role.FARMER)
    response = await service.get_centre_capacity(
        centre_id, crop_id, target_date, auth_user
    )

    assert response.centre_id == centre_id
    assert response.crop_id == crop_id
    assert response.date == target_date
    assert response.total_capacity_kg == Decimal("1000.00")
    assert response.allocated_quantity_kg == Decimal("300.00")
    assert response.procured_quantity_kg == Decimal("100.00")
    assert response.available_capacity_kg == Decimal("700.00")
    assert response.utilisation == Decimal("0.3")
    assert response.capacity_status == CapacityStatus.PARTIAL
    assert response.active is True


@pytest.mark.asyncio
async def test_farmer_read_inactive_centre_raises_not_found(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        CentreRepository,
        CropRepository,
        FarmerRepository,
        FakeSession,
    ],
) -> None:
    cap_repo, c_repo, cr_repo, f_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 11, 15)

    centre = ProcurementCentre(id=centre_id, name="Centre Inactive", active=False)
    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))

    service = CapacityService(
        capacity_repo=cap_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        farmer_repo=f_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(uuid4()), Role.FARMER)
    with pytest.raises(NotFoundError) as exc:
        await service.get_centre_capacity(centre_id, crop_id, target_date, auth_user)
    assert "Procurement centre not found" in str(exc.value)


@pytest.mark.asyncio
async def test_officer_read_assigned_centre_success(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        CentreRepository,
        CropRepository,
        FarmerRepository,
        FakeSession,
    ],
) -> None:
    cap_repo, c_repo, cr_repo, f_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    user_id = uuid4()
    target_date = date(2026, 11, 15)

    centre = ProcurementCentre(id=centre_id, name="Centre Assigned", active=True)
    crop = Crop(id=crop_id, code="PADDY", name="Paddy", active=True)
    user = User(
        id=user_id,
        role=Role.OFFICER,
        centre_id=centre_id,
        username="officer1",
        password_hash="hash",
    )
    record = CapacityRecord(
        id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("2000.00"),
        allocated_quantity_kg=Decimal("0"),
        procured_quantity_kg=Decimal("0"),
        active=True,
    )

    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(cap_repo, "get_capacity_record", AsyncMock(return_value=record))

    service = CapacityService(
        capacity_repo=cap_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        farmer_repo=f_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.OFFICER)
    response = await service.get_centre_capacity(
        centre_id, crop_id, target_date, auth_user
    )

    assert response.capacity_status == CapacityStatus.AVAILABLE
    assert response.available_capacity_kg == Decimal("2000.00")
    assert response.utilisation == Decimal("0")


@pytest.mark.asyncio
async def test_officer_read_unassigned_centre_raises_forbidden(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        CentreRepository,
        CropRepository,
        FarmerRepository,
        FakeSession,
    ],
) -> None:
    cap_repo, c_repo, cr_repo, f_repo, fake_session = service_deps
    requested_centre_id = uuid4()
    assigned_centre_id = uuid4()
    crop_id = uuid4()
    user_id = uuid4()
    target_date = date(2026, 11, 15)

    centre = ProcurementCentre(id=requested_centre_id, name="Other Centre", active=True)
    user = User(
        id=user_id,
        role=Role.OFFICER,
        centre_id=assigned_centre_id,
        username="officer1",
        password_hash="hash",
    )

    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))

    service = CapacityService(
        capacity_repo=cap_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        farmer_repo=f_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.OFFICER)
    with pytest.raises(PermissionDeniedError) as exc:
        await service.get_centre_capacity(
            requested_centre_id, crop_id, target_date, auth_user
        )
    assert "Officers can only view capacity for their assigned centre" in str(exc.value)


@pytest.mark.asyncio
async def test_missing_capacity_record_raises_not_found(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        CentreRepository,
        CropRepository,
        FarmerRepository,
        FakeSession,
    ],
) -> None:
    cap_repo, c_repo, cr_repo, f_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 11, 15)

    centre = ProcurementCentre(id=centre_id, name="Centre 1", active=True)
    crop = Crop(id=crop_id, code="WHEAT", name="Wheat", active=True)

    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(cap_repo, "get_capacity_record", AsyncMock(return_value=None))

    service = CapacityService(
        capacity_repo=cap_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        farmer_repo=f_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(uuid4()), Role.FARMER)
    with pytest.raises(NotFoundError) as exc:
        await service.get_centre_capacity(centre_id, crop_id, target_date, auth_user)
    assert "Capacity record not found" in str(exc.value)


@pytest.mark.asyncio
async def test_configured_zero_capacity_returns_full(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        CentreRepository,
        CropRepository,
        FarmerRepository,
        FakeSession,
    ],
) -> None:
    cap_repo, c_repo, cr_repo, f_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 11, 15)

    centre = ProcurementCentre(id=centre_id, name="Centre Zero", active=True)
    crop = Crop(id=crop_id, code="WHEAT", name="Wheat", active=True)
    record = CapacityRecord(
        id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("0"),
        allocated_quantity_kg=Decimal("0"),
        procured_quantity_kg=Decimal("0"),
        active=True,
    )

    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(cap_repo, "get_capacity_record", AsyncMock(return_value=record))

    service = CapacityService(
        capacity_repo=cap_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        farmer_repo=f_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(uuid4()), Role.FARMER)
    response = await service.get_centre_capacity(
        centre_id, crop_id, target_date, auth_user
    )

    assert response.capacity_status == CapacityStatus.FULL
    assert response.total_capacity_kg == Decimal("0")
    assert response.available_capacity_kg == Decimal("0")
    assert response.utilisation == Decimal("0")
