from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    IdentifierResponse,
    PaginationParams,
    PaginationResponse,
)


def test_identifier_response_accepts_valid_data() -> None:
    identifier = uuid4()
    created_at = datetime.now()

    schema = IdentifierResponse(
        id=identifier,
        created_at=created_at,
    )

    assert schema.id == identifier
    assert schema.created_at == created_at


def test_pagination_params_defaults() -> None:
    schema = PaginationParams()

    assert schema.page == 1
    assert schema.page_size == 20


def test_pagination_params_rejects_invalid_page() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page=0)


def test_pagination_params_rejects_large_page_size() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page_size=101)


def test_pagination_params_limit_matches_page_size() -> None:
    schema = PaginationParams(page_size=50)

    assert schema.limit == 50


def test_pagination_params_offset_for_first_page() -> None:
    schema = PaginationParams(page=1, page_size=20)

    assert schema.offset == 0


def test_pagination_params_offset_for_later_page() -> None:
    schema = PaginationParams(page=3, page_size=20)

    assert schema.offset == 40


def test_pagination_response_wraps_items() -> None:
    identifier = uuid4()
    created_at = datetime.now()

    response = PaginationResponse[IdentifierResponse](
        items=[IdentifierResponse(id=identifier, created_at=created_at)],
        page=1,
        page_size=20,
        total=1,
    )

    assert response.total == 1
    assert len(response.items) == 1
    assert response.items[0].id == identifier


def test_identifier_response_reads_from_attributes() -> None:
    class Row:
        def __init__(self, id: UUID, created_at: datetime) -> None:
            self.id = id
            self.created_at = created_at

    identifier = uuid4()
    created_at = datetime.now()
    row = Row(id=identifier, created_at=created_at)

    schema = IdentifierResponse.model_validate(row)

    assert schema.id == identifier
    assert schema.created_at == created_at
