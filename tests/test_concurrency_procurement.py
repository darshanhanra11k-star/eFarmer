import asyncio
import sys
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.exceptions import ConflictError
from app.core.rbac import Role
from app.db.session import get_session_factory
from app.dependencies.auth import AuthenticatedUser
from app.models.centre import ProcurementCentre
from app.models.crop import Crop
from app.models.farmer import Farmer
from app.models.land_holding import FarmerLandHolding
from app.models.procurement import ProcurementIntent
from app.models.user import User
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.procurement import ProcurementRepository
from app.schemas.procurement import ProcurementIntentCreate
from app.services.procurement import ProcurementService


@pytest.mark.asyncio
async def test_concurrent_duplicate_intents_safe_rollback() -> None:
    """Scenario D: 2 concurrent intent submissions for the identical slot.

    Assertions:
    - Exactly one success
    - Exactly one ConflictError
    - Exactly one persisted intent
    - Failed transaction rolls back
    - Failed session can successfully execute another query afterward
    """
    factory = get_session_factory()
    target_date = date(2026, 11, 15)

    # 1. Seed prerequisite entities
    async with factory() as setup_session:
        centre = ProcurementCentre(
            name=f"Intent Centre {uuid4().hex[:6]}",
            district="District",
            state="State",
            active=True,
        )
        crop = Crop(
            code=f"CR-{uuid4().hex[:8]}",
            name="Intent Crop",
            unit="kg",
            active=True,
        )
        setup_session.add_all([centre, crop])
        await setup_session.flush()

        phone_num = f"+9199{uuid4().hex[:8]}"
        farmer = Farmer(
            farmer_id=f"F-{uuid4().hex[:8]}",
            name="Intent Farmer",
            phone=phone_num,
            village="Village",
            block="Block",
            district="District",
            state="State",
            active=True,
        )
        setup_session.add(farmer)
        await setup_session.flush()

        holding = FarmerLandHolding(
            farmer_id=farmer.id,
            survey_number=f"SN-{uuid4().hex[:6]}",
            area_acres=Decimal("5.0"),
            district="District",
            state="State",
            active=True,
        )
        setup_session.add(holding)
        await setup_session.flush()

        user = User(
            username=f"farmer_{uuid4().hex[:8]}",
            phone=phone_num,
            password_hash="hashed_pw",
            role=Role.FARMER,
            farmer_id=farmer.id,
            centre_id=None,
            active=True,
        )
        setup_session.add(user)
        await setup_session.commit()

        centre_id = centre.id
        crop_id = crop.id
        farmer_id = farmer.id
        holding_id = holding.id
        user_id = user.id

    payload = ProcurementIntentCreate(
        centre_id=centre_id,
        crop_id=crop_id,
        land_holding_id=holding_id,
        expected_quantity_kg=Decimal("400.00"),
        ready_date=target_date,
    )
    auth_user = AuthenticatedUser(
        subject=str(user_id),
        role=Role.FARMER,
    )

    # 2. Concurrently execute 2 intent creations with independent sessions
    session1 = factory()
    session2 = factory()

    svc1 = ProcurementService(
        procurement_repo=ProcurementRepository(session1),
        farmer_repo=FarmerRepository(session1),
        centre_repo=CentreRepository(session1),
        crop_repo=CropRepository(session1),
        session=session1,
    )
    svc2 = ProcurementService(
        procurement_repo=ProcurementRepository(session2),
        farmer_repo=FarmerRepository(session2),
        centre_repo=CentreRepository(session2),
        crop_repo=CropRepository(session2),
        session=session2,
    )

    try:
        task1 = svc1.create_procurement_intent(payload, auth_user)
        task2 = svc2.create_procurement_intent(payload, auth_user)

        results = await asyncio.gather(task1, task2, return_exceptions=True)

        successes = [r for r in results if isinstance(r, ProcurementIntent)]
        conflicts = [r for r in results if isinstance(r, ConflictError)]

        # Exactly one success, exactly one ConflictError
        assert len(successes) == 1, f"Expected 1 success, got: {results}"
        assert len(conflicts) == 1, f"Expected 1 conflict, got: {results}"

        # Identify which session experienced the conflict
        failed_session = session1 if isinstance(results[0], ConflictError) else session2

        # Verify that the failed session rolled back and remains fully
        # usable for subsequent queries
        subsequent_result = await failed_session.execute(text("SELECT 1"))
        assert subsequent_result.scalar() == 1, (
            "Failed session was unable to execute subsequent queries"
        )

    finally:
        await session1.close()
        await session2.close()

    # Verify exactly one intent exists in the database for this slot
    async with factory() as verify_session:
        stmt = select(ProcurementIntent).where(
            ProcurementIntent.farmer_id == farmer_id,
            ProcurementIntent.centre_id == centre_id,
            ProcurementIntent.crop_id == crop_id,
            ProcurementIntent.ready_date == target_date,
        )
        res = await verify_session.execute(stmt)
        persisted = list(res.scalars().all())
        assert len(persisted) == 1
