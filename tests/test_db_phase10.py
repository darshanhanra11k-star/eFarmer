from collections.abc import Iterator
from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import (
    Base,
    Counter,
    Crop,
    Farmer,
    ProcurementCentre,
    Queue,
    QueueEntry,
    QueueStatus,
    Token,
    TokenStatus,
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


def test_phase10_tables_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "queues",
        "queue_entries",
        "tokens",
    }
    assert expected.issubset(table_names)


def test_alembic_upgrade_downgrade_cycle_phase10(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head", sql=True)
    command.downgrade(cfg, "0003:0001", sql=True)
    command.upgrade(cfg, "head", sql=True)


def test_queue_entry_has_no_status_column() -> None:
    queue_entry_cols = [c.name for c in QueueEntry.__table__.columns]
    assert "status" not in queue_entry_cols
    assert "position" in queue_entry_cols
    assert "farmer_id" in queue_entry_cols
    assert "queue_id" in queue_entry_cols


def test_queue_unique_centre_date_crop(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 1", district="District 1")
    crop = Crop(id=uuid4(), code="WHEAT", name="Wheat", unit="QUINTAL")
    sync_db.add_all([centre, crop])
    sync_db.commit()

    q1 = Queue(
        id=uuid4(),
        centre_id=centre.id,
        date=date(2026, 9, 18),
        crop_id=crop.id,
        status=QueueStatus.OPEN,
    )
    sync_db.add(q1)
    sync_db.commit()

    q2 = Queue(
        id=uuid4(),
        centre_id=centre.id,
        date=date(2026, 9, 18),
        crop_id=crop.id,
        status=QueueStatus.OPEN,
    )
    sync_db.add(q2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_queue_entries_unique_position(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 2", district="District 2")
    farmer1 = Farmer(id=uuid4(), farmer_id="F-1", name="Farmer 1")
    farmer2 = Farmer(id=uuid4(), farmer_id="F-2", name="Farmer 2")
    sync_db.add_all([centre, farmer1, farmer2])
    sync_db.commit()

    queue = Queue(id=uuid4(), centre_id=centre.id, date=date(2026, 9, 18))
    sync_db.add(queue)
    sync_db.commit()

    entry1 = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer1.id,
        position=1,
    )
    sync_db.add(entry1)
    sync_db.commit()

    entry2 = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer2.id,
        position=1,
    )
    sync_db.add(entry2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_tokens_unique_sequence_number(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 3", district="District 3")
    farmer1 = Farmer(id=uuid4(), farmer_id="F-3", name="Farmer 3")
    farmer2 = Farmer(id=uuid4(), farmer_id="F-4", name="Farmer 4")
    sync_db.add_all([centre, farmer1, farmer2])
    sync_db.commit()

    queue = Queue(id=uuid4(), centre_id=centre.id, date=date(2026, 9, 18))
    sync_db.add(queue)
    sync_db.commit()

    e1 = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer1.id,
        position=1,
    )
    e2 = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer2.id,
        position=2,
    )
    sync_db.add_all([e1, e2])
    sync_db.commit()

    t1 = Token(
        id=uuid4(),
        token_number="T-001",
        sequence_number=1,
        queue_id=queue.id,
        queue_entry_id=e1.id,
        farmer_id=farmer1.id,
        status=TokenStatus.WAITING,
    )
    sync_db.add(t1)
    sync_db.commit()

    t2 = Token(
        id=uuid4(),
        token_number="T-002",
        sequence_number=1,
        queue_id=queue.id,
        queue_entry_id=e2.id,
        farmer_id=farmer2.id,
        status=TokenStatus.WAITING,
    )
    sync_db.add(t2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_tokens_unique_token_number(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 4", district="District 4")
    farmer1 = Farmer(id=uuid4(), farmer_id="F-5", name="Farmer 5")
    farmer2 = Farmer(id=uuid4(), farmer_id="F-6", name="Farmer 6")
    sync_db.add_all([centre, farmer1, farmer2])
    sync_db.commit()

    queue = Queue(id=uuid4(), centre_id=centre.id, date=date(2026, 9, 18))
    sync_db.add(queue)
    sync_db.commit()

    e1 = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer1.id,
        position=1,
    )
    e2 = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer2.id,
        position=2,
    )
    sync_db.add_all([e1, e2])
    sync_db.commit()

    t1 = Token(
        id=uuid4(),
        token_number="T-001",
        sequence_number=1,
        queue_id=queue.id,
        queue_entry_id=e1.id,
        farmer_id=farmer1.id,
        status=TokenStatus.WAITING,
    )
    sync_db.add(t1)
    sync_db.commit()

    t2 = Token(
        id=uuid4(),
        token_number="T-001",
        sequence_number=2,
        queue_id=queue.id,
        queue_entry_id=e2.id,
        farmer_id=farmer2.id,
        status=TokenStatus.WAITING,
    )
    sync_db.add(t2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_token_unique_queue_entry_id(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 5", district="District 5")
    farmer = Farmer(id=uuid4(), farmer_id="F-7", name="Farmer 7")
    sync_db.add_all([centre, farmer])
    sync_db.commit()

    queue = Queue(id=uuid4(), centre_id=centre.id, date=date(2026, 9, 18))
    sync_db.add(queue)
    sync_db.commit()

    entry = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer.id,
        position=1,
    )
    sync_db.add(entry)
    sync_db.commit()

    t1 = Token(
        id=uuid4(),
        token_number="T-001",
        sequence_number=1,
        queue_id=queue.id,
        queue_entry_id=entry.id,
        farmer_id=farmer.id,
        status=TokenStatus.WAITING,
    )
    sync_db.add(t1)
    sync_db.commit()

    t2 = Token(
        id=uuid4(),
        token_number="T-002",
        sequence_number=2,
        queue_id=queue.id,
        queue_entry_id=entry.id,
        farmer_id=farmer.id,
        status=TokenStatus.WAITING,
    )
    sync_db.add(t2)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_token_counter_relationship(sync_db: Session) -> None:
    centre = ProcurementCentre(id=uuid4(), name="Centre 6", district="District 6")
    sync_db.add(centre)
    sync_db.commit()

    counter = Counter(id=uuid4(), centre_id=centre.id, name="Counter 1")
    farmer = Farmer(id=uuid4(), farmer_id="F-8", name="Farmer 8")
    sync_db.add_all([counter, farmer])
    sync_db.commit()

    queue = Queue(id=uuid4(), centre_id=centre.id, date=date(2026, 9, 18))
    sync_db.add(queue)
    sync_db.commit()

    entry = QueueEntry(
        id=uuid4(),
        queue_id=queue.id,
        farmer_id=farmer.id,
        position=1,
    )
    sync_db.add(entry)
    sync_db.commit()

    token = Token(
        id=uuid4(),
        token_number="T-001",
        sequence_number=1,
        queue_id=queue.id,
        queue_entry_id=entry.id,
        farmer_id=farmer.id,
        counter_id=counter.id,
        status=TokenStatus.CALLED,
    )
    sync_db.add(token)
    sync_db.commit()

    assert token.counter is not None
    assert token.counter.name == "Counter 1"
    assert token.status == TokenStatus.CALLED
