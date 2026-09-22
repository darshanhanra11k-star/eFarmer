from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import PermissionDeniedError
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.models.capacity import CapacityRecord
from app.models.centre import ProcurementCentre
from app.models.user import User
from app.repositories.capacity import CapacityRepository
from app.repositories.centre import CentreRepository
from app.repositories.farmer import FarmerRepository
from app.schemas.priority_centre import (
    CentrePreference,
    PriorityCentreSelectionRequest,
)
from app.services.priority_centre import PriorityCentreService


@pytest.fixture
def mock_centre_repo() -> AsyncMock:
    return AsyncMock(spec=CentreRepository)


@pytest.fixture
def mock_capacity_repo() -> AsyncMock:
    return AsyncMock(spec=CapacityRepository)


@pytest.fixture
def mock_farmer_repo() -> AsyncMock:
    return AsyncMock(spec=FarmerRepository)


@pytest.fixture
def farmer_user() -> tuple[AuthenticatedUser, User]:
    user_id = uuid4()
    farmer_id = uuid4()
    auth_user = AuthenticatedUser(
        subject=str(user_id),
        role=Role.FARMER,
    )

    db_user = User(
        id=user_id,
        phone="+919876543210",
        password_hash="hashed",
        role=Role.FARMER,
        farmer_id=farmer_id,
        centre_id=None,
        active=True,
    )
    return auth_user, db_user


@pytest.mark.asyncio
async def test_priority_1_available_selected_immediately(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
    farmer_user: tuple[AuthenticatedUser, User],
) -> None:
    auth_user, db_user = farmer_user
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    c1 = uuid4()
    c2 = uuid4()
    crop_id = uuid4()
    ready_date = date(2026, 11, 15)

    centre1 = ProcurementCentre(id=c1, name="Centre 1", active=True)
    mock_centre_repo.get_by_id.side_effect = lambda cid: centre1 if cid == c1 else None

    cap_record1 = CapacityRecord(
        centre_id=c1,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("200"),
        active=True,
    )
    mock_capacity_repo.get_capacity_record.return_value = cap_record1

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    req = PriorityCentreSelectionRequest(
        crop_id=crop_id,
        ready_date=ready_date,
        requested_quantity_kg=Decimal("300"),
        preferred_centres=[
            CentrePreference(centre_id=c1, priority=1),
            CentrePreference(centre_id=c2, priority=2),
        ],
    )

    res = await service.select_priority_centre(req, auth_user)

    assert res.success is True
    assert res.selected_centre_id == c1
    assert res.selected_priority == 1
    assert res.available_capacity_kg == "800.00"
    assert len(res.evaluated_centres) == 1
    assert res.evaluated_centres[0].status == "AVAILABLE"
    # Centre 2 was never fetched or evaluated
    assert mock_centre_repo.get_by_id.call_count == 1
    assert mock_capacity_repo.get_capacity_record.call_count == 1


@pytest.mark.asyncio
async def test_priority_1_unavailable_priority_2_selected(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
    farmer_user: tuple[AuthenticatedUser, User],
) -> None:
    auth_user, db_user = farmer_user
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    c1 = uuid4()
    c2 = uuid4()
    crop_id = uuid4()
    ready_date = date(2026, 11, 15)

    centre1 = ProcurementCentre(id=c1, name="Centre 1", active=True)
    centre2 = ProcurementCentre(id=c2, name="Centre 2", active=True)

    async def get_centre(cid: object) -> ProcurementCentre | None:
        if cid == c1:
            return centre1
        if cid == c2:
            return centre2
        return None

    mock_centre_repo.get_by_id.side_effect = get_centre

    # Centre 1 has insufficient capacity (100 available < 300 requested)
    cap1 = CapacityRecord(
        centre_id=c1,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("900"),
        active=True,
    )
    # Centre 2 has sufficient capacity (500 available >= 300 requested)
    cap2 = CapacityRecord(
        centre_id=c2,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("500"),
        active=True,
    )

    async def get_cap(
        centre_id: object, crop_id: object, target_date: object, for_update: bool
    ) -> CapacityRecord | None:
        if centre_id == c1:
            return cap1
        if centre_id == c2:
            return cap2
        return None

    mock_capacity_repo.get_capacity_record.side_effect = get_cap

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    req = PriorityCentreSelectionRequest(
        crop_id=crop_id,
        ready_date=ready_date,
        requested_quantity_kg=Decimal("300"),
        preferred_centres=[
            CentrePreference(centre_id=c1, priority=1),
            CentrePreference(centre_id=c2, priority=2),
        ],
    )

    res = await service.select_priority_centre(req, auth_user)

    assert res.success is True
    assert res.selected_centre_id == c2
    assert res.selected_priority == 2
    assert len(res.evaluated_centres) == 2
    assert res.evaluated_centres[0].centre_id == c1
    assert res.evaluated_centres[0].status == "UNAVAILABLE"
    assert "insufficient capacity" in res.evaluated_centres[0].reason.lower()
    assert res.evaluated_centres[1].centre_id == c2
    assert res.evaluated_centres[1].status == "AVAILABLE"


