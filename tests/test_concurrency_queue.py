import asyncio
import sys
from datetime import date
from uuid import UUID, uuid4

import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import func, select

from app.core.exceptions import ConflictError
from app.core.rbac import Role
from app.db.session import get_session_factory
from app.dependencies.auth import AuthenticatedUser
from app.models.centre import ProcurementCentre
from app.models.counter import Counter
from app.models.crop import Crop
from app.models.farmer import Farmer
from app.models.queue import Queue, QueueStatus
from app.models.queue_entry import QueueEntry
from app.models.token import Token, TokenStatus
from app.models.user import User
from app.repositories.queue import QueueRepository
from app.repositories.token import TokenRepository
from app.services.queue import QueueService


@pytest.mark.asyncio
async def test_concurrent_queue_joins_unique_sequences() -> None:
    """Scenario A: 10 distinct farmers join the same queue concurrently
    using independent sessions.
    """
    factory = get_session_factory()

    # 1. Seed centre, crop, and queue in a setup session
    async with factory() as setup_session:
        centre = ProcurementCentre(
            name=f"Concurrency Test Centre {uuid4().hex[:6]}",
            district="District",
            state="State",
            active=True,
        )
        crop = Crop(
            code=f"CR-{uuid4().hex[:8]}",
            name="Concurrency Test Crop",
            unit="kg",
            active=True,
        )
        setup_session.add_all([centre, crop])
        await setup_session.flush()

        queue = Queue(
            centre_id=centre.id,
            crop_id=crop.id,
            date=date.today(),
            status=QueueStatus.OPEN,
        )
        setup_session.add(queue)
        await setup_session.flush()

        farmers: list[Farmer] = []
        users: list[User] = []
        for i in range(10):
            phone_num = f"+9198{uuid4().hex[:8]}"
            farmer = Farmer(
                farmer_id=f"F-{uuid4().hex[:8]}",
                name=f"Farmer {i}",
                phone=phone_num,
                village="Village",
                block="Block",
                district="District",
                state="State",
                active=True,
            )
            setup_session.add(farmer)
            await setup_session.flush()
            farmers.append(farmer)

            user = User(
                username=f"user_{uuid4().hex[:8]}",
                phone=phone_num,
                password_hash="hashed_pw",
                role=Role.FARMER,
                farmer_id=farmer.id,
                centre_id=None,
                active=True,
            )
            setup_session.add(user)
            await setup_session.flush()
            users.append(user)

        await setup_session.commit()
        queue_id = queue.id

    # 2. Concurrently execute 10 join_queue operations using
    # 10 independent AsyncSession instances
    async def _join(idx: int) -> Token:
        async with factory() as session:
            q_repo = QueueRepository(session)
            t_repo = TokenRepository(session)
            service = QueueService(q_repo, t_repo, session=session)
            auth_user = AuthenticatedUser(
                subject=str(users[idx].id),
                role=Role.FARMER,
            )
            res = await service.join_queue(
                queue_id=queue_id,
                requested_farmer_id=farmers[idx].id,
                current_user=auth_user,
            )
            # Re-read token entity to assert properties
            token = await t_repo.get_by_id(res.id)
            assert token is not None
            return token

    tasks = [_join(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # 3. Assertions
    assert len(results) == 10
    sequences = [t.sequence_number for t in results]

    async with factory() as verify_session:
        stmt = select(QueueEntry.position).where(QueueEntry.queue_id == queue_id)
        res_positions = await verify_session.execute(stmt)
        positions = list(res_positions.scalars().all())

    assert sorted(sequences) == list(range(1, 11)), f"Expected 1..10, got {sequences}"
    assert sorted(positions) == list(range(1, 11)), f"Expected 1..10, got {positions}"
    assert len(set(sequences)) == 10, "Duplicate sequence numbers detected"
    assert len(set(positions)) == 10, "Duplicate positions detected"


@pytest.mark.asyncio
async def test_concurrent_queue_joins_same_farmer_conflict() -> None:
    """Scenario B: 5 concurrent join requests for the same farmer on the same queue."""
    factory = get_session_factory()

    async with factory() as setup_session:
        centre = ProcurementCentre(
            name=f"Conflict Test Centre {uuid4().hex[:6]}",
            district="District",
            state="State",
            active=True,
        )
        crop = Crop(
            code=f"CR-{uuid4().hex[:8]}",
            name="Conflict Test Crop",
            unit="kg",
            active=True,
        )
        setup_session.add_all([centre, crop])
        await setup_session.flush()

        queue = Queue(
            centre_id=centre.id,
            crop_id=crop.id,
            date=date.today(),
            status=QueueStatus.OPEN,
        )
        setup_session.add(queue)

        farmer = Farmer(
            farmer_id=f"F-{uuid4().hex[:8]}",
            name="Single Farmer",
            phone=f"98111{uuid4().hex[:5]}",
            village="Village",
            block="Block",
            district="District",
            state="State",
            active=True,
        )
        setup_session.add(farmer)
        await setup_session.flush()

        user = User(
            username=f"user_{uuid4().hex[:8]}",
            phone=farmer.phone,
            password_hash="hashed_pw",
            role=Role.FARMER,
            farmer_id=farmer.id,
            centre_id=None,
            active=True,
        )
        setup_session.add(user)
        await setup_session.commit()

        queue_id = queue.id
        farmer_id = farmer.id
        user_id = user.id

    async def _join() -> str:
        async with factory() as session:
            q_repo = QueueRepository(session)
            t_repo = TokenRepository(session)
            service = QueueService(q_repo, t_repo, session=session)
            auth_user = AuthenticatedUser(
                subject=str(user_id),
                role=Role.FARMER,
            )
            try:
                await service.join_queue(
                    queue_id=queue_id,
                    requested_farmer_id=farmer_id,
                    current_user=auth_user,
                )
                return "SUCCESS"
            except ConflictError:
                return "CONFLICT"

    tasks = [_join() for _ in range(5)]
    outcomes = await asyncio.gather(*tasks)

    # Exactly 1 success, exactly 4 ConflictError outcomes
    assert outcomes.count("SUCCESS") == 1, f"Expected 1 success, got: {outcomes}"
    assert outcomes.count("CONFLICT") == 4, f"Expected 4 conflicts, got: {outcomes}"

    # Verify database contains exactly one active token and queue entry for this farmer
    async with factory() as verify_session:
        t_repo = TokenRepository(verify_session)
        token = await t_repo.get_active_token_for_farmer(farmer_id, queue_id)
        assert token is not None

        entry_stmt = select(func.count(QueueEntry.id)).where(
            QueueEntry.farmer_id == farmer_id,
            QueueEntry.queue_id == queue_id,
        )
        entry_count = (await verify_session.execute(entry_stmt)).scalar_one()
        assert entry_count == 1, f"Expected exactly 1 queue entry, got {entry_count}"


@pytest.mark.asyncio
async def test_concurrent_call_next_multi_counter() -> None:
    """Scenario C: 2 officers at different counters concurrently call next
    on a queue with 5 waiting tokens.
    """
    factory = get_session_factory()

    async with factory() as setup_session:
        centre = ProcurementCentre(
            name=f"Dispatch Test Centre {uuid4().hex[:6]}",
            district="District",
            state="State",
            active=True,
        )
        crop = Crop(
            code=f"CR-{uuid4().hex[:8]}",
            name="Dispatch Test Crop",
            unit="kg",
            active=True,
        )
        setup_session.add_all([centre, crop])
        await setup_session.flush()

        queue = Queue(
            centre_id=centre.id,
            crop_id=crop.id,
            date=date.today(),
            status=QueueStatus.OPEN,
        )
        setup_session.add(queue)

        counter1 = Counter(
            centre_id=centre.id,
            name="Counter 1",
            active=True,
        )
        counter2 = Counter(
            centre_id=centre.id,
            name="Counter 2",
            active=True,
        )
        setup_session.add_all([counter1, counter2])
        await setup_session.flush()

        officer1 = User(
            username=f"off1_{uuid4().hex[:8]}",
            password_hash="hashed_pw",
            role=Role.OFFICER,
            centre_id=centre.id,
            active=True,
        )
        officer2 = User(
            username=f"off2_{uuid4().hex[:8]}",
            password_hash="hashed_pw",
            role=Role.OFFICER,
            centre_id=centre.id,
            active=True,
        )
        setup_session.add_all([officer1, officer2])
        await setup_session.flush()

        # Seed 5 waiting tokens
        t_repo = TokenRepository(setup_session)
        for seq in range(1, 6):
            f = Farmer(
                farmer_id=f"F-{uuid4().hex[:8]}",
                name=f"Waiting Farmer {seq}",
                phone=f"91111{seq:05d}",
                village="V",
                block="B",
                district="D",
                state="S",
                active=True,
            )
            setup_session.add(f)
            await setup_session.flush()
            await t_repo.create_entry_and_token(
                queue_id=queue.id,
                farmer_id=f.id,
                position=seq,
                sequence_number=seq,
                token_number=f"T-{seq:03d}",
            )

        await setup_session.commit()

        queue_id = queue.id
        counter1_id = counter1.id
        counter2_id = counter2.id
        off1_id = officer1.id
        off2_id = officer2.id

    # Two concurrent calls
    async def _call(officer_user_id: UUID, counter_id: UUID) -> Token:
        async with factory() as session:
            q_repo = QueueRepository(session)
            t_repo = TokenRepository(session)
            service = QueueService(q_repo, t_repo, session=session)
            auth_officer = AuthenticatedUser(
                subject=str(officer_user_id),
                role=Role.OFFICER,
            )
            res = await service.call_next(
                queue_id=queue_id,
                counter_id=counter_id,
                current_user=auth_officer,
            )
            token = await t_repo.get_by_id(res.id)
            assert token is not None
            return token

    task1 = _call(off1_id, counter1_id)
    task2 = _call(off2_id, counter2_id)
    tok1, tok2 = await asyncio.gather(task1, task2)

    # Assertions
    assert tok1.id != tok2.id, "Same token was called by two counters"
    assert tok1.status == TokenStatus.CALLED
    assert tok2.status == TokenStatus.CALLED
    called_sequences = sorted([tok1.sequence_number, tok2.sequence_number])
    assert called_sequences == [1, 2], (
        f"Expected sequences 1 and 2, got: {called_sequences}"
    )
