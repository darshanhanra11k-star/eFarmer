from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.capacity.engine import CapacityEngine
from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.repositories.capacity import CapacityRepository
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.schemas.capacity import CapacityRecordResponse


class CapacityService:
    def __init__(
        self,
        capacity_repo: CapacityRepository,
        centre_repo: CentreRepository,
        crop_repo: CropRepository,
        farmer_repo: FarmerRepository,
        session: AsyncSession,
        engine: CapacityEngine | None = None,
    ) -> None:
        self.capacity_repo = capacity_repo
        self.centre_repo = centre_repo
        self.crop_repo = crop_repo
        self.farmer_repo = farmer_repo
        self.session = session
        self.engine = engine or CapacityEngine()

    async def get_centre_capacity(
        self,
        centre_id: UUID,
        crop_id: UUID,
        target_date: date,
        current_user: AuthenticatedUser,
    ) -> CapacityRecordResponse:
        centre = await self.centre_repo.get_by_id(centre_id)
        if centre is None or not centre.active:
            raise NotFoundError(message="Procurement centre not found.")

        if current_user.role == Role.FARMER:
            pass
        elif current_user.role == Role.OFFICER:
            user = await self.farmer_repo.get_user_by_subject(current_user.subject)
            if user is None:
                raise NotFoundError(message="Authenticated user not found in database.")
            if user.centre_id is None or user.centre_id != centre_id:
                raise PermissionDeniedError(
                    message=(
                        "Officers can only view capacity for their assigned centre."
                    ),
                )
        else:
            raise PermissionDeniedError(
                message="User role is not permitted to view capacity.",
            )

        crop = await self.crop_repo.get_by_id(crop_id)
        if crop is None or not crop.active:
            raise NotFoundError(message="Crop not found.")

        record = await self.capacity_repo.get_capacity_record(
            centre_id, crop_id, target_date
        )
        if record is None:
            raise NotFoundError(
                message=(
                    "Capacity record not found for the specified "
                    "centre, crop, and date."
                ),
            )

        metrics = self.engine.calculate(
            total_capacity_kg=record.total_capacity_kg,
            allocated_quantity_kg=record.allocated_quantity_kg,
            active=record.active,
        )

        return CapacityRecordResponse(
            centre_id=record.centre_id,
            crop_id=record.crop_id,
            date=record.date,
            total_capacity_kg=record.total_capacity_kg,
            allocated_quantity_kg=record.allocated_quantity_kg,
            procured_quantity_kg=record.procured_quantity_kg,
            available_capacity_kg=metrics.available_capacity_kg,
            utilisation=metrics.utilisation,
            capacity_status=metrics.capacity_status,
            active=record.active,
        )
