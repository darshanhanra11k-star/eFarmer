from app.rules.base import BaseRule
from app.rules.builtin import (
    CentreActiveRule,
    CropActiveRule,
    FarmerActiveRule,
    FarmerHasLandHoldingRule,
    NoDuplicateActiveIntentRule,
)


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, BaseRule] = {}

    def register(self, rule: BaseRule) -> None:
        self._rules[rule.rule_id] = rule

    def unregister(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> BaseRule | None:
        return self._rules.get(rule_id)

    def get_rules(
        self,
        rule_ids: list[str] | None = None,
        include_deferred: bool = False,
    ) -> list[BaseRule]:
        # Always sort strictly by rule_id ascending
        sorted_ids = sorted(self._rules.keys())
        rules: list[BaseRule] = []

        target_ids = set(rule_ids) if rule_ids is not None else None

        for rid in sorted_ids:
            if target_ids is not None and rid not in target_ids:
                continue
            rule = self._rules[rid]
            if rule.is_deferred and not include_deferred:
                continue
            rules.append(rule)

        return rules


def get_default_registry() -> RuleRegistry:
    registry = RuleRegistry()
    registry.register(FarmerActiveRule())
    registry.register(CentreActiveRule())
    registry.register(CropActiveRule())
    registry.register(FarmerHasLandHoldingRule())
    registry.register(NoDuplicateActiveIntentRule())
    return registry
