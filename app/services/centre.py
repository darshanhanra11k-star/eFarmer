from uuid import UUID

from app.core.exceptions import NotFoundError
from app.repositories.centre import CentreRepository
from app.schemas.centre import CentreResponse
from app.schemas.common import PaginationParams, PaginationResponse


class CentreService:
    def __init__(self, centre_repo: CentreRepository) -> None:
        self.centre_repo = centre_repo

    async def list_centres(
        self,
        params: PaginationParams,
    ) -> PaginationResponse[CentreResponse]:
        centres, total = await self.centre_repo.list_centres(
            offset=params.offset,
            limit=params.limit,
        )
        items = [CentreResponse.model_validate(centre) for centre in centres]
        return PaginationResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

    async def get_centre(self, centre_id: UUID) -> CentreResponse:
        centre = await self.centre_repo.get_by_id(centre_id)
        if centre is None:
            raise NotFoundError(message="Procurement centre not found.")

        return CentreResponse.model_validate(centre)
