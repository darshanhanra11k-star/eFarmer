from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvaluationMode(StrEnum):
    FIRST_FAILURE = "FIRST_FAILURE"
    ALL_FAILURES = "ALL_FAILURES"


class EvaluationStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class RuleFailure(BaseModel):
    rule_id: str
    rule_name: str
    code: str
    reason: str

    model_config = ConfigDict(frozen=True)


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    failure: RuleFailure | None = None
    deferred: bool = False
    deferred_reason: str | None = None

    model_config = ConfigDict(frozen=True)


class RuleEvaluationSummary(BaseModel):
    status: EvaluationStatus
    eligible: bool
    mode: EvaluationMode
    failures: list[RuleFailure] = Field(default_factory=list)
    results: list[RuleResult] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class RuleEvaluationContext(BaseModel):
    farmer: Any | None = None
    centre: Any | None = None
    crop: Any | None = None
    land_holdings: list[Any] | None = None
    active_intents: list[Any] | None = None
    target_centre_id: UUID | None = None
    target_crop_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
