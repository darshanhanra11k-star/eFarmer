from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.models.centre import ProcurementCentre
from app.models.crop import Crop
from app.models.farmer import Farmer
from app.models.land_holding import FarmerLandHolding
from app.rules.base import BaseRule
from app.rules.builtin import (
    CentreActiveRule,
    CropActiveRule,
    FarmerActiveRule,
    FarmerHasLandHoldingRule,
    NoDuplicateActiveIntentRule,
)
from app.rules.engine import RuleEngine
from app.rules.registry import RuleRegistry, get_default_registry
from app.rules.schemas import (
    EvaluationMode,
    EvaluationStatus,
    RuleEvaluationContext,
    RuleResult,
)


def _make_valid_context() -> RuleEvaluationContext:
    farmer = Farmer(
        id=uuid4(),
        farmer_id="F-RULE-1",
        name="Valid Farmer",
        active=True,
    )
    centre = ProcurementCentre(
        id=uuid4(),
        name="Valid Centre",
        district="District V",
        active=True,
    )
    crop = Crop(
        id=uuid4(),
        code="WHEAT",
        name="Wheat",
        unit="QUINTAL",
        active=True,
    )
    holding = FarmerLandHolding(
        id=uuid4(),
        farmer_id=farmer.id,
        survey_number="123/A",
        area_acres=Decimal("5.0"),
        active=True,
    )
    return RuleEvaluationContext(
        farmer=farmer,
        centre=centre,
        crop=crop,
        land_holdings=[holding],
        target_centre_id=centre.id,
        target_crop_id=crop.id,
    )


# 1. RULE-001 passes
def test_rule_001_farmer_active_passes() -> None:
    rule = FarmerActiveRule()
    farmer = Farmer(id=uuid4(), farmer_id="F-1", name="Active", active=True)
    ctx = RuleEvaluationContext(farmer=farmer)
    result = rule.evaluate(ctx)

    assert result.passed is True
    assert result.failure is None
    assert result.rule_id == "RULE-001"


# 2. RULE-001 fails
def test_rule_001_farmer_active_fails() -> None:
    rule = FarmerActiveRule()
    farmer = Farmer(id=uuid4(), farmer_id="F-2", name="Inactive", active=False)
    ctx = RuleEvaluationContext(farmer=farmer)
    result = rule.evaluate(ctx)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "FARMER_INACTIVE"
    assert result.failure.reason == "Farmer record is inactive."


# 3. RULE-002 passes
def test_rule_002_centre_active_passes() -> None:
    rule = CentreActiveRule()
    centre = ProcurementCentre(
        id=uuid4(), name="Centre A", district="Dist", active=True
    )
    ctx = RuleEvaluationContext(centre=centre)
    result = rule.evaluate(ctx)

    assert result.passed is True
    assert result.failure is None
    assert result.rule_id == "RULE-002"


# 4. RULE-002 fails
def test_rule_002_centre_active_fails() -> None:
    rule = CentreActiveRule()
    centre = ProcurementCentre(
        id=uuid4(), name="Centre B", district="Dist", active=False
    )
    ctx = RuleEvaluationContext(centre=centre)
    result = rule.evaluate(ctx)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "CENTRE_INACTIVE"
    assert result.failure.reason == "Procurement centre is not accepting submissions."


# 5. RULE-003 passes
def test_rule_003_crop_active_passes() -> None:
    rule = CropActiveRule()
    crop = Crop(id=uuid4(), code="RICE", name="Rice", unit="Q", active=True)
    ctx = RuleEvaluationContext(crop=crop)
    result = rule.evaluate(ctx)

    assert result.passed is True
    assert result.failure is None
    assert result.rule_id == "RULE-003"


# 6. RULE-003 fails
def test_rule_003_crop_active_fails() -> None:
    rule = CropActiveRule()
    crop = Crop(id=uuid4(), code="PULSE", name="Pulse", unit="Q", active=False)
    ctx = RuleEvaluationContext(crop=crop)
    result = rule.evaluate(ctx)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "CROP_INACTIVE"
    assert result.failure.reason == "Crop is not currently supported."


# 7. RULE-004 passes
def test_rule_004_farmer_has_land_holding_passes() -> None:
    rule = FarmerHasLandHoldingRule()
    f_id = uuid4()
    h1 = FarmerLandHolding(
        id=uuid4(),
        farmer_id=f_id,
        survey_number="1",
        area_acres=Decimal("2"),
        active=False,
    )
    h2 = FarmerLandHolding(
        id=uuid4(),
        farmer_id=f_id,
        survey_number="2",
        area_acres=Decimal("3"),
        active=True,
    )
    ctx = RuleEvaluationContext(land_holdings=[h1, h2])
    result = rule.evaluate(ctx)

    assert result.passed is True
    assert result.failure is None
    assert result.rule_id == "RULE-004"


