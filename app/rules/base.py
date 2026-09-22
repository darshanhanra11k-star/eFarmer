from abc import ABC, abstractmethod

from app.rules.schemas import RuleEvaluationContext, RuleFailure, RuleResult


class BaseRule(ABC):
    rule_id: str
    rule_name: str
    failure_code: str
    failure_reason: str
    is_deferred: bool = False
    deferred_reason: str | None = None

    def create_pass_result(self) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=True,
            failure=None,
            deferred=False,
            deferred_reason=None,
        )

    def create_fail_result(
        self,
        code: str | None = None,
        reason: str | None = None,
    ) -> RuleResult:
        failure = RuleFailure(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            code=code or self.failure_code,
            reason=reason or self.failure_reason,
        )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=False,
            failure=failure,
            deferred=False,
            deferred_reason=None,
        )

    def create_deferred_result(
        self,
        reason: str | None = None,
    ) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=False,
            failure=None,
            deferred=True,
            deferred_reason=reason or self.deferred_reason,
        )

    @abstractmethod
    def evaluate(self, context: RuleEvaluationContext) -> RuleResult:
        """Evaluate the rule against the supplied context."""
        raise NotImplementedError
