from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

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
from app.models.counter import Counter
from app.models.farmer import Farmer
from app.models.queue import Queue, QueueStatus
from app.models.queue_entry import QueueEntry
from app.models.token import Token, TokenStatus
from app.models.user import User
from app.repositories.queue import QueueRepository
from app.repositories.token import TokenRepository
from app.services.queue import QueueService


class _FakeScalarResult:
    def __init__(self, item: Any) -> None:
        self._item = item

    def scalar_one_or_none(self) -> Any:
        return self._item

    def scalar_one(self) -> Any:
        return self._item

    def scalars(self) -> Any:
        return self

    def all(self) -> list[Any]:
        if self._item is None:
            return []
        if isinstance(self._item, list):
            return self._item
        return [self._item]


class FakeQueueDbSession:
    def __init__(self) -> None:
        self.queues: dict[UUID, Queue] = {}
        self.queue_entries: dict[UUID, QueueEntry] = {}
        self.tokens: dict[UUID, Token] = {}
        self.farmers: dict[UUID, Farmer] = {}
        self.users: dict[UUID, User] = {}
        self.counters: dict[UUID, Counter] = {}
        self._pending: list[Any] = []

    def add(self, obj: Any) -> None:
        self._pending.append(obj)

    def add_all(self, objs: list[Any]) -> None:
        self._pending.extend(objs)

    def sync_flush(self) -> None:
        now = datetime.now(UTC)
        for obj in self._pending:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = now
            if isinstance(obj, Queue):
                self.queues[obj.id] = obj
            elif isinstance(obj, QueueEntry):
                self.queue_entries[obj.id] = obj
            elif isinstance(obj, Token):
                self.tokens[obj.id] = obj
            elif isinstance(obj, Farmer):
                self.farmers[obj.id] = obj
            elif isinstance(obj, User):
                self.users[obj.id] = obj
            elif isinstance(obj, Counter):
                self.counters[obj.id] = obj
        self._pending.clear()

    async def flush(self) -> None:
        self.sync_flush()

    async def commit(self) -> None:
        self.sync_flush()

    async def refresh(self, obj: Any) -> None:
        pass

    async def rollback(self) -> None:
        self._pending.clear()

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        sql = str(stmt)
        params = stmt.compile().params if hasattr(stmt, "compile") else {}

        if "FROM queues" in sql:
            for q_id, q in self.queues.items():
                if (
                    f"queues.id = '{q_id}'" in sql
                    or params.get("id_1") == q_id
                    or params.get("id_1") == str(q_id)
                ):
                    return _FakeScalarResult(q)
                for val in params.values():
                    if val == q_id or str(val) == str(q_id):
                        return _FakeScalarResult(q)
            return _FakeScalarResult(None)

        if "FROM tokens" in sql:
            sql_lower = sql.lower()
            if "count(" in sql_lower:
                counts: dict[str, int] = {}
                target_qid: UUID | None = None
                for val in params.values():
                    if val in self.queues:
                        target_qid = val
                for t in self.tokens.values():
                    if target_qid is None or t.queue_id == target_qid:
                        status_str = str(
                            t.status.value if hasattr(t.status, "value") else t.status
                        )
                        counts[status_str] = counts.get(status_str, 0) + 1
                return _FakeScalarResult(list(counts.items()))

            if "max(tokens.sequence_number)" in sql_lower:
                target_max_qid: UUID | None = None
                for val in params.values():
                    if val in self.queues or str(val) in [str(k) for k in self.queues]:
                        target_max_qid = val
                seqs = [
                    t.sequence_number
                    for t in self.tokens.values()
                    if target_max_qid is None or str(t.queue_id) == str(target_max_qid)
                ]
                return _FakeScalarResult((max(seqs) + 1) if seqs else 1)

            if "order by tokens.called_at" in sql_lower:
                called = [
                    t
                    for t in self.tokens.values()
                    if t.status in {TokenStatus.CALLED, TokenStatus.PROCESSING}
                    and t.called_at is not None
                ]
                called.sort(key=lambda x: x.called_at or datetime.min, reverse=True)
                return _FakeScalarResult(called[0].token_number if called else None)

            if "tokens.sequence_number desc" in sql_lower:
                tokens_list = list(self.tokens.values())
                tokens_list.sort(key=lambda x: x.sequence_number, reverse=True)
                return _FakeScalarResult(
                    tokens_list[0].token_number if tokens_list else None
                )

            if "skip locked" in sql_lower or (
                "tokens.sequence_number asc" in sql_lower and "where" in sql_lower
            ):
                waiting = [
                    t for t in self.tokens.values() if t.status == TokenStatus.WAITING
                ]
                waiting.sort(key=lambda x: x.sequence_number)
                return _FakeScalarResult(waiting[0] if waiting else None)

            if "where" in sql_lower and "tokens.farmer_id =" in sql_lower:
                active_statuses = {
                    "CHECK_IN",
                    "TOKEN",
                    "WAITING",
                    "CALLED",
                    "PROCESSING",
                }
                for t in self.tokens.values():
                    t_status = (
                        t.status.value if hasattr(t.status, "value") else str(t.status)
                    )
                    match_farmer = any(
                        val == t.farmer_id or str(val) == str(t.farmer_id)
                        for val in params.values()
                    )
                    match_queue = any(
                        val == t.queue_id or str(val) == str(t.queue_id)
                        for val in params.values()
                    )
                    if match_farmer and match_queue and t_status in active_statuses:
                        return _FakeScalarResult(t)
                return _FakeScalarResult(None)

            for t_id, t in self.tokens.items():
                for val in params.values():
                    if val == t_id or str(val) == str(t_id):
                        return _FakeScalarResult(t)
            return _FakeScalarResult(None)

        if "FROM queue_entries" in sql and "max(queue_entries.position)" in sql:
            target_pos_qid: UUID | None = None
            for val in params.values():
                if val in self.queues or str(val) in [str(k) for k in self.queues]:
                    target_pos_qid = val
            positions = [
                e.position
                for e in self.queue_entries.values()
                if target_pos_qid is None or str(e.queue_id) == str(target_pos_qid)
            ]
            return _FakeScalarResult((max(positions) + 1) if positions else 1)

        if "FROM users" in sql:
            for u_id, u in self.users.items():
                for val in params.values():
                    if val == u_id or str(val) == str(u_id) or val == u.username:
                        return _FakeScalarResult(u)
            return _FakeScalarResult(None)

        if "FROM counters" in sql:
            for c_id, c in self.counters.items():
                for val in params.values():
                    if val == c_id or str(val) == str(c_id):
                        return _FakeScalarResult(c)
            return _FakeScalarResult(None)

        return _FakeScalarResult(None)