# 8. RULE-004 fails
def test_rule_004_farmer_has_land_holding_fails() -> None:
    rule = FarmerHasLandHoldingRule()
    f_id = uuid4()
    # Case A: Only inactive holdings
    h1 = FarmerLandHolding(
        id=uuid4(),
        farmer_id=f_id,
        survey_number="1",
        area_acres=Decimal("2"),
        active=False,
    )
    ctx1 = RuleEvaluationContext(land_holdings=[h1])
    res1 = rule.evaluate(ctx1)
    assert res1.passed is False
    assert res1.failure is not None
    assert res1.failure.code == "NO_ACTIVE_LAND_HOLDING"
    assert res1.failure.reason == "Farmer has no active registered land holding."

    # Case B: Empty list
    ctx2 = RuleEvaluationContext(land_holdings=[])
    res2 = rule.evaluate(ctx2)
    assert res2.passed is False
    assert res2.failure is not None
    assert res2.failure.code == "NO_ACTIVE_LAND_HOLDING"


# 9. RULE-005 passes if its required data exists
def test_rule_005_passes_when_intents_exist_without_active_duplicates() -> None:
    rule = NoDuplicateActiveIntentRule()
    cid = uuid4()
    crid = uuid4()

    completed_intent = SimpleNamespace(
        id=uuid4(), centre_id=cid, crop_id=crid, status="COMPLETED"
    )
    cancelled_intent = SimpleNamespace(
        id=uuid4(), centre_id=cid, crop_id=crid, status="CANCELLED"
    )
    different_crop_intent = SimpleNamespace(
        id=uuid4(), centre_id=cid, crop_id=uuid4(), status="PENDING"
    )

    ctx = RuleEvaluationContext(
        target_centre_id=cid,
        target_crop_id=crid,
        active_intents=[completed_intent, cancelled_intent, different_crop_intent],
    )
    result = rule.evaluate(ctx)

    assert result.passed is True
    assert result.failure is None
    assert result.deferred is False


# 10. RULE-005 fails if its required data exists
def test_rule_005_fails_when_duplicate_active_intent_exists() -> None:
    rule = NoDuplicateActiveIntentRule()
    cid = uuid4()
    crid = uuid4()

    active_intent = SimpleNamespace(
        id=uuid4(), centre_id=cid, crop_id=crid, status="SUBMITTED"
    )

    ctx = RuleEvaluationContext(
        target_centre_id=cid,
        target_crop_id=crid,
        active_intents=[active_intent],
    )
    result = rule.evaluate(ctx)

    assert result.passed is False
    assert result.failure is not None
    assert result.failure.code == "DUPLICATE_ACTIVE_INTENT"
    assert (
        result.failure.reason
        == "Farmer already has an active request for this crop at this centre."
    )


# 11. deferred RULE-005 behavior when required schema/data does not exist
def test_rule_005_deferred_when_schema_data_missing() -> None:
    rule = NoDuplicateActiveIntentRule()
    ctx = RuleEvaluationContext(active_intents=None)
    result = rule.evaluate(ctx)

    assert result.passed is False
    assert result.deferred is True
    assert result.failure is None
    assert "Missing schema dependency" in (result.deferred_reason or "")


# 12. first-failure mode
def test_rule_engine_first_failure_mode() -> None:
    engine = RuleEngine()
    ctx = _make_valid_context()
    assert ctx.farmer is not None
    assert ctx.centre is not None
    # Invalidate both farmer and centre
    ctx.farmer.active = False
    ctx.centre.active = False

    summary = engine.evaluate(ctx, mode=EvaluationMode.FIRST_FAILURE)

    assert summary.status == EvaluationStatus.REJECTED
    assert summary.eligible is False
    assert summary.mode == EvaluationMode.FIRST_FAILURE
    assert len(summary.failures) == 1
    assert summary.failures[0].code == "FARMER_INACTIVE"
    # Stopped immediately after RULE-001
    assert len(summary.results) == 1
    assert summary.results[0].rule_id == "RULE-001"


# 13. evaluate-all-failures mode
def test_rule_engine_all_failures_mode() -> None:
    engine = RuleEngine()
    ctx = _make_valid_context()
    assert ctx.farmer is not None
    assert ctx.centre is not None
    assert ctx.crop is not None
    # Invalidate farmer, centre, and crop
    ctx.farmer.active = False
    ctx.centre.active = False
    ctx.crop.active = False

    summary = engine.evaluate(ctx, mode=EvaluationMode.ALL_FAILURES)

    assert summary.status == EvaluationStatus.REJECTED
    assert summary.eligible is False
    assert summary.mode == EvaluationMode.ALL_FAILURES
    assert len(summary.failures) == 3
    assert [f.code for f in summary.failures] == [
        "FARMER_INACTIVE",
        "CENTRE_INACTIVE",
        "CROP_INACTIVE",
    ]
    # Evaluated all rules
    assert len(summary.results) == 4  # RULE-001 through RULE-004