@pytest.mark.asyncio
async def test_first_two_unavailable_third_selected(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
    farmer_user: tuple[AuthenticatedUser, User],
) -> None:
    auth_user, db_user = farmer_user
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    c1 = uuid4()
    c2 = uuid4()
    c3 = uuid4()
    c4 = uuid4()
    crop_id = uuid4()
    ready_date = date(2026, 11, 15)

    # c1 is inactive
    centre1 = ProcurementCentre(id=c1, name="Centre 1", active=False)
    # c2 has missing capacity record
    centre2 = ProcurementCentre(id=c2, name="Centre 2", active=True)
    # c3 is active with capacity
    centre3 = ProcurementCentre(id=c3, name="Centre 3", active=True)
    # c4 should never be visited
    centre4 = ProcurementCentre(id=c4, name="Centre 4", active=True)

    centres_map = {c1: centre1, c2: centre2, c3: centre3, c4: centre4}
    mock_centre_repo.get_by_id.side_effect = lambda cid: centres_map.get(cid)

    cap3 = CapacityRecord(
        centre_id=c3,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("0"),
        active=True,
    )

    async def get_cap(
        centre_id: object, crop_id: object, target_date: object, for_update: bool
    ) -> CapacityRecord | None:
        if centre_id == c3:
            return cap3
        return None

    mock_capacity_repo.get_capacity_record.side_effect = get_cap

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    req = PriorityCentreSelectionRequest(
        crop_id=crop_id,
        ready_date=ready_date,
        requested_quantity_kg=Decimal("200"),
        preferred_centres=[
            CentrePreference(centre_id=c1, priority=1),
            CentrePreference(centre_id=c2, priority=2),
            CentrePreference(centre_id=c3, priority=3),
            CentrePreference(centre_id=c4, priority=4),
        ],
    )

    res = await service.select_priority_centre(req, auth_user)

    assert res.success is True
    assert res.selected_centre_id == c3
    assert res.selected_priority == 3
    assert len(res.evaluated_centres) == 3
    assert res.evaluated_centres[0].reason == "Procurement centre is inactive."
    assert "No capacity record" in res.evaluated_centres[1].reason
    assert res.evaluated_centres[2].status == "AVAILABLE"
    # c4 was never queried
    assert mock_centre_repo.get_by_id.call_count == 3


@pytest.mark.asyncio
async def test_all_preferred_centres_unavailable_returns_domain_failure(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
    farmer_user: tuple[AuthenticatedUser, User],
) -> None:
    auth_user, db_user = farmer_user
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    c1 = uuid4()
    c2 = uuid4()
    crop_id = uuid4()
    ready_date = date(2026, 11, 15)

    centre1 = ProcurementCentre(id=c1, name="Centre 1", active=True)
    centre2 = ProcurementCentre(id=c2, name="Centre 2", active=True)
    mock_centre_repo.get_by_id.side_effect = lambda cid: (
        centre1 if cid == c1 else centre2
    )

    # c1 has inactive capacity
    cap1 = CapacityRecord(
        centre_id=c1,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("0"),
        active=False,
    )
    # c2 has 100 available < 500 requested
    cap2 = CapacityRecord(
        centre_id=c2,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("900"),
        active=True,
    )

    async def get_cap(
        centre_id: object, crop_id: object, target_date: object, for_update: bool
    ) -> CapacityRecord | None:
        return cap1 if centre_id == c1 else cap2

    mock_capacity_repo.get_capacity_record.side_effect = get_cap

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    req = PriorityCentreSelectionRequest(
        crop_id=crop_id,
        ready_date=ready_date,
        requested_quantity_kg=Decimal("500"),
        preferred_centres=[
            CentrePreference(centre_id=c1, priority=1),
            CentrePreference(centre_id=c2, priority=2),
        ],
    )

    res = await service.select_priority_centre(req, auth_user)

    assert res.success is False
    assert res.selected_centre_id is None
    assert res.selected_priority is None
    assert res.available_capacity_kg is None
    assert len(res.evaluated_centres) == 2
    assert "inactive" in res.evaluated_centres[0].reason.lower()
    assert "insufficient capacity" in res.evaluated_centres[1].reason.lower()
    assert "no preferred centre available" in res.message.lower()