@pytest.fixture
async def fake_session() -> FakeQueueDbSession:
    session = FakeQueueDbSession()
    centre = ProcurementCentre(id=uuid4(), name="Test Centre", district="Test District")
    farmer = Farmer(
        id=uuid4(), farmer_id="F-TEST-1", name="Ramesh Kumar", phone="9876543210"
    )
    farmer_user = User(
        id=uuid4(),
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=farmer.id,
        centre_id=None,
        username=None,
    )
    officer_user = User(
        id=uuid4(),
        password_hash="hash",
        role=Role.OFFICER,
        farmer_id=None,
        centre_id=centre.id,
        username="officer_1",
    )
    queue = Queue(
        id=uuid4(),
        centre_id=centre.id,
        date=date(2026, 9, 18),
        status=QueueStatus.OPEN,
    )
    session.add_all([centre, farmer, farmer_user, officer_user, queue])
    await session.flush()
    return session


async def test_join_queue_farmer_success(fake_session: FakeQueueDbSession) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = list(fake_session.users.values())[0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_user = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)

    token = await service.join_queue(
        queue_id=queue.id,
        requested_farmer_id=farmer.id,
        current_user=auth_user,
    )

    assert token.farmer_id == farmer.id
    assert token.queue_id == queue.id
    assert token.sequence_number == 1
    assert token.token_number == "T-001"
    assert token.status == TokenStatus.WAITING


