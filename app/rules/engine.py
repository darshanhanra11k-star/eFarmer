import logging
from collections.abc import Sequence

from app.rules.base import BaseRule
from app.rules.registry import RuleRegistry, get_default_registry
from app.rules.schemas import (
    EvaluationMode,
    EvaluationStatus,
    RuleEvaluationContext,
    RuleEvaluationSummary,
    RuleFailure,
    RuleResult,
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """Dedicated deterministic Rule Engine independent of web frameworks."""

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self.registry = registry if registry is not None else get_default_registry()

    def evaluate(
        self,
        context: RuleEvaluationContext,
        mode: EvaluationMode = EvaluationMode.FIRST_FAILURE,
        rule_ids: list[str] | None = None,
        include_deferred: bool = False,
    ) -> RuleEvaluationSummary:
        rules: Sequence[BaseRule] = self.registry.get_rules(
            rule_ids=rule_ids,
            include_deferred=include_deferred,
        )

        if not rules:
            return RuleEvaluationSummary(
                status=EvaluationStatus.ELIGIBLE,
                eligible=True,
                mode=mode,
                failures=[],
                results=[],
            )

        results: list[RuleResult] = []
        failures: list[RuleFailure] = []
        evaluation_error: bool = False

        for rule in rules:
            try:
                res = rule.evaluate(context)
            except Exception as exc:
                logger.exception(
                    "Unexpected error evaluating rule %s: %s", rule.rule_id, exc
                )
                res = RuleResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    passed=False,
                    failure=RuleFailure(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        code="EVALUATION_ERROR",
                        reason=f"Error evaluating rule {rule.rule_id}: {exc}",
                    ),
                )
                evaluation_error = True

            results.append(res)

            if not res.passed and not res.deferred:
                if res.failure is not None:
                    failures.append(res.failure)
                if mode == EvaluationMode.FIRST_FAILURE:
                    break

        if evaluation_error:
            status = EvaluationStatus.ERROR
            eligible = False
        elif failures:
            status = EvaluationStatus.REJECTED
            eligible = False
        else:
            status = EvaluationStatus.ELIGIBLE
            eligible = True

        return RuleEvaluationSummary(
            status=status,
            eligible=eligible,
            mode=mode,
            failures=failures,
            results=results,
        )
