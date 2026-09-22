from app.rules.base import BaseRule
from app.rules.schemas import RuleEvaluationContext, RuleResult


class FarmerActiveRule(BaseRule):
    rule_id = "RULE-001"
    rule_name = "FARMER_ACTIVE"
    failure_code = "FARMER_INACTIVE"
    failure_reason = "Farmer record is inactive."

    def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
        if context.farmer is None:
            return self.create_fail_result(
                code="MISSING_CONTEXT",
                reason="Farmer record is missing from evaluation context.",
            )
        is_active = getattr(context.farmer, "active", None)
        if is_active is True:
            return self.create_pass_result()
        return self.create_fail_result()


class CentreActiveRule(BaseRule):
    rule_id = "RULE-002"
    rule_name = "CENTRE_ACTIVE"
    failure_code = "CENTRE_INACTIVE"
    failure_reason = "Procurement centre is not accepting submissions."

    def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
        if context.centre is None:
            return self.create_fail_result(
                code="MISSING_CONTEXT",
                reason="Procurement centre record is missing from evaluation context.",
            )
        is_active = getattr(context.centre, "active", None)
        if is_active is True:
            return self.create_pass_result()
        return self.create_fail_result()


class CropActiveRule(BaseRule):
    rule_id = "RULE-003"
    rule_name = "CROP_ACTIVE"
    failure_code = "CROP_INACTIVE"
    failure_reason = "Crop is not currently supported."

    def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
        if context.crop is None:
            return self.create_fail_result(
                code="MISSING_CONTEXT",
                reason="Crop record is missing from evaluation context.",
            )
        is_active = getattr(context.crop, "active", None)
        if is_active is True:
            return self.create_pass_result()
        return self.create_fail_result()


class FarmerHasLandHoldingRule(BaseRule):
    rule_id = "RULE-004"
    rule_name = "FARMER_HAS_LAND_HOLDING"
    failure_code = "NO_ACTIVE_LAND_HOLDING"
    failure_reason = "Farmer has no active registered land holding."

    def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
        if context.land_holdings is None:
            return self.create_fail_result(
                code="MISSING_CONTEXT",
                reason="Farmer land holdings data is missing from evaluation context.",
            )

        has_active = any(
            getattr(h, "active", False) is True for h in context.land_holdings
        )
        if has_active:
            return self.create_pass_result()
        return self.create_fail_result()


class NoDuplicateActiveIntentRule(BaseRule):
    rule_id = "RULE-005"
    rule_name = "NO_DUPLICATE_ACTIVE_INTENT"
    failure_code = "DUPLICATE_ACTIVE_INTENT"
    failure_reason = (
        "Farmer already has an active request for this crop at this centre."
    )
    is_deferred = True
    deferred_reason = (
        "Missing schema dependency: M4-owned procurement_intents / "
        "procurement_requests table does not exist in current schema."
    )

    def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
        if context.active_intents is None:
            return self.create_deferred_result(self.deferred_reason)

        inactive_statuses = {"CANCELLED", "REJECTED", "COMPLETED"}
        target_centre = context.target_centre_id or getattr(context.centre, "id", None)
        target_crop = context.target_crop_id or getattr(context.crop, "id", None)

        for intent in context.active_intents:
            status = getattr(intent, "status", None)
            if status is None:
                continue
            status_str = status.value if hasattr(status, "value") else str(status)
            if status_str.upper() not in inactive_statuses:
                intent_centre = getattr(intent, "centre_id", None)
                intent_crop = getattr(intent, "crop_id", None)
                centre_matches = (
                    target_centre is None
                    or intent_centre is None
                    or str(intent_centre) == str(target_centre)
                )
                crop_matches = (
                    target_crop is None
                    or intent_crop is None
                    or str(intent_crop) == str(target_crop)
                )
                if centre_matches and crop_matches:
                    return self.create_fail_result()

        return self.create_pass_result()
