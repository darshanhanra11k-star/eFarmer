from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IdentifierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginationResponse[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int
