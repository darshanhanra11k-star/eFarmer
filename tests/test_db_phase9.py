from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import (
    Numeric,
    create_engine,
    event,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import Role
from app.db.base import (
    Base,
    Counter,
    Crop,
    Farmer,
    FarmerLandHolding,
    ProcurementCentre,
    User,
)

TEST_JWT_SECRET = "super_secret_test_key_that_is_at_least_32_characters_long"


@pytest.fixture
def sync_db() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_con: object, _connection_record: object) -> None:
        cursor = getattr(dbapi_con, "cursor", None)
        if callable(cursor):
            cur = cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_all_six_tables_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users",
        "farmers",
        "crops",
        "farmer_land_holdings",
        "procurement_centres",
        "counters",
    }
    assert expected.issubset(table_names)


def test_alembic_upgrade_downgrade_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head", sql=True)
    command.downgrade(cfg, "0001:base", sql=True)
    command.upgrade(cfg, "head", sql=True)


def test_user_role_enum_values() -> None:
    assert Role.FARMER.value == "FARMER"
    assert Role.OFFICER.value == "OFFICER"
    assert set(Role) == {Role.FARMER, Role.OFFICER}


def test_user_check_constraint_farmer_valid(sync_db: Session) -> None:
    farmer = Farmer(
        farmer_id="FARMER-1",
        name="Ramesh",
        phone="9876543210",
    )
    sync_db.add(farmer)
    sync_db.commit()

    user = User(
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=farmer.id,
        centre_id=None,
        username=None,
    )
    sync_db.add(user)
    sync_db.commit()
    assert user.id is not None
    assert user.role == Role.FARMER


def test_user_check_constraint_farmer_requires_farmer_id(sync_db: Session) -> None:
    user = User(
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=None,
        centre_id=None,
        username=None,
    )
    sync_db.add(user)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_user_check_constraint_farmer_cannot_have_centre_id(
    sync_db: Session,
) -> None:
    farmer = Farmer(farmer_id="F-1", name="Ramesh")
    centre = ProcurementCentre(name="Centre 1", district="District A")
    sync_db.add_all([farmer, centre])
    sync_db.commit()

    user = User(
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=farmer.id,
        centre_id=centre.id,
        username=None,
    )
    sync_db.add(user)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_user_check_constraint_farmer_cannot_have_username(
    sync_db: Session,
) -> None:
    farmer = Farmer(farmer_id="F-1", name="Ramesh")
    sync_db.add(farmer)
    sync_db.commit()

    user = User(
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=farmer.id,
        centre_id=None,
        username="ramesh123",
    )
    sync_db.add(user)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_user_check_constraint_officer_valid(sync_db: Session) -> None:
    centre = ProcurementCentre(name="Centre 1", district="District A")
    sync_db.add(centre)
    sync_db.commit()

    user = User(
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
        username="officer1",
        farmer_id=None,
    )
    sync_db.add(user)
    sync_db.commit()
    assert user.id is not None
    assert user.role == Role.OFFICER


def test_user_check_constraint_officer_requires_centre_id(
    sync_db: Session,
) -> None:
    user = User(
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=None,
        username="officer1",
        farmer_id=None,
    )
    sync_db.add(user)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_user_check_constraint_officer_requires_username(
    sync_db: Session,
) -> None:
    centre = ProcurementCentre(name="Centre 1", district="District A")
    sync_db.add(centre)
    sync_db.commit()

    user = User(
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
        username=None,
        farmer_id=None,
    )
    sync_db.add(user)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_user_check_constraint_officer_cannot_have_farmer_id(
    sync_db: Session,
) -> None:
    centre = ProcurementCentre(name="Centre 1", district="District A")
    farmer = Farmer(farmer_id="F-1", name="Ramesh")
    sync_db.add_all([centre, farmer])
    sync_db.commit()

    user = User(
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
        username="officer1",
        farmer_id=farmer.id,
    )
    sync_db.add(user)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_users_farmer_id_unique_enforced(sync_db: Session) -> None:
    farmer = Farmer(farmer_id="F-1", name="Ramesh")
    sync_db.add(farmer)
    sync_db.commit()

    u1 = User(
        password_hash="hash1",
        role=Role.FARMER,
        farmer_id=farmer.id,
    )
    u2 = User(
        password_hash="hash2",
        role=Role.FARMER,
        farmer_id=farmer.id,
    )
    sync_db.add(u1)
    sync_db.commit()

    sync_db.add(u2)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_users_phone_unique_enforced(sync_db: Session) -> None:
    centre = ProcurementCentre(name="Centre 1", district="District A")
    sync_db.add(centre)
    sync_db.commit()

    u1 = User(
        username="o1",
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
        phone="9876543210",
    )
    u2 = User(
        username="o2",
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
        phone="9876543210",
    )
    sync_db.add(u1)
    sync_db.commit()

    sync_db.add(u2)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_users_username_unique_enforced(sync_db: Session) -> None:
    centre = ProcurementCentre(name="Centre 1", district="District A")
    sync_db.add(centre)
    sync_db.commit()

    u1 = User(
        username="officer_same",
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
    )
    u2 = User(
        username="officer_same",
        password_hash="hash",
        role=Role.OFFICER,
        centre_id=centre.id,
    )
    sync_db.add(u1)
    sync_db.commit()

    sync_db.add(u2)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_farmers_farmer_id_unique_enforced(sync_db: Session) -> None:
    f1 = Farmer(farmer_id="GOV-100", name="Farmer A")
    f2 = Farmer(farmer_id="GOV-100", name="Farmer B")
    sync_db.add(f1)
    sync_db.commit()

    sync_db.add(f2)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_crops_code_unique_enforced(sync_db: Session) -> None:
    c1 = Crop(code="WHEAT", name="Wheat", unit="QUINTAL")
    c2 = Crop(code="WHEAT", name="Wheat Duplicate", unit="KG")
    sync_db.add(c1)
    sync_db.commit()

    sync_db.add(c2)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_foreign_key_integrity_is_enforced(sync_db: Session) -> None:
    fake_centre_id = uuid4()
    counter = Counter(centre_id=fake_centre_id, name="Counter 1")
    sync_db.add(counter)
    with pytest.raises(IntegrityError):
        sync_db.commit()


def test_area_acres_precision(sync_db: Session) -> None:
    farmer = Farmer(farmer_id="F-10", name="Farmer Test")
    sync_db.add(farmer)
    sync_db.commit()

    holding = FarmerLandHolding(
        farmer_id=farmer.id,
        survey_number="SN-999",
        area_acres=Decimal("12345678.90"),
    )
    sync_db.add(holding)
    sync_db.commit()

    col = FarmerLandHolding.__table__.c.area_acres
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 10
    assert col.type.scale == 2


def test_uuid_and_timestamp_fields(sync_db: Session) -> None:
    crop = Crop(code="RICE", name="Rice", unit="QUINTAL")
    sync_db.add(crop)
    sync_db.commit()
    sync_db.refresh(crop)

    assert isinstance(crop.id, UUID)
    assert crop.created_at is not None
    assert crop.updated_at is not None

    orig_updated = crop.updated_at
    crop.name = "Basmati Rice"
    sync_db.commit()
    sync_db.refresh(crop)

    stmt = select(Crop).where(Crop.id == crop.id)
    saved = sync_db.execute(stmt).scalar_one()
    assert saved.name == "Basmati Rice"
    assert saved.updated_at >= orig_updated
