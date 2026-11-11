from typing import Any, Literal
from pydantic import BaseModel, Field

Priority = Literal["high", "medium", "low"]

class Recommendation(BaseModel):
    rule_id: str
    title: str
    priority: Priority
    evidence: dict[str, Any]
    suggested_action: str
    reason: str

class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    generated_at_utc: str
    data_mode: str
    warnings: list[str] = Field(default_factory=list)
    thresholds: dict[str, float | int] = Field(default_factory=dict)
