from uuid import UUID

from app.core.exceptions import NotFoundError
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.rules.engine import RuleEngine
from app.rules.schemas import (
    EvaluationMode,
    RuleEvaluationContext,
    RuleEvaluationSummary,
)


class EligibilityService:
    """Service to coordinate domain data loading and rule engine evaluation."""

    def __init__(
        self,
        farmer_repo: FarmerRepository,
        centre_repo: CentreRepository,
        crop_repo: CropRepository | None = None,
        rule_engine: RuleEngine | None = None,
    ) -> None:
        self.farmer_repo = farmer_repo
        self.centre_repo = centre_repo
        self.crop_repo = crop_repo
        self.rule_engine = rule_engine if rule_engine is not None else RuleEngine()

    async def evaluate_eligibility(
        self,
        farmer_id: UUID,
        centre_id: UUID,
        crop_id: UUID | None = None,
        mode: EvaluationMode = EvaluationMode.FIRST_FAILURE,
    ) -> RuleEvaluationSummary:
        farmer = await self.farmer_repo.get_by_id(farmer_id)
        if farmer is None:
            raise NotFoundError(message="Farmer not found.")

        centre = await self.centre_repo.get_by_id(centre_id)
        if centre is None:
            raise NotFoundError(message="Procurement centre not found.")

        crop = None
        if crop_id is not None and self.crop_repo is not None:
            crop = await self.crop_repo.get_by_id(crop_id)
            if crop is None:
                raise NotFoundError(message="Crop not found.")

        land_holdings = await self.farmer_repo.get_land_holdings_by_farmer_id(farmer_id)

        context = RuleEvaluationContext(
            farmer=farmer,
            centre=centre,
            crop=crop,
            land_holdings=land_holdings,
            target_centre_id=centre_id,
            target_crop_id=crop_id,
        )

        return self.rule_engine.evaluate(context, mode=mode)
