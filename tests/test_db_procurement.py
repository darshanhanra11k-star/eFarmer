from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.db.base import (
    Base,
    Counter,
    Crop,
    Farmer,
    FarmerLandHolding,
    IntentStatus,
    ProcurementCentre,
    ProcurementIntent,
    ProcurementRecord,
    ProcurementStatusHistory,
    ProcurementToken,
    ProcurementTokenStatus,
    User,
)


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


def test_procurement_tables_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "procurement_intents",
        "procurement_tokens",
        "procurement_records",
        "procurement_status_history",
    }
    assert expected.issubset(table_names)


def _create_seeded_entities(
    session: Session,
) -> tuple[Farmer, ProcurementCentre, Crop, FarmerLandHolding, User, Counter]:
    farmer = Farmer(
        id=uuid4(),
        farmer_id="F-999",
        name="Test Farmer",
        phone="9876543210",
    )
    centre = ProcurementCentre(
        id=uuid4(),
        name="North Centre",
        district="District North",
    )
    crop = Crop(
        id=uuid4(),
        code="WHEAT-01",
        name="Wheat",
        unit="KG",
    )
    session.add_all([farmer, centre, crop])
    session.flush()

    holding = FarmerLandHolding(
        id=uuid4(),
        farmer_id=farmer.id,
        survey_number="SN-100",
        area_acres=Decimal("5.50"),
    )
    officer_user = User(
        id=uuid4(),
        username="officer_north",
        password_hash="fake_hash",
        role=Role.OFFICER,
        centre_id=centre.id,
    )
    counter = Counter(
        id=uuid4(),
        centre_id=centre.id,
        name="Counter 1",
    )
    session.add_all([holding, officer_user, counter])
    session.flush()
    return farmer, centre, crop, holding, officer_user, counter


def test_procurement_intent_persistence(sync_db: Session) -> None:
    farmer, centre, crop, holding, officer, _ = _create_seeded_entities(sync_db)

    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        land_holding_id=holding.id,
        expected_quantity_kg=Decimal("1500.00"),
        ready_date=date(2026, 10, 1),
        status=IntentStatus.PENDING,
        created_by=officer.id,
    )
    sync_db.add(intent)
    sync_db.commit()

    saved = sync_db.get(ProcurementIntent, intent.id)
    assert saved is not None
    assert saved.expected_quantity_kg == Decimal("1500.00")
    assert saved.status == IntentStatus.PENDING
    assert saved.farmer.id == farmer.id
    assert saved.centre.id == centre.id
    assert saved.crop.id == crop.id
    assert len(saved.status_history) == 0


def test_procurement_intent_unique_slot_constraint(sync_db: Session) -> None:
    farmer, centre, crop, holding, officer, _ = _create_seeded_entities(sync_db)

    intent1 = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        land_holding_id=holding.id,
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 10, 1),
        status=IntentStatus.PENDING,
        created_by=officer.id,
    )
    sync_db.add(intent1)
    sync_db.commit()

    intent2 = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        land_holding_id=holding.id,
        expected_quantity_kg=Decimal("2000"),
        ready_date=date(2026, 10, 1),
        status=IntentStatus.PENDING,
        created_by=officer.id,
    )
    sync_db.add(intent2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_procurement_token_unique_centre_schedule_token(sync_db: Session) -> None:
    farmer, centre, crop, holding, officer, _ = _create_seeded_entities(sync_db)

    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        land_holding_id=holding.id,
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 10, 1),
        status=IntentStatus.APPROVED,
        created_by=officer.id,
    )
    sync_db.add(intent)
    sync_db.flush()

    scheduled = datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC)
    t1 = ProcurementToken(
        id=uuid4(),
        intent_id=intent.id,
        centre_id=centre.id,
        token_number=1,
        scheduled_at=scheduled,
        status=ProcurementTokenStatus.WAITING,
    )
    sync_db.add(t1)
    sync_db.commit()

    # Duplicate token number for same centre and scheduled_at
    t2 = ProcurementToken(
        id=uuid4(),
        intent_id=intent.id,
        centre_id=centre.id,
        token_number=1,
        scheduled_at=scheduled,
        status=ProcurementTokenStatus.WAITING,
    )
    sync_db.add(t2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_procurement_record_unique_token_id(sync_db: Session) -> None:
    farmer, centre, crop, holding, officer, counter = _create_seeded_entities(sync_db)

    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        land_holding_id=holding.id,
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 10, 1),
        status=IntentStatus.APPROVED,
        created_by=officer.id,
    )
    sync_db.add(intent)
    sync_db.flush()

    token = ProcurementToken(
        id=uuid4(),
        intent_id=intent.id,
        centre_id=centre.id,
        token_number=1,
        scheduled_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        status=ProcurementTokenStatus.COMPLETED,
    )
    sync_db.add(token)
    sync_db.flush()

    rec1 = ProcurementRecord(
        id=uuid4(),
        intent_id=intent.id,
        token_id=token.id,
        counter_id=counter.id,
        actual_quantity_kg=Decimal("950.00"),
        price_per_kg=Decimal("25.00"),
        total_amount=Decimal("23750.00"),
    )
    sync_db.add(rec1)
    sync_db.commit()

    # Second record with same token_id must fail unique constraint
    rec2 = ProcurementRecord(
        id=uuid4(),
        intent_id=intent.id,
        token_id=token.id,
        counter_id=counter.id,
        actual_quantity_kg=Decimal("950.00"),
        price_per_kg=Decimal("25.00"),
        total_amount=Decimal("23750.00"),
    )
    sync_db.add(rec2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_procurement_status_history_check_constraint(sync_db: Session) -> None:
    farmer, centre, crop, holding, officer, _ = _create_seeded_entities(sync_db)

    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        land_holding_id=holding.id,
        expected_quantity_kg=Decimal("1000"),
        ready_date=date(2026, 10, 1),
        status=IntentStatus.PENDING,
        created_by=officer.id,
    )
    sync_db.add(intent)
    sync_db.flush()

    # Valid: from_status = 'PENDING' without token
    h1 = ProcurementStatusHistory(
        id=uuid4(),
        intent_id=intent.id,
        token_id=None,
        from_status="PENDING",
        to_status="APPROVED",
        changed_by=officer.id,
    )
    sync_db.add(h1)
    sync_db.commit()

    # Invalid: no token, from_status != PENDING and
    # to_status not in (APPROVED, REJECTED, CANCELLED)
    h2 = ProcurementStatusHistory(
        id=uuid4(),
        intent_id=intent.id,
        token_id=None,
        from_status="PROCESSING",
        to_status="COMPLETED",
        changed_by=officer.id,
    )
    sync_db.add(h2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()