# 14. deterministic rule ordering
def test_rule_registry_deterministic_ascending_rule_order() -> None:
    registry = RuleRegistry()
    # Register out of order
    registry.register(FarmerHasLandHoldingRule())  # RULE-004
    registry.register(CropActiveRule())  # RULE-003
    registry.register(FarmerActiveRule())  # RULE-001
    registry.register(CentreActiveRule())  # RULE-002

    rules = registry.get_rules()
    rule_ids = [r.rule_id for r in rules]

    assert rule_ids == ["RULE-001", "RULE-002", "RULE-003", "RULE-004"]


# 15. deterministic failure ordering
def test_deterministic_failure_ordering() -> None:
    registry = RuleRegistry()
    registry.register(CropActiveRule())  # RULE-003
    registry.register(FarmerActiveRule())  # RULE-001
    registry.register(CentreActiveRule())  # RULE-002

    engine = RuleEngine(registry)
    ctx = _make_valid_context()
    assert ctx.farmer is not None
    assert ctx.centre is not None
    assert ctx.crop is not None
    ctx.farmer.active = False
    ctx.centre.active = False
    ctx.crop.active = False

    summary = engine.evaluate(ctx, mode=EvaluationMode.ALL_FAILURES)
    failure_ids = [f.rule_id for f in summary.failures]

    assert failure_ids == ["RULE-001", "RULE-002", "RULE-003"]


# 16. empty applicable rule set
def test_rule_engine_empty_rule_set() -> None:
    empty_registry = RuleRegistry()
    engine = RuleEngine(empty_registry)
    ctx = _make_valid_context()

    summary = engine.evaluate(ctx)

    assert summary.status == EvaluationStatus.ELIGIBLE
    assert summary.eligible is True
    assert summary.failures == []
    assert summary.results == []


# 17. structured failure codes
def test_structured_failure_codes() -> None:
    registry = get_default_registry()

    r1 = registry.get_rule("RULE-001")
    assert r1 is not None and r1.failure_code == "FARMER_INACTIVE"

    r2 = registry.get_rule("RULE-002")
    assert r2 is not None and r2.failure_code == "CENTRE_INACTIVE"

    r3 = registry.get_rule("RULE-003")
    assert r3 is not None and r3.failure_code == "CROP_INACTIVE"

    r4 = registry.get_rule("RULE-004")
    assert r4 is not None and r4.failure_code == "NO_ACTIVE_LAND_HOLDING"

    r5 = registry.get_rule("RULE-005")
    assert r5 is not None and r5.failure_code == "DUPLICATE_ACTIVE_INTENT"


# 18. Rule Engine independence from FastAPI
def test_rule_engine_independent_of_fastapi() -> None:
    import sys

    # Assert RuleEngine module does not import fastapi
    engine_module = sys.modules.get("app.rules.engine")
    assert engine_module is not None
    assert "fastapi" not in dir(engine_module)

    schemas_module = sys.modules.get("app.rules.schemas")
    assert schemas_module is not None
    assert "fastapi" not in dir(schemas_module)

    # Clean execution with plain dataclass/objects
    engine = RuleEngine()
    plain_ctx = RuleEvaluationContext(
        farmer=SimpleNamespace(active=True),
        centre=SimpleNamespace(active=True),
        crop=SimpleNamespace(active=True),
        land_holdings=[SimpleNamespace(active=True)],
    )
    summary = engine.evaluate(plain_ctx)
    assert summary.eligible is True


# 19. missing/invalid required context
def test_missing_or_invalid_required_context() -> None:
    engine = RuleEngine()
    empty_ctx = RuleEvaluationContext()

    summary = engine.evaluate(empty_ctx, mode=EvaluationMode.FIRST_FAILURE)

    assert summary.status == EvaluationStatus.REJECTED
    assert summary.eligible is False
    assert len(summary.failures) == 1
    assert summary.failures[0].code == "MISSING_CONTEXT"
    assert "Farmer record is missing" in summary.failures[0].reason


# 20. Exception safety in RuleEngine
def test_rule_engine_exception_handling() -> None:
    class CrashingRule(BaseRule):
        rule_id = "RULE-999"
        rule_name = "CRASH"
        failure_code = "CRASH_FAIL"
        failure_reason = "Crash"

        def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
            raise RuntimeError("Database connection died abruptly")

    reg = RuleRegistry()
    reg.register(CrashingRule())
    engine = RuleEngine(reg)

    summary = engine.evaluate(RuleEvaluationContext())
    assert summary.status == EvaluationStatus.ERROR
    assert summary.eligible is False
    assert len(summary.failures) == 1
    assert summary.failures[0].code == "EVALUATION_ERROR"
    assert "Database connection died abruptly" in summary.failures[0].reason
