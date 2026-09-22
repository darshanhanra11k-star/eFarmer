from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.models.centre import ProcurementCentre
from app.models.crop import Crop
from app.models.farmer import Farmer
from app.models.land_holding import FarmerLandHolding
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.rules.schemas import EvaluationMode, EvaluationStatus
from app.services.eligibility import EligibilityService


class _FakeScalarResult:
    def __init__(self, item: Any) -> None:
        self._item = item

    def scalar_one_or_none(self) -> Any:
        return self._item

    def scalar_one(self) -> Any:
        return self._item

    def scalars(self) -> Any:
        return self

    def all(self) -> list[Any]:
        if self._item is None:
            return []
        if isinstance(self._item, list):
            return self._item
        return [self._item]


class FakeEligibilitySession:
    def __init__(self) -> None:
        self.farmers: dict[Any, Farmer] = {}
        self.centres: dict[Any, ProcurementCentre] = {}
        self.crops: dict[Any, Crop] = {}
        self.holdings: dict[Any, FarmerLandHolding] = {}

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        sql = str(stmt)
        params = stmt.compile().params if hasattr(stmt, "compile") else {}

        if "FROM farmers" in sql:
            for f_id, f in self.farmers.items():
                for val in params.values():
                    if val == f_id or str(val) == str(f_id):
                        return _FakeScalarResult(f)
            return _FakeScalarResult(None)

        if "FROM procurement_centres" in sql:
            for c_id, c in self.centres.items():
                for val in params.values():
                    if val == c_id or str(val) == str(c_id):
                        return _FakeScalarResult(c)
            return _FakeScalarResult(None)

        if "FROM crops" in sql:
            for cr_id, cr in self.crops.items():
                for val in params.values():
                    if val == cr_id or str(val) == str(cr_id):
                        return _FakeScalarResult(cr)
            return _FakeScalarResult(None)

        if "FROM farmer_land_holdings" in sql:
            target_fid = None
            for val in params.values():
                if val in self.farmers or str(val) in [str(k) for k in self.farmers]:
                    target_fid = val
            matches = [
                h
                for h in self.holdings.values()
                if target_fid is None or str(h.farmer_id) == str(target_fid)
            ]
            return _FakeScalarResult(matches)

        return _FakeScalarResult(None)


@pytest.fixture
def fake_session() -> FakeEligibilitySession:
    session = FakeEligibilitySession()
    f = Farmer(
        id=uuid4(),
        farmer_id="F-ELIG-1",
        name="Eligible Farmer",
        active=True,
    )
    c = ProcurementCentre(
        id=uuid4(),
        name="Centre One",
        district="District 1",
        active=True,
    )
    cr = Crop(
        id=uuid4(),
        code="MAIZE",
        name="Maize",
        unit="Q",
        active=True,
    )
    h = FarmerLandHolding(
        id=uuid4(),
        farmer_id=f.id,
        survey_number="12/3",
        area_acres=Decimal("4.5"),
        active=True,
    )
    session.farmers[f.id] = f
    session.centres[c.id] = c
    session.crops[cr.id] = cr
    session.holdings[h.id] = h
    return session


async def test_eligibility_service_success(
    fake_session: FakeEligibilitySession,
) -> None:
    farmer = list(fake_session.farmers.values())[0]
    centre = list(fake_session.centres.values())[0]
    crop = list(fake_session.crops.values())[0]

    service = EligibilityService(
        farmer_repo=FarmerRepository(fake_session),  # type: ignore[arg-type]
        centre_repo=CentreRepository(fake_session),  # type: ignore[arg-type]
        crop_repo=CropRepository(fake_session),  # type: ignore[arg-type]
    )

    summary = await service.evaluate_eligibility(
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
        mode=EvaluationMode.ALL_FAILURES,
    )

    assert summary.eligible is True
    assert summary.status == EvaluationStatus.ELIGIBLE
    assert summary.failures == []


async def test_eligibility_service_inactive_centre(
    fake_session: FakeEligibilitySession,
) -> None:
    farmer = list(fake_session.farmers.values())[0]
    centre = list(fake_session.centres.values())[0]
    crop = list(fake_session.crops.values())[0]
    centre.active = False

    service = EligibilityService(
        farmer_repo=FarmerRepository(fake_session),  # type: ignore[arg-type]
        centre_repo=CentreRepository(fake_session),  # type: ignore[arg-type]
        crop_repo=CropRepository(fake_session),  # type: ignore[arg-type]
    )

    summary = await service.evaluate_eligibility(
        farmer_id=farmer.id,
        centre_id=centre.id,
        crop_id=crop.id,
    )

    assert summary.eligible is False
    assert summary.status == EvaluationStatus.REJECTED
    assert len(summary.failures) == 1
    assert summary.failures[0].code == "CENTRE_INACTIVE"


async def test_eligibility_service_nonexistent_farmer_raises_not_found(
    fake_session: FakeEligibilitySession,
) -> None:
    centre = list(fake_session.centres.values())[0]

    service = EligibilityService(
        farmer_repo=FarmerRepository(fake_session),  # type: ignore[arg-type]
        centre_repo=CentreRepository(fake_session),  # type: ignore[arg-type]
        crop_repo=CropRepository(fake_session),  # type: ignore[arg-type]
    )

    with pytest.raises(NotFoundError) as exc_info:
        await service.evaluate_eligibility(
            farmer_id=uuid4(),
            centre_id=centre.id,
        )
    assert "Farmer not found" in exc_info.value.message
