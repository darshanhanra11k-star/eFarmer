from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.farmer import FarmerCreate, FarmerResponse


def test_farmer_create_accepts_valid_data() -> None:
    farmer = FarmerCreate(
        farmer_id="GOV-2026-000123",
        name="Ravi Kumar",
        phone="9876543210",
        village="Rampur",
        block="Sadar",
        district="Bokaro",
        state="Jharkhand",
    )

    assert farmer.farmer_id == "GOV-2026-000123"
    assert farmer.name == "Ravi Kumar"
    assert farmer.phone == "9876543210"
    assert farmer.village == "Rampur"
    assert farmer.block == "Sadar"
    assert farmer.district == "Bokaro"
    assert farmer.state == "Jharkhand"


def test_farmer_create_uses_optional_defaults() -> None:
    farmer = FarmerCreate(
        farmer_id="GOV-2026-000123",
        name="Ravi Kumar",
    )

    assert farmer.phone is None
    assert farmer.village is None
    assert farmer.block is None
    assert farmer.district is None
    assert farmer.state is None


def test_farmer_create_rejects_missing_farmer_id() -> None:
    with pytest.raises(ValidationError):
        FarmerCreate.model_validate(
            {
                "name": "Ravi Kumar",
                "phone": "9876543210",
            }
        )


def test_farmer_create_rejects_empty_farmer_id() -> None:
    with pytest.raises(ValidationError):
        FarmerCreate(
            farmer_id="",
            name="Ravi Kumar",
        )


def test_farmer_create_rejects_overlong_farmer_id() -> None:
    with pytest.raises(ValidationError):
        FarmerCreate(
            farmer_id="X" * 65,
            name="Ravi Kumar",
        )


def test_farmer_create_rejects_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        FarmerCreate(
            farmer_id="GOV-2026-000123",
            name="Ravi Kumar",
            phone="12345",
        )


def test_farmer_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        FarmerCreate(
            farmer_id="GOV-2026-000123",
            name="",
            phone="9876543210",
        )


def test_farmer_response_accepts_valid_data() -> None:
    resource_id = uuid4()
    created_at = datetime.now()
    updated_at = datetime.now()

    farmer = FarmerResponse(
        id=resource_id,
        farmer_id="GOV-2026-000123",
        created_at=created_at,
        updated_at=updated_at,
        name="Ravi Kumar",
        phone="9876543210",
        village="Rampur",
        block="Sadar",
        district="Bokaro",
        state="Jharkhand",
        active=True,
    )

    assert farmer.id == resource_id
    assert farmer.farmer_id == "GOV-2026-000123"
    assert farmer.created_at == created_at
    assert farmer.updated_at == updated_at
    assert farmer.name == "Ravi Kumar"
    assert farmer.phone == "9876543210"
    assert farmer.active is True


def test_farmer_response_reads_from_attributes() -> None:
    class Row:
        def __init__(self) -> None:
            self.id = uuid4()
            self.farmer_id = "GOV-2026-000123"
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
            self.name = "Ravi Kumar"
            self.phone = "9876543210"
            self.village = "Rampur"
            self.block = "Sadar"
            self.district = "Bokaro"
            self.state = "Jharkhand"
            self.active = True

    row = Row()
    farmer = FarmerResponse.model_validate(row)

    assert farmer.id == row.id
    assert farmer.farmer_id == row.farmer_id
    assert farmer.name == row.name
    assert farmer.phone == row.phone
    assert farmer.active == row.active


def test_farmer_response_rejects_empty_farmer_id() -> None:
    with pytest.raises(ValidationError):
        FarmerResponse(
            id=uuid4(),
            farmer_id="",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            name="Ravi Kumar",
        )


def test_farmer_response_rejects_overlong_farmer_id() -> None:
    with pytest.raises(ValidationError):
        FarmerResponse(
            id=uuid4(),
            farmer_id="X" * 65,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            name="Ravi Kumar",
        )
