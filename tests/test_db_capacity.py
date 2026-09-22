from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import (
    Base,
    CapacityRecord,
    Crop,
    ProcurementCentre,
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


def test_capacity_records_table_registered_in_metadata() -> None:
    assert "capacity_records" in Base.metadata.tables


def test_capacity_record_persistence(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 1", district="District 1")
    crop = Crop(id=uuid4(), code="WHEAT", name="Wheat", unit="KG")
    sync_db.add_all([centre, crop])
    sync_db.flush()

    record = CapacityRecord(
        id=uuid4(),
        centre_id=centre.id,
        crop_id=crop.id,
        date=date(2026, 11, 15),
        total_capacity_kg=Decimal("1500.50"),
        allocated_quantity_kg=Decimal("500.00"),
        procured_quantity_kg=Decimal("200.00"),
    )
    sync_db.add(record)
    sync_db.commit()

    saved = sync_db.get(CapacityRecord, record.id)
    assert saved is not None
    assert saved.total_capacity_kg == Decimal("1500.50")
    assert saved.allocated_quantity_kg == Decimal("500.00")
    assert saved.procured_quantity_kg == Decimal("200.00")
    assert saved.active is True
    assert saved.centre.id == centre.id
    assert saved.crop.id == crop.id


def test_capacity_record_unique_constraint(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 1", district="District 1")
    crop = Crop(id=uuid4(), code="WHEAT", name="Wheat", unit="KG")
    sync_db.add_all([centre, crop])
    sync_db.flush()

    target_date = date(2026, 11, 15)
    r1 = CapacityRecord(
        id=uuid4(),
        centre_id=centre.id,
        crop_id=crop.id,
        date=target_date,
        total_capacity_kg=Decimal("1000.00"),
    )
    sync_db.add(r1)
    sync_db.commit()

    r2 = CapacityRecord(
        id=uuid4(),
        centre_id=centre.id,
        crop_id=crop.id,
        date=target_date,
        total_capacity_kg=Decimal("2000.00"),
    )
    sync_db.add(r2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_capacity_check_non_negative_constraint(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 1", district="District 1")
    crop = Crop(id=uuid4(), code="WHEAT", name="Wheat", unit="KG")
    sync_db.add_all([centre, crop])
    sync_db.flush()

    invalid_record = CapacityRecord(
        id=uuid4(),
        centre_id=centre.id,
        crop_id=crop.id,
        date=date(2026, 11, 15),
        total_capacity_kg=Decimal("-100.00"),
    )
    sync_db.add(invalid_record)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_capacity_check_not_exceeded_constraint(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 1", district="District 1")
    crop = Crop(id=uuid4(), code="WHEAT", name="Wheat", unit="KG")
    sync_db.add_all([centre, crop])
    sync_db.flush()

    invalid_record = CapacityRecord(
        id=uuid4(),
        centre_id=centre.id,
        crop_id=crop.id,
        date=date(2026, 11, 15),
        total_capacity_kg=Decimal("100.00"),
        allocated_quantity_kg=Decimal("200.00"),
    )
    sync_db.add(invalid_record)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()
