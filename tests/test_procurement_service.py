from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.models.centre import ProcurementCentre
from app.models.crop import Crop
from app.models.farmer import Farmer
from app.models.land_holding import FarmerLandHolding
from app.models.procurement import (
    IntentStatus,
    ProcurementIntent,
    ProcurementStatusHistory,
)
from app.models.user import User
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.procurement import ProcurementRepository
from app.schemas.procurement import ProcurementIntentCreate
from app.services.procurement import ProcurementService


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.is_committed = False
        self.is_flushed = False

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    async def flush(self) -> None:
        self.is_flushed = True

    async def commit(self) -> None:
        self.is_committed = True

    async def refresh(self, instance: object) -> None:
        pass

    async def rollback(self) -> None:
        pass


@pytest.fixture
def fake_session() -> FakeAsyncSession:
    return FakeAsyncSession()


def _make_auth_user(user_id: str, role: Role) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=user_id,
        role=role,
    )


@pytest.mark.asyncio
async def test_farmer_creates_procurement_intent_own_profile_success(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    holding_id = uuid4()
    user_id = uuid4()

    farmer = Farmer(
        id=farmer_id,
        farmer_id="F-1",
        name="Farmer 1",
        phone="1234567890",
        active=True,
    )
    centre = ProcurementCentre(
        id=centre_id, name="Centre 1", district="District 1", active=True
    )
    crop = Crop(id=crop_id, code="C-1", name="Crop 1", unit="KG", active=True)
    holding = FarmerLandHolding(
        id=holding_id,
        farmer_id=farmer_id,
        survey_number="S-1",
        area_acres=Decimal("2.0"),
        active=True,
    )
    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=farmer_id,
        username="farmer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(f_repo, "get_by_id", AsyncMock(return_value=farmer))
    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(
        f_repo, "get_land_holdings_by_farmer_id", AsyncMock(return_value=[holding])
    )
    monkeypatch.setattr(
        p_repo, "get_active_intents_for_farmer", AsyncMock(return_value=[])
    )

    async def _mock_create_intent(intent: ProcurementIntent) -> ProcurementIntent:
        intent.id = uuid4()
        return intent

    monkeypatch.setattr(p_repo, "create_intent", _mock_create_intent)

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    # Farmer does not need to provide farmer_id in payload; uses authenticated user
    payload = ProcurementIntentCreate(
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("1000.00"),
        ready_date=date(2026, 11, 1),
    )

    result = await service.create_procurement_intent(payload, auth_user)
    assert result is not None
    assert result.status == IntentStatus.PENDING
    assert result.farmer_id == farmer_id
    assert result.created_by == user_id
    assert result.expected_quantity_kg == Decimal("1000.00")
    assert fake_session.is_committed is True
    # Schema integrity: Do NOT create status history row for initial creation
    assert not any(isinstance(x, ProcurementStatusHistory) for x in fake_session.added)


@pytest.mark.asyncio
async def test_farmer_cannot_create_intent_for_another_farmer(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    farmer_id = uuid4()
    other_farmer_id = uuid4()
    user_id = uuid4()

    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=farmer_id,
        username="farmer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    payload = ProcurementIntentCreate(
        farmer_id=other_farmer_id,
        centre_id=uuid4(),
        crop_id=uuid4(),
        land_holding_id=uuid4(),
        expected_quantity_kg=Decimal("500"),
        ready_date=date(2026, 11, 1),
    )

    with pytest.raises(PermissionDeniedError) as exc:
        await service.create_procurement_intent(payload, auth_user)
    assert "for another farmer" in str(exc.value)


@pytest.mark.asyncio
async def test_officer_creates_procurement_intent_success(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    holding_id = uuid4()
    officer_user_id = uuid4()

    farmer = Farmer(
        id=farmer_id,
        farmer_id="F-1",
        name="Farmer 1",
        phone="1234567890",
        active=True,
    )
    centre = ProcurementCentre(
        id=centre_id, name="Centre 1", district="District 1", active=True
    )
    crop = Crop(id=crop_id, code="C-1", name="Crop 1", unit="KG", active=True)
    holding = FarmerLandHolding(
        id=holding_id,
        farmer_id=farmer_id,
        survey_number="S-1",
        area_acres=Decimal("2.0"),
        active=True,
    )
    user = User(
        id=officer_user_id,
        role=Role.OFFICER,
        centre_id=centre_id,
        username="officer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(f_repo, "get_by_id", AsyncMock(return_value=farmer))
    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(
        f_repo, "get_land_holdings_by_farmer_id", AsyncMock(return_value=[holding])
    )
    monkeypatch.setattr(
        p_repo, "get_active_intents_for_farmer", AsyncMock(return_value=[])
    )

    async def _mock_create_intent(intent: ProcurementIntent) -> ProcurementIntent:
        intent.id = uuid4()
        return intent

    monkeypatch.setattr(p_repo, "create_intent", _mock_create_intent)

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(officer_user_id), Role.OFFICER)
    payload = ProcurementIntentCreate(
        farmer_id=farmer_id,
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("1200.00"),
        ready_date=date(2026, 11, 1),
    )

    result = await service.create_procurement_intent(payload, auth_user)
    assert result is not None
    assert result.status == IntentStatus.PENDING
    assert result.farmer_id == farmer_id
    assert result.created_by == officer_user_id
    assert fake_session.is_committed is True


@pytest.mark.asyncio
async def test_officer_cross_centre_forbidden(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    officer_centre_id = uuid4()
    other_centre_id = uuid4()
    officer_user_id = uuid4()

    user = User(
        id=officer_user_id,
        role=Role.OFFICER,
        centre_id=officer_centre_id,
        username="officer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(officer_user_id), Role.OFFICER)
    payload = ProcurementIntentCreate(
        farmer_id=uuid4(),
        centre_id=other_centre_id,
        crop_id=uuid4(),
        land_holding_id=uuid4(),
        expected_quantity_kg=Decimal("500"),
        ready_date=date(2026, 11, 1),
    )

    with pytest.raises(PermissionDeniedError) as exc:
        await service.create_procurement_intent(payload, auth_user)
    assert "Officers cannot create procurement intents for centres" in str(exc.value)


@pytest.mark.asyncio
async def test_create_procurement_intent_invalid_land_holding(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    user_id = uuid4()

    farmer = Farmer(
        id=farmer_id,
        farmer_id="F-1",
        name="Farmer 1",
        phone="1234567890",
        active=True,
    )
    centre = ProcurementCentre(
        id=centre_id, name="Centre 1", district="District 1", active=True
    )
    crop = Crop(id=crop_id, code="C-1", name="Crop 1", unit="KG", active=True)
    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=farmer_id,
        username="farmer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(f_repo, "get_by_id", AsyncMock(return_value=farmer))
    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(
        f_repo, "get_land_holdings_by_farmer_id", AsyncMock(return_value=[])
    )

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    payload = ProcurementIntentCreate(
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=uuid4(),
        expected_quantity_kg=Decimal("500"),
        ready_date=date(2026, 11, 1),
    )

    with pytest.raises(ValidationError) as exc:
        await service.create_procurement_intent(payload, auth_user)
    assert "land holding does not belong to the farmer" in str(exc.value)


@pytest.mark.asyncio
async def test_create_procurement_intent_duplicate_active_conflict(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    farmer_id = uuid4()
    centre_id = uuid4()
    crop_id = uuid4()
    holding_id = uuid4()
    user_id = uuid4()

    farmer = Farmer(
        id=farmer_id,
        farmer_id="F-1",
        name="Farmer 1",
        phone="1234567890",
        active=True,
    )
    centre = ProcurementCentre(
        id=centre_id, name="Centre 1", district="District 1", active=True
    )
    crop = Crop(id=crop_id, code="C-1", name="Crop 1", unit="KG", active=True)
    holding = FarmerLandHolding(
        id=holding_id,
        farmer_id=farmer_id,
        survey_number="S-1",
        area_acres=Decimal("2.0"),
        active=True,
    )
    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=farmer_id,
        username="farmer1",
        password_hash="hash",
    )

    existing_active_intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer_id,
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 11, 1),
        status=IntentStatus.PENDING,
        created_by=user_id,
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(f_repo, "get_by_id", AsyncMock(return_value=farmer))
    monkeypatch.setattr(c_repo, "get_by_id", AsyncMock(return_value=centre))
    monkeypatch.setattr(cr_repo, "get_by_id", AsyncMock(return_value=crop))
    monkeypatch.setattr(
        f_repo, "get_land_holdings_by_farmer_id", AsyncMock(return_value=[holding])
    )
    monkeypatch.setattr(
        p_repo,
        "get_active_intents_for_farmer",
        AsyncMock(return_value=[existing_active_intent]),
    )

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    payload = ProcurementIntentCreate(
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("1000.00"),
        ready_date=date(2026, 11, 1),
    )

    with pytest.raises(ConflictError) as exc:
        await service.create_procurement_intent(payload, auth_user)
    assert "Farmer already has an active request" in str(exc.value)


@pytest.mark.asyncio
async def test_get_procurement_by_id_farmer_own_success(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    farmer_id = uuid4()
    intent_id = uuid4()
    user_id = uuid4()

    intent = ProcurementIntent(
        id=intent_id,
        farmer_id=farmer_id,
        centre_id=uuid4(),
        crop_id=uuid4(),
        land_holding_id=uuid4(),
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 11, 1),
        status=IntentStatus.PENDING,
        created_by=user_id,
    )
    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=farmer_id,
        username="farmer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(p_repo, "get_intent_by_id", AsyncMock(return_value=intent))

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    res = await service.get_procurement_by_id(intent_id, auth_user)
    assert res.id == intent_id
    assert res.farmer_id == farmer_id


@pytest.mark.asyncio
async def test_get_procurement_by_id_farmer_cross_farmer_forbidden(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    intent_id = uuid4()
    intent_farmer_id = uuid4()
    my_farmer_id = uuid4()
    user_id = uuid4()

    intent = ProcurementIntent(
        id=intent_id,
        farmer_id=intent_farmer_id,
        centre_id=uuid4(),
        crop_id=uuid4(),
        land_holding_id=uuid4(),
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 11, 1),
        status=IntentStatus.PENDING,
        created_by=uuid4(),
    )
    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=my_farmer_id,
        username="farmer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(p_repo, "get_intent_by_id", AsyncMock(return_value=intent))

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    with pytest.raises(PermissionDeniedError) as exc:
        await service.get_procurement_by_id(intent_id, auth_user)
    assert "access another farmer's procurement record" in str(exc.value)


@pytest.mark.asyncio
async def test_get_procurement_by_id_not_found(
    monkeypatch: pytest.MonkeyPatch, fake_session: FakeAsyncSession
) -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        role=Role.FARMER,
        farmer_id=uuid4(),
        username="farmer1",
        password_hash="hash",
    )

    p_repo = ProcurementRepository(fake_session)  # type: ignore[arg-type]
    f_repo = FarmerRepository(fake_session)  # type: ignore[arg-type]
    c_repo = CentreRepository(fake_session)  # type: ignore[arg-type]
    cr_repo = CropRepository(fake_session)  # type: ignore[arg-type]

    monkeypatch.setattr(f_repo, "get_user_by_subject", AsyncMock(return_value=user))
    monkeypatch.setattr(p_repo, "get_intent_by_id", AsyncMock(return_value=None))

    service = ProcurementService(
        procurement_repo=p_repo,
        farmer_repo=f_repo,
        centre_repo=c_repo,
        crop_repo=cr_repo,
        session=fake_session,  # type: ignore[arg-type]
    )

    auth_user = _make_auth_user(str(user_id), Role.FARMER)
    with pytest.raises(NotFoundError):
        await service.get_procurement_by_id(uuid4(), auth_user)