async def test_join_queue_duplicate_active_token_raises_conflict(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer_user = list(fake_session.users.values())[0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_user = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)

    await service.join_queue(
        queue_id=queue.id,
        requested_farmer_id=None,
        current_user=auth_user,
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.join_queue(
            queue_id=queue.id,
            requested_farmer_id=None,
            current_user=auth_user,
        )
    assert "already has an active token" in exc_info.value.message


async def test_join_queue_farmer_for_another_farmer_raises_permission_denied(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer_user = list(fake_session.users.values())[0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_user = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)

    with pytest.raises(PermissionDeniedError):
        await service.join_queue(
            queue_id=queue.id,
            requested_farmer_id=uuid4(),
            current_user=auth_user,
        )


async def test_join_queue_closed_raises_conflict(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = list(fake_session.users.values())[0]
    queue.status = QueueStatus.CLOSED

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_user = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)

    with pytest.raises(ConflictError) as exc:
        await service.join_queue(
            queue_id=queue.id,
            requested_farmer_id=farmer.id,
            current_user=auth_user,
        )
    assert "not open" in exc.value.message


async def test_join_queue_officer_requires_farmer_id(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]
    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    officer_user = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)

    with pytest.raises(ValidationError):
        await service.join_queue(
            queue_id=queue.id,
            requested_farmer_id=None,
            current_user=officer_user,
        )


async def test_call_next_officer_success(fake_session: FakeQueueDbSession) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = [u for u in fake_session.users.values() if u.role == Role.FARMER][0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    await service.join_queue(queue.id, farmer.id, auth_farmer)

    auth_officer = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)
    called = await service.call_next(
        queue.id, counter_id=None, current_user=auth_officer
    )

    assert called.status == TokenStatus.CALLED
    assert called.called_at is not None


async def test_call_next_no_waiting_tokens_raises_not_found(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]
    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_officer = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)

    with pytest.raises(NotFoundError):
        await service.call_next(queue.id, counter_id=None, current_user=auth_officer)


async def test_call_next_farmer_role_raises_permission_denied(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer_user = [u for u in fake_session.users.values() if u.role == Role.FARMER][0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)

    with pytest.raises(PermissionDeniedError):
        await service.call_next(queue.id, counter_id=None, current_user=auth_farmer)


async def test_process_token_lifecycle(fake_session: FakeQueueDbSession) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = [u for u in fake_session.users.values() if u.role == Role.FARMER][0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    token = await service.join_queue(queue.id, farmer.id, auth_farmer)

    auth_officer = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)

    # Invalid transition: WAITING cannot be PROCESSING directly
    with pytest.raises(ConflictError):
        await service.process_token(token.id, auth_officer)

    # Move WAITING -> CALLED
    called = await service.call_next(queue.id, None, auth_officer)
    assert called.status == TokenStatus.CALLED

    # Move CALLED -> PROCESSING
    processing = await service.process_token(token.id, auth_officer)
    assert processing.status == TokenStatus.PROCESSING
    assert processing.processing_started_at is not None

    # Move PROCESSING -> COMPLETED
    completed = await service.complete_token(token.id, auth_officer)
    assert completed.status == TokenStatus.COMPLETED
    assert completed.completed_at is not None

    # Invalid transition: COMPLETED cannot be PROCESSING again
    with pytest.raises(ConflictError):
        await service.process_token(token.id, auth_officer)


async def test_cancel_token_by_owner_farmer(fake_session: FakeQueueDbSession) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = list(fake_session.users.values())[0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    token = await service.join_queue(queue.id, farmer.id, auth_farmer)

    cancelled = await service.cancel_token(token.id, auth_farmer)
    assert cancelled.status == TokenStatus.CANCELLED
    assert cancelled.cancelled_at is not None


async def test_cancel_token_non_owner_farmer_raises_permission_denied(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = list(fake_session.users.values())[0]

    other_farmer = Farmer(id=uuid4(), farmer_id="F-OTHER", name="Other")
    other_user = User(
        id=uuid4(),
        password_hash="hash",
        role=Role.FARMER,
        farmer_id=other_farmer.id,
    )
    fake_session.add_all([other_farmer, other_user])
    await fake_session.flush()

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    token = await service.join_queue(queue.id, farmer.id, auth_farmer)

    auth_other = AuthenticatedUser(subject=str(other_user.id), role=Role.FARMER)
    with pytest.raises(PermissionDeniedError):
        await service.cancel_token(token.id, auth_other)


async def test_cancel_called_or_processing_token_raises_conflict(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = [u for u in fake_session.users.values() if u.role == Role.FARMER][0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    token = await service.join_queue(queue.id, farmer.id, auth_farmer)

    auth_officer = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)
    await service.call_next(queue.id, None, auth_officer)

    with pytest.raises(ConflictError):
        await service.cancel_token(token.id, auth_officer)


async def test_get_queue_status_counts(fake_session: FakeQueueDbSession) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = list(fake_session.users.values())[0]

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    await service.join_queue(queue.id, farmer.id, auth_farmer)

    status_resp = await service.get_queue_status(queue.id, auth_farmer)
    assert status_resp.total_waiting == 1
    assert status_resp.total_called == 0
    assert status_resp.last_issued_token == "T-001"


async def test_officer_cross_centre_operations_rejected(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = [u for u in fake_session.users.values() if u.role == Role.FARMER][0]

    # Officer from different centre
    other_centre = ProcurementCentre(
        id=uuid4(), name="Other Centre", district="District X"
    )
    other_officer = User(
        id=uuid4(),
        password_hash="hash",
        role=Role.OFFICER,
        farmer_id=None,
        centre_id=other_centre.id,
        username="other_officer",
    )
    fake_session.add_all([other_centre, other_officer])
    await fake_session.flush()

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )

    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    token = await service.join_queue(queue.id, farmer.id, auth_farmer)

    cross_officer_auth = AuthenticatedUser(
        subject=str(other_officer.id),
        role=Role.OFFICER,
    )

    # Cross-centre join_queue
    with pytest.raises(PermissionDeniedError):
        await service.join_queue(queue.id, farmer.id, cross_officer_auth)

    # Cross-centre call_next
    with pytest.raises(PermissionDeniedError):
        await service.call_next(queue.id, None, cross_officer_auth)

    # Cross-centre process_token
    with pytest.raises(PermissionDeniedError):
        await service.process_token(token.id, cross_officer_auth)

    # Cross-centre complete_token
    with pytest.raises(PermissionDeniedError):
        await service.complete_token(token.id, cross_officer_auth)

    # Cross-centre cancel_token
    with pytest.raises(PermissionDeniedError):
        await service.cancel_token(token.id, cross_officer_auth)


async def test_counter_from_different_centre_rejected_on_call_next(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    farmer = list(fake_session.farmers.values())[0]
    farmer_user = [u for u in fake_session.users.values() if u.role == Role.FARMER][0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]

    # Counter in a different centre
    other_centre = ProcurementCentre(
        id=uuid4(), name="Other Centre 2", district="District Y"
    )
    other_counter = Counter(
        id=uuid4(), centre_id=other_centre.id, name="Foreign Counter"
    )
    fake_session.add_all([other_centre, other_counter])
    await fake_session.flush()

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )
    auth_farmer = AuthenticatedUser(subject=str(farmer_user.id), role=Role.FARMER)
    await service.join_queue(queue.id, farmer.id, auth_farmer)

    auth_officer = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)

    with pytest.raises(PermissionDeniedError) as exc_info:
        await service.call_next(
            queue.id, counter_id=other_counter.id, current_user=auth_officer
        )
    assert "does not belong to this procurement centre" in exc_info.value.message


async def test_call_next_strict_fifo_ordering(
    fake_session: FakeQueueDbSession,
) -> None:
    queue = list(fake_session.queues.values())[0]
    officer_db_user = [
        u for u in fake_session.users.values() if u.role == Role.OFFICER
    ][0]
    auth_officer = AuthenticatedUser(subject=str(officer_db_user.id), role=Role.OFFICER)

    # Add 3 farmers
    f1 = Farmer(id=uuid4(), farmer_id="F-FIFO-1", name="Farmer 1")
    u1 = User(id=uuid4(), password_hash="h", role=Role.FARMER, farmer_id=f1.id)
    f2 = Farmer(id=uuid4(), farmer_id="F-FIFO-2", name="Farmer 2")
    u2 = User(id=uuid4(), password_hash="h", role=Role.FARMER, farmer_id=f2.id)
    f3 = Farmer(id=uuid4(), farmer_id="F-FIFO-3", name="Farmer 3")
    u3 = User(id=uuid4(), password_hash="h", role=Role.FARMER, farmer_id=f3.id)
    fake_session.add_all([f1, u1, f2, u2, f3, u3])
    await fake_session.flush()

    service = QueueService(
        QueueRepository(fake_session),  # type: ignore[arg-type]
        TokenRepository(fake_session),  # type: ignore[arg-type]
    )

    t1 = await service.join_queue(
        queue.id, f1.id, AuthenticatedUser(subject=str(u1.id), role=Role.FARMER)
    )
    t2 = await service.join_queue(
        queue.id, f2.id, AuthenticatedUser(subject=str(u2.id), role=Role.FARMER)
    )
    t3 = await service.join_queue(
        queue.id, f3.id, AuthenticatedUser(subject=str(u3.id), role=Role.FARMER)
    )

    assert t1.sequence_number < t2.sequence_number < t3.sequence_number

    # First call_next must return t1
    first = await service.call_next(queue.id, None, auth_officer)
    assert first.id == t1.id
    assert first.status == TokenStatus.CALLED

    # Second call_next must return t2 (strict FIFO, never t3)
    second = await service.call_next(queue.id, None, auth_officer)
    assert second.id == t2.id
    assert second.status == TokenStatus.CALLED

    # Third call_next must return t3
    third = await service.call_next(queue.id, None, auth_officer)
    assert third.id == t3.id
    assert third.status == TokenStatus.CALLED