@pytest.mark.asyncio
async def test_priority_order_respected_regardless_of_payload_list_order(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
    farmer_user: tuple[AuthenticatedUser, User],
) -> None:
    auth_user, db_user = farmer_user
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    c1 = uuid4()
    c2 = uuid4()
    crop_id = uuid4()
    ready_date = date(2026, 11, 15)

    centre1 = ProcurementCentre(id=c1, name="Centre 1", active=True)
    centre2 = ProcurementCentre(id=c2, name="Centre 2", active=True)
    mock_centre_repo.get_by_id.side_effect = lambda cid: (
        centre1 if cid == c1 else centre2
    )

    cap = CapacityRecord(
        centre_id=c1,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("0"),
        active=True,
    )
    mock_capacity_repo.get_capacity_record.return_value = cap

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    # Note: list passes priority 2 first, then priority 1
    req = PriorityCentreSelectionRequest(
        crop_id=crop_id,
        ready_date=ready_date,
        requested_quantity_kg=Decimal("100"),
        preferred_centres=[
            CentrePreference(centre_id=c2, priority=2),
            CentrePreference(centre_id=c1, priority=1),
        ],
    )

    res = await service.select_priority_centre(req, auth_user)

    # Must select c1 because priority 1 comes first
    assert res.selected_centre_id == c1
    assert res.selected_priority == 1
    assert len(res.evaluated_centres) == 1


@pytest.mark.asyncio
async def test_exact_capacity_boundary_selected(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
    farmer_user: tuple[AuthenticatedUser, User],
) -> None:
    auth_user, db_user = farmer_user
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    c1 = uuid4()
    crop_id = uuid4()
    ready_date = date(2026, 11, 15)

    centre1 = ProcurementCentre(id=c1, name="Centre 1", active=True)
    mock_centre_repo.get_by_id.return_value = centre1

    # Exactly 250 available (1000 - 750)
    cap1 = CapacityRecord(
        centre_id=c1,
        crop_id=crop_id,
        date=ready_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("750"),
        active=True,
    )
    mock_capacity_repo.get_capacity_record.return_value = cap1

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    # Requesting exactly 250
    req = PriorityCentreSelectionRequest(
        crop_id=crop_id,
        ready_date=ready_date,
        requested_quantity_kg=Decimal("250"),
        preferred_centres=[CentrePreference(centre_id=c1, priority=1)],
    )

    res = await service.select_priority_centre(req, auth_user)

    assert res.success is True
    assert res.selected_centre_id == c1
    assert res.available_capacity_kg == "250.00"


@pytest.mark.asyncio
async def test_farmer_without_farmer_id_raises_permission_denied(
    mock_centre_repo: AsyncMock,
    mock_capacity_repo: AsyncMock,
    mock_farmer_repo: AsyncMock,
) -> None:
    auth_user = AuthenticatedUser(
        subject=str(uuid4()),
        role=Role.FARMER,
    )

    db_user = User(
        id=uuid4(),
        phone="+919876543210",
        password_hash="hashed",
        role=Role.FARMER,
        farmer_id=None,  # No linked farmer record
        centre_id=None,
        active=True,
    )
    mock_farmer_repo.get_user_by_subject.return_value = db_user

    service = PriorityCentreService(
        centre_repo=mock_centre_repo,
        capacity_repo=mock_capacity_repo,
        farmer_repo=mock_farmer_repo,
    )

    req = PriorityCentreSelectionRequest(
        crop_id=uuid4(),
        ready_date=date(2026, 11, 15),
        requested_quantity_kg=Decimal("100"),
        preferred_centres=[CentrePreference(centre_id=uuid4(), priority=1)],
    )

    with pytest.raises(PermissionDeniedError, match="associated farmer profile"):
        await service.select_priority_centre(req, auth_user)
