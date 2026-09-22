from decimal import Decimal

from app.capacity.engine import CapacityEngine, CapacityStatus
from app.core.exceptions import PermissionDeniedError
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.repositories.capacity import CapacityRepository
from app.repositories.centre import CentreRepository
from app.repositories.farmer import FarmerRepository
from app.schemas.priority_centre import (
    CentreEvaluationDetail,
    PriorityCentreSelectionRequest,
    PriorityCentreSelectionResponse,
)


class PriorityCentreService:
    def __init__(
        self,
        centre_repo: CentreRepository,
        capacity_repo: CapacityRepository,
        farmer_repo: FarmerRepository,
        capacity_engine: CapacityEngine | None = None,
    ) -> None:
        self.centre_repo = centre_repo
        self.capacity_repo = capacity_repo
        self.farmer_repo = farmer_repo
        self.capacity_engine = capacity_engine or CapacityEngine()

    async def select_priority_centre(
        self,
        payload: PriorityCentreSelectionRequest,
        current_user: AuthenticatedUser,
    ) -> PriorityCentreSelectionResponse:
        # 1. Farmer authorization verification
        if current_user.role == Role.FARMER:
            user = await self.farmer_repo.get_user_by_subject(current_user.subject)
            if user is None or user.farmer_id is None:
                raise PermissionDeniedError(
                    message="Authenticated user has no associated farmer profile.",
                )
        elif current_user.role == Role.OFFICER:
            pass
        else:
            raise PermissionDeniedError(
                message="User role is not permitted to perform centre selection.",
            )

        # 2. Sort preferences strictly by priority ascending (1 -> 2 -> 3 ...)
        sorted_prefs = sorted(payload.preferred_centres, key=lambda p: p.priority)

        evaluated_centres: list[CentreEvaluationDetail] = []
        selected = False
        selected_centre_id = None
        selected_priority = None
        available_capacity: Decimal | None = None

        # 3. Evaluate centres strictly in ascending priority order
        for pref in sorted_prefs:
            # Check 1: Centre existence and active status
            centre = await self.centre_repo.get_by_id(pref.centre_id)
            if centre is None:
                evaluated_centres.append(
                    CentreEvaluationDetail(
                        centre_id=pref.centre_id,
                        priority=pref.priority,
                        status="UNAVAILABLE",
                        reason="Procurement centre not found.",
                    )
                )
                continue

            if not centre.active:
                evaluated_centres.append(
                    CentreEvaluationDetail(
                        centre_id=pref.centre_id,
                        priority=pref.priority,
                        status="UNAVAILABLE",
                        reason="Procurement centre is inactive.",
                    )
                )
                continue

            # Check 2: Capacity record existence
            capacity_record = await self.capacity_repo.get_capacity_record(
                centre_id=pref.centre_id,
                crop_id=payload.crop_id,
                target_date=payload.ready_date,
                for_update=False,
            )
            if capacity_record is None:
                evaluated_centres.append(
                    CentreEvaluationDetail(
                        centre_id=pref.centre_id,
                        priority=pref.priority,
                        status="UNAVAILABLE",
                        reason=(
                            "No capacity record found for the specified crop and date."
                        ),
                    )
                )
                continue

            # Check 3: Capacity active status via Phase 13 CapacityEngine
            metrics = self.capacity_engine.calculate(
                total_capacity_kg=capacity_record.total_capacity_kg,
                allocated_quantity_kg=capacity_record.allocated_quantity_kg,
                active=capacity_record.active,
            )
            if metrics.capacity_status == CapacityStatus.INACTIVE:
                evaluated_centres.append(
                    CentreEvaluationDetail(
                        centre_id=pref.centre_id,
                        priority=pref.priority,
                        status="UNAVAILABLE",
                        reason="Capacity is inactive for the specified crop and date.",
                    )
                )
                continue

            # Check 4: Capacity sufficiency for requested quantity
            if metrics.available_capacity_kg < payload.requested_quantity_kg:
                evaluated_centres.append(
                    CentreEvaluationDetail(
                        centre_id=pref.centre_id,
                        priority=pref.priority,
                        status="UNAVAILABLE",
                        reason=(
                            f"Insufficient capacity: "
                            f"{metrics.available_capacity_kg} kg available, "
                            f"{payload.requested_quantity_kg} kg requested."
                        ),
                    )
                )
                continue

            # Check 5: All checks passed -> First available centre selected!
            selected = True
            selected_centre_id = pref.centre_id
            selected_priority = pref.priority
            available_capacity = metrics.available_capacity_kg

            evaluated_centres.append(
                CentreEvaluationDetail(
                    centre_id=pref.centre_id,
                    priority=pref.priority,
                    status="AVAILABLE",
                    reason="Sufficient capacity available.",
                )
            )

            # STOP immediately. Lower-priority centres are never evaluated.
            break

        # 4. Construct domain response
        if (
            selected
            and selected_centre_id is not None
            and selected_priority is not None
        ):
            return PriorityCentreSelectionResponse(
                success=True,
                selected_centre_id=selected_centre_id,
                selected_priority=selected_priority,
                crop_id=payload.crop_id,
                ready_date=payload.ready_date,
                requested_quantity_kg=f"{payload.requested_quantity_kg:.2f}",
                available_capacity_kg=(
                    f"{available_capacity:.2f}"
                    if available_capacity is not None
                    else None
                ),
                evaluated_centres=evaluated_centres,
                message=(
                    f"Centre {selected_centre_id} selected with priority "
                    f"{selected_priority}."
                ),
            )

        return PriorityCentreSelectionResponse(
            success=False,
            selected_centre_id=None,
            selected_priority=None,
            crop_id=payload.crop_id,
            ready_date=payload.ready_date,
            requested_quantity_kg=f"{payload.requested_quantity_kg:.2f}",
            available_capacity_kg=None,
            evaluated_centres=evaluated_centres,
            message="No preferred centre available satisfying the requested quantity.",
        )
