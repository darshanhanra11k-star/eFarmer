from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.models.procurement import IntentStatus, ProcurementIntent
from app.models.user import User
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.procurement import ProcurementRepository
from app.rules.engine import RuleEngine
from app.rules.schemas import RuleEvaluationContext
from app.schemas.procurement import ProcurementIntentCreate


class ProcurementService:
    def __init__(
        self,
        procurement_repo: ProcurementRepository,
        farmer_repo: FarmerRepository,
        centre_repo: CentreRepository,
        crop_repo: CropRepository,
        session: AsyncSession,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        self.procurement_repo = procurement_repo
        self.farmer_repo = farmer_repo
        self.centre_repo = centre_repo
        self.crop_repo = crop_repo
        self.session = session
        self.rule_engine = rule_engine or RuleEngine()

    async def _get_current_db_user(self, subject: str) -> User:
        user = await self.farmer_repo.get_user_by_subject(subject)
        if user is None:
            raise NotFoundError(message="Authenticated user not found in database.")
        return user

    async def create_procurement_intent(
        self,
        payload: ProcurementIntentCreate,
        current_user: AuthenticatedUser,
    ) -> ProcurementIntent:
        user = await self._get_current_db_user(current_user.subject)

        # 1. Farmer ownership and RBAC enforcement
        # (do not trust client-supplied identity)
        if current_user.role == Role.FARMER:
            if user.farmer_id is None:
                raise PermissionDeniedError(
                    message="Authenticated user has no associated farmer profile.",
                )
            if payload.farmer_id is not None and payload.farmer_id != user.farmer_id:
                raise PermissionDeniedError(
                    message=(
                        "You do not have permission to create a "
                        "procurement intent for another farmer."
                    ),
                )
            effective_farmer_id = user.farmer_id
        elif current_user.role == Role.OFFICER:
            if payload.farmer_id is None:
                raise ValidationError(
                    message=(
                        "farmer_id is required when creating an intent as an officer."
                    ),
                )
            if user.centre_id is not None and user.centre_id != payload.centre_id:
                raise PermissionDeniedError(
                    message=(
                        "Officers cannot create procurement intents for centres "
                        "they are not assigned to."
                    ),
                )
            effective_farmer_id = payload.farmer_id
        else:
            raise PermissionDeniedError(
                message="User role is not permitted to create procurement intents.",
            )

        # 2. Load entities
        farmer = await self.farmer_repo.get_by_id(effective_farmer_id)
        if farmer is None:
            raise NotFoundError(message="Farmer not found.")

        centre = await self.centre_repo.get_by_id(payload.centre_id)
        if centre is None:
            raise NotFoundError(message="Procurement centre not found.")

        crop = await self.crop_repo.get_by_id(payload.crop_id)
        if crop is None:
            raise NotFoundError(message="Crop not found.")

        land_holdings = await self.farmer_repo.get_land_holdings_by_farmer_id(
            effective_farmer_id
        )

        # 3. Relationship validation
        valid_holding = any(h.id == payload.land_holding_id for h in land_holdings)
        if not valid_holding:
            raise ValidationError(
                message="The specified land holding does not belong to the farmer.",
            )

        # 4. Query active intents for duplicate evaluation
        active_intents = await self.procurement_repo.get_active_intents_for_farmer(
            farmer_id=effective_farmer_id,
            centre_id=payload.centre_id,
            crop_id=payload.crop_id,
        )

        # 5. Rule Engine evaluation
        context = RuleEvaluationContext(
            farmer=farmer,
            centre=centre,
            crop=crop,
            land_holdings=land_holdings,
            active_intents=active_intents,
            target_centre_id=payload.centre_id,
            target_crop_id=payload.crop_id,
        )
        summary = self.rule_engine.evaluate(context, include_deferred=True)
        if not summary.eligible:
            first_fail = summary.failures[0] if summary.failures else None
            reason = first_fail.reason if first_fail else "Eligibility check failed."
            if first_fail and first_fail.code == "DUPLICATE_ACTIVE_INTENT":
                raise ConflictError(message=reason)
            raise ValidationError(message=reason)

        # 6. Create PENDING intent (created_by comes strictly from authenticated user)
        intent = ProcurementIntent(
            farmer_id=effective_farmer_id,
            centre_id=payload.centre_id,
            crop_id=payload.crop_id,
            land_holding_id=payload.land_holding_id,
            expected_quantity_kg=payload.expected_quantity_kg,
            ready_date=payload.ready_date,
            status=IntentStatus.PENDING,
            created_by=user.id,
        )
        created_intent = await self.procurement_repo.create_intent(intent)

        # 7. Commit transaction atomically
        try:
            await self.session.commit()
            await self.session.refresh(created_intent)
            return created_intent
        except Exception:
            await self.session.rollback()
            raise

    async def get_procurement_by_id(
        self,
        intent_id: UUID,
        current_user: AuthenticatedUser,
    ) -> ProcurementIntent:
        user = await self._get_current_db_user(current_user.subject)

        intent = await self.procurement_repo.get_intent_by_id(intent_id)
        if intent is None:
            raise NotFoundError(message="Procurement record not found.")

        # Scoping validation
        if current_user.role == Role.FARMER and user.farmer_id != intent.farmer_id:
            raise PermissionDeniedError(
                message=(
                    "You do not have permission to access another farmer's "
                    "procurement record."
                ),
            )
        elif (
            current_user.role == Role.OFFICER
            and user.centre_id is not None
            and user.centre_id != intent.centre_id
        ):
            raise PermissionDeniedError(
                message=(
                    "You do not have permission to access records for another "
                    "procurement centre."
                ),
            )

        return intent
